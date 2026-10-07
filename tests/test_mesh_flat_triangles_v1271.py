# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.271 (D270) — the mesh generator no longer leaves flat triangles, and a
mesh that still has them (saved by an earlier version) is reported.

The defect
----------
Each region is triangulated by an unconstrained Delaunay of its boundary
and interior points. Where several boundary nodes are collinear on an edge
of the region's outline that is also an edge of their convex hull, Qhull
closes the hull with triangles of zero area, and the centroid filter keeps
them by rounding. On the verification bank: 7 on the slope face of
05-007 / 05-020, 16 on the slope face of 02-038, 7 on dam 2 of 05-009 at
1500 elements. The damage is topological: the long edge of a fan of flat
triangles is what the mesh counts as boundary, so the nodes under it are
not boundary nodes (Euler's V - E + F was 0, -3 and -4) and never get the
seepage-face condition; and on a domain metres across, the flat element
passes the absolute 1e-15 of ``shape_gradients`` and enters the matrix
~1e15 times stiffer than its neighbours. The seepage of 02-038 never
converged; repaired, it converges in all twelve of its combinations.

The invariants (identities, not snapshots)
------------------------------------------
For a generated mesh: every edge belongs to one or two elements; every node
belongs to some element; no node lies inside a boundary edge; V - E + F = 1
for a domain without holes; the areas add up to the regions' area; and no
element is flat (minimum angle above 1 degree). Checked on dam 2 of 05-009
at 1500 elements, the mesh of the defect.

How many flat triangles Qhull makes depends on its version, so that count
is not pinned; the repair itself is checked on hand-made meshes with both
shapes a flat fan takes, which do not depend on Qhull. A mesh with no flat
triangle comes out of the generator identical with the repair on and off.
The solvers report a mesh with flat elements (``degenerate_elements``,
``mesh_warning``) and do not skip them. The module switch is restored in
``finally`` (rule 5).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_fem2d.mesh import generate_mesh_for_project, generator  # noqa: E402
from ogr_fem2d.mesh.generator import _repair_flat_triangles  # noqa: E402
from ogr_fem2d.mesh.mesh import Element, Mesh, Node  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    SeepageSolver,
)


