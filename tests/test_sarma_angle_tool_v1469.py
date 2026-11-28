# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.469 (D357) — the face angles of Sarma's method by the mouse, and the
context menu of a user surface's vertex.

WHAT THIS VERSION ADDS

Until v0.1.468 the face angle at a vertex of a non-circular user surface
was given only in the table of Surfaces -> Sarma Data per Vertex...; the
canvas picked no vertex of a user surface and had no menu for one, and the
given angles were drawn a fifth of the surface's width long, which is not
the face the method cuts.

* Surfaces -> Set Sarma Face Angles: a vertex, then the direction of its
  face (a live ray, up to where the method would cut it) or Enter to type
  the angle from 0 to 360°; Remove Sarma Face Angles; each edit one undo
  step, the vertex's c and φ kept.
* The owner's decisions (2026-11-17): the tool stores θ in (0°, 180°), the
  half of the line that rises (300° is stored as 120°, a click below the
  vertex gives the face that rises); a point that is a vertex of a boundary
  and of a user surface opens one menu with both parts; the rays, live and
  stored, reach the ground by the method's own rule (``vertex_face``).

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The published problem 4** (Hoek 1987; the bank's transcription of
   the verification manual's problem 4, saturated, 2 wedges): its interface
   rises from the kink (108, 6.4) to the ground at x = 82.85 on the slope
   y = 76.5·x/111.4. Typing its angle with the tool gives through the door
   the factor of the bank's tool (``cunas_sarma.py``) and the published
   0.434 at ±1 %; a click on the published top of the interface stores the
   angle of the clicked point to a tenth of a degree, within 0.1° of the
   published one, and the factor at ±1 %; removing it gives back the
   policy's factor (the action moves the number both ways: rule 7).
2. **The face the canvas draws is the one the method cuts**: the top of
   ``vertex_face`` at the kink is the closed-form point of that line and the
   top of the face ``build_wedges`` cuts, to the bit; a ray that leaves
   through a side of the model has none.
3. **The rule of the edit** (``with_vertex_angle``): the c and φ of the
   vertex stay; a horizontal face and a point that is no interior vertex
   are refused with their reason; other rows are left as they are.
4. **The tool**: the pick is in pixels (two zooms); θ is the rising half,
   to a tenth of a degree; 300° typed is 120° stored, 0/180/360 refused in
   the user's language and nothing written; one undo step per edit, named
   in Spanish; a vertex that changed between the clicks is asked again;
   Esc and the right button let the vertex go, then leave.
5. **The menu**: at problem 4's kink, the contact's part and the surface's
   part; at a vertex of the surface alone, its part; each action does what
   it says; with a circular run, its actions are grey with the reason.

The review of v0.1.469 (an agent) added, with the owner's decisions: a
vertex two surfaces share has a part of the menu for each, and the tool
takes the first and names it; the Selection Filter's «Slip surfaces» is
read; Interpret's canvas offers none of it; a project replaced, a change of
tool, a redraw and an Enter forget a vertex that is no longer there; loads
and supports keep their menus; a closed gate writes nothing; a refused
datum is said as such; the typed value is the box's four decimals and its
start the stored face; a face that does not leave the ground is said after
a typing; an id that is no string still works.

The window is shown, with snapping off and a known scale (the pattern of
``test_annotation_clicks_v1416``): an unshown canvas is 98 x 28 px.
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: Problem 4's interface (``W63._THETA4``): from the kink to the ground at
#: x = 82.85, on the slope y = 76.5·x / 111.4.
_KINK = W63._KINK4
_TOP = (82.85, 76.5 * 82.85 / 111.4)
#: A vertex of a user surface that is no boundary vertex: (60, 20) lies in
#: the spoil, 21 m below the slope.
_OTHER = ((0.0, 0.0), (60.0, 20.0), (128.0, 67.6737))
#: A second surface through the kink, ending on the slope at x = 125.
_SECOND = ((0.0, 0.0), _KINK,
           (125.0, 76.5 - (125.0 - 111.4) * (76.5 - 13.6815)
            / (229.545 - 111.4)))
_SCALE = 10.0

_CACHE: dict = {}
_WINDOW: list = []


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _surface(points=W63._SURFACE4, data=None, id=None):
    from ogr_core.geometry.user_polyline import UserPolylineSurface
    return UserPolylineSurface.from_points(list(points), vertex_data=data,
                                           id=id)


def _factor(project, up):
    """Sarma's factor of the stored surface ``up``, through the door."""
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    from ogr_slip2d.surface import slip_surface_of
    return evaluate_surfaces(project, slip_surface_of(up),
                             ["sarma"]).results["sarma"].fos


def _window(scale=_SCALE):
    """The one window of the file: problem 4 saturated (2 wedges, the
    root's tolerance at 1e-12), a non-circular run, shown, at ``scale``
    px per metre around the interface, snapping off; its published surface
    stored without data."""
    from PySide6.QtGui import QTransform
    from ogr_core.project.settings import SurfaceType
    from ogr_gui.canvas.tool_mode import ToolMode
    if not _WINDOW:
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        _app()
        set_language("en")
        w = MainWindow()
        p, _s, _a = W63._problem4(True)
        p.settings.sarma.num_slices = 2
        p.settings.sarma.tolerance = 1e-12
        w._attach_project(p)
        w.resize(1200, 900)
        w.show()
        _app().processEvents()
        s = w.canvas.snap_settings
        s.snap = s.ortho = s.osnap = False
        _WINDOW.append(w)
    w = _WINDOW[0]
    c = w.canvas
    c.set_tool_mode(ToolMode.SELECT)
    c.selection_filter.surfaces = True
    w.project.supports = []
    w.project.settings.search.surface_type = SurfaceType.NON_CIRCULAR.value
    w.project.user_polylines = [_surface()]
    w.command_stack.clear()
    w.refresh_action_availability()
    c.refresh_scene()
    c.setTransform(QTransform().scale(scale, -scale))
    c.centerOn(95.0, 31.0)
    _app().processEvents()
    return w


def _pixel(c, x, y):
    from PySide6.QtCore import QPointF
    p = c.mapFromScene(QPointF(x, y))
    return p.x(), p.y()


def _scene(c, px, py):
    """What the canvas reads for that pixel."""
    from PySide6.QtCore import QPoint
    q = c.mapToScene(QPoint(px, py))
    return q.x(), q.y()


def _press(c, px, py, button=None):
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    button = Qt.LeftButton if button is None else button
    c.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, QPointF(px, py),
        c.mapToGlobal(QPoint(px, py)), button, button, Qt.NoModifier))


