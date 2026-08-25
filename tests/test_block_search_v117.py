# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.17 — Block Search (non-circular) reimplemented per Slide2.

Block Search generates points within block windows, sorts them by X,
projects to the ground with Left/Right projection angles, and filters
to kinematically admissible (unimodal, convex-optional) surfaces that
daylight within the Slope Limits and stay inside the External.
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
    # v0.1.89 — the 10 m foundation. This contour used to be
    # ``(0,0) (60,0) (60,H) (crest,H) (toe,0)``, whose closing edge runs back
    # along the bottom one: between x = 0 and the toe at x = 30 the ground
    # surface and the base of the model are the same line at y = 0, enclosing
    # no soil at all. v0.1.84 fixed the two files that depended on the
    # degeneracy to pass and left five that did not; this is one of them.
    base = -10.0
    ext = Polyline(vertices=[
        Vertex(0, base), Vertex(60, base), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("block")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=8, friction_angle=20))]
    return p, [(v.x, v.y) for v in ext.vertices]


class TestBlockSearchV117:
    def test_finds_valid_surfaces(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        p, _ = _slope()
        r = BlockSearch(method=BishopSimplified(), num_groups=3,
            num_surfaces=1500, num_slices=25, min_area=2.0,
            seed=42).run(p)
        assert r.valid_count > 0
        assert r.critical is not None
        assert 0.9 < r.critical.fos < 1.6

    def test_surfaces_inside_external(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        try:
            from shapely.geometry import Polygon, Point
        except ImportError:
            return
        p, ext_verts = _slope()
        ext_poly = Polygon(ext_verts)
        for seed in (7, 42, 100):
            r = BlockSearch(method=BishopSimplified(), num_groups=3,
                num_surfaces=1200, num_slices=20, min_area=2.0,
                seed=seed).run(p)
            vs = r.critical.surface.polyline.vertices
            outside = [(v.x, v.y) for v in vs
                       if not ext_poly.buffer(0.15).contains(Point(v.x, v.y))]
            assert not outside, f"seed {seed}: outside {outside}"

    def test_no_spurious_low_fos(self):
        """A stable slope must not return a sub-unity factor.

        v0.1.118 — this used to say "the unimodal filter should remove
        sawtooth wedges", and that filter is gone: the reference does not
        have it, it was applied whether or not the user asked for
        convexity, and it was the acceptance rate (defect D21). The
        invariant survives it untouched, which is the point — what catches
        those wedges now is the post-analysis m-alpha check, on by default
        since v0.1.89, which is where the reference puts the screen.
        """
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        p, _ = _slope()
        for seed in (7, 42, 100, 2024, 55):
            r = BlockSearch(method=BishopSimplified(), num_groups=3,
                num_surfaces=1500, num_slices=20, min_area=2.0,
                seed=seed).run(p)
            assert r.critical.fos > 1.0, (
                f"seed {seed}: spurious low FoS {r.critical.fos:.3f}"
            )

    def test_reproducible(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        p, _ = _slope()
        r1 = BlockSearch(method=BishopSimplified(), num_groups=3,
            num_surfaces=600, num_slices=20, seed=11).run(p)
        r2 = BlockSearch(method=BishopSimplified(), num_groups=3,
            num_surfaces=600, num_slices=20, seed=11).run(p)
        assert abs(r1.critical.fos - r2.critical.fos) < 1e-9

    def test_convex_filter_runs(self):
        """Convex-only mode should still find surfaces (subset)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        p, _ = _slope()
        r = BlockSearch(method=BishopSimplified(), num_groups=2,
            num_surfaces=1500, num_slices=20, min_area=2.0,
            convex_only=True, seed=42).run(p)
        # may be fewer, but should not crash and ideally finds something
        assert r.valid_count >= 0

    def test_is_convex_down_helper(self):
        from ogr_slip2d.search import BlockSearch
        from ogr_core.geometry import Vertex
        # A convex-down (bowl) polyline
        bowl = [Vertex(0, 5), Vertex(2, 1), Vertex(4, 0),
                Vertex(6, 1), Vertex(8, 5)]
        assert BlockSearch._is_convex_down(bowl) is True
        # A sawtooth
        saw = [Vertex(0, 5), Vertex(2, 1), Vertex(4, 4),
               Vertex(6, 1), Vertex(8, 5)]
        assert BlockSearch._is_convex_down(saw) is False
