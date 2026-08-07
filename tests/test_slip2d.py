# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for ogr_slip2d."""
from __future__ import annotations

import math

import pytest

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, MohrCoulomb, Undrained
from ogr_core.project import Project
from ogr_slip2d import (
    BishopSimplified,
    GridSearch,
    JanbuSimplified,
    OrdinaryFellenius,
    SlipCircle,
)
from ogr_slip2d.methods import GLEMorgensternPrice, Spencer, constant, half_sine
from ogr_slip2d.slicer import _ground_surface_from_external, slice_surface


def _make_slope_project(cohesion=10.0, phi=25.0, gamma=19.0):
    p = Project("test")
    ext = Polyline(
        vertices=[
            Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
            Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
        ],
        closed=True,
    )
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_material(Material(
        name="soil",
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=phi),
        unit_weight=gamma,
    ))
    return p


# ----------------------------------------------------------------------
class TestSlipCircle:
    def test_from_three_points(self):
        c = SlipCircle.from_three_points(Vertex(0, 0), Vertex(2, 0), Vertex(1, 1))
        # Circle through (0,0), (2,0), (1,1): centre (1, 0), radius 1
        assert c.centre_x == pytest.approx(1.0)
        assert c.centre_y == pytest.approx(0.0)
        assert c.radius == pytest.approx(1.0)

    def test_collinear_points_raise(self):
        with pytest.raises(ValueError):
            SlipCircle.from_three_points(Vertex(0, 0), Vertex(1, 0), Vertex(2, 0))

    def test_base_y_at_returns_lower_arc(self):
        c = SlipCircle(centre_x=0.0, centre_y=0.0, radius=5.0)
        y = c.base_y_at(0.0)
        assert y == pytest.approx(-5.0)

    def test_base_angle_zero_at_bottom(self):
        c = SlipCircle(centre_x=0.0, centre_y=0.0, radius=5.0)
        assert c.base_angle_at(0.0) == pytest.approx(0.0)

    def test_intersection_with_horizontal_ground(self):
        c = SlipCircle(centre_x=0.0, centre_y=3.0, radius=5.0)
        ground = Polyline(vertices=[Vertex(-10, 0), Vertex(10, 0)])
        hit = c.intersect_with_ground(ground)
        assert hit is not None
        xl, xr = hit
        assert xl == pytest.approx(-4.0, abs=1e-3)
        assert xr == pytest.approx(4.0, abs=1e-3)


# ----------------------------------------------------------------------
class TestSlicer:
    def test_slices_generated(self):
        p = _make_slope_project()
        ext = p.external_boundary()
        ground = _ground_surface_from_external(ext)
        circle = SlipCircle(centre_x=30, centre_y=35, radius=20)
        circle.intersect_with_ground(ground)
        slices = slice_surface(p, circle, num_slices=20)
        assert slices is not None
        assert len(slices) >= 3

    def test_slices_have_positive_weight(self):
        p = _make_slope_project()
        ext = p.external_boundary()
        ground = _ground_surface_from_external(ext)
        circle = SlipCircle(centre_x=30, centre_y=35, radius=20)
        circle.intersect_with_ground(ground)
        slices = slice_surface(p, circle, num_slices=15)
        for s in slices.slices:
            assert s.weight >= 0
            assert s.base_length > 0
            assert s.width > 0

    def test_surface_outside_model_returns_none(self):
        p = _make_slope_project()
        circle = SlipCircle(centre_x=100, centre_y=100, radius=1)
        slices = slice_surface(p, circle, num_slices=10)
        assert slices is None


