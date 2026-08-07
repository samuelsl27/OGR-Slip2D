# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.15 — the critical subdivision bug fix.

In v0.1.14 the shapely planar-subdivision algorithm clipped each
material boundary to the External polygon BEFORE the unary_union. This
created endpoints on the slope face with sub-millimetre floating-point
error, which prevented polygonize() from recognising them as shared
nodes — dropping ALL faces (0 regions) on realistic slope geometries.

v0.1.15 rewrites the algorithm with the extend-then-clip-faces
approach: material boundaries are EXTENDED beyond the External, unioned,
polygonized, and faces outside the External are discarded.
"""
from __future__ import annotations


def _slope_project(n_layers: int):
    """A realistic slope (toe shelf + inclined face) with n horizontal
    material layers."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("v115")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 30),
        Vertex(60, 30), Vertex(20, 5), Vertex(0, 5),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name=f"L{i}",
                 strength=MohrCoulomb(cohesion=10, friction_angle=20))
        for i in range(n_layers + 4)
    ]
    ys = [30.0 * (i + 1) / (n_layers + 1) for i in range(n_layers)]
    for y in ys:
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, y), Vertex(100, y)], closed=False),
            btype=BoundaryType.MATERIAL))
    return p


# ======================================================================
class TestSubdivisionRobustness:
    def test_single_horizontal_on_sloped_external(self):
        """The classic regression: ONE horizontal cut on a slope with
        an inclined face must produce 2 regions (was 0 in v0.1.14)."""
        p = _slope_project(1)
        regs = p.resolve_regions()
        assert len(regs) == 2, (
            f"Single horizontal on sloped External should give 2 "
            f"regions, got {len(regs)}"
        )

    def test_eight_horizontals(self):
        """Eight layers → nine regions."""
        p = _slope_project(8)
        regs = p.resolve_regions()
        assert len(regs) == 9, (
            f"8 horizontals should give 9 regions, got {len(regs)}"
        )

    def test_many_horizontals_stress(self):
        """Stress test: 15 layers → 16 regions, none missing."""
        p = _slope_project(15)
        regs = p.resolve_regions()
        assert len(regs) == 16, (
            f"15 horizontals should give 16 regions, got {len(regs)}"
        )

    def test_assign_distinct_materials_to_all(self):
        """Every region must be independently assignable."""
        p = _slope_project(5)
        regs = p.resolve_regions()
        assert len(regs) == 6
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            assert p.assign_material_at(cx, cy, p.materials[i].id), (
                f"Region {i} at ({cx:.1f},{cy:.1f}) not assignable"
            )
        regs2 = p.resolve_regions()
        names = set()
        for r in regs2:
            m = next((m for m in p.materials if m.id == r.material_id), None)
            names.add(m.name if m else None)
        assert len(names) == 6, (
            f"Expected 6 distinct materials, got {names}"
        )

    def test_diagonal_after_assignment_inherits(self):
        """Adding a diagonal that subdivides assigned regions: all
        sub-regions must inherit (no None)."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _slope_project(5)
        regs = p.resolve_regions()
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)
        # Add diagonal
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(30, 24), Vertex(80, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs2 = p.resolve_regions()
        none_count = sum(1 for r in regs2 if r.material_id is None)
        assert none_count == 0, (
            f"{none_count} sub-regions lost their material after "
            f"adding the diagonal"
        )


# ======================================================================
class TestTJunctionVsDangling:
    """The extension logic must distinguish T-junctions (endpoint on
    another cut → don't extend) from dangling cuts (endpoint floating
    inside External → extend to subdivide)."""

    def _base(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        p = Project("tj")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(60, 0), Vertex(60, 14),
            Vertex(35, 14), Vertex(15, 25), Vertex(0, 25),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [
            Material(name=f"M{i}", strength=MohrCoulomb(cohesion=10, friction_angle=20))
            for i in range(8)
        ]
        return p

    def test_t_junction_gives_four(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = self._base()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 4), Vertex(60, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 8), Vertex(60, 8)], closed=False),
            btype=BoundaryType.MATERIAL))
        # Diagonal whose endpoints sit ON the two horizontals
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 8), Vertex(50, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        assert len(regs) == 4, (
            f"T-junction should give 4 regions (no spurious extension), "
            f"got {len(regs)}"
        )

    def test_dangling_diagonal_subdivides(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = self._base()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 6), Vertex(60, 6)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 10), Vertex(60, 10)], closed=False),
            btype=BoundaryType.MATERIAL))
        # Diagonal with both endpoints floating INSIDE the External
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 4), Vertex(40, 11)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        assert len(regs) >= 5, (
            f"Dangling diagonal should subdivide adjacent zones "
            f"(≥5 regions), got {len(regs)}"
        )
