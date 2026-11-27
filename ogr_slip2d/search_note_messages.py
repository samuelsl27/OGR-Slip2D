# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The notes a search writes about its own run, with stable codes
(v0.1.349, D335).

A search says what it threw away and why: surfaces the slicer refused, ends
off the ground, bases in the air, a run that found nothing, the surfaces the
user drew by hand, what Optimize Surfaces could not use, a pool that fell
back to one process, and why a given surface was not analysed at all. Each
line is a code here with the English template the engine wrote, format
specs included, so the sentence is byte for byte the one the tests and the
bank read. ``run_analysis`` puts the method in front
(``ogr_core.messages.method_note``).

Shapes the engine assembled from English pieces are whole templates per
variant: a count with its "s" (``MessageSpec.one``), the reasons a run lists
(nested, in a list field joined with "; " -- ``MessageSpec.seps``), a clause
that is there or not (nested, or ``NOTHING``), the reason a surface has no
factor of safety (nested with the code D314 gave it). The singular of five
of them says "1 surface were discarded" or "1 circle that do not cut",
which is what the engine wrote; the English is not changed here, only coded.

Codes are ``search.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, as_nested, coded, nested

# --- what the slicer and the guards refused -----------------------------------
UNSLICEABLE = "search.unsliceable"
UNSLICEABLE_CIRCLE = "search.unsliceable_circle"
OUTSIDE_MODEL = "search.outside_model"
ORPHAN_MATERIAL = "search.orphan_material"
END_OFF_GROUND = "search.end_off_ground"
END_BELOW = "search.end_below"
END_ABOVE = "search.end_above"
BASE_ABOVE_GROUND = "search.base_above_ground"
ON_MODEL_EDGE = "search.on_model_edge"
WEAK_LAYER_STEEP = "search.weak_layer_steep"

# --- a run that found nothing ---------------------------------------------------
NO_VALID = "search.no_valid"
NO_VALID_PRICED = "search.no_valid_priced"
NO_VALID_REFUSED = "search.no_valid_refused"
R_SLOPE_LIMITS = "search.refused.slope_limits"
R_SLOPE_LIMITS_ONE = "search.refused.slope_limits_one"
R_SLOPE_LIMITS_TWO = "search.refused.slope_limits_two"
R_SLOPE_LIMITS_MANY = "search.refused.slope_limits_many"
R_MISSES_GROUND = "search.refused.misses_ground"
# v0.1.445 (D420) -- the circles that left the External Boundary (the -103)
R_LEAVES_EXTERNAL = "search.refused.leaves_external"
# v0.1.495 (D434) -- the circles of a grid centre with no valid radius (-1000)
R_NO_VALID_RADIUS = "search.refused.no_valid_radius"
R_LEFT_MODEL = "search.refused.left_model"
R_ORPHAN = "search.refused.orphan"
R_UNSLICEABLE = "search.refused.unsliceable"
R_END_OFF = "search.refused.end_off"
R_BASE_ABOVE = "search.refused.base_above"
R_FOCUS = "search.refused.focus"

