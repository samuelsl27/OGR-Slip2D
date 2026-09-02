# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Define Slope Limits dialog (v0.1.146).

The Slope Limits are the stretch of ground within which a slip surface is
allowed to daylight. They do two jobs: they FILTER every surface, whatever
the search, and they define the piece of ground the surfaces that generate
from the profile are built on.

This dialog exists because of defect **D50**: a model may declare a SECOND
window, so that "may daylight anywhere between here and there" can become
"may daylight in this window near the toe, or in that one near the crest".
Two chained input boxes were enough for one pair; four would not be, and
they gave no way to say the second pair is off.

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


# ======================================================================
class SlopeLimitsDialog(QDialog):
    """Edit one or two sets of Slope Limits.

    The automatic state (``None``) is kept distinct from an explicit
    value. Before v0.1.146 the editor showed ``None`` as ``0.0``, so a
    model on automatic limits was indistinguishable from one limited at
    x = 0, and merely opening the editor and accepting turned the first
    into the second. Here the spin boxes start on the ground profile's own
    extent — which is what automatic MEANS — and the reset button is the
    documented way back.
    """

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Define Slope Limits"))
        self.project = project
        s = project.settings.search

        # The ground's own extent: the default the reference puts the
        # markers at when the External Boundary is created, and the
        # sensible starting point for a model that has never set them.
        lo, hi = self._ground_extent()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            tr("Slip surfaces must daylight within these limits. "
               "Positions are X coordinates.")))

        self.first = QGroupBox(tr("First set of limits"))
        f1 = QFormLayout(self.first)
        self.left_1 = self._spin(
            s.slope_limit_left if s.slope_limit_left is not None else lo)
        self.right_1 = self._spin(
            s.slope_limit_right if s.slope_limit_right is not None else hi)
        f1.addRow(tr("Left limit (x):"), self.left_1)
        f1.addRow(tr("Right limit (x):"), self.right_1)
        layout.addWidget(self.first)

        # The second set is defined ON TOP of the first, never instead of
        # it, so it lives behind a checkbox rather than as four equal
        # boxes: an empty pair of boxes cannot say "there is no second
        # window", and a window nobody meant to declare would silently
        # narrow every search.
        self.second_on = QCheckBox(tr("Second set of limits"))
        self.second_on.setChecked(s.slope_limit_left_2 is not None
                                  and s.slope_limit_right_2 is not None)
        layout.addWidget(self.second_on)

        self.second = QGroupBox(tr("Second set of limits"))
        f2 = QFormLayout(self.second)
        span = max(hi - lo, 1e-6)
        self.left_2 = self._spin(
            s.slope_limit_left_2 if s.slope_limit_left_2 is not None
            else lo + 0.6 * span)
        self.right_2 = self._spin(
            s.slope_limit_right_2 if s.slope_limit_right_2 is not None
            else hi)
        f2.addRow(tr("Left limit (x):"), self.left_2)
        f2.addRow(tr("Right limit (x):"), self.right_2)
        layout.addWidget(self.second)

        self.second.setEnabled(self.second_on.isChecked())
        self.second_on.toggled.connect(self.second.setEnabled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Reset)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Reset).setText(tr("Reset"))
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self._reset)
        layout.addWidget(buttons)

        self._reset_requested = False

    # ------------------------------------------------------------------
    @staticmethod
    def _spin(value: float) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(4)
        box.setRange(-1e9, 1e9)
        box.setValue(float(value))
        return box

    def _ground_extent(self) -> tuple:
        """The x-extent of the ground profile, or a bare fallback."""
        try:
            xmin, _ymin, xmax, _ymax = self.project.bounding_box()
            if xmax > xmin:
                return float(xmin), float(xmax)
        except Exception:  # noqa: BLE001
            pass
        return 0.0, 1.0

    def _reset(self) -> None:
        """Back to automatic — the same thing the menu's Reset does."""
        self._reset_requested = True
        self.accept()

    # ------------------------------------------------------------------
    def validate(self) -> str:
        """The reason this cannot be applied, or an empty string.

        Separate from :meth:`accept` so a test can ask the question
        without a modal dialog, which is the one thing an offscreen test
        cannot survive.
        """
        if self._reset_requested:
            return ""
        if self.right_1.value() <= self.left_1.value():
            return tr("The right limit must be greater than the left one.")
        if not self.second_on.isChecked():
            return ""
        if self.right_2.value() <= self.left_2.value():
            return tr("The right limit must be greater than the left one.")
        # The reference does not let a marker be dragged past another, and
        # overlapping windows are not a second window at all: their union
        # is one wider span, which the first set alone could already say.
        if self.left_2.value() <= self.right_1.value():
            return tr("The second set of limits must lie entirely to the "
                      "right of the first.")
        return ""

    def values(self) -> tuple:
        """``(left, right, left_2, right_2)``, with None meaning automatic."""
        if self._reset_requested:
            return (None, None, None, None)
        if not self.second_on.isChecked():
            return (self.left_1.value(), self.right_1.value(), None, None)
        return (self.left_1.value(), self.right_1.value(),
                self.left_2.value(), self.right_2.value())
