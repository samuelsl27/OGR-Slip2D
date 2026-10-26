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
USER_REPORTED = "search.user_reported"
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
    MessageSpec(USER_REPORTED,
                "The surface reported for this method is one the user defined "
                "by hand (centre ({x:.4g}, {y:.4g}), radius {r:.4g}), not one "
                "the search generated."),
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
                "of {choices}."),
    MessageSpec(OPT_THREE_VERTICES,
                "Optimisation needs at least three vertices: there is nothing "
                "to move on a two-point surface."),
    MessageSpec(OPT_START_REFUSED,
                "The starting surface could not be evaluated: the slicer "
                "refused it whole. A polyline that rises above the ground "
                "anywhere is refused entirely, so a vertex a ten-thousandth "
                "over the profile is enough."),
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
