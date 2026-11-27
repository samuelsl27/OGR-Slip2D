# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the Interpret window asks of a search result, without the window.

v0.1.201 (spec 008, F3b). These questions were answered inside
``ogr_gui/interpret_window.py`` and ``ogr_gui/canvas/canvas_view.py``, so
an agent could not ask them and a script had to re-derive them. They move
here, and the interface asks here:

* :func:`error_code` — the negative code the reference writes in place of
  a factor of safety (-120, -112, -111, -101); one mapping for the raw-data
  export, the census and the agent;
* :func:`raw_data_rows` and its header :func:`raw_data_columns`, which list
  every surface the run analysed, the user's included and marked
  (v0.1.442), and :func:`invalid_summary`, the census, which stays the
  search's: it describes the population ``total_count`` counts;
* :func:`surfaces_through_point` — measured to the surface the engine
  PRICED (the base of its slices), not to the whole circle: a point below
  the ground on the far side of a circle is not on its slip surface;
* :func:`minimum_per_centre`, :func:`sf_along_slope`;
* :func:`slice_rows` — the per-slice numbers OF THE METHOD. The interface's
  "Show Values Along Surface" recomputed the effective normal stress as
  W cos(alpha) / b - u, which is none of the nine methods' answer and not
  even the Ordinary method's (that divides by the base length l = b /
  cos(alpha), so it was off by 1/cos(alpha) for it too);
* :func:`surface_area`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from .slice_store import SpilledSlices

#: The codes the reference writes in place of a factor of safety.
ERROR_TENSILE = -120
ERROR_M_ALPHA = -112
ERROR_NOT_CONVERGED = -111
#: v0.1.445 (D420) — a circle that runs outside the External Boundary
#: between its crossings with the ground: the reference's -103. Counted on
#: the result (``SearchResult.leaves_external``), never on an evaluation:
#: such a circle is not sliced, so ``error_code`` never returns it.
ERROR_LEAVES_EXTERNAL = -103
#: v0.1.496 (D435) — a surface with an end that daylights outside the
#: user's Slope Limits: the reference's -113 («Slip surface intersects the
#: External Boundary outside of user-defined Slope Limits»). Its -101 applies
#: instead to one that does not intersect within the default limits either,
#: the ends of the profile; every surface counted here does, because one that
#: cuts the ground nowhere is refused before as ``misses_ground``. Counted on
#: the result (``SearchResult.outside_slope_limits``).
ERROR_SLOPE_LIMITS = -113
ERROR_OTHER = -101
#: v0.1.495 (D434) — a circle of a grid centre with no valid radius, which
#: the grid emits so that its population stays (nx+1)(ny+1)(rinc+1): the
#: reference's -1000, «No valid slip surface is generated». Counted on the
#: result (``SearchResult.no_valid_radius``), like the -103. Ej_1 publishes
#: 231 of them in every method, and no -101.
ERROR_NO_SURFACE = -1000
ERROR_CODES = {
    ERROR_TENSILE: "tensile stress at a slice base (Tensile Stress Check)",
    ERROR_M_ALPHA: "m-alpha below its limit (the m-alpha screen)",
    ERROR_NOT_CONVERGED: "no converged factor of safety",
    ERROR_LEAVES_EXTERNAL: "the circle leaves the External Boundary between "
                           "its crossings with the ground (counted before "
                           "slicing, so no surface carries it)",
    ERROR_SLOPE_LIMITS: "an end daylights outside the Slope Limits (counted "
                        "before slicing, so no surface carries it)",
    ERROR_OTHER: "any other rejection",
    ERROR_NO_SURFACE: "a circle of a grid centre with no valid radius: no "
                      "valid slip surface is generated there (counted "
                      "before slicing, so no surface carries it)",
}


