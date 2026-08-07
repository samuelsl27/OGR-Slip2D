# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.6 — Region assignment tests.

These verify the new Slide-style material-painting flow:
    1. Material Boundaries are OPEN polylines (they cut the External).
    2. Regions emerge from planar subdivision (External ∪ Material Bs).
    3. Water Table / Piezometric / TensionCrack / Drawdown do NOT split
       regions.
    4. User clicks are recorded as RegionAssignments on the project.
    5. Assignments survive save/load.
    6. Assignments survive boundary edits if the click-point still lies
       in a (possibly different) region.
    7. The first material of the project is the default for unassigned
       regions (Slide convention).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
    regions_available,
)
from ogr_core.materials import Material, MohrCoulomb
from ogr_core.project import Project
from ogr_core.project.commands import CommandStack, PaintRegionCommand


# Skip the whole module if shapely is unavailable
_SHAPELY = regions_available()


def _build_slope_with_horizontal_cut():
    """50x20 trapezoidal External + horizontal Material boundary at y=10."""
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
        Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    mat_line = Polyline(
        vertices=[Vertex(0, 10), Vertex(50, 10)], closed=False,
    )
    p = Project("Region test")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=mat_line, btype=BoundaryType.MATERIAL))
    p.materials = [
        Material(name="Silty clay", unit_weight=18, sat_unit_weight=19,
                 strength=MohrCoulomb(cohesion=10, friction_angle=25)),
        Material(name="Gravel", unit_weight=20, sat_unit_weight=21,
                 strength=MohrCoulomb(cohesion=0, friction_angle=35)),
    ]
    return p


class TestOpenMaterialBoundary:
    """Material Boundaries are always open; External auto-closes."""

    def test_tool_mode_only_external_is_closed(self):
        # Import via explicit module file to avoid pulling in the Qt
        # dependency (tool_mode.py itself is pure-Python).
        import importlib.util
        from pathlib import Path
        tm_path = Path(__file__).parent.parent / "ogr_gui" / "canvas" / "tool_mode.py"
        spec = importlib.util.spec_from_file_location("_tm", tm_path)
        tm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tm)
        assert tm.ToolMode.DRAW_EXTERNAL.draws_closed_polygon is True
        assert tm.ToolMode.DRAW_MATERIAL.draws_closed_polygon is False
        assert tm.ToolMode.DRAW_WATER_TABLE.draws_closed_polygon is False


class TestRegionResolution:
    """Regions emerge from planar subdivision."""

    def test_no_external_no_regions(self):
        if not _SHAPELY:
            return
        p = Project("Empty")
        assert p.resolve_regions() == []

    def test_two_regions_from_horizontal_cut(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        regions = p.resolve_regions()
        assert len(regions) == 2

    def test_water_table_does_not_split_regions(self):
        """Adding a water table must NOT create new regions."""
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        n_before = len(p.resolve_regions())
        wt = Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, 8), Vertex(50, 8)], closed=False
            ),
            btype=BoundaryType.WATER_TABLE,
        )
        p.add_boundary(wt)
        n_after = len(p.resolve_regions())
        assert n_before == n_after

    def test_piezometric_does_not_split_regions(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        n_before = len(p.resolve_regions())
        piezo = Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, 12), Vertex(50, 12)], closed=False
            ),
            btype=BoundaryType.PIEZOMETRIC,
        )
        p.add_boundary(piezo)
        assert len(p.resolve_regions()) == n_before


