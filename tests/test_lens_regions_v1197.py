# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.197 — a lens is a hole of the region around it.

A closed material boundary strictly inside the model (a lens) came out of
the region builder as TWO regions covering the lens: ``polygonize`` hands
back the surrounding face WITH its hole, and the builder kept only its
outer ring. Every point of the lens was in both, and whichever came first
answered. Measured before the fix: painting a weak 80 m² lens painted the
whole 550 m² slope (factor of safety 1.6725 -> 0.4030), the region areas
summed to 630 m², and the finite-element mesh covered 1550 m² of a
1500 m² model with the lens meshed twice.

Invariants protected, each against an external reference:

* **Areas, exactly.** The region around a lens is the model minus the lens;
  the regions tile the model; a lens inside a lens gives a ring.
* **The Coulomb wedge (Coulomb 1776; Duncan & Wright 2005 §6).** A lens of
  the SAME material inside the sliding wedge leaves the closed form
  untouched; a HEAVIER lens gives the closed form with
  W = γ₁·A_wedge + (γ₂ − γ₁)·A_lens, exactly when the lens's vertical edges
  fall on slice edges, and within the band the slice rule allows
  ((γ₂ − γ₁)·t·b) when they do not.
* **Painting touches one region.** The lens and the region around it are
  painted independently, in either order.
* **An open line that ends ON a lens stops there** (it was taken for a
  dangling end and extended through the lens), and one that crosses it
  splits both regions as the areas say.
* **Inner wins.** A face inside nested closed boundaries inherits the
  innermost one's material (the loop kept the LARGEST).
* **Finite elements.** The mesh area is the model's, the lens is meshed
  once, its outline is not model boundary, and 1-D confined flow through a
  model with a lens is Darcy's closed form: the head linear at EVERY node
  and the discharge q = k·Δh/L·H. Measured with the holes dropped (the
  mesh of every version before this one): the discharge through the
  section still came out right, but the head was off by up to 7.6 m, the
  lens outline's nodes having been left as a boundary with no condition.
* **Converting a line to a material boundary keeps it open** (it was
  closed with a chord across the model).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_anchored_wedge_root_v1177 as W  # noqa: E402

_REL = 2e-6       # a factor of safety is reported to 6 decimals
#: The region builder snap-rounds onto a grid of diag·1e-8 before
#: polygonising (``regions.py``), so an area is exact to about grid ×
#: perimeter: 5.8e-7 m × < 200 m on these 50 × 30 models, well under this.
_AREA_ABS = 1e-4


def _raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} was not raised")


def _b(pts, btype, closed=False, material_id=None):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    pl = Polyline(vertices=[Vertex(*p) for p in pts], closed=closed)
    if closed:
        pl.ensure_ccw()
    return Boundary(polyline=pl, btype=btype, material_id=material_id)


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _regions(ext_pts, mats):
    from ogr_core.geometry import BoundaryType
    from ogr_core.geometry.regions import build_regions
    return build_regions(_b(ext_pts, BoundaryType.EXTERNAL, True), mats)


def _close(a, b, tol=_AREA_ABS):
    return abs(a - b) <= tol


# ======================================================================
class TestAreas:
    def test_the_region_around_a_lens_has_it_as_a_hole(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 15), B.MATERIAL, True)])
        areas = sorted(r.area for r in regs)
        assert len(regs) == 2
        assert _close(areas[0], 50.0) and _close(areas[1], 1500.0 - 50.0)
        assert _close(sum(areas), 1500.0)
        outer = max(regs, key=lambda r: r.area)
        lens = min(regs, key=lambda r: r.area)
        assert len(outer.holes) == 1 and not lens.holes
        assert outer.holes[0].signed_area() < 0          # holes run CW
        assert lens.contains(25, 12.5) and not outer.contains(25, 12.5)
        assert outer.contains(5, 5) and not lens.contains(5, 5)
        assert outer.contains(*outer.inside_point)
        assert lens.contains(*lens.inside_point)

    def test_a_lens_in_a_lens_is_a_ring(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(10, 5, 40, 25), B.MATERIAL, True),
                         _b(_box(20, 10, 30, 15), B.MATERIAL, True)])
        areas = sorted(r.area for r in regs)
        want = sorted([1500.0 - 600.0, 600.0 - 50.0, 50.0])
        assert len(regs) == 3
        assert all(_close(a, w) for a, w in zip(areas, want)), areas

    def test_the_centroid_of_a_holed_region_is_the_composite_one(self):
        # A centred lens puts the centroid of the ring around it IN the
        # lens: the reason ``inside_point`` exists.
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 20), B.MATERIAL, True)])
        outer = max(regs, key=lambda r: r.area)
        cx, cy = outer.centroid()
        assert abs(cx - 25.0) < 1e-6 and abs(cy - 15.0) < 1e-6
        assert not outer.contains(cx, cy)
        assert outer.contains(*outer.inside_point)


