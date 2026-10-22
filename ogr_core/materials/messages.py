# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the Hoek-Brown parameter calculator says about the values it was given
(v0.1.352, D335), and what a strength model says when a design standard's
partial factors could not be applied to it (v0.1.353, D335), with stable
codes.

Codes are ``calc.*`` and ``factoring.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, as_nested, coded, parts

D_CLAMPED = "calc.d_clamped"
GSI_CLAMPED = "calc.gsi_clamped"

CALCULATOR_NOTES = {s.code: s for s in (
    MessageSpec(D_CLAMPED,
                "D = 2 makes mb undefined (28 − 14 D = 0); it has been clamped "
                "to 1.999."),
    MessageSpec(GSI_CLAMPED, "GSI was clamped to the range 0 to 100."),
)}


def calculator_note(code: str, **args) -> Coded:
    """The note ``code``: its English sentence, carrying the code."""
    return coded(CALCULATOR_NOTES, code, **args)


# ----------------------------------------------------------------------
# A strength model under a design standard (v0.1.353)
# ----------------------------------------------------------------------
F = "factoring."
LEGACY_POINTS = F + "legacy_points"
LEGACY_SNOWDEN = F + "legacy_snowden"
NO_FACTOR = F + "no_factor"
CHILD_UNBUILT = F + "child_unbuilt"
CHILD_NOTE = F + "child_note"
#: Snowden's two functions are named by their role; one code per role,
#: because the role is words of the sentence, not a value.
SNOWDEN_UNBUILT = F + "snowden_unbuilt."
SNOWDEN_NOTE = F + "snowden_note."
SNOWDEN_ROLES = ("bedding", "rock_mass")
JOINED = F + "joined"

FACTORING_NOTES = {s.code: s for s in (
    MessageSpec(LEGACY_POINTS,
                "a table saved as points before 0.1.218 is refused by the "
                "analysis, so it was not factored"),
    MessageSpec(LEGACY_SNOWDEN,
                "a material saved before 0.1.229 is refused by the analysis, "
                "so it was not factored"),
    MessageSpec(NO_FACTOR,
                "{model}: this strength model declares no partial factor, so "
                "it was NOT factored.",
                kinds=(("model", "label"),)),
    MessageSpec(CHILD_UNBUILT,
                "{label}: its model cannot be built, so it was not factored"),
    MessageSpec(CHILD_NOTE, "{label}: {note}"),
    MessageSpec(SNOWDEN_UNBUILT + "bedding",
                "its bedding function cannot be built, so it was not "
                "factored"),
    MessageSpec(SNOWDEN_UNBUILT + "rock_mass",
                "its rock mass function cannot be built, so it was not "
                "factored"),
    MessageSpec(SNOWDEN_NOTE + "bedding", "bedding: {note}"),
    MessageSpec(SNOWDEN_NOTE + "rock_mass", "rock mass: {note}"),
    MessageSpec(JOINED, "{items}", seps=(("items", "; "),)),
)}


def factoring_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(FACTORING_NOTES, code, **args)


def factoring_joined(notes) -> Coded:
    """``notes`` joined with "; ", as the models always joined them, each
    kept with its code."""
    items = []
    for note in notes:
        code, args, _text = parts(note)
        if code == JOINED:
            items.extend(args.get("items") or [])
        else:
            items.append(as_nested(note))
    return factoring_note(JOINED, items=items)
