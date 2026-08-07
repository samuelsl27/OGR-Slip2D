# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.14 material region assignment with **footprint
inheritance** — the core fix Samuel requested.

When the user clicks a region to assign material M, the polygon
**footprint** of that region is stored alongside the click. Later,
when a new Material Boundary subdivides that region into sub-regions,
each sub-region inherits M because it overlaps (geometrically) the
stored footprint.

This is the algorithm used by Slide, AutoCAD, Inkscape, QGIS for
persistent attribute-by-region: store *what was assigned to what
shape*, not just *what was assigned to what point*.
"""
from __future__ import annotations


def _three_layer_project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("v114")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 14),
        Vertex(35, 14), Vertex(15, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 4), Vertex(60, 4)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 8), Vertex(60, 8)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.materials = [
        Material(name=f"M{i}", strength=MohrCoulomb(cohesion=10, friction_angle=20))
        for i in range(8)
    ]
    return p


# ======================================================================
class TestFootprintInheritance:
    def test_diagonal_split_preserves_layer_material(self):
        """The classic case Samuel reports: after assigning a material
        to a layer, a diagonal cut SHOULD subdivide that layer into
        sub-regions that ALL still carry the same material."""
        p = _three_layer_project()
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        regs = p.resolve_regions()
        assert len(regs) == 3, f"expected 3 layers, got {len(regs)}"

        # Assign materials to each layer via centroid clicks
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            assert p.assign_material_at(cx, cy, p.materials[i].id)

        # NOW add a diagonal in the middle layer
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 8), Vertex(50, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs2 = p.resolve_regions()
        # 3 layers, middle one subdivided → 4 regions
        assert len(regs2) == 4

        # Map each region to its material
        per_region = []
        for r in regs2:
            cx, cy = r.centroid()
            m = next((m for m in p.materials if m.id == r.material_id), None)
            per_region.append((cy, m.name if m else "NONE"))
        per_region.sort()
        # Bottom layer keeps M0
        assert per_region[0][1] == "M0"
        # The two middle sub-regions BOTH inherit M1 (the layer's material)
        mid_materials = [t[1] for t in per_region if 4 < t[0] < 8]
        assert len(mid_materials) == 2
        assert all(m == "M1" for m in mid_materials), (
            f"Both sub-regions in the middle layer should inherit M1, "
            f"got {mid_materials}"
        )
        # Top layer keeps M2
        assert per_region[-1][1] == "M2"

    def test_cascading_subdivisions_preserve_materials(self):
        """Two successive subdivisions: each new sub-region inherits
        from the right ancestor."""
        p = _three_layer_project()
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        regs = p.resolve_regions()
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)

        # First diagonal subdivides middle layer
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 8), Vertex(50, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        # Second diagonal subdivides bottom layer
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(5, 4), Vertex(40, 0)], closed=False),
            btype=BoundaryType.MATERIAL))

        regs3 = p.resolve_regions()
        assert len(regs3) == 5
        per_region = []
        for r in regs3:
            cx, cy = r.centroid()
            m = next((m for m in p.materials if m.id == r.material_id), None)
            per_region.append((cy, m.name if m else "NONE"))
        per_region.sort()
        # 2 bottom-layer pieces with M0
        bottom = [t[1] for t in per_region if t[0] < 4]
        assert len(bottom) == 2 and all(m == "M0" for m in bottom), bottom
        # 2 middle-layer pieces with M1
        middle = [t[1] for t in per_region if 4 < t[0] < 8]
        assert len(middle) == 2 and all(m == "M1" for m in middle), middle

    def test_direct_click_overrides_footprint_inheritance(self):
        """If the user clicks a sub-region after subdivision with a
        different material, that direct click wins over inheritance."""
        p = _three_layer_project()
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        regs = p.resolve_regions()
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)
        # Add diagonal
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 8), Vertex(50, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs2 = p.resolve_regions()
        # Pick a region on the RIGHT side of the diagonal and override
        for r in regs2:
            cx, cy = r.centroid()
            if 4 < cy < 8 and cx > 30:
                # Override this one with M3
                assert p.assign_material_at(cx, cy, p.materials[3].id)
                break
        regs3 = p.resolve_regions()
        for r in regs3:
            cx, cy = r.centroid()
            if 4 < cy < 8 and cx > 30:
                m = next((m for m in p.materials if m.id == r.material_id), None)
                assert m.name == "M3", \
                    f"Direct click should override, got {m.name}"
                break


# ======================================================================
class TestFootprintPersistence:
    """Footprints must survive save/load roundtrips."""

    def test_save_load_preserves_footprints(self, tmp_path=None):
        import tempfile, os
        if tmp_path is None:
            tmp_path = tempfile.mkdtemp()
        p = _three_layer_project()
        regs = p.resolve_regions()
        for i, r in enumerate(regs):
            cx, cy = r.centroid()
            p.assign_material_at(cx, cy, p.materials[i].id)
        # Save
        from pathlib import Path
        fpath = Path(tmp_path) / "test.ogr"
        p.save(fpath)
        # Reload
        from ogr_core.project import Project
        p2 = Project.load(fpath)
        # Footprints must be present
        for a in p2.region_assignments:
            assert "footprint" in a
            assert len(a["footprint"]) >= 3  # at least 3 vertices
            # Now apply a subdivision and verify inheritance still works
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p2.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(10, 8), Vertex(50, 4)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs2 = p2.resolve_regions()
        assert len(regs2) == 4
        mids = {r.material_id for r in regs2}
        # Three distinct materials still represented in the 4 regions
        assert len(mids) >= 3
