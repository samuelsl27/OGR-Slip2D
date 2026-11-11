# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The shape of a ``.ogr``, checked before it is read (v0.1.438, D422).

``Project.from_dict`` took the shape ``Project.to_dict`` writes for granted.
A root that was a list, a ``"settings": []`` or a ``"focus_objects": [[1]]``
ended in ``'list' object has no attribute 'get'``, an ``AttributeError`` the
agent received loose, outside every ``except`` of the readers; and a
``"materials": {}`` or a ``{}`` opened, empty, without a word. Measured with
0.1.435 and 0.1.437 (the bank's ``medir_d422.py``).

The table is literal on purpose: it is what ``to_dict`` writes, and the test
of this version compares it with ``to_dict()`` of a model that has every
section, so a section added to the file without its shape here fails there.
A section the reader has always tolerated as null (``if section:``, or
``data.get(...) or {}``) keeps tolerating a null -- and only a null: those
idioms also swallowed ``""``, ``0`` and ``false``, and a file with one of
them where a section goes is refused now, like any section of another shape
(the owner's decision in the review of 0.1.438). Measured on the 248 source
``.ogr`` of the bank, every file that opened before opens the same, with the
same ``document_hash``, and the review found none refused among the 2486 of
the repository and the history. Only what was not a valid file is refused,
by a code the window says in the reader's language.

What is checked is the shape of the sections, not the values inside them (a
unit weight ``"x"``): that is D429, by the owner's decision.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..file_messages import (ITEM_SHAPE, NO_PROJECT_KEY, NOT_A_PROJECT,
                             SECTION_SHAPE, SHAPE_WORDS, file_refusal,
                             json_shape)

LIST = "list"
OBJECT = "object"
LIST_OR_NULL = "list_or_null"
OBJECT_OR_NULL = "object_or_null"

#: The sections of a project, by the JSON shape ``Project.to_dict`` gives
#: them. A list holds objects, one per item.
SECTIONS = {
    "settings": OBJECT,
    "boundaries": LIST,
    "materials": LIST,
    "supports": LIST,
    "support_types": LIST,
    "distributed_loads": LIST,
    "line_loads": LIST,
    "seismic": OBJECT,
    "seismic_records": LIST,
    "region_assignments": LIST,
    "tension_crack_properties": OBJECT,
    "water_pressure_grid": OBJECT_OR_NULL,
    "fem_mesh": OBJECT_OR_NULL,
    "seepage_bcs": OBJECT_OR_NULL,
    "seepage_result": OBJECT_OR_NULL,
    "transient_results": LIST_OR_NULL,
    "random_variables": LIST_OR_NULL,
    "annotations": LIST_OR_NULL,
    "focus_objects": LIST_OR_NULL,
    "user_surfaces": LIST_OR_NULL,
    "transient_initial_result": OBJECT_OR_NULL,
    "user_polylines": LIST_OR_NULL,
}

#: The subsections of ``settings``; ``search``, ``advanced`` and
#: ``design_standard`` have always read a null as their defaults.
SETTINGS_SECTIONS = {
    "units": OBJECT,
    "methods": OBJECT,
    "groundwater": OBJECT,
    "search": OBJECT_OR_NULL,
    "statistics": OBJECT,
    "back_analysis": OBJECT,
    "random_numbers": OBJECT,
    "design_standard": OBJECT_OR_NULL,
    "advanced": OBJECT_OR_NULL,
    "seismic": OBJECT,
    "summary": OBJECT,
}

#: The keys a project's file holds besides its sections: an object with
#: none of these and none of the sections is not a project.
SCALARS = ("format_version", "id", "name")

_ACCEPTS = {
    LIST: ("list",),
    OBJECT: ("object",),
    LIST_OR_NULL: ("list", "null"),
    OBJECT_OR_NULL: ("object", "null"),
}


def check_shape(data) -> None:
    """Raise ``ValueError`` with a coded refusal if ``data`` -- the JSON of a
    ``.ogr`` -- does not have the shape a project's file has; return
    nothing if it does. A key this build does not know is left alone, as
    the reader always left it."""
    found = json_shape(data)
    if found != "object":
        raise ValueError(file_refusal(
            NOT_A_PROJECT, f"The file does not hold a project: it is "
            f"{SHAPE_WORDS.get(found, found)}, not an object.", found=found))
    if not any(k in data for k in (*SECTIONS, *SCALARS)):
        raise ValueError(file_refusal(
            NO_PROJECT_KEY,
            "The file does not hold a project: it has none of the keys of "
            "one."))
    _check_sections(data, SECTIONS, "")
    settings = data.get("settings")
    if isinstance(settings, dict):
        _check_sections(settings, SETTINGS_SECTIONS, "settings.")


def _check_sections(data: dict, table: dict, prefix: str) -> None:
    for key, expected in table.items():
        if key not in data:
            continue
        value = data[key]
        found = json_shape(value)
        if found not in _ACCEPTS[expected]:
            section = prefix + key
            raise ValueError(file_refusal(
                SECTION_SHAPE, f"The section '{section}' of the file must be "
                f"{SHAPE_WORDS[expected]}, not "
                f"{SHAPE_WORDS.get(found, found)}.",
                section=section, expected=expected, found=found))
        if found == "list":
            for n, item in enumerate(value, start=1):
                kind = json_shape(item)
                if kind != "object":
                    section = prefix + key
                    raise ValueError(file_refusal(
                        ITEM_SHAPE, f"Item {n} of the section '{section}' of "
                        f"the file must be an object, not "
                        f"{SHAPE_WORDS.get(kind, kind)}.",
                        n=n, section=section, found=kind))
