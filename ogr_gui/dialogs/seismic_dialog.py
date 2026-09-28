# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Seismic Load dialog (v0.1.9).

Pseudo-static seismic inertial body force applied to every slice.
Per the reference's convention:
    F = W · k_h (horizontal, in failure direction)
    F = W · k_v (vertical, +ve downward)

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)
from ogr_core.project.rules import SEISMIC_COEFFICIENT_LIMIT
from ogr_gui.i18n import tr  # noqa: E402

#: Decimals of the two spin boxes, and the largest magnitude they can hold:
#: one step inside the limit that ``rules.seismic_coefficient_refusal``
#: enforces for the API, so the two cannot disagree. v0.1.214 — the range
#: was ±1 exactly, which the API refused and which, with ``kv`` positive
#: downward (D170), is a soil with no weight at ``kv = −1``.
_DECIMALS = 3
_K_MAX = SEISMIC_COEFFICIENT_LIMIT - 10.0 ** -_DECIMALS


class SeismicLoadDialog(QDialog):
    """Edit the project's pseudo-static seismic load coefficients."""

    def __init__(self, seismic, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Seismic Load"))
        self.resize(420, self.sizeHint().height())
        self.seismic = seismic

        root = QVBoxLayout(self)
        # v0.1.219 (D206) — the force is proportional to the weight of the
        # slice's SOIL (loads and ponded water carry none), and k_h is a
        # magnitude: it always acts in the direction of failure, so it is
        # never negative (``rules.seismic_coefficient_refusal``).
        root.addWidget(QLabel(tr(
            "<b>Pseudo-static seismic load.</b><br>"
            "Applied to every slice as a body force proportional to the "
            "weight of its soil; distributed and line loads and ponded "
            "water carry none.<br><br>"
            "<i>k_h ≥ 0 → always in the direction of failure</i><br>"
            "<i>k_v positive → downward (gravity-like)</i>")))

        self.cb_enabled = QCheckBox(tr("Apply seismic load to compute"))
        self.cb_enabled.setChecked(seismic.enabled)
        root.addWidget(self.cb_enabled)

        form = QFormLayout()

        self.sb_kh = QDoubleSpinBox()
        self.sb_kh.setDecimals(_DECIMALS)
        # v0.1.219 (D206) — from zero: k_h is a magnitude.
        self.sb_kh.setRange(0.0, _K_MAX)
        self.sb_kh.setSingleStep(0.01)
        self.sb_kh.setValue(seismic.kh)
        # A negative k_h stored by an older version, a file or a script is
        # not silently turned into zero: the dialog says what it found.
        if float(seismic.kh) < 0.0:
            root.addWidget(QLabel(tr(
                "The stored k_h was negative (%g). k_h is a magnitude that "
                "always acts in the direction of failure: enter it positive."
            ) % float(seismic.kh)))
        self.sb_kh.setToolTip(
            "Horizontal seismic coefficient. Typical values:\n"
            "  0.05 — light shaking\n"
            "  0.10 — moderate (Eurocode 8 zone 2-3)\n"
            "  0.15-0.20 — strong (zone 4)\n"
            "  0.25+ — severe (Japan, California rural)"
        )
        form.addRow(tr("k_h (horizontal):"), self.sb_kh)

        self.sb_kv = QDoubleSpinBox()
        self.sb_kv.setDecimals(_DECIMALS)
        self.sb_kv.setRange(-_K_MAX, _K_MAX)
        self.sb_kv.setSingleStep(0.01)
        self.sb_kv.setValue(seismic.kv)
        self.sb_kv.setToolTip(
            "Vertical seismic coefficient. Often taken as 1/2 or 2/3 "
            "of k_h, or zero. Positive downward."
        )
        form.addRow(tr("k_v (vertical):"), self.sb_kv)

        root.addLayout(form)

        # Reactive: disable spinners when unchecked
        self.cb_enabled.toggled.connect(self.sb_kh.setEnabled)
        self.cb_enabled.toggled.connect(self.sb_kv.setEnabled)
        self.sb_kh.setEnabled(seismic.enabled)
        self.sb_kv.setEnabled(seismic.enabled)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def apply(self) -> None:
        """Write back into the seismic instance."""
        self.seismic.enabled = self.cb_enabled.isChecked()
        self.seismic.kh = self.sb_kh.value()
        self.seismic.kv = self.sb_kv.value()
