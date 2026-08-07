# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Add Support / Add Support Pattern dialogs.

Add Support is a 2-click canvas interaction (no modal dialog).
Add Support Pattern is a modal dialog that asks for length, spacing,
orientation, and then waits for the user to draw a 2-point segment
on the canvas.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ogr_core.support import (
    ForceApplication,
    ForceOrientation,
    SupportPattern,
)
from ogr_gui.i18n import tr  # noqa: E402


class AddSupportPatternDialog(QDialog):
    """Slide-style "Add Support Pattern" dialog.

    Asks the user for length, spacing, orientation. After OK is pressed,
    the MainWindow puts the canvas into pattern-pick mode (2-point
    segment along a boundary). The pattern is generated automatically
    from the picked segment.
    """

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Add Support Pattern"))
        self.resize(440, 380)
        self.project = project
        self.pattern: SupportPattern | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 1. Support type
        gtype = QGroupBox(tr("Support type"))
        ftype = QFormLayout(gtype)
        self.cbo_type = QComboBox()
        if self.project.support_types:
            for st in self.project.support_types:
                name = getattr(st, "_display_name", st.DISPLAY_NAME)
                self.cbo_type.addItem(name, st.TYPE_ID)
        else:
            self.cbo_type.addItem(
                "(no support types — open Define Support first)", "",
            )
            self.cbo_type.setEnabled(False)
        ftype.addRow(tr("Type:"), self.cbo_type)
        layout.addWidget(gtype)

        # 2. Geometry
        ggeom = QGroupBox(tr("Geometry"))
        fgeom = QFormLayout(ggeom)
        self.spn_length = QDoubleSpinBox()
        self.spn_length.setRange(0.01, 1e6)
        self.spn_length.setSuffix(" m")
        self.spn_length.setValue(6.0)
        fgeom.addRow(tr("Length:"), self.spn_length)

        self.spn_spacing = QDoubleSpinBox()
        self.spn_spacing.setRange(0.01, 1e6)
        self.spn_spacing.setSuffix(" m")
        self.spn_spacing.setValue(1.5)
        fgeom.addRow(tr("In-plane spacing:"), self.spn_spacing)
        layout.addWidget(ggeom)

        # 3. Orientation
        gori = QGroupBox(tr("Orientation along boundary"))
        fori = QFormLayout(gori)
        self.cbo_orientation = QComboBox()
        self.cbo_orientation.addItem(
            "Angle from horizontal", "angle",
        )
        self.cbo_orientation.addItem(
            "Perpendicular to boundary", "normal",
        )
        self.cbo_orientation.addItem(
            "Vertical (depth)", "depth",
        )
        self.cbo_orientation.currentIndexChanged.connect(self._on_ori_changed)
        fori.addRow(tr("Mode:"), self.cbo_orientation)

        self.spn_angle = QDoubleSpinBox()
        self.spn_angle.setRange(-180, 180)
        self.spn_angle.setSuffix(" °")
        self.spn_angle.setValue(-15.0)
        fori.addRow(tr("Angle:"), self.spn_angle)

        self.chk_flip = QCheckBox(tr("Flip angle 180°"))
        fori.addRow("", self.chk_flip)
        layout.addWidget(gori)

        # 4. Force application & orientation (defaults overridable here)
        gapp = QGroupBox(tr("Force application"))
        fapp = QFormLayout(gapp)
        self.cbo_app = QComboBox()
        for fa in ForceApplication:
            self.cbo_app.addItem(fa.value.capitalize(), fa)
        fapp.addRow(tr("Application:"), self.cbo_app)
        self.cbo_force_ori = QComboBox()
        for fo in ForceOrientation:
            self.cbo_force_ori.addItem(fo.value.replace("_", " ").title(), fo)
        fapp.addRow(tr("Force direction:"), self.cbo_force_ori)
        layout.addWidget(gapp)

        # OK / Cancel
        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _on_ori_changed(self, _idx: int) -> None:
        mode = self.cbo_orientation.currentData()
        self.spn_angle.setEnabled(mode == "angle")

    def accept(self) -> None:
        type_id = self.cbo_type.currentData()
        if not type_id:
            self.reject()
            return
        self.pattern = SupportPattern(
            type_id=type_id,
            length=self.spn_length.value(),
            spacing=self.spn_spacing.value(),
            orientation_mode=self.cbo_orientation.currentData(),
            angle_deg=self.spn_angle.value(),
            flip_180=self.chk_flip.isChecked(),
            force_application=self.cbo_app.currentData(),
            orientation=self.cbo_force_ori.currentData(),
        )
        super().accept()
