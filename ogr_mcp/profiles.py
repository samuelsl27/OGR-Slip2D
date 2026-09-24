# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which tools a client sees.

A small local model loses its way among many tools, and every tool's
description costs context on every request. So there are two profiles:

* ``full`` — every tool (Claude, OpenAI, large models);
* ``compact`` — the ones a complete build-run-read cycle needs, with
  ``model_define`` doing the whole geometry in one call and ``python_exec``
  covering the rest.

``--toolsets`` overrides the profile with an explicit list of toolsets.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

TOOLSETS: dict[str, tuple[str, ...]] = {
    "core": ("server_info", "catalog", "project_new", "project_open",
             "project_save", "project_close", "project_list",
             "project_summary", "project_validate", "project_get"),
    "model": ("model_define", "boundary_add", "boundary_edit",
              "material_set", "material_delete", "material_assign",
              "external_reshape", "slope_angle_change", "geometry_cleanup"),
    "settings": ("settings_get", "settings_set", "analysis_configure"),
    "analysis": ("analysis_run", "job_get", "job_cancel", "job_list",
                 "results_get", "surface_evaluate"),
    "loads": ("load_set", "load_delete", "seismic_set",
              "seismic_record_set", "seismic_record_delete"),
    "supports": ("support_type_set", "support_type_delete", "support_set",
                 "support_pattern_add", "support_delete", "support_ungroup"),
    "search": ("tension_crack_set", "focus_set", "focus_delete",
               "user_surface_add", "user_surface_delete"),
    "annotations": ("annotation_set", "annotation_delete",
                    "annotation_to_boundary", "properties_table"),
    "files": ("dxf_inspect", "dxf_import", "dxf_export", "report_generate",
              "properties_import"),
    "view": ("model_render",),
    "history": ("project_history",),
    "python": ("python_exec",),
}

PROFILES: dict[str, tuple[str, ...]] = {
    "full": tuple(t for tools in TOOLSETS.values() for t in tools),
    "compact": ("server_info", "catalog", "project_new", "project_open",
                "project_save", "project_summary", "model_define",
                "analysis_configure", "analysis_run", "job_get",
                "job_cancel", "results_get", "model_render", "python_exec"),
}


def select(profile: str = "full", toolsets=None) -> tuple[str, ...]:
    """The tool names to publish, in a stable order.

    Stable because the 2026-07-28 specification asks servers to list tools
    deterministically, so clients can cache the list and a model's prompt
    cache is not invalidated by a reshuffle.
    """
    if toolsets:
        unknown = [t for t in toolsets if t not in TOOLSETS]
        if unknown:
            raise ValueError(f"unknown toolset(s) {unknown}; "
                             f"known: {list(TOOLSETS)}")
        wanted = [t for ts in toolsets for t in TOOLSETS[ts]]
        if "server_info" not in wanted:
            wanted.insert(0, "server_info")
        return tuple(dict.fromkeys(wanted))
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; "
                         f"known: {list(PROFILES)}")
    return PROFILES[profile]
