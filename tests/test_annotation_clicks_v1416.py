# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.416 (D354) — the annotation tools are drawn with clicks on the canvas.

The finding (the fifth interface test, 0.1.355, H7 and H14): Tools → Draw →
Line opened «Dibujar» with «Introduce 2 punto(s) como x,y  x,y …», and Add
Text asked for the point and the text in dialogs; nothing was clicked. The
inventory: all twelve tools — Line, Arrow, Polyline, Polygon, Rectangle,
Circle, Add Text, the four Dimensions and Add Axes — went through one
``_start_annotation``, which asked ``QInputDialog`` for the points. Measure
already used clicks (D329a). The decision (the owner, 2026-11-02): clicks
only; an exact point is typed the way every drawing takes one, in the
status bar's X,Y box or the Coordinate Table; a text asks for its words
after the click.

What these tests protect, on the real canvas — shown, at a known zoom,
snapping off (memory of 0.1.311: a canvas not shown is 98 × 28 px and every
click snaps to one vertex), real mouse events —:

* each of the twelve menu entries enters its mode and no dialog asks for a
  coordinate; its clicks make the annotation of its kind, at the clicked
  points, as ONE undo step that undo and redo give back exactly; and the
  canvas goes back to Select;
* a polygon needs three points: Enter on two says so and keeps drawing;
* the status bar's X,Y box adds an exact point;
* Esc and a cancelled text leave nothing, and no step.

``QInputDialog.getText`` is replaced by a fake for the whole file: it
answers the text of Add Text and records any other question, so that on the
old tree a case fails instead of hanging the run.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QTransform
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


#: One model unit is this many pixels: a click lands within half a pixel.
_SCALE = 15.0
_TOL = 1.0 / _SCALE

_WINDOW: list = []


def _window():
    """The one window of the file: the demo, shown, at 15 px per metre
    around its middle, with snapping, ortho and object snap off."""
    if not _WINDOW:
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        w = MainWindow()
        w._attach_project(build_demo_project())
        w.resize(1200, 800)
        w.show()
        QApplication.processEvents()
        c = w.canvas
        s = c.snap_settings
        s.snap = s.ortho = s.osnap = False
        _WINDOW.append(w)
    w = _WINDOW[0]
    w.canvas.setTransform(QTransform().scale(_SCALE, -_SCALE))
    w.canvas.centerOn(25.0, 12.5)
    w.command_stack.clear()
    w.project.is_dirty = False
    return w


@contextlib.contextmanager
def _questions(text=("Nota", True)):
    """``QInputDialog.getText`` replaced: Add Text's question (title
    "Text") gets ``text``, any other is cancelled, and every question asked
    is recorded. Cancelled and not answered: on the old tree the question
    was the coordinates, and a wrong answer opened a modal warning."""
    from PySide6.QtWidgets import QInputDialog
    asked = []
    raw = QInputDialog.__dict__.get("getText")

    def fake(_parent, title, label, *a, **k):
        asked.append((title, label))
        return text if title == "Text" else ("", False)
    QInputDialog.getText = staticmethod(fake)
    try:
        yield asked
    finally:
        if raw is None:
            del QInputDialog.getText
        else:
            QInputDialog.getText = raw


def _click(c, x, y):
    """A real left click on the viewport at the model point (x, y)."""
    p = c.mapFromScene(QPointF(x, y))
    QTest.mouseClick(c.viewport(), Qt.LeftButton, Qt.NoModifier,
                     QPoint(p.x(), p.y()))


def _key(c, key):
    QTest.keyClick(c.viewport(), key)


def _dump(project):
    return json.dumps(project.to_dict(), sort_keys=True, default=str)


def _tools():
    """(menu action, mode, kind, clicks, Enter at the end?)"""
    from ogr_core.annotations import AnnotationKind as K
    from ogr_gui.canvas.tool_mode import ToolMode as T
    two = [(8.0, 18.0), (20.0, 22.0)]
    return [
        ("draw_line", T.DRAW_ANN_LINE, K.LINE, two, False),
        ("draw_arrow", T.DRAW_ANN_ARROW, K.ARROW, two, False),
        ("draw_polyline", T.DRAW_ANN_POLYLINE, K.POLYLINE,
         [(5.0, 20.0), (15.0, 23.0), (30.0, 21.0)], True),
        ("draw_polygon", T.DRAW_ANN_POLYGON, K.POLYGON,
         [(5.0, 5.0), (15.0, 5.0), (15.0, 12.0), (5.0, 12.0)], True),
        ("draw_rect", T.DRAW_ANN_RECTANGLE, K.RECTANGLE,
         [(6.0, 4.0), (18.0, 10.0)], False),
        ("draw_circle", T.DRAW_ANN_CIRCLE, K.CIRCLE,
         [(30.0, 8.0), (34.0, 8.0)], False),
        ("add_text", T.DRAW_ANN_TEXT, K.TEXT, [(10.0, 22.0)], False),
        ("dim_len", T.DRAW_ANN_DIM_LENGTH, K.DIMENSION_LENGTH,
         [(0.0, 2.0), (50.0, 2.0)], False),
        ("dim_ang", T.DRAW_ANN_DIM_ANGLE, K.DIMENSION_ANGLE,
         [(45.0, 5.0), (35.0, 5.0), (40.0, 12.0)], False),
        ("dim_x", T.DRAW_ANN_DIM_X, K.DIMENSION_X,
         [(25.0, 23.0), (35.0, 18.0)], False),
        ("dim_y", T.DRAW_ANN_DIM_Y, K.DIMENSION_Y,
         [(42.0, 2.0), (42.0, 13.0)], False),
        ("add_axes", T.DRAW_ANN_AXES, K.AXES, [(2.0, 2.0), (48.0, 23.0)],
         False),
    ]


