# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Material properties dialog — polymorphic constitutive-model editor.

Every strength model registered in :mod:`ogr_core.materials.registry`
is available from a combo box. When the user changes the model, the
parameter panel is rebuilt on-the-fly from ``PARAMETERS`` — so newly
added plugins appear automatically.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ogr_core.materials import (
    REGISTRY,
    Material,
    PorePressureType,
    StrengthModel,
)
from ogr_gui.i18n import tr

from .drawdown_strength_dialog import DrawdownStrengthDialog, envelope_summary


# ----------------------------------------------------------------------
class _StrengthParamPanel(QWidget):
    """Dynamically-built parameter editor for the active strength model.

    v0.1.13 — unit-aware. Each parameter's canonical unit (declared in
    ``PARAMETERS``) is mapped to a :class:`Quantity` and the editor shows
    the value in the active project unit system. Conversion happens in
    ``set_model`` (SI → user) and ``get_params`` (user → SI).
    """

    # Map the literal SI unit string declared in builtin_models to the
    # corresponding Quantity. Used for display + conversion only.
    _UNIT_TO_QUANTITY = {
        "kPa":     "pressure",
        "kN/m³":   "unit_weight",
        "kN/m²":   "shear_strength",
        "kN":      "force",
        "kNm":     "moment",
        "deg":     "angle",
        "m":       "length",
        "mm":      "very_small_length",
        "1/m":     "one_over_length",
        "-":       "dimensionless",
        "":        "dimensionless",
    }

    def __init__(self, parent=None, units_obj=None) -> None:
        super().__init__(parent)
        self._form = QFormLayout(self)
        self._editors: dict[str, QDoubleSpinBox] = {}
        self._param_quantity: dict[str, str] = {}  # name → quantity_id
        self._model_cls: type[StrengthModel] | None = None
        self._units_obj = units_obj  # ogr_core.project.units.Units or None

    def set_units(self, units_obj) -> None:
        """Update the active unit system (e.g. project settings changed).
        Repopulates the editors converting their current SI values to
        the new display system."""
        old_si_values = self.get_params() if self._editors else None
        self._units_obj = units_obj
        if self._model_cls is not None:
            self.set_model(self._model_cls, old_si_values)

    def _active_system(self):
        """Return the active UnitSystem (detailed) or None."""
        if self._units_obj is None:
            return None
        try:
            return self._units_obj.get_system()
        except Exception:  # noqa: BLE001
            return None

    def set_model(
        self,
        model_cls: type[StrengthModel],
        current_params: dict | None = None,
    ) -> None:
        """Build editors. ``current_params`` are values in SI (canonical
        units stored on the material)."""
        from ogr_core.units import Quantity
        self._model_cls = model_cls
        # Clear
        while self._form.count():
            item = self._form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._editors.clear()
        self._param_quantity.clear()

        current_params = current_params or {}
        sys_obj = self._active_system()

        for name, (default, unit, description) in model_cls.PARAMETERS.items():
            quantity_id = self._UNIT_TO_QUANTITY.get(unit, "dimensionless")
            self._param_quantity[name] = quantity_id

            # SI value (always)
            si_value = float(current_params.get(name, default))
            # Convert to display
            if sys_obj is not None and quantity_id != "dimensionless":
                try:
                    q = Quantity(quantity_id)
                    user_value = sys_obj.to_user(si_value, q)
                    user_label = sys_obj.label_for(q)
                except (ValueError, KeyError):
                    user_value = si_value
                    user_label = unit if unit != "-" else ""
            else:
                user_value = si_value
                user_label = unit if unit != "-" else ""

            ed = QDoubleSpinBox()
            ed.setRange(-1e12, 1e12)
            ed.setDecimals(4)
            ed.setSuffix(f" {user_label}" if user_label else "")
            ed.setValue(user_value)
            ed.setToolTip(description)
            label = QLabel(f"{name}:")
            label.setToolTip(description)
            self._form.addRow(label, ed)
            self._editors[name] = ed

        if not model_cls.PARAMETERS:
            self._form.addRow(QLabel(tr("(no parameters)")))

        # v0.1.15 — function/table-based models (Shear/Normal Function,
        # Discrete Function, Anisotropic Strength Function) carry a
        # ``points`` list instead of (or in addition to) numeric
        # PARAMETERS. Build a small table editor for them.
        self._table = None
        self._table_kind = None
        mid = getattr(model_cls, "MODEL_ID", "")
        if mid in ("shear_normal_function", "discrete_function"):
            self._build_points_table(
                current_params, columns=["σ'ₙ (kPa)", "τ (kPa)"],
                kind="points",
                default=[(0.0, 5.0), (100.0, 45.0), (300.0, 110.0)],
            )
        elif mid == "anisotropic_strength_function":
            self._build_points_table(
                current_params, columns=["Angle (°)", "c (kPa)", "φ (°)"],
                kind="points3",
                default=[(-90.0, 20.0, 30.0), (0.0, 5.0, 15.0),
                         (90.0, 20.0, 30.0)],
            )

    def _build_points_table(self, current_params, columns, kind, default):
        """Build an editable table for function-based models."""
        from PySide6.QtWidgets import (
            QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QWidget,
        )
        pts = None
        if current_params and "points" in current_params:
            pts = current_params["points"]
        if not pts:
            pts = default
        ncol = len(columns)
        tbl = QTableWidget(len(pts), ncol)
        tbl.setHorizontalHeaderLabels(columns)
        tbl.horizontalHeader().setStretchLastSection(True)
        for r, row in enumerate(pts):
            for c in range(ncol):
                tbl.setItem(r, c, QTableWidgetItem(f"{row[c]:.3f}"))
        self._form.addRow(QLabel(tr("Function points:")), tbl)
        # Add/remove buttons
        btns = QWidget()
        hl = QHBoxLayout(btns)
        hl.setContentsMargins(0, 0, 0, 0)
        b_add = QPushButton(tr("+ Row"))
        b_del = QPushButton(tr("− Row"))

        def _add():
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c in range(ncol):
                tbl.setItem(r, c, QTableWidgetItem("0.0"))

        def _del():
            cur = tbl.currentRow()
            if cur >= 0:
                tbl.removeRow(cur)
        b_add.clicked.connect(_add)
        b_del.clicked.connect(_del)
        hl.addWidget(b_add)
        hl.addWidget(b_del)
        hl.addStretch()
        self._form.addRow("", btns)
        self._table = tbl
        self._table_kind = kind
        self._table_ncol = ncol

    def get_params(self) -> dict:
        """Return the editor values converted to SI (the storage unit)."""
        from ogr_core.units import Quantity
        sys_obj = self._active_system()
        out: dict = {}
        for k, ed in self._editors.items():
            user_value = ed.value()
            quantity_id = self._param_quantity.get(k, "dimensionless")
            if sys_obj is not None and quantity_id != "dimensionless":
                try:
                    q = Quantity(quantity_id)
                    out[k] = sys_obj.from_user(user_value, q)
                    continue
                except (ValueError, KeyError):
                    pass
            out[k] = user_value
        # v0.1.15 — read the function table if present
        tbl = getattr(self, "_table", None)
        if tbl is not None:
            ncol = self._table_ncol
            pts = []
            for r in range(tbl.rowCount()):
                try:
                    vals = tuple(
                        float(tbl.item(r, c).text()) for c in range(ncol)
                    )
                    pts.append(vals)
                except (ValueError, AttributeError):
                    continue
            out["points"] = pts
        return out

    def current_model(self) -> type[StrengthModel] | None:
        return self._model_cls


