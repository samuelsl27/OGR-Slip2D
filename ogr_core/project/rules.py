# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Model invariants that used to live only in the interface.

v0.1.194 (spec 008) — every rule in this module was, until this version,
enforced by the main window and by nothing else: greying a menu action,
or refusing inside a click handler. ``Project.add_boundary`` accepted a
second water table without a word, and ``ogr_slip2d/slicer.py`` says in so
many words that the engine never checks it either. So a script, the
command line, or an AI agent driving the program could build a model the
interface cannot, and get a number for it.

The rules are MOVED here, not copied: the interface now asks this module
the same question and only keeps its tooltips, which are presentation. A
rule written twice is a rule that will disagree with itself, which is how
the six captions of v0.1.165 (D96) came to say different things.

Nothing here imports Qt or the solver packages. Messages are English, like
every message the engine produces; the interface translates its own.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ..geometry import BoundaryType


@dataclass(frozen=True)
class Refusal:
    """Why an edit or a run is not allowed.

    ``code`` is for a program to branch on and never changes wording;
    ``message`` is for a person or a language model to read. ``cause``
    (v0.1.229) is the refusal of a part, when the whole is refused because
    of it: an interface that translates by code can then say which part and
    why.
    """

    code: str
    message: str
    cause: Optional["Refusal"] = None


#: Boundary types a model may hold at most one of. EXTERNAL is here
#: because the region subdivision reads ``external_boundary()``, which
#: returns the FIRST one and ignores the rest, so a second external would
#: be a boundary that silently does nothing (rule 7).
_SINGLE_INSTANCE = {
    BoundaryType.EXTERNAL: (
        "A model has exactly one External boundary; replace the existing "
        "one instead of adding a second."),
    BoundaryType.WATER_TABLE: (
        "Only one Water Table is allowed; delete or edit the existing one."),
    BoundaryType.TENSION_CRACK: (
        "Only one Tension Crack boundary is allowed; delete the existing one "
        "to add a new one."),
    BoundaryType.DRAWDOWN: (
        "Only one Drawdown Line is allowed; delete or edit the existing one."),
}


def boundary_refusal(project, btype: BoundaryType) -> Optional[Refusal]:
    """Why a new boundary of type ``btype`` cannot be added, or None.

    The same answer the interface gives by greying its drawing actions
    (``MainWindow.refresh_action_availability``). Two kinds of refusal:

    * ``single_instance`` — the model already holds the one it may hold;
    * ``requires_rapid_drawdown`` / ``requires_block_search`` — the
      boundary would be read by nothing under the current settings. A
      drawdown line is only consumed by a rapid-drawdown analysis and a
      Block Search object only by the Block Search, so adding one
      otherwise is a control that moves no number.

    For a drawdown line the settings question is asked FIRST, which is
    the order the interface's tooltip has always reported them in.
    """
    btype = BoundaryType(btype) if not isinstance(btype, BoundaryType) \
        else btype
    settings = project.settings
    if btype == BoundaryType.DRAWDOWN and not getattr(
            settings.groundwater, "rapid_drawdown", False):
        return Refusal(
            "requires_rapid_drawdown",
            "A Drawdown Line is only read by a rapid drawdown analysis; "
            "enable it first (groundwater advanced option "
            "'rapid_drawdown').")
    if btype == BoundaryType.BLOCK_SEARCH_OBJECT and (
            settings.search.search_method != "block"):
        return Refusal(
            "requires_block_search",
            "A Block Search object is only read by the Block Search; set "
            "search.surface_type='non_circular' and "
            "search.search_method='block' first.")
    message = _SINGLE_INSTANCE.get(btype)
    if message is not None and any(b.btype == btype
                                   for b in project.boundaries):
        return Refusal("single_instance", message)
    return None


# ----------------------------------------------------------------------
def block_object_refusal(boundary) -> Optional[Refusal]:
    """Why this Block Search object cannot be searched as it is, or None.

    v0.1.232 (D109). The kind stored on the object — or inferred, for one
    saved before — has to be one its geometry can be:

    * a Point is one vertex, a Line is one segment given by two points,
      and a Window is a closed polygon (four-sided in the reference; OGR
      takes any of three or more vertices, which contains it);
    * a Polyline is open, has two or more vertices, and ADVANCES in x from
      one end to the other. The trial surface follows it between its two
      points and is assembled by sorting every vertex by x, so a polyline
      that doubles back would give a surface that reverses direction —
      not kinematically admissible, which is what the reference's own
      sorting is there to prevent;
    * the «Left / Right Line Segment» option draws its point on the end
      segment of that side, which «assumes that the polyline consists of at
      least two line segments». On a single segment it is refused instead
      of quietly meaning «anywhere».
    """
    from ..geometry.block_object import (BlockObjectKind, PolylinePointMode,
                                         block_spec_of, left_to_right)

    poly = boundary.polyline
    verts = poly.vertices
    n = len(verts)
    spec = block_spec_of(boundary)
    if spec is None:
        return Refusal("block_object_empty",
                       "A Block Search object needs at least one vertex.")
    kind = spec.kind
    if kind is BlockObjectKind.POINT and n != 1:
        return Refusal(
            "block_object_geometry",
            f"A Block Search Point is a single point; this one has {n} "
            f"vertices.")
    if kind is BlockObjectKind.LINE and n != 2:
        return Refusal(
            "block_object_geometry",
            f"A Block Search Line is one segment given by two points; this "
            f"one has {n} vertices. A path of several segments that the "
            f"surface should follow is a Block Search Polyline.")
    if kind is BlockObjectKind.WINDOW and not (poly.closed and n >= 3):
        return Refusal(
            "block_object_geometry",
            "A Block Search Window is a closed polygon of at least three "
            "vertices.")
    if kind is BlockObjectKind.POLYLINE:
        if poly.closed or n < 2:
            return Refusal(
                "block_object_geometry",
                "A Block Search Polyline is an open line of at least two "
                "vertices.")
        pts = left_to_right(verts)
        if any(b.x <= a.x for a, b in zip(pts, pts[1:])):
            return Refusal(
                "block_polyline_not_monotone",
                "A Block Search Polyline has to advance in x from one end to "
                "the other: the trial surface follows it between its two "
                "points, and a polyline that doubles back (or has a vertical "
                "segment) would give a surface that reverses direction.")
        if n < 3 and PolylinePointMode.SEGMENT in (spec.left_point,
                                                   spec.right_point):
            return Refusal(
                "block_polyline_segment_mode",
                "The Left / Right Line Segment option places its point on "
                "the end segment of that side, which needs a polyline of at "
                "least two segments; this one has one. Use Any Line Segment "
                "or End Point.")
    return None


