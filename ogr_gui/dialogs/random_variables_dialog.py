# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Statistics — random variables dialog (Phase P5).

Lets the user pick model input parameters and turn them into random
variables, following the reference's workflow: choose the parameters from
a catalogue of everything that CAN be randomised, then give each one a
distribution, a standard deviation and **relative** minimum and maximum
values.

Two details taken from the reference:

* the minimum and maximum are entered as **relative** distances from the
  mean, because that is how uncertainty is naturally stated and it keeps
  the sampled values physically sensible;
* for a Mohr-Coulomb material the **cohesion and friction angle may be
  correlated**, which is the physically usual case (a higher cohesion
  tends to accompany a lower friction angle).

The dialog also plots the resulting probability density function, so the
user can see the effect of the parameters before running anything.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ogr_core.statistics import (
    Distribution,
    DistributionType,
    RandomVariable,
    VariableKind,
    available_variables,
)
from ogr_gui.i18n import tr  # noqa: E402

_DIST_LABELS = [
    (DistributionType.NORMAL, "Normal"),
    (DistributionType.UNIFORM, "Uniform"),
    (DistributionType.TRIANGULAR, "Triangular"),
    (DistributionType.BETA, "Beta"),
    (DistributionType.EXPONENTIAL, "Exponential"),
    (DistributionType.LOGNORMAL, "Lognormal"),
    (DistributionType.GAMMA, "Gamma"),
]

# Distributions that take a standard deviation
_USES_STD = {DistributionType.NORMAL, DistributionType.LOGNORMAL,
             DistributionType.BETA, DistributionType.GAMMA}


