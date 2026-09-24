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
* ``PENDING``: the phase of spec 008 that will map it, or ``owner`` when
  it waits on a decision of the project's owner. The test holds the number
  of pending actions to a ceiling that can only go DOWN, and phase F4
  closes with none left.

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
    # --- v0.1.196 (F2) ---------------------------------------------
    "load_demo": "project_new",
    "import_dxf": "dxf_import",
    "export_dxf": "dxf_export",
    "generate_report": "report_generate",
    "import_props": "properties_import",
    "copy_boundary": "boundary_edit",
    "scale_boundary": "boundary_edit",
    "rotate_boundary": "boundary_edit",
    "simplify_boundary": "boundary_edit",
    "expand_shrink": "external_reshape",
    "change_slope": "slope_angle_change",         # v0.1.198
    "geometry_cleanup": "geometry_cleanup",
    "add_dist": "load_set",
    "add_line": "load_set",
    "modify_load": "load_set",
    "del_load": "load_delete",
    "seismic": "seismic_set",
    "seismic_records": "seismic_record_set",
    "def_support": "support_type_set",
    "add_support": "support_set",
    "modify_support": "support_set",
    "move_support": "support_set",
    "stretch_support": "support_set",
    "support_pattern": "support_pattern_add",
    "del_support": "support_delete",
    "ungroup_pattern": "support_ungroup",
    "def_tension_crack": "tension_crack_set",
    # --- v0.1.200 (F3a): groundwater ------------------------------------
    "wp_grid": "water_grid_set",
    "gw_hydraulic": "hydraulic_set",
    "gen_mesh": "mesh_generate",
    "reset_mesh": "mesh_reset",
    "gw_bcs": "seepage_bc_set",
    "gw_transient": "transient_set",
    "gw_compute": "groundwater_run",
    "gw_interpret": "groundwater_results",
    "drawdown_sweep": "drawdown_sweep_run",
    "focus_window": "focus_set",
    "focus_line": "focus_set",
    "focus_point": "focus_set",
    "focus_tangent": "focus_set",
    "focus_manage": "focus_set",
    "surf_centre_radius": "user_surface_add",
    "surf_three_points": "user_surface_add",
    "surf_manage": "user_surface_delete",
    "add_text": "annotation_set",
    "measure": "annotation_set",
    "dim_len": "annotation_set",
    "dim_ang": "annotation_set",
    "dim_x": "annotation_set",
    "dim_y": "annotation_set",
    "draw_line": "annotation_set",
    "draw_arrow": "annotation_set",
    "draw_polyline": "annotation_set",
    "draw_polygon": "annotation_set",
    "draw_rect": "annotation_set",
    "draw_circle": "annotation_set",
    "add_axes": "annotation_set",
    "add_image": "annotation_set",
    "ann_show_all": "annotation_set",
    "ann_hide_all": "annotation_set",
    "ann_manage": "annotation_set",
    "ann_delete_all": "annotation_delete",
    "convert_tool": "annotation_to_boundary",
    "mat_tab": "properties_table",
    "sup_tab": "properties_table",
    "hyd_tab": "properties_table",
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
    # ``change_slope`` waited here for the owner (v0.1.196: the old
    # function rotated the WHOLE External); rewritten in v0.1.198.
    # F3 — statistics, back analysis, optimisation (F3b). The nine
    # groundwater actions were mapped in v0.1.200 (F3a).
    **{k: "F3" for k in (
        "stat_vars", "stat_compute", "stat_show", "back_analysis",
        "optimize_surfaces")},
}

#: The most actions allowed to be pending. Lower it with every phase;
#: never raise it (a raise needs its reason in a changelog).
PENDING_CEILING = 5


def coverage() -> dict:
    """Counts, for ``server_info`` and the documentation."""
    return {"mapped": len(MAPPED), "ui_only": len(UI_ONLY),
            "pending": len(PENDING),
            "pending_by_phase": {ph: sum(1 for v in PENDING.values()
                                         if v == ph)
                                 for ph in sorted(set(PENDING.values()))}}
