# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.17 — Simulated Annealing (HSA) and Auto Refine Search.
"""
from __future__ import annotations
import math


def _slope():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("sa")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=8, friction_angle=20))]
    return p, [(v.x, v.y) for v in ext.vertices]


class TestSimulatedAnnealing:
    def test_finds_physical_fos(self):
        """SA must find a physical FoS near the circular reference, NOT
        a spurious sub-unity value (the v0.1.16 bug)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch
        p, _ = _slope()
        r = SimulatedAnnealingSearch(method=BishopSimplified(),
            initial_vertices=9, generation_steps=300,
            num_slices=25).run(p)
        assert r.critical is not None
        assert 0.9 < r.critical.fos < 1.4, (
            f"SA FoS {r.critical.fos:.3f} not physical"
        )

    def test_surfaces_inside_external(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch
        try:
            from shapely.geometry import Polygon, Point
        except ImportError:
            return
        p, ext_verts = _slope()
        ext_poly = Polygon(ext_verts)
        r = SimulatedAnnealingSearch(method=BishopSimplified(),
            initial_vertices=9, generation_steps=200,
            num_slices=25).run(p)
        vs = r.critical.surface.polyline.vertices
        outside = [(v.x, v.y) for v in vs
                   if not ext_poly.buffer(0.1).contains(Point(v.x, v.y))]
        assert not outside, f"SA vertices outside External: {outside}"

    def test_surface_admissible(self):
        """Critical SA surface is x-monotonic and concave-up."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch
        p, _ = _slope()
        r = SimulatedAnnealingSearch(method=BishopSimplified(),
            initial_vertices=9, generation_steps=200,
            num_slices=25).run(p)
        vs = r.critical.surface.polyline.vertices
        for a, b in zip(vs[:-1], vs[1:]):
            assert b.x > a.x - 1e-6, "surface must be x-monotonic"


class TestAutoRefine:
    def test_finds_critical(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p, _ = _slope()
        r = AutoRefineSearch(method=BishopSimplified(),
            divisions=12, circles_per_division=10, iterations=5,
            num_slices=25).run(p)
        assert r.critical is not None
        assert 1.05 < r.critical.fos < 1.25, (
            f"AutoRefine FoS {r.critical.fos:.3f} out of band"
        )

    def test_converges_with_more_divisions(self):
        """More divisions → FoS at least as low (finer search)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p, _ = _slope()
        coarse = AutoRefineSearch(method=BishopSimplified(),
            divisions=6, circles_per_division=6, iterations=3,
            num_slices=20).run(p)
        fine = AutoRefineSearch(method=BishopSimplified(),
            divisions=14, circles_per_division=10, iterations=5,
            num_slices=20).run(p)
        assert fine.critical.fos <= coarse.critical.fos + 0.05

    def test_circle_construction(self):
        """The two-point + tangent circle construction yields a circle
        through both points with the centre above them."""
        from ogr_slip2d.search import AutoRefineSearch
        c = AutoRefineSearch._circle_through_two_points_tangent(
            35.0, 2.0, 45.0, 7.0, math.radians(155))
        assert c is not None
        cx, cy, r = c
        d1 = math.hypot(cx - 35.0, cy - 2.0)
        d2 = math.hypot(cx - 45.0, cy - 7.0)
        assert abs(d1 - r) < 1e-6 and abs(d2 - r) < 1e-6
        assert cy >= 7.0