def _move(c, px, py):
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    c.mouseMoveEvent(QMouseEvent(
        QEvent.MouseMove, QPointF(px, py), c.mapToGlobal(QPoint(px, py)),
        Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _key(c, key):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))


def _click_at(c, x, y, button=None):
    _press(c, *_pixel(c, x, y), button=button)


@contextlib.contextmanager
def _messages(c):
    got: list = []
    c.status_message.connect(got.append)
    try:
        yield got
    finally:
        try:
            c.status_message.disconnect(got.append)
        except (TypeError, RuntimeError):  # pragma: no cover
            pass


@contextlib.contextmanager
def _typed(value):
    """``QInputDialog.getDouble`` answering ``value`` (None: cancelled),
    recording every question asked."""
    from PySide6.QtWidgets import QInputDialog
    asked = []
    raw = QInputDialog.__dict__.get("getDouble")

    def fake(_parent, title, label, start, low, high, decimals, *a, **k):
        asked.append((title, label, start, low, high, decimals))
        return (0.0, False) if value is None else (value, True)
    QInputDialog.getDouble = staticmethod(fake)
    try:
        yield asked
    finally:
        if raw is None:
            del QInputDialog.getDouble
        else:
            QInputDialog.getDouble = raw


def _angle(w, up=None):
    up = up or w.project.user_polylines[0]
    datum = up.vertex_data.get(_KINK) or {}
    return datum.get("angle")


