# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The undo step names that carry values, with stable codes (v0.1.434, D412).

A step's name is what the Edit menu says («Deshacer «…»»), what the status
bar says after Ctrl+Z and what the agent reads in ``project_history``. A
literal name («Set material») is translated by its exact key; a name built
with an f-string never matched one, so seven reached the Spanish window in
English: «Paint material at (12.34, 5.67)», «Offset External (+1.50 m)»,
«Expand/Shrink (shrink)», and four the agent's operations write («Edit
boundary (translate)», «Hydraulic properties of Clay», «Random variable
material:<uuid>:cohesion», «Delete random variable …»).

Each is a code here, with the English its f-string wrote, byte for byte: the
agent's history is unchanged, because a :class:`~ogr_core.messages.Coded` is
the sentence. The undo stack keeps the ``Coded`` (``commands.step_description``)
and the window says it through its code. A name assembled from an English word
(«expand» / «shrink», «all») is one whole template per variant.

The literal names and ``commands.add_boundary_step_name`` stay as they are:
each of those has its own exact key.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

S = "step."
PAINT_MATERIAL = S + "paint_material"
OFFSET_EXTERNAL = S + "offset_external"
EXPAND_EXTERNAL = S + "expand_external"
SHRINK_EXTERNAL = S + "shrink_external"
EDIT_BOUNDARY = S + "edit_boundary"
HYDRAULIC = S + "hydraulic"
RANDOM_VARIABLE = S + "random_variable"
DELETE_RANDOM_VARIABLE = S + "delete_random_variable"
DELETE_ALL_RANDOM_VARIABLES = S + "delete_all_random_variables"

STEP_NAMES = {s.code: s for s in (
    MessageSpec(PAINT_MATERIAL, "Paint material at ({x:.2f}, {y:.2f})"),
    MessageSpec(OFFSET_EXTERNAL, "Offset External ({distance:+.2f} m)"),
    MessageSpec(EXPAND_EXTERNAL, "Expand/Shrink (expand)"),
    MessageSpec(SHRINK_EXTERNAL, "Expand/Shrink (shrink)"),
    # the operation's identifier (``boundary_edit``'s ``op``)
    MessageSpec(EDIT_BOUNDARY, "Edit boundary ({op})",
                kinds=(("op", "boundary_edit_op"),)),
    # the material as the agent named it: an id or a name
    MessageSpec(HYDRAULIC, "Hydraulic properties of {material}",
                kinds=(("material", "material_ref"),)),
    MessageSpec(RANDOM_VARIABLE, "Random variable {key}",
                kinds=(("key", "variable_key"),)),
    MessageSpec(DELETE_RANDOM_VARIABLE, "Delete random variable {key}",
                kinds=(("key", "variable_key"),)),
    MessageSpec(DELETE_ALL_RANDOM_VARIABLES, "Delete random variable all"),
)}


def step_name(code: str, **args) -> Coded:
    """The step name ``code`` with ``args``: its English, carrying the code
    and the values (v0.1.434, D412)."""
    return coded(STEP_NAMES, code, **args)


def expand_shrink_step_name(mode: str) -> Coded:
    """The name of an Expand / Shrink of the External; ``mode`` is the
    result's ``"expand"`` or ``"shrink"``."""
    return step_name(SHRINK_EXTERNAL if mode == "shrink" else EXPAND_EXTERNAL)


def delete_random_variable_step_name(key: str) -> Coded:
    """The name of ``random_variable_delete``: one variable, or ``"all"``."""
    if key == "all":
        return step_name(DELETE_ALL_RANDOM_VARIABLES)
    return step_name(DELETE_RANDOM_VARIABLE, key=key)
