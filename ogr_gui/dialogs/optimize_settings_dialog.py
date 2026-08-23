# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Optimize Surfaces Settings (v0.1.104).

The panel behind the "Settings…" button that sits beside the *Optimize
Surfaces* checkbox in Surface Options. Twelve of the thirteen settings it
edits had no editor at all before this: they were declared in
``SearchSettings``, written to the ``.ogr`` and reachable only by editing
that file by hand — while the thirteenth, the checkbox itself, was
editable and read by no analysis. That whole pairing is defect D08.

Four groups, in the reference's own order, because the order is what makes
them legible: which surfaces get optimised, how the walk behaves, what to
do about surfaces that end up hugging the ground, and whether the search's
own surface checks apply to the optimisation too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ogr_gui.i18n import tr


class OptimizeSettingsDialog(QDialog):
    """Edit the ``optimize_*`` block of ``SearchSettings``.

    Writes nothing until :meth:`apply` is called, so the caller can hold
    the values and commit them with the rest of Surface Options — the
    behaviour the enclosing dialog's own OK / Cancel already promises.
    """

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Optimize Surfaces Settings"))
        self.project = project
        s = project.settings.search

        root = QVBoxLayout(self)

        # ---- Surfaces to Optimize -----------------------------------
        # Three exclusive choices. The cost between them is not a detail:
        # Global Minimum walks one surface, All walks every surface the
        # search generated, which on a 5000-surface Block Search is five
        # thousand walks. The reference warns about it in the same words.
        g_which = QGroupBox(tr("Surfaces to Optimize"))
        v_which = QVBoxLayout(g_which)
        self.rb_global = QRadioButton(tr("Global Minimum"))
        self.rb_all = QRadioButton(tr("All"))
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        self.rb_threshold = QRadioButton(tr("Factor of Safety Less Than:"))
        self.sb_threshold = QDoubleSpinBox()
        self.sb_threshold.setRange(0.001, 1000.0)
        self.sb_threshold.setDecimals(3)
        self.sb_threshold.setValue(float(s.optimize_fos_threshold))
        h.addWidget(self.rb_threshold)
        h.addWidget(self.sb_threshold)
        v_which.addWidget(self.rb_global)
        v_which.addWidget(self.rb_all)
        v_which.addWidget(row)
        {"all": self.rb_all,
         "fos_less_than": self.rb_threshold}.get(
            s.optimize_target, self.rb_global).setChecked(True)
        self.rb_threshold.toggled.connect(self.sb_threshold.setEnabled)
        self.sb_threshold.setEnabled(self.rb_threshold.isChecked())
        self.rb_all.setToolTip(tr(
            "Optimises every surface the search generated. The answer is "
            "the same kind of answer; the run takes far longer."))
        root.addWidget(g_which)

        # ---- Optimization Options -----------------------------------
        g_opt = QGroupBox(tr("Optimization Options"))
        f = QFormLayout(g_opt)
        self.sb_tolerance = QDoubleSpinBox()
        self.sb_tolerance.setDecimals(9)
        self.sb_tolerance.setRange(1e-9, 1.0)
        self.sb_tolerance.setSingleStep(1e-6)
        self.sb_tolerance.setValue(float(s.optimize_tolerance))
        self.sb_tolerance.setToolTip(tr(
            "The optimisation has converged when the factor of safety "
            "differs from the average of the last five passes by less "
            "than this."))
        f.addRow(tr("Tolerance (factor of safety):"), self.sb_tolerance)

        self.sb_iterations = QSpinBox()
        self.sb_iterations.setRange(1, 1000000)
        self.sb_iterations.setValue(int(s.optimize_max_iterations))
        f.addRow(tr("Maximum Iterations:"), self.sb_iterations)

        self.sb_step = QDoubleSpinBox()
        self.sb_step.setRange(0.01, 0.99)
        self.sb_step.setDecimals(2)
        self.sb_step.setSingleStep(0.05)
        self.sb_step.setValue(float(s.optimize_step_reduction_factor))
        self.sb_step.setToolTip(tr(
            "How far the vertices move on each pass, relative to the "
            "previous one. A small value is slow; a large one stops "
            "early. 0.5 is the recommended value."))
        f.addRow(tr("Step reduction factor (0 to 1):"), self.sb_step)

        concave = QWidget()
        hc = QHBoxLayout(concave)
        hc.setContentsMargins(0, 0, 0, 0)
        self.cb_concave = QCheckBox(tr("Maximum Concave Angle:"))
        self.cb_concave.setChecked(bool(s.optimize_max_concave_angle_enabled))
        self.sb_concave = QDoubleSpinBox()
        self.sb_concave.setRange(0.0, 180.0)
        self.sb_concave.setDecimals(1)
        self.sb_concave.setSuffix(" °")
        self.sb_concave.setValue(float(s.optimize_max_concave_angle_deg))
        self.sb_concave.setEnabled(self.cb_concave.isChecked())
        self.cb_concave.toggled.connect(self.sb_concave.setEnabled)
        # Unticked is NOT "no limit": it means no concave angle is allowed
        # at all. Saying so here is cheaper than a user inferring the
        # opposite from every other checkbox in the program.
        self.cb_concave.setToolTip(tr(
            "Unticked means no concave angle is allowed between adjacent "
            "segments of a surface produced by the optimisation."))
        hc.addWidget(self.cb_concave)
        hc.addWidget(self.sb_concave)
        f.addRow("", concave)

        self.cb_explore = QCheckBox(
            tr("Explore all vertices before moving surface"))
        self.cb_explore.setChecked(bool(s.optimize_explore_all_vertices))
        f.addRow("", self.cb_explore)
        root.addWidget(g_opt)

        # ---- Snap Shallow Surfaces to Slope --------------------------
        self.g_snap = QGroupBox(tr("Snap Shallow Surfaces to Slope"))
        self.g_snap.setCheckable(True)
        self.g_snap.setChecked(bool(s.optimize_snap_shallow_to_slope))
        v_snap = QVBoxLayout(self.g_snap)
        dist = QWidget()
        hd = QHBoxLayout(dist)
        hd.setContentsMargins(0, 0, 0, 0)
        self.cb_distance = QCheckBox(tr("Specify Distance:"))
        self.cb_distance.setChecked(bool(s.optimize_snap_specify_distance))
        self.sb_distance = QDoubleSpinBox()
        self.sb_distance.setRange(0.0, 1e6)
        self.sb_distance.setDecimals(4)
        self.sb_distance.setValue(float(s.optimize_snap_distance))
        self.sb_distance.setEnabled(self.cb_distance.isChecked())
        self.cb_distance.toggled.connect(self.sb_distance.setEnabled)
        self.cb_distance.setToolTip(tr(
            "Unticked, the minimum allowable depth is derived from the "
            "model's own relief."))
        hd.addWidget(self.cb_distance)
        hd.addWidget(self.sb_distance)
        v_snap.addWidget(dist)
        root.addWidget(self.g_snap)

        # ---- and the one that ties this to the Surface Filters -------
        self.cb_checks = QCheckBox(
            tr("Use checks for depth, elevation, concave surface"))
        self.cb_checks.setChecked(
            bool(s.optimize_use_depth_elevation_concave_checks))
        self.cb_checks.setToolTip(tr(
            "Applies the Minimum Depth and Minimum Elevation filters, and "
            "the concave angle limit, to the surfaces the optimisation "
            "produces as well as to those the search generates."))
        root.addWidget(self.cb_checks)

        buttons = QDialogButtonBox(
            QDialogButtonBox.RestoreDefaults | QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
            self._on_defaults)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def _on_defaults(self) -> None:
        """Reset every field to the engineering defaults."""
        from ogr_core.project.settings import SearchSettings
        d = SearchSettings()
        self.rb_global.setChecked(True)
        self.sb_threshold.setValue(d.optimize_fos_threshold)
        self.sb_tolerance.setValue(d.optimize_tolerance)
        self.sb_iterations.setValue(int(d.optimize_max_iterations))
        self.sb_step.setValue(d.optimize_step_reduction_factor)
        self.cb_concave.setChecked(d.optimize_max_concave_angle_enabled)
        self.sb_concave.setValue(d.optimize_max_concave_angle_deg)
        self.cb_explore.setChecked(d.optimize_explore_all_vertices)
        self.g_snap.setChecked(d.optimize_snap_shallow_to_slope)
        self.cb_distance.setChecked(d.optimize_snap_specify_distance)
        self.sb_distance.setValue(d.optimize_snap_distance)
        self.cb_checks.setChecked(
            d.optimize_use_depth_elevation_concave_checks)

    def apply(self) -> None:
        """Write the panel back into ``project.settings.search``."""
        s = self.project.settings.search
        if self.rb_all.isChecked():
            s.optimize_target = "all"
        elif self.rb_threshold.isChecked():
            s.optimize_target = "fos_less_than"
        else:
            s.optimize_target = "global_minimum"
        s.optimize_fos_threshold = float(self.sb_threshold.value())
        s.optimize_tolerance = float(self.sb_tolerance.value())
        s.optimize_max_iterations = int(self.sb_iterations.value())
        s.optimize_step_reduction_factor = float(self.sb_step.value())
        s.optimize_max_concave_angle_enabled = self.cb_concave.isChecked()
        s.optimize_max_concave_angle_deg = float(self.sb_concave.value())
        s.optimize_explore_all_vertices = self.cb_explore.isChecked()
        s.optimize_snap_shallow_to_slope = self.g_snap.isChecked()
        s.optimize_snap_specify_distance = self.cb_distance.isChecked()
        s.optimize_snap_distance = float(self.sb_distance.value())
        s.optimize_use_depth_elevation_concave_checks = (
            self.cb_checks.isChecked())
