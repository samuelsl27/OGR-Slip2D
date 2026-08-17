# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.17 — Grid Search reimplemented per Slide2.

Key Slide conventions verified:
  - grid_nx / grid_ny are the number of INTERVALS → (nx+1)·(ny+1) centres
  - radius_increment is the number of INTERVALS between r_min and r_max
    → (radius_increment + 1) circles per centre
  - per-centre r_min/r_max bracket from the slope surface
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
    p = Project("grid")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=8, friction_angle=20))]
    return p


class TestGridSearchV117:
    def test_interval_convention_centres(self):
        """grid_nx=n intervals → n+1 distinct centre x-coordinates."""
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _slope()
        s = GridSearch(method=BishopSimplified(),
            grid_x=(25.0, 40.0), grid_y=(20.0, 35.0),
            grid_nx=4, grid_ny=4, radius_increment=5, min_radius=8.0,
            num_slices=15)
        r = s.run(p)
        centres = set()
        for ev in r.evaluations:
            sd = ev.surface.to_dict()
            centres.add((round(sd["centre_x"], 2), round(sd["centre_y"], 2)))
        xs = {c[0] for c in centres}
        ys = {c[1] for c in centres}
        # 4 intervals → 5 distinct values on each axis
        assert len(xs) == 5, f"expected 5 centre-x, got {len(xs)}"
        assert len(ys) == 5, f"expected 5 centre-y, got {len(ys)}"

    def test_circles_per_centre(self):
        """radius_increment=k → at most (k+1) circles per centre."""
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _slope()
        k = 6
        s = GridSearch(method=BishopSimplified(),
            grid_x=(30.0, 35.0), grid_y=(25.0, 30.0),
            grid_nx=1, grid_ny=1, radius_increment=k, min_radius=8.0,
            num_slices=15)
        r = s.run(p)
        # 2x2 centres, each ≤ k+1 circles
        per_centre = {}
        for ev in r.evaluations:
            sd = ev.surface.to_dict()
            key = (round(sd["centre_x"], 2), round(sd["centre_y"], 2))
            per_centre[key] = per_centre.get(key, 0) + 1
        for key, n in per_centre.items():
            assert n <= k + 1, f"centre {key} has {n} circles > {k+1}"

    def test_finds_critical(self):
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _slope()
        s = GridSearch(method=BishopSimplified(),
            grid_x=(20, 45), grid_y=(15, 40),
            grid_nx=15, grid_ny=15, radius_increment=12, min_radius=6.0,
            num_slices=25, min_area=0.5)
        r = s.run(p)
        assert r.critical is not None
        # Known reference FoS ≈ 1.11 for this slope
        assert 1.05 < r.critical.fos < 1.20, (
            f"FoS {r.critical.fos:.3f} out of expected band"
        )

    def test_circles_daylight_on_slope(self):
        """Generated circles should reach the slope surface, not float
        above it or engulf the whole model. Check the critical circle's
        radius is sensible relative to the slope height."""
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _slope()
        s = GridSearch(method=BishopSimplified(),
            grid_x=(20, 45), grid_y=(15, 40),
            grid_nx=12, grid_ny=12, radius_increment=10, min_radius=6.0,
            num_slices=25, min_area=0.5)
        r = s.run(p)
        c = r.critical.surface
        # Slope height is 12 m; a sensible critical radius is within a
        # few slope-heights, not the whole-model diagonal.
        assert 8.0 < c.radius < 50.0
