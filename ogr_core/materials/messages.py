# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the Hoek-Brown parameter calculator says about the values it was given,
with stable codes (v0.1.352, D335).

Codes are ``calc.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

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
