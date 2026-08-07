# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Support integration into LEM solvers.

This module computes the force contribution of each support (bolt /
geosynthetic / pile / etc.) on a slip surface, and produces a list of
``SupportEffect`` records that the LEM solver can sum into its
equilibrium equations.

Implementation follows Slide's convention:

  - Each support intersects the slip surface at a single point (if at
    all). At that point we evaluate ``force_at(distance_from_head)``
    which returns the MINIMUM of all applicable failure-mode capacities
    in kN per unit width of slope.

  - The support force orientation is decided by ``ForceOrientation``:

      * tangent_to_slip:    along slip-surface tangent at intersection
      * parallel_to_support: along support axis
      * bisector:           halfway between tangent and parallel
      * horizontal:         along positive x (used for piles only)
      * perpendicular_to_pile: perpendicular to support axis
      * user_defined:       at ``user_angle_deg`` from horizontal

  - The force is then decomposed into HORIZONTAL (H_s) and VERTICAL
    (V_s) components. The slice into whose base x-range the intersection
    falls receives those components, plus a flag for Active vs Passive.

  - Solver-side: an Active support REDUCES the driving moment / force
    by the projection of the support force on the slip surface; a
    Passive support INCREASES the resisting moment / force by the
    same projection (divided by F in the iteration).

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ogr_core.project import Project
    from ogr_core.support import SupportInstance, SupportType

    from .surface import SurfaceProtocol


@dataclass
class SupportEffect:
    """Per-slice support contribution.

    Attributes:
        slice_index: index of the slice whose base contains the
            intersection
        intersection_x, intersection_y: scene coordinates of the hit
        force_magnitude: kN/m of slope width (already accounts for
            out-of-plane spacing)
        force_angle_rad: orientation from positive horizontal axis.
            Positive = up-and-to-the-right.
        force_h: horizontal component F·cos(angle)  (kN/m)
        force_v: vertical component F·sin(angle)    (kN/m)
        is_active: True for Active (Method A) support, False for Passive
        support_id: id of the SupportInstance for traceability
    """
    slice_index: int
    intersection_x: float
    intersection_y: float
    force_magnitude: float
    force_angle_rad: float
    force_h: float
    force_v: float
    is_active: bool
    support_id: str


def _slip_polyline(surface, slices) -> list[tuple[float, float]]:
    """Build a polyline (list of (x, y)) representing the slip-surface
    base, ordered by x. Works for both circular and non-circular
    surfaces.
    """
    if not slices:
        return []
    pts: list[tuple[float, float]] = []
    s_list = slices.slices if hasattr(slices, "slices") else slices
    if not s_list:
        return []
    # First slice's left
    pts.append((s_list[0].base_x_left, s_list[0].base_y_left))
    for s in s_list:
        pts.append((s.base_x_right, s.base_y_right))
    return pts


def _slip_tangent_at_x(slices, x: float) -> Optional[float]:
    """Return the slope (dy/dx) of the slip surface at x.

    Approximates by linear interpolation between adjacent base
    endpoints. Returns None if x is outside the surface range.
    """
    s_list = slices.slices if hasattr(slices, "slices") else slices
    for s in s_list:
        if s.base_x_left <= x <= s.base_x_right + 1e-9:
            dx = s.base_x_right - s.base_x_left
            if abs(dx) < 1e-12:
                return 0.0
            dy = s.base_y_right - s.base_y_left
            return dy / dx
    return None


