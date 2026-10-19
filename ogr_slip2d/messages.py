# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The codes of the engine's per-surface messages (v0.1.333, D314).

Why a surface has no factor of safety (``LEMResult.error_message``) and why
a converged one was judged inadmissible (``admissibility_note``), each as a
code with its values beside the English sentence. The mechanism is
``ogr_core.messages``; this is the engine's catalogue.

These codes are FINER than ``methods.base.REASON_*`` on purpose, and they do
not replace them. ``REASON_NON_PHYSICAL_FOS`` covers five different
sentences, and ``REASON_DRAWDOWN_NOT_APPLICABLE`` about ten. The reasons
group the invalid-surface census (D56) and are what the verification bank
counts, so splitting them would move both. A translation needs one template
per sentence, and that is what a code here is.

The engine writes a message through :func:`failure` or :func:`inadmissible`,
which return the sentence and its code together, so the two cannot drift
apart. ``tests/test_core_messages_v1333.py`` checks that every sentence
equals what the engine wrote before this version.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import (CORE_MESSAGES, JOIN, MessageSpec, english,
                               nested)

# -- every method ------------------------------------------------------
NO_SHEAR_STRENGTH = "lem.no_shear_strength"
NOT_CONVERGED = "lem.not_converged"
ENVELOPE_NOT_CONVERGED = "lem.envelope_not_converged"
NO_SLICES = "lem.no_slices"
ARITHMETIC_FAILURE = "lem.arithmetic_failure"
# -- Bishop, Janbu and the Ordinary Method -----------------------------
M_ALPHA_COLLAPSED = "lem.m_alpha_collapsed"
N_ALPHA_COLLAPSED = "lem.n_alpha_collapsed"
ZERO_DRIVING_MOMENT = "lem.zero_driving_moment"
ZERO_DRIVING_FORCE = "lem.zero_driving_force"
NON_PHYSICAL_FOS = "lem.non_physical_fos"
NON_PHYSICAL_FOS_ITERATION = "lem.non_physical_fos_iteration"
NON_FINITE_FOS = "lem.non_finite_fos"
NON_FINITE_FOS_ITERATION = "lem.non_finite_fos_iteration"
ACTIVE_SUPPORT_EXCEEDS_MOMENT = "lem.active_support_exceeds_moment"
ACTIVE_SUPPORT_EXCEEDS_FORCE = "lem.active_support_exceeds_force"
# -- Spencer and GLE ---------------------------------------------------
ALL_LAMBDA_DIVERGED = "lem.all_lambda_diverged"
NO_LAMBDA_BRACKET = "lem.no_lambda_bracket"
RELAXED_THRUST = "lem.relaxed_thrust"
DIVERGENT_AT_FINAL_LAMBDA = "lem.divergent_at_final_lambda"
LAMBDA_NOT_CLOSED = "lem.lambda_not_closed"
# -- the prescribed-inclination family ---------------------------------
FORCE_BALANCE_DIVERGED = "lem.force_balance_diverged"
NO_FORCE_BRACKET = "lem.no_force_bracket"
# -- the post-analysis screens (``checks.screen_verdict``) -------------
SCREEN_TENSILE_STRESS = "screen.tensile_stress"
SCREEN_M_ALPHA = "screen.m_alpha"
SCREEN_ERROR = "screen.error"
# -- rapid drawdown ----------------------------------------------------
DRAWDOWN_CURVED_ENVELOPE = "drawdown.curved_envelope"
DRAWDOWN_NO_ENVELOPE = "drawdown.no_envelope"
DRAWDOWN_STAGE1_NORMALS = "drawdown.stage1_normals"
DRAWDOWN_CAP_NORMALS = "drawdown.cap_normals"
DRAWDOWN_UNKNOWN_PROCEDURE = "drawdown.unknown_procedure"
DRAWDOWN_UNSLICEABLE_INITIAL = "drawdown.unsliceable_initial"
DRAWDOWN_UNSLICEABLE_DRAWN_DOWN = "drawdown.unsliceable_drawn_down"
DRAWDOWN_STAGE1_UNUSABLE = "drawdown.stage1_unusable"
DRAWDOWN_STAGE1_UNSTABLE = "drawdown.stage1_unstable"
DRAWDOWN_STAGE_FAILED = "drawdown.stage_failed"
DRAWDOWN_STAGE_FAILED_CAP = "drawdown.stage_failed_cap"
DRAWDOWN_STAGE_UNCONVERGED = "drawdown.stage_unconverged"
DRAWDOWN_STAGE1_INADMISSIBLE = "drawdown.stage1_inadmissible"
DECLARED_INADMISSIBLE = "drawdown.declared_inadmissible"
NO_REASON_GIVEN = "lem.no_reason_given"