def _menu(open_menu):
    """``[(text, enabled)]`` of the popup menu ``open_menu()`` shows: a
    timer inside the menu's own loop reads it and closes it
    (``test_labels_spanish_v1321._menu_texts``)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMenu
    seen = []
    tries = [0]

    def grab():
        tries[0] += 1
        menus = [m for m in _app().topLevelWidgets()
                 if isinstance(m, QMenu) and m.isVisible()]
        if not menus and tries[0] < 200:
            QTimer.singleShot(10, grab)
            return
        for m in menus:
            seen.extend((a.text(), a.isEnabled()) for a in m.actions()
                        if a.text())
            m.close()

    QTimer.singleShot(0, grab)
    open_menu()
    return seen


# ======================================================================
class TestTheFaceRule:

    def test_the_face_drawn_is_the_face_cut(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.sarma.wedges import vertex_face
        from ogr_slip2d.surface import attach_vertex_data
        p, s, _a = W63._problem4(True)
        theta, top = vertex_face(p, *_KINK, W63._THETA4)
        assert abs(theta - W63._THETA4) <= 1e-12
        assert math.hypot(top[0] - _TOP[0], top[1] - _TOP[1]) <= 1e-6, top
        # the face build_wedges cuts there, to the bit
        p.settings.sarma.num_slices = 2
        attach_vertex_data(s, {_KINK: {"angle": W63._THETA4, "c": None,
                                       "phi": None}})
        r = evaluate_surfaces(p, s, ["sarma"]).results["sarma"]
        face = r.slices.faces[1]
        assert (face.x_top, face.y_top) == top
        # the same line, given the other way or past 360
        for other in (W63._THETA4 + 180.0, W63._THETA4 - 180.0,
                      W63._THETA4 + 360.0):
            t2, top2 = vertex_face(p, *_KINK, other)
            assert abs(t2 - theta) <= 1e-9 and top2 == top, other
        # no face, and a face that leaves through the model's right side
        assert vertex_face(p, *_KINK, 180.0) == (None, None)
        t1, none = vertex_face(p, *_KINK, 1.0)
        assert t1 == 1.0 and none is None

    def test_the_pointer_gives_the_rising_half_to_a_tenth(self):
        from ogr_slip2d.sarma.angles import upward_degrees
        dx, dy = _TOP[0] - _KINK[0], _TOP[1] - _KINK[1]
        up = upward_degrees(dx, dy)
        assert up == round(math.degrees(math.atan2(dy, dx)), 1) == 116.5
        assert upward_degrees(-dx, -dy) == up       # below the vertex
        assert upward_degrees(1.0, 0.0) is None
        assert upward_degrees(1.0, 1e-5) is None    # 0.0006°, rounds to 0
        assert upward_degrees(0.0, 0.0) is None
        assert upward_degrees(0.0, -3.0) == 90.0


class TestTheEditRule:

    def test_the_angle_alone_changes(self):
        from ogr_core.geometry.user_polyline import (checked_points,
                                                     with_vertex_angle)
        pts = checked_points(list(_OTHER))
        data = {(60.0, 20.0): {"angle": None, "c": 5.0, "phi": 20.0}}
        got = with_vertex_angle(pts, data, (60.0, 20.0), 70.0)
        assert got == {(60.0, 20.0): {"angle": 70.0, "c": 5.0, "phi": 20.0}}
        assert with_vertex_angle(pts, got, (60.0, 20.0), None) == data
        assert with_vertex_angle(
            pts, {(60.0, 20.0): {"angle": 70.0, "c": None, "phi": None}},
            (60.0, 20.0), None) == {}
        # matched as the rule matches: a billionth of the width away
        near = (60.0 + 1e-8, 20.0)
        assert list(with_vertex_angle(pts, {}, near, 80.0)) == [(60.0, 20.0)]
        # two keys of one vertex (a hand-edited file): the first is its row
        two = {(60.0, 20.0): {"angle": None, "c": 5.0, "phi": 20.0},
               near: {"angle": None, "c": 9.0, "phi": 30.0}}
        assert with_vertex_angle(pts, two, (60.0, 20.0), 70.0) == {
            (60.0, 20.0): {"angle": 70.0, "c": 5.0, "phi": 20.0}}

    def test_what_is_refused_and_what_is_left(self):
        from ogr_core.geometry.user_polyline import (NotASurface,
                                                     checked_points,
                                                     with_vertex_angle)
        pts = checked_points(list(W63._SURFACE4))
        for vertex, angle, reason in ((_KINK, 0.0, "angle"),
                                      (_KINK, 180.0, "angle"),
                                      ((0.0, 0.0), 90.0, "not_a_vertex")):
            try:
                with_vertex_angle(pts, {}, vertex, angle)
            except NotASurface as exc:
                assert exc.reason == reason, (vertex, angle, exc.reason)
            else:
                raise AssertionError((vertex, angle))
        # another row of a hand-edited file stays exactly as it was
        bad = {(1.0, 2.0): {"angle": "abc", "c": None, "phi": None}}
        got = with_vertex_angle(pts, bad, _KINK, 100.0)
        assert got[(1.0, 2.0)] is bad[(1.0, 2.0)]
        assert got[_KINK]["angle"] == 100.0


# ======================================================================
class TestTheTool:

    def test_typing_the_published_angle_gives_the_published_factor(self):
        w = _window()
        c = w.canvas
        w._actions["surf_polyline_sarma_set"].trigger()
        from ogr_gui.canvas.tool_mode import ToolMode
        assert c.tool_mode == ToolMode.SET_SARMA_ANGLE
        _click_at(c, *_KINK)
        with _typed(W63._THETA4) as asked:
            _key(c, _enter())
        assert len(asked) == 1 and asked[0][3:5] == (0.0, 360.0), asked
        # to the box's four decimals, which is what it can hand back
        assert _angle(w) == round(W63._THETA4, 4) == 116.4768
        F = _factor(w.project, w.project.user_polylines[0])
        assert abs(F / W63._TOOL4[True] - 1.0) <= 1e-5, F
        assert abs(F / W63._PUBLISHED4[True] - 1.0) <= 0.01, F
        # still in the mode, for the next vertex
        assert c.tool_mode == ToolMode.SET_SARMA_ANGLE

    def test_a_click_on_the_published_top(self):
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        px = _pixel(c, *_TOP)
        sx, sy = _scene(c, *px)
        _press(c, *px)
        stored = _angle(w)
        from ogr_slip2d.sarma.angles import upward_degrees
        # the angle of the point clicked, from the vertex picked
        assert stored == upward_degrees(sx - _KINK[0], sy - _KINK[1]), stored
        assert abs(stored - W63._THETA4) <= 0.1, stored
        F = _factor(w.project, w.project.user_polylines[0])
        assert abs(F / W63._PUBLISHED4[True] - 1.0) <= 0.01, F

    def test_removing_it_gives_back_the_policys_factor(self):
        w = _window()
        c = w.canvas
        up = w.project.user_polylines[0]
        policy = _factor(w.project, up)
        w._write_sarma_angle(up.id, *_KINK, W63._THETA4)
        given = _factor(w.project, w.project.user_polylines[0])
        w._actions["surf_polyline_sarma_remove"].trigger()
        _click_at(c, *_KINK)
        assert _angle(w) is None and not w.project.user_polylines[0] \
            .vertex_data
        back = _factor(w.project, w.project.user_polylines[0])
        assert back == policy and abs(given / policy - 1.0) > 0.05, (
            policy, given)
        # a vertex with no angle says so and writes nothing
        with _messages(c) as said:
            _click_at(c, *_KINK)
        assert said == ["That vertex has no face angle to remove."], said
        assert w.command_stack.history()[0] == [
            "Set Sarma face angle", "Remove Sarma face angle"]

    def test_a_click_below_the_vertex_stores_the_rising_face(self):
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        below = (2 * _KINK[0] - _TOP[0], 2 * _KINK[1] - _TOP[1])
        _click_at(c, *below)
        assert 0.0 < _angle(w) < 180.0
        assert abs(_angle(w) - W63._THETA4) <= 0.1

    def test_300_is_stored_as_120_and_a_horizontal_face_is_refused(self):
        w = _window()
        c = w.canvas
        up = w.project.user_polylines[0]
        with _typed(300.0), _status(w) as said:
            w._on_sarma_angle_typed(up.id, *_KINK)
        assert _angle(w) == 120.0
        assert said[-1] == "300° is the same face as 120°, which is stored."
        for value in (0.0, 180.0, 360.0):
            w.command_stack.clear()
            before = dict(w.project.user_polylines[0].vertex_data)
            with _typed(value), _status(w) as said:
                w._on_sarma_angle_typed(up.id, *_KINK)
            assert w.project.user_polylines[0].vertex_data == before
            assert w.command_stack.history() == ([], [])
            assert said == ["The angle at (108, 6.4) must be a finite number "
                            "and not horizontal."], said

    def test_the_refusal_is_said_in_spanish(self):
        from ogr_gui.i18n import current_language, set_language
        w = _window()
        up = w.project.user_polylines[0]
        was = current_language()
        set_language("es")
        try:
            with _typed(180.0), _status(w) as said:
                w._on_sarma_angle_typed(up.id, *_KINK)
            with _typed(300.0), _status(w) as said2:
                w._on_sarma_angle_typed(up.id, *_KINK)
        finally:
            set_language(was)
        assert said == ["El ángulo en (108, 6.4) ha de ser un número finito "
                        "y no horizontal."], said
        assert said2[-1] == ("300° es la misma cara que 120°, que es lo que "
                             "se guarda."), said2

    def test_c_and_phi_stay(self):
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(data=[
            {"x": _KINK[0], "y": _KINK[1], "c": 7.0, "phi": 33.0}])]
        c.refresh_scene()
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        _click_at(c, *_TOP)
        datum = w.project.user_polylines[0].vertex_data[_KINK]
        assert (datum["c"], datum["phi"]) == (7.0, 33.0) and datum["angle"]
        c.set_tool_mode(_mode("REMOVE_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        assert w.project.user_polylines[0].vertex_data[_KINK] == {
            "angle": None, "c": 7.0, "phi": 33.0}

    def test_one_step_each_and_undo(self):
        from ogr_gui.i18n import current_language, set_language, tr
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        _click_at(c, *_TOP)
        first = _angle(w)
        _click_at(c, *_KINK)
        with _typed(100.0):
            _key(c, _enter())
        assert _angle(w) == 100.0
        assert w.command_stack.history() == (
            ["Set Sarma face angle", "Set Sarma face angle"], [])
        w.act_undo()
        assert _angle(w) == first
        w.act_undo()
        assert _angle(w) is None
        was = current_language()
        set_language("es")
        try:
            names = [tr("Set Sarma face angle"), tr("Remove Sarma face angle")]
        finally:
            set_language(was)
        assert names == ["Definir un ángulo de cara de Sarma",
                         "Quitar un ángulo de cara de Sarma"]

    def test_the_pick_is_in_pixels(self):
        for scale in (5.0, 12.0):
            w = _window(scale)
            c = w.canvas
            c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
            kx, ky = _pixel(c, *_KINK)
            with _messages(c) as said:
                _press(c, kx + 15, ky)
            assert said == ["Click an interior vertex of a non-circular "
                            "surface."], (scale, said)
            assert c._sarma_pick is None
            _press(c, kx + 5, ky)
            assert c._sarma_pick == (w.project.user_polylines[0].id,
                                     *_KINK), scale
            # an end of the surface has no face
            c.set_tool_mode(_mode("SELECT"))
            c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
            with _messages(c) as said:
                _press(c, *_pixel(c, 0.0, 0.0))
            assert c._sarma_pick is None
            assert said == ["Click an interior vertex of a non-circular "
                            "surface."], said
            assert not w.project.user_polylines[0].vertex_data

    def test_the_live_ray_reaches_the_ground(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGraphicsPathItem
        from ogr_slip2d.sarma.wedges import vertex_face
        w = _window()
        c = w.canvas
        dotted = _dotted(c)
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        px = _pixel(c, *_TOP)
        with _messages(c) as said:
            _move(c, *px)
        rays = [it for it in c._draw_preview_items
                if isinstance(it, QGraphicsPathItem)
                and it.pen().style() == Qt.DashLine]
        assert len(rays) == 1, c._draw_preview_items
        path = rays[0].path()
        sx, sy = _scene(c, *px)
        from ogr_slip2d.sarma.angles import upward_degrees
        theta = upward_degrees(sx - _KINK[0], sy - _KINK[1])
        _t, top = vertex_face(w.project, *_KINK, theta)
        end = path.elementAt(path.elementCount() - 1)
        assert (path.elementAt(0).x, path.elementAt(0).y) == _KINK
        assert (end.x, end.y) == top, ((end.x, end.y), top)
        assert said == ["Face angle %.1f°: click to set it, Enter to type it,"
                        " Esc to let the vertex go." % theta], said
        # a second move gives the same ray its new path: no item is made
        # again (the review of v0.1.469)
        items = list(c._draw_preview_items)
        _move(c, *_pixel(c, *_KINK[:1], _KINK[1] + 30.0))
        assert c._draw_preview_items == items
        assert rays[0].path().elementAt(1).x == _KINK[0]
        # a direction whose face leaves through the side of the model
        with _messages(c) as said:
            _move(c, *_pixel(c, _KINK[0] + 40.0, _KINK[1] + 0.5))
        assert "does not leave the ground" in said[-1], said
        # Esc lets the vertex go and clears the preview; the stored rays
        # are untouched; a second Esc leaves the tool
        _key(c, _esc())
        assert c._sarma_pick is None and not c._draw_preview_items
        assert c.tool_mode == _mode("SET_SARMA_ANGLE")
        assert _dotted(c) == dotted
        _key(c, _esc())
        assert c.tool_mode == _mode("SELECT")

    def test_the_right_button_lets_go_then_leaves(self):
        from PySide6.QtCore import Qt
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        assert c._sarma_pick is not None
        _click_at(c, *_TOP, button=Qt.RightButton)
        assert c._sarma_pick is None and _angle(w) is None
        assert c.tool_mode == _mode("SET_SARMA_ANGLE")
        _click_at(c, *_TOP, button=Qt.RightButton)
        assert c.tool_mode == _mode("SELECT")

    def test_a_vertex_that_changed_between_the_clicks_is_asked_again(self):
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        # an edit between the two clicks: the kink moves, the surface
        # stays (its id), so what is asked is the vertex and not the id
        up = w.project.user_polylines[0]
        w.project.user_polylines = [_surface(
            [(0.0, 0.0), (107.0, 6.0), (128.0, 67.6737)], id=up.id)]
        with _messages(c) as said:
            _click_at(c, *_TOP)
        assert c._sarma_pick is None
        assert not w.project.user_polylines[0].vertex_data
        assert said and "changed" in said[-1], said

    def test_a_change_of_tool_or_of_project_lets_the_vertex_go(self):
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        c.set_tool_mode(_mode("SELECT"))
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        assert c._sarma_pick is None and not c._draw_preview_items
        # the same file opened again: same ids, and the click wrote there
        _click_at(c, *_KINK)
        c._forget_interaction()
        assert c._sarma_pick is None

    def test_a_redraw_and_an_enter_ask_for_a_vertex_still_there(self):
        w = _window()
        c = w.canvas
        up = w.project.user_polylines[0]
        moved = [(0.0, 0.0), (107.0, 6.0), (128.0, 67.6737)]
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        w.project.user_polylines = [_surface(moved, id=up.id)]
        c.refresh_scene()
        assert c._sarma_pick is None and not c._draw_preview_items
        # and Enter, with no redraw in between
        w.project.user_polylines = [_surface(id=up.id)]
        c.refresh_scene()
        _click_at(c, *_KINK)
        w.project.user_polylines = [_surface(moved, id=up.id)]
        with _typed(100.0) as asked, _messages(c) as said:
            _key(c, _enter())
        assert asked == [] and said and "changed" in said[-1], said

    def test_two_surfaces_through_one_vertex(self):
        """The first takes the tool and is named; the menu has a part for
        each (the owner's decision)."""
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(), _surface(_SECOND)]
        c.refresh_scene()
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        with _messages(c) as said:
            _click_at(c, *_KINK)
        assert said[-1].startswith("Vertex picked on non-circular surface "
                                   "1:"), said
        _click_at(c, *_TOP)
        first, second = w.project.user_polylines
        assert first.vertex_data and not second.vertex_data
        c.set_tool_mode(_mode("SELECT"))
        texts = [x for x, _e in TestTheVertexMenu()._right_click(c, *_KINK)]
        heads = [x for x in texts if x.startswith("Vertex (108.000")]
        assert heads == ["Vertex (108.000, 6.400) of non-circular surface 1",
                         "Vertex (108.000, 6.400) of non-circular surface 2"]
        assert texts.count("Set Face Angle") == 2, texts
        # a vertex of the second surface alone is named by its number
        w.project.user_polylines = [_surface(_OTHER), _surface()]
        c.refresh_scene()
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        with _messages(c) as said:
            _click_at(c, *_KINK)
        assert said[-1].startswith("Vertex picked on non-circular surface "
                                   "2:"), said
        c.set_tool_mode(_mode("SELECT"))

    def test_the_selection_filter_is_read(self):
        w = _window()
        c = w.canvas
        c.selection_filter.surfaces = False
        try:
            c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
            with _messages(c) as said:
                _click_at(c, *_KINK)
            assert c._sarma_pick is None and said == [
                "Click an interior vertex of a non-circular surface."]
        finally:
            c.selection_filter.surfaces = True
        _click_at(c, *_KINK)
        assert c._sarma_pick is not None

    def test_a_closed_gate_writes_nothing(self):
        from ogr_core.project.settings import SurfaceType
        w = _window()
        c = w.canvas
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        w.project.settings.search.surface_type = SurfaceType.CIRCULAR.value
        w.refresh_action_availability()
        try:
            with _status(w) as said:
                _click_at(c, *_TOP)
        finally:
            w.project.settings.search.surface_type = \
                SurfaceType.NON_CIRCULAR.value
            w.refresh_action_availability()
        assert _angle(w) is None and w.command_stack.history() == ([], [])
        assert said == ["Only available with Surface Options -> Surface "
                        "Type = Non-Circular."], said

    def test_a_refused_datum_is_said_as_such(self):
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface()]
        w.project.user_polylines[0].vertex_data = {
            _KINK: {"angle": 100.0, "c": -5.0, "phi": 20.0}}
        c.refresh_scene()
        c.set_tool_mode(_mode("REMOVE_SARMA_ANGLE"))
        with _messages(c) as said:
            _click_at(c, *_KINK)
        assert said == ["The face strength at (108, 6.4) needs numbers with "
                        "c >= 0 and 0 <= φ < 90. Correct it in Surfaces -> "
                        "Sarma Data per Vertex..."], said

    def test_the_typed_value_starts_at_the_stored_face(self):
        w = _window()
        up = w.project.user_polylines[0]
        up.vertex_data = {_KINK: {"angle": -60.0, "c": None, "phi": None}}
        with _typed(None) as asked:
            w._on_sarma_angle_typed(up.id, *_KINK)
        assert asked[0][2] == 120.0, asked
        with _typed(300.1):
            w._on_sarma_angle_typed(up.id, *_KINK)
        assert _angle(w) == 120.1
        with _typed(1.0), _status(w) as said:
            w._on_sarma_angle_typed(up.id, *_KINK)
        assert _angle(w) == 1.0
        assert said == ["Face angle 1° stored at (108.000, 6.400): the face "
                        "does not leave the ground there, and the method "
                        "would refuse the surface."], said

    def test_an_id_that_is_no_string(self):
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(id=5)]
        c.refresh_scene()
        c.set_tool_mode(_mode("SET_SARMA_ANGLE"))
        _click_at(c, *_KINK)
        _click_at(c, *_TOP)
        assert abs(_angle(w) - W63._THETA4) <= 0.1

    def test_the_stored_rays_reach_the_ground(self):
        w = _window()
        c = w.canvas
        up = w.project.user_polylines[0]
        w._write_sarma_angle(up.id, *_KINK, W63._THETA4)
        (ray,) = _dotted(c)
        path = ray.path()
        end = path.elementAt(1)
        assert math.hypot(end.x - _TOP[0], end.y - _TOP[1]) <= 1e-6
        # a face that does not leave the ground keeps a fifth of the width
        w._write_sarma_angle(up.id, *_KINK, 1.0)
        (ray,) = _dotted(c)
        end = ray.path().elementAt(1)
        length = math.hypot(end.x - _KINK[0], end.y - _KINK[1])
        assert abs(length - 0.2 * 128.0) <= 1e-9, length


