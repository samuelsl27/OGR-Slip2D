# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Moment equilibrium about an axis, for surfaces that have no centre.

A circle has a centre of rotation by definition, every moment arm is its
radius, and the radius cancels out of the ratio — so its moment equation can
be written with almost no geometry at all. A polyline has none of that: each
slice base has its own arm, the base normal stops pointing at the axis and so
contributes a moment of its own, and a horizontal force needs the elevation at
which it acts. This module is where that geometry lives, ONCE, for the four
methods that have a moment equation: Bishop, Ordinary, Spencer and GLE.

Everything here is a CROSS PRODUCT: the moment of a force ``F`` applied at
``P`` about the axis ``O`` is ``(P − O) × F``. That is the whole point of the
module. Three earlier attempts at this derived "arms" by hand and all three
came out wrong — once by 6 %, once by 13 %, once by 8 % — always through a
sign, never through the physics (see docs/changelog/CHANGELOG_v0.1.92.md). A
cross product takes its sign from the geometry, so there is nothing left to
get backwards.

Two signs still have to be decided, and neither is decided by hand:

  * **Which way the block turns.** It turns the way its own weight turns it
    about the axis, so ``rotation`` is the sign of the weight's moment.
  * **Which way the base shear acts.** Each slice's base velocity follows from
    that rotation, and the shear opposes it.

A third follows from the first, and it is the one that was wrong in two
methods until v0.1.105: **the direction of the pseudo-static seismic force**.
``SliceForces.h_seismic`` is a MAGNITUDE — ``kh · W``, unsigned — so it has to
be given a direction before it can be given a moment. The moment axis always
sits above the slip surface, so every slice's base moves horizontally in the
sense of ``rotation``, and the seismic force is ``rotation · h_seismic`` in x.
Applied unsigned it points right whatever the slope does; on a slope
descending to the LEFT it then holds the mass back and the factor of safety
GROWS with the earthquake. Measured on a homogeneous slope and its mirror
image, the same arc, 40 slices, kh = 0.15:

    Bishop on a polyline    1.318056 descending right    3.332505 mirrored

``h_water`` and the support's ``f_h`` are already SIGNED in +x by the slicer,
because they are real forces with a known direction. They must not be
multiplied by the rotation, and they are not.

References:
    Bishop, A.W. (1955). "The use of the slip circle in the stability analysis
        of slopes." Géotechnique 5(1), 7-17.
    Spencer, E. (1967). "A method of analysis of the stability of embankments
        assuming parallel inter-slice forces." Géotechnique 17(1), 11-26.
    Fredlund, D.G. & Krahn, J. (1977). "Comparison of slope stability methods
        of analysis." Can. Geotech. J. 14(3), 429-439.
    Abramson, L.W., Lee, T.S., Sharma, S. & Boyce, G.M. (2001). "Slope
        Stability and Stabilization Methods", 2nd ed., Wiley.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

from .external_forces import slice_forces
from .surface import moment_axis


# ----------------------------------------------------------------------
def axis_for(project, surface) -> tuple[float, float]:
    """The moment axis of ``surface``, honouring the user's override.

    ``SearchSettings.axis_x`` / ``axis_y`` hold the axis the user placed by
    hand. HALF an axis is not an axis: one coordinate does not define a point,
    so a setting with only one of the two falls back to the automatic
    construction rather than pairing the typed value with a computed one.
    A circle ignores the override entirely — it has a centre.
    """
    override = None
    search = getattr(getattr(project, "settings", None), "search", None)
    ax = getattr(search, "axis_x", None)
    ay = getattr(search, "axis_y", None)
    if ax is not None and ay is not None:
        override = (float(ax), float(ay))
    return moment_axis(surface, override)