def block_objects_refusal(project) -> Optional[Refusal]:
    """Why the Block Search objects of ``project`` cannot be searched, or None.

    v0.1.232 (D109). Each object on its own (:func:`block_object_refusal`),
    then the one rule between them: no other object may overlap the lateral
    extent of a Block Search Polyline. The reference does not allow it
    «because this is likely to create kinematically inadmissible slip
    surfaces»; in OGR it is also what keeps the polyline's stretch whole,
    since a trial surface is assembled by sorting the vertices of all its
    objects by x and a vertex from another object inside that range would
    cut the stretch in two. Objects that merely touch at an end are allowed.

    The tolerance of «merely touch» is relative to the size of the objects'
    coordinates, not absolute: the same number would mean different things
    in millimetres and in metres.

    v0.1.233 (D99) — the rule holds WITHIN a group. With Multiple Groups on
    (``SearchSettings.block_multiple_groups``) each Group ID is searched on
    its own and its surfaces are assembled from its own objects only, so a
    polyline in one group cannot be cut by an object of another. That is
    exactly what the reference uses groups for: one polyline per weak layer,
    overlapping in x, each with its id.
    """
    from ..geometry.block_object import (BlockObjectKind, block_group_of,
                                         block_spec_of)

    objects = [b for b in project.boundaries
               if b.btype == BoundaryType.BLOCK_SEARCH_OBJECT]
    for i, b in enumerate(objects):
        why = block_object_refusal(b)
        if why is not None:
            return Refusal(why.code, f"{_block_label(b, i)}: {why.message}",
                           cause=why)
    grouped = bool(getattr(project.settings.search, "block_multiple_groups",
                           False))
    spans = []
    for i, b in enumerate(objects):
        xs = [v.x for v in b.polyline.vertices]
        spans.append((i, b, min(xs), max(xs), block_spec_of(b).kind,
                      block_group_of(b) if grouped else 0))
    scale = max([1.0] + [abs(x) for _i, _b, lo, hi, _k, _g in spans
                         for x in (lo, hi)])
    tol = 1e-9 * scale
    for i, p, p_lo, p_hi, kind, g_p in spans:
        if kind is not BlockObjectKind.POLYLINE:
            continue
        for j, q, q_lo, q_hi, _kind, g_q in spans:
            if j == i or g_q != g_p:
                continue
            if q_hi > p_lo + tol and q_lo < p_hi - tol:
                where = (f" (both in Group ID {g_p})" if grouped else "")
                way_out = (" Give them different Group IDs to search them "
                           "separately." if grouped else
                           " To search them separately, turn Multiple Groups "
                           "on and give them different Group IDs.")
                return Refusal(
                    "block_polyline_overlap",
                    f"{_block_label(q, j)} overlaps the lateral extent of "
                    f"the Block Search Polyline {_block_label(p, i)} (x from "
                    f"{p_lo:g} to {p_hi:g}){where}. This is not allowed: the "
                    f"trial surface follows the polyline between its two "
                    f"points, and a vertex of another object inside that "
                    f"range would cut the stretch.{way_out}")
    return None


def _block_label(boundary, index: int) -> str:
    """A Block Search object named in a refusal: its name and its position
    among the model's Block Search objects, since every object drawn in
    the interface is called the same."""
    return f"{boundary.name or boundary.btype.display_name} #{index + 1}"