# --- the surfaces the user drew -------------------------------------------------
USER_CIRCULAR_SKIPPED = "search.user_circular_skipped"
USER_NO_RESULT = "search.user_no_result"
USER_NO_RESULT_FILTERED = "search.user_no_result_filtered"
# v0.1.367 (D346) -- the reason, when the search knows it, before the filters
USER_MISSES_GROUND = "search.user_misses_ground"
USER_REFUSED = "search.user_refused"
F_SLOPE_LIMITS = "search.filter.slope_limits"
F_MIN_AREA = "search.filter.min_area"
F_MIN_AREA_DEFAULT = "search.filter.min_area_default"
F_MIN_DEPTH = "search.filter.min_depth"
F_MIN_ELEVATION = "search.filter.min_elevation"
USER_NO_FACTOR = "search.user_no_factor"
# v0.1.444 (D402) -- what the polylines have had since v0.1.427
USER_INADMISSIBLE = "search.user_inadmissible"
USER_REPORTED = "search.user_reported"
# v0.1.427 (D357) -- the hand-drawn NON-circular surfaces, named by their two
# ends: a polyline has no centre and no radius to be told apart by
USER_PL_SKIPPED = "search.user_polyline_skipped"
USER_PL_NO_RESULT = "search.user_polyline_no_result"
USER_PL_NO_RESULT_FILTERED = "search.user_polyline_no_result_filtered"
USER_PL_REFUSED = "search.user_polyline_refused"
USER_PL_NO_FACTOR = "search.user_polyline_no_factor"
USER_PL_REPORTED = "search.user_polyline_reported"
USER_PL_END_MOVED = "search.user_polyline_end_moved"
USER_PL_SNAP_REFUSED = "search.user_polyline_snap_refused"
USER_PL_NOT_A_SURFACE = "search.user_polyline_not_a_surface"
USER_PL_INADMISSIBLE = "search.user_polyline_inadmissible"
# v0.1.465 (D357) -- Sarma's data per vertex of a stored polyline
USER_PL_SARMA_REFUSED = "search.user_polyline_sarma_refused"
USER_PL_SARMA_UNUSED = "search.user_polyline_sarma_unused"
NO_REASON = "search.no_reason"
NO_REASON_STOP = "search.no_reason_stop"

# --- Optimize Surfaces ----------------------------------------------------------
OPTIMISATION_LOST = "search.optimisation_lost"
O_NO_RESULT = "search.opt.no_result"
O_NO_FACTOR = "search.opt.no_factor"
O_INADMISSIBLE = "search.opt.inadmissible"
OPT_UNKNOWN_TECHNIQUE = "search.opt.unknown_technique"
OPT_THREE_VERTICES = "search.opt.three_vertices"
OPT_START_REFUSED = "search.opt.start_refused"
#: v0.1.493 (D436) -- the start refused for a reason the search knows: the
#: reason, by the rule of the door of one surface (``given_refusal``)
OPT_START_REFUSED_BECAUSE = "search.opt.start_refused_because"
OPT_START_INVALID = "search.opt.start_invalid"
OPT_SNAP_FAILED = "search.opt.snap_failed"
OPT_SUMMARY = "search.opt.summary"

# --- the process pool -----------------------------------------------------------
PARALLEL_FALLBACK = "search.parallel_fallback"

# --- why a given surface was not analysed (``evaluate_surface``) ----------------
#: Keyed by the refusal the search records (``_last_refusal``); the default
#: is the one with no refusal recorded.
REFUSED = "search.refused_surface."
REFUSED_DEFAULT = "search.refused_surface.default"
#: v0.1.446 (D403) -- no refusal recorded, and filters active on the run that
#: can remove the surface: named, as the run names them for a hand-drawn one,
#: instead of "the surface does not cut the model" of a surface that does
GIVEN_NO_RESULT_FILTERED = "search.given_no_result_filtered"

_DISCARDED_OUTSIDE = (
    " discarded because a slice base fell outside the External Boundary, "
    "where there is no soil to give it strength. This is not a slice-count "
    "problem: the surfaces left the model. Check the extent of the External "
    "Boundary against the search area.")
_DISCARDED_ORPHAN = (
    " discarded because a slice base fell in a region whose material no "
    "longer exists. Assign that region another material (Properties > "
    "Assign Materials).")
_DISCARDED_END = (
    " discarded because an end was not on the ground surface: {parts}. This "
    "is not a slice-count problem: the first and last vertices of a polyline "
    "have to lie on the ground.")
_DISCARDED_BASE = (
    " discarded because the base rose above the ground surface between the "
    "two ends, so part of the sliding mass would be in the air. This is not "
    "a slice-count problem: more slices cannot put the base back under the "
    "ground. It happens where a surface follows a line that lies on the "
    "ground, such as a weak layer or a Block Search polyline along an "
    "exposed bench, and the line sits a little above the ground there.")
