# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Errors an operation raises on purpose, each with a stable code.

The reader of these messages is very often a language model, and the one
thing that lets it recover is being told WHAT was wrong and WHAT to do
instead. So every error carries a ``hint`` where one exists, and every
"unknown name" carries the closest known names (:func:`did_you_mean`).

Codes are stable strings; the wording of ``message`` is not.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import difflib
from typing import Iterable, Optional


class OgrApiError(Exception):
    """Base class: ``[CODE] message Hint: hint``."""

    code = "E_INTERNAL"

    def __init__(self, message: str, *, hint: Optional[str] = None,
                 details: Optional[dict] = None,
                 code: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}
        if code is not None:
            self.code = code

    def __str__(self) -> str:
        text = f"[{self.code}] {self.message}"
        if self.hint:
            text += f" Hint: {self.hint}"
        return text

    def to_dict(self) -> dict:
        out = {"code": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        if self.details:
            out["details"] = self.details
        return out


class NotFound(OgrApiError):
    """A handle, id or name that does not exist."""

    code = "E_NOT_FOUND"


class InvalidArgument(OgrApiError):
    """A value of the wrong type, out of range, or not one of the choices."""

    code = "E_INVALID_ARGUMENT"


class Conflict(OgrApiError):
    """A valid request the current model does not allow (a second water
    table, a factor on a non-custom design standard, ...)."""

    code = "E_CONFLICT"


class NotConfigured(OgrApiError):
    """The model cannot be analysed as configured; ``details['problems']``
    lists every reason, as ``check_analysis_settings`` gave them."""

    code = "E_NOT_CONFIGURED"


class Busy(OgrApiError):
    """Another operation holds the model, or a job is already running."""

    code = "E_BUSY"


class JobFailed(OgrApiError):
    """A background job ended in failure; the message carries its error."""

    code = "E_JOB_FAILED"


def did_you_mean(word: str, options: Iterable[str], n: int = 3) -> str:
    """``"Did you mean 'a' or 'b'?"``, or an empty string.

    The cut-off is difflib's default similarity (0.6) lowered a little,
    because setting names are long and share prefixes, and a suggestion
    that is merely plausible still beats a bare "unknown".
    """
    opts = [str(o) for o in options]
    close = difflib.get_close_matches(str(word), opts, n=n, cutoff=0.55)
    if not close:
        lowered = {o.lower(): o for o in opts}
        close = [lowered[c] for c in difflib.get_close_matches(
            str(word).lower(), list(lowered), n=n, cutoff=0.55)]
    if not close:
        return ""
    if len(close) == 1:
        return f"Did you mean '{close[0]}'?"
    return ("Did you mean " + ", ".join(f"'{c}'" for c in close[:-1])
            + f" or '{close[-1]}'?")


def unknown(kind: str, word, options: Iterable[str]) -> NotFound:
    """A :class:`NotFound` for ``word`` among ``options``, with suggestions."""
    options = list(options)
    hint = did_you_mean(str(word), options)
    listing = ", ".join(repr(o) for o in options[:40])
    more = "" if len(options) <= 40 else f" (+{len(options) - 40} more)"
    return NotFound(f"Unknown {kind} {word!r}.",
                    hint=(hint + " " if hint else "")
                    + f"Known: {listing}{more}.")