# ----------------------------------------------------------------------
def assign_water_surface(project, surface_id, picked: Iterable[str],
                         cleared: Iterable[str] = ()) -> None:
    """Point materials at a water surface, and set their pore-pressure model.

    Moved here from ``MainWindow.apply_water_surface_assignment`` in
    v0.1.194; the history below is that method's, kept with the code it
    explains.

    v0.1.97 — IT ALSO SETS ``Material.pore_pressure``, and that is the
    whole reason this function exists. Until then the assignment wrote
    ``water_surface_id`` alone, while ``pore_pressure_at`` returns 0.0
    out of ``if ppt == PorePressureType.NONE`` BEFORE it ever reads that
    field. So ticking a material moved nothing: measured on the Ej_2
    piezometric model, u at (0, 10) stayed at 0.000 kPa with the id
    written, and became 196.200 kPa once the model was set too. A control
    that does not change the number is worse than no control, because the
    user believes the analysis respects it.

    Clearing restores ``NONE``, but only for a material that was actually
    using a water surface: one on Ru, a constant or a finite-element field
    is left alone, since its pore-pressure model was never this
    assignment's to set.
    """
    from ..materials import PorePressureType

    surface = next((b for b in project.boundaries if b.id == surface_id),
                   None)
    model = (PorePressureType.WATER_TABLE
             if surface is not None
             and surface.btype == BoundaryType.WATER_TABLE
             else PorePressureType.PIEZO_LINE)
    picked, cleared = set(picked), set(cleared)
    surface_models = (PorePressureType.WATER_TABLE,
                      PorePressureType.PIEZO_LINE)
    for m in project.materials:
        if m.id in picked:
            m.water_surface_id = surface_id
            m.pore_pressure = model
        elif m.id in cleared:
            m.water_surface_id = None
            if m.pore_pressure in surface_models:
                m.pore_pressure = PorePressureType.NONE
    project._notify("materials_changed")


def water_surface_model(project, surface_id):
    """The pore-pressure model a material pointed at ``surface_id`` gets.

    The same choice :func:`assign_water_surface` makes, exposed so a caller
    that sets the two fields itself cannot pick the other one.
    """
    from ..materials import PorePressureType

    surface = next((b for b in project.boundaries if b.id == surface_id),
                   None)
    if surface is not None and surface.btype == BoundaryType.WATER_TABLE:
        return PorePressureType.WATER_TABLE
    return PorePressureType.PIEZO_LINE


# ----------------------------------------------------------------------
def compute_blockers(project) -> list[Refusal]:
    """The model-level reasons a run cannot start, in the order checked.

    Moved from ``MainWindow.act_compute`` in v0.1.194. These are the two
    checks that are about the MODEL being empty; the checks about the
    SETTINGS live in ``ogr_slip2d.analysis_runner.check_analysis_settings``,
    which this package cannot import. The interface asks the first one
    before the settings and the second one after them, and keeps doing so:
    the codes exist so it can.

    ``no_boundaries`` asks for ANY boundary, exactly as the interface
    always has, not for an External one. A model with boundaries but no
    External reaches the search and finds nothing; whether that should be
    refused up front is a separate decision, reported and not taken here.
    """
    out: list[Refusal] = []
    if not project.boundaries:
        out.append(Refusal(
            "no_boundaries",
            "No model to compute. Add an external boundary first."))
    if not project.materials:
        out.append(Refusal("no_materials", "No materials defined."))
    return out


# ----------------------------------------------------------------------
def anisotropic_function_rows_refusal(rows) -> Optional[Refusal]:
    """Why ``rows`` cannot be the table of an Anisotropic Strength Function,
    or None.

    v0.1.218 (D209) — the table is a list of angular RANGES of slice base
    inclination, ``(angle to, c, phi)``, as the reference documents the
    strength type: ordered counter-clockwise from -90 to +90, the first
    range starting at -90 (so the first "angle to" lies above it) and the
    last ending at +90, which has to be entered. Each row is a range, so
    the angles must strictly increase; c is a cohesion and phi a friction
    angle, so c ≥ 0 and 0 ≤ phi < 90.

    The model computes with whatever it is given; this is the one place
    that says what it may be given, asked by the material dialog, the API
    and the analysis (``strength_model_refusal``).
    """
    import math

    try:
        rows = [tuple(r) for r in rows]
    except TypeError:
        return Refusal("anisotropic_table_not_rows",
                       "The table must be a list of (angle to, c, phi) "
                       "rows.")
    if not rows:
        return Refusal("anisotropic_table_empty",
                       "The table has no rows: at least one range, ending "
                       "at +90 degrees, is needed.")
    angles = []
    for i, row in enumerate(rows, start=1):
        try:
            a, c, phi = (float(v) for v in row)
        except (TypeError, ValueError):
            return Refusal("anisotropic_table_not_rows",
                           f"Row {i} is not three numbers (angle to, c, "
                           f"phi): {row!r}.")
        if not all(math.isfinite(v) for v in (a, c, phi)):
            return Refusal("anisotropic_table_not_rows",
                           f"Row {i} holds a value that is not finite.")
        if c < 0.0 or not 0.0 <= phi < 90.0:
            return Refusal("anisotropic_table_strength",
                           f"Row {i}: the cohesion must be ≥ 0 and the "
                           f"friction angle in [0, 90), got c = {c:g}, "
                           f"phi = {phi:g}.")
        angles.append(a)
    if angles[0] <= -90.0:
        return Refusal("anisotropic_table_start",
                       f"The first range starts at -90 degrees, so its "
                       f"'angle to' must be above -90; got {angles[0]:g}.")
    for i in range(1, len(angles)):
        if not angles[i] > angles[i - 1]:
            return Refusal("anisotropic_table_order",
                           f"The ranges must be ordered counter-clockwise: "
                           f"row {i + 1} ends at {angles[i]:g} degrees, not "
                           f"after row {i} ({angles[i - 1]:g}).")
    if abs(angles[-1] - 90.0) > 1e-9:
        return Refusal("anisotropic_table_end",
                       f"The last range must end at +90 degrees; it ends "
                       f"at {angles[-1]:g}.")
    return None


