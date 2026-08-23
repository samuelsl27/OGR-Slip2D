# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.15 — kinematically-admissible non-circular surfaces.

The old Path Search / Block Search produced "impossible" wavy surfaces
(interior vertices rising above the entry-exit chord, surfaces that a
real sliding mass cannot follow). v0.1.15 rewrites Path Search per the
Slide2 algorithm (Greco 1996) with concave-up admissibility, and adds
an admissibility filter to Block Search.
"""
from __future__ import annotations

from ogr_slip2d.optimize import OptimizeSettings
import math


def _slope_project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    # v0.1.89 — 10 m foundation; see the module docstring.
    base = -10.0
    ext = Polyline(vertices=[
        Vertex(0, base), Vertex(60, base), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("nc")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=18,
        strength=MohrCoulomb(cohesion=8, friction_angle=20))]
    return p


def _is_concave_up(verts) -> bool:
    """A surface is admissible if no interior vertex rises above the
    chord between the first and last vertex."""
    if len(verts) < 3:
        return True
    x0, y0 = verts[0].x, verts[0].y
    xn, yn = verts[-1].x, verts[-1].y
    if abs(xn - x0) < 1e-9:
        return True
    for v in verts[1:-1]:
        t = (v.x - x0) / (xn - x0)
        chord = y0 + t * (yn - y0)
        if v.y > chord + 1e-3:
            return False
    return True


#: v0.1.104 — ``optimize=True`` used to switch on a random walk private
#: to Path Search, run over its best five surfaces for 200 iterations.
#: There is one optimiser now, shared by every non-circular search and
#: driven by the *Optimize Surfaces* checkbox; this is what asking for it
#: from code looks like. The budget matches what these tests used to get.
_OPTIMISE = OptimizeSettings(enabled=True, max_iterations=200)


# ======================================================================
class TestPathSearch:
    def test_path_search_finds_valid_surface(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _slope_project()
        search = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=200, num_slices=25, optimize=_OPTIMISE, seed=1)
        r = search.run(p)
        assert r.valid_count > 0, "Path Search found no valid surfaces"
        assert r.critical is not None
        assert 0.5 < r.critical.fos < 2.0, (
            f"Critical FoS {r.critical.fos} out of plausible range"
        )

    def test_critical_surface_is_admissible(self):
        """The critical surface must be concave-up (no humps)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _slope_project()
        search = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=200, num_slices=25, optimize=_OPTIMISE, seed=7)
        r = search.run(p)
        vs = r.critical.surface.polyline.vertices
        assert _is_concave_up(vs), (
            "Critical surface is not concave-up (kinematically "
            "impossible shape)"
        )

    def test_surface_x_monotonic(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _slope_project()
        search = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=150, num_slices=25, seed=3)
        r = search.run(p)
        vs = r.critical.surface.polyline.vertices
        xs = [v.x for v in vs]
        assert all(xs[i] < xs[i + 1] for i in range(len(xs) - 1)), (
            "Surface vertices not x-monotonic"
        )

    def test_pseudo_random_reproducible(self):
        """Same seed → same critical FoS (Slide's Pseudo-Random mode)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _slope_project()
        r1 = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=100, num_slices=20, seed=99).run(p)
        r2 = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=100, num_slices=20, seed=99).run(p)
        assert abs(r1.critical.fos - r2.critical.fos) < 1e-9, (
            "Same seed should give identical results"
        )

    def test_optimization_lowers_fos(self):
        """Surface Altering Optimization should not INCREASE the FoS."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _slope_project()
        r_no = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=200, num_slices=20, seed=5).run(p)
        r_opt = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=200, num_slices=20, optimize=_OPTIMISE, seed=5).run(p)
        # Optimized run should find FoS ≤ non-optimized (same seed,
        # extra optimization can only help or stay equal)
        assert r_opt.critical.fos <= r_no.critical.fos + 0.05