# ----------------------------------------------------------------------
# Codes and the census
# ----------------------------------------------------------------------
def error_code(res) -> Optional[int]:
    """The reference's negative code for a rejected evaluation; None for a
    valid, admissible one.

    -120 for the Tensile Stress Check, -112 for the m-alpha screen, -111
    for a factor of safety that did not converge, -101 for anything else.
    The tensile screen goes first because the screen tests tension first,
    so a surface failing both is a tensile rejection (v0.1.192, D177). The
    m-alpha branch also accepts the note, so a result built before
    ``admissibility_reason`` existed maps as it always did.

    v0.1.211 (D184) — a surface the checks could not evaluate is -101, and
    that branch goes BEFORE the note test: the exception's own text can say
    ``m_alpha`` (a missing ``m_alpha_sign`` key, say), and -112 is a verdict
    of the m-alpha screen, which is exactly what did not happen.
    """
    from .methods.base import (SCREEN_ERROR, SCREEN_M_ALPHA,
                               SCREEN_TENSILE_STRESS)

    if res.is_valid and getattr(res, "admissible", True):
        return None
    why = getattr(res, "admissibility_reason", "") or ""
    note = (getattr(res, "admissibility_note", "") or
            getattr(res, "error_message", "") or "")
    if why == SCREEN_TENSILE_STRESS:
        return ERROR_TENSILE
    if why == SCREEN_ERROR:
        return ERROR_OTHER
    if why == SCREEN_M_ALPHA or "m_alpha" in note:
        return ERROR_M_ALPHA
    if not res.converged:
        return ERROR_NOT_CONVERGED
    return ERROR_OTHER


def invalid_reason(res) -> Optional[str]:
    """Why an evaluation was rejected, in words, or None if it was not.

    The text groups the census and feeds the interface's error-code
    filter; the CODE is :func:`error_code`.
    """
    if res.is_valid and getattr(res, "admissible", True):
        return None
    return (getattr(res, "error_message", None)
            or getattr(res, "admissibility_note", None)
            or "did not converge")


def invalid_group(res) -> Optional[str]:
    """The group an evaluation's rejection is filed under, in English: its
    reason with the values that vary between surfaces left out ("…"), as
    the interpretation window groups them (v0.1.354, D335); a reason
    without a code is its own group. None if it was not rejected."""
    if res.is_valid and getattr(res, "admissible", True):
        return None
    from ogr_core.messages import render

    from .messages import MESSAGES
    for attr, code_attr, args_attr in (
            ("error_message", "message_code", "message_args"),
            ("admissibility_note", "note_code", "note_args")):
        sentence = getattr(res, attr, None)
        if sentence:
            return render(MESSAGES, getattr(res, code_attr, "") or "",
                          getattr(res, args_attr, None) or {}, sentence,
                          elide=True)
    return "did not converge"


#: The header of :func:`raw_data_rows` in a run without surfaces of the user.
RAW_DATA_COLUMNS = ("centre_x", "centre_y", "radius", "x_left", "x_right",
                    "fos_or_error_code")
#: Its seventh column, only in a run that analysed a surface the user drew.
RAW_DATA_USER_COLUMN = "user_defined"


def raw_data_columns(search_result) -> list:
    """The header of :func:`raw_data_rows` for THIS run (v0.1.442, D400).

    Six columns, as always, for a run without surfaces of the user; a
    seventh, ``user_defined``, when the run analysed any, valid or not. The
    one place the header is written: the API and the interpretation window
    each spelled the six names out by hand.
    """
    cols = list(RAW_DATA_COLUMNS)
    if getattr(search_result, "user_evaluations", None):
        cols.append(RAW_DATA_USER_COLUMN)
    return cols


def raw_data_rows(search_result) -> list:
    """One row per surface analysed, valid or not: ``[centre_x, centre_y,
    radius, x_left, x_right, fos or error code]`` as strings — the
    reference's *Export Raw Data*. A surface rejected before it was sliced
    has no result and no row.

    v0.1.442 (D400) — the surfaces the user drew are surfaces the run
    analysed, and one of them may be its critical surface: they were not
    here. They follow the search's rows, which keep their order, and a run
    that has any gives EVERY row a seventh cell, ``"1"`` for a surface of
    the user and ``"0"`` for one of the search
    (:func:`raw_data_columns`). Without any, the six cells of always.
    """
    from .search import all_evaluations_of

    # By identity, as ``is_user_surface_of``. The ids are of objects the
    # result holds while this runs, so none can be reused meanwhile.
    theirs = {id(r) for r in
              getattr(search_result, "user_evaluations", None) or ()}
    rows = []
    for r in all_evaluations_of(search_result):
        sd = r.surface.to_dict()
        code = error_code(r)
        row = [
            f"{sd.get('centre_x', '')}", f"{sd.get('centre_y', '')}",
            f"{sd.get('radius', '')}",
            f"{sd.get('x_left', '')}", f"{sd.get('x_right', '')}",
            f"{r.fos:.6f}" if code is None else f"{code}",
        ]
        if theirs:
            row.append("1" if id(r) in theirs else "0")
        rows.append(row)
    return rows