# ----------------------------------------------------------------------
def base_frame(axis, s) -> tuple[float, float, float, float, float, float]:
    """``(x_mid, y_mid, tx, ty, nx, ny)`` for one slice base.

    The base is the straight CHORD between the slice's two base corners, which
    is what the slicer actually built (v0.1.100); it is not the arc, and not
    the tangent at the slice's own abscissa. ``(tx, ty)`` runs left to right
    along that chord, and ``(nx, ny)`` is the unit normal pointing from the
    base TOWARDS the axis, i.e. into the sliding mass.
    """
    ox, oy = axis
    xa, ya = s.base_x_left, s.base_y_left
    xb, yb = s.base_x_right, s.base_y_right
    length = math.hypot(xb - xa, yb - ya) or 1e-9
    tx, ty = (xb - xa) / length, (yb - ya) / length
    xm, ym = 0.5 * (xa + xb), 0.5 * (ya + yb)
    nx, ny = -ty, tx
    if nx * (ox - xm) + ny * (oy - ym) < 0.0:
        nx, ny = -nx, -ny
    return xm, ym, tx, ty, nx, ny


def slice_cg_y(s) -> float:
    """Elevation at which a slice's inertial force acts.

    Midway between the mean top and the mean base, the centroid of a
    rectangular column — which is what every method in this project has used
    for the seismic term since it was written.
    """
    return 0.5 * (0.5 * (s.top_y_left + s.top_y_right)
                  + 0.5 * (s.base_y_left + s.base_y_right))


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class MomentTerms:
    """The moment sum about one axis, split so it can be inspected.

    ``shear`` is the moment of the base shear with the factor of safety
    divided out, so the balance ``driving + shear / F = 0`` gives
    ``F = −shear / driving`` — which is what :meth:`factor_of_safety` returns.
    """

    axis: tuple
    rotation: float
    weight: float
    normal: float
    external: float
    shear: float

    @property
    def driving(self) -> float:
        return self.weight + self.normal + self.external

    def factor_of_safety(self) -> Optional[float]:
        """``−shear / driving``, or None when there is no driving moment."""
        d = self.driving
        if abs(d) < 1e-9:
            return None
        f = -self.shear / d
        return f if math.isfinite(f) else None


# ----------------------------------------------------------------------
def rotation_sense(axis, s_list, weights: Sequence[float]) -> float:
    """Which way the block turns: the sign of its own weight's moment.

    Kept separate from :func:`moment_terms` because the seismic force has to
    be signed with it BEFORE the normal forces can be computed, and Ordinary —
    which gets its normal by projecting the external forces onto the base —
    needs exactly that ordering.
    """
    ox, _oy = axis
    total = 0.0
    for s, w in zip(s_list, weights):
        xm = 0.5 * (s.base_x_left + s.base_x_right)
        total += (xm - ox) * (-w)
    return 1.0 if total >= 0.0 else -1.0