# ======================================================================
class TestBlockSearchAdmissibility:
    def test_block_surfaces_admissible(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        p = _slope_project()
        search = BlockSearch(method=BishopSimplified(), num_groups=3,
            num_surfaces=300, num_slices=20)
        r = search.run(p)
        assert r.valid_count > 0
        vs = r.critical.surface.polyline.vertices
        assert _is_concave_up(vs), (
            "Block Search critical surface is not admissible"
        )


# ======================================================================
# v0.1.16 — surfaces must stay inside the External boundary
# ======================================================================
class TestSurfacesInsideExternal:
    def _slope_descending_right(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        ext_verts = [Vertex(0, 0), Vertex(0, 20), Vertex(20, 20),
                     Vertex(40, 5), Vertex(60, 5), Vertex(60, 0)]
        ext = Polyline(vertices=ext_verts, closed=True)
        ext.ensure_ccw()
        p = Project("inside")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="S", unit_weight=19,
            strength=MohrCoulomb(cohesion=12, friction_angle=22))]
        return p, ext_verts

    def test_ground_profile_includes_toe(self):
        """The ground profile must follow the real upper contour,
        including the toe vertex (not the convex hull)."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.search import PathSearch
        import math
        H = 12.0
        beta = math.radians(30.96)
        toe = 30.0
        crest = toe + H / math.tan(beta)
        # v0.1.89 — 10 m foundation; see the module docstring. Without
        # it the stretch from x = 0 to the toe encloses no soil.
        ext_verts = [Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
                     Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0)]
        top = PathSearch._ground_profile(ext_verts)
        # The toe (30, 0) must be present — the convex hull dropped it
        xs = [round(v.x, 1) for v in top]
        assert 30.0 in xs, f"Toe x=30 missing from ground profile {xs}"

    def test_critical_surface_inside_external(self):
        """Every vertex of the critical non-circular surface must lie
        inside the External polygon (v0.1.16 bug fix)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        try:
            from shapely.geometry import Polygon, Point
        except ImportError:
            return  # skip without shapely
        p, ext_verts = self._slope_descending_right()
        ext_poly = Polygon([(v.x, v.y) for v in ext_verts])
        for seed in (7, 42, 100):
            search = PathSearch(method=BishopSimplified(), num_vertices=8,
                num_paths=300, num_slices=20, optimize=_OPTIMISE, seed=seed)
            r = search.run(p)
            assert r.critical is not None, f"seed {seed}: no critical"
            vs = r.critical.surface.polyline.vertices
            outside = [
                (v.x, v.y) for v in vs
                if not ext_poly.buffer(0.1).contains(Point(v.x, v.y))
            ]
            assert not outside, (
                f"seed {seed}: vertices outside External: {outside}"
            )

    def test_standard_slope_surface_inside(self):
        """Same check on the canonical toe-at-30 slope."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        import math
        try:
            from shapely.geometry import Polygon, Point
        except ImportError:
            return
        H = 12.0
        beta = math.radians(30.96)
        toe = 30.0
        crest = toe + H / math.tan(beta)
        # v0.1.89 — 10 m foundation; see the module docstring. Without
        # it the stretch from x = 0 to the toe encloses no soil.
        ext_verts = [Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
                     Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0)]
        ext = Polyline(vertices=ext_verts, closed=True)
        ext.ensure_ccw()
        p = Project("std")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="S", unit_weight=18,
            strength=MohrCoulomb(cohesion=8, friction_angle=20))]
        ext_poly = Polygon([(v.x, v.y) for v in ext_verts])
        search = PathSearch(method=BishopSimplified(), num_vertices=8,
            num_paths=300, num_slices=25, optimize=_OPTIMISE, seed=42)
        r = search.run(p)
        assert r.critical is not None
        vs = r.critical.surface.polyline.vertices
        outside = [
            (v.x, v.y) for v in vs
            if not ext_poly.buffer(0.1).contains(Point(v.x, v.y))
        ]
        assert not outside, f"vertices outside External: {outside}"


# ======================================================================
# v0.1.17 — XSTABL Path Search method-specific tests
# ======================================================================
class TestPathSearchXSTABL:
    def _slope(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        import math
        H = 12.0
        beta = math.radians(30.96)
        toe = 30.0
        crest = toe + H / math.tan(beta)
        # v0.1.89 — 10 m foundation; see the module docstring.
        ext = Polyline(vertices=[
            Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
            Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("xstabl")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="S", unit_weight=18,
            strength=MohrCoulomb(cohesion=8, friction_angle=20))]
        return p

    def test_fos_near_circular_reference(self):
        """A non-circular Path Search FoS should be close to (and
        typically ≤) the circular Bishop reference for the same slope."""
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.search import PathSearch
        p = self._slope()
        gs = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 35), grid_nx=8, grid_ny=8,
            radius_increment=3.0, min_radius=8.0, num_slices=25,
            min_area=0.5)
        ref = gs.run(p).critical.fos
        r = PathSearch(method=BishopSimplified(), num_paths=400,
            num_slices=25, optimize=_OPTIMISE, seed=100).run(p)
        assert r.critical is not None
        # Non-circular should be within a sensible band of the circular
        assert r.critical.fos <= ref + 0.15, (
            f"Path FoS {r.critical.fos:.3f} >> circular {ref:.3f}"
        )
        assert r.critical.fos > 0.7

    def test_segment_length_auto(self):
        """With segment_length=None the search auto-picks ≈0.3H and
        still finds valid surfaces."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = self._slope()
        r = PathSearch(method=BishopSimplified(), num_paths=300,
            num_slices=25, segment_length=None,
            seed=5).run(p)
        assert r.valid_count > 0

    def test_initial_angle_window_respected(self):
        """The first segment descends (negative angle) — the surface's
        second vertex is below the first."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = self._slope()
        r = PathSearch(method=BishopSimplified(), num_paths=300,
            num_slices=25, seed=11).run(p)
        vs = r.critical.surface.polyline.vertices
        # Entry is at the toe side; the surface must dip down then rise.
        ymin = min(v.y for v in vs)
        assert ymin < vs[0].y or ymin < vs[-1].y, (
            "Surface should dip below at least one endpoint"
        )

    def test_validity_ratio_reasonable(self):
        """The XSTABL generator should produce a non-trivial fraction of
        valid surfaces (sanity check, not a tight bound)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = self._slope()
        r = PathSearch(method=BishopSimplified(), num_paths=400,
            num_slices=25, seed=100).run(p)
        total = r.valid_count + r.invalid_count
        assert total > 0
        assert r.valid_count / total > 0.10, (
            f"Validity ratio too low: {r.valid_count}/{total}"
        )
