# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.199 — a line load normal (or at an angle) to the boundary pushes along
the ground surface's frame, not vertically.

Until this version ``LineLoad.direction_vector`` had no branch for either
orientation and fell through to vertical, silently, while the interface
offered both (reported in v0.1.196; the operations layer refused them). The
owner decided the convention (2026-09-24), because the documentation this
interface follows does not define it: the normal points INTO the ground,
computed from the ground surface at the load point, the bisector of the two
neighbouring normals at a vertex; "angle to boundary" turns the ground's
left-to-right tangent counter-clockwise, so -90° is that normal. A point off
the ground has no such direction and is refused.

Invariants protected:

* **Rule 1, the Coulomb wedge** (Coulomb 1776; Duncan & Wright 2005 §6) of
  ``test_janbu_wedge_v1142`` with 100 kN/m normal to its face at (34, 6):
  F = [c'L + (W cos α + N_P) tan φ'] / (W sin α + D_P), with the load's
  components taken from the FIXTURE'S vertices, (12, −8)/√208 — never from
  ``direction_vector``. The force-equilibrium methods reach it on every
  plane (Janbu, both Corps, Lowe-Karafiath); Spencer and GLE on 40° and 45°
  (at 35° their λ search falls back, the family of D148 documented in
  ``test_anchored_wedge_root_v1177``, reported and not this file's claim).
  Bishop and Ordinary are not bound: the horizontal part acts at the load's
  elevation, above the base, and adds a couple — measured, not asserted.
* **Exact identities**: normal = angle_to_boundary(−90°) =
  angle_from_horizontal(atan2(−8, 12)) on the face; normal on the flat crest
  = vertical; at the crest vertex, the bisector in closed form; +90° is the
  outward normal; a vertical step points into the wall; the mirror image of
  the slope gives the mirror image of the direction.
* **Refusals**: off the ground, the operation refuses, the analysis refuses
  with the load named, and the interface does not add it.
* **Every consumer** goes through the one door: the DXF arrow of a
  horizontal load is horizontal now (it was drawn at ``angle_deg or 270``).
"""
from __future__ import annotations

import json
import math

H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
P = 100.0
_N_FACE = (12 / math.sqrt(208), -8 / math.sqrt(208))
_REL = 2e-6     # a factor of safety is reported to 6 decimals
_FORCE = ("janbu_simplified", "janbu_corrected", "corps_engineers_1",
          "corps_engineers_2", "lowe_karafiath")
_COMPLETE = ("spencer", "gle_morgenstern_price")


def _raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} was not raised")


def _xd(beta):
    return TOE + H / math.tan(math.radians(beta))


def _closed_form(beta, d):
    """The wedge with a point force P along unit d, from geometry alone."""
    a = math.radians(beta)
    w = GAMMA * 0.5 * H * (_xd(beta) - CREST)
    length = H / math.sin(a)
    dx, dy = d
    drive = -P * (dx * math.cos(a) + dy * math.sin(a))
    press = P * (dx * math.sin(a) - dy * math.cos(a))
    return (COH * length + (w * math.cos(a) + press)
            * math.tan(math.radians(PHI))) / (w * math.sin(a) + drive)


def _wedge(ws, **load):
    from ogr_api import call
    pid = call(ws, "project_new", name="Wedge")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, -10], [60, -10], [60, H], [CREST, H], [TOE, 0],
                     [0, 0]],
        "materials": [{"name": "S", "unit_weight": GAMMA, "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": COH, "friction_angle": PHI}}}],
        "settings": {"methods.num_slices": 50, "methods.tolerance": 1e-10,
                     "methods.max_iterations": 400}})
    if load:
        call(ws, "load_set", project_id=pid, kind="line", magnitude=P,
             **load)
    return pid


def _fos(ws, pid, beta, methods):
    from ogr_api import call
    plane = {"type": "polyline", "points": [[TOE, 0], [_xd(beta), H]]}
    out = call(ws, "surface_evaluate", project_id=pid, surface=plane,
               methods=list(methods))["methods"]
    return {k: v["fos"] for k, v in out.items()}


def _direction(ws, pid):
    from ogr_core.loads.loads import line_load_direction
    p = ws.get(pid).project
    return line_load_direction(p, p.line_loads[0])


# ======================================================================
class TestTheWedgeWithAFaceNormalLoad:
    def test_the_force_methods_reach_the_closed_form(self):
        from ogr_api import Workspace
        ws = Workspace()
        try:
            pid = _wedge(ws, point_xy=[34, 6],
                         orientation="normal_to_boundary")
            for beta in (35.0, 40.0, 45.0):
                ref = _closed_form(beta, _N_FACE)
                for mid, f in _fos(ws, pid, beta, _FORCE).items():
                    assert abs(f / ref - 1) < _REL, (beta, mid, f, ref)
            for beta in (40.0, 45.0):
                ref = _closed_form(beta, _N_FACE)
                for mid, f in _fos(ws, pid, beta, _COMPLETE).items():
                    assert abs(f / ref - 1) < _REL, (beta, mid, f, ref)
        finally:
            ws.shutdown()

    def test_the_normal_is_not_the_vertical_it_used_to_be(self):
        # The same load vertical gives the closed form with d = (0, −1):
        # a different number, so the direction is read (rule 7).
        from ogr_api import Workspace
        ws = Workspace()
        try:
            normal = _fos(ws, _wedge(ws, point_xy=[34, 6],
                                     orientation="normal_to_boundary"),
                          40.0, ("janbu_simplified",))["janbu_simplified"]
            vertical = _fos(ws, _wedge(ws, point_xy=[34, 6],
                                       orientation="vertical"),
                            40.0, ("janbu_simplified",))["janbu_simplified"]
            assert abs(vertical / _closed_form(40.0, (0.0, -1.0)) - 1) < _REL
            assert abs(normal - vertical) > 0.1
        finally:
            ws.shutdown()


class TestIdentities:
    def test_three_ways_of_saying_the_face_normal(self):
        from ogr_api import Workspace
        ws = Workspace()
        try:
            ways = [dict(orientation="normal_to_boundary"),
                    dict(orientation="angle_to_boundary", angle_deg=-90.0),
                    dict(orientation="angle_from_horizontal",
                         angle_deg=math.degrees(math.atan2(-8, 12)))]
            dirs = [_direction(ws, _wedge(ws, point_xy=[34, 6], **w))
                    for w in ways]
            for d in dirs:
                assert math.dist(d, _N_FACE) < 1e-12, d
            outward = _direction(ws, _wedge(
                ws, point_xy=[34, 6], orientation="angle_to_boundary",
                angle_deg=90.0))
            assert math.dist(outward, (-_N_FACE[0], -_N_FACE[1])) < 1e-12
        finally:
            ws.shutdown()

    def test_the_crest_and_its_corner(self):
        from ogr_api import Workspace
        ws = Workspace()
        try:
            flat = _direction(ws, _wedge(ws, point_xy=[50, 12],
                                         orientation="normal_to_boundary"))
            assert math.dist(flat, (0.0, -1.0)) < 1e-12
            corner = _direction(ws, _wedge(ws, point_xy=[CREST, H],
                                           orientation="normal_to_boundary"))
            sx, sy = _N_FACE[0], _N_FACE[1] - 1.0
            want = (sx / math.hypot(sx, sy), sy / math.hypot(sx, sy))
            assert math.dist(corner, want) < 1e-12, (corner, want)
        finally:
            ws.shutdown()

    def test_a_step_and_a_mirror(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.ground import ground_frame, ground_surface
        # a vertical step up at x = 20, ground higher on the right
        ext = Boundary(polyline=Polyline(vertices=[
            Vertex(0, 0), Vertex(40, 0), Vertex(40, 10), Vertex(20, 10),
            Vertex(20, 5), Vertex(0, 5)], closed=True),
            btype=BoundaryType.EXTERNAL)
        tx, ty, nx, ny = ground_frame(ground_surface(ext), 20, 7.5, 1e-6)
        assert math.dist((nx, ny), (1.0, 0.0)) < 1e-12    # into the wall
        # the mirror image of the wedge: its face normal is the mirror one
        mirror = Boundary(polyline=Polyline(vertices=[
            Vertex(60 - x, y) for x, y in
            [(0, -10), (60, -10), (60, H), (CREST, H), (TOE, 0), (0, 0)]],
            closed=True), btype=BoundaryType.EXTERNAL)
        mirror.polyline.ensure_ccw()
        _t, _u, mx, my = ground_frame(ground_surface(mirror), 60 - 34, 6,
                                      1e-6)
        assert math.dist((mx, my), (-_N_FACE[0], _N_FACE[1])) < 1e-12


# ======================================================================
class TestOffTheGround:
    def test_the_operation_the_analysis_and_the_interface_refuse(self):
        from ogr_api import Conflict, Workspace, call
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad, LoadOrientation
        from ogr_slip2d.analysis_runner import check_analysis_settings
        ws = Workspace()
        try:
            pid = _wedge(ws)
            before = json.dumps(ws.get(pid).project.to_dict(),
                                sort_keys=True, default=str)
            err = _raised(Conflict, lambda: call(
                ws, "load_set", project_id=pid, kind="line",
                point_xy=[45, 5], magnitude=P,
                orientation="normal_to_boundary"))
            assert "not on the ground" in str(err)
            assert json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                              default=str) == before
            p = ws.get(pid).project
            p.line_loads.append(LineLoad(
                point=Vertex(45, 5), magnitude=P, name="Buried",
                orientation=LoadOrientation.NORMAL_TO_BOUNDARY))
            problems = check_analysis_settings(p)
            assert any("Buried" in s and "not on the ground" in s
                       for s in problems), problems
        finally:
            ws.shutdown()

    def test_the_window_does_not_add_it(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:  # pragma: no cover
            return
        QApplication.instance() or QApplication([])
        from ogr_core.loads import LoadOrientation
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w._attach_project(build_demo_project())
        w._pending_line_load = {"magnitude": 10.0, "angle_deg": 0.0,
                                "orientation":
                                    LoadOrientation.NORMAL_TO_BOUNDARY}
        w._on_line_load_point_picked(20.0, 10.0)        # inside the mass
        assert w.project.line_loads == []
        w._pending_line_load = {"magnitude": 10.0, "angle_deg": 0.0,
                                "orientation":
                                    LoadOrientation.NORMAL_TO_BOUNDARY}
        w._on_line_load_point_picked(30.0, 20.0)        # on the face
        assert len(w.project.line_loads) == 1


class TestTheConsumers:
    def test_the_dxf_arrow_follows_the_direction(self):
        import shutil
        import tempfile
        from pathlib import Path

        import ezdxf

        from ogr_api import Workspace, call
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_ll_"))
        try:
            pid = _wedge(ws, point_xy=[50, 12], orientation="horizontal")
            path = str(tmp / "loads.dxf")
            call(ws, "dxf_export", project_id=pid, path=path)
            doc = ezdxf.readfile(path)
            shafts = [e for e in doc.modelspace()
                      if e.dxftype() == "LINE" and "LOAD" in e.dxf.layer
                      and abs(e.dxf.end.x - 50) < 1e-9
                      and abs(e.dxf.end.y - 12) < 1e-9]
            assert shafts, "no arrow ends at the load point"
            s = shafts[0]
            assert abs(s.dxf.start.y - s.dxf.end.y) < 1e-9     # horizontal
            assert s.dxf.start.x < s.dxf.end.x                 # pushing +x
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)
