# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.266 (D124) — the unsaturated steady solver reaches its fixed point
when the Picard loop cannot.

The invariant
-------------
A permeability function that drops many decades over a fraction of a
metre makes the Picard map of the steady unsaturated equations cycle for
ever on a fine enough mesh, and no relaxation stops it. When the loop
fails, ``UnsaturatedSeepageSolver._rescue`` looks for the same fixed point
(Anderson acceleration of the Picard map, then continuation in the
steepness solved by Newton's method). What these tests protect:

* **an exact solution is reached that the loop cannot reach.** Gardner
  (1958): for steady infiltration I through a column over a water table,
  with k = Ks exp(a P), the pressure head far above the table is
  P = ln(I/Ks)/a, and the discrete solution reproduces it EXACTLY there,
  because a uniform P gives every element the same k = I. The curve is a
  user-defined one, six decades over 0.4 m: log-linear interpolation of
  two points IS Gardner's exponential. The loop fails here for every
  relaxation from 0.2 to 0.6 (measured), so the column fails without the
  rescue and the answer cannot come from anywhere else.
* **the rescue lands on the loop's own fixed point.** Where the loop
  converges, the rescue started in its place gives the same heads — by
  both of its roads.
* **the case of the defect.** Dam 2 of the groundwater verification
  problem 9 (Bowles 1984; also Chapuis et al. 2001): with the
  toe drain's curve (six decades between 8 and 12 kPa) the manual's mesh
  converges and a finer one runs into a cycle. The finer one must now
  converge, give the coarse one's discharge within 3 % (the criterion of
  the defect) and stay in the band the published discharges span:
  Bowles' flow net 3.8e-6 and the finite-element results 4.23e-6
  m3/(min m), widened by 5 % for the readings of the figure. The curves
  are those of the figure read in m/min (D130), which is why they are
  divided by 60 and the discharge multiplied by 60.

What converged before the rescue must not move: that is guaranteed by
construction (the rescue only runs after the loop has failed) and checked
on the whole groundwater bank, switch on against switch off; it is not a
property a unit test here could prove for every model.

Every test restores the module switches it touches (rule 5).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.mesh.mesh import Element, Mesh, Node  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    UnsaturatedSeepageSolver,
)

GAMMA_W = 9.81


# ======================================================================
# The Gardner column
# ======================================================================
KS = 1.0e-5
RATIO = 1.0e-3          # I / Ks
DECADES, SPAN_M = 6.0, 0.4
A_GARDNER = DECADES * math.log(10.0) / SPAN_M      # 1/m
P_FAR = math.log(RATIO) / A_GARDNER                 # -0.200 m
HEIGHT, DZ, WIDTH = 10.0, 0.25, 0.25


def _column():
    rows = int(round(HEIGHT / DZ))
    nodes = []
    for j in range(rows + 1):
        nodes.append(Node(2 * j, 0.0, j * DZ))
        nodes.append(Node(2 * j + 1, WIDTH, j * DZ))
    elements = []
    for j in range(rows):
        a, b, c, d = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
        elements.append(Element(len(elements), (a, b, c), "m"))
        elements.append(Element(len(elements), (a, c, d), "m"))
    mesh = Mesh(nodes=nodes, elements=elements, target_size=DZ)
    # kPa, as every user-defined curve since v0.1.200 (D121)
    curve = [(0.0, KS), (SPAN_M * GAMMA_W, KS * 10.0 ** (-DECADES))]
    props = {"m": HydraulicProperties(
        ks=KS, model=PermeabilityModel.USER_DEFINED, user_curve=curve)}
    bcs = SeepageBoundaryConditions()
    bcs.add_node(0, BCType.TOTAL_HEAD, 0.0)
    bcs.add_node(1, BCType.TOTAL_HEAD, 0.0)
    bcs.add_segment(2 * rows, 2 * rows + 1, RATIO * KS)
    return mesh, props, bcs


def _solve_column(relaxation=0.5):
    mesh, props, bcs = _column()
    s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W,
                                 relaxation=relaxation, max_iterations=200,
                                 tolerance=1e-6)
    return mesh, s.solve_unsaturated(bcs)


def _far_error(mesh, r):
    return max(abs(r.total_head[i] - mesh.nodes[i].y - P_FAR)
               for i in range(mesh.node_count)
               if mesh.nodes[i].y >= HEIGHT / 2 - 1e-9)


