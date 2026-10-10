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


def discrete_function_refusal(strength) -> Optional[Refusal]:
    """Why a Discrete Function cannot be computed with, or None.

    v0.1.246 (D229) — the reference's field of strength over the material:
    a function type (``undrained``: rows (x, y, cu); ``drained``: rows
    (x, y, c, φ)), an interpolation method the model knows, at least one
    point, every value a finite number, cu and c zero or more, φ in [0, 90),
    and no two points at the same place (two strengths for one point, which
    no interpolation can honour). Asked by the dialog, the API and the
    analysis, through :func:`strength_model_refusal`.
    """
    import math

    ftype = getattr(strength, "function_type", None)
    if ftype not in strength.FUNCTION_TYPES:
        return Refusal("discrete_function_type",
                       f"The function type must be one of "
                       f"{list(strength.FUNCTION_TYPES)}, got {ftype!r}.")
    method = getattr(strength, "method", None)
    if method not in strength.METHODS:
        return Refusal("discrete_function_method",
                       f"The interpolation method must be one of "
                       f"{list(strength.METHODS)}, got {method!r}.")
    width = 3 if ftype == "undrained" else 4
    what = ("(x, y, cu)" if ftype == "undrained" else "(x, y, c, phi)")
    try:
        rows = [tuple(r) for r in (strength.points or [])]
    except TypeError:
        return Refusal("discrete_function_not_points",
                       f"The table must be a list of {what} points.")
    if not rows:
        return Refusal("discrete_function_empty",
                       f"The table has no points: at least one {what} point "
                       f"is needed.")
    seen = set()
    for i, r in enumerate(rows, start=1):
        try:
            vals = tuple(float(v) for v in r)
        except (TypeError, ValueError):
            vals = ()
        if len(vals) != width:
            return Refusal("discrete_function_not_points",
                           f"Point {i} is not {what}: {r!r}.")
        if not all(math.isfinite(v) for v in vals):
            return Refusal("discrete_function_not_points",
                           f"Point {i} holds a value that is not finite.")
        if vals[2] < 0.0:
            return Refusal("discrete_function_strength",
                           f"Point {i}: the cohesion must be zero or more, "
                           f"got {vals[2]:g}.")
        if width == 4 and not 0.0 <= vals[3] < 90.0:
            return Refusal("discrete_function_angle",
                           f"Point {i}: the friction angle must be in "
                           f"[0, 90), got {vals[3]:g}.")
        if vals[:2] in seen:
            return Refusal("discrete_function_repeated",
                           f"Point {i} repeats the place ({vals[0]:g}, "
                           f"{vals[1]:g}): two strengths for one point.")
        seen.add(vals[:2])
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


