# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Dialogs for boundary editing operations (v0.1.2).

Contains:
    - EditCoordinatesDialog (spreadsheet-style (X,Y) editor)
    - ScaleDialog / RotateDialog / ExpandShrinkDialog
    - ChangeSlopeAngleDialog
    - ConvertBoundaryDialog
    - SimplifyBoundaryDialog
    - GeometryCleanupDialog
    - SelectionFilterDialog
    - AssignMaterialDialog

All dialogs are modal and produce a new Boundary (or a parameter tuple)
that the MainWindow wraps in a Command and pushes onto the undo stack.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
    offset_polygon,
    rotate as g_rotate,
    scale as g_scale,
    simplify_rdp,
)
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class EditCoordinatesDialog(QDialog):
    """Spreadsheet-style editor for (X, Y) of each vertex of a boundary."""

    def __init__(self, boundary: Boundary, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit Coordinates — {boundary.name}")
        self.resize(360, 460)
        self._result_boundary: Optional[Boundary] = None
        self._source_boundary = boundary

        root = QVBoxLayout(self)
        info = QLabel(
            f"<b>{boundary.btype.display_name}</b> — "
            f"{'closed polygon' if boundary.polyline.closed else 'open polyline'}"
        )
        root.addWidget(info)

        self.table = QTableWidget(len(boundary.vertices), 2)
        self.table.setHorizontalHeaderLabels(["X", "Y"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r, v in enumerate(boundary.vertices):
            self.table.setItem(r, 0, QTableWidgetItem(f"{v.x:.4f}"))
            self.table.setItem(r, 1, QTableWidgetItem(f"{v.y:.4f}"))
        root.addWidget(self.table, 1)

        # Row controls
        row_btns = QHBoxLayout()
        btn_add = QPushButton(tr("Add Row"))
        btn_add.clicked.connect(self._add_row)
        btn_del = QPushButton(tr("Delete Row"))
        btn_del.clicked.connect(self._del_row)
        btn_up = QPushButton(tr("Move Up"))
        btn_up.clicked.connect(lambda: self._move_row(-1))
        btn_dn = QPushButton(tr("Move Down"))
        btn_dn.clicked.connect(lambda: self._move_row(+1))
        for b in (btn_add, btn_del, btn_up, btn_dn):
            row_btns.addWidget(b)
        row_btns.addStretch(1)
        root.addLayout(row_btns)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # --- row actions --------------------------------------------------
    def _add_row(self) -> None:
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount()
        self.table.insertRow(r + 1)
        self.table.setItem(r + 1, 0, QTableWidgetItem("0.0000"))
        self.table.setItem(r + 1, 1, QTableWidgetItem("0.0000"))

    def _del_row(self) -> None:
        r = self.table.currentRow()
        if r >= 0 and self.table.rowCount() > 2:
            self.table.removeRow(r)

    def _move_row(self, delta: int) -> None:
        r = self.table.currentRow()
        new_r = r + delta
        if r < 0 or new_r < 0 or new_r >= self.table.rowCount():
            return
        # Swap contents
        for col in (0, 1):
            a = self.table.item(r, col).text()
            b = self.table.item(new_r, col).text()
            self.table.item(r, col).setText(b)
            self.table.item(new_r, col).setText(a)
        self.table.setCurrentCell(new_r, 0)

    # --- result -------------------------------------------------------
    def _accept(self) -> None:
        verts: list[Vertex] = []
        for r in range(self.table.rowCount()):
            try:
                x = float(self.table.item(r, 0).text())
                y = float(self.table.item(r, 1).text())
            except (ValueError, AttributeError):
                continue
            verts.append(Vertex(x, y))
        if len(verts) < 2:
            return
        new_b = deepcopy(self._source_boundary)
        new_b.polyline.vertices = verts
        if new_b.polyline.closed and len(verts) >= 3:
            try:
                new_b.polyline.ensure_ccw()
            except Exception:  # noqa: BLE001
                pass
        self._result_boundary = new_b
        self.accept()

    def result_boundary(self) -> Optional[Boundary]:
        return self._result_boundary


# ======================================================================
class ScaleDialog(QDialog):
    """Scale factor input dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Scale Boundary"))
        self.resize(320, 200)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.spn_sx = QDoubleSpinBox()
        self.spn_sx.setRange(0.01, 100.0)
        self.spn_sx.setDecimals(4)
        self.spn_sx.setSingleStep(0.1)
        self.spn_sx.setValue(1.0)

        self.spn_sy = QDoubleSpinBox()
        self.spn_sy.setRange(0.01, 100.0)
        self.spn_sy.setDecimals(4)
        self.spn_sy.setSingleStep(0.1)
        self.spn_sy.setValue(1.0)

        self.chk_uniform = QCheckBox(tr("Uniform scaling"))
        self.chk_uniform.setChecked(True)
        self.chk_uniform.toggled.connect(self._on_uniform_toggled)

        self.spn_px = QDoubleSpinBox()
        self.spn_px.setRange(-1e6, 1e6)
        self.spn_px.setDecimals(3)
        self.spn_px.setValue(0.0)

        self.spn_py = QDoubleSpinBox()
        self.spn_py.setRange(-1e6, 1e6)
        self.spn_py.setDecimals(3)
        self.spn_py.setValue(0.0)

        form.addRow(self.chk_uniform)
        form.addRow(tr("Sx:"), self.spn_sx)
        form.addRow(tr("Sy:"), self.spn_sy)
        form.addRow(tr("Pivot X:"), self.spn_px)
        form.addRow(tr("Pivot Y:"), self.spn_py)
        root.addLayout(form)

        note = QLabel("<i>Pivot defaults to (0, 0). Use the boundary centroid "
                      "by leaving it at zero and selecting a non-central "
                      "boundary carefully.</i>")
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._on_uniform_toggled(True)

    def _on_uniform_toggled(self, on: bool) -> None:
        self.spn_sy.setEnabled(not on)
        if on:
            self.spn_sx.valueChanged.connect(self.spn_sy.setValue)
        else:
            try:
                self.spn_sx.valueChanged.disconnect(self.spn_sy.setValue)
            except (TypeError, RuntimeError):
                pass

    def parameters(self) -> tuple[float, float, Vertex]:
        sx = self.spn_sx.value()
        sy = self.spn_sx.value() if self.chk_uniform.isChecked() else self.spn_sy.value()
        return sx, sy, Vertex(self.spn_px.value(), self.spn_py.value())


# ======================================================================
class RotateDialog(QDialog):
    """Rotation angle + pivot input."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Rotate Boundary"))
        self.resize(320, 180)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.spn_angle = QDoubleSpinBox()
        self.spn_angle.setRange(-360.0, 360.0)
        self.spn_angle.setDecimals(2)
        self.spn_angle.setSuffix(" °")
        self.spn_angle.setValue(0.0)
        self.spn_px = QDoubleSpinBox(); self.spn_px.setRange(-1e6, 1e6); self.spn_px.setDecimals(3)
        self.spn_py = QDoubleSpinBox(); self.spn_py.setRange(-1e6, 1e6); self.spn_py.setDecimals(3)

        form.addRow(tr("Angle (CCW):"), self.spn_angle)
        form.addRow(tr("Pivot X:"), self.spn_px)
        form.addRow(tr("Pivot Y:"), self.spn_py)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def parameters(self) -> tuple[float, Vertex]:
        return self.spn_angle.value(), Vertex(self.spn_px.value(), self.spn_py.value())


# ======================================================================
class ExpandShrinkDialog(QDialog):
    """Polygon offset distance input."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Expand / Shrink External Boundary"))
        self.resize(320, 140)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.spn_d = QDoubleSpinBox()
        self.spn_d.setRange(-10000.0, 10000.0)
        self.spn_d.setDecimals(3)
        self.spn_d.setSuffix(" m")
        self.spn_d.setValue(1.0)
        form.addRow(tr("Offset distance:"), self.spn_d)
        root.addLayout(form)
        note = QLabel(tr("<i>Positive = expand outward. Negative = shrink inward.</i>"))
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def distance(self) -> float:
        return self.spn_d.value()


# ======================================================================
class ChangeSlopeAngleDialog(QDialog):
    """Target slope angle + pivot input."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Change Slope Angle"))
        self.resize(320, 200)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.spn_angle = QDoubleSpinBox()
        self.spn_angle.setRange(0.01, 89.99)
        self.spn_angle.setDecimals(2)
        self.spn_angle.setSuffix(" °")
        self.spn_angle.setValue(30.0)
        self.spn_px = QDoubleSpinBox(); self.spn_px.setRange(-1e6, 1e6); self.spn_px.setDecimals(3)
        self.spn_py = QDoubleSpinBox(); self.spn_py.setRange(-1e6, 1e6); self.spn_py.setDecimals(3)
        form.addRow(tr("Target slope angle:"), self.spn_angle)
        form.addRow(tr("Pivot X (toe):"), self.spn_px)
        form.addRow(tr("Pivot Y (toe):"), self.spn_py)
        root.addLayout(form)
        note = QLabel("<i>The steepest edge of the external boundary will be "
                      "rotated about the pivot to match the target angle.</i>")
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def parameters(self) -> tuple[float, Vertex]:
        return self.spn_angle.value(), Vertex(self.spn_px.value(), self.spn_py.value())