#: v0.1.445 (D420) — the rejections a search counts on its RESULT because
#: they leave no evaluation: ``(attribute, code, reason)``, in the order the
#: census lists them. One list, read by :func:`invalid_summary` and by the
#: interpretation window's summary of rejected surfaces, which until this
#: version kept a census of its own and called all of these "discarded
#: before slicing, so they carry no error code".
#:
#: * v0.1.258 (D244) — polylines refused at an end: a surface with an end
#:   off the ground meets the slope once or not at all, which is the
#:   reference's −101 («Only one (or none) slip surface / slope
#:   intersections»). OGR also uses −101 for "any other rejection"
#:   (``ERROR_OTHER``): the two meanings share the code, and the reason
#:   tells them apart;
#: * v0.1.259 (D256) — surfaces whose base rose above the ground between
#:   the ends, under OGR's "any other rejection" −101 with a reason of
#:   their own;
#: * v0.1.261 (D263) — surfaces refused because an end daylights outside
#:   the Slope Limits, and circles that do not cut the ground twice, which
#:   ARE its −101 in its own words. The first were filed under −101 too, on
#:   the reading that the reference does not code them: its help does, −113
#:   (v0.1.496, D435);
#: * v0.1.445 (D420) — circles that leave the External Boundary between
#:   their crossings with the ground, its −103;
#: * v0.1.495 (D434) — the circles of a grid centre with no valid radius,
#:   its −1000, taken out of the two rows of D263 whichever refused them.
#:   They were Ej_1's 231 −101 ``misses_ground`` (the column x = 120) where
#:   the reference publishes 231 −1000 and no −101.
COUNTED_REJECTIONS = (
    (("ends_below_ground", "ends_above_ground"), ERROR_OTHER,
     "an end of the polyline is not on the ground surface"),
    (("bases_above_ground",), ERROR_OTHER,
     "the base rises above the ground surface between the ends"),
    (("outside_slope_limits",), ERROR_SLOPE_LIMITS,
     "an end daylights outside the Slope Limits"),
    (("misses_ground",), ERROR_OTHER,
     "the circle does not cut the ground surface twice"),
    (("leaves_external",), ERROR_LEAVES_EXTERNAL,
     "the circle leaves the External Boundary between its crossings with "
     "the ground"),
    (("no_valid_radius",), ERROR_NO_SURFACE,
     "the circle is one of a grid centre with no valid radius"),
)


def counted_rejections(search_result) -> list:
    """``[(code, reason, n)]``: the rejections ``search_result`` counted
    without an evaluation, those with ``n > 0``, in the census's order
    (:data:`COUNTED_REJECTIONS`)."""
    out = []
    for attrs, code, why in COUNTED_REJECTIONS:
        n = sum(int(getattr(search_result, a, 0) or 0) for a in attrs)
        if n:
            out.append((code, why, n))
    return out


