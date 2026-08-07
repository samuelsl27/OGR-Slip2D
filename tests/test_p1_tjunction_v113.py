# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.13 P1 fix — material boundary starting on/ending on
another material boundary (T-junction case Samuel reported).

In v0.1.11 / v0.1.12, when a Material Boundary's endpoint sat exactly
on the interior of another Material Boundary, the planar graph was
missing a node at that point and the resulting subdivision merged
regions that should have been separated.

v0.1.13 adds an explicit "node endpoints on segments" pre-processing
step in :mod:`ogr_core.geometry.regions`.
"""
from __future__ import annotations


def _setup():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("t-junction-test")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0),
        Vertex(60, 14), Vertex(35, 14),
        Vertex(15, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    return p, Boundary, BoundaryType, Polyline, Vertex, Material, MohrCoulomb


# ======================================================================
class TestTJunctionRegionGeneration:
    def test_diagonal_endpoints_on_two_horizontals_creates_5_regions(self):
        """Two horizontal cuts + a diagonal whose endpoints lie ON those
        horizontals should produce 5 regions (the diagonal subdivides
        the middle layer into left/right zones)."""
        p, B, BT, PL, V, _, _ = _setup()
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 4), V(60, 4)], closed=False),
            btype=BT.MATERIAL))
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 8), V(60, 8)], closed=False),
            btype=BT.MATERIAL))
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 12), V(60, 12)], closed=False),
            btype=BT.MATERIAL))
        # T-junction diagonal: starts on y=8, ends on y=4
        p.add_boundary(B(
            polyline=PL(vertices=[V(10, 8), V(50, 4)], closed=False),
            btype=BT.MATERIAL))
        regs = p.resolve_regions()
        assert len(regs) >= 5, (
            f"Expected ≥ 5 regions for T-junction diagonal between two "
            f"horizontals, got {len(regs)}"
        )

    def test_diagonal_starting_on_external_endpoint_on_other_cut(self):
        """Diagonal whose first endpoint is on the External perimeter
        and last endpoint sits on another cut should still subdivide."""
        p, B, BT, PL, V, _, _ = _setup()
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 8), V(60, 8)], closed=False),
            btype=BT.MATERIAL))
        # Diagonal: endpoint at (0, 14) is on External, (30, 8) is on the cut
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 14), V(30, 8)], closed=False),
            btype=BT.MATERIAL))
        regs = p.resolve_regions()
        # Without T-junction noding: 2 regions. With: should be at least 3.
        assert len(regs) >= 3, (
            f"Diagonal endpoint on another cut should split adjacent "
            f"region. Got {len(regs)} regions"
        )

    def test_distinct_material_assignment_after_fix(self):
        """After the fix, each of the 5 regions should be assignable
        to a distinct material via centroid clicking."""
        p, B, BT, PL, V, Mat, MC = _setup()
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 4), V(60, 4)], closed=False),
            btype=BT.MATERIAL))
        p.add_boundary(B(
            polyline=PL(vertices=[V(0, 8), V(60, 8)], closed=False),
            btype=BT.MATERIAL))
        p.add_boundary(B(
            polyline=PL(vertices=[V(10, 8), V(50, 4)], closed=False),
            btype=BT.MATERIAL))
        p.materials = [
            Mat(name=f"M{i}", strength=MC(cohesion=10, friction_angle=20))
            for i in range(6)
        ]
        regs = p.resolve_regions()
        # Assign each region a distinct material via centroid
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)
        regs2 = p.resolve_regions()
        mat_ids = [r.material_id for r in regs2 if r.material_id is not None]
        assert len(set(mat_ids)) >= 4, (
            f"Each region should hold its assigned material, "
            f"got {mat_ids}"
        )


# ======================================================================
class TestNodingHelper:
    """Direct tests of the new helper function."""

    def test_t_junction_splits_receiver(self):
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.regions import _node_endpoints_on_segments
        # Segment A: horizontal from (0,0) to (10,0)
        # Segment B: vertical from (5,0) to (5,5) — its first endpoint
        # sits on the interior of A. Expect A to be split at (5,0).
        a = (Vertex(0, 0), Vertex(10, 0))
        b = (Vertex(5, 0), Vertex(5, 5))
        out = _node_endpoints_on_segments([a, b], 1e-6)
        # A becomes 2 segments, B remains 1
        assert len(out) == 3
        # One of the new segments should end at (5, 0)
        endpoints = [(s[0].x, s[0].y, s[1].x, s[1].y) for s in out]
        assert any(abs(s[2] - 5) < 1e-6 and abs(s[3] - 0) < 1e-6
                   for s in endpoints), endpoints

    def test_no_split_when_endpoints_at_corners(self):
        """Endpoints AT the receiver's own corners must NOT split it."""
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.regions import _node_endpoints_on_segments
        # Two segments sharing a corner — no T-junction
        a = (Vertex(0, 0), Vertex(10, 0))
        b = (Vertex(10, 0), Vertex(10, 5))
        out = _node_endpoints_on_segments([a, b], 1e-6)
        assert len(out) == 2  # nothing should change

    def test_endpoint_off_segment_no_split(self):
        """An endpoint that's not on any other segment must not split."""
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.regions import _node_endpoints_on_segments
        a = (Vertex(0, 0), Vertex(10, 0))
        b = (Vertex(15, 5), Vertex(20, 5))  # nowhere near segment a
        out = _node_endpoints_on_segments([a, b], 1e-6)
        assert len(out) == 2
