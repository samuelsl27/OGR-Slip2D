# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.17 — Slope Search (circular) reimplemented per Slide2.

The Slope Search generates circles from two ground-surface points
(within the Slope Limits) plus an Initial Angle at Toe, then refines
the best candidates locally. It should converge onto the same critical
circle the Grid Search finds.
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
    p = Project("slope")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=8, friction_angle=20))]
    return p


class TestSlopeSearch:
    def test_finds_valid_circles(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch
        p = _slope()
        r = SlopeSearch(method=BishopSimplified(), num_surfaces=800,
            num_slices=25, seed=42).run(p)
        assert r.valid_count > 0
        assert r.critical is not None
        assert 0.7 < r.critical.fos < 2.0

    def test_agrees_with_grid_search(self):
        """Slope Search should find essentially the same critical FoS as
        the Grid Search (within ~5%)."""
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.search import SlopeSearch
        p = _slope()
        grid = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 40), grid_nx=12, grid_ny=12,
            radius_increment=4.0, min_radius=8.0, num_slices=25,
            min_area=0.5).run(p)
        slope = SlopeSearch(method=BishopSimplified(),
            num_surfaces=1500, num_slices=25, seed=42).run(p)
        assert abs(slope.critical.fos - grid.critical.fos) < 0.05 * grid.critical.fos, (
            f"Slope {slope.critical.fos:.3f} vs Grid {grid.critical.fos:.3f}"
        )

    def test_critical_circle_at_least_as_good_as_grid(self):
        """The Slope Search must find a critical surface at least as
        critical as a (necessarily coarse) Grid Search on the same model.

        v0.1.24 — this test previously asserted that the Slope Search
        critical CENTRE lay within 6 units of the Grid Search critical
        centre. That premise was wrong: the FoS surface has a broad flat
        valley, so many (centre, radius) pairs give an almost identical
        FoS, and the coarse reference grid (12×12, Δr = 4) is not ground
        truth — here it returns FoS 1.157 while the Slope Search finds
        1.103. Penalising the better surface for sitting at a different
        centre inverted the invariant. What actually matters is search
        quality, which is what we assert now (the FoS-agreement test
        above still bounds the two results to within 5 %).
        """
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.search import SlopeSearch
        p = _slope()
        grid = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 40), grid_nx=12, grid_ny=12,
            radius_increment=4.0, min_radius=8.0, num_slices=25,
            min_area=0.5).run(p)
        slope = SlopeSearch(method=BishopSimplified(),
            num_surfaces=1500, num_slices=25, seed=42).run(p)
        assert slope.critical is not None and grid.critical is not None
        # At least as critical as the coarse grid (small tolerance for
        # the grid occasionally landing right on a good circle).
        assert slope.critical.fos <= grid.critical.fos * 1.02, (
            f"Slope {slope.critical.fos:.4f} worse than "
            f"Grid {grid.critical.fos:.4f}"
        )
        # And the circle must sit in the slope's own neighbourhood.
        sc = slope.critical.surface
        assert 10.0 <= sc.centre_x <= 70.0, sc.centre_x
        assert 10.0 <= sc.centre_y <= 50.0, sc.centre_y

    def test_reproducible_with_seed(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch
        p = _slope()
        r1 = SlopeSearch(method=BishopSimplified(), num_surfaces=500,
            num_slices=20, seed=7).run(p)
        r2 = SlopeSearch(method=BishopSimplified(), num_surfaces=500,
            num_slices=20, seed=7).run(p)
        assert abs(r1.critical.fos - r2.critical.fos) < 1e-9

    def test_circle_from_point_tangent_point(self):
        """The 3-point/tangent circle construction is geometrically
        correct: the circle passes through both points and its centre
        is above them."""
        from ogr_slip2d.search import SlopeSearch
        # Point 1 at (0,0), tangent horizontal (angle 0), point 2 at (10,0)
        # → centre on the vertical through midpoint, above.
        res = SlopeSearch._circle_from_point_tangent_point(
            0.0, 0.0, 0.0, 10.0, 0.0, True)
        # Horizontal tangent + symmetric points → degenerate (centre at
        # infinity) → should handle gracefully (None or huge R)
        # Use a descending tangent instead:
        res = SlopeSearch._circle_from_point_tangent_point(
            0.0, 5.0, math.radians(-30), 10.0, 5.0, True)
        assert res is not None
        cx, cy, r = res
        # Both points are equidistant from centre
        d1 = math.hypot(cx - 0.0, cy - 5.0)
        d2 = math.hypot(cx - 10.0, cy - 5.0)
        assert abs(d1 - r) < 1e-6 and abs(d2 - r) < 1e-6
        assert cy >= 5.0  # centre above the surface points
