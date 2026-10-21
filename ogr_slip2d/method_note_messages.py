# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The notes about one method's reported surface, with stable codes
(v0.1.348, D335).

``run_analysis`` says, once per method, what the surface it reports leans on:
a near-zero m-alpha, a daylight too steep for the slicing, an inter-slice
inclination that was the closest sample rather than a root, slices with no
strength, a centre on the edge of the grid, the seismic modes, the supports
that are reversed or put no force on it. Each line is
``"<method id>: <note>"`` (:func:`ogr_core.messages.method_note`), and each
note is a code here, with the English template the engine wrote and its
format specs, so the sentence is byte for byte the one the tests and the
bank read.

Three shapes the engine assembled from English pieces:

* a count glued to a plural ("inclination" / "inclinations", "was" /
  "were") is two whole templates, through ``MessageSpec.one``. The plural of
  three of the lambda sentences says "inclinations was discarded", which is
  what the engine wrote; the English is not changed here, only coded;
* the m-alpha sentence is a frame and four clauses, each a code of its own
  and nested, because its 4 x 2 x 2 x 2 combinations are one fact each;
* the supports that put no force list their reasons, each a fragment with
  its own code, in a list field (``ogr_core.messages.is_nested_list``).

Codes are ``method.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, as_nested, coded

# --- the run --------------------------------------------------------------
UNREGISTERED = "method.unregistered"

# --- the inter-slice inclination (Spencer, GLE) ---------------------------
LAMBDA_FALLBACK = "method.lambda_fallback"
LAMBDA_NOT_CLOSED = "method.lambda_not_closed"
LAMBDA_LOST_BUDGET = "method.lambda_lost_budget"
LAMBDA_LOST_OVERFLOW = "method.lambda_lost_overflow"
LAMBDA_LOST_STALL = "method.lambda_lost_stall"
LAMBDA_LOST_INADMISSIBLE = "method.lambda_lost_inadmissible"
LAMBDA_REFINED = "method.lambda_refined"
LAMBDA_RECOVERED = "method.lambda_recovered"

# --- the surface ------------------------------------------------------------
DAYLIGHT_STEEP = "method.daylight_steep"
M_ALPHA_MARGIN = "method.m_alpha_margin"
M_ALPHA_WHERE = "method.m_alpha_where"
M_ALPHA_CLEARS = "method.m_alpha_clears"
M_ALPHA_BELOW = "method.m_alpha_below"
M_ALPHA_INFLATES = "method.m_alpha_inflates"
M_ALPHA_NONPOSITIVE = "method.m_alpha_nonpositive"
M_ALPHA_ADVICE_COMPLETE = "method.m_alpha_advice_complete"
M_ALPHA_ADVICE_FORCE = "method.m_alpha_advice_force"
M_ALPHA_ADVICE_MOMENT = "method.m_alpha_advice_moment"
M_ALPHA_ADVICE_UNKNOWN = "method.m_alpha_advice_unknown"
ZERO_STRENGTH = "method.zero_strength"
GRID_EDGE = "method.grid_edge"

# --- the seismic modes ------------------------------------------------------
SEISMIC_KH_REPLACED = "method.seismic_kh_replaced"
SEISMIC_NO_KY = "method.seismic_no_ky"
NEWMARK_NO_RECORD = "method.newmark_no_record"
NEWMARK_UNUSABLE = "method.newmark_unusable"
NEWMARK_POLARITY = "method.newmark_polarity"

# --- the supports -----------------------------------------------------------
SUPPORT_REVERSED = "method.support_reversed"
SUPPORT_REVERSED_ANY = "method.support_reversed_any"
SUPPORT_UNPRICED = "method.support_unpriced"
SUPPORT_NONE_REACHED = "method.support_none_reached"
SUPPORT_ONLY_ONE_SILENT = "method.support_only_one_silent"
SUPPORT_NONE_FORCED = "method.support_none_forced"
SUPPORT_SOME_SILENT = "method.support_some_silent"
SUPPORT_SHEAR_FAILED = "method.support_shear_failed"
SUPPORT_BOND_FAILED = "method.support_bond_failed"
SUPPORT_FAILURE_ONE = "method.support_failure_one"
SUPPORT_FAILURE_MANY = "method.support_failure_many"
#: A reason a support puts no force, as one fragment of the list
#: (``part``, with its count) and as the whole clause when it is the only
#: support (``bare``). Keyed by the reason the engine records.
PART = "method.support_part."
BARE = "method.support_bare."
#: The reason whose fragment carries the exception that building the bond
#: profile raised (v0.1.163, D95): its own codes, with that name.
RAISED = "_raised"

