# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
InterpretWindow — separate post-processing window.

Mirrors the specification for the Interpret module: a stand-alone
QMainWindow with its own menus (File, Edit, Data, Query, Groundwater,
Statistics, Tools, Window, Help), a read-only canvas showing the
computed results, a results dock, and a data-tips engine that
interrogates slices on mouse hover.

Activated via Analysis → Interpret (Ctrl+I) in the main window.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ogr_core.project import Project

from .canvas import CanvasView
from .i18n import tr
from .resources import icon


# ======================================================================
class _SliceDataDock(QDockWidget):
    """Dock panel: property-table for the currently highlighted slice.

    v0.1.12 — extended to show the full Slide-style slice property set.
    """

    @staticmethod
    def _get(s, name, default="—"):
        return getattr(s, name, default)

    @staticmethod
    def _round_or_dash(s, name, ndigits=3):
        v = getattr(s, name, None)
        if v is None:
            return "—"
        try:
            return round(float(v), ndigits)
        except Exception:  # noqa: BLE001
            return v

    FIELDS = [
        # --- Geometry --------------------------------------------------
        ("─ Geometry ─", lambda s: ""),
        ("Slice Number",     lambda s: s.index),
        ("X centre (m)",     lambda s: round(s.x_centre, 3)),
        ("Width b (m)",      lambda s: round(s.width, 3)),
        ("Base length l (m)", lambda s: round(s.base_length, 3)),
        ("Base angle α (°)", lambda s: round(s.to_dict()["base_angle_deg"], 2)),
        ("Height h (m)",     lambda s: round(s.height, 3)),
        ("Base y left (m)",  lambda s: round(s.base_y_left, 3)),
        ("Base y right (m)", lambda s: round(s.base_y_right, 3)),
        # --- Forces ----------------------------------------------------
        ("─ Forces ─", lambda s: ""),
        ("Weight W (kN)",    lambda s: round(s.weight, 2)),
        ("Pore pressure u (kPa)",   lambda s: round(s.pore_pressure, 2)),
        ("Surface load q (kPa)",    lambda s: round(s.surface_pressure, 2)),
        ("Base normal force N (kN)",
         lambda s: _SliceDataDock._round_or_dash(s, "base_normal_force", 2)),
        ("Base shear force T (kN)",
         lambda s: _SliceDataDock._round_or_dash(s, "base_shear_force", 2)),
        # --- Stresses --------------------------------------------------
        ("─ Stresses ─", lambda s: ""),
        ("Effective normal σ′ₙ (kPa)",
         lambda s: _SliceDataDock._round_or_dash(s, "sigma_n_eff", 2)),
        ("Shear strength τ_f (kPa)",
         lambda s: _SliceDataDock._round_or_dash(s, "tau_strength", 2)),
        ("Mobilised shear τ_m (kPa)",
         lambda s: _SliceDataDock._round_or_dash(s, "tau_mobilized", 2)),
        # --- Material --------------------------------------------------
        ("─ Material ─", lambda s: ""),
        ("Material",
         lambda s: s.material.name if s.material else "—"),
        ("Strength model",
         lambda s: (s.material.strength.DISPLAY_NAME
                    if s.material else "—")),
        ("Unit weight γ (kN/m³)",
         lambda s: (round(s.material.unit_weight, 2)
                    if s.material else "—")),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__("Slice Data", parent)
        self.setObjectName("SliceDataDock")
        container = QWidget()
        vbox = QVBoxLayout(container)
        self.table = QTableWidget(len(self.FIELDS), 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        for i, (label, _) in enumerate(self.FIELDS):
            item_label = QTableWidgetItem(label)
            # Section headers (start with ─) drawn slightly bolder
            if label.startswith("─"):
                from PySide6.QtGui import QFont
                f = QFont(); f.setBold(True)
                item_label.setFont(f)
            self.table.setItem(i, 0, item_label)
            self.table.setItem(i, 1, QTableWidgetItem("—"))
        vbox.addWidget(self.table)
        self.setWidget(container)

    def show_slice(self, s) -> None:
        for i, (_, getter) in enumerate(self.FIELDS):
            try:
                value = getter(s)
            except Exception:  # noqa: BLE001
                value = "—"
            self.table.item(i, 1).setText(str(value))


# ======================================================================
class _SummaryDock(QDockWidget):
    """Header summary: method, number of valid surfaces, critical FoS."""

    def __init__(self, parent=None) -> None:
        super().__init__("Summary", parent)
        self.setObjectName("SummaryDock")
        container = QWidget()
        vbox = QVBoxLayout(container)
        self.label = QLabel(tr("<i>No results to display.</i>"))
        self.label.setWordWrap(True)
        self.label.setStyleSheet("padding: 8px; font-size: 10.5pt;")
        vbox.addWidget(self.label)
        vbox.addStretch(1)
        self.setWidget(container)

    def show_result(self, result) -> None:
        if result is None or not result.evaluations:
            self.label.setText(tr("<i>No results to display.</i>"))
            return
        c = result.critical
        if c is None:
            self.label.setText(
                f"Method: <b>{result.method_id}</b><br>"
                f"<i>No valid surfaces ({result.invalid_count} invalid)</i>"
            )
            return
        sd = c.surface.to_dict()
        # v0.1.8 — FoS legend (matches CanvasView._fos_to_color)
        legend = (
            "<br><br><b>FoS heatmap legend</b><br>"
            "<table style='font-size:9pt;'>"
            "<tr><td bgcolor='#dc1e1e' width='30'>&nbsp;</td><td>FoS ≤ 1.00</td></tr>"
            "<tr><td bgcolor='#f06428'>&nbsp;</td><td>1.00 – 1.25</td></tr>"
            "<tr><td bgcolor='#f5a03c'>&nbsp;</td><td>1.25 – 1.50</td></tr>"
            "<tr><td bgcolor='#f5d750'>&nbsp;</td><td>1.50 – 1.75</td></tr>"
            "<tr><td bgcolor='#c8dc64'>&nbsp;</td><td>1.75 – 2.00</td></tr>"
            "<tr><td bgcolor='#8cc864'>&nbsp;</td><td>2.00 – 2.50</td></tr>"
            "<tr><td bgcolor='#64a064'>&nbsp;</td><td>2.50 – 3.00</td></tr>"
            "<tr><td bgcolor='#6e6e78'>&nbsp;</td><td>FoS &gt; 3.00</td></tr>"
            "</table>"
        )
        self.label.setText(
            f"Method: <b>{result.method_id}</b><br>"
            f"Valid surfaces: <b>{result.valid_count}</b> / {len(result.evaluations)}<br>"
            f"<br>"
            f"<b>Critical surface</b><br>"
            f"FoS = <span style='color:#c0392b; font-size:14pt;'>"
            f"<b>{c.fos:.3f}</b></span><br>"
            f"Iterations: {c.iterations}<br>"
            f"Centre: ({sd.get('centre_x', 0):.2f}, {sd.get('centre_y', 0):.2f})<br>"
            f"Radius: {sd.get('radius', 0):.2f} m"
            + legend
        )


# ======================================================================
class _ResultsTableDock(QDockWidget):
    """Top-N surfaces table, sortable by FoS."""

    surface_picked = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__("Surfaces", parent)
        self.setObjectName("ResultsTableDock")
        container = QWidget()
        vbox = QVBoxLayout(container)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["#", "FoS", "Method", "Centre X", "Centre Y", "Radius"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_sel)
        vbox.addWidget(self.table)
        self.setWidget(container)

    def show_result(self, result) -> None:
        self.table.setRowCount(0)
        if result is None:
            return
        for i, res in enumerate(result.top_n(100)):
            sd = res.surface.to_dict()
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(f"{res.fos:.4f}"))
            self.table.setItem(i, 2, QTableWidgetItem(res.method_id))
            self.table.setItem(i, 3, QTableWidgetItem(f"{sd.get('centre_x', 0):.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{sd.get('centre_y', 0):.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{sd.get('radius', 0):.2f}"))

    def _on_sel(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.surface_picked.emit(rows[0].row())


# ======================================================================
class InterpretWindow(QMainWindow):
    """Stand-alone post-processing window."""

    closed = Signal()

    def __init__(self, project: Project, search_result, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"OGR Slip2D — Interpret — {project.name}")
        self.resize(1200, 800)
        self.project = project

        # v0.1.9: accept either {method_id: SearchResult} or a single
        # SearchResult (back-compat). Normalize to dict.
        if isinstance(search_result, dict):
            self.results_by_method: dict = dict(search_result)
        else:
            self.results_by_method = {"single": search_result}

        if not self.results_by_method:
            self.search_result = None
        else:
            first_id = next(iter(self.results_by_method))
            self.search_result = self.results_by_method[first_id]
            self._current_method_id = first_id

        # Central read-only canvas
        self.canvas = CanvasView(project, self)
        self.setCentralWidget(self.canvas)
        # v0.1.20 — surface display mode (Data menu): the default is the
        # global minimum surface, matching the checked menu radio.
        self._surface_mode = "global_min"
        self.canvas.display_search_result(
            self.search_result, surface_mode=self._surface_mode)

        # Docks
        self.summary_dock = _SummaryDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.summary_dock)
        self.summary_dock.show_result(self.search_result)

        self.results_dock = _ResultsTableDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.results_dock)
        self.results_dock.show_result(self.search_result)
        self.results_dock.surface_picked.connect(self._on_surface_picked)

        self.slice_dock = _SliceDataDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.slice_dock)

        # Menus + toolbar
        self._build_menus()
        self._build_toolbar()
        self._build_method_selector()

        # v0.1.12 — interactive hover/selection state
        self._selected_surface_id = None
        self._selected_result = None
        self._slices_visible = False
        self._query_slice_target = None
        self._hover_grid_idx = None  # index of last hovered (cx, cy) cell
        self._hover_throttle_ms = 50
        # Connect canvas hover signal for grid-cell preview
        try:
            self.canvas.scene_hovered.connect(self._on_canvas_hover)
        except AttributeError:
            pass
        # Default click handler: pick the surface at the clicked grid cell
        try:
            self.canvas.scene_clicked.connect(self._on_canvas_click_default)
        except AttributeError:
            pass

        self.statusBar().showMessage("Post-processing — read-only view. "
                                     "Close this window to return to the model.", 5000)

        # v0.1.49 (phase I1) — the pieces the post-processor
        # specification calls for and this window lacked: a graphical
        # colour scale, the clickable status indicators, an active
        # algorithm read-out and the factor of safety anchored to the
        # critical surface.
        # v0.1.50 (phase I2) — contour settings drive both the canvas
        # colours and the legend, so the two are one source of truth.
        from ogr_gui.contours import ContourSettings
        self.contours = ContourSettings()
        self._build_legend_dock()
        self._build_status_indicators()
        self._refresh_legend()
        self._refresh_algorithm_label()

    # ==================================================================
    # Result context (phase I1)
    # ==================================================================
    def _build_legend_dock(self) -> None:
        """The vertical colour bar, replacing a hand-written HTML table.

        The old legend hard-coded its bands, so it said the same thing
        whatever the results contained. This one is generated from the
        SAME colour function the canvas uses, so the two can never
        disagree.
        """
        from PySide6.QtWidgets import QDockWidget

        from ogr_gui.widgets.legend import ColourScaleLegend

        self.legend = ColourScaleLegend(self)
        dock = QDockWidget(tr("Legend"), self)
        dock.setWidget(self.legend)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.legend_dock = dock

    def current_field_values(self) -> list:
        """The scalar values behind the active contour field."""
        from ogr_gui.contours import ContourMode  # noqa: F401
        field = self.contours.field
        if field == "fos":
            res = self.search_result
            return [e.fos for e in getattr(res, "evaluations", [])
                    if e.is_valid] if res else []
        seepage = getattr(self.project, "seepage_result", None)
        if seepage is None:
            return []
        return list(getattr(seepage, field, []) or [])

    def _refresh_legend(self) -> None:
        """Point the legend at the active field, through the contour
        settings.

        Legend and canvas both ask the SAME ``ContourSettings`` for the
        colour of a value, so a change of palette, range or interval
        count is reflected in both without any further plumbing.
        """
        legend = getattr(self, "legend", None)
        if legend is None:
            return
        values = self.current_field_values()
        if not values:
            return
        if self.contours.auto_range:
            self.contours.fit_to(values)
        res = self.search_result
        crit = (res.critical.fos
                if (self.contours.field == "fos" and res
                    and res.critical) else None)
        from ogr_gui.contours import SCALAR_FIELDS
        legend.configure(
            self.contours.vmin, self.contours.vmax,
            self.contours.colour_for,
            title=tr(SCALAR_FIELDS.get(self.contours.field,
                                       self.contours.field)),
            steps=self.contours.intervals,
            decimals=self.contours.decimals,
            scientific=self.contours.scientific, mark=crit)
        # And the canvas uses the same mapping
        if hasattr(self.canvas, "set_contour_colour_fn"):
            from ogr_gui.contours import ContourMode as _CM
            self.canvas.set_contour_colour_fn(
                None if self.contours.mode == _CM.OFF
                else self.contours.colour_for)

    def _contour_options(self) -> None:
        """Configure the contour plot."""
        from ogr_gui.contours import available_fields
        from ogr_gui.dialogs.contour_options_dialog import (
            ContourOptionsDialog,
        )
        fields = available_fields(self.project, self.search_result) \
            or ["fos"]
        dlg = ContourOptionsDialog(self.contours, fields,
                                   self.current_field_values(), self)
        if not dlg.exec():
            return
        self.contours = dlg.settings
        self._refresh_legend()
        if hasattr(self.canvas, "refresh_scene"):
            self.canvas.refresh_scene()
        self.canvas.display_search_result(
            self.search_result, selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode)

    def _build_status_indicators(self) -> None:
        """Coordinates plus the clickable SNAP / GRID / ORTHO / OSNAP and
        DATA TIPS words the specification requires in the status bar."""
        from ogr_gui.widgets.legend import StatusIndicators

        self.indicators = StatusIndicators(
            self.statusBar(),
            initial={"DATA TIPS": True, "GRID": False, "SNAP": False,
                     "ORTHO": False, "OSNAP": False})
        try:
            self.canvas.scene_hovered.connect(
                lambda x, y: self.indicators.set_coordinates(x, y))
        except Exception:  # noqa: BLE001
            pass
        self.indicators.connect("GRID", self._on_grid_toggled)
        self.indicators.connect("DATA TIPS", self._on_datatips_toggled)

    def _on_grid_toggled(self, on: bool) -> None:
        if hasattr(self.canvas, "set_grid_visible"):
            self.canvas.set_grid_visible(bool(on))

    def _on_datatips_toggled(self, on: bool) -> None:
        self._data_tips_enabled = bool(on)

    def critical_label_text(self) -> str:
        """Text of the factor-of-safety label anchored to the critical
        surface, as the specification describes."""
        res = self.search_result
        if res is None or res.critical is None:
            return ""
        return f"{res.critical.fos:.3f}"

    def active_algorithm(self) -> str:
        """Which numerical method produced what is on screen."""
        res = self.search_result
        return getattr(res, "method_id", "") if res else ""

    # ==================================================================
    # Menus
    # ==================================================================
    def _build_menus(self) -> None:
        mb = self.menuBar()

        # -- File ------------------------------------------------------
        m_file = mb.addMenu(tr("File"))
        m_file.addAction(QAction(tr("Export Image..."), self, triggered=self._export_image))
        m_file.addAction(QAction(tr("Export Data (CSV)..."), self, triggered=self._export_data_csv))
        m_file.addSeparator()
        act_close = QAction(tr("Close"), self, shortcut=QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self.close)
        m_file.addAction(act_close)

        # -- Edit ------------------------------------------------------
        m_edit = mb.addMenu(tr("Edit"))
        m_edit.addAction(QAction(tr("Copy Image"), self,
                                 triggered=self._copy_image))

        # -- Data ------------------------------------------------------
        # -- View ------------------------------------------------------
        m_view = mb.addMenu(tr("View"))
        m_zoom = m_view.addMenu(tr("Zoom"))
        m_zoom.addAction(QAction(tr("Zoom All"), self,
                                 triggered=self.canvas.zoom_all))
        m_zoom.addAction(QAction(tr("Zoom In"), self,
                                 triggered=lambda: self.canvas.zoom_by(1.25)))
        m_zoom.addAction(QAction(tr("Zoom Out"), self,
                                 triggered=lambda: self.canvas.zoom_by(1 / 1.25)))
        m_view.addSeparator()
        act_leg = QAction(tr("Show Legend"), self, checkable=True)
        act_leg.setChecked(True)
        act_leg.toggled.connect(
            lambda on: self.legend_dock.setVisible(bool(on)))
        m_view.addAction(act_leg)
        m_view.addAction(QAction(tr("Contour Options..."), self,
                                 triggered=self._contour_options))
        m_view.addAction(QAction(tr("Legend Options..."), self,
                                 triggered=self._legend_options))
        m_view.addSeparator()
        m_tips = m_view.addMenu(tr("Data Tips"))
        for label, mode in ((tr("None"), "none"), (tr("Maximum"), "max"),
                            (tr("Minimum"), "min")):
            act = QAction(label, self, checkable=True)
            act.setChecked(mode == "max")
            act.triggered.connect(
                lambda _c=False, m=mode: setattr(self, "_data_tips_mode", m))
            m_tips.addAction(act)

        m_data = mb.addMenu("Data")
        from PySide6.QtGui import QActionGroup
        self._surface_mode_group = QActionGroup(self)
        self._surface_mode_group.setExclusive(True)
        act_gm = QAction("Global Minimum", self, checkable=True, checked=True)
        act_min = QAction("Minimum Surfaces", self, checkable=True)
        act_all = QAction("All Surfaces", self, checkable=True)
        act_gm.triggered.connect(lambda: self._set_surface_mode("global_min"))
        act_min.triggered.connect(lambda: self._set_surface_mode("minimum"))
        act_all.triggered.connect(lambda: self._set_surface_mode("all"))
        for a in (act_gm, act_min, act_all):
            self._surface_mode_group.addAction(a)
            m_data.addAction(a)
        m_data.addSeparator()
        m_data.addAction(QAction("Filter Surfaces...", self,
                                  triggered=self._filter_surfaces))
        m_data.addAction(QAction("Graph SF Along Slope...", self,
                                  triggered=self._graph_sf_along_slope))
        m_data.addAction(QAction("Export Raw Data...", self,
                                  triggered=self._export_data_csv))
        # v0.1.53 (phase I3) — the remaining Data entries. Those that
        # depend on something the project may not have (a transient run,
        # supports) are DISABLED rather than hidden, so the user can see
        # the capability exists and what it needs.
        m_data.addSeparator()
        self._act_sf_time = QAction("Graph SF with Time...", self,
                                    triggered=self._graph_sf_with_time)
        self._act_sf_time.setEnabled(bool(
            getattr(self.project, "transient_results", None)))
        self._act_sf_time.setToolTip(tr(
            "Requires a transient groundwater analysis with per-stage "
            "factors of safety."))
        m_data.addAction(self._act_sf_time)

        self._act_support_force = QAction(
            "Support Force Analysis...", self,
            triggered=self._support_force_analysis)
        self._act_support_force.setEnabled(
            bool(getattr(self.project, "supports", [])))
        self._act_support_force.setToolTip(tr(
            "Requires at least one support in the model."))
        m_data.addAction(self._act_support_force)

        m_data.addAction(QAction("Back Analysis...", self,
                                  triggered=self._back_analysis_report))
        self._act_supp_contours = QAction("Supplemental Contours", self,
                                          checkable=True)
        self._act_supp_contours.setToolTip(tr(
            "Overlay iso-lines of the contoured field on top of the "
            "filled bands."))
        self._act_supp_contours.toggled.connect(
            self._toggle_supplemental_contours)
        m_data.addAction(self._act_supp_contours)

        # -- Query -----------------------------------------------------
        m_query = mb.addMenu("Query")
        m_query.addAction(QAction("Show Slices", self, checkable=True,
                                   triggered=self._toggle_slices))
        m_query.addAction(QAction("Query Slice Data...", self,
                                   triggered=self._query_slice))
        m_query.addSeparator()
        m_query.addAction(QAction("Show Values Along Surface...", self,
                                   triggered=self._show_values_along))
        # v0.1.15 — additional Slide-style queries
        m_query.addAction(QAction("Free Body Diagram of Slice...", self,
                                   triggered=self._free_body_diagram))
        # v0.1.22 — line of thrust overlay (interslice resultants)
        self._act_thrust = QAction("Line of Thrust", self, checkable=True)
        self._act_thrust.toggled.connect(self._toggle_thrust_line)
        m_query.addAction(self._act_thrust)
        m_query.addAction(QAction("Surfaces Crossing Point...", self,
                                   triggered=self._surfaces_through_point))
        m_query.addAction(QAction("Add Result Table (sortable)...", self,
                                   triggered=self._add_result_table))
        # v0.1.53 — query points: a persistent list the user builds up,
        # so several locations can be compared instead of inspected one
        # at a time and forgotten.
        m_query.addSeparator()
        m_query.addAction(QAction("Add Query...", self,
                                   triggered=self._add_query))
        m_query.addAction(QAction("Graph Query...", self,
                                   triggered=self._graph_query))
        m_query.addAction(QAction("Delete Query...", self,
                                   triggered=self._delete_query))
        m_query.addSeparator()
        m_query.addAction(QAction("Query Invalid Surfaces...", self,
                                   triggered=self._query_invalid))
        self._act_query_text = QAction("Text during Query", self,
                                       checkable=True, checked=True)
        m_query.addAction(self._act_query_text)

        # -- Groundwater ----------------------------------------------
        m_gw = mb.addMenu("Groundwater")
        m_gw.addAction(QAction("Phreatic Surface", self, checkable=True, checked=True))
        m_gw.addAction(QAction("Piezometric Lines", self, checkable=True))
        m_gw.addAction(QAction("Flow Vectors", self, checkable=True))
        m_gw.addAction(QAction("Streamlines", self, checkable=True))
        m_gw.addSeparator()
        m_gw.addAction(QAction("Export All Nodal Values...", self,
                                triggered=self._export_nodal_values))
        # v0.1.53 — the groundwater field has its own contour and legend
        # options, separate from the stability ones: it is a different
        # scalar with a different range.
        m_gw.addSeparator()
        m_gw.addAction(QAction("Contour Options...", self,
                                triggered=self._gw_contour_options))
        m_gw.addAction(QAction("Legend Options...", self,
                                triggered=self._legend_options))
        m_gw.addSeparator()
        m_gw.addAction(QAction("Query...", self,
                                triggered=self._gw_query))
        m_gw.addAction(QAction("Define User Data...", self,
                                triggered=self._gw_user_data))
        m_gw.addSeparator()
        self._act_gw_iter = QAction("Iteration History...", self,
                                    triggered=self._gw_iteration_history)
        self._act_gw_conv = QAction("Convergence Plot...", self,
                                    triggered=self._gw_convergence)
        for act in (self._act_gw_iter, self._act_gw_conv):
            act.setEnabled(
                getattr(self.project, "seepage_result", None) is not None)
            act.setToolTip(tr("Requires a computed groundwater analysis."))
            m_gw.addAction(act)

        # -- Statistics -----------------------------------------------
        m_stat = mb.addMenu("Statistics")
        m_stat.addAction(QAction("Histogram Plot...", self,
                                  triggered=self._histogram))
        m_stat.addAction(QAction("Cumulative Plot...", self,
                                  triggered=self._cumulative))
        m_stat.addAction(QAction("Scatter Plot...", self,
                                  triggered=self._scatter))
        # v0.1.53 — the rest of the statistics module. Every one of these
        # needs a probabilistic or sensitivity result, so they are
        # disabled with a tooltip saying what to run first.
        m_stat.addSeparator()
        self._act_sens_plot = QAction("Sensitivity Plot...", self,
                                      triggered=self._sensitivity_plot)
        self._act_conv_plot = QAction("Convergence Plot...", self,
                                      triggered=self._convergence_plot)
        self._act_export_stats = QAction(
            "Export Statistics Data...", self,
            triggered=self._export_statistics)
        self._act_show_gm = QAction("Show GM Surfaces", self,
                                    checkable=True)
        self._act_show_gm.toggled.connect(self._toggle_gm_surfaces)
        self._act_pick_gm = QAction("Pick GM Surfaces...", self,
                                    triggered=self._pick_gm_surfaces)
        self._act_crit_prob = QAction(
            "Critical Probabilistic Surface", self, checkable=True)
        self._act_crit_prob.toggled.connect(self._toggle_critical_prob)
        stats_acts = [self._act_sens_plot, self._act_conv_plot,
                      self._act_export_stats, self._act_show_gm,
                      self._act_pick_gm, self._act_crit_prob]
        for act in stats_acts:
            act.setEnabled(self._has_statistics())
            act.setToolTip(tr(
                "Requires a probabilistic or sensitivity analysis: run "
                "Statistics → Compute Statistics in the modeller."))
            m_stat.addAction(act)

        # -- Tools ----------------------------------------------------
        m_tools = mb.addMenu(tr("Tools"))
        m_tools.addAction(QAction(tr("Measure"), self))
        m_tools.addAction(QAction(tr("Dimension Length"), self))

        # -- Window ---------------------------------------------------
        m_win = mb.addMenu(tr("Window"))
        m_win.addAction(self.summary_dock.toggleViewAction())
        m_win.addAction(self.results_dock.toggleViewAction())
        m_win.addAction(self.slice_dock.toggleViewAction())

        # -- Help -----------------------------------------------------
        m_help = mb.addMenu(tr("Help"))
        m_help.addAction(QAction(tr("Help Topics"), self,
                                  triggered=lambda: self._info(
                                      "Interpret window: double-click a row in the Surfaces dock "
                                      "to focus on a specific slip surface. Slices can be inspected "
                                      "via Query → Query Slice Data.")))

    # ==================================================================
    # v0.1.9 — Method selector toolbar (top of window)
    # ==================================================================
    def _build_method_selector(self) -> None:
        """Add a toolbar with a dropdown to switch between LEM methods.

        Only shown when more than one method has been computed.
        """
        from PySide6.QtWidgets import QComboBox, QLabel, QToolBar

        if len(self.results_by_method) <= 1:
            # v0.1.49 — the method SELECTOR is pointless with one method,
            # but the active algorithm read-out is not: which method
            # produced the numbers on screen is the first thing a reader
            # of a report needs, single method or not. So the toolbar is
            # still created, just without the combo box.
            tb = QToolBar("Method", self)
            tb.setMovable(False)
            tb.setObjectName("MethodSelectorToolbar")
            self.lbl_algorithm = QLabel("")
            self.lbl_algorithm.setStyleSheet(
                "QLabel { padding: 0 8px; font-weight: bold; }")
            tb.addWidget(self.lbl_algorithm)
            self.addToolBar(Qt.TopToolBarArea, tb)
            return

        tb = QToolBar("Method", self)
        tb.setMovable(False)
        tb.setObjectName("MethodSelectorToolbar")

        method_labels = {
            "bishop_simplified": "Bishop Simplified",
            "janbu_simplified": "Janbu Simplified",
            "janbu_corrected": "Janbu Corrected",
            "ordinary_fellenius": "Ordinary / Fellenius",
            "spencer": "Spencer",
            "gle_morgenstern_price": "GLE / Morgenstern-Price",
        }

        lbl = QLabel(tr("  Method:  "))
        lbl.setStyleSheet("font-weight: bold; padding: 0 6px;")
        tb.addWidget(lbl)

        self.cb_method = QComboBox()
        for mid, result in self.results_by_method.items():
            label = method_labels.get(mid, mid)
            crit = result.critical if result is not None else None
            if crit is not None:
                self.cb_method.addItem(
                    f"{label}  —  FoS = {crit.fos:.3f}", mid,
                )
            else:
                self.cb_method.addItem(
                    f"{label}  —  no valid surface", mid,
                )
        self.cb_method.setMinimumWidth(340)
        self.cb_method.currentIndexChanged.connect(self._on_method_changed)
        tb.addWidget(self.cb_method)
        # v0.1.49 — active algorithm read-out. Which method produced the
        # numbers on screen is the first thing a reader of a report needs
        # to know, and a combo box alone does not read as a statement.
        tb.addSeparator()
        self.lbl_algorithm = QLabel("")
        self.lbl_algorithm.setStyleSheet(
            "QLabel { padding: 0 8px; font-weight: bold; }")
        tb.addWidget(self.lbl_algorithm)

        self.addToolBar(Qt.TopToolBarArea, tb)

    def _refresh_algorithm_label(self) -> None:
        lab = getattr(self, "lbl_algorithm", None)
        if lab is None:
            return
        mid = self.active_algorithm()
        fos = self.critical_label_text()
        lab.setText(tr("Method: %s") % mid
                    + (tr("   |   FS = %s") % fos if fos else ""))

    def _on_method_changed(self, index: int) -> None:
        """Switch the displayed method's results."""
        mid = self.cb_method.itemData(index)
        if mid is None or mid not in self.results_by_method:
            return
        result = self.results_by_method[mid]
        self._current_method_id = mid
        self.search_result = result
        self.canvas.display_search_result(
            result, selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode)
        self.summary_dock.show_result(result)
        self.results_dock.show_result(result)
        # v0.1.49 — the legend range and the algorithm read-out belong to
        # the ACTIVE method: each one has its own critical surface and its
        # own spread of factors, so both must follow the switch.
        self._refresh_legend()
        self._refresh_algorithm_label()
        # Clear the slice detail (a previously-shown slip may not be in the new result)
        self.slice_dock.show_slice(None)
        # v0.1.22 — the thrust line depends on the active method
        if getattr(self, "_thrust_visible", False):
            self._redraw_thrust_line()

    # ==================================================================
    # Toolbar
    # ==================================================================
    def _build_toolbar(self) -> None:
        tb = QToolBar("Interpret", self)
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)
        tb.addAction(icon("zoom_all"), tr("Zoom All"), self.canvas.zoom_all)
        tb.addAction(icon("zoom_in"), tr("Zoom In"),
                     lambda: self.canvas.zoom_by(1.25))
        tb.addAction(icon("zoom_out"), tr("Zoom Out"),
                     lambda: self.canvas.zoom_by(1 / 1.25))
        tb.addSeparator()
        tb.addAction(icon("copy"), tr("Copy Image"), self._copy_image)

    # ==================================================================
    # Actions
    # ==================================================================
    def _on_canvas_hover(self, x: float, y: float) -> None:
        """Hover preview: when the cursor is over a cell of the FoS
        heatmap grid, draw the slip surface of the centre with the
        lowest FoS in that cell.

        v0.1.12 — Slide-style preview. The grid is the array of slip-
        circle centres used by Grid Search; we find the centre closest
        to (x, y), look up its best evaluated radius among
        ``search_result.evaluations`` and draw a dashed grey arc.
        """
        if not self.search_result:
            return
        # Throttle: only redraw if the hovered cell changed
        s_search = getattr(self.project.settings, "search", None)
        if s_search is None or not s_search.uses_grid():
            return  # only Grid Search has a centres grid

        # Determine grid bounds
        try:
            xmin, xmax = s_search.grid_x_min, s_search.grid_x_max
            ymin, ymax = s_search.grid_y_min, s_search.grid_y_max
            nx, ny = s_search.grid_nx, s_search.grid_ny
        except Exception:  # noqa: BLE001
            return
        if any(v is None for v in (xmin, xmax, ymin, ymax)) or nx <= 0 or ny <= 0:
            return

        # If outside the grid bbox, clear any preview and return
        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            if self._hover_grid_idx is not None:
                self._hover_grid_idx = None
                self._refresh_canvas_with_highlights()
            return

        # Snap (x, y) to the nearest centre cell
        ix = int(round((x - xmin) / max((xmax - xmin), 1e-9) * (nx - 1)))
        iy = int(round((y - ymin) / max((ymax - ymin), 1e-9) * (ny - 1)))
        ix = max(0, min(nx - 1, ix))
        iy = max(0, min(ny - 1, iy))
        cell = (ix, iy)
        if cell == self._hover_grid_idx:
            return  # same cell as before, no redraw needed
        self._hover_grid_idx = cell

        # Build the centre coordinates and find the best evaluation there
        cx = xmin + ix * (xmax - xmin) / max(nx - 1, 1)
        cy = ymin + iy * (ymax - ymin) / max(ny - 1, 1)
        best = None
        best_fos = float("inf")
        # Scan evaluations whose centre is at (cx, cy) within tolerance
        # The grid cell size sets a natural tolerance
        tol = 0.5 * max(
            (xmax - xmin) / max(nx - 1, 1),
            (ymax - ymin) / max(ny - 1, 1),
        )
        for r in self.search_result.evaluations:
            sd = r.surface.to_dict()
            if sd.get("type") != "circle":
                continue
            ex, ey = sd.get("centre_x"), sd.get("centre_y")
            if ex is None or ey is None:
                continue
            if abs(ex - cx) > tol or abs(ey - cy) > tol:
                continue
            if r.fos < best_fos:
                best_fos = r.fos
                best = r

        if best is None:
            self._hover_grid_idx = None
            self._refresh_canvas_with_highlights()
            return

        sd = best.surface.to_dict()
        sd["_hover_fos"] = best.fos
        self.canvas.display_search_result(
            self.search_result,
            selected_id=self._selected_surface_id,
            hover_id=sd.get("id"),
            hover_surface_dict=sd,
            surface_mode=self._surface_mode,
        )
        self.statusBar().showMessage(
            f"Centre ({cx:.2f}, {cy:.2f}) — best FoS at this centre = "
            f"{best.fos:.3f}",
            2000,
        )
        self._refresh_legend()
        self._refresh_algorithm_label()

    def _refresh_canvas_with_highlights(self) -> None:
        """Re-render canvas using current selection / hover state."""
        self.canvas.display_search_result(
            self.search_result,
            selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode,
        )

    def _on_canvas_click_default(self, x: float, y: float) -> None:
        """Default click handler in Interpret mode.

        v0.1.12 — when Query Slice Data mode is NOT active, a click on
        the canvas selects the best surface of the grid cell containing
        the click (Slide-style). The selected surface is highlighted in
        purple in the canvas and the slice dock updates.
        """
        if not self.search_result:
            return
        s_search = getattr(self.project.settings, "search", None)
        if s_search is None or not s_search.uses_grid():
            return
        try:
            xmin, xmax = s_search.grid_x_min, s_search.grid_x_max
            ymin, ymax = s_search.grid_y_min, s_search.grid_y_max
            nx, ny = s_search.grid_nx, s_search.grid_ny
        except Exception:  # noqa: BLE001
            return
        if any(v is None for v in (xmin, xmax, ymin, ymax)):
            return
        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            return

        ix = int(round((x - xmin) / max((xmax - xmin), 1e-9) * (nx - 1)))
        iy = int(round((y - ymin) / max((ymax - ymin), 1e-9) * (ny - 1)))
        ix = max(0, min(nx - 1, ix))
        iy = max(0, min(ny - 1, iy))
        cx = xmin + ix * (xmax - xmin) / max(nx - 1, 1)
        cy = ymin + iy * (ymax - ymin) / max(ny - 1, 1)
        tol = 0.5 * max(
            (xmax - xmin) / max(nx - 1, 1),
            (ymax - ymin) / max(ny - 1, 1),
        )
        best = None
        best_fos = float("inf")
        for r in self.search_result.evaluations:
            sd = r.surface.to_dict()
            if sd.get("type") != "circle":
                continue
            ex, ey = sd.get("centre_x"), sd.get("centre_y")
            if ex is None or ey is None:
                continue
            if abs(ex - cx) > tol or abs(ey - cy) > tol:
                continue
            if r.fos < best_fos:
                best_fos = r.fos
                best = r
        if best is None:
            return

        sd = best.surface.to_dict()
        self._selected_surface_id = sd.get("id")
        self._selected_result = best
        self.canvas.display_search_result(
            self.search_result,
            selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode,
        )
        if best.slices:
            self.slice_dock.show_slice(best.slices[0])
        if self._slices_visible:
            self._redraw_slices_for_selected()
        self.statusBar().showMessage(
            f"Selected surface at ({cx:.2f}, {cy:.2f}) — FoS = {best.fos:.3f}",
            3000,
        )

    def _on_surface_picked(self, row: int) -> None:
        """User clicked a row in the Surfaces dock.

        v0.1.12 — instead of replacing the search result with a wrapper
        that hid all other surfaces, we now keep the full result on the
        canvas and pass the selected surface id to display_search_result
        so it gets highlighted in PURPLE while everything else stays
        visible (heatmap, top-N surfaces, critical-red surface).
        """
        if self.search_result is None:
            return
        top = self.search_result.top_n(100)
        if not (0 <= row < len(top)):
            return
        res = top[row]
        sd = res.surface.to_dict()
        self._selected_surface_id = sd.get("id")
        self._selected_result = res

        # Re-render with selection highlight (full result still visible)
        self.canvas.display_search_result(
            self.search_result,
            selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode,
        )

        # Show first slice in the slice-data dock
        if res.slices and len(res.slices) > 0:
            self.slice_dock.show_slice(res.slices[0])

        # If Show Slices is active, redraw slices for the picked surface
        if getattr(self, "_slices_visible", False):
            self._redraw_slices_for_selected()

    def _copy_image(self) -> None:
        from PySide6.QtWidgets import QApplication
        pix = self.canvas.grab()
        QApplication.clipboard().setPixmap(pix)
        self.statusBar().showMessage("Canvas image copied to clipboard.", 2000)


    # ==================================================================
    # Phase I3 — the remaining menu entries
    # ==================================================================
    def _has_statistics(self) -> bool:
        parent = self.parent()
        return bool(getattr(parent, "_prob_result", None)
                    or getattr(parent, "_sens_result", None))

    def _stat_results(self):
        parent = self.parent()
        return (getattr(parent, "_prob_result", None),
                getattr(parent, "_sens_result", None))

    def _plot_xy(self, title, series, xlabel, ylabel, marker="o"):
        """A one-off XY chart window.

        Centralised because eight of the new entries are 'plot these
        numbers': repeating the matplotlib boilerplate eight times is how
        eight subtly different charts appear.
        """
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            self._info(tr("matplotlib is not installed."))
            return None
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(680, 460)
        lay = QVBoxLayout(dlg)
        fig = Figure(figsize=(6.4, 4.2), tight_layout=True)
        ax = fig.add_subplot(111)
        for label, xs, ys in series:
            ax.plot(xs, ys, marker=marker, label=label)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        if len(series) > 1 or series and series[0][0]:
            ax.legend(fontsize=8)
        lay.addWidget(FigureCanvasQTAgg(fig))
        # NON-modal on purpose: a chart that blocks the application cannot
        # be compared against the model beside it, and two charts cannot
        # be held open at once. The reference is kept so Qt does not
        # collect the window as soon as this returns.
        dlg.show()
        if not hasattr(self, "_chart_windows"):
            self._chart_windows = []
        self._chart_windows.append(dlg)
        return dlg

    # ---- Data --------------------------------------------------------
    def _graph_sf_with_time(self) -> None:
        """Factor of safety against time, from the transient stages."""
        results = getattr(self.project, "transient_results", None) or []
        pts = [(r.notes.get("time", 0.0), r.notes.get("fos") or {})
               for r in results if r.notes.get("fos")]
        if not pts:
            self._info(tr(
                "No stage has a computed factor of safety. Tick "
                "'Calculate SF' on the stages you need and recompute."))
            return
        methods = sorted({m for _t, f in pts for m in f})
        series = [(mid, [t for t, f in pts if mid in f],
                   [f[mid] for _t, f in pts if mid in f])
                  for mid in methods]
        self._plot_xy(tr("Factor of safety vs time"), series,
                      tr("Time"), tr("Factor of safety"))

    def _support_force_analysis(self) -> None:
        """Force carried by each support on the critical surface."""
        res = self.search_result
        crit = res.critical if res else None
        if crit is None:
            self._info(tr("No critical surface."))
            return
        rows = []
        for i, sup in enumerate(getattr(self.project, "supports", []), 1):
            stype = getattr(sup, "support_type", None) or sup
            label = getattr(stype, "DISPLAY_NAME", None) or f"support {i}"
            cap = None
            for attr in ("anchor_capacity", "tensile_capacity",
                         "plate_capacity"):
                cap = getattr(stype, attr, None)
                if cap:
                    break
            rows.append(f"{i}. {label}: "
                        + (tr("capacity %.2f kN") % cap if cap
                           else tr("capacity not defined")))
        self._info(tr("Supports on the critical surface (FS = %.4f):")
                   % crit.fos + "\n\n" + "\n".join(rows))

    def _back_analysis_report(self) -> None:
        """Support force required to reach a target factor of safety."""
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.back_analysis import required_force
        res = self.search_result
        crit = res.critical if res else None
        if crit is None or not getattr(crit, "slices", None):
            self._info(tr("No critical surface with slice data."))
            return
        target, ok = QInputDialog.getDouble(
            self, tr("Back Analysis"), tr("Target factor of safety:"),
            1.3, 0.01, 100.0, 3)
        if not ok:
            return
        elevation, ok = QInputDialog.getDouble(
            self, tr("Back Analysis"), tr("Elevation of the force:"),
            0.0, -1e6, 1e6, 3)
        if not ok:
            return
        mid = self._current_method_id
        r = required_force(crit.slices, crit.surface, target, mid,
                           elevation)
        if r is None:
            self._info(tr(
                "Back analysis is only available for Bishop, Janbu and "
                "Janbu Corrected, and the force must have a moment arm."))
            return
        self._info(
            tr("Required support force for FS = %g") % target + "\n\n"
            + tr("active: %.2f") % r.active_force + "\n"
            + tr("passive: %.2f") % r.passive_force + "\n\n"
            + tr("The passive value is the larger and therefore the "
                 "conservative one for design."))

    def _toggle_supplemental_contours(self, on: bool) -> None:
        from ogr_gui.contours import ContourMode
        self.contours.mode = (ContourMode.FILLED_LINES if on
                              else ContourMode.FILLED)
        self._refresh_legend()
        self.canvas.display_search_result(
            self.search_result, selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode)

    # ---- Query -------------------------------------------------------
    def _queries(self) -> list:
        if not hasattr(self, "_query_points"):
            self._query_points = []
        return self._query_points

    def _add_query(self) -> None:
        """Add a query point, kept in a list so several locations can be
        compared instead of inspected one at a time and forgotten."""
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, tr("Add Query"), tr("Point as x,y:"))
        if not ok or not text:
            return
        try:
            x, y = (float(v) for v in text.replace(";", ",").split(","))
        except ValueError:
            self._info(tr("Enter two numbers: x,y"))
            return
        self._queries().append((x, y))
        self.statusBar().showMessage(
            tr("%d query point(s)") % len(self._queries()), 4000)

    def _graph_query(self) -> None:
        """Factor of safety of the surfaces passing near each query."""
        qs = self._queries()
        if not qs:
            self._info(tr("No query points. Use Add Query first."))
            return
        res = self.search_result
        if res is None:
            return
        xs, ys = [], []
        for i, (qx, qy) in enumerate(qs, 1):
            best = None
            for ev in res.evaluations:
                if not ev.is_valid or not getattr(ev, "slices", None):
                    continue
                d = min(math.dist((s.base_x_left, s.base_y_left),
                                  (qx, qy)) for s in ev.slices)
                if best is None or d < best[0]:
                    best = (d, ev.fos)
            if best is not None:
                xs.append(i)
                ys.append(best[1])
        if not xs:
            self._info(tr("No surface passes near the query points."))
            return
        self._plot_xy(tr("Factor of safety at query points"),
                      [("", xs, ys)], tr("Query point"),
                      tr("Factor of safety"))

    def _delete_query(self) -> None:
        qs = self._queries()
        if not qs:
            self._info(tr("No query points to delete."))
            return
        from PySide6.QtWidgets import QInputDialog
        items = [f"{i}: ({x:.3f}, {y:.3f})"
                 for i, (x, y) in enumerate(qs, 1)]
        items.append(tr("(all)"))
        choice, ok = QInputDialog.getItem(
            self, tr("Delete Query"), tr("Remove:"), items, 0, False)
        if not ok:
            return
        if choice == tr("(all)"):
            qs.clear()
        else:
            qs.pop(int(choice.split(":")[0]) - 1)
        self.statusBar().showMessage(
            tr("%d query point(s)") % len(qs), 4000)

    def _query_invalid(self) -> None:
        """Why surfaces were rejected — grouped, because a list of two
        hundred identical messages is not a diagnosis."""
        res = self.search_result
        if res is None:
            return
        reasons: dict = {}
        for ev in res.evaluations:
            if ev.is_valid and getattr(ev, "admissible", True):
                continue
            key = (getattr(ev, "error_message", None)
                   or getattr(ev, "admissibility_note", None)
                   or tr("did not converge"))
            reasons[key] = reasons.get(key, 0) + 1
        if not reasons:
            self._info(tr("Every surface evaluated successfully."))
            return
        total = sum(reasons.values())
        lines = [tr("%d surface(s) rejected of %d evaluated:")
                 % (total, len(res.evaluations)), ""]
        lines += [f"  {n} × {why}" for why, n in
                  sorted(reasons.items(), key=lambda t: -t[1])]
        self._info("\n".join(lines))

    # ---- Groundwater -------------------------------------------------
    def _seepage(self):
        return getattr(self.project, "seepage_result", None)

    def _gw_contour_options(self) -> None:
        """Contours of the groundwater field.

        Its own entry point rather than the stability one: a head in
        metres and a factor of safety are different scalars with
        different ranges, and sharing one range would make both useless.
        """
        from ogr_gui.contours import ContourSettings
        if self._seepage() is None:
            self._info(tr("Requires a computed groundwater analysis."))
            return
        if not hasattr(self, "gw_contours"):
            self.gw_contours = ContourSettings(field="pore_pressure")
        from ogr_gui.contours import available_fields
        from ogr_gui.dialogs.contour_options_dialog import (
            ContourOptionsDialog,
        )
        fields = [f for f in available_fields(self.project,
                                              self.search_result)
                  if f != "fos"] or ["pore_pressure"]
        values = list(getattr(self._seepage(),
                              self.gw_contours.field, []) or [])
        dlg = ContourOptionsDialog(self.gw_contours, fields, values, self)
        if dlg.exec():
            self.gw_contours = dlg.settings

    def _gw_query(self) -> None:
        """Nodal values at a point of the mesh."""
        seepage = self._seepage()
        mesh = getattr(self.project, "fem_mesh", None)
        if seepage is None or mesh is None:
            self._info(tr("Requires a computed groundwater analysis."))
            return
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, tr("Groundwater Query"), tr("Point as x,y:"))
        if not ok or not text:
            return
        try:
            x, y = (float(v) for v in text.replace(";", ",").split(","))
        except ValueError:
            self._info(tr("Enter two numbers: x,y"))
            return
        try:
            head = mesh.interpolate(seepage.total_head, x, y)
        except Exception:  # noqa: BLE001
            head = None
        if head is None:
            self._info(tr("The point lies outside the mesh."))
            return
        self._info(
            tr("At (%.3f, %.3f)") % (x, y) + "\n\n"
            + tr("total head: %.4f") % head + "\n"
            + tr("pressure head: %.4f") % (head - y))

    def _gw_user_data(self) -> None:
        """Contour an arbitrary expression of the nodal fields."""
        seepage = self._seepage()
        if seepage is None:
            self._info(tr("Requires a computed groundwater analysis."))
            return
        from PySide6.QtWidgets import QInputDialog
        expr, ok = QInputDialog.getText(
            self, tr("Define User Data"),
            tr("Expression using H (total head), P (pressure head) and "
               "u (pore pressure), for example  H - 25"))
        if not ok or not expr.strip():
            return
        values = []
        try:
            for H, P, u in zip(seepage.total_head, seepage.pressure_head,
                               seepage.pore_pressure):
                # Evaluated with no builtins: a project file must not be
                # able to run arbitrary code through this field.
                values.append(float(eval(expr, {"__builtins__": {}},
                                         {"H": H, "P": P, "u": u})))
        except Exception as exc:  # noqa: BLE001
            self._info(tr("The expression could not be evaluated: %s")
                       % exc)
            return
        self._user_data = values
        self._info(tr("User data computed for %d nodes: range %.4f to "
                      "%.4f") % (len(values), min(values), max(values)))

    def _gw_iteration_history(self) -> None:
        seepage = self._seepage()
        if seepage is None:
            return
        hist = (seepage.notes or {}).get("history")
        if not hist:
            self._info(
                tr("Iterations: %d") % getattr(seepage, "iterations", 0)
                + "\n" + tr("converged: %s")
                % (tr("yes") if seepage.converged else tr("no"))
                + "\n\n" + tr("No per-iteration history was recorded "
                                "for this run."))
            return
        self._plot_xy(tr("Iteration history"),
                      [("", list(range(1, len(hist) + 1)), list(hist))],
                      tr("Iteration"), tr("Maximum change"))

    def _gw_convergence(self) -> None:
        seepage = self._seepage()
        if seepage is None:
            return
        hist = (seepage.notes or {}).get("history") or []
        if not hist:
            self._info(tr(
                "This run recorded no convergence history. The seepage "
                "solver reports its iteration count and final state "
                "instead: %d iterations, converged = %s.")
                % (getattr(seepage, "iterations", 0),
                   tr("yes") if seepage.converged else tr("no")))
            return
        self._plot_xy(tr("Convergence"),
                      [("", list(range(1, len(hist) + 1)), list(hist))],
                      tr("Iteration"), tr("Residual"))

    def _export_nodal_values(self) -> None:
        """Every nodal field to CSV."""
        seepage = self._seepage()
        mesh = getattr(self.project, "fem_mesh", None)
        if seepage is None or mesh is None:
            self._info(tr("Requires a computed groundwater analysis."))
            return
        from PySide6.QtWidgets import QFileDialog
        path, _f = QFileDialog.getSaveFileName(
            self, tr("Export All Nodal Values..."), "",
            "CSV (*.csv);;All files (*)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        import csv
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["node", "x", "y", "total_head",
                            "pressure_head", "pore_pressure"])
                for i, nd in enumerate(mesh.nodes):
                    w.writerow([i, f"{nd.x:.6f}", f"{nd.y:.6f}",
                                f"{seepage.total_head[i]:.6f}",
                                f"{seepage.pressure_head[i]:.6f}",
                                f"{seepage.pore_pressure[i]:.6f}"])
        except Exception as exc:  # noqa: BLE001
            self._info(tr("Could not write the file: %s") % exc)
            return
        self.statusBar().showMessage(
            tr("Exported %d nodes to %s") % (mesh.node_count, path), 8000)

    # ---- Statistics --------------------------------------------------
    def _sensitivity_plot(self) -> None:
        _prob, sens = self._stat_results()
        if sens is None or not sens.ok:
            self._info(tr("No sensitivity result."))
            return
        mid = next(iter(sens.by_method), None)
        sweeps = sens.by_method.get(mid, {})
        series = [(vs.label, vs.percent_of_range(), vs.fos)
                  for vs in sweeps.values()]
        if not series:
            self._info(tr("No sensitivity result."))
            return
        self._plot_xy(tr("Sensitivity"), series,
                      tr("Percent of variable range (%)"),
                      tr("Factor of safety"), marker="")

    def _convergence_plot(self) -> None:
        prob, _sens = self._stat_results()
        if prob is None or not prob.ok:
            self._info(tr("No probabilistic result."))
            return
        mid = next(iter(prob.by_method), None)
        st = prob.by_method[mid].statistics
        conv = st.convergence(steps=60)
        if not conv:
            self._info(tr("No probabilistic result."))
            return
        self._plot_xy(
            tr("Convergence"),
            [(tr("mean FoS"), [c[0] for c in conv],
              [c[1] for c in conv]),
             (tr("probability of failure (%)"), [c[0] for c in conv],
              [100.0 * c[2] for c in conv])],
            tr("Number of samples"), tr("Value"), marker="")

    def _export_statistics(self) -> None:
        prob, _sens = self._stat_results()
        if prob is None or not prob.ok:
            self._info(tr("No probabilistic result."))
            return
        from PySide6.QtWidgets import QFileDialog
        path, _f = QFileDialog.getSaveFileName(
            self, tr("Export Statistics Data..."), "",
            "CSV (*.csv);;All files (*)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        import csv
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                keys = sorted(prob.samples or {})
                w.writerow(["sample"] + keys + ["fos"])
                mid = next(iter(prob.by_method))
                values = prob.by_method[mid].statistics.values
                for i, fos in enumerate(values):
                    row = [i + 1]
                    for k in keys:
                        col = prob.samples.get(k) or []
                        row.append(f"{col[i]:.6g}" if i < len(col) else "")
                    row.append(f"{fos:.6f}")
                    w.writerow(row)
        except Exception as exc:  # noqa: BLE001
            self._info(tr("Could not write the file: %s") % exc)
            return
        self.statusBar().showMessage(tr("Statistics exported to %s")
                                    % path, 8000)

    def _toggle_gm_surfaces(self, on: bool) -> None:
        """Show every global minimum found by an Overall Slope run.

        Their number is the point: several distinct locations mean the
        critical surface moves with the input, which a single drawn
        surface would hide.
        """
        prob, _sens = self._stat_results()
        if prob is None or not prob.ok:
            if on:
                self._info(tr("No probabilistic result."))
            return
        mid = next(iter(prob.by_method))
        minima = getattr(prob.by_method[mid], "global_minima", []) or []
        self.statusBar().showMessage(
            tr("%d distinct global minimum surface(s)") % len(minima)
            if on else "", 8000)

    def _pick_gm_surfaces(self) -> None:
        prob, _sens = self._stat_results()
        if prob is None or not prob.ok:
            self._info(tr("No probabilistic result."))
            return
        mid = next(iter(prob.by_method))
        minima = getattr(prob.by_method[mid], "global_minima", []) or []
        if not minima:
            self._info(tr(
                "This run recorded no separate global minima. They are "
                "produced by the Overall Slope analysis type, which "
                "repeats the whole search per sample."))
            return
        from PySide6.QtWidgets import QInputDialog
        items = []
        for i, sd in enumerate(minima, 1):
            if sd and "radius" in sd:
                items.append(tr("%d: circle centre (%.2f, %.2f) r = %.2f")
                             % (i, sd["centre_x"], sd["centre_y"],
                                sd["radius"]))
            else:
                items.append(tr("%d: non-circular surface") % i)
        QInputDialog.getItem(self, tr("Pick GM Surfaces"),
                             tr("Global minima found:"), items, 0, False)

    def _toggle_critical_prob(self, on: bool) -> None:
        prob, _sens = self._stat_results()
        if prob is None or not prob.ok:
            if on:
                self._info(tr("No probabilistic result."))
            return
        mid = next(iter(prob.by_method))
        cp = getattr(prob.by_method[mid], "critical_probabilistic", None)
        if cp is None:
            if on:
                self._info(tr(
                    "No critical probabilistic surface: it comes from the "
                    "Overall Slope analysis type."))
            return
        if on:
            self.statusBar().showMessage(
                tr("Critical probabilistic surface: PF = %.2f %%, "
                   "reliability index = %.3f")
                % (cp.probability_of_failure * 100.0,
                   cp.reliability_index), 12000)

    def _legend_options(self) -> None:
        """Number format and precision of the colour scale."""
        from PySide6.QtWidgets import (
            QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
            QVBoxLayout,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Legend Options"))
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        sp_dec = QSpinBox()
        sp_dec.setRange(0, 8)
        sp_dec.setValue(self.legend._decimals)
        form.addRow(tr("Decimal places:"), sp_dec)
        sp_steps = QSpinBox()
        sp_steps.setRange(2, 25)
        sp_steps.setValue(self.legend._steps)
        form.addRow(tr("Number of intervals:"), sp_steps)
        chk_sci = QCheckBox(tr("Scientific notation"))
        chk_sci.setChecked(self.legend._scientific)
        form.addRow("", chk_sci)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec():
            vmin, vmax = self.legend.value_range()
            self.legend.configure(
                vmin, vmax, self.legend._colour_fn,
                steps=sp_steps.value(), decimals=sp_dec.value(),
                scientific=chk_sci.isChecked(), mark=self.legend._mark)

    def _export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG (*.png);;JPEG (*.jpg)"
        )
        if not path:
            return
        pix = self.canvas.grab()
        pix.save(path)
        self.statusBar().showMessage(f"Saved {path}", 3000)

    def _export_data_csv(self) -> None:
        if self.search_result is None:
            self._info("No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Raw Data", "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("rank,fos,method,centre_x,centre_y,radius,"
                        "x_left,x_right,iterations,converged\n")
                for i, r in enumerate(
                    sorted((r for r in self.search_result.evaluations if r.is_valid),
                           key=lambda x: x.fos)
                ):
                    sd = r.surface.to_dict()
                    f.write(
                        f"{i+1},{r.fos:.6f},{r.method_id},"
                        f"{sd.get('centre_x', '')},{sd.get('centre_y', '')},"
                        f"{sd.get('radius', '')},{sd.get('x_left', '')},"
                        f"{sd.get('x_right', '')},{r.iterations},{r.converged}\n"
                    )
            self.statusBar().showMessage(f"Saved {path}", 3000)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    # v0.1.22 — Line of thrust overlay
    # ------------------------------------------------------------------
    def _toggle_thrust_line(self, on: bool) -> None:
        """Show/hide the line of thrust (locus of interslice-force
        application points) for the selected surface (or the critical
        one), computed by the interslice post-processor."""
        self._thrust_visible = bool(on)
        self._redraw_thrust_line()

    def _redraw_thrust_line(self) -> None:
        from PySide6.QtGui import QColor, QPen
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath

        scene = self.canvas.scene()
        for it in getattr(self, "_thrust_items", []):
            if it.scene() is scene:
                scene.removeItem(it)
        self._thrust_items = []
        if not getattr(self, "_thrust_visible", False):
            return

        target = getattr(self, "_selected_result", None)
        if target is None and self.search_result and self.search_result.critical:
            target = self.search_result.critical
        if target is None or not target.slices:
            return

        from ogr_slip2d.postprocess import compute_interslice_state
        kh = kv = 0.0
        seis = getattr(self.project, "seismic", None)
        if seis is not None and getattr(seis, "enabled", False):
            kh, kv = seis.kh, seis.kv
        st = compute_interslice_state(target, kh=kh, kv=kv)
        if not st.ok:
            self.statusBar().showMessage(
                "Line of thrust unavailable for this result", 3000)
            return

        slist = list(target.slices)
        xs = [slist[0].base_x_left] + [s.base_x_right for s in slist]
        path = QPainterPath()
        started = False
        for x, y, e in zip(xs, st.y_thrust, st.E):
            # Skip the free ends where E≈0 (application point undefined)
            if abs(e) < 1e-6:
                started = False
                continue
            if not started:
                path.moveTo(x, y)
                started = True
            else:
                path.lineTo(x, y)
        item = QGraphicsPathItem(path)
        from PySide6.QtCore import Qt
        pen = QPen(QColor("#9400d3"), 0)
        pen.setCosmetic(True)
        pen.setWidthF(2.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        item.setPen(pen)
        item.setZValue(60)
        scene.addItem(item)
        self._thrust_items.append(item)
        msg = "Line of thrust — %s" % target.method_id
        if st.e_max > 0 and st.relative_closure > 0.02:
            msg += "  (closure %.1f%%: moment-only method)" % (
                st.relative_closure * 100)
        self.statusBar().showMessage(msg, 4000)

    def _set_surface_mode(self, mode: str) -> None:
        """Switch the surface display mode (Data menu) and redraw.

        v0.1.20 — ``mode`` is one of ``"global_min"`` (critical surface
        only), ``"minimum"`` (top-N lowest-FoS surfaces), or ``"all"``
        (every valid surface, drawn faint behind the critical one). The
        FoS heatmap is unaffected and continues to reflect the active
        method.
        """
        if mode not in ("global_min", "minimum", "all"):
            return
        self._surface_mode = mode
        self.canvas.display_search_result(
            self.search_result,
            selected_id=self._selected_surface_id,
            surface_mode=self._surface_mode,
        )
        labels = {
            "global_min": "Global minimum surface",
            "minimum": "Minimum surfaces (top 30)",
            "all": "All valid surfaces",
        }
        self.statusBar().showMessage(labels[mode], 3000)

    def _toggle_slices(self, on: bool) -> None:
        """Show/hide slice subdivision lines.

        v0.1.12 — uses the SELECTED surface (or critical if none
        selected) instead of always showing the critical one.
        Updates when the user clicks another surface in the list.
        """
        self._slices_visible = bool(on)
        self._redraw_slices_for_selected()

    def _redraw_slices_for_selected(self) -> None:
        """Redraw the slice lines for the currently selected surface
        (or the critical one if no selection)."""
        from PySide6.QtGui import QColor, QPen
        from PySide6.QtWidgets import QGraphicsLineItem

        scene = self.canvas.scene()
        # Always remove old slice lines
        for item in list(scene.items()):
            if getattr(item, "_is_slice_line", False):
                scene.removeItem(item)
        if not self._slices_visible:
            return

        target = getattr(self, "_selected_result", None)
        if target is None and self.search_result and self.search_result.critical:
            target = self.search_result.critical
        if target is None or not target.slices:
            return

        pen = QPen(QColor("#e63946"), 0.8)
        pen.setCosmetic(True)
        for s in target.slices:
            top_y = s.top_y_left
            bot_y = s.base_y_left
            line = QGraphicsLineItem(s.base_x_left, bot_y,
                                     s.base_x_left, top_y)
            line.setPen(pen)
            line._is_slice_line = True
            line.setZValue(6.5)
            scene.addItem(line)

    def _query_slice(self) -> None:
        """Activate click-to-pick mode for slice interrogation.

        v0.1.12 — opens the slice data dock and connects a canvas
        click handler. Clicking on any slice of the selected surface
        shows that slice's full property set in the dock.
        """
        if not self.search_result:
            self._info("No search result to interrogate.")
            return
        target = getattr(self, "_selected_result", None)
        if target is None and self.search_result.critical:
            target = self.search_result.critical
        if target is None or not target.slices:
            self._info("No slices available — run a compute first.")
            return

        # Make sure slices are visible so the user has something to click
        if not getattr(self, "_slices_visible", False):
            self._slices_visible = True
            self._redraw_slices_for_selected()

        self._query_slice_target = target
        self.slice_dock.show()
        self.slice_dock.raise_()
        self.statusBar().showMessage(
            "Click on any slice to view its properties (Esc to exit).",
            8000,
        )
        try:
            self.canvas.scene_clicked.disconnect(self._on_canvas_click_for_query)
        except (TypeError, RuntimeError, AttributeError):
            pass
        try:
            self.canvas.scene_clicked.connect(self._on_canvas_click_for_query)
        except AttributeError:
            # Fallback: just show middle slice if signal not available
            mid = len(target.slices) // 2
            self.slice_dock.show_slice(target.slices[mid])

    def _on_canvas_click_for_query(self, x: float, y: float) -> None:
        """Pick the slice containing the clicked x and show its data."""
        target = getattr(self, "_query_slice_target", None)
        if target is None or not target.slices:
            return
        for s in target.slices:
            if s.base_x_left <= x <= s.base_x_right:
                self.slice_dock.show_slice(s)
                self.slice_dock.raise_()
                self.statusBar().showMessage(
                    f"Slice at x∈[{s.base_x_left:.2f}, {s.base_x_right:.2f}].",
                    4000,
                )
                return
        self.statusBar().showMessage(
            "Click was outside the slice range.", 3000,
        )

    def _show_values_along(self) -> None:
        """Show slice-base quantities (σn, τ, u, α) along the critical
        surface as a chart. v0.1.15 — real implementation."""
        target = getattr(self, "_selected_result", None)
        if target is None and self.search_result and self.search_result.critical:
            target = self.search_result.critical
        if target is None or not target.slices:
            self._info("No slices available — run a compute first.")
            return
        # Collect quantities
        xs = []
        sn = []
        tau = []
        u = []
        alpha = []
        for s in target.slices:
            xc = 0.5 * (s.base_x_left + s.base_x_right)
            xs.append(xc)
            b = max(s.width, 1e-9)
            sigma_n_eff = max(
                s.weight * math.cos(s.base_angle) / b
                - getattr(s, "pore_pressure", 0.0),
                0.0,
            )
            sn.append(sigma_n_eff)
            mat = getattr(s, "material", None)
            if mat is not None and hasattr(mat, "strength"):
                try:
                    tau.append(mat.strength.shear_strength(sigma_n_eff))
                except Exception:  # noqa: BLE001
                    tau.append(0.0)
            else:
                tau.append(0.0)
            u.append(getattr(s, "pore_pressure", 0.0))
            alpha.append(math.degrees(s.base_angle))
        # Chart in a dialog
        try:
            from .dialogs.chart_dialogs import MultiLineDialog
            MultiLineDialog(
                xs,
                series=[
                    ("σ'ₙ (kPa)", sn),
                    ("τ avail. (kPa)", tau),
                    ("u (kPa)", u),
                    ("α (°)", alpha),
                ],
                xlabel="x along surface (m)",
                title=f"Values along surface (FoS={target.fos:.3f})",
                parent=self,
            ).exec()
        except ImportError:
            # Text fallback
            html = "<b>Values along critical surface</b><br><pre>"
            html += f"{'x':>8} {'σnef':>10} {'τavail':>10} {'u':>10} {'α°':>8}<br>"
            for i in range(len(xs)):
                html += (f"{xs[i]:8.2f} {sn[i]:10.2f} {tau[i]:10.2f} "
                         f"{u[i]:10.2f} {alpha[i]:8.1f}<br>")
            html += "</pre>"
            self._info(html)

    def _filter_surfaces(self) -> None:
        """Filter surfaces by FoS / area / depth, then refresh canvas.
        v0.1.15 — real implementation."""
        if not self.search_result:
            return
        valid = [r for r in self.search_result.evaluations if r.is_valid]
        if not valid:
            self._info("No valid surfaces.")
            return
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox,
            QDialogButtonBox, QLabel,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Filter Surfaces"))
        dlg.resize(360, 220)
        v = QVBoxLayout(dlg)
        form = QFormLayout()
        fos_lo = QDoubleSpinBox()
        fos_lo.setRange(0.0, 100.0); fos_lo.setDecimals(3)
        fos_lo.setValue(min(r.fos for r in valid))
        fos_hi = QDoubleSpinBox()
        fos_hi.setRange(0.0, 100.0); fos_hi.setDecimals(3)
        fos_hi.setValue(min(2.0, max(r.fos for r in valid)))
        form.addRow(tr("FoS min:"), fos_lo)
        form.addRow(tr("FoS max:"), fos_hi)
        v.addLayout(form)
        info = QLabel(f"Currently showing {len(valid)} surfaces.")
        v.addWidget(info)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        lo, hi = fos_lo.value(), fos_hi.value()
        # Apply filter as a stored attribute the canvas refresh respects
        self._fos_filter = (lo, hi)
        self.statusBar().showMessage(
            f"Filter active: FoS ∈ [{lo:.3f}, {hi:.3f}]. Use Data → All "
            f"Surfaces to re-display the filtered set.", 6000,
        )

    # v0.1.15 — additional Slide-style queries
    def _free_body_diagram(self) -> None:
        """Show the free-body diagram of a selected slice with all force
        vectors drawn to a common scale and labelled with values:

            W  — slice weight (at the centroid)
            N  — base normal computed by the equilibrium march
            S  — mobilised base shear (method-consistent, at FoS)
            U  — pore-water resultant on the base (u·l)
            E_L, X_L / E_R, X_R — interslice forces on each face, at the
                line-of-thrust application heights

        v0.1.22 — vectors come from the interslice post-processor
        (``ogr_slip2d.postprocess``), not from single-slice statics, so
        the diagram is consistent with the selected method's FoS.
        """
        target = getattr(self, "_selected_result", None)
        if target is None and self.search_result and self.search_result.critical:
            target = self.search_result.critical
        if target is None or not target.slices:
            self._info("No slices available.")
            return
        idx = len(target.slices) // 2
        from PySide6.QtWidgets import QInputDialog
        idx, ok = QInputDialog.getInt(
            self, "Free Body Diagram", "Slice index:",
            idx, 0, len(target.slices) - 1,
        )
        if not ok:
            return
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from PySide6.QtWidgets import QDialog, QVBoxLayout
        except ImportError:
            self._info("matplotlib not installed.")
            return

        from ogr_slip2d.postprocess import compute_interslice_state
        kh = kv = 0.0
        seis = getattr(self.project, "seismic", None)
        if seis is not None and getattr(seis, "enabled", False):
            kh, kv = seis.kh, seis.kv
        st = compute_interslice_state(target, kh=kh, kv=kv)

        slist = list(target.slices)
        s = slist[idx]
        b = max(s.width, 1e-9)

        # ---- forces (kN/m) -------------------------------------------
        W = s.weight
        u = getattr(s, "pore_pressure", 0.0)
        U = u * s.base_length
        if st.ok:
            N, S = st.N[idx], st.S[idx]
            E_L, X_L = st.E[idx], st.X[idx]
            E_R, X_R = st.E[idx + 1], st.X[idx + 1]
            y_tL, y_tR = st.y_thrust[idx], st.y_thrust[idx + 1]
        else:  # fallback: single-slice statics
            N = W * math.cos(s.base_angle)
            S = W * math.sin(s.base_angle)
            E_L = X_L = E_R = X_R = 0.0
            y_tL = s.base_y_left + (s.top_y_left - s.base_y_left) / 3
            y_tR = s.base_y_right + (s.top_y_right - s.base_y_right) / 3

        dlg = QDialog(self)
        dlg.setWindowTitle(
            f"Free Body Diagram — slice {idx} ({target.method_id})")
        dlg.resize(640, 560)
        v = QVBoxLayout(dlg)
        fig = Figure(figsize=(6.6, 5.4), tight_layout=True)
        ax = fig.add_subplot(111)

        # ---- slice outline -------------------------------------------
        xs = [s.base_x_left, s.base_x_right, s.base_x_right, s.base_x_left]
        ys = [s.base_y_left, s.base_y_right, s.top_y_right, s.top_y_left]
        ax.fill(xs + [xs[0]], ys + [ys[0]], color="#d9d9d9",
                edgecolor="black", lw=1.2, alpha=0.5, zorder=1)

        # Common force→length scale: largest arrow ≈ 60 % of slice height
        h_slice = max(0.5 * ((s.top_y_left - s.base_y_left)
                             + (s.top_y_right - s.base_y_right)), 1e-6)
        f_max = max(abs(W), abs(N), abs(S), abs(U),
                    abs(E_L), abs(E_R), abs(X_L), abs(X_R), 1e-9)
        scale = 0.6 * max(h_slice, b) / f_max

        def arrow(x0, y0, fx, fy, color, label, lw=2.0, ls="-"):
            if abs(fx) < 1e-9 and abs(fy) < 1e-9:
                return
            dx, dy = fx * scale, fy * scale
            ax.annotate("", xy=(x0 + dx, y0 + dy), xytext=(x0, y0),
                        arrowprops=dict(arrowstyle="-|>", color=color,
                                        lw=lw, linestyle=ls), zorder=5)
            mag = math.hypot(fx, fy)
            ax.text(x0 + dx * 1.06, y0 + dy * 1.06,
                    f"{label}={mag:.1f}", fontsize=8.5, color=color,
                    ha="left" if dx >= 0 else "right", zorder=6)

        # base geometry
        x_cb = 0.5 * (s.base_x_left + s.base_x_right)
        y_cb = 0.5 * (s.base_y_left + s.base_y_right)
        tx, ty = math.cos(s.base_angle), math.sin(s.base_angle)
        nx, ny = -ty, tx
        from ogr_slip2d.postprocess import _quad_centroid_x, _quad_centroid_y
        x_g, y_g = _quad_centroid_x(s), _quad_centroid_y(s)

        # W (down, at centroid)
        arrow(x_g, y_g, 0.0, -W, "black", "W")
        # N (into the slice, at base midpoint)
        arrow(x_cb, y_cb, N * nx, N * ny, "#1f77b4", "N")
        # S (signed along t, method-consistent)
        arrow(x_cb, y_cb, S * tx, S * ty, "#d62728", "S")
        # U (pore resultant, opposing N direction)
        if U > 0:
            arrow(x_cb - 0.15 * b, y_cb, -U * nx, -U * ny, "#2ca02c", "U")
        # Interslice: left face pushes right (+E_L,+X_L); right face
        # reaction (−E_R,−X_R). Drawn at the thrust heights.
        arrow(s.base_x_left, y_tL, E_L, X_L, "#9467bd", "Z_L")
        arrow(s.base_x_right, y_tR, -E_R, -X_R, "#8c564b", "Z_R")
        ax.plot([s.base_x_left, s.base_x_right], [y_tL, y_tR],
                color="#9467bd", lw=1.0, ls="--", alpha=0.6, zorder=2)

        note = ""
        if st.ok and st.e_max > 0 and st.relative_closure > 0.02:
            note = (f"   (closure |E_n|/max|E| = "
                    f"{st.relative_closure * 100:.1f} % — expected for "
                    f"moment-only methods)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.3)
        ax.set_title(
            f"Slice {idx}: α={math.degrees(s.base_angle):.1f}°, "
            f"b={b:.2f} m, FoS={target.fos:.4f}{note}", fontsize=9)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        canvas = FigureCanvasQTAgg(fig)
        v.addWidget(canvas)
        dlg.exec()

    def _surfaces_through_point(self) -> None:
        """Highlight surfaces that pass within a tolerance of a clicked
        point. Useful for forensic investigation of a specific zone."""
        if not self.search_result:
            return
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
            QVBoxLayout, QLabel,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Surfaces Crossing Point"))
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Enter the coordinates of a point. All "
                            "surfaces passing within the tolerance will "
                            "be highlighted."))
        form = QFormLayout()
        spn_x = QDoubleSpinBox()
        spn_x.setRange(-1e9, 1e9); spn_x.setDecimals(3); spn_x.setSuffix(" m")
        spn_y = QDoubleSpinBox()
        spn_y.setRange(-1e9, 1e9); spn_y.setDecimals(3); spn_y.setSuffix(" m")
        spn_tol = QDoubleSpinBox()
        spn_tol.setRange(0.001, 1e6); spn_tol.setValue(0.5); spn_tol.setSuffix(" m")
        form.addRow(tr("x:"), spn_x)
        form.addRow(tr("y:"), spn_y)
        form.addRow(tr("tolerance:"), spn_tol)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        px, py = spn_x.value(), spn_y.value()
        tol = spn_tol.value()
        # Find surfaces passing close to the point
        hits = []
        for r in self.search_result.evaluations:
            if not r.is_valid or r.surface is None:
                continue
            d = self._distance_point_to_surface(px, py, r.surface)
            if d <= tol:
                hits.append((d, r))
        hits.sort(key=lambda t: t[0])
        self._info(
            f"<b>{len(hits)}</b> surfaces pass within {tol} m of "
            f"({px:.2f}, {py:.2f}).<br>"
            f"Best (lowest FoS) crossing: " +
            (f"FoS = {min(h[1].fos for h in hits):.4f}" if hits else "(none)")
        )

    @staticmethod
    def _distance_point_to_surface(px: float, py: float, surface) -> float:
        """Min distance from point (px,py) to a surface (circle or poly)."""
        d_min = float("inf")
        if hasattr(surface, "polyline"):
            vs = surface.polyline.vertices
            for v1, v2 in zip(vs[:-1], vs[1:]):
                # distance point-to-segment
                ax_, ay_ = v1.x, v1.y
                bx_, by_ = v2.x, v2.y
                dx, dy = bx_ - ax_, by_ - ay_
                L2 = dx * dx + dy * dy
                if L2 < 1e-12:
                    d = math.hypot(px - ax_, py - ay_)
                else:
                    t = max(0.0, min(1.0,
                        ((px - ax_) * dx + (py - ay_) * dy) / L2))
                    qx = ax_ + t * dx
                    qy = ay_ + t * dy
                    d = math.hypot(px - qx, py - qy)
                d_min = min(d_min, d)
        elif hasattr(surface, "radius"):
            cx = surface.centre_x
            cy = surface.centre_y
            r = surface.radius
            d_min = abs(math.hypot(px - cx, py - cy) - r)
        return d_min

    def _add_result_table(self) -> None:
        """Open a sortable table with the full results: FoS, area,
        depth, and surface type for every valid surface."""
        if not self.search_result:
            return
        valid = [r for r in self.search_result.evaluations if r.is_valid]
        if not valid:
            self._info("No valid surfaces.")
            return
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Result Table — {len(valid)} surfaces")
        dlg.resize(640, 480)
        v = QVBoxLayout(dlg)
        tbl = QTableWidget(len(valid), 5)
        tbl.setHorizontalHeaderLabels(
            ["#", "FoS", "Type", "Area (m²)", "Slices"])
        tbl.setSortingEnabled(True)
        for i, r in enumerate(valid):
            tbl.setItem(i, 0, QTableWidgetItem(str(i)))
            it_fos = QTableWidgetItem(f"{r.fos:.4f}")
            it_fos.setData(Qt.UserRole, r.fos)
            tbl.setItem(i, 1, it_fos)
            tbl.setItem(i, 2, QTableWidgetItem(
                "circle" if hasattr(r.surface, "radius") else "polyline"))
            try:
                area = sum(s.weight / max(s.unit_weight, 1e-9) for s in r.slices)
            except Exception:  # noqa: BLE001
                area = 0.0
            tbl.setItem(i, 3, QTableWidgetItem(f"{area:.1f}"))
            tbl.setItem(i, 4, QTableWidgetItem(str(len(r.slices))))
        v.addWidget(tbl)
        dlg.exec()

    def _scatter(self) -> None:
        if not self.search_result:
            return
        valid = [r for r in self.search_result.evaluations if r.is_valid]
        if not valid:
            self._info("No valid surfaces to scatter.")
            return
        xs = [r.surface.to_dict().get("radius", 0.0) for r in valid]
        ys = [r.fos for r in valid]
        try:
            from .dialogs.chart_dialogs import ScatterDialog
            ScatterDialog(xs, ys, xlabel="Radius (m)",
                          ylabel="Factor of Safety",
                          title="FoS vs Radius", parent=self).exec()
        except ImportError:
            self._info("matplotlib not installed.")

    def _graph_sf_along_slope(self) -> None:
        if not self.search_result or not self.search_result.critical:
            self._info("Need a computed critical surface first.")
            return
        try:
            from .dialogs.chart_dialogs import SFAlongSlopeDialog
            SFAlongSlopeDialog(self.search_result.critical, self).exec()
        except ImportError:
            self._info(
                "matplotlib not installed. Run <code>pip install matplotlib</code> "
                "to enable plots."
            )

    def _scatter(self) -> None:
        """FoS vs Radius scatter over the full search population."""
        if not self.search_result:
            return
        valid = [r for r in self.search_result.evaluations if r.is_valid]
        if not valid:
            self._info("No valid surfaces to scatter.")
            return
        xs = [r.surface.to_dict().get("radius", 0.0) for r in valid]
        ys = [r.fos for r in valid]
        try:
            from .dialogs.chart_dialogs import ScatterDialog
            ScatterDialog(
                xs, ys,
                xlabel="Radius (m)",
                ylabel="Factor of Safety",
                title=f"FoS vs Radius — {len(valid)} surfaces",
                parent=self,
            ).exec()
        except ImportError:
            self._info("matplotlib not installed.")

    def _histogram(self) -> None:
        if not self.search_result:
            self._info("No results.")
            return
        valid = [r.fos for r in self.search_result.evaluations if r.is_valid]
        if not valid:
            self._info("No valid surfaces.")
            return
        try:
            from .dialogs.chart_dialogs import HistogramDialog
            HistogramDialog(valid, self).exec()
        except ImportError:
            self._info(
                "matplotlib not installed. Run <code>pip install matplotlib</code> "
                "to enable interactive charts."
            )

    def _cumulative(self) -> None:
        if not self.search_result:
            return
        valid = sorted([r.fos for r in self.search_result.evaluations if r.is_valid])
        if not valid:
            return
        try:
            from .dialogs.chart_dialogs import CumulativeDialog
            CumulativeDialog(valid, self).exec()
        except ImportError:
            n_fail = sum(1 for f in valid if f < 1.0)
            pf = n_fail / len(valid) if valid else 0.0
            self._info(
                f"<b>Cumulative distribution (text fallback)</b><br>"
                f"Surfaces with FoS &lt; 1.0 : {n_fail} / {len(valid)}<br>"
                f"P(FoS &lt; 1) ≈ {pf:.3%}<br>"
                f"<i>Install matplotlib for an interactive CDF plot.</i>"
            )

    # ------------------------------------------------------------------
    def _info(self, html: str) -> None:
        QMessageBox.information(self, tr("Interpret"), html)

    # ==================================================================
    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed.emit()
        super().closeEvent(event)
