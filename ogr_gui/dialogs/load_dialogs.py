# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Load dialogs for Distributed and Line loads.

Reactive UI: the angle field is enabled only for ANGLE_FROM_HORIZONTAL
or ANGLE_TO_BOUNDARY orientations. The "magnitude 2" field is enabled
only for non-CONSTANT distributions.

Author: Samuel Sáez López (UPCT).
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
    QLabel,
    QVBoxLayout,
)

from ogr_core.loads import LoadDistribution, LoadOrientation
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class _BaseLoadDialog(QDialog):
    """Common UI scaffolding for distributed/line load definition."""

    def __init__(
        self,
        title: str,
        magnitude_unit: str,
        show_distribution: bool,
        existing=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(440, self.sizeHint().height())

        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            f"<b>{title}</b><br>"
            f"Magnitude in {magnitude_unit}. Always positive — "
            f"direction is set by Orientation."
        ))

        form = QFormLayout()

        # Magnitude 1
        self.sb_mag1 = QDoubleSpinBox()
        self.sb_mag1.setRange(0.0, 1e9)
        self.sb_mag1.setDecimals(3)
        self.sb_mag1.setSuffix(f" {magnitude_unit}")
        form.addRow(tr("Magnitude:"), self.sb_mag1)

        # Distribution (only for distributed loads)
        self.cb_distribution: QComboBox | None = None
        self.sb_mag2: QDoubleSpinBox | None = None
        if show_distribution:
            self.cb_distribution = QComboBox()
            for d in LoadDistribution:
                self.cb_distribution.addItem(d.value.title(), d)
            form.addRow(tr("Distribution:"), self.cb_distribution)

            self.sb_mag2 = QDoubleSpinBox()
            self.sb_mag2.setRange(0.0, 1e9)
            self.sb_mag2.setDecimals(3)
            self.sb_mag2.setSuffix(f" {magnitude_unit}")
            form.addRow(tr("Magnitude (end):"), self.sb_mag2)

        # Orientation
        self.cb_orientation = QComboBox()
        self._orientations = [
            (LoadOrientation.NORMAL_TO_BOUNDARY, "Normal to Boundary"),
            (LoadOrientation.VERTICAL, "Vertical (default downward)"),
            (LoadOrientation.HORIZONTAL, "Horizontal (against failure dir.)"),
            (LoadOrientation.ANGLE_FROM_HORIZONTAL, "Angle from Horizontal"),
            (LoadOrientation.ANGLE_TO_BOUNDARY, "Angle to Boundary"),
        ]
        for orient, label in self._orientations:
            self.cb_orientation.addItem(label, orient)
        form.addRow(tr("Orientation:"), self.cb_orientation)

        # Angle (only for angle-based orientations)
        self.sb_angle = QDoubleSpinBox()
        self.sb_angle.setRange(-360.0, 360.0)
        self.sb_angle.setDecimals(2)
        self.sb_angle.setSuffix(" °")
        self.sb_angle.setToolTip(
            "Positive angle = counter-clockwise from the +X axis "
            "(or from the boundary direction)."
        )
        form.addRow(tr("Angle:"), self.sb_angle)

        # Excess pore pressure (only relevant in B-bar mode)
        self.cb_excess = QCheckBox(
            tr("Load creates excess pore pressure (B-bar method)")
        )
        self.cb_excess.setToolTip(
            "Only the vertical component of the load contributes to\n"
            "excess pore pressure on undrained materials with B-bar > 0."
        )
        form.addRow("", self.cb_excess)

        root.addLayout(form)

        # Pre-fill with existing values
        if existing is not None:
            self.sb_mag1.setValue(existing.magnitude_1)
            if self.cb_distribution is not None:
                idx = self.cb_distribution.findData(existing.distribution)
                self.cb_distribution.setCurrentIndex(max(0, idx))
            if self.sb_mag2 is not None and existing.magnitude_2 is not None:
                self.sb_mag2.setValue(existing.magnitude_2)
            for i, (orient, _) in enumerate(self._orientations):
                if orient == existing.orientation:
                    self.cb_orientation.setCurrentIndex(i)
                    break
            self.sb_angle.setValue(existing.angle_deg)
            self.cb_excess.setChecked(getattr(existing, "excess_pp", False))

        # Reactive visibility
        self.cb_orientation.currentIndexChanged.connect(self._refresh)
        if self.cb_distribution is not None:
            self.cb_distribution.currentIndexChanged.connect(self._refresh)
        self._refresh()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _refresh(self) -> None:
        orient = self.cb_orientation.currentData()
        angle_active = orient in (
            LoadOrientation.ANGLE_FROM_HORIZONTAL,
            LoadOrientation.ANGLE_TO_BOUNDARY,
        )
        self.sb_angle.setEnabled(angle_active)
        if self.cb_distribution is not None and self.sb_mag2 is not None:
            dist = self.cb_distribution.currentData()
            self.sb_mag2.setEnabled(dist != LoadDistribution.CONSTANT)

    def magnitude_1(self) -> float:
        return self.sb_mag1.value()

    def magnitude_2(self) -> float | None:
        if self.sb_mag2 is None or not self.sb_mag2.isEnabled():
            return None
        return self.sb_mag2.value()

    def orientation(self) -> LoadOrientation:
        return self.cb_orientation.currentData()

    def angle_deg(self) -> float:
        return self.sb_angle.value() if self.sb_angle.isEnabled() else 0.0

    def distribution(self) -> LoadDistribution:
        if self.cb_distribution is None:
            return LoadDistribution.CONSTANT
        return self.cb_distribution.currentData()

    def excess_pp(self) -> bool:
        return self.cb_excess.isChecked()


# ======================================================================
class DistributedLoadDialog(_BaseLoadDialog):
    def __init__(self, existing=None, parent=None) -> None:
        super().__init__(
            title="Add Distributed Load",
            magnitude_unit="kN/m²",
            show_distribution=True,
            existing=existing,
            parent=parent,
        )


# ======================================================================
class LineLoadDialog(_BaseLoadDialog):
    def __init__(self, existing=None, parent=None) -> None:
        super().__init__(
            title="Add Line Load",
            magnitude_unit="kN/m",
            show_distribution=False,
            existing=existing,
            parent=parent,
        )