def function_points_refusal(points) -> Optional[Refusal]:
    """Why ``points`` cannot be the table of a shear-normal or discrete
    strength function, or None.

    v0.1.227 (D217) — the table is τ as a function of σ'ₙ: at least one
    point, every value a finite number, τ ≥ 0, and σ'ₙ strictly increasing
    (a repeated σ'ₙ is two strengths for one stress). Until this version an
    EMPTY table was accepted by the API and answered τ = 0 at every base,
    and a row the dialog could not read was dropped without a word.
    """
    import math

    try:
        pts = [tuple(p) for p in (points or [])]
    except TypeError:
        return Refusal("function_points_not_points",
                       "The table must be a list of (normal stress, shear "
                       "strength) points.")
    if not pts:
        return Refusal("function_points_empty",
                       "The table has no points: at least one (normal "
                       "stress, shear strength) point is needed.")
    sigmas = []
    for i, p in enumerate(pts, start=1):
        try:
            s, tau = (float(v) for v in p)
        except (TypeError, ValueError):
            return Refusal("function_points_not_points",
                           f"Point {i} is not two numbers (normal stress, "
                           f"shear strength): {p!r}.")
        if not (math.isfinite(s) and math.isfinite(tau)):
            return Refusal("function_points_not_points",
                           f"Point {i} holds a value that is not finite.")
        if tau < 0.0:
            return Refusal("function_points_strength",
                           f"Point {i}: the shear strength must be zero or "
                           f"more, got {tau:g}.")
        sigmas.append(s)
    for i in range(1, len(sigmas)):
        if not sigmas[i] > sigmas[i - 1]:
            return Refusal("function_points_order",
                           f"The normal stresses must increase strictly: "
                           f"point {i + 1} ({sigmas[i]:g}) does not exceed "
                           f"point {i} ({sigmas[i - 1]:g}).")
    return None


def c_phi_rows_refusal(rows) -> Optional[Refusal]:
    """Why ``rows`` cannot be the table of a C/Phi function, or None.

    v0.1.229 (D215) — ``(σ'ₙ, c, φ)`` rows: at least one, every value a
    finite number, σ'ₙ strictly increasing (a repeated σ'ₙ is two strengths
    for one stress), c ≥ 0 and 0 ≤ φ < 90, as in every Mohr-Coulomb table of
    the program.
    """
    import math

    try:
        rows = [tuple(r) for r in (rows or [])]
    except TypeError:
        return Refusal("c_phi_rows_not_rows",
                       "The table must be a list of (normal stress, cohesion, "
                       "friction angle) rows.")
    if not rows:
        return Refusal("c_phi_rows_empty",
                       "The table has no rows: at least one (normal stress, "
                       "cohesion, friction angle) row is needed.")
    sigmas = []
    for i, row in enumerate(rows, start=1):
        try:
            s, c, phi = (float(v) for v in row)
        except (TypeError, ValueError):
            return Refusal("c_phi_rows_not_rows",
                           f"Row {i} is not three numbers (normal stress, "
                           f"cohesion, friction angle): {row!r}.")
        if not all(math.isfinite(v) for v in (s, c, phi)):
            return Refusal("c_phi_rows_not_rows",
                           f"Row {i} holds a value that is not finite.")
        if c < 0.0 or not 0.0 <= phi < 90.0:
            return Refusal("c_phi_rows_strength",
                           f"Row {i}: the cohesion must be ≥ 0 and the "
                           f"friction angle in [0, 90), got c = {c:g}, "
                           f"phi = {phi:g}.")
        sigmas.append(s)
    for i in range(1, len(sigmas)):
        if not sigmas[i] > sigmas[i - 1]:
            return Refusal("c_phi_rows_order",
                           f"The normal stresses must increase strictly: row "
                           f"{i + 1} ({sigmas[i]:g}) does not exceed row {i} "
                           f"({sigmas[i - 1]:g}).")
    return None


