# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Every chart dialog can actually be constructed.

``MultiLineDialog`` could not. It read ``self.fig``, which the base class
does not define — it is ``self.figure`` — so **every** construction
raised ``AttributeError``. Its only caller, *Show Values Along Surface*
in the Interpret window, guarded the call with ``except ImportError``,
which does not catch that; the option raised out of the window instead of
falling back to its text table. It had been that way since the dialog was
written, because nothing ever built one.

That is the whole invariant here: a chart class that no test constructs
is a chart class that may not construct. These are three-line tests
against a bug that survived in production, and they are cheap because
none of them needs data that means anything — only data of the right
shape.

Rule 5: the dialogs are created with a QApplication that already exists
under the offscreen platform, and never shown, so nothing global moves.
"""
from __future__ import annotations


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _mpl() -> bool:
    from ogr_gui.dialogs.chart_dialogs import MPL_AVAILABLE
    return MPL_AVAILABLE


# ======================================================================
class TestEveryChartDialogConstructs:
    """One per public dialog in the module."""

    def test_multi_line(self):
        """The one that was broken."""
        _app()
        from ogr_gui.dialogs.chart_dialogs import MultiLineDialog
        d = MultiLineDialog(
            [0.0, 1.0, 2.0],
            series=[("a", [1.0, 2.0, 3.0]), ("b", [3.0, 2.0, 1.0])],
            xlabel="x", title="t")
        assert d is not None

    def test_multi_line_with_one_series(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import MultiLineDialog
        assert MultiLineDialog([0.0, 1.0], series=[("only", [1.0, 2.0])])

    def test_scatter(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import ScatterDialog
        assert ScatterDialog([1.0, 2.0], [3.0, 4.0], "x", "y", "t")

    def test_histogram(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import HistogramDialog
        assert HistogramDialog([1.0, 1.2, 1.4, 1.1]) is not None

    def test_cumulative(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import CumulativeDialog
        assert CumulativeDialog([1.0, 1.2, 1.4, 1.1]) is not None

    def test_sf_along_slope(self):
        """It takes a result object, so the empty case is the cheap one
        to pin — and it is the one the Interpret window hits before any
        analysis has run."""
        _app()
        from ogr_gui.dialogs.chart_dialogs import SFAlongSlopeDialog
        assert SFAlongSlopeDialog(None) is not None

    def test_sensitivity(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import SensitivityDialog
        assert SensitivityDialog({"c'": 0.4, "phi'": 0.2}) is not None

    def test_sensitivity_with_nothing_to_show(self):
        _app()
        from ogr_gui.dialogs.chart_dialogs import SensitivityDialog
        assert SensitivityDialog({}) is not None


# ======================================================================
class TestTheChartActuallyDrew:
    """Constructing is not enough: a silent no-op would also 'pass'."""

    def test_multi_line_draws_one_line_per_series(self):
        if not _mpl():
            return          # no matplotlib: the dialog is a stub by design
        _app()
        from ogr_gui.dialogs.chart_dialogs import MultiLineDialog
        d = MultiLineDialog(
            [0.0, 1.0, 2.0],
            series=[("a", [1.0, 2.0, 3.0]), ("b", [3.0, 2.0, 1.0])])
        ax = d.ax()
        assert ax is not None
        assert len(ax.get_lines()) == 2
