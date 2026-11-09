# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The notes of the strong-motion record reader, with stable codes (v0.1.434,
D412).

``parse_record_text`` answers ``(accel, dt, note)``, and the note was an
English phrase the Seismic Records dialog pasted after a translated frame
(«No se ha importado nada: no numeric data»). Each is a code here; the note
is still the English it was (the agent reads ``f"Nothing was read: {note}"``
and the notes list), and an empty note stays the plain ``""`` a reader tests
for.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

S = "seismic."
NO_NUMERIC_DATA = S + "no_numeric_data"
TOO_FEW_SAMPLES = S + "too_few_samples"
TIME_NOT_INCREASING = S + "time_not_increasing"
STEP_NOT_CONSTANT = S + "step_not_constant"
NEEDS_INTERVAL = S + "needs_interval"

SEISMIC_NOTES = {s.code: s for s in (
    MessageSpec(NO_NUMERIC_DATA, "no numeric data"),
    MessageSpec(TOO_FEW_SAMPLES, "fewer than two samples"),
    MessageSpec(TIME_NOT_INCREASING, "non-increasing time column"),
    MessageSpec(STEP_NOT_CONSTANT, "time step is not constant"),
    MessageSpec(NEEDS_INTERVAL, "single-column file needs a time interval"),
)}


def seismic_note(code: str, **args) -> Coded:
    """The note ``code``: its English phrase, carrying the code (v0.1.434)."""
    return coded(SEISMIC_NOTES, code, **args)
