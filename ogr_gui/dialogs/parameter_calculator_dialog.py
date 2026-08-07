# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Parameter Calculator dialog — phase M6.

Derives the Generalised Hoek-Brown constants from GSI, mi and D, updating
live as the inputs change.

The guidance tables are shown next to the fields rather than hidden behind
help, because GSI and D are **judgement-based** quantities: a number typed
without that context is the usual source of a wrong Hoek-Brown envelope,
and no amount of precision downstream repairs it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_core.materials import (
    DISTURBANCE_GUIDANCE,
    GSI_GUIDANCE,
    MI_GUIDANCE,
    calculate_hoek_brown,
)
from ogr_gui.i18n import tr


class ParameterCalculatorDialog(QDialog):
    """GSI, mi and D in; mb, s and a out."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Parameter Calculator"))
        self.resize(520, 480)
        self.result_params = None

        v = QVBoxLayout(self)

        gb_in = QGroupBox(tr("Input"))
        f = QFormLayout(gb_in)

        self.sp_gsi = QDoubleSpinBox()
        self.sp_gsi.setRange(0.0, 100.0)
        self.sp_gsi.setDecimals(1)
        self.sp_gsi.setValue(50.0)
        f.addRow(tr("GSI:"), self.sp_gsi)
        self.cbo_gsi = QComboBox()
        self.cbo_gsi.addItem(tr("(pick a rock mass description)"), None)
        for value, text in GSI_GUIDANCE:
            self.cbo_gsi.addItem(f"{value} — {text}", value)
        self.cbo_gsi.currentIndexChanged.connect(self._pick_gsi)
        f.addRow("", self.cbo_gsi)

        self.sp_mi = QDoubleSpinBox()
        self.sp_mi.setRange(0.0, 100.0)
        self.sp_mi.setDecimals(2)
        self.sp_mi.setValue(10.0)
        f.addRow(tr("mi:"), self.sp_mi)
        self.cbo_mi = QComboBox()
        self.cbo_mi.addItem(tr("(pick a lithology)"), None)
        for name, value in MI_GUIDANCE:
            self.cbo_mi.addItem(f"{name} — {value}", value)
        self.cbo_mi.currentIndexChanged.connect(self._pick_mi)
        f.addRow("", self.cbo_mi)

        self.sp_d = QDoubleSpinBox()
        self.sp_d.setRange(0.0, 2.0)
        self.sp_d.setDecimals(2)
        self.sp_d.setSingleStep(0.1)
        self.sp_d.setValue(0.0)
        f.addRow(tr("Disturbance factor D:"), self.sp_d)
        self.cbo_d = QComboBox()
        self.cbo_d.addItem(tr("(pick an excavation method)"), None)
        for value, text in DISTURBANCE_GUIDANCE:
            self.cbo_d.addItem(f"{value} — {text}", value)
        self.cbo_d.currentIndexChanged.connect(self._pick_d)
        f.addRow("", self.cbo_d)
        v.addWidget(gb_in)

        gb_out = QGroupBox(tr("Calculated"))
        fo = QFormLayout(gb_out)
        self.lbl_mb = QLabel("—")
        self.lbl_s = QLabel("—")
        self.lbl_a = QLabel("—")
        fo.addRow("mb:", self.lbl_mb)
        fo.addRow("s:", self.lbl_s)
        fo.addRow("a:", self.lbl_a)
        self.lbl_note = QLabel("")
        self.lbl_note.setWordWrap(True)
        fo.addRow("", self.lbl_note)
        v.addWidget(gb_out)

        note = QLabel(tr(
            "GSI and D are judgement-based: use the descriptions above "
            "rather than a remembered number. Equations from Hoek, "
            "Carranza-Torres and Corkum (2002)."))
        note.setWordWrap(True)
        v.addWidget(note)
        v.addStretch(1)

        for w in (self.sp_gsi, self.sp_mi, self.sp_d):
            w.valueChanged.connect(self._recalculate)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Use these values"))
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._recalculate()

    # ------------------------------------------------------------------
    def _pick_gsi(self, _i) -> None:
        value = self.cbo_gsi.currentData()
        if value is not None:
            self.sp_gsi.setValue(float(value))

    def _pick_mi(self, _i) -> None:
        value = self.cbo_mi.currentData()
        if value is not None:
            self.sp_mi.setValue(float(value))

    def _pick_d(self, _i) -> None:
        value = self.cbo_d.currentData()
        if value is not None:
            self.sp_d.setValue(float(value))

    def _recalculate(self, *_a) -> None:
        r = calculate_hoek_brown(self.sp_gsi.value(), self.sp_mi.value(),
                                 self.sp_d.value())
        self.result_params = r
        self.lbl_mb.setText(f"{r.mb:.4f}")
        # s spans many orders of magnitude, so a fixed number of decimals
        # would show 0.000000 for a poor rock mass.
        self.lbl_s.setText(f"{r.s:.3e}" if r.s < 1e-3 else f"{r.s:.6f}")
        self.lbl_a.setText(f"{r.a:.4f}")
        self.lbl_note.setText("\n".join(r.notes))

    def _accept(self) -> None:
        self._recalculate()
        self.accept()
