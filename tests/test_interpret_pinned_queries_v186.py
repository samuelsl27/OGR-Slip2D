# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Interpret: a click keeps a surface, and a kept surface keeps its number.

WHAT INVARIANT THIS PROTECTS, and the trap it exists to avoid.

``CanvasView.scene_clicked`` is what turns a hovered surface into a Query
and what picks a slice for the Slice Data panel. Its emission was guarded
by ``not event.isAccepted()``, and a QMouseEvent for a button press
arrives ALREADY ACCEPTED — so the condition was never true and the signal
was never emitted, in any build, since v0.1.12. Two documented features
looked implemented and neither could fire.

It stayed green for seventy-four versions because the test that covered it
**called the slot directly**. Calling ``w._on_canvas_click_default(x, y)``
proves the handler works; it proves nothing about whether anything ever
calls it. Every case here dispatches a real ``QMouseEvent`` through
``CanvasView.mousePressEvent`` for that reason, and the first one asserts
the signal itself.

The second invariant is the read-out. ``_commit_query`` cleared the
floating label on commit, so a surface's factor of safety disappeared at
the exact moment it became a Query — which defeats keeping several, the
whole point being to compare two or three at once.

Reference: Slide Interpret > Slip Surfaces > Query > Add Query — "click
the left mouse button and a Query will be created for that slip surface".

Author: Samuel Sáez López (UPCT)
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


_WINDOWS = []


def _interpret():
    from test_slide_validation_ej1 import _ej1_project

    import ogr_slip2d as M
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language("en")
    p = _ej1_project()
    r = GridSearch(method=M.BishopSimplified(), grid_x=(70, 100),
                   grid_y=(58, 84), grid_nx=4, grid_ny=4,
                   radius_increment=8, min_radius=12, num_slices=14,
                   min_area=0.5).run(p)
    w = InterpretWindow(p, {"bishop_simplified": r}, None)
    w.canvas.resize(800, 600)
    w.canvas.show()
    _WINDOWS.append(w)
    return p, r, w


def _click(view, scene_x, scene_y):
    """A real left-click at a scene point, through mousePressEvent."""
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QPointF, QEvent
    pos = QPointF(view.mapFromScene(QPointF(scene_x, scene_y)))
    view.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, pos, view.mapToGlobal(pos),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))


def _labels(w):
    return [it for it in w.canvas.scene().items()
            if getattr(it, "_is_query_label", False)]


def _centre_of(res):
    sd = res.surface.to_dict()
    return sd["centre_x"], sd["centre_y"]


# ======================================================================
@_requires_qt
class TestTheCanvasClickReachesTheWindow:
    def test_scene_clicked_is_emitted_by_a_real_mouse_event(self):
        """The signal itself. This is the bug, in one assertion."""
        from ogr_gui.canvas.canvas_view import ToolMode
        _p, _r, w = _interpret()
        w.canvas.set_tool_mode(ToolMode.SELECT)
        seen = []
        w.canvas.scene_clicked.connect(lambda x, y: seen.append((x, y)))
        _click(w.canvas, 88.0, 70.5)
        assert seen, "scene_clicked never fired for a real left-click"

    def test_a_press_event_arrives_accepted(self):
        """Why the old guard could not work — kept so it stays fixed."""
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import Qt, QPointF, QEvent
        ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(10, 10),
                         QPointF(10, 10), Qt.LeftButton, Qt.LeftButton,
                         Qt.NoModifier)
        assert ev.isAccepted() is True


# ======================================================================
@_requires_qt
class TestAddQueryKeepsTheSurface:
    def test_a_click_creates_the_query(self):
        _p, r, w = _interpret()
        assert w._queries() == []
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        assert len(w._queries()) == 1, w._queries()

    def test_and_leaves_pick_mode(self):
        """The reference exits Add Query on the click."""
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        assert getattr(w, "_query_pick_mode", False) is False

    def test_two_surfaces_can_be_held_at_once(self):
        """The point of the feature: compare several factors of safety."""
        _p, r, w = _interpret()
        picks = sorted({(_centre_of(e)) for e in r.valid()})
        assert len(picks) >= 2, picks
        for cx, cy in picks[:2]:
            w._add_query()
            _click(w.canvas, cx, cy)
        assert len(w._queries()) == 2, w._queries()

    def test_the_same_surface_twice_is_still_one_query(self):
        _p, r, w = _interpret()
        cx, cy = _centre_of(r.critical)
        for _ in range(2):
            w._add_query()
            _click(w.canvas, cx, cy)
        assert len(w._queries()) == 1, w._queries()


# ======================================================================
@_requires_qt
class TestAQueryKeepsItsReadOut:
    def test_the_factor_of_safety_stays_on_screen(self):
        """It used to be erased at the moment of committing."""
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        labels = _labels(w)
        assert len(labels) == 1, labels
        assert labels[0].text() == f"{w._queries()[0].fos:.3f}"

    def test_one_read_out_per_query(self):
        _p, r, w = _interpret()
        picks = sorted({(_centre_of(e)) for e in r.valid()})[:2]
        for cx, cy in picks:
            w._add_query()
            _click(w.canvas, cx, cy)
        assert len(_labels(w)) == len(w._queries()) == 2

    def test_they_survive_a_redraw(self):
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        w._refresh_canvas_with_highlights()
        assert len(_labels(w)) == 1

    def test_they_do_not_pile_up_on_repeated_redraws(self):
        """The failure mode of anything added outside the one draw path."""
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        for _ in range(4):
            w._refresh_canvas_with_highlights()
        assert len(_labels(w)) == 1, len(_labels(w))

    def test_they_survive_a_change_of_display_mode(self):
        """A Query outlives the filter, so its number must too."""
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        for mode in ("all", "global_min", "minimum"):
            w._set_surface_mode(mode)
            assert len(_labels(w)) == 1, (mode, len(_labels(w)))

    def test_deleting_every_query_removes_them(self):
        _p, r, w = _interpret()
        w._add_query()
        cx, cy = _centre_of(r.critical)
        _click(w.canvas, cx, cy)
        assert _labels(w)
        w._queries().clear()
        w._refresh_canvas_with_highlights()
        assert _labels(w) == []
