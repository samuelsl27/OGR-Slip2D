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

from ogr_core.messages import METHOD_NOTE, parts, render

from .i18n import tr


_CATALOGUE: dict = {}


def _catalogue() -> dict:
    """The engine's codes, the DXF import's (v0.1.334), the analysis notes'
    and the project rules' (v0.1.347), the notes about one method's surface
    (v0.1.348) and the search's (v0.1.349), in one table: the codes do not
    collide, each family having its own prefix."""
    if not _CATALOGUE:
        from ogr_core.dxf.messages import MESSAGES as DXF
        from ogr_core.messages import CORE_MESSAGES, NOTE_FRAMES
        from ogr_core.project.messages import RULES
        from ogr_slip2d.messages import MESSAGES as LEM
        from ogr_slip2d.method_note_messages import METHOD_NOTES
        from ogr_slip2d.note_messages import NOTES
        from ogr_slip2d.search_note_messages import SEARCH_NOTES
        for table in (CORE_MESSAGES, NOTE_FRAMES, LEM, DXF, NOTES,
                      RULES, METHOD_NOTES, SEARCH_NOTES):
            _CATALOGUE.update(table)
    return _CATALOGUE


def _show(kind: str, value):
    """How a value of a declared kind reads: a method by its name, a name the
    program shows through its translation, a strength model by its name."""
    if kind == "method_id":
        from .labels import method_name
        return method_name(value)
    if kind == "method_list":
        # v0.1.347 (D335) -- the ids ", "-joined, as the engine wrote them
        from .labels import method_name
        return ", ".join(method_name(m) for m in str(value).split(", ") if m)
    if kind == "label":
        return tr(str(value))
    if kind == "force_orientation":
        # v0.1.348 (D335) -- a support's force orientation, by its value:
        # the table is keyed by the member, and a value this build does not
        # know shows as it is
        from ogr_core.support import ForceOrientation
        from .labels import force_orientation_label
        try:
            value = ForceOrientation(value)
        except ValueError:
            pass
        return force_orientation_label(value)
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


def problem_text(problem: dict) -> str:
    """A DXF import problem (a sanitiser record) in the reader's language
    (v0.1.334, D314)."""
    return text(problem.get("code", "") or "", problem.get("args"),
                problem.get("message", "") or "")


def preview_error_text(pv) -> str:
    """Why a DXF import preview failed, in the reader's language, or the
    empty string when it did not."""
    return text(getattr(pv, "error_code", "") or "",
                getattr(pv, "error_args", None), getattr(pv, "error", "")
                or "")


def invalid_label(res) -> str:
    """The group ``res`` is rejected under: :func:`invalid_text` with the
    values that vary between surfaces left out."""
    parts = _parts(res)
    if parts is None:
        return tr("did not converge")
    return label(*parts)


# ----------------------------------------------------------------------
# The analysis notes (v0.1.347, D335)
# ----------------------------------------------------------------------
def note_text(note) -> str:
    """A note -- a message the engine or the core wrote, with its code or
    without one -- in the reader's language: through its code when it has
    one, through its translation when it is a fixed sentence with an entry,
    and as it was written otherwise."""
    code, args, english = parts(note)
    if code:
        return text(code, args, english)
    return tr(english)


def note_group(note) -> tuple:
    """``(group, sentence)`` of a note for the Analysis Notes panel.

    A note about one method's reported surface is grouped under the method,
    shown by its name; a note about the model has no group (None). A note
    without a code keeps the rule the panel always had: an identifier
    before ``": "`` is the method's."""
    code, args, english = parts(note)
    if code == METHOD_NOTE:
        inner = args.get("note") or {}
        sentence = (text(inner.get("code", ""), inner.get("args"),
                         inner.get("text", ""))
                    if inner.get("code") else tr(inner.get("text", "")))
        return _show("method_id", args.get("method_id", "")), sentence
    if code:
        return None, text(code, args, english)
    head, sep, tail = english.partition(": ")
    if sep and head and " " not in head:
        return head, tr(tail)
    return None, tr(english)


def note_line(note) -> str:
    """A note on one line, its method first when it has one: what the status
    bar shows and what *Copy all* copies."""
    group, sentence = note_group(note)
    return sentence if group is None else "%s: %s" % (group, sentence)
