# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for ogr_core.geometry."""
from __future__ import annotations

import math

import pytest

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
    cleanup_boundaries,
    find_intersections,
    has_self_intersections,
    remove_duplicate_vertices,
    simplify_rdp,
)


class TestVertex:
    def test_distance(self):
        a, b = Vertex(0, 0), Vertex(3, 4)
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_operators(self):
        a, b = Vertex(1, 2), Vertex(3, 4)
        assert (a + b).as_tuple() == (4, 6)
        assert (b - a).as_tuple() == (2, 2)
        assert (a * 2).as_tuple() == (2, 4)

    def test_immutable(self):
        v = Vertex(1, 2)
        with pytest.raises(Exception):
            v.x = 5  # frozen dataclass


class TestPolyline:
    def test_length_open(self):
        p = Polyline(vertices=[Vertex(0, 0), Vertex(3, 0), Vertex(3, 4)])
        assert p.length() == pytest.approx(7.0)

    def test_length_closed(self):
        p = Polyline(vertices=[Vertex(0, 0), Vertex(3, 0), Vertex(3, 4)], closed=True)
        assert p.length() == pytest.approx(12.0)

    def test_bounding_box(self):
        p = Polyline(vertices=[Vertex(-1, 2), Vertex(5, -3), Vertex(0, 7)])
        assert p.bounding_box() == (-1, -3, 5, 7)

    def test_signed_area_ccw(self):
        p = Polyline(
            vertices=[Vertex(0, 0), Vertex(4, 0), Vertex(4, 3), Vertex(0, 3)],
            closed=True,
        )
        assert p.signed_area() > 0
        assert p.area() == pytest.approx(12.0)

    def test_ensure_ccw_reverses_cw(self):
        p = Polyline(
            vertices=[Vertex(0, 0), Vertex(0, 3), Vertex(4, 3), Vertex(4, 0)],
            closed=True,
        )
        assert p.signed_area() < 0
        p.ensure_ccw()
        assert p.signed_area() > 0

    def test_roundtrip(self):
        p = Polyline(vertices=[Vertex(1, 2), Vertex(3, 4)], closed=True)
        p2 = Polyline.from_dict(p.to_dict())
        assert p2.vertices[0].x == 1
        assert p2.closed


class TestCleanup:
    def test_remove_consecutive_duplicates(self):
        p = Polyline(vertices=[Vertex(0, 0), Vertex(0, 0), Vertex(1, 1)])
        n = remove_duplicate_vertices(p, tol=1e-6)
        assert n == 1
        assert len(p) == 2

    def test_rdp_simplification(self):
        pts = [Vertex(x, 0.0) for x in range(11)] + [Vertex(10, 1)]
        p = Polyline(vertices=pts)
        p2 = simplify_rdp(p, epsilon=0.1)
        # Colinear points should collapse
        assert len(p2) < len(p)
        assert len(p2) >= 2

    def test_segment_intersection_proper(self):
        a = Polyline(vertices=[Vertex(0, 0), Vertex(10, 10)])
        b = Polyline(vertices=[Vertex(0, 10), Vertex(10, 0)])
        pts = find_intersections(a, b)
        assert len(pts) == 1
        assert pts[0].x == pytest.approx(5.0)
        assert pts[0].y == pytest.approx(5.0)

    def test_self_intersection_bowtie(self):
        p = Polyline(
            vertices=[Vertex(0, 0), Vertex(1, 1), Vertex(1, 0), Vertex(0, 1)],
            closed=True,
        )
        assert has_self_intersections(p)

    def test_self_intersection_simple_square(self):
        p = Polyline(
            vertices=[Vertex(0, 0), Vertex(1, 0), Vertex(1, 1), Vertex(0, 1)],
            closed=True,
        )
        assert not has_self_intersections(p)

    def test_cleanup_pipeline(self):
        b1 = Boundary(
            polyline=Polyline(vertices=[Vertex(0, 0), Vertex(0, 0), Vertex(1, 0)]),
            btype=BoundaryType.MATERIAL,
        )
        report = cleanup_boundaries([b1])
        assert report["duplicates_removed"] == 1


class TestBoundary:
    def test_default_color_per_type(self):
        b = Boundary(polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 1)]),
                     btype=BoundaryType.WATER_TABLE)
        assert b.color is not None
        assert b.btype.display_name == "Water Table"

    def test_roundtrip(self):
        b = Boundary(
            polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 0)], closed=False),
            btype=BoundaryType.MATERIAL,
            name="Layer 1",
            material_id="abc",
        )
        b2 = Boundary.from_dict(b.to_dict())
        assert b2.btype == BoundaryType.MATERIAL
        assert b2.name == "Layer 1"
        assert b2.material_id == "abc"
        assert b2.id == b.id