class TestLinesMeetingALens:
    def test_a_line_that_ends_on_the_lens_stops_there(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 15), B.MATERIAL, True),
                         _b([(0, 12.5), (20, 12.5)], B.MATERIAL)])
        areas = sorted(r.area for r in regs)
        assert len(regs) == 2, areas
        assert _close(areas[0], 50.0) and _close(areas[1], 1450.0)

    def test_a_line_through_the_lens_splits_both(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 15), B.MATERIAL, True),
                         _b([(0, 12.5), (50, 12.5)], B.MATERIAL)])
        areas = sorted(r.area for r in regs)
        want = sorted([50 * 17.5 - 25, 50 * 12.5 - 25, 25.0, 25.0])
        assert len(regs) == 4, areas
        assert all(_close(a, w) for a, w in zip(areas, want)), areas

    def test_the_innermost_closed_boundary_gives_its_material(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(10, 5, 40, 25), B.MATERIAL, True, "big"),
                         _b(_box(20, 10, 30, 15), B.MATERIAL, True, "small")])
        by_area = sorted(regs, key=lambda r: r.area)
        assert by_area[0].material_id == "small"
        assert by_area[1].material_id == "big"


# ======================================================================
# Rule 1 — the Coulomb wedge with a lens inside the sliding mass
# ======================================================================
_BETA = 40.0
_N = 50


def _wedge_with_lens(ws, lens_pts, lens_gamma, *, num_slices=_N):
    from ogr_api import call
    strength = {"model": "mohr_coulomb",
                "params": {"cohesion": W.COH, "friction_angle": W.PHI}}
    pid = call(ws, "project_new", name="Wedge")["project_id"]
    spec = {
        "external": [[0, -10], [60, -10], [60, W.H], [W.CREST, W.H],
                     [W.TOE, 0], [0, 0]],
        "materials": [{"name": "S", "unit_weight": W.GAMMA,
                       "strength": strength, "at": [5, -5]}],
        "settings": {"methods.num_slices": num_slices,
                     "methods.tolerance": W.TIGHT,
                     "methods.max_iterations": W.MAX_IT}}
    if lens_pts is not None:
        cx = sum(p[0] for p in lens_pts) / len(lens_pts)
        cy = sum(p[1] for p in lens_pts) / len(lens_pts)
        spec["material_boundaries"] = [{"points": lens_pts,
                                        "closed": True}]
        spec["materials"].append({"name": "L", "unit_weight": lens_gamma,
                                  "strength": strength, "at": [cx, cy]})
    call(ws, "model_define", project_id=pid, spec=spec)
    return pid


def _fos(ws, pid, method):
    from ogr_api import call
    plane = {"type": "polyline",
             "points": [[W.TOE, 0.0], [W._daylight_x(_BETA), W.H]]}
    return call(ws, "surface_evaluate", project_id=pid, surface=plane,
                methods=[method])["methods"][method]["fos"]


def _closed_form(weight):
    xd = W._daylight_x(_BETA)
    a = math.radians(_BETA)
    length = math.hypot(xd - W.TOE, W.H)
    return (W.COH * length + weight * math.cos(a) * math.tan(
        math.radians(W.PHI))) / (weight * math.sin(a))


def _aligned_lens(i0=25, i1=33, y0=8.2, y1=9.5):
    """A lens whose vertical edges fall on slice edges i0 and i1 of the
    uniform layout from the toe to the daylight point (no mandatory cut:
    it does not touch the plane), strictly inside the wedge."""
    xd = W._daylight_x(_BETA)
    b = (xd - W.TOE) / _N
    x0, x1 = W.TOE + i0 * b, W.TOE + i1 * b
    assert y0 > W.H * (x1 - W.TOE) / (xd - W.TOE)       # above the plane
    assert y1 < W.H * (x0 - W.TOE) / (W.CREST - W.TOE)  # below the face
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], (x1 - x0) * (y1 - y0)


