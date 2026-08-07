# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for the Slide-style Expand/Shrink External Boundary algorithm.

Covers:
    - Expand on same edge (bulge out)
    - Shrink on same edge (notch in)
    - Expand across different edges
    - Rejection when endpoints aren't on the External
    - Auto-detection of expand vs shrink
    - Removed arc generation (for optional Material Boundary conversion)
"""
from __future__ import annotations

import math

from ogr_core.geometry import (
    ExpandShrinkError,
    Polyline,
    Vertex,
    expand_shrink_external,
)


def _area(verts):
    s = 0.0
    n = len(verts)
    for i in range(n):
        s += verts[i].x * verts[(i + 1) % n].y - verts[(i + 1) % n].x * verts[i].y
    return abs(s) / 2


SQUARE = Polyline(
    vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 10), Vertex(0, 10)],
    closed=True,
)


class TestExpand:
    def test_expand_same_edge_bulge_out(self):
        poly = Polyline(vertices=[
            Vertex(10, 3), Vertex(15, 3), Vertex(15, 7), Vertex(10, 7),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.mode == "expand"
        assert math.isclose(_area(r.new_external.vertices), 120.0, rel_tol=1e-6)
        # The removed arc is the 2-vertex segment between (10,3) and (10,7)
        assert r.removed_arc is not None
        assert len(r.removed_arc.vertices) == 2

    def test_expand_across_bottom_edge(self):
        poly = Polyline(vertices=[
            Vertex(8, 0), Vertex(8, -3), Vertex(2, -3), Vertex(2, 0),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.mode == "expand"
        # Original 100 + bulge 6*3 = 118
        assert math.isclose(_area(r.new_external.vertices), 118.0, rel_tol=1e-6)

    def test_expand_across_two_edges(self):
        # Polyline starts on right edge, ends on top edge
        poly = Polyline(vertices=[
            Vertex(10, 7), Vertex(13, 7), Vertex(13, 13), Vertex(7, 13), Vertex(7, 10),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.mode == "expand"
        # Should be larger than the original 100
        assert _area(r.new_external.vertices) > 100.0


class TestShrink:
    def test_shrink_same_edge_notch_in(self):
        poly = Polyline(vertices=[
            Vertex(10, 3), Vertex(8, 3), Vertex(8, 7), Vertex(10, 7),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.mode == "shrink"
        # Original 100, removed notch of 2*4 = 8 → new 92
        assert math.isclose(_area(r.new_external.vertices), 92.0, rel_tol=1e-6)
        # Removed arc is the 2 vertices of the bitten-off edge piece
        assert r.removed_arc is not None

    def test_shrink_across_corner(self):
        # Notch that clips the (10, 0) corner off
        poly = Polyline(vertices=[
            Vertex(10, 3), Vertex(5, 3), Vertex(5, 0),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.mode == "shrink"
        # Cut off a 5x3 = 15 triangle? No, a 5x3 RECTANGLE bottom-right.
        # Original 100 - 15 = 85
        assert math.isclose(_area(r.new_external.vertices), 85.0, rel_tol=1e-6)


class TestErrors:
    def test_endpoint_not_on_external_raises(self):
        # Both endpoints are far from the External
        poly = Polyline(vertices=[
            Vertex(-5, -5), Vertex(-5, -3),
        ], closed=False)
        try:
            expand_shrink_external(SQUARE, poly)
            raised = False
        except ExpandShrinkError:
            raised = True
        assert raised

    def test_open_external_raises(self):
        ext = Polyline(
            vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 10)],
            closed=False,
        )
        poly = Polyline(vertices=[Vertex(10, 3), Vertex(15, 5)], closed=False)
        try:
            expand_shrink_external(ext, poly)
            raised = False
        except ExpandShrinkError:
            raised = True
        assert raised


class TestRemovedArc:
    def test_removed_arc_spans_cut_points(self):
        poly = Polyline(vertices=[
            Vertex(10, 3), Vertex(15, 3), Vertex(15, 7), Vertex(10, 7),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        arc_verts = r.removed_arc.vertices
        # The arc should start and end on the cut points
        assert abs(arc_verts[0].x - 10) < 1e-6
        assert abs(arc_verts[0].y - 3) < 1e-6
        assert abs(arc_verts[-1].x - 10) < 1e-6
        assert abs(arc_verts[-1].y - 7) < 1e-6

    def test_removed_arc_is_open_polyline(self):
        poly = Polyline(vertices=[
            Vertex(10, 3), Vertex(15, 5), Vertex(10, 7),
        ], closed=False)
        r = expand_shrink_external(SQUARE, poly)
        assert r.removed_arc.closed is False
