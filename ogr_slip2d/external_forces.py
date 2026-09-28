# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Per-slice force bookkeeping shared by every LEM method.

Before v0.1.61 each method computed its own ``W_eff = weight * (1 - kv)``
and used that single number for the gravity term, the seismic term and the
normal on the base. That was fine while the only load was the soil weight,
but it cannot express the two things this version adds:

  * **Ponded water** on top of a slice contributes a vertical weight AND a
    horizontal thrust, and the seismic coefficients must NOT act on either
    (water has no shear strength, so it develops no inertial force that the
    sliding mass has to carry).
  * **Water in a tension crack** contributes a horizontal thrust applied at
    a known elevation, which is a driving force.

``slice_forces`` returns the four quantities every method needs, so each
one applies the same convention and the per-method edits stay small enough
to audit. The equilibrium equations themselves stay in each method.

Sign conventions, all shared with :mod:`ogr_slip2d.slicer`:

  * ``+x`` is to the right; horizontal forces are signed accordingly.
  * Vertical forces are stored as magnitudes acting DOWNWARD.
  * ``kh`` is applied in the direction of failure by the caller, which
    knows the sliding sense; ``H_seismic`` here is the unsigned magnitude.
  * ``kv`` POSITIVE is a vertical seismic force pointing DOWN, so the soil
    carries ``W·(1 + kv)``. :func:`seismic_soil_weight` is the one place that
    says so; every method, the checks and the post-processing go through it
    or through :func:`slice_forces`.

v0.1.214 (D170) — the pseudo-static earthquake is the inertial force of the
sliding mass, mass times acceleration in each direction, and BOTH components
are proportional to the STATIC weight: ``F_h = kh·W`` and ``F_v = kv·W``
(Terzaghi 1950; Kramer 1996, §10.6.1; EN 1998-5:2004, §4.1.3.3, where
``F_H = 0.5·α·S·W`` and ``F_V = ±0.5·F_H``). What the sign of ``kv`` means is
a definition, and OGR states it where the user types it — ``SeismicLoad``,
the seismic dialog — as the reference documentation does: positive is a
force directed downwards. Until v0.1.213 this function applied the opposite
sense, ``W·(1 − kv)``, while ``ogr_core.hydraulic.excess_pore_pressure``
added ``kv·σ_v`` as the text says: one coefficient, two physical senses.

It also scaled the horizontal force with the vertical one,
``kh·W·(1 − kv)``, and that is wrong with EITHER sign: the horizontal
inertial force of a mass does not depend on its vertical acceleration.
Mononobe-Okabe and EN 1998-5 Annex E write the inclination of the resultant
body force as ``tan θ = kh / (1 ± kv)``, which only follows from
``F_h = kh·W``; a coupled ``F_h`` would make it ``kh`` whatever ``kv``.
Measured on a 40° plane through a 56° slope (c = 5 kPa, φ = 30°),
kh = 0.15 and kv = +0.1: 0.711390 before, against the closed-form wedge
0.691024 with kv down and 0.691573 with kv up. See
``tests/test_seismic_convention_v1214.py``.

v0.1.219 (D206) — WHICH weight. The seismic force acts on the SOIL of the
slice: "Seismic Coefficient × area of slice × Unit Weight of slice
material", as the reference documentation defines it, and the centre of
gravity of the sliding soil mass (Terzaghi 1950; Duncan, Wright & Brandon
2014, §10.1). The slicer folds the vertical component of distributed and
line loads into ``weight``, and until this version both coefficients
multiplied that sum, so a surcharge was accelerated like soil. A surcharge
is a traction on the ground, as the reference defines its distributed loads,
and carries no inertia here; a fill that has mass is drawn as a material
(decision of the owner, 2026-09-28). The slice keeps its soil weight apart
(``Slice.soil_weight``) and :func:`seismic_vertical_load` is what the base
carries under ``kv``: ``W_soil·(1 + kv) + the loads``. Without loads, or with
``kv = 0``, bit for bit what it was.

