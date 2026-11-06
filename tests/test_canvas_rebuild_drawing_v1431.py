# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.431 (D398) — a scene rebuilt in the middle of a drawing leaves the
drawing tools working, and what was picked on the model is not trusted
after the model changed.

The invariant: the canvas clears and redraws its scene on every project
event (an agent's edit, an undo) and on Display Options. When that happens
while the user is drawing, the drawing's points stay, its preview is drawn
again, the next vertex and the finish deliver every point clicked, and a
change of tool does not raise. A Zoom Window drag in progress is cancelled,
as a change of tool cancels it. In Interpret, the thrust line comes back
with the result, and the query label is forgotten.

Until this version the preview items' Python wrappers outlived the scene:
the next move, click, finish or change of tool touched a dead one and raised
RuntimeError ("Internal C++ object already deleted"). The list was never
emptied, because emptying it raised first, so every drawing tool of the
session raised from then on and the drawing was lost. Measured on 0.1.430
with a bare canvas: after one rebuild mid-drawing, the first clicks of the
NEXT drawing raised too. The same held for the rubber band of Zoom Window
and, in Interpret, for the thrust line, which vanished with the scene and
raised on its next toggle.

What the fix makes survive a redraw must not survive a change of the model
it was picked on, and the first version of this fix let it (the review of
0.1.431):

* the toe of Change Slope Angle is an index into the External boundary: an
  edit between the two clicks renumbered it, and the crest click edited
  another face or raised IndexError. It is checked at the crest click;
* a new project (File > New, Open, an agent's project_new) carried a
  drawing in progress into it. It drops whatever was half done;
* Interpret drew the thrust line of a result alone over an edited model,
  where the result itself is not drawn (D323). It comes back with the
  result only.

Not a number: the reference is the clicks themselves. The test puts them
through the canvas's own pixel mapping (``mapFromScene`` → ``mapToScene``)
and compares what is delivered with what was clicked, to a tolerance
relative to the model's size.

Cost: measured below the tests, in the changelog of this version.
"""
from __future__ import annotations

import contextlib
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402


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


def _click(c, x, y):
    from PySide6.QtCore import QPointF
    from test_move_boundary_drag_v1312 import _press, _release
    pt = QPointF(x, y)
    _press(c, pt)
    _release(c, pt)


def _as_seen(c, x, y):
    """A scene point as the canvas reads it back from a mouse event."""
    from PySide6.QtCore import QPointF
    p = c.mapToScene(c.mapFromScene(QPointF(x, y)))
    return (p.x(), p.y())


def _same_points(c, got, clicked):
    """The points delivered are the clicks as the canvas reads them, to a
    tolerance relative to the model's size, never ``==`` on doubles."""
    size = max(c.sceneRect().width(), c.sceneRect().height(), 1.0)
    want = [_as_seen(c, x, y) for x, y in clicked]
    return len(got) == len(want) and all(
        abs(a - b) <= 1e-9 * size
        for p, q in zip(got, want) for a, b in zip(p, q))


_CANVASES: list = []


def _canvas():
    """A canvas alone, one per test: no window, so no dialog when a drawing
    is finished, and a test that breaks it breaks no other. Shown and
    900 x 600 with no snapping: hidden, it is 98 x 28 px and a model unit
    is under a pixel (test_add_surface_three_points_v1168)."""
    from examples.quick_slope import build_demo_slope
    from ogr_gui.canvas.canvas_view import CanvasView
    QApplication.instance() or QApplication([])
    p = build_demo_slope()
    p.settings.search.surface_type = "non_circular"
    c = CanvasView(p)
    _CANVASES.append(c)
    c.resize(900, 600)
    c.show()
    c.snap_settings.snap = False
    c.refresh_scene()
    c.zoom_all()
    assert c.viewport().width() >= 800, c.viewport().size()
    delivered: list = []
    c.boundary_drawn.connect(lambda obj: delivered.append(obj))
    c.user_surface_drawn.connect(lambda obj: delivered.append(obj))
    return c, delivered


_PTS = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]


def _draw_through_a_rebuild(c, mode, rebuild):
    """Two vertices, the scene rebuilt, the other two, and finish."""
    from PySide6.QtCore import QPointF
    from test_move_boundary_drag_v1312 import _move
    c.set_tool_mode(mode)
    for x, y in _PTS[:2]:
        _click(c, x, y)
    rebuild()
    _move(c, QPointF(28.0, 16.0))
    for x, y in _PTS[2:]:
        _click(c, x, y)
    c._finish_drawing()


# ======================================================================
class TestTheCanvas:

    def test_every_drawing_tool_delivers_what_was_clicked(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        c, delivered = _canvas()
        with _errors() as seen:
            for mode in (ToolMode.DRAW_EXTERNAL, ToolMode.DRAW_MATERIAL,
                         ToolMode.DRAW_USER_SURFACE):
                delivered.clear()
                _draw_through_a_rebuild(c, mode, c.refresh_scene)
                # 0.1.430: RuntimeError on the move, and nothing delivered;
                # and from the second mode on, on its first clicks too
                assert len(delivered) == 1, (mode, delivered)
                got = [(v.x, v.y) for v in delivered[0].vertices]
                assert _same_points(c, got, _PTS), (mode, got)
                c.set_tool_mode(ToolMode.SELECT)
        assert seen == [], seen

    def test_the_preview_is_drawn_again_on_the_new_scene(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        c.set_tool_mode(ToolMode.DRAW_MATERIAL)
        for x, y in _PTS[:2]:
            _click(c, x, y)
        c.refresh_scene()
        assert len(c._draw_points) == 2
        assert c._draw_preview_items, "no preview after the rebuild"
        assert all(it.scene() is c.scene() for it in c._draw_preview_items)
        c.set_tool_mode(ToolMode.SELECT)
        assert c._draw_points == [] and c._draw_preview_items == []

    def test_a_zoom_window_drag_is_cancelled(self):
        from PySide6.QtCore import QPointF
        from test_move_boundary_drag_v1312 import _move, _press, _release

        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        with _errors() as seen:
            c.set_tool_mode(ToolMode.ZOOM_WINDOW)
            before = c.transform()
            _press(c, QPointF(10.0, 10.0))
            _move(c, QPointF(20.0, 20.0))
            assert c._zw_rubber is not None     # the drag did start
            c.refresh_scene()
            # 0.1.430: RuntimeError on these, on the dead rubber band
            _move(c, QPointF(25.0, 22.0))
            _release(c, QPointF(30.0, 24.0))
            assert c._zw_rubber is None
            assert c.transform() == before      # no zoom: it was cancelled
            c.set_tool_mode(ToolMode.SELECT)
        assert seen == [], seen


class TestWhatWasPickedOnTheModel:
    """A redraw keeps a pick; a change of the model it was made on does
    not leave it trusted."""

    def _toe_and_crest(self, c):
        ring = c.project.external_boundary().polyline.vertices
        return (ring[1].x, ring[1].y), (ring[2].x, ring[2].y), 1, 2

    def test_the_toe_is_used_while_the_ring_is_the_same(self):
        """The control: a redraw between the two clicks changes nothing."""
        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        picked: list = []
        c.slope_vertices_picked.connect(lambda a, b: picked.append((a, b)))
        toe, crest, ti, ci = self._toe_and_crest(c)
        c.set_tool_mode(ToolMode.CHANGE_SLOPE_ANGLE)
        _click(c, *toe)
        c.refresh_scene()
        _click(c, *crest)
        assert picked == [(ti, ci)], picked
        c.set_tool_mode(ToolMode.SELECT)

    def test_a_renumbered_ring_asks_for_the_toe_again(self):
        """An edit between the two clicks puts another vertex at the toe's
        index; 0.1.430 raised there, and the first version of this fix
        handed the slot the old index, another face."""
        from ogr_core.geometry import Vertex
        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        picked: list = []
        said: list = []
        c.slope_vertices_picked.connect(lambda a, b: picked.append((a, b)))
        c.status_message.connect(said.append)
        toe, crest, _ti, _ci = self._toe_and_crest(c)
        c.set_tool_mode(ToolMode.CHANGE_SLOPE_ANGLE)
        _click(c, *toe)
        ring = c.project.external_boundary().polyline.vertices
        ring.insert(0, Vertex(ring[0].x - 1.0, ring[0].y))   # an edit
        c.refresh_scene()                       # what the edit redraws
        _click(c, *crest)
        assert picked == [], picked
        assert c._draw_points == [] and c._slope_toe_idx is None
        assert any("click the toe vertex again" in s for s in said), said
        c.set_tool_mode(ToolMode.SELECT)

    def test_a_crest_at_the_toes_old_index_asks_for_the_toe_too(self):
        """An undo that takes a vertex out before the toe puts the crest at
        the toe's old index: the click was ignored without a word, because
        the check came after the repeat of the toe (the review of 0.1.431)."""
        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        picked: list = []
        said: list = []
        c.slope_vertices_picked.connect(lambda a, b: picked.append((a, b)))
        c.status_message.connect(said.append)
        toe, crest, ti, _ci = self._toe_and_crest(c)
        c.set_tool_mode(ToolMode.CHANGE_SLOPE_ANGLE)
        _click(c, *toe)
        ring = c.project.external_boundary().polyline.vertices
        del ring[0]                             # the crest is at index ti now
        assert (ring[ti].x, ring[ti].y) == crest
        c.refresh_scene()
        _click(c, *crest)
        assert picked == [], picked
        assert c._slope_toe_idx is None
        assert any("click the toe vertex again" in s for s in said), said
        c.set_tool_mode(ToolMode.SELECT)

    def test_a_new_project_drops_the_drawing(self):
        from examples.quick_slope import build_demo_slope
        from ogr_gui.canvas.tool_mode import ToolMode
        c, delivered = _canvas()
        c.set_tool_mode(ToolMode.DRAW_MATERIAL)
        for x, y in _PTS[:2]:
            _click(c, x, y)
        other = build_demo_slope()
        c.set_project(other)                   # File > New, Open, an agent
        # the first version of this fix kept these two points, now on
        # another project
        assert c._draw_points == [] and c._draw_preview_items == []
        for x, y in _PTS[2:]:
            _click(c, x, y)
        c._finish_drawing()
        assert len(delivered) == 1
        assert _same_points(c, [(v.x, v.y) for v in delivered[0].vertices],
                            _PTS[2:])
        c.set_tool_mode(ToolMode.SELECT)

    def test_the_same_project_handed_again_keeps_it(self):
        """A DXF import and Convert to Boundary hand the canvas its own
        project again: that is a redraw, and the drawing stays."""
        from ogr_gui.canvas.tool_mode import ToolMode
        c, delivered = _canvas()
        c.set_tool_mode(ToolMode.DRAW_MATERIAL)
        for x, y in _PTS[:2]:
            _click(c, x, y)
        c.set_project(c.project)
        assert len(c._draw_points) == 2
        for x, y in _PTS[2:]:
            _click(c, x, y)
        c._finish_drawing()
        assert len(delivered) == 1
        assert _same_points(c, [(v.x, v.y) for v in delivered[0].vertices],
                            _PTS)
        c.set_tool_mode(ToolMode.SELECT)


# ======================================================================
class TestTheWindowWhileAnAgentEdits:
    """The case of the ficha: an agent's edit lands while the user draws."""

    def test_the_users_polyline_is_stored_whole(self):
        from ogr_gui.agent_bridge import WindowHost
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        w = MainWindow()
        try:
            w.act_load_demo()
            w.project.settings.search.surface_type = "non_circular"
            w.refresh_action_availability()
            # the window shown: a canvas inside a hidden window keeps its
            # 98 x 28 px whatever it is resized to (the review of 0.1.431)
            w.resize(1200, 800)
            w.show()
            c = w.canvas
            c.snap_settings.snap = False
            c.zoom_all()
            assert c.viewport().width() >= 600, c.viewport().size()
            with _errors() as seen:
                _draw_through_a_rebuild(c, ToolMode.DRAW_USER_SURFACE,
                                        WindowHost(w).after_edit)
            assert seen == [], seen
            assert len(w.project.user_polylines) == 1, \
                w.ogr_status.currentMessage()
            got = w.project.user_polylines[0].points
            assert len(got) == 4, got
            # the ends may be brought onto the ground; the vertices between
            # them are the clicks
            assert _same_points(c, [tuple(p) for p in got[1:3]], _PTS[1:3]), \
                got
            assert c.tool_mode == ToolMode.SELECT
        finally:
            w.project.is_dirty = False
            w.close()


# ======================================================================
_INTERPRET: dict = {}


class TestInterpret:

    def _window(self):
        if "window" not in _INTERPRET:
            from test_design_factor_report_gui_v1165 import _slope

            from ogr_gui.interpret_window import InterpretWindow
            from ogr_slip2d.analysis_runner import run_analysis
            QApplication.instance() or QApplication([])
            p = _slope()
            result = run_analysis(p, ["spencer"]).results["spencer"]
            iw = InterpretWindow(p, {"spencer": result}, None)
            iw.resize(900, 600)
            _INTERPRET["window"] = iw
        return _INTERPRET["window"]

    def test_the_thrust_line_comes_back_with_the_result(self):
        """Contour Options, the water layers and Hide Geometry rebuild the
        scene and then draw the result again: the thrust line with it."""
        iw = self._window()
        with _errors() as seen:
            iw._toggle_thrust_line(True)
            try:
                assert iw._thrust_items, "no thrust line to begin with"
                iw.canvas.refresh_scene()
                iw._refresh_canvas_with_highlights()
                # 0.1.430: gone with the scene, and the toggle below raised
                assert iw._thrust_items
                assert all(it.scene() is iw.canvas.scene()
                           for it in iw._thrust_items)
            finally:
                iw._toggle_thrust_line(False)
            assert iw._thrust_items == []
        assert seen == [], seen

    def test_an_edit_does_not_draw_it_alone(self):
        """An edit of the model rebuilds the scene without the result
        (D323): its thrust line stays off with it."""
        iw = self._window()
        with _errors() as seen:
            iw._toggle_thrust_line(True)
            try:
                assert iw._thrust_items
                iw.canvas.refresh_scene()       # what an edit does
                assert iw._thrust_items == []
            finally:
                iw._toggle_thrust_line(False)
        assert seen == [], seen

    def test_the_query_label_is_forgotten(self):
        iw = self._window()
        with _errors() as seen:
            iw._show_query_label(20.0, 20.0, "F = 1.234")
            assert iw._query_label_item is not None
            iw.canvas.refresh_scene()
            iw._clear_query_label()
            assert iw._query_label_item is None
        assert seen == [], seen


# ======================================================================
class TestTheRuleOfABoundaryAtTheEnd:
    """By the owner's decision (2026-11-06): a drawing now survives the edit
    that adds the one boundary of its kind the model may hold, so the rule
    is asked again when it ends (``boundary_refusal``)."""

    def test_a_second_water_table_is_not_added(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        w = MainWindow()
        try:
            w.act_load_demo()
            # what an added water surface opens next is a question the user
            # answers; without a display it would block (0.1.430 got there,
            # adding the second water table). Replaced on this window only.
            for name in ("_maybe_prompt_assign_water_surface",
                         "_maybe_prompt_weak_layer_material",
                         "_maybe_open_block_polyline_options"):
                setattr(w, name, lambda boundary: None)

            def tables():
                return [b for b in w.project.boundaries
                        if b.btype == BoundaryType.WATER_TABLE]
            assert len(tables()) == 1        # the demo slope has one
            w._on_boundary_drawn(Boundary(
                polyline=Polyline([Vertex(0, 10), Vertex(50, 10)]),
                btype=BoundaryType.WATER_TABLE))
            # 0.1.430 added it: two water tables, which rules.py forbids
            assert len(tables()) == 1
            said = w.ogr_status.currentMessage()
            assert "Only one Water Table is allowed." in said, said
            assert "The boundary was not added." in said, said
            # the control: a material boundary has no such rule
            n = len(w.project.boundaries)
            w._on_boundary_drawn(Boundary(
                polyline=Polyline([Vertex(0, 12), Vertex(50, 12)]),
                btype=BoundaryType.MATERIAL))
            assert len(w.project.boundaries) == n + 1
        finally:
            w.project.is_dirty = False
            w.close()


class TestScaleAndRotate:
    """The same check as the toe, for the boundary Scale / Rotate picked,
    by the owner's decision (2026-11-06); and its ghost after a redraw."""

    def _pick_the_external(self, c):
        from ogr_gui.canvas.tool_mode import ToolMode
        c.set_tool_mode(ToolMode.SCALE_BOUNDARY)
        _click(c, 25.0, 0.0)                 # the base of the External
        assert c._transform_target == 0, c._transform_target

    def test_the_ghost_comes_back_and_the_pivot_is_taken(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        c, _delivered = _canvas()
        picked: list = []
        c.boundary_base_picked.connect(lambda i, x, y: picked.append(i))
        self._pick_the_external(c)
        c.refresh_scene()
        # 0.1.430: the ghost died with the scene and nothing drew it again
        assert c._transform_ghost is not None
        assert c._transform_ghost.scene() is c.scene()
        _click(c, 10.0, 10.0)                # the pivot
        assert picked == [0], picked
        c.set_tool_mode(ToolMode.SELECT)

    def test_renumbered_boundaries_ask_for_the_boundary_again(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        for redraw in (True, False):
            c, _delivered = _canvas()
            picked: list = []
            said: list = []
            c.boundary_base_picked.connect(lambda i, x, y: picked.append(i))
            c.status_message.connect(said.append)
            self._pick_the_external(c)
            bs = c.project.boundaries
            bs.insert(0, bs.pop(1))          # an edit: the water table first
            if redraw:
                c.refresh_scene()
            _click(c, 10.0, 10.0)            # meant as the pivot
            # 0.1.430 scaled boundaries[0], the water table now
            assert picked == [], (redraw, picked)
            assert any("click it again, then the pivot" in s for s in said), \
                (redraw, said)
            c.set_tool_mode(ToolMode.SELECT)


class TestShowSlices:
    """By the owner's decision (2026-11-06), the slice lines too."""

    def _lines(self, iw):
        return [it for it in iw.canvas.scene().items()
                if getattr(it, "_is_slice_line", False)]

    def test_they_come_back_and_hide_with_the_geometry(self):
        iw = TestInterpret()._window()
        with _errors() as seen:
            iw._toggle_slices(True)
            try:
                assert self._lines(iw), "no slice lines to begin with"
                iw.canvas.refresh_scene()
                iw._refresh_canvas_with_highlights()
                # 0.1.430: gone with the scene, the entry still checked
                assert self._lines(iw)
                iw._set_geometry_hidden(True)    # the slice alone
                assert self._lines(iw) == []
                iw._set_geometry_hidden(False)   # and all of it back
                assert self._lines(iw)
            finally:
                iw._toggle_slices(False)
            assert self._lines(iw) == []
        assert seen == [], seen