class TestTheWedgeWithALens:
    def _soil_weight(self):
        return W.GAMMA * 0.5 * W.H * (W._daylight_x(_BETA) - W.CREST)

    def test_a_lens_of_the_same_weight_changes_nothing(self):
        from ogr_api import Workspace
        ws = Workspace()
        try:
            lens, _area = _aligned_lens()
            ref = _closed_form(self._soil_weight())
            for method in ("spencer", "janbu_simplified"):
                bare = _fos(ws, _wedge_with_lens(ws, None, None), method)
                same = _fos(ws, _wedge_with_lens(ws, lens, W.GAMMA), method)
                assert same == bare, (method, same, bare)
                assert abs(same / ref - 1) < _REL, (method, same, ref)
        finally:
            ws.shutdown()

    def test_a_heavier_lens_is_the_closed_form_of_its_weight(self):
        from ogr_api import Workspace
        ws = Workspace()
        try:
            gamma_lens = 25.0
            lens, area = _aligned_lens()
            weight = self._soil_weight() + (gamma_lens - W.GAMMA) * area
            ref = _closed_form(weight)
            pid = _wedge_with_lens(ws, lens, gamma_lens)
            for method in ("spencer", "janbu_simplified"):
                f = _fos(ws, pid, method)
                assert abs(f / ref - 1) < _REL, (method, f, ref)
            # and it moved: the lens is read, not painted over
            assert abs(ref / _closed_form(self._soil_weight()) - 1) > 1e-3
        finally:
            ws.shutdown()

    def test_an_unaligned_lens_stays_in_the_slice_band(self):
        # Each vertical edge of the lens inside a slice is weighed by the
        # slice's centre column, so the lens weight is off by at most
        # (γ₂ − γ₁)·t·b/2 per edge; F falls as W grows.
        from ogr_api import Workspace
        ws = Workspace()
        try:
            gamma_lens, n = 25.0, 51
            lens, area = _aligned_lens()
            t = lens[2][1] - lens[0][1]
            b = (W._daylight_x(_BETA) - W.TOE) / n
            weight = self._soil_weight() + (gamma_lens - W.GAMMA) * area
            band = (gamma_lens - W.GAMMA) * t * b
            lo, hi = _closed_form(weight + band), _closed_form(weight - band)
            pid = _wedge_with_lens(ws, lens, gamma_lens, num_slices=n)
            f = _fos(ws, pid, "spencer")
            assert lo * (1 - _REL) <= f <= hi * (1 + _REL), (f, lo, hi)
        finally:
            ws.shutdown()