def _support_force_angle(
    support: "SupportInstance",
    slip_tangent: float,
    is_left_to_right_failure: bool = True,
) -> float:
    """Compute the angle at which the support force is applied.

    Returns angle in radians from positive x. The convention follows
    Slide's force-application rules per orientation type.

    The orientation is taken so that the support RESISTS the sliding
    direction — i.e. for a slide moving LEFT (most typical), the
    resisting force has a horizontal component pointing RIGHT (+x).
    """
    from ogr_core.support import ForceOrientation

    o = support.orientation
    axis_angle = support.axis_angle_rad()  # head → tail

    # The slip tangent vector points along the slip surface; we
    # orient it to oppose the sliding direction (resisting tangent).
    # If sliding is right→left, the resisting tangent points right
    # (positive cos). The slip-surface tangent has slope ``slip_tangent``;
    # the resisting tangent angle is therefore atan(slip_tangent).
    if is_left_to_right_failure:
        # Slide moves rightward → resisting tangent points left
        tangent_angle = math.atan(slip_tangent) + math.pi
    else:
        # Slide moves leftward → resisting tangent points right
        tangent_angle = math.atan(slip_tangent)

    # Support axis: pointing from tail → head (the resisting direction
    # of an anchored bolt is from anchor toward the slope face)
    support_resisting_angle = axis_angle + math.pi

    if o == ForceOrientation.TANGENT_TO_SLIP:
        return tangent_angle
    if o == ForceOrientation.PARALLEL_TO_SUPPORT:
        return support_resisting_angle
    if o == ForceOrientation.BISECTOR:
        # Bisector of tangent and parallel-to-support
        a1 = tangent_angle
        a2 = support_resisting_angle
        # Wrap to nearest equivalent angles
        while a2 - a1 > math.pi:
            a2 -= 2 * math.pi
        while a1 - a2 > math.pi:
            a2 += 2 * math.pi
        return 0.5 * (a1 + a2)
    if o == ForceOrientation.HORIZONTAL:
        return math.pi if is_left_to_right_failure else 0.0
    if o == ForceOrientation.PERPENDICULAR_TO_PILE:
        # Perpendicular to support axis. Pick the perpendicular that
        # opposes sliding (positive y component on the up-slope side).
        return axis_angle + math.pi / 2
    if o == ForceOrientation.USER_DEFINED:
        return math.radians(support.user_angle_deg)
    return support_resisting_angle


def compute_support_effects(
    project: "Project",
    surface: "SurfaceProtocol",
    slices,
) -> list[SupportEffect]:
    """Compute the list of per-slice support effects on a slip surface.

    Returns an empty list if the project has no supports or none of
    them intersect the slip surface.
    """
    from ogr_core.support import support_registry

    supports = getattr(project, "supports", []) or []
    if not supports:
        return []

    # Failure direction: from settings
    is_l2r = False
    try:
        from ogr_core.project.units import FailureDirection
        fd = project.settings.units.failure_direction
        is_l2r = (fd == FailureDirection.LEFT_TO_RIGHT)
    except Exception:  # noqa: BLE001
        is_l2r = False

    slip_xy = _slip_polyline(surface, slices)
    if len(slip_xy) < 2:
        return []
    registry = support_registry()
    s_list = slices.slices if hasattr(slices, "slices") else slices
    effects: list[SupportEffect] = []
    # Build a lookup of support-type properties by id (project.support_types)
    type_props = {}
    for stype in getattr(project, "support_types", []) or []:
        type_props[stype.TYPE_ID] = stype

    for support in supports:
        hit = support.intersection_with_polyline(slip_xy)
        if hit is None:
            continue
        ix, iy, d_from_head = hit
        # Find which slice this intersection falls into
        slice_idx = None
        for i, s in enumerate(s_list):
            if s.base_x_left - 1e-9 <= ix <= s.base_x_right + 1e-9:
                slice_idx = i
                break
        if slice_idx is None:
            continue

        # Resolve the support-type property (force_at function)
        stype = type_props.get(support.type_id)
        if stype is None:
            # Fall back to creating a default instance from registry
            cls = registry.get(support.type_id)
            if cls is None:
                continue
            stype = cls()

        L_total = support.length()
        F = stype.force_at(d_from_head, L_total)
        if F <= 0:
            continue

        # Force orientation angle
        slip_slope = _slip_tangent_at_x(slices, ix) or 0.0
        ang = _support_force_angle(support, slip_slope, is_l2r)
        Fh = F * math.cos(ang)
        Fv = F * math.sin(ang)

        from ogr_core.support import ForceApplication
        is_active = (support.force_application == ForceApplication.ACTIVE)

        effects.append(SupportEffect(
            slice_index=slice_idx,
            intersection_x=ix,
            intersection_y=iy,
            force_magnitude=F,
            force_angle_rad=ang,
            force_h=Fh,
            force_v=Fv,
            is_active=is_active,
            support_id=support.id,
        ))

    return effects
