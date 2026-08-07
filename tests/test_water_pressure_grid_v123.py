# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.23 — Water Pressure Grid tests (Phase 0 of the groundwater plan).

Validation strategy: analytic fields. Both interpolators must be exact
at the data points; TPS must reproduce PLANAR fields exactly anywhere
(its polynomial part), which is the analytically correct behaviour for
hydrostatic conditions (total head H = const → u = γw·(H − y) linear).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import GridValueType, WaterPressureGrid  # noqa: E402

GW = 9.81


def _plane_points(f, xs=(0, 10, 20, 35, 50), ys=(0, 8, 15, 30)):
    return [(x, y, f(x, y)) for x in xs for y in ys]


class TestInterpolators:
    def test_tps_exact_at_data_points(self):
        g = WaterPressureGrid(points=[(0, 0, 5.0), (10, 0, 7.0),
                                      (0, 10, 3.0), (10, 10, 9.0),
                                      (5, 5, 6.0)])
        for x, y, v in g.points:
            assert abs(g.value_at(x, y) - v) < 1e-6

    def test_tps_reproduces_planar_field(self):
        # v(x, y) = 30 + 0.2·x − 0.5·y sampled on a coarse grid must be
        # recovered EXACTLY anywhere (TPS polynomial part).
        f = lambda x, y: 30.0 + 0.2 * x - 0.5 * y
        g = WaterPressureGrid(points=_plane_points(f))
        for x, y in [(3.3, 4.7), (17.1, 12.9), (42.0, 1.5), (25.0, 25.0)]:
            assert abs(g.value_at(x, y) - f(x, y)) < 1e-4, (x, y)

    def test_idw_exact_at_data_points(self):
        g = WaterPressureGrid(points=[(0, 0, 5.0), (10, 0, 7.0),
                                      (0, 10, 3.0)],
                              interpolation="idw")
        for x, y, v in g.points:
            assert abs(g.value_at(x, y) - v) < 1e-9

    def test_idw_bounded_by_data(self):
        g = WaterPressureGrid(points=[(0, 0, 2.0), (10, 0, 8.0)],
                              interpolation="idw")
        v = g.value_at(5, 0)
        assert 2.0 <= v <= 8.0

    def test_large_cloud_falls_back_to_idw(self):
        pts = [(float(i % 25), float(i // 25), 1.0) for i in range(400)]
        g = WaterPressureGrid(points=pts)  # tps requested, 400 > 300
        assert abs(g.value_at(12.2, 7.7) - 1.0) < 1e-9


class TestGridTypes:
    def test_total_head_hydrostatic(self):
        # Constant total head H = 20 → u = γw·(20 − y): exact anywhere.
        g = WaterPressureGrid(points=_plane_points(lambda x, y: 20.0),
                              value_type=GridValueType.TOTAL_HEAD)
        for y in (0.0, 5.0, 12.5, 19.0):
            u = g.pore_pressure_at(10.0, y, GW)
            assert abs(u - GW * (20.0 - y)) < 1e-3, y

    def test_total_head_suction_clamped_by_default(self):
        g = WaterPressureGrid(points=_plane_points(lambda x, y: 20.0),
                              value_type=GridValueType.TOTAL_HEAD)
        assert g.pore_pressure_at(10.0, 25.0, GW) == 0.0

    def test_total_head_suction_kept_when_allowed(self):
        g = WaterPressureGrid(points=_plane_points(lambda x, y: 20.0),
                              value_type=GridValueType.TOTAL_HEAD,
                              allow_suction=True)
        u = g.pore_pressure_at(10.0, 25.0, GW)
        assert abs(u - GW * (20.0 - 25.0)) < 1e-3
        assert u < 0

    def test_pressure_head_conversion(self):
        g = WaterPressureGrid(points=_plane_points(lambda x, y: 4.0),
                              value_type=GridValueType.PRESSURE_HEAD)
        assert abs(g.pore_pressure_at(7.0, 3.0, GW) - 4.0 * GW) < 1e-3

    def test_pore_pressure_direct(self):
        g = WaterPressureGrid(points=_plane_points(lambda x, y: 55.5),
                              value_type=GridValueType.PORE_PRESSURE)
        assert abs(g.pore_pressure_at(1.0, 1.0, GW) - 55.5) < 1e-3

    def test_empty_grid_returns_none(self):
        g = WaterPressureGrid()
        assert g.value_at(0, 0) is None
        assert g.pore_pressure_at(0, 0, GW) is None


class TestSerialisation:
    def test_round_trip(self):
        g = WaterPressureGrid(points=[(1, 2, 3.5), (4, 5, 6.5)],
                              value_type=GridValueType.TOTAL_HEAD,
                              interpolation="idw", idw_neighbours=4,
                              allow_suction=True)
        g2 = WaterPressureGrid.from_dict(g.to_dict())
        assert g2.points == [(1, 2, 3.5), (4, 5, 6.5)]
        assert g2.value_type == GridValueType.TOTAL_HEAD
        assert g2.interpolation == "idw"
        assert g2.idw_neighbours == 4
        assert g2.allow_suction is True

    def test_project_round_trip(self):
        from ogr_core.project import Project
        p = Project(name="wpg")
        p.water_pressure_grid = WaterPressureGrid(
            points=[(0, 0, 10.0), (5, 5, 12.0)],
            value_type=GridValueType.PRESSURE_HEAD)
        d = p.to_dict()
        p2 = Project.from_dict(d)
        assert p2.water_pressure_grid is not None
        assert p2.water_pressure_grid.value_type == GridValueType.PRESSURE_HEAD
        assert len(p2.water_pressure_grid.points) == 2

    def test_project_without_grid_round_trip(self):
        from ogr_core.project import Project
        p = Project(name="dry")
        p2 = Project.from_dict(p.to_dict())
        assert p2.water_pressure_grid is None


class TestPorePressureIntegration:
    def _project_with_grid(self):
        from test_slide_validation_ej1 import _ej1_project
        from ogr_core.project.settings import GroundwaterMethod
        p = _ej1_project()
        p.settings.groundwater.method = GroundwaterMethod.GRID_TOTAL_HEAD.value
        # Horizontal phreatic surface at y = 30 encoded as a total-head
        # grid: H = 30 everywhere.
        p.water_pressure_grid = WaterPressureGrid(
            points=[(x, y, 30.0) for x in (0, 40, 80, 130)
                    for y in (0, 20, 45)],
            value_type=GridValueType.TOTAL_HEAD)
        return p

    def test_grid_governs_water_driven_materials(self):
        from ogr_core.geometry.primitives import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = self._project_with_grid()
        mat = p.materials[0]
        gw = p.settings.groundwater.pore_fluid_unit_weight
        u = pore_pressure_at(p, Vertex(50.0, 10.0), mat)
        assert abs(u - gw * (30.0 - 10.0)) < 1e-3
        # Above the head surface → clamped to zero
        assert pore_pressure_at(p, Vertex(50.0, 35.0), mat) == 0.0

    def test_grid_lowers_fos_vs_dry(self):
        """Sanity: adding a phreatic grid must LOWER the FoS of the
        reference circle compared to the dry model."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from test_slide_validation_ej1 import _ej1_project
        circ = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        dry = ev.evaluate_circle(_ej1_project(), circ)
        wet = ev.evaluate_circle(self._project_with_grid(), circ)
        assert dry.is_valid and wet.is_valid
        assert wet.fos < dry.fos, (wet.fos, dry.fos)


class TestCsvParser:
    def test_parse_mixed_separators_and_header(self):
        from ogr_gui.dialogs.water_pressure_grid_dialog import (
            parse_grid_csv_text,
        )
        text = """# comment
x, y, total_head
0, 5, 30.0
10;6;29.5
20\t7\t29.0
malformed line
30 8 28.5
"""
        pts = parse_grid_csv_text(text)
        assert pts == [(0.0, 5.0, 30.0), (10.0, 6.0, 29.5),
                       (20.0, 7.0, 29.0), (30.0, 8.0, 28.5)]

    def test_parse_empty(self):
        from ogr_gui.dialogs.water_pressure_grid_dialog import (
            parse_grid_csv_text,
        )
        assert parse_grid_csv_text("just a header\n") == []