_EDGE_A = (" sat on the edge of the model, within the resolution of its own "
           "geometry, and ")
_EDGE_B = (" taken as being inside it. Nothing was discarded for this. It "
           "happens where a slip surface daylights exactly on a vertex of the "
           "External Boundary.")
_PRICED = (" priced and gave none; the census of invalid surfaces has their "
           "codes.")
_OUTSIDE_LIMITS = "{n} with an end outside the Slope Limits"
_SKIPPED_A = (" not analysed: the Surface Type of this analysis is "
              "Non-Circular, and one analysis carries one Surface Type. Set "
              "Surface Options -> Surface Type = Circular to include ")
_USER_AT = ("The user-defined surface at centre ({x:.4g}, {y:.4g}) with radius "
            "{r:.4g} ")
_NO_RESULT = ("produced no result, so it is not in the reported population. ")
_SKIPPED_PL = (" not analysed: the Surface Type of this analysis is Circular, "
               "and one analysis carries one Surface Type. Set Surface "
               "Options -> Surface Type = Non-Circular to include ")
#: A hand-drawn polyline is named by its number in the list (as the window's
#: manager numbers them), its vertices and its two ends: the ends alone give
#: two surfaces drawn from the same crest to the same toe the same sentence,
#: and a run keeps each sentence once.
_PL_AT = ("The user-defined non-circular surface {k} ({nv} vertices, from "
          "({x0:.4g}, {y0:.4g}) to ({x1:.4g}, {y1:.4g})) ")
_REFUSAL = "the surface was not analysed: "

#: ``(refusal, text)``: the English of ``BaseSearch._REFUSAL_TEXT`` until
#: v0.1.349, keyed by the value the search records.
_REFUSALS = (
    ("end_below_ground",
     _REFUSAL + "its first or last vertex is below the ground, so it meets "
     "the slope only once (the reference's error -101) and its end slice "
     "would have a vertical face with no strength. Put both ends on the "
     "ground surface."),
    ("end_above_ground",
     _REFUSAL + "its first or last vertex is above the ground. Put both ends "
     "on the ground surface."),
    ("outside_model",
     _REFUSAL + "a slice base fell outside the External Boundary, where there "
     "is no soil."),
    ("orphan_material",
     _REFUSAL + "a slice base fell in a region whose material no longer "
     "exists."),
    ("base_above_ground",
     _REFUSAL + "between its two ends its base rises above the ground "
     "surface, so part of the mass would be in the air."),
    ("leaves_soil",
     _REFUSAL + "it dips below the External Boundary."),
    ("unsliceable",
     _REFUSAL + "the slicer refused it (more mandatory cuts than slices, a "
     "degenerate width or a tension crack it could not place)."),
    ("outside_slope_limits",
     _REFUSAL + "an end daylights outside the Slope Limits."),
    ("misses_ground",
     _REFUSAL + "the circle does not cut the ground surface twice (the "
     "reference's error -101)."),
    # v0.1.445 (D420) -- what ``_candidate_surfaces`` dropped without a word:
    # the two halves of the reference's -103 (the floor, the side), and three
    # that are not it. A circle has its own words for the floor: "it dips
    # below the External Boundary" is the polyline's, and names no remedy.
    ("leaves_external",
     _REFUSAL + "between its two crossings with the ground the circle runs "
     "outside the External Boundary, so part of the mass would not be soil "
     "(the reference's error -103). Composite Surfaces makes a circle follow "
     "the base of the External Boundary instead."),
    ("reverse_curvature_side",
     _REFUSAL + "the circle turns back above its centre (reverse curvature), "
     "and the vertical tension crack that would end it falls outside the "
     "model: the arc leaves through a side of the External Boundary (the "
     "reference's error -103)."),
    # The box is on two panels of Surface Options only, though every circle
    # obeys it (Auto Refine, the user's circles, one surface's door): the
    # sentence names where it can be found.
    ("reverse_curvature_discarded",
     _REFUSAL + "the circle turns back above its centre (reverse curvature), "
     "and \"Create tension crack for reverse curvature\" is off in Surface "
     "Options (the Grid Search and Slope Search panels), so such a circle "
     "is discarded."),
    ("reverse_curvature_no_crack",
     _REFUSAL + "the circle turns back above its centre (reverse curvature), "
     "and there is no place for the vertical tension crack that would end "
     "it."),
    ("tension_crack_zone",
     _REFUSAL + "the sliding mass lies entirely within the zone of the "
     "Tension Crack boundary, where the soil has no strength, so there is no "
     "slip surface to analyse."),
    # v0.1.446 (D403) -- the ceiling on the base of a weak-layer clip, said
    # until now only by the run's own note, so the door of one surface said
    # it "does not cut the model" and a hand-drawn one blamed a filter
    # v0.1.493 (D436) -- a focus object of the search excludes the surface:
    # Optimize asks the focus before it evaluates, and said "the slicer
    # refused it whole" of a start the focus had removed
    ("outside_focus",
     _REFUSAL + "a focus object of the search excludes it."),
    ("weak_layer_steep",
     _REFUSAL + "a weak layer clips it, and the base of one of its slices is "
     "steeper than the \"Maximum base angle on weak-layer clips\" of Project "
     "Settings > Advanced."),
)

