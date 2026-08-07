# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.49 — Interpret phase I1: result context.

The post-processor specification describes four things this window was
missing: a graphical **colour scale legend**, the factor of safety
**anchored to the critical surface**, an **active algorithm** read-out,
and a **status bar** whose SNAP / GRID / ORTHO / OSNAP and DATA TIPS
words can be toggled by clicking them.

The point worth testing rather than merely building is **agreement**:

* the legend is generated from the SAME colour function the canvas uses,
  so it cannot say one thing while the drawing says another — the
  previous legend was a hand-written HTML table with hard-coded bands
  that reported identical values whatever the results contained;
* everything that depends on the active method — the legend range, its
  marker, the algorithm label — must follow when the method is switched,
  because each method has its own critical surface.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []      # keep references: Qt destroys child widgets otherwise


def _interpret(methods=("bishop_simplified", "spencer")):
    from test_slide_validation_ej1 import _ej1_project

    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d import BishopSimplified, Spencer
    from ogr_slip2d.search import GridSearch

    QApplication.instance() or QApplication([])
    set_language("en")
    factory = {"bishop_simplified": BishopSimplified, "spencer": Spencer}
    p = _ej1_project()
    res = {}
    for mid in methods:
        res[mid] = GridSearch(
            method=factory[mid](), grid_x=(70, 100), grid_y=(60, 85),
            grid_nx=3, grid_ny=3, radius_increment=10, min_radius=15,
            num_slices=16, min_area=0.5).run(p)
    w = InterpretWindow(p, res, None)
    _WINDOWS.append(w)
    return p, res, w