_COMPLETE = " Spencer and GLE/Morgenstern-Price"
_FALLBACK_TAIL = (" because its inner iteration used its whole budget of "
                  "passes while still improving, so the limit that decided "
                  "this answer belongs to the solver rather than to the "
                  "slope. A looser convergence tolerance spends fewer passes "
                  "per inclination and may bracket it.")
_OVERFLOW_TAIL = (" because the inter-slice thrust of its inner iteration ran "
                  "past {limit:g} times the total force the sliding mass has "
                  "to work with, which is a runaway and not a solution of "
                  "anything.")
_STALL_TAIL = (" because its inner iteration stopped improving for {passes} "
               "passes, in its factor and in its inter-slice thrust alike, and "
               "the relaxation rescue could not settle it either, so the limit "
               "that decided this answer belongs to the solver rather than to "
               "the slope.")
_INADMISSIBLE_TAIL = (" discarded because one of its two equilibrium branches "
                      "had no admissible solution there at all: the factor of "
                      "safety it was iterating towards stopped being finite "
                      "and positive, so that inclination could not be "
                      "compared with its neighbours.")
_REFINED_TAIL = (" sampled between the last one that solved and the first one "
                 "that did not, which is where a crossing hidden by a lost "
                 "sample would be.")
_RECOVERED_TAIL = (" put back after being set aside for an inter-slice thrust "
                   "in net tension: the crossing lay among them, so the factor "
                   "reported is a solved root rather than the closest sampled "
                   "inclination.")
_ZERO_TAIL = ("): the effective normal stress the strength envelope was read "
              "at was negative, and the envelope has no strength at zero "
              "stress. The factor of safety counts no resistance on ")
_REVERSED = ("Support '{name}' has its head at ({hx:.2f}, {hy:.2f}), on the "
             "stable side of the reported surface, and its tail at ({tx:.2f}, "
             "{ty:.2f}), inside the sliding mass. The head is the end at the "
             "slope FACE: the stripping length L_i is measured from it, the "
             "pullout length L_o from the tail, and the force under "
             "'{orientation}' is placed from the axis read head to tail. Drawn "
             "this way round all three are reversed. Check which end was "
             "clicked first before quoting this factor.")
_LEFT_OUT = (" A support left out lowers no number and raises none, so ")
_NO_REINFORCEMENT = (" This factor of safety is the one for the slope with no "
                     "reinforcement at all.")
#: The two reasons deliberately NOT in ``UNCONTRIBUTING``: every entry there
#: completes "the support puts no force on the surface", and these say the
#: opposite -- the support is in the equilibrium, priced at less than it
#: declares. Sharing the table would have bought one loop at the price of a
#: sentence that contradicts itself. v0.1.162, defect D98 (``_SHEAR``); the
#: second one v0.1.163, defect D95 (``_BOND``), its counterpart: the profile
#: would not build and the type HAS an envelope at zero effective stress, so
#: the support was priced off that instead. Its own sentence rather than a
#: share of the first, because what was lost is different -- there one
#: vector, here every term that depends on the stress state along the
#: reinforcement.
_SHEAR = (" contributed only {their} axial capacity: shear_at raised "
          "{errors}, so the shear {they} declare{s} was not counted. That is a "
          "defect in the support type rather than a property of the model, "
          "and the factor of safety is the one for less reinforcement than "
          "the model carries.")
_BOND = ("That is a defect in the support type rather than a property of the "
         "model.")

