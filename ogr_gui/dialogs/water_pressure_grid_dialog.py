# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Water Pressure Grid dialog — edit / import the grid of water-pressure
data points (Phase 0 of the groundwater plan).

Provides an editable (x, y, value) table, CSV import (three numeric
columns, comma/semicolon/whitespace separated, header auto-skipped),
grid value type and interpolation options, and live point count.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ogr_core.hydraulic import GridValueType, WaterPressureGrid
from ogr_gui.i18n import tr  # noqa: E402


class WaterPressureGridDialog(QDialog):
    """Edit the project's Water Pressure Grid."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Water Pressure Grid"))
        self.resize(520, 560)

        grid = project.water_pressure_grid or WaterPressureGrid()

        v = QVBoxLayout(self)

        # --- type / interpolation row ---------------------------------
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Grid type:")))
        self.cbo_type = QComboBox()
        for t, label in [
            (GridValueType.TOTAL_HEAD, "Total Head"),
            (GridValueType.PRESSURE_HEAD, "Pressure Head"),
            (GridValueType.PORE_PRESSURE, "Pore Pressure"),
        ]:
            self.cbo_type.addItem(label, t)
        i = self.cbo_type.findData(grid.value_type)
        if i >= 0:
            self.cbo_type.setCurrentIndex(i)
        row.addWidget(self.cbo_type)

        row.addWidget(QLabel(tr("Interpolation:")))
        self.cbo_interp = QComboBox()
        self.cbo_interp.addItem("Thin Plate Spline", "tps")
        self.cbo_interp.addItem("Inverse Distance (IDW)", "idw")
        i = self.cbo_interp.findData(grid.interpolation)
        if i >= 0:
            self.cbo_interp.setCurrentIndex(i)
        row.addWidget(self.cbo_interp)
        v.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(tr("IDW neighbours:")))
        self.spn_nb = QSpinBox()
        self.spn_nb.setRange(1, 64)
        self.spn_nb.setValue(grid.idw_neighbours)
        row2.addWidget(self.spn_nb)
        self.chk_suction = QCheckBox(tr("Allow suction (keep u < 0)"))
        self.chk_suction.setChecked(grid.allow_suction)
        row2.addWidget(self.chk_suction)
        row2.addStretch(1)
        v.addLayout(row2)

        # --- points table ---------------------------------------------
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["x", "y", "value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        for (x, y, val) in grid.points:
            self._append_row(x, y, val)
        v.addWidget(self.table, 1)

        # --- buttons row ----------------------------------------------
        brow = QHBoxLayout()
        b_add = QPushButton(tr("Add row"))
        b_add.clicked.connect(lambda: self._append_row(0.0, 0.0, 0.0))
        b_del = QPushButton(tr("Delete selected"))
        b_del.clicked.connect(self._delete_selected)
        b_csv = QPushButton(tr("Import CSV…"))
        b_csv.clicked.connect(self._import_csv)
        b_clear = QPushButton(tr("Clear"))
        b_clear.clicked.connect(lambda: self.table.setRowCount(0))
        for b in (b_add, b_del, b_csv, b_clear):
            brow.addWidget(b)
        brow.addStretch(1)
        self.lbl_count = QLabel("")
        brow.addWidget(self.lbl_count)
        v.addLayout(brow)
        self._update_count()

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    # ------------------------------------------------------------------
    def _append_row(self, x, y, val) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, value in enumerate((x, y, val)):
            self.table.setItem(r, c, QTableWidgetItem(f"{value:g}"))
        self._update_count()

    def _delete_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self._update_count()

    def _update_count(self) -> None:
        if hasattr(self, "lbl_count"):
            self.lbl_count.setText(f"{self.table.rowCount()} points")

    # ------------------------------------------------------------------
    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import grid points", "",
            "CSV / text files (*.csv *.txt *.dat);;All files (*)")
        if not path:
            return
        pts = parse_grid_csv_text(open(path, encoding="utf-8",
                                       errors="ignore").read())
        if not pts:
            QMessageBox.warning(
                self, "Import",
                "No (x, y, value) rows could be parsed from the file.")
            return
        for x, y, val in pts:
            self._append_row(x, y, val)

    # ------------------------------------------------------------------
    def _accept(self) -> None:
        pts: list[tuple[float, float, float]] = []
        for r in range(self.table.rowCount()):
            try:
                x = float(self.table.item(r, 0).text().replace(",", "."))
                y = float(self.table.item(r, 1).text().replace(",", "."))
                val = float(self.table.item(r, 2).text().replace(",", "."))
            except (TypeError, ValueError, AttributeError):
                QMessageBox.warning(
                    self, "Water Pressure Grid",
                    f"Row {r + 1} is not numeric.")
                return
            pts.append((x, y, val))
        self.project.water_pressure_grid = WaterPressureGrid(
            points=pts,
            value_type=self.cbo_type.currentData(),
            interpolation=self.cbo_interp.currentData(),
            idw_neighbours=self.spn_nb.value(),
            allow_suction=self.chk_suction.isChecked(),
        ) if pts else None
        self.project.is_dirty = True
        self.accept()


# ----------------------------------------------------------------------
def parse_grid_csv_text(text: str) -> list[tuple[float, float, float]]:
    """Parse (x, y, value) rows from CSV-ish text. Accepts comma,
    semicolon, tab or whitespace separators; skips headers and blank or
    comment lines. Exposed as a function for testability."""
    out: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in (",", ";", "\t"):
            line = line.replace(sep, " ")
        parts = [p for p in line.split() if p]
        if len(parts) < 3:
            continue
        try:
            out.append((float(parts[0]), float(parts[1]), float(parts[2])))
        except ValueError:
            continue  # header or non-numeric line
    return out
