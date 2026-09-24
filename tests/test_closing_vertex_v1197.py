# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.197 — a closed boundary never stores its closing vertex.

The DXF reader repeats the first point of every closed polyline at its end
(since v0.1.59): the DXF package walks a ring's edges without wrapping and
needs the closing edge as a real segment. ``_to_boundary`` carried that
ring format into the model, so every imported closed boundary had a
zero-length closing edge. Measured in v0.1.196: harmless for the factor of
safety, but moving vertex 0 of an imported External left the copy behind
and cut a notch (575 m² instead of 580), a parallel offset turned the
zero-length edge into a spike, and the canvas drew two handles on one
point.

Invariants protected:

* a DXF round trip stores exactly the vertices drawn, and editing vertex 0
  of the imported model gives the area of the drawn one (the shoelace
  area, computed by hand);
* a mitred offset of an imported rectangle is (w + 2d)(h + 2d);
* a CIRCLE, whose ring closes only to −2.4e-16·r, is stripped too (the
  tolerance is relative to the polyline, not ``==``);
* a ``.ogr`` saved with the repeat is normalised on load, and
  ``from_dict(to_dict())`` is still the identity afterwards;
* ``add_boundary`` strips it for every other path (a converted
  annotation, a script);
* the inspection reports a crossing that only touches the closing edge of
  a closed polyline (the repeat used to be the only reason an imported
  model's closing edge was checked);
* the preview's vertex counts are the counts the model stores.
"""
from __future__ import annotations

import json
import math
import shutil
import tempfile
from pathlib import Path

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}
_SLOPE = [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25], [20, 25]]


def _area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                   in zip(pts, pts[1:] + pts[:1]))) / 2


def _model(ws, external=_SLOPE):
    from ogr_api import call
    pid = call(ws, "project_new", name="Closing")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": external,
        "materials": [{"name": "Soil", "unit_weight": 20.0,
                       "strength": _SOIL}]})
    return pid


def _round_trip(ws, pid, tmp):
    from ogr_api import call
    path = str(tmp / "m.dxf")
    call(ws, "dxf_export", project_id=pid, path=path, overwrite=True)
    call(ws, "dxf_import", project_id=pid, path=path)
    return path


def _xy(boundary):
    return [(float(v.x), float(v.y)) for v in boundary.polyline.vertices]


class TestTheDxfRoundTrip:
    def test_it_stores_the_vertices_drawn(self):
        from ogr_api import Workspace
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_closing_"))
        try:
            pid = _model(ws)
            _round_trip(ws, pid, tmp)
            ext = ws.get(pid).project.external_boundary()
            assert _xy(ext) == [tuple(map(float, p)) for p in _SLOPE]
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_moving_vertex_zero_moves_the_corner_not_a_copy(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_closing_"))
        try:
            pid = _model(ws)
            _round_trip(ws, pid, tmp)
            ext = ws.get(pid).project.external_boundary()
            call(ws, "boundary_edit", project_id=pid, boundary=ext.id,
                 op="move_vertex", index=0, point_xy=[18, 19])
            moved = [(18.0, 19.0)] + [tuple(map(float, p))
                                      for p in _SLOPE[1:]]
            regs = call(ws, "project_summary", project_id=pid)["regions"]
            assert [r["area"] for r in regs] == [_area(moved)] == [580.0]
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_an_imported_rectangle_offsets_without_a_spike(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_closing_"))
        try:
            pid = _model(ws, external=[[0, 0], [10, 0], [10, 5], [0, 5]])
            _round_trip(ws, pid, tmp)
            out = call(ws, "external_reshape", project_id=pid, offset=1.0)
            v = [tuple(p) for p in out["external"]["vertices"]]
            assert len(v) == 4
            assert abs(_area(v) - 12 * 7) < 1e-9
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_circle_closes_without_a_near_copy(self):
        import ezdxf

        from ogr_api import Workspace, call
        from ogr_core.geometry.cleanup import closing_tolerance
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_closing_"))
        try:
            doc = ezdxf.new()
            doc.modelspace().add_circle((0, 0), 10.0,
                                        dxfattribs={"layer": "TERRENO"})
            path = str(tmp / "circle.dxf")
            doc.saveas(path)
            pid = call(ws, "project_new", name="Circle")["project_id"]
            call(ws, "dxf_import", project_id=pid, path=path,
                 layer_kinds={"TERRENO": "external"})
            ext = ws.get(pid).project.external_boundary()
            vs = ext.polyline.vertices
            assert vs[0].distance_to(vs[-1]) > closing_tolerance(ext.polyline)
            # the ring is the polygon inscribed in r = 10
            assert abs(_area(_xy(ext)) - math.pi * 100) / (math.pi * 100) \
                < 0.01
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_preview_counts_what_is_stored(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_closing_"))
        try:
            pid = _model(ws)
            path = str(tmp / "m.dxf")
            call(ws, "dxf_export", project_id=pid, path=path)
            seen = call(ws, "dxf_inspect", path=path)
            n = len(_SLOPE)
            assert f"{n} → {n} vertices" in seen["summary"], seen["summary"]
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)


class TestTheRuleEverywhere:
    def test_a_file_with_the_repeat_is_normalised_on_load(self):
        from ogr_api import Workspace
        from ogr_core.project import Project
        ws = Workspace()
        try:
            data = ws.get(_model(ws)).project.to_dict()
        finally:
            ws.shutdown()
        for b in data["boundaries"]:
            if b["type"] == "EXTERNAL":
                b["polyline"]["vertices"].append(
                    list(b["polyline"]["vertices"][0]))
        p = Project.from_dict(data)
        assert _xy(p.external_boundary()) == \
            [tuple(map(float, q)) for q in _SLOPE]
        once = json.dumps(p.to_dict(), sort_keys=True, default=str)
        twice = json.dumps(Project.from_dict(p.to_dict()).to_dict(),
                           sort_keys=True, default=str)
        assert once == twice

    def test_add_boundary_strips_it(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.project import Project
        p = Project("x")
        ring = [(0, 0), (10, 0), (10, 5), (0, 5), (0, 1e-9)]
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(*q) for q in ring],
                              closed=True),
            btype=BoundaryType.EXTERNAL))
        assert len(p.boundaries[0].polyline.vertices) == 4
        # an OPEN polyline is left as it is: its ends are not a seam
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, 1), Vertex(5, 2),
                                        Vertex(0, 1)]),
            btype=BoundaryType.WATER_TABLE))
        assert len(p.boundaries[1].polyline.vertices) == 3

    def test_a_crossing_on_the_closing_edge_is_reported(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.cleanup import inspect_boundaries
        ext = Boundary(polyline=Polyline(vertices=[
            Vertex(0, 0), Vertex(10, 0), Vertex(10, 5), Vertex(0, 5)],
            closed=True), btype=BoundaryType.EXTERNAL)
        # crosses only the closing edge (0, 5) -> (0, 0)
        line = Boundary(polyline=Polyline(vertices=[Vertex(-1, 2),
                                                    Vertex(3, 2)]),
                        btype=BoundaryType.MATERIAL)
        rep = inspect_boundaries([ext, line])
        assert rep["cross_intersections"] == [
            {"a": ext.id, "b": line.id, "count": 1}]