# ======================================================================
class TestPainting:
    _SOIL = {"model": "mohr_coulomb",
             "params": {"cohesion": 3.0, "friction_angle": 19.6}}
    _WEAK = {"model": "mohr_coulomb",
             "params": {"cohesion": 0.5, "friction_angle": 5.0}}

    def _model(self, ws):
        from ogr_api import call
        pid = call(ws, "project_new", name="Lens")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "material_boundaries": [{"points": [[40, 24], [56, 24],
                                                [56, 29], [40, 29]],
                                     "closed": True}],
            "materials": [{"name": "Soil", "strength": self._SOIL},
                          {"name": "Weak", "strength": self._WEAK}]})
        return pid

    def test_the_lens_and_its_surroundings_are_painted_apart(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            for order in (("Soil", "Weak"), ("Weak", "Soil")):
                pid = self._model(ws)
                at = {"Soil": (60, 32), "Weak": (48, 26.5)}
                for name in order:
                    call(ws, "material_assign", project_id=pid,
                         material=name, x=at[name][0], y=at[name][1])
                p = ws.get(pid).project
                assert p.material_at(48, 26.5).name == "Weak", order
                assert p.material_at(60, 32).name == "Soil", order
                assert p.material_at(25, 22).name == "Soil", order
                regs = call(ws, "project_summary", project_id=pid)["regions"]
                assert sorted(r["area"] for r in regs) == [80.0, 470.0]
                assert all(r["how"] == "assigned" for r in regs)
        finally:
            ws.shutdown()

    def test_a_piece_of_a_split_lens_keeps_the_lens_material(self):
        # The footprint of the region AROUND the lens carries the hole, so
        # the unpainted half of a lens split later inherits from the lens,
        # not from the surroundings painted after it.
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = self._model(ws)
            call(ws, "material_assign", project_id=pid, material="Weak",
                 x=44, y=26.5)
            call(ws, "material_assign", project_id=pid, material="Soil",
                 x=60, y=32)
            call(ws, "boundary_add", project_id=pid, type="material",
                 points=[[48, 24], [48, 29]])
            p = ws.get(pid).project
            assert p.material_at(44, 26.5).name == "Weak"
            assert p.material_at(52, 26.5).name == "Weak"
            assert p.material_at(60, 32).name == "Soil"
        finally:
            ws.shutdown()


# ======================================================================
class TestFiniteElements:
    L, H, K = 20.0, 10.0, 1.0e-5
    H0, H1 = 10.0, 4.0

    def _regions(self):
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, self.L, self.H),
                        [_b(_box(8, 3, 12, 6), B.MATERIAL, True)])
        for r in regs:
            r.material_id = "lens" if r.area < 20 else "m"
        return regs

    def test_the_lens_is_meshed_once(self):
        from ogr_fem2d.mesh import generate_mesh
        mesh = generate_mesh(self._regions(), target_size=1.0)

        def area(e):
            a, b, c = (mesh.nodes[i] for i in e.nodes)
            return 0.5 * abs((b.x - a.x) * (c.y - a.y)
                             - (c.x - a.x) * (b.y - a.y))
        assert _close(sum(area(e) for e in mesh.elements), self.L * self.H)
        assert _close(sum(area(e) for e in mesh.elements
                          if e.material_id == "lens"), 12.0)
        inner = [i for i in mesh.boundary_node_ids()
                 if 1e-6 < mesh.nodes[i].x < self.L - 1e-6
                 and 1e-6 < mesh.nodes[i].y < self.H - 1e-6]
        assert not inner, "lens outline counted as model boundary"

    def test_confined_flow_through_the_lens_is_darcy(self):
        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.mesh import generate_mesh
        from ogr_fem2d.solvers import (BCType, SeepageBoundaryConditions,
                                       SeepageSolver)
        mesh = generate_mesh(self._regions(), target_size=1.0)
        k = HydraulicProperties(ks=self.K)
        s = SeepageSolver(mesh, {"m": k, "lens": k})
        bc = SeepageBoundaryConditions()
        # 1e-6: the regions are snap-rounded (grid 2.2e-7 m here), so a
        # corner node may sit at x = 19.99999998.
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-6:
                bc.add_node(nid, BCType.TOTAL_HEAD, self.H0)
            elif abs(nd.x - self.L) < 1e-6:
                bc.add_node(nid, BCType.TOTAL_HEAD, self.H1)
        r = s.solve(bc)
        assert r.ok
        for i, nd in enumerate(mesh.nodes):
            exact = self.H0 + (self.H1 - self.H0) * nd.x / self.L
            assert abs(r.total_head[i] - exact) < 1e-6, (i, nd.x, nd.y)
        q = abs(s.flux_through_segment(r, 10.0, 0.0, 10.0, self.H))
        darcy = self.K * (self.H0 - self.H1) / self.L * self.H
        assert abs(q - darcy) / darcy < 1e-6, (q, darcy)

    def test_the_project_mesh_takes_the_resolved_materials(self):
        from ogr_api import Workspace, call
        from ogr_fem2d.mesh.generator import generate_mesh_for_project
        ws = Workspace()
        try:
            pid = TestPainting()._model(ws)
            call(ws, "material_assign", project_id=pid, material="Soil",
                 x=60, y=32)
            call(ws, "material_assign", project_id=pid, material="Weak",
                 x=48, y=26.5)
            p = ws.get(pid).project
            mesh = generate_mesh_for_project(p, target_size=1.0)
            weak = p.materials[1].id
            for e in mesh.elements:
                cx = sum(mesh.nodes[i].x for i in e.nodes) / 3
                cy = sum(mesh.nodes[i].y for i in e.nodes) / 3
                inside = 40 < cx < 56 and 24 < cy < 29
                assert (e.material_id == weak) == inside, (cx, cy)
        finally:
            ws.shutdown()


