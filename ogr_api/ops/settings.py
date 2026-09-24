# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Reading and changing the analysis settings.

``settings_set`` takes any setting by its dotted path and checks it
(``ogr_api.settings_schema``); ``analysis_configure`` is the short, typed
version of the handful a caller changes most, written for a model with a
small context that should not have to learn eighty field names to run a
Spencer analysis with a slope search.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Any, Optional

from ..errors import InvalidArgument
from ..results import json_safe
from . import operation


@operation("settings_get", toolset="settings")
def settings_get(ws, project_id: Optional[str] = None,
                 section: Optional[str] = None) -> dict:
    """Every setting (or one section) with its value, type and choices."""
    from ..settings_schema import describe, settings_diagnostics

    handle = ws.get(project_id)
    with ws.reading(handle.id, "settings_get") as project:
        return {"project_id": handle.id,
                "settings": describe(project, section),
                **settings_diagnostics(project)}


@operation("settings_set", toolset="settings", mutates=True)
def settings_set(ws, changes: dict,
                 project_id: Optional[str] = None) -> dict:
    """Change settings by dotted path, all or nothing."""
    from ..settings_schema import apply_changes, settings_diagnostics

    def edit(project):
        out = apply_changes(project, changes)
        return {"changed": json_safe(out["changed"]),
                **settings_diagnostics(project)}

    return ws.mutate(project_id, "Change settings", edit)


@operation("analysis_configure", toolset="settings", mutates=True)
def analysis_configure(ws, project_id: Optional[str] = None,
                       methods: Optional[list] = None,
                       surface_type: Optional[str] = None,
                       search_method: Optional[str] = None,
                       num_slices: Optional[int] = None,
                       grid: Any = None,
                       radius_increment: Optional[int] = None,
                       failure_direction: Optional[str] = None,
                       tolerance: Optional[float] = None,
                       design_standard: Optional[str] = None) -> dict:
    """The common analysis settings in one typed call."""
    changes: dict = {}
    if methods is not None:
        changes["methods.enabled_methods"] = methods
    if surface_type is not None:
        changes["search.surface_type"] = surface_type
    if search_method is not None:
        changes["search.search_method"] = search_method
    if num_slices is not None:
        changes["methods.num_slices"] = num_slices
    if tolerance is not None:
        changes["methods.tolerance"] = tolerance
    if radius_increment is not None:
        changes["search.radius_increment"] = radius_increment
    if failure_direction is not None:
        aliases = {"left_to_right": "L2R", "l2r": "L2R",
                   "right_to_left": "R2L", "r2l": "R2L"}
        fd = aliases.get(str(failure_direction).strip().lower(),
                         failure_direction)
        changes["units.failure_direction"] = fd
    if grid is not None:
        if grid == "auto":
            changes.update({"search.grid_x_min": None,
                            "search.grid_x_max": None,
                            "search.grid_y_min": None,
                            "search.grid_y_max": None})
        elif isinstance(grid, dict):
            names = {"x_min": "grid_x_min", "x_max": "grid_x_max",
                     "y_min": "grid_y_min", "y_max": "grid_y_max",
                     "nx": "grid_nx", "ny": "grid_ny"}
            for k, v in grid.items():
                if k not in names:
                    raise InvalidArgument(
                        f"grid has no key {k!r}.",
                        hint=f"Keys: {list(names)}; nx and ny are the "
                             f"number of INTERVALS (points = nx + 1).")
                changes[f"search.{names[k]}"] = v
        else:
            raise InvalidArgument("grid is 'auto' or an object with "
                                  "x_min, x_max, y_min, y_max, nx, ny.")
    if design_standard is not None:
        if design_standard in ("off", "none"):
            changes["design_standard.enabled"] = False
            changes["design_standard.standard"] = "none"
        else:
            changes["design_standard.enabled"] = True
            changes["design_standard.standard"] = design_standard
    if not changes:
        raise InvalidArgument("Nothing to configure.",
                              hint="Pass at least one argument.")
    return settings_set(ws, changes=changes, project_id=project_id)
