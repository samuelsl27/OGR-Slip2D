# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Why a project cannot be analysed as configured, with stable codes
(v0.1.350, D335).

``check_analysis_settings`` refuses a run instead of computing a plausible
number from settings that were quietly dropped, and ``check_drawdown_
settings`` and ``drawdown_gap`` refuse a rapid drawdown the run would not
perform. Their sentences are codes here, with the English the engine wrote
and its format specs; the refusals the core asks
(``ogr_core.project.messages.REFUSALS``) arrive with codes of their own and
are nested where a sentence carries one.

The value type of a water pressure grid is a word of the sentence ("total
head"), so the mismatch is one template per type; a groundwater method is a
value the interface shows by its name.

Codes are ``setting.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, coded

GRID_TYPE_MISMATCH = "setting.grid_type_mismatch."
LINE_LOAD_MOVE = "setting.line_load_move"
FEM_FIELD_MISSING = "setting.fem_field_missing"
DESIGN_SEISMIC = "setting.design_seismic"
SHADOW_REMOVED = "setting.shadow_removed"
SHADOW_RENAMED = "setting.shadow_renamed"
DRAWDOWN_UNKNOWN = "setting.drawdown_unknown"
DRAWDOWN_NEEDS_SURFACES = "setting.drawdown_needs_surfaces"
DRAWDOWN_NO_UNDRAINED = "setting.drawdown_no_undrained"
DRAWDOWN_LINE_ABOVE = "setting.drawdown_line_above"
DRAWDOWN_GAP = "setting.drawdown_gap"

#: The grid value types, as the sentence names them.
GRID_TYPES = ("total_head", "pressure_head", "pore_pressure")

_GW = (("method", "groundwater_method"), ("wanted", "groundwater_method"))
_SHADOW = "This project sets {name} = {value}. That "

SETTING_NOTES = {s.code: s for s in (
    MessageSpec(LINE_LOAD_MOVE,
                "{reason} Move it onto the ground surface or give it an "
                "absolute orientation."),
    MessageSpec(FEM_FIELD_MISSING,
                "These materials take their pore pressure from a "
                "finite-element seepage field, and this project has no "
                "computed field: {materials}. Run the groundwater analysis "
                "first — computing now would report u = 0 everywhere, which "
                "looks like a dry slope."),
    MessageSpec(DESIGN_SEISMIC,
                "With the design standard's seismic factor {factor:g}: "
                "{reason}"),
    MessageSpec(SHADOW_REMOVED,
                _SHADOW + "setting was removed in {version}: no analysis ever "
                "read it, and it has no replacement."),
    MessageSpec(SHADOW_RENAMED,
                _SHADOW + "name was removed in {version} because the interface "
                "never showed it; set {survivor} instead. Computing now would "
                "ignore the value and report a plausible number."),
    MessageSpec(DRAWDOWN_UNKNOWN,
                "'{method}' is not a rapid-drawdown procedure, so the analysis "
                "would ignore the drawdown entirely. Available: {available}."),
    MessageSpec(DRAWDOWN_NEEDS_SURFACES,
                "Rapid drawdown defines both reservoir levels with water "
                "surfaces, so it cannot run with groundwater method "
                "'{method}'. Choose Water Surfaces."),
    MessageSpec(DRAWDOWN_NO_UNDRAINED,
                "No material is marked as having undrained behaviour, so the "
                "drawdown would not change any strength. Tick Undrained "
                "Behaviour on the low-permeability materials."),
    MessageSpec(DRAWDOWN_LINE_ABOVE,
                "The Drawdown Line lies ABOVE the Water Table. The water table "
                "is the initial reservoir level and the drawdown line the "
                "final, lower one; swap them."),
    MessageSpec(DRAWDOWN_GAP,
                "This project asks for a rapid drawdown ('{drawdown}'), and the "
                "method '{method}' does not perform one, so the factor of "
                "safety would be the ordinary DRAINED one at the lowered water "
                "level. Build the method with "
                "ogr_slip2d.analysis_runner.build_method(project, method_id), "
                "which is the one place that applies the drawdown wrapper."),
) + tuple(MessageSpec(GRID_TYPE_MISMATCH + t,
                      "The water pressure grid was built as "
                      + t.replace("_", " ") + " values, but the groundwater "
                      "method is {method}. The method decides how the grid is "
                      "read: set it to {wanted}, or build the grid without a "
                      "type.", kinds=_GW)
          for t in GRID_TYPES)}


def setting_note(code: str, **args) -> Coded:
    """The refusal ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(SETTING_NOTES, code, **args)
