# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.25 — FE mesh generator tests (Phase 1 of the groundwater plan).

Validation strategy: geometric invariants that must hold for ANY correct
conforming mesh, checked on both a synthetic square (where the exact
answer is known analytically) and the reference slope model:

    * **Area conservation** — the summed element area must equal the
      region area exactly. This is the strongest single correctness
      check: it fails if the mesh has gaps, overlaps, or triangles
      leaking outside the domain.
    * **Conformity** — no edge shared by more than two elements.
    * **Quality** — minimum angle above a usable floor, stable across
      refinement levels.
    * **Material assignment** — every element carries the material of
      the region it was generated in, and no element straddles an
      interface (guaranteed by per-region triangulation).
    * **Shape functions** — T3 gradients reproduce a linear field
      exactly, and partition of unity holds.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.regions import MaterialRegion  # noqa: E402
from ogr_fem2d.mesh import Mesh, generate_mesh  # noqa: E402
from ogr_fem2d.mesh.generator import (  # noqa: E402
    _bowyer_watson,
    generate_mesh_for_project,
)


def _square_region(size: float = 10.0, material_id: str = "m1"):
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(size, 0),
                              Vertex(size, size), Vertex(0, size)],
                    closed=True)
    return MaterialRegion(polygon=poly, material_id=material_id)


def _two_stacked_regions():
    """Two squares sharing the horizontal edge y = 10 — exercises
    inter-region conformity."""
    low = Polyline(vertices=[Vertex(0, 0), Vertex(10, 0),
                             Vertex(10, 10), Vertex(0, 10)], closed=True)
    high = Polyline(vertices=[Vertex(0, 10), Vertex(10, 10),
                              Vertex(10, 20), Vertex(0, 20)], closed=True)
    return [MaterialRegion(polygon=low, material_id="bottom"),
            MaterialRegion(polygon=high, material_id="top")]


# ======================================================================
class TestSquareMesh:
    def test_area_conserved_exactly(self):
        m = generate_mesh([_square_region(10.0)], target_size=1.5)
        assert m.element_count > 0
        assert abs(m.total_area() - 100.0) < 1e-6, m.total_area()

    def test_conforming(self):
        m = generate_mesh([_square_region()], target_size=1.5)
        assert m.is_conforming()

    def test_quality_floor(self):
        m = generate_mesh([_square_region()], target_size=1.5,
                          min_angle=25.0)
        q = m.quality_stats()
        # Delaunay of a lattice on a square should be excellent.
        assert q["min_angle"] > 20.0, q["min_angle"]
        assert q["pct_below_20deg"] == 0.0, q["pct_below_20deg"]

    def test_all_elements_positive_area(self):
        m = generate_mesh([_square_region()], target_size=1.5)
        assert all(e.area(m) > 1e-12 for e in m.elements)

    def test_ccw_orientation(self):
        m = generate_mesh([_square_region()], target_size=2.0)
        for e in m.elements:
            (x1, y1), (x2, y2), (x3, y3) = e.coords(m)
            cross = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
            assert cross > 0, e.id

    def test_target_size_controls_density(self):
        coarse = generate_mesh([_square_region()], target_size=3.0)
        fine = generate_mesh([_square_region()], target_size=1.0)
        assert fine.element_count > coarse.element_count * 3

    def test_target_elements_approximately_honoured(self):
        m = generate_mesh([_square_region()], target_elements=400)
        assert 200 <= m.element_count <= 800, m.element_count

    def test_boundary_edges_form_closed_outline(self):
        m = generate_mesh([_square_region(10.0)], target_size=2.0)
        edges = m.boundary_edges()
        # Every boundary node must have exactly two boundary edges
        deg: dict[int, int] = {}
        for u, v in edges:
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
        assert all(d == 2 for d in deg.values()), deg
        # And all boundary nodes lie on the square outline
        for nid in deg:
            n = m.nodes[nid]
            on = (abs(n.x) < 1e-9 or abs(n.x - 10.0) < 1e-9
                  or abs(n.y) < 1e-9 or abs(n.y - 10.0) < 1e-9)
            assert on, (n.x, n.y)


# ======================================================================
class TestInterRegionConformity:
    def test_shared_interface_nodes_are_shared(self):
        m = generate_mesh(_two_stacked_regions(), target_size=1.5)
        assert m.is_conforming()
        assert abs(m.total_area() - 200.0) < 1e-6, m.total_area()

    def test_no_interior_gap_at_interface(self):
        """Nodes on the shared edge y = 10 must not be duplicated: each
        appears in elements of both regions, so the interface generates
        no boundary edges."""
        m = generate_mesh(_two_stacked_regions(), target_size=1.5)
        interface_nodes = {n.id for n in m.nodes if abs(n.y - 10.0) < 1e-9
                           and 1e-9 < n.x < 10.0 - 1e-9}
        assert interface_nodes, "no interface nodes found"
        bnd = set()
        for u, v in m.boundary_edges():
            bnd.add(u)
            bnd.add(v)
        # Interior interface nodes must NOT be on the mesh boundary
        assert not (interface_nodes & bnd), interface_nodes & bnd

    def test_elements_do_not_straddle_interface(self):
        m = generate_mesh(_two_stacked_regions(), target_size=1.5)
        for e in m.elements:
            ys = [m.nodes[i].y for i in e.nodes]
            if e.material_id == "bottom":
                assert max(ys) <= 10.0 + 1e-9, ys
            else:
                assert min(ys) >= 10.0 - 1e-9, ys

    def test_material_ids_preserved(self):
        m = generate_mesh(_two_stacked_regions(), target_size=2.0)
        mats = {e.material_id for e in m.elements}
        assert mats == {"bottom", "top"}, mats


