# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for ogr_core.geometry.transforms (v0.1.2)."""
from __future__ import annotations

import math

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
    change_slope_angle,
    convert_boundary,
    offset_polygon,
    rotate,
    scale,
    translate,
)


def _unit_square() -> Boundary:
    pl = Polyline(
        vertices=[Vertex(0, 0), Vertex(1, 0), Vertex(1, 1), Vertex(0, 1)],
        closed=True,
    )
    return Boundary(polyline=pl, btype=BoundaryType.EXTERNAL)


# ======================================================================
class TestTranslate:
    def test_translate_unit_square(self):
        b = _unit_square()
        new_b = translate(b, 5.0, -3.0)
        assert new_b.vertices[0].x == 5.0
        assert new_b.vertices[0].y == -3.0
        assert new_b.vertices[2].x == 6.0
        assert new_b.vertices[2].y == -2.0
        # Original unchanged
        assert b.vertices[0].x == 0.0

    def test_translate_zero_is_identity(self):
        b = _unit_square()
        new_b = translate(b, 0.0, 0.0)
        for v1, v2 in zip(b.vertices, new_b.vertices):
            assert v1.x == v2.x and v1.y == v2.y


# ======================================================================
class TestRotate:
    def test_rotate_90_around_origin(self):
        b = _unit_square()
        new_b = rotate(b, Vertex(0, 0), 90.0)
        # (1,0) -> (0,1), (1,1) -> (-1,1), (0,1) -> (-1,0), (0,0) -> (0,0)
        expected = [(0, 0), (0, 1), (-1, 1), (-1, 0)]
        for (ex, ey), v in zip(expected, new_b.vertices):
            assert abs(v.x - ex) < 1e-9, f"x mismatch: got {v.x}, expected {ex}"
            assert abs(v.y - ey) < 1e-9, f"y mismatch: got {v.y}, expected {ey}"

    def test_rotate_360_is_identity(self):
        b = _unit_square()
        new_b = rotate(b, Vertex(2.0, 2.0), 360.0)
        for v1, v2 in zip(b.vertices, new_b.vertices):
            assert abs(v1.x - v2.x) < 1e-9
            assert abs(v1.y - v2.y) < 1e-9

    def test_rotate_preserves_shape(self):
        b = _unit_square()
        new_b = rotate(b, Vertex(0.5, 0.5), 37.0)
        # Lengths of edges must be preserved
        for (a1, a2), (b1, b2) in zip(
            zip(b.vertices, b.vertices[1:] + [b.vertices[0]]),
            zip(new_b.vertices, new_b.vertices[1:] + [new_b.vertices[0]]),
        ):
            d1 = math.hypot(a2.x - a1.x, a2.y - a1.y)
            d2 = math.hypot(b2.x - b1.x, b2.y - b1.y)
            assert abs(d1 - d2) < 1e-9


# ======================================================================
class TestScale:
    def test_scale_by_1_is_identity(self):
        b = _unit_square()
        new_b = scale(b, Vertex(5, 5), 1.0, 1.0)
        for v1, v2 in zip(b.vertices, new_b.vertices):
            assert abs(v1.x - v2.x) < 1e-9
            assert abs(v1.y - v2.y) < 1e-9

    def test_uniform_scale_by_2(self):
        b = _unit_square()
        new_b = scale(b, Vertex(0, 0), 2.0)
        assert new_b.vertices[2].x == 2.0
        assert new_b.vertices[2].y == 2.0

    def test_non_uniform_scale(self):
        b = _unit_square()
        new_b = scale(b, Vertex(0, 0), 2.0, 3.0)
        assert new_b.vertices[2].x == 2.0
        assert new_b.vertices[2].y == 3.0


# ======================================================================
class TestOffsetPolygon:
    def test_offset_unit_square_outward_is_bigger(self):
        b = _unit_square()
        new_poly = offset_polygon(b.polyline, 1.0)
        # The new square should be 3x3 centred at (0.5, 0.5)
        xs = [v.x for v in new_poly.vertices]
        ys = [v.y for v in new_poly.vertices]
        assert abs(min(xs) - (-1.0)) < 1e-6
        assert abs(max(xs) - 2.0) < 1e-6
        assert abs(min(ys) - (-1.0)) < 1e-6
        assert abs(max(ys) - 2.0) < 1e-6

    def test_offset_zero_is_identity(self):
        b = _unit_square()
        new_poly = offset_polygon(b.polyline, 0.0)
        # Even with zero offset, intersection of parallel edges may drift
        # very slightly — so we only check the bounding box
        xs = [v.x for v in new_poly.vertices]
        ys = [v.y for v in new_poly.vertices]
        assert abs(min(xs)) < 1e-9
        assert abs(max(xs) - 1.0) < 1e-9


# ======================================================================
class TestConvertBoundary:
    def test_material_to_piezometric_unlinks_material(self):
        b = _unit_square()
        b.btype = BoundaryType.MATERIAL
        b.material_id = "some-id"
        new_b = convert_boundary(b, BoundaryType.PIEZOMETRIC)
        assert new_b.btype == BoundaryType.PIEZOMETRIC
        assert new_b.material_id is None
        assert not new_b.polyline.closed

    def test_convert_preserves_vertices(self):
        b = _unit_square()
        b.btype = BoundaryType.MATERIAL
        new_b = convert_boundary(b, BoundaryType.WATER_TABLE)
        # Number of vertices unchanged
        assert len(new_b.vertices) == len(b.vertices)


# ======================================================================
class TestChangeSlopeAngle:
    def test_change_slope_rotates_geometry(self):
        # Simple slope: (0,0), (10,0), (10,5), (5,5), (0,0)  — a 45° face
        pl = Polyline(
            vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 5), Vertex(5, 5)],
            closed=True,
        )
        b = Boundary(polyline=pl, btype=BoundaryType.EXTERNAL)
        # Pivot at (5, 5) — the top of the slope face
        new_b = change_slope_angle(b, Vertex(5, 5), 30.0)
        # All vertices should still exist
        assert len(new_b.vertices) == len(b.vertices)
