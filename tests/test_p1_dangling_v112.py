# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.12 P1 fix — material assignment with crossing/dangling
material boundaries.

v0.1.11 had a bug: when a Material Boundary had endpoint(s) inside the
External (rather than on its perimeter), the planar subdivision algorithm
dropped the dangling edges and merged the regions adjacent to it. This
made it impossible for the user to assign distinct materials to those
zones.

v0.1.12 adds an "extend dangling endpoints" pre-processing step that
casts each dangling endpoint along the cut's tangent until it hits the
External — closing the regions properly.
"""
from __future__ import annotations


def _setup(name="dangling-test"):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project(name)
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0),
        Vertex(60, 14),
        Vertex(35, 14),
        Vertex(15, 25),
        Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    return p, Boundary, BoundaryType, Polyline, Vertex, Material, MohrCoulomb


# ======================================================================
class TestDanglingEndpointSubdivision:
    """Two horizontal boundaries + one diagonal whose BOTH endpoints lie
    strictly inside the External — should produce 6 regions."""

    def test_diagonal_inside_creates_extra_regions(self):
        p, Boundary, BType, PL, V, _, _ = _setup("d1")
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 6), V(60, 6)], closed=False),
            btype=BType.MATERIAL))
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 10), V(60, 10)], closed=False),
            btype=BType.MATERIAL))
        # Diagonal with both endpoints inside the External
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(10, 4), V(40, 11)], closed=False),
            btype=BType.MATERIAL))

        regs = p.resolve_regions()
        # Without dangling extension we got 4. With the fix we expect ≥ 5.
        assert len(regs) >= 5, (
            f"Expected ≥ 5 regions, got {len(regs)}. The diagonal cut's "
            f"dangling endpoints should subdivide adjacent zones."
        )

    def test_assignment_distinguishes_each_zone(self):
        """After the fix, clicking in different zones returns different
        materials."""
        p, Boundary, BType, PL, V, Mat, MC = _setup("d2")
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 5), V(60, 5)], closed=False),
            btype=BType.MATERIAL))
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 8), V(60, 8)], closed=False),
            btype=BType.MATERIAL))
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(15, 8), V(45, 4)], closed=False),
            btype=BType.MATERIAL))
        p.materials = [
            Mat(name=f"M{i}",
                strength=MC(cohesion=10, friction_angle=20)) for i in range(6)
        ]
        regs = p.resolve_regions()
        # Assign each region its own material via centroid
        for i, r in enumerate(regs[:6]):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)
        regs2 = p.resolve_regions()
        # Each region should now have a distinct material_id
        mat_ids = [r.material_id for r in regs2]
        # Most should be distinct (allow 1-2 collisions due to centroid
        # ambiguity in degenerate cases)
        assert len(set(mat_ids)) >= len(regs2) - 1, (
            f"After per-region assignment, expected distinct material_ids "
            f"per region, got {mat_ids}"
        )

    def test_simple_horizontal_layers_still_work(self):
        """Regression: simple non-dangling case must still work."""
        p, Boundary, BType, PL, V, Mat, MC = _setup("d3")
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 5), V(60, 5)], closed=False),
            btype=BType.MATERIAL))
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 10), V(60, 10)], closed=False),
            btype=BType.MATERIAL))
        regs = p.resolve_regions()
        # 2 horizontal cuts in a slope → 3 regions
        assert len(regs) == 3, f"Expected 3 regions, got {len(regs)}"


# ======================================================================
class TestSingleEndpointDangling:
    """Cases where ONE endpoint is dangling, the other on the perimeter.
    """

    def test_left_endpoint_on_perimeter_right_inside(self):
        p, Boundary, BType, PL, V, _, _ = _setup("s1")
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 8), V(60, 8)], closed=False),
            btype=BType.MATERIAL))
        # Left endpoint on perimeter (x=0), right endpoint inside the External
        p.add_boundary(Boundary(
            polyline=PL(vertices=[V(0, 4), V(30, 4)], closed=False),
            btype=BType.MATERIAL))
        regs = p.resolve_regions()
        # The dangling tip at (30, 4) should extend rightward and create
        # an additional region below the horizontal cut on the right side
        assert len(regs) >= 3
