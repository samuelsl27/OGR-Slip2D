# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Undrained envelope editor for the multi-stage rapid-drawdown procedures.

Why this is a dialog of its own rather than three more rows in the
material editor: the envelope is only meaningful for a material that
behaves undrained, in a project that runs a multi-stage drawdown — a
combination that is rare enough that keeping its five widgets permanently
on screen cost every other user the space. The reference reaches it the
same way, through a *Define Strength* button.

Either form of the envelope is accepted, because the conversion between
them is exact and biyective (see
:mod:`ogr_core.materials.drawdown_envelopes`), so nothing is lost by
entering the one the laboratory report happens to give:

* **Total stress R envelope** — ``τ = c_R + σ·tan φ_R``, what the Army
  Corps two-stage procedure uses directly.
* **Kc = 1 envelope** — ``τ_ff = d + σ'_fc·tan ψ``, what Duncan, Wright &
  Wong (1990) and Lowe & Karafiath (1960) use.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from ogr_core.materials.drawdown_envelopes import Kc1Envelope, REnvelope
from ogr_gui.i18n import tr


def envelope_summary(envelope) -> str:
    """One-line description of an envelope, for the button's side label.

    Kept next to the dialog that edits the envelope so the two cannot
    drift apart, and exported because the material editor shows it
    WITHOUT opening this dialog — the whole point of moving the fields
    behind a button is that the value stays visible anyway.
    """
    if isinstance(envelope, REnvelope):
        return tr("R: Cr = %.4g, φR = %.4g°") % (
            envelope.c_r, envelope.phi_r_deg)
    if isinstance(envelope, Kc1Envelope):
        return tr("Kc = 1: d = %.4g, ψ = %.4g°") % (
            envelope.d, envelope.psi_deg)
    return tr("(none)")


class DrawdownStrengthDialog(QDialog):
    """Editor for a material's undrained (rapid-drawdown) envelope."""

    def __init__(self, envelope=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Define Strength"))
        root = QVBoxLayout(self)

        note = QLabel(tr(
            "Undrained envelope from isotropically consolidated undrained "
            "tests. Either form is accepted: the conversion between them "
            "is exact, and each procedure is given the one it needs."))
        note.setWordWrap(True)
        root.addWidget(note)

        form = QFormLayout()
        root.addLayout(form)

        self.cbo_kind = QComboBox()
        self.cbo_kind.addItem(tr("(none)"), None)
        self.cbo_kind.addItem(tr("Total Stress R Envelope"), "r")
        self.cbo_kind.addItem(tr("Kc = 1 Envelope"), "kc1")

        self.dsp_a = QDoubleSpinBox()
        self.dsp_a.setRange(0.0, 1e6)
        self.dsp_a.setDecimals(3)
        self.dsp_b = QDoubleSpinBox()
        self.dsp_b.setRange(0.0, 89.0)
        self.dsp_b.setDecimals(3)
        self.dsp_b.setSuffix(" °")
        self.lbl_a = QLabel(tr("Cr:"))
        self.lbl_b = QLabel(tr("Angle:"))

        form.addRow(tr("Undrained envelope:"), self.cbo_kind)
        form.addRow(self.lbl_a, self.dsp_a)
        form.addRow(self.lbl_b, self.dsp_b)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self.cbo_kind.currentIndexChanged.connect(self._refresh)
        self.set_envelope(envelope)

    # ------------------------------------------------------------------
    def set_envelope(self, envelope) -> None:
        """Populate the widgets from an envelope (or None)."""
        self.cbo_kind.blockSignals(True)
        if isinstance(envelope, REnvelope):
            self.cbo_kind.setCurrentIndex(self.cbo_kind.findData("r"))
            self.dsp_a.setValue(envelope.c_r)
            self.dsp_b.setValue(envelope.phi_r_deg)
        elif isinstance(envelope, Kc1Envelope):
            self.cbo_kind.setCurrentIndex(self.cbo_kind.findData("kc1"))
            self.dsp_a.setValue(envelope.d)
            self.dsp_b.setValue(envelope.psi_deg)
        else:
            self.cbo_kind.setCurrentIndex(0)
            self.dsp_a.setValue(0.0)
            self.dsp_b.setValue(0.0)
        self.cbo_kind.blockSignals(False)
        self._refresh()

    def envelope(self):
        """The envelope the widgets describe: ``REnvelope``, ``Kc1Envelope``
        or None."""
        kind = self.cbo_kind.currentData()
        if kind == "r":
            return REnvelope(c_r=self.dsp_a.value(),
                             phi_r_deg=self.dsp_b.value())
        if kind == "kc1":
            return Kc1Envelope(d=self.dsp_a.value(),
                               psi_deg=self.dsp_b.value())
        return None

    # ------------------------------------------------------------------
    def _refresh(self, *_args) -> None:
        """Name the two fields after the form chosen, and grey them when
        there is no envelope to describe."""
        kind = self.cbo_kind.currentData()
        on = kind is not None
        self.dsp_a.setEnabled(on)
        self.dsp_b.setEnabled(on)
        self.lbl_a.setText(tr("Cr:") if kind != "kc1" else tr("d:"))
        self.lbl_b.setText(tr("Angle:") if kind != "kc1" else tr("Psi:"))
