# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the statistical runs say -- the probabilistic analysis (Global Minimum
and Overall Slope) and the sensitivity sweep -- with stable codes (v0.1.353,
D335).

Their notes, warnings, errors and lines (``notes``, ``note_lines``,
``switch_lines``) were English sentences with their values baked in, and the
status bar, the notes panel and the Statistics window showed them as they
came. Each is a code here with that English, so the sentence is the one the
run wrote -- the tests, the API and the bank read it -- and the interface
translates it:

* a sentence about one method is ``ogr_core.messages.method_note`` (the
  "<method id>: " the runs always put in front), with the sentence nested;
* the sentences a run joins with "; " into one headline are a list
  (:data:`JOINED`), so each keeps its own code;
* a switch sentence nests its head (who answered for what, in the caller's
  words) and the stretches it names;
* the causes a method lost its samples to are counted labels, each with its
  code, or the engine's own reason identifier as it was.

Codes are ``stat.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, as_nested, coded, parts

S = "stat."

# --- what a run refuses before sampling -------------------------------------
ENABLE_STATISTICS = S + "enable_statistics"
DEFINE_VARIABLE = S + "define_variable"
NO_DETERMINISTIC_CRITICAL = S + "no_deterministic_critical"
FACTORED_COPY = S + "factored_copy"
NO_VARIABLES = S + "no_variables"
NO_DETERMINISTIC_RESULT = S + "no_deterministic_result"
NO_METHOD_SELECTED = S + "no_method_selected"
NO_RANGE = S + "no_range"
VARS_NONE = S + "vars_none"
VARS_NOT_SAMPLED = S + "vars_not_sampled"
VARS_NOT_SWEPT = S + "vars_not_swept"
VAR_ORPHAN = S + "var_orphan"

# --- why one method was not sampled -------------------------------------------
NO_METHOD = S + "no_method"
NO_DETERMINISTIC = S + "no_deterministic"
NO_SURFACE = S + "no_surface"
WEAK_COMPOSITE_OFF = S + "weak_composite_off"
COMPOSITE_OFF = S + "composite_off"
TYPE_WEAK = S + "type_weak"
TYPE = S + "type"
NOT_ITSELF = S + "not_itself"
NOT_ITSELF_CASE = S + "not_itself_case"
NO_SAMPLE = S + "no_sample"
ALL_FAILED_GM = S + "all_failed_gm"
ALL_FAILED_OS = S + "all_failed_os"
GM_FAILED = S + "gm_failed"
OS_FAILED = S + "os_failed"

# --- the critical probabilistic surface ---------------------------------------
CPS_STEERED = S + "cps_steered"
CPS_KY = S + "cps_ky"
CPS_TOO_FEW = S + "cps_too_few"
CPS_NOT_IN_EVERY_SAMPLE = S + "cps_not_in_every_sample"

# --- what the samples answered for (D89, D85) ---------------------------------
SPAN = S + "span"
SPAN_IN = S + "span_in"
CASE_NONE = S + "case_none"
CASE_LAYERS = S + "case_layers"
CASE_IN = S + "case_in"
CASE_TEXT_NONE = S + "case_text_none"
CASE_TEXT_LAYERS = S + "case_text_layers"
SWITCH_MASS = S + "switch_mass"
SWITCH_MASS_BELOW = S + "switch_mass_below"
SWITCH_CASE = S + "switch_case"
SWITCH_CASE_BELOW = S + "switch_case_below"
HEAD_GM_MASS = S + "head_gm_mass"
HEAD_GM_CASE = S + "head_gm_case"
HEAD_OS_MASS = S + "head_os_mass"
HEAD_SENS_MASS = S + "head_sens_mass"
HEAD_SENS_CASE = S + "head_sens_case"

# --- how a sample was lost, counted --------------------------------------------
RAISED = S + "raised"
NO_RESULT = S + "no_result"
CODE_120 = S + "code_120"
CODE_112 = S + "code_112"
CODE_101 = S + "code_101"
INADMISSIBLE = S + "inadmissible"
UNSTATED = S + "unstated"
NO_ADMISSIBLE = S + "no_admissible"
NO_CRITICAL = S + "no_critical"
COUNTED = S + "counted"
REASONS = S + "reasons"

#: Sentences joined with "; " into one headline (``notes["warning"]``, the
#: roll-up of ``notes["error"]``): the list, each with its own code.
JOINED = S + "joined"