# ----------------------------------------------------------------------
class MaterialPropertiesDialog(QDialog):
    """Editor for the full list of materials in a project."""

    def __init__(
        self,
        materials: list[Material],
        parent=None,
        units_obj=None,
        gw_method: str = "none",
        has_water_table: bool = False,
        water_surfaces: list[tuple[str, str]] | None = None,
        rapid_drawdown: bool = False,
        drawdown_method: str = "b_bar",
        excess_pore_pressure: bool = False,
    ) -> None:
        super().__init__(parent)
        # v0.1.62 — (boundary id, translated label) for every water table
        # and piezometric line in the project. Passed in rather than read
        # from a Project so this dialog keeps knowing nothing about one,
        # the same way ``has_water_table`` is a derived flag.
        self._water_surfaces = list(water_surfaces or [])
        self._rapid_drawdown = bool(rapid_drawdown)
        # v0.1.72 — which of the four procedures is configured. B̄ and the
        # undrained envelope belong to different ones, so the dialog needs
        # to know which before it can show only the relevant field.
        self._drawdown_method = str(drawdown_method or "b_bar")
        # v0.1.75 — the OTHER advanced groundwater option. Mutually
        # exclusive with the drawdown, so at most one of the two
        # groups is ever on screen.
        self._excess_pore_pressure = bool(excess_pore_pressure)
        # v0.1.29 — the unsaturated-strength fields are only meaningful
        # (and only shown) when the groundwater method is an FEA, since
        # only then can pore pressures be negative.
        self._gw_method = str(gw_method)
        # v0.1.60 — a saturated unit weight can only mean something if a
        # water table exists to separate the saturated zone from the rest.
        self._has_water_table = bool(has_water_table)
        self.setWindowTitle(tr("Define Materials..."))
        self.resize(720, 500)
        # v0.1.60 — work on deep copies, so the user can move freely
        # between materials and still have Cancel discard everything. A
        # shallow ``list(materials)`` shared the Material instances with
        # the project, which made Cancel a no-op for field edits.
        # ``deepcopy`` rather than ``from_dict(to_dict())`` because it also
        # preserves each material's ``id`` (region assignments key off it)
        # and any attribute set outside the dataclass, such as ``b_bar``.
        self.materials = [copy.deepcopy(m) for m in materials]
        self._current_row = -1
        self._units_obj = units_obj  # ogr_core.project.units.Units

        layout = QHBoxLayout(self)

        # Left: material list
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMaximumWidth(200)
        for m in self.materials:
            self._append_item(m)
        self.list.currentRowChanged.connect(self._on_select)
        btn_add = QPushButton("+ " + tr("Name"))
        btn_add.setText(tr("+ Add"))
        btn_add.clicked.connect(self._add_material)
        btn_del = QPushButton(tr("− Remove"))
        btn_del.clicked.connect(self._remove_material)
        left.addWidget(self.list, 1)
        hb = QHBoxLayout()
        hb.addWidget(btn_add)
        hb.addWidget(btn_del)
        left.addLayout(hb)
        layout.addLayout(left)

        # Right: editor form
        right = QVBoxLayout()

        # Identity group
        gen_grp = QGroupBox(tr("General"))
        gen_form = QFormLayout(gen_grp)
        self._general_form = gen_form
        self.ed_name = QLineEdit()
        self.btn_color = QPushButton()
        self.btn_color.setFixedWidth(60)
        self.btn_color.clicked.connect(self._pick_color)
        self._color_hex = "#d4a373"
        self._update_color_button()
        # γ and γ_sat: display in active system, store internally in kN/m³.
        gamma_label, gamma_factor = self._unit_weight_label_factor()
        self._gamma_label = gamma_label
        self._gamma_factor = gamma_factor
        self.dsp_gamma = QDoubleSpinBox()
        self.dsp_gamma.setRange(0.0, 1e6); self.dsp_gamma.setDecimals(4)
        self.dsp_gamma.setSuffix(f" {gamma_label}")
        self.dsp_gamma_sat = QDoubleSpinBox()
        self.dsp_gamma_sat.setRange(0.0, 1e6); self.dsp_gamma_sat.setDecimals(4)
        self.dsp_gamma_sat.setSuffix(f" {gamma_label}")
        # v0.1.60 — the saturated unit weight is opt-in, and the option is
        # only offered when a water table exists: without one there is no
        # boundary between the saturated and unsaturated zones, so the
        # value could not be applied anywhere.
        self.chk_gamma_sat = QCheckBox(tr("Saturated Unit Weight") + ":")
        self.chk_gamma_sat.setEnabled(self._has_water_table)
        self.chk_gamma_sat.setToolTip(
            tr("Different unit weights above and below the water table. "
               "Requires a water table in the model.")
            if not self._has_water_table else
            tr("Saturated bulk unit weight, used below the water table. "
               "It is not the submerged (buoyant) unit weight, so it "
               "should be greater than the unit weight above.")
        )
        self.chk_gamma_sat.toggled.connect(self._on_gamma_sat_toggled)
        # Non-modal warning: the saturated BULK unit weight must exceed the
        # unsaturated one. The value is still accepted — this only says so.
        self.lbl_gamma_sat_warn = QLabel(
            tr("The saturated unit weight should be greater than the "
               "unit weight above the water table."))
        self.lbl_gamma_sat_warn.setStyleSheet("color: #b00020;")
        self.lbl_gamma_sat_warn.setWordWrap(True)
        self.lbl_gamma_sat_warn.setVisible(False)
        self.dsp_gamma.valueChanged.connect(self._refresh_gamma_warning)
        self.dsp_gamma_sat.valueChanged.connect(self._refresh_gamma_warning)
        gen_form.addRow(tr("Name") + ":", self.ed_name)
        gen_form.addRow(tr("Color") + ":", self.btn_color)
        gen_form.addRow(tr("Unit Weight") + ":", self.dsp_gamma)
        gen_form.addRow(self.chk_gamma_sat, self.dsp_gamma_sat)
        gen_form.addRow("", self.lbl_gamma_sat_warn)

        # v0.1.29 — Unsaturated shear strength (extended Mohr-Coulomb).
        # The reference only exposes these when the groundwater method is
        # a finite-element analysis, because only then can the pore
        # pressures be negative. Both default to 0, so matric suction
        # contributes nothing unless the user opts in.
        from PySide6.QtWidgets import QDoubleSpinBox as _DSB
        self.dsp_phi_b = _DSB()
        self.dsp_phi_b.setDecimals(2)
        self.dsp_phi_b.setRange(0.0, 89.0)
        self.dsp_phi_b.setSingleStep(1.0)
        self.dsp_phi_b.setToolTip(
            "Unsaturated shear strength angle. 0 means matric suction "
            "does not contribute to strength (conservative default).")
        self.dsp_aev = _DSB()
        self.dsp_aev.setDecimals(3)
        self.dsp_aev.setRange(0.0, 1e7)
        self.dsp_aev.setSingleStep(5.0)
        self.dsp_aev.setToolTip(
            "Air entry value: matric suction below which the saturated "
            "friction angle still governs (bilinear envelope).")
        self._row_phi_b = gen_form.rowCount()
        gen_form.addRow(tr("Unsaturated Shear Strength Angle") + ":",
                        self.dsp_phi_b)
        gen_form.addRow(tr("Air Entry Value") + ":", self.dsp_aev)
        self._unsat_widgets = [self.dsp_phi_b, self.dsp_aev]
        self._apply_unsaturated_visibility()
        right.addWidget(gen_grp)

        # Strength group
        str_grp = QGroupBox(tr("Strength Type"))
        str_layout = QVBoxLayout(str_grp)
        # Top row: dropdown + formula label
        top_row = QHBoxLayout()
        self.cbo_strength = QComboBox()
        for mid, cls in REGISTRY.all().items():
            self.cbo_strength.addItem(cls.DISPLAY_NAME, mid)
        self.cbo_strength.currentIndexChanged.connect(self._on_strength_changed)
        top_row.addWidget(self.cbo_strength)
        # Formula label, shown next to the dropdown
        self.lbl_strength_formula = QLabel("")
        self.lbl_strength_formula.setStyleSheet(
            "color: #444; font-style: italic; padding-left: 12px;"
        )
        self.lbl_strength_formula.setMinimumWidth(220)
        top_row.addWidget(self.lbl_strength_formula, stretch=1)
        # v0.1.57 — the GSI calculator, shown only for the Generalised
        # Hoek-Brown criterion, whose mb, s and a are DERIVED quantities.
        self.btn_gsi = QPushButton(tr("GSI..."))
        self.btn_gsi.setToolTip(tr(
            "Calculate mb, s and a from GSI, the intact rock constant mi "
            "and the disturbance factor D."))
        self.btn_gsi.clicked.connect(self._open_parameter_calculator)
        self.btn_gsi.setVisible(False)
        top_row.addWidget(self.btn_gsi)
        str_layout.addLayout(top_row)
        self.param_panel = _StrengthParamPanel(units_obj=self._units_obj)
        str_layout.addWidget(self.param_panel)
        right.addWidget(str_grp)

        # Water parameters — named after what the reference calls this
        # section. "Pore pressure" is the quantity; these are the inputs
        # that determine it, and only some of them apply at a time.
        pp_grp = QGroupBox(tr("Water Parameters"))
        self.grp_water = pp_grp
        pp_form = QFormLayout(pp_grp)
        self._water_form = pp_form
        self.cbo_pp = QComboBox()
        for t in PorePressureType:
            self.cbo_pp.addItem(t.value, t)
        self.dsp_ru = QDoubleSpinBox(); self.dsp_ru.setRange(0.0, 1.0); self.dsp_ru.setDecimals(3)
        self.dsp_u = QDoubleSpinBox(); self.dsp_u.setRange(0.0, 1e6); self.dsp_u.setDecimals(2); self.dsp_u.setSuffix(" kPa")

        # v0.1.62 — which water surface this material takes its pore
        # pressure from. The field existed and was honoured by the solver
        # since v0.1.7, but nothing in the interface ever wrote it, so
        # every project silently fell back to "the first one of that type"
        # and a second piezometric line was unreachable.
        self.cbo_water_surface = QComboBox()
        self.cbo_water_surface.addItem(tr("(first of this type)"), None)
        for wid, label in self._water_surfaces:
            self.cbo_water_surface.addItem(label, wid)
        self.cbo_water_surface.setToolTip(tr(
            "Water surface this material takes its pore pressure from. "
            "It must span every abscissa the material occupies."))

        # Hu: unchecked means "use the project default", which is why this
        # is a checkbox and not a spinbox with a magic value — the same
        # pattern the saturated unit weight above already uses.
        self.chk_hu = QCheckBox(tr("Hu coefficient") + ":")
        self.dsp_hu = QDoubleSpinBox()
        self.dsp_hu.setRange(0.0, 1.0); self.dsp_hu.setDecimals(3)
        self.dsp_hu.setValue(1.0)
        self.chk_hu.setToolTip(tr(
            "u = γw · Hu · h, with h the vertical distance up to the "
            "water surface. Unchecked, the project default applies."))
        self.chk_auto_hu = QCheckBox(tr("Auto Hu (cos²α from the water-surface slope)"))
        self.chk_auto_hu.setToolTip(tr(
            "Assumes the equipotential through the slice base is straight, "
            "which is exact only for an infinite slope."))

        # v0.1.72 — the per-material way out of a water pressure grid.
        # Only shown when the project actually uses one, because that is
        # the only time it decides anything.
        self.chk_use_grid = QCheckBox(tr("Use the water pressure grid"))
        self.chk_use_grid.setChecked(True)
        self.chk_use_grid.setToolTip(tr(
            "With the grid off, this material takes its pore pressure "
            "from its own water parameters instead of the grid."))

        pp_form.addRow(tr("Type:"), self.cbo_pp)
        pp_form.addRow("", self.chk_use_grid)
        pp_form.addRow(tr("Water Surface:"), self.cbo_water_surface)
        pp_form.addRow(self.chk_hu, self.dsp_hu)
        pp_form.addRow("", self.chk_auto_hu)
        pp_form.addRow(tr("Ru coefficient:"), self.dsp_ru)
        pp_form.addRow(tr("Constant u:"), self.dsp_u)
        right.addWidget(pp_grp)

        # v0.1.62 — Rapid drawdown parameters. B̄ used to be read off the
        # material with getattr, defaulting to 1.0, which made EVERY
        # material undrained without anyone choosing it.
        # v0.1.72 — the whole group is gone unless a rapid drawdown is
        # configured. It used to be permanently on screen and merely
        # greyed out, which cost every other user a quarter of the dialog
        # for a parameter almost nobody sets. Hiding it is not losing it:
        # the analysis that needs it is what brings it back, which is the
        # same route the reference takes.
        rd_grp = QGroupBox(tr("Rapid Drawdown Parameters"))
        self.grp_drawdown = rd_grp
        rd_form = QFormLayout(rd_grp)
        self._drawdown_form = rd_form
        self.chk_undrained = QCheckBox(tr("Undrained Behaviour"))
        self.dsp_b_bar = QDoubleSpinBox()
        self.dsp_b_bar.setRange(0.0, 5.0); self.dsp_b_bar.setDecimals(3)
        self.dsp_b_bar.setToolTip(tr(
            "Skempton's B̄: Δu = B̄ · Δσv. Only a material that behaves "
            "undrained retains excess pore pressure after drawdown."))
        # v0.1.68 — the undrained envelope the multi-stage procedures need.
        # v0.1.72 — it moved behind this button, where the reference keeps
        # it. The summary beside the button means the value is still
        # readable without opening anything.
        self.btn_envelope = QPushButton(tr("Define Strength..."))
        self.btn_envelope.clicked.connect(self._open_drawdown_strength)
        self.btn_envelope.setToolTip(tr(
            "Undrained envelope from isotropically consolidated undrained "
            "tests. Needed by the multi-stage drawdown procedures."))
        self.lbl_envelope = QLabel("")
        self.lbl_envelope.setStyleSheet("color: #555; font-style: italic;")
        # The envelope being edited for the material on screen. Staged the
        # same way ``_color_hex`` is: ``_load`` fills it, ``_store`` writes
        # it back, so Cancel still discards everything.
        self._envelope = None

        rd_form.addRow("", self.chk_undrained)
        rd_form.addRow(tr("B-bar:"), self.dsp_b_bar)
        rd_form.addRow(self.btn_envelope, self.lbl_envelope)
        right.addWidget(rd_grp)

        # v0.1.75 — Excess pore pressure from undrained LOADING, which is
        # a different analysis from the drawdown above and exclusive with
        # it, so it gets its own group with its own gate. Deliberately
        # held back in v0.1.72, when its engine did not exist: an
        # interface for a calculation nobody performs is the fault the
        # partial factors had for five versions.
        ex_grp = QGroupBox(tr("Excess Pore Pressure"))
        self.grp_excess = ex_grp
        ex_form = QFormLayout(ex_grp)
        self.dsp_b_bar_excess = QDoubleSpinBox()
        self.dsp_b_bar_excess.setRange(0.0, 5.0)
        self.dsp_b_bar_excess.setDecimals(3)
        self.dsp_b_bar_excess.setToolTip(tr(
            "Skempton's B̄: Δu = B̄ · Δσv. Use 0 for a free-draining "
            "material, which then develops no excess however much load "
            "arrives."))
        self.chk_weight_excess = QCheckBox(
            tr("Material weight creates excess pore pressure"))
        self.chk_weight_excess.setToolTip(tr(
            "This material's weight loads the materials BENEATH it. It "
            "is a separate question from whether this material develops "
            "excess itself, which is its own B-bar: an embankment over a "
            "clay foundation usually has this on and B-bar = 0."))
        ex_form.addRow(tr("B-bar:"), self.dsp_b_bar_excess)
        ex_form.addRow("", self.chk_weight_excess)
        right.addWidget(ex_grp)

        self.cbo_pp.currentIndexChanged.connect(self._refresh_water_parameters)
        self.chk_use_grid.toggled.connect(self._refresh_water_parameters)
        self.chk_hu.toggled.connect(self._refresh_water_parameters)
        self.chk_auto_hu.toggled.connect(self._refresh_water_parameters)
        self.chk_undrained.toggled.connect(self._refresh_water_parameters)
        self.cbo_strength.currentIndexChanged.connect(
            self._refresh_water_parameters)

        right.addStretch(1)
        layout.addLayout(right, 1)

        # Buttons — v0.1.60: no Apply. Edits are committed to the working
        # copy as soon as the user moves to another material, so Apply had
        # nothing left to do; OK confirms the whole list, Cancel drops it.
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._ok)
        self.buttons.rejected.connect(self.reject)
        right.addWidget(self.buttons)

        if self.materials:
            self.list.setCurrentRow(0)
        else:
            self._set_editor_enabled(False)

    # ------------------------------------------------------------------
    def _append_item(self, m: Material) -> None:
        item = QListWidgetItem(m.name)
        item.setData(Qt.UserRole, m.id)
        item.setForeground(QColor(m.color))
        self.list.addItem(item)

    def _set_editor_enabled(self, on: bool) -> None:
        for w in (self.ed_name, self.btn_color, self.dsp_gamma,
                  self.cbo_strength, self.cbo_pp, self.param_panel):
            w.setEnabled(on)
        # γsat has its own gate on top of this one: the checkbox needs a
        # water table, and the spinbox needs the checkbox.
        self.chk_gamma_sat.setEnabled(on and self._has_water_table)
        self.dsp_gamma_sat.setEnabled(
            on and self._has_water_table and self.chk_gamma_sat.isChecked())
        if not on:
            self.lbl_gamma_sat_warn.setVisible(False)
        self._editor_on = on
        self._refresh_water_parameters()

    # ------------------------------------------------------------------
    # Strength models for which the reference disables water parameters
    # outright: none of the three reads a pore pressure, so offering the
    # inputs would suggest an influence that does not exist (rule 7).
    _NO_WATER_STRENGTHS = ("undrained", "no_strength", "infinite_strength")

    @staticmethod
    def _set_row_visible(form: QFormLayout, field: QWidget,
                         visible: bool) -> None:
        """Show or hide a form row, label included.

        ``QFormLayout.setRowVisible`` only arrived in Qt 6.4, and
        ``labelForField`` returns whatever was passed as the row's first
        element — a QLabel for a string, or the widget itself when the row
        was built from two widgets — so this works for both shapes.
        """
        label = form.labelForField(field)
        if label is not None:
            label.setVisible(visible)
        field.setVisible(visible)

    def _refresh_water_parameters(self, *_args) -> None:
        """Show only the water parameters that decide something.

        Two layers, and they are different on purpose. What the PROJECT
        makes irrelevant is HIDDEN — a grid switch in a project with no
        grid, or the whole group under a finite-element analysis, where
        the reference replaces it with the unsaturated parameters. What
        the MATERIAL's own choice makes irrelevant is merely DISABLED, so
        that changing the type back shows the value that was there.
        """
        on = getattr(self, "_editor_on", True)
        ppt = self.cbo_pp.currentData()
        uses_surface = ppt in (PorePressureType.WATER_TABLE,
                               PorePressureType.PIEZO_LINE)

        # A finite-element analysis supplies the pore pressures itself;
        # the material contributes phi_b and the air entry value instead,
        # which live in the General group and have their own gate.
        fea = self._gw_method in ("fea_steady", "fea_transient")
        self.grp_water.setVisible(not fea)

        # The grid switch decides nothing unless the project uses a grid.
        grid = self._gw_method in ("grid_total_head", "grid_pressure_head",
                                   "grid_pore_pressure")
        self._set_row_visible(self._water_form, self.chk_use_grid, grid)
        self.chk_use_grid.setEnabled(on)
        # With the grid governing, the material's own model is what
        # applies only after switching the grid off.
        own_model = on and (not grid or not self.chk_use_grid.isChecked())

        # Rule of the reference: these three strength models read no pore
        # pressure at all, so the whole group is greyed out.
        mid = self.cbo_strength.currentData()
        if mid in self._NO_WATER_STRENGTHS:
            own_model = False
        self.cbo_pp.setEnabled(own_model)

        self.cbo_water_surface.setEnabled(own_model and uses_surface)
        self.chk_auto_hu.setEnabled(own_model and uses_surface)
        self.chk_hu.setEnabled(
            own_model and uses_surface and not self.chk_auto_hu.isChecked())
        self.dsp_hu.setEnabled(
            own_model and uses_surface
            and not self.chk_auto_hu.isChecked()
            and self.chk_hu.isChecked())
        self.dsp_ru.setEnabled(
            own_model and ppt == PorePressureType.RU_COEFFICIENT)
        self.dsp_u.setEnabled(own_model and ppt == PorePressureType.CONSTANT)

        self._refresh_drawdown_group()
        self._refresh_excess_group()

    def _refresh_excess_group(self) -> None:
        """Present only when the project runs the B-bar loading analysis.

        The same rule the drawdown group follows, and for the same
        reason: the analysis that needs these fields is what brings them
        back, and it is switched on somewhere else entirely.
        """
        on = getattr(self, "_editor_on", True)
        self.grp_excess.setVisible(self._excess_pore_pressure)
        for wgt in (self.dsp_b_bar_excess, self.chk_weight_excess):
            wgt.setEnabled(on and self._excess_pore_pressure)

    def _refresh_drawdown_group(self) -> None:
        """Show the drawdown parameters the chosen procedure asks for.

        B̄ and the undrained envelope are alternatives, not companions:
        the effective-stress procedure needs the first and the three
        multi-stage ones need the second. Showing both at once was
        showing every user at least one field their analysis ignores.
        """
        on = getattr(self, "_editor_on", True)
        self.grp_drawdown.setVisible(self._rapid_drawdown)
        if not self._rapid_drawdown:
            # Hidden AND disabled. Hiding alone would be enough for the
            # eye, but the guarantee being made is that B̄ cannot be set
            # without a drawdown run, and that is a statement about the
            # widgets, not about what happens to be on screen.
            for wgt in (self.chk_undrained, self.dsp_b_bar,
                        self.btn_envelope):
                wgt.setEnabled(False)
            return
        undrained = self.chk_undrained.isChecked()
        self.chk_undrained.setEnabled(on)
        multistage = self._drawdown_method != "b_bar"
        self._set_row_visible(self._drawdown_form, self.dsp_b_bar,
                              not multistage)
        self._set_row_visible(self._drawdown_form, self.lbl_envelope,
                              multistage)
        self.dsp_b_bar.setEnabled(on and undrained)
        self.btn_envelope.setEnabled(on and undrained)
        self.lbl_envelope.setText(envelope_summary(self._envelope))

    def _open_drawdown_strength(self) -> None:
        """Edit the undrained envelope of the material on screen."""
        dlg = DrawdownStrengthDialog(self._envelope, self)
        if dlg.exec():
            self._envelope = dlg.envelope()
            self._refresh_drawdown_group()

    def _current_material(self) -> Material | None:
        row = self.list.currentRow()
        if 0 <= row < len(self.materials):
            return self.materials[row]
        return None

    # ------------------------------------------------------------------
    def _on_select(self, row: int) -> None:
        """Commit the material being left, then load the new one.

        v0.1.60 — the commit half used to be missing, so any edit was
        silently discarded unless the user pressed Apply before changing
        the selection.
        """
        if self._current_row >= 0 and self._current_row != row:
            self._store(self._current_row)
        self._current_row = row if 0 <= row < len(self.materials) else -1
        if self._current_row < 0:
            self._set_editor_enabled(False)
            return
        self._set_editor_enabled(True)
        self._load(self._current_row)

    def _load(self, row: int) -> None:
        """Populate the editor widgets from ``self.materials[row]``."""
        m = self.materials[row]
        self.ed_name.setText(m.name)
        self._color_hex = m.color
        self._update_color_button()
        self._populate_gamma(m)
        self.dsp_phi_b.setValue(getattr(m, "phi_b", 0.0) or 0.0)
        self.dsp_aev.setValue(getattr(m, "air_entry_value", 0.0) or 0.0)

        idx = self.cbo_strength.findData(m.strength.MODEL_ID)
        if idx >= 0:
            self.cbo_strength.setCurrentIndex(idx)
        self.param_panel.set_model(type(m.strength), m.strength.params)
        # v0.1.15 — for function/table-based models, also pass the
        # ``points`` so the table editor pre-fills.
        if hasattr(m.strength, "points") and self.param_panel._table is not None:
            # Rebuild with points included
            params_with_pts = dict(m.strength.params)
            params_with_pts["points"] = list(m.strength.points)
            self.param_panel.set_model(type(m.strength), params_with_pts)

        idx = self.cbo_pp.findData(m.pore_pressure)
        if idx >= 0:
            self.cbo_pp.setCurrentIndex(idx)
        self.dsp_ru.setValue(m.ru)
        self.dsp_u.setValue(m.constant_u)

        # v0.1.62 — water parameters. Signals are blocked while loading so
        # that populating the widgets cannot write back into the material
        # that is only being displayed.
        _blocked = (self.cbo_water_surface, self.chk_hu, self.chk_auto_hu,
                    self.chk_undrained, self.chk_use_grid,
                    self.chk_weight_excess)
        for w in _blocked:
            w.blockSignals(True)
        idx = self.cbo_water_surface.findData(m.water_surface_id)
        self.cbo_water_surface.setCurrentIndex(max(0, idx))
        self.chk_auto_hu.setChecked(bool(m.auto_hu))
        self.chk_hu.setChecked(m.hu is not None)
        self.dsp_hu.setValue(1.0 if m.hu is None else float(m.hu))
        self.chk_use_grid.setChecked(bool(getattr(m, "use_grid", True)))
        self.chk_undrained.setChecked(bool(m.undrained_behaviour))
        self.dsp_b_bar.setValue(float(m.b_bar))
        # Same B̄ field, shown in whichever group is active.
        self.dsp_b_bar_excess.setValue(float(m.b_bar))
        self.chk_weight_excess.setChecked(
            bool(getattr(m, "weight_creates_excess", False)))
        # v0.1.72 — the envelope is staged rather than shown, because its
        # editor is a dialog of its own now.
        self._envelope = getattr(m, "drawdown_envelope", None)
        for w in _blocked:
            w.blockSignals(False)
        self._refresh_water_parameters()

    # Formula text shown next to each strength type — these mirror the
    # equations displayed in Slide's Strength Parameters PDF.
    _FORMULA_TEXT = {
        "mohr_coulomb":         "τ = c′ + σ′ₙ · tan(φ′)",
        "undrained":            "τ = c",
        "no_strength":          "τ = 0",
        "infinite_strength":    "τ = ∞",
        "hoek_brown_classic":   "σ′₁ = σ′₃ + σ_ci · √(m·σ′₃/σ_ci + s)",
        "hoek_brown":           "σ′₁ = σ′₃ + σ_ci · ((m_b·σ′₃/σ_ci + s)^a)",
        "power_curve":          "τ = c + a·(σ′ₙ + d)^b + σ′ₙ · tan(W)",
        "hyperbolic":           "τ = c_∞·σ′ₙ·tan(φ_0) / (c_∞ + σ′ₙ·tan(φ_0))",
        "vertical_stress_ratio":"τ = K · σ′_v",
        # v0.1.15 — new Slide2 strength models
        "barton_bandis":        "τ = σ′ₙ · tan(φ_r + JRC·log₁₀(JCS/σ′ₙ))",
        "drained_undrained":    "τ = min(c′+σ′ₙ·tanφ′,  c′+σ_t·tanφ′)",
        "anisotropic_linear":   "(c, φ) vary linearly with angle to bedding",
        "shear_normal_function":"τ = f(σ′ₙ)  (piecewise-linear table)",
        "discrete_function":    "τ = f(σ′ₙ)  (step function table)",
        "shansep":              "s_u = σ′_v · S · OCR^m",
        "anisotropic_strength_function":
                                "(c, φ) = f(base angle)  (table)",
        "generalized_anisotropic":
                                "model assigned per base-angle range",
        "snowden_anisotropic_linear":
                                "(c, φ) vary by cosine with angle to bedding",
    }

    def _unit_weight_label_factor(self) -> tuple[str, float]:
        """Return (display_label, kN/m³ → user factor) for the active
        unit system. Defaults to ('kN/m³', 1.0) if no units_obj."""
        if self._units_obj is None:
            return "kN/m³", 1.0
        try:
            from ogr_core.units import Quantity
            sys_obj = self._units_obj.get_system()
            return (
                sys_obj.label_for(Quantity.UNIT_WEIGHT),
                sys_obj.factors[Quantity.UNIT_WEIGHT.value],
            )
        except Exception:  # noqa: BLE001
            return "kN/m³", 1.0

    def _populate_gamma(self, mat) -> None:
        """Set the γ / γ_sat controls from the material (stored in SI).

        Signals are blocked while repopulating: the spinboxes drive the
        γ_sat warning and the checkbox drives the spinbox's enabled state,
        and neither should fire for values that are merely being loaded.
        """
        gamma_si = mat.unit_weight
        gamma_sat_si = mat.sat_unit_weight
        for wgt, value in ((self.dsp_gamma, gamma_si * self._gamma_factor),
                           (self.dsp_gamma_sat,
                            gamma_sat_si * self._gamma_factor)):
            wgt.blockSignals(True)
            wgt.setValue(value)
            wgt.blockSignals(False)
        self.chk_gamma_sat.blockSignals(True)
        self.chk_gamma_sat.setChecked(bool(mat.use_sat_unit_weight))
        self.chk_gamma_sat.blockSignals(False)
        self.dsp_gamma_sat.setEnabled(
            self._has_water_table and self.chk_gamma_sat.isChecked())
        self._refresh_gamma_warning()

    def _read_gamma(self) -> tuple[float, float, bool]:
        """Read γ, γ_sat (converted to SI) and the γ_sat opt-in flag."""
        f = self._gamma_factor or 1.0
        gamma_si = self.dsp_gamma.value() / f
        gamma_sat_si = self.dsp_gamma_sat.value() / f
        return gamma_si, gamma_sat_si, self.chk_gamma_sat.isChecked()

    def _on_gamma_sat_toggled(self, checked: bool) -> None:
        self.dsp_gamma_sat.setEnabled(self._has_water_table and checked)
        self._refresh_gamma_warning()

    def _refresh_gamma_warning(self) -> None:
        """Warn, without blocking, when γ_sat ≤ γ.

        γ_sat is the saturated BULK unit weight, not the submerged one, so
        it must exceed the weight above the water table. The value is left
        as typed — this only makes the inconsistency visible.
        """
        show = (self.chk_gamma_sat.isChecked()
                and self._has_water_table
                and self.dsp_gamma_sat.value() < self.dsp_gamma.value())
        self.lbl_gamma_sat_warn.setVisible(show)

    def _on_strength_changed(self, _) -> None:
        mid = self.cbo_strength.currentData()
        if not mid:
            return
        cls = REGISTRY.get(mid)
        self.param_panel.set_model(cls)
        # Update formula label
        self.lbl_strength_formula.setText(self._FORMULA_TEXT.get(mid, ""))
        # v0.1.57 — the GSI calculator only makes sense for the
        # Generalised Hoek-Brown criterion, whose mb, s and a are derived
        # quantities rather than things to be typed from memory.
        btn = getattr(self, "btn_gsi", None)
        if btn is not None:
            btn.setVisible(mid == "hoek_brown")

    def _open_parameter_calculator(self) -> None:
        """Derive mb, s and a from GSI, mi and D."""
        from .parameter_calculator_dialog import ParameterCalculatorDialog

        dlg = ParameterCalculatorDialog(self)
        if not dlg.exec():
            return
        result = dlg.result_params
        if result is None:
            return
        panel = self.param_panel
        for key, value in (("mb", result.mb), ("s", result.s),
                           ("a", result.a)):
            widget = getattr(panel, "_widgets", {}).get(key)
            if widget is not None and hasattr(widget, "setValue"):
                widget.setValue(float(value))

    def _pick_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._color_hex), self, tr("Color"))
        if c.isValid():
            self._color_hex = c.name()
            self._update_color_button()

    def _update_color_button(self) -> None:
        self.btn_color.setStyleSheet(f"background:{self._color_hex}; border:1px solid #777;")
        self.btn_color.setText("")

    # ------------------------------------------------------------------
    def _store(self, row: int) -> None:
        """Write the editor widgets back into ``self.materials[row]``."""
        if not (0 <= row < len(self.materials)):
            return
        m = self.materials[row]
        m.name = self.ed_name.text().strip() or m.name
        m.color = self._color_hex
        # γ and γ_sat: convert from displayed user-units back to SI (kN/m³)
        m.unit_weight, m.sat_unit_weight, m.use_sat_unit_weight = \
            self._read_gamma()
        m.phi_b = self.dsp_phi_b.value()
        m.air_entry_value = self.dsp_aev.value()

        mid = self.cbo_strength.currentData()
        cls = REGISTRY.get(mid)
        m.strength = cls(**self.param_panel.get_params())

        m.pore_pressure = self.cbo_pp.currentData()
        m.ru = self.dsp_ru.value()
        m.constant_u = self.dsp_u.value()

        # v0.1.62 — water parameters
        m.water_surface_id = self.cbo_water_surface.currentData()
        m.auto_hu = self.chk_auto_hu.isChecked()
        m.hu = self.dsp_hu.value() if self.chk_hu.isChecked() else None
        m.use_grid = self.chk_use_grid.isChecked()
        m.undrained_behaviour = self.chk_undrained.isChecked()
        # B̄ is ONE property of the material, shown in the group the
        # active analysis owns; whichever is on screen is the one
        # that writes it.
        m.b_bar = (self.dsp_b_bar_excess.value()
                   if self._excess_pore_pressure
                   else self.dsp_b_bar.value())
        m.weight_creates_excess = self.chk_weight_excess.isChecked()
        m.drawdown_envelope = self._envelope

        # Refresh list item
        item = self.list.item(row)
        if item is not None:
            item.setText(m.name)
            item.setForeground(QColor(m.color))

    def _ok(self) -> None:
        self._store(self._current_row)
        self.accept()

    # ------------------------------------------------------------------
    def _add_material(self) -> None:
        from ogr_core.materials import MohrCoulomb  # lazy
        # Commit whatever is on screen first: adding a material moves the
        # selection, which would otherwise drop the pending edits.
        self._store(self._current_row)
        m = Material(
            name=f"Material {len(self.materials) + 1}",
            strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        )
        self.materials.append(m)
        self._append_item(m)
        self.list.setCurrentRow(len(self.materials) - 1)

    def _remove_material(self) -> None:
        row = self.list.currentRow()
        if 0 <= row < len(self.materials):
            # The row about to disappear must not be committed afterwards.
            self._current_row = -1
            del self.materials[row]
            self.list.takeItem(row)
            self._on_select(self.list.currentRow())

    # ------------------------------------------------------------------
    def result_materials(self) -> list[Material]:
        return list(self.materials)

    # ------------------------------------------------------------------
    def _apply_unsaturated_visibility(self) -> None:
        """Show the unsaturated-strength fields only when the groundwater
        method is a finite-element analysis, as the reference does.

        v0.1.72 — the LABELS used to stay behind. The old code looked up
        ``wgt.parentWidget()``, which is the group box rather than the
        label, and then hid the spinbox again; the result was two captions
        floating over nothing. The form layout knows where its labels are,
        so it is the one asked.
        """
        method = getattr(self, "_gw_method", "none")
        show = method in ("fea_steady", "fea_transient")
        form = getattr(self, "_general_form", None)
        for wgt in getattr(self, "_unsat_widgets", []):
            wgt.setEnabled(show)
            if form is not None:
                self._set_row_visible(form, wgt, show)
            else:
                wgt.setVisible(show)
        return show
