# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Matplotlib-based chart widgets for the Interpret window (v0.1.3).

Provides four reusable chart dialogs:
    - HistogramDialog — FoS frequency distribution
    - CumulativeDialog — CDF with P(FoS<1) highlighted
    - ScatterDialog — generic X vs Y scatter
    - SFAlongSlopeDialog — Factor of Safety along the slope, from every
      valid surface (Interpret's Graph SF Along Slope, v0.1.433)

All dialogs embed a matplotlib FigureCanvas, so the Interpret window
shows real interactive plots rather than text summaries.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ogr_gui.i18n import tr  # noqa: E402

try:
    from matplotlib.backends.backend_qtagg import (  # type: ignore[import-not-found]
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT as NavigationToolbar,
    )
    from matplotlib.figure import Figure  # type: ignore[import-not-found]
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False


# ======================================================================
class _ChartDialogBase(QDialog):
    """Shared matplotlib hosting logic."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 520)

        self._root = QVBoxLayout(self)
        if not MPL_AVAILABLE:
            self._root.addWidget(QLabel(
                tr("<b>matplotlib is required for interactive charts.</b><br>"
                "Install it with:<br><code>pip install matplotlib</code>")
            ))
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(self.reject)
            btns.accepted.connect(self.accept)
            self._root.addWidget(btns)
            self.figure = None
            self.canvas = None
            return

        self.figure = Figure(figsize=(7, 4.8), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self._root.addWidget(self.toolbar)
        self._root.addWidget(self.canvas, 1)

        self._controls_bar = QHBoxLayout()
        self._root.addLayout(self._controls_bar)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        self._root.addWidget(btns)

    def ax(self):
        """Shortcut to the single primary axes."""
        if self.figure is None:
            return None
        if not self.figure.axes:
            return self.figure.add_subplot(111)
        return self.figure.axes[0]


# ======================================================================
class HistogramDialog(_ChartDialogBase):
    """FoS histogram for the full population.

    v0.1.435 (D413) -- ``factored``: the values are over-design factors (a
    design standard was applied), and every text says so; without it, the
    texts it always had."""

    def __init__(self, fos_values: Sequence[float], parent=None,
                 factored: bool = False) -> None:
        self._factored = bool(factored)
        super().__init__(
            tr("Histogram — Over-design factor distribution") if factored
            else tr("Histogram — Factor of Safety distribution"), parent)
        self._values = [v for v in fos_values if v is not None]
        if self.canvas is None or not self._values:
            return

        self.spn_bins = QSpinBox()
        self.spn_bins.setRange(5, 200)
        self.spn_bins.setValue(25)
        self.spn_bins.valueChanged.connect(self._redraw)
        self.chk_mark_one = QCheckBox(
            tr("Mark ODF = 1.0") if factored else tr("Mark FoS = 1.0"))
        self.chk_mark_one.setChecked(True)
        self.chk_mark_one.toggled.connect(self._redraw)

        self._controls_bar.addWidget(QLabel(tr("Bins:")))
        self._controls_bar.addWidget(self.spn_bins)
        self._controls_bar.addWidget(self.chk_mark_one)
        self._controls_bar.addStretch(1)

        self._redraw()

    def _redraw(self) -> None:
        if self.figure is None:
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        n_bins = self.spn_bins.value()
        ax.hist(self._values, bins=n_bins, color="#3a87c8",
                edgecolor="#10305a", alpha=0.85)
        if self.chk_mark_one.isChecked():
            ax.axvline(1.0, color="#c0392b", linestyle="--",
                       linewidth=1.2,
                       label=(tr("ODF = 1.0") if self._factored
                              else tr("FoS = 1.0")))
            ax.legend(loc="upper right")
        ax.set_xlabel(tr("Over-design factor") if self._factored
                      else tr("Factor of Safety"))
        ax.set_ylabel(tr("Number of surfaces"))
        ax.set_title(tr('Distribution over {0} valid surfaces').format(len(self._values)))
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class CumulativeDialog(_ChartDialogBase):
    """CDF of FoS values with P(FoS<1) annotation; ``factored`` as in
    :class:`HistogramDialog` (v0.1.435, D413)."""

    def __init__(self, fos_values: Sequence[float], parent=None,
                 factored: bool = False) -> None:
        self._factored = bool(factored)
        super().__init__(tr("Cumulative — ODF CDF") if factored
                         else tr("Cumulative — FoS CDF"), parent)
        self._values = sorted(v for v in fos_values if v is not None)
        if self.canvas is None or not self._values:
            return
        self._redraw()

    def _redraw(self) -> None:
        if self.figure is None:
            return
        import numpy as np

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        values = np.asarray(self._values)
        y = np.arange(1, len(values) + 1) / len(values)
        ax.step(values, y, where="post", color="#3a87c8", linewidth=1.8)
        ax.axvline(1.0, color="#c0392b", linestyle="--", linewidth=1.2)
        # P(FoS < 1)
        pf = (values < 1.0).sum() / len(values) if len(values) else 0.0
        ax.text(
            1.02, 0.05,
            (tr('P(ODF<1) = {0:.2%}') if self._factored
             else tr('P(FoS<1) = {0:.2%}')).format(pf),
            color="#c0392b", fontsize=11, fontweight="bold",
            transform=ax.transData,
        )
        ax.set_xlabel(tr("Over-design factor") if self._factored
                      else tr("Factor of Safety"))
        ax.set_ylabel(tr("Cumulative probability"))
        ax.set_title(tr('CDF over {0} surfaces').format(len(values)))
        ax.set_ylim(0, 1.02)
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class ScatterDialog(_ChartDialogBase):
    """Generic scatter: X vs Y."""

    def __init__(
        self,
        xs: Sequence[float],
        ys: Sequence[float],
        xlabel: str = "X",
        ylabel: str = "Y",
        title: str = "Scatter",
        parent=None,
    ) -> None:
        super().__init__(title, parent)
        if self.canvas is None:
            return
        ax = self.ax()
        ax.scatter(xs, ys, s=12, alpha=0.6, color="#3a87c8")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class SFAlongSlopeDialog(_ChartDialogBase):
    """Factor of safety along the slope, from EVERY valid surface: the
    series ``interpretation.sf_along_slope`` computes — each surface's
    factor at its slope intercepts, or the minimum in each bin.

    v0.1.433 (D411) — the chart of Interpret's *Graph SF Along Slope...*, by
    the owner's decision: no menu opened this dialog, and it drew the
    critical surface's global factor at every slice, the reading v0.1.82
    retired from Interpret («one number, repeated»). The numbers are the
    ones that entry plotted before; the line of factor 1 is added.
    """

    def __init__(self, xs, ys, binned: bool = True, ylabel=None,
                 parent=None, factored: bool = False) -> None:
        # v0.1.435 (D413) -- ``factored`` as in :class:`HistogramDialog`
        super().__init__(tr("Over-design Factor Along Slope") if factored
                         else tr("Factor of Safety Along Slope"), parent)
        if ylabel is None and factored:
            ylabel = tr("Over-design factor")
        if self.canvas is None:
            return
        ax = self.ax()
        if not xs:
            ax.text(0.5, 0.5, tr("No valid surfaces."),
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw_idle()
            return
        ax.plot(list(xs), list(ys), marker="o" if binned else ".")
        ax.axhline(1.0, color="#c0392b", linestyle="--", linewidth=1.0)
        ax.set_xlabel(tr("X coordinate"))
        ax.set_ylabel(ylabel or tr("Factor of safety"))
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class SensitivityDialog(_ChartDialogBase):
    """Tornado of a sensitivity run: one bar per variable, the change of the
    factor from the variable's minimum to its maximum, with its sign — the
    numbers the ranking prints (``SensitivityResult.ranking``,
    ``VariableSweep.fos_range`` and ``is_increasing``).

    v0.1.433 (D411) — by the owner's decision it opens from Interpret's
    Statistics menu: no menu opened it, and its axis said «per standard
    deviation» of numbers it never was given. ``effects`` is a list of
    ``(label, signed range)`` pairs (or a ``{label: value}`` dict);
    :func:`sensitivity_effects` builds it. A list, and bars at numeric
    positions, because two variables can be shown with the same label (two
    loads of the same magnitude): keyed by the label, or placed by it on a
    categorical axis, they shared one bar (review of 0.1.433).
    """

    def __init__(self, effects, xlabel=None, method=None,
                 parent=None) -> None:
        # v0.1.435 (D413) -- the method it draws, named when given: Interpret
        # drew the run's first and said nothing
        if method:
            from ogr_gui.labels import method_name
            title = tr("Sensitivity Tornado — {0}").format(method_name(method))
        else:
            title = tr("Sensitivity — Tornado")
        super().__init__(title, parent)
        if self.canvas is None:
            return
        ax = self.ax()
        if not effects:
            ax.text(0.5, 0.5, tr("No sensitivity result."),
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw_idle()
            return

        pairs = list(effects.items() if isinstance(effects, dict)
                     else effects)
        pairs.sort(key=lambda kv: abs(kv[1]))
        names = [str(k) for k, _ in pairs]
        vals = [v for _, v in pairs]
        colors = ["#c0392b" if v < 0 else "#27ae60" for v in vals]
        ax.barh(range(len(vals)), vals, color=colors, alpha=0.85)
        ax.set_yticks(range(len(vals)), names)
        ax.axvline(0, color="#333", linewidth=0.8)
        # the bar is the factor's range over the sweep (``fos_range``), the
        # ranking's number, signed by ``is_increasing``: on a sweep that is
        # not monotonic it is not FS(max) - FS(min) of the variable, so the
        # axis says what it is (review of 0.1.433)
        ax.set_xlabel(xlabel or tr(
            "Range of the factor of safety over the variable's sweep "
            "(positive: larger at the variable's maximum)"))
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis="x")
        self.canvas.draw_idle()


def sensitivity_effects(sweeps: dict, name=None) -> list:
    """``[(label, signed range)]`` of a sensitivity run's sweeps for the
    tornado, one pair per swept variable: its ``fos_range``, positive when
    the factor at the variable's maximum is not below the one at its minimum
    (``is_increasing``). A variable with a note was never swept and is left
    out, as the ranking leaves it (D91). ``name(key, stored)`` gives the
    shown label. A list and not a dict keyed by the label: two variables
    shown alike would share one entry."""
    out = []
    for vs in sweeps.values():
        if getattr(vs, "note", None) or not getattr(vs, "values", None):
            continue
        label = name(vs.key, vs.label) if name else vs.label
        out.append((label, vs.fos_range if vs.is_increasing
                    else -vs.fos_range))
    return out


# ======================================================================
# v0.1.15 — Multi-line plot (Show Values Along Surface)
# ======================================================================
class MultiLineDialog(_ChartDialogBase):
    """Plot multiple series sharing a common x axis.

    Used by the Interpret "Show Values Along Surface" feature to display
    σ'ₙ, τ, u and α along the critical surface in a single window.
    """

    def __init__(
        self,
        xs,
        series,            # list of (label, y_values) or (label, xs, ys)
        xlabel: str = "x",
        title: str = "Values",
        parent=None,
    ) -> None:
        super().__init__(parent=parent, title=title)
        # v0.1.70 — this read ``self.fig``, which the base class does not
        # define; it is ``self.figure``, reached through ``ax()``. Every
        # construction raised AttributeError, so "Show Values Along
        # Surface" in the Interpret window had never worked. Its caller
        # guarded only against ImportError, so the failure escaped.
        ax = self.ax()
        if ax is None:                       # matplotlib not installed
            return
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        for item in series:
            # v0.1.435 (D413) -- a series may carry its own x, (label, xs,
            # ys): the drawdown sweep's methods are valid at different
            # levels, and one shared x put a factor at a level it was not
            # computed at
            label, sx, ys = (item if len(item) == 3
                             else (item[0], xs, item[1]))
            ax.plot(sx, ys, marker="o", linewidth=1.2, label=label)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
        self.canvas.draw()
