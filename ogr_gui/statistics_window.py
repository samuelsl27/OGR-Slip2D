# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Statistics interpret window (Phase P5).

Presents the output of a probabilistic or sensitivity run:

* **Histogram** of the computed factors of safety, with the failure
  threshold marked, plus the headline numbers (mean, standard deviation,
  probability of failure, reliability index).
* **Convergence plot** of the mean factor of safety and the probability
  of failure against the number of samples — the reference's way of
  judging whether enough samples were used.
* **Scatter plot** of the factor of safety against any random variable,
  which shows at a glance which input drives the response.
* **Sensitivity plot** of factor of safety versus each variable, with the
  x-axis in percent of range so variables with different units share one
  set of axes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from ogr_gui.i18n import tr  # noqa: E402


class StatisticsWindow(QMainWindow):
    """Read-only viewer for probabilistic / sensitivity results."""

    def __init__(self, project, prob_result=None, sens_result=None,
                 parent=None):
        super().__init__(parent)
        self.project = project
        self.prob = prob_result
        self.sens = sens_result
        self.setWindowTitle(tr("Statistics — OGR Slip2D"))
        self.resize(980, 620)

        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        bar = QHBoxLayout()
        bar.addWidget(QLabel(tr("Method:")))
        self.cbo_method = QComboBox()
        for mid in self._method_ids():
            self.cbo_method.addItem(mid, mid)
        self.cbo_method.currentIndexChanged.connect(self._redraw)
        bar.addWidget(self.cbo_method)

        bar.addWidget(QLabel(tr("Plot:")))
        self.cbo_plot = QComboBox()
        if prob_result is not None and prob_result.ok:
            self.cbo_plot.addItem("Histogram of FoS", "histogram")
            self.cbo_plot.addItem("Convergence", "convergence")
        if sens_result is not None and sens_result.ok:
            self.cbo_plot.addItem("Sensitivity", "sensitivity")
        self.cbo_plot.currentIndexChanged.connect(self._redraw)
        bar.addWidget(self.cbo_plot)
        bar.addStretch(1)
        v.addLayout(bar)

        # v0.1.170 (D129) — a label of its OWN, above the plot and outside
        # everything ``_redraw`` rewrites. It cannot share ``self.status``
        # below: that one is reset on every redraw, so a run-wide sentence
        # written there would survive exactly until the user changed the
        # plot or the method. ``_redraw`` does not mention this widget in
        # any line, which is the only guarantee that does not erode.
        self.lbl_run_notes = QLabel("")
        self.lbl_run_notes.setWordWrap(True)
        self.lbl_run_notes.setStyleSheet("color: #b00020;")
        _lines = self._run_notes()
        if _lines:
            self.lbl_run_notes.setText(
                tr("What this run could not do:") + "\n"
                + "\n".join(_lines))
        # Regla 7 in interface form: with nothing to say, the window of a
        # sound run is pixel for pixel the one it has always been.
        self.lbl_run_notes.setVisible(bool(_lines))
        v.addWidget(self.lbl_run_notes)

        self.canvas = None
        self._holder = QVBoxLayout()
        v.addLayout(self._holder, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self._redraw()

    # ------------------------------------------------------------------
    def _run_notes(self) -> list:
        """The lines the engines left, in order and without repeats.

        Nothing is parsed: the window never asks what a line says or which
        method it is about. The two engines share ``_cannot_reevaluate``,
        so they can refuse the same method with the same sentence -- hence
        the de-duplication, with the order kept.

        The honest limit: ``_compute_statistics`` only keeps a result when
        it is ``ok``, so a run that failed ENTIRELY never reaches this
        window. This label is for the PARTIAL case, which is D129; the
        total one is carried by the status bar and the notes panel.
        """
        lines = []
        for res in (self.prob, self.sens):
            lines += list(getattr(res, "note_lines", None) or [])
        return list(dict.fromkeys(lines))

    def _method_note(self, mid) -> str:
        """What an engine said about THIS method, asked for BY NAME.

        Not "which keys of ``notes`` are neither error nor warning": that
        is dispatching on the shape of a dictionary, which is D59. The
        method id is already in hand, so the only question asked is
        whether the run left anything under it.
        """
        for res in (self.prob, self.sens):
            note = (getattr(res, "notes", None) or {}).get(mid)
            if note:
                return str(note)
        return ""

    def _with_reason(self, text: str, mid) -> str:
        """``text``, and the engine's reason behind it when there is one.

        The generic sentences below are true but useless on their own: in
        Overall Slope a method that lost every search KEEPS its entry, so
        it is selectable, and the window answered "No probabilistic result
        for this method" without ever saying why. ``notes[mid]`` is the
        bare fact precisely so it can be read here, where the combo is
        already showing the method's name.
        """
        note = self._method_note(mid)
        return text + "   |   " + note if note else text

    def _method_ids(self):
        ids = []
        if self.prob is not None and self.prob.ok:
            ids += list(self.prob.by_method)
        if self.sens is not None and self.sens.ok:
            ids += [m for m in self.sens.by_method if m not in ids]
        return ids or ["(none)"]

    def _figure(self):
        import matplotlib
        matplotlib.use("QtAgg", force=False)
        from matplotlib.figure import Figure
        return Figure(figsize=(9.0, 4.6), tight_layout=True)

    def _show(self, fig):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        if self.canvas is not None:
            self._holder.removeWidget(self.canvas)
            self.canvas.setParent(None)
        self.canvas = FigureCanvasQTAgg(fig)
        self._holder.addWidget(self.canvas)

    # ==================================================================
    def _redraw(self, *_args):
        try:
            self._figure()
        except ImportError:
            self.status.setText(tr("matplotlib is not installed."))
            return
        mid = self.cbo_method.currentData()
        kind = self.cbo_plot.currentData()
        if kind == "histogram":
            self._plot_histogram(mid)
        elif kind == "convergence":
            self._plot_convergence(mid)
        elif kind == "sensitivity":
            self._plot_sensitivity(mid)
        else:
            self.status.setText(tr("No results to display."))

    # ------------------------------------------------------------------
    def _stats_for(self, mid):
        if self.prob is None or not self.prob.ok:
            return None
        res = self.prob.by_method.get(mid)
        return None if res is None else res.statistics

    def _plot_histogram(self, mid):
        st = self._stats_for(mid)
        if st is None or not st.values:
            self.status.setText(self._with_reason(
                tr("No probabilistic result for this method."), mid))
            return
        fig = self._figure()
        ax = fig.add_subplot(111)
        hist = st.histogram(bins=25)
        widths = (hist[1][0] - hist[0][0]) if len(hist) > 1 else 0.05
        ax.bar([h[0] for h in hist], [h[1] for h in hist],
               width=widths * 0.9, color="#4c78a8", edgecolor="white")
        ax.axvline(1.0, color="crimson", lw=2.0,
                   label="failure threshold (FS = 1)")
        ax.axvline(st.mean, color="#333333", ls="--", lw=1.4,
                   label=f"mean = {st.mean:.4f}")
        ax.set_xlabel("Factor of safety")
        ax.set_ylabel("Number of samples")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        self._show(fig)
        res = self.prob.by_method[mid]
        self.status.setText(
            f"samples: {st.n}   |   mean: {st.mean:.4f}   |   "
            f"std dev: {st.std_dev:.4f}   |   min: {st.minimum:.4f}   |   "
            f"max: {st.maximum:.4f}\n"
            f"probability of failure: "
            f"{st.probability_of_failure() * 100:.2f} %   |   "
            f"reliability index: {st.reliability_index():.3f} "
            f"(lognormal {st.lognormal_reliability_index():.3f})   |   "
            f"deterministic FoS: {res.deterministic_fos:.4f}")

    # ------------------------------------------------------------------
    def _plot_convergence(self, mid):
        st = self._stats_for(mid)
        if st is None or not st.values:
            self.status.setText(self._with_reason(
                tr("No probabilistic result for this method."), mid))
            return
        conv = st.convergence(steps=60)
        fig = self._figure()
        ax = fig.add_subplot(111)
        ax.plot([c[0] for c in conv], [c[1] for c in conv],
                color="#4c78a8", label="mean FoS")
        ax.set_xlabel("Number of samples")
        ax.set_ylabel("Mean factor of safety")
        ax.grid(True, alpha=0.3)
        ax2 = ax.twinx()
        ax2.plot([c[0] for c in conv], [100.0 * c[2] for c in conv],
                 color="crimson", ls="--", label="probability of failure")
        ax2.set_ylabel("Probability of failure (%)")
        lines = ax.get_lines() + ax2.get_lines()
        ax.legend(lines, [ln.get_label() for ln in lines], fontsize=8)
        self._show(fig)
        self.status.setText(
            "A flat tail means the sample count is sufficient; a curve "
            "still drifting means more samples are needed.")

    # ------------------------------------------------------------------
    def _plot_sensitivity(self, mid):
        if self.sens is None or not self.sens.ok:
            self.status.setText(tr("No sensitivity result."))
            return
        sweeps = self.sens.by_method.get(mid)
        if not sweeps:
            self.status.setText(self._with_reason(
                tr("No sensitivity result for this method."), mid))
            return
        fig = self._figure()
        ax = fig.add_subplot(111)
        # v0.1.164 (D91) — a variable whose target no longer matches the
        # model carries a note and NO points. Plotting it drew a flat line
        # at the deterministic factor, which reads as "this parameter does
        # not matter": the one thing the run cannot claim about a parameter
        # it never applied. It is named in the status line instead.
        refused = [vs for vs in sweeps.values() if vs.note]
        for vs in sweeps.values():
            if vs.note:
                continue
            ax.plot(vs.percent_of_range(), vs.fos, marker="",
                    label=vs.label)
        ax.axhline(1.0, color="crimson", lw=1.6, ls="-",
                   label="FS = 1")
        ax.set_xlabel("Percent of variable range (%)")
        ax.set_ylabel("Factor of safety")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        self._show(fig)
        rows = self.sens.ranking(mid)
        txt = "   |   ".join(f"{lab}: ΔFoS {span:.4f}"
                             for _k, lab, span in rows[:5])
        if refused:
            txt += ("   |   " + tr("not swept, no longer in the model: ")
                    + ", ".join(vs.label for vs in refused))
        self.status.setText(tr("Most influential first — ") + txt)

    # ==================================================================
    def scatter_data(self, mid, variable_key):
        """(variable value, factor of safety) pairs for a scatter plot.

        Exposed as a method so it can be tested without a display.
        v0.1.201 — paired by each factor's sample index
        (``sample_pairs``): a zip shifted every pair after the first
        sample that failed.
        """
        from ogr_core.statistics import sample_pairs
        return [(v, f) for _i, v, f in sample_pairs(self.prob, mid,
                                                     variable_key)]
