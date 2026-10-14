# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.312 (D307) — *Move Boundary* by dragging moves the boundary, and leaves
one undo step.

The canvas previewed the drag by assigning ``v.x`` and ``v.y`` on the
project's own vertices. ``Vertex`` is a frozen dataclass, and has been since
the first commit in the history (v0.1.59), so the first move raised
``FrozenInstanceError``: the boundary never moved, ``boundary_dragged`` was
never emitted and no undo step was recorded. No test touched the mode. The
preview also rebuilt the whole scene, regions included, on every move.

Now a dashed ghost of the boundary follows the mouse, and the model is
written once, on release, by the window's existing ``_on_boundary_dragged``
(one ``ReplaceBoundaryCommand``).

The invariants, through the real canvas (mouse events, Esc):

* while dragging, the project is untouched and the ghost is displaced by
  the mouse's displacement; nothing reaches ``sys.excepthook``;
* on release the boundary is displaced by exactly that, as one step
  ("Edit Boundary") that undo and redo take back and forth, compared as
  JSON, and the ghost is gone;
* a click without moving leaves no step;
* Esc in the middle cancels the drag and keeps the tool, as it does with a
  drawing; a change of tool cancels it too; neither leaves a step;
* a scene rebuild in the middle of a drag does not break it;
* control: the vertex drag (QUÉ NO SE PUEDE MOVER) still leaves one step.
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402


def _ready():
    from ogr_gui.canvas.tool_mode import ToolMode
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    c = w.canvas
    # a real size, and no snapping: inside a window that is not shown the
    # canvas is 98 x 28 px, a model unit under one pixel (as
    # test_add_surface_three_points_v1168 sets it up)
    c.resize(900, 600)
    c.show()
    c.snap_settings.snap = False
    c.zoom_all()
    w.command_stack.clear()
    w.project.is_dirty = False
    w._set_tool(ToolMode.MOVE_BOUNDARY)
    return w, c


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


@contextlib.contextmanager
def _errors():
    """What a Qt slot raises goes to sys.excepthook, not to the test."""
    seen: list = []
    raw = sys.excepthook
    sys.excepthook = lambda *a: seen.append(
        "".join(traceback.format_exception(*a)))
    try:
        yield seen
    finally:
        sys.excepthook = raw


def _event(c, kind, scene_pt, button, buttons):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    vp = QPointF(c.mapFromScene(scene_pt))
    return QMouseEvent(kind, vp, c.viewport().mapToGlobal(vp.toPoint()),
                       button, buttons, Qt.NoModifier)


def _press(c, pt):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QMouseEvent
    c.mousePressEvent(_event(c, QMouseEvent.MouseButtonPress, pt,
                             Qt.LeftButton, Qt.LeftButton))


def _move(c, pt):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QMouseEvent
    c.mouseMoveEvent(_event(c, QMouseEvent.MouseMove, pt,
                            Qt.NoButton, Qt.LeftButton))


def _release(c, pt):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QMouseEvent
    c.mouseReleaseEvent(_event(c, QMouseEvent.MouseButtonRelease, pt,
                               Qt.LeftButton, Qt.NoButton))


def _esc(c):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))


def _grab(w):
    """The middle of the first segment of the External boundary, and a
    point (2, 1) model units away."""
    from PySide6.QtCore import QPointF
    b = w.project.external_boundary()
    v0, v1 = b.polyline.vertices[0], b.polyline.vertices[1]
    mid = QPointF((v0.x + v1.x) / 2, (v0.y + v1.y) / 2)
    return mid, QPointF(mid.x() + 2.0, mid.y() + 1.0)


def _as_seen(c, pt):
    """A scene point as the canvas reads it back from a mouse event."""
    return c.mapToScene(c.mapFromScene(pt))


def _verts(w, bi):
    return [(v.x, v.y) for v in w.project.boundaries[bi].polyline.vertices]


def _scale(w):
    x0, y0, x1, y1 = w.project.bounding_box()
    return max(x1 - x0, y1 - y0)


