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

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
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
    ) -> None:
        super().__init__(parent)
        # v0.1.29 — the unsaturated-strength fields are only meaningful
        # (and only shown) when the groundwater method is an FEA, since
        # only then can pore pressures be negative.
        self._gw_method = str(gw_method)
        self.setWindowTitle(tr("Define Materials..."))
        self.resize(720, 500)
        self.materials = list(materials)
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
        gen_form.addRow(tr("Name") + ":", self.ed_name)
        gen_form.addRow(tr("Color") + ":", self.btn_color)
        gen_form.addRow(tr("Unit Weight") + ":", self.dsp_gamma)
        gen_form.addRow(tr("Saturated Unit Weight") + ":", self.dsp_gamma_sat)

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
        # Formula label, shown next to the dropdown (Slide-style)
        from PySide6.QtWidgets import QLabel
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

        # Pore pressure
        pp_grp = QGroupBox(tr("Pore Pressure"))
        pp_form = QFormLayout(pp_grp)
        self.cbo_pp = QComboBox()
        for t in PorePressureType:
            self.cbo_pp.addItem(t.value, t)
        self.dsp_ru = QDoubleSpinBox(); self.dsp_ru.setRange(0.0, 1.0); self.dsp_ru.setDecimals(3)
        self.dsp_u = QDoubleSpinBox(); self.dsp_u.setRange(0.0, 1e6); self.dsp_u.setDecimals(2); self.dsp_u.setSuffix(" kPa")
        pp_form.addRow(tr("Type:"), self.cbo_pp)
        pp_form.addRow(tr("Ru coefficient:"), self.dsp_ru)
        pp_form.addRow(tr("Constant u:"), self.dsp_u)
        right.addWidget(pp_grp)

        right.addStretch(1)
        layout.addLayout(right, 1)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.buttons.accepted.connect(self._ok)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply_current)
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
        for w in (self.ed_name, self.btn_color, self.dsp_gamma, self.dsp_gamma_sat,
                  self.cbo_strength, self.cbo_pp, self.dsp_ru, self.dsp_u,
                  self.param_panel):
            w.setEnabled(on)

    def _current_material(self) -> Material | None:
        row = self.list.currentRow()
        if 0 <= row < len(self.materials):
            return self.materials[row]
        return None

    # ------------------------------------------------------------------
    def _on_select(self, row: int) -> None:
        if not (0 <= row < len(self.materials)):
            self._set_editor_enabled(False)
            return
        self._set_editor_enabled(True)
        m = self.materials[row]
        self.ed_name.setText(m.name)
        self._color_hex = m.color
        self._update_color_button()
        self.dsp_gamma.setValue(m.unit_weight * self._gamma_factor)
        self.dsp_gamma_sat.setValue(m.sat_unit_weight * self._gamma_factor)
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
        """Set γ and γ_sat spinboxes from the material (stored in SI)."""
        gamma_si = mat.unit_weight
        gamma_sat_si = getattr(mat, "saturated_unit_weight", gamma_si) or gamma_si
        self.dsp_gamma.setValue(gamma_si * self._gamma_factor)
        self.dsp_gamma_sat.setValue(gamma_sat_si * self._gamma_factor)

    def _read_gamma(self) -> tuple[float, float]:
        """Read γ and γ_sat from spinboxes and convert to SI."""
        f = self._gamma_factor or 1.0
        gamma_si = self.dsp_gamma.value() / f
        gamma_sat_si = self.dsp_gamma_sat.value() / f
        return gamma_si, gamma_sat_si

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
    def _apply_current(self) -> None:
        m = self._current_material()
        if m is None:
            return
        m.name = self.ed_name.text().strip() or m.name
        m.color = self._color_hex
        # γ and γ_sat: convert from displayed user-units back to SI (kN/m³)
        f = self._gamma_factor or 1.0
        m.unit_weight = self.dsp_gamma.value() / f
        m.sat_unit_weight = self.dsp_gamma_sat.value() / f
        m.phi_b = self.dsp_phi_b.value()
        m.air_entry_value = self.dsp_aev.value()

        mid = self.cbo_strength.currentData()
        cls = REGISTRY.get(mid)
        m.strength = cls(**self.param_panel.get_params())

        m.pore_pressure = self.cbo_pp.currentData()
        m.ru = self.dsp_ru.value()
        m.constant_u = self.dsp_u.value()

        # Refresh list item
        row = self.list.currentRow()
        item = self.list.item(row)
        item.setText(m.name)
        item.setForeground(QColor(m.color))

    def _ok(self) -> None:
        self._apply_current()
        self.accept()

    # ------------------------------------------------------------------
    def _add_material(self) -> None:
        from ogr_core.materials import MohrCoulomb  # lazy
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
            del self.materials[row]
            self.list.takeItem(row)

    # ------------------------------------------------------------------
    def result_materials(self) -> list[Material]:
        return list(self.materials)

    # ------------------------------------------------------------------
    def _apply_unsaturated_visibility(self) -> None:
        """Show the unsaturated-strength fields only when the groundwater
        method is a finite-element analysis, as the reference does."""
        method = getattr(self, "_gw_method", "none")
        show = method in ("fea_steady", "fea_transient")
        for wgt in getattr(self, "_unsat_widgets", []):
            wgt.setEnabled(show)
            lbl = wgt.parentWidget()
            if lbl is not None:
                wgt.setVisible(show)
        return show