class TestClickAssignment:
    """User clicks become RegionAssignments."""

    def test_default_material_is_first(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        # Unpainted region resolves to the first material
        mat = p.material_at(25, 5)
        assert mat is not None
        assert mat.name == "Silty clay"

    def test_click_paints_region(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        gravel = p.materials[1]
        ok = p.assign_material_at(25, 5, gravel.id)
        assert ok is True
        mat = p.material_at(25, 5)
        assert mat is not None
        assert mat.name == "Gravel"
        # Upper region untouched
        assert p.material_at(25, 20).name == "Silty clay"

    def test_click_outside_any_region_rejected(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        ok = p.assign_material_at(200, 200, p.materials[1].id)
        assert ok is False

    def test_assignment_survives_save_load(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        gravel = p.materials[1]
        p.assign_material_at(25, 5, gravel.id)
        with tempfile.NamedTemporaryFile(suffix=".ogr", delete=False) as f:
            tmp = Path(f.name)
        try:
            p.save(tmp)
            p2 = Project.load(tmp)
        finally:
            tmp.unlink()
        assert p2.material_at(25, 5).name == "Gravel"


class TestPaintRegionCommand:
    """Undo/redo integration."""

    def test_command_paints_then_undo_reverts(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        stack = CommandStack()
        gravel = p.materials[1]
        stack.do(p, PaintRegionCommand(x=25, y=5, material_id=gravel.id))
        assert p.material_at(25, 5).name == "Gravel"
        stack.undo(p)
        # Back to the default (first material)
        assert p.material_at(25, 5).name == "Silty clay"

    def test_command_repaint_same_point_replaces(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        stack = CommandStack()
        silty, gravel = p.materials
        stack.do(p, PaintRegionCommand(x=25, y=5, material_id=gravel.id))
        stack.do(p, PaintRegionCommand(x=25, y=5, material_id=silty.id))
        assert p.material_at(25, 5).name == "Silty clay"
        # Only one entry in the assignment list
        assert len(p.region_assignments) == 1
        # Undo restores gravel (the previous assignment at this point)
        stack.undo(p)
        assert p.material_at(25, 5).name == "Gravel"


class TestBoundaryEditsPreserveAssignments:
    """If the user moves a boundary, assignments survive when the
    click-point still lies in some region."""

    def test_moving_cut_line_preserves_assignment_if_click_still_inside(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        gravel = p.materials[1]
        p.assign_material_at(25, 5, gravel.id)
        # Move the horizontal cut from y=10 up to y=15 — our click at
        # (25, 5) is still in the bottom region. Vertex is a frozen
        # dataclass, so we replace the list elements rather than mutate.
        mat_b = p.boundaries_of(BoundaryType.MATERIAL)[0]
        verts = mat_b.polyline.vertices
        verts[0] = Vertex(verts[0].x, 15)
        verts[1] = Vertex(verts[1].x, 15)
        assert p.material_at(25, 5).name == "Gravel"

    def test_prune_stale_assignments_removes_orphans(self):
        if not _SHAPELY:
            return
        p = _build_slope_with_horizontal_cut()
        # Assign somewhere inside
        p.assign_material_at(25, 5, p.materials[1].id)
        # Manually inject a stale assignment outside
        p.region_assignments.append(
            {"x": 999, "y": 999, "material_id": p.materials[1].id}
        )
        pruned = p.prune_stale_assignments()
        assert pruned == 1
        assert len(p.region_assignments) == 1


# ======================================================================
# v0.1.7 — regression: more than 2 materials must produce N+1 regions
# ======================================================================
class TestMultipleMaterialBoundaries:
    """Reproduce v0.1.6 bug: 3+ Material Boundaries only created 2 regions."""

    def test_three_horizontal_cuts_make_four_regions(self):
        if not _SHAPELY:
            # The pure-Python fallback is what we actually fixed
            pass
        from ogr_core.geometry import (
            Boundary as _B,
            BoundaryType as _BT,
            Polyline as _PL,
            Vertex as _V,
            build_regions,
        )
        ext = _PL(vertices=[_V(0,0), _V(50,0), _V(50,30), _V(0,30)], closed=True)
        ext.ensure_ccw()
        ext_b = _B(polyline=ext, btype=_BT.EXTERNAL)
        ms = [
            _B(polyline=_PL(vertices=[_V(0, y), _V(50, y)], closed=False),
               btype=_BT.MATERIAL)
            for y in (8, 16, 24)
        ]
        assert len(build_regions(ext_b, ms)) == 4

    def test_five_horizontal_cuts_make_six_regions(self):
        from ogr_core.geometry import (
            Boundary as _B,
            BoundaryType as _BT,
            Polyline as _PL,
            Vertex as _V,
            build_regions,
        )
        ext = _PL(vertices=[_V(0,0), _V(50,0), _V(50,30), _V(0,30)], closed=True)
        ext.ensure_ccw()
        ms = [_B(polyline=_PL(vertices=[_V(0,5*i), _V(50,5*i)], closed=False),
                  btype=_BT.MATERIAL) for i in range(1, 6)]
        assert len(build_regions(_B(polyline=ext, btype=_BT.EXTERNAL), ms)) == 6

    def test_horizontal_plus_vertical_makes_four_quadrants(self):
        from ogr_core.geometry import (
            Boundary as _B,
            BoundaryType as _BT,
            Polyline as _PL,
            Vertex as _V,
            build_regions,
        )
        ext = _PL(vertices=[_V(0,0), _V(50,0), _V(50,30), _V(0,30)], closed=True)
        ext.ensure_ccw()
        h = _B(polyline=_PL(vertices=[_V(0,15), _V(50,15)], closed=False), btype=_BT.MATERIAL)
        v = _B(polyline=_PL(vertices=[_V(25,0), _V(25,30)], closed=False), btype=_BT.MATERIAL)
        assert len(build_regions(_B(polyline=ext, btype=_BT.EXTERNAL), [h, v])) == 4

    def test_assign_three_different_materials_to_three_regions(self):
        """Direct project-level test that mimics user click flow."""
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.geometry import (
            Boundary as _B,
            BoundaryType as _BT,
            Polyline as _PL,
            Vertex as _V,
        )
        from ogr_core.project import Project
        p = Project("MultiMat")
        ext = _PL(vertices=[_V(0,0), _V(50,0), _V(50,30), _V(0,30)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(_B(polyline=ext, btype=_BT.EXTERNAL))
        for y in (10, 20):
            p.add_boundary(_B(
                polyline=_PL(vertices=[_V(0,y), _V(50,y)], closed=False),
                btype=_BT.MATERIAL,
            ))
        p.materials = [
            Material(name="A", strength=MohrCoulomb(cohesion=10, friction_angle=20)),
            Material(name="B", strength=MohrCoulomb(cohesion=15, friction_angle=25)),
            Material(name="C", strength=MohrCoulomb(cohesion=20, friction_angle=30)),
        ]
        # Click in each of the 3 regions
        assert p.assign_material_at(25, 5, p.materials[2].id) is True   # bottom
        assert p.assign_material_at(25, 15, p.materials[1].id) is True  # middle
        assert p.assign_material_at(25, 25, p.materials[0].id) is True  # top
        assert p.material_at(25, 5).name == "C"
        assert p.material_at(25, 15).name == "B"
        assert p.material_at(25, 25).name == "A"


# ======================================================================
# v0.1.9 — crossing material boundaries (planar subdivision via faces)
# ======================================================================
class TestCrossingBoundaries:
    """v0.1.8 algorithm gave wrong region count for crossing boundaries.
    v0.1.9 uses a half-edge planar subdivision that handles arbitrary
    crossings."""

    def _make(self, mat_polylines):
        from ogr_core.geometry import (
            Boundary as _B,
            BoundaryType as _BT,
            Polyline as _PL,
            Vertex as _V,
        )
        from ogr_core.project import Project
        p = Project("xtest")
        ext = _PL(vertices=[_V(0, 0), _V(50, 0), _V(50, 30), _V(0, 30)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(_B(polyline=ext, btype=_BT.EXTERNAL))
        for verts in mat_polylines:
            p.add_boundary(_B(polyline=_PL(vertices=verts, closed=False),
                              btype=_BT.MATERIAL))
        return p

    def test_two_crossing_diagonals_give_four_regions(self):
        from ogr_core.geometry import Vertex as _V
        p = self._make([
            [_V(0, 5), _V(50, 25)],
            [_V(0, 25), _V(50, 5)],
        ])
        assert len(p.resolve_regions()) == 4

    def test_horizontal_plus_full_diagonal_four_regions(self):
        from ogr_core.geometry import Vertex as _V
        p = self._make([
            [_V(0, 15), _V(50, 15)],
            [_V(5, 0), _V(45, 30)],
        ])
        assert len(p.resolve_regions()) == 4

    def test_v_shape_inside_two_regions(self):
        from ogr_core.geometry import Vertex as _V
        p = self._make([
            [_V(0, 20), _V(25, 5), _V(50, 20)],
        ])
        assert len(p.resolve_regions()) == 2

    def test_no_cuts_one_region(self):
        p = self._make([])
        assert len(p.resolve_regions()) == 1
