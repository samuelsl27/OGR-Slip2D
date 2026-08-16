# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
MainWindow — central application window of OGR Slip2D (v0.1.1).

v0.1.1 changes over v0.1.0:
    - Pan, Zoom Window, Zoom Mouse now switch the canvas into a proper
      ToolMode with cursor feedback and interactive behaviour.
    - Display Options dialog fully wired up (toggle a checkbox → canvas
      re-renders).
    - Surface Options dialog under Surfaces menu (the spec position).
    - Spencer and GLE/Morgenstern-Price included in the compute pipeline.
    - Window → Terminal exposes an embedded Python REPL with access to
      the live project, canvas, and OGR API.
    - Analysis → Interpret opens a separate InterpretWindow with its
      own File/Data/Query/Groundwater/Statistics/Tools menus.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
    cleanup_boundaries,
    find_intersections,
    has_self_intersections,
    offset_polygon,
    remove_duplicate_vertices,
    rotate as g_rotate,
    scale as g_scale,
    simplify_rdp,
    change_slope_angle,
    convert_boundary,
)
from ogr_core.materials import Material, MohrCoulomb
from ogr_core.project import Project, save_results
from ogr_core.project.commands import (
    AddBoundaryCommand,
    AssignMaterialCommand,
    PaintRegionCommand,
    CommandStack,
    MacroCommand,
    RemoveBoundaryCommand,
    ReplaceBoundaryCommand,
)
# v0.1.77 — the method classes and the search classes are no longer
# imported here. The window does not build an analysis any more; it asks
# ``ogr_slip2d.analysis_runner`` for one, which is what lets the CLI ask
# for the same one.

from .canvas import CanvasView, DisplayOptions, ToolMode
from .dialogs import (
    AboutDialog,
    AssignMaterialDialog,
    ChangeSlopeAngleDialog,
    ComputeProgressDialog,
    ConvertBoundaryDialog,
    DisplayOptionsDialog,
    EditCoordinatesDialog,
    ExpandShrinkDialog,
    GeometryCleanupDialog,
    MaterialPropertiesDialog,
    PreferencesDialog,
    ProjectSettingsDialog,
    RotateDialog,
    ScaleDialog,
    SelectionFilterDialog,
    SelectionFilterState,
    SimplifyBoundaryDialog,
    SurfaceOptionsDialog,
)
from .i18n import set_language, tr
from .interpret_window import InterpretWindow
from .resources import icon
from .themes import apply_theme
from .widgets import AssignMaterialsPanel, OgrStatusBar, ResultsDock, TerminalDock
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class _ComputeWorker(QThread):
    finished_result = Signal(object)
    progress = Signal(int, int)
    failed = Signal(str)

    def __init__(self, project: Project, method_ids: list) -> None:
        # v0.1.77 — the design-factor substitution, the method table, the
        # rapid-drawdown wrapper and the six-way search dispatch all moved
        # to ``ogr_slip2d.analysis_runner``, which contains no Qt. That is
        # the point: the command line can now run a project exactly as
        # configured instead of rebuilding a different analysis out of its
        # own defaults, which is what it had been doing since v0.1.59.
        # What is left in this class is the thread and the signals.
        super().__init__()
        self.project = project
        self.method_ids = (list(method_ids) if method_ids
                           else ["bishop_simplified"])
        self.results: dict = {}
        self.warnings: list[str] = []
        self.factor_report = None

    def build_search(self, method_id: str):
        """The configured search object for one method.

        v0.1.38 — exposed so the Overall Slope probabilistic analysis can
        rebuild EXACTLY the same search (same method, same search
        settings) once per sample, instead of duplicating this dispatch.
        v0.1.77 — kept as a delegate: the dispatch it used to capture by
        running a throwaway worker now lives in the shared runner, and
        callers can reach it without constructing a QThread.
        """
        from ogr_slip2d.analysis_runner import build_search
        try:
            return build_search(self.project, method_id)
        except Exception:  # noqa: BLE001
            return None

    def run(self) -> None:
        try:
            from ogr_slip2d.analysis_runner import run_analysis
            outcome = run_analysis(
                self.project, self.method_ids,
                progress_cb=lambda done, total: self.progress.emit(done, total))
            # v0.1.31 — keep the results on the instance so the same
            # search-building logic can be reused synchronously (the
            # per-stage transient factors of safety do exactly that).
            self.results = outcome.results
            self.warnings = outcome.warnings
            self.factor_report = outcome.factor_report
            self.finished_result.emit(outcome.results)
        except Exception as e:  # noqa: BLE001
            # v0.1.74 found what this blanket handler costs: it catches a
            # TypeError from a programming mistake exactly as it catches a
            # bad model, so a broken call signature reads as "analysis
            # failed". The type name is included for that reason — it is
            # the only thing that distinguishes the two on screen.
            self.failed.emit(f"{type(e).__name__}: {e}")


# ======================================================================
class _DrawdownSweepWorker(QThread):
    """The drawdown level sweep, off the GUI thread.

    v0.1.70 — a sweep is N full searches, so it cannot run the way
    ``_compute_statistics`` does, synchronously on the GUI thread with no
    progress: on a real model the window would simply stop responding for
    minutes. It reuses ``_ComputeWorker.build_search`` so the sweep
    honours exactly the search the user configured.
    """

    finished_result = Signal(object)
    progress = Signal(int, int)
    failed = Signal(str)

    def __init__(self, project: Project, method_ids: list,
                 n_levels: int, include_total: bool) -> None:
        super().__init__()
        self.project = project
        self.method_ids = list(method_ids)
        self.n_levels = int(n_levels)
        self.include_total = bool(include_total)
        self.result = None

    def run(self) -> None:                       # noqa: D102
        try:
            from ogr_core.statistics import run_drawdown_sweep

            helper = _ComputeWorker(self.project, self.method_ids)
            searches = {mid: helper.build_search(mid)
                        for mid in self.method_ids}
            missing = [mid for mid, s in searches.items() if s is None]
            if missing:
                self.failed.emit(
                    f"Could not build the search for: {', '.join(missing)}")
                return

            def factory(mid):
                # A fresh search per level would rebuild the same object;
                # the search holds no per-project state, so one is enough.
                return searches[mid]

            self.result = run_drawdown_sweep(
                self.project, factory, self.method_ids,
                n_levels=self.n_levels, include_total=self.include_total,
                progress_cb=lambda d, t: self.progress.emit(d, t))
            self.finished_result.emit(self.result)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}")