_LAMBDA = ("method",)
_NAME = (("method", "label"),)

MESSAGES: dict = dict(CORE_MESSAGES)
for _spec in (
    MessageSpec(NO_SHEAR_STRENGTH,
                "Zero shear strength on the whole slip surface — factor of "
                "safety is zero"),
    MessageSpec(NOT_CONVERGED,
                "The factor of safety iteration did not converge within the "
                "maximum number of iterations"),
    MessageSpec(ENVELOPE_NOT_CONVERGED,
                "The strength envelope depends on the normal stress, and the "
                "stress it was read at did not settle on the stress the "
                "method resolved within the maximum number of passes"),
    MessageSpec(NO_SLICES, "No slices"),
    MessageSpec(ARITHMETIC_FAILURE, "Arithmetic failure: {error}"),
    MessageSpec(M_ALPHA_COLLAPSED,
                "mα collapsed to {value:.4g} at slice {slice}"),
    MessageSpec(N_ALPHA_COLLAPSED, "nα collapsed at slice {slice}"),
    MessageSpec(ZERO_DRIVING_MOMENT,
                "Zero driving moment — surface does not slide"),
    MessageSpec(ZERO_DRIVING_FORCE,
                "Zero driving force — surface does not slide"),
    MessageSpec(NON_PHYSICAL_FOS, "Non-physical factor of safety"),
    MessageSpec(NON_PHYSICAL_FOS_ITERATION,
                "Non-physical factor of safety {value:.4g} in iteration"),
    MessageSpec(NON_FINITE_FOS, "Non-finite FoS"),
    MessageSpec(NON_FINITE_FOS_ITERATION, "Non-finite FoS in iteration"),
    MessageSpec(ACTIVE_SUPPORT_EXCEEDS_MOMENT,
                "Active support force exceeds the driving moment; the factor "
                "of safety is undefined for this surface"),
    MessageSpec(ACTIVE_SUPPORT_EXCEEDS_FORCE,
                "Active support force exceeds the driving force; the factor "
                "of safety is undefined for this surface"),
    MessageSpec(ALL_LAMBDA_DIVERGED, "{method}: all sampled λ diverged",
                group_by=_LAMBDA),
    MessageSpec(NO_LAMBDA_BRACKET,
                "{method}: no λ-bracket; the nearest λ leaves F_f − F_m at "
                "{residual:.3g}", group_by=_LAMBDA),
    MessageSpec(RELAXED_THRUST,
                "{method}: no λ leaves the inter-slice thrust in net "
                "compression; the answer is reported with the criterion "
                "relaxed", group_by=_LAMBDA),
    MessageSpec(DIVERGENT_AT_FINAL_LAMBDA, "{method}: divergent at final λ",
                group_by=_LAMBDA),
    MessageSpec(LAMBDA_NOT_CLOSED,
                "{method}: the λ bracket did not close; F_f − F_m is "
                "{residual:.3g} at λ = {lam:.6g}, with the bracket at "
                "{width:.3g} after {iterations} iterations",
                group_by=_LAMBDA),
    MessageSpec(FORCE_BALANCE_DIVERGED, "{method}: force balance diverged",
                group_by=_LAMBDA, kinds=_NAME),
    MessageSpec(NO_FORCE_BRACKET,
                "{method}: no F-bracket; reporting the sampled F of smallest "
                "residual", group_by=_LAMBDA, kinds=_NAME),
    MessageSpec(SCREEN_TENSILE_STRESS,
                "tensile stress on {count} slice base(s) (error -120)"),
    MessageSpec(SCREEN_M_ALPHA, "m_alpha < {limit} on {count} slice(s)",
                group_by=("limit",)),
    MessageSpec(SCREEN_ERROR,
                "admissibility checks could not be evaluated "
                "({error_type}: {error})", group_by=("error_type",)),
    MessageSpec(DRAWDOWN_CURVED_ENVELOPE,
                "Rapid drawdown needs a linear effective envelope; material "
                "'{material}' uses '{model}'. A curved envelope cannot be "
                "carried through a procedure that rewrites c and phi on "
                "every slice.", group_by=("material", "model"),
                kinds=(("model", "strength_model"),)),
    MessageSpec(DRAWDOWN_NO_ENVELOPE,
                "Material '{material}' is marked undrained but has no R or "
                "Kc=1 envelope defined.", group_by=("material",)),
    MessageSpec(DRAWDOWN_STAGE1_NORMALS,
                "Method '{method}' reported {count} base normal forces for "
                "{slices} slices, so the stage-1 consolidation state cannot "
                "be recovered. Without it the procedure would apply no "
                "undrained strength at all and report the drained factor of "
                "safety.", group_by=("method",),
                kinds=(("method", "method_id"),)),
    MessageSpec(DRAWDOWN_CAP_NORMALS,
                "Method '{method}' reported {count} base normal forces for "
                "{slices} slices, so the drained cap cannot be evaluated on "
                "all of them.", group_by=("method",),
                kinds=(("method", "method_id"),)),
    MessageSpec(DRAWDOWN_UNKNOWN_PROCEDURE,
                "Unknown drawdown procedure: {procedure}",
                group_by=("procedure",)),
    MessageSpec(DRAWDOWN_UNSLICEABLE_INITIAL,
                "The slip surface could not be sliced at the initial level"),
    MessageSpec(DRAWDOWN_UNSLICEABLE_DRAWN_DOWN,
                "The slip surface could not be sliced at the drawn-down "
                "level"),
    MessageSpec(DRAWDOWN_STAGE1_UNUSABLE,
                "Stage 1 did not produce a usable factor of safety"),
    MessageSpec(DRAWDOWN_STAGE1_UNSTABLE,
                "Stage 1 factor of safety is {factor:.3f} < 1: the slope is not "
                "stable with the reservoir full, and the rapid-drawdown "
                "procedure does not apply to it"),
    MessageSpec(DRAWDOWN_STAGE_FAILED,
                "Stage {stage} produced no factor of safety: {why}",
                group_by=("stage", "why")),
    MessageSpec(DRAWDOWN_STAGE_FAILED_CAP,
                "Stage {stage} (drained cap, pass {cap_pass}) produced no "
                "factor of safety: {why}", group_by=("stage", "why")),
    MessageSpec(DRAWDOWN_STAGE_UNCONVERGED,
                "Stage {stage} returned an unconverged factor of safety "
                "(F = {factor:.3f}, not a solution): {why}",
                group_by=("stage", "why")),
    MessageSpec(DRAWDOWN_STAGE1_INADMISSIBLE,
                "Stage 1 (full reservoir): {why}", group_by=("why",)),
    MessageSpec(DECLARED_INADMISSIBLE,
                "declared inadmissible by its own method"),
    MessageSpec(NO_REASON_GIVEN, "no reason given"),
):
    MESSAGES[_spec.code] = _spec


