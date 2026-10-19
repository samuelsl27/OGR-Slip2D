# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The engine's messages in the reader's language (v0.1.333, D314).

The engine writes each per-surface message as an English sentence plus a
stable code with its values (``ogr_core.messages``,
``ogr_slip2d.messages``). This module turns the code back into a sentence
through ``tr()``: the English template is the key of the translation, so
there is one entry per code in ``ogr_gui/i18n``. A message without a code,
or whose code this version does not know, is shown as the engine wrote it.

It also gives the label of a message's GROUP: the same sentence with the
values that vary from surface to surface replaced by "…". The
interpretation window groups the invalid surfaces by that label, so one
condition is one group however many slice counts it was found at.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import render

from .i18n import tr


def _catalogue() -> dict:
    from ogr_slip2d.messages import MESSAGES
    return MESSAGES


def _show(kind: str, value):
    """How a value of a declared kind reads: a method by its name, a name the
    program shows through its translation, a strength model by its name."""
    if kind == "method_id":
        from .labels import method_name
        return method_name(value)
    if kind == "label":
        return tr(str(value))
    if kind == "strength_model":
        from ogr_core.materials import REGISTRY
        return tr(REGISTRY.get(value).DISPLAY_NAME)
    return value


def text(code: str, args, english: str) -> str:
    """The message ``code`` with ``args`` in the reader's language, or
    ``english`` (the sentence the engine wrote) when there is no code."""
    return render(_catalogue(), code, args, english, translate=tr,
                  show=_show)


def label(code: str, args, english: str) -> str:
    """The label of the group the message belongs to."""
    return render(_catalogue(), code, args, english, translate=tr,
                  show=_show, elide=True)


def _parts(res):
    """``(code, args, sentence)`` of why ``res`` was rejected: its failure,
    else its admissibility note, else None (the order the core's
    ``interpretation.invalid_reason`` reads them in)."""
    sentence = getattr(res, "error_message", None) or ""
    if sentence:
        return (getattr(res, "message_code", "") or "",
                getattr(res, "message_args", None) or {}, sentence)
    sentence = getattr(res, "admissibility_note", None) or ""
    if sentence:
        return (getattr(res, "note_code", "") or "",
                getattr(res, "note_args", None) or {}, sentence)
    return None


def invalid_text(res) -> str:
    """Why ``res`` was rejected, in full and in the reader's language."""
    parts = _parts(res)
    if parts is None:
        return tr("did not converge")
    return text(*parts)


def invalid_label(res) -> str:
    """The group ``res`` is rejected under: :func:`invalid_text` with the
    values that vary between surfaces left out."""
    parts = _parts(res)
    if parts is None:
        return tr("did not converge")
    return label(*parts)
