# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.16 — material-assignment independence after subdivision.

Samuel's bug (v0.1.15): drawing a boundary that splits a region into 4
and 5, then assigning a material to region 5, also painted region 4 —
the two siblings could not hold distinct materials. This happened
because footprint inheritance bled a child's assignment into its
sibling.

The fix distinguishes by the temporal logic encoded in the stored
footprint:
  - assignment made on the ANCESTOR (large footprint) → all children
    inherit;
  - assignment made on a CHILD after subdivision (small footprint) →
    only that child gets it, siblings stay at the default.
"""
from __future__ import annotations


def _rect_project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    p = Project("v116")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 60), Vertex(0, 60),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name=f"M{i}", strength=MohrCoulomb(cohesion=10, friction_angle=20))
        for i in range(1, 4)
    ]
    return p


def _find(regs, pred):
    cands = [r for r in regs if pred(*r.centroid())]
    return min(cands, key=lambda r: r.centroid()[1]) if cands else None


class TestAssignmentIndependence:
    def test_sibling_does_not_inherit_after_subdivide_then_paint(self):
        """Subdivide FIRST, then paint one child: the sibling must keep
        the default material (Samuel's exact bug)."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _rect_project()
        # Three dividing lines (like the screenshot)
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 40), Vertex(100, 40)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(50, 40), Vertex(100, 10)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 20), Vertex(75, 20)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        r5 = _find(regs, lambda x, y: y < 20 and x < 50)
        assert r5 is not None
        # Paint Material 2 onto region 5 only
        p.assign_material_at(*r5.centroid(), p.materials[1].id)
        regs2 = p.resolve_regions()
        r4 = _find(regs2, lambda x, y: 20 < y < 40 and x < 45)
        r5b = _find(regs2, lambda x, y: y < 20 and x < 50)
        m4 = next(m for m in p.materials if m.id == r4.material_id)
        m5 = next(m for m in p.materials if m.id == r5b.material_id)
        assert m5.name == "M2", f"R5 should be M2, got {m5.name}"
        assert m4.name == "M1", (
            f"R4 should stay default M1 (not bleed), got {m4.name}"
        )

    def test_both_children_inherit_when_ancestor_painted_first(self):
        """Paint the ANCESTOR, THEN subdivide: both children inherit."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _rect_project()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 40), Vertex(100, 40)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        bottom = _find(regs, lambda x, y: y < 40)
        # Paint the whole bottom with M3
        p.assign_material_at(*bottom.centroid(), p.materials[2].id)
        # Now subdivide the bottom
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 20), Vertex(100, 20)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs2 = p.resolve_regions()
        for r in regs2:
            cx, cy = r.centroid()
            if cy < 40:
                m = next(mm for mm in p.materials if mm.id == r.material_id)
                assert m.name == "M3", (
                    f"Child at ({cx:.0f},{cy:.0f}) should inherit M3, "
                    f"got {m.name}"
                )

    def test_distinct_materials_to_two_siblings(self):
        """Two siblings created by subdivision can hold distinct
        materials assigned independently."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _rect_project()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 40), Vertex(100, 40)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(50, 40), Vertex(100, 10)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 20), Vertex(75, 20)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        r5 = _find(regs, lambda x, y: y < 20 and x < 50)
        r4 = _find(regs, lambda x, y: 20 < y < 40 and x < 45)
        p.assign_material_at(*r5.centroid(), p.materials[1].id)  # M2
        p.assign_material_at(*r4.centroid(), p.materials[2].id)  # M3
        regs2 = p.resolve_regions()
        r5b = _find(regs2, lambda x, y: y < 20 and x < 50)
        r4b = _find(regs2, lambda x, y: 20 < y < 40 and x < 45)
        m5 = next(m for m in p.materials if m.id == r5b.material_id)
        m4 = next(m for m in p.materials if m.id == r4b.material_id)
        assert m5.name == "M2"
        assert m4.name == "M3"
        assert m4.name != m5.name, "Siblings must hold distinct materials"
