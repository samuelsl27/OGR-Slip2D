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
from ogr_gui.labels import (force_application_label,
                            force_orientation_label, support_type_label)  # noqa: E402
from ogr_gui.themes import theme_color


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

        # Type combobox — references the project's support_types.
        # v0.1.149 — the item DATA is the set's own id, not the class id.
        # With the class id two soil nails of different capacity were
        # one entry to this combo, and whichever the user picked, the
        # instance got the class and the engine the last set (D66).
        from ogr_core.support import resolve_support_type
        self.cbo_type = QComboBox()
        current = resolve_support_type(project, support)
        active_idx = 0
        for i, st in enumerate(project.support_types):
            name = support_type_label(st)
            self.cbo_type.addItem(name, st.id)
            if st is current:
                active_idx = i
        self.cbo_type.setCurrentIndex(active_idx)
        form.addRow(tr("Type:"), self.cbo_type)

        # Force application
        self.cbo_app = QComboBox()
        for fa in ForceApplication:
            self.cbo_app.addItem(force_application_label(fa), fa)
        idx = self.cbo_app.findData(support.force_application)
        if idx >= 0:
            self.cbo_app.setCurrentIndex(idx)
        form.addRow(tr("Force Application:"), self.cbo_app)

        # Force orientation
        self.cbo_ori = QComboBox()
        for fo in ForceOrientation:
            self.cbo_ori.addItem(force_orientation_label(fo), fo)
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
            tr('Length: {0:.2f} m   Axis: {1:.1f}°').format(support.length(), support.axis_angle_deg())
        )
        lbl.setStyleSheet(f"color: {theme_color('muted')};")
        form.addRow("", lbl)

        # v0.1.313 (D313) — why OK did not close, said here and not modal
        self.lbl_problem = QLabel("")
        self.lbl_problem.setWordWrap(True)
        self.lbl_problem.setStyleSheet(f"color: {theme_color('error')};")
        self.lbl_problem.setVisible(False)
        form.addRow(self.lbl_problem)

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
        from ogr_core.project.rules import (SUPPORT_NO_LENGTH,
                                            support_has_no_length)
        head = (self.spn_head_x.value(), self.spn_head_y.value())
        tail = (self.spn_tail_x.value(), self.spn_tail_y.value())
        # v0.1.313 (D313) — before anything is written: the API refuses a
        # support whose ends coincide, and this dialog stored one
        if support_has_no_length(self.project, head, tail):
            self.lbl_problem.setText(tr(SUPPORT_NO_LENGTH))
            self.lbl_problem.setVisible(True)
            return
        self.support.name = self.ed_name.text()
        chosen = self.cbo_type.currentData()
        for st in self.project.support_types:
            if st.id == chosen:
                # Both: the set by identity, and the class kept in
                # step so a reader of ``type_id`` alone — a file older
                # than v0.1.149, the pattern detector — is not lied to.
                self.support.type_ref = st.id
                self.support.type_id = st.TYPE_ID
                break
        self.support.force_application = self.cbo_app.currentData()
        self.support.orientation = self.cbo_ori.currentData()
        self.support.user_angle_deg = self.spn_user_angle.value()
        self.support.head = Vertex(*head)
        self.support.tail = Vertex(*tail)
        self.support.color = self._chosen_color
        super().accept()
