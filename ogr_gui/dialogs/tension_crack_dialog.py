# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Define Tension Crack dialog (v0.1.7).

Reactive UI: the visible & enabled fields depend on the selected
``Water Level`` mode, exactly as described in the Slide reference
(Define_Tension_Crack.htm). Implements:
    - Dry, Filled, Percent Filled
    - Filled below Elevation, Filled to Depth
    - Use Water Table, Use Piezometric Line

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from ogr_core.geometry import BoundaryType
from ogr_core.geometry.tension_crack import TensionCrackProperties, WaterLevelMode
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class DefineTensionCrackDialog(QDialog):
    """Edit the hydraulic properties of the Tension Crack zone."""

    # User-facing labels for each WaterLevelMode (in display order)
    _MODES = [
        (WaterLevelMode.DRY, "Dry — no water"),
        (WaterLevelMode.FILLED, "Filled — 100% saturated"),
        (WaterLevelMode.PERCENT_FILLED, "Percent Filled"),
        (WaterLevelMode.FILLED_BELOW_ELEVATION, "Filled below Elevation (absolute Y)"),
        (WaterLevelMode.FILLED_TO_DEPTH, "Filled to Depth (relative to crack top)"),
        (WaterLevelMode.USE_WATER_TABLE, "Use Water Table"),
        (WaterLevelMode.USE_PIEZOMETRIC, "Use Piezometric Line"),
    ]

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Define Tension Crack"))
        self.project = project
        self._props = TensionCrackProperties(
            mode=project.tension_crack_properties.mode,
            percent_filled=project.tension_crack_properties.percent_filled,
            elevation=project.tension_crack_properties.elevation,
            depth=project.tension_crack_properties.depth,
            piezo_id=project.tension_crack_properties.piezo_id,
        )

        # Detect availability of WT / piezo (for greying out)
        self._has_wt = any(
            b.btype == BoundaryType.WATER_TABLE for b in project.boundaries
        )
        self._piezos = [
            b for b in project.boundaries if b.btype == BoundaryType.PIEZOMETRIC
        ]

        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "<b>Tension Crack hydraulic properties.</b><br>"
            "Defines the water level inside the tension crack zone, used "
            "to compute the hydrostatic force on slip surfaces.<br>"
            f"<i>γ_w = {project.settings.groundwater.pore_fluid_unit_weight:.2f} "
            f"kN/m³ (from Project Settings)</i>"
        ))

        form = QFormLayout()

        # 1. Water Level mode selector
        self.cb_mode = QComboBox()
        for mode, label in self._MODES:
            self.cb_mode.addItem(label, mode)
        # Disable WT / Piezo entries that are unavailable
        for i, (mode, _) in enumerate(self._MODES):
            if mode == WaterLevelMode.USE_WATER_TABLE and not self._has_wt:
                self.cb_mode.model().item(i).setEnabled(False)
                self.cb_mode.setItemData(
                    i, "No Water Table defined in this model. Add one first.",
                    Qt.ToolTipRole,
                )
            elif mode == WaterLevelMode.USE_PIEZOMETRIC and not self._piezos:
                self.cb_mode.model().item(i).setEnabled(False)
                self.cb_mode.setItemData(
                    i, "No Piezometric Lines defined. Add one first.",
                    Qt.ToolTipRole,
                )
        # Pre-select current mode
        for i, (mode, _) in enumerate(self._MODES):
            if mode == self._props.mode:
                self.cb_mode.setCurrentIndex(i)
                break
        self.cb_mode.currentIndexChanged.connect(self._refresh_visibility)
        form.addRow(tr("Water Level:"), self.cb_mode)

        # 2. Percent Filled
        self.sb_percent = QDoubleSpinBox()
        self.sb_percent.setRange(0.0, 100.0)
        self.sb_percent.setDecimals(1)
        self.sb_percent.setSuffix(" %")
        self.sb_percent.setValue(self._props.percent_filled)
        form.addRow(tr("Percent Filled:"), self.sb_percent)

        # 3. Elevation (absolute Y)
        self.sb_elevation = QDoubleSpinBox()
        self.sb_elevation.setRange(-1e6, 1e6)
        self.sb_elevation.setDecimals(3)
        self.sb_elevation.setSuffix(" m")
        self.sb_elevation.setValue(self._props.elevation)
        form.addRow(tr("Elevation (Y):"), self.sb_elevation)

        # 4. Depth (from crack top)
        self.sb_depth = QDoubleSpinBox()
        self.sb_depth.setRange(0.0, 1e6)
        self.sb_depth.setDecimals(3)
        self.sb_depth.setSuffix(" m")
        self.sb_depth.setValue(self._props.depth)
        form.addRow(tr("Depth from crack top:"), self.sb_depth)

        # 5. Piezometric line selector
        self.cb_piezo = QComboBox()
        for p in self._piezos:
            self.cb_piezo.addItem(p.name or f"Piezo {p.id[:8]}", p.id)
        if not self._piezos:
            self.cb_piezo.addItem("(no piezometric line in model)", None)
        # Pre-select
        if self._props.piezo_id is not None:
            for i in range(self.cb_piezo.count()):
                if self.cb_piezo.itemData(i) == self._props.piezo_id:
                    self.cb_piezo.setCurrentIndex(i)
                    break
        form.addRow(tr("Piezo Line:"), self.cb_piezo)

        # Keep reference to label widgets so we can grey them out too
        self._labels = {}
        for i in range(form.rowCount()):
            try:
                lbl_item = form.itemAt(i, QFormLayout.LabelRole)
                fld_item = form.itemAt(i, QFormLayout.FieldRole)
                if lbl_item is None or fld_item is None:
                    continue
                lbl = lbl_item.widget()
                field = fld_item.widget()
                if lbl is not None and field is not None:
                    self._labels[id(field)] = lbl
            except Exception:
                continue

        root.addLayout(form)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        self._refresh_visibility()
        self.resize(420, self.sizeHint().height())

    # ------------------------------------------------------------------
    def _refresh_visibility(self) -> None:
        """Enable / disable fields per the selected mode."""
        mode = self.cb_mode.currentData()
        # Default: all disabled
        widgets = {
            self.sb_percent: False,
            self.sb_elevation: False,
            self.sb_depth: False,
            self.cb_piezo: False,
        }
        if mode == WaterLevelMode.PERCENT_FILLED:
            widgets[self.sb_percent] = True
        elif mode == WaterLevelMode.FILLED_BELOW_ELEVATION:
            widgets[self.sb_elevation] = True
        elif mode == WaterLevelMode.FILLED_TO_DEPTH:
            widgets[self.sb_depth] = True
        elif mode == WaterLevelMode.USE_PIEZOMETRIC:
            widgets[self.cb_piezo] = True
        for w, enabled in widgets.items():
            w.setEnabled(enabled)
            lbl = self._labels.get(id(w))
            if lbl is not None:
                lbl.setStyleSheet(
                    "" if enabled else "color: #909090;"
                )

    # ------------------------------------------------------------------
    def result_properties(self) -> TensionCrackProperties:
        return TensionCrackProperties(
            mode=self.cb_mode.currentData(),
            percent_filled=self.sb_percent.value(),
            elevation=self.sb_elevation.value(),
            depth=self.sb_depth.value(),
            piezo_id=self.cb_piezo.currentData(),
        )