def invalid_summary(search_result) -> dict:
    """The census of rejected surfaces: by code, by reason, by group, and
    the ones that were never sliced or a focus object removed.

    ``by_reason`` keys on the whole sentence, values and all, so one
    condition found at several slice counts is several entries. v0.1.354
    (D335) -- ``by_group`` keys on the group the interpretation window files
    a rejection under since v0.1.333 (D314): the reason's code with the
    values that vary from surface to surface left out ("…"). A reason
    without a code is its own group. ``by_code`` is the reference's error
    code (-112, -101 ...), as it always was.

    It reads ``evaluations`` alone, on purpose (v0.1.442, D400): the census
    is of what the SEARCH generated, the population ``total_count`` and the
    counters describe. A surface the user drew and a check rejected is in
    the listings, marked, and not here.
    """
    by_code: dict = {}
    by_reason: dict = {}
    by_group: dict = {}
    for ev in getattr(search_result, "evaluations", []) or []:
        code = error_code(ev)
        if code is None:
            continue
        by_code[code] = by_code.get(code, 0) + 1
        why = invalid_reason(ev)
        by_reason[why] = by_reason.get(why, 0) + 1
        group = invalid_group(ev)
        by_group[group] = by_group.get(group, 0) + 1
    # The rejections that leave no evaluation arrive as counts on the
    # result, each under its code with a reason of its own
    # (:data:`COUNTED_REJECTIONS`); until each was counted, it sat in "not
    # sliced" with no reason.
    for code, why, n in counted_rejections(search_result):
        by_code[code] = by_code.get(code, 0) + n
        by_reason[why] = by_reason.get(why, 0) + n
        by_group[why] = by_group.get(why, 0) + n
    generated = getattr(search_result, "total_count",
                        len(getattr(search_result, "evaluations", [])))
    analysed = getattr(search_result, "analysed_count",
                       getattr(search_result, "valid_count", 0))
    with_code = sum(by_code.values())
    return {
        "generated": generated,
        "analysed": analysed,
        "rejected": generated - analysed,
        "by_code": dict(sorted(by_code.items())),
        "by_reason": dict(sorted(by_reason.items(),
                                 key=lambda kv: -kv[1])),
        "by_group": dict(sorted(by_group.items(), key=lambda kv: -kv[1])),
        # Rejected before slicing: counted in the total, with no result.
        "not_sliced": max(0, (generated - analysed) - with_code),
        "focus_removed": getattr(search_result, "focus_rejected", 0),
    }


# ----------------------------------------------------------------------
# Geometry of a priced surface
# ----------------------------------------------------------------------
def drawing_points(res) -> Optional[list]:
    """The surface of ``res`` as the DXF export draws it, ``[(x, y), ...]``,
    or None for a surface class this does not know.

    v0.1.341 (D337) -- moved word for word from ``ogr_core.dxf.exporter``,
    which asked these classes itself and so imported the engine:

    * a composite or a weak-layer surface, its drawing vertices;
    * a circle, the base of its slices (``_surface_arc``);
    * a polyline, its vertices.

    Not :func:`surface_path`: that takes the first left point and every
    right point of the slices, this every left point and the last right
    one, which agree only when the slices are contiguous.
    """
    from .surface import CompositeSurface, SlipCircle, WeakLayerSurface
    surf = res.surface
    if isinstance(surf, (CompositeSurface, WeakLayerSurface)):
        # v0.1.111 — asked BEFORE the circle branch, and asked of the
        # surface rather than reconstructed here: a composite has a centre
        # and a radius, so ``_surface_arc`` would happily draw the arc it
        # was clipped from — a curve that dives below the floor of the
        # model and was never analysed. Exporting that into a drawing
        # someone builds from is worse than exporting nothing.
        # v0.1.252 (D251) — a weak-layer surface likewise: it has no
        # ``polyline``, so until that version the export raised
        # AttributeError, before ``saveas``, and wrote no file.
        return surf.drawing_vertices()
    if isinstance(surf, SlipCircle):
        return _surface_arc(surf, res)
    if hasattr(surf, "polyline"):
        return [(v.x, v.y) for v in surf.polyline.vertices]
    return None


def _surface_kind(surf) -> str:
    """The serialised type of ``surf`` (``"circle"``, ``"composite"``...),
    which the export note names in the reader's language, else its class
    name. v0.1.433 (D411) -- the class name alone made the note's declared
    kind translate nothing (review of 0.1.433)."""
    try:
        kind = surf.to_dict().get("type")
    except Exception:  # noqa: BLE001 -- a class without a serial form
        kind = None
    return str(kind) if kind else type(surf).__name__


def critical_drawings(results) -> list:
    """The critical surface of each method in ``results`` (a mapping
    ``method_id -> SearchResult``) as the DXF export takes it:
    ``(method_id, points, fos)``, or ``(method_id, None, fos, kind)`` for
    one :func:`drawing_points` cannot draw (its serialised type, else its
    class name). A method without a critical
    surface is left out (v0.1.341, D337)."""
    out = []
    for mid, sr in (results or {}).items():
        crit = getattr(sr, "critical", None)
        if crit is None:
            continue
        pts = drawing_points(crit)
        if pts is None:
            out.append((mid, None, crit.fos, _surface_kind(crit.surface)))
        else:
            out.append((mid, pts, crit.fos))
    return out


