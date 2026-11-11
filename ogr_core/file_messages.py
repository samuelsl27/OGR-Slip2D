# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The refusals of the readers of a ``.ogr``, with their codes (v0.1.437, D414).

Opening a file the program cannot read showed, inside a translated frame,
the English of the reader that refused it, with the quotes of a
``KeyError``'s repr: «'Unknown support type: future_nail'». Three of those
sentences are the core's own (an unknown support type, strength model or
parameter); two more are Python's, but say what the file holds that this
build does not know (a value of an enumeration, a boundary type), and the
owner decided they are said too (2026-11-11). Everything else a broken file
raises -- a key missing, a value of another type -- stays as Python wrote
it, inside the frame (the rule of D412).

What the agent reads does not move by a byte. The core's three refusals
raise the exception they always raised with a :class:`~ogr_core.messages.
Coded` as its argument, which IS the English sentence. The two of Python
keep their own exception and their own text, and carry the code as
attributes (``code`` and ``values``, as ``DxfReadError`` does), which the
interface reads (``ogr_gui.core_messages.error_text``).

No dependency on the rest of the core, so every reader can import it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from .messages import Coded, Joined, MessageSpec

F = "file."
SUPPORT_TYPE_UNKNOWN = F + "support_type_unknown"
STRENGTH_MODEL_UNKNOWN = F + "strength_model_unknown"
PARAMETER_UNKNOWN = F + "parameter_unknown"
BOUNDARY_TYPE_UNKNOWN = F + "boundary_type_unknown"
ENUM_UNKNOWN = F + "enum_unknown"

#: The value a file holds, as the window quotes it: «null», not Python's
#: «None» (review of 0.1.437).
_VALUE = "file_value"

FILE_MESSAGES = {s.code: s for s in (
    MessageSpec(SUPPORT_TYPE_UNKNOWN, "Unknown support type: {type_id}",
                kinds=(("type_id", _VALUE),)),
    # the models this build has, by their names in the window
    MessageSpec(STRENGTH_MODEL_UNKNOWN,
                "Unknown strength model: '{model_id}'. Available: {available}",
                kinds=(("model_id", _VALUE),
                       ("available", "strength_model_list"))),
    MessageSpec(PARAMETER_UNKNOWN,
                "{model_id}: unknown parameter '{key}'. Valid: {valid}",
                kinds=(("model_id", "strength_model"),
                       ("valid", "parameter_list"))),
    # Python's own words are the exception's text (the agent's); these are
    # the window's, which names the enumeration by what it is
    MessageSpec(BOUNDARY_TYPE_UNKNOWN, "Unknown boundary type: '{value}'",
                kinds=(("value", _VALUE),)),
    MessageSpec(ENUM_UNKNOWN, "'{value}' is not a valid value for {enum}",
                kinds=(("value", _VALUE), ("enum", "enum_name"))),
)}


def file_refusal(code: str, text: str, **args) -> Coded:
    """A refusal of a reader: ``text``, the sentence it always wrote (an
    f-string, kept as it is), carrying ``code`` and ``args``.

    Not built from the template: ``english`` joins a list of values as a
    list of messages, so an empty one came out as nothing, and a model with
    no parameters said «Valid: » where it said «Valid: []» (review of
    0.1.437). A list in ``args`` goes as a :class:`Joined`, which the window
    names item by item."""
    return Coded(text, code, {k: (Joined(v) if isinstance(v, list) else v)
                              for k, v in args.items()})


def said_as(exc, code: str, **values):
    """``exc`` as it was, carrying the code it is said by in the window: its
    type and its text -- Python's -- are what the agent reads."""
    exc.code = code
    exc.values = dict(values)
    return exc


def read_enum(cls, value):
    """``cls(value)``, the value of an enumeration a file holds. One this
    build does not know raises the ``ValueError`` it always raised, with its
    text, and with the code that names, in the window, what the value is of
    (v0.1.437, D414)."""
    try:
        return cls(value)
    except ValueError as exc:
        raise said_as(exc, ENUM_UNKNOWN, value=value, enum=cls.__name__)