# ----------------------------------------------------------------------
def moment_terms(
    axis,
    s_list,
    weights: Sequence[float],
    resisting: Sequence[float],
    normals: Sequence[float],
    kh: float = 0.0,
    kv: float = 0.0,
    sup=None,
    tangential: Optional[Sequence[float]] = None,
    tangential_passive: Optional[Sequence[float]] = None,
    rotation: Optional[float] = None,
    forces: Optional[Sequence] = None,
) -> MomentTerms:
    """Sum every moment about ``axis``.

    Args:
        axis: the point moments are taken about, from :func:`axis_for`.
        s_list: the slices, left to right.
        weights: total vertical DOWNWARD load on each slice [kN/m]. The moment
            of a vertical force depends only on its abscissa, so it is applied
            at the base midpoint. The caller folds in whatever it must —
            ponded water always. A support's vertical component does NOT
            belong here since v0.1.115: it is applied at the support's own
            abscissa through ``sup``, because the slice's centre of gravity is
            not where a bolt crosses the surface.
        resisting: tangential resisting force of each base with the factor of
            safety divided out, i.e. ``S · F``. For Ordinary, whose factor is
            a plain ratio, that is the available strength ``tau · l``.
        normals: base normal force of each slice [kN/m], positive pressing.
        kh, kv: seismic coefficients. Only ``kh`` produces a moment of its
            own; ``kv`` is already inside ``weights``.
        sup: :class:`~ogr_slip2d.support_integration.SupportTerms`. Only its
            NORMAL part is read — ``nf_h`` / ``nf_v`` applied at
            ``(x_app, y_app)`` — and only by the methods that resolve that
            part inside the slice equilibrium (Spencer, GLE). Bishop and
            Ordinary put the same normal part inside ``resisting`` as
            ``T_N·tan φ'`` and pass no ``sup`` at all.
        tangential: extra force along each base that follows the SHEAR's own
            sign, from ACTIVE supports. It joins the DRIVING side, which is
            the reference's Eqn. 1: ``F = M_resisting / (M_overturning −
            M_reinforcement)``.
        tangential_passive: the same from PASSIVE supports, which instead
            joins the RESISTING side — Eqn. 3, ``F = (M_resisting +
            M_reinforcement) / M_overturning``. Splitting the two is what
            makes the Active/Passive control move the number on a
            non-circular surface; until v0.1.114 every caller handed the SUM
            through ``tangential`` and seven of the nine methods answered the
            same figure either way.
        rotation: pass the value from :func:`rotation_sense` when the caller
            already needed it; otherwise it is computed here.
        forces: the :class:`~ogr_slip2d.external_forces.SliceForces` the caller
            already built, to save resolving them a second time. Every caller
            has them: this sits inside a fixed-point iteration over every trial
            surface of a search, so one avoidable object per slice per pass is
            worth not allocating.

    ``sup`` and the two ``tangential*`` lists are DIFFERENT halves of the
    same support, so passing all three is correct and is what Spencer and GLE
    do: ``sup`` carries the normal part, the lists carry the tangential one.
    What must never happen is the normal part arriving twice — through
    ``sup`` AND already summed into ``resisting`` as ``T_N·tan φ'``.

    Returns:
        The :class:`MomentTerms`.
    """
    ox, oy = axis
    if rotation is None:
        rotation = rotation_sense(axis, s_list, weights)

    def moment(px, py, fx, fy):
        return (px - ox) * fy - (py - oy) * fx

    m_weight = m_normal = m_shear = m_extra = 0.0
    for i, s in enumerate(s_list):
        xm, ym, tx, ty, nx, ny = base_frame(axis, s)
        w = weights[i]
        m_weight += moment(xm, ym, 0.0, -w)
        m_normal += moment(xm, ym, normals[i] * nx, normals[i] * ny)

        # The base point moves with the rotation; the shear opposes it.
        vx, vy = -rotation * (ym - oy), rotation * (xm - ox)
        shear_sign = -1.0 if (vx * tx + vy * ty) >= 0.0 else 1.0
        q = resisting[i]
        m_shear += moment(xm, ym, shear_sign * q * tx, shear_sign * q * ty)
        if tangential is not None and tangential[i]:
            t_extra = tangential[i]
            m_extra += moment(xm, ym, shear_sign * t_extra * tx,
                              shear_sign * t_extra * ty)
        if tangential_passive is not None and tangential_passive[i]:
            # Same force, same sign, the OTHER side of the fraction bar:
            # ``driving`` collects ``m_extra`` while ``factor_of_safety``
            # divides by it, and ``m_shear`` is the numerator.
            t_pas = tangential_passive[i]
            m_shear += moment(xm, ym, shear_sign * t_pas * tx,
                              shear_sign * t_pas * ty)

        f = slice_forces(s, kh, kv) if forces is None else forces[i]
        if f.h_seismic:
            # A MAGNITUDE, signed by the failure sense. See the module
            # docstring: unsigned, it holds the mass back on half the slopes.
            m_extra += moment(xm, slice_cg_y(s), rotation * f.h_seismic, 0.0)
        if f.h_water:
            # Already signed in +x. Its elevation comes from the stored moment
            # about y = 0 rather than from an application height, because two
            # water forces with OPPOSITE signs can act on the same slice and a
            # force-weighted mean height is undefined there.
            m_extra += moment(xm, f.m_water_ref0 / f.h_water, f.h_water, 0.0)
        if sup is not None and sup.present and (sup.nf_h[i] or sup.nf_v[i]):
            # The NORMAL part, at the point the support actually crosses the
            # surface. About a circle's centre this moment is exactly zero;
            # about a general axis it is not, and that is why it is taken
            # here instead of being assumed away.
            m_extra += moment(sup.x_app[i], sup.y_app[i],
                              sup.nf_h[i], sup.nf_v[i])

    return MomentTerms(axis=(ox, oy), rotation=rotation, weight=m_weight,
                       normal=m_normal, external=m_extra, shear=m_shear)
