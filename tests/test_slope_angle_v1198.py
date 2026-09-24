# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.198 — Change Slope Angle moves the slope face, and only the face.

The function this replaces rotated the WHOLE External boundary about a typed
pivot, with a sense that depended on which way the slope faced: on the demo
slope, asking for 30° left the face at 60° and the base, the crest and
everything else tilted by 15°. Its tool mode was never entered, and an
agent could not reach it.

Invariants protected, each against a closed form:

* **Only the face moves.** The toe and the crest are External vertices; the
  base and the plateau keep every coordinate.
* **Horizontal projection** (the default): the crest goes to
  x_t + s·H/tan β' at its own elevation, the overall angle is β' exactly,
  and the area changes by ½·H·|Δx| — the same whichever way the slope
  faces (the mirror image of the demo gives the mirror result).
* **Keep benches** (the default): two vertices at one elevation move
  together, so a bench keeps its width; without it each vertex is carried
  on its own ray from the toe, turned by the chord's rotation and brought
  back to its elevation, x = x_t + (y_v − y_t)·cot(φ_v + δ). The two differ
  on a benched slope (rule 7).
* **Vertical projection**: abscissae kept, y_c' = y_t + |Δx|·tan β'.
  **Rotate**: every face vertex keeps its distance to the toe.
* **Rule 1 through the engine.** The Coulomb wedge of
  ``test_anchored_wedge_root_v1177`` with its face taken from 56.3° to 50°
  by the operation gives the closed form of the NEW geometry (Coulomb 1776;
  Duncan & Wright 2005 §6).
* **What sits on the face.** A layer ending on the face still ends on it,
  at its elevation; a support is not moved and is named in a note.
* **Refusals leave the model untouched**: 0° and 90°, a toe above the
  crest, a point that is not a vertex, a crest pushed past the plateau,
  ``keep_benches`` with ``rotate`` (a setting the mode would not read).
* **The interface** picks the toe and the crest with real clicks, refuses a
  click away from an External vertex, cancels with Esc, enters the mode
  from the right-click menu, and applies one undoable step; its dialog
  greys out the bench option for Rotate and refuses an angle outside
  (0°, 90°).
* **Insert Vertex works**: ``_pick_edge`` had lost its ``def`` line (so
  every click raised AttributeError) since the first public release.
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_anchored_wedge_root_v1177 as W  # noqa: E402

_REL = 2e-6
_WINDOWS: list = []
_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 10.0, "friction_angle": 25.0}}
#: The demo slope: toe (35, 15), crest (25, 25), facing right (+x).
_DEMO = [[0, 0], [50, 0], [50, 15], [35, 15], [25, 25], [0, 25]]
#: Two benches: toe (36, 4), a bench at y = 12 from x 26 to 30, crest
#: (20, 20); overall 45°.
_BENCHED = [[0, 0], [60, 0], [60, 4], [36, 4], [30, 12], [26, 12],
            [20, 20], [0, 20]]


def _raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} was not raised")


def _project(external, extra=None):
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Slope")["project_id"]
        spec = {"external": external,
                "materials": [{"name": "Soil", "unit_weight": 19.0,
                               "strength": _SOIL}]}
        spec.update(extra or {})
        call(ws, "model_define", project_id=pid, spec=spec)
        return ws.get(pid).project
    finally:
        ws.shutdown()


def _xy(project):
    return [(v.x, v.y) for v in project.external_boundary().polyline.vertices]


def _area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                   in zip(pts, pts[1:] + pts[:1]))) / 2


def _dump(project):
    return json.dumps(project.to_dict(), sort_keys=True, default=str)


def _change(project, toe, crest, **kw):
    from ogr_core.geometry.slope_angle import change_slope_angle
    return change_slope_angle(project, toe, crest, **kw)


def _mirror(pts, width=50.0):
    return [[width - x, y] for x, y in pts]


