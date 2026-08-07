# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Snap dialog — phase M1.

Configures the snap engine that already lives in the canvas
(``ogr_gui/canvas/snap_engine.py``). The engine supported grid spacing,
per-kind capture tolerances and an ortho angle window from the start;
none of it was reachable from the interface.

Two points of design:

* **Tolerances are in pixels, and the dialog says so.** They are
  converted to model units by the canvas, which is what keeps snapping
  equally easy at any zoom. A tolerance expressed in metres would get
  harder to use the further you zoomed out, so the units are labelled to
  stop anyone "fixing" them.
* **The dialog edits the live settings object.** The status-bar words read
  the same object, so the two stay in step without a synchronisation
  step — and the main window pushes the three constraints back onto the
  labels on accept.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_gui.data_tips import DataTipMode
from ogr_gui.i18n import tr

_TIP_LABELS = [
    (DataTipMode.NONE, "None"),
    (DataTipMode.MINIMUM, "Minimum"),
    (DataTipMode.MAXIMUM, "Maximum"),
]


def _spin(value, lo=0.0, hi=1e6, decimals=3, step=1.0):
    sp = QDoubleSpinBox()
    sp.setDecimals(decimals)
    sp.setRange(lo, hi)
    sp.setSingleStep(step)
    sp.setValue(float(value))
    return sp


class SnapDialog(QDialog):
    """Snap, ortho, object snap and data tips."""

    def __init__(self, snap_settings, data_tip_mode=DataTipMode.MAXIMUM,
                 parent=None):
        super().__init__(parent)
        self.settings = snap_settings          # edited in place
        self.data_tip_mode = data_tip_mode
        self.setWindowTitle(tr("Snap"))
        self.resize(460, 520)

        v = QVBoxLayout(self)

        gb_m = QGroupBox(tr("Constraints"))
        fm = QVBoxLayout(gb_m)
        self.chk_snap = QCheckBox(tr("Grid snap (F9)"))
        self.chk_snap.setChecked(bool(snap_settings.snap))
        self.chk_ortho = QCheckBox(tr("Orthogonal (F8)"))
        self.chk_ortho.setChecked(bool(snap_settings.ortho))
        self.chk_osnap = QCheckBox(tr("Object snap (F3)"))
        self.chk_osnap.setChecked(bool(snap_settings.osnap))
        for w in (self.chk_snap, self.chk_ortho, self.chk_osnap):
            fm.addWidget(w)
        v.addWidget(gb_m)

        gb_g = QGroupBox(tr("Grid spacing"))
        fg = QFormLayout(gb_g)
        self.sp_gh = _spin(getattr(snap_settings, "grid_h", 1.0),
                           lo=1e-6, decimals=4, step=0.5)
        self.sp_gv = _spin(getattr(snap_settings, "grid_v", 1.0),
                           lo=1e-6, decimals=4, step=0.5)
        fg.addRow(tr("Horizontal:"), self.sp_gh)
        fg.addRow(tr("Vertical:"), self.sp_gv)
        v.addWidget(gb_g)

        gb_t = QGroupBox(tr("Capture tolerances"))
        ft = QFormLayout(gb_t)
        self.sp_vertex = _spin(snap_settings.vertex_tolerance_px,
                               lo=1.0, hi=100.0, decimals=1)
        self.sp_line = _spin(snap_settings.line_tolerance_px,
                             lo=1.0, hi=100.0, decimals=1)
        self.sp_grid = _spin(snap_settings.grid_tolerance_px,
                             lo=1.0, hi=100.0, decimals=1)
        self.sp_ext = _spin(snap_settings.extension_tolerance_px,
                            lo=1.0, hi=100.0, decimals=1)
        for label, w in ((tr("Vertex:"), self.sp_vertex),
                         (tr("Line:"), self.sp_line),
                         (tr("Grid node:"), self.sp_grid),
                         (tr("Extension:"), self.sp_ext)):
            w.setSuffix(" px")
            ft.addRow(label, w)
        note = QLabel(tr(
            "Tolerances are in SCREEN PIXELS. The canvas converts them to "
            "model units, which is what keeps snapping equally easy at "
            "any zoom; a tolerance in metres would get harder to use the "
            "further you zoomed out."))
        note.setWordWrap(True)
        ft.addRow("", note)
        self.sp_angle = _spin(snap_settings.ortho_snap_angle_deg,
                              lo=0.0, hi=45.0, decimals=1)
        self.sp_angle.setSuffix(" °")
        self.sp_angle.setToolTip(tr(
            "Orthogonal locks the movement to an axis when the cursor is "
            "within this angle of horizontal or vertical."))
        ft.addRow(tr("Orthogonal window:"), self.sp_angle)
        v.addWidget(gb_t)

        gb_d = QGroupBox(tr("Data tips"))
        fd = QFormLayout(gb_d)
        self.cbo_tips = QComboBox()
        for mode, label in _TIP_LABELS:
            self.cbo_tips.addItem(tr(label), mode)
        i = self.cbo_tips.findData(data_tip_mode)
        self.cbo_tips.setCurrentIndex(max(0, i))
        self.cbo_tips.setToolTip(tr(
            "Hovering over a material, support or load shows its "
            "properties. 'Minimum' shows only the identity, enough to "
            "tell two objects apart while drawing."))
        fd.addRow(tr("Show:"), self.cbo_tips)
        v.addWidget(gb_d)

        v.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                              | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
            self._defaults)
        v.addWidget(bb)

    # ------------------------------------------------------------------
    def _defaults(self) -> None:
        from ogr_gui.canvas.snap_engine import SnapSettings
        d = SnapSettings()
        self.chk_snap.setChecked(d.snap)
        self.chk_ortho.setChecked(d.ortho)
        self.chk_osnap.setChecked(d.osnap)
        self.sp_gh.setValue(d.grid_h)
        self.sp_gv.setValue(d.grid_v)
        self.sp_vertex.setValue(d.vertex_tolerance_px)
        self.sp_line.setValue(d.line_tolerance_px)
        self.sp_grid.setValue(d.grid_tolerance_px)
        self.sp_ext.setValue(d.extension_tolerance_px)
        self.sp_angle.setValue(d.ortho_snap_angle_deg)
        self.cbo_tips.setCurrentIndex(
            self.cbo_tips.findData(DataTipMode.MAXIMUM))

    def _accept(self) -> None:
        s = self.settings
        s.snap = self.chk_snap.isChecked()
        s.ortho = self.chk_ortho.isChecked()
        s.osnap = self.chk_osnap.isChecked()
        s.grid_h = self.sp_gh.value()
        s.grid_v = self.sp_gv.value()
        s.vertex_tolerance_px = self.sp_vertex.value()
        s.line_tolerance_px = self.sp_line.value()
        s.grid_tolerance_px = self.sp_grid.value()
        s.extension_tolerance_px = self.sp_ext.value()
        s.ortho_snap_angle_deg = self.sp_angle.value()
        self.data_tip_mode = self.cbo_tips.currentData()
        self.accept()
