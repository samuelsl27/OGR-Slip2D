# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Transient groundwater stages dialog — Phase 6.

Mirrors the reference's *Transient* page in Project Settings: a table of
stages with their time and a per-stage **Calculate SF** checkbox, plus
the transient FEA options (tolerance, maximum iterations and number of
time steps, where 0 means the engine chooses automatically).

The page is only reachable when the *Transient Groundwater* advanced
option is enabled, which is itself exclusive with Excess Pore Pressure
and Rapid Drawdown — the main window enforces that.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from ogr_gui.i18n import tr  # noqa: E402


class TransientStagesDialog(QDialog):
    """Edit the transient stages and FEA options."""

    def __init__(self, settings, parent=None, current_bcs=None):
        super().__init__(parent)
        self.settings = settings          # GroundwaterSettings
        self._current_bcs = current_bcs   # SeepageBoundaryConditions
        self._stage_bcs: dict = {}
        self.setWindowTitle(tr("Transient Groundwater"))
        self.resize(520, 480)

        v = QVBoxLayout(self)

        self.chk_enabled = QCheckBox(
            tr("Transient groundwater analysis"))
        self.chk_enabled.setChecked(bool(settings.transient))
        self.chk_enabled.setToolTip(
            "Advanced groundwater options are mutually exclusive: "
            "enabling this disables Excess Pore Pressure and Rapid "
            "Drawdown.")
        self.chk_enabled.toggled.connect(self._on_enabled)
        v.addWidget(self.chk_enabled)

        self.lbl_excl = QLabel("")
        self.lbl_excl.setWordWrap(True)
        v.addWidget(self.lbl_excl)

        v.addWidget(QLabel(tr("Stages:")))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Calculate SF", "Label"])
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, st in enumerate(settings.transient_stages):
            self._add_row(st.get("time", 0.0),
                          bool(st.get("calculate_sf", False)),
                          str(st.get("label", "")))
            if st.get("bcs"):
                self._stage_bcs[i] = st["bcs"]
        v.addWidget(self.table, 1)

        row = QHBoxLayout()
        b_cap = QPushButton(tr("Capture current BCs"))
        b_cap.setToolTip(
            "Store the boundary conditions currently defined in Set "
            "Boundary Conditions into the selected stage. A transient "
            "run only evolves if the stage conditions differ from the "
            "initial ones.")
        b_cap.clicked.connect(self._capture)
        row.addWidget(b_cap)
        b_init = QPushButton(tr("Capture as initial state"))
        b_init.setToolTip(
            "Store the current boundary conditions as the INITIAL state "
            "(the steady field the transient run starts from).")
        b_init.clicked.connect(self._capture_initial)
        row.addWidget(b_init)
        b_add = QPushButton(tr("Add stage"))
        b_add.clicked.connect(lambda: self._add_row(self._next_time(),
                                                    False, ""))
        b_del = QPushButton(tr("Delete stage"))
        b_del.clicked.connect(self._delete)
        for b in (b_add, b_del):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        gb = QGroupBox(tr("Transient FEA options"))
        f = QFormLayout(gb)
        self.sp_tol = QDoubleSpinBox()
        self.sp_tol.setDecimals(9)
        self.sp_tol.setRange(1e-9, 1.0)
        self.sp_tol.setValue(settings.transient_tolerance)
        f.addRow(tr("Tolerance:"), self.sp_tol)
        self.sp_iter = QSpinBox()
        self.sp_iter.setRange(1, 1000)
        self.sp_iter.setValue(settings.transient_max_iterations)
        f.addRow(tr("Maximum iterations:"), self.sp_iter)
        self.sp_steps = QSpinBox()
        self.sp_steps.setRange(0, 100000)
        self.sp_steps.setValue(settings.transient_time_steps)
        self.sp_steps.setSpecialValueText("Auto")
        f.addRow(tr("Number of time steps:"), self.sp_steps)
        v.addWidget(gb)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._on_enabled(self.chk_enabled.isChecked())

    # ------------------------------------------------------------------
    def _on_enabled(self, on: bool) -> None:
        self.table.setEnabled(on)
        if on and (self.settings.excess_pore_pressure
                   or self.settings.rapid_drawdown):
            self.lbl_excl.setText(
                "<i>Enabling transient analysis will switch off the other "
                "advanced groundwater option.</i>")
        else:
            self.lbl_excl.setText("")

    def _next_time(self) -> float:
        times = []
        for r in range(self.table.rowCount()):
            try:
                times.append(float(self.table.item(r, 0).text()))
            except (AttributeError, ValueError):
                pass
        return (max(times) * 2.0 if times else 1.0) or 1.0

    def _add_row(self, time_value: float, calc_sf: bool,
                 label: str) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(f"{time_value:g}"))
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk.setCheckState(Qt.Checked if calc_sf else Qt.Unchecked)
        self.table.setItem(r, 1, chk)
        self.table.setItem(r, 2, QTableWidgetItem(label))

    def _capture(self) -> None:
        """Snapshot the current boundary conditions into the selected
        stage."""
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Transient Groundwater",
                                    "Select a stage first.")
            return
        if self._current_bcs is None:
            QMessageBox.information(
                self, "Transient Groundwater",
                "No boundary conditions defined yet.")
            return
        self._stage_bcs[r] = self._current_bcs.to_dict()
        item = self.table.item(r, 2)
        label = item.text() if item else ""
        if "[BC]" not in label:
            self.table.setItem(r, 2,
                               QTableWidgetItem((label + " [BC]").strip()))

    def _capture_initial(self) -> None:
        if self._current_bcs is None:
            QMessageBox.information(
                self, "Transient Groundwater",
                "No boundary conditions defined yet.")
            return
        self.settings.transient_initial_bcs = self._current_bcs.to_dict()
        QMessageBox.information(
            self, "Transient Groundwater",
            "Current boundary conditions stored as the initial state.")

    def _delete(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    # ------------------------------------------------------------------
    def stages(self) -> list:
        """Read the table into the settings' stage representation."""
        out = []
        for r in range(self.table.rowCount()):
            try:
                t = float(self.table.item(r, 0).text().replace(",", "."))
            except (AttributeError, ValueError):
                continue
            chk = self.table.item(r, 1)
            lbl = self.table.item(r, 2)
            entry = {
                "time": t,
                "calculate_sf": bool(chk and chk.checkState() == Qt.Checked),
                "label": lbl.text() if lbl else "",
            }
            if r in self._stage_bcs:
                entry["bcs"] = self._stage_bcs[r]
            out.append(entry)
        out.sort(key=lambda s: s["time"])
        return out

    def _accept(self) -> None:
        stages = self.stages()
        if self.chk_enabled.isChecked():
            if not stages:
                QMessageBox.warning(
                    self, "Transient Groundwater",
                    "Define at least one stage, or switch the transient "
                    "analysis off.")
                return
            times = [s["time"] for s in stages]
            if any(t <= 0 for t in times):
                QMessageBox.warning(
                    self, "Transient Groundwater",
                    "Stage times must be positive.")
                return
            if len(set(times)) != len(times):
                QMessageBox.warning(
                    self, "Transient Groundwater",
                    "Stage times must be distinct.")
                return
            self.settings.set_advanced_option("transient")
        elif self.settings.transient:
            self.settings.set_advanced_option(None)
        self.settings.transient_stages = stages
        self.settings.transient_tolerance = self.sp_tol.value()
        self.settings.transient_max_iterations = self.sp_iter.value()
        self.settings.transient_time_steps = self.sp_steps.value()
        self.accept()