def _surface_arc(circle, result, segments: int = 72):
    """The slip surface as it was actually analysed.

    Drawing the whole circle would be misleading — only the arc below
    ground is the failure surface — so the slice base points are used
    directly. They ARE the analysed surface, which also means the drawing
    cannot drift from the calculation by re-deriving the geometry.
    ``segments`` is kept for the fallback path, where no slices are
    available and the arc has to be reconstructed from the circle.
    """
    slices = list(getattr(result, "slices", []) or [])
    if slices:
        pts = [(s.base_x_left, s.base_y_left) for s in slices]
        last = slices[-1]
        pts.append((last.base_x_right, last.base_y_right))
        return pts
    # Fallback: no slices, so rebuild the arc from the circle itself
    pts = []
    x0 = circle.centre_x - circle.radius
    x1 = circle.centre_x + circle.radius
    for i in range(segments + 1):
        x = x0 + (x1 - x0) * i / segments
        dx = x - circle.centre_x
        under = circle.radius ** 2 - dx * dx
        if under < 0:
            continue
        pts.append((x, circle.centre_y - math.sqrt(under)))
    return pts


def surface_path(res) -> list:
    """The base of the slices, left to right, as ``[(x, y), ...]``: the
    surface the engine priced, tension-crack truncation and composite
    segments included. Empty when the result has no slices."""
    slices = getattr(res, "slices", None)
    if not slices or len(slices) == 0:
        return []
    # v0.1.408 (D383) — a spilled surface keeps this in memory: Add Query
    # asks it of every surface on every mouse move
    if type(slices) is SpilledSlices:
        return slices.trace()
    pts = [(slices[0].base_x_left, slices[0].base_y_left)]
    for s in slices:
        pts.append((s.base_x_right, s.base_y_right))
    return pts


def distance_to_path(x: float, y: float, path) -> float:
    """Shortest distance from (x, y) to the polyline ``path``."""
    best = math.inf
    for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, (
            (x - ax) * dx + (y - ay) * dy) / L2))
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


def surfaces_through_point(search_result, x: float, y: float,
                           tolerance: float) -> list:
    """``[(distance, result)]`` of the valid surfaces whose PRICED base
    passes within ``tolerance`` of (x, y), lowest factor of safety first.

    v0.1.201 — the interface measured a circle to the WHOLE circle, so a
    point on the upper, unsliced side of a circle counted as crossing it,
    and a weak-layer surface (no radius, no polyline) never matched."""
    hits = []
    for r in search_result.valid():
        path = surface_path(r)
        if len(path) < 2:
            continue
        d = distance_to_path(x, y, path)
        if d <= tolerance:
            hits.append((d, r))
    hits.sort(key=lambda t: t[1].fos)
    return hits


def surface_area(res) -> float:
    """Area of the sliding mass, sum of width x mean height of the slices.

    v0.1.201 — the interface's result table divided each weight by a unit
    weight the slice does not have, so every row read 0.0.

    v0.1.408 (D383) — a spilled surface keeps the value this function gave
    when it was spilled: the result table asks it of every surface."""
    slices = getattr(res, "slices", None)
    if type(slices) is SpilledSlices:
        return slices.area
    return sum(s.width * s.height for s in (slices or []))


def slip_centre(surface_dict) -> Optional[tuple]:
    """``(x, y)`` of the slip centre a serialised surface was drawn about,
    or None for a surface that has none.

    A circle and a composite carry their centre. v0.1.252 (D251) — and a
    weak-layer surface clipped from either belongs to the centre of its
    BASE, for the reason a composite belongs to its circle's: the grid
    generated it there. Until this version it had no centre for the
    interpretation window and for ``minimum_per_centre``, so a clipped
    surface could not be picked on the grid that produced it. ONE answer,
    read by both, instead of a type test in each.
    """
    sd = surface_dict or {}
    if sd.get("type") == "weak_layer":
        sd = sd.get("base") or {}
    if sd.get("type", "circle") not in ("circle", "composite"):
        return None
    cx, cy = sd.get("centre_x"), sd.get("centre_y")
    if cx is None or cy is None:
        return None
    return cx, cy


