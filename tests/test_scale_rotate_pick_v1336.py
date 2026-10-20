# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.336 (D142, second part; D339) — Scale and Rotate Boundary by clicks,
and EXPAND_SHRINK retired.

``ToolMode.SCALE_BOUNDARY`` and ``ROTATE_BOUNDARY`` sat in the canvas's
one-click tuple, with a hint that promised a pivot click, and nothing
entered them (D142). The reference picks the boundary with the mouse, then
the base point, then asks for the factor or the angle. By decision of the
owner they do that now: the menu enters the mode, the first click picks a
boundary (shown as a dashed ghost), the second is the pivot, and the dialog
opens with that pivot filled in and editable. ``EXPAND_SHRINK`` had nothing
to enter it either, and its drawn variant is ``DRAW_EXPAND_SHRINK``: it is
retired.

D339, found while writing this (reported before it was fixed): ``triggered``
passes ``checked`` (False) to a slot that takes a parameter, and the three
actions took it as ``preselected_idx``. False is not None, so Scale and
Rotate never asked which boundary — they transformed ``boundaries[False]``,
the FIRST boundary, whatever the user meant — and Expand / Shrink never
looked for the External. Measured on 0.1.335 by the cases below.

The geometry is checked against the transforms themselves (rule 1): a
scale by 2 about p sends v to p + 2(v - p); a rotation by 90° about p keeps
|v - p| and adds 90° to its direction.