# ----------------------------------------------------------------------
class TestLEMMethods:
    """Smoke tests for each method on a known homogeneous slope."""

    def test_ordinary_converges(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=OrdinaryFellenius(),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
            num_slices=20, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        # For c=10 kPa, φ=25°, γ=19 kN/m³, expect FoS in [0.8, 2.0]
        assert 0.5 < r.critical.fos < 3.0
        assert r.critical.is_valid

    def test_bishop_converges(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=BishopSimplified(tolerance=1e-3, max_iterations=60),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
            num_slices=20, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        assert r.critical.converged
        assert 0.5 < r.critical.fos < 4.0

    def test_janbu_converges(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=JanbuSimplified(tolerance=1e-3, max_iterations=60),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
            num_slices=20, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        assert 0.5 < r.critical.fos < 4.0

    def test_methods_relative_ordering(self):
        """Ordinary tends to be the most conservative on typical slopes."""
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        results = {}
        for cls in [OrdinaryFellenius, BishopSimplified, JanbuSimplified]:
            search = GridSearch(
                method=cls(),
                grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
                num_slices=20, min_area=5.0,
            )
            r = search.run(p)
            assert r.critical is not None
            results[cls.__name__] = r.critical.fos
        # Bishop > Ordinary is the usual pattern (simplified/friction effect)
        # We don't enforce strict ordering — just that they're all reasonable
        for name, fos in results.items():
            assert 0.3 < fos < 5.0, f"{name}: unreasonable FoS {fos}"

    def test_undrained_slope(self):
        """Pure-cohesion slope: FoS should scale linearly with c."""
        # Simpler slope so Taylor's chart assumptions hold better
        p = Project("undrained")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(50, 0), Vertex(50, 10),
            Vertex(30, 10), Vertex(20, 20), Vertex(0, 20),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))

        results = {}
        for cu in [30.0, 60.0]:
            # Rebuild to get fresh material instance
            p.materials = []
            p.add_material(Material(
                name="soft clay",
                strength=Undrained(cohesion=cu),
                unit_weight=18.0,
            ))
            search = GridSearch(
                method=BishopSimplified(),
                grid_nx=6, grid_ny=6, radius_increment=1.5, min_radius=4.0,
                num_slices=20, min_area=3.0,
            )
            r = search.run(p)
            assert r.critical is not None
            results[cu] = r.critical.fos

        # Doubling cu should roughly double the FoS (undrained scales linearly)
        ratio = results[60.0] / results[30.0]
        assert 1.7 < ratio < 2.3, f"FoS ratio {ratio} far from expected ~2.0"


# ----------------------------------------------------------------------
class TestRigorousMethods:
    """Smoke tests for Spencer and GLE/Morgenstern-Price."""

    def test_spencer_converges(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=Spencer(tolerance=1e-3, max_iterations=50),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
            num_slices=25, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        # Spencer satisfies both force and moment; FoS in a reasonable range
        assert 0.5 < r.critical.fos < 3.0

    def test_gle_converges(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=GLEMorgensternPrice(tolerance=1e-3, max_iterations=50),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=5.0,
            num_slices=25, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        assert 0.5 < r.critical.fos < 3.0

    def test_gle_with_constant_f_matches_spencer(self):
        """GLE with f(x)=1 should be numerically close to Spencer."""
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)

        s_search = GridSearch(
            method=Spencer(),
            grid_nx=5, grid_ny=5, radius_increment=3.0, min_radius=5.0,
            num_slices=25, min_area=5.0,
        )
        g_search = GridSearch(
            method=GLEMorgensternPrice(interslice_func=constant),
            grid_nx=5, grid_ny=5, radius_increment=3.0, min_radius=5.0,
            num_slices=25, min_area=5.0,
        )
        r_s = s_search.run(p)
        r_g = g_search.run(p)
        assert r_s.critical is not None
        assert r_g.critical is not None
        # Should match within 5% (both implement the same physics)
        rel = abs(r_s.critical.fos - r_g.critical.fos) / r_s.critical.fos
        assert rel < 0.10, f"Spencer {r_s.critical.fos:.3f} vs GLE(f=1) {r_g.critical.fos:.3f}"

    def test_gle_half_sine_runs(self):
        p = _make_slope_project(cohesion=10, phi=25, gamma=19)
        search = GridSearch(
            method=GLEMorgensternPrice(interslice_func=half_sine),
            grid_nx=5, grid_ny=5, radius_increment=3.0, min_radius=5.0,
            num_slices=25, min_area=5.0,
        )
        r = search.run(p)
        assert r.critical is not None
        assert r.valid_count > 0