def slip_circle(surface_dict) -> Optional[tuple]:
    """``(x, y, radius)`` of the circle a serialised surface was drawn
    about, by :func:`slip_centre`'s rule, or None for a surface that has
    none (v0.1.419, D361: the tables printed «nan» or «0.00» for it)."""
    sd = surface_dict or {}
    if sd.get("type") == "weak_layer":
        sd = sd.get("base") or {}
    centre = slip_centre(sd)
    radius = sd.get("radius")
    if centre is None or radius is None:
        return None
    return centre[0], centre[1], radius


def minimum_per_centre(search_result) -> list:
    """The lowest-factor surface at each slip-centre grid point, plus every
    surface that has no centre (a non-circular search has no grid of
    centres, and the reference documents the option for a circular Grid
    Search only). Over the VALID surfaces, as the interface draws them."""
    best: dict = {}
    loose: list = []
    for r in search_result.valid():
        centre = slip_centre(r.surface.to_dict())
        if centre is None:
            loose.append(r)
            continue
        cx, cy = centre
        key = (round(cx, 6), round(cy, 6))
        if key not in best or r.fos < best[key].fos:
            best[key] = r
    return list(best.values()) + loose


def reported_value(search_result, r, caption=None) -> Optional[float]:
    """The number of surface ``r`` under what ``search_result`` reports
    (``reported_caption``): its Ky on a Ky run, its Newmark displacement in
    metres on a Newmark run, its factor otherwise; None when the surface has
    no such number (no Ky below the ceiling, no displacement) (v0.1.450,
    D423).

    ``caption``, the run's, when the caller already has it: asking it reads
    ``critical``, which walks every surface of the run, so a caller that asks
    it per surface is quadratic (the review of 0.1.450 measured 8 s for a
    grid of 4746 surfaces, 0.012 s asked once)."""
    from .reported import KY, NEWMARK, reported_caption

    if caption is None:
        caption = reported_caption(search_result)
    details = getattr(r, "details", None) or {}
    value = (details.get("ky") if caption == KY
             else details.get("newmark_displacement") if caption == NEWMARK
             else r.fos)
    if value is None or not math.isfinite(value):
        return None
    return float(value)


def critical_per_centre(search_result, caption=None) -> list:
    """The surface each slip centre of a grid is drawn by, under what the run
    reports (v0.1.450, D423): the lowest factor of the centre
    (:func:`minimum_per_centre`, bit for bit) on a run of factors; the lowest
    Ky on a Ky run; and the largest Newmark displacement on a Newmark run.
    Over the valid surfaces, the ones without the run's number left out, plus
    every surface that has no centre and has the number.

    The report's figure contoured the lowest factor of each centre on every
    run, and marked as the critical centre the one of the lowest Ky. On a
    Newmark run the displacement is taken as it is, and not as the one of
    the centre's lowest Ky: the two are the same surface for a rigid block
    (its displacement does not grow with its Ky; Newmark 1965), but not with
    upslope sliding allowed, where the displacement is a net one (D437).
    ``minimum_per_centre`` itself does not change: Minimum Surfaces and the
    API's view read it (D438). ``caption`` as in :func:`reported_value`:
    asked once here, never per surface."""
    from .reported import KY, NEWMARK, reported_caption

    if caption is None:
        caption = reported_caption(search_result)
    if caption not in (KY, NEWMARK):
        return minimum_per_centre(search_result)
    larger = caption == NEWMARK
    best: dict = {}
    value_of: dict = {}
    loose: list = []
    for r in search_result.valid():
        value = reported_value(search_result, r, caption)
        if value is None:
            continue
        centre = slip_centre(r.surface.to_dict())
        if centre is None:
            loose.append(r)
            continue
        key = (round(centre[0], 6), round(centre[1], 6))
        if key not in best or (value > value_of[key] if larger
                               else value < value_of[key]):
            best[key], value_of[key] = r, value
    return list(best.values()) + loose


def slope_intercepts(res) -> tuple:
    """``(x_left, x_right)`` where the surface meets the ground.

    v0.1.201 — ``to_dict().get("x_left") or x_range()`` treated an
    intercept at x = 0.0 as missing and fell back to the circle's centre
    minus its radius.

    v0.1.447 (D424) — the rule moved to the core word for word
    (``ogr_core.geometry.surface_ends.surface_x_ends``), so the report's
    «Global Minimums» block asks the same one."""
    from ogr_core.geometry.surface_ends import surface_x_ends
    return surface_x_ends(res.surface)