# ======================================================================
class MainWindow(QMainWindow):
    VERSION = "0.1.82"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"OGR Slip2D v{self.VERSION} — OpenGeoRock Suite")
        self.register_session()
        self.resize(1400, 900)

        self.project: Project = Project("Untitled")
        self.command_stack = CommandStack()
        self.active_theme = "light"
        self.last_search_result = None
        self.last_search_results: dict = {}
        self.interpret_windows: list[InterpretWindow] = []

        # v0.1.2 — selection filter state
        self.selection_filter = SelectionFilterState()

        # v0.1.4 — assign materials floating panel state
        self.assign_panel: Optional[AssignMaterialsPanel] = None
        self._assign_active_material_id: Optional[str] = None

        # Central canvas
        self.canvas = CanvasView(self.project, self)
        self.canvas.selection_filter = self.selection_filter
        self.setCentralWidget(self.canvas)
        self.canvas.tool_mode_changed.connect(self._sync_tool_actions)
        # v0.1.2 — interactive editing signals
        self.canvas.boundary_drawn.connect(self._on_boundary_drawn)
        self.canvas.boundary_clicked.connect(self._on_boundary_clicked)
        self.canvas.vertex_moved.connect(self._on_vertex_moved)
        self.canvas.vertex_inserted.connect(self._on_vertex_inserted)
        self.canvas.vertex_deleted.connect(self._on_vertex_deleted)
        # v0.1.8 — right-click delete/modify on loads
        self.canvas.load_action_requested.connect(self._on_load_action)
        # v0.1.9 — drag-to-move boundary
        self.canvas.boundary_dragged.connect(self._on_boundary_dragged)
        # v0.1.9 — right-click context menu actions
        self.canvas.boundary_action_requested.connect(
            self._on_boundary_action_requested
        )
        self.canvas.vertex_action_requested.connect(
            self._on_vertex_action_requested
        )
        # v0.1.15 — right-click on a support
        self.canvas.support_action_requested.connect(
            self._on_support_action_requested
        )
        self.canvas.canvas_right_click_xy.connect(
            self._on_canvas_right_click_xy
        )
        self.canvas.vertex_drag_finished.connect(self._on_vertex_drag_finished)
        self.canvas.canvas_click_xy.connect(self._on_canvas_assign_click)

        # Results dock
        self.results_dock = ResultsDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.results_dock)

        # Terminal dock (hidden by default)
        self.terminal_dock = TerminalDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)
        self.terminal_dock.attach_context(self.project, self.canvas, self)
        self.terminal_dock.hide()

        # v0.1.7 — listen to project changes to update conditional UI
        # availability (Drawdown / Pressure Grid only when settings allow,
        # Tension Crack 1-only rule, etc.)
        self.project.add_listener(self._on_project_event)

        # Status bar
        self.ogr_status = OgrStatusBar(self)
        self.setStatusBar(self.ogr_status)
        self.canvas.cursor_moved.connect(self.ogr_status.update_coords)
        self.canvas.status_message.connect(lambda m: self.ogr_status.showMessage(m, 3000))
        self.ogr_status.snap_toggled.connect(self._on_snap_toggle)
        self.ogr_status.grid_toggled.connect(self._on_grid_toggle)
        self.ogr_status.ortho_toggled.connect(self._on_ortho_toggle)
        self.ogr_status.osnap_toggled.connect(self._on_osnap_toggle)
        # v0.1.3 — manual coord input forwards to the canvas' drawing state
        self.ogr_status.manual_coords_submitted.connect(self._on_manual_coords)

        # Menus & toolbar
        self._actions: dict[str, QAction] = {}
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        # v0.1.29 — apply the Groundwater dependency rules from the start
        self._update_groundwater_actions()
        self._update_statistics_actions()

        # v0.1.51 (phase M1) — data tips, plus a dialog and keyboard
        # shortcuts for the snap engine that ALREADY existed in the
        # canvas (ogr_gui/canvas/snap_engine.py). The audit wrongly
        # listed snapping as missing: the engine and the status-bar
        # toggles were there, only the configuration dialog, the F3/F8/F9
        # keys and the data tips were not.
        from ogr_gui.data_tips import DataTipMode
        self.data_tip_mode = DataTipMode.MAXIMUM
        self._build_m1_extras()

        # v0.1.5: start with an EMPTY project. User can load demo via
        # File → Load Demo Slope.
        self.ogr_status.showMessage(
            tr("Ready") + " — File → Load Demo Slope to start with a sample model.",
            6000,
        )
        # v0.1.7 — first availability refresh
        self.refresh_action_availability()

    # ==================================================================
    def _mk(self, key: str, text: str, slot, icon_key: Optional[str] = None,
            shortcut: Optional[str] = None, checkable: bool = False) -> QAction:
        act = QAction(tr(text), self)
        if icon_key:
            act.setIcon(icon(icon_key))
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        if checkable:
            act.setCheckable(True)
        act.triggered.connect(slot)
        self._actions[key] = act
        return act

    def _build_actions(self) -> None:
        # File
        self._mk("new", "New Project", self.act_new, "new_project", "Ctrl+N")
        self._mk("load_demo", "Load Demo Slope", self.act_load_demo, None)
        self._mk("open", "Open Project...", self.act_open, "open_project", "Ctrl+O")
        self._mk("save", "Save", self.act_save, "save", "Ctrl+S")
        self._mk("save_as", "Save As...", self.act_save_as, "save_as", "Ctrl+Shift+S")
        self._mk("import_dxf", "Import DXF...", self.act_import_dxf, "import_dxf")
        self._mk("export_dxf", "Export DXF...", self.act_export_dxf, "export_dxf")
        self._mk("generate_report", "Generate Report...", self.act_generate_report, "print")
        self._mk("print", "Print...", self.act_print, "print", "Ctrl+P")
        self._mk("prefs", "Preferences...", self.act_preferences, "preferences")
        self._mk("exit", "Exit", self.close, None, "Ctrl+Q")

        # Edit
        self._mk("undo", "Undo", self.act_undo, "undo", "Ctrl+Z")
        self._mk("redo", "Redo", self.act_redo, "redo", "Ctrl+Y")
        self._mk("copy_img", "Copy Image", self.act_copy_image, "copy")

        # View / navigation (checkable for the tool-mode actions)
        self._mk("zoom_all", "Zoom All", self.canvas.zoom_all, "zoom_all", "F2")
        self._mk("zoom_in", "Zoom In",
                 lambda: self.canvas.zoom_by(1.25), "zoom_in", "F5")
        self._mk("zoom_out", "Zoom Out",
                 lambda: self.canvas.zoom_by(1 / 1.25), "zoom_out", "F4")

        self._mk("pan", "Pan",
                 lambda: self._set_tool(ToolMode.PAN),
                 "pan", "F10", checkable=True)
        self._mk("zoom_window", "Zoom Window",
                 lambda: self._set_tool(ToolMode.ZOOM_WINDOW),
                 "zoom_window", None, checkable=True)
        self._mk("zoom_mouse", "Zoom Mouse",
                 lambda: self._set_tool(ToolMode.ZOOM_MOUSE),
                 None, None, checkable=True)
        self._mk("select", "Select",
                 lambda: self._set_tool(ToolMode.SELECT),
                 None, "Escape", checkable=True)
        self._actions["select"].setChecked(True)

        self._mk("grid_toggle", "Grid", self._toggle_grid, "grid", "F7", checkable=True)
        # v0.1.51 — Snap dialog (the F3 / F8 / F9 keys are bound directly)
        self._mk("snap_opts", "Snap...", self._snap_options, None,
                 shortcut="Ctrl+Shift+S")
        self._actions["grid_toggle"].setChecked(True)
        self._mk("ruler_toggle", "Ruler", self._toggle_ruler, "ruler", None, checkable=True)
        self._actions["ruler_toggle"].setChecked(True)
        self._mk("grayscale", "Grayscale", self._toggle_grayscale, None, None, checkable=True)
        self._mk("display_opts", "Display Options...", self.act_display_options, "display_options", "Ctrl+D")

        # Analysis
        self._mk("project_settings", "Project Settings...", self.act_project_settings, "project_settings", "Ctrl+J")
        self._mk("compute", "Compute", self.act_compute, "compute", "Ctrl+T")
        self._mk("interpret", "Interpret", self.act_interpret, "interpret")
        self._mk("info_viewer", "Info Viewer", self.act_info_viewer, "info_viewer", "Ctrl+I")

        # Boundaries — v0.1.2 interactive tools
        self._mk("add_ext", "Add External Boundary",
                 lambda: self._set_tool(ToolMode.DRAW_EXTERNAL), "ext_boundary", "Ctrl+1")
        self._mk("add_mat", "Add Material Boundary",
                 lambda: self._set_tool(ToolMode.DRAW_MATERIAL), "mat_boundary", "Ctrl+2")
        self._mk("add_wt", "Add Water Table",
                 lambda: self._set_tool(ToolMode.DRAW_WATER_TABLE), "water_table", "Ctrl+3")
        self._mk("add_drawdown", "Add Drawdown Line",
                 lambda: self._set_tool(ToolMode.DRAW_DRAWDOWN), "piezo_line", "Ctrl+4")
        self._mk("add_piezo", "Add Piezometric Line",
                 lambda: self._set_tool(ToolMode.DRAW_PIEZOMETRIC), "piezo_line", "Ctrl+5")
        self._mk("add_crack", "Add Tension Crack",
                 lambda: self._set_tool(ToolMode.DRAW_TENSION_CRACK), "tension_crack", "Ctrl+6")
        # v0.1.23 — Water Pressure Grid editor (Phase 0 groundwater)
        self._mk("wp_grid", "Water Pressure Grid...",
                 self._edit_water_pressure_grid, "water_table")
        # v0.1.29 — Groundwater mode (Phase 5). Ordered by the real
        # workflow, which is sequential and has hard dependencies.
        # v0.1.38 — Statistics (Phase P5 of the probabilistic plan)
        self._mk("back_analysis", "Back Analysis of Support Force...",
                 self._back_analysis, None)
        self._mk("stat_vars", "Random Variables...",
                 self._edit_random_variables, None)
        self._mk("stat_compute", "Compute Statistics",
                 self._compute_statistics, None)
        self._mk("stat_show", "Show Statistics",
                 self._show_statistics, None)
        self._mk("gw_hydraulic", "Define Hydraulic Properties...",
                 self._define_hydraulic_properties, None)
        self._mk("gen_mesh", "Generate FE Mesh...",
                 self._generate_fem_mesh, None)
        self._mk("reset_mesh", "Reset FE Mesh",
                 self._reset_fem_mesh, None)
        self._mk("gw_bcs", "Set Boundary Conditions...",
                 self._set_boundary_conditions, None)
        self._mk("gw_transient", "Transient Groundwater...",
                 self._edit_transient_stages, None)
        self._mk("gw_compute", "Compute Groundwater",
                 self._compute_groundwater, None)
        self._mk("gw_interpret", "Interpret Groundwater",
                 self._interpret_groundwater, None)
        # v0.1.70 — the drawdown level that is critical is not always the
        # total one, and nothing in the interface used to suggest looking.
        self._mk("drawdown_sweep", "Drawdown Level Sweep...",
                 self._drawdown_sweep, None)

        self._mk("del_boundary", "Delete Boundary",
                 lambda: self._set_tool(ToolMode.DELETE_BOUNDARY), "boundary_delete")
        self._mk("move_boundary", "Move Boundary",
                 lambda: self._set_tool(ToolMode.MOVE_BOUNDARY), None)
        self._mk("copy_boundary", "Copy Boundary",
                 lambda: self._set_tool(ToolMode.COPY_BOUNDARY), "copy")

        self._mk("scale_boundary", "Scale Boundary...",
                 self.act_scale_boundary, None)
        self._mk("rotate_boundary", "Rotate Boundary...",
                 self.act_rotate_boundary, None)
        self._mk("expand_shrink", "Expand / Shrink External...",
                 self.act_expand_shrink, None)
        self._mk("change_slope", "Change Slope Angle...",
                 self.act_change_slope_angle, None)
        self._mk("convert_boundary", "Convert Boundary...",
                 lambda: self._set_tool(ToolMode.CONVERT_BOUNDARY), None)
        self._mk("simplify_boundary", "Simplify Boundary...",
                 self.act_simplify_boundary, None)
        self._mk("geometry_cleanup", "Geometry Cleanup...",
                 self.act_geometry_cleanup, None)
        self._mk("edit_coordinates", "Edit Coordinates...",
                 self.act_edit_coordinates, None)

        self._mk("move_vertex", "Move Vertex",
                 lambda: self._set_tool(ToolMode.MOVE_VERTEX), "move_vertex")
        self._mk("insert_vertex", "Insert Vertex",
                 lambda: self._set_tool(ToolMode.INSERT_VERTEX), "insert_vertex")
        self._mk("delete_vertex", "Delete Vertex",
                 lambda: self._set_tool(ToolMode.DELETE_VERTEX), "delete_vertex")

        self._mk("assign_material", "Assign Material",
                 lambda: self._set_tool(ToolMode.ASSIGN_MATERIAL), "assign")

        self._mk("selection_filter", "Selection Filter...",
                 self.act_selection_filter, None, "Ctrl+F")

        # Loading
        self._mk("add_dist", "Add Distributed Load...", self.act_add_distributed_load, "distributed_load")
        self._mk("add_line", "Add Line Load...", self.act_add_line_load, "line_load")
        self._mk("seismic", "Seismic Load...", self.act_seismic_load, "seismic_load")
        self._mk("del_load", "Delete Load", self.act_delete_load, "delete_load")

        # Support
        self._mk("add_support", "Add Support",
                 self.act_add_support, "add_support")
        self._mk("support_pattern", "Add Support Pattern...",
                 self.act_add_support_pattern, "support_pattern")
        self._mk("del_support", "Delete Support",
                 self.act_delete_support_mode, "delete_support")
        self._mk("stretch_support", "Stretch Support",
                 self.act_stretch_support_mode, "delete_support")

        # Surfaces — Surface Options is HERE (as per spec)
        self._mk("surface_opts", "Surface Options...",
                 self.act_surface_options, "surface_options")
        self._mk("auto_grid", "Auto Grid", self.act_auto_grid, "auto_grid")
        self._mk("add_grid", "Add Grid...", self.act_add_grid, "auto_grid")
        self._mk("surf_3pts", "Add Surface", self.act_add_surface, "surface_3pts")
        # v0.1.55 (phase M4) — focus objects, optimisation and the
        # remaining surface entries.
        from ogr_slip2d.focus import FocusKind as _FK
        for key, label, kind in (
            ("focus_window", "Add Focus Window...", _FK.WINDOW),
            ("focus_line", "Add Focus Line...", _FK.LINE),
            ("focus_point", "Add Focus Point...", _FK.POINT),
            ("focus_tangent", "Add Focus Tangent...", _FK.TANGENT),
        ):
            self._mk(key, label,
                     lambda _c=False, k=kind: self._add_focus(k), None)
        self._mk("focus_manage", "Manage Focus Objects...",
                 self._manage_focus, None)
        self._mk("optimize_surfaces", "Optimize Surfaces...",
                 self._optimize_surfaces, None)
        self._mk("surf_centre_radius", "Add Surface (centre and radius)...",
                 self._add_surface_centre_radius, None)
        self._mk("slope_limits_move", "Move Slope Limits...",
                 self._move_slope_limits, None)
        self._mk("slope_limits_reset", "Reset Slope Limits",
                 self._reset_slope_limits, None)
        # v0.1.56 — was a placeholder message; the limits now exist on
        # SearchSettings and reach the engine (v0.1.55), so Define is
        # simply Move with the same dialog.
        self._mk("slope_limits", "Define Limits...",
                 self._move_slope_limits, "slope_limits")

        # Properties
        self._mk("def_materials", "Define Materials...", self.act_define_materials, "define_materials")
        self._mk("def_support", "Define Support...",
                 self.act_define_support, "define_support")
        self._mk("assign", "Assign Materials",
                 self.act_open_assign_panel, "assign")
        # v0.1.7
        self._mk("def_tension_crack", "Define Tension Crack...",
                 self.act_define_tension_crack, None)
        # v0.1.62
        self._mk("assign_water_surface", "Assign Water Surface...",
                 self.act_assign_water_surface, None)

        # Tools
        from ogr_core.annotations import AnnotationKind as _AK

        # v0.1.56 (phase M5) — the remaining minor-menu entries.
        self._mk("import_props", "Import Properties...",
                 self._import_properties, None)
        self._mk("export_image", "Export Image...", self._export_image,
                 None)
        self._mk("page_setup", "Page Setup...", self._page_setup, None)
        self._mk("print_preview", "Print Preview...",
                 self._print_preview, None)
        self._mk("modify_load", "Modify Load...", self._modify_load,
                 None)
        self._mk("modify_support", "Modify Support...",
                 self._modify_support, None)
        self._mk("move_support", "Move Support...", self._move_support,
                 None)
        self._mk("ungroup_pattern", "Ungroup Support Pattern",
                 self._ungroup_pattern, None)
        self._mk("check_updates", "Check for Updates...",
                 self._check_updates, None)
        self._mk("pic_bitmap", "Bitmap", self._pic_bitmap, None,
                 checkable=True)
        self._mk("pic_vector", "Vector (SVG)", self._pic_vector, None,
                 checkable=True)
        self._actions["pic_bitmap"].setChecked(True)

        # v0.1.56 — these three were placeholders; they now write to the
        # annotation layer built in v0.1.54 instead of showing a message.
        self._mk("add_text", "Add Text",
                 lambda: self._start_annotation(_AK.TEXT), "add_text")
        self._mk("measure", "Measure",
                 lambda: self._start_annotation(_AK.DIMENSION_LENGTH),
                 "measure")
        self._mk("dim_len", "Dimension Length",
                 lambda: self._start_annotation(_AK.DIMENSION_LENGTH),
                 "dim_length")
        self._mk("dim_ang", "Dimension Angle",
                 lambda: self._start_annotation(_AK.DIMENSION_ANGLE),
                 "dim_angle")
        self._mk("mat_tab", "Material Properties Table",
                 lambda: self._properties_table("materials"),
                 "material_table")
        # v0.1.54 (phase M3) — drawing primitives, property tables and
        # object management. Primitives write to the ANNOTATION layer,
        # which the solver never reads.
        for key, label, kind in (
            ("draw_line", "Line", _AK.LINE),
            ("draw_arrow", "Arrow", _AK.ARROW),
            ("draw_polyline", "Polyline", _AK.POLYLINE),
            ("draw_polygon", "Polygon", _AK.POLYGON),
            ("draw_rect", "Rectangle", _AK.RECTANGLE),
            ("draw_circle", "Circle", _AK.CIRCLE),
        ):
            self._mk(key, label,
                     lambda _c=False, k=kind: self._start_annotation(k),
                     None)
        self._mk("sup_tab", "Support Properties Table",
                 lambda: self._properties_table("supports"), None)
        self._mk("hyd_tab", "Hydraulic Properties Table",
                 lambda: self._properties_table("hydraulic"), None)
        self._mk("dim_x", "Dimension X",
                 lambda: self._start_annotation(_AK.DIMENSION_X), None)
        self._mk("dim_y", "Dimension Y",
                 lambda: self._start_annotation(_AK.DIMENSION_Y), None)
        self._mk("add_axes", "Add Axes",
                 lambda: self._start_annotation(_AK.AXES), None)
        self._mk("add_image", "Add Image...", self._add_image, None)
        self._mk("convert_tool", "Convert Tool to Boundary...",
                 self._convert_tool_to_boundary, None)
        self._mk("ann_show_all", "Show All Annotations",
                 lambda: self._set_annotations_visible(True), None)
        self._mk("ann_hide_all", "Hide All Annotations",
                 lambda: self._set_annotations_visible(False), None)
        self._mk("ann_delete_all", "Delete All Annotations",
                 self._delete_all_annotations, None)
        self._mk("ann_manage", "Manage Annotations...",
                 self._manage_annotations, None)

        # Window
        self._mk("terminal", "Terminal", self.act_terminal, None, "Ctrl+`", checkable=True)

        # Help
        self._mk("help", "Help Topics", self.act_help, "help", "F1")
        self._mk("about", "About OGR Slip2D", self.act_about, "about")

    # ==================================================================
    def _build_menus(self) -> None:
        mb = self.menuBar()

        m_file = mb.addMenu(tr("File"))
        for k in ["new", "open", "save", "save_as"]:
            m_file.addAction(self._actions[k])
        m_file.addSeparator()
        m_file.addAction(self._actions["load_demo"])
        m_file.addSeparator()
        m_file.addAction(self._actions["import_props"])
        m_file.addAction(self._actions["import_dxf"])
        m_file.addAction(self._actions["export_dxf"])
        m_file.addSeparator()
        m_file.addAction(self._actions["generate_report"])
        m_file.addAction(self._actions["export_image"])
        m_file.addSeparator()
        m_file.addAction(self._actions["page_setup"])
        m_file.addAction(self._actions["print_preview"])
        m_file.addAction(self._actions["print"])
        m_file.addSeparator()
        m_file.addAction(self._actions["prefs"])
        m_file.addSeparator()
        m_file.addAction(self._actions["exit"])

        m_edit = mb.addMenu(tr("Edit"))
        m_edit.addAction(self._actions["undo"])
        m_edit.addAction(self._actions["redo"])
        m_edit.addSeparator()
        m_edit.addAction(self._actions["copy_img"])
        # v0.1.56 — the format Copy Image puts on the clipboard. Bitmap
        # pastes anywhere; vector stays sharp when a figure is enlarged
        # in a report, which is what a printed section usually needs.
        m_pic = m_edit.addMenu(tr("Picture Format"))
        for k in ["pic_bitmap", "pic_vector"]:
            m_pic.addAction(self._actions[k])

        m_view = mb.addMenu(tr("View"))
        # Zoom submenu
        zoom_menu = m_view.addMenu(tr("Zoom"))
        for k in ["zoom_all", "zoom_in", "zoom_out"]:
            zoom_menu.addAction(self._actions[k])
        zoom_menu.addSeparator()
        zoom_menu.addAction(self._actions["zoom_window"])
        zoom_menu.addAction(self._actions["zoom_mouse"])
        zoom_menu.addAction(self._actions["pan"])
        zoom_menu.addAction(self._actions["select"])

        m_view.addSeparator()
        m_view.addAction(self._actions["grid_toggle"])
        m_view.addAction(self._actions["snap_opts"])
        m_view.addAction(self._actions["ruler_toggle"])
        m_view.addAction(self._actions["grayscale"])
        m_view.addSeparator()
        m_view.addAction(self._actions["display_opts"])

        m_ana = mb.addMenu(tr("Analysis"))
        m_ana.addAction(self._actions["project_settings"])
        m_ana.addAction(self._actions["info_viewer"])
        m_ana.addSeparator()
        m_ana.addAction(self._actions["compute"])
        m_ana.addAction(self._actions["interpret"])

        m_bnd = mb.addMenu(tr("Boundaries"))
        # Creation
        for k in ["add_ext", "add_mat", "add_wt", "add_drawdown", "add_piezo", "add_crack"]:
            m_bnd.addAction(self._actions[k])
        m_bnd.addSeparator()
        # Advanced geometry
        for k in ["expand_shrink", "change_slope"]:
            m_bnd.addAction(self._actions[k])
        m_bnd.addSeparator()
        # Edit submenu
        m_edit_bnd = m_bnd.addMenu(tr("Edit"))
        for k in ["del_boundary", "move_boundary", "copy_boundary",
                  "scale_boundary", "rotate_boundary"]:
            m_edit_bnd.addAction(self._actions[k])
        m_edit_bnd.addSeparator()
        for k in ["insert_vertex", "move_vertex", "delete_vertex"]:
            m_edit_bnd.addAction(self._actions[k])
        m_bnd.addSeparator()
        # Maintenance
        for k in ["convert_boundary", "simplify_boundary",
                  "geometry_cleanup", "edit_coordinates"]:
            m_bnd.addAction(self._actions[k])
        m_bnd.addSeparator()
        m_bnd.addAction(self._actions["selection_filter"])

        m_load = mb.addMenu(tr("Loading"))
        for k in ["add_dist", "add_line", "seismic",
                  "modify_load", "del_load"]:
            m_load.addAction(self._actions[k])

        m_sup = mb.addMenu(tr("Support"))
        for k in ["add_support", "support_pattern", "modify_support",
                  "move_support", "stretch_support", "ungroup_pattern",
                  "del_support"]:
            m_sup.addAction(self._actions[k])
        m_sup.addSeparator()
        # The reference places Back Analysis in the Support menu
        m_sup.addAction(self._actions["back_analysis"])

        m_surf = mb.addMenu(tr("Surfaces"))
        m_surf.addAction(self._actions["surface_opts"])
        m_surf.addSeparator()
        m_surf.addAction(self._actions["auto_grid"])
        m_surf.addAction(self._actions["add_grid"])
        m_surf.addAction(self._actions["surf_3pts"])
        m_surf.addAction(self._actions["surf_centre_radius"])
        m_surf.addSeparator()
        m_focus = m_surf.addMenu(tr("Focus Search"))
        for k in ["focus_window", "focus_line", "focus_point",
                  "focus_tangent"]:
            m_focus.addAction(self._actions[k])
        m_focus.addSeparator()
        m_focus.addAction(self._actions["focus_manage"])
        m_surf.addAction(self._actions["optimize_surfaces"])
        m_surf.addSeparator()
        m_limits = m_surf.addMenu(tr("Slope Limits"))
        for k in ["slope_limits", "slope_limits_move",
                  "slope_limits_reset"]:
            m_limits.addAction(self._actions[k])

        m_prop = mb.addMenu(tr("Properties"))
        for k in ["def_materials", "def_support", "assign",
                  # v0.1.42 — the click-to-assign canvas tool was also
                  # unreachable from any menu, like the groundwater ones.
                  "assign_material", "def_tension_crack",
                  # v0.1.62 — bulk assignment of a water surface.
                  "assign_water_surface"]:
            m_prop.addAction(self._actions[k])

        # v0.1.42 — Groundwater and Statistics menus.
        #
        # The actions for the groundwater module (v0.1.23-v0.1.31), the
        # probabilistic module (v0.1.33-v0.1.38) and the support back
        # analysis (v0.1.40) were being REGISTERED but never added to any
        # menu, so none of them was reachable from the menu bar: the
        # dialogs and interpret windows existed but the user had no way
        # in. They are grouped here following the reference layout, where
        # groundwater is its own top-level menu ordered by the real
        # workflow (properties -> mesh -> boundary conditions -> compute
        # -> interpret).
        m_gw = mb.addMenu(tr("Groundwater"))
        m_gw.addAction(self._actions["gw_hydraulic"])
        m_gw.addSeparator()
        m_gw.addAction(self._actions["wp_grid"])
        m_gw.addSeparator()
        m_gw_mesh = m_gw.addMenu(tr("Mesh"))
        m_gw_mesh.addAction(self._actions["gen_mesh"])
        m_gw_mesh.addAction(self._actions["reset_mesh"])
        m_gw.addAction(self._actions["gw_bcs"])
        m_gw.addSeparator()
        m_gw.addAction(self._actions["gw_transient"])
        m_gw.addSeparator()
        m_gw.addAction(self._actions["drawdown_sweep"])
        m_gw.addSeparator()
        m_gw.addAction(self._actions["gw_compute"])
        m_gw.addAction(self._actions["gw_interpret"])

        m_stat = mb.addMenu(tr("Statistics"))
        m_stat.addAction(self._actions["stat_vars"])
        m_stat.addSeparator()
        m_stat.addAction(self._actions["stat_compute"])
        m_stat.addAction(self._actions["stat_show"])

        m_tools = mb.addMenu(tr("Tools"))
        m_draw = m_tools.addMenu(tr("Draw"))
        for k in ["draw_line", "draw_arrow", "draw_polyline",
                  "draw_polygon", "draw_rect", "draw_circle", "add_text"]:
            m_draw.addAction(self._actions[k])
        m_dim = m_tools.addMenu(tr("Dimensions"))
        for k in ["dim_len", "dim_ang", "dim_x", "dim_y"]:
            m_dim.addAction(self._actions[k])
        m_tools.addAction(self._actions["add_axes"])
        m_tools.addAction(self._actions["add_image"])
        m_tools.addAction(self._actions["measure"])
        m_tools.addSeparator()
        m_tab = m_tools.addMenu(tr("Property Tables"))
        for k in ["mat_tab", "sup_tab", "hyd_tab"]:
            m_tab.addAction(self._actions[k])
        m_tools.addSeparator()
        # The single, explicit bridge from annotation to model geometry
        m_tools.addAction(self._actions["convert_tool"])
        m_tools.addSeparator()
        m_ann = m_tools.addMenu(tr("Annotations"))
        for k in ["ann_manage", "ann_show_all", "ann_hide_all",
                  "ann_delete_all"]:
            m_ann.addAction(self._actions[k])

        # v0.1.57 (phase M6) — a live session registry. The menu was
        # three inert lambdas; it now lists the open windows, marks the
        # active one and flags unsaved changes with an asterisk, and is
        # rebuilt each time it opens so it cannot go stale.
        m_win = mb.addMenu(tr("Window"))
        self._window_menu = m_win
        m_win.aboutToShow.connect(self._rebuild_window_menu)
        self._rebuild_window_menu()

        m_help = mb.addMenu(tr("Help"))
        m_help.addAction(self._actions["help"])
        m_help.addAction(self._actions["check_updates"])
        m_help.addSeparator()
        m_help.addAction(self._actions["about"])

    # ==================================================================
    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)

        groups = [
            ["new", "open", "save", "save_as", "print"],
            ["undo", "redo"],
            ["project_settings", "compute", "interpret"],
            ["zoom_all", "zoom_in", "zoom_out", "zoom_window", "zoom_mouse", "pan", "select"],
            ["display_opts"],
            ["add_ext", "add_mat", "add_wt", "add_drawdown", "add_piezo", "add_crack",
             "expand_shrink", "change_slope", "del_boundary"],
            ["move_vertex", "insert_vertex", "delete_vertex"],
            ["add_dist", "add_line", "seismic", "del_load"],
            ["add_support", "support_pattern", "stretch_support",
             "del_support"],
            ["auto_grid", "surf_3pts", "surface_opts", "slope_limits"],
            ["def_materials", "def_support", "assign"],
            ["add_text", "measure", "dim_len", "dim_ang", "mat_tab"],
            ["help", "about"],
        ]
        for group in groups:
            for k in group:
                if k in self._actions:
                    tb.addAction(self._actions[k])
            tb.addSeparator()

    # ==================================================================
    # Tool-mode handling
    # ==================================================================
    def _set_tool(self, mode: ToolMode) -> None:
        self.canvas.set_tool_mode(mode)

    def _sync_tool_actions(self, mode) -> None:
        """Keep the toggled state of Pan / Zoom Window / Zoom Mouse /
        Select in sync with the canvas' current mode."""
        mapping = {
            ToolMode.PAN: "pan",
            ToolMode.ZOOM_WINDOW: "zoom_window",
            ToolMode.ZOOM_MOUSE: "zoom_mouse",
            ToolMode.SELECT: "select",
        }
        for m, key in mapping.items():
            if key in self._actions:
                self._actions[key].setChecked(m == mode)

    # ==================================================================
    # File actions
    # ==================================================================
    def _tool_msg(self, name: str) -> None:
        self.ogr_status.showMessage(
            f"Tool: {name} — interactive placement scheduled for next release", 4000
        )

    def act_new(self) -> None:
        if self.project.is_dirty:
            r = QMessageBox.question(
                self, tr("New Project"),
                "Current project has unsaved changes. Save first?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if r == QMessageBox.Save:
                self.act_save()
            elif r == QMessageBox.Cancel:
                return
        self._attach_project(Project("Untitled"))
        self.terminal_dock.attach_context(self.project, self.canvas, self)
        self.command_stack.clear()
        self.results_dock.show_result(None)
        self.last_search_result = None
        self.last_search_results: dict = {}
        self.setWindowTitle(f"OGR Slip2D v{self.VERSION} — Untitled")

    def act_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Open Project..."), "",
            "OGR Project (*.ogr *.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self._attach_project(Project.load(Path(path)))
            self.terminal_dock.attach_context(self.project, self.canvas, self)
            self.command_stack.clear()
            self.setWindowTitle(f"OGR Slip2D v{self.VERSION} — {Path(path).name}")
            self.ogr_status.showMessage(f"Loaded {path}", 3000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Could not open project:\n{e}")

    def act_save(self) -> None:
        if self.project.file_path is None:
            self.act_save_as()
            return
        try:
            self.project.save()
            self.ogr_status.showMessage(f"Saved {self.project.file_path.name}", 2000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(e))

    def act_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save As..."), "", "OGR Project (*.ogr);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".ogr"):
            path += ".ogr"
        try:
            self.project.save(Path(path))
            self.setWindowTitle(f"OGR Slip2D v{self.VERSION} — {Path(path).name}")
            self.ogr_status.showMessage(f"Saved {path}", 2000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(e))

    def act_import_dxf(self) -> None:
        """v0.1.46 — import geometry from a DXF drawing (Phase D2)."""
        from PySide6.QtWidgets import QFileDialog

        from ogr_core.dxf import apply_to_project

        from .dialogs.dxf_import_dialog import DxfImportDialog

        path, _flt = QFileDialog.getOpenFileName(
            self, tr("Import DXF..."), "",
            "DXF drawings (*.dxf);;All files (*)")
        if not path:
            return
        dlg = DxfImportDialog(path, self)
        if not dlg.exec():
            return
        pv = dlg.result_preview
        if pv is None or not pv.ok:
            self._info(pv.error if pv is not None
                       else tr("The drawing could not be read."))
            return
        created = apply_to_project(self.project, pv, dlg.options)
        self.canvas.set_project(self.project)
        self.canvas.refresh_scene()
        self.canvas.zoom_all() if hasattr(self.canvas, "zoom_all") else None

        counts = ", ".join(f"{k}: {v}" for k, v in sorted(created.items()))
        msg = tr("Imported %s") % (counts or tr("nothing"))
        if pv.report is not None:
            msg += "   |   " + tr("%d region(s)") % pv.regions
            if pv.external_area > 0 and not pv.area_matches:
                msg += "   |   " + tr(
                    "WARNING: region areas do not match the external "
                    "boundary; some region did not close.")
            if pv.report.problems:
                msg += "   |   " + tr("%d problem(s) reported") % len(
                    pv.report.problems)
        self.statusBar().showMessage(msg, 20000)

        # v0.1.47 (Phase D3) — open the problem report when anything was
        # left unresolved. Listing a count in the status bar is not
        # actionable: a gap of a few millimetres in a hundred-metre model
        # cannot be found by panning, so the panel locates each one.
        needs_panel = bool(
            (pv.report is not None and pv.report.problems)
            or (pv.external_area > 0 and not pv.area_matches))
        if needs_panel:
            self._show_dxf_problems(pv)

    def _show_dxf_problems(self, pv) -> None:
        """Open (or refresh) the non-modal DXF problem report."""
        from .dialogs.dxf_problems_panel import DxfProblemsPanel

        panel = getattr(self, "_dxf_problems_panel", None)
        if panel is not None and panel.isVisible():
            panel.populate(pv)
            panel.raise_()
            return
        panel = DxfProblemsPanel(pv, self.canvas, self)
        panel.show()
        self._dxf_problems_panel = panel

    def act_export_dxf(self) -> None:
        """v0.1.48 — write the model to a DXF drawing."""
        from PySide6.QtWidgets import QFileDialog

        from ogr_core.dxf import export_dxf

        from .dialogs.dxf_export_dialog import DxfExportDialog

        results = getattr(self, "last_search_results", None)
        dlg = DxfExportDialog(self.project, bool(results), self)
        if not dlg.exec():
            return
        path, _flt = QFileDialog.getSaveFileName(
            self, tr("Export DXF..."), "",
            "DXF drawings (*.dxf);;All files (*)")
        if not path:
            return
        if not path.lower().endswith(".dxf"):
            path += ".dxf"
        rep = export_dxf(self.project, path, dlg.options, results)
        if not rep.ok:
            self._info(rep.error or tr("The drawing could not be "
                                       "written."))
            return
        msg = tr("Exported to %s   |   %s") % (path, rep.summary())
        if rep.skipped:
            msg += "   |   " + tr("skipped: %s") % ", ".join(
                sorted(set(rep.skipped)))
        self.statusBar().showMessage(msg, 20000)

    def act_generate_report(self) -> None:
        """Generate a Slide-style PDF analysis report from the last
        Compute run (all enabled methods)."""
        results = getattr(self, "last_search_results", None)
        if not results:
            QMessageBox.warning(
                self, tr("Generate Report"),
                "No analysis results available. Run Compute first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Generate Report"),
            f"{self.project.name or 'analysis'}_report.pdf",
            "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            from ogr_core.report import generate_report
            summary = self.project.settings.summary
            generate_report(
                self.project, results, path,
                author=summary.author or None,
                company=summary.company or None,
                title=summary.title or None)
        except ImportError:
            QMessageBox.critical(
                self, tr("Generate Report"),
                "The 'reportlab' package is required for PDF reports.\n"
                "Install it with:  pip install reportlab")
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, tr("Generate Report"),
                f"Failed to generate report:\n{exc}")
            return
        self.ogr_status.showMessage(f"Report saved to {path}", 6000)
        QMessageBox.information(
            self, tr("Generate Report"),
            f"Report generated successfully:\n{path}")

    def act_print(self) -> None:
        QMessageBox.information(self, tr("Print..."), "Print planned for v0.2.0.")

    def act_preferences(self) -> None:
        dlg = PreferencesDialog(self, active_theme=self.active_theme)
        dlg.language_changed.connect(self._apply_language)
        dlg.theme_changed.connect(self._apply_theme)
        dlg.exec()

    # ==================================================================
    # Edit
    # ==================================================================
    def act_undo(self) -> None:
        self.command_stack.undo(self.project)

    def act_redo(self) -> None:
        self.command_stack.redo(self.project)

    def act_copy_image(self) -> None:
        pix = self.canvas.grab()
        QApplication.clipboard().setPixmap(pix)
        self.ogr_status.showMessage("Canvas image copied to clipboard.", 2000)

    # ==================================================================
    # View
    # ==================================================================
    def _toggle_grid(self, checked: bool) -> None:
        self.canvas.set_grid_visible(checked)
        self.ogr_status.grid.setChecked(checked)

    def _toggle_ruler(self, checked: bool) -> None:
        self.canvas.set_ruler_visible(checked)

    def _toggle_grayscale(self, checked: bool) -> None:
        self.canvas.set_grayscale(checked)

    def act_display_options(self) -> None:
        dlg = DisplayOptionsDialog(self.canvas.display_options, self)
        dlg.options_applied.connect(self._on_display_options_applied)
        dlg.exec()

    def _on_display_options_applied(self, opts: DisplayOptions) -> None:
        self.canvas.set_display_options(opts)

    # ==================================================================
    # Surfaces
    # ==================================================================
    def act_surface_options(self) -> None:
        # v0.1.9: Slide-style Surface Options dialog (lives in grid_dialogs)
        dlg = SurfaceOptionsDialog(self.project, self)
        if dlg.exec():
            dlg.apply()
            self.project.is_dirty = True
            self.project._notify("settings_changed")
            self.ogr_status.showMessage(
                f"Surface search configured: "
                f"{self.project.settings.search.search_method}", 3000,
            )

    def act_add_surface(self) -> None:
        """Add a Block Search object (a search window) on the canvas.

        Block Search uses one or more user-drawn search objects to
        generate slip-surface vertices. This enters a draw mode where
        the user clicks the corners of a search window (a closed
        quadrilateral); the resulting boundary is stored as a
        BLOCK_SEARCH_OBJECT and used by the Block Search.
        """
        s = self.project.settings.search
        if s.search_method != "block":
            QMessageBox.information(
                self, "Add Surface",
                "Add Surface adds a Block Search object (search window).\n\n"
                "It is only available when the Search Method is "
                "Block Search.\nOpen Surface Options and set:\n"
                "  • Surface Type = Non-Circular\n"
                "  • Search Method = Block Search",
            )
            return
        self._set_tool(ToolMode.DRAW_BLOCK_SEARCH)
        self.ogr_status.showMessage(
            "Draw a Block Search window: click the corners, "
            "right-click or Enter to close.", 5000,
        )

    def act_auto_grid(self) -> None:
        """Reset to Auto Grid (clear user-defined grid bounds)."""
        s = self.project.settings.search
        s.grid_x_min = None
        s.grid_x_max = None
        s.grid_y_min = None
        s.grid_y_max = None
        self.project.is_dirty = True
        self.project._notify("settings_changed")
        self.canvas.refresh()
        self.ogr_status.showMessage(
            "Grid set to Auto (computed from model bounding box)", 3000,
        )

    def act_add_grid(self) -> None:
        """Open the Add Grid dialog as a non-modal floating window.

        v0.1.13 (P9 fix per Samuel's suggestion): the dialog is opened
        non-modal with show() instead of exec(). It stays visible the
        entire time, including during the canvas-pick step. After the
        2 corner clicks, the dialog's spinboxes update via
        ``update_bounds`` and the user clicks OK directly.

        OK / Cancel are wired through ``accepted`` / ``rejected`` Qt
        signals so we can apply the settings asynchronously.
        """
        from .dialogs.grid_dialogs import AddGridDialog

        dlg = getattr(self, "_active_grid_dialog", None)
        if dlg is not None and dlg.isVisible():
            dlg.raise_()
            dlg.activateWindow()
            return

        dlg = AddGridDialog(self.project, self)
        self._active_grid_dialog = dlg
        # Connect signals (only once per dialog instance)
        dlg.pick_started.connect(self._begin_grid_pick)
        dlg.accepted.connect(lambda d=dlg: self._on_grid_dialog_accepted(d))
        dlg.rejected.connect(lambda d=dlg: self._on_grid_dialog_rejected(d))
        # Non-modal floating
        dlg.setModal(False)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_grid_dialog_accepted(self, dlg) -> None:
        """User pressed OK on the Add Grid dialog."""
        try:
            dlg.apply_to_settings()
        except Exception:  # noqa: BLE001
            pass
        self.project.is_dirty = True
        self.project._notify("settings_changed")
        self.canvas.refresh()
        s = self.project.settings.search
        self.ogr_status.showMessage(
            f"Grid: {s.grid_nx}×{s.grid_ny} intervals "
            f"({s.grid_nx + 1}×{s.grid_ny + 1} centres) in "
            f"x∈[{s.grid_x_min:.1f}, {s.grid_x_max:.1f}], "
            f"y∈[{s.grid_y_min:.1f}, {s.grid_y_max:.1f}]",
            4000,
        )
        self._active_grid_dialog = None

    def _on_grid_dialog_rejected(self, dlg) -> None:
        self._active_grid_dialog = None

    def _begin_grid_pick(self) -> None:
        """Activate canvas pick mode while the dialog stays visible."""
        try:
            self.canvas.segment_picked.disconnect(self._on_grid_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.segment_picked.connect(self._on_grid_picked)
        self.canvas.set_tool_mode(ToolMode.PICK_GRID_RECT)
        self.ogr_status.showMessage(
            "Click two opposite corners on the canvas. The dialog will "
            "update with the picked bounds; press OK to apply.",
            12000,
        )

    def _on_grid_picked(
        self, x1: float, y1: float, x2: float, y2: float,
    ) -> None:
        """User clicked two corners — push values to the live dialog."""
        try:
            self.canvas.segment_picked.disconnect(self._on_grid_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.set_tool_mode(ToolMode.SELECT)

        s = self.project.settings.search
        s.grid_x_min = min(x1, x2)
        s.grid_x_max = max(x1, x2)
        s.grid_y_min = min(y1, y2)
        s.grid_y_max = max(y1, y2)
        self.canvas.refresh()

        dlg = getattr(self, "_active_grid_dialog", None)
        if dlg is not None:
            # Use the new update_bounds method which also brings the
            # dialog to the front.
            try:
                dlg.update_bounds(x1, y1, x2, y2)
            except Exception:  # noqa: BLE001
                pass

    # ==================================================================
    # Analysis
    # ==================================================================
    def act_project_settings(self) -> None:
        dlg = ProjectSettingsDialog(self.project.settings, self)
        if dlg.exec():
            self.project._notify("settings_changed")
            self._update_groundwater_actions()
            self._update_statistics_actions()

    def _generate_fem_mesh(self) -> None:
        """v0.1.25 — generate the FE mesh for the seepage analysis."""
        from PySide6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getInt(
            self, "Generate FE Mesh",
            "Approximate number of elements:", 1000, 20, 200000, 100)
        if not ok:
            return
        from ogr_fem2d.mesh import generate_mesh_for_project
        try:
            mesh = generate_mesh_for_project(self.project,
                                             target_elements=n)
        except Exception as exc:  # noqa: BLE001
            self._info(f"Mesh generation failed: {exc}")
            return
        if mesh.element_count == 0:
            self._info("No mesh generated. An External boundary with a "
                       "valid closed polygon is required.")
            return
        self.project.fem_mesh = mesh
        self.project.seepage_bcs = None
        self.project.seepage_result = None
        # v0.1.78 — the transient stages have to go with it. They were
        # left behind here and in _reset_fem_mesh, which did not show
        # while nothing was saved: a stale list only existed until the
        # session ended. Now that the fields are written to the .ogr, a
        # list of results indexed by the OLD mesh's nodes would be saved
        # alongside the new mesh.
        self.project.transient_results = []
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self._update_groundwater_actions()
        q = mesh.quality_stats()
        self.statusBar().showMessage(
            f"FE mesh: {q['elements']} elements, {q['nodes']} nodes, "
            f"min angle {q['min_angle']:.1f} deg", 8000)

    def _reset_fem_mesh(self) -> None:
        """v0.1.25 — discard the FE mesh."""
        if getattr(self.project, "fem_mesh", None) is None:
            self.statusBar().showMessage("No FE mesh to reset", 3000)
            return
        self.project.fem_mesh = None
        self.project.seepage_bcs = None
        self.project.seepage_result = None
        self.project.transient_results = []   # see act_generate_mesh
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self._update_groundwater_actions()
        self.statusBar().showMessage("FE mesh cleared", 3000)

    # ==================================================================
    # Groundwater mode (Phase 5)
    # ==================================================================
    # ==================================================================
    # Back analysis of support force
    # ==================================================================
    def _back_analysis(self) -> None:
        """Compute the support force required to reach a target factor of
        safety, and report the surface that needs the most.

        Independent of the main analysis, as the reference specifies: it
        neither uses nor alters the stability results.
        """
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
            QComboBox, QVBoxLayout,
        )
        from ogr_slip2d.back_analysis import (
            SUPPORTED_METHODS, run_back_analysis,
        )
        cfg = self.project.settings.back_analysis

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Back Analysis of Support Force"))
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        sp_fos = QDoubleSpinBox()
        sp_fos.setDecimals(3)
        sp_fos.setRange(0.001, 100.0)
        sp_fos.setValue(cfg.target_fos)
        form.addRow(tr("Target factor of safety:"), sp_fos)
        sp_el = QDoubleSpinBox()
        sp_el.setDecimals(3)
        sp_el.setRange(-1e6, 1e6)
        sp_el.setValue(cfg.elevation)
        sp_el.setToolTip(
            "Elevation of the horizontal force. Only affects Bishop: "
            "Janbu uses force equilibrium, where the position of a "
            "horizontal force is irrelevant.")
        form.addRow(tr("Elevation (y):"), sp_el)
        cbo = QComboBox()
        for mid in SUPPORTED_METHODS:
            cbo.addItem(mid, mid)
        i = cbo.findData(cfg.method_id)
        cbo.setCurrentIndex(max(0, i))
        form.addRow(tr("Analysis method:"), cbo)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not dlg.exec():
            return

        cfg.enabled = True
        cfg.target_fos = sp_fos.value()
        cfg.elevation = sp_el.value()
        cfg.method_id = cbo.currentData()
        self.project.is_dirty = True

        worker = _ComputeWorker(self.project, [cfg.method_id])
        search = worker.build_search(cfg.method_id)
        if search is None:
            self._info("Could not build the search for this method.")
            return
        res = run_back_analysis(self.project, search, cfg.target_fos,
                                cfg.elevation, cfg.method_id)
        self._back_analysis_result = res
        if res.critical is None:
            self._info(res.notes.get("error", "Back analysis failed."))
            return
        c = res.critical
        self.statusBar().showMessage(
            f"Back analysis ({cfg.method_id}): required force "
            f"{res.required_force:.1f} for FS = {cfg.target_fos:g}  "
            f"(active {c.active_force:.1f}, passive "
            f"{c.passive_force:.1f}; surface FoS without support "
            f"{c.unsupported_fos:.4f}, {res.surfaces_analysed} surfaces)",
            15000)

    # ==================================================================
    # Drawdown level sweep (v0.1.70)
    # ==================================================================
    def _drawdown_sweep(self) -> None:
        """Search at a range of drawdown levels and report the worst.

        The total drawdown is not always the critical case. The reference
        documents both behaviours — a homogeneous slope is worst emptied
        completely, a zoned dam with a freely draining shell can be worst
        at an intermediate level, because the shell drains to zero pore
        pressure only when the reservoir is gone entirely. On such a dam
        the difference is around 12 % on the unsafe side.
        """
        from PySide6.QtWidgets import (
            QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
            QVBoxLayout,
        )
        from ogr_core.hydraulic.drawdown_levels import ground_elevation_span
        from ogr_core.statistics import default_levels
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings

        gw = self.project.settings.groundwater
        if not gw.rapid_drawdown:
            QMessageBox.warning(
                self, tr("Drawdown Level Sweep"),
                tr("Enable Rapid Drawdown analysis in Project Settings "
                   "> Groundwater > Advanced first."))
            return
        why = check_drawdown_settings(self.project)
        if why:
            QMessageBox.warning(self, tr("Drawdown Level Sweep"), why)
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Drawdown Level Sweep"))
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        sp_n = QSpinBox()
        sp_n.setRange(2, 101)
        sp_n.setValue(11)
        sp_n.setToolTip(tr(
            "Reservoir levels between the initial water table and the "
            "lowest ground in the model. Each one is a full search, so "
            "this is the cost of the run."))
        form.addRow(tr("Number of levels:"), sp_n)
        chk_total = QCheckBox(tr("Include total drawdown"))
        chk_total.setChecked(True)
        form.addRow("", chk_total)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not dlg.exec():
            return

        method_ids = list(
            self.project.settings.methods.enabled_methods) or [
            "bishop_simplified"]
        self.prog = ComputeProgressDialog(self)
        self.sweep_worker = _DrawdownSweepWorker(
            self.project, method_ids, sp_n.value(), chk_total.isChecked())
        self.sweep_worker.progress.connect(self.prog.update_progress)
        self.sweep_worker.finished_result.connect(self._on_drawdown_sweep_done)
        self.sweep_worker.failed.connect(
            lambda msg: QMessageBox.critical(self, "Error", msg))
        self.sweep_worker.finished.connect(self.prog.accept)
        self.sweep_worker.start()
        self.prog.exec()

    def _on_drawdown_sweep_done(self, result) -> None:
        """Report the critical level and chart the sweep."""
        self.last_drawdown_sweep = result
        if result.notes.get("error"):
            QMessageBox.warning(self, tr("Drawdown Level Sweep"),
                                result.notes["error"])
            return
        worst = result.worst()
        if worst is None:
            QMessageBox.warning(
                self, tr("Drawdown Level Sweep"),
                tr("No level produced a valid factor of safety."))
            return
        mid, level, fos = worst
        sweep = result.by_method[mid]
        margin = sweep.unsafe_margin()
        where = (tr("total drawdown") if level is None
                 else f"y = {level:.2f}")
        msg = (f"{tr('Critical drawdown level')} ({mid}): {where}, "
               f"FS = {fos:.4f}")
        if margin is not None and margin > 0.005:
            # v0.1.76 — the lookup stays OUTSIDE the f-string. Splitting an
            # implicitly concatenated literal across lines inside a
            # replacement field is PEP 701, i.e. Python 3.12 and later;
            # on the 3.11 this project supports the literal ends at the
            # line break and the module does not parse at all.
            overstate = tr("the total drawdown alone would overstate it by")
            msg += f"  — {overstate} {100 * margin:.1f} %"
        self.statusBar().showMessage(msg, 20000)

        xs, series = [], []
        for m_id, sw in result.by_method.items():
            valid = sw.valid
            if not valid:
                continue
            # Total drawdown has no elevation; it plots at the lowest
            # level swept so the curve stays a curve.
            lows = [lv for lv, _f, _s in valid if lv is not None]
            floor = min(lows) if lows else 0.0
            xs = [floor if lv is None else lv for lv, _f, _s in valid]
            series.append((m_id, [f for _lv, f, _s in valid]))
        if not series:
            return
        try:
            from .dialogs.chart_dialogs import MultiLineDialog
            MultiLineDialog(
                xs, series=series,
                xlabel=tr("Drawdown level (y)"),
                title=tr("Factor of safety vs drawdown level"),
                parent=self,
            ).exec()
        except Exception:  # noqa: BLE001
            html = f"<b>{tr('Factor of safety vs drawdown level')}</b><pre>"
            for m_id, sw in result.by_method.items():
                html += f"<br>{m_id}<br>"
                for lv, f, _s in sw.valid:
                    lab = "total" if lv is None else f"{lv:8.2f}"
                    html += f"  {lab}   {f:.4f}<br>"
            html += "</pre>"
            self._info(html)

    # ==================================================================
    # Statistics (Phase P5)
    # ==================================================================
    def _update_statistics_actions(self) -> None:
        """The Statistics options are only meaningful once a
        probabilistic or a sensitivity analysis has been enabled in
        Project Settings, mirroring the reference where the Statistics
        menu appears only then."""
        st = self.project.settings.statistics
        on = bool(st.probabilistic_analysis or st.sensitivity_analysis)
        has_vars = bool(getattr(self.project, "random_variables", []))
        has_res = (getattr(self, "_prob_result", None) is not None
                   or getattr(self, "_sens_result", None) is not None)
        for key, enabled in (("stat_vars", on),
                             ("stat_compute", on and has_vars),
                             ("stat_show", has_res)):
            act = self._actions.get(key)
            if act is not None:
                act.setEnabled(bool(enabled))

    def _edit_random_variables(self) -> None:
        from .dialogs.random_variables_dialog import RandomVariablesDialog
        if RandomVariablesDialog(self.project, self).exec():
            n = len(self.project.random_variables)
            self._update_statistics_actions()
            self.statusBar().showMessage(
                f"{n} random variable(s) defined", 5000)

    def _deterministic_criticals(self) -> dict:
        """Run the configured deterministic search once, reusing the
        very same machinery as a normal Compute."""
        method_ids = list(
            self.project.settings.methods.enabled_methods) or [
            "bishop_simplified"]
        worker = _ComputeWorker(self.project, method_ids)
        worker.run()
        return {mid: sr.critical
                for mid, sr in (worker.results or {}).items()
                if sr is not None and sr.critical is not None}

    def _compute_statistics(self) -> None:
        """Run the probabilistic and/or sensitivity analysis."""
        from ogr_core.statistics import (
            SamplingMethod, run_global_minimum, run_overall_slope,
            run_sensitivity,
        )
        st = self.project.settings.statistics
        variables = list(getattr(self.project, "random_variables", []))
        if not variables:
            self._info("Define at least one random variable first.")
            return
        det = self._deterministic_criticals()
        if not det:
            self._info("The deterministic analysis produced no critical "
                       "surface. Check the model and the search settings.")
            return

        try:
            sampling = SamplingMethod(st.sampling_method)
        except ValueError:
            sampling = SamplingMethod.MONTE_CARLO

        self._prob_result = None
        self._sens_result = None
        messages = []

        if st.probabilistic_analysis:
            if st.analysis_type == "overall_slope":
                method_ids = list(det)

                def _factory(mid, _self=self):
                    worker = _ComputeWorker(_self.project, [mid])
                    return worker.build_search(mid)

                res = run_overall_slope(
                    self.project, _factory, variables, method_ids,
                    num_samples=st.num_samples, sampling=sampling,
                    seed=self.project.settings.analysis_seed(),
                    deterministic=det)
            else:
                res = run_global_minimum(
                    self.project, det, variables,
                    num_samples=st.num_samples, sampling=sampling,
                    seed=self.project.settings.analysis_seed(),
                    num_slices=self.project.settings.methods.num_slices)
            if res.ok:
                self._prob_result = res
                first = next(iter(res.by_method.values()))
                messages.append(
                    f"PF = {first.probability_of_failure * 100:.2f} %, "
                    f"beta = {first.reliability_index:.3f}")
            else:
                messages.append(res.notes.get("error", "probabilistic "
                                                       "run failed"))

        if st.sensitivity_analysis:
            res = run_sensitivity(
                self.project, det, variables,
                intervals=st.sensitivity_intervals,
                num_slices=self.project.settings.methods.num_slices)
            if res.ok:
                self._sens_result = res
                rows = res.ranking()
                if rows:
                    messages.append(f"most sensitive: {rows[0][1]}")
            else:
                messages.append(res.notes.get("error", "sensitivity run "
                                                       "failed"))

        self._update_statistics_actions()
        if not messages:
            self._info("Enable a probabilistic or sensitivity analysis "
                       "in Project Settings first.")
            return
        self.statusBar().showMessage("   |   ".join(messages), 12000)
        if self._prob_result is not None or self._sens_result is not None:
            self._show_statistics()

    def _show_statistics(self) -> None:
        if (getattr(self, "_prob_result", None) is None
                and getattr(self, "_sens_result", None) is None):
            self._info("Run Compute Statistics first.")
            return
        from .statistics_window import StatisticsWindow
        w = StatisticsWindow(self.project,
                             getattr(self, "_prob_result", None),
                             getattr(self, "_sens_result", None), self)
        w.show()
        self._stats_window = w

    # ==================================================================
    # Snap and data tips (phase M1)
    # ==================================================================
    def _build_m1_extras(self) -> None:
        """Keyboard shortcuts and the data-tip hover, on top of the
        existing snap engine.

        The status bar already carried the SNAP / GRID / ORTHO / OSNAP
        words wired to ``canvas.snap_settings``; what was missing was a
        keyboard route. Both routes are made to funnel through the SAME
        status-bar labels, so pressing F9 moves the word and clicking the
        word moves the engine — there is one place holding the state.
        """
        from PySide6.QtGui import QKeySequence, QShortcut

        for key, attr in (("F9", "snap"), ("F8", "ortho"),
                          ("F3", "osnap")):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda a=attr: self._toggle_snap_flag(a))

        # DATA TIPS was the one indicator the status bar lacked
        self._data_tips_label = self.ogr_status.add_toggle(
            tr("DATA TIPS"), True)
        if self._data_tips_label is not None:
            self._data_tips_label.toggled.connect(
                self._on_data_tips_toggled)

        try:
            self.canvas.scene_hovered.connect(self._on_canvas_hover)
        except Exception:  # noqa: BLE001
            pass

    def _toggle_snap_flag(self, attr: str) -> None:
        """Flip a snap constraint from the keyboard.

        Driven through the status-bar label rather than the engine, so the
        word on screen and the engine can never disagree.
        """
        label = {"snap": self.ogr_status.snap,
                 "ortho": self.ogr_status.ortho,
                 "osnap": self.ogr_status.osnap}.get(attr)
        if label is None:
            return
        label.setChecked(not label.isChecked())
        state = tr("on") if label.isChecked() else tr("off")
        self.statusBar().showMessage(f"{attr.upper()}: {state}", 2000)

    def _on_data_tips_toggled(self, on: bool) -> None:
        from ogr_gui.data_tips import DataTipMode
        self.data_tip_mode = (DataTipMode.MAXIMUM if on
                              else DataTipMode.NONE)

    def _on_canvas_hover(self, x: float, y: float) -> None:
        """The data tip under the cursor.

        Asked for in the opening paragraph of the project brief: hovering
        over a material, a support or a load shows its properties.
        """
        from ogr_gui.data_tips import DataTipMode, tip_at
        if self.data_tip_mode == DataTipMode.NONE:
            self.canvas.setToolTip("")
            return
        # A constant number of PIXELS converted to model units, so a tip
        # is equally easy to hit at any zoom.
        scale = abs(self.canvas.transform().m11()) or 1.0
        try:
            text = tip_at(self.project, x, y, self.data_tip_mode,
                          8.0 / scale)
        except Exception:  # noqa: BLE001
            text = ""
        self.canvas.setToolTip(text)

    def _snap_options(self) -> None:
        """Configure the existing snap engine."""
        from .dialogs.snap_dialog import SnapDialog

        dlg = SnapDialog(self.canvas.snap_settings, self.data_tip_mode,
                         self)
        if not dlg.exec():
            return
        self.data_tip_mode = dlg.data_tip_mode
        # Reflect the three constraints back onto the status bar, so the
        # dialog and the words stay in step in both directions.
        for attr, label in (("snap", self.ogr_status.snap),
                            ("ortho", self.ogr_status.ortho),
                            ("osnap", self.ogr_status.osnap)):
            label.setChecked(getattr(self.canvas.snap_settings, attr))
        if self._data_tips_label is not None:
            from ogr_gui.data_tips import DataTipMode
            self._data_tips_label.setChecked(
                self.data_tip_mode != DataTipMode.NONE)


    # ==================================================================
    # Annotation layer and property tables (phase M3)
    # ==================================================================
    def _start_annotation(self, kind) -> None:
        """Begin drawing an annotation.

        Coordinates are typed rather than picked for now: the canvas
        picking modes belong to the drawing tools, and an annotation that
        can be placed exactly is more useful for a figure than one placed
        approximately by mouse.
        """
        from PySide6.QtWidgets import QInputDialog

        from ogr_core.annotations import Annotation, AnnotationKind

        needed = {AnnotationKind.TEXT: 1,
                  AnnotationKind.DIMENSION_ANGLE: 3,
                  AnnotationKind.AXES: 1}.get(kind, 2)
        prompt = tr("Enter %d point(s) as x,y  x,y ...") % needed
        text, ok = QInputDialog.getText(self, tr("Draw"), prompt)
        if not ok or not text.strip():
            return
        pts = []
        for chunk in text.replace(";", " ").split():
            try:
                x, y = (float(v) for v in chunk.split(","))
            except ValueError:
                self._info(tr("Could not read '%s' as x,y") % chunk)
                return
            pts.append((x, y))
        if len(pts) < needed:
            self._info(tr("This shape needs %d point(s).") % needed)
            return
        label = ""
        if kind == AnnotationKind.TEXT:
            label, ok = QInputDialog.getText(self, tr("Text"),
                                             tr("Text:"))
            if not ok:
                return
        ann = self.project.annotations.add(
            Annotation(kind=kind, points=pts, text=label))
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        value = ann.measured_value()
        msg = tr("Added %s") % kind.value
        if value is not None:
            msg += tr("   |   measured: %.4f") % value
        self.statusBar().showMessage(msg, 6000)

    def _set_annotations_visible(self, visible: bool) -> None:
        self.project.annotations.set_all_visible(visible)
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("%d annotation(s) %s")
            % (len(self.project.annotations),
               tr("shown") if visible else tr("hidden")), 4000)

    def _delete_all_annotations(self) -> None:
        n = len(self.project.annotations)
        if not n:
            self._info(tr("There are no annotations."))
            return
        from PySide6.QtWidgets import QMessageBox
        # Destructive and not undoable through the annotation layer, so
        # it asks first.
        if QMessageBox.question(
                self, tr("Delete All Annotations"),
                tr("Delete all %d annotation(s)? The physical model is "
                   "not affected.") % n) != QMessageBox.Yes:
            return
        self.project.annotations.clear()
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("%d annotation(s) deleted") % n, 4000)

    def _manage_annotations(self) -> None:
        from .dialogs.annotations_dialog import AnnotationsDialog

        if not len(self.project.annotations):
            self._info(tr("There are no annotations."))
            return
        if AnnotationsDialog(self.project.annotations, self).exec():
            self.project.is_dirty = True
            self.canvas.refresh_scene()

    def _convert_tool_to_boundary(self) -> None:
        """The single, explicit bridge from the annotation layer to the
        model.

        Nothing converts itself: a sketch becomes geometry when the
        engineer says so, which is what stops an analysis result from
        changing because someone drew on the drawing.
        """
        from PySide6.QtWidgets import QInputDialog

        from ogr_core.annotations import to_boundary_points
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )

        candidates = [a for a in self.project.annotations
                      if a.convertible]
        if not candidates:
            self._info(tr(
                "No annotation can become geometry. Dimensions, text and "
                "axes annotate the model rather than define it; draw a "
                "line, polyline, polygon, rectangle or circle first."))
            return
        labels = [f"{i + 1}. {a.kind.value} ({len(a.outline())} pts)"
                  for i, a in enumerate(candidates)]
        choice, ok = QInputDialog.getItem(
            self, tr("Convert Tool to Boundary"), tr("Annotation:"),
            labels, 0, False)
        if not ok:
            return
        ann = candidates[labels.index(choice)]

        types = [(BoundaryType.EXTERNAL, tr("External Boundary")),
                 (BoundaryType.MATERIAL, tr("Material Boundary")),
                 (BoundaryType.WATER_TABLE, tr("Water Table")),
                 (BoundaryType.PIEZOMETRIC, tr("Piezometric Line")),
                 (BoundaryType.TENSION_CRACK, tr("Tension Crack"))]
        tlabels = [t[1] for t in types]
        tchoice, ok = QInputDialog.getItem(
            self, tr("Convert Tool to Boundary"), tr("Convert to:"),
            tlabels, 1, False)
        if not ok:
            return
        btype = types[tlabels.index(tchoice)][0]

        pts = to_boundary_points(ann)
        if not pts:
            self._info(tr("This annotation has no usable geometry."))
            return
        self.project.add_boundary(Boundary(
            btype=btype,
            polyline=Polyline(vertices=[Vertex(x, y) for x, y in pts],
                              closed=ann.closed)))
        self.project.is_dirty = True
        self.canvas.set_project(self.project)
        self.canvas.refresh_scene()
        # The annotation stays: converting copies the shape into the
        # model rather than moving it, so the sketch that documented the
        # intent is not lost.
        self.statusBar().showMessage(
            tr("Converted to %s (%d vertices). The annotation was kept.")
            % (tchoice, len(pts)), 8000)

    def _add_image(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from ogr_core.annotations import Annotation, AnnotationKind
        path, _f = QFileDialog.getOpenFileName(
            self, tr("Add Image..."), "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All files (*)")
        if not path:
            return
        try:
            xmin, ymin, xmax, ymax = self.project.bounding_box()
        except Exception:  # noqa: BLE001
            xmin, ymin, xmax, ymax = 0.0, 0.0, 100.0, 50.0
        self.project.annotations.add(Annotation(
            kind=AnnotationKind.IMAGE,
            points=[(xmin, ymin), (xmax, ymax)], text=path))
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("Image placed over the model extent; use Manage "
               "Annotations to reposition it."), 8000)

    def _properties_table(self, what: str) -> None:
        """A read-only table of the model's properties.

        Read-only on purpose: editing happens in the dedicated dialogs,
        where validation lives. A second editing path would be a second
        place for validation to be forgotten.
        """
        from .dialogs.properties_table_dialog import PropertiesTableDialog

        dlg = PropertiesTableDialog(self.project, what, self)
        if dlg.is_empty:
            self._info(dlg.empty_message)
            return
        dlg.exec()


    # ==================================================================
    # Focus objects, optimisation and surface entries (phase M4)
    # ==================================================================
    def _read_points(self, title, count):
        """Ask for ``count`` points as text.

        Typed rather than picked: a focus object placed exactly is more
        useful than one placed approximately, and the canvas picking
        modes belong with the drawing tools.
        """
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, title, tr("Enter %d point(s) as x,y  x,y ...") % count)
        if not ok or not text.strip():
            return None
        pts = []
        for chunk in text.replace(";", " ").split():
            try:
                x, y = (float(v) for v in chunk.split(","))
            except ValueError:
                self._info(tr("Could not read '%s' as x,y") % chunk)
                return None
            pts.append((x, y))
        if len(pts) < count:
            self._info(tr("This needs %d point(s).") % count)
            return None
        return pts

    def _add_focus(self, kind) -> None:
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.focus import FocusKind, FocusObject
        need = {FocusKind.WINDOW: 4, FocusKind.LINE: 2,
                FocusKind.POINT: 1, FocusKind.TANGENT: 2}[kind]
        pts = self._read_points(tr("Focus Search"), need)
        if pts is None:
            return
        tol = 0.5
        if kind in (FocusKind.POINT, FocusKind.TANGENT):
            # These two match on a DISTANCE, so without a tolerance they
            # would accept nothing: an exact tangency never occurs in a
            # discretised search.
            tol, ok = QInputDialog.getDouble(
                self, tr("Focus Search"), tr("Capture tolerance:"),
                0.5, 0.0001, 1e6, 4)
            if not ok:
                return
        self.project.focus_objects.append(
            FocusObject(kind=kind, points=pts, tolerance=tol))
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("%d focus object(s) defined. They narrow the search: a "
               "circle must satisfy every one of them.")
            % len(self.project.focus_objects), 9000)

    def _manage_focus(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        objs = self.project.focus_objects
        if not objs:
            self._info(tr("No focus objects are defined."))
            return
        items = [tr("%d: %s (%d points, tolerance %.4g)%s")
                 % (i + 1, o.kind.value, len(o.points), o.tolerance,
                    "" if o.enabled else tr("  [disabled]"))
                 for i, o in enumerate(objs)]
        items.append(tr("(delete all)"))
        choice, ok = QInputDialog.getItem(
            self, tr("Manage Focus Objects"),
            tr("Toggle or delete:"), items, 0, False)
        if not ok:
            return
        if choice == tr("(delete all)"):
            objs.clear()
        else:
            idx = items.index(choice)
            action, ok = QInputDialog.getItem(
                self, tr("Manage Focus Objects"), tr("Action:"),
                [tr("Enable / disable"), tr("Delete")], 0, False)
            if not ok:
                return
            if action == tr("Delete"):
                objs.pop(idx)
            else:
                objs[idx].enabled = not objs[idx].enabled
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("%d focus object(s) defined.") % len(objs), 5000)

    def _optimize_surfaces(self) -> None:
        """Random-walk the critical surface towards a lower factor."""
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        results = getattr(self, "last_search_results", None) or {}
        candidates = {mid: sr for mid, sr in results.items()
                      if sr is not None and sr.critical is not None}
        if not candidates:
            self._info(tr(
                "Run an analysis first: optimisation refines an existing "
                "surface, so it needs one to start from."))
            return
        mid = next(iter(candidates))
        if len(candidates) > 1:
            choice, ok = QInputDialog.getItem(
                self, tr("Optimize Surfaces"), tr("Method:"),
                list(candidates), 0, False)
            if not ok:
                return
            mid = choice
        crit = candidates[mid].critical
        surface = crit.surface
        if not hasattr(surface, "polyline"):
            self._info(tr(
                "Optimisation applies to NON-CIRCULAR surfaces. The "
                "critical surface of this method is a circle; use a "
                "Block or Path Search first."))
            return

        iters, ok = QInputDialog.getInt(
            self, tr("Optimize Surfaces"), tr("Maximum evaluations:"),
            400, 10, 100000)
        if not ok:
            return
        worker = _ComputeWorker(self.project, [mid])
        search = worker.build_search(mid)
        if search is None:
            self._info(tr("Could not build the search for this method."))
            return
        best, res, rep = optimize_surface(
            self.project, search, surface,
            OptimizeSettings(max_iterations=iters))
        if "error" in rep.notes:
            self._info(rep.notes["error"])
            return
        if not rep.improved:
            self.statusBar().showMessage(
                tr("No improvement found: %s") % rep.summary(), 12000)
            return
        # The optimised surface replaces the critical one in the stored
        # result, so Interpret shows what the optimisation produced
        # rather than the surface it started from.
        crit.surface = best
        crit.fos = res.fos
        crit.slices = res.slices
        self.canvas.display_search_result(candidates[mid])
        self.statusBar().showMessage(
            tr("Optimised: %s") % rep.summary(), 15000)

    def _add_surface_centre_radius(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.surface import SlipCircle
        pts = self._read_points(tr("Add Surface"), 1)
        if pts is None:
            return
        radius, ok = QInputDialog.getDouble(
            self, tr("Add Surface"), tr("Radius:"), 20.0, 0.001, 1e6, 4)
        if not ok:
            return
        circle = SlipCircle(centre_x=pts[0][0], centre_y=pts[0][1],
                            radius=radius)
        if not hasattr(self.project, "user_surfaces"):
            self.project.user_surfaces = []
        self.project.user_surfaces.append(circle)
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("Circle added: centre (%.3f, %.3f), radius %.3f")
            % (circle.centre_x, circle.centre_y, circle.radius), 8000)

    def _move_slope_limits(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        s = self.project.settings.search
        left, ok = QInputDialog.getDouble(
            self, tr("Move Slope Limits"), tr("Left limit (x):"),
            float(getattr(s, "slope_limit_left", 0.0) or 0.0),
            -1e9, 1e9, 4)
        if not ok:
            return
        right, ok = QInputDialog.getDouble(
            self, tr("Move Slope Limits"), tr("Right limit (x):"),
            float(getattr(s, "slope_limit_right", 0.0) or 0.0),
            -1e9, 1e9, 4)
        if not ok:
            return
        if right <= left:
            self._info(tr("The right limit must be greater than the "
                          "left one."))
            return
        s.slope_limit_left = left
        s.slope_limit_right = right
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("Slope limits: %.3f to %.3f") % (left, right), 6000)

    def _reset_slope_limits(self) -> None:
        """Back to automatic, derived from the ground surface."""
        s = self.project.settings.search
        s.slope_limit_left = None
        s.slope_limit_right = None
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("Slope limits reset to automatic."), 6000)


    # ==================================================================
    # Minor menus (phase M5)
    # ==================================================================


    # ==================================================================
    # Session registry (phase M6)
    # ==================================================================
    #: Every open main window. A class attribute so a new window can find
    #: its siblings without a global registry object.
    _sessions: list = []

    def register_session(self) -> None:
        if self not in MainWindow._sessions:
            MainWindow._sessions.append(self)

    def unregister_session(self) -> None:
        if self in MainWindow._sessions:
            MainWindow._sessions.remove(self)

    def session_label(self) -> str:
        """How this window appears in the Window menu.

        The asterisk marks unsaved changes and the bullet the active
        window — the two things a user needs from such a list, and the
        reason a static menu was useless.
        """
        name = getattr(self.project, "name", None) or tr("Untitled")
        dirty = "*" if getattr(self.project, "is_dirty", False) else ""
        active = "• " if self.isActiveWindow() else "   "
        return f"{active}{name}{dirty}"

    def _rebuild_window_menu(self) -> None:
        """Rebuild on every open, so the list cannot go stale."""
        menu = getattr(self, "_window_menu", None)
        if menu is None:
            return
        menu.clear()
        menu.addAction(tr("New Window"), self._new_window)
        menu.addSeparator()
        if "terminal" in self._actions:
            menu.addAction(self._actions["terminal"])
            menu.addSeparator()
        sessions = [w for w in MainWindow._sessions if w is not None]
        if self not in sessions:
            sessions.append(self)
        for i, win in enumerate(sessions, 1):
            act = menu.addAction(f"{i}. {win.session_label()}")
            act.setCheckable(True)
            act.setChecked(win is self)
            act.triggered.connect(
                lambda _c=False, w=win: self._activate_session(w))
        menu.addSeparator()
        menu.addAction(tr("Close Window"), self.close)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Deregister on close, or the Window menu would list windows
        that no longer exist."""
        self.unregister_session()
        super().closeEvent(event)

    def _new_window(self) -> None:
        """Open a second independent session.

        Independent, not a view of the same model: two windows editing one
        project would let a change in one invalidate results shown in the
        other without any sign of it.
        """
        win = MainWindow()
        win.register_session()
        win.show()
        return win

    def _activate_session(self, window) -> None:
        try:
            window.raise_()
            window.activateWindow()
        except Exception:  # noqa: BLE001
            pass

    def _pic_bitmap(self) -> None:
        """Copy Image will place a bitmap on the clipboard."""
        self.picture_format = "bitmap"
        self._actions["pic_vector"].setChecked(False)
        self._actions["pic_bitmap"].setChecked(True)
        self.statusBar().showMessage(
            tr("Copy Image will use a bitmap."), 4000)

    def _pic_vector(self) -> None:
        """Copy Image will place vector data on the clipboard.

        Worth having because a bitmap enlarged in a report goes soft,
        and a section drawing is exactly the kind of figure a reader
        zooms into.
        """
        self.picture_format = "vector"
        self._actions["pic_bitmap"].setChecked(False)
        self._actions["pic_vector"].setChecked(True)
        self.statusBar().showMessage(
            tr("Copy Image will use vector data, which stays sharp when "
               "the figure is enlarged."), 6000)

    def _import_properties(self) -> None:
        """Bring materials and supports across from another project.

        Names are made unique rather than overwriting: silently replacing
        a material that a region already references would change results
        without the user seeing it happen.
        """
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        from ogr_core.project import Project
        path, _f = QFileDialog.getOpenFileName(
            self, tr("Import Properties..."), "",
            "OGR projects (*.ogr);;All files (*)")
        if not path:
            return
        try:
            other = Project.load(path)
        except Exception as exc:  # noqa: BLE001
            self._info(tr("Could not read the project: %s") % exc)
            return

        what, ok = QInputDialog.getItem(
            self, tr("Import Properties"), tr("Import:"),
            [tr("Materials"), tr("Supports"), tr("Both")], 2, False)
        if not ok:
            return
        existing = {m.name for m in self.project.materials}
        n_mat = n_sup = 0
        if what in (tr("Materials"), tr("Both")):
            for m in other.materials:
                clone = type(m).from_dict(m.to_dict()) \
                    if hasattr(m, "from_dict") else m
                name = clone.name
                i = 2
                while name in existing:
                    name = f"{clone.name} ({i})"
                    i += 1
                clone.name = name
                existing.add(name)
                self.project.materials.append(clone)
                n_mat += 1
        if what in (tr("Supports"), tr("Both")):
            for s in getattr(other, "support_types", []) or []:
                self.project.support_types.append(s)
                n_sup += 1
        self.project.is_dirty = True
        self.statusBar().showMessage(
            tr("Imported %d material(s) and %d support type(s). "
               "Duplicated names were numbered rather than overwritten.")
            % (n_mat, n_sup), 12000)

    def _export_image(self) -> None:
        """The model view as a PNG."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        path, _f = QFileDialog.getSaveFileName(
            self, tr("Export Image..."), "",
            "PNG (*.png);;All files (*)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        width, ok = QInputDialog.getInt(
            self, tr("Export Image"), tr("Width in pixels:"),
            1920, 200, 12000)
        if not ok:
            return
        scene = self.canvas.scene()
        rect = scene.itemsBoundingRect()
        if rect.isEmpty():
            self._info(tr("There is nothing to export."))
            return
        height = max(1, int(width * rect.height() / max(rect.width(),
                                                        1e-9)))
        image = QImage(width, height, QImage.Format_ARGB32)
        # White, not transparent: a transparent figure pasted into a
        # report shows whatever is behind it, which is rarely wanted.
        image.fill(0xFFFFFFFF)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        scene.render(painter, QRectF(0, 0, width, height), rect)
        painter.end()
        if not image.save(path):
            self._info(tr("Could not write the image."))
            return
        self.statusBar().showMessage(
            tr("Image exported: %d × %d px to %s")
            % (width, height, path), 10000)

    def _page_setup(self) -> None:
        from PySide6.QtPrintSupport import QPageSetupDialog, QPrinter
        if not hasattr(self, "_printer"):
            self._printer = QPrinter(QPrinter.HighResolution)
        QPageSetupDialog(self._printer, self).exec()

    def _print_preview(self) -> None:
        from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
        if not hasattr(self, "_printer"):
            self._printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintPreviewDialog(self._printer, self)
        dlg.paintRequested.connect(self._render_to_printer)
        dlg.exec()

    def _render_to_printer(self, printer) -> None:
        """Draw the model view onto a printer or preview surface."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter
        scene = self.canvas.scene()
        rect = scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.Antialiasing, True)
        target = QRectF(printer.pageRect(printer.DevicePixel))
        scene.render(painter, target, rect)
        painter.end()

    def _modify_load(self) -> None:
        """Edit an existing load."""
        from PySide6.QtWidgets import QInputDialog

        dist = list(getattr(self.project, "distributed_loads", []))
        line = list(getattr(self.project, "line_loads", []))
        if not dist and not line:
            self._info(tr("There are no loads to modify."))
            return
        labels = []
        for i, ld in enumerate(dist):
            labels.append(tr("Distributed %d: %.3g kPa")
                          % (i + 1, getattr(ld, "magnitude_1", 0.0)
                             or getattr(ld, "magnitude", 0.0) or 0.0))
        for i, ld in enumerate(line):
            labels.append(tr("Line %d: %.3g kN/m")
                          % (i + 1, getattr(ld, "magnitude", 0.0) or 0.0))
        choice, ok = QInputDialog.getItem(
            self, tr("Modify Load"), tr("Load:"), labels, 0, False)
        if not ok:
            return
        idx = labels.index(choice)
        load = dist[idx] if idx < len(dist) else line[idx - len(dist)]
        attr = ("magnitude_1" if hasattr(load, "magnitude_1")
                else "magnitude")
        value, ok = QInputDialog.getDouble(
            self, tr("Modify Load"), tr("Magnitude:"),
            float(getattr(load, attr, 0.0) or 0.0), -1e9, 1e9, 4)
        if not ok:
            return
        setattr(load, attr, value)
        if hasattr(load, "magnitude_2") and \
                getattr(load, "magnitude_2", None) is not None:
            second, ok = QInputDialog.getDouble(
                self, tr("Modify Load"), tr("Magnitude at the far end:"),
                float(load.magnitude_2), -1e9, 1e9, 4)
            if ok:
                load.magnitude_2 = second
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(tr("Load modified."), 5000)

    def _modify_support(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        sups = list(getattr(self.project, "supports", []))
        if not sups:
            self._info(tr("There are no supports to modify."))
            return
        labels = [tr("%d: %s") % (i + 1, self._support_label(s))
                  for i, s in enumerate(sups)]
        choice, ok = QInputDialog.getItem(
            self, tr("Modify Support"), tr("Support:"), labels, 0, False)
        if not ok:
            return
        support = sups[labels.index(choice)]
        types = list(getattr(self.project, "support_types", []))
        if not types:
            self._info(tr("No support types are defined."))
            return
        tlabels = [getattr(t, "DISPLAY_NAME", None)
                   or getattr(t, "TYPE_ID", "?") for t in types]
        tchoice, ok = QInputDialog.getItem(
            self, tr("Modify Support"), tr("Support type:"), tlabels,
            0, False)
        if not ok:
            return
        support.support_type = types[tlabels.index(tchoice)]
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(tr("Support modified."), 5000)

    def _support_label(self, support) -> str:
        stype = getattr(support, "support_type", None) or support
        return str(getattr(stype, "DISPLAY_NAME", None)
                   or getattr(stype, "TYPE_ID", "support"))

    def _move_support(self) -> None:
        """Translate a support without changing its length or angle."""
        from PySide6.QtWidgets import QInputDialog

        sups = list(getattr(self.project, "supports", []))
        if not sups:
            self._info(tr("There are no supports to move."))
            return
        labels = [tr("%d: %s") % (i + 1, self._support_label(s))
                  for i, s in enumerate(sups)]
        choice, ok = QInputDialog.getItem(
            self, tr("Move Support"), tr("Support:"), labels, 0, False)
        if not ok:
            return
        support = sups[labels.index(choice)]
        dx, ok = QInputDialog.getDouble(
            self, tr("Move Support"), tr("Displacement in x:"), 0.0,
            -1e9, 1e9, 4)
        if not ok:
            return
        dy, ok = QInputDialog.getDouble(
            self, tr("Move Support"), tr("Displacement in y:"), 0.0,
            -1e9, 1e9, 4)
        if not ok:
            return
        # Both ends move by the same vector: a support that changed
        # length or inclination on being moved would silently change the
        # force it contributes.
        # ``Vertex`` is IMMUTABLE, so the ends are replaced rather than
        # mutated in place — an in-place update raised at runtime.
        from ogr_core.geometry import Vertex
        for attr in ("head", "tail"):
            pt = getattr(support, attr, None)
            if pt is not None:
                setattr(support, attr, Vertex(pt.x + dx, pt.y + dy))
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("Support moved by (%.3f, %.3f)") % (dx, dy), 5000)

    def _ungroup_pattern(self) -> None:
        """Break a pattern into independent supports.

        The supports themselves already exist individually; ungrouping
        clears the pattern reference so each can be edited or deleted on
        its own without the others following.
        """
        sups = [s for s in getattr(self.project, "supports", [])
                if getattr(s, "pattern_id", None)]
        if not sups:
            self._info(tr(
                "No support belongs to a pattern. Patterns are created "
                "with Add Support Pattern."))
            return
        for s in sups:
            s.pattern_id = None
        self.project.is_dirty = True
        self.canvas.refresh_scene()
        self.statusBar().showMessage(
            tr("%d support(s) ungrouped; each can now be edited on its "
               "own.") % len(sups), 8000)

    def _check_updates(self) -> None:
        """Where to look for a newer version.

        Deliberately does NOT contact a server: a geotechnical tool
        phoning home unannounced is not something to add without asking,
        and an offline machine is a normal place to run this.
        """
        self._info(
            tr("This is OGR Suite %s.") % self.VERSION + "\n\n"
            + tr("Releases are published at opengeorock.org. This "
                 "command does not contact any server: nothing is sent "
                 "from your machine."))

    def _info(self, message: str, title: str = "OGR Slip2D") -> None:
        """Modal information message (used by the groundwater actions)."""
        QMessageBox.information(self, tr(title), message)

    def _gw_method_is_fea(self) -> bool:
        """True when Project Settings selects a finite-element
        groundwater method. The reference only exposes the hydraulic
        modelling options in that case, and so do we."""
        m = getattr(self.project.settings.groundwater, "method", "none")
        return str(m) in ("fea_steady", "fea_transient")

    def _update_groundwater_actions(self) -> None:
        """Enforce the reference's hard dependencies:
        hydraulic properties only with an FEA method, and boundary
        conditions / compute only once a mesh exists."""
        fea = self._gw_method_is_fea()
        has_mesh = (getattr(self.project, "fem_mesh", None) is not None
                    and self.project.fem_mesh.element_count > 0)
        has_result = getattr(self.project, "seepage_result", None) is not None
        for key, enabled in (
            ("gw_hydraulic", fea),
            ("gw_transient", fea),
            ("gw_bcs", has_mesh),
            ("gw_compute", has_mesh),
            ("gw_interpret", has_result),
            ("reset_mesh", has_mesh),
        ):
            act = self._actions.get(key)
            if act is not None:
                act.setEnabled(bool(enabled))

    def _define_hydraulic_properties(self) -> None:
        if not self.project.materials:
            self._info("Define some materials first.")
            return
        from .dialogs.hydraulic_properties_dialog import (
            HydraulicPropertiesDialog,
        )
        if HydraulicPropertiesDialog(self.project, self).exec():
            self.statusBar().showMessage("Hydraulic properties updated",
                                          4000)

    def _seepage_bcs(self):
        """The project's boundary conditions, created with the documented
        defaults the first time (Unknown on the ground surface, zero
        nodal flow on the sides and bottom)."""
        from ogr_fem2d.solvers import default_boundary_conditions
        bcs = getattr(self.project, "seepage_bcs", None)
        mesh = self.project.fem_mesh
        node_ids = {b.node_id for b in bcs.nodes} if bcs else set()
        valid = bcs is not None and node_ids <= set(range(mesh.node_count))
        if not valid:
            bcs = default_boundary_conditions(mesh)
            self.project.seepage_bcs = bcs
        return bcs

    def _set_boundary_conditions(self) -> None:
        mesh = getattr(self.project, "fem_mesh", None)
        if mesh is None or mesh.element_count == 0:
            self._info("Generate the FE mesh first.")
            return
        from .dialogs.boundary_conditions_dialog import (
            BoundaryConditionsDialog,
        )
        bcs = self._seepage_bcs()
        if BoundaryConditionsDialog(mesh, bcs, self).exec():
            self.project.seepage_bcs = bcs
            self.project.is_dirty = True
            self.statusBar().showMessage(
                f"Boundary conditions: {len(bcs.nodes)} nodes, "
                f"{len(bcs.segments)} segments", 5000)

    def _edit_transient_stages(self) -> None:
        """v0.1.30 — edit the transient stages (Phase 6)."""
        from .dialogs.transient_stages_dialog import TransientStagesDialog
        gw = self.project.settings.groundwater
        if TransientStagesDialog(
                gw, self,
                current_bcs=(self._seepage_bcs()
                             if getattr(self.project, 'fem_mesh', None)
                             else None)).exec():
            self.project.is_dirty = True
            self._update_groundwater_actions()
            n = len(gw.transient_stages)
            self.statusBar().showMessage(
                f"Transient: {'on' if gw.transient else 'off'}, "
                f"{n} stage(s)", 5000)

    def _compute_transient(self):
        """Run the staged transient analysis and keep the per-stage
        results. The stage flagged last (or the last one overall) becomes
        the field feeding the stability analysis."""
        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.solvers import (
            TransientSeepageSolver, TransientStage,
        )
        gw = self.project.settings.groundwater
        mesh = self.project.fem_mesh
        props = {}
        for m in self.project.materials:
            props[m.id] = m.hydraulic or HydraulicProperties()
        gamma_w = getattr(gw, "pore_fluid_unit_weight", 9.81)
        solver = TransientSeepageSolver(
            mesh, props, gamma_w=gamma_w, relaxation=0.5,
            tolerance=gw.transient_tolerance,
            max_picard=gw.transient_max_iterations,
            time_steps=gw.transient_time_steps,
        )
        # v0.1.31 — per-stage boundary conditions. Without them the
        # initial state and every stage would share the same conditions,
        # the field would already be at equilibrium and NOTHING would
        # evolve in time: a drawdown needs the initial (high) level to
        # differ from the stage (lowered) level. Each stage may carry its
        # own captured conditions; stages without one fall back to the
        # currently defined set.
        from ogr_fem2d.solvers import SeepageBoundaryConditions
        current = self._seepage_bcs()
        initial = current
        init_dict = getattr(gw, "transient_initial_bcs", None)
        if init_dict:
            initial = SeepageBoundaryConditions.from_dict(init_dict)
        stages = []
        for st in gw.transient_stages:
            sb = st.get("bcs")
            stages.append(TransientStage(
                time=float(st.get("time", 0.0)),
                calculate_sf=bool(st.get("calculate_sf")),
                label=str(st.get("label", "")),
                bcs=(SeepageBoundaryConditions.from_dict(sb) if sb
                     else current),
            ))
        results = solver.solve_transient(stages, initial_bcs=initial)
        self.project.transient_results = results
        self._gw_solver = solver
        self._compute_stage_factors_of_safety(results)
        return results

    def _compute_stage_factors_of_safety(self, results) -> None:
        """Run the stability analysis at every stage flagged
        *Calculate SF* (Phase 6, v0.1.31).

        This is the point of the per-stage checkbox: it turns a transient
        pore-pressure history into a factor-of-safety history, which is
        what an engineer actually needs from a drawdown or a prolonged
        rainfall. Each flagged stage temporarily becomes the project's
        active seepage field, the configured search runs against it, and
        the resulting critical FoS is stored in the stage's notes.

        The search machinery is reused verbatim from ``_ComputeWorker``
        (called synchronously) so the per-stage runs honour exactly the
        same search method and settings as a normal Compute.
        """
        flagged = [(i, r) for i, r in enumerate(results)
                   if r.notes.get("calculate_sf") and r.total_head]
        if not flagged:
            return
        # The stage pressures only reach the LEM through materials set to
        # FEM_SEEPAGE; warn instead of silently reporting a dry FoS.
        from ogr_core.materials import PorePressureType
        if not any(m.pore_pressure == PorePressureType.FEM_SEEPAGE
                   for m in self.project.materials):
            for _i, r in flagged:
                r.notes["fos_warning"] = (
                    "No material uses the FEM seepage pore-pressure type, "
                    "so the stage factors of safety would ignore the "
                    "computed water pressures.")
            return
        method_ids = list(
            self.project.settings.methods.enabled_methods) or [
            "bishop_simplified"]
        saved = getattr(self.project, "seepage_result", None)
        try:
            for _i, r in flagged:
                self.project.seepage_result = r
                worker = _ComputeWorker(self.project, method_ids)
                worker.run()
                per_method = {}
                for mid, sr in (worker.results or {}).items():
                    crit = sr.critical if sr else None
                    if crit is not None:
                        per_method[mid] = crit.fos
                r.notes["fos"] = per_method
                if per_method:
                    r.notes["fos_min"] = min(per_method.values())
        finally:
            self.project.seepage_result = saved

    def _compute_groundwater(self) -> None:
        mesh = getattr(self.project, "fem_mesh", None)
        if mesh is None or mesh.element_count == 0:
            self._info("Generate the FE mesh first.")
            return
        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.solvers import UnsaturatedSeepageSolver
        props = {}
        missing = []
        for m in self.project.materials:
            if m.hydraulic is None:
                missing.append(m.name)
                props[m.id] = HydraulicProperties()
            else:
                props[m.id] = m.hydraulic
        gamma_w = 9.81
        try:
            gamma_w = self.project.settings.groundwater.pore_fluid_unit_weight
        except Exception:  # noqa: BLE001
            pass
        if self.project.settings.groundwater.transient and \
                self.project.settings.groundwater.transient_stages:
            results = self._compute_transient()
            if not results:
                self._info("Transient analysis produced no results.")
                return
            result = results[-1]
            self.project.seepage_result = result
            self._update_groundwater_actions()
            bad = [i for i, r in enumerate(results) if not r.converged]
            msg = (f"Transient: {len(results)} stage(s) solved; final "
                   f"u from {min(result.pore_pressure):.1f} to "
                   f"{max(result.pore_pressure):.1f}")
            if bad:
                msg += f"  (stages not converged: {bad})"
            self.statusBar().showMessage(msg, 9000)
            return
        solver = UnsaturatedSeepageSolver(mesh, props, gamma_w=gamma_w,
                                          relaxation=0.4,
                                          max_iterations=200,
                                          tolerance=1e-5)
        result = solver.solve_unsaturated(self._seepage_bcs())
        self.project.seepage_result = result
        self._gw_solver = solver
        self._update_groundwater_actions()
        if not result.converged:
            msg = result.notes.get("error") or result.notes.get(
                "warning", "did not converge")
            self._info(f"Groundwater analysis: {msg}")
            return
        note = ""
        if missing:
            note = (f"  (default properties used for: "
                    f"{', '.join(missing[:3])})")
        self.statusBar().showMessage(
            f"Groundwater solved in {result.iterations} iterations; "
            f"u from {min(result.pore_pressure):.1f} to "
            f"{max(result.pore_pressure):.1f}{note}", 9000)

    def _interpret_groundwater(self) -> None:
        result = getattr(self.project, "seepage_result", None)
        if result is None:
            self._info("Compute the groundwater analysis first.")
            return
        from .interpret_groundwater_window import (
            InterpretGroundwaterWindow,
        )
        w = InterpretGroundwaterWindow(self.project, result,
                                       getattr(self, "_gw_solver", None),
                                       self)
        w.show()
        self._gw_interpret_window = w

    def _edit_water_pressure_grid(self) -> None:
        """v0.1.23 — edit / import the Water Pressure Grid."""
        from .dialogs.water_pressure_grid_dialog import (
            WaterPressureGridDialog,
        )
        dlg = WaterPressureGridDialog(self.project, self)
        if dlg.exec():
            self.canvas.refresh_scene()
            n = (len(self.project.water_pressure_grid.points)
                 if self.project.water_pressure_grid else 0)
            self.statusBar().showMessage(
                f"Water pressure grid: {n} points", 4000)

    def act_info_viewer(self) -> None:
        p = self.project
        info = (
            f"<b>Project:</b> {p.name}<br>"
            f"<b>Boundaries:</b> {len(p.boundaries)}<br>"
            f"<b>Materials:</b> {len(p.materials)}<br>"
            f"<b>Supports:</b> {len(p.supports)}<br>"
            f"<b>Distributed loads:</b> {len(p.distributed_loads)}<br>"
            f"<b>Line loads:</b> {len(p.line_loads)}<br>"
            f"<b>Bounding box:</b> {p.bounding_box()}<br>"
            f"<b>Search:</b> {p.settings.search.search_method}<br>"
            f"<b>Author:</b> {p.settings.summary.author}"
        )
        QMessageBox.information(self, tr("Info Viewer"), info)

    def act_compute(self) -> None:
        if not self.project.boundaries:
            QMessageBox.warning(self, tr("Compute"),
                                "No model to compute. Add an external boundary first.")
            return
        # v0.1.68 — a rapid drawdown that cannot run must say so instead
        # of quietly reporting the ordinary factor of safety, which looks
        # exactly like a successful analysis. v0.1.77 — the same guard now
        # covers the finite-element seepage field, for the same reason:
        # without a field, u = 0 everywhere and the result looks like a
        # dry slope. v0.1.78 stores the field in the .ogr, so reopening a
        # solved project no longer trips this; it still catches a project
        # that was never solved, or whose mesh has been regenerated since
        # (which clears the field — see act_generate_mesh/_reset_fem_mesh).
        from ogr_slip2d.analysis_runner import check_analysis_settings
        _why = check_analysis_settings(self.project)
        if _why:
            QMessageBox.warning(self, tr("Compute"), "\n\n".join(_why))
            return
        if not self.project.materials:
            QMessageBox.warning(self, tr("Compute"), "No materials defined.")
            return

        # v0.1.9 — pass ALL enabled methods, not just the first.
        method_ids = list(self.project.settings.methods.enabled_methods) or [
            "bishop_simplified",
        ]
        self.prog = ComputeProgressDialog(self)
        self.worker = _ComputeWorker(self.project, method_ids)
        self.worker.progress.connect(self.prog.update_progress)
        self.worker.finished_result.connect(self._on_compute_done)
        self.worker.failed.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self.worker.finished.connect(self.prog.accept)
        self.worker.start()
        self.prog.exec()

    def _on_compute_done(self, results) -> None:
        """Handle the dict {method_id: SearchResult} from the worker.

        v0.1.9: Compute now produces results for every enabled method.
        We store the full dict and display the first method's result
        in the main canvas; the Interpret window has a method selector.
        """
        # v0.1.9: results is a dict {method_id: SearchResult}
        self.last_search_results = results
        # v0.1.77 — a method that could not run, or a setting the chosen
        # search does not read, is now reported. Ticking "Janbu Corrected"
        # used to remove it from the results with no trace of why. Not a
        # dialog: this method runs inside the test suite, where a modal
        # blocks forever without a display.
        worker = getattr(self, "worker", None)
        self.last_compute_warnings = list(getattr(worker, "warnings", []) or [])
        if self.last_compute_warnings:
            self.ogr_status.showMessage(self.last_compute_warnings[0], 15000)
        if not results:
            self.last_search_result = None
            self.ogr_status.showMessage("No methods produced results.", 6000)
            return
        # Pick the first enabled method's result for the main canvas
        first_id = next(iter(results))
        first_result = results[first_id]
        self.last_search_result = first_result  # back-compat
        self.results_dock.show_result(first_result)
        self.canvas.display_search_result(first_result)
        critical = first_result.critical
        if critical:
            n_methods = len(results)
            extra = (
                f"  ({n_methods} methods computed — "
                f"open Interpret for full results)"
                if n_methods > 1 else ""
            )
            warn = self._ordinary_pore_pressure_warning(results)
            self.ogr_status.showMessage(
                f"{tr('Critical FoS')} ({first_id}): "
                f"{critical.fos:.3f}{extra}{warn}", 10000,
            )
            if self.project.results_path:
                try:
                    save_results(self.project.results_path, first_result,
                                 project_id=self.project.id)
                except Exception:  # noqa: BLE001
                    pass
        else:
            self.ogr_status.showMessage("No valid failure surface found.", 6000)

    @staticmethod
    def _ordinary_pore_pressure_warning(results) -> str:
        """Warn when Ordinary/Fellenius hit negative effective normals.

        v0.1.62 — not a defect to fix but a property of the method: with
        no interslice forces, a high pore pressure on a steep part of the
        arc drives N' below zero, the clamp discards the deficit and the
        factor of safety comes out low (Whitman and Bailey 1967 measured
        up to 60 %; Bishop 1955 stays under 7 %). Saying so is the only
        honest option — a reported number nobody questions is worse than
        a reported number with its caveat attached.
        """
        res = results.get("ordinary_fellenius") if results else None
        critical = getattr(res, "critical", None) if res else None
        if critical is None:
            return ""
        details = getattr(critical, "details", None) or {}
        n_bad = int(details.get("negative_effective_normal", 0) or 0)
        if n_bad <= 0:
            return ""
        n_tot = int(details.get("num_slices", 0) or 0)
        return "  — " + (
            tr("Ordinary/Fellenius: %d of %d slices had a negative "
               "effective normal force; its FoS is underestimated.")
            % (n_bad, n_tot)
        )

    def act_interpret(self) -> None:
        results = getattr(self, "last_search_results", None)
        if not results:
            QMessageBox.information(self, tr("Interpret"),
                                    "Run Compute first (Ctrl+T).")
            return
        # v0.1.9: pass the full dict so the InterpretWindow can offer
        # a method selector
        win = InterpretWindow(self.project, results, self)
        win.closed.connect(lambda: self._forget_interpret(win))
        self.interpret_windows.append(win)
        win.show()

    def _forget_interpret(self, win) -> None:
        if win in self.interpret_windows:
            self.interpret_windows.remove(win)

    # ==================================================================
    # Properties
    # ==================================================================
    def act_define_materials(self) -> None:
        dlg = MaterialPropertiesDialog(
            self.project.materials, self, units_obj=self.project.settings.units,
            gw_method=str(self.project.settings.groundwater.method),
            # v0.1.60 — the saturated unit weight is only offered when a
            # water table exists to separate the two zones.
            has_water_table=bool(
                self.project.boundaries_of(BoundaryType.WATER_TABLE)),
            # v0.1.62 — the assignable water surfaces, already labelled and
            # translated here so ogr_core stays free of the interface.
            water_surfaces=self._water_surface_choices(),
            rapid_drawdown=bool(
                self.project.settings.groundwater.rapid_drawdown),
            # v0.1.72 — B̄ belongs to the effective-stress procedure and
            # the undrained envelope to the three multi-stage ones, so the
            # dialog needs to know which is configured to show only the
            # one the analysis will actually read.
            drawdown_method=str(
                self.project.settings.groundwater.rapid_drawdown_method),
            # v0.1.75 — the other advanced option, whose material
            # fields waited for their engine.
            excess_pore_pressure=bool(
                self.project.settings.groundwater.excess_pore_pressure),
        )
        if dlg.exec():
            self.project.materials = dlg.result_materials()
            self.project._notify("materials_changed")

    # ------------------------------------------------------------------
    def _water_surface_choices(self) -> list[tuple[str, str]]:
        """(boundary id, translated label) for every assignable surface.

        Piezometric lines are identified by their number, which comes from
        project order — so the label is built here, where ``tr()`` lives,
        rather than in ``ogr_core``.
        """
        from ogr_core.hydraulic import water_surface_index, water_surfaces

        out: list[tuple[str, str]] = []
        for b in water_surfaces(self.project):
            n = water_surface_index(self.project, b)
            if b.btype == BoundaryType.WATER_TABLE:
                total = len(self.project.boundaries_of(
                    BoundaryType.WATER_TABLE))
                label = (tr("Water Table") if total <= 1
                         else "%s %d" % (tr("Water Table"), n))
            else:
                label = "%s %d" % (tr("Piezometric Line"), n)
            out.append((b.id, label))
        return out

    def act_assign_water_surface(self) -> None:
        """Assign one water surface to several materials at once."""
        from ogr_gui.dialogs.assign_water_surface_dialog import (
            AssignWaterSurfaceDialog,
        )

        choices = self._water_surface_choices()
        if not choices:
            self.statusBar().showMessage(
                tr("Draw a water table or a piezometric line first."), 5000)
            return
        if not self.project.materials:
            self.statusBar().showMessage(
                tr("This project has no materials yet."), 5000)
            return

        mats = [(m.id, m.name, m.water_surface_id)
                for m in self.project.materials]
        dlg = AssignWaterSurfaceDialog(choices, mats, self)
        if not dlg.exec():
            return
        wid = dlg.selected_surface_id()
        picked = set(dlg.selected_material_ids())
        cleared = set(dlg.cleared_material_ids())
        for m in self.project.materials:
            if m.id in picked:
                m.water_surface_id = wid
            elif m.id in cleared:
                m.water_surface_id = None
        self.project._notify("materials_changed")

    # ==================================================================
    # Support menu (v0.1.14)
    # ==================================================================
    def act_define_support(self) -> None:
        """Open the Define Support Properties dialog (Slide-style).

        Allows the user to manage a list of named Support Types, each
        bound to one of the 7 built-in classes (End Anchored, Grouted
        Tieback, Soil Nail, Pile, Geosynthetic, etc.).
        """
        from .dialogs.define_support_dialog import DefineSupportDialog
        dlg = DefineSupportDialog(self.project, self)
        if dlg.exec():
            self.canvas.refresh()
            self.ogr_status.showMessage(
                f"{len(self.project.support_types)} support types defined",
                3000,
            )

    def act_add_support(self) -> None:
        """Enter 2-click canvas mode: click head, click tail."""
        if not self.project.support_types:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "No support types",
                "No support types are defined yet.\n\n"
                "Open Properties → Define Support... first to create at "
                "least one support type.",
            )
            return
        try:
            self.canvas.segment_picked.disconnect(self._on_add_support_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.segment_picked.connect(self._on_add_support_picked)
        self.canvas.set_tool_mode(ToolMode.ADD_SUPPORT)

    def _on_add_support_picked(
        self, x0: float, y0: float, x1: float, y1: float,
    ) -> None:
        from ogr_core.geometry import Vertex
        from ogr_core.support import SupportInstance, ForceApplication, ForceOrientation
        # First support type by default — Slide also uses the
        # "currently active" support type
        stype = self.project.support_types[0]
        force_app = getattr(stype, "_force_application",
                            ForceApplication.ACTIVE)
        orient = getattr(stype, "_orientation",
                         stype.DEFAULT_ORIENTATION)
        u_ang = getattr(stype, "_user_angle_deg", 0.0)
        s = SupportInstance(
            type_id=stype.TYPE_ID,
            head=Vertex(x0, y0), tail=Vertex(x1, y1),
            force_application=force_app,
            orientation=orient,
            user_angle_deg=u_ang,
            name=getattr(stype, "_display_name", stype.DISPLAY_NAME),
            color=getattr(stype, "_color", "#4b0082"),
        )
        self.project.supports.append(s)
        self.project.is_dirty = True
        self.project._notify("supports_changed")
        try:
            self.canvas.segment_picked.disconnect(self._on_add_support_picked)
        except (TypeError, RuntimeError):
            pass
        # Stay in ADD_SUPPORT mode so the user can place several in a
        # row (Slide behaviour). Reconnect.
        self.canvas.segment_picked.connect(self._on_add_support_picked)
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Support added ({len(self.project.supports)} total). "
            "Click again to add another, or Esc to finish.", 3000,
        )

    def act_add_support_pattern(self) -> None:
        """Open the Add Support Pattern dialog, then pick segment."""
        if not self.project.support_types:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "No support types",
                "No support types are defined yet.\n\n"
                "Open Properties → Define Support... first.",
            )
            return
        from .dialogs.support_pattern_dialog import AddSupportPatternDialog
        dlg = AddSupportPatternDialog(self.project, self)
        if not dlg.exec() or dlg.pattern is None:
            return
        self._active_pattern = dlg.pattern
        try:
            self.canvas.segment_picked.disconnect(self._on_pattern_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.segment_picked.connect(self._on_pattern_picked)
        self.canvas.set_tool_mode(ToolMode.ADD_SUPPORT_PATTERN)
        self.ogr_status.showMessage(
            "Click two points along the slope boundary; pattern will "
            "be generated automatically.", 8000,
        )

    def _on_pattern_picked(
        self, x0: float, y0: float, x1: float, y1: float,
    ) -> None:
        from ogr_core.geometry import Vertex
        pat = getattr(self, "_active_pattern", None)
        if pat is None:
            return
        new_supports = pat.generate_along_segment(
            Vertex(x0, y0), Vertex(x1, y1),
        )
        # Fill in display name / color from the support type metadata
        stype_by_id = {st.TYPE_ID: st for st in self.project.support_types}
        for s in new_supports:
            st = stype_by_id.get(s.type_id)
            if st is not None:
                s.name = getattr(st, "_display_name", st.DISPLAY_NAME)
                s.color = getattr(st, "_color", "#4b0082")
        self.project.supports.extend(new_supports)
        self.project.is_dirty = True
        self.project._notify("supports_changed")
        try:
            self.canvas.segment_picked.disconnect(self._on_pattern_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.set_tool_mode(ToolMode.SELECT)
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Pattern generated: {len(new_supports)} supports added "
            f"({len(self.project.supports)} total).", 4000,
        )

    def act_delete_support_mode(self) -> None:
        """Enter Delete Support mode: clicking a support removes it."""
        try:
            self.canvas.support_clicked.disconnect(self._on_delete_support_clicked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.support_clicked.connect(self._on_delete_support_clicked)
        self.canvas.set_tool_mode(ToolMode.DELETE_SUPPORT)

    def _on_delete_support_clicked(self, idx: int) -> None:
        if 0 <= idx < len(self.project.supports):
            removed = self.project.supports.pop(idx)
            self.project.is_dirty = True
            self.project._notify("supports_changed")
            self.canvas.refresh()
            self.ogr_status.showMessage(
                f"Support deleted ({len(self.project.supports)} remain). "
                "Click another or Esc to finish.", 3000,
            )

    def act_stretch_support_mode(self) -> None:
        """Enter Stretch Support mode: 2 clicks (endpoint, new position)."""
        try:
            self.canvas.segment_picked.disconnect(self._on_stretch_support_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.segment_picked.connect(self._on_stretch_support_picked)
        self.canvas.set_tool_mode(ToolMode.STRETCH_SUPPORT)

    def _on_stretch_support_picked(
        self, x0: float, y0: float, x1: float, y1: float,
    ) -> None:
        """Find the nearest support endpoint to (x0, y0) and move it
        to (x1, y1)."""
        import math
        from ogr_core.geometry import Vertex
        best = None
        best_d = float("inf")
        for i, s in enumerate(self.project.supports):
            for end_name, p in (("head", s.head), ("tail", s.tail)):
                d = math.hypot(p.x - x0, p.y - y0)
                if d < best_d:
                    best_d = d
                    best = (i, end_name)
        if best is None:
            return
        idx, end_name = best
        s = self.project.supports[idx]
        if end_name == "head":
            s.head = Vertex(x1, y1)
        else:
            s.tail = Vertex(x1, y1)
        self.project.is_dirty = True
        self.project._notify("supports_changed")
        try:
            self.canvas.segment_picked.disconnect(self._on_stretch_support_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.set_tool_mode(ToolMode.SELECT)
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Support {idx + 1} {end_name} stretched.", 3000,
        )

    # v0.1.15 — support right-click context menu actions
    def _on_support_action_requested(self, action: str, sidx: int) -> None:
        if sidx < 0 or sidx >= len(self.project.supports):
            return
        if action == "support_delete":
            self.project.supports.pop(sidx)
            self.project.is_dirty = True
            self.project._notify("supports_changed")
            self.canvas.refresh()
            self.ogr_status.showMessage("Support deleted.", 3000)
        elif action == "support_stretch":
            # Auto-pick the clicked support as the target and switch to stretch mode
            self._selected_support_idx = sidx
            self.act_stretch_support_mode()
        elif action == "support_properties":
            from .dialogs.support_properties_dialog import SupportInstancePropertiesDialog
            dlg = SupportInstancePropertiesDialog(
                self.project.supports[sidx], self.project, self,
            )
            if dlg.exec():
                self.project.is_dirty = True
                self.project._notify("supports_changed")
                self.canvas.refresh()
        elif action == "support_modify_pattern":
            from .dialogs.modify_support_pattern_dialog import (
                ModifySupportPatternDialog,
            )
            dlg = ModifySupportPatternDialog(self.project, sidx, self)
            if dlg.exec():
                self.project.is_dirty = True
                self.project._notify("supports_changed")
                self.canvas.refresh()


    # ----- v0.1.7: dynamic action availability ------------------------
    def _on_project_event(self, event: str) -> None:
        """Project notified a state change — refresh conditional UI."""
        self.refresh_action_availability()

    def _attach_project(self, project: "Project") -> None:
        """Bind a (new or loaded) project to all UI that depends on it.

        v0.1.16 fix — when the user creates a New project or Opens a
        file, the previous code reassigned ``self.project`` but left the
        change-listener bound to the OLD project. As a result, changing
        the Search Method in the new project never refreshed the menu
        state, leaving Auto Grid / Add Grid greyed out regardless of the
        selected method. This helper rebinds the listener and forces an
        immediate availability refresh, so the grid actions track the
        current Search Method correctly.
        """
        self.project = project
        # (Re)connect the change listener to THIS project instance.
        try:
            project.add_listener(self._on_project_event)
        except Exception:  # noqa: BLE001
            pass
        self.canvas.set_project(project)
        # Refresh the menu/toolbar enabled-state for the new project.
        self.refresh_action_availability()

    def refresh_action_availability(self) -> None:
        """Greys out actions whose preconditions are not met (Slide-style).

        Rules:
          - Add Tension Crack: only one allowed.
          - Define Tension Crack: enabled only if a TC boundary exists.
          - Add Water Table: only one allowed.
          - Add Drawdown Line: only if Rapid Drawdown analysis enabled
            in Project Settings, AND no existing drawdown line.
        """
        actions = getattr(self, "_actions", None)
        if not actions:
            return
        boundaries = self.project.boundaries

        def has_btype(bt) -> bool:
            return any(b.btype == bt for b in boundaries)

        # Tension Crack: max one
        has_tc = has_btype(BoundaryType.TENSION_CRACK)
        if "add_crack" in actions:
            actions["add_crack"].setEnabled(not has_tc)
            actions["add_crack"].setToolTip(
                "Only one Tension Crack boundary is allowed.\n"
                "Delete the existing one to add a new one."
                if has_tc else "Add Tension Crack"
            )
        if "def_tension_crack" in actions:
            # v0.1.10: Define Tension Crack action stays always enabled.
            # If there's no TC boundary, the handler shows an info dialog.
            # This avoids a stale-disabled-state bug seen in v0.1.9 where
            # a project listener race could leave the action greyed out
            # even after a TC boundary was added.
            actions["def_tension_crack"].setEnabled(True)
            actions["def_tension_crack"].setToolTip(
                tr("Define Tension Crack hydraulic properties")
                if has_tc else
                "Define Tension Crack hydraulic properties\n"
                "(add a Tension Crack boundary first via "
                "Boundaries → Add Tension Crack)"
            )

        # Water Table: max one
        if "add_wt" in actions:
            has_wt = has_btype(BoundaryType.WATER_TABLE)
            actions["add_wt"].setEnabled(not has_wt)
            actions["add_wt"].setToolTip(
                tr("Only one Water Table is allowed.")
                if has_wt else "Add Water Table"
            )

        # Drawdown Line: requires Rapid Drawdown enabled
        rapid_drawdown = getattr(
            self.project.settings.groundwater, "rapid_drawdown", False
        )
        if "add_drawdown" in actions:
            has_dd = has_btype(BoundaryType.DRAWDOWN)
            actions["add_drawdown"].setEnabled(
                rapid_drawdown and not has_dd
            )
            if not rapid_drawdown:
                actions["add_drawdown"].setToolTip(
                    "Drawdown Line is only available when\n"
                    "Project Settings → Groundwater → Advanced →\n"
                    "Rapid Drawdown is enabled."
                )
            elif has_dd:
                actions["add_drawdown"].setToolTip(
                    tr("Only one Drawdown Line is allowed.")
                )
            else:
                actions["add_drawdown"].setToolTip(tr("Add Drawdown Line"))

        # v0.1.70 — the sweep needs the same analysis enabled, but NOT a
        # drawn line: it supplies its own levels, and a project without a
        # drawdown line is exactly the one whose user has only ever seen
        # the total-drawdown answer.
        if "drawdown_sweep" in actions:
            actions["drawdown_sweep"].setEnabled(rapid_drawdown)
            actions["drawdown_sweep"].setToolTip(
                tr("Search at a range of reservoir levels. The total "
                   "drawdown is not always the critical one.")
                if rapid_drawdown else
                "Drawdown Level Sweep is only available when\n"
                "Project Settings → Groundwater → Advanced →\n"
                "Rapid Drawdown is enabled."
            )

        # v0.1.12 — Greying-out grid actions when the current search
        # method does NOT use a centre grid (Slope/Auto Refine/Block/
        # Path/SA). The actions stay visible so the user always sees
        # them in the menu/toolbar; only their interactivity is
        # disabled (Slide convention).
        try:
            uses_grid = self.project.settings.search.uses_grid()
        except Exception:  # noqa: BLE001
            uses_grid = True
        for key in ("auto_grid", "add_grid"):
            if key in actions:
                actions[key].setEnabled(uses_grid)
                if uses_grid:
                    actions[key].setToolTip(
                        tr("Auto-generate the slip-circle search grid")
                        if key == "auto_grid"
                        else "Define a slip-circle search grid manually"
                    )
                else:
                    actions[key].setToolTip(
                        "The current Search Method does not use a\n"
                        "slip-circle centre grid.\n"
                        "Switch to Surface Options → Grid Search to\n"
                        "use this action."
                    )

        # v0.1.17 — "Add Surface" (Block Search objects) is only
        # meaningful for the Block Search method. Enable it when Block
        # Search is selected; grey it out otherwise (Slide convention:
        # the action stays visible).
        try:
            is_block = (self.project.settings.search.search_method
                        == "block")
        except Exception:  # noqa: BLE001
            is_block = False
        if "surf_3pts" in actions:
            actions["surf_3pts"].setEnabled(is_block)
            actions["surf_3pts"].setToolTip(
                tr("Add a Block Search object (search window) on the model")
                if is_block else
                "Add Surface is only available with the Block Search\n"
                "method. Set Surface Options → Surface Type =\n"
                "Non-Circular, Search Method = Block Search."
            )

    # ----- v0.1.7: Loadings (interactive in v0.1.8) ------------------
    def act_add_distributed_load(self) -> None:
        """Add a Distributed Load along a boundary segment.

        v0.1.8 flow:
          1. Open the DistributedLoadDialog to specify magnitude /
             orientation / distribution.
          2. Activate ADD_DISTRIBUTED_LOAD tool mode.
          3. User clicks two points on the canvas (snapped to boundaries).
          4. Canvas emits segment_picked → handler creates the load.
        """
        from .dialogs.load_dialogs import DistributedLoadDialog

        dlg = DistributedLoadDialog(parent=self)
        if not dlg.exec():
            return

        # Capture properties for the next click
        self._pending_dist_load = {
            "magnitude_1": dlg.magnitude_1(),
            "magnitude_2": dlg.magnitude_2(),
            "orientation": dlg.orientation(),
            "angle_deg": dlg.angle_deg(),
            "distribution": dlg.distribution(),
            # v0.1.75 — the checkbox has been on this dialog since
            # the load dialogs were written, and ``excess_pp()`` was
            # never called by anyone: the model field did not exist,
            # so the tick went nowhere.
            "creates_excess_pore_pressure": dlg.excess_pp(),
        }
        # Disconnect anything previously connected, then connect once
        try:
            self.canvas.segment_picked.disconnect(self._on_dist_load_segment_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.segment_picked.connect(self._on_dist_load_segment_picked)
        self.canvas.set_tool_mode(ToolMode.ADD_DISTRIBUTED_LOAD)
        self.ogr_status.showMessage(
            "Click the start point of the load on a boundary, "
            "then the end point. Esc to cancel.", 8000,
        )

    def _on_dist_load_segment_picked(
        self, sx: float, sy: float, ex: float, ey: float,
    ) -> None:
        try:
            self.canvas.segment_picked.disconnect(self._on_dist_load_segment_picked)
        except (TypeError, RuntimeError):
            pass
        if not getattr(self, "_pending_dist_load", None):
            return
        params = self._pending_dist_load
        self._pending_dist_load = None
        from ogr_core.geometry import Vertex as _V
        from ogr_core.loads import DistributedLoad
        load = DistributedLoad(
            start=_V(sx, sy),
            end=_V(ex, ey),
            magnitude_1=params["magnitude_1"],
            magnitude_2=params["magnitude_2"],
            orientation=params["orientation"],
            angle_deg=params["angle_deg"],
            distribution=params["distribution"],
            name=f"Dist {params['magnitude_1']:.1f} kN/m²",
        )
        self.project.distributed_loads.append(load)
        self.project.is_dirty = True
        self.project._notify("loads_changed")
        self.canvas.set_tool_mode(ToolMode.SELECT)
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Distributed Load added: {params['magnitude_1']:.1f} kN/m² "
            f"between ({sx:.2f},{sy:.2f}) and ({ex:.2f},{ey:.2f})", 4000,
        )

    def act_add_line_load(self) -> None:
        """Add a Line Load (force per unit out-of-plane length at a point).

        v0.1.8 flow: dialog → click on canvas → load placed.
        """
        from .dialogs.load_dialogs import LineLoadDialog

        dlg = LineLoadDialog(parent=self)
        if not dlg.exec():
            return

        self._pending_line_load = {
            "magnitude": dlg.magnitude_1(),
            "orientation": dlg.orientation(),
            "angle_deg": dlg.angle_deg(),
            "creates_excess_pore_pressure": dlg.excess_pp(),
        }
        try:
            self.canvas.point_picked.disconnect(self._on_line_load_point_picked)
        except (TypeError, RuntimeError):
            pass
        self.canvas.point_picked.connect(self._on_line_load_point_picked)
        self.canvas.set_tool_mode(ToolMode.ADD_LINE_LOAD)
        self.ogr_status.showMessage(
            "Click on a boundary to place the line load. Esc to cancel.", 6000,
        )

    def act_seismic_load(self) -> None:
        """Open the Seismic Load dialog (pseudo-static k_h / k_v)."""
        from .dialogs.seismic_dialog import SeismicLoadDialog
        dlg = SeismicLoadDialog(self.project.seismic, self)
        if dlg.exec():
            dlg.apply()
            self.project.is_dirty = True
            self.project._notify("seismic_changed")
            s = self.project.seismic
            if s.enabled:
                self.ogr_status.showMessage(
                    f"Seismic load: k_h = {s.kh:+.3f}, k_v = {s.kv:+.3f}", 4000,
                )
            else:
                self.ogr_status.showMessage("Seismic load disabled", 3000)

    def act_delete_load(self) -> None:
        """Delete a load via a list dialog (also available via right-click).

        Opens a list of all loads in the project, the user picks one
        or more (multi-select), they are deleted.
        """
        loads_listing: list[tuple[str, int, str]] = []
        for i, ld in enumerate(self.project.distributed_loads):
            loads_listing.append((
                "distributed", i,
                f"Distributed: {ld.magnitude_1:.1f} kN/m² "
                f"({ld.start.x:.1f}, {ld.start.y:.1f}) → "
                f"({ld.end.x:.1f}, {ld.end.y:.1f})  "
                f"[{ld.orientation.value}]",
            ))
        for i, ld in enumerate(self.project.line_loads):
            loads_listing.append((
                "line", i,
                f"Line: {ld.magnitude:.1f} kN/m at "
                f"({ld.point.x:.1f}, {ld.point.y:.1f})  "
                f"[{ld.orientation.value}]",
            ))
        if not loads_listing:
            QMessageBox.information(
                self, "Delete Load", "No loads in the project.",
            )
            return

        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QListWidget,
            QListWidgetItem, QVBoxLayout, QLabel,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Delete Load"))
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(tr("Select one or more loads to delete:")))
        listw = QListWidget()
        listw.setSelectionMode(QListWidget.MultiSelection)
        for kind, idx, label in loads_listing:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (kind, idx))
            listw.addItem(item)
        v.addWidget(listw)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.resize(520, 360)
        if dlg.exec() != QDialog.Accepted:
            return

        targets: list[tuple[str, int]] = [
            listw.item(i).data(Qt.UserRole)
            for i in range(listw.count())
            if listw.item(i).isSelected()
        ]
        if not targets:
            return
        # Sort descending so popping doesn't shift earlier indices
        targets.sort(key=lambda kv: (kv[0], -kv[1]))

        n_dist = n_line = 0
        for kind, idx in targets:
            if kind == "distributed" and 0 <= idx < len(self.project.distributed_loads):
                self.project.distributed_loads.pop(idx)
                n_dist += 1
            elif kind == "line" and 0 <= idx < len(self.project.line_loads):
                self.project.line_loads.pop(idx)
                n_line += 1
        self.project.is_dirty = True
        self.project._notify("loads_changed")
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Deleted {n_dist} distributed + {n_line} line loads.", 4000,
        )

    def _on_load_action(self, action: str, kind: str, idx: int) -> None:
        """Handle right-click context menu on loads (Modify / Delete)."""
        if action == "delete":
            if kind == "distributed" and 0 <= idx < len(self.project.distributed_loads):
                load = self.project.distributed_loads.pop(idx)
                self.project.is_dirty = True
                self.project._notify("loads_changed")
                self.canvas.refresh()
                self.ogr_status.showMessage(
                    f"Deleted Distributed Load: {load.magnitude_1:.1f} kN/m²", 3000,
                )
            elif kind == "line" and 0 <= idx < len(self.project.line_loads):
                load = self.project.line_loads.pop(idx)
                self.project.is_dirty = True
                self.project._notify("loads_changed")
                self.canvas.refresh()
                self.ogr_status.showMessage(
                    f"Deleted Line Load: {load.magnitude:.1f} kN/m", 3000,
                )
        elif action == "modify":
            if kind == "distributed" and 0 <= idx < len(self.project.distributed_loads):
                from .dialogs.load_dialogs import DistributedLoadDialog
                load = self.project.distributed_loads[idx]
                dlg = DistributedLoadDialog(existing=load, parent=self)
                if dlg.exec():
                    load.magnitude_1 = dlg.magnitude_1()
                    load.magnitude_2 = dlg.magnitude_2()
                    load.orientation = dlg.orientation()
                    load.angle_deg = dlg.angle_deg()
                    load.distribution = dlg.distribution()
                    load.creates_excess_pore_pressure = dlg.excess_pp()
                    self.project.is_dirty = True
                    self.project._notify("loads_changed")
                    self.canvas.refresh()
            elif kind == "line" and 0 <= idx < len(self.project.line_loads):
                from .dialogs.load_dialogs import LineLoadDialog
                load = self.project.line_loads[idx]
                dlg = LineLoadDialog(existing=load, parent=self)
                if dlg.exec():
                    load.magnitude = dlg.magnitude_1()
                    load.orientation = dlg.orientation()
                    load.angle_deg = dlg.angle_deg()
                    load.creates_excess_pore_pressure = dlg.excess_pp()
                    self.project.is_dirty = True
                    self.project._notify("loads_changed")
                    self.canvas.refresh()

    def _on_line_load_point_picked(self, x: float, y: float) -> None:
        try:
            self.canvas.point_picked.disconnect(self._on_line_load_point_picked)
        except (TypeError, RuntimeError):
            pass
        if not getattr(self, "_pending_line_load", None):
            return
        params = self._pending_line_load
        self._pending_line_load = None
        from ogr_core.geometry import Vertex as _V
        from ogr_core.loads import LineLoad
        load = LineLoad(
            point=_V(x, y),
            magnitude=params["magnitude"],
            orientation=params["orientation"],
            angle_deg=params["angle_deg"],
            name=f"Line {params['magnitude']:.1f} kN/m",
        )
        self.project.line_loads.append(load)
        self.project.is_dirty = True
        self.project._notify("loads_changed")
        self.canvas.set_tool_mode(ToolMode.SELECT)
        self.canvas.refresh()
        self.ogr_status.showMessage(
            f"Line Load added at ({x:.2f}, {y:.2f}): "
            f"{params['magnitude']:.1f} kN/m", 4000,
        )

    def act_define_tension_crack(self) -> None:
        """Open the Define Tension Crack dialog (Slide-style).

        Slide rule: this option only makes sense if a Tension Crack
        boundary exists. Otherwise show an informational message.
        """
        has_tc = any(
            b.btype == BoundaryType.TENSION_CRACK
            for b in self.project.boundaries
        )
        if not has_tc:
            QMessageBox.information(
                self, "Define Tension Crack",
                "No Tension Crack boundary in the project.\n\n"
                "Add one first via Boundaries → Add Tension Crack."
            )
            return
        from .dialogs.tension_crack_dialog import DefineTensionCrackDialog
        dlg = DefineTensionCrackDialog(self.project, self)
        if dlg.exec():
            self.project.tension_crack_properties = dlg.result_properties()
            self.project.is_dirty = True
            self.project._notify("tension_crack_changed")
            self.ogr_status.showMessage(
                f"Tension Crack: "
                f"{self.project.tension_crack_properties.mode.value}",
                3000,
            )

    def act_open_assign_panel(self) -> None:
        """Open the floating Assign Materials panel.

        Pick a material on the panel's list, then click on any region of
        the canvas to paint it. The panel stays open until closed.
        """
        if not self.project.materials:
            QMessageBox.information(
                self, "Assign Materials",
                "No materials defined yet.\n"
                "Use Properties → Define Materials… first."
            )
            return
        if self.assign_panel is not None and self.assign_panel.isVisible():
            self.assign_panel.raise_()
            return
        self.assign_panel = AssignMaterialsPanel(self.project.materials, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.assign_panel)
        self.assign_panel.material_selected.connect(
            self._on_assign_material_selected
        )
        self.assign_panel.closed_by_user.connect(self._on_assign_panel_closed)
        self.assign_panel.setFloating(True)
        self.assign_panel.resize(260, 340)
        self.assign_panel.show()
        self.canvas.set_tool_mode(ToolMode.ASSIGN_MATERIAL)
        self.ogr_status.showMessage(
            "Pick a material, then click a region on the canvas to paint it.",
            5000,
        )

    def _on_assign_material_selected(self, material_id: str) -> None:
        self._assign_active_material_id = material_id or None

    def _on_assign_panel_closed(self) -> None:
        self.assign_panel = None
        self._assign_active_material_id = None
        if self.canvas.tool_mode == ToolMode.ASSIGN_MATERIAL:
            self.canvas.set_tool_mode(ToolMode.SELECT)

    def _on_canvas_assign_click(self, x: float, y: float) -> None:
        """Click in ASSIGN_MATERIAL mode — paint the region under cursor.

        v0.1.6: uses the Slide-style click-record system. The click is
        recorded as a RegionAssignment on the project; every future
        refresh re-localises the click into whatever region currently
        contains (x, y). This means the assignment survives boundary
        edits.
        """
        if self._assign_active_material_id is None:
            self.ogr_status.showMessage(
                "Pick a material in the Assign panel first.", 3000
            )
            return
        if self.project.external_boundary() is None:
            self.ogr_status.showMessage(
                "Draw the External Boundary first.", 3000
            )
            return
        mid = self._assign_active_material_id
        self.command_stack.do(
            self.project,
            PaintRegionCommand(x=x, y=y, material_id=mid),
        )
        mat = self.project.material_by_id(mid)
        name = mat.name if mat else "(none)"
        self.ogr_status.showMessage(f"Painted region with '{name}'.", 2000)

    # ==================================================================
    # Window
    # ==================================================================
    def act_terminal(self, checked: bool) -> None:
        self.terminal_dock.setVisible(checked)
        if checked:
            self.terminal_dock.raise_()
            self.terminal_dock.terminal.setFocus()

    # ==================================================================
    # Help
    # ==================================================================
    def act_help(self) -> None:
        QMessageBox.information(
            self, tr("Help Topics"),
            "Online docs: https://github.com/samuelsl27/OGR-Slip2D\n"
            "Window → Terminal opens a Python REPL connected to the live project.",
        )

    def act_about(self) -> None:
        AboutDialog(self).exec()

    # ==================================================================
    # Status-bar toggles
    # ==================================================================
    def _on_snap_toggle(self, on: bool) -> None:
        self.canvas.snap_settings.snap = on

    def _on_grid_toggle(self, on: bool) -> None:
        self.canvas.set_grid_visible(on)
        self._actions["grid_toggle"].setChecked(on)

    def _on_ortho_toggle(self, on: bool) -> None:
        self.canvas.snap_settings.ortho = on

    def _on_osnap_toggle(self, on: bool) -> None:
        self.canvas.snap_settings.osnap = on

    def _on_manual_coords(self, x: float, y: float) -> None:
        """Status-bar x,y input was submitted. Add the point if a
        drawing tool is active; otherwise show a helpful message."""
        added = self.canvas.add_manual_point(x, y)
        if added:
            self.ogr_status.showMessage(
                f"Added vertex ({x:+.3f}, {y:+.3f})", 2000
            )
        else:
            self.ogr_status.showMessage(
                "Activate a boundary drawing tool first (Ctrl+1 … Ctrl+6).",
                3000,
            )

    # ==================================================================
    # Language & theme
    # ==================================================================
    def _apply_language(self, code: str) -> None:
        set_language(code)
        QMessageBox.information(
            self, "Language",
            f"Language changed to {code.upper()}.\n"
            "Restart the application to fully apply translations."
        )

    def _apply_theme(self, name: str) -> None:
        self.active_theme = name
        apply_theme(QApplication.instance(), name)

    # ==================================================================
    # v0.1.2 — Boundary editing handlers
    # ==================================================================
    def _on_boundary_drawn(self, boundary) -> None:
        """Canvas emitted a completed new boundary → persist it.

        Invariant: at most **one** External boundary in the project. If
        the user draws a new External while one exists, the old one is
        replaced atomically (Macro command = remove + add).
        """
        # Single-External enforcement
        if boundary.btype == BoundaryType.EXTERNAL:
            existing_ext_idx = next(
                (i for i, b in enumerate(self.project.boundaries)
                 if b.btype == BoundaryType.EXTERNAL),
                None,
            )
            if existing_ext_idx is not None:
                reply = QMessageBox.question(
                    self, "Replace External Boundary",
                    "An External Boundary already exists. Replace it with "
                    "the new one?\n\n"
                    "(The old external will be removed; material boundaries "
                    "remain untouched.)",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    self.ogr_status.showMessage(
                        "Drawing discarded (External already exists).", 3000
                    )
                    return
                # Atomic replace via ReplaceBoundaryCommand
                self.command_stack.do(self.project, ReplaceBoundaryCommand(
                        index=existing_ext_idx, new_boundary=boundary
                    ))
                self.ogr_status.showMessage(
                    f"External Boundary replaced with {len(boundary.vertices)} vertices",
                    3000,
                )
                return

        # Default: just add
        self.command_stack.do(self.project, AddBoundaryCommand(boundary=boundary))
        self.ogr_status.showMessage(
            f"Added {boundary.btype.display_name} with {len(boundary.vertices)} vertices",
            3000,
        )

    def _on_boundary_clicked(self, index: int) -> None:
        """Canvas hit-tested a boundary while a pick-based tool is active."""
        mode = self.canvas.tool_mode
        if mode == ToolMode.DELETE_BOUNDARY:
            self._do_delete_boundary(index)
        elif mode == ToolMode.COPY_BOUNDARY:
            self._do_copy_boundary(index)
        elif mode == ToolMode.CONVERT_BOUNDARY:
            self._do_convert_boundary(index)
        elif mode == ToolMode.ASSIGN_MATERIAL:
            self._do_assign_material(index)
        elif mode == ToolMode.SCALE_BOUNDARY:
            self._pending_boundary_idx = index
            self.act_scale_boundary(preselected_idx=index)
        elif mode == ToolMode.ROTATE_BOUNDARY:
            self.act_rotate_boundary(preselected_idx=index)
        elif mode == ToolMode.EXPAND_SHRINK:
            self.act_expand_shrink(preselected_idx=index)
        elif mode == ToolMode.CHANGE_SLOPE_ANGLE:
            self.act_change_slope_angle(preselected_idx=index)
        elif mode == ToolMode.MOVE_BOUNDARY:
            # Move by dx/dy input (simple for now)
            from PySide6.QtWidgets import QInputDialog
            dx, ok = QInputDialog.getDouble(
                self, "Move Boundary", "ΔX (m):", 0.0, -1e6, 1e6, 3
            )
            if not ok:
                return
            dy, ok = QInputDialog.getDouble(
                self, "Move Boundary", "ΔY (m):", 0.0, -1e6, 1e6, 3
            )
            if not ok:
                return
            self._do_move_boundary(index, dx, dy)

    # --- primitive boundary ops --------------------------------------
    def _do_delete_boundary(self, index: int) -> None:
        if 0 <= index < len(self.project.boundaries):
            b = self.project.boundaries[index]
            # v0.1.7: RemoveBoundaryCommand takes the Boundary object
            # itself so undo can re-insert the exact same instance.
            self.command_stack.do(
                self.project, RemoveBoundaryCommand(boundary=b)
            )
            self.ogr_status.showMessage(f"Deleted {b.name}", 2000)

    def _do_copy_boundary(self, index: int) -> None:
        if 0 <= index < len(self.project.boundaries):
            from copy import deepcopy
            from uuid import uuid4
            orig = self.project.boundaries[index]
            new_b = deepcopy(orig)
            new_b.id = str(uuid4())
            # Offset slightly so it's visible
            new_b.polyline.vertices = [
                Vertex(v.x + 2.0, v.y + 2.0) for v in orig.polyline.vertices
            ]
            self.command_stack.do(self.project, AddBoundaryCommand(boundary=new_b))
            self.ogr_status.showMessage(f"Copied {orig.name}", 2000)

    def _do_move_boundary(self, index: int, dx: float, dy: float) -> None:
        if 0 <= index < len(self.project.boundaries):
            from ogr_core.geometry import translate as g_translate
            orig = self.project.boundaries[index]
            new_b = g_translate(orig, dx, dy)
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=index, new_boundary=new_b))
            self.ogr_status.showMessage(
                f"Moved {orig.name} by ({dx:.2f}, {dy:.2f})", 2000
            )

    def _do_convert_boundary(self, index: int) -> None:
        if not (0 <= index < len(self.project.boundaries)):
            return
        orig = self.project.boundaries[index]
        dlg = ConvertBoundaryDialog(orig.btype, self)
        if dlg.exec():
            new_type = dlg.new_type()
            new_b = convert_boundary(orig, new_type)
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=index, new_boundary=new_b))
            self.ogr_status.showMessage(
                f"Converted to {new_type.display_name}", 2000
            )

    def _do_assign_material(self, index: int) -> None:
        """Deprecated fallback — kept for legacy menu entries.

        The modern flow is Properties → Assign Materials (floating panel).
        """
        if not (0 <= index < len(self.project.boundaries)):
            return
        b = self.project.boundaries[index]
        if b.btype != BoundaryType.MATERIAL:
            self.ogr_status.showMessage(
                "Assign Material applies to Material boundaries only. "
                "Use Properties → Assign Materials to paint regions.",
                3000,
            )
            return
        dlg = AssignMaterialDialog(self.project.materials, b.material_id, self)
        if dlg.exec():
            self.command_stack.do(self.project, AssignMaterialCommand(index=index, material_id=dlg.material_id()))
            self.ogr_status.showMessage("Material assigned.", 2000)

    # --- vertex-level ops --------------------------------------------
    def _on_vertex_moved(self, bi: int, vi: int, x: float, y: float) -> None:
        if not (0 <= bi < len(self.project.boundaries)):
            return
        from copy import deepcopy
        orig = self.project.boundaries[bi]
        if not (0 <= vi < len(orig.polyline.vertices)):
            return
        new_b = deepcopy(orig)
        new_b.polyline.vertices[vi] = Vertex(x, y)
        new_b.id = orig.id
        # For live dragging we bypass the command stack on every emit — but we
        # still want undo. Only push the command on mouseRelease; for now we
        # push on every move (which creates many small commands). A future
        # refinement: buffer the start state and push at release.
        self.project.boundaries[bi] = new_b
        self.project._notify("vertex_moved")

    def _on_vertex_inserted(self, bi: int, vi: int, x: float, y: float) -> None:
        if not (0 <= bi < len(self.project.boundaries)):
            return
        from copy import deepcopy
        orig = self.project.boundaries[bi]
        new_b = deepcopy(orig)
        new_b.polyline.vertices.insert(vi + 1, Vertex(x, y))
        new_b.id = orig.id
        self.command_stack.do(self.project, ReplaceBoundaryCommand(index=bi, new_boundary=new_b))
        self.ogr_status.showMessage("Vertex inserted", 1500)




    # ==================================================================
    # v0.1.9 — Right-click context menu handlers
    # ==================================================================
    def _on_boundary_action_requested(self, action: str, bidx: int) -> None:
        """Handle a right-click context-menu action on a boundary."""
        if not (0 <= bidx < len(self.project.boundaries)):
            return
        b = self.project.boundaries[bidx]
        if action == "delete":
            self.command_stack.do(
                self.project, RemoveBoundaryCommand(boundary=b),
            )
            self.ogr_status.showMessage(f"Deleted {b.name}", 3000)
        elif action == "move_boundary":
            self._set_tool(ToolMode.MOVE_BOUNDARY)
            self.ogr_status.showMessage(
                "Click and drag the boundary to move it.", 4000,
            )
        elif action == "edit_coords":
            from .dialogs import EditCoordinatesDialog
            dlg = EditCoordinatesDialog(b, self)
            if dlg.exec():
                new_b = dlg.result_boundary()
                if new_b is not None:
                    new_b.id = b.id
                    self.command_stack.do(
                        self.project,
                        ReplaceBoundaryCommand(index=bidx, new_boundary=new_b),
                    )
        elif action == "convert":
            from .dialogs import ConvertBoundaryDialog
            dlg = ConvertBoundaryDialog(b.btype, self)
            if dlg.exec():
                from copy import deepcopy
                new_b = deepcopy(b)
                new_b.btype = dlg.new_type()
                new_b.id = b.id
                self.command_stack.do(
                    self.project,
                    ReplaceBoundaryCommand(index=bidx, new_boundary=new_b),
                )
        elif action == "define_tension_crack":
            self.act_define_tension_crack()
        elif action == "expand_shrink":
            self.act_expand_shrink(preselected_idx=bidx)
        elif action == "change_slope":
            self.act_change_slope_angle(preselected_idx=bidx)

    def _on_vertex_action_requested(
        self, action: str, bi: int, vi: int,
    ) -> None:
        """Handle a right-click context-menu action on a vertex."""
        if not (0 <= bi < len(self.project.boundaries)):
            return
        b = self.project.boundaries[bi]
        if not (0 <= vi < len(b.polyline.vertices)):
            return
        if action == "move":
            self._set_tool(ToolMode.MOVE_VERTEX)
            self.ogr_status.showMessage(
                "Click and drag a vertex to move it.", 3000,
            )
        elif action == "insert":
            self._set_tool(ToolMode.INSERT_VERTEX)
        elif action == "delete":
            self._on_vertex_deleted(bi, vi)
        elif action == "edit_coords":
            from .dialogs import EditCoordinatesDialog
            dlg = EditCoordinatesDialog(b, self)
            if dlg.exec():
                new_b = dlg.result_boundary()
                if new_b is not None:
                    new_b.id = b.id
                    self.command_stack.do(
                        self.project,
                        ReplaceBoundaryCommand(index=bi, new_boundary=new_b),
                    )

    def _on_canvas_right_click_xy(
        self, x: float, y: float, global_pos,
    ) -> None:
        """Right-click on empty canvas / inside a region — Assign Material menu."""
        material_at = self.project.material_at(x, y)
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        menu = QMenu(self)

        if material_at is None:
            info = QAction(
                f"Region at ({x:.2f}, {y:.2f}) — no material assigned",
                self,
            )
        else:
            info = QAction(
                f"Region — current: {material_at.name}", self,
            )
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        if self.project.materials:
            assign_menu = menu.addMenu("Assign Material")
            for mat in self.project.materials:
                a = QAction(mat.name, self)
                a.triggered.connect(
                    lambda _c=False, mid=mat.id, mx=x, my=y:
                    self._do_assign_material_at(mx, my, mid)
                )
                assign_menu.addAction(a)
        else:
            no_mat = QAction("(no materials defined)", self)
            no_mat.setEnabled(False)
            menu.addAction(no_mat)

        a_def = QAction("Define Materials…", self)
        a_def.triggered.connect(self.act_define_materials)
        menu.addAction(a_def)
        menu.exec(global_pos)

    def _do_assign_material_at(
        self, x: float, y: float, material_id: str,
    ) -> None:
        """Apply a material to the region under (x, y) and refresh."""
        ok = self.project.assign_material_at(x, y, material_id)
        if ok:
            self.project.is_dirty = True
            self.project._notify("region_assignments_changed")
            self.canvas.refresh()
            mat = next(
                (m for m in self.project.materials if m.id == material_id),
                None,
            )
            mat_name = mat.name if mat else "?"
            self.ogr_status.showMessage(
                f"Region at ({x:.2f}, {y:.2f}) → {mat_name}", 3000,
            )
        else:
            self.ogr_status.showMessage(
                f"No region under ({x:.2f}, {y:.2f}).", 3000,
            )

    def _on_boundary_dragged(self, bi: int, dx: float, dy: float) -> None:
        """Move Boundary drag finished — wrap in an undoable command."""
        if not (0 <= bi < len(self.project.boundaries)):
            return
        from copy import deepcopy
        from ogr_core.geometry import translate as g_translate
        orig = self.project.boundaries[bi]
        new_b = g_translate(orig, dx, dy)
        new_b.id = orig.id
        self.command_stack.do(
            self.project,
            ReplaceBoundaryCommand(index=bi, new_boundary=new_b),
        )
        self.ogr_status.showMessage(
            f"Moved {orig.name} by ({dx:+.2f}, {dy:+.2f})", 3000,
        )

    def _on_vertex_deleted(self, bi: int, vi: int) -> None:
        if not (0 <= bi < len(self.project.boundaries)):
            return
        from copy import deepcopy
        orig = self.project.boundaries[bi]
        if len(orig.polyline.vertices) <= 2:
            QMessageBox.information(
                self, "Delete Vertex",
                "Cannot delete — boundary must keep at least 2 vertices.",
            )
            return
        new_b = deepcopy(orig)
        del new_b.polyline.vertices[vi]
        new_b.id = orig.id
        self.command_stack.do(self.project, ReplaceBoundaryCommand(index=bi, new_boundary=new_b))
        self.ogr_status.showMessage("Vertex deleted", 1500)

    def _on_vertex_drag_finished(self, bi: int, snapshot_before) -> None:
        """Called when user releases the mouse after dragging a vertex.

        The live drag has already mutated the project in place (via
        ``_on_vertex_moved``). We now rewind that mutation with the
        snapshot and re-apply it as a proper ReplaceBoundaryCommand so
        the whole drag is undoable as a single action.
        """
        if not (0 <= bi < len(self.project.boundaries)):
            return
        final_boundary = self.project.boundaries[bi]
        # Restore pre-drag state silently, then push one command
        self.project.boundaries[bi] = snapshot_before
        self.command_stack.do(self.project, ReplaceBoundaryCommand(index=bi, new_boundary=final_boundary))
        self.ogr_status.showMessage("Vertex moved", 1500)

    # --- dialog-launched transformations ------------------------------
    def act_scale_boundary(self, preselected_idx: Optional[int] = None) -> None:
        idx = preselected_idx if preselected_idx is not None else self._ask_boundary_index()
        if idx is None:
            return
        dlg = ScaleDialog(self)
        if dlg.exec():
            sx, sy, pivot = dlg.parameters()
            orig = self.project.boundaries[idx]
            new_b = g_scale(orig, pivot, sx, sy)
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=idx, new_boundary=new_b))
            self.ogr_status.showMessage(
                f"Scaled {orig.name} by ({sx:.3f}, {sy:.3f})", 2000
            )

    def act_rotate_boundary(self, preselected_idx: Optional[int] = None) -> None:
        idx = preselected_idx if preselected_idx is not None else self._ask_boundary_index()
        if idx is None:
            return
        dlg = RotateDialog(self)
        if dlg.exec():
            angle, pivot = dlg.parameters()
            orig = self.project.boundaries[idx]
            new_b = g_rotate(orig, pivot, angle)
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=idx, new_boundary=new_b))
            self.ogr_status.showMessage(
                f"Rotated {orig.name} by {angle:.2f}°", 2000
            )

    def act_expand_shrink(self, preselected_idx: Optional[int] = None) -> None:
        """Expand or shrink the External Boundary — Slide-style.

        Workflow (matches Slide UX):
          1. User picks the mode: Numeric offset OR Draw polyline.
          2. For draw mode:
               - FIRST click must snap onto the External (green cross)
               - intermediate points go OUTSIDE (expand) or INSIDE (shrink)
               - LAST click must snap onto the External
               - Right-click → Done, or press Enter, to finish
          3. On finish, a dialog asks "convert the removed part of the
             old External into a Material Boundary?" — Yes / No
          4. Everything is wrapped in an undoable MacroCommand.
        """
        # Must have an External
        if preselected_idx is None:
            for i, b in enumerate(self.project.boundaries):
                if b.btype == BoundaryType.EXTERNAL:
                    preselected_idx = i
                    break
        if preselected_idx is None:
            QMessageBox.information(
                self, "Expand / Shrink",
                "No External Boundary in the project."
            )
            return

        from PySide6.QtWidgets import QInputDialog
        options = [
            "Draw polyline (Slide-style — recommended)",
            "Numeric offset (all edges by a fixed distance)",
        ]
        choice, ok = QInputDialog.getItem(
            self, "Expand / Shrink External",
            "Choose the method to modify the External Boundary:",
            options, 0, False,
        )
        if not ok:
            return
        if choice == options[1]:
            self._expand_shrink_numeric(preselected_idx)
        else:
            self._expand_shrink_slide_style(preselected_idx)

    # ------------------------------------------------------------------
    def _expand_shrink_numeric(self, idx: int) -> None:
        """Legacy numeric offset (parallel to all edges)."""
        dlg = ExpandShrinkDialog(self)
        if not dlg.exec():
            return
        d = dlg.distance()
        orig = self.project.boundaries[idx]
        try:
            new_poly = offset_polygon(orig.polyline, d)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Expand / Shrink", f"Failed: {e}")
            return
        from copy import deepcopy
        new_b = deepcopy(orig)
        new_b.polyline = new_poly
        new_b.id = orig.id
        self.command_stack.do(
            self.project,
            ReplaceBoundaryCommand(index=idx, new_boundary=new_b),
        )
        self.ogr_status.showMessage(f"External offset by {d:+.2f} m", 2000)

    # ------------------------------------------------------------------
    def _expand_shrink_slide_style(self, idx: int) -> None:
        """Enter the interactive Slide-style draw mode."""
        self._expand_shrink_target_idx = idx
        try:
            self.canvas.boundary_drawn.disconnect(self._on_boundary_drawn)
        except (TypeError, RuntimeError):
            pass
        self.canvas.boundary_drawn.connect(self._on_expand_shrink_polyline_drawn)
        self.canvas.set_tool_mode(ToolMode.DRAW_EXPAND_SHRINK)
        self.ogr_status.showMessage(
            "Expand/Shrink: FIRST click must be ON the External (snap — "
            "green cross). Intermediate points go OUTSIDE (expand) or "
            "INSIDE (shrink). LAST click must also be ON the External. "
            "Right-click → Done when finished.",
            10000,
        )

    # ------------------------------------------------------------------
    def _on_expand_shrink_polyline_drawn(self, polyline_boundary) -> None:
        """Called when the user finishes drawing the Expand/Shrink polyline."""
        # Restore the normal boundary_drawn routing
        try:
            self.canvas.boundary_drawn.disconnect(
                self._on_expand_shrink_polyline_drawn
            )
        except (TypeError, RuntimeError):
            pass
        self.canvas.boundary_drawn.connect(self._on_boundary_drawn)

        idx = getattr(self, "_expand_shrink_target_idx", None)
        if idx is None or not (0 <= idx < len(self.project.boundaries)):
            return
        old_ext = self.project.boundaries[idx]

        # Run the pure-geometry algorithm
        try:
            from ogr_core.geometry import (
                ExpandShrinkError,
                expand_shrink_external,
            )
            result = expand_shrink_external(
                old_ext.polyline, polyline_boundary.polyline,
            )
        except ExpandShrinkError as e:
            QMessageBox.warning(self, "Expand / Shrink", str(e))
            return
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Expand / Shrink",
                f"Unexpected failure: {e}",
            )
            return

        # Ask the user whether to preserve the removed arc as a Material Boundary
        convert_arc = False
        if result.removed_arc is not None and len(result.removed_arc.vertices) >= 2:
            reply = QMessageBox.question(
                self, "Expand / Shrink External",
                f"External Boundary successfully <b>{result.mode}ed</b>."
                "<br><br>Do you want to convert the deleted segments of the "
                "original External Boundary into a Material Boundary?"
                "<br><br>(This is useful if you want to keep the original "
                "ground surface as a geological reference — e.g. for a fill "
                "or an excavation.)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            convert_arc = (reply == QMessageBox.Yes)

        # Build the replacement External boundary
        from copy import deepcopy
        new_ext = deepcopy(old_ext)
        new_ext.polyline = result.new_external
        new_ext.id = old_ext.id

        commands = [
            ReplaceBoundaryCommand(index=idx, new_boundary=new_ext),
        ]

        if convert_arc:
            from ogr_core.geometry import Boundary as _B
            from uuid import uuid4
            arc_as_material = _B(
                polyline=result.removed_arc,
                btype=BoundaryType.MATERIAL,
                name="Original ground (from Expand/Shrink)",
            )
            arc_as_material.color = BoundaryType.MATERIAL.default_color
            arc_as_material.id = str(uuid4())
            commands.append(AddBoundaryCommand(boundary=arc_as_material))

        from ogr_core.project.commands import MacroCommand
        self.command_stack.do(
            self.project,
            MacroCommand(
                commands=commands,
                description=f"Expand/Shrink ({result.mode})",
            ),
        )
        msg = f"External {result.mode}ed."
        if convert_arc:
            msg += " Old segment preserved as Material Boundary."
        self.ogr_status.showMessage(msg, 5000)

    def act_change_slope_angle(self, preselected_idx: Optional[int] = None) -> None:
        if preselected_idx is None:
            for i, b in enumerate(self.project.boundaries):
                if b.btype == BoundaryType.EXTERNAL:
                    preselected_idx = i
                    break
        if preselected_idx is None:
            QMessageBox.information(self, "Change Slope Angle",
                                    "No external boundary in the project.")
            return
        dlg = ChangeSlopeAngleDialog(self)
        if dlg.exec():
            target, pivot = dlg.parameters()
            orig = self.project.boundaries[preselected_idx]
            new_b = change_slope_angle(orig, pivot, target)
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=preselected_idx, new_boundary=new_b))
            self.ogr_status.showMessage(f"Slope set to {target:.2f}°", 2000)

    def act_simplify_boundary(self) -> None:
        idx = self._ask_boundary_index()
        if idx is None:
            return
        dlg = SimplifyBoundaryDialog(self)
        if dlg.exec():
            tol = dlg.tolerance()
            orig = self.project.boundaries[idx]
            pts = [(v.x, v.y) for v in orig.polyline.vertices]
            simplified = simplify_rdp(pts, tol)
            from copy import deepcopy
            new_b = deepcopy(orig)
            new_b.polyline.vertices = [Vertex(x, y) for (x, y) in simplified]
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=idx, new_boundary=new_b))
            self.ogr_status.showMessage(
                f"Simplified from {len(orig.vertices)} to {len(simplified)} vertices", 3000
            )

    def act_geometry_cleanup(self) -> None:
        report_lines = ["Geometry Cleanup Report", "=" * 40, ""]
        report_lines.append(f"Total boundaries: {len(self.project.boundaries)}")
        for i, b in enumerate(self.project.boundaries):
            n = len(b.polyline.vertices)
            has_self = False
            try:
                has_self = has_self_intersections(b.polyline)
            except Exception:  # noqa: BLE001
                pass
            closed_ok = True
            if b.btype == BoundaryType.EXTERNAL and not b.polyline.closed:
                closed_ok = False
            flags = []
            if has_self:
                flags.append("SELF-INTERSECTS")
            if not closed_ok:
                flags.append("NOT CLOSED (external)")
            status = ", ".join(flags) if flags else "OK"
            report_lines.append(f"  [{i}] {b.btype.name} '{b.name}': {n} vertices — {status}")

        # Inter-boundary intersections
        try:
            inter = find_intersections(self.project.boundaries)
            if inter:
                report_lines.append("")
                report_lines.append(f"Inter-boundary intersections: {len(inter)}")
        except Exception:  # noqa: BLE001
            pass

        report_lines.append("")
        report_lines.append("Running cleanup_boundaries()…")
        cleaned = cleanup_boundaries(list(self.project.boundaries))
        report_lines.append(f"  After cleanup: {len(cleaned)} boundaries")

        dlg = GeometryCleanupDialog("\n".join(report_lines), self)
        dlg.exec()

    def act_edit_coordinates(self) -> None:
        idx = self._ask_boundary_index()
        if idx is None:
            return
        orig = self.project.boundaries[idx]
        dlg = EditCoordinatesDialog(orig, self)
        if dlg.exec():
            new_b = dlg.result_boundary()
            if new_b is None:
                return
            new_b.id = orig.id
            self.command_stack.do(self.project, ReplaceBoundaryCommand(index=idx, new_boundary=new_b))
            self.ogr_status.showMessage("Coordinates updated", 2000)

    def act_selection_filter(self) -> None:
        dlg = SelectionFilterDialog(self.selection_filter, self)
        if dlg.exec():
            self.selection_filter = dlg.state()
            self.canvas.selection_filter = self.selection_filter
            # Give feedback on what's now selectable
            active = [n for n in ("boundaries", "vertices", "materials",
                                   "supports", "loads", "surfaces")
                       if getattr(self.selection_filter, n)]
            self.ogr_status.showMessage(
                f"Selection filter: {', '.join(active) or 'nothing selectable'}",
                3000,
            )

    # --- helper: pick boundary from a list ---------------------------
    def _ask_boundary_index(self) -> Optional[int]:
        if not self.project.boundaries:
            QMessageBox.information(self, "Select Boundary", "No boundaries defined.")
            return None
        from PySide6.QtWidgets import QInputDialog
        labels = [
            f"[{i}] {b.btype.display_name} '{b.name}' ({len(b.vertices)} verts)"
            for i, b in enumerate(self.project.boundaries)
        ]
        choice, ok = QInputDialog.getItem(
            self, "Select Boundary", "Boundary:", labels, 0, False
        )
        if not ok:
            return None
        return labels.index(choice)

    # ==================================================================
    # Demo project
    def act_load_demo(self) -> None:
        """Replace current project with the demo slope."""
        if self.project.is_dirty:
            r = QMessageBox.question(
                self, tr("Load Demo Slope"),
                "Current project has unsaved changes. Load demo anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if r != QMessageBox.Yes:
                return
        self._attach_project(Project("Demo slope"))
        self.terminal_dock.attach_context(self.project, self.canvas, self)
        self.command_stack.clear()
        self.last_search_result = None
        self.last_search_results: dict = {}
        self.results_dock.show_result(None)
        self._install_demo_project()
        self.setWindowTitle(f"OGR Slip2D v{self.VERSION} — Demo slope")
        self.ogr_status.showMessage("Demo slope loaded.", 3000)

    # ==================================================================
    def _install_demo_project(self) -> None:
        ext = Polyline(
            vertices=[
                Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
            ],
            closed=True,
        )
        ext.ensure_ccw()
        self.project.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        self.project.add_material(Material(
            name="Silty clay",
            strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
            unit_weight=19.0, sat_unit_weight=20.5,
        ))
        wt = Boundary(
            polyline=Polyline(vertices=[Vertex(0, 8), Vertex(50, 8)]),
            btype=BoundaryType.WATER_TABLE,
        )
        self.project.add_boundary(wt)
        self.project.is_dirty = False
        self.canvas.zoom_all()