# ======================================================================
class TestOnlyTheFaceMoves:
    def test_horizontal_projection_on_the_demo(self):
        p = _project(_DEMO)
        before = _xy(p)
        out = _change(p, (35, 15), (25, 25), target_deg=30.0)
        after = _xy(p)
        crest_x = 35 - 10 / math.tan(math.radians(30))
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        assert moved == [((25.0, 25.0), (crest_x, 25.0))], moved
        assert abs(out["old_angle_deg"] - 45.0) < 1e-12
        assert abs(math.degrees(math.atan2(10, 35 - crest_x)) - 30) < 1e-12
        # the triangle between the old face and the new one
        assert abs((_area(before) - _area(after))
                   - 0.5 * 10 * (25 - crest_x)) < 1e-9

    def test_the_sense_does_not_depend_on_the_facing(self):
        p = _project(_mirror(_DEMO))
        before = _xy(p)
        _change(p, (15, 15), (25, 25), target_deg=30.0)
        crest_x = 15 + 10 / math.tan(math.radians(30))
        moved = [(b, a) for b, a in zip(before, _xy(p)) if b != a]
        assert moved == [((25.0, 25.0), (crest_x, 25.0))], moved

    def test_a_change_is_added_to_the_overall_angle(self):
        p = _project(_DEMO)
        out = _change(p, (35, 15), (25, 25), change_deg=-15.0)
        assert abs(out["new_angle_deg"] - 30.0) < 1e-12
        q = _project(_DEMO)
        _change(q, (35, 15), (25, 25), change_deg=10.0)
        crest = [v for v in _xy(q) if v[1] == 25.0 and v[0] > 0][0]
        assert abs(math.degrees(math.atan2(10, 35 - crest[0])) - 55) < 1e-12


class TestBenches:
    def _benches(self, pts):
        """Widths of the horizontal steps between toe and crest."""
        face = [p for p in pts if 4 < p[1] < 20]
        by_y: dict = {}
        for x, y in face:
            by_y.setdefault(y, []).append(x)
        return {y: max(xs) - min(xs) for y, xs in by_y.items()
                if len(xs) == 2}

    def test_keep_benches_keeps_their_width(self):
        p = _project(_BENCHED)
        before = self._benches(_xy(p))
        _change(p, (36, 4), (20, 20), target_deg=35.0)
        after = _xy(p)
        assert self._benches(after) == before == {12.0: 4.0}
        crest = next(v for v in after if v[1] == 20.0 and v[0] > 0)
        assert abs(math.degrees(math.atan2(16, 36 - crest[0])) - 35) < 1e-12

    def test_without_it_each_vertex_rides_its_own_ray(self):
        p = _project(_BENCHED)
        _change(p, (36, 4), (20, 20), target_deg=35.0, keep_benches=False)
        after = dict((y, sorted(x for x, yy in _xy(p) if yy == y))
                     for y in (12.0,))
        # the chord turns by δ; each vertex's ray from the toe turns by δ
        # and is brought back to its own elevation
        xt, yt = 36.0, 4.0
        delta = math.radians(180 - 35) - math.atan2(16, 20 - 36)
        want = sorted(xt + (y - yt) / math.tan(math.atan2(y - yt, x - xt)
                                               + delta)
                      for x, y in ((30, 12), (26, 12)))
        assert all(abs(a - b) < 1e-9 for a, b in zip(after[12.0], want))
        width = after[12.0][1] - after[12.0][0]
        assert abs(width - 4.0) > 0.1          # the option moves the bench


class TestTheOtherModes:
    def test_vertical_projection(self):
        p = _project(_DEMO)
        before = _xy(p)
        _change(p, (35, 15), (25, 25), target_deg=30.0, mode="vertical")
        moved = [(b, a) for b, a in zip(before, _xy(p)) if b != a]
        want = 15 + 10 * math.tan(math.radians(30))
        assert len(moved) == 1 and moved[0][1][0] == 25.0
        assert abs(moved[0][1][1] - want) < 1e-12

    def test_rotation_keeps_the_distance_to_the_toe(self):
        p = _project(_BENCHED)
        before = _xy(p)
        _change(p, (36, 4), (20, 20), target_deg=30.0, mode="rotate")
        after = _xy(p)
        for b, a in zip(before, after):
            if b != a:
                assert abs(math.dist(b, (36, 4)) - math.dist(a, (36, 4))) \
                    < 1e-9
        crest = after[before.index((20.0, 20.0))]
        assert abs(math.degrees(math.atan2(crest[1] - 4, 36 - crest[0]))
                   - 30) < 1e-9


