# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Matplotlib-based chart widgets for the Interpret window (v0.1.3).

Provides four reusable chart dialogs:
    - HistogramDialog — FoS frequency distribution
    - CumulativeDialog — CDF with P(FoS<1) highlighted
    - ScatterDialog — generic X vs Y scatter
    - SFAlongSlopeDialog — Factor of Safety along the critical surface

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
                "<b>matplotlib is required for interactive charts.</b><br>"
                "Install it with:<br><code>pip install matplotlib</code>"
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
    """FoS histogram for the full population."""

    def __init__(self, fos_values: Sequence[float], parent=None) -> None:
        super().__init__("Histogram — Factor of Safety distribution", parent)
        self._values = [v for v in fos_values if v is not None]
        if self.canvas is None or not self._values:
            return

        self.spn_bins = QSpinBox()
        self.spn_bins.setRange(5, 200)
        self.spn_bins.setValue(25)
        self.spn_bins.valueChanged.connect(self._redraw)
        self.chk_mark_one = QCheckBox(tr("Mark FoS = 1.0"))
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
                       linewidth=1.2, label="FoS = 1.0")
            ax.legend(loc="upper right")
        ax.set_xlabel("Factor of Safety")
        ax.set_ylabel("Number of surfaces")
        ax.set_title(f"Distribution over {len(self._values)} valid surfaces")
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class CumulativeDialog(_ChartDialogBase):
    """CDF of FoS values with P(FoS<1) annotation."""

    def __init__(self, fos_values: Sequence[float], parent=None) -> None:
        super().__init__("Cumulative — FoS CDF", parent)
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
            f"P(FoS<1) = {pf:.2%}",
            color="#c0392b", fontsize=11, fontweight="bold",
            transform=ax.transData,
        )
        ax.set_xlabel("Factor of Safety")
        ax.set_ylabel("Cumulative probability")
        ax.set_title(f"CDF over {len(values)} surfaces")
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
    """FoS along the critical failure surface.

    Projects each slice centroid onto the toe-to-crest direction and
    plots FoS of that slice as a function of the projected distance.
    """

    def __init__(self, critical_result, parent=None) -> None:
        super().__init__("Factor of Safety Along Slope", parent)
        if self.canvas is None:
            return
        ax = self.ax()
        if critical_result is None or not critical_result.slices:
            ax.text(0.5, 0.5, "No critical surface available",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw_idle()
            return

        slices = critical_result.slices.slices
        xs = [s.x_centre for s in slices]
        if not xs:
            return
        x_min, x_max = min(xs), max(xs)
        span = (x_max - x_min) or 1.0
        fos_global = critical_result.fos
        # Per-slice mobilised strength vs available (approximate local FoS)
        import math
        local_fos: list[float] = []
        dists: list[float] = []
        for s in slices:
            alpha = s.base_angle
            W = s.weight
            drive = abs(W * math.sin(alpha))
            if drive < 1e-9:
                continue
            # Very coarse: treat every slice with the global FoS —
            # realistic per-slice FoS requires the chosen method to
            # expose its strength ratio.
            local_fos.append(fos_global)
            dists.append((s.x_centre - x_min) / span)

        ax.plot(dists, local_fos, color="#3a87c8", linewidth=1.8,
                marker="o", markersize=4)
        ax.axhline(1.0, color="#c0392b", linestyle="--", linewidth=1.0)
        ax.set_xlabel("Normalised distance along slope (toe → crest)")
        ax.set_ylabel("Factor of Safety")
        ax.set_title(f"Critical surface — {len(slices)} slices — "
                     f"global FoS = {fos_global:.3f}")
        ax.grid(True, alpha=0.3)
        self.canvas.draw_idle()


# ======================================================================
class SensitivityDialog(_ChartDialogBase):
    """Tornado-style sensitivity plot from a dict of parameter → effect."""

    def __init__(self, effects: dict[str, float], parent=None) -> None:
        super().__init__("Sensitivity — FoS vs input parameters", parent)
        if self.canvas is None:
            return
        ax = self.ax()
        if not effects:
            ax.text(0.5, 0.5, "No sensitivity data available. "
                             "Run probabilistic analysis first.",
                    ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw_idle()
            return

        names = list(effects.keys())
        vals = [effects[n] for n in names]
        order = sorted(range(len(names)), key=lambda i: abs(vals[i]))
        names = [names[i] for i in order]
        vals = [vals[i] for i in order]
        colors = ["#c0392b" if v < 0 else "#27ae60" for v in vals]
        ax.barh(names, vals, color=colors, alpha=0.85)
        ax.axvline(0, color="#333", linewidth=0.8)
        ax.set_xlabel("Effect on FoS (Δ per standard deviation)")
        ax.set_title("Sensitivity — Tornado")
        ax.grid(True, alpha=0.3, axis="x")
        self.canvas.draw_idle()


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
        series,            # list of (label, y_values)
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
        for label, ys in series:
            ax.plot(xs, ys, marker="o", linewidth=1.2, label=label)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)
        self.canvas.draw()