def snowden_refusal(strength) -> Optional[Refusal]:
    """Why a Snowden Modified Anisotropic Linear model cannot be computed
    with, or None.

    v0.1.229 (D215) — its A1, B1, A2 and B2 are angles from the bedding on
    each side of it, the band of bedding strength and the end of the
    transition, within the (-90, 90] of the reference documentation's
    anisotropy function: 0 ≤ A ≤ B ≤ 90 on each side (A = B is a step,
    which the model computes). Its bedding and rock mass strengths are each
    a shear-normal or a C/Phi function, with a valid table; a refusal of
    one of them is the ``cause`` of the refusal returned.
    """
    import math

    from ..materials.builtin_models import CPhiFunction, ShearNormalFunction

    p = strength.params
    for side in ("1", "2"):
        a = float(p.get("A" + side, 0.0))
        b = float(p.get("B" + side, 0.0))
        if not (math.isfinite(a) and math.isfinite(b)) or \
                not 0.0 <= a <= b <= 90.0:
            return Refusal("snowden_ab",
                           f"A{side} and B{side} must satisfy 0 <= A{side} "
                           f"<= B{side} <= 90 degrees; got A{side} = {a:g}, "
                           f"B{side} = {b:g}.")
    for which in ("bedding", "rock_mass"):
        label = which.replace("_", " ")
        try:
            fn = strength.function(which)
        except ValueError as exc:
            return Refusal("snowden_" + which,
                           f"The {label} strength function: {exc}.",
                           cause=Refusal("snowden_function_type", str(exc)))
        if isinstance(fn, ShearNormalFunction):
            why = function_points_refusal(fn.points)
        elif isinstance(fn, CPhiFunction):
            why = c_phi_rows_refusal(fn.rows)
        else:                                  # guarded by ``function``
            why = Refusal("snowden_function_type",
                          f"{fn.DISPLAY_NAME} is not a shear-normal or a "
                          f"C/Phi function.")
        if why is not None:
            return Refusal("snowden_" + which,
                           f"The {label} strength function: {why.message}",
                           cause=why)
    return None


def generalized_anisotropic_rules_refusal(rules) -> Optional[Refusal]:
    """Why ``rules`` cannot be the rules of a Generalized Anisotropic
    model, or None.

    v0.1.225 (D218) — the model used to answer a strength of ZERO, in
    silence, for an angle no rule held and for a rule whose model could not
    be built. The rules are the reference's "Angle Range" input: ranges of
    slice base inclination "ordered counter-clockwise, from −90 to +90",
    each "Angle From" being the previous "Angle To" and the last one
    ending at +90. So the first rule starts at −90, each one starts where
    the previous one ends, and the last one ends at +90: a gap is an angle
    with no strength and an overlap a rule that can never be reached (the
    first one that holds an angle wins). Every model must be present and
    buildable. Its own refusals are asked by :func:`strength_model_refusal`
    AFTER this one, so the structure is judged first.
    """
    import math

    from ..materials.strength_model import StrengthModel

    try:
        rules = list(rules or [])
    except TypeError:
        return Refusal("generalized_rules_not_rules",
                       "The rules must be a list of {angle_min, angle_max, "
                       "model} objects.")
    if not rules:
        return Refusal("generalized_rules_empty",
                       "There are no rules: at least one range, from -90 to "
                       "+90 degrees, with its strength model, is needed.")
    bounds = []
    for i, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            return Refusal("generalized_rules_not_rules",
                           f"Rule {i} is not an {{angle_min, angle_max, "
                           f"model}} object: {rule!r}.")
        try:
            amin = float(rule.get("angle_min", -90.0))
            amax = float(rule.get("angle_max", 90.0))
        except (TypeError, ValueError):
            return Refusal("generalized_rules_not_rules",
                           f"The angles of rule {i} are not numbers.")
        if not (math.isfinite(amin) and math.isfinite(amax)) or not (
                -90.0 - 1e-9 <= amin < amax <= 90.0 + 1e-9):
            return Refusal("generalized_rules_angles",
                           f"Rule {i} must go from a lower to a higher angle "
                           f"within [-90, 90] degrees; it goes from {amin:g} "
                           f"to {amax:g}.")
        bounds.append((amin, amax))
    if abs(bounds[0][0] + 90.0) > 1e-9:
        return Refusal("generalized_rules_start",
                       f"The first range starts at -90 degrees; it starts at "
                       f"{bounds[0][0]:g}.")
    for i in range(1, len(bounds)):
        if abs(bounds[i][0] - bounds[i - 1][1]) > 1e-9:
            kind = ("leaves the angles between {a:g} and {b:g} degrees "
                    "with no strength" if bounds[i][0] > bounds[i - 1][1]
                    else "overlaps it, so part of a range can never be "
                         "reached")
            return Refusal("generalized_rules_order",
                           f"Rule {i + 1} must start where rule {i} ends "
                           f"({bounds[i - 1][1]:g} degrees); it starts at "
                           f"{bounds[i][0]:g}, which "
                           + kind.format(a=bounds[i - 1][1], b=bounds[i][0])
                           + ".")
    if abs(bounds[-1][1] - 90.0) > 1e-9:
        return Refusal("generalized_rules_end",
                       f"The last range must end at +90 degrees; it ends at "
                       f"{bounds[-1][1]:g}.")
    for i, rule in enumerate(rules, start=1):
        data = rule.get("model")
        if not data:
            return Refusal("generalized_rules_model",
                           f"Rule {i} has no strength model.")
        try:
            StrengthModel.from_dict(data)
        except Exception as exc:  # noqa: BLE001 - the message says which
            return Refusal("generalized_rules_model",
                           f"The strength model of rule {i} cannot be built: "
                           f"{type(exc).__name__}: {exc}")
    return None


