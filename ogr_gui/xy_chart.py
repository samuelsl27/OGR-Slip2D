# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A one-off XY chart in its own NON-modal window.

v0.1.308 (D311) — moved out of ``InterpretWindow._plot_xy`` so that every
window that plots "these numbers" draws them the same way. *Interpret
Groundwater* drew its factor of safety against time in a dialog of its own
opened with ``exec()``: modal, so the chart could not be compared with the
model beside it, and a path a test reaches blocked for ever without a
screen.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def show_xy_chart(parent, title, series, xlabel, ylabel, marker="o",
                  yscale="linear"):
    """Plot ``series`` — ``[(label, xs, ys)]`` — in a non-modal window
    owned by ``parent``; returns the window, or None without matplotlib.

    ``yscale`` is matplotlib's (v0.1.269: the convergence chart spans ten
    decades, and plotting log10 of the values instead would turn a zero
    change into -inf). The window is kept on ``parent._chart_windows`` so Qt
    does not collect it as soon as this returns.
    """
    try:
        import matplotlib
        matplotlib.use("QtAgg", force=False)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
    except ImportError:
        return None
    from PySide6.QtWidgets import QDialog, QVBoxLayout
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(680, 460)
    lay = QVBoxLayout(dlg)
    fig = Figure(figsize=(6.4, 4.2), tight_layout=True)
    ax = fig.add_subplot(111)
    for label, xs, ys in series:
        ax.plot(xs, ys, marker=marker, label=label)
    if yscale != "linear":
        ax.set_yscale(yscale)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    if len(series) > 1 or series and series[0][0]:
        ax.legend(fontsize=8)
    lay.addWidget(FigureCanvasQTAgg(fig))
    # NON-modal on purpose: a chart that blocks the application cannot be
    # compared against the model beside it, and two charts cannot be held
    # open at once.
    dlg.show()
    if not hasattr(parent, "_chart_windows"):
        parent._chart_windows = []
    parent._chart_windows.append(dlg)
    return dlg