# ======================================================================
@_requires_qt
class TestColourScaleLegend:
    def test_legend_exists_and_is_docked(self):
        _p, _r, w = _interpret()
        assert w.legend is not None
        assert w.legend_dock is not None

    def test_range_covers_the_results(self):
        _p, res, w = _interpret(("bishop_simplified",))
        vmin, vmax = w.legend.value_range()
        crit = res["bishop_simplified"].critical.fos
        assert vmin <= crit <= vmax
        assert vmax > vmin

    def test_critical_value_is_marked(self):
        _p, res, w = _interpret(("bishop_simplified",))
        assert abs(w.legend._mark
                   - res["bishop_simplified"].critical.fos) < 1e-9

    def test_legend_and_canvas_use_one_colour_function(self):
        """The legend and the drawing must ask the same object for the
        colour of a value; otherwise they can disagree silently.

        v0.1.50 moved that shared object from the canvas's built-in
        convention to the ``ContourSettings``, so that a change of
        palette, range or interval count reaches both at once. The
        invariant under test is unchanged — one source of truth — only
        the object providing it moved.
        """
        _p, _r, w = _interpret(("bishop_simplified",))
        assert w.legend._colour_fn == w.contours.colour_for
        assert w.canvas._contour_colour_fn == w.contours.colour_for
        for value in (0.8, 1.2, 2.0, 5.0):
            assert w.legend._colour_fn(value) == \
                w.contours.colour_for(value)

    def test_number_formatting(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        w.legend.configure(0.0, 1.0, w.legend._colour_fn, decimals=3)
        assert w.legend.format_value(0.5) == "0.500"
        w.legend.configure(0.0, 1.0, w.legend._colour_fn, decimals=2,
                           scientific=True)
        assert "e" in w.legend.format_value(0.5)

    def test_degenerate_range_is_handled(self):
        """A model where every surface has the same factor must not make
        the legend divide by zero."""
        _p, _r, w = _interpret(("bishop_simplified",))
        w.legend.configure(1.5, 1.5, w.legend._colour_fn)
        vmin, vmax = w.legend.value_range()
        assert vmax > vmin

    def test_paints_without_error(self):
        from PySide6.QtGui import QPixmap
        _p, _r, w = _interpret(("bishop_simplified",))
        w.legend.resize(120, 300)
        pm = QPixmap(120, 300)
        w.legend.render(pm)        # must not raise


# ======================================================================
@_requires_qt
class TestActiveAlgorithmAndLabel:
    def test_algorithm_label_names_the_method(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        assert "bishop_simplified" in w.lbl_algorithm.text()

    def test_algorithm_label_shows_the_factor(self):
        _p, res, w = _interpret(("bishop_simplified",))
        fos = f"{res['bishop_simplified'].critical.fos:.3f}"
        assert fos in w.lbl_algorithm.text()

    def test_anchored_label_matches_the_critical_surface(self):
        _p, res, w = _interpret(("bishop_simplified",))
        assert w.critical_label_text() == \
            f"{res['bishop_simplified'].critical.fos:.3f}"

    def test_active_algorithm_reported(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        assert w.active_algorithm() == "bishop_simplified"


# ======================================================================
@_requires_qt
class TestMethodSwitchKeepsEverythingInStep:
    def test_algorithm_label_follows_the_switch(self):
        _p, _r, w = _interpret()
        w.cb_method.setCurrentIndex(w.cb_method.findData("spencer"))
        assert "spencer" in w.lbl_algorithm.text()
        assert w.active_algorithm() == "spencer"

    def test_legend_marker_follows_the_switch(self):
        """Each method has its own critical surface, so the marker must
        move with it."""
        _p, res, w = _interpret()
        w.cb_method.setCurrentIndex(w.cb_method.findData("spencer"))
        assert abs(w.legend._mark - res["spencer"].critical.fos) < 1e-9

    def test_anchored_label_follows_the_switch(self):
        _p, res, w = _interpret()
        w.cb_method.setCurrentIndex(w.cb_method.findData("spencer"))
        assert w.critical_label_text() == \
            f"{res['spencer'].critical.fos:.3f}"


# ======================================================================
@_requires_qt
class TestStatusIndicators:
    def test_all_five_words_present(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        for name in ("DATA TIPS", "SNAP", "GRID", "ORTHO", "OSNAP"):
            assert name in w.indicators.labels, name

    def test_clicking_toggles(self):
        """The specification is explicit: these must be toggleable by
        clicking the words, not only from a dialog."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QMouseEvent
        _p, _r, w = _interpret(("bishop_simplified",))
        lab = w.indicators.labels["ORTHO"]
        before = lab.state()
        ev = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(3, 3),
                         Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        lab.mousePressEvent(ev)
        assert lab.state() is not before

    def test_toggle_emits_a_signal(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        seen = []
        w.indicators.connect("SNAP", lambda on: seen.append(on))
        w.indicators.set_state("SNAP", True)
        assert seen == [True]

    def test_setting_the_same_state_is_a_no_op(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        seen = []
        w.indicators.connect("OSNAP", lambda on: seen.append(on))
        current = w.indicators.state("OSNAP")
        w.indicators.set_state("OSNAP", current)
        assert seen == []

    def test_visual_state_differs_when_on(self):
        """On and off must be legible at a glance."""
        _p, _r, w = _interpret(("bishop_simplified",))
        lab = w.indicators.labels["GRID"]
        lab.setState(False)
        off = lab.styleSheet()
        lab.setState(True)
        assert lab.styleSheet() != off

    def test_coordinates_readout(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        w.indicators.set_coordinates(12.345, 67.891)
        text = w.indicators.coords.text()
        assert "12.345" in text and "67.891" in text

    def test_states_snapshot(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        states = w.indicators.states()
        assert set(states) == {"DATA TIPS", "SNAP", "GRID", "ORTHO",
                               "OSNAP"}
        assert all(isinstance(v, bool) for v in states.values())


# ======================================================================
@_requires_qt
class TestViewMenu:
    def _view_items(self, w):
        for act in w.menuBar().actions():
            if act.menu() is not None and act.text() == "View":
                return [a.text() for a in act.menu().actions() if a.text()]
        return None

    def test_view_menu_exists(self):
        """Interpret had no View menu at all."""
        _p, _r, w = _interpret(("bishop_simplified",))
        items = self._view_items(w)
        assert items is not None, "no View menu"

    def test_offers_legend_and_data_tips(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        items = self._view_items(w)
        assert any("Legend" in t for t in items)
        assert any("Data Tips" in t for t in items)
        assert any("Zoom" in t for t in items)

    def test_legend_can_be_hidden(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        for act in w.menuBar().actions():
            if act.menu() is not None and act.text() == "View":
                for a in act.menu().actions():
                    if a.text() == "Show Legend":
                        a.setChecked(False)
                        assert w.legend_dock.isVisible() is False
                        a.setChecked(True)
                        return
        raise AssertionError("Show Legend not found")