def anisotropic_linear_refusal(strength) -> Optional[Refusal]:
    """Why an Anisotropic Linear model's A and B cannot be used, or None.

    v0.1.225 (D216) — A is "an angular range on either side of the bedding
    plane orientation" and B − A "the angular range over which the increase
    from bedding plane to rock mass shear strength takes place" (the
    reference documentation), so 0 ≤ A ≤ B. A = B is a step, which the
    model computes.
    """
    import math

    a = float(strength.params.get("A", 0.0))
    b = float(strength.params.get("B", 0.0))
    if not (math.isfinite(a) and math.isfinite(b)) or not 0.0 <= a <= b:
        return Refusal("anisotropic_linear_ab",
                       f"A and B must satisfy 0 <= A <= B degrees; got "
                       f"A = {a:g}, B = {b:g}.")
    return None


def strength_model_refusal(strength, name: Optional[str] = None
                           ) -> Optional[Refusal]:
    """Why a material's strength model cannot be computed with, or None.

    v0.1.218 (D209) — the Anisotropic Strength Function: a table saved as
    interpolated points by a version before 0.1.218 (``legacy_points``), or
    rows that are not a valid set of ranges. v0.1.225 — Generalized
    Anisotropic rules that are not the reference's contiguous ranges or
    hold a model that cannot be built (D218), and the A and B of Anisotropic
    Linear (D216). v0.1.227 — the τ–σ'ₙ tables of the shear-normal and
    discrete functions (D217). v0.1.229 — the C/Phi function's table, and
    Snowden: a material saved before 0.1.229, its A and B, and its two
    strength functions (D215). A Generalized Anisotropic model is then
    asked about the models of its rules, since one of them can be such a
    table. ``name`` is the material's, for the message.
    """
    from ..materials.builtin_models import (ANISOTROPIC_FUNCTION_LEGACY_NOTE,
                                            SNOWDEN_LEGACY_NOTE,
                                            AnisotropicLinear,
                                            AnisotropicStrengthFunction,
                                            CPhiFunction,
                                            DiscreteFunction,
                                            GeneralizedAnisotropic,
                                            ShearNormalFunction,
                                            SnowdenModifiedAnisotropicLinear)
    from ..materials.strength_model import StrengthModel

    label = name if name is not None else "?"
    if isinstance(strength, (ShearNormalFunction, DiscreteFunction)):
        # v0.1.227 (D217).
        why = function_points_refusal(strength.points)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, "
                                 f"{strength.DISPLAY_NAME}: {why.message}")
    if isinstance(strength, CPhiFunction):
        why = c_phi_rows_refusal(strength.rows)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, C/Phi Function: "
                                 f"{why.message}")
    if isinstance(strength, SnowdenModifiedAnisotropicLinear):
        if strength.legacy_params is not None:
            return Refusal("snowden_legacy",
                           SNOWDEN_LEGACY_NOTE.format(name=label))
        why = snowden_refusal(strength)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, Snowden Modified "
                                 f"Anisotropic Linear: {why.message}",
                       cause=why.cause)
    if isinstance(strength, AnisotropicStrengthFunction):
        if strength.legacy_points is not None:
            return Refusal("anisotropic_table_legacy",
                           ANISOTROPIC_FUNCTION_LEGACY_NOTE.format(
                               name=label))
        why = anisotropic_function_rows_refusal(strength.rows)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, Anisotropic Strength "
                                 f"Function: {why.message}")
    if isinstance(strength, AnisotropicLinear):
        why = anisotropic_linear_refusal(strength)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, Anisotropic Linear: "
                                 f"{why.message}")
    if isinstance(strength, GeneralizedAnisotropic):
        why = generalized_anisotropic_rules_refusal(strength.rules)
        if why is not None:
            return Refusal(why.code, f"Material {label!r}, Generalized "
                                     f"Anisotropic: {why.message}")
        for rule in strength.rules:
            why = strength_model_refusal(
                StrengthModel.from_dict(rule["model"]), name)
            if why is not None:
                return why
    return None


def generalized_links_refusal(material, materials) -> Optional[Refusal]:
    """Why a Generalized Anisotropic material's LINKED rules cannot be
    computed with, or None.

    v0.1.228 (D218b) — a rule may name the material whose strength it takes
    (``material_id``), as the reference's "Angle Range" input assigns a
    material to each range. The link must name a material of the project,
    not the Generalized material itself and not another Generalized one: a
    range takes a plain strength, which also rules out cycles.
    """
    from ..materials.builtin_models import GeneralizedAnisotropic

    strength = getattr(material, "strength", None)
    if not isinstance(strength, GeneralizedAnisotropic):
        return None
    by_id = {m.id: m for m in materials}
    label = getattr(material, "name", "?")
    for i, rule in enumerate(strength.rules or [], start=1):
        link = rule.get("material_id") if isinstance(rule, dict) else None
        if not link:
            continue
        src = by_id.get(link)
        if src is None:
            return Refusal("generalized_link_missing",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"rule {i} links a material that is not in the "
                           f"project.")
        if src is material:
            return Refusal("generalized_link_self",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"rule {i} links the material itself.")
        if isinstance(getattr(src, "strength", None),
                      GeneralizedAnisotropic):
            return Refusal("generalized_link_generalized",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"rule {i} links {src.name!r}, another "
                           f"Generalized Anisotropic material; a range takes "
                           f"a plain strength model.")
    return None