# ======================================================================
class TestTheWedgeThroughTheOperation:
    def test_a_flatter_face_is_the_coulomb_wedge_of_the_new_geometry(self):
        from ogr_api import Workspace, call
        beta_face, beta_plane = 50.0, 40.0
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="Wedge")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, -10], [60, -10], [60, W.H],
                             [W.CREST, W.H], [W.TOE, 0], [0, 0]],
                "materials": [{"name": "S", "unit_weight": W.GAMMA,
                               "strength": {
                                   "model": "mohr_coulomb",
                                   "params": {"cohesion": W.COH,
                                              "friction_angle": W.PHI}}}],
                "settings": {"methods.num_slices": W.NSLICES,
                             "methods.tolerance": W.TIGHT,
                             "methods.max_iterations": W.MAX_IT}})
            out = call(ws, "slope_angle_change", project_id=pid,
                       toe=[W.TOE, 0], crest=[W.CREST, W.H],
                       target_deg=beta_face)
            assert abs(out["old_angle_deg"]
                       - math.degrees(math.atan2(W.H, W.CREST - W.TOE))) \
                < 1e-12
            crest = W.TOE + W.H / math.tan(math.radians(beta_face))
            xd = W._daylight_x(beta_plane)
            a = math.radians(beta_plane)
            weight = W.GAMMA * 0.5 * W.H * (xd - crest)
            ref = (W.COH * math.hypot(xd - W.TOE, W.H) + weight * math.cos(a)
                   * math.tan(math.radians(W.PHI))) / (weight * math.sin(a))
            plane = {"type": "polyline", "points": [[W.TOE, 0], [xd, W.H]]}
            got = call(ws, "surface_evaluate", project_id=pid, surface=plane,
                       methods=["spencer", "janbu_simplified"])["methods"]
            for mid, m in got.items():
                assert abs(m["fos"] / ref - 1) < _REL, (mid, m["fos"], ref)
        finally:
            ws.shutdown()


# ======================================================================
class TestWhatSitsOnTheFace:
    def test_a_layer_follows_and_a_support_stays(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import SupportInstance
        p = _project(_DEMO, {"material_boundaries": [[[0, 20], [30, 20]]]})
        p.supports.append(SupportInstance(
            type_id="end_anchored", head=Vertex(32, 18), tail=Vertex(25, 15),
            name="Anchor A"))
        out = _change(p, (35, 15), (25, 25), target_deg=30.0)
        layer = next(b for b in p.boundaries if b.btype.name == "MATERIAL")
        end = layer.polyline.vertices[-1]
        assert abs(end.y - 20) < 1e-12
        assert abs(end.x - (35 - 5 / math.tan(math.radians(30)))) < 1e-9
        assert (layer.polyline.vertices[0].x,
                layer.polyline.vertices[0].y) == (0, 20)
        assert (p.supports[0].head.x, p.supports[0].head.y) == (32, 18)
        assert out["attached_moved"] == 1
        assert any("Anchor A" in n for n in out["notes"])


class TestRefusals:
    def test_each_leaves_the_model_untouched(self):
        p = _project(_DEMO)
        before = _dump(p)
        attempts = [
            dict(toe=(35, 15), crest=(25, 25), target_deg=90.0),
            dict(toe=(35, 15), crest=(25, 25), target_deg=0.0),
            dict(toe=(25, 25), crest=(35, 15), target_deg=30.0),
            dict(toe=(34, 16), crest=(25, 25), target_deg=30.0),
            dict(toe=(35, 15), crest=(25, 25), target_deg=5.0),
            dict(toe=(35, 15), crest=(25, 25), target_deg=30.0,
                 mode="rotate", keep_benches=True),
            dict(toe=(35, 15), crest=(25, 25), target_deg=30.0,
                 change_deg=5.0),
        ]
        for kw in attempts:
            toe, crest = kw.pop("toe"), kw.pop("crest")
            _raised(ValueError, lambda: _change(p, toe, crest, **kw))
            assert _dump(p) == before, kw

    def test_the_operation_says_why(self):
        from ogr_api import InvalidArgument, Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            err = _raised(InvalidArgument, lambda: call(
                ws, "slope_angle_change", project_id=pid, toe=[35, 15],
                crest=[25, 25], target_deg=5.0))
            assert "runs into" in str(err)
            # indices work as well as points
            ext = ws.get(pid).project.external_boundary()
            ti = next(i for i, v in enumerate(ext.polyline.vertices)
                      if (v.x, v.y) == (35, 15))
            ci = next(i for i, v in enumerate(ext.polyline.vertices)
                      if (v.x, v.y) == (25, 25))
            out = call(ws, "slope_angle_change", project_id=pid, toe=ti,
                       crest=ci, target_deg=30.0)
            assert abs(out["new_angle_deg"] - 30.0) < 1e-12
            call(ws, "project_history", project_id=pid, action="undo")
            assert (25.0, 25.0) in _xy(ws.get(pid).project)
        finally:
            ws.shutdown()


# ======================================================================
# The interface
# ======================================================================
def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, raw)