Every dialog is replaced by a fake that never blocks, so that on the old
tree a case fails instead of hanging the run (offscreen, a modal dialog
waits for ever).
"""
from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QKeyEvent, QMouseEvent, QTransform
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


# ----------------------------------------------------------------------
def _f2():
    import test_f2_rules_v1196 as f2
    return f2


def _ready(project=None):
    """A window on the slope of ``test_f2_rules_v1196``, its canvas shown
    at a known zoom with snapping off."""
    f2 = _f2()
    QApplication.instance() or QApplication([])
    w = f2._window(project or f2._project())
    c = w.canvas
    c.resize(900, 700)
    c.show()
    QApplication.processEvents()
    c.snap_settings.snap = False
    c.setTransform(QTransform().scale(20.0, -20.0))
    c.centerOn(45.0, 27.5)
    return w, c


def _pixel(c, x, y):
    p = c.mapFromScene(QPointF(x, y))
    return p.x(), p.y()


def _scene(c, px, py):
    p = c.mapToScene(QPoint(px, py))
    return p.x(), p.y()


def _press(c, px, py):
    c.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, QPointF(px, py),
        c.mapToGlobal(QPoint(px, py)), Qt.LeftButton, Qt.LeftButton,
        Qt.NoModifier))


def _key(c, key):
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))


@contextlib.contextmanager
def _dialogs(scale=None, rotate=None):
    """``ScaleDialog`` / ``RotateDialog`` replaced by fakes that record the
    pivot they were opened with and answer with the given values; and the
    list of boundaries replaced by a refusal."""
    import ogr_gui.main_window as mw
    from ogr_core.geometry import Vertex
    opened = []

    def fake(kind, answer):
        class _Fake:
            def __init__(self, parent=None, pivot=None):
                opened.append((kind, pivot))
                self._pivot = pivot

            def exec(self):
                return 1 if answer is not None else 0

            def parameters(self):
                values, typed = answer
                pivot = typed if typed is not None else self._pivot
                return (*values, Vertex(*pivot))
        return _Fake

    saved = (mw.ScaleDialog, mw.RotateDialog)
    mw.ScaleDialog = fake("scale", scale)
    mw.RotateDialog = fake("rotate", rotate)
    try:
        yield opened
    finally:
        mw.ScaleDialog, mw.RotateDialog = saved


def _external(w):
    return w.project.external_boundary()


def _pick_and_pivot(w, c, action, edge=(45.0, 20.0), pivot=(30.0, 22.0)):
    """Enter ``action``'s mode from the menu, click the External on its
    edge, then the pivot. Returns the pivot as the canvas computed it."""
    w._actions[action].trigger()
    _press(c, *_pixel(c, *edge))
    px, py = _pixel(c, *pivot)
    _press(c, px, py)
    return _scene(c, px, py)


# ======================================================================
@_requires_qt
class TestTheMenuEntersTheMode:

    def test_scale_enters_its_mode_and_opens_nothing(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        before = [(v.x, v.y) for v in _external(w).polyline.vertices]
        with _dialogs(scale=((2.0, 2.0), None)) as opened:
            w._actions["scale_boundary"].trigger()
        assert c.tool_mode == ToolMode.SCALE_BOUNDARY
        assert opened == []
        # D339 -- on 0.1.335 the menu scaled boundaries[False], the first
        assert [(v.x, v.y) for v in _external(w).polyline.vertices] == before

    def test_rotate_enters_its_mode_and_opens_nothing(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        with _dialogs(rotate=((90.0,), None)) as opened:
            w._actions["rotate_boundary"].trigger()
        assert c.tool_mode == ToolMode.ROTATE_BOUNDARY
        assert opened == []


@_requires_qt
class TestTheBoundaryThenThePivot:

    def test_the_dialog_opens_with_the_clicked_pivot(self):
        w, c = _ready()
        with _dialogs(scale=None) as opened:          # cancelled
            p = _pick_and_pivot(w, c, "scale_boundary")
        assert opened == [("scale", p)], opened

    def test_scale_by_two_about_the_pivot(self):
        w, c = _ready()
        before = [(v.x, v.y) for v in _external(w).polyline.vertices]
        with _dialogs(scale=((2.0, 2.0), None)):
            px, py = _pick_and_pivot(w, c, "scale_boundary")
        after = [(v.x, v.y) for v in _external(w).polyline.vertices]
        assert len(after) == len(before)
        for (x0, y0), (x1, y1) in zip(before, after):
            assert abs(x1 - (px + 2.0 * (x0 - px))) < 1e-9
            assert abs(y1 - (py + 2.0 * (y0 - py))) < 1e-9

    def test_rotate_by_ninety_about_the_pivot(self):
        w, c = _ready()
        before = [(v.x, v.y) for v in _external(w).polyline.vertices]
        with _dialogs(rotate=((90.0,), None)):
            px, py = _pick_and_pivot(w, c, "rotate_boundary")
        after = [(v.x, v.y) for v in _external(w).polyline.vertices]
        for (x0, y0), (x1, y1) in zip(before, after):
            r0, r1 = math.hypot(x0 - px, y0 - py), math.hypot(x1 - px, y1 - py)
            assert abs(r1 - r0) < 1e-9
            turn = math.degrees(math.atan2(y1 - py, x1 - px)
                                - math.atan2(y0 - py, x0 - px)) % 360.0
            assert abs(turn - 90.0) < 1e-7, turn

    def test_a_typed_pivot_wins(self):
        w, c = _ready()
        before = [(v.x, v.y) for v in _external(w).polyline.vertices]
        with _dialogs(scale=((2.0, 2.0), (0.0, 0.0))):
            _pick_and_pivot(w, c, "scale_boundary")
        after = [(v.x, v.y) for v in _external(w).polyline.vertices]
        for (x0, y0), (x1, y1) in zip(before, after):
            assert abs(x1 - 2.0 * x0) < 1e-9 and abs(y1 - 2.0 * y0) < 1e-9

    def test_undo_puts_it_back(self):
        w, c = _ready()
        before = [(v.x, v.y) for v in _external(w).polyline.vertices]
        with _dialogs(scale=((2.0, 2.0), None)):
            _pick_and_pivot(w, c, "scale_boundary")
        w.act_undo()
        assert [(v.x, v.y) for v in _external(w).polyline.vertices] == before

    def test_the_picked_boundary_is_shown_until_the_pivot(self):
        w, c = _ready()
        with _dialogs(scale=None):
            w._actions["scale_boundary"].trigger()
            _press(c, *_pixel(c, 45.0, 20.0))
            assert c._transform_target == w.project.boundaries.index(
                _external(w))
            assert c._transform_ghost is not None
            _press(c, *_pixel(c, 30.0, 22.0))
            assert c._transform_target is None
            assert c._transform_ghost is None


@_requires_qt
class TestAPickedBoundaryIsForgotten:

    def test_by_escape_and_the_tool_stays(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        with _dialogs(scale=None) as opened:
            w._actions["scale_boundary"].trigger()
            _press(c, *_pixel(c, 45.0, 20.0))
            _key(c, Qt.Key_Escape)
            assert c._transform_target is None
            assert c.tool_mode == ToolMode.SCALE_BOUNDARY
            # the next click picks a boundary again: no dialog yet
            _press(c, *_pixel(c, 45.0, 20.0))
        assert opened == []

    def test_by_a_change_of_mode(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        with _dialogs(rotate=None) as opened:
            w._actions["rotate_boundary"].trigger()
            _press(c, *_pixel(c, 45.0, 20.0))
            c.set_tool_mode(ToolMode.SELECT)
            assert c._transform_target is None
            w._actions["rotate_boundary"].trigger()
            _press(c, *_pixel(c, 45.0, 20.0))     # picks; no dialog
        assert opened == []

    def test_a_click_on_nothing_picks_nothing(self):
        w, c = _ready()
        with _dialogs(scale=None) as opened:
            w._actions["scale_boundary"].trigger()
            _press(c, *_pixel(c, 45.0, 60.0))      # far above the slope
            assert c._transform_target is None
            _press(c, *_pixel(c, 45.0, 61.0))
        assert opened == []


@_requires_qt
class TestExpandShrinkFromTheMenu:

    def test_it_targets_the_external_and_not_the_first_boundary(self):
        """D339 -- with the External not first, the menu's ``checked``
        (False) made boundaries[0] the target of the drawn polyline."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from PySide6.QtWidgets import QInputDialog
        from ogr_gui.canvas.tool_mode import ToolMode
        f2 = _f2()
        p = f2._project()
        p.boundaries.insert(0, Boundary(polyline=Polyline(vertices=[
            Vertex(20, 22), Vertex(70, 22)]), btype=BoundaryType.MATERIAL))
        w, c = _ready(p)
        first = staticmethod(lambda _parent, _t, _l, items, *a, **k:
                             (items[0], True))
        with f2._swap(QInputDialog, "getItem", first):
            w._actions["expand_shrink"].trigger()
        assert w._expand_shrink_target_idx == p.boundaries.index(
            p.external_boundary()) == 1
        assert c.tool_mode == ToolMode.DRAW_EXPAND_SHRINK


@_requires_qt
class TestTheModesNowEntered:

    def test_expand_shrink_is_retired_and_its_draw_mode_stays(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        names = {m.name for m in ToolMode}
        assert "EXPAND_SHRINK" not in names
        assert "DRAW_EXPAND_SHRINK" in names

    def test_scale_and_rotate_hints_name_the_pivot(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        for mode in (ToolMode.SCALE_BOUNDARY, ToolMode.ROTATE_BOUNDARY):
            assert "pivot" in mode.status_message, mode
