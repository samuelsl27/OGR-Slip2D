# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Support Instance Properties dialog — edits a single SupportInstance.

Differs from DefineSupportDialog (which edits the *catalogue* of
SupportType definitions): this one edits the per-instance attributes
of a single placed support — type assignment, force application,
orientation, head/tail coordinates, name, color.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtGui import QColor

from ogr_core.support import ForceApplication, ForceOrientation
from ogr_gui.i18n import tr  # noqa: E402


class SupportInstancePropertiesDialog(QDialog):
    """Edit a single SupportInstance's per-instance attributes."""

    def __init__(self, support, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Support Properties"))
        self.resize(380, 380)
        self.support = support
        self.project = project

        form = QFormLayout(self)

        self.ed_name = QLineEdit(support.name or "")
        form.addRow(tr("Name:"), self.ed_name)

        # Type combobox — references the project's support_types
        self.cbo_type = QComboBox()
        active_idx = 0
        for i, st in enumerate(project.support_types):
            name = getattr(st, "_display_name", st.DISPLAY_NAME)
            self.cbo_type.addItem(name, st.TYPE_ID)
            if st.TYPE_ID == support.type_id:
                active_idx = i
        self.cbo_type.setCurrentIndex(active_idx)
        form.addRow(tr("Type:"), self.cbo_type)

        # Force application
        self.cbo_app = QComboBox()
        for fa in ForceApplication:
            self.cbo_app.addItem(fa.value.capitalize(), fa)
        idx = self.cbo_app.findData(support.force_application)
        if idx >= 0:
            self.cbo_app.setCurrentIndex(idx)
        form.addRow(tr("Force Application:"), self.cbo_app)

        # Force orientation
        self.cbo_ori = QComboBox()
        for fo in ForceOrientation:
            self.cbo_ori.addItem(fo.value.replace("_", " ").title(), fo)
        idx = self.cbo_ori.findData(support.orientation)
        if idx >= 0:
            self.cbo_ori.setCurrentIndex(idx)
        form.addRow(tr("Force Orientation:"), self.cbo_ori)

        # User angle
        self.spn_user_angle = QDoubleSpinBox()
        self.spn_user_angle.setRange(-360.0, 360.0)
        self.spn_user_angle.setSuffix(" °")
        self.spn_user_angle.setValue(support.user_angle_deg)
        form.addRow(tr("User Angle:"), self.spn_user_angle)

        # Geometry: head, tail
        self.spn_head_x = QDoubleSpinBox()
        self.spn_head_x.setRange(-1e9, 1e9); self.spn_head_x.setDecimals(4)
        self.spn_head_x.setSuffix(" m"); self.spn_head_x.setValue(support.head.x)
        self.spn_head_y = QDoubleSpinBox()
        self.spn_head_y.setRange(-1e9, 1e9); self.spn_head_y.setDecimals(4)
        self.spn_head_y.setSuffix(" m"); self.spn_head_y.setValue(support.head.y)
        head_row = QHBoxLayout()
        head_row.addWidget(self.spn_head_x); head_row.addWidget(self.spn_head_y)
        form.addRow(tr("Head (x, y):"), head_row)

        self.spn_tail_x = QDoubleSpinBox()
        self.spn_tail_x.setRange(-1e9, 1e9); self.spn_tail_x.setDecimals(4)
        self.spn_tail_x.setSuffix(" m"); self.spn_tail_x.setValue(support.tail.x)
        self.spn_tail_y = QDoubleSpinBox()
        self.spn_tail_y.setRange(-1e9, 1e9); self.spn_tail_y.setDecimals(4)
        self.spn_tail_y.setSuffix(" m"); self.spn_tail_y.setValue(support.tail.y)
        tail_row = QHBoxLayout()
        tail_row.addWidget(self.spn_tail_x); tail_row.addWidget(self.spn_tail_y)
        form.addRow(tr("Tail (x, y):"), tail_row)

        # Color
        self.btn_color = QPushButton(support.color or "#4b0082")
        self.btn_color.setStyleSheet(
            f"background-color: {support.color or '#4b0082'}; color: white;"
        )
        self.btn_color.clicked.connect(self._pick_color)
        self._chosen_color = support.color or "#4b0082"
        form.addRow(tr("Color:"), self.btn_color)

        # Read-only info
        lbl = QLabel(
            f"Length: {support.length():.2f} m   "
            f"Axis: {support.axis_angle_deg():.1f}°"
        )
        lbl.setStyleSheet("color: #555;")
        form.addRow("", lbl)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _pick_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._chosen_color), self)
        if c.isValid():
            self._chosen_color = c.name()
            self.btn_color.setText(self._chosen_color)
            self.btn_color.setStyleSheet(
                f"background-color: {self._chosen_color}; color: white;"
            )

    def accept(self) -> None:
        from ogr_core.geometry import Vertex
        self.support.name = self.ed_name.text()
        self.support.type_id = self.cbo_type.currentData()
        self.support.force_application = self.cbo_app.currentData()
        self.support.orientation = self.cbo_ori.currentData()
        self.support.user_angle_deg = self.spn_user_angle.value()
        self.support.head = Vertex(
            self.spn_head_x.value(), self.spn_head_y.value(),
        )
        self.support.tail = Vertex(
            self.spn_tail_x.value(), self.spn_tail_y.value(),
        )
        self.support.color = self._chosen_color
        super().accept()