And the SIGN of ``kh`` (v0.1.219, entered in D206): ``kh`` is the magnitude
of the horizontal inertial force, which every method applies in the sliding
sense of its own surface, out of the slope. The input refuses a negative
value (``ogr_core.project.rules.seismic_coefficient_refusal``), and the
methods apply whatever value reaches them in the same way: until this
version the moment sums on a circle of Bishop and of Spencer/GLE skipped a
negative ``kh`` (``if kh > 0``) while every force sum applied it, so one
model gave a method-dependent answer.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass

# v0.1.219 (D206) -- a module switch, read at call time, so an A/B can turn
# it off and a test can demand that it moves the number (rule 7). Off, the
# seismic coefficients multiply the slice weight WITH its surcharge, as
# before v0.1.219. Only a slice with a distributed or line load differs.
SEISMIC_SOIL_ONLY = True


def seismic_soil_weight(weight: float, kv: float) -> float:
    """The soil weight under the vertical seismic coefficient, ``W·(1 + kv)``.

    ``kv`` positive points DOWN (see the module docstring). The one place
    that sign lives: a method that needs the vertical load without building
    a :class:`SliceForces` — the sliding-sense sums, the back analysis —
    goes through :func:`seismic_vertical_load`, which calls this, instead of
    writing the factor out, which is how seven copies of ``(1 − kv)`` came
    to disagree with the documentation together.
    """
    return weight * (1.0 + kv)


def seismic_soil_part(s) -> float:
    """The part of ``s.weight`` the seismic coefficients act on: its soil.

    ``s.soil_weight`` is set by the slicer before it adds the loads; a slice
    built by hand (a test, the support stand-in of ``ogr_core.support.bond``)
    has none and is all soil, as every slice was before v0.1.219. With
    ``SEISMIC_SOIL_ONLY`` off, the whole weight, loads included.
    """
    soil = getattr(s, "soil_weight", None)
    if soil is None or not SEISMIC_SOIL_ONLY:
        return s.weight
    return soil


def seismic_vertical_load(s, kv: float) -> float:
    """The vertical load a slice base carries under ``kv``, ponded water
    excluded: ``W_soil·(1 + kv) + (W − W_soil)`` (v0.1.219, D206).

    With ``kv = 0`` it is ``s.weight`` itself, bit for bit: the factor is 1
    and there is nothing to separate. With no load on the slice the second
    term is exactly zero, so ``W·(1 + kv)`` as before. See the module
    docstring for why the loads carry no seismic force.
    """
    if not kv:
        return s.weight
    soil = seismic_soil_part(s)
    return seismic_soil_weight(soil, kv) + (s.weight - soil)


@dataclass(frozen=True)
class SliceForces:
    """Resolved force quantities for one slice.

    Attributes:
        w_soil: the vertical load of the slice under the vertical seismic
            coefficient, ponded water excluded [kN/m]: its soil weight times
            ``(1 + kv)``, with ``kv`` positive downward, plus the vertical
            component of the loads folded into ``weight``, which carries no
            seismic factor since v0.1.219 (D206)
            (:func:`seismic_vertical_load`).
        w_total: total vertical load carried by the base, soil plus ponded
            water [kN/m]. This is what the base normal and the gravity
            driving term must use.
        h_seismic: the pseudo-static horizontal force, ``kh · W_soil``
            [kN/m], in the sliding sense of the surface: on the STATIC
            weight, so the vertical coefficient does not scale it (v0.1.214,
            D170), and on the SOIL only, so neither ponded water nor a
            surcharge contributes an inertial force (v0.1.219, D206).
        h_water: net horizontal external water force, signed in +x [kN/m].
        m_water_ref0: moment of the horizontal water forces about y = 0,
            ``Σ F_h · y`` [kN]. Combine with :meth:`water_moment_about`.
        h_pond: the part of ``h_water`` that is the ponded water's pressure
            on the slice top, signed in +x [kN/m] (v0.1.217, D199). Already
            inside ``h_water``.
    """

    w_soil: float
    w_total: float
    h_seismic: float
    h_water: float
    m_water_ref0: float
    h_pond: float = 0.0

    def water_moment_about(self, y_c: float) -> float:
        """Moment of the horizontal water forces about elevation ``y_c``."""
        return y_c * self.h_water - self.m_water_ref0