def _window(project):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QTransform

    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.PROMPT_ASSIGN_ON_DRAW = False
    w._attach_project(project)
    c = w.canvas
    c.resize(800, 600)
    c.show()
    c.snap_settings.snap = False
    c.setTransform(QTransform().scale(20.0, -20.0))
    c.centerOn(QPointF(25.0, 12.5))
    _WINDOWS.append(w)
    return w


def _click(canvas, x, y):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    pt = canvas.mapFromScene(QPointF(x, y))
    ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(pt),
                     canvas.mapToGlobal(pt), Qt.LeftButton, Qt.LeftButton,
                     Qt.NoModifier)
    canvas.mousePressEvent(ev)


class _Fake:
    """The dialog, answered: 45° → 30°, horizontal, benches kept."""
    seen: list = []

    def __init__(self, current_angle, parent=None):
        _Fake.seen.append(current_angle)

    def exec(self):
        return 1

    def parameters(self):
        return {"change_deg": -15.0, "mode": "horizontal",
                "keep_benches": True}


class TestTheInterface:
    def test_toe_and_crest_by_mouse(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_gui.main_window as mw
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window(_project(_DEMO))
        before = _dump(w.project)
        _Fake.seen.clear()
        with _swap(mw, "ChangeSlopeAngleDialog", _Fake):
            w.act_change_slope_angle()
            assert w.canvas.tool_mode == ToolMode.CHANGE_SLOPE_ANGLE
            _click(w.canvas, 30, 12)          # nowhere near a vertex
            assert w.canvas._slope_toe_idx is None
            _click(w.canvas, 35, 15)          # the toe
            _click(w.canvas, 25, 25)          # the crest
        assert _Fake.seen == [45.0]
        ref = _project(_DEMO)
        _change(ref, (35, 15), (25, 25), change_deg=-15.0)
        assert _xy(w.project) == _xy(ref)
        assert w.canvas.tool_mode == ToolMode.SELECT
        w.command_stack.undo(w.project)
        assert _dump(w.project) == before

    def test_escape_forgets_the_toe_and_the_menu_enters_the_mode(self):
        if _qt() is None:  # pragma: no cover
            return
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window(_project(_DEMO))
        ext_idx = w.project.boundaries.index(w.project.external_boundary())
        w._on_boundary_action_requested("change_slope", ext_idx)
        assert w.canvas.tool_mode == ToolMode.CHANGE_SLOPE_ANGLE
        _click(w.canvas, 35, 15)
        assert w.canvas._draw_points
        w.canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape,
                                         Qt.NoModifier))
        assert not w.canvas._draw_points
        got = []
        w.canvas.slope_vertices_picked.connect(lambda *a: got.append(a))
        _click(w.canvas, 25, 25)             # a toe again, not a crest
        assert got == []

    def test_the_dialog(self):
        if _qt() is None:  # pragma: no cover
            return
        from PySide6.QtWidgets import QDialogButtonBox

        from ogr_gui.dialogs.boundary_dialogs import ChangeSlopeAngleDialog
        dlg = ChangeSlopeAngleDialog(45.0)
        ok = dlg.buttons.button(QDialogButtonBox.Ok)
        dlg.spn_change.setValue(15.0)
        assert dlg.parameters() == {"change_deg": -15.0,
                                    "mode": "horizontal",
                                    "keep_benches": True}
        dlg.rb_increase.setChecked(True)
        dlg.spn_change.setValue(50.0)        # 95°: not a slope
        assert not ok.isEnabled()
        dlg.spn_change.setValue(10.0)
        assert ok.isEnabled()
        dlg.rb_rotate.setChecked(True)
        assert not dlg.chk_benches.isEnabled()
        assert dlg.parameters() == {"change_deg": 10.0, "mode": "rotate",
                                    "keep_benches": None}


class TestInsertVertex:
    def test_a_click_on_an_edge_inserts_a_vertex(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window(_project(_DEMO))
        n = len(w.project.external_boundary().polyline.vertices)
        w.canvas.set_tool_mode(ToolMode.INSERT_VERTEX)
        _click(w.canvas, 20, 0)               # on the base
        verts = w.project.external_boundary().polyline.vertices
        assert len(verts) == n + 1
        assert any(abs(v.y) < 1e-9 and 19 < v.x < 21 for v in verts)
