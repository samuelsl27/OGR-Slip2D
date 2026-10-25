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
    #: v0.1.347 (D335) -- the SINGULAR of the sentence, and the field whose
    #: value 1 chooses it. English pasted "s" and "was/were" onto a count,
    #: which no other language can translate; a sentence with a count is two
    #: whole templates instead, each with its own translation.
    one: str = ""
    count: str = ""
    #: v0.1.349 (D335) -- ``(field, separator)`` for a field holding several
    #: messages that the engine joined with something else than
    #: ``LIST_SEP`` ("; " between the reasons of a search, for instance).
    seps: tuple = ()

    def template(self, args=None) -> str:
        """The English template for ``args``: ``one`` when its count is 1."""
        if self.one and self.count and (args or {}).get(self.count) == 1:
            return self.one
        return self.english

    def sep(self, field: str) -> str:
        """How the messages of ``field`` are joined."""
        return dict(self.seps).get(field, LIST_SEP)


#: Two messages one after the other, as the engine joined them with "; ".
JOIN = "join"
#: v0.1.347 (D335) -- a note about one method's reported surface, written
#: ``"<method id>: <note>"`` since the analysis notes existed. The method is
#: a value of its kind, so the interface shows its name; the note is nested.
METHOD_NOTE = "note.method"

CORE_MESSAGES = {
    JOIN: MessageSpec(JOIN, "{first}; {second}",
                      group_by=("first", "second")),
}

#: The frames of the analysis notes (v0.1.347). A table of their own, and
#: not in ``CORE_MESSAGES``: that one is the base the engine's reasons and
#: the DXF problems start from, and a note frame is neither.
NOTE_FRAMES = {
    METHOD_NOTE: MessageSpec(METHOD_NOTE, "{method_id}: {note}",
                             group_by=("method_id", "note"),
                             kinds=(("method_id", "method_id"),)),
}


class Coded(str):
    """An English sentence that also carries its code and its values
    (v0.1.347, D335).

    It IS the sentence: equality, ``in``, ``startswith``, de-duplication by
    value, JSON and printing see the English the engine always wrote, so
    the tests and tools that read it are untouched. The interface reads
    ``code`` and ``args`` to say it in the reader's language. Anything that
    builds a NEW string from it (a concatenation, an f-string) gets a plain
    ``str``, without the code: a note that has to keep it is built with
    :func:`coded` or :func:`method_note`, never by hand.

    It pickles with its code (``__reduce__``), because the analysis jobs of
    the API come back from a subprocess.
    """

    def __new__(cls, text: str, code: str = "", args: Optional[dict] = None):
        self = str.__new__(cls, text)
        self.code = code or ""
        self.args = dict(args or {})
        return self

    def __reduce__(self):
        return (Coded, (str(self), self.code, self.args))


def coded(catalogue: dict, code: str, **args) -> Coded:
    """The message ``code`` with ``args``: its English sentence, carrying the
    code and the values (v0.1.347, D335)."""
    return Coded(english(catalogue, code, args), code, args)


def parts(note) -> tuple:
    """``(code, args, sentence)`` of a note: a :class:`Coded` one carries its
    code and values, a plain string none."""
    return (getattr(note, "code", "") or "",
            dict(getattr(note, "args", None) or {}), str(note))


def as_nested(note) -> dict:
    """A note as the value of another message's field."""
    code, args, text = parts(note)
    return nested(code, args, text)


def method_note(method_id: str, note) -> Coded:
    """``"<method id>: <note>"`` -- the sentence the analysis notes always
    wrote for one method -- with the method and the note kept (v0.1.347)."""
    return Coded("%s: %s" % (method_id, note), METHOD_NOTE,
                 {"method_id": method_id, "note": as_nested(note)})


def nested(code: str, args: Optional[dict], text: str) -> dict:
    """A message carried as the value of another one's field: its code, its
    values and the sentence it was written as (shown when the code is not
    known, which is also how a message from a plugin without codes
    travels)."""
    return {"code": code or "", "args": dict(args or {}), "text": text or ""}


def is_nested(value) -> bool:
    return (isinstance(value, dict) and "code" in value and "args" in value
            and "text" in value)


#: How a field that holds several messages joins them, as the engine always
#: joined its lists of reasons (v0.1.348, D335).
LIST_SEP = ", "


def is_nested_list(value) -> bool:
    """A field holding several messages, each nested (v0.1.348): the
    reasons a sentence lists, which the engine joined with ``LIST_SEP``.
    An empty list is one too, and joins to "" as ``", ".join([])`` did:
    no template takes a list of anything else."""
    return (isinstance(value, (list, tuple))
            and all(is_nested(v) for v in value))


def _english_value(value, sep: str = LIST_SEP):
    if is_nested(value):
        return value["text"]
    if is_nested_list(value):
        return sep.join(v["text"] for v in value)
    return value


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
    values = {k: _english_value(v, spec.sep(k))
              for k, v in (args or {}).items()}
    return spec.template(args).format(**values)


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
        elif is_nested_list(value):
            values[key] = spec.sep(key).join(
                render(catalogue, v["code"], v["args"], v["text"],
                       translate=translate, show=show, elide=elide)
                for v in value)
        elif elide and key not in spec.group_by:
            values[key] = _Elided()
        elif show is not None and key in kinds:
            try:
                values[key] = show(kinds[key], value)
            except Exception:  # noqa: BLE001 - a value is shown as it is
                values[key] = value
        else:
            values[key] = value
    # v0.1.347 (D335) -- the singular or the plural, chosen on the values
    # as they are (an elided count still chooses)
    base = spec.template(args)
    templates = [base]
    if translate is not None:
        templates.insert(0, translate(base))
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


#: The strings :func:`json_args` writes for the floats JSON has no number for.
_NON_FINITE = {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}


def args_from_json(args) -> dict:
    """The inverse of :func:`json_args` for what it changed: ``"nan"``,
    ``"inf"`` and ``"-inf"`` are floats again (v0.1.364, D342).

    Without it a note whose value was not finite renders its English
    sentence, because a template written for a number does not format the
    string ``"nan"``. A tuple stays a list, which formats the same."""
    def conv(v):
        if isinstance(v, str) and v in _NON_FINITE:
            return _NON_FINITE[v]
        if isinstance(v, dict):
            return {str(k): conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return {str(k): conv(v) for k, v in (args or {}).items()}