def slice_forces(s, kh: float = 0.0, kv: float = 0.0) -> SliceForces:
    """Resolve the forces acting on slice ``s``.

    Args:
        s: a :class:`ogr_slip2d.slicer.Slice`.
        kh: horizontal seismic coefficient (0 when seismic is off).
        kv: vertical seismic coefficient; positive acts downward.

    Returns:
        The :class:`SliceForces` for that slice.
    """
    w_soil = seismic_vertical_load(s, kv)
    water_v = getattr(s, "water_weight", 0.0)
    return SliceForces(
        w_soil=w_soil,
        w_total=w_soil + water_v,
        # kh multiplies the SOIL weight, not the ponded water: the seismic
        # force is "seismic coefficient × area of slice × unit weight of
        # the slice material". Water has no shear strength, so its motion
        # develops no force the sliding mass has to carry; nor the loads,
        # which are tractions on the ground (D206). And the STATIC weight,
        # not ``w_soil``: the horizontal inertial force of a mass does not
        # depend on its vertical acceleration (D170).
        h_seismic=kh * seismic_soil_part(s),
        h_water=getattr(s, "water_force_h", 0.0),
        m_water_ref0=getattr(s, "water_force_h_moment", 0.0),
        h_pond=getattr(s, "pond_force_h", 0.0),
    )


def interslice_water_thrust(project, slices) -> list:
    """Horizontal water thrust on each inter-slice face, in kN/m.

    Returns ``n+1`` values: the thrust on the left face of slice 0, then
    on the right face of every slice. The two free ends are zero, because
    the sliding mass has no height where the slip surface daylights.

    **Why this exists.** In the total-stress formulation the force
    transmitted across a vertical inter-slice boundary is the sum of an
    effective part carried by the soil skeleton and the water pressure
    integrated over the face, which is purely HORIZONTAL. Methods that
    solve for the inter-slice inclination (Spencer, GLE) or assume it
    horizontal (Bishop, Janbu) are insensitive to the split. A method that
    PRESCRIBES the inclination — Lowe-Karafiath fixes it at ½(β+α) — is
    not: forcing a resultant dominated by nearly-horizontal water pressure
    to lie at 20° invents a large spurious vertical component.

    Measured on a fully submerged slope, ignoring this made Lowe-Karafiath
    report FS ≈ 5 where every rigorous method gives 1.60. Separating the
    thrust brings it back to 1.61 and makes it independent of the depth of
    water above the slope, as it must be.

    The integration samples the project's own pore-pressure model along
    the face, so it stays correct for Hu ≠ 1, Ru and grid models — not
    only for a hydrostatic water table.
    """
    from ogr_core.geometry import Vertex
    from ogr_core.hydraulic.pore_pressure import pore_pressure_at

    s_list = slices.slices if hasattr(slices, "slices") else slices
    n = len(s_list)
    thrust = [0.0] * (n + 1)
    if n == 0:
        return thrust

    samples = 9  # trapezoidal points over the face; cheap and ample here
    for i, s in enumerate(s_list[:-1]):
        x = s.base_x_right
        y_lo, y_hi = s.base_y_right, s.top_y_right
        h = y_hi - y_lo
        if h <= 0.0:
            continue
        total = 0.0
        for k in range(samples):
            y = y_lo + h * k / (samples - 1)
            u = pore_pressure_at(project, Vertex(x, y), s.material,
                                 ground_surface_y=y_hi)
            w = 0.5 if k in (0, samples - 1) else 1.0
            total += w * u
        thrust[i + 1] = total * h / (samples - 1)
    return thrust


def has_water_forces(slices) -> bool:
    """True if any slice carries an external water force.

    Lets a method skip the extra terms entirely — and keeps results for
    models without ponded water or a watered tension crack bit-identical
    to the previous version.
    """
    s_list = slices.slices if hasattr(slices, "slices") else slices
    for s in s_list:
        if getattr(s, "water_weight", 0.0) or getattr(s, "water_force_h", 0.0):
            return True
    return False
