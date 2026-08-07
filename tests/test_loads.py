# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for the v0.1.7 Loadings model.

Verifies:
    - DistributedLoad.pressure_at(t) interpolates between m1 and m2
    - direction_vector() for all 5 orientations
    - LineLoad direction_vector() matches expectations
"""
from __future__ import annotations

import math

from ogr_core.geometry import Vertex
from ogr_core.loads import (
    DistributedLoad,
    LineLoad,
    LoadDistribution,
    LoadOrientation,
)


# ======================================================================
class TestDistributedLoadPressure:
    def test_constant_distribution(self):
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=50.0,
            distribution=LoadDistribution.CONSTANT,
        )
        assert load.pressure_at(0.0) == 50.0
        assert load.pressure_at(0.5) == 50.0
        assert load.pressure_at(1.0) == 50.0

    def test_triangular_distribution(self):
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=0.0, magnitude_2=100.0,
            distribution=LoadDistribution.TRIANGULAR,
        )
        assert load.pressure_at(0.0) == 0.0
        assert math.isclose(load.pressure_at(0.5), 50.0)
        assert load.pressure_at(1.0) == 100.0


# ======================================================================
class TestDistributedLoadDirection:
    def test_vertical_orientation_is_downward(self):
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=50.0,
            orientation=LoadOrientation.VERTICAL,
        )
        dx, dy = load.direction_vector()
        assert math.isclose(dx, 0.0, abs_tol=1e-9)
        assert math.isclose(dy, -1.0, abs_tol=1e-9)

    def test_horizontal_orientation(self):
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=50.0,
            orientation=LoadOrientation.HORIZONTAL,
        )
        dx, dy = load.direction_vector()
        assert math.isclose(dx, 1.0)
        assert math.isclose(dy, 0.0)

    def test_normal_to_horizontal_boundary_is_downward(self):
        # Boundary along +X: normal (CW rotation of tangent) → -Y
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=50.0,
            orientation=LoadOrientation.NORMAL_TO_BOUNDARY,
        )
        dx, dy = load.direction_vector()
        assert math.isclose(dx, 0.0, abs_tol=1e-9)
        assert dy < 0  # downward into the slope

    def test_angle_from_horizontal_45deg(self):
        load = DistributedLoad(
            start=Vertex(0, 10), end=Vertex(10, 10),
            magnitude_1=50.0,
            orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
            angle_deg=45.0,
        )
        dx, dy = load.direction_vector()
        assert math.isclose(dx, math.sqrt(2) / 2, rel_tol=1e-6)
        assert math.isclose(dy, math.sqrt(2) / 2, rel_tol=1e-6)


# ======================================================================
class TestLineLoad:
    def test_default_vertical(self):
        load = LineLoad(point=Vertex(5, 10), magnitude=200.0)
        dx, dy = load.direction_vector()
        assert math.isclose(dy, -1.0)

    def test_horizontal(self):
        load = LineLoad(
            point=Vertex(5, 10), magnitude=200.0,
            orientation=LoadOrientation.HORIZONTAL,
        )
        dx, dy = load.direction_vector()
        assert math.isclose(dx, 1.0)