def text(code: str, **args) -> str:
    """The English sentence of ``code`` with ``args``."""
    return english(MESSAGES, code, args)


def failure(code: str, **args) -> dict:
    """The keyword arguments of an ``LEMResult`` that failed for ``code``:
    the sentence and its code, written together so they cannot disagree."""
    return {"error_message": text(code, **args), "message_code": code,
            "message_args": dict(args)}


def inadmissible(code: str, **args) -> dict:
    """The keyword arguments of an ``LEMResult`` judged inadmissible for
    ``code`` (its note), the counterpart of :func:`failure`."""
    return {"admissibility_note": text(code, **args), "note_code": code,
            "note_args": dict(args)}


def error_of(result) -> dict:
    """A result's failure as a message to carry inside another one: its
    code and values when it has them, its sentence always, and "no reason
    given" when it has none (D56 obliges a sentence, not a code)."""
    sentence = getattr(result, "error_message", "") or ""
    if not sentence:
        return nested(NO_REASON_GIVEN, {}, text(NO_REASON_GIVEN))
    return nested(getattr(result, "message_code", "") or "",
                  getattr(result, "message_args", None) or {}, sentence)


def note_of(result) -> dict:
    """The same for a result's admissibility note."""
    return nested(getattr(result, "note_code", "") or "",
                  getattr(result, "note_args", None) or {},
                  getattr(result, "admissibility_note", "") or "")
