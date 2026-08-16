# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Contour Options dialog — Interpret phase I2.

Collects the scalar field, the value range, the number of intervals, the
draw mode and the palette, following the specification's *Contour
Options* module.

Two choices worth stating:

* **The palette preview is live.** A list of palette names tells the user
  nothing; a strip of the actual colours does. The preview is drawn from
  the same sampling function the plot uses, so what is previewed is what
  will be drawn.
* **Auto-range is a checkbox, and there are one-shot buttons beside it.**
  Left on, the range follows the data as results change; switched off,
  the user's own bounds are kept. The buttons (*0 to 6*, *Fit to results*)
  set the bounds once and turn the checkbox off, which is the honest way
  to offer them: a "fit" that pretended to keep following the data would
  silently go stale the next time the method changed.
* **The range follows the scalar.** Switching field resets the bounds to
  that field's defaults, because a 0–6 range means everything for a
  factor of safety and nothing for a total head in metres.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ogr_gui.contours import (
    PALETTES,
    SCALAR_FIELDS,
    ContourMode,
    ContourSettings,
)
from ogr_gui.i18n import tr

_MODE_LABELS = [
    (ContourMode.FILLED, "Filled"),
    (ContourMode.FILLED_LINES, "Filled (with lines)"),
    (ContourMode.LINES, "Lines"),
    (ContourMode.SMOOTH, "Smooth gradient"),
    (ContourMode.OFF, "Off"),
]