def _dam2_project():
    spec = importlib.util.spec_from_file_location(
        "t1266_d270", Path(__file__).parent / "test_picard_steep_curve_v1266.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    return t._dam2_project()


def _identities(mesh):
    """The topological identities of a T3 mesh of a domain without holes."""
    em = mesh.edge_map()
    used = {i for e in mesh.elements for i in e.nodes}
    boundary = [k for k, v in em.items() if len(v) == 1]
    inside = 0
    for u, v in boundary:
        (x1, y1), (x2, y2) = ((mesh.nodes[i].x, mesh.nodes[i].y) for i in (u, v))
        L2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
        for i in used - {u, v}:
            x, y = mesh.nodes[i].x, mesh.nodes[i].y
            if abs((x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)) <= 1e-9 * L2:
                t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / L2
                if 1e-9 < t < 1 - 1e-9:
                    inside += 1
    return {"edges_with_3_or_more": sum(1 for v in em.values() if len(v) > 2),
            "unused_nodes": mesh.node_count - len(used),
            "nodes_inside_boundary_edges": inside,
            "euler": len(used) - len(em) + mesh.element_count,
            "min_angle": min(e.min_angle_deg(mesh) for e in mesh.elements)}


def _fingerprint(mesh):
    return (tuple((n.x, n.y) for n in mesh.nodes),
            tuple((e.nodes, e.region_index) for e in mesh.elements))


_CACHE: dict = {}


def _dam2_mesh():
    if "dam2" not in _CACHE:
        _CACHE["dam2"] = generate_mesh_for_project(_dam2_project(),
                                                   target_elements=1500)
    return _CACHE["dam2"]


class TestTheMeshOfTheDefect:
    def test_it_is_a_valid_triangulation(self):
        mesh = _dam2_mesh()
        ids = _identities(mesh)
        assert ids["edges_with_3_or_more"] == 0, ids
        assert ids["unused_nodes"] == 0, ids
        assert ids["nodes_inside_boundary_edges"] == 0, ids
        assert ids["euler"] == 1, ids

    def test_no_element_is_flat(self):
        mesh = _dam2_mesh()
        assert _identities(mesh)["min_angle"] > 1.0
        assert mesh.degenerate_elements() == []

    def test_the_area_is_the_regions_area(self):
        mesh = _dam2_mesh()
        ref = mesh.notes["region_area"]
        assert abs(mesh.total_area() - ref) <= 1e-12 * ref


class TestTheRepair:
    """Hand-made: a strip [0, 4] x [0, 2] whose bottom edge carries the
    collinear nodes b0..b4, closed the two ways Qhull closes such a run."""

    @staticmethod
    def _nodes():
        pts = [(i, 0.0) for i in range(5)] + [(0.0, 2.0), (4.0, 2.0), (2.0, 1.0)]
        return [Node(k, float(x), float(y)) for k, (x, y) in enumerate(pts)]

    B0, B1, B2, B3, B4, T0, T1, C = range(8)
    REAL = [(B4, T1, C), (T1, T0, C), (T0, B0, C)]

    def _mesh(self, tris):
        nodes = self._nodes()
        els = [Element(k, t, "m", 0) for k, t in enumerate(tris)]
        return Mesh(nodes=nodes, elements=els, target_size=1.0)

    def _repaired(self, tris):
        m = self._mesh(tris)
        els, n = _repair_flat_triangles(m.nodes, m.elements)
        return Mesh(nodes=m.nodes, elements=els, target_size=1.0), n

    def test_flat_triangles_outside_the_real_ones_are_removed(self):
        # the real triangles use every bottom node; flat ones close the hull
        real = self.REAL + [(self.B0, self.B1, self.C), (self.B1, self.B2, self.C),
                            (self.B2, self.B3, self.C), (self.B3, self.B4, self.C)]
        flat = [(self.B0, self.B2, self.B1), (self.B2, self.B4, self.B3),
                (self.B0, self.B4, self.B2)]
        before = self._mesh(real + flat)
        # the defect's signature: the long flat edge b0-b4 is the boundary,
        # and b1, b2, b3 lie inside it
        assert _identities(before)["nodes_inside_boundary_edges"] == 3
        assert len(before.degenerate_elements()) == 3
        m, n = self._repaired(real + flat)
        assert n == 3 and m.element_count == 7
        ids = _identities(m)
        assert ids["euler"] == 1 and ids["nodes_inside_boundary_edges"] == 0
        assert ids["min_angle"] > 1.0
        assert math.isclose(m.total_area(), 8.0)

    def test_a_long_edge_over_the_run_is_split_as_a_fan(self):
        # the real triangle uses the long edge b0-b4; b1..b3 hang in flats
        real = self.REAL + [(self.B0, self.B4, self.C)]
        flat = [(self.B0, self.B1, self.B4), (self.B1, self.B2, self.B4),
                (self.B2, self.B3, self.B4)]
        before = self._mesh(real + flat)
        # the defect's signature here: b1, b2, b3 touch flat elements only
        flat_ids = set(before.degenerate_elements())
        only_flat = {i for i in range(before.node_count)
                     if all(e.id in flat_ids for e in before.elements
                            if i in e.nodes)
                     and any(i in e.nodes for e in before.elements)}
        assert only_flat == {self.B1, self.B2, self.B3}
        m, n = self._repaired(real + flat)
        assert n == 3
        ids = _identities(m)
        assert ids == {**ids, "edges_with_3_or_more": 0, "unused_nodes": 0,
                       "nodes_inside_boundary_edges": 0, "euler": 1}, ids
        assert ids["min_angle"] > 1.0
        # the fan from C: b0-b1, b1-b2, b2-b3, b3-b4 are boundary edges now
        bnd = {tuple(sorted(k)) for k in m.boundary_edges()}
        for a, b in ((self.B0, self.B1), (self.B1, self.B2),
                     (self.B2, self.B3), (self.B3, self.B4)):
            assert (a, b) in bnd
        assert math.isclose(m.total_area(), 8.0)

    def test_every_element_stays_counter_clockwise(self):
        real = self.REAL + [(self.B0, self.B4, self.C)]
        flat = [(self.B0, self.B1, self.B4), (self.B1, self.B2, self.B4),
                (self.B2, self.B3, self.B4)]
        m, _n = self._repaired(real + flat)
        for e in m.elements:
            (x1, y1), (x2, y2), (x3, y3) = e.coords(m)
            assert (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) > 0, e

    def test_a_mesh_without_flat_triangles_is_returned_as_is(self):
        real = self.REAL + [(self.B0, self.B1, self.C), (self.B1, self.B2, self.C),
                            (self.B2, self.B3, self.C), (self.B3, self.B4, self.C)]
        m = self._mesh(real)
        els, n = _repair_flat_triangles(m.nodes, m.elements)
        assert n == 0 and els is m.elements


class TestASoundMeshIsNotTouched:
    def test_the_generator_gives_the_same_mesh_with_the_repair_off(self):
        old = generator.FLAT_TRIANGLE_REPAIR
        try:
            generator.FLAT_TRIANGLE_REPAIR = False
            off = generate_mesh_for_project(_dam2_project(), target_elements=1000)
            generator.FLAT_TRIANGLE_REPAIR = True
            on = generate_mesh_for_project(_dam2_project(), target_elements=1000)
        finally:
            generator.FLAT_TRIANGLE_REPAIR = old
        assert on.degenerate_elements() == []
        assert _fingerprint(on) == _fingerprint(off)
        assert "flat_triangles_repaired" not in on.notes


class TestTheSolverReportsAnOldMesh:
    def _solve(self, mesh):
        bcs = SeepageBoundaryConditions()
        bcs.add_node(TestTheRepair.T0, BCType.TOTAL_HEAD, 3.0)
        bcs.add_node(TestTheRepair.T1, BCType.TOTAL_HEAD, 2.0)
        return SeepageSolver(mesh).solve(bcs)

    def test_flat_elements_are_counted_and_warned(self):
        """Flat triangles outside the real ones: the solve goes through,
        and says the mesh has them."""
        t = TestTheRepair()
        real = t.REAL + [(t.B0, t.B1, t.C), (t.B1, t.B2, t.C),
                         (t.B2, t.B3, t.C), (t.B3, t.B4, t.C)]
        flat = [(t.B0, t.B2, t.B1), (t.B2, t.B4, t.B3), (t.B0, t.B4, t.B2)]
        r = self._solve(t._mesh(real + flat))
        assert r.converged
        assert r.notes["degenerate_elements"] == 3
        assert "Regenerate the mesh" in r.notes["mesh_warning"]

    def test_a_failure_they_cause_carries_the_reason(self):
        """Nodes that only flat elements touch have no conductivity: the
        system is singular, and the failed result says why."""
        t = TestTheRepair()
        real = t.REAL + [(t.B0, t.B4, t.C)]
        flat = [(t.B0, t.B1, t.B4), (t.B1, t.B2, t.B4), (t.B2, t.B3, t.B4)]
        r = self._solve(t._mesh(real + flat))
        assert not r.ok
        assert r.notes["degenerate_elements"] == 3
        assert "Regenerate the mesh" in r.notes["mesh_warning"]

    def test_a_sound_mesh_gets_no_note(self):
        t = TestTheRepair()
        real = t.REAL + [(t.B0, t.B4, t.C)]
        flat = [(t.B0, t.B1, t.B4), (t.B1, t.B2, t.B4), (t.B2, t.B3, t.B4)]
        m, _n = t._repaired(real + flat)
        r = self._solve(m)
        assert r.converged
        assert "degenerate_elements" not in r.notes
        assert "mesh_warning" not in r.notes
