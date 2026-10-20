# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.335 (D142, first part) — Add Surface (centre and radius) on the canvas.

``ToolMode.ADD_SURFACE_CR`` had its cursor and its hint («Click the centre,
then a point on the circle») since v0.1.3, and nothing entered it: the
action typed the centre and the radius into two dialogs. The reference
draws it on the canvas, the centre and then the radius, dragged or typed. By
decision of the owner it does that now:

* **two clicks make the circle**: its centre is the first click and the
  second lies on it — the radius is ``hypot`` of the two clicks, exactly
  (the reference is the geometry, rule 1);
* the first click adds nothing; a second click on the centre (closer than
  ``_MIN_PERP_PX`` pixels) gives no radius, and is ignored with the centre
  kept, as the three-point flow ignores a repeat;
* **Enter types what was not clicked**: the radius after a centre, or the
  centre and the radius with nothing clicked — the old dialogs, which is
  how the typed path survives;
* **a pending centre is forgotten** by Esc and by a change of mode (D308);
* each circle is ONE undo step, «Add user surface», and a cancelled dialog
  leaves none;
* the label loses its "...": it no longer opens a dialog (D102).

Clicks are real ``mousePressEvent`` calls on the shown canvas, with the zoom
known and snapping off (``test_add_surface_three_points_v1168``'s helpers).
"""
from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _helpers():
    import test_add_surface_three_points_v1168 as h
    return h


def _cr(w):
    w._add_surface_centre_radius()


def _no_dialog(*_a, **_k):
    raise AssertionError("a dialog would open here, and offscreen it would "
                         "block the run")


@contextlib.contextmanager
def _ready():
    """The shown canvas of ``_canvas_ready``, with the two dialogs of the
    typed path replaced by a refusal: on a tree where the action still opens
    them (0.1.334) a case fails instead of blocking the run, and a case that
    expects one replaces it again inside."""
    from PySide6.QtWidgets import QInputDialog
    swap, _answers = _swaps()
    with _helpers()._canvas_ready() as (w, c), \
            swap(w, "_read_points", _no_dialog), \
            swap(QInputDialog, "getDouble", staticmethod(_no_dialog)):
        yield w, c


# ======================================================================
@_requires_qt
class TestTheActionEntersTheMode:

    def test_the_action_enters_it(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        h = _helpers()
        with _ready() as (w, c):
            w._actions["surf_centre_radius"].trigger()
            assert c.tool_mode == ToolMode.ADD_SURFACE_CR
            assert w.project.user_surfaces == []

    def test_its_label_has_no_dots(self):
        h = _helpers()
        act = h._window()._actions["surf_centre_radius"]
        assert act.text() == "Add Surface (centre and radius)"


@_requires_qt
class TestTwoClicksMakeACircle:

    def test_the_centre_and_a_point_on_the_circle(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        h = _helpers()
        with _ready() as (w, c):
            _cr(w)
            h._press(c, 300, 300)
            assert w.project.user_surfaces == []      # the first adds nothing
            h._press(c, 420, 250)
            (cx, cy), (px, py) = h._scene(c, 300, 300), h._scene(c, 420, 250)
            assert len(w.project.user_surfaces) == 1
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y) == (cx, cy)
            assert s.radius == math.hypot(px - cx, py - cy)
            assert c.tool_mode == ToolMode.SELECT
            assert c._draw_points == []

    def test_a_click_on_the_centre_is_ignored_and_the_centre_kept(self):
        h = _helpers()
        with _ready() as (w, c):
            _cr(w)
            h._press(c, 300, 300)
            centre = h._scene(c, 300, 300)
            h._press(c, 301, 300)                 # 1 px: below _MIN_PERP_PX
            assert w.project.user_surfaces == []
            assert c._draw_points == [centre]
            h._press(c, 300, 380)
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y) == centre

    def test_it_is_one_undo_step(self):
        h = _helpers()
        with _ready() as (w, c):
            before = list(w.command_stack.history()[0])
            _cr(w)
            h._press(c, 300, 300)
            h._press(c, 360, 300)
            undo, _redo = w.command_stack.history()
            assert undo[len(before):] == ["Add user surface"], undo
            w.act_undo()
            assert w.project.user_surfaces == []

    def test_the_circle_is_previewed_while_moving(self):
        from PySide6.QtWidgets import QGraphicsEllipseItem
        h = _helpers()
        with _ready() as (w, c):
            _cr(w)
            h._press(c, 300, 300)
            cx, cy = h._scene(c, 300, 300)
            c._update_draw_preview(live_cursor=(cx + 4.0, cy))
            rings = [it for it in c._draw_preview_items
                     if isinstance(it, QGraphicsEllipseItem)
                     and abs(it.rect().width() - 8.0) < 1e-9]
            assert len(rings) == 1


@_requires_qt
class TestEnterTypesWhatWasNotClicked:

    def test_after_the_centre_it_asks_for_the_radius(self):
        from PySide6.QtWidgets import QInputDialog
        h = _helpers()
        swap, answers = _swaps()
        with _ready() as (w, c), \
                swap(QInputDialog, "getDouble", answers((12.5, True))), \
                swap(w, "_read_points", _refuse):
            _cr(w)
            h._press(c, 300, 300)
            h._key(c, Qt.Key_Return)
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y) == h._scene(c, 300, 300)
            assert s.radius == 12.5

    def test_with_nothing_clicked_it_asks_for_both(self):
        from PySide6.QtWidgets import QInputDialog
        h = _helpers()
        swap, answers = _swaps()
        with _ready() as (w, c), \
                swap(QInputDialog, "getDouble", answers((7.0, True))), \
                swap(w, "_read_points", lambda title, n: [(5.0, 6.0)]):
            _cr(w)
            h._key(c, Qt.Key_Enter)
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y, s.radius) == (5.0, 6.0, 7.0)

    def test_a_cancelled_radius_adds_nothing_and_leaves_no_step(self):
        from PySide6.QtWidgets import QInputDialog
        h = _helpers()
        swap, answers = _swaps()
        with _ready() as (w, c), \
                swap(QInputDialog, "getDouble", answers((0.0, False))):
            before = list(w.command_stack.history()[0])
            _cr(w)
            h._press(c, 300, 300)
            h._key(c, Qt.Key_Return)
            assert w.project.user_surfaces == []
            assert list(w.command_stack.history()[0]) == before


@_requires_qt
class TestAPendingCentreIsForgotten:

    def test_by_escape(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        h = _helpers()
        with _ready() as (w, c):
            _cr(w)
            h._press(c, 300, 300)
            h._key(c, Qt.Key_Escape)
            assert c._draw_points == []
            assert c.tool_mode == ToolMode.ADD_SURFACE_CR   # the tool stays
            h._press(c, 200, 200)                 # a NEW centre
            h._press(c, 260, 200)
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y) == h._scene(c, 200, 200)

    def test_by_a_change_of_mode(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        h = _helpers()
        with _ready() as (w, c):
            _cr(w)
            h._press(c, 300, 300)
            c.set_tool_mode(ToolMode.MEASURE)
            _cr(w)
            assert c._draw_points == []
            h._press(c, 200, 200)
            h._press(c, 200, 260)
            s = w.project.user_surfaces[0]
            assert (s.centre_x, s.centre_y) == h._scene(c, 200, 200)


# ----------------------------------------------------------------------
def _refuse(*_a, **_k):
    raise AssertionError("the centre was clicked: nothing to type")


def _swaps():
    import test_undo_settings_annotations_v1305 as u
    return u._swap, u._answers