def generalized_angle_or_surface_refusal(strength) -> Optional[Refusal]:
    """Why the "Angle or Surface" input of a Generalized Anisotropic model
    cannot be computed with, or None (v0.1.248, D231a).

    The reference's dialog: a base material, joints each with its angle (or
    its anisotropic surface) and its material, and, once per function, the
    mapping function (A and B, cosine or linear), which joint answers when
    there are several ("Worst Case" or "Closest") and whether a weaker base
    takes over. So: a base and at least one joint, each with a strength
    model that can be built; a joint angle that is a number; A and B with
    0 <= A <= B <= 90, as in Snowden, when the mapping reads them; the
    three choices among their values. v0.1.249 (D231b): joints by
    surface name their surface (``surface_id``) instead of an angle; that
    the surface is in the model is asked of the project
    (:func:`generalized_surfaces_refusal`).
    """
    import math

    from ..materials.builtin_models import GeneralizedAnisotropic as _G
    from ..materials.strength_model import StrengthModel

    if strength.definition not in _G.DEFINITIONS:
        return Refusal("generalized_aos_definition",
                       f"The anisotropy is defined by 'angle' or 'surface', "
                       f"not {strength.definition!r}.")
    if strength.mapping not in _G.MAPPINGS:
        return Refusal("generalized_aos_mapping",
                       f"The mapping function is one of {list(_G.MAPPINGS)}, "
                       f"not {strength.mapping!r}.")
    if strength.joint_selection not in _G.JOINT_SELECTIONS:
        return Refusal("generalized_aos_selection",
                       f"The joint selection is one of "
                       f"{list(_G.JOINT_SELECTIONS)}, not "
                       f"{strength.joint_selection!r}.")
    if not isinstance(strength.use_base_if_weaker, bool):
        return Refusal("generalized_aos_base_if_weaker",
                       f"use_base_if_weaker must be true or false, not "
                       f"{strength.use_base_if_weaker!r}.")
    base = strength.base
    if not isinstance(base, dict) or not base.get("model"):
        return Refusal("generalized_aos_base",
                       "The base needs a strength: a material or a model of "
                       "its own.")
    joints = strength.joints
    if not isinstance(joints, list) or not joints:
        return Refusal("generalized_aos_joints",
                       "At least one joint is needed, with its angle and its "
                       "strength.")
    for j, joint in enumerate(joints, start=1):
        if not isinstance(joint, dict) or not joint.get("model"):
            return Refusal("generalized_aos_joint_model",
                           f"Joint {j} needs a strength: a material or a "
                           f"model of its own.")
        if strength.definition == "surface":
            sid = joint.get("surface_id")
            if not isinstance(sid, str) or not sid:
                return Refusal("generalized_aos_joint_surface",
                               f"Joint {j} must name its anisotropic "
                               f"surface.")
        else:
            try:
                angle = float(joint.get("angle"))
            except (TypeError, ValueError):
                angle = float("nan")
            if not math.isfinite(angle):
                return Refusal("generalized_aos_joint_angle",
                               f"The angle of joint {j} must be a number of "
                               f"degrees.")
        if strength.mapping == "ab":
            try:
                a = float(joint.get("A"))
                b = float(joint.get("B"))
            except (TypeError, ValueError):
                a = b = float("nan")
            # B <= 90 as in Snowden: the offset never passes 90 degrees, so
            # a larger B would be a base that is never reached.
            if not (math.isfinite(a) and math.isfinite(b)) or \
                    not 0.0 <= a <= b <= 90.0:
                return Refusal("generalized_aos_ab",
                               f"Joint {j}: A and B must satisfy 0 <= A <= B "
                               f"<= 90 degrees; got A = {joint.get('A')!r}, B = "
                               f"{joint.get('B')!r}.")
    for key, entry in strength.children_items(active_only=True):
        try:
            child = StrengthModel.from_dict(entry["model"])
        except Exception as exc:  # noqa: BLE001 - the message says which
            return Refusal("generalized_aos_model",
                           f"The strength model of "
                           f"{strength.child_label(key)} cannot be built: "
                           f"{type(exc).__name__}: {exc}")
        if isinstance(child, _G):
            return Refusal("generalized_aos_nested",
                           f"{strength.child_label(key).capitalize()} holds "
                           f"a Generalized Anisotropic model; it takes a "
                           f"plain strength.")
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
                                            SnowdenModifiedAnisotropicLinear,
                                            StepFunction)
    from ..materials.strength_model import StrengthModel

    label = name if name is not None else "?"
    if isinstance(strength, (ShearNormalFunction, StepFunction)):
        # v0.1.227 (D217); the step function was called Discrete Function
        # until v0.1.246 (D229).
        why = function_points_refusal(strength.points)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, "
                                 f"{strength.DISPLAY_NAME}: {why.message}")
    if isinstance(strength, DiscreteFunction):
        # v0.1.246 (D229) — the reference's field over the material.
        why = discrete_function_refusal(strength)
        if why is None:
            return None
        return Refusal(why.code, f"Material {label!r}, Discrete Function: "
                                 f"{why.message}")
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
        # v0.1.248 (D231a) -- the input that computes is judged: the ranges
        # of "Angle Range" or the base and joints of "Angle or Surface".
        if strength.input_type not in strength.INPUT_TYPES:
            return Refusal("generalized_input_type",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"the input is one of "
                           f"{list(strength.INPUT_TYPES)}, not "
                           f"{strength.input_type!r}.")
        if strength.angle_or_surface:
            why = generalized_angle_or_surface_refusal(strength)
        else:
            why = generalized_anisotropic_rules_refusal(strength.rules)
        if why is not None:
            return Refusal(why.code, f"Material {label!r}, Generalized "
                                     f"Anisotropic: {why.message}")
        # v0.1.247 (D230) -- a switch, so a bool: a 0, a "false" or a None
        # would be read as true or false by whoever reads it next.
        if not isinstance(getattr(strength, "use_parent_water", True), bool):
            return Refusal(
                "generalized_parent_water",
                f"Material {label!r}, Generalized Anisotropic: "
                f"use_parent_water must be true or false, not "
                f"{strength.use_parent_water!r}.")
        for _key, entry in strength.children_items(active_only=True):
            why = strength_model_refusal(
                StrengthModel.from_dict(entry["model"]), name)
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

    v0.1.248 (D231a) — the base and the joints of "Angle or Surface" too:
    the children of the input that computes (``children_items``).
    """
    from ..materials.builtin_models import GeneralizedAnisotropic

    strength = getattr(material, "strength", None)
    if not isinstance(strength, GeneralizedAnisotropic):
        return None
    by_id = {m.id: m for m in materials}
    label = getattr(material, "name", "?")
    for key, entry in strength.children_items(active_only=True):
        who = strength.child_label(key)
        link = entry.get("material_id") if isinstance(entry, dict) else None
        if not link:
            continue
        src = by_id.get(link)
        if src is None:
            return Refusal("generalized_link_missing",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"{who} links a material that is not in the "
                           f"project.")
        if src is material:
            return Refusal("generalized_link_self",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"{who} links the material itself.")
        if isinstance(getattr(src, "strength", None),
                      GeneralizedAnisotropic):
            return Refusal("generalized_link_generalized",
                           f"Material {label!r}, Generalized Anisotropic: "
                           f"{who} links {src.name!r}, another "
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


def generalized_surfaces_refusal(material, project) -> Optional[Refusal]:
    """Why the joints of a Generalized Anisotropic "Angle or Surface"
    material defined by a surface cannot be computed with in ``project``,
    or None (v0.1.249, D231b): each one must name an anisotropic surface of
    the model. A joint whose surface is gone has no orientation to read, and
    computing it with some other angle would be a number nobody entered."""
    from ..geometry.boundary_type import BoundaryType
    from ..materials.builtin_models import GeneralizedAnisotropic

    st = getattr(material, "strength", None)
    if not (isinstance(st, GeneralizedAnisotropic) and st.angle_or_surface
            and st.definition == "surface"):
        return None
    ids = {b.id for b in getattr(project, "boundaries", ())
           if b.btype == BoundaryType.ANISOTROPIC_SURFACE}
    for j, joint in enumerate(st.joints or [], start=1):
        sid = joint.get("surface_id") if isinstance(joint, dict) else None
        if sid not in ids:
            return Refusal("generalized_surface_missing",
                           f"Material {getattr(material, 'name', '?')!r}, "
                           f"Generalized Anisotropic: joint {j} names an "
                           f"anisotropic surface that is not in the model.")
    return None


def surface_in_use_refusal(project, boundary_id) -> Optional[Refusal]:
    """Why the boundary ``boundary_id`` cannot be deleted, or None
    (v0.1.249, D231b): an anisotropic surface that a joint of a
    Generalized Anisotropic material reads. Deleting it would leave the
    joint with no orientation; the user changes the joint first. Asked by
    the API and by the interface."""
    from ..materials.builtin_models import GeneralizedAnisotropic

    users = []
    for m in getattr(project, "materials", ()):
        st = getattr(m, "strength", None)
        if not isinstance(st, GeneralizedAnisotropic):
            continue
        if any(isinstance(j, dict) and j.get("surface_id") == boundary_id
               for j in st.joints or []):
            users.append(repr(m.name))
    if not users:
        return None
    return Refusal("surface_in_use",
                   "The anisotropic surface is read by the joints of "
                   + ", ".join(users) + "; change them first.")


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
#: v0.1.256 (D237) — the angular limits the reference gives for the Block
#: Search projection angles, in degrees counter-clockwise from the positive
#: x axis. A typical search keeps the left angle in 95..175 and the right
#: one in 5..85, "in order to generate kinematically valid slip surfaces";
#: a surface that daylights into the face with a downward dip may take the
#: left angle down to 265 on a left-facing slope, or the right one down to
#: −85 on a right-facing slope, and only on that side. The reasons are
#: kinematic: 5° off the vertical keeps every ray on its own side and the
#: surface single-valued in x, which vertical slicing needs; and the crest
#: side cannot dip, because the head scarp leaves the ground upwards and a
#: descending ray never reaches a level crest.
BLOCK_LEFT_MIN = 95.0
BLOCK_LEFT_MAX = 175.0
BLOCK_LEFT_MAX_FACE = 265.0
BLOCK_RIGHT_MIN = 5.0
BLOCK_RIGHT_MIN_FACE = -85.0
BLOCK_RIGHT_MAX = 85.0

#: The window each side's angles are read in, closed at both ends. A left
#: ray must point to the left, so its forbidden direction is 0° and its
#: window is centred on 180°; a right ray's forbidden direction is 180°.
_BLOCK_WINDOWS = {"left": (0.0, 360.0), "right": (-180.0, 180.0)}


def _into_window(angle: float, side: str) -> float:
    """``angle`` as the same direction inside ``side``'s window.

    Only a value strictly outside the window is shifted, by whole turns,
    so every value inside it is returned untouched — bit for bit.
    """
    lo, hi = _BLOCK_WINDOWS[side]
    a = float(angle)
    while a < lo:
        a += 360.0
    while a > hi:
        a -= 360.0
    return a


def block_projection_range(start, end, side: str) -> tuple[float, float]:
    """The arc of directions a projection-angle pair denotes, as (lo, hi).

    v0.1.256 (D237). A projection angle is a direction, so 315° and −45°
    are one ray, and two directions bound two arcs. On each side exactly
    one of them avoids the direction that ray can never take (0° for the
    left ray, which would point right; 180° for the right ray); that arc
    is the set the user wrote, whatever the order of the two angles, and a
    uniform draw over it has the same distribution in both orders. The
    other arc between 45° and −45° on the right, for instance, holds every
    ray from 90° to 270°: rays that point back across the surface they are
    meant to close. So the only reading of «45 to −45» on the right is
    [−45, 45]. The reference writes the convention as "the Start Angle
    must always be LESS than the End Angle"; a pair written the other way
    is read here and reported by :func:`block_angle_notes`, not refused.

    Each angle is first brought into its side's closed window, [0, 360]
    on the left and [−180, 180] on the right; an angle already inside is
    untouched and the pair comes back as ``(min, max)``, which is what the
    search drew before this function existed. ``side`` is ``"left"`` or
    ``"right"``.
    """
    a = _into_window(start, side)
    b = _into_window(end, side)
    return (min(a, b), max(a, b))


def optimize_technique_refusal(search_settings) -> Optional[Refusal]:
    """v0.1.260 (D259) — an optimisation technique this program does not
    have. One rule, asked by the analysis (``check_analysis_settings``) and
    by every door that writes the setting, so that a misspelt value is
    refused rather than quietly run as the default."""
    from ogr_core.project.settings import OptimizeTechnique
    allowed = [t.value for t in OptimizeTechnique]
    value = getattr(search_settings, "optimize_technique",
                    OptimizeTechnique.MONTE_CARLO.value)
    if value in allowed:
        return None
    return Refusal(
        "optimize_technique_unknown",
        "Unknown optimisation technique %r: it has to be one of %s."
        % (value, ", ".join(allowed)))


def slope_limit_windows(search_settings) -> Optional[tuple]:
    """The two Slope Limit windows as ``((lo, hi), (lo, hi))``, first set
    first, or None unless both sets are complete. Each pair is sorted; the
    sets keep the order they were typed in, which is the order a message
    should quote them in (the engine sorts them by their left limit,
    ``search._normalise_slope_limits``)."""
    keys = ("slope_limit_left", "slope_limit_right",
            "slope_limit_left_2", "slope_limit_right_2")
    vals = [getattr(search_settings, k, None) for k in keys]
    if any(v is None for v in vals):
        return None
    first = tuple(sorted((float(vals[0]), float(vals[1]))))
    second = tuple(sorted((float(vals[2]), float(vals[3]))))
    return first, second


def slope_limit_windows_overlap(search_settings) -> Optional[str]:
    """How the two Slope Limit windows share ground: ``"nested"`` (one
    lies inside the other), ``"partial"`` (they overlap and neither holds
    the other) or None (separate, touching at a single point, or fewer
    than two sets).

    v0.1.261 (D262). Overlap means a common stretch of POSITIVE length,
    judged against 1e-9 of the span of the two windows, so that two
    windows that only touch at a limit point stay separate whatever the
    units of the model.
    """
    w = slope_limit_windows(search_settings)
    if w is None:
        return None
    (a0, a1), (b0, b1) = w
    span = max(a1, b1) - min(a0, b0)
    tol = 1e-9 * span
    if min(a1, b1) - max(a0, b0) <= tol:
        return None
    if (a0 <= b0 + tol and b1 <= a1 + tol) or (b0 <= a0 + tol
                                               and a1 <= b1 + tol):
        return "nested"
    return "partial"


def slope_limit_windows_refusal(search_settings) -> Optional[Refusal]:
    """v0.1.261 (D262) — a Grid Search with two overlapping Slope Limit
    windows.

    With two sets, the grid generates at each centre the radii of the
    circles that run from one window to the other (``GridSearch.
    _radius_bracket_two_windows``, read off the reference in D77). That
    rule was measured on SEPARATE windows only. Each crossing of the
    ground is given the first window that contains it, the windows being
    sorted by their left limit, so on a stretch two windows share every
    crossing goes to the one that starts further left — a choice nothing
    measured supports — and with a window inside another that starts
    further left no crossing ever belongs to the inner one and not one
    circle is generated: the 109 of the verification bank, 0..30 +
    14.473..18, gave none at any of 121 centres, in silence. The
    reference's behaviour with overlapping windows is not measured
    anywhere, so it is refused here instead of being invented.

    Only the grid: every other search reads the two sets as ranges an end
    may daylight in, which is well defined however they overlap
    (``search._within_slope_limits``).
    """
    if getattr(search_settings, "search_method", None) != "grid":
        return None
    how = slope_limit_windows_overlap(search_settings)
    if how is None:
        return None
    (a0, a1), (b0, b1) = slope_limit_windows(search_settings)
    return Refusal(
        "slope_limit_windows_overlap",
        "The two sets of Slope Limits overlap ([%g, %g] and [%g, %g]). "
        "With two sets, a Grid Search generates the circles that run from "
        "one window to the other, a rule measured on separate windows "
        "only: on the stretch two windows share it gives every crossing "
        "to the window that starts further left, which nothing measured "
        "supports, and with a window inside one that starts further left "
        "it generates no circle at all. Make the two windows separate, or "
        "use a single set." % (a0, a1, b0, b1))


@dataclass(frozen=True)
class BlockAngleNote:
    """Something to say about one side's Block Search projection angles.

    ``code`` is ``"block_angle_reread"`` (the pair was written backwards,
    or with an angle outside its side's window, and is read as ``lo..hi``)
    or ``"block_angle_out_of_limits"`` (``lo..hi`` leaves the reference's
    range ``limit_lo..limit_hi`` for this slope). The numbers are there so
    the interface can say it in its own language; ``message`` is the
    engine's English.
    """

    code: str
    side: str
    start: float
    end: float
    lo: float
    hi: float
    limit_lo: float
    limit_hi: float
    message: str


def block_angle_limits(side: str, crest_on_right: bool) -> tuple[float, float]:
    """The reference's admissible range for ``side`` on this slope.

    The downward extension belongs to the side where the face is: the left
    end of a slope whose crest is on the right (a left-facing slope), the
    right end of one whose crest is on the left.
    """
    if side == "left":
        return (BLOCK_LEFT_MIN,
                BLOCK_LEFT_MAX_FACE if crest_on_right else BLOCK_LEFT_MAX)
    return (BLOCK_RIGHT_MIN if crest_on_right else BLOCK_RIGHT_MIN_FACE,
            BLOCK_RIGHT_MAX)


def block_angle_notes(angles, crest_on_right: bool) -> list[BlockAngleNote]:
    """What the Block Search will do with these projection angles, said.

    v0.1.256 (D237). ``angles`` is anything with the four
    ``block_*_angle_deg`` attributes of the search settings;
    ``crest_on_right`` says which side the face is on, and is asked by the
    caller from ``ogr_slip2d.failure_direction`` because this package
    cannot import it.

    Not refusals, by the owner's decision of 2026-10-04: a pair written
    backwards is read as the arc of :func:`block_projection_range` and an
    angle outside the reference's limits is used as given, but both are
    said. Before this version neither was: the search straightened a
    reversed pair with ``min``/``max`` and calculated with any angle at all.
    """
    notes: list[BlockAngleNote] = []
    for side, label in (("left", "left"), ("right", "right")):
        start = float(getattr(angles, f"block_{side}_start_angle_deg"))
        end = float(getattr(angles, f"block_{side}_end_angle_deg"))
        lo, hi = block_projection_range(start, end, side)
        limit_lo, limit_hi = block_angle_limits(side, crest_on_right)
        if (start, end) != (lo, hi):
            forbidden = 0 if side == "left" else 180
            notes.append(BlockAngleNote(
                "block_angle_reread", side, start, end, lo, hi,
                limit_lo, limit_hi,
                f"The {label} projection angles are written from {start:g}° "
                f"to {end:g}°, and the reference measures them "
                f"counter-clockwise from the positive x axis with the Start "
                f"Angle less than the End Angle. They were read as {lo:g}° "
                f"to {hi:g}°: the arc between the two that avoids "
                f"{forbidden}°, a direction no {label} projection can "
                f"take."))
        if lo < limit_lo or hi > limit_hi:
            facing = "left" if crest_on_right else "right"
            notes.append(BlockAngleNote(
                "block_angle_out_of_limits", side, start, end, lo, hi,
                limit_lo, limit_hi,
                f"The {label} projection angles, {lo:g}° to {hi:g}°, go "
                f"outside {limit_lo:g}° to {limit_hi:g}°, the range the "
                f"reference gives for kinematically valid surfaces on a "
                f"{facing}-facing slope. The search uses them as given; a "
                f"projection that cannot reach the ground leaves its "
                f"surface invalid."))
    return notes


# ----------------------------------------------------------------------
#: The bound every action factor meets: an unfavourable one is at least 1
#: and a favourable one at most 1 (EN 1990:2002, Table A1.2 (A) to (C);
#: EN 1997-1:2004, Tables A.1, A.3, A.15 and A.17: permanent 1.1/0.9,
#: 1.35/1.0, 1.0/1.0, 1.0/0.9 and 1.35/0.9, variable 1.5/0 and 1.3/0, never
#: the other way round). Since v0.1.243 (D226b) the variable pair meets it
#: too; the name stayed.
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

    v0.1.243 (D226b) — the variable pair, now that each load is classed and
    factored whole: γQ ≥ 1 ≥ γQ,fav ≥ 0, by the same argument (a load that
    drives grows, one that resists shrinks, so the balance that decided the
    sense of sliding can only grow). Here 0 is allowed and is EN 1997-1's own
    value: a variable load that would help may not be there.
    """
    import math

    names = (("factor_permanent", "permanent actions, unfavourable"),
             ("factor_permanent_favourable", "permanent actions, favourable"),
             ("factor_variable", "variable actions, unfavourable"),
             ("factor_variable_favourable", "variable actions, favourable"))
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
    q_unfav = values["factor_variable"]
    q_fav = values["factor_variable_favourable"]
    if q_unfav < PERMANENT_ACTION_FACTOR_BOUND:
        return Refusal(
            "design_action_factor_variable_unfavourable_below_one",
            f"The partial factor on unfavourable variable actions must be at "
            f"least 1, got {q_unfav}: below 1 it would make a load that "
            f"drives the sliding lighter than its characteristic value.")
    if q_fav > PERMANENT_ACTION_FACTOR_BOUND:
        return Refusal(
            "design_action_factor_variable_favourable_above_one",
            f"The partial factor on favourable variable actions must be at "
            f"most 1, got {q_fav}: above 1 it would make a load that resists "
            f"the sliding heavier than its characteristic value.")
    if q_fav < 0.0:
        return Refusal(
            "design_action_factor_variable_favourable_negative",
            f"The partial factor on favourable variable actions must not be "
            f"negative, got {q_fav}: at 0 the load is left out, which is "
            f"the most a favourable variable action can be discounted.")
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


def fe_model_signature(project, regions=None) -> str:
    """The fingerprint of what a finite-element mesh is built from: the
    resolved regions, each with its outline, its holes and the material it
    takes (v0.1.280, D284).

    It is what ``generate_mesh_for_project`` meshes and nothing else: the
    hydraulic properties are read from the materials at solve time, so
    changing a permeability does not change it, while moving a vertex,
    deleting or reassigning a material, or redefining the model does. The
    canvas edits boundaries in place without notifying (see
    ``Project.regions_frozen``), which is why this is a fingerprint of the
    content and not a revision counter. ``regions`` may be passed when the
    caller has just resolved them."""
    import hashlib
    if regions is None:
        regions = project.resolve_regions()
    items = []
    for r in regions:
        outline = tuple((v.x, v.y) for v in r.polygon.vertices)
        holes = tuple(tuple((v.x, v.y) for v in h.vertices)
                      for h in (getattr(r, "holes", None) or ()))
        items.append(repr((getattr(r, "material_id", None), outline, holes)))
    items.sort()
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()[:20]


#: The two reasons of :func:`mesh_mismatch_reason`, English keys that the
#: interface translates at the point of use.
MESH_ORPHAN_ELEMENTS = ("{0} element(s) of the mesh belong to a material "
                        "that no longer exists. Regenerate the mesh.")
MESH_OF_ANOTHER_MODEL = ("The mesh was generated for another geometry or "
                         "material assignment. Regenerate the mesh.")


def mesh_mismatch(project) -> Optional[str]:
    """:func:`mesh_mismatch_reason` in words (English); None when the
    stored mesh is a mesh of this model or there is none."""
    why = mesh_mismatch_reason(project)
    return why[0].format(*why[1]) if why else None


def mesh_mismatch_reason(project):
    """Why the stored finite-element mesh is not a mesh of this model, as
    ``(template, args)``; None when it is, or when there is no mesh
    (v0.1.280, D284).

    A mesh survives every edit but *Generate* and *Reset*
    (:func:`set_fem_mesh`): deleting or replacing a material left its
    elements pointing to an id the solver does not know, and it computed
    them with the default properties (Constant, Ks 1e-6) without a word;
    an edited geometry left a mesh of the old one. Measured: a material
    deleted with ``reassign_to`` left 190 of 190 elements orphaned and the
    discharge ten times off. Every door that solves asks this first and
    refuses (decision of the owner, 2026-10-08).

    Two checks: elements whose material no longer exists (any mesh, also
    one saved before this version), and the fingerprint stored at meshing
    against the model's (meshes generated since this version)."""
    mesh = getattr(project, "fem_mesh", None)
    if mesh is None or not getattr(mesh, "elements", None):
        return None
    live = {m.id for m in getattr(project, "materials", [])}
    orphans = sum(1 for e in mesh.elements
                  if e.material_id is not None and e.material_id not in live)
    if orphans:
        return MESH_ORPHAN_ELEMENTS, (orphans,)
    stored = (getattr(mesh, "notes", None) or {}).get("model_signature")
    if stored and stored != fe_model_signature(project):
        return MESH_OF_ANOTHER_MODEL, ()
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


def transient_storage_is_read(project) -> bool:
    """True when the water contents and the specific storage of the
    materials move a number: only a transient groundwater analysis reads
    them (``TransientSeepageSolver``: the stored water and the moisture
    capacity of every step). A steady analysis, the slope stability and
    the coupling never do.

    v0.1.268 (D191) — the hydraulic-properties dialog shows theta_s,
    theta_r and Ss for every model and greys them out when this is False,
    so a field that changes nothing says so (rule 7). The alpha, n and m of
    the curve depend on the permeability model too: see
    :func:`retention_field_is_read`.
    """
    gw = getattr(getattr(project, "settings", None), "groundwater", None)
    return bool(getattr(gw, "transient", False))


def retention_field_is_read(project, model, field: str) -> bool:
    """True when ``field`` of the water-retention curve of a material with
    permeability ``model`` moves a number in ``project`` (rule 7).

    v0.1.278 (D275):

    * ``wc_alpha`` — only a transient analysis, and never with van
      Genuchten, whose curve reads ``vg_alpha``
      (``HydraulicProperties.retention_alpha``);
    * ``vg_alpha`` — always with van Genuchten (its permeability); never
      with another model;
    * ``vg_n``, ``vg_m`` and ``vg_custom_m`` — always with van Genuchten
      (its permeability); with another model, only a transient;
    * ``wc_sat``, ``wc_res`` and ``specific_storage`` — only a transient
      (:func:`transient_storage_is_read`).
    """
    from ogr_core.hydraulic.permeability_models import PermeabilityModel
    vg = model == PermeabilityModel.VAN_GENUCHTEN
    transient = transient_storage_is_read(project)
    if field == "wc_alpha":
        return transient and not vg
    if field == "vg_alpha":
        return vg
    if field in ("vg_n", "vg_m", "vg_custom_m"):
        return vg or transient
    return transient


# ----------------------------------------------------------------------
# v0.1.286 (D287) — who uses a material
# ----------------------------------------------------------------------
#: The window's refusal to remove a material in use. A template: the
#: dialog fills in the name and the counts, and translates the key.
MATERIAL_IN_USE = ("{0} cannot be removed: {1} region(s) and {2} weak "
                   "layer(s) use it. Assign them another material first.")


def material_link_users(materials, material_id) -> list:
    """``(material, rule)`` for every Generalized Anisotropic range (and,
    since D231a, base or joint of "Angle or Surface") in ``materials`` that
    takes its strength from ``material_id`` (D218b)."""
    return [(g, r) for g in materials
            if getattr(g, "id", None) != material_id
            and hasattr(getattr(g, "strength", None), "children_items")
            for _k, r in g.strength.children_items()
            if isinstance(r, dict) and r.get("material_id") == material_id]


def material_users(project, material_id, materials=None):
    """Who uses a material: ``(region assignments, weak layers, linked
    ranges)``.

    v0.1.286 (D287) — moved from the API's ``material_delete``, which was
    the only door that asked: the window's *Define Materials* removed a
    material that regions used without a word, and left them pointing at
    an id that no longer exists (the limit equilibrium then found no
    factor and blamed surfaces leaving the model). ``materials`` is the
    list searched for linked ranges — the dialog's pending one — and
    defaults to the project's.
    """
    regions = [a for a in project.region_assignments
               if a.get("material_id") == material_id]
    layers = [b for b in project.boundaries
              if getattr(b, "material_id", None) == material_id]
    links = material_link_users(
        project.materials if materials is None else materials, material_id)
    return regions, layers, links


def material_region_uses(project) -> dict:
    """``{material id: (region assignments, weak layers)}`` for every
    material of ``project``: what the materials dialog — which knows
    nothing of a Project — is handed to refuse a removal (v0.1.286,
    D287). The linked ranges it checks itself, on its pending list."""
    out = {}
    for m in project.materials:
        regions, layers, _links = material_users(project, m.id)
        out[m.id] = (len(regions), len(layers))
    return out


# ----------------------------------------------------------------------
# v0.1.298 (D298) — a region assigned to a material that no longer exists
# ----------------------------------------------------------------------
#: The warning, a template with the click point of the assignment. Every
#: door says it: the validation, the analysis's notes, the window before
#: computing (the owner's decision: warn, say what to change, and let the
#: user compute anyway) and on opening a file.
ORPHAN_ASSIGNMENT = (
    "The region at ({0:.2f}, {1:.2f}) is assigned a material that no "
    "longer exists. Assign it another material (Properties > Assign "
    "Materials); a surface through it cannot be analysed.")


def orphan_assignments(project) -> list:
    """The region assignments whose material is not in the project.

    Up to 0.1.285 the window's *Define Materials* removed a material in use
    and left its regions pointing at it (D287), and a file saved then keeps
    them. ``resolve_regions`` copies the id unchecked, ``material_at`` gives
    None there, and the slicer used to refuse every surface through such a
    region as "outside the External Boundary" while the validation said the
    model could run (D298)."""
    ids = {m.id for m in project.materials}
    return [a for a in project.region_assignments
            if a.get("material_id") not in ids]


def orphan_assignment_reasons(project) -> list:
    """``(template, args)`` per orphan assignment, for an interface that
    translates the template (``ORPHAN_ASSIGNMENT``)."""
    return [(ORPHAN_ASSIGNMENT,
             (float(a.get("x", 0.0)), float(a.get("y", 0.0))))
            for a in orphan_assignments(project)]


def orphan_assignment_messages(project) -> list:
    """The same, in English, for the API and the analysis notes."""
    return [t.format(*args) for t, args in orphan_assignment_reasons(project)]


def in_orphan_region(project, x: float, y: float) -> bool:
    """Whether (x, y) lies in a region whose material does not exist — what
    the slicer asks to name the cause of a base with no material (D298)."""
    mid = project.region_material_id_at(x, y)
    return mid is not None and project.material_by_id(mid) is None