# ----------------------------------------------------------------------
class TestTheDragMovesTheBoundary:
    def test_press_move_release(self):
        w, c = _ready()
        try:
            mid, dst = _grab(w)
            before = _json(w.project)
            with _errors() as seen:
                _press(c, mid)
                bi = c._dragging_boundary
                assert bi is not None
                orig = _verts(w, bi)
                _move(c, dst)
                # the preview writes nothing
                assert _json(w.project) == before
                p0, p1 = _as_seen(c, mid), _as_seen(c, dst)
                dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
                assert abs(dx) > 1.0 and abs(dy) > 0.5
                ghost = c._drag_ghost
                assert ghost is not None and ghost.scene() is c.scene()
                tol = 1e-9 * _scale(w)
                assert math.isclose(ghost.pos().x(), dx, abs_tol=tol)
                assert math.isclose(ghost.pos().y(), dy, abs_tol=tol)
                _release(c, dst)
            assert seen == []
            moved = _verts(w, bi)
            assert len(moved) == len(orig)
            for (x, y), (mx, my) in zip(orig, moved):
                assert math.isclose(mx, x + dx, abs_tol=tol)
                assert math.isclose(my, y + dy, abs_tol=tol)
            assert w.command_stack.history() == (["Edit Boundary"], [])
            assert c._drag_ghost is None and c._dragging_boundary is None
            after = _json(w.project)
            w.act_undo()
            assert _json(w.project) == before
            w.act_redo()
            assert _json(w.project) == after
        finally:
            _done(w)

    def test_a_click_without_moving_leaves_no_step(self):
        w, c = _ready()
        try:
            mid, _dst = _grab(w)
            before = _json(w.project)
            with _errors() as seen:
                _press(c, mid)
                assert c._dragging_boundary is not None
                _release(c, mid)
            assert seen == []
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            assert c._drag_ghost is None
        finally:
            _done(w)


class TestCancelled:
    def test_esc_in_the_middle_cancels_and_keeps_the_tool(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            mid, dst = _grab(w)
            before = _json(w.project)
            with _errors() as seen:
                _press(c, mid)
                _move(c, dst)
                ghost = c._drag_ghost
                assert ghost is not None
                _esc(c)
                assert c._drag_ghost is None and c._dragging_boundary is None
                assert ghost.scene() is None
                assert c.tool_mode is ToolMode.MOVE_BOUNDARY
                # the button is still down: moving and releasing do nothing
                _move(c, mid)
                assert c._drag_ghost is None
                _release(c, mid)
            assert seen == []
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            _esc(c)
            assert c.tool_mode is ToolMode.SELECT
        finally:
            _done(w)

    def test_a_change_of_tool_in_the_middle_cancels(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            mid, dst = _grab(w)
            before = _json(w.project)
            with _errors() as seen:
                _press(c, mid)
                _move(c, dst)
                w._set_tool(ToolMode.SELECT)
                assert c._drag_ghost is None and c._dragging_boundary is None
                _release(c, dst)
            assert seen == []
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
        finally:
            _done(w)

    def test_a_scene_rebuild_in_the_middle_does_not_break_it(self):
        w, c = _ready()
        try:
            mid, dst = _grab(w)
            with _errors() as seen:
                _press(c, mid)
                _move(c, mid)
                c.refresh_scene()
                assert c._drag_ghost is None
                _move(c, dst)
                assert c._drag_ghost is not None
                assert c._drag_ghost.scene() is c.scene()
                _release(c, dst)
            assert seen == []
            assert w.command_stack.history() == (["Edit Boundary"], [])
        finally:
            _done(w)


class TestTheVertexDragIsUnchanged:
    def test_a_vertex_drag_still_leaves_one_step(self):
        from PySide6.QtCore import QPointF
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            w._set_tool(ToolMode.MOVE_VERTEX)
            b = w.project.external_boundary()
            v = b.polyline.vertices[1]
            at = QPointF(v.x, v.y)
            to = QPointF(v.x + 1.0, v.y + 0.5)
            before = _json(w.project)
            with _errors() as seen:
                _press(c, at)
                assert c._dragging_vertex is not None
                _move(c, to)
                _release(c, to)
            assert seen == []
            assert _json(w.project) != before
            assert w.command_stack.history() == (["Edit Boundary"], [])
            w.act_undo()
            assert _json(w.project) == before
        finally:
            _done(w)
