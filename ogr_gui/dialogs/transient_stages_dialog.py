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

v0.1.306 (D294) — the analysis can be accepted with NO stages, so the
initial state can be captured first, the boundary conditions changed in
their own dialog (which cannot open while this one is), and the stage
added afterwards. The dialog says which initial state the transient starts
from and lets it be cleared; computing a transient with no stages is
refused, and the dialog says that too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

from PySide6.QtCore import QSize, Qt
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
from ogr_gui.dialog_size import open_at_content_size
from ogr_gui.i18n import tr  # noqa: E402


class TransientStagesDialog(QDialog):
    """Edit the transient stages and FEA options."""

    def __init__(self, settings, parent=None, current_bcs=None):
        super().__init__(parent)
        self.settings = settings          # GroundwaterSettings
        self._current_bcs = current_bcs   # SeepageBoundaryConditions
        self._stage_bcs: dict = {}
        # v0.1.306 (D294) — what OK writes as the initial state. It starts
        # as the stored one, so that clearing it is a change OK can write.
        self._initial_bcs = copy.deepcopy(settings.transient_initial_bcs)
        self.setWindowTitle(tr("Transient Groundwater"))

        v = QVBoxLayout(self)
        # Built first: adding the stored rows below already refreshes them.
        self.lbl_initial = QLabel("")
        self.lbl_initial.setWordWrap(True)
        self.lbl_no_stages = QLabel("")
        self.lbl_no_stages.setWordWrap(True)
        self.b_clear_initial = QPushButton(tr("Clear initial state"))
        self.b_clear_initial.setToolTip(tr(
            "Start the transient from the current boundary conditions "
            "again, which means the model starts in equilibrium with "
            "them."))
        self.b_clear_initial.clicked.connect(self._clear_initial)

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

        # v0.1.315 (D293) — two rows: in Spanish the four buttons of one
        # row asked for 1156 px, and the 520 px the dialog opened at cut all
        # four once the theme let them shrink under their text.
        row = QHBoxLayout()
        b_cap = QPushButton(tr("Capture current BCs"))
        b_cap.setToolTip(tr(
            "Store the boundary conditions currently defined in Set "
            "Boundary Conditions into the selected stage. A transient "
            "run only evolves if the stage conditions differ from the "
            "initial ones."))
        b_cap.clicked.connect(self._capture)
        row.addWidget(b_cap)
        b_init = QPushButton(tr("Capture as initial state"))
        b_init.setToolTip(tr(
            "Store the current boundary conditions as the INITIAL state "
            "(the steady field the transient run starts from)."))
        b_init.clicked.connect(self._capture_initial)
        row.addWidget(b_init)
        if current_bcs is None:
            # Conditions are keyed by mesh node: without a mesh there are
            # none to capture (they used to answer with a modal box).
            for b in (b_cap, b_init):
                b.setEnabled(False)
                b.setToolTip(tr(
                    "Needs the finite-element mesh: Groundwater > Mesh."))
        b_add = QPushButton(tr("Add stage"))
        b_add.clicked.connect(lambda: self._add_row(self._next_time(),
                                                    False, ""))
        b_del = QPushButton(tr("Delete stage"))
        b_del.clicked.connect(self._delete)
        row.addStretch(1)
        stage_row = QHBoxLayout()
        for b in (b_add, b_del):
            stage_row.addWidget(b)
        stage_row.addStretch(1)
        v.addLayout(stage_row)
        v.addLayout(row)
        # Next to what it clears, and not a fifth button on a row that is
        # already too narrow in Spanish (D293).
        init_row = QHBoxLayout()
        init_row.addWidget(self.lbl_initial, 1)
        init_row.addWidget(self.b_clear_initial)
        v.addLayout(init_row)
        v.addWidget(self.lbl_no_stages)

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
        # v0.1.315 (D293) — at the size its content asks for, not a fixed
        # English one
        open_at_content_size(self, QSize(520, 480))

    # ------------------------------------------------------------------
    def _on_enabled(self, on: bool) -> None:
        self.table.setEnabled(on)
        if on and (self.settings.excess_pore_pressure
                   or self.settings.rapid_drawdown):
            self.lbl_excl.setText(tr(
                "<i>Enabling transient analysis will switch off the other "
                "advanced groundwater option.</i>"))
        else:
            self.lbl_excl.setText("")
        self._refresh_notes()

    def _refresh_notes(self) -> None:
        """The two lines that say what OK would store: which initial state
        the transient starts from, and that it has no stage yet."""
        if self._initial_bcs is None:
            self.lbl_initial.setText(tr(
                "Initial state: the current boundary conditions (none "
                "captured)."))
        else:
            self.lbl_initial.setText(tr(
                "Initial state: captured boundary conditions ({0} nodes, "
                "{1} segments).").format(
                    len(self._initial_bcs.get("nodes", [])),
                    len(self._initial_bcs.get("segments", []))))
        self.b_clear_initial.setEnabled(self._initial_bcs is not None)
        empty = self.chk_enabled.isChecked() and self.table.rowCount() == 0
        self.lbl_no_stages.setText(tr(
            "No stages yet: Compute Groundwater will refuse until you add "
            "one.") if empty else "")

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
        self._refresh_notes()

    def _capture(self) -> None:
        """Snapshot the current boundary conditions into the selected
        stage."""
        if self._current_bcs is None:     # the button is disabled then
            return
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, tr("Transient Groundwater"),
                                    tr("Select a stage first."))
            return
        self._stage_bcs[r] = self._current_bcs.to_dict()
        item = self.table.item(r, 2)
        label = item.text() if item else ""
        if "[BC]" not in label:
            self.table.setItem(r, 2,
                               QTableWidgetItem((label + " [BC]").strip()))

    def _capture_initial(self) -> None:
        """Keep the current boundary conditions as the initial state."""
        if self._current_bcs is None:     # the button is disabled then
            return
        # v0.1.200 — kept until OK: this wrote the settings at once, so
        # the capture survived Cancel. v0.1.306 (D294) — said on the
        # dialog's own line instead of a modal box (in English, and it
        # said "stored" of something stored only on OK).
        self._initial_bcs = self._current_bcs.to_dict()
        self._refresh_notes()

    def _clear_initial(self) -> None:
        """Start from the current conditions again (written on OK)."""
        self._initial_bcs = None
        self._refresh_notes()

    def _delete(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)
            # v0.1.200 — the per-stage conditions are keyed by ROW; the
            # rows below a deleted one move up, and their conditions have
            # to move with them or they attach to the wrong stage.
            self._stage_bcs.pop(r, None)
            self._stage_bcs = {(k - 1 if k > r else k): v
                               for k, v in self._stage_bcs.items()}
        self._refresh_notes()

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
        # v0.1.200 — the checks moved to
        # ``GroundwaterSettings.set_transient``, which an agent's stages go
        # through too; it changes nothing when one fails. v0.1.306 (D294):
        # no stages is no longer one of them.
        try:
            self.settings.set_transient(
                self.chk_enabled.isChecked(), self.stages(),
                tolerance=self.sp_tol.value(),
                max_iterations=self.sp_iter.value(),
                time_steps=self.sp_steps.value())
        except ValueError as exc:
            QMessageBox.warning(self, tr("Transient Groundwater"),
                                tr(str(exc)))
            return
        # Always written: clearing the initial state is a change too.
        self.settings.transient_initial_bcs = self._initial_bcs
        self.accept()