#: v0.1.225 (D218) — the strength models that read an anisotropic surface,
#: moved here from the material dialog so that the API asks the same
#: question. The reference lists three (Anisotropic Linear, Snowden Modified
#: Anisotropic Linear and Generalized Anisotropic), but in Generalized
#: Anisotropic a surface belongs to the "Angle or Surface" input, one per
#: joint, which OGR does not implement; its "Angle Range" input, the one
#: OGR has, reads absolute slice base inclinations and no surface.
SURFACE_READING_MODEL_IDS = frozenset({
    "anisotropic_linear",
    "snowden_anisotropic_linear",
})


def reads_anisotropic_surface(strength_or_id) -> bool:
    """Whether a strength model (or model id) reads an anisotropic surface.

    A link from a material whose model does not read one would be a
    setting that decides nothing (rule 7)."""
    mid = (strength_or_id if isinstance(strength_or_id, str)
           else getattr(strength_or_id, "MODEL_ID", None))
    return mid in SURFACE_READING_MODEL_IDS


def material_surface_refusal(material) -> Optional[Refusal]:
    """Why a material's anisotropic-surface link cannot be computed with,
    or None.

    v0.1.225 (D218) — a Generalized Anisotropic material that links one:
    until this version the model subtracted the surface's bedding from the
    base angle, so its ranges would now select other rules. It is refused
    until reviewed, the treatment D209 gave a table whose meaning changed;
    the material dialog removes the link when it stores the material. A
    link from any other model that does not read it was inert before and
    stays inert.
    """
    from ..materials.builtin_models import (GENERALIZED_SURFACE_NOTE,
                                            GeneralizedAnisotropic)

    if getattr(material, "anisotropic_surface_id", None) and isinstance(
            getattr(material, "strength", None), GeneralizedAnisotropic):
        return Refusal("generalized_surface_legacy",
                       GENERALIZED_SURFACE_NOTE.format(
                           name=getattr(material, "name", "?")))
    return None


# ----------------------------------------------------------------------
#: A pseudo-static coefficient is a fraction of g, and the vertical one
#: cancels gravity at the end of its range: with ``kv`` positive DOWN the
#: soil carries ``W·(1 + kv)`` (v0.1.214, D170), so ``kv = −1`` leaves a mass
#: with no weight and every method's driving sum identically zero. Strictly
#: inside, for both coefficients.
SEISMIC_COEFFICIENT_LIMIT = 1.0