def sf_along_slope(search_result, use_left: bool = True,
                   use_right: bool = True, bins: Optional[int] = None):
    """Factor of safety against position along the slope: every valid
    surface's factor at its two ground intercepts; with ``bins``, the
    MINIMUM within each of ``bins`` equal intervals. ``(xs, fos)``."""
    pts: list = []
    for ev in search_result.valid():
        try:
            xl, xr = slope_intercepts(ev)
        except Exception:  # noqa: BLE001 - a surface without a range
            continue
        if use_left and xl is not None:
            pts.append((float(xl), ev.fos))
        if use_right and xr is not None:
            pts.append((float(xr), ev.fos))
    if not pts:
        return [], []
    if not bins or bins < 1:
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]
    x_lo = min(p[0] for p in pts)
    x_hi = max(p[0] for p in pts)
    width = (x_hi - x_lo) or 1.0
    best: dict = {}
    for x, f in pts:
        i = min(bins - 1, int((x - x_lo) / width * bins))
        if i not in best or f < best[i][1]:
            best[i] = (x, f)
    ordered = [best[i] for i in sorted(best)]
    return [p[0] for p in ordered], [p[1] for p in ordered]


# ----------------------------------------------------------------------
# Per-slice numbers of the method
# ----------------------------------------------------------------------
# v0.1.468 (D453) -- the rule lives in the core, where the PDF report can ask
# it too (it printed forces under its kPa): one copy, imported here.
from ogr_core.result_rows import face_rows, per_slice, slice_stress  # noqa: E402,F401


def base_parameter(slice_, name: str):
    """A strength parameter of the material the slice base cuts, from
    ``strength.params``, where every registered model keeps them."""
    mat = getattr(slice_, "material", None)
    if mat is None or getattr(mat, "strength", None) is None:
        return None
    return mat.strength.params.get(name)


def slice_rows(result) -> list:
    """One dict per slice with the METHOD's numbers.

    Forces in kN/m and stresses in kPa: ``sigma_n = N / l`` with N the
    method's base normal force, ``sigma_n_eff = sigma_n - u``, ``tau_f``
    the shear strength per unit base length and ``tau_m = tau_f / F`` (the
    reference's "Shear Stress"; its Ej_2 table: 31.082 / 1.11442 =
    27.8907).

    v0.1.220 (D211) -- F is the factor the method's equilibrium was solved
    at (``checks.equilibrium_fos``): the mobilised shear is the equilibrium
    shear stress, tau = s/F (Duncan, Wright & Brandon 2014, Eqs. 6.1-6.2).
    It is the reported factor for every method but Janbu Corrected, which
    solves at F0 and reports f0*F0."""
    from .checks import equilibrium_fos

    rows = []
    fos = getattr(result, "fos", None)
    if fos:
        fos = equilibrium_fos(result)
    for s in getattr(result, "slices", None) or []:
        i = getattr(s, "index", None)
        sn = slice_stress(result, "base_normal_force", s)
        tf = slice_stress(result, "base_shear_strength", s)
        u = getattr(s, "pore_pressure", 0.0) or 0.0
        rows.append({
            "index": i,
            "x_centre": s.x_centre,
            "width": s.width,
            "base_length": s.base_length,
            "base_angle_deg": math.degrees(s.base_angle),
            "height": s.height,
            "weight": s.weight,
            # v0.1.242 (D226a) -- the permanent-action factor already in
            # ``weight``: 1.0 without a design standard.
            "weight_factor": getattr(s, "weight_factor", 1.0),
            "pore_pressure": u,
            "surface_pressure": getattr(s, "surface_pressure", 0.0),
            "base_normal_force": per_slice(result, "base_normal_force", i),
            "driving_shear": per_slice(result, "base_shear_force", i),
            "sigma_n": sn,
            "sigma_n_eff": None if sn is None else sn - u,
            "tau_f": tf,
            "tau_m": (tf / fos if tf is not None and fos else None),
            "material": (s.material.name if getattr(s, "material", None)
                         else None),
            "cohesion": base_parameter(s, "cohesion"),
            "friction_angle": base_parameter(s, "friction_angle"),
        })
    return rows
