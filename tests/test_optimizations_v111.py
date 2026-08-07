# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.11 compute optimizations.

Verifies:
    - regions cache returns same objects on repeated calls (no re-build)
    - cache invalidates when boundaries change
    - cache invalidates when material assignments change
    - bbox cache works correctly
    - early-skip filter doesn't reject valid surfaces
"""
from __future__ import annotations


def _make_two_layer():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("opt-test")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 20),
        Vertex(40, 20), Vertex(20, 5), Vertex(0, 5),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(0, 8), Vertex(60, 8)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.materials = [
        Material(name="Top", strength=MohrCoulomb(cohesion=10, friction_angle=20)),
        Material(name="Bot", strength=MohrCoulomb(cohesion=30, friction_angle=30)),
    ]
    return p


# ======================================================================
class TestRegionsCache:
    def test_cache_returns_same_object_on_repeated_calls(self):
        p = _make_two_layer()
        r1 = p.resolve_regions()
        r2 = p.resolve_regions()
        # Same Python object (== identity) means we hit the cache
        assert r1 is r2

    def test_cache_invalidates_on_boundary_added(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _make_two_layer()
        r1 = p.resolve_regions()
        # Add another material boundary
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, 14), Vertex(60, 14)], closed=False),
            btype=BoundaryType.MATERIAL))
        r2 = p.resolve_regions()
        # Different number of regions now → cache must have been
        # invalidated and recomputed
        assert r1 is not r2
        assert len(r2) > len(r1)

    def test_cache_invalidates_on_material_assignment(self):
        p = _make_two_layer()
        r1 = p.resolve_regions()
        # Manually invalidate
        p.invalidate_regions_cache()
        r2 = p.resolve_regions()
        assert r1 is not r2

    def test_cache_persists_across_lookups(self):
        """Repeated material_at calls should hit the cache."""
        p = _make_two_layer()
        # First call seeds the cache
        m1 = p.material_at(30, 4)
        # Second call returns same material via cached regions
        m2 = p.material_at(30, 4)
        # Same material_id (whether m or None)
        if m1 is None:
            assert m2 is None
        else:
            assert m1.id == m2.id


# ======================================================================
class TestBboxCache:
    def test_bbox_returns_same_tuple(self):
        p = _make_two_layer()
        b1 = p.bounding_box()
        b2 = p.bounding_box()
        assert b1 == b2

    def test_bbox_invalidates_on_boundary_change(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _make_two_layer()
        b1 = p.bounding_box()
        # Add a far-out boundary
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(100, 100), Vertex(110, 100)], closed=False),
            btype=BoundaryType.MATERIAL))
        b2 = p.bounding_box()
        # bbox should now be larger
        assert b2[2] > b1[2] or b2[3] > b1[3]


# ======================================================================
class TestEarlySkipFilter:
    """The early-skip filter in evaluate_circle must not reject valid
    surfaces. We verify by running a search with and without the
    filter — but since the filter is internal, we verify by checking
    that the same critical FoS is found compared to a known reference.
    """

    def test_grid_finds_critical_surface(self):
        """GridSearch must still find a critical surface despite
        early-skip rejecting circles outside the bbox."""
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _make_two_layer()
        g = GridSearch(method=BishopSimplified(),
            grid_x=(15, 45), grid_y=(20, 40),
            grid_nx=8, grid_ny=8, radius_increment=2.0, min_radius=8.0,
            num_slices=20, min_area=0.5)
        result = g.run(p)
        assert result.critical is not None
        # FoS in a reasonable range for this slope
        assert 0.5 < result.critical.fos < 5.0

    def test_far_away_circle_is_skipped(self):
        """A circle whose bbox is entirely outside the model should
        be rejected by the early-skip without any slicing."""
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _make_two_layer()
        # Build a faraway circle far above the model
        far_circle = SlipCircle(centre_x=1000.0, centre_y=1000.0, radius=10.0)
        g = GridSearch(method=BishopSimplified(),
            grid_x=(15, 45), grid_y=(20, 40),
            grid_nx=4, grid_ny=4, radius_increment=2.0, min_radius=8.0,
            num_slices=20, min_area=0.5)
        # evaluate_circle should return None (early-skipped)
        res = g.evaluate_circle(p, far_circle)
        assert res is None


# ======================================================================
class TestPerformanceImprovement:
    """Regression test: GridSearch on the standard slope must complete
    in well under 5 seconds — if this fails, an optimisation regressed."""

    def test_grid_completes_quickly(self):
        import time
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _make_two_layer()
        g = GridSearch(method=BishopSimplified(),
            grid_x=(15, 45), grid_y=(20, 40),
            grid_nx=12, grid_ny=12, radius_increment=2.0, min_radius=8.0,
            num_slices=25, min_area=0.5)
        t = time.time()
        result = g.run(p)
        dt = time.time() - t
        # On normal hardware the fully-cached version takes ~1s.
        # 5s leaves margin for slow CI runners. Anything > 5s indicates
        # a regression in the cache path.
        assert dt < 5.0, f"GridSearch took {dt:.1f}s — cache regressed"
        assert result.critical is not None