class PalettePreview(QWidget):
    """A strip of the actual band colours."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = ContourSettings()
        self.setMinimumHeight(28)

    def set_settings(self, settings: ContourSettings) -> None:
        self._settings = settings
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        p = QPainter(self)
        colours = self._settings.band_colours()
        if not colours:
            p.end()
            return
        w = self.width() / len(colours)
        for i, c in enumerate(colours):
            p.fillRect(int(i * w), 0, int(w) + 1, self.height(),
                       QColor(c))
        p.setPen(QColor("#404040"))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.end()


class ContourOptionsDialog(QDialog):
    """Configure the contour plot."""

    def __init__(self, settings: ContourSettings, fields=None,
                 values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Contour Options"))
        self.resize(460, 480)
        self._values = list(values or [])
        self.settings = ContourSettings.from_dict(settings.to_dict())
        # The sample values belong to ONE field — the one that was active
        # when the dialog opened. Fitting a range to them after the user
        # picks a different scalar would fit metres of head to factors of
        # safety, so the fit is only offered while the field matches.
        self._values_field = self.settings.field

        v = QVBoxLayout(self)

        gb_f = QGroupBox(tr("Scalar field"))
        ff = QFormLayout(gb_f)
        self.cbo_field = QComboBox()
        for key in (fields or ["fos"]):
            self.cbo_field.addItem(tr(SCALAR_FIELDS.get(key, key)), key)
        i = self.cbo_field.findData(self.settings.field)
        self.cbo_field.setCurrentIndex(max(0, i))
        ff.addRow(tr("Show:"), self.cbo_field)
        v.addWidget(gb_f)

        gb_r = QGroupBox(tr("Range"))
        fr = QFormLayout(gb_r)
        self.chk_auto = QCheckBox(tr("Automatic range from the results"))
        self.chk_auto.setChecked(self.settings.auto_range)
        self.chk_auto.setToolTip(tr(
            "Left on, the range follows the data as results change. The "
            "upper bound uses a percentile so a single extreme value "
            "cannot squash everything else into one band."))
        self.chk_auto.toggled.connect(self._on_auto_toggled)
        fr.addRow("", self.chk_auto)
        self.sp_min = QDoubleSpinBox()
        self.sp_min.setDecimals(4)
        self.sp_min.setRange(-1e9, 1e9)
        self.sp_min.setValue(self.settings.vmin)
        fr.addRow(tr("Minimum:"), self.sp_min)
        self.sp_max = QDoubleSpinBox()
        self.sp_max.setDecimals(4)
        self.sp_max.setRange(-1e9, 1e9)
        self.sp_max.setValue(self.settings.vmax)
        fr.addRow(tr("Maximum:"), self.sp_max)
        self.sp_int = QSpinBox()
        self.sp_int.setRange(2, 40)
        self.sp_int.setValue(self.settings.intervals)
        fr.addRow(tr("Number of intervals:"), self.sp_int)
        self.lbl_step = QLabel("")
        fr.addRow(tr("Interval size:"), self.lbl_step)
        # v0.1.82 — the reference's two one-click ranges. "0 to 6" is the
        # published default for a factor of safety and the range every
        # comparison against the reference has to be read in; "Fit to
        # results" is the one-shot version of the checkbox above, for
        # when the user wants today's data but not a range that keeps
        # moving under them.
        row = QWidget()
        hb = QVBoxLayout(row)
        hb.setContentsMargins(0, 0, 0, 0)
        self.btn_0to6 = QPushButton(tr("0 to 6"))
        self.btn_0to6.setToolTip(tr(
            "Restore the default factor-of-safety range: 0 to 6 in 24 "
            "intervals of 0.25."))
        self.btn_0to6.clicked.connect(self._range_0_to_6)
        self.btn_fit = QPushButton(tr("Fit to results"))
        self.btn_fit.setToolTip(tr(
            "Set the range from the values actually present, once."))
        self.btn_fit.clicked.connect(self._range_fit)
        hb.addWidget(self.btn_0to6)
        hb.addWidget(self.btn_fit)
        fr.addRow("", row)
        v.addWidget(gb_r)

        gb_s = QGroupBox(tr("Appearance"))
        fs = QFormLayout(gb_s)
        self.cbo_mode = QComboBox()
        for mode, label in _MODE_LABELS:
            self.cbo_mode.addItem(tr(label), mode)
        j = self.cbo_mode.findData(self.settings.mode)
        self.cbo_mode.setCurrentIndex(max(0, j))
        fs.addRow(tr("Mode:"), self.cbo_mode)
        self.cbo_palette = QComboBox()
        for name in PALETTES:
            self.cbo_palette.addItem(name, name)
        k = self.cbo_palette.findData(self.settings.palette)
        self.cbo_palette.setCurrentIndex(max(0, k))
        fs.addRow(tr("Palette:"), self.cbo_palette)
        self.chk_rev = QCheckBox(tr("Reverse colours"))
        self.chk_rev.setChecked(self.settings.reverse)
        fs.addRow("", self.chk_rev)
        self.preview = PalettePreview()
        fs.addRow(tr("Preview:"), self.preview)
        v.addWidget(gb_s)

        gb_n = QGroupBox(tr("Number format"))
        fn = QFormLayout(gb_n)
        self.sp_dec = QSpinBox()
        self.sp_dec.setRange(0, 8)
        self.sp_dec.setValue(self.settings.decimals)
        fn.addRow(tr("Decimal places:"), self.sp_dec)
        self.chk_sci = QCheckBox(tr("Scientific notation"))
        self.chk_sci.setChecked(self.settings.scientific)
        fn.addRow("", self.chk_sci)
        v.addWidget(gb_n)

        for w in (self.sp_min, self.sp_max, self.sp_int, self.sp_dec):
            w.valueChanged.connect(self._refresh)
        for w in (self.cbo_mode, self.cbo_palette):
            w.currentIndexChanged.connect(self._refresh)
        self.cbo_field.currentIndexChanged.connect(self._on_field_changed)
        for w in (self.chk_rev, self.chk_sci):
            w.toggled.connect(self._refresh)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                              | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
            self._defaults)
        v.addWidget(bb)

        self._on_auto_toggled(self.chk_auto.isChecked())
        self._refresh()

    # ------------------------------------------------------------------
    def _fittable(self) -> bool:
        """True when the sample values belong to the selected field."""
        return bool(self._values) and (
            (self.cbo_field.currentData() or "fos") == self._values_field)

    def _on_auto_toggled(self, on: bool) -> None:
        self.sp_min.setEnabled(not on)
        self.sp_max.setEnabled(not on)
        self.btn_fit.setEnabled(self._fittable())
        if on and self._fittable():
            probe = ContourSettings.from_dict(self.settings.to_dict())
            probe.fit_to(self._values)
            self.sp_min.blockSignals(True)
            self.sp_max.blockSignals(True)
            self.sp_min.setValue(probe.vmin)
            self.sp_max.setValue(probe.vmax)
            self.sp_min.blockSignals(False)
            self.sp_max.blockSignals(False)
        self._refresh()

    def _collect(self) -> ContourSettings:
        return ContourSettings(
            mode=self.cbo_mode.currentData(),
            palette=self.cbo_palette.currentData(),
            vmin=self.sp_min.value(),
            vmax=self.sp_max.value(),
            intervals=self.sp_int.value(),
            reverse=self.chk_rev.isChecked(),
            auto_range=self.chk_auto.isChecked(),
            field=self.cbo_field.currentData() or "fos",
            decimals=self.sp_dec.value(),
            scientific=self.chk_sci.isChecked(),
            opacity=self.settings.opacity,
        )

    def _refresh(self, *_a) -> None:
        s = self._collect()
        self.preview.set_settings(s)
        step = s.span / max(1, s.intervals)
        self.lbl_step.setText(s.format_value(step))

    def _on_field_changed(self, *_a) -> None:
        """A different scalar needs a different range, not the last one."""
        self._defaults()

    def _range_0_to_6(self) -> None:
        self.chk_auto.setChecked(False)
        self.sp_min.setValue(0.0)
        self.sp_max.setValue(6.0)
        self.sp_int.setValue(24)
        self._refresh()

    def _range_fit(self) -> None:
        if not self._fittable():
            return
        probe = self._collect()
        probe.fit_to(self._values)
        self.chk_auto.setChecked(False)
        self.sp_min.setValue(probe.vmin)
        self.sp_max.setValue(probe.vmax)
        self._refresh()

    def _defaults(self) -> None:
        fresh = ContourSettings.for_field(
            self.cbo_field.currentData() or "fos")
        if fresh.auto_range and self._fittable():
            fresh.fit_to(self._values)
        self.sp_min.setValue(fresh.vmin)
        self.sp_max.setValue(fresh.vmax)
        self.sp_int.setValue(fresh.intervals)
        self.sp_dec.setValue(fresh.decimals)
        self.chk_auto.setChecked(fresh.auto_range)
        self.chk_rev.setChecked(False)
        self.cbo_mode.setCurrentIndex(
            self.cbo_mode.findData(ContourMode.FILLED))
        self.cbo_palette.setCurrentIndex(
            self.cbo_palette.findData(fresh.palette))
        self._refresh()

    def _accept(self) -> None:
        self.settings = self._collect()
        self.accept()