# ======================================================================
@_requires_qt
class TestEveryToolIsClicked:

    def test_every_tool_from_its_menu_entry(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        c = w.canvas
        done = []
        with _questions() as asked:
            for key, mode, kind, clicks, enter in _tools():
                w.command_stack.clear()
                before = _dump(w.project)
                n = len(w.project.annotations)
                w._actions[key].trigger()
                assert c.tool_mode == mode, (key, c.tool_mode)
                for x, y in clicks:
                    _click(c, x, y)
                if enter:
                    assert c.tool_mode == mode, key   # waits for Enter
                    _key(c, Qt.Key_Return)
                QApplication.processEvents()
                assert c.tool_mode == ToolMode.SELECT, (key, c.tool_mode)
                assert c._last_snap is None, key
                assert len(w.project.annotations) == n + 1, key
                ann = list(w.project.annotations)[-1]
                assert ann.kind == kind, (key, ann.kind)
                assert len(ann.points) == len(clicks), (key, ann.points)
                for (x, y), (px, py) in zip(clicks, ann.points):
                    assert abs(px - x) <= _TOL and abs(py - y) <= _TOL, \
                        (key, (x, y), (px, py))
                assert w.command_stack.history() == (["Set annotation"],
                                                     []), key
                after = _dump(w.project)
                w.act_undo()
                assert _dump(w.project) == before, key
                w.act_redo()
                assert _dump(w.project) == after, key
                done.append(key)
        # the only question asked was Add Text's words, after its click
        assert asked == [("Text", "Text:")], asked
        assert len(done) == 12

    def test_the_text_is_the_answered_one(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        with _questions(("Nota de prueba", True)):
            w._actions["add_text"].trigger()
            _click(w.canvas, 12.0, 21.0)
        ann = list(w.project.annotations)[-1]
        assert ann.kind == K.TEXT and ann.text == "Nota de prueba"


@_requires_qt
class TestTheDrawingRules:

    def test_a_polygon_needs_three_points(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        c = w.canvas
        n = len(w.project.annotations)
        with _questions():
            w._actions["draw_polygon"].trigger()
            _click(c, 5.0, 5.0)
            _click(c, 15.0, 5.0)
            _key(c, Qt.Key_Return)
            assert c.tool_mode == ToolMode.DRAW_ANN_POLYGON
            assert w.ogr_status.currentMessage() == \
                "This shape needs 3 point(s).", w.ogr_status.currentMessage()
            assert len(w.project.annotations) == n
            _click(c, 10.0, 12.0)
            _key(c, Qt.Key_Return)
        assert c.tool_mode == ToolMode.SELECT
        assert len(list(w.project.annotations)[-1].points) == 3

    def test_the_status_bar_types_an_exact_point(self):
        """The X,Y box of the status bar, as for a boundary: the line's
        points are the typed ones, to the bit."""
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        with _questions():
            w._actions["draw_line"].trigger()
            w._on_manual_coords(1.25, 2.5)
            _click(w.canvas, 20.0, 20.0)
        ann = list(w.project.annotations)[-1]
        assert ann.kind == K.LINE
        assert ann.points[0] == (1.25, 2.5), ann.points

    def test_esc_leaves_nothing(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        c = w.canvas
        before = _dump(w.project)
        with _questions():
            w._actions["draw_line"].trigger()
            _click(c, 8.0, 18.0)
            _key(c, Qt.Key_Escape)          # the drawing
            _key(c, Qt.Key_Escape)          # the tool
        assert c.tool_mode == ToolMode.SELECT
        assert _dump(w.project) == before
        assert w.command_stack.history() == ([], [])

    def test_a_cancelled_text_leaves_nothing(self):
        w = _window()
        before = _dump(w.project)
        with _questions(("", False)) as asked:
            w._actions["add_text"].trigger()
            _click(w.canvas, 10.0, 22.0)
        assert asked == [("Text", "Text:")], asked
        assert _dump(w.project) == before
        assert w.command_stack.history() == ([], [])
        assert not w.project.is_dirty