# ======================================================================
class TestTheVertexMenu:

    def _right_click(self, c, x, y):
        from PySide6.QtCore import Qt
        return _menu(lambda: _click_at(c, x, y, button=Qt.RightButton))

    def test_the_kink_shows_both_parts(self):
        w = _window()
        c = w.canvas
        texts = [t for t, _e in self._right_click(c, *_KINK)]
        assert "Move Vertex" in texts and "Delete Vertex" in texts, texts
        i = texts.index("Delete Vertex")
        assert texts[i + 1] == ("Vertex (108.000, 6.400) of non-circular "
                                "surface 1"), texts
        assert texts[i + 2:] == ["Set Face Angle", "Type Face Angle…",
                                 "Remove Face Angle",
                                 "Sarma Data per Vertex..."], texts

    def test_a_vertex_of_the_surface_alone(self):
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(_OTHER)]
        c.refresh_scene()
        got = self._right_click(c, 60.0, 20.0)
        assert [t for t, _e in got] == [
            "Vertex (60.000, 20.000) of non-circular surface 1",
            "Set Face Angle", "Type Face Angle…", "Remove Face Angle",
            "Sarma Data per Vertex..."], got
        enabled = dict(got)
        assert enabled["Set Face Angle"] and not enabled["Remove Face Angle"]
        w.project.user_polylines = [_surface(_OTHER, data=[
            {"x": 60.0, "y": 20.0, "angle": 80.0}])]
        c.refresh_scene()
        assert dict(self._right_click(c, 60.0, 20.0))["Remove Face Angle"]

    def test_each_action_does_what_it_says(self):
        from ogr_gui.dialogs.sarma_vertex_dialog import SarmaVertexDialog
        w = _window()
        c = w.canvas
        pid = w.project.user_polylines[0].id
        with _typed(95.0):
            c.user_vertex_action_requested.emit("sarma_type", pid, *_KINK)
        assert _angle(w) == 95.0
        c.user_vertex_action_requested.emit("sarma_remove", pid, *_KINK)
        assert _angle(w) is None
        c.user_vertex_action_requested.emit("sarma_set", pid, 100.0, 5.0)
        assert c.tool_mode == _mode("SET_SARMA_ANGLE")
        assert c._sarma_pick is None        # (100, 5) is no vertex
        c.user_vertex_action_requested.emit("sarma_set", pid, *_KINK)
        assert c.tool_mode == _mode("SET_SARMA_ANGLE")
        assert c._sarma_pick == (pid, *_KINK)
        _click_at(c, *_TOP)
        assert abs(_angle(w) - W63._THETA4) <= 0.1
        c.set_tool_mode(_mode("SELECT"))
        # the table of the surface whose vertex it is, without asking which:
        # with two surfaces the menu's path would ask (a modal question)
        from PySide6.QtWidgets import QInputDialog
        w.project.user_polylines = [_surface(_OTHER),
                                    w.project.user_polylines[0]]
        opened, asked = [], []
        raw, raw_item = SarmaVertexDialog.exec, QInputDialog.__dict__.get(
            "getItem")

        def record(dlg):
            opened.append(dlg._polyline)
            return dlg.DialogCode.Rejected

        def ask(*_a, **_k):
            asked.append(_a)
            return "", False
        SarmaVertexDialog.exec = record
        QInputDialog.getItem = staticmethod(ask)
        try:
            c.user_vertex_action_requested.emit("sarma_table", pid, *_KINK)
        finally:
            SarmaVertexDialog.exec = raw
            if raw_item is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw_item
        assert opened == [w.project.user_polylines[1]] and not asked, (
            opened, asked)

    def test_a_support_through_the_vertex_keeps_its_menu(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import EndAnchored, SupportInstance
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(_OTHER)]
        st = EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)
        w.project.support_types = [st]
        w.project.supports = [SupportInstance(
            type_id=st.TYPE_ID, type_ref=st.id, head=Vertex(55.0, 20.0),
            tail=Vertex(65.0, 20.0))]
        c.refresh_scene()
        try:
            texts = [x for x, _e in self._right_click(c, 60.0, 20.0)]
        finally:
            w.project.supports = []
            w.project.support_types = []
        assert texts and "Set Face Angle" not in texts, texts

    def test_interprets_canvas_offers_none_of_it(self):
        from ogr_gui.canvas.canvas_view import CanvasView
        w = _window()
        assert w.canvas.user_surface_menu
        loose = CanvasView(w.project)
        try:
            assert loose.user_surface_menu is False
            loose.resize(800, 600)
            loose.show()
            _app().processEvents()
            loose.snap_settings.snap = False
            loose.setTransform(w.canvas.transform())
            loose.centerOn(95.0, 31.0)
            texts = [x for x, _e in self._right_click(loose, *_KINK)]
        finally:
            loose.close()
            loose.deleteLater()
        # v0.1.513 (D456) -- the boundary vertex's menu did open (its one
        # action off the main window is Copy Coordinates; Move Vertex was
        # the control here until the edit actions left Interpret's canvas)
        assert "Copy Coordinates" in texts and "Move Vertex" not in texts, \
            texts
        assert "Set Face Angle" not in texts, texts

    def test_with_a_circular_run_its_actions_are_grey(self):
        from ogr_core.project.settings import SurfaceType
        w = _window()
        c = w.canvas
        w.project.user_polylines = [_surface(_OTHER)]
        w.project.settings.search.surface_type = SurfaceType.CIRCULAR.value
        c.refresh_scene()
        try:
            got = self._right_click(c, 60.0, 20.0)
        finally:
            w.project.settings.search.surface_type = \
                SurfaceType.NON_CIRCULAR.value
        assert ("Only available with Surface Options -> Surface Type = "
                "Non-Circular.", False) in got, got
        assert not any(e for t, e in got if t in (
            "Set Face Angle", "Type Face Angle…", "Remove Face Angle",
            "Sarma Data per Vertex...")), got