# ======================================================================
class TestShapeFunctions:
    def test_gradients_reproduce_linear_field(self):
        """A T3 must differentiate f = 3x - 2y + 7 exactly."""
        m = generate_mesh([_square_region()], target_size=2.5)
        f = [3.0 * n.x - 2.0 * n.y + 7.0 for n in m.nodes]
        for e in m.elements:
            g = e.shape_gradients(m)
            assert g is not None
            dNdx, dNdy, _a = g
            dfdx = sum(dNdx[k] * f[e.nodes[k]] for k in range(3))
            dfdy = sum(dNdy[k] * f[e.nodes[k]] for k in range(3))
            assert abs(dfdx - 3.0) < 1e-6, dfdx
            assert abs(dfdy + 2.0) < 1e-6, dfdy

    def test_gradient_partition_of_unity(self):
        m = generate_mesh([_square_region()], target_size=3.0)
        for e in m.elements:
            dNdx, dNdy, _a = e.shape_gradients(m)
            assert abs(sum(dNdx)) < 1e-9
            assert abs(sum(dNdy)) < 1e-9

    def test_barycentric_sums_to_one(self):
        m = generate_mesh([_square_region()], target_size=3.0)
        e = m.elements[0]
        cx, cy = e.centroid(m)
        bc = e.barycentric(m, cx, cy)
        assert abs(sum(bc) - 1.0) < 1e-12
        assert all(abs(w - 1.0 / 3.0) < 1e-9 for w in bc)

    def test_interpolation_of_linear_field(self):
        m = generate_mesh([_square_region()], target_size=2.0)
        vals = [2.0 * n.x + 5.0 for n in m.nodes]
        for (px, py) in [(3.3, 4.1), (7.5, 2.2), (5.0, 5.0)]:
            got = m.interpolate(vals, px, py)
            assert got is not None, (px, py)
            assert abs(got - (2.0 * px + 5.0)) < 1e-6, (px, py, got)

    def test_locate_outside_returns_none(self):
        m = generate_mesh([_square_region()], target_size=3.0)
        assert m.locate(-5.0, -5.0) is None


# ======================================================================
class TestReferenceModelMesh:
    def test_mesh_of_reference_slope(self):
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        m = generate_mesh_for_project(p, target_elements=600)
        q = m.quality_stats()
        assert m.element_count > 300
        assert m.is_conforming()
        assert q["min_angle"] > 15.0, q["min_angle"]
        # The model has three material regions
        assert m.notes["regions"] == 3
        assert abs(m.total_area() - m.notes["region_area"]) < 1e-6

    def test_materials_resolved_from_project(self):
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        m = generate_mesh_for_project(p, target_elements=400)
        mats = {e.material_id for e in m.elements}
        assert None not in mats, "unresolved material"
        assert len(mats) == 3, mats

    def test_area_invariant_across_refinement(self):
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        areas = []
        for n in (200, 800, 2000):
            m = generate_mesh_for_project(p, target_elements=n)
            areas.append(m.total_area())
            assert m.is_conforming()
        assert max(areas) - min(areas) < 1e-6, areas

    def test_project_without_external_returns_empty(self):
        from ogr_core.project import Project
        m = generate_mesh_for_project(Project(name="empty"))
        assert m.element_count == 0


# ======================================================================
class TestFallbackTriangulator:
    def test_bowyer_watson_triangulates_square(self):
        pts = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]
        tris = _bowyer_watson(pts)
        assert len(tris) >= 3
        # Total area of the triangulation equals the unit square
        area = 0.0
        for t in tris:
            (x1, y1), (x2, y2), (x3, y3) = (pts[i] for i in t)
            area += 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        assert abs(area - 1.0) < 1e-9, area

    def test_degenerate_input(self):
        assert _bowyer_watson([(0, 0), (1, 1)]) == []


# ======================================================================
class TestSerialisation:
    def test_round_trip(self):
        m = generate_mesh([_square_region()], target_size=2.5)
        m2 = Mesh.from_dict(m.to_dict())
        assert m2.node_count == m.node_count
        assert m2.element_count == m.element_count
        assert abs(m2.total_area() - m.total_area()) < 1e-9
        assert m2.elements[0].material_id == m.elements[0].material_id

    def test_empty_regions(self):
        assert generate_mesh([]).element_count == 0


# ======================================================================
class TestProjectAndGuiIntegration:
    def test_project_round_trip_with_mesh(self):
        from ogr_core.project import Project
        p = Project(name="mesh")
        p.fem_mesh = generate_mesh([_square_region(6.0)], target_size=1.5)
        p2 = Project.from_dict(p.to_dict())
        assert p2.fem_mesh is not None
        assert p2.fem_mesh.element_count == p.fem_mesh.element_count
        assert abs(p2.fem_mesh.total_area() - 36.0) < 1e-6

    def test_project_round_trip_without_mesh(self):
        from ogr_core.project import Project
        p2 = Project.from_dict(Project(name="nomesh").to_dict())
        assert p2.fem_mesh is None

    def test_gui_generates_and_resets_mesh(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            return
        app = QApplication.instance() or QApplication([])
        from test_slide_validation_ej1 import _ej1_project
        from ogr_gui.main_window import MainWindow
        p = _ej1_project()
        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        p.fem_mesh = generate_mesh_for_project(p, target_elements=300)
        w.canvas.refresh_scene()          # must not raise
        assert p.fem_mesh.element_count > 100
        w._reset_fem_mesh()
        assert p.fem_mesh is None
        w.canvas.refresh_scene()
