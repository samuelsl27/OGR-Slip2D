# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the runs that are not one analysis say: the transient factor-of-safety
history and the back analysis, and the runner when it cannot build a search,
with stable codes (v0.1.352, D335). The drawdown level sweep is the core's
(``ogr_core.statistics.messages``).

Their warnings and ``notes["error"]`` were English sentences; each is a code
here with that English, so the sentence is the one the engine wrote, and the
interface translates it. A reason the seepage solver gave is nested with its
own code (``ogr_fem2d.messages``).

Codes are ``run.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, coded

TRANSIENT_NO_STAGES = "run.transient_no_stages"
TRANSIENT_NO_FIELD = "run.transient_no_field"
TRANSIENT_INITIAL_NOT_CONVERGED = "run.transient_initial_not_converged"
TRANSIENT_NO_COUPLING = "run.transient_no_coupling"
BACK_ONLY_FOR = "run.back_only_for"
BACK_TARGET_POSITIVE = "run.back_target_positive"
BACK_SEARCH_FAILED = "run.back_search_failed"
BACK_NONE = "run.back_none"
BACK_ENVELOPE = "run.back_envelope"
BACK_ENVELOPE_LEFT_OUT = "run.back_envelope_left_out"
BACK_COMPOSITE_LEFT_OUT = "run.back_composite_left_out"
BACK_SUPPORTS = "run.back_supports"
SWEEP_ENABLE_DRAWDOWN = "run.sweep_enable_drawdown"
SEARCH_NOT_BUILT = "run.search_not_built"

#: The sentence a back-analysed surface carries when its envelope did not
#: settle (``back_analysis.ENVELOPE_NOT_SETTLED_NOTE`` reads it from here).
ENVELOPE_NOT_SETTLED = (
    "The strength envelope depends on the normal stress, and on at least one "
    "slice the stress it is read at did not settle on the stress the method "
    "resolves at the target factor of safety; the surface was left out rather "
    "than back-analysed at a point the method does not use.")

RUN_NOTES = {s.code: s for s in (
    MessageSpec(TRANSIENT_NO_STAGES,
                "This project has no transient groundwater stages, so there is "
                "no factor-of-safety history to compute. Turn on Transient "
                "Groundwater and define the stages first."),
    MessageSpec(TRANSIENT_NO_FIELD,
                "The groundwater analysis produced no field: {why}"),
    MessageSpec(TRANSIENT_INITIAL_NOT_CONVERGED,
                "The initial steady state of the transient analysis did not "
                "converge, so every stage starts from an unconverged field "
                "(see each stage's initial-state warning)."),
    MessageSpec(TRANSIENT_NO_COUPLING,
                "No material takes its pore pressure from the finite-element "
                "seepage field, so the stage factors of safety would ignore the "
                "computed water pressures entirely."),
    MessageSpec(BACK_ONLY_FOR,
                "Back analysis is only available for {methods}.",
                kinds=(("methods", "method_list"),)),
    MessageSpec(BACK_TARGET_POSITIVE,
                "The target factor of safety must be positive."),
    MessageSpec(BACK_SEARCH_FAILED, "search failed: {error}"),
    MessageSpec(BACK_NONE,
                "No surface could be back-analysed. Check the target factor of "
                "safety and the search settings."),
    MessageSpec(BACK_ENVELOPE, ENVELOPE_NOT_SETTLED),
    MessageSpec(BACK_ENVELOPE_LEFT_OUT,
                "{n} surface(s) were left out: " + ENVELOPE_NOT_SETTLED),
    MessageSpec(BACK_COMPOSITE_LEFT_OUT,
                "{n} composite surface(s) were left out: back analysis is "
                "written in the circular form of the method, which does not "
                "hold on the straight stretches of a composite. Turn "
                "Composite Surfaces off to back-analyse this model, and read "
                "the result as being about circular surfaces only."),
    MessageSpec(SEARCH_NOT_BUILT, "Could not build the search for: {methods}",
                kinds=(("methods", "method_list"),)),
    MessageSpec(BACK_SUPPORTS,
                "The back analysis supports {methods}, not {method}.",
                kinds=(("methods", "method_list"), ("method", "method_id"))),
    MessageSpec(SWEEP_ENABLE_DRAWDOWN,
                "Enable Rapid Drawdown analysis in Project Settings > "
                "Groundwater > Advanced first."),
)}


def run_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(RUN_NOTES, code, **args)
