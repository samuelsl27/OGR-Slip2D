# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Messages with a stable code (v0.1.333, D314).

An engine message reaches the screen in two halves. One is the English
sentence, which callers have read since v0.1.152 and which no change may
move by a byte: about ninety tests and the verification bank match
substrings of it, and the raw-data export reads ``"m_alpha"`` in it. The
other, new here, is a CODE with the VALUES that went into the sentence, so
the interface can say the same thing in the reader's language.

Before this version only the sentence existed, with its numbers baked in by
an f-string. The only way to translate it was to parse it, and grouping by
it split one condition into as many groups as there were values: the
m-alpha rejections of a search came out in one group per slice count.

A catalogue maps each code to a :class:`MessageSpec`. Its ``english`` is a
``str.format`` template with named fields and the very format specs the
f-string used (``"%.3g" % x`` and ``"{x:.3g}"`` print the same), so the
sentence it renders is the one the engine wrote before. One template per
code, in one place, is what a translator keys on.

A value may itself be a message (:func:`nested`): the reason a stage of a
rapid drawdown failed is the reason its method gave. Rendering, translating
and grouping recurse into it, and a nested message whose code is unknown
shows its own text.

No Qt here. The core and the engines build messages; the interface
translates them (``ogr_gui.core_messages``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

#: What a group label shows in place of a value it leaves out.
ELIDED = "…"


@dataclass(frozen=True)
class MessageSpec:
    """One message: its code, its English template and how to group it.

    ``group_by`` names the fields a group label keeps. The others become
    "…", so one condition is one group whatever its numbers. ``kinds``
    pairs a field with the kind of value it holds — ``"method_id"``,
    ``"label"`` (a name the program shows through its translation) or
    ``"strength_model"`` — so the interface can show that value in the
    reader's language too.
    """
    code: str
    english: str
    group_by: tuple = ()
    kinds: tuple = ()


#: Two messages one after the other, as the engine joined them with "; ".
JOIN = "join"

CORE_MESSAGES = {
    JOIN: MessageSpec(JOIN, "{first}; {second}",
                      group_by=("first", "second")),
}


def nested(code: str, args: Optional[dict], text: str) -> dict:
    """A message carried as the value of another one's field: its code, its
    values and the sentence it was written as (shown when the code is not
    known, which is also how a message from a plugin without codes
    travels)."""
    return {"code": code or "", "args": dict(args or {}), "text": text or ""}


def is_nested(value) -> bool:
    return (isinstance(value, dict) and "code" in value and "args" in value
            and "text" in value)


class _Elided:
    """A value a group label leaves out: it formats as "…" whatever the
    format spec, so a template written for a number still renders."""

    def __format__(self, spec: str) -> str:
        return ELIDED

    def __str__(self) -> str:
        return ELIDED


def english(catalogue: dict, code: str, args: Optional[dict] = None) -> str:
    """The sentence ``code`` with ``args``, in English, exactly as the engine
    writes it: a nested message contributes its own text.

    Raises when the code is not in the catalogue or the values do not fill
    its template. Both are mistakes in the code that writes the message, and
    a test catches them; a reader never sees this, it sees the sentence.
    """
    spec = catalogue[code]
    values = {k: (v["text"] if is_nested(v) else v)
              for k, v in (args or {}).items()}
    return spec.english.format(**values)


def render(catalogue: dict, code: str, args: Optional[dict],
           fallback: str = "", *,
           translate: Optional[Callable[[str], str]] = None,
           show: Optional[Callable] = None, elide: bool = False) -> str:
    """The message ``code`` with ``args`` for a reader.

    ``translate`` maps an English template to its translation; ``show``
    maps ``(kind, value)`` to how a value of a declared kind is shown. With
    ``elide`` the fields outside ``group_by`` become "…": the label of the
    group the message belongs to.

    Never raises and never loses a message. An unknown code gives
    ``fallback`` (the sentence the engine wrote), and a translation that
    does not format falls back on the English template.
    """
    spec = catalogue.get(code) if code else None
    if spec is None:
        return fallback
    kinds = dict(spec.kinds)
    values = {}
    for key, value in (args or {}).items():
        if is_nested(value):
            values[key] = render(catalogue, value["code"], value["args"],
                                 value["text"], translate=translate,
                                 show=show, elide=elide)
        elif elide and key not in spec.group_by:
            values[key] = _Elided()
        elif show is not None and key in kinds:
            try:
                values[key] = show(kinds[key], value)
            except Exception:  # noqa: BLE001 - a value is shown as it is
                values[key] = value
        else:
            values[key] = value
    templates = [spec.english]
    if translate is not None:
        templates.insert(0, translate(spec.english))
    for template in templates:
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError, TypeError,
                AttributeError):
            continue
    return fallback


def json_args(args) -> dict:
    """``args`` as plain JSON data: a non-finite float becomes its ``repr``
    (``"inf"``, ``"nan"``), which JSON has no number for, and a tuple a
    list. Nested messages are converted too."""
    def conv(v):
        if isinstance(v, float) and not math.isfinite(v):
            return repr(v)
        if isinstance(v, dict):
            return {str(k): conv(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [conv(x) for x in v]
        return v
    return {str(k): conv(v) for k, v in (args or {}).items()}