def seismic_coefficient_refusal(name: str, value) -> Optional[Refusal]:
    """Why ``value`` cannot be the seismic coefficient ``name``, or None.

    v0.1.214 — moved here from ``ogr_api.ops.loads.seismic_set``, the only
    place that enforced it: the seismic dialog accepted ±1 exactly, and
    with the downward-positive convention of D170 ``kv = −1`` is the
    weightless case. The API and the dialog now ask this function.

    v0.1.219 (D206) — ``kh`` may not be negative. It is the MAGNITUDE of the
    horizontal inertial force, which every method applies in the sliding
    sense of its own surface, out of the slope: the reference documents the
    horizontal coefficient as "always POSITIVE", Eurocode 8 gives it as
    ``0.5·α·S`` against ``F_V = ±0.5·F_H`` for the vertical one, and the
    pseudo-static check is the unfavourable direction (Kramer 1996, §10.6.1;
    Duncan, Wright & Brandon 2014, §10.1). The sign therefore chooses no
    direction, and a negative value can only be a force into the slope,
    which no pseudo-static check uses, or a sign typed to mean "to the
    left", which would raise the factor of safety without a word. ``kv``
    keeps both signs: up and down are both real cases.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return Refusal("seismic_coefficient_not_a_number",
                       f"{name} must be a number, got {value!r}.")
    if not abs(v) < SEISMIC_COEFFICIENT_LIMIT:
        return Refusal("seismic_coefficient_out_of_range",
                       f"|{name}| must be below 1 (a fraction of g), "
                       f"got {v}.")
    if name == "kh" and v < 0.0:
        return Refusal("seismic_kh_negative",
                       f"kh must not be negative, got {v}. It is the "
                       f"magnitude of the horizontal seismic force, which "
                       f"always acts in the sliding direction of each "
                       f"surface, out of the slope; its sign does not "
                       f"choose a direction.")
    return None


# ----------------------------------------------------------------------
#: The bound both permanent-action factors meet: the unfavourable one is at
#: least 1 and the favourable one at most 1 (EN 1990:2002, Table A1.2 (A)
#: to (C); EN 1997-1:2004, Tables A.1, A.3, A.15 and A.17: 1.1/0.9,
#: 1.35/1.0, 1.0/1.0, 1.0/0.9 and 1.35/0.9, never the other way round).
PERMANENT_ACTION_FACTOR_BOUND = 1.0


def design_action_factors_refusal(design_standard) -> Optional[Refusal]:
    """Why the permanent-action factors of a design standard cannot be
    applied, or None.

    v0.1.242 (D226a), when the slicer started applying them. The weight of a
    slice whose base drives the sliding takes the unfavourable factor γG,
    that of one whose base resists it the favourable γG,fav, and which is
    which is decided on the UNFACTORED slices (``ogr_slip2d.design_actions``).
    With γG ≥ 1 ≥ γG,fav the factored mass slides the same way: with s that
    sense, s·Σ ξ·W·sin α = Σ_drive γG·W·|sin α| − Σ_resist γG,fav·W·|sin α|
    is at least s·Σ W·sin α > 0, so no slice changes side by being factored.
    The bound is also what the two words mean: a factor below 1 on an
    unfavourable action, or above 1 on a favourable one, makes the design
    less safe than the characteristic model. A factor of 0 or less would
    remove the weight of the slices that resist, or turn it upward, and a
    value that is not a finite number would reach every slice as one.

    Checked whatever ``single_source_weight`` says: a value that is wrong is
    wrong before the option that would use it is switched on.
    """
    import math

    names = (("factor_permanent", "permanent actions, unfavourable"),
             ("factor_permanent_favourable", "permanent actions, favourable"))
    values = {}
    for attr, label in names:
        raw = getattr(design_standard, attr, 1.0)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            v = math.nan
        if not math.isfinite(v):
            return Refusal("design_action_factor_not_a_number",
                           f"The partial factor on {label} must be a finite "
                           f"number, got {raw!r}.")
        values[attr] = v
    unfav = values["factor_permanent"]
    fav = values["factor_permanent_favourable"]
    if unfav < PERMANENT_ACTION_FACTOR_BOUND:
        return Refusal(
            "design_action_factor_unfavourable_below_one",
            f"The partial factor on unfavourable permanent actions must be "
            f"at least 1, got {unfav}: below 1 it would make the driving "
            f"weight lighter than the characteristic one.")
    if fav > PERMANENT_ACTION_FACTOR_BOUND:
        return Refusal(
            "design_action_factor_favourable_above_one",
            f"The partial factor on favourable permanent actions must be at "
            f"most 1, got {fav}: above 1 it would make the resisting weight "
            f"heavier than the characteristic one.")
    if not fav > 0.0:
        return Refusal(
            "design_action_factor_favourable_not_positive",
            f"The partial factor on favourable permanent actions must be "
            f"above 0, got {fav}: a permanent action keeps its sign, and "
            f"at 0 the slices that resist would have no weight.")
    return None


# ----------------------------------------------------------------------
def set_seismic_records(project, records) -> bool:
    """Replace the project's strong-motion records.

    Moved from ``SeismicRecordsDialog.apply`` in v0.1.196 (spec 008, F2).
    A record the Newmark settings had selected and that is no longer in the
    list leaves the selection EMPTY rather than pointing at nothing: the run
    then says it has no record instead of integrating one that was deleted.
    Returns whether the selection had to be cleared.
    """
    project.seismic_records = list(records)
    settings = getattr(project.settings, "seismic", None)
    if settings is not None and settings.record_id:
        alive = {r.id for r in project.seismic_records}
        if settings.record_id not in alive:
            settings.record_id = ""
            return True
    return False


# ----------------------------------------------------------------------
# v0.1.200 (spec 008, F3a) — the finite-element mesh and what hangs on it
# ----------------------------------------------------------------------
def grid_refusal(project) -> Optional[str]:
    """Why the Water Pressure Grid would not be read, or None.

    v0.1.202 — the reference enables the grid only with one of the three
    grid groundwater methods, which is also where its type lives.
    """
    from ogr_core.hydraulic.water_pressure_grid import value_type_for_method

    if value_type_for_method(project.settings.groundwater.method) is None:
        return ("The Water Pressure Grid is read only with a grid "
                "groundwater method (Project Settings > Groundwater > "
                "Method), which also says what its values are.")
    return None


def set_fem_mesh(project, mesh) -> list[str]:
    """Install ``mesh`` and drop what belonged to the previous one; returns
    what was dropped, in words.

    Boundary conditions are keyed by NODE ID, so they cannot survive a new
    mesh, and a seepage field or a transient history computed on another
    mesh is not a field of this one. Moved from the interface
    (``MainWindow._generate_fem_mesh``), where this rule lived.

    v0.1.200 — the rule covered the current conditions but not the
    conditions of each TRANSIENT STAGE nor the initial ones, which are
    keyed by node id just the same. Measured on the demo slope: a stage
    reservoir on the left face (8 total-head nodes at x = 0), after
    remeshing 300 -> 600 elements, stood on 8 nodes of the CREST (y = 25),
    and the transient would have run with it in silence. The stages keep
    their times, labels and flags; without conditions of their own they
    use the current ones, as a stage always has.
    """
    dropped = []
    gw = project.settings.groundwater
    for what, present in (
            ("boundary conditions", project.seepage_bcs is not None),
            ("seepage field", project.seepage_result is not None),
            ("transient results", bool(project.transient_results)),
            ("initial conditions of the transient",
             gw.transient_initial_bcs is not None),
            ("conditions of the transient stages",
             any(st.get("bcs") for st in gw.transient_stages))):
        if present:
            dropped.append(what)
    project.fem_mesh = mesh
    project.seepage_bcs = None
    project.seepage_result = None
    project.transient_results = []
    gw.transient_initial_bcs = None
    for st in gw.transient_stages:
        st.pop("bcs", None)
    project._fea_ponding_cache = None
    project._gw_solver = None
    project._notify("mesh_changed")
    return dropped


def reset_fem_mesh(project) -> list[str]:
    """Remove the mesh and everything computed on it (see
    :func:`set_fem_mesh`); returns what was dropped."""
    return set_fem_mesh(project, None)