#: The reasons a support puts no force, in the order the engine lists them:
#: ``(reason, one, many, bare)``. Until v0.1.348 this was
#: ``support_integration._UNCONTRIBUTING_PHRASES``, with ``%d`` where this
#: has ``{n}``; ``uncontributing_support_notes`` reads it from here.
#:
#: How each reason reads: singular, plural, and once more with no count
#: at all for the lone-support case, where "None of the 1 supports
#: placed" would be plainly ungrammatical. Ordered most actionable
#: first, so the five that describe BROKEN INPUT come before the three
#: that describe a legitimate calculation decision (v0.1.313 added
#: ``SUPPORT_NO_LENGTH`` to the first group, D313). v0.1.161 put
#: ``SUPPORT_NOT_PRICEABLE`` at the head of that first group: it is the
#: only one that means the analysis could not READ the model, and it
#: carries its own text on the result besides (defect D94). v0.1.163 put
#: ``SUPPORT_BOND_PROFILE_NO_FORCE`` right behind it, in the same group
#: and for the same reason: a profile that will not build is a defect in
#: the type, not a property of the slope (defect D95).
#:
#: The reasons are the values of ``support_integration.SUPPORT_*``; a test
#: holds the two together.
UNCONTRIBUTING = (
    ("not_priceable",
     "{n} could not be priced at all",
     "{n} could not be priced at all",
     "it could not be priced at all"),
    ("bond_profile_no_force",
     "{n} could not be given a bond profile, and its type prices nothing "
     "without one",
     "{n} could not be given a bond profile, and their type prices nothing "
     "without one",
     "it could not be given a bond profile, and its type prices nothing "
     "without one"),
    ("unknown_type",
     "{n} names a support class this build does not have",
     "{n} name a support class this build does not have",
     "it names a support class this build does not have"),
    ("no_length",
     "{n} has no length: its head and tail coincide",
     "{n} have no length: their head and tail coincide",
     "it has no length: its head and tail coincide"),
    ("no_crest",
     "{n} is drawn with both ends at one elevation, and its type measures "
     "its diagram from the upper one",
     "{n} are drawn with both ends at one elevation, and their type "
     "measures its diagram from the upper one",
     "it is drawn with both ends at one elevation, and its type measures "
     "its diagram from the upper one"),
    ("no_capacity",
     "{n} develops no capacity where it crosses",
     "{n} develop no capacity where they cross",
     "it develops no capacity where it crosses"),
    ("no_slice",
     "{n} crosses it at a point that falls in no slice",
     "{n} cross it at a point that falls in no slice",
     "it crosses that surface at a point that falls in no slice"),
    ("no_crossing",
     "{n} does not cross it",
     "{n} do not cross it",
     "it does not cross that surface"),
)
#: The exception class, pasted onto the fragment of the bond-profile reason.
#: It does not fit the table -- every entry there takes one count and
#: nothing else -- and it cannot be dropped either: naming the bug is the
#: whole reason the reasons carry a suffix (v0.1.163, defect D95). Since
#: v0.1.348 the fragment with it is a code of its own (``RAISED``).
_RAISED_SUFFIX = " (building it raised {errors})"
#: That fragment's reason.
BOND_NO_FORCE = "bond_profile_no_force"


def _parts():
    out = []
    for reason, one, many, bare in UNCONTRIBUTING:
        # A reason whose English is the same for one support and for many
        # ("could not be priced at all") has one template: a singular equal
        # to its plural would be the same dictionary key twice, with two
        # translations it cannot hold.
        if one == many:
            out.append(MessageSpec(PART + reason, many))
        else:
            out.append(MessageSpec(PART + reason, many, one=one, count="n"))
        out.append(MessageSpec(BARE + reason, bare))
        if reason == BOND_NO_FORCE:
            out.append(MessageSpec(PART + reason + RAISED,
                                   many + _RAISED_SUFFIX,
                                   one=one + _RAISED_SUFFIX, count="n"))
            out.append(MessageSpec(BARE + reason + RAISED,
                                   bare + _RAISED_SUFFIX))
    return tuple(out)