_WHY_SKIPPED = ("which a statistical run cannot re-evaluate; this method "
                "was skipped.")
_NO_PF = "so this method has no probability of failure."
_BELOW = ("; {below} of the {total} with a factor below 1 are among them, "
          "and the probability of failure counts them")

STAT_NOTES = {s.code: s for s in (
    MessageSpec(ENABLE_STATISTICS,
                "Enable a probabilistic or sensitivity analysis in Project "
                "Settings first."),
    MessageSpec(DEFINE_VARIABLE, "Define at least one random variable first."),
    MessageSpec(NO_DETERMINISTIC_CRITICAL,
                "The deterministic analysis produced no critical surface. "
                "Check the model and the search settings."),
    MessageSpec(FACTORED_COPY,
                "The project handed to this statistical run is the "
                "design-factored copy an analysis computes on, not the model: "
                "its samples would overwrite factored values with unfactored "
                "ones and be factored a second time. Pass the model itself; "
                "every sample is prepared like the analysis."),
    MessageSpec(NO_VARIABLES,
                "No random variables defined. At least one model input "
                "parameter must be given a statistical distribution."),
    MessageSpec(NO_DETERMINISTIC_RESULT,
                "No deterministic result: run the regular analysis first so "
                "the global minimum surface is known."),
    MessageSpec(NO_METHOD_SELECTED, "No analysis method selected."),
    MessageSpec(NO_RANGE,
                "No variable has a range: enter a relative minimum and "
                "maximum for at least one parameter."),
    MessageSpec(VARS_NONE,
                "none of the {n} random variables matches the model: {keys}"),
    MessageSpec(VARS_NOT_SAMPLED,
                "{n} of the {total} random variables no longer match the "
                "model and were not sampled: {keys}"),
    MessageSpec(VARS_NOT_SWEPT,
                "{n} of the {total} random variables no longer match the "
                "model and were not swept: {keys}"),
    MessageSpec(VAR_ORPHAN, "no longer matches the model: {key}"),
    MessageSpec(NO_METHOD,
                "not a registered analysis method, so it was not computed."),
    MessageSpec(NO_DETERMINISTIC,
                "the deterministic run left no critical surface for this "
                "method, so there is nothing to re-evaluate."),
    MessageSpec(NO_SURFACE,
                "The deterministic result carries no serialised surface, so "
                "there is nothing to re-evaluate."),
    MessageSpec(WEAK_COMPOSITE_OFF,
                "The deterministic critical surface runs along a weak layer "
                "from a composite one, and Composite Surfaces is off in the "
                "project the samples run on, so that surface cannot be formed "
                "again; this method was skipped."),
    MessageSpec(COMPOSITE_OFF,
                "The deterministic critical surface is a composite one, and "
                "Composite Surfaces is off in the project the samples run on, "
                "so that surface cannot be formed again; this method was "
                "skipped."),
    MessageSpec(TYPE_WEAK,
                "The deterministic critical surface is of type '{stype}' on a "
                "base of type '{btype}', " + _WHY_SKIPPED),
    MessageSpec(TYPE,
                "The deterministic critical surface is of type '{stype}', "
                + _WHY_SKIPPED),
    MessageSpec(NOT_ITSELF,
                "The deterministic critical surface does not re-evaluate to "
                "itself on the project the samples run on (it answers for x "
                "from {x0:.2f} to {x1:.2f}, {there_type}, instead of x from "
                "{hx0:.2f} to {hx1:.2f}, {home_type}); a setting that decides "
                "the sliding mass, such as Composite Surfaces or a surface "
                "filter, differs between the two runs, so this method was "
                "skipped."),
    MessageSpec(NOT_ITSELF_CASE,
                "The deterministic critical surface does not re-evaluate to "
                "itself on the project the samples run on (it answers for the "
                "same mass as {there}, instead of {home}); a setting that "
                "decides the weak-layer case, such as the weak-layer handling "
                "or a suppressed weak layer, differs between the two runs, so "
                "this method was skipped."),
    MessageSpec(NO_SAMPLE, "no sample was drawn, " + _NO_PF),
    MessageSpec(ALL_FAILED_GM,
                "all {n} samples failed on the deterministic critical "
                "surface, " + _NO_PF + " Reasons: {reasons}."),
    MessageSpec(ALL_FAILED_OS,
                "all {n} samples produced no valid surface, " + _NO_PF
                + " Reasons: {reasons}."),
    MessageSpec(GM_FAILED,
                "{failed} of {n} samples could not be evaluated; check the "
                "variable ranges."),
    MessageSpec(OS_FAILED, "{failed} of {n} searches produced no valid "
                           "surface."),
    MessageSpec(CPS_STEERED,
                "No critical probabilistic surface: this search steers on the "
                "factors of safety it computes, so it analyses different "
                "surfaces in every sample and none of them has a probability "
                "of failure of its own. It is computed for the Grid, Slope, "
                "Path and Block searches."),
    MessageSpec(CPS_KY,
                "No critical probabilistic surface: the search minimised the "
                "critical seismic coefficient Ky, and the critical "
                "probabilistic surface is defined on the factor of safety."),
    MessageSpec(CPS_TOO_FEW,
                "No critical probabilistic surface: too few valid samples to "
                "estimate one."),
    MessageSpec(CPS_NOT_IN_EVERY_SAMPLE,
                "No critical probabilistic surface: no surface of the search "
                "had a factor of safety in every sample, and a probability of "
                "failure counted over some of the samples only is not "
                "comparable with the others."),
    MessageSpec(SPAN, "x from {x0:.2f} to {x1:.2f}"),
    MessageSpec(SPAN_IN, "x from {x0:.2f} to {x1:.2f} in {n}"),
    MessageSpec(CASE_NONE, "on no weak layer"),
    MessageSpec(CASE_LAYERS, "along weak layers over {spans}"),
    MessageSpec(CASE_IN, "{case} in {n}"),
    MessageSpec(CASE_TEXT_NONE, "a {stype} on no weak layer"),
    MessageSpec(CASE_TEXT_LAYERS, "a {stype} along weak layers over {spans}"),
    MessageSpec(SWITCH_MASS,
                "{head} ({where}), not for its own (x from {x0:.2f} to "
                "{x1:.2f}).",),
    MessageSpec(SWITCH_MASS_BELOW,
                "{head} ({where}), not for its own (x from {x0:.2f} to "
                "{x1:.2f})" + _BELOW + ".",),
    MessageSpec(SWITCH_CASE, "{head} ({where}), not for its own ({own}).",),
    MessageSpec(SWITCH_CASE_BELOW,
                "{head} ({where}), not for its own ({own})" + _BELOW + ".",),
    MessageSpec(HEAD_GM_MASS,
                "{n} of {total} samples answered for another sliding mass of "
                "the deterministic circle"),
    MessageSpec(HEAD_GM_CASE,
                "{n} of {total} samples answered for another weak-layer case "
                "of the deterministic surface"),
    MessageSpec(HEAD_OS_MASS,
                "{n} of {total} samples had the deterministic circle as their "
                "critical surface, answering for another sliding mass"),
    MessageSpec(HEAD_SENS_MASS,
                "The sweep of {label} answered for another sliding mass of the "
                "deterministic circle at {n} of {total} points, from {lo:g} "
                "to {hi:g}"),
    MessageSpec(HEAD_SENS_CASE,
                "The sweep of {label} answered for another weak-layer case of "
                "the deterministic surface at {n} of {total} points, from "
                "{lo:g} to {hi:g}"),
    MessageSpec(RAISED, "raised {exc}"),
    MessageSpec(NO_RESULT, "no result"),
    MessageSpec(CODE_120, "-120 tensile stress"),
    MessageSpec(CODE_112, "-112 m-alpha"),
    MessageSpec(CODE_101, "inadmissible (-101)"),
    MessageSpec(INADMISSIBLE, "inadmissible"),
    MessageSpec(UNSTATED, "unstated"),
    MessageSpec(NO_ADMISSIBLE, "no admissible surface"),
    MessageSpec(NO_CRITICAL, "no critical surface"),
    MessageSpec(COUNTED, "{label} x {n}"),
    MessageSpec(REASONS, "{reasons}"),
    MessageSpec(JOINED, "{items}", seps=(("items", "; "),)),
)}


def stat_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(STAT_NOTES, code, **args)


def joined(*notes) -> Coded:
    """``notes`` joined with "; ", as the runs always joined them, each kept
    with its code. A note that is itself a join contributes its items, so a
    headline that grows sentence by sentence stays one flat list."""
    items = []
    for note in notes:
        code, args, _text = parts(note)
        if code == JOINED:
            items.extend(args.get("items") or [])
        else:
            items.append(as_nested(note))
    return stat_note(JOINED, items=items)