# ======================================================================
class ConvertBoundaryDialog(QDialog):
    """Pick a new BoundaryType to convert a boundary to."""

    def __init__(self, current_type: BoundaryType, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Convert Boundary"))
        self.resize(320, 140)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.cbo = QComboBox()
        for bt in BoundaryType:
            self.cbo.addItem(bt.display_name, bt)
        idx = self.cbo.findData(current_type)
        self.cbo.setCurrentIndex(max(0, idx))
        form.addRow(tr("New type:"), self.cbo)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def new_type(self) -> BoundaryType:
        return self.cbo.currentData()


# ======================================================================
class SimplifyBoundaryDialog(QDialog):
    """RDP simplification tolerance."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Simplify Boundary"))
        self.resize(320, 160)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.spn_tol = QDoubleSpinBox()
        self.spn_tol.setRange(1e-6, 1e4)
        self.spn_tol.setDecimals(4)
        self.spn_tol.setSingleStep(0.1)
        self.spn_tol.setSuffix(" m")
        self.spn_tol.setValue(0.5)
        form.addRow(tr("Tolerance (ε):"), self.spn_tol)
        root.addLayout(form)
        note = QLabel("<i>Vertices whose deviation from the simplified line "
                      "is below ε will be removed (Ramer-Douglas-Peucker).</i>")
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def tolerance(self) -> float:
        return self.spn_tol.value()


# ======================================================================
class GeometryCleanupDialog(QDialog):
    """Report-style dialog showing cleanup output."""

    def __init__(self, report: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Geometry Cleanup"))
        self.resize(600, 400)
        root = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(report)
        root.addWidget(text, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


# ======================================================================
@dataclass
class SelectionFilterState:
    boundaries: bool = True
    vertices: bool = True
    materials: bool = True
    supports: bool = True
    loads: bool = True
    surfaces: bool = True


class SelectionFilterDialog(QDialog):
    """Toggle which entity types are selectable by the cursor."""

    def __init__(self, state: SelectionFilterState, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Selection Filter (Ctrl+F)"))
        self.resize(320, 320)
        self._state = state

        root = QVBoxLayout(self)
        grp = QGroupBox(tr("Selectable entity types"))
        lay = QVBoxLayout(grp)
        self.chk_bnd = QCheckBox(tr("Boundaries")); self.chk_bnd.setChecked(state.boundaries)
        self.chk_vert = QCheckBox(tr("Vertices (Nodes)")); self.chk_vert.setChecked(state.vertices)
        self.chk_mat = QCheckBox(tr("Materials")); self.chk_mat.setChecked(state.materials)
        self.chk_sup = QCheckBox(tr("Supports")); self.chk_sup.setChecked(state.supports)
        self.chk_load = QCheckBox(tr("Loads")); self.chk_load.setChecked(state.loads)
        self.chk_surf = QCheckBox(tr("Slip surfaces")); self.chk_surf.setChecked(state.surfaces)
        for c in (self.chk_bnd, self.chk_vert, self.chk_mat, self.chk_sup,
                  self.chk_load, self.chk_surf):
            lay.addWidget(c)
        root.addWidget(grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _ok(self) -> None:
        self._state.boundaries = self.chk_bnd.isChecked()
        self._state.vertices = self.chk_vert.isChecked()
        self._state.materials = self.chk_mat.isChecked()
        self._state.supports = self.chk_sup.isChecked()
        self._state.loads = self.chk_load.isChecked()
        self._state.surfaces = self.chk_surf.isChecked()
        self.accept()

    def state(self) -> SelectionFilterState:
        return self._state


# ======================================================================
class AssignMaterialDialog(QDialog):
    """Quick picker to assign a material to a material boundary."""

    def __init__(self, materials: list, current_id: Optional[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Assign Material"))
        self.resize(340, 160)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.cbo = QComboBox()
        self.cbo.addItem("(none)", None)
        for m in materials:
            self.cbo.addItem(m.name, m.id)
        if current_id is not None:
            idx = self.cbo.findData(current_id)
            if idx >= 0:
                self.cbo.setCurrentIndex(idx)
        form.addRow(tr("Material:"), self.cbo)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def material_id(self) -> Optional[str]:
        return self.cbo.currentData()