METHOD_NOTES = {s.code: s for s in (
    MessageSpec(UNREGISTERED,
                "'{method}' is not a registered analysis method, so it was "
                "not computed. Available: {available}.",
                kinds=(("available", "method_list"),)),
    MessageSpec(LAMBDA_FALLBACK,
                "no inclination of the inter-slice forces makes the force and "
                "the moment factors of safety agree, so the factor reported "
                "is the closest sampled inclination rather than a solved one: "
                "its two factors differ by {residual:.3g}, against a "
                "convergence tolerance of {tolerance:.3g}."),
    MessageSpec(LAMBDA_NOT_CLOSED,
                "an inclination of the inter-slice forces where the force and "
                "the moment factors of safety cross WAS found, and refining "
                "it did not close the gap: the two factors still differ by "
                "{residual:.3g} against a convergence tolerance of "
                "{tolerance:.3g}, with the interval narrowed to {width:.3g}. "
                "The factor reported is the one at that inclination, not a "
                "solved root."),
    MessageSpec(LAMBDA_LOST_BUDGET,
                "and {n} inclinations was discarded" + _FALLBACK_TAIL,
                one="and {n} inclination was discarded" + _FALLBACK_TAIL,
                count="n"),
    MessageSpec(LAMBDA_LOST_OVERFLOW,
                "and {n} inclinations was discarded" + _OVERFLOW_TAIL,
                one="and {n} inclination was discarded" + _OVERFLOW_TAIL,
                count="n"),
    MessageSpec(LAMBDA_LOST_STALL,
                "and {n} inclinations was discarded" + _STALL_TAIL,
                one="and {n} inclination was discarded" + _STALL_TAIL,
                count="n"),
    MessageSpec(LAMBDA_LOST_INADMISSIBLE,
                "and {n} inclinations were" + _INADMISSIBLE_TAIL,
                one="and {n} inclination was" + _INADMISSIBLE_TAIL,
                count="n"),
    MessageSpec(LAMBDA_REFINED,
                "The calibrated grid of inclinations bracketed nothing, so "
                "{n} further inclinations were" + _REFINED_TAIL,
                one="The calibrated grid of inclinations bracketed nothing, "
                    "so {n} further inclination was" + _REFINED_TAIL,
                count="n"),
    MessageSpec(LAMBDA_RECOVERED,
                "The calibrated grid bracketed nothing until {n} inclinations "
                "were" + _RECOVERED_TAIL,
                one="The calibrated grid bracketed nothing until {n} "
                    "inclination was" + _RECOVERED_TAIL,
                count="n"),
    MessageSpec(DAYLIGHT_STEEP,
                "The critical surface daylights at {steepest:.1f} deg from the "
                "horizontal, which is too steep for a fixed number of slices "
                "to resolve: its factor of safety depends on that number. It "
                "was computed with {num_slices} slices. Re-run with more and "
                "compare before quoting it."),
    MessageSpec(M_ALPHA_MARGIN,
                "The reported surface has m_alpha down to "
                "{worst:.4f}{where}{tail}.{effect}{advice}",
                group_by=("where", "tail", "effect", "advice")),
    MessageSpec(M_ALPHA_WHERE, " on a base at {angle:.1f} deg"),
    MessageSpec(M_ALPHA_CLEARS,
                ", which clears the {limit} limit by {margin:.4f}"),
    MessageSpec(M_ALPHA_BELOW, ", below the {limit} limit"),
    MessageSpec(M_ALPHA_INFLATES,
                " That divides the normal force on that base by {worst:.4f}, "
                "inflating it {factor:.1f}-fold."),
    MessageSpec(M_ALPHA_NONPOSITIVE,
                " That denominator is zero or negative, so the normal force "
                "on that base is meaningless rather than merely large."),
    MessageSpec(M_ALPHA_ADVICE_COMPLETE,
                " This method satisfies force AND moment equilibrium, so "
                "there is no more complete one to check it against; what a "
                "base this steep costs it is the conditioning of the base "
                "normal, not the equilibrium it solves. Vary the number of "
                "slices, and compare against the other complete-equilibrium "
                "method, which differs from it only in the interslice force "
                "function."),
    MessageSpec(M_ALPHA_ADVICE_FORCE,
                " A force-equilibrium method is least reliable there, and "
                "this value is the Bishop denominator: the one this method "
                "actually divides by carries its own interslice inclination. "
                "Compare against a complete-equilibrium method —" + _COMPLETE
                + " — before quoting it."),
    MessageSpec(M_ALPHA_ADVICE_MOMENT,
                " A method of moments is not reliable there. Compare against "
                "a complete-equilibrium method —" + _COMPLETE + " — before "
                "quoting it."),
    MessageSpec(M_ALPHA_ADVICE_UNKNOWN,
                " Compare against a complete-equilibrium method —" + _COMPLETE
                + " — before quoting it."),
    MessageSpec(ZERO_STRENGTH,
                "{n} slices entered with zero shear strength (slices {shown}"
                + _ZERO_TAIL + "those bases.",
                one="{n} slice entered with zero shear strength (slice "
                    "{shown}" + _ZERO_TAIL + "that base.",
                count="n"),
    MessageSpec(GRID_EDGE,
                "The critical centre lies on the edge of the search grid "
                "({edges}; grid x {x0:g} to {x1:g}, y {y0:g} to {y1:g}). A "
                "minimum on the boundary is the best of what was searched, "
                "not necessarily the lowest one: widen the grid on that side "
                "and re-run before quoting it."),
    MessageSpec(SEISMIC_KH_REPLACED,
                "the project applies a horizontal seismic coefficient of "
                "{kh:g}, and the critical coefficient replaces it rather than "
                "adding to it. Ky is solved over kh from zero."),
    MessageSpec(SEISMIC_NO_KY,
                "{unanswered} of {valid} surfaces have no critical seismic "
                "coefficient below {k_max:g}; they are excluded from the "
                "ranking rather than treated as strong."),
    MessageSpec(NEWMARK_NO_RECORD,
                "Newmark displacements were requested but no seismic record "
                "is selected, so no displacement was computed."),
    MessageSpec(NEWMARK_UNUSABLE,
                "the seismic record '{name}' cannot be integrated (it needs at "
                "least two samples and a positive time interval), so no "
                "displacement was computed."),
    MessageSpec(NEWMARK_POLARITY,
                "'{polarity}' is not a polarity this program knows, so the "
                "maximum of the two was used."),
    MessageSpec(SUPPORT_REVERSED, _REVERSED,
                kinds=(("orientation", "force_orientation"),)),
    MessageSpec(SUPPORT_REVERSED_ANY,
                _REVERSED.replace("'{orientation}'", "'the chosen orientation'")),
    MessageSpec(SUPPORT_UNPRICED,
                "The analysis could not price the reinforcement on the "
                "reported surface: {said}." + _LEFT_OUT + "this factor of "
                "safety is the one for the slope without it."),
    MessageSpec(SUPPORT_NONE_REACHED,
                "None of the {total} supports placed reached the reported "
                "surface: {error}. The analysis prices the surface with no "
                "reinforcement at all when that happens, so this factor of "
                "safety is the one for the slope without any of them."),
    MessageSpec(SUPPORT_ONLY_ONE_SILENT,
                "The only support placed puts no force on the reported "
                "surface: {bare}." + _NO_REINFORCEMENT),
    MessageSpec(SUPPORT_NONE_FORCED,
                "None of the {total} supports placed put any force on the "
                "reported surface: {parts}." + _NO_REINFORCEMENT),
    MessageSpec(SUPPORT_SOME_SILENT,
                "{silent} of the {total} supports placed put no force on the "
                "reported surface: {parts}." + _LEFT_OUT + "the factor of "
                "safety is the one for the model without it. Check that these "
                "are the ones meant to be left out."),
    MessageSpec(SUPPORT_SHEAR_FAILED,
                "{n} supports" + _SHEAR.format(their="their", they="they",
                                               s="", errors="{errors}"),
                one="{n} support" + _SHEAR.format(their="its", they="it",
                                                  s="s", errors="{errors}"),
                count="n"),
    MessageSpec(SUPPORT_BOND_FAILED,
                "{n} supports were priced off their zero-stress envelopes: "
                "building their bond profiles raised {errors}, so they carry "
                "less reinforcement than the model declares. " + _BOND,
                one="{n} support was priced off its zero-stress envelope: "
                    "building its bond profile raised {errors}, so it carries "
                    "less reinforcement than the model declares. " + _BOND,
                count="n"),
    MessageSpec(SUPPORT_FAILURE_ONE, "support {sid} could not be priced: {why}"),
    MessageSpec(SUPPORT_FAILURE_MANY,
                "{n} supports could not be priced: {entries}"),
) + _parts()}


def method_note_text(code: str, **args) -> Coded:
    """The note ``code`` about one method's surface, with ``args``: its
    English sentence, carrying the code and the values. The caller prefixes
    the method with :func:`ogr_core.messages.method_note`."""
    return coded(METHOD_NOTES, code, **args)


def nested_method_note(code: str, **args) -> dict:
    """One of these notes as the value of another one's field."""
    return as_nested(method_note_text(code, **args))


#: The empty clause: a field the sentence leaves out (no base angle to name).
NOTHING = {"code": "", "args": {}, "text": ""}
