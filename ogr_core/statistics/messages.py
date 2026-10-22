# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Why the drawdown level sweep could not run, with stable codes (v0.1.352,
D335).

``notes["error"]`` of a sweep was an English sentence; each is a code here
with that English, so the sentence is the one the sweep wrote, and the
interface translates it.

Codes are ``sweep.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

SWEEP_NO_METHOD = "sweep.no_method"
SWEEP_NEEDS_DRAWDOWN = "sweep.needs_drawdown"

SWEEP_NOTES = {s.code: s for s in (
    MessageSpec(SWEEP_NO_METHOD, "No analysis method selected."),
    MessageSpec(SWEEP_NEEDS_DRAWDOWN,
                "The drawdown level sweep needs a Rapid Drawdown analysis: "
                "enable it in Project Settings > Groundwater > Advanced."),
)}


def sweep_note(code: str, **args) -> Coded:
    """The note ``code``: its English sentence, carrying the code."""
    return coded(SWEEP_NOTES, code, **args)