class RandomVariablesDialog(QDialog):
    """Define the random variables of the model."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Statistics — Random Variables"))
        self.resize(860, 560)

        self.catalogue = available_variables(project)
        # Working copies keyed by variable key
        self.defined: dict = {}
        for rv in getattr(project, "random_variables", []) or []:
            self.defined[rv.key] = RandomVariable.from_dict(rv.to_dict())

        root = QHBoxLayout(self)

        # ---- available parameters -----------------------------------
        left = QVBoxLayout()
        left.addWidget(QLabel(tr("Available parameters")))
        self.list_available = QListWidget()
        for rv in self.catalogue:
            it = QListWidgetItem(rv.label or rv.key)
            it.setData(Qt.UserRole, rv.key)
            self.list_available.addItem(it)
        left.addWidget(self.list_available, 1)
        b_add = QPushButton(tr("Add →"))
        b_add.clicked.connect(self._add)
        left.addWidget(b_add)
        root.addLayout(left, 2)

        # ---- defined variables --------------------------------------
        mid = QVBoxLayout()
        mid.addWidget(QLabel(tr("Random variables")))
        self.list_defined = QListWidget()
        self.list_defined.currentRowChanged.connect(self._on_selected)
        mid.addWidget(self.list_defined, 1)
        b_del = QPushButton(tr("Remove"))
        b_del.clicked.connect(self._remove)
        mid.addWidget(b_del)
        root.addLayout(mid, 2)

        # ---- statistics ---------------------------------------------
        right = QVBoxLayout()
        gb = QGroupBox(tr("Statistical parameters"))
        f = QFormLayout(gb)
        self.cbo_dist = QComboBox()
        for t, label in _DIST_LABELS:
            self.cbo_dist.addItem(label, t)
        self.cbo_dist.currentIndexChanged.connect(self._on_dist_changed)
        f.addRow(tr("Distribution:"), self.cbo_dist)

        self.sp_mean = QDoubleSpinBox()
        self.sp_mean.setDecimals(6)
        self.sp_mean.setRange(-1e12, 1e12)
        self.sp_mean.setReadOnly(True)
        self.sp_mean.setToolTip(
            tr("The mean is the deterministic value defined in the model."))
        f.addRow(tr("Mean (deterministic):"), self.sp_mean)

        self.sp_std = QDoubleSpinBox()
        self.sp_std.setDecimals(6)
        self.sp_std.setRange(0.0, 1e12)
        f.addRow(tr("Standard deviation:"), self.sp_std)

        self.sp_rmin = QDoubleSpinBox()
        self.sp_rmin.setDecimals(6)
        self.sp_rmin.setRange(0.0, 1e12)
        self.sp_rmin.setToolTip(
            tr("RELATIVE minimum: actual minimum = mean - this value."))
        f.addRow(tr("Relative minimum:"), self.sp_rmin)

        self.sp_rmax = QDoubleSpinBox()
        self.sp_rmax.setDecimals(6)
        self.sp_rmax.setRange(0.0, 1e12)
        self.sp_rmax.setToolTip(
            tr("RELATIVE maximum: actual maximum = mean + this value."))
        f.addRow(tr("Relative maximum:"), self.sp_rmax)

        self.lbl_actual = QLabel("")
        f.addRow(tr("Actual range:"), self.lbl_actual)

        self.cbo_corr_with = QComboBox()
        self.cbo_corr_with.addItem("(none)", None)
        f.addRow(tr("Correlated with:"), self.cbo_corr_with)
        self.sp_corr = QDoubleSpinBox()
        self.sp_corr.setDecimals(3)
        self.sp_corr.setRange(-1.0, 1.0)
        self.sp_corr.setSingleStep(0.05)
        self.sp_corr.setToolTip(
            "Correlation coefficient. A negative value is the usual case "
            "for cohesion and friction angle.")
        f.addRow(tr("Correlation coefficient:"), self.sp_corr)

        for w in (self.sp_std, self.sp_rmin, self.sp_rmax, self.sp_corr):
            w.valueChanged.connect(self._store_current)
        self.cbo_corr_with.currentIndexChanged.connect(self._store_current)

        right.addWidget(gb)
        b_plot = QPushButton(tr("Plot distribution…"))
        b_plot.clicked.connect(self._plot)
        right.addWidget(b_plot)
        right.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        root.addLayout(right, 3)

        self._current_key = None
        self._refresh_defined()

    # ==================================================================
    def _by_key(self, key):
        for rv in self.catalogue:
            if rv.key == key:
                return rv
        return None

    def _refresh_defined(self):
        self.list_defined.clear()
        for key, rv in self.defined.items():
            it = QListWidgetItem(rv.label or key)
            it.setData(Qt.UserRole, key)
            self.list_defined.addItem(it)
        self._refresh_correlation_choices()
        if self.list_defined.count():
            self.list_defined.setCurrentRow(0)
        else:
            self._current_key = None

    def _refresh_correlation_choices(self):
        current = self.cbo_corr_with.currentData()
        self.cbo_corr_with.blockSignals(True)
        self.cbo_corr_with.clear()
        self.cbo_corr_with.addItem("(none)", None)
        for key, rv in self.defined.items():
            if key != self._current_key:
                self.cbo_corr_with.addItem(rv.label or key, key)
        i = self.cbo_corr_with.findData(current)
        self.cbo_corr_with.setCurrentIndex(max(0, i))
        self.cbo_corr_with.blockSignals(False)

    # ------------------------------------------------------------------
    def _add(self):
        it = self.list_available.currentItem()
        if it is None:
            return
        key = it.data(Qt.UserRole)
        if key in self.defined:
            return
        src = self._by_key(key)
        if src is None:
            return
        rv = RandomVariable.from_dict(src.to_dict())
        # A sensible starting point: 10 % of the mean either side
        m = abs(rv.distribution.mean) or 1.0
        rv.distribution.std_dev = 0.1 * m
        rv.distribution.rel_min = 0.3 * m
        rv.distribution.rel_max = 0.3 * m
        self.defined[key] = rv
        self._refresh_defined()

    def _remove(self):
        it = self.list_defined.currentItem()
        if it is None:
            return
        key = it.data(Qt.UserRole)
        self.defined.pop(key, None)
        # Drop dangling correlations
        for rv in self.defined.values():
            if rv.correlated_with == key:
                rv.correlated_with = None
                rv.correlation = 0.0
        self._refresh_defined()

    # ------------------------------------------------------------------
    def _on_selected(self, row: int):
        self._current_key = None
        it = self.list_defined.item(row)
        if it is None:
            return
        key = it.data(Qt.UserRole)
        rv = self.defined.get(key)
        if rv is None:
            return
        d = rv.distribution
        for w in (self.cbo_dist, self.sp_std, self.sp_rmin, self.sp_rmax,
                  self.sp_corr, self.cbo_corr_with):
            w.blockSignals(True)
        i = self.cbo_dist.findData(d.dist_type)
        self.cbo_dist.setCurrentIndex(max(0, i))
        self.sp_mean.setValue(d.mean)
        self.sp_std.setValue(d.std_dev)
        self.sp_rmin.setValue(d.rel_min)
        self.sp_rmax.setValue(d.rel_max)
        self.sp_corr.setValue(rv.correlation)
        for w in (self.cbo_dist, self.sp_std, self.sp_rmin, self.sp_rmax,
                  self.sp_corr, self.cbo_corr_with):
            w.blockSignals(False)
        self._current_key = key
        self._refresh_correlation_choices()
        j = self.cbo_corr_with.findData(rv.correlated_with)
        if j >= 0:
            self.cbo_corr_with.setCurrentIndex(j)
        self._on_dist_changed(0)

    def _on_dist_changed(self, _idx):
        t = self.cbo_dist.currentData()
        self.sp_std.setEnabled(t in _USES_STD)
        self._store_current()

    def _store_current(self):
        key = self._current_key
        if key is None or key not in self.defined:
            return
        rv = self.defined[key]
        rv.distribution.dist_type = self.cbo_dist.currentData()
        rv.distribution.std_dev = self.sp_std.value()
        rv.distribution.rel_min = self.sp_rmin.value()
        rv.distribution.rel_max = self.sp_rmax.value()
        rv.correlated_with = self.cbo_corr_with.currentData()
        rv.correlation = self.sp_corr.value()
        d = rv.distribution
        self.lbl_actual.setText(f"{d.low:g}  …  {d.high:g}")

    # ------------------------------------------------------------------
    def _plot(self):
        key = self._current_key
        if key is None:
            return
        rv = self.defined[key]
        if not rv.distribution.is_random:
            QMessageBox.information(
                self, "Plot",
                "Enter a relative minimum and maximum first.")
            return
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            QMessageBox.information(self, "Plot",
                                    "matplotlib is not installed.")
            return
        curve = rv.distribution.curve(120)
        dlg = QDialog(self)
        dlg.setWindowTitle(rv.label or key)
        dlg.resize(560, 400)
        v = QVBoxLayout(dlg)
        fig = Figure(figsize=(5.4, 3.8), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.plot([c[0] for c in curve], [c[1] for c in curve], lw=1.8)
        ax.axvline(rv.distribution.mean, color="crimson", ls="--", lw=1.0,
                   label="mean")
        ax.set_xlabel("Value")
        ax.set_ylabel("Probability density")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        v.addWidget(FigureCanvasQTAgg(fig))
        dlg.exec()

    # ------------------------------------------------------------------
    def _accept(self):
        self._store_current()
        self.project.random_variables = list(self.defined.values())
        self.project.is_dirty = True
        self.accept()
