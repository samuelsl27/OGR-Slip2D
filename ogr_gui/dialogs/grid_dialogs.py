# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Add Grid + Surface Options dialogs (v0.1.8).

Surface menu has:
    - Auto Grid: uses bounding-box-based grid (existing default)
    - Add Grid: user-defined rectangular grid (NEW in v0.1.8)
    - Surface Options: refactored, includes radius increment,
      composite surfaces, search filters

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class AddGridDialog(QDialog):
    """Define the slip-circle centre grid used by Grid Search.

    Slide convention: the grid is a rectangular array of centres above
    the slope. Each centre has multiple radii swept from a min radius
    up to a maximum determined by the geometry, in steps of the Radius
    Increment (Surface Options).

    The dialog presents:
      - X range (min, max)
      - Y range (min, max)
      - Number of centres in X and Y
      - "Auto" button: fills with sensible defaults from the model bbox
    """

    # Emitted when the user clicks "Pick rectangle on canvas" so the
    # MainWindow can switch the canvas to picking mode while the dialog
    # stays alive (hidden) waiting to be re-shown after the picks.
    pick_started = Signal()

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Add Grid"))
        self.project = project
        self.setSizeGripEnabled(True)
        self.setMinimumSize(380, 360)
        self.resize(440, 480)

        s = project.settings.search

        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "<b>Define the slip-circle centre grid.</b><br>"
            "Each cell of the grid is a candidate circle centre. "
            "For each centre, the radius is swept from a minimum to "
            "the maximum geometric extent in steps defined by the "
            "Radius Increment (Surface Options)."
        ))

        # X range
        gx = QGroupBox(tr("X range"))
        fx = QFormLayout(gx)
        self.sb_xmin = QDoubleSpinBox()
        self.sb_xmin.setRange(-1e6, 1e6); self.sb_xmin.setDecimals(3)
        self.sb_xmax = QDoubleSpinBox()
        self.sb_xmax.setRange(-1e6, 1e6); self.sb_xmax.setDecimals(3)
        fx.addRow(tr("X min:"), self.sb_xmin)
        fx.addRow(tr("X max:"), self.sb_xmax)
        root.addWidget(gx)

        # Y range
        gy = QGroupBox(tr("Y range (above slope)"))
        fy = QFormLayout(gy)
        self.sb_ymin = QDoubleSpinBox()
        self.sb_ymin.setRange(-1e6, 1e6); self.sb_ymin.setDecimals(3)
        self.sb_ymax = QDoubleSpinBox()
        self.sb_ymax.setRange(-1e6, 1e6); self.sb_ymax.setDecimals(3)
        fy.addRow(tr("Y min:"), self.sb_ymin)
        fy.addRow(tr("Y max:"), self.sb_ymax)
        root.addWidget(gy)

        # Discretisation
        gn = QGroupBox(tr("Number of centres"))
        fn = QFormLayout(gn)
        self.sp_nx = QSpinBox(); self.sp_nx.setRange(2, 200)
        self.sp_ny = QSpinBox(); self.sp_ny.setRange(2, 200)
        fn.addRow(tr("nx:"), self.sp_nx)
        fn.addRow(tr("ny:"), self.sp_ny)
        root.addWidget(gn)

        # Pre-fill with existing settings or auto-compute
        self._fill_from_settings_or_auto()

        # Auto button
        btn_auto = QPushButton(tr("Reset to Auto"))
        btn_auto.clicked.connect(self._fill_auto)
        root.addWidget(btn_auto)

        # v0.1.9 — Pick rectangle on canvas (2-click flow)
        self.btn_pick = QPushButton(tr("Pick rectangle on canvas (2 clicks)"))
        self.btn_pick.setToolTip(
            "Click this, then click two opposite corners of the desired "
            "grid rectangle directly on the canvas."
        )
        self.btn_pick.clicked.connect(self._pick_on_canvas)
        root.addWidget(self.btn_pick)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _fill_from_settings_or_auto(self) -> None:
        s = self.project.settings.search
        if s.grid_x_min is not None and s.grid_x_max is not None:
            self.sb_xmin.setValue(s.grid_x_min)
            self.sb_xmax.setValue(s.grid_x_max)
        else:
            self._fill_auto_x()
        if s.grid_y_min is not None and s.grid_y_max is not None:
            self.sb_ymin.setValue(s.grid_y_min)
            self.sb_ymax.setValue(s.grid_y_max)
        else:
            self._fill_auto_y()
        self.sp_nx.setValue(s.grid_nx)
        self.sp_ny.setValue(s.grid_ny)

    def _fill_auto(self) -> None:
        self._fill_auto_x()
        self._fill_auto_y()
        self.sp_nx.setValue(20)
        self.sp_ny.setValue(20)

    def _fill_auto_x(self) -> None:
        try:
            xmin, ymin, xmax, ymax = self.project.bounding_box()
            dx = xmax - xmin
            self.sb_xmin.setValue(xmin + 0.2 * dx)
            self.sb_xmax.setValue(xmax - 0.2 * dx)
        except Exception:
            self.sb_xmin.setValue(0.0)
            self.sb_xmax.setValue(50.0)

    def _fill_auto_y(self) -> None:
        try:
            xmin, ymin, xmax, ymax = self.project.bounding_box()
            dy = ymax - ymin
            self.sb_ymin.setValue(ymax)
            self.sb_ymax.setValue(ymax + 0.8 * dy)
        except Exception:
            self.sb_ymin.setValue(20.0)
            self.sb_ymax.setValue(40.0)

    def _pick_on_canvas(self) -> None:
        """Activate canvas-pick mode WITHOUT hiding the dialog.

        v0.1.13 (P9 fix per Samuel's suggestion): the dialog stays
        visible during the 2-click pick. We only emit ``pick_started``
        to let the MainWindow switch the canvas to PICK_GRID_RECT mode.

        After the picks complete, the MainWindow updates this dialog's
        spinboxes via the existing ``_on_grid_picked`` slot. The user
        then clicks OK directly — no re-opening required.
        """
        self._pick_requested = True
        # Make the dialog non-modal and lower it under the canvas so
        # the user can click on the scene. We do NOT hide() it.
        try:
            self.setModal(False)
        except Exception:  # noqa: BLE001
            pass
        # Keep on top so the user can read its instructions
        from PySide6.QtCore import Qt
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.lower()
        # Tell the MainWindow to start picking now
        if hasattr(self, "pick_started"):
            self.pick_started.emit()

    def _emit_pick_signal(self) -> None:  # back-compat alias
        if hasattr(self, "pick_started"):
            self.pick_started.emit()

    def update_bounds(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Called by the MainWindow after the user clicks 2 corners.
        Updates the spinboxes and brings the dialog back to the front."""
        try:
            self.sb_xmin.setValue(min(x1, x2))
            self.sb_xmax.setValue(max(x1, x2))
            self.sb_ymin.setValue(min(y1, y2))
            self.sb_ymax.setValue(max(y1, y2))
        except Exception:  # noqa: BLE001
            pass
        self._pick_requested = False
        self.raise_()
        self.activateWindow()

    @property
    def pick_requested(self) -> bool:
        return getattr(self, "_pick_requested", False)

    # ------------------------------------------------------------------
    def apply_to_settings(self) -> None:
        s = self.project.settings.search
        s.grid_x_min = self.sb_xmin.value()
        s.grid_x_max = self.sb_xmax.value()
        s.grid_y_min = self.sb_ymin.value()
        s.grid_y_max = self.sb_ymax.value()
        s.grid_nx = self.sp_nx.value()
        s.grid_ny = self.sp_ny.value()


# ======================================================================
class SurfaceOptionsDialog(QDialog):
    """Full Slide-style Surface Options dialog (v0.1.10).

    The dialog is split into:
      1. Global header — Surface Type radio + Search Method dropdown
      2. Method panel — context-sensitive parameters for the chosen method
      3. Filters group — min elevation / depth / area
      4. OK / Cancel / Defaults buttons

    Selecting a different Search Method swaps the visible parameter
    panel (panel switcher pattern). The Search Method dropdown is
    auto-restricted to the methods compatible with the selected
    Surface Type:
        Circular  → Grid, Slope, Auto Refine
        Non-Circular → Block, Path, Simulated Annealing, Auto Refine
    """

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Surface Options"))
        self.project = project
        self.setSizeGripEnabled(True)
        self.setMinimumSize(460, 520)
        self.resize(560, 660)

        from PySide6.QtWidgets import (
            QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox,
            QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
            QRadioButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
        )
        from ogr_core.project.settings import (
            CIRCULAR_METHODS, NON_CIRCULAR_METHODS,
            SearchMethod, SurfaceType, WeakLayerHandling,
        )
        self._SearchMethod = SearchMethod
        self._SurfaceType = SurfaceType
        self._CIRCULAR = CIRCULAR_METHODS
        self._NON_CIRCULAR = NON_CIRCULAR_METHODS

        s = project.settings.search

        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "<b>Failure surface generation & optimization.</b><br>"
            "Configure the algorithm used to enumerate slip surfaces "
            "and the global filters that prune candidate results."
        ))

        # ============ HEADER ============
        header = QGroupBox(tr("Surface Type & Algorithm"))
        hf = QFormLayout(header)

        # Surface Type radio buttons
        st_box = QHBoxLayout()
        self.rb_circular = QRadioButton("Circular")
        self.rb_non_circular = QRadioButton("Non-Circular")
        st_box.addWidget(self.rb_circular)
        st_box.addWidget(self.rb_non_circular)
        st_box.addStretch()
        st_w = QWidget(); st_w.setLayout(st_box)
        hf.addRow(tr("Surface Type:"), st_w)
        if s.surface_type == SurfaceType.NON_CIRCULAR.value:
            self.rb_non_circular.setChecked(True)
        else:
            self.rb_circular.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self.rb_circular)
        bg.addButton(self.rb_non_circular)
        self.rb_circular.toggled.connect(self._on_surface_type_changed)

        # Search Method dropdown
        self.cb_method = QComboBox()
        hf.addRow(tr("Search Method:"), self.cb_method)
        self._method_labels = {
            SearchMethod.GRID_SEARCH: "Grid Search",
            SearchMethod.SLOPE_SEARCH: "Slope Search",
            SearchMethod.AUTO_REFINE: "Auto Refine Search",
            SearchMethod.BLOCK_SEARCH: "Block Search",
            SearchMethod.PATH_SEARCH: "Path Search",
            SearchMethod.SIMULATED_ANNEALING: "Simulated Annealing",
            SearchMethod.PARTICLE_SWARM: "Particle Swarm Search",
        }

        root.addWidget(header)

        # Every "Optimize Surfaces" checkbox on the page; they show
        # one and the same setting, so they are kept in step.
        self._optimize_boxes = []
        # v0.1.111 — the same problem the optimize boxes were given
        # ``_sync_optimize_boxes`` for in v0.1.104, and the same answer.
        # THREE panels show "Composite Surfaces" and two show "Create
        # tension crack for reverse curvature", and there is ONE setting
        # behind each. ``apply`` used to write both from the GRID widgets
        # whatever page the user had been on, so ticking Composite Surfaces
        # under Slope Search or Auto Refine did nothing at all — and was
        # then overwritten by whatever the unseen Grid page still showed.
        # Open since v0.1.78, and rule 7 in its plainest form now that the
        # option finally does something.
        self._composite_boxes: list = []
        self._tcrack_boxes: list = []

        # ============ STACKED PANELS (one per method) ============
        self.stack = QStackedWidget()
        self._panels: dict = {}
        self._panels[SearchMethod.GRID_SEARCH] = self._build_grid_panel(s)
        self._panels[SearchMethod.SLOPE_SEARCH] = self._build_slope_panel(s)
        self._panels[SearchMethod.AUTO_REFINE] = self._build_auto_refine_panel(s)
        self._panels[SearchMethod.BLOCK_SEARCH] = self._build_block_panel(s)
        self._panels[SearchMethod.PATH_SEARCH] = self._build_path_panel(s)
        self._panels[SearchMethod.SIMULATED_ANNEALING] = self._build_sa_panel(s)
        self._panels[SearchMethod.PARTICLE_SWARM] = self._build_pso_panel(s)
        for m in (SearchMethod.GRID_SEARCH, SearchMethod.SLOPE_SEARCH,
                  SearchMethod.AUTO_REFINE, SearchMethod.BLOCK_SEARCH,
                  SearchMethod.PATH_SEARCH, SearchMethod.SIMULATED_ANNEALING,
                  SearchMethod.PARTICLE_SWARM):
            self.stack.addWidget(self._panels[m])
        root.addWidget(self.stack, stretch=1)

        # ============ FILTERS ============
        g_filt = QGroupBox(tr("Filters (apply to all candidate surfaces)"))
        f_filt = QFormLayout(g_filt)

        def _filter_row(label_text, default_value, suffix, current_value, allow_negative=True):
            cb = QCheckBox()
            cb.setChecked(current_value is not None)
            sb = QDoubleSpinBox()
            lo = -1e6 if allow_negative else 0.0
            sb.setRange(lo, 1e6); sb.setDecimals(3); sb.setSuffix(suffix)
            sb.setValue(current_value if current_value is not None else default_value)
            sb.setEnabled(cb.isChecked())
            cb.toggled.connect(sb.setEnabled)
            w = QWidget()
            h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(cb); h.addWidget(sb)
            f_filt.addRow(label_text, w)
            return cb, sb

        # v0.1.102 — wrapped HERE and not inside ``_filter_row``. The three
        # labels used to reach ``addRow`` as a variable, which is a blind
        # spot in both directions: the coverage test counts unwrapped text
        # by looking for a literal in ``addRow(...)`` and saw none, and the
        # completeness test collects tr() keys from the syntax tree, where
        # ``tr(label_text)`` carries no key to check. Untranslated, and
        # nothing said so.
        self.cb_filter_min_elev, self.sb_min_elev = _filter_row(
            tr("Minimum elevation"), 0.0, " m", s.min_elevation,
            allow_negative=True,
        )
        self.cb_filter_min_depth, self.sb_min_depth = _filter_row(
            tr("Minimum depth"), 0.0, " m", s.min_depth,
            allow_negative=False,
        )
        self.cb_filter_min_area, self.sb_min_area = _filter_row(
            tr("Minimum area"), 0.5, " m²", s.min_area,
            allow_negative=False,
        )
        root.addWidget(g_filt)

        # ============ WEAK LAYER HANDLING (v0.1.121) ============
        # Shown always and not only when the model has weak layers: the
        # dialog is built from the settings, not from the geometry, and a
        # control that appears and disappears is one the user cannot find
        # when they need it.
        self.g_weak = QGroupBox(tr("Weak Layer Handling"))
        f_weak = QFormLayout(self.g_weak)
        self.cb_weak = QComboBox()
        self.cb_weak.addItem(tr("Always snap to highest layer"),
                             WeakLayerHandling.HIGHEST.value)
        self.cb_weak.addItem(tr("Automatic case generation"),
                             WeakLayerHandling.AUTO_CASES.value)
        _wl = getattr(s, "weak_layer_handling", WeakLayerHandling.HIGHEST.value)
        _i = self.cb_weak.findData(_wl)
        self.cb_weak.setCurrentIndex(_i if _i >= 0 else 0)
        self.cb_weak.setToolTip(tr(
            "Snapping to the highest layer costs one analysis per surface. "
            "Automatic case generation tries every combination of the layers "
            "a surface touches and keeps the worst, which is rigorous and "
            "costs 2^n analyses of that surface."))
        f_weak.addRow(tr("When a surface touches several layers:"),
                      self.cb_weak)
        self.sp_weak_cases = QSpinBox()
        self.sp_weak_cases.setRange(0, 12)
        self.sp_weak_cases.setValue(
            int(getattr(s, "weak_layer_max_cases_log2", 6)))
        self.sp_weak_cases.setToolTip(tr(
            "Above this many layers on one surface, that surface falls back "
            "to snapping to the highest, and the run says so."))
        f_weak.addRow(tr("Most layers to combine (n in 2^n):"),
                      self.sp_weak_cases)
        root.addWidget(self.g_weak)

        # ============ BUTTONS ============
        btn_box = QHBoxLayout()
        self.btn_defaults = QPushButton(tr("Defaults"))
        self.btn_defaults.clicked.connect(self._on_defaults)
        btn_box.addWidget(self.btn_defaults)
        btn_box.addStretch()
        self.btn_ok = QPushButton(tr("OK"))
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton(tr("Cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_ok)
        btn_box.addWidget(self.btn_cancel)
        root.addLayout(btn_box)

        # Wire method dropdown change → panel swap
        self.cb_method.currentIndexChanged.connect(self._on_method_changed)

        # Initial fill of method dropdown
        self._refill_methods(initial=True)

    # ----------------------------------------------------------------
    def _refill_methods(self, initial: bool = False) -> None:
        """Refill the Search Method dropdown with methods compatible
        with the currently-selected Surface Type."""
        SearchMethod = self._SearchMethod
        s = self.project.settings.search

        if self.rb_circular.isChecked():
            allowed = [
                SearchMethod.GRID_SEARCH,
                SearchMethod.SLOPE_SEARCH,
                SearchMethod.AUTO_REFINE,
                SearchMethod.PARTICLE_SWARM,
            ]
        else:
            allowed = [
                SearchMethod.BLOCK_SEARCH,
                SearchMethod.PATH_SEARCH,
                SearchMethod.SIMULATED_ANNEALING,
                SearchMethod.AUTO_REFINE,
                SearchMethod.PARTICLE_SWARM,
            ]

        # Pre-fetch the previously selected method
        prev_id = (
            self.cb_method.currentData()
            if self.cb_method.count() > 0
            else None
        )
        # On the very first fill, use settings
        if initial:
            try:
                prev_id = SearchMethod(s.search_method)
            except (KeyError, ValueError):
                prev_id = allowed[0]

        self.cb_method.blockSignals(True)
        self.cb_method.clear()
        for m in allowed:
            self.cb_method.addItem(self._method_labels[m], m)
        self.cb_method.blockSignals(False)

        # Restore selection if still available, else default to first
        idx = self.cb_method.findData(prev_id) if prev_id else -1
        if idx < 0:
            idx = 0
        self.cb_method.setCurrentIndex(idx)
        self._on_method_changed()

    def _on_surface_type_changed(self, _checked: bool = False) -> None:
        self._refill_methods()

    def _on_method_changed(self, *_args) -> None:
        m = self.cb_method.currentData()
        if m is None:
            return
        panel = self._panels.get(m)
        if panel is not None:
            self.stack.setCurrentWidget(panel)

    def _on_defaults(self) -> None:
        """Reset the current panel to engineering defaults from SearchSettings()."""
        from ogr_core.project.settings import (SearchSettings,
                                               optimize_enabled_for)
        defaults = SearchSettings()

        def _optimize_default_for(method) -> bool:
            """The Optimize Surfaces default OF THIS METHOD.

            v0.1.119 — it is not one value any more: the setting defaults to
            automatic, which reads ON for Simulated Annealing and OFF for
            the rest. Restoring defaults on the annealing panel with the
            Block Search's answer would be restoring the wrong default.
            """
            probe = SearchSettings()
            probe.search_method = getattr(method, "value", method)
            return optimize_enabled_for(probe)
        SM = self._SearchMethod
        m = self.cb_method.currentData()
        try:
            if m == SM.GRID_SEARCH:
                self._g_radius.setValue(int(defaults.radius_increment))
                self._g_composite.setChecked(defaults.composite_surfaces)
                self._g_tcrack.setChecked(defaults.create_tension_crack_reverse_curvature)
            elif m == SM.SLOPE_SEARCH:
                self._sl_num.setValue(int(defaults.num_surfaces))
                self._sl_upper_cb.setChecked(defaults.initial_angle_at_toe_upper_enabled)
                self._sl_upper_sb.setValue(defaults.initial_angle_at_toe_upper_deg)
                self._sl_lower_cb.setChecked(defaults.initial_angle_at_toe_lower_enabled)
                self._sl_lower_sb.setValue(defaults.initial_angle_at_toe_lower_deg)
                self._sl_composite.setChecked(defaults.composite_surfaces)
                self._sl_tcrack.setChecked(defaults.create_tension_crack_reverse_curvature)
            elif m == SM.AUTO_REFINE:
                self._ar_div_slope.setValue(int(defaults.auto_refine_divisions_along_slope))
                self._ar_circles_per_div.setValue(int(defaults.auto_refine_circles_per_division))
                self._ar_num_iter.setValue(int(defaults.auto_refine_num_iterations))
                self._ar_div_pct.setValue(defaults.auto_refine_divisions_to_use_pct)
                if self._ar_num_verts is not None:
                    self._ar_num_verts.setValue(int(defaults.auto_refine_num_vertices_along_surface))
                self._ar_composite.setChecked(defaults.composite_surfaces)
            elif m == SM.SIMULATED_ANNEALING:
                self._sa_verts.setValue(int(defaults.sa_initial_vertices))
                self._sa_steps.setValue(int(defaults.sa_generation_steps))
                self._sa_num_fos.setValue(int(defaults.sa_num_fos_compared_before_stopping))
                self._sa_tol.setValue(defaults.sa_tolerance)
                self._sa_tcoef.setValue(defaults.sa_temperature_coefficient)
                self._sa_convex.setChecked(defaults.sa_convex_only)
                self._pso_n.setValue(int(defaults.pso_num_particles))
                self._pso_it.setValue(int(defaults.pso_num_iterations))
                self._pso_multi.setChecked(bool(defaults.pso_multiple_minima))
                self._pso_radius.setValue(
                    float(defaults.pso_niche_radius_pct))
                self._sync_optimize_boxes(_optimize_default_for(m))
            elif m == SM.PATH_SEARCH:
                self._p_num.setValue(int(defaults.path_num_surfaces))
                self._p_upper_cb.setChecked(defaults.path_initial_angle_at_toe_upper_enabled)
                self._p_upper_sb.setValue(defaults.path_initial_angle_at_toe_upper_deg)
                self._p_lower_cb.setChecked(defaults.path_initial_angle_at_toe_lower_enabled)
                self._p_lower_sb.setValue(defaults.path_initial_angle_at_toe_lower_deg)
                self._p_seglen_cb.setChecked(defaults.path_segment_length_manual)
                self._p_seglen.setValue(defaults.path_segment_length_value)
                self._p_convex.setChecked(defaults.path_convex_only)
                self._sync_optimize_boxes(_optimize_default_for(m))
            elif m == SM.BLOCK_SEARCH:
                self._b_num.setValue(int(defaults.block_num_surfaces))
                self._b_multi.setChecked(defaults.block_multiple_groups)
                self._b_groups.setValue(max(1, int(defaults.block_num_groups)))
                self._b_left_start.setValue(defaults.block_left_start_angle_deg)
                self._b_left_end.setValue(defaults.block_left_end_angle_deg)
                self._b_right_start.setValue(defaults.block_right_start_angle_deg)
                self._b_right_end.setValue(defaults.block_right_end_angle_deg)
                self._b_convex.setChecked(defaults.block_convex_only)
                self._sync_optimize_boxes(_optimize_default_for(m))
        except (AttributeError, RuntimeError):
            pass

    # ================================================================
    def _optimize_row(self, s):
        """One "Optimize Surfaces" checkbox with its Settings... button.

        v0.1.104 — three panels show this control and there is ONE setting
        behind it, ``optimize_enabled``, so the three have to agree. They
        did not: ``apply`` used to fold them together with an OR, and since
        all three start from the same stored value, unticking the box in
        one panel left the other two holding True and the OR put it back.
        The box could be ticked and never cleared.

        They are kept in step here instead, at the moment of the click, so
        ``apply`` has one value to write and no rule to get wrong.
        """
        from PySide6.QtWidgets import QHBoxLayout, QWidget

        box = QCheckBox(tr("Optimize Surfaces"))
        # v0.1.119 — the RESOLVED value. ``optimize_enabled`` is a
        # tri-state since this version and ``None`` means automatic;
        # handing a checkbox a None would show it unticked and then
        # write that back on OK, quietly turning the option off for
        # Simulated Annealing, which is where it defaults ON.
        from ogr_core.project.settings import optimize_enabled_for
        box.setChecked(optimize_enabled_for(s))
        button = QPushButton(tr("Settings..."))
        button.setEnabled(box.isChecked())
        button.clicked.connect(self._on_optimize_settings)
        box.toggled.connect(button.setEnabled)
        box.toggled.connect(self._sync_optimize_boxes)
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(box)
        h.addWidget(button)
        h.addStretch(1)
        self._optimize_boxes.append(box)
        return box, row

    def _sync_optimize_boxes(self, checked: bool) -> None:
        """Carry a tick across to the panels the user cannot see."""
        self._sync_boxes(self._optimize_boxes, checked)

    def _sync_composite_boxes(self, checked: bool) -> None:
        """Composite Surfaces: three panels, one setting."""
        self._sync_boxes(self._composite_boxes, checked)

    def _sync_tcrack_boxes(self, checked: bool) -> None:
        """Reverse-curvature tension crack: two panels, one setting."""
        self._sync_boxes(self._tcrack_boxes, checked)

    @staticmethod
    def _sync_boxes(boxes, checked: bool) -> None:
        """Carry a tick across to the panels the user cannot see.

        Kept at the moment of the click rather than reconciled in
        ``apply``, so that ``apply`` has one value to write and no rule to
        get wrong. v0.1.104 tried the other way for the optimize boxes: an
        OR over the three, which — since all three start from the same
        stored value — put back a tick the user had just cleared.
        """
        for box in boxes:
            if box.isChecked() != checked:
                box.blockSignals(True)
                box.setChecked(checked)
                box.blockSignals(False)

    def _on_optimize_settings(self) -> None:
        """Open the Optimize Surfaces Settings panel.

        Applied straight onto the project rather than held: this dialog's
        own OK writes the rest of the page the same way, and holding a
        second layer of pending values would be a second place for them to
        get out of step.
        """
        from .optimize_settings_dialog import OptimizeSettingsDialog

        dlg = OptimizeSettingsDialog(self.project, self)
        if dlg.exec():
            dlg.apply()

    # ================================================================
    # Panel builders
    # ================================================================
    # ================================================================
    # Panel builders — parameters as defined in Slide's Surface Options
    # (Surface_Options.pdf)
    # ================================================================
    def _build_grid_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QFormLayout, QGroupBox, QSpinBox,
        )
        w = QGroupBox(tr("Grid Search Options"))
        f = QFormLayout(w)
        self._g_radius = QSpinBox()
        self._g_radius.setRange(1, 1000)
        self._g_radius.setValue(int(s.radius_increment))
        self._g_radius.setToolTip(
            "Number of radius increments swept at each grid centre.\n"
            "More = more candidate circles per centre = slower but\n"
            "more thorough."
        )
        f.addRow(tr("Radius Increment:"), self._g_radius)
        self._g_composite = QCheckBox(
            # v0.1.111 — the label said "a Material Boundary" and that is
            # not what it does: the surface follows the LOWER EDGE OF THE
            # EXTERNAL BOUNDARY, which is where a bedrock horizon is drawn.
            # Harmless while the option did nothing; misleading now.
            tr("Composite Surfaces (the slip surface follows the base of "
               "the External Boundary)")
        )
        self._g_composite.setChecked(s.composite_surfaces)
        self._composite_boxes.append(self._g_composite)
        self._g_composite.toggled.connect(self._sync_composite_boxes)
        f.addRow("", self._g_composite)
        self._g_tcrack = QCheckBox(
            tr("Create tension crack for reverse curvature")
        )
        self._g_tcrack.setChecked(s.create_tension_crack_reverse_curvature)
        self._tcrack_boxes.append(self._g_tcrack)
        self._g_tcrack.toggled.connect(self._sync_tcrack_boxes)
        self._g_tcrack.setToolTip(
            "Insert a tension crack automatically when the slip surface\n"
            "exhibits a concave segment (κ < 0) at the up-slope side."
        )
        f.addRow("", self._g_tcrack)
        return w

    def _build_slope_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
            QSpinBox, QWidget,
        )
        w = QGroupBox(tr("Slope Search Options"))
        f = QFormLayout(w)
        self._sl_num = QSpinBox()
        self._sl_num.setRange(10, 1000000)
        self._sl_num.setValue(int(s.num_surfaces))
        self._sl_num.setToolTip(
            tr("Total population size N for the random slope-tangent search.")
        )
        f.addRow(tr("Number of Surfaces:"), self._sl_num)

        # Initial Angle at Toe — Upper / Lower with checkboxes (Slide style)
        def _angle_row(enabled, value, default):
            cb = QCheckBox(); cb.setChecked(bool(enabled))
            sb = QDoubleSpinBox(); sb.setRange(-180.0, 180.0)
            sb.setDecimals(1); sb.setSuffix(" °")
            sb.setValue(value if value is not None else default)
            sb.setEnabled(cb.isChecked())
            cb.toggled.connect(sb.setEnabled)
            ww = QWidget(); h = QHBoxLayout(ww)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(cb); h.addWidget(sb)
            return cb, sb, ww

        self._sl_upper_cb, self._sl_upper_sb, upper_w = _angle_row(
            s.initial_angle_at_toe_upper_enabled,
            s.initial_angle_at_toe_upper_deg, -45.0,
        )
        f.addRow(tr("Upper Angle:"), upper_w)
        self._sl_lower_cb, self._sl_lower_sb, lower_w = _angle_row(
            s.initial_angle_at_toe_lower_enabled,
            s.initial_angle_at_toe_lower_deg, -45.0,
        )
        f.addRow(tr("Lower Angle:"), lower_w)

        self._sl_composite = QCheckBox(tr("Composite Surfaces"))
        self._sl_composite.setChecked(s.composite_surfaces)
        self._composite_boxes.append(self._sl_composite)
        self._sl_composite.toggled.connect(self._sync_composite_boxes)
        f.addRow("", self._sl_composite)
        self._sl_tcrack = QCheckBox(tr("Create tension crack for reverse curvature"))
        self._sl_tcrack.setChecked(s.create_tension_crack_reverse_curvature)
        self._tcrack_boxes.append(self._sl_tcrack)
        self._sl_tcrack.toggled.connect(self._sync_tcrack_boxes)
        f.addRow("", self._sl_tcrack)
        return w

    def _build_auto_refine_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QSpinBox,
        )
        w = QGroupBox(tr("Auto Refine Search Options"))
        f = QFormLayout(w)
        self._ar_div_slope = QSpinBox()
        self._ar_div_slope.setRange(2, 200)
        self._ar_div_slope.setValue(int(s.auto_refine_divisions_along_slope))
        f.addRow(tr("Divisions along slope:"), self._ar_div_slope)
        self._ar_circles_per_div = QSpinBox()
        self._ar_circles_per_div.setRange(1, 200)
        self._ar_circles_per_div.setValue(int(s.auto_refine_circles_per_division))
        f.addRow(tr("Circles per division:"), self._ar_circles_per_div)
        self._ar_num_iter = QSpinBox()
        self._ar_num_iter.setRange(1, 50)
        self._ar_num_iter.setValue(int(s.auto_refine_num_iterations))
        f.addRow(tr("Number of Iterations:"), self._ar_num_iter)
        self._ar_div_pct = QDoubleSpinBox()
        self._ar_div_pct.setRange(1.0, 100.0); self._ar_div_pct.setDecimals(1)
        self._ar_div_pct.setSuffix(" %")
        self._ar_div_pct.setValue(s.auto_refine_divisions_to_use_pct)
        f.addRow(tr("Divisions to use in next iteration:"), self._ar_div_pct)
        # Only show "Number of vertices along surface" for non-circular
        if s.surface_type == self._SurfaceType.NON_CIRCULAR.value:
            self._ar_num_verts = QSpinBox()
            self._ar_num_verts.setRange(3, 100)
            self._ar_num_verts.setValue(int(s.auto_refine_num_vertices_along_surface))
            f.addRow(tr("Number of vertices along surface:"), self._ar_num_verts)
        else:
            self._ar_num_verts = None
        # Computed totals (informative)
        n_total = (s.auto_refine_divisions_along_slope
                   * s.auto_refine_circles_per_division
                   * s.auto_refine_num_iterations)
        n_interp = (s.auto_refine_divisions_along_slope
                    * s.auto_refine_circles_per_division)
        self._ar_total_label = QLabel(
            f"Number of Surfaces Computed: {n_total}\n"
            f"Number of Surfaces Interpreted: {n_interp}"
        )
        self._ar_total_label.setStyleSheet("color: #666; font-size: 9pt;")
        f.addRow("", self._ar_total_label)
        self._ar_composite = QCheckBox(tr("Composite Surfaces"))
        self._ar_composite.setChecked(s.composite_surfaces)
        self._composite_boxes.append(self._ar_composite)
        self._ar_composite.toggled.connect(self._sync_composite_boxes)
        f.addRow("", self._ar_composite)
        return w

    def _build_sa_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QSpinBox,
        )
        w = QGroupBox(tr("Simulated Annealing Search Options"))
        f = QFormLayout(w)
        self._sa_verts = QSpinBox()
        self._sa_verts.setRange(3, 100); self._sa_verts.setValue(int(s.sa_initial_vertices))
        f.addRow(tr("Initial number of surface vertices:"), self._sa_verts)
        self._sa_steps = QSpinBox()
        self._sa_steps.setRange(10, 1000000); self._sa_steps.setValue(int(s.sa_generation_steps))
        f.addRow(tr("Number of annealing generation steps:"), self._sa_steps)
        self._sa_num_fos = QSpinBox()
        self._sa_num_fos.setRange(2, 50)
        self._sa_num_fos.setValue(int(s.sa_num_fos_compared_before_stopping))
        f.addRow(tr("Number of factors of safety compared\nbefore stopping:"), self._sa_num_fos)
        self._sa_tol = QDoubleSpinBox()
        self._sa_tol.setRange(1e-9, 1.0); self._sa_tol.setDecimals(9)
        self._sa_tol.setSingleStep(1e-4); self._sa_tol.setValue(s.sa_tolerance)
        f.addRow(tr("Tolerance for stopping criterion:"), self._sa_tol)
        self._sa_tcoef = QDoubleSpinBox()
        self._sa_tcoef.setRange(0.5, 50.0); self._sa_tcoef.setDecimals(2)
        self._sa_tcoef.setSingleStep(0.5); self._sa_tcoef.setValue(s.sa_temperature_coefficient)
        self._sa_tcoef.setToolTip(
            "Slide spec: c-coefficient in T_k = T_0 · exp(-c · k^(1/n)).\n"
            "Default 8.0 (paper Su 2009)."
        )
        f.addRow(tr("Coefficient in temperature reduction:"), self._sa_tcoef)
        self._sa_convex = QCheckBox(tr("Convex Surfaces Only"))
        self._sa_convex.setChecked(s.sa_convex_only)
        f.addRow("", self._sa_convex)
        self._sa_optimize, sa_row = self._optimize_row(s)
        f.addRow("", sa_row)
        return w

    def _build_pso_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QSpinBox,
        )
        w = QGroupBox(tr("Particle Swarm Search Options"))
        f = QFormLayout(w)
        self._pso_n = QSpinBox()
        self._pso_n.setRange(3, 2000)
        self._pso_n.setValue(int(s.pso_num_particles))
        f.addRow(tr("Number of particles:"), self._pso_n)
        self._pso_it = QSpinBox()
        self._pso_it.setRange(1, 10000)
        self._pso_it.setValue(int(s.pso_num_iterations))
        f.addRow(tr("Number of iterations:"), self._pso_it)
        self._pso_multi = QCheckBox(tr("Report several minima"))
        self._pso_multi.setChecked(bool(s.pso_multiple_minima))
        self._pso_multi.setToolTip(tr(
            "A slope may have several critical regions. With this on the "
            "search reports the most critical surface of each region "
            "instead of the single global minimum."))
        f.addRow(tr("Number of Mins:"), self._pso_multi)
        self._pso_radius = QDoubleSpinBox()
        self._pso_radius.setRange(0.1, 100.0)
        self._pso_radius.setDecimals(1)
        self._pso_radius.setSuffix(" %")
        self._pso_radius.setValue(float(s.pso_niche_radius_pct))
        self._pso_radius.setToolTip(tr(
            "Two minima closer together than this are the same minimum. "
            "As a percentage of the span of the search space, so it means "
            "the same whatever the model measures."))
        f.addRow(tr("Grouping radius:"), self._pso_radius)
        self._pso_radius.setEnabled(self._pso_multi.isChecked())
        self._pso_multi.toggled.connect(self._pso_radius.setEnabled)
        self._pso_optimize, pso_row = self._optimize_row(s)
        f.addRow("", pso_row)
        return w

    def _build_path_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
            QSpinBox, QWidget,
        )
        w = QGroupBox(tr("Path Search Options"))
        f = QFormLayout(w)
        self._p_num = QSpinBox()
        self._p_num.setRange(10, 1000000)
        self._p_num.setValue(int(s.path_num_surfaces))
        f.addRow(tr("Number of Surfaces:"), self._p_num)

        # Initial Angle at Toe — Upper / Lower with checkboxes
        def _angle_row(enabled, value, default):
            cb = QCheckBox(); cb.setChecked(bool(enabled))
            sb = QDoubleSpinBox(); sb.setRange(-180.0, 180.0)
            sb.setDecimals(1); sb.setSuffix(" °")
            sb.setValue(value if value is not None else default)
            sb.setEnabled(cb.isChecked())
            cb.toggled.connect(sb.setEnabled)
            ww = QWidget(); h = QHBoxLayout(ww); h.setContentsMargins(0,0,0,0)
            h.addWidget(cb); h.addWidget(sb)
            return cb, sb, ww

        self._p_upper_cb, self._p_upper_sb, upper_w = _angle_row(
            s.path_initial_angle_at_toe_upper_enabled,
            s.path_initial_angle_at_toe_upper_deg, 45.0,
        )
        f.addRow(tr("Upper Angle (Initial Angle at Toe):"), upper_w)
        self._p_lower_cb, self._p_lower_sb, lower_w = _angle_row(
            s.path_initial_angle_at_toe_lower_enabled,
            s.path_initial_angle_at_toe_lower_deg, 45.0,
        )
        f.addRow(tr("Lower Angle (Initial Angle at Toe):"), lower_w)

        # Segment Length (auto by default, manual override)
        seg_w = QWidget(); seg_h = QHBoxLayout(seg_w)
        seg_h.setContentsMargins(0,0,0,0)
        self._p_seglen_cb = QCheckBox(tr("Manual:"))
        self._p_seglen_cb.setChecked(s.path_segment_length_manual)
        self._p_seglen = QDoubleSpinBox()
        self._p_seglen.setRange(0.1, 1000.0); self._p_seglen.setDecimals(4)
        self._p_seglen.setSuffix(" m")
        self._p_seglen.setValue(s.path_segment_length_value)
        self._p_seglen.setEnabled(self._p_seglen_cb.isChecked())
        self._p_seglen_cb.toggled.connect(self._p_seglen.setEnabled)
        seg_h.addWidget(self._p_seglen_cb); seg_h.addWidget(self._p_seglen)
        f.addRow(tr("Segment Length:"), seg_w)

        self._p_convex = QCheckBox(tr("Convex Surfaces Only"))
        self._p_convex.setChecked(s.path_convex_only)
        f.addRow("", self._p_convex)
        self._p_optimize, p_row = self._optimize_row(s)
        f.addRow("", p_row)
        return w

    def _build_block_panel(self, s):
        from PySide6.QtWidgets import (
            QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
            QLabel, QSpinBox, QVBoxLayout, QWidget,
        )
        w = QGroupBox(tr("Block Search Options"))
        outer = QVBoxLayout(w)

        # Top row: Number of Surfaces + Multiple Groups
        f1 = QFormLayout()
        self._b_num = QSpinBox()
        self._b_num.setRange(10, 1000000)
        self._b_num.setValue(int(s.block_num_surfaces))
        f1.addRow(tr("Number of Surfaces:"), self._b_num)
        self._b_multi = QCheckBox(tr("Multiple Groups"))
        self._b_multi.setChecked(s.block_multiple_groups)
        f1.addRow("", self._b_multi)
        # v0.1.118 — the group count is its OWN control now. It used to be
        # derived as ``Number of Surfaces // 1000``, which is two unrelated
        # magnitudes tied together: 5000 surfaces meant five groups, and a
        # user who asked for more surfaces silently got a different shape
        # of search. Defect D07c(b).
        self._b_groups = QSpinBox()
        self._b_groups.setRange(1, 20)
        self._b_groups.setValue(max(1, int(s.block_num_groups)))
        self._b_groups.setEnabled(self._b_multi.isChecked())
        self._b_multi.toggled.connect(self._b_groups.setEnabled)
        f1.addRow(tr("Number of Groups:"), self._b_groups)
        outer.addLayout(f1)

        # Side-by-side projection angles
        proj_w = QWidget()
        proj_h = QHBoxLayout(proj_w)
        proj_h.setContentsMargins(0, 0, 0, 0)
        # Left projection
        gleft = QGroupBox(tr("Left Projection Angle"))
        fl = QFormLayout(gleft)
        self._b_left_start = QDoubleSpinBox()
        self._b_left_start.setRange(0.0, 360.0); self._b_left_start.setDecimals(1)
        self._b_left_start.setSuffix(" °"); self._b_left_start.setValue(s.block_left_start_angle_deg)
        fl.addRow(tr("Start Angle:"), self._b_left_start)
        self._b_left_end = QDoubleSpinBox()
        self._b_left_end.setRange(0.0, 360.0); self._b_left_end.setDecimals(1)
        self._b_left_end.setSuffix(" °"); self._b_left_end.setValue(s.block_left_end_angle_deg)
        fl.addRow(tr("End Angle:"), self._b_left_end)
        proj_h.addWidget(gleft)
        # Right projection
        gright = QGroupBox(tr("Right Projection Angle"))
        fr = QFormLayout(gright)
        self._b_right_start = QDoubleSpinBox()
        self._b_right_start.setRange(0.0, 360.0); self._b_right_start.setDecimals(1)
        self._b_right_start.setSuffix(" °"); self._b_right_start.setValue(s.block_right_start_angle_deg)
        fr.addRow(tr("Start Angle:"), self._b_right_start)
        self._b_right_end = QDoubleSpinBox()
        self._b_right_end.setRange(0.0, 360.0); self._b_right_end.setDecimals(1)
        self._b_right_end.setSuffix(" °"); self._b_right_end.setValue(s.block_right_end_angle_deg)
        fr.addRow(tr("End Angle:"), self._b_right_end)
        proj_h.addWidget(gright)
        outer.addWidget(proj_w)

        # Convex / Optimize
        self._b_convex = QCheckBox(tr("Convex Surfaces Only"))
        self._b_convex.setChecked(s.block_convex_only)
        outer.addWidget(self._b_convex)
        self._b_optimize, b_row = self._optimize_row(s)
        outer.addWidget(b_row)
        return w

    # ================================================================
    def apply(self) -> None:
        """Write all panel values back into project.settings.search.

        v0.1.12 — writes both the new (PDF-aligned) fields and the
        legacy fields used by the search algorithms in v0.1.11."""
        s = self.project.settings.search
        # Surface type + method
        if self.rb_non_circular.isChecked():
            s.surface_type = self._SurfaceType.NON_CIRCULAR.value
        else:
            s.surface_type = self._SurfaceType.CIRCULAR.value
        m = self.cb_method.currentData()
        if m is not None:
            s.search_method = m.value

        # ----- Grid Search -----
        s.radius_increment = int(self._g_radius.value())
        s.composite_surfaces = self._g_composite.isChecked()
        s.create_tension_crack_reverse_curvature = self._g_tcrack.isChecked()

        # ----- Slope Search -----
        s.num_surfaces = int(self._sl_num.value())
        s.initial_angle_at_toe_upper_enabled = self._sl_upper_cb.isChecked()
        s.initial_angle_at_toe_upper_deg = self._sl_upper_sb.value()
        s.initial_angle_at_toe_lower_enabled = self._sl_lower_cb.isChecked()
        s.initial_angle_at_toe_lower_deg = self._sl_lower_sb.value()

        # ----- Auto Refine -----
        s.auto_refine_divisions_along_slope = int(self._ar_div_slope.value())
        s.auto_refine_circles_per_division = int(self._ar_circles_per_div.value())
        s.auto_refine_num_iterations = int(self._ar_num_iter.value())
        s.auto_refine_divisions_to_use_pct = self._ar_div_pct.value()
        if self._ar_num_verts is not None:
            s.auto_refine_num_vertices_along_surface = int(self._ar_num_verts.value())

        # ----- Simulated Annealing -----
        s.sa_initial_vertices = int(self._sa_verts.value())
        s.sa_generation_steps = int(self._sa_steps.value())
        s.sa_num_fos_compared_before_stopping = int(self._sa_num_fos.value())
        s.sa_tolerance = self._sa_tol.value()
        s.sa_temperature_coefficient = self._sa_tcoef.value()
        s.sa_convex_only = self._sa_convex.isChecked()

        # ----- Particle Swarm -----
        s.pso_num_particles = int(self._pso_n.value())
        s.pso_num_iterations = int(self._pso_it.value())
        s.pso_multiple_minima = self._pso_multi.isChecked()
        s.pso_niche_radius_pct = self._pso_radius.value()

        # ----- Path Search -----
        s.path_num_surfaces = int(self._p_num.value())
        s.path_initial_angle_at_toe_upper_enabled = self._p_upper_cb.isChecked()
        s.path_initial_angle_at_toe_upper_deg = self._p_upper_sb.value()
        s.path_initial_angle_at_toe_lower_enabled = self._p_lower_cb.isChecked()
        s.path_initial_angle_at_toe_lower_deg = self._p_lower_sb.value()
        s.path_segment_length_manual = self._p_seglen_cb.isChecked()
        s.path_segment_length_value = self._p_seglen.value()
        s.path_convex_only = self._p_convex.isChecked()

        # ----- Block Search -----
        s.block_num_surfaces = int(self._b_num.value())
        s.block_multiple_groups = self._b_multi.isChecked()
        s.block_left_start_angle_deg = self._b_left_start.value()
        s.block_left_end_angle_deg = self._b_left_end.value()
        s.block_right_start_angle_deg = self._b_right_start.value()
        s.block_right_end_angle_deg = self._b_right_end.value()
        s.block_convex_only = self._b_convex.isChecked()
        # v0.1.104 — ONE write for the three synchronised boxes.
        # It used to be three, folded with an OR, which is why the
        # option could be ticked and never cleared.
        s.optimize_enabled = self._b_optimize.isChecked()
        # v0.1.118 — read from its own box. Unticked keeps the single
        # implicit block region the search has always used when nobody has
        # drawn any Block Search objects; ticked says how many points to
        # draw in it. Closes the derivation D07c(b) reported.
        s.block_num_groups = (max(1, int(self._b_groups.value()))
                              if self._b_multi.isChecked() else 3)

        # ----- Filters -----
        s.min_elevation = (
            self.sb_min_elev.value() if self.cb_filter_min_elev.isChecked() else None
        )
        s.min_depth = (
            self.sb_min_depth.value() if self.cb_filter_min_depth.isChecked() else None
        )
        s.min_area = (
            self.sb_min_area.value() if self.cb_filter_min_area.isChecked() else None
        )

        # ----- Weak layer handling (v0.1.121) -----
        s.weak_layer_handling = self.cb_weak.currentData()
        s.weak_layer_max_cases_log2 = int(self.sp_weak_cases.value())
