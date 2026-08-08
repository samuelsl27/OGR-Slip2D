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

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SliceForces:
    """Resolved force quantities for one slice.

    Attributes:
        w_soil: soil weight after the vertical seismic coefficient,
            ``weight · (1 − kv)`` [kN/m]. This is what a seismic force is
            proportional to, and what the surcharge is already folded into.
        w_total: total vertical load carried by the base, soil plus ponded
            water [kN/m]. This is what the base normal and the gravity
            driving term must use.
        h_seismic: magnitude of the pseudo-static horizontal force,
            ``kh · w_soil`` [kN/m]. Deliberately proportional to the SOIL
            weight only, so ponded water contributes no inertial force.
        h_water: net horizontal external water force, signed in +x [kN/m].
        m_water_ref0: moment of the horizontal water forces about y = 0,
            ``Σ F_h · y`` [kN]. Combine with :meth:`water_moment_about`.
    """

    w_soil: float
    w_total: float
    h_seismic: float
    h_water: float
    m_water_ref0: float

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
    w_soil = s.weight * (1.0 - kv)
    water_v = getattr(s, "water_weight", 0.0)
    return SliceForces(
        w_soil=w_soil,
        w_total=w_soil + water_v,
        # kh multiplies the SOIL weight, not the ponded water: the seismic
        # force is "seismic coefficient × area of slice × unit weight of
        # the slice material". Water has no shear strength, so its motion
        # develops no force the sliding mass has to carry.
        h_seismic=kh * w_soil,
        h_water=getattr(s, "water_force_h", 0.0),
        m_water_ref0=getattr(s, "water_force_h_moment", 0.0),
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
