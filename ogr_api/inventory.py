# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Every action of the main window, and what an agent uses instead.

Rule 3 of AGENTS.md says every action must be reachable from a menu,
because a module was once built, tested and shipped invisible. Spec 008
asks the same of the agent: everything the program can do, an agent can do.
This table is how that is checked rather than claimed —
``tests/test_action_inventory_v1195.py`` builds the real window and fails
when an action appears that this table does not classify.

Each action (the keys of ``MainWindow._actions``) is exactly one of:

* ``MAPPED``: the ``ogr_api`` operation that does the same to the model;
* ``UI_ONLY``: why it has no meaning without the window (zoom, printing,
  help) — with the reason written, never left implicit;
* ``PENDING``: the phase of spec 008 that will map it. The test holds the
  number of pending actions to a ceiling that can only go DOWN, and phase
  F4 closes with none left.

Only strings live here: no Qt, no interface import.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

MAPPED: dict[str, str] = {
    # File / Edit
    "new": "project_new",
    "open": "project_open",
    "save": "project_save",
    "save_as": "project_save",
    "undo": "project_history",
    "redo": "project_history",
    "export_image": "model_render",
    "copy_img": "model_render",
    # Analysis
    "project_settings": "settings_set",
    "info_viewer": "project_summary",
    "compute": "analysis_run",
    "interpret": "results_get",
    "analysis_notes": "results_get",
    # Boundaries
    "add_ext": "boundary_add",
    "add_mat": "boundary_add",
    "add_wt": "boundary_add",
    "add_drawdown": "boundary_add",
    "add_piezo": "boundary_add",
    "add_crack": "boundary_add",
    "add_weak_layer": "boundary_add",
    "add_aniso_surface": "boundary_add",
    "block_object": "boundary_add",
    "del_boundary": "boundary_edit",
    "move_boundary": "boundary_edit",
    "edit_coordinates": "boundary_edit",
    "move_vertex": "boundary_edit",
    "insert_vertex": "boundary_edit",
    "delete_vertex": "boundary_edit",
    "convert_boundary": "boundary_edit",
    # Properties
    "def_materials": "material_set",
    "assign": "material_assign",
    "assign_material": "material_assign",
    "assign_water_surface": "material_set",
    # Surfaces: the search options, the grid, slope limits and the moment
    # axis are all settings (``search.*``), reachable by path.
    "surface_opts": "settings_set",
    "auto_grid": "analysis_configure",
    "add_grid": "analysis_configure",
    "slope_limits": "settings_set",
    "slope_limits_move": "settings_set",
    "slope_limits_reset": "settings_set",
    "moment_axis": "settings_set",
    "moment_axis_reset": "settings_set",
    # Window
    "terminal": "python_exec",
}

UI_ONLY: dict[str, str] = {
    "exit": "closes the application window",
    "zoom_all": "canvas navigation; model_render draws the whole model",
    "zoom_in": "canvas navigation",
    "zoom_out": "canvas navigation",
    "zoom_window": "canvas navigation",
    "zoom_mouse": "canvas navigation",
    "pan": "canvas navigation",
    "select": "mouse selection; operations address objects by id or name",
    "selection_filter": "filters what a mouse click selects",
    "grid_toggle": "canvas display",
    "ruler_toggle": "canvas display",
    "grayscale": "canvas display",
    "display_opts": "canvas display",
    "snap_opts": "mouse snapping; an agent gives exact coordinates",
    "prefs": "application preferences (language, ...), not the model",
    "pic_bitmap": "format of the clipboard picture",
    "pic_vector": "format of the clipboard picture",
    "page_setup": "printing",
    "print_preview": "printing",
    "print": "printing (a placeholder in the interface too)",
    "help": "help pages",
    "about": "about box",
    "check_updates": "contacts nothing by design",
}

PENDING: dict[str, str] = {
    # F2 — loads, supports, crack properties, seismic, focus, user
    # surfaces, annotations, DXF, report, boundary transforms.
    **{k: "F2" for k in (
        "load_demo", "import_dxf", "export_dxf", "generate_report",
        "import_props", "copy_boundary", "scale_boundary", "rotate_boundary",
        "expand_shrink", "change_slope", "simplify_boundary",
        "geometry_cleanup", "add_dist", "add_line", "seismic",
        "seismic_records", "del_load", "modify_load", "add_support",
        "support_pattern", "del_support", "stretch_support",
        "modify_support", "move_support", "ungroup_pattern", "def_support",
        "def_tension_crack", "focus_window", "focus_line", "focus_point",
        "focus_tangent", "focus_manage", "surf_centre_radius",
        "surf_three_points", "surf_manage", "add_text", "measure",
        "dim_len", "dim_ang", "dim_x", "dim_y", "draw_line", "draw_arrow",
        "draw_polyline", "draw_polygon", "draw_rect", "draw_circle",
        "add_axes", "add_image", "convert_tool", "ann_show_all",
        "ann_hide_all", "ann_delete_all", "ann_manage", "mat_tab",
        "sup_tab", "hyd_tab")},
    # F3 — groundwater FE, statistics, back analysis, optimisation.
    **{k: "F3" for k in (
        "wp_grid", "gw_hydraulic", "gen_mesh", "reset_mesh", "gw_bcs",
        "gw_transient", "gw_compute", "gw_interpret", "drawdown_sweep",
        "stat_vars", "stat_compute", "stat_show", "back_analysis",
        "optimize_surfaces")},
}

#: The most actions allowed to be pending. Lower it with every phase;
#: never raise it (a raise needs its reason in a changelog).
PENDING_CEILING = 71


def coverage() -> dict:
    """Counts, for ``server_info`` and the documentation."""
    return {"mapped": len(MAPPED), "ui_only": len(UI_ONLY),
            "pending": len(PENDING),
            "pending_by_phase": {ph: sum(1 for v in PENDING.values()
                                         if v == ph)
                                 for ph in sorted(set(PENDING.values()))}}
