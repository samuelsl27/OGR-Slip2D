# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a design standard did to the copy an analysis computes on, with stable
codes (v0.1.353, D335).

``DesignFactorReport.notes`` and ``summary()`` were English sentences with
their factors in them; the notes panel showed them as they came ("they
arrive in English and stay in English"). Each is a code here with that
English, so the sentence is the one the core wrote -- the command line and
the API print it -- and the interface translates it. What a strength model
said about its own factoring is nested with its code
(``ogr_core.materials.messages``).

Codes are ``design.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

D = "design."
NONE = D + "none"
SUMMARY = D + "summary"
MATERIAL = D + "material"
SEISMIC_NOT_APPLIED = D + "seismic_not_applied"
SEISMIC = D + "seismic"
WEIGHT_SINGLE = D + "weight_single"
WEIGHT = D + "weight"
LOADS_BY_ACTION = D + "loads_by_action"
LOADS_VARIABLE = D + "loads_variable"
IDENTITY = D + "identity"

DESIGN_NOTES = {s.code: s for s in (
    MessageSpec(NONE, "no partial factors applied"),
    MessageSpec(SUMMARY,
                "{standard}: {materials} material(s) and {loads} load(s) "
                "factored"),
    MessageSpec(MATERIAL, "Material {name!r}: {note}."),
    MessageSpec(SEISMIC_NOT_APPLIED,
                "Seismic: the factor {factor:g} is not applied — the run "
                "seeks the critical seismic coefficient, so there is no "
                "coefficient to factor."),
    MessageSpec(SEISMIC, "Seismic: kh and kv multiplied by {factor:g}."),
    MessageSpec(WEIGHT_SINGLE,
                "Soil weight: the permanent-action factor {factor:g} "
                "multiplies the weight of every slice (single source "
                "assumption)."),
    MessageSpec(WEIGHT,
                "Soil weight: the permanent-action factor {unfavourable:g} "
                "multiplies the weight of the slices whose base drives the "
                "sliding, and {favourable:g} that of the others."),
    MessageSpec(LOADS_BY_ACTION,
                "Loads: each one is factored as a whole, by its action and by "
                "whether it drives the sliding of the surface: a permanent "
                "load by {pu:g} or {pf:g}, a variable one by {vu:g} or "
                "{vf:g}."),
    MessageSpec(LOADS_VARIABLE,
                "Every load takes the variable-action factor ({factor:g}): a "
                "load carries no action type in this version."),
    MessageSpec(IDENTITY,
                "The standard is enabled but every factor is 1.0, so nothing "
                "changed."),
)}


def design_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(DESIGN_NOTES, code, **args)
