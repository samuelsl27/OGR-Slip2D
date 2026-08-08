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

v0.1.64 — ``resolve_support_terms`` below turns those raw effects into
the two quantities the equilibrium equations actually need, T_S and T_N,
with their SIGNS. Until then only Bishop consumed the effects, and it did
so through ``abs(projection)``, which made a support that pushed the mass
downhill improve the factor of safety exactly as much as one holding it
back — see the header of ``tests/test_supports_all_methods_v164.py``.

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


@dataclass(frozen=True)
class SupportTerms:
    """Support contributions resolved onto each slice base.

    Every list is indexed by slice. Signs follow the slicer's conventions
    (``+x`` right, ``+y`` up) and the sliding sense passed in:

        t_active   resisting TANGENTIAL force from Active supports [kN/m].
                   Positive opposes sliding. Enters the DRIVING side of
                   the factor of safety as a subtraction.
        t_passive  the same for Passive supports, but it enters the
                   RESISTING side as an addition.
        n_press    NORMAL force pressing the slice onto its base [kN/m].
                   Positive presses, negative lifts. Multiplied by tan φ'
                   it is the frictional resistance the support mobilises,
                   which the previous implementation dropped entirely.
        f_h, f_v   raw resultant per slice, +x and +y [kN/m], for the
                   methods that solve equilibrium rather than a ratio.
        y_app      elevation at which the resultant acts, for moments.

    The distinction between Active and Passive is, as the reference
    itself admits, partly arbitrary — it is a modelling choice about
    whether a reinforcement is pre-tensioned. What is NOT arbitrary is
    that both must be signed.
    """

    t_active: list
    t_passive: list
    n_press: list
    f_h: list
    f_v: list
    y_app: list
    present: bool = False
    # Resisting HORIZONTAL component, for the methods whose equilibrium is
    # a horizontal force balance rather than a moment balance. Janbu's
    # driving side is Σ W·tan α + Σ kh·W, a sum of horizontal forces, so
    # projecting the support onto the base tangent there would be mixing
    # two different balances.
    h_active: list = None
    h_passive: list = None

    def total_active_t(self) -> float:
        return sum(self.t_active)

    def total_passive_t(self) -> float:
        return sum(self.t_passive)

    def total_active_h(self) -> float:
        return sum(self.h_active or ())

    def total_passive_h(self) -> float:
        return sum(self.h_passive or ())


# Shared "there is no reinforcement here" answer. Immutable in practice:
# every consumer guards on ``present`` before indexing, and the empty
# lists make ``total_*`` return 0.0 without a special case.
_EMPTY_TERMS = SupportTerms([], [], [], [], [], [], False, [], [])


def resolve_support_terms(
    project: "Project",
    surface: "SurfaceProtocol",
    slices,
    slide_sign: float,
) -> SupportTerms:
    """Resolve every support onto the base of the slice it crosses.

    ``slide_sign`` is the sense of sliding the caller derived from the
    driving moment: the DOWNSLOPE unit tangent of a base at angle α is

        t_d = −slide_sign · (cos α, sin α)

    which is the vector that makes the weight ``(0, −W)`` produce the
    driving term ``+slide_sign · W · sin α`` every method already uses.
    A support force **F** then contributes ``F · t_d`` to driving, so its
    RESISTING tangential component is ``−F · t_d``.

    The inward base normal is ``n = (−sin α, cos α)``; a force presses the
    slice onto its base by ``−F · n``. A nail perpendicular to the surface
    and pointing into the slope therefore presses (positive), and one
    pointing out of it lifts (negative) — which is the sign the previous
    implementation had no way of expressing, since it kept only
    ``abs`` of the tangential part.
    """
    # Every method calls this for every trial surface, so the no-support
    # case — which is most models, and all of the validation suite — must
    # cost nothing. Checking before allocating the eight per-slice lists
    # is the difference between a free call and eight allocations per
    # surface per method.
    if not (getattr(project, "supports", None) or ()):
        return _EMPTY_TERMS

    s_list = slices.slices if hasattr(slices, "slices") else slices
    n = len(s_list)
    if n == 0:
        return _EMPTY_TERMS
    try:
        effects = compute_support_effects(project, surface, slices)
    except Exception:  # noqa: BLE001
        return _EMPTY_TERMS
    if not effects:
        return _EMPTY_TERMS

    from ogr_core.support import ForceApplication

    t_active = [0.0] * n
    t_passive = [0.0] * n
    h_active = [0.0] * n
    h_passive = [0.0] * n
    n_press = [0.0] * n
    f_h = [0.0] * n
    f_v = [0.0] * n
    y_app = [0.0] * n
    w_h = [0.0] * n  # |F_h| weights for the application elevation

    for eff in effects:
        i = eff.slice_index
        if i < 0 or i >= n:
            continue
        a = s_list[i].base_angle
        ca, sa = math.cos(a), math.sin(a)
        # Resisting tangential: −F·t_d  with  t_d = −slide_sign·(cos, sin)
        t_r = slide_sign * (eff.force_h * ca + eff.force_v * sa)
        # Pressing normal: −F·n  with  n = (−sin, cos)
        t_n = eff.force_h * sa - eff.force_v * ca
        # Resisting HORIZONTAL component. The sliding direction has x
        # component −slide_sign (the sense in which the water thrust is
        # already resolved by every force method), so a force resists by
        # +slide_sign·F_h.
        h_r = slide_sign * eff.force_h
        if eff.is_active:
            t_active[i] += t_r
            h_active[i] += h_r
        else:
            t_passive[i] += t_r
            h_passive[i] += h_r
        n_press[i] += t_n
        f_h[i] += eff.force_h
        f_v[i] += eff.force_v
        w = abs(eff.force_h)
        y_app[i] += w * eff.intersection_y
        w_h[i] += w

    for i in range(n):
        if w_h[i] > 0.0:
            y_app[i] /= w_h[i]
        else:
            # No horizontal component to take a moment: the elevation is
            # irrelevant, but the base is the honest place to report.
            y_app[i] = 0.5 * (s_list[i].base_y_left + s_list[i].base_y_right)

    return SupportTerms(t_active, t_passive, n_press, f_h, f_v, y_app, True,
                        h_active, h_passive)


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