# ======================================================================
class TestTheOtherReaders:
    def test_the_canvas_leaves_the_hole_unpainted(self):
        try:
            from PySide6.QtCore import QPointF
            from PySide6.QtWidgets import QApplication
        except ImportError:  # pragma: no cover
            return
        QApplication.instance() or QApplication([])
        from ogr_core.geometry import BoundaryType as B
        from ogr_gui.canvas.canvas_view import _region_to_item
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 15), B.MATERIAL, True)])
        outer = max(regs, key=lambda r: r.area)
        path = _region_to_item(outer, None).path()
        assert not path.contains(QPointF(25, 12.5))
        assert path.contains(QPointF(5, 5))

    def test_the_data_tip_names_the_resolved_material(self):
        from ogr_api import Workspace, call
        from ogr_gui.data_tips import tip_at
        ws = Workspace()
        try:
            pid = TestPainting()._model(ws)
            call(ws, "material_assign", project_id=pid, material="Weak",
                 x=48, y=26.5)
            call(ws, "material_assign", project_id=pid, material="Soil",
                 x=60, y=32)
            p = ws.get(pid).project
            assert "Weak" in tip_at(p, 48, 26.5, radius=0.01)
            tip = tip_at(p, 60, 32, radius=0.01)
            # a painted region used to read "no material assigned"
            assert "Soil" in tip and "no material" not in tip
        finally:
            ws.shutdown()

    def test_the_png_leaves_the_hole_unpainted(self):
        # Drawn by Agg, the renderer of ``render_png``, and read back:
        # ``Path.contains_point`` does not apply a fill rule to a compound
        # path, so only the pixels say what the image shows.
        import numpy as np
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from matplotlib.patches import PathPatch

        from ogr_api.render import _ring_path
        from ogr_core.geometry import BoundaryType as B
        regs = _regions(_box(0, 0, 50, 30),
                        [_b(_box(20, 10, 30, 15), B.MATERIAL, True)])
        outer = max(regs, key=lambda r: r.area)
        path = _ring_path([(v.x, v.y) for v in outer.polygon.vertices],
                          outer.holes)
        fig = Figure(figsize=(5, 3), dpi=100)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 50)
        ax.set_ylim(0, 30)
        ax.axis("off")
        ax.add_patch(PathPatch(path, facecolor="black", edgecolor="none"))
        canvas.draw()
        img = np.asarray(canvas.buffer_rgba())

        def pixel(x, y):
            px, py = ax.transData.transform((x, y))
            return tuple(img[int(img.shape[0] - py), int(px)][:3])
        assert pixel(25, 12.5) == (255, 255, 255)        # the hole
        assert pixel(5, 5) == (0, 0, 0)                  # the region


class TestConvertingToAMaterialBoundary:
    def test_an_open_line_stays_open(self):
        from ogr_core.geometry import BoundaryType as B
        from ogr_core.geometry.transforms import convert_boundary
        wt = _b([(0, 8), (20, 9), (50, 8)], B.WATER_TABLE)
        mat = convert_boundary(wt, B.MATERIAL)
        assert mat.polyline.closed is False
        lens = _b(_box(20, 10, 30, 15), B.MATERIAL, True)
        assert convert_boundary(lens, B.MATERIAL).polyline.closed is True


class TestTheOperationsTakeALens:
    def test_open_rings_and_degenerate_lenses_are_refused(self):
        from ogr_api import Conflict, InvalidArgument, Workspace, call
        ws = Workspace()
        try:
            pid = TestPainting()._model(ws)
            _raised(Conflict, lambda: call(
                ws, "boundary_add", project_id=pid, type="material",
                points=[[42, 21], [46, 21], [46, 22], [42, 21]]))
            _raised(InvalidArgument, lambda: call(
                ws, "boundary_add", project_id=pid, type="material",
                closed=True, points=[[42, 21], [46, 21], [42, 21]]))
            _raised(InvalidArgument, lambda: call(
                ws, "boundary_add", project_id=pid, type="water_table",
                closed=True, points=[[20, 22], [70, 22], [70, 23]]))
            out = call(ws, "boundary_add", project_id=pid, type="material",
                       closed=True,
                       points=[[42, 21], [46, 21], [46, 22], [42, 22],
                               [42, 21]])
            assert out["boundary"]["closed"] is True
            assert out["boundary"]["n_vertices"] == 4    # no closing copy
        finally:
            ws.shutdown()

    def test_a_closed_annotation_becomes_a_lens(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = TestPainting()._model(ws)
            rect = call(ws, "annotation_set", project_id=pid,
                        kind="rectangle",
                        points_xy=[[22, 21], [26, 23]])["annotation"]
            out = call(ws, "annotation_to_boundary", project_id=pid,
                       annotation=rect["id"], type="material")
            assert out["boundary"]["closed"] is True
            assert out["boundary"]["n_vertices"] == 4
            areas = sorted(r["area"] for r in call(
                ws, "project_summary", project_id=pid)["regions"])
            assert areas == [8.0, 80.0, 462.0]
        finally:
            ws.shutdown()