# ======================================================================
class TestTheMenuAndTheWords:

    def test_the_actions_are_in_surfaces_and_greyed_with_a_reason(self):
        from ogr_core.project.settings import SurfaceType
        w = _window()
        # the menu holding the table's action (the pattern of
        # test_sarma_vertices_v1465: a QMenu taken out of a generator lost
        # its wrapper)
        menus = [[a for a in m.menu().actions()]
                 for m in w.menuBar().actions() if m.menu()]
        surfaces = next(acts for acts in menus
                        if w._actions["surf_polyline_sarma"] in acts)
        for key in ("surf_polyline_sarma_set", "surf_polyline_sarma_remove"):
            act = w._actions[key]
            assert act in surfaces, key
            assert act.isEnabled(), key
        w.project.user_polylines = []
        w.refresh_action_availability()
        for key in ("surf_polyline_sarma_set", "surf_polyline_sarma_remove"):
            act = w._actions[key]
            assert not act.isEnabled() and "Draw a non-circular surface" \
                in act.statusTip(), key
        w.project.user_polylines = [_surface()]
        w.project.settings.search.surface_type = SurfaceType.CIRCULAR.value
        w.refresh_action_availability()
        try:
            for key in ("surf_polyline_sarma_set",
                        "surf_polyline_sarma_remove"):
                assert not w._actions[key].isEnabled()
                assert "Non-Circular" in w._actions[key].statusTip()
        finally:
            w.project.settings.search.surface_type = \
                SurfaceType.NON_CIRCULAR.value
            w.refresh_action_availability()

    def test_the_words_in_spanish(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import current_language, set_language, tr
        was = current_language()
        set_language("es")
        try:
            got = [tr(k) for k in (
                "Set Sarma Face Angles", "Remove Sarma Face Angles",
                ToolMode.SET_SARMA_ANGLE.status_message,
                ToolMode.REMOVE_SARMA_ANGLE.status_message,
                "Set Face Angle", "Type Face Angle…", "Remove Face Angle",
                "Vertex let go.",
                "Click an interior vertex of a non-circular surface.")]
            live = tr("Face angle {0:.1f}°: click to set it, Enter to type "
                      "it, Esc to let the vertex go.").format(116.5)
        finally:
            set_language(was)
        assert got[:2] == ["Definir ángulos de cara de Sarma",
                           "Quitar ángulos de cara de Sarma"], got
        assert got[2].startswith("Definir ángulos de cara de Sarma: pulsa")
        assert got[3].startswith("Quitar ángulos de cara de Sarma: pulsa")
        assert got[4:] == ["Definir ángulo de cara", "Teclear ángulo de cara…",
                           "Quitar ángulo de cara", "Vértice soltado.",
                           "Pulsa un vértice interior de una superficie no "
                           "circular."], got
        assert live == ("Ángulo de cara 116.5°: pulsa para fijarlo, Intro "
                        "para teclearlo, Esc para soltar el vértice.")


# ======================================================================
def _mode(name):
    from ogr_gui.canvas.tool_mode import ToolMode
    return getattr(ToolMode, name)


def _enter():
    from PySide6.QtCore import Qt
    return Qt.Key_Return


def _esc():
    from PySide6.QtCore import Qt
    return Qt.Key_Escape


def _dotted(c):
    """The stored rays: the dotted path items of the scene."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QGraphicsPathItem
    return [it for it in c.scene().items()
            if isinstance(it, QGraphicsPathItem)
            and it.pen().style() == Qt.PenStyle.DotLine]


@contextlib.contextmanager
def _status(w):
    """What the window shows on its status bar."""
    got: list = []
    raw = w.ogr_status.showMessage

    def record(text, *a, **k):
        got.append(text)
        return raw(text, *a, **k)
    w.ogr_status.showMessage = record
    try:
        yield got
    finally:
        del w.ogr_status.showMessage