class TestGardnerColumn:
    def test_the_loop_alone_fails_here(self):
        """Without the rescue, the v0.1.265 solver: no convergence."""
        old = seepage.PICARD_RESCUE
        try:
            seepage.PICARD_RESCUE = False
            for w in (0.3, 0.5):
                _mesh, r = _solve_column(relaxation=w)
                assert not r.converged, (w, r.notes)
                assert "rescue" not in r.notes
        finally:
            seepage.PICARD_RESCUE = old

    def test_reaches_gardners_pressure_head(self):
        mesh, r = _solve_column()
        assert r.converged, r.notes
        assert r.notes["rescue"] == "continuation-newton", r.notes
        assert _far_error(mesh, r) < 1e-6, (_far_error(mesh, r), P_FAR)

    def test_the_base_drains_the_infiltration(self):
        """The reaction of the head-fixed base is the outflow, I x width,
        negative (water leaving: v0.1.266 also fixed the comment that
        said the opposite)."""
        _mesh, r = _solve_column()
        assert r.converged, r.notes
        out = r.reactions[0] + r.reactions[1]
        assert abs(out + RATIO * KS * WIDTH) < 1e-6 * RATIO * KS * WIDTH, out


# ======================================================================
# Both roads land on the loop's fixed point
# ======================================================================
L_DAM, H_DAM, K_DAM = 20.0, 12.0, 1.0e-5
H1, H2 = 10.0, 2.0


def _rect_dam():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.geometry.regions import MaterialRegion
    from ogr_fem2d.mesh import generate_mesh
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(L_DAM, 0),
                              Vertex(L_DAM, H_DAM), Vertex(0, H_DAM)],
                    closed=True)
    mesh = generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=0.7)
    b = SeepageBoundaryConditions()
    for nid in sorted(mesh.boundary_node_ids()):
        nd = mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            b.add_node(nid, BCType.TOTAL_HEAD if nd.y <= H1 + 1e-9
                       else BCType.UNKNOWN, H1 if nd.y <= H1 + 1e-9 else 0.0)
        elif abs(nd.x - L_DAM) < 1e-9:
            b.add_node(nid, BCType.TOTAL_HEAD if nd.y <= H2 + 1e-9
                       else BCType.UNKNOWN, H2 if nd.y <= H2 + 1e-9 else 0.0)
        elif abs(nd.y - H_DAM) < 1e-9:
            b.add_node(nid, BCType.UNKNOWN)
    props = {"m": HydraulicProperties(ks=K_DAM,
                                      model=PermeabilityModel.GARDNER,
                                      gardner_a=1.0, gardner_n=3.0)}
    return mesh, props, b


def _dam_solver(mesh, props, max_iterations):
    return UnsaturatedSeepageSolver(mesh, props, relaxation=0.4,
                                    max_iterations=max_iterations,
                                    tolerance=1e-6)


class TestTheRescueKeepsTheFixedPoint:
    _cache: dict = {}

    def _reference(self):
        if "ref" not in self._cache:
            mesh, props, bcs = _rect_dam()
            r = _dam_solver(mesh, props, 400).solve_unsaturated(bcs)
            assert r.converged and "rescue" not in r.notes, r.notes
            self._cache["ref"] = (mesh, props, bcs, r)
        return self._cache["ref"]

    def _rescued(self, depths):
        mesh, props, bcs, ref = self._reference()
        old = seepage.RESCUE_ANDERSON_DEPTHS
        try:
            seepage.RESCUE_ANDERSON_DEPTHS = depths
            r = _dam_solver(mesh, props, 1).solve_unsaturated(bcs)
        finally:
            seepage.RESCUE_ANDERSON_DEPTHS = old
        return ref, r

    def _same(self, ref, r):
        assert r.converged, r.notes
        assert sorted(r.seepage_nodes) == sorted(ref.seepage_nodes)
        # The loop stops on a RELAXED change of 1e-6 (an unrelaxed one of
        # 2.5e-6 at w = 0.4); the rescue on an unrelaxed one of 1e-6.
        d = max(abs(a - b) for a, b in zip(ref.total_head, r.total_head))
        assert d < 1e-4, d

    def test_anderson_road(self):
        ref, r = self._rescued(seepage.RESCUE_ANDERSON_DEPTHS)
        assert r.notes["rescue"].startswith("anderson"), r.notes
        self._same(ref, r)

    def test_continuation_road(self):
        ref, r = self._rescued(())
        assert r.notes["rescue"] == "continuation-newton", r.notes
        self._same(ref, r)

    def test_switched_off_reports_like_before(self):
        mesh, props, bcs, _ref = self._reference()
        old = seepage.PICARD_RESCUE
        try:
            seepage.PICARD_RESCUE = False
            r = _dam_solver(mesh, props, 1).solve_unsaturated(bcs)
        finally:
            seepage.PICARD_RESCUE = old
        assert not r.converged
        assert "rescue" not in r.notes
        assert r.iterations == 1
        assert "neither did the rescue" not in r.notes.get("warning", "")


# ======================================================================
# Dam 2 of the groundwater verification problem 9 (Bowles 1984)
# ======================================================================
#: Geometry of the manual's figure 9.5: 40 m high, slopes 90 / crest 10 /
#: 90, reservoir at 36 m (read to scale), triangular toe drain under the
#: downstream slope from (100, 0) to (139.375, 22.5).
DAM2 = dict(height=40.0, up=90.0, crest=10.0, down=90.0, water=36.0)
DRAIN = [(100.0, 0.0), (139.375, 22.5)]
#: Figure 9.6, k (m/min read as m/s, D130) against matric suction (kPa).
CORE_KPA = [(0.0, 2.0e-7), (10.0, 1.8e-7), (20.0, 1.0e-7), (30.0, 4.0e-8),
            (40.0, 2.0e-8), (50.0, 1.0e-8), (75.0, 2.5e-9), (100.0, 3.0e-10),
            (175.0, 3.0e-11), (250.0, 2.0e-12), (300.0, 2.0e-12)]
