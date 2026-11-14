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
from ogr_core.statistics.distributions import USES_STD_DEV
from ogr_gui.i18n import tr  # noqa: E402
from ogr_gui.dialog_size import list_width
from ogr_gui.disabled_reasons import gate
from ogr_gui.labels import random_variable_label  # noqa: E402

_DIST_LABELS = [
    (DistributionType.NORMAL, "Normal"),
    (DistributionType.UNIFORM, "Uniform"),
    (DistributionType.TRIANGULAR, "Triangular"),
    (DistributionType.BETA, "Beta"),
    (DistributionType.EXPONENTIAL, "Exponential"),
    (DistributionType.LOGNORMAL, "Lognormal"),
    (DistributionType.GAMMA, "Gamma"),
    # v0.1.435 (D413) -- the choice an agent can make (``distribution="none"``):
    # missing here, selecting such a variable put the combo on Normal and
    # stored it, so OK switched the variable back on
    (DistributionType.NONE, "No distribution"),
]

# Distributions that take a standard deviation: the core's list, which the
# run reads too (v0.1.453, D416)
_USES_STD = USES_STD_DEV


def not_random_text(why: str) -> str:
    """The reader's sentence for a reason of the core's
    ``Distribution.not_random_reason`` (the dialog's greyed Plot button).
    A module function since v0.1.453, so a test can ask it for every reason
    the core gives without building the dialog; an unknown reason is shown
    as it came."""
    reasons = {
        "none": tr("This variable has no distribution: it is not random."),
        "no_range": tr("The range is empty: enter a relative minimum or a "
                       "relative maximum."),
        # v0.1.453 (D416) -- the beta and the gamma too, so the reason no
        # longer names two of the four
        "no_std_dev": tr("This distribution needs a standard deviation "
                         "greater than zero."),
        # the review of 0.1.453 -- the mean is the model's value, so what
        # can be changed here is the distribution
        "no_positive_mean": tr("This distribution takes only positive "
                               "values, and the mean is not positive: "
                               "choose another distribution."),
    }
    return reasons.get(why, why)


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
            # v0.1.321 (D300) — shown translated; the stored label stays.
            it = QListWidgetItem(random_variable_label(rv, self.project))
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
        # v0.1.326 (D321) — both lists as wide as the widest parameter
        # («Silty clay — cohesión» showed 186 of its 340 px); the defined
        # variables are a choice among the same labels
        need = list_width(self.list_available)
        self.list_available.setMinimumWidth(need)
        self.list_defined.setMinimumWidth(need)
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
            self.cbo_dist.addItem(tr(label), t)
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
        self.cbo_corr_with.addItem(tr("(none)"), None)
        f.addRow(tr("Correlated with:"), self.cbo_corr_with)
        self.sp_corr = QDoubleSpinBox()
        self.sp_corr.setDecimals(3)
        self.sp_corr.setRange(-1.0, 1.0)
        self.sp_corr.setSingleStep(0.05)
        self.sp_corr.setToolTip(
            tr("Correlation coefficient. A negative value is the usual case "
            "for cohesion and friction angle."))
        f.addRow(tr("Correlation coefficient:"), self.sp_corr)

        # v0.1.435 (D413) -- each control stores its own field, and only
        # when the user changes it: one handler wrote back every field the
        # controls show, so selecting a variable (and OK) rounded what an
        # agent stored (3 decimals of correlation, 6 of standard deviation;
        # 4e-7 became 0 and switched the variable off). Bound methods, not
        # lambdas: a lambda that names ``self`` is held from C++ and kept
        # the closed dialog alive, with its plots and its project
        self.sp_std.valueChanged.connect(self._on_std_changed)
        self.sp_rmin.valueChanged.connect(self._on_rmin_changed)
        self.sp_rmax.valueChanged.connect(self._on_rmax_changed)
        self.sp_corr.valueChanged.connect(self._on_corr_changed)
        self.cbo_corr_with.currentIndexChanged.connect(
            self._on_corr_with_changed)

        right.addWidget(gb)
        # v0.1.435 (D413) -- grey with the reason when there is nothing to
        # plot: it opened a modal box that named one reason for three
        self.btn_plot = QPushButton(tr("Plot distribution…"))
        self.btn_plot.clicked.connect(self._plot)
        right.addWidget(self.btn_plot)
        right.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        root.addLayout(right, 3)

        self._current_key = None
        self._refresh_defined()
        self._update_plot_gate()

    # ==================================================================
    def _by_key(self, key):
        for rv in self.catalogue:
            if rv.key == key:
                return rv
        return None

    def _refresh_defined(self):
        self.list_defined.clear()
        for key, rv in self.defined.items():
            it = QListWidgetItem(random_variable_label(rv, self.project))
            it.setData(Qt.UserRole, key)
            self.list_defined.addItem(it)
        self._refresh_correlation_choices()
        if self.list_defined.count():
            self.list_defined.setCurrentRow(0)
        else:
            self._current_key = None

    def _refresh_correlation_choices(self):
        current = self.cbo_corr_with.currentData()
        # the state it found, not False: _on_selected calls it with the
        # signals already blocked (v0.1.435)
        was = self.cbo_corr_with.blockSignals(True)
        self.cbo_corr_with.clear()
        self.cbo_corr_with.addItem(tr("(none)"), None)
        for key, rv in self.defined.items():
            if key != self._current_key:
                self.cbo_corr_with.addItem(
                    random_variable_label(rv, self.project), key)
        i = self.cbo_corr_with.findData(current)
        self.cbo_corr_with.setCurrentIndex(max(0, i))
        self.cbo_corr_with.blockSignals(was)

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
        # v0.1.201 — the starting dispersion is the core's
        # (``default_dispersion``), which an agent's variables get too.
        from ogr_core.statistics.random_variables import default_dispersion
        rv = default_dispersion(RandomVariable.from_dict(src.to_dict()))
        self.defined[key] = rv
        self._refresh_defined()

    def _remove(self):
        it = self.list_defined.currentItem()
        if it is None:
            return
        key = it.data(Qt.UserRole)
        # v0.1.201 — the core's ``forget_variable``: the variable goes and
        # a correlation that pointed at it is cleared.
        from ogr_core.statistics.random_variables import forget_variable
        kept = forget_variable(list(self.defined.values()), key)
        self.defined = {rv.key: rv for rv in kept}
        self._refresh_defined()

    # ------------------------------------------------------------------
    def _on_selected(self, row: int):
        """Show the selected variable. It stores nothing (v0.1.435, D413):
        the controls round what they show, and writing that back changed a
        variable nobody had touched."""
        self._current_key = None
        it = self.list_defined.item(row)
        key = it.data(Qt.UserRole) if it is not None else None
        rv = self.defined.get(key) if key is not None else None
        if rv is None:
            # the last variable removed: nothing to plot (this is the only
            # call that greys the button then)
            self._update_plot_gate()
            return
        d = rv.distribution
        controls = (self.cbo_dist, self.sp_std, self.sp_rmin, self.sp_rmax,
                    self.sp_corr, self.cbo_corr_with)
        for w in controls:
            w.blockSignals(True)
        try:
            i = self.cbo_dist.findData(d.dist_type)
            self.cbo_dist.setCurrentIndex(max(0, i))
            self.sp_mean.setValue(d.mean)
            self.sp_std.setValue(d.std_dev)
            self.sp_rmin.setValue(d.rel_min)
            self.sp_rmax.setValue(d.rel_max)
            self.sp_corr.setValue(rv.correlation)
            self._current_key = key
            self._refresh_correlation_choices()
            # blocked too: it stored the previous variable's partner when
            # this one's was not in the list
            j = self.cbo_corr_with.findData(rv.correlated_with)
            self.cbo_corr_with.setCurrentIndex(max(0, j))
        finally:
            for w in controls:
                w.blockSignals(False)
        self.sp_std.setEnabled(d.dist_type in _USES_STD)
        self._after_edit()

    def _current(self):
        key = self._current_key
        return self.defined.get(key) if key is not None else None

    def _after_edit(self) -> None:
        rv = self._current()
        if rv is not None:
            d = rv.distribution
            self.lbl_actual.setText(f"{d.low:g}  …  {d.high:g}")
        self._update_plot_gate()

    def _store(self, owner: str, field: str, value) -> None:
        rv = self._current()
        if rv is not None:
            setattr(rv.distribution if owner == "dist" else rv, field, value)
        self._after_edit()

    def _on_dist_changed(self, _idx):
        t = self.cbo_dist.currentData()
        self.sp_std.setEnabled(t in _USES_STD)
        self._store("dist", "dist_type", t)

    def _on_std_changed(self, value):
        self._store("dist", "std_dev", value)

    def _on_rmin_changed(self, value):
        self._store("dist", "rel_min", value)

    def _on_rmax_changed(self, value):
        self._store("dist", "rel_max", value)

    def _on_corr_changed(self, value):
        self._store("rv", "correlation", value)

    def _on_corr_with_changed(self, _idx):
        self._store("rv", "correlated_with", self.cbo_corr_with.currentData())

    def _plot_reason(self) -> str:
        """Why there is nothing to plot, or "" (v0.1.435, D413): the core's
        reason (``Distribution.not_random_reason``), the same rule the run
        reads, and no matplotlib."""
        key = self._current_key
        if key is None or key not in self.defined:
            return tr("Select a random variable first.")
        why = self.defined[key].distribution.not_random_reason()
        if why:
            return not_random_text(why)
        import importlib.util
        if importlib.util.find_spec("matplotlib") is None:
            return tr("matplotlib is not installed.")
        return ""

    def _update_plot_gate(self) -> None:
        btn = getattr(self, "btn_plot", None)
        if btn is None:                 # signals while the dialog is built
            return
        why = self._plot_reason()
        gate(btn, not why, why)
        btn.setToolTip(why)

    # ------------------------------------------------------------------
    def _plot(self):
        """The density of the selected variable, in a window of its own:
        non-modal since v0.1.435 (D413), as every informative chart, and
        kept on the dialog. Returns it, or None when the button's reason
        says there is nothing to plot."""
        if self._plot_reason():
            return None
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            return None
        rv = self.defined[self._current_key]
        curve = rv.distribution.curve(120)
        dlg = QDialog(self)
        dlg.setWindowTitle(random_variable_label(rv, self.project))
        dlg.resize(560, 400)
        v = QVBoxLayout(dlg)
        fig = Figure(figsize=(5.4, 3.8), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.plot([c[0] for c in curve], [c[1] for c in curve], lw=1.8)
        # v0.1.433 (D411) -- the axes and the legend through tr()
        ax.axvline(rv.distribution.mean, color="crimson", ls="--", lw=1.0,
                   label=tr("mean"))
        ax.set_xlabel(tr("Value"))
        ax.set_ylabel(tr("Probability density"))
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        v.addWidget(FigureCanvasQTAgg(fig))
        from ogr_gui.xy_chart import keep_chart
        return keep_chart(self, dlg)

    # ------------------------------------------------------------------
    def _accept(self):
        # v0.1.435 (D413) -- nothing re-stored from the controls here: each
        # edit is already in the working copy, and only the edits
        self.project.random_variables = list(self.defined.values())
        self.project.is_dirty = True
        self.accept()

    def done(self, result):
        """OK or Cancel also close the plots it opened (v0.1.435, D413): a
        non-modal plot outlived the editor and kept showing a distribution
        that Cancel had thrown away."""
        for win in list(getattr(self, "_chart_windows", ()) or ()):
            try:
                win.close()
            except RuntimeError:        # already deleted on the C++ side
                pass
        super().done(result)
