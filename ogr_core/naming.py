# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The names the program gives what it creates, in one place (v0.1.436, D415).

A support set born in Define Support was «Type N» with N the number of rows,
so deleting the second of three and adding one gave a second «Type 3», and
duplicating a set twice gave two «X (copy)». The agent finds a set by its
name only when one set has it (``ogr_api.ops.supports.find_type``), so those
repeated names were sets it could no longer name. A strong-motion record is
«Record», and a load «Dist 20.0 kN/m²» or «Line 50.0 kN/m», with the
magnitude it had when it was created and never again.

These names are DATA once written: the ``.ogr`` keeps them, the agent reads
and writes them byte for byte, and a name the user gave is never touched.
What this module adds is the rule each one is made by, so that the interface
can tell a name the program made from one the user gave, and show the former
in the reader's language (``ogr_gui.labels``). Define Support, the window's
loads, the agent's loads and records and the record reader take their names
from here; the agent's second set of a class and the importer's numbering
still keep their own copy of :func:`numbered_name`, the same today, until
D421 (0.1.439) makes them import it. No dependency on the rest of the core,
so the loads and the supports can import it without a cycle.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

#: A support set Define Support adds: «Type 1», «Type 2», ...
NEW_SET_NAME = "Type {0}"
#: What Define Support's Duplicate appends to the name it copies.
COPY_SUFFIX = " (copy)"
#: A strong-motion record read from text or values, with no file to name it.
DEFAULT_RECORD_NAME = "Record"

#: The names a load is born with, by its kind, as the window and the agent
#: wrote them since v0.1.59 (``f"Dist {m:.1f} kN/m²"``).
_LOAD_NAMES = {"distributed": "Dist {0:.1f} kN/m²",
               "line": "Line {0:.1f} kN/m"}
#: Exactly what ``{0:.1f}`` writes: a name the user typed («Dist 20 kN/m²»,
#: «Dist 1e3 kN/m²») is the user's (review of 0.1.436).
_LOAD_NAME_RE = {kind: re.compile(re.escape(fmt.split("{")[0])
                                  + r"(-?[0-9]+\.[0-9])"
                                  + re.escape(fmt.split("}")[1]), re.ASCII)
                 for kind, fmt in _LOAD_NAMES.items()}


def name_key(name) -> str:
    """What two names are compared by: without the spaces at the ends and
    without case. The rule ``find_type`` finds a set by, so a name this
    module calls free is one the agent can find."""
    return str(name or "").strip().lower()


def numbered_name(base: str, taken: Iterable) -> str:
    """``base``, or «base (2)», «base (3)», ... -- the first that no name in
    ``taken`` has under :func:`name_key`. The rule the importer gives a
    material whose name the model already has, and the agent a second set
    of a class -- each with its own copy of this loop today; D421 (0.1.439)
    makes them import it."""
    keys = {name_key(t) for t in taken}
    label, i = base, 2
    while name_key(label) in keys:
        label, i = f"{base} ({i})", i + 1
    return label


def first_free_set_name(taken: Iterable) -> str:
    """«Type N» with the smallest N ≥ 1 that no name in ``taken`` has."""
    keys = {name_key(t) for t in taken}
    n = 1
    while name_key(NEW_SET_NAME.format(n)) in keys:
        n += 1
    return NEW_SET_NAME.format(n)


def copy_name(name: str, taken: Iterable) -> str:
    """The name of a copy of ``name``: «name (copy)», numbered when that is
    taken (a set duplicated twice gives «X (copy)» and «X (copy) (2)»)."""
    return numbered_name(str(name or "") + COPY_SUFFIX, taken)


def default_load_name(kind: str, magnitude: float) -> str:
    """The name a load of ``kind`` ("distributed" or "line") is born with."""
    return _LOAD_NAMES[kind].format(magnitude)


def parse_default_load_name(name) -> Optional[tuple]:
    """``(kind, magnitude)`` when ``name`` is a name :func:`default_load_name`
    wrote, else None. The magnitude is the one it had when it was named."""
    for kind, pattern in _LOAD_NAME_RE.items():
        m = pattern.fullmatch(str(name or ""))
        if m:
            try:
                return kind, float(m.group(1))
            except ValueError:
                return None
    return None


def load_kind(load) -> str:
    """"line" for a line load, "distributed" for any other: the two kinds a
    load name is made for. By the attribute only a line load has, so the
    core needs no import of the loads here."""
    return "line" if hasattr(load, "point") else "distributed"


def load_magnitude(load) -> Optional[float]:
    """The magnitude a load is named by: a line load's, a distributed load's
    first (the one the context menu has always shown)."""
    value = getattr(load, "magnitude", None)
    if value is None:
        value = getattr(load, "magnitude_1", None)
    return value


def load_end_magnitude(load) -> Optional[float]:
    """The second magnitude of a distributed load that varies along it, or
    None when it is uniform (no second one, the same, or a constant
    distribution): a trapezoidal load is named by both ends (the owner's
    decision in the review of 0.1.436)."""
    second = getattr(load, "magnitude_2", None)
    distribution = getattr(getattr(load, "distribution", None), "value",
                           getattr(load, "distribution", None))
    if (second is None or distribution in (None, "constant")
            or second == load_magnitude(load)):
        return None
    return second


def load_has_given_name(load) -> bool:
    """Whether the user named ``load``: its name is neither empty nor one
    :func:`default_load_name` wrote."""
    name = getattr(load, "name", "") or ""
    return bool(name) and parse_default_load_name(name) is None


class LoadName(str):
    """The name a run keeps for a load it factored, and what the load was
    then (v0.1.436, D415).

    It IS the text the run always kept (the load's name, or its id when it
    has none), so the agent's JSON and the agent's PDF do not change. A
    reader that names the load as the run saw it reads ``kind``,
    ``magnitude`` and ``given`` instead: the owner's decision (2026-11-11)
    is that the results panel and the window's PDF name an unnamed load by
    the magnitude of the RUN, as a heading under a standard is asked of the
    run and not of the model (D413).

    It pickles with what it carries (``__reduce__``), because a search
    comes back from a pool of processes.
    """

    def __new__(cls, text: str, kind: str = "", magnitude=None,
                given: bool = True, end_magnitude=None):
        self = str.__new__(cls, text)
        self.kind = kind or ""
        self.magnitude = magnitude
        self.given = bool(given)
        self.end_magnitude = end_magnitude
        return self

    def __reduce__(self):
        return (LoadName, (str(self), self.kind, self.magnitude, self.given,
                           self.end_magnitude))

    @classmethod
    def of(cls, load):
        """The name of ``load`` as a run keeps it. A name that is not text
        (``"name": 5`` in a hand-edited file) is kept as it came: the
        agent's JSON read that value (review of 0.1.436)."""
        text = getattr(load, "name", "") or getattr(load, "id", "")
        if not isinstance(text, str):
            return text
        return cls(text, kind=load_kind(load), magnitude=load_magnitude(load),
                   given=load_has_given_name(load),
                   end_magnitude=load_end_magnitude(load))
