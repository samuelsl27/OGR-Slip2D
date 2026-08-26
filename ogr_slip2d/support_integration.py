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

      * tangent_to_slip:    along the slip-surface tangent, in the sense
        that RESISTS sliding
      * parallel_to_support: along the support axis, HEAD → TAIL, i.e.
        from the slope face towards the anchor — the direction a bolt in
        tension pulls the sliding mass
      * bisector:           halfway between tangent and parallel
      * horizontal:         opposing the sliding direction
      * perpendicular_to_pile: perpendicular to the support axis, on the
        side that resists sliding
      * user_defined:       at ``user_angle_deg`` from horizontal

    Only the first, the fourth and the fifth consult the sliding sense.
    The parallel direction is pure geometry: a bolt whose anchor lies
    downhill of the slip surface genuinely pushes the mass, and saying so
    is the point of publishing the angle.

  - v0.1.124 — a type that declares ``SUPPORTS_SHEAR`` contributes a
    SECOND vector: ``shear_at`` perpendicular to its own axis, on the side
    that opposes the slide, added to the axial one. The reference states
    it in words: "the vector perpendicular to the bolt direction, and
    opposite to the direction of failure, is added to the overall bolt
    capacity vector [...] the support force at the base of the slice is no
    longer parallel to the support but angled in a direction opposite to
    the slip direction". Until this version ``shear_at`` was declared by
    three types, editable and serialised, and read by nobody.

  - The force is then decomposed into HORIZONTAL (H_s) and VERTICAL
    (V_s) components. The slice into whose base x-range the intersection
    falls receives those components, plus a flag for Active vs Passive.

  - Solver-side, for the RATIO methods (Ordinary/Fellenius, Bishop,
    Janbu simplified and corrected), the reference writes one pair of
    equations and OGR follows it literally:

        Active   F = (R + T_N·tan φ') / (D − T_S)
        Passive  F = (R + T_N·tan φ' + T_S) / D

    ``T_S`` is the support force projected ON THE BASE of the slice it
    crosses, and ``T_N`` the projection on the base normal. Both are
    added OUTSIDE the per-slice ``m_α`` / ``n_α`` normalisation, which
    is how the reference writes them.

    v0.1.115 — the SAME split now governs the methods that solve complete
    equilibrium (Spencer, GLE, the two Corps of Engineers, Lowe-Karafiath).
    Until then those five took the support's whole Cartesian resultant as an
    external force on the slice, which had two consequences:

      * Active and Passive came out BIT FOR BIT EQUAL in all five — the
        reference's own Active/Passive case, verification problem 85, gave
        the same six digits either way while Bishop separated them by 20 %.
        A configurable control that cannot move the number is worse than no
        control at all;
      * a PASSIVE support cannot be a Cartesian load at all. Passive
        reinforcement develops only as far as the rest of the slope
        mobilises, so what acts is ``T_S/F`` — and that is exactly what turns
        ``F = R/(D − T)`` into ``F = (R + T)/D``. A resultant stored as
        ``f_h`` / ``f_v`` has nowhere to put that F, which is why one number
        came out for both settings.

    So the support arrives here SPLIT, and every solver reads the split:

      * the NORMAL part is a Cartesian load on the slice (``nf_h`` /
        ``nf_v``) and enters the equilibrium whole in both cases, so
        ``T_N·tan φ'`` falls out of it instead of being added by hand;
      * the TANGENTIAL part is a RESISTANCE on the base, mobilised at
        ``t_active + t_passive/F``, which is the only place the Active /
        Passive flag has any arithmetic effect.

    The ACTIVE answer barely moves under this, and that is the honest
    result: applying ``t_active`` at face value on the base is algebraically
    the same statement as applying the whole resultant as a Cartesian load.
    On the published circle of verification problem 85 the two Corps methods
    and Lowe-Karafiath do not move a digit and Spencer moves 0.07 %. It is
    PASSIVE that changes — from equal-to-Active to within 1.2 % (GLE) and
    4.3 % (Spencer) of what a φ' = 0 circle forces, against 18.6 % and
    27.7 % before.

    The normal part is resolved INSIDE the equilibrium rather than bolted on
    outside ``m_α`` as Bishop does; the difference is second-order and is
    the same modelling choice ``bishop.py`` already documents.

    The reference publishes FOUR equations, not two — one pair for moment
    equilibrium and one for force equilibrium — which is precisely what says
    the distinction is defined for the complete-equilibrium methods too:

        Active   moment  F = M_resisting / (M_overturning − M_reinforcement)
        Active   force   F = τ_available / (τ_required − T_reinforcement)
        Passive  moment  F = (M_resisting + M_reinforcement) / M_overturning
        Passive  force   F = (τ_available + T_reinforcement) / τ_required

    and it attributes the pair to Methods A and B of Duncan & Wright (2005),
    chapter 8. In both of them ``T_N·tan φ'`` is in the NUMERATOR; only the
    tangential term changes sides.

    NOT divided by F. Method B of Duncan & Wright (2005) factors the
    reinforcement by F as well as the soil strength, and this module's
    docstring claimed as much until v0.1.113 — but measured against the
    reference it is wrong: on problem 85, which is the reference's own
    Active/Passive case (Duncan & Wright fig. 6.34), dividing moves the
    published passive value from +0.23 % to −5.91 %.

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
        nf_h, nf_v the NORMAL part alone, back in Cartesian components
                   (+x, +y) [kN/m]. This is the Cartesian LOAD a solver
                   hands to the slice's own equilibrium; the tangential part
                   travels separately through ``t_active`` / ``t_passive``,
                   because only there can it be mobilised at T/F.
                   Identically ``n_press·(sin α, −cos α)``.
        f_h, f_v   the WHOLE resultant per slice, +x and +y [kN/m]. No
                   solver reads it since v0.1.115 — it is what a report or
                   a data tip shows, and what locates the slice a support
                   crossed.
        x_app,     where the resultant acts, force-magnitude weighted when
        y_app      several supports cross the same slice. Needed for the
                   moment of the normal part about a general axis; about a
                   circle's centre that moment is exactly zero, because a
                   base normal passes through the centre.

    The distinction between Active and Passive is, as the reference
    itself admits, partly arbitrary — it is a modelling choice about
    whether a reinforcement is pre-tensioned. What is NOT arbitrary is
    that both must be signed.

    v0.1.115 — ``t_active`` and ``t_passive`` are no longer only the ratio
    methods' business. Every method now takes the tangential part from one
    of these two lists, and the ONLY thing Active and Passive change is
    which side of the fraction bar it lands on. See the module docstring
    for the four published equations that say so.

    v0.1.113 — there used to be a third pair, ``h_active`` / ``h_passive``,
    holding the HORIZONTAL projection, and Janbu was its only consumer.
    The reference resolves a support into exactly two numbers, and writes
    the same two equations for every ratio method:

        Active   F = (R + T_N·tanφ') / (D − T_S)
        Passive  F = (R + T_N·tanφ' + T_S) / D

    ``T_S`` is the component ON THE BASE. Janbu taking the horizontal one
    instead put a 15 % systematic error into every reinforced Janbu run —
    see ``tests/test_support_projection_v1113.py`` for the six published
    planes that measure it. The pair is gone rather than left unused: a
    dead field is an invitation to route a method through it again.
    """

    t_active: list
    t_passive: list
    n_press: list
    nf_h: list
    nf_v: list
    f_h: list
    f_v: list
    x_app: list
    y_app: list
    present: bool = False
    #: v0.1.122 -- the COUPLE left over from applying a resultant somewhere
    #: other than the point where the support crosses the surface. Zero for
    #: every support that acts at its own intersection, which is all seven
    #: types that existed before. One scalar for the whole surface because a
    #: couple is independent of the axis it is measured about; only the four
    #: methods that write a moment equation can honour it, and the ones that
    #: cannot say so rather than ignoring it silently.
    couple: float = 0.0

    def total_active_t(self) -> float:
        return sum(self.t_active)

    def total_passive_t(self) -> float:
        return sum(self.t_passive)


# Shared "there is no reinforcement here" answer. Immutable in practice:
# every consumer guards on ``present`` before indexing, and the empty
# lists make ``total_*`` return 0.0 without a special case.
_EMPTY_TERMS = SupportTerms([], [], [], [], [], [], [], [], [],
                            False, 0.0)


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
    n_press = [0.0] * n
    f_h = [0.0] * n
    f_v = [0.0] * n
    x_app = [0.0] * n
    y_app = [0.0] * n
    w_app = [0.0] * n  # |F| weights for the application point
    couple = 0.0

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
        if eff.is_active:
            t_active[i] += t_r
        else:
            t_passive[i] += t_r
        n_press[i] += t_n
        f_h[i] += eff.force_h
        f_v[i] += eff.force_v
        # v0.1.115 — weighted by the force MAGNITUDE, not by |F_h| as it was
        # until v0.1.114. The old weight had no answer for a support with no
        # horizontal component: it fell through to the base midpoint, which
        # is not where a vertical anchor acts. The two agree whenever every
        # support crossing a slice is horizontal, which is every case of the
        # validation bank that this weight reaches.
        w = abs(eff.force_magnitude)
        x_app[i] += w * eff.intersection_x
        y_app[i] += w * eff.intersection_y
        w_app[i] += w
        couple += eff.couple()

    # The normal part alone, back in Cartesian components. Written from
    # ``n_press`` rather than accumulated per effect on purpose: every effect
    # in a slice shares that slice's base direction, so the sum of the normal
    # parts IS the normal part of the sum, and saying it once is one place
    # for the sign convention to live.
    nf_h = [0.0] * n
    nf_v = [0.0] * n
    for i in range(n):
        if n_press[i]:
            a = s_list[i].base_angle
            nf_h[i] = n_press[i] * math.sin(a)
            nf_v[i] = -n_press[i] * math.cos(a)
        if w_app[i] > 0.0:
            x_app[i] /= w_app[i]
            y_app[i] /= w_app[i]
        else:
            # Nothing crossed this slice: the base midpoint is the honest
            # place to report a point that no force is applied at.
            x_app[i] = 0.5 * (s_list[i].base_x_left + s_list[i].base_x_right)
            y_app[i] = 0.5 * (s_list[i].base_y_left + s_list[i].base_y_right)

    return SupportTerms(t_active, t_passive, n_press, nf_h, nf_v,
                        f_h, f_v, x_app, y_app, True, couple)


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
        application_x, application_y: where the resultant ACTS. Equal to
            the intersection for every support type but a retaining wall
            asked to act at the centroid of its pressure diagram
            (v0.1.122). Translating a force does not change the force, so
            the two points differ by a pure COUPLE and nothing else --
            which is exactly how it enters the solvers.
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
    application_x: float = float("nan")
    application_y: float = float("nan")

    def __post_init__(self) -> None:
        if self.application_x != self.application_x:      # NaN
            self.application_x = self.intersection_x
        if self.application_y != self.application_y:
            self.application_y = self.intersection_y

    def couple(self) -> float:
        """Moment of moving the resultant from the cut to where it acts.

        A pure couple: ``(P2 - P1) x F`` does not depend on the axis it is
        taken about, which is why one scalar per analysis is enough and no
        method has to be told where the wall is.
        """
        return ((self.application_x - self.intersection_x) * self.force_v
                - (self.application_y - self.intersection_y) * self.force_h)


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


def _resisting_tangent_angle(
    slip_tangent: float, is_left_to_right_failure: bool,
) -> float:
    """Angle of the slip-surface tangent, in the sense that RESISTS.

    The slip tangent has slope ``slip_tangent``; of its two directions the
    resisting one is the one pointing against the movement. If sliding is
    right to left the resisting tangent points right, which is
    ``atan(slip_tangent)``; the other way round it is that plus pi.

    v0.1.124 -- lifted out of :func:`_support_force_angle` because the
    shear capacity needs the same reference direction to decide which of
    the two perpendiculars to the support opposes the slide. A rule
    written in two places goes stale in one of them.
    """
    if is_left_to_right_failure:
        return math.atan(slip_tangent) + math.pi
    return math.atan(slip_tangent)


def _resisting_perpendicular(
    axis_angle: float, tangent_angle: float,
) -> float:
    """Perpendicular to a support axis, on the side that resists sliding.

    Two perpendiculars exist; the shear a reinforcement mobilises acts
    AGAINST the movement, so take the one whose projection on the
    resisting tangent is positive. Before v0.1.112 the caller returned
    ``axis_angle + pi/2`` unconditionally -- right only for a pile drawn
    head-at-top, and silently pushing the mass downhill for one drawn the
    other way round.
    """
    perp = axis_angle + math.pi / 2
    if math.cos(perp - tangent_angle) < 0.0:
        perp -= math.pi
    return perp


def _support_force_angle(
    support: "SupportInstance",
    slip_tangent: float,
    is_left_to_right_failure: bool = True,
) -> float:
    """Compute the angle at which the support force is applied.

    Returns angle in radians from positive x.

    Two of the five orientations are decided by the SLIDING SENSE and
    three by GEOMETRY, and mixing the two up is what made v0.1.97 hand a
    tensioned bolt a force pointing downhill:

      * ``tangent_to_slip`` and ``horizontal`` are resisting directions
        by construction, so they must consult
        ``is_left_to_right_failure``;
      * ``parallel_to_support`` is the bolt's own axis, HEAD → TAIL. It
        is not oriented to resist anything: a bolt whose anchor sits
        downhill of the slip surface really does push the mass, and the
        angle is an output the user is meant to check.
      * ``perpendicular_to_pile`` is an axis-derived direction with a
        free sign, and there the sliding sense picks WHICH of the two
        perpendiculars — a pile mobilises its shear against the movement.

    ``head`` is the end at the slope FACE and ``tail`` the anchored end.
    That is not a free choice made here: ``SoilNail.force_at`` and
    ``GroutedTieback.force_at`` already measure the stripping length
    ``L_i`` from the head and the pullout length ``L_o`` from the tail,
    so the plate is at the head. A bolt in tension pulls the sliding
    mass TOWARDS its anchor, which is ``axis_angle`` — head → tail. Until
    v0.1.112 this returned ``axis_angle + pi``, anchor → face, i.e. the
    sliding direction, and reinforcement LOWERED the factor of safety
    with ``parallel_to_support`` and with ``bisector`` (the factory
    default of ``SoilNail``). See ``tests/test_support_orientation_v1112.py``.
    """
    from ogr_core.support import ForceOrientation

    o = support.orientation
    axis_angle = support.axis_angle_rad()  # head (face) → tail (anchor)
    tangent_angle = _resisting_tangent_angle(
        slip_tangent, is_left_to_right_failure)

    if o == ForceOrientation.TANGENT_TO_SLIP:
        return tangent_angle
    if o == ForceOrientation.PARALLEL_TO_SUPPORT:
        return axis_angle
    if o == ForceOrientation.BISECTOR:
        # Bisector of tangent and parallel-to-support
        a1 = tangent_angle
        a2 = axis_angle
        # Wrap to nearest equivalent angles
        while a2 - a1 > math.pi:
            a2 -= 2 * math.pi
        while a1 - a2 > math.pi:
            a2 += 2 * math.pi
        return 0.5 * (a1 + a2)
    if o == ForceOrientation.HORIZONTAL:
        return math.pi if is_left_to_right_failure else 0.0
    if o == ForceOrientation.PERPENDICULAR_TO_PILE:
        return _resisting_perpendicular(axis_angle, tangent_angle)
    if o == ForceOrientation.USER_DEFINED:
        return math.radians(support.user_angle_deg)
    return axis_angle


def _bond_profiles(project: "Project") -> dict:
    """Interface shear strength along every support, keyed by support id.

    v0.1.116 — the two stress-dependent pullout laws need σ'_n sampled
    along the reinforcement, and that profile depends ONLY on the project:
    the layers above, the water, the external loads. Not on the trial
    surface. So it is built once per analysis rather than once per
    surface, which is the difference between a few milliseconds and a few
    minutes — 50 column weights per support, times fifteen sheets, times
    the thousands of surfaces a grid search evaluates, times nine methods.

    The cache is trusted inside a ``regions_frozen()`` block and rebuilt
    outside one. That is the same contract the regions cache runs on, and
    it is what makes a stale profile impossible: an analysis cannot modify
    the project it is analysing (design coefficients are applied to a
    COPY, which is a different Project with its own caches), and the entry
    to the freeze clears whatever was there. Outside a freeze the only
    caller is a canvas tooltip, with a handful of supports.
    """
    cached = getattr(project, "_support_bond_cache", None)
    if cached is not None and getattr(project, "_regions_freeze_depth", 0):
        return cached

    from ogr_core.support import build_bond_profile, support_registry as _reg

    registry = _reg()
    type_props = {st.TYPE_ID: st
                  for st in (getattr(project, "support_types", []) or [])}
    profiles: dict = {}
    for support in (getattr(project, "supports", None) or ()):
        stype = type_props.get(support.type_id)
        if stype is None:
            cls = registry.get(support.type_id)
            if cls is None:
                continue
            stype = cls()
        if not getattr(stype, "NEEDS_BOND_PROFILE", False):
            continue
        try:
            profiles[support.id] = build_bond_profile(project, support, stype)
        except Exception:  # noqa: BLE001
            # A profile that cannot be built leaves ``force_at`` to fall
            # back on its zero-stress envelope, which is conservative:
            # never MORE reinforcement than the stress state would give.
            continue
    project._support_bond_cache = profiles
    return profiles


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
    bond_profiles = _bond_profiles(project)
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

        # v0.1.122 -- some profiles are defined from the CREST of the
        # support, not from its head. ``force_at`` never sees the instance,
        # so it cannot tell which end is higher; a wall drawn bottom-to-top
        # would silently invert its pressure diagram and return a plausible,
        # wrong number. Deciding it here, by geometry, is the only place the
        # question can be answered at all.
        d_along = d_from_head
        crest, other = support.head, support.tail
        if getattr(stype, "MEASURED_FROM_TOP", False):
            if support.tail.y > support.head.y:
                d_along = L_total - d_from_head
                crest, other = support.tail, support.head
            elif support.tail.y == support.head.y:
                # No crest to measure from. Refusing beats guessing: the
                # analysis reports it instead of publishing a number that
                # depends on the drawing order.
                continue

        F = stype.force_at(d_along, L_total,
                           bond_profiles.get(support.id))

        # v0.1.124 -- the SHEAR capacity, at last connected to something.
        # Until this version ``shear_at`` and ``SUPPORTS_SHEAR`` were
        # declared by three types, editable, serialised and read by NOBODY
        # outside ``ogr_core/support/support.py``: a configurable control
        # that could not move the number, which is the defect rule 7
        # exists for. The reference says what it does, in words: "the
        # vector perpendicular to the bolt direction, and opposite to the
        # direction of failure, is added to the overall bolt capacity
        # vector [...] the support force at the base of the slice is no
        # longer parallel to the support but angled in a direction
        # opposite to the slip direction". So it is a SECOND vector, not a
        # bigger axial one, and the two are summed here.
        V = 0.0
        if getattr(stype, "SUPPORTS_SHEAR", False):
            try:
                V = max(0.0, float(stype.shear_at(d_along, L_total)))
            except Exception:  # noqa: BLE001 - a plugin must not kill a run
                V = 0.0
        # A support with no axial capacity left but some shear still acts.
        # Before v0.1.124 the guard was ``F <= 0`` alone, which was right
        # only because the shear reached nothing.
        if F <= 0 and V <= 0:
            continue

        # Force orientation angle
        slip_slope = _slip_tangent_at_x(slices, ix) or 0.0
        ang = _support_force_angle(support, slip_slope, is_l2r)
        Fh = F * math.cos(ang)
        Fv = F * math.sin(ang)
        if V > 0.0:
            perp = _resisting_perpendicular(
                support.axis_angle_rad(),
                _resisting_tangent_angle(slip_slope, is_l2r))
            Fh += V * math.cos(perp)
            Fv += V * math.sin(perp)
            # The RESULTANT replaces the axial force from here on, which is
            # what makes the split into T_S and T_N, the Active/Passive
            # flag and the nine methods work unchanged. With ``V = 0`` the
            # arithmetic below is untouched, bit for bit, and that is what
            # protects every model validated before this version.
            F = math.hypot(Fh, Fv)
            ang = math.atan2(Fv, Fh)

        from ogr_core.support import ForceApplication
        is_active = (support.force_application == ForceApplication.ACTIVE)

        # v0.1.122 -- where the resultant acts. Every type but a retaining
        # wall asked for the centroid acts at the cut, and then the two
        # points coincide and the couple below is exactly zero.
        ax, ay = ix, iy
        if (getattr(stype, "force_location", "intersection") == "centroid"
                and hasattr(stype, "resultant_arm") and L_total > 0.0):
            # v0.1.123 -- the profile goes in too. A wall knows its own
            # diagram in closed form, but an Ito-Matsui pile does not: its
            # diagram IS the sampled profile, so the centroid cannot be
            # computed without it.
            arm = stype.resultant_arm(d_along, L_total,
                                      bond_profiles.get(support.id))
            ux = (other.x - crest.x) / L_total
            uy = (other.y - crest.y) / L_total
            ax, ay = crest.x + arm * ux, crest.y + arm * uy

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
            application_x=ax,
            application_y=ay,
        ))

    return effects