DRAIN_KPA = [(0.0, 1.0e-4), (8.0, 1.0e-4), (12.0, 1.0e-10), (25.0, 1.0e-11),
             (300.0, 1.0e-11)]
PUBLISHED = (3.8e-6, 4.23e-6)       # Bowles' flow net; Chapuis et al. 2001
BAND = 0.05


def _dam2_project():
    from shapely.geometry import Polygon
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    g = DAM2
    base = g["up"] + g["crest"] + g["down"]
    outline = [(0.0, 0.0), (base, 0.0), (g["up"] + g["crest"], g["height"]),
               (g["up"], g["height"])]
    p = Project("Bowles dam 2")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in outline], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in DRAIN], closed=False),
        btype=BoundaryType.MATERIAL))

    def curve(pts):
        return [(s, k / 60.0) for s, k in pts]
    mats = []
    for name, pts in (("Drain", DRAIN_KPA), ("Dam", CORE_KPA)):
        m = Material(name=name, unit_weight=20.0, sat_unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
        m.hydraulic = HydraulicProperties(
            ks=pts[0][1] / 60.0, model=PermeabilityModel.USER_DEFINED,
            user_curve=curve(pts))
        mats.append(m)
    p.materials = mats
    (x0, y0), (x1, y1) = DRAIN
    for reg in p.resolve_regions():
        pt = Polygon([(v.x, v.y) for v in reg.polygon.vertices]
                     ).representative_point()
        in_drain = pt.x > x0 and pt.y < y0 + (y1 - y0) * (pt.x - x0) / (x1 - x0)
        p.assign_material_at(pt.x, pt.y, mats[0 if in_drain else 1].id)
    return p


def _dam2_discharge(elements, max_iterations):
    from ogr_fem2d.mesh import generate_mesh_for_project
    g = DAM2
    base = g["up"] + g["crest"] + g["down"]
    p = _dam2_project()
    mesh = generate_mesh_for_project(p, target_elements=elements)
    props = {m.id: m.hydraulic for m in p.materials}
    b = SeepageBoundaryConditions()
    for nid in mesh.boundary_node_ids():
        nd = mesh.nodes[nid]
        y_up = g["height"] * nd.x / g["up"]
        y_down = g["height"] * (base - nd.x) / g["down"]
        if (nd.x <= g["up"] + 1e-6 and abs(nd.y - y_up) < 1e-3
                and nd.y <= g["water"] + 1e-6):
            b.add_node(nid, BCType.TOTAL_HEAD, g["water"])
        elif (nd.x >= g["up"] + g["crest"] - 1e-6
              and abs(nd.y - y_down) < 1e-3):
            b.add_node(nid, BCType.UNKNOWN)
    s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W,
                                 relaxation=0.3,
                                 max_iterations=max_iterations,
                                 tolerance=1e-6)
    r = s.solve_unsaturated(b)
    xc = g["up"] + g["crest"] / 2.0
    q = (60.0 * abs(s.flux_through_segment(r, xc, 0.0, xc, g["height"],
                                           samples=400))
         if r.ok else float("nan"))
    return mesh, r, q


class TestBowlesDam2:
    _cache: dict = {}

    def _runs(self):
        if not self._cache:
            # The manual's mesh: the loop converges on its own.
            self._cache["coarse"] = _dam2_discharge(1000, 300)
            # Four times finer: the loop cycles. A short loop is enough
            # to get there; what is under test is what follows it.
            self._cache["fine"] = _dam2_discharge(4000, 30)
        return self._cache["coarse"], self._cache["fine"]

    def test_the_manual_mesh_needs_no_rescue(self):
        (_m, r, _q), _fine = self._runs()
        assert r.converged and "rescue" not in r.notes, r.notes

    def test_the_fine_mesh_converges(self):
        _coarse, (mesh, r, _q) = self._runs()
        assert mesh.element_count > 3000, mesh.element_count
        assert r.converged, r.notes
        assert "rescue" in r.notes, r.notes
        assert r.notes["unsettled_nodes"] == 0, r.notes

    def test_the_discharge_does_not_depend_on_the_mesh(self):
        (_m, _r, q_coarse), (_m2, _r2, q_fine) = self._runs()
        assert abs(q_fine / q_coarse - 1.0) <= 0.03, (q_fine, q_coarse)

    def test_the_discharge_is_in_the_published_band(self):
        _coarse, (_m, _r, q) = self._runs()
        lo, hi = PUBLISHED
        assert lo * (1 - BAND) <= q <= hi * (1 + BAND), q