SEARCH_NOTES = {s.code: s for s in (
    MessageSpec(UNSLICEABLE,
                "{n} of the {total} surfaces this search formed could not be "
                "sliced and were dropped. Every vertex of a surface is a "
                "mandatory slice boundary, so a surface needs at least as many "
                "slices as it has segments, and every material boundary and "
                "water table it crosses adds one more; this analysis uses "
                "{num_slices}. The surfaces lost are the ones that cross the "
                "most layers, so this is not an even thinning of the search. "
                "Use more slices, or fewer vertices per surface."),
    MessageSpec(UNSLICEABLE_CIRCLE,
                "{n} of the {total} surfaces this search formed could not be "
                "sliced and were dropped. Each circle is converted into "
                "{vertices} vertices, which is {segments} straight segments, "
                "and this analysis uses {num_slices} slices; every vertex is a "
                "mandatory slice boundary, and material boundaries and the "
                "water table take slices of their own. The surfaces lost are "
                "the ones that cross the most layers, so this is not an even "
                "thinning of the search. Use fewer vertices or more slices."),
    MessageSpec(OUTSIDE_MODEL, "{n} surfaces were" + _DISCARDED_OUTSIDE,
                one="{n} surface were" + _DISCARDED_OUTSIDE, count="n"),
    MessageSpec(ORPHAN_MATERIAL, "{n} surfaces were" + _DISCARDED_ORPHAN,
                one="{n} surface were" + _DISCARDED_ORPHAN, count="n"),
    MessageSpec(END_OFF_GROUND, "{n} polyline surfaces were" + _DISCARDED_END,
                one="{n} polyline surface were" + _DISCARDED_END, count="n",
                seps=(("parts", "; "),)),
    MessageSpec(END_BELOW,
                "{n} with an end below the ground, which would have given its "
                "end slice a vertical face with no strength (the reference "
                "calls such a surface -101: one intersection with the slope)"),
    MessageSpec(END_ABOVE, "{n} with an end above it"),
    MessageSpec(BASE_ABOVE_GROUND, "{n} surfaces were" + _DISCARDED_BASE,
                one="{n} surface were" + _DISCARDED_BASE, count="n"),
    MessageSpec(ON_MODEL_EDGE, "{n} slice bases" + _EDGE_A + "were" + _EDGE_B,
                one="{n} slice base" + _EDGE_A + "was" + _EDGE_B, count="n"),
    MessageSpec(WEAK_LAYER_STEEP,
                "A surface clipped by a weak layer was discarded: its steepest "
                "slice base is {angle:.1f} deg, past the {limit:.0f} deg "
                "ceiling in Project Settings > Advanced."),
    MessageSpec(NO_VALID,
                "No trial surface gave a valid factor of safety ({total} "
                "generated).{priced}{refused} Anything else was refused before "
                "it could be priced, for reasons this search does not record.",
                group_by=("priced", "refused")),
    MessageSpec(NO_VALID_PRICED, " {n} were" + _PRICED,
                one=" {n} was" + _PRICED, count="n"),
    MessageSpec(NO_VALID_REFUSED, " Refused before pricing: {parts}.",
                seps=(("parts", "; "),)),
    MessageSpec(R_SLOPE_LIMITS, _OUTSIDE_LIMITS),
    MessageSpec(R_SLOPE_LIMITS_ONE, _OUTSIDE_LIMITS + " [{lo:g}, {hi:g}]"),
    MessageSpec(R_SLOPE_LIMITS_TWO,
                _OUTSIDE_LIMITS + " [{lo1:g}, {hi1:g}] and [{lo2:g}, {hi2:g}]"),
    MessageSpec(R_SLOPE_LIMITS_MANY, _OUTSIDE_LIMITS + " {windows}"),
    MessageSpec(R_MISSES_GROUND,
                "{n} circles that do not cut the ground twice",
                one="{n} circle that do not cut the ground twice", count="n"),
    MessageSpec(R_LEAVES_EXTERNAL,
                "{n} circles that leave the External Boundary between their "
                "crossings with the ground",
                one="{n} circle that leaves the External Boundary between its "
                    "crossings with the ground", count="n"),
    MessageSpec(R_NO_VALID_RADIUS,
                "{n} circles of grid centres with no valid radius",
                one="{n} circle of a grid centre with no valid radius",
                count="n"),
    MessageSpec(R_LEFT_MODEL, "{n} that left the model"),
    MessageSpec(R_ORPHAN, "{n} that crossed a region with no material"),
    MessageSpec(R_UNSLICEABLE, "{n} that the slicer refused"),
    MessageSpec(R_END_OFF, "{n} with an end off the ground"),
    MessageSpec(R_BASE_ABOVE, "{n} with the base above the ground"),
    MessageSpec(R_FOCUS, "{n} removed by the focus objects"),
    MessageSpec(USER_CIRCULAR_SKIPPED,
                "{n} user-defined circular surfaces were" + _SKIPPED_A + "them.",
                one="{n} user-defined circular surface was" + _SKIPPED_A
                    + "it.",
                count="n"),
    MessageSpec(USER_NO_RESULT,
                _USER_AT + _NO_RESULT + "No surface filter is active on this "
                "run, so the circle does not meet the ground twice inside the "
                "External Boundary."),
    MessageSpec(USER_NO_RESULT_FILTERED,
                _USER_AT + _NO_RESULT + "Filters active on this run that can "
                "remove it: {filters}."),
    MessageSpec(USER_MISSES_GROUND,
                _USER_AT + _NO_RESULT + "It does not cut the ground surface "
                "twice inside the External Boundary, so there is no sliding "
                "mass to analyse."),
    MessageSpec(USER_REFUSED,
                _USER_AT + _NO_RESULT + "The search says why: {reason}"),
    MessageSpec(F_SLOPE_LIMITS, "Slope Limits {windows}"),
    MessageSpec(F_MIN_AREA, "Minimum Area {value:g}"),
    MessageSpec(F_MIN_AREA_DEFAULT,
                "Minimum Area {value:g} (the search's default, not a setting "
                "of this model)"),
    MessageSpec(F_MIN_DEPTH, "Minimum Depth {value:g}"),
    MessageSpec(F_MIN_ELEVATION, "Minimum Elevation {value:g}"),
    MessageSpec(USER_NO_FACTOR, _USER_AT + "has no factor of safety: {reason}"),
    # A factor the post-analysis checks rejected (m-alpha, tension): in the
    # population, never the critical surface, and said so. The words of the
    # polyline's note; ``{factor}``, never ``{fos}`` (the Spanish terms test
    # reads «FoS» whatever its case).
    MessageSpec(USER_INADMISSIBLE,
                _USER_AT + "has a factor of safety of {factor:.4g}, but the "
                "post-analysis checks reject it, so it cannot be the critical "
                "surface: {reason}"),
    MessageSpec(USER_REPORTED,
                "The surface reported for this method is one the user defined "
                "by hand (centre ({x:.4g}, {y:.4g}), radius {r:.4g}), not one "
                "the search generated."),
    MessageSpec(USER_PL_SKIPPED,
                "{n} user-defined non-circular surfaces were" + _SKIPPED_PL
                + "them.",
                one="{n} user-defined non-circular surface was" + _SKIPPED_PL
                    + "it.",
                count="n"),
    MessageSpec(USER_PL_NO_RESULT,
                _PL_AT + _NO_RESULT + "No surface filter is active on this "
                "run, and the search recorded no reason."),
    MessageSpec(USER_PL_NO_RESULT_FILTERED,
                _PL_AT + _NO_RESULT + "Filters active on this run that can "
                "remove it: {filters}."),
    MessageSpec(USER_PL_REFUSED,
                _PL_AT + _NO_RESULT + "The search says why: {reason}"),
    MessageSpec(USER_PL_NO_FACTOR,
                _PL_AT + "has no factor of safety: {reason}"),
    MessageSpec(USER_PL_REPORTED,
                "The surface reported for this method is one the user defined "
                "by hand (non-circular surface {k}: {nv} vertices, from "
                "({x0:.4g}, {y0:.4g}) to ({x1:.4g}, {y1:.4g})), not one the "
                "search generated."),
    MessageSpec(USER_PL_END_MOVED,
                _PL_AT + "has an end off the External Boundary: ({ox:g}, "
                "{oy:g}) was moved to the nearest point of it, ({nx:g}, "
                "{ny:g}), {d:g} away, before it was analysed."),
    MessageSpec(USER_PL_SNAP_REFUSED,
                _PL_AT + "was not analysed: moving its ends onto the External "
                "Boundary would make x stop increasing. Give ends on the "
                "ground surface."),
    # A stored polyline that fails the rule every door asks
    # (``checked_points``): only a hand-edited file or a script can store one.
    MessageSpec(USER_PL_NOT_A_SURFACE,
                _PL_AT + "was not analysed: it is not a slip surface the "
                "engine can slice, because it does not advance in x from one "
                "end to the other (a step back in x, a vertical segment, "
                "fewer than two points or a coordinate that is not a "
                "number). Delete it and draw it again."),
    # A factor the post-analysis checks rejected (m-alpha, tension): in the
    # population, never the critical surface, and said so.
    MessageSpec(USER_PL_INADMISSIBLE,
                _PL_AT + "has a factor of safety of {factor:.4g}, but the "
                "post-analysis checks reject it, so it cannot be the critical "
                "surface: {reason}"),
    # v0.1.465 (D357) -- a datum of Sarma's method per vertex that the rule
    # refuses (only a hand-edited file or a script can store one): the
    # polyline is analysed with the others, and this says so.
    MessageSpec(USER_PL_SARMA_REFUSED,
                _PL_AT + "carries {count} datum (data) of Sarma's method per "
                "vertex that the rule refuses (not an interior vertex, an "
                "angle that is not a number or is horizontal, a cohesion "
                "without its friction angle or out of range): its faces took "
                "the policy and the face strength of the settings."),
    # one per polyline, not only for the reported surface (the review of
    # v0.1.465): a datum a crack cut off another polyline went unsaid.
    MessageSpec(USER_PL_SARMA_UNUSED,
                _PL_AT + "has {count} datum (data) of Sarma's method given at "
                "vertices that did not reach the surface analysed (a crack "
                "cut the vertex off): its faces took the policy and the face "
                "strength of the settings."),
    MessageSpec(NO_REASON, "no reason declared"),
    MessageSpec(NO_REASON_STOP, "no reason declared."),
    MessageSpec(OPTIMISATION_LOST,
                "Optimize Surfaces walked {walked} surface(s) and {lost} came "
                "back unusable: {parts}. Those walks contributed nothing, and "
                "what is reported is what the search itself found.",
                seps=(("parts", "; "),)),
    MessageSpec(O_NO_RESULT, "{n} could not evaluate the starting surface at all"),
    MessageSpec(O_NO_FACTOR,
                "{n} started from a surface the method has no factor of safety "
                "for ({reason})"),
    MessageSpec(O_INADMISSIBLE, "{n} ended on an inadmissible surface"),
    MessageSpec(OPT_UNKNOWN_TECHNIQUE,
                "Unknown optimisation technique {technique!r}: it has to be one "
                "of {choices}.",
                kinds=(("choices", "technique_list"),)),   # v0.1.433
    MessageSpec(OPT_THREE_VERTICES,
                "Optimisation needs at least three vertices: there is nothing "
                "to move on a two-point surface."),
    MessageSpec(OPT_START_REFUSED,
                "The starting surface could not be evaluated: the slicer "
                "refused it whole. A polyline that rises above the ground "
                "anywhere is refused entirely, so a vertex a ten-thousandth "
                "over the profile is enough."),
    MessageSpec(OPT_START_REFUSED_BECAUSE,
                "The optimisation cannot start from this surface, because "
                "{reason}"),
    MessageSpec(OPT_START_INVALID,
                "The starting surface was evaluated and has no factor of "
                "safety: {reason}. That is not missing data, it is the "
                "answer."),
    MessageSpec(OPT_SNAP_FAILED,
                "The snapped surface could not be evaluated; the unsnapped one "
                "is reported."),
    MessageSpec(OPT_SUMMARY,
                "{initial:.4f} → {final:.4f} ({improvement:+.4f}) in "
                "{iterations} evaluations, {accepted} accepted"),
    MessageSpec(PARALLEL_FALLBACK,
                "The Grid Search was to be split across {workers} processes "
                "and ran in one, because the process pool failed "
                "({error_type}: {error}). The result is the same; only the "
                "time is not."),
    MessageSpec(REFUSED_DEFAULT,
                "the surface does not cut the model, so there is nothing to "
                "price."),
    MessageSpec(GIVEN_NO_RESULT_FILTERED,
                "the surface was not analysed, and no reason was recorded; "
                "filters active that can remove it: {filters}."),
) + tuple(MessageSpec(REFUSED + key, text) for key, text in _REFUSALS)}


def search_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(SEARCH_NOTES, code, **args)


def nested_search_note(code: str, **args) -> dict:
    """One of these notes as the value of another one's field."""
    return as_nested(search_note(code, **args))


def refusal(key) -> Coded:
    """Why a given surface was not analysed, for the refusal ``key`` the
    search recorded (None or an unknown one: the default)."""
    code = REFUSED + str(key)
    return search_note(code if code in SEARCH_NOTES else REFUSED_DEFAULT)


def reason_of(result, fallback: str = NO_REASON) -> dict:
    """Why ``result`` has no factor of safety, nested with its code: its
    failure, else its admissibility note (the order
    ``interpretation.invalid_reason`` reads them in, with the codes D314 gave
    them), else ``fallback``."""
    text = getattr(result, "error_message", None) or ""
    if text:
        return nested(getattr(result, "message_code", "") or "",
                      getattr(result, "message_args", None) or {}, text)
    text = getattr(result, "admissibility_note", None) or ""
    if text:
        return nested(getattr(result, "note_code", "") or "",
                      getattr(result, "note_args", None) or {}, text)
    return nested_search_note(fallback)


#: The empty clause: a part of the sentence that is not there.
NOTHING = {"code": "", "args": {}, "text": ""}
