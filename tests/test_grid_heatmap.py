# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for the v0.1.8 user-defined grid and the FoS heatmap data model.

Verifies:
    - SearchSettings persists grid bounds in to_dict / from_dict
    - GridSearch honours user-defined grid_x / grid_y / grid_nx / grid_ny
    - SearchResult.evaluations groups correctly by (centre_x, centre_y)
"""
from __future__ import annotations

from collections import defaultdict


# ======================================================================
class TestSearchSettingsPersistence:
    def test_grid_bounds_default_to_none(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        assert s.grid_x_min is None
        assert s.grid_x_max is None
        assert s.grid_y_min is None
        assert s.grid_y_max is None
        assert s.grid_nx == 12
        assert s.grid_ny == 12

    def test_set_then_serialize_roundtrip(self):
        from dataclasses import asdict

        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        s.grid_x_min = 5.0
        s.grid_x_max = 45.0
        s.grid_y_min = 30.0
        s.grid_y_max = 60.0
        s.grid_nx = 30
        s.grid_ny = 25
        d = asdict(s)
        s2 = SearchSettings(**d)
        assert s2.grid_x_min == 5.0
        assert s2.grid_x_max == 45.0
        assert s2.grid_y_min == 30.0
        assert s2.grid_y_max == 60.0
        assert s2.grid_nx == 30
        assert s2.grid_ny == 25


# ======================================================================
class TestGridSearchHonoursUserGrid:
    def test_user_grid_overrides_auto(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import BishopSimplified, GridSearch

        p = Project("test")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(50, 0),
            Vertex(50, 30), Vertex(0, 30),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [
            Material(
                name="Soil",
                strength=MohrCoulomb(cohesion=10, friction_angle=25),
            )
        ]

        # User grid: 3 × 3 inside a known box
        s = GridSearch(
            method=BishopSimplified(),
            grid_x=(20.0, 30.0),
            grid_y=(40.0, 50.0),
            grid_nx=2,
            grid_ny=2,
            radius_increment=5.0,
            min_radius=10.0,
            num_slices=10,
        )
        result = s.run(p)
        # v0.1.17 — Slide convention: grid_nx/grid_ny are the number of
        # INTERVALS, so 2 × 2 intervals → 3 × 3 = 9 distinct centres.
        centres = set()
        for r in result.evaluations:
            sd = r.surface.to_dict()
            centres.add((round(sd["centre_x"], 1), round(sd["centre_y"], 1)))
        assert len(centres) == 9
        # All centres are within the user box
        for cx, cy in centres:
            assert 20.0 <= cx <= 30.0
            assert 40.0 <= cy <= 50.0


# ======================================================================
class TestHeatmapBucketing:
    def test_min_fos_per_centre(self):
        """The heatmap reduces all radii at one centre to the min FoS."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import BishopSimplified, GridSearch

        p = Project("hm")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(40, 0),
            Vertex(40, 30), Vertex(0, 30),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [
            Material(
                name="Soil",
                strength=MohrCoulomb(cohesion=20, friction_angle=30),
            )
        ]
        s = GridSearch(
            method=BishopSimplified(),
            grid_x=(15.0, 25.0),
            grid_y=(35.0, 45.0),
            grid_nx=3,
            grid_ny=3,
            radius_increment=2.0,
            min_radius=8.0,
            num_slices=10,
        )
        result = s.run(p)

        # Replicate the bucketing logic used by the heatmap renderer
        bucket = defaultdict(lambda: float("inf"))
        for r in result.valid():
            sd = r.surface.to_dict()
            key = (round(sd["centre_x"], 3), round(sd["centre_y"], 3))
            if r.fos < bucket[key]:
                bucket[key] = r.fos

        # The valid bucket must contain at most 9 entries and every
        # value must be the minimum FoS across all radii at that centre
        assert len(bucket) <= 9
        for r in result.valid():
            sd = r.surface.to_dict()
            key = (round(sd["centre_x"], 3), round(sd["centre_y"], 3))
            assert bucket[key] <= r.fos
