# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.358 (D356) — a Picard loop that stops with the seepage face unsettled
hands the run to the rescue.

The defect
----------
The loop of ``UnsaturatedSeepageSolver.solve_unsaturated`` stops when the
relaxed change is below the tolerance and the face set has stopped
changing. A node frozen by the switch budget cannot change the set, so the
loop could stop with a frozen node held at P = 0 while water went in. The
final check reported the face unsettled and the run unconverged, and the
rescue (D124, D285), which ran only after a loop that failed, was never
tried.

It reaches the groundwater door. Dam 2 of Bowles (1984), the toe-drain
earth dam that Chapuis et al. (2001) model, meshed with 1000 target
elements and solved with the door's settings (w = 0.4, 200 passes,
tolerance 1e-5): the loop stops with a node of the drain's face held while
water goes in at 35 times the flow through the dam, and the run comes out
unconverged, with no discharge and the free surface 3 to 4 m high.

The fix, and the owner's decision
---------------------------------
``LOOP_SETTLED_FACE``: the loop's final state is asked before the loop is
believed; when its face is unsettled, the rescue runs with Anderson
started from the loop's face WITHOUT its frozen nodes, and if no road
settles the face the loop's own state is published, as before. Started
from the loop's face as it was, the rescue published as converged, once in
14 cases forced with a starved budget, a face admissible within the bands
but not the answer: a node held in dry ground, 4.2 cm off (measured in the
bank, ``_auditoria/P6_0358``).

Whether the door's loop stops is decided by round-off (v0.1.361)
-----------------------------------------------------------------
On dam 2 the loop stops on the edge of the tolerance: its last relaxed
change is 6e-6 to 9.9e-6 against 1e-5. A machine that rounds differently
can keep it cycling to the 200th pass instead, and then the loop has simply
failed and the rescue runs switched on or off. The continuous integration
on Python 3.12 did exactly that, while 3.11, 3.13 and Windows stopped with
the face unsettled. Emulated here by moving w a few units in the last place
(_auditoria/P6_0361 of the bank): of 9 runs, 7 stop with the face unsettled
and 2 (w moved by 2 ulp either way) cycle and are rescued. The toe-drain
dam of Harr with a switch budget of 1 stops with the face unsettled in all
9, identically. So the switch is shown to move the number on Harr's dam,
and at the door only what holds in both regimes is asked.

The invariants
--------------
* switched off, the defect, on Harr's dam with a budget of 1: the loop
  stopped (its last relaxed change is below the tolerance) with the face
  unsettled, no rescue ran and the run is unconverged. Rule 7: the switch
  moves the number it exists for;
* switched off at the door, the run is never published converged with the
  face unsettled: either the loop stopped with it unsettled, and the run is
  unconverged, with no rescue and no discharge, or the loop failed and the
  rescue settled it;
* switched on, the rescue settles it: converged, every face node obeys the
  condition (checked here with the solver's bands, not its
  ``_unsettled_nodes``), and the discharge is the published one, 4.23e-6
  m3/(min m) (Chapuis et al. 2001), within 1 % -- measured -0.46 %. Rule 1,
  an external value: on this dam no road of the solver converges but the
  continuation (D124), so there is no other road to compare with;
* the toe-drain dam of Harr (1990) with a switch budget of 1 lands on the
  fixed point the loop reaches ALONE with the default budget, with the same
  face and the heads within the loop's tol / w (measured 1.7e-6 m): the
  case that separates the start without frozen nodes from the start with
  them;
* when no road settles the face (the dam of ``test_transient_coupling_v1125``
  with a budget of 1), the state published is the loop's, to the bit, still
  unconverged, with the rescue "failed"; only the iteration count and the
  published series grow;
* a loop that converges with its face settled does the same arithmetic
  switched on and off.

The slow-relaxation case of the defect (the Gardner dam at w = 0.1 with a
budget of 25) is in ``test_picard_tolerance_v1272``.

Cost: about 90 s; the rescued dam 2 alone takes 30, the continuation being
the only road that converges there. Every test restores the switch it
touches (rule 5).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    SeepageSolver,
    UnsaturatedSeepageSolver,
)
from ogr_slip2d.transient_stability import (  # noqa: E402
    STEADY_MAX_ITERATIONS,
    STEADY_RELAXATION,
    STEADY_TOLERANCE,
)

GAMMA_W = 9.81
_CACHE: dict = {}


def _module(name):
    """Another test module of this suite, for its cases."""
    if name not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t1358_" + name, Path(__file__).parent / (name + ".py"))
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        _CACHE[name] = t
    return _CACHE[name]


def _solve(mesh, props, bcs, on, **kw):
    """``solve_unsaturated`` with ``LOOP_SETTLED_FACE`` set to ``on`` for
    the run; (solver, result)."""
    old = seepage.LOOP_SETTLED_FACE
    try:
        seepage.LOOP_SETTLED_FACE = on
        s = UnsaturatedSeepageSolver(mesh, props, **kw)
        return s, s.solve_unsaturated(bcs)
    finally:
        seepage.LOOP_SETTLED_FACE = old


def _breaches(mesh, props, bcs, r):
    """Face nodes whose condition the published field breaks, with the
    solver's bands: p_tol from the element size, q_tol from the largest
    nodal flux of the saturated solve. A node held at P = 0 must not take
    water in; a free one must not be under pressure."""
    s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W)
    p_tol = s._face_p_tol()
    first = SeepageSolver(mesh, props, gamma_w=GAMMA_W).solve(bcs)
    q_tol = s._face_q_tol(max(abs(q) for q in first.reactions))
    held = set(r.seepage_nodes or [])
    out = []
    for b in bcs.nodes:
        if b.bc_type != BCType.UNKNOWN:
            continue
        i = b.node_id
        if i in held:
            if r.reactions[i] > q_tol:
                out.append(i)
        elif r.total_head[i] - mesh.nodes[i].y > p_tol:
            out.append(i)
    return out


def _max_dh(a, b):
    return max(abs(x - y) for x, y in zip(a.total_head, b.total_head))


# ======================================================================
# Dam 2 of Bowles (1984), with the toe drain of Chapuis et al. (2001)
# ======================================================================
#: Crest at 45 m between x = 90 and 100, both slopes 2:1, the reservoir at
#: 40 m; the drain is the toe below the line from (100, 0) to (145, 22.5).
#: Geometry measured on the reference's figures (the bank's D358).
DAM2 = [(0.0, 0.0), (190.0, 0.0), (100.0, 45.0), (90.0, 45.0)]
DRAIN_LINE = [(100.0, 0.0), (145.0, 22.5)]
WATER = 40.0
#: Suction (kPa) against k, the core and the drain, read from the vector
#: traces of the reference's figure (D358). Its k is per MINUTE although
#: its axis says per second: only per minute gives the published flow-net
#: ratio q/(k H) = 0.47 (the bank's D130). The model takes it per second,
#: so the curves are divided by 60 and the discharge multiplied back.
CORE = [(0.0, 1.95e-07), (7.84, 1.95e-07), (15.67, 1.53e-07),
        (19.59, 8.89e-08), (24.53, 5.89e-08), (27.43, 2.72e-08),
        (39.18, 1.2e-08), (50.0, 4.65e-09), (70.03, 1.19e-09),
        (91.03, 4.63e-10), (100.0, 3.07e-10), (174.96, 2.98e-11),
        (250.0, 1.81e-12), (300.0, 1.81e-12)]
DRAIN = [(0.0, 1e-4), (6.9, 1e-4), (9.8, 1e-10), (24.53, 1e-11),
         (50.0, 1e-11), (300.0, 1e-11)]
PER_MINUTE = 60.0
#: Chapuis et al. (2001), 2328 elements, m3/(min m); Bowles' flow net
#: gives 3.8e-6.
Q_PUBLISHED = 4.23e-6
ELEMENTS, T3 = 1000, 955


def _dam2():
    if "dam2" not in _CACHE:
        from shapely.geometry import Polygon

        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_fem2d.mesh import generate_mesh_for_project
        p = Project("toe-drain dam 2")
        ext = Polyline(vertices=[Vertex(x, y) for x, y in DAM2], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(x, y) for x, y in DRAIN_LINE],
                              closed=False),
            btype=BoundaryType.MATERIAL))
        mats = []
        for name, curve in (("Drain", DRAIN), ("Dam", CORE)):
            m = Material(name=name, unit_weight=20.0, sat_unit_weight=20.0,
                         strength=MohrCoulomb(cohesion=10.0,
                                              friction_angle=30.0))
            k = [(kpa, v / PER_MINUTE) for kpa, v in curve]
            m.hydraulic = HydraulicProperties(
                ks=k[0][1], model=PermeabilityModel.USER_DEFINED,
                user_curve=k)
            mats.append(m)
        p.materials = mats
        (x0, y0), (x1, y1) = DRAIN_LINE
        for reg in p.resolve_regions():
            pt = Polygon([(v.x, v.y) for v in reg.polygon.vertices]
                         ).representative_point()
            drain = pt.x > x0 and pt.y < y0 + (y1 - y0) * (pt.x - x0) / (x1 - x0)
            p.assign_material_at(pt.x, pt.y, mats[0 if drain else 1].id)
        mesh = generate_mesh_for_project(p, target_elements=ELEMENTS)
        props = {m.id: m.hydraulic for m in p.materials}
        _CACHE["dam2"] = (mesh, props, _dam2_bcs(mesh))
    return _CACHE["dam2"]


def _dam2_bcs(mesh):
    """The reservoir's head on the upstream slope up to the water; the
    downstream slope free to seep; the base and the rest impervious."""
    b = SeepageBoundaryConditions()
    ids = sorted(mesh.boundary_node_ids())
    for i in ids:
        x, y = mesh.nodes[i].x, mesh.nodes[i].y
        if x <= 90.0 + 1e-6 and abs(y - 0.5 * x) < 1e-3 and y <= WATER + 1e-6:
            b.add_node(i, BCType.TOTAL_HEAD, WATER)
    for i in ids:
        x, y = mesh.nodes[i].x, mesh.nodes[i].y
        if x >= 100.0 - 1e-6 and abs(y - 0.5 * (190.0 - x)) < 1e-3:
            b.add_node(i, BCType.UNKNOWN)
    return b


def _door(on):
    """Dam 2 solved with the groundwater door's settings."""
    key = ("door", on)
    if key not in _CACHE:
        mesh, props, bcs = _dam2()
        _CACHE[key] = _solve(mesh, props, bcs, on, gamma_w=GAMMA_W,
                             relaxation=STEADY_RELAXATION,
                             max_iterations=STEADY_MAX_ITERATIONS,
                             tolerance=STEADY_TOLERANCE)
    return _CACHE[key]


def _discharge(s, r):
    """m3/(min m) through the vertical under the middle of the crest; NaN
    for a field that did not converge (``flux_through_segment``)."""
    return abs(s.flux_through_segment(r, 95.0, 0.0, 95.0, 45.0,
                                      samples=400)) * PER_MINUTE


class TestTheDoorOnDam2:
    def test_the_mesh_is_the_one_measured(self):
        mesh, _props, _bcs = _dam2()
        assert mesh.element_count == T3, (
            "not the mesh this case was measured on", mesh.element_count)

    def test_switched_off_it_is_never_published_settled_when_it_is_not(self):
        """Two regimes, chosen by round-off (see the module's docstring)."""
        mesh, props, bcs = _dam2()
        s, r = _door(False)
        if r.notes["picard_delta"] < STEADY_TOLERANCE:      # the loop stopped
            assert r.converged is False
            assert "rescue" not in r.notes, r.notes
            assert r.notes["unsettled_nodes"] >= 1
            assert r.notes["warning"].code == "seepage.face_unsettled"
            assert math.isnan(_discharge(s, r))
        else:                                              # the loop failed
            assert r.notes["rescue"] == "continuation-newton", r.notes
            assert r.converged and r.notes["unsettled_nodes"] == 0, r.notes
            assert _breaches(mesh, props, bcs, r) == []

    def test_switched_on_the_rescue_settles_it(self):
        mesh, props, bcs = _dam2()
        _s, r = _door(True)
        assert r.converged, r.notes
        assert r.notes["rescue"] == "continuation-newton", r.notes
        assert r.notes["unsettled_nodes"] == 0
        assert "warning" not in r.notes
        assert _breaches(mesh, props, bcs, r) == []

    def test_and_its_discharge_is_the_published_one(self):
        s, r = _door(True)
        q = _discharge(s, r)
        assert abs(q / Q_PUBLISHED - 1.0) < 0.01, q     # measured -0.46 %


# ======================================================================
# The start of the rescue: the toe-drain dam of Harr, budget 1
# ======================================================================
def _harr(budget=None, on=True):
    key = ("harr", budget, on)
    if key not in _CACHE:
        t = _module("test_rescue_face_v1356")
        mesh, props, bcs = t._case()
        kw = {} if budget is None else {"max_node_switches": budget}
        _CACHE[key] = _solve(mesh, props, bcs, on, gamma_w=GAMMA_W,
                             relaxation=t.W, max_iterations=200,
                             tolerance=t.TOL, **kw)[1]
    return _CACHE[key]


class TestSwitchedOffTheDefect:
    def test_the_loop_stops_with_the_face_unsettled(self):
        """Harr's dam with a budget of 1, switched off: what 0.1.357 did.
        It stops with a node of the drain's face held while water goes in
        (measured: the same in all 9 runs with w moved by up to 8 ulp)."""
        t = _module("test_rescue_face_v1356")
        r = _harr(budget=1, on=False)
        assert r.converged is False
        assert "rescue" not in r.notes, r.notes
        assert r.notes["picard_delta"] < t.TOL               # it stopped
        assert r.notes["unsettled_nodes"] >= 1
        assert r.notes["warning"].code == "seepage.face_unsettled"


class TestTheRescueStartsWithoutTheFrozenNodes:
    def test_a_starved_loop_is_rescued_to_the_loops_own_fixed_point(self):
        """The loop alone, with the default budget, converges without the
        rescue (``test_rescue_face_v1356``); with a budget of 1 it stops
        with a node of the drain's face held while water goes in. Rescued
        without its frozen nodes, it lands where the loop alone does;
        started with them, a node held in dry ground stayed held, inside
        the flux band, 4.2 cm off."""
        t = _module("test_rescue_face_v1356")
        ref = _harr()
        r = _harr(budget=1)
        assert ref.converged and "rescue" not in ref.notes, ref.notes
        assert r.converged, r.notes
        assert r.notes["rescue"].startswith("anderson"), r.notes
        assert r.notes["picard_delta"] < t.TOL               # it stopped
        assert sorted(r.seepage_nodes) == sorted(ref.seepage_nodes)
        assert _max_dh(r, ref) < t.TOL / t.W, _max_dh(r, ref)


# ======================================================================
# When no road settles: the loop's own state, to the bit
# ======================================================================
def _starved_102(on):
    key = ("102", on)
    if key not in _CACHE:
        from ogr_fem2d.solvers import (SIDE_LEFT, apply_reservoir,
                                       default_boundary_conditions)
        t = _module("test_transient_coupling_v1125")
        p, m = t._dam_project(elements=1200)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, t.RESERVOIR, SIDE_LEFT)
        _CACHE[key] = _solve(mesh, {m.id: m.hydraulic}, bcs, on,
                             gamma_w=GAMMA_W, relaxation=0.4,
                             max_iterations=400, tolerance=1e-5,
                             max_node_switches=1)[1]
    return _CACHE[key]


class TestWhenNoRoadSettles:
    """The dam of problem 102 with a switch budget of 1: every road the
    rescue tries freezes a node in the wrong state."""

    def test_the_state_published_is_the_loops(self):
        on, off = _starved_102(True), _starved_102(False)
        assert on.converged is False and off.converged is False
        assert list(on.total_head) == list(off.total_head)
        assert sorted(on.seepage_nodes) == sorted(off.seepage_nodes)
        for k in ("frozen_nodes", "unsettled_nodes", "picard_delta"):
            assert on.notes[k] == off.notes[k], k
        w_on, w_off = on.notes["warning"], off.notes["warning"]
        assert (str(w_on), w_on.code, w_on.args) \
            == (str(w_off), w_off.code, w_off.args)

    def test_the_rescue_is_reported_and_only_the_series_grow(self):
        on, off = _starved_102(True), _starved_102(False)
        assert "rescue" not in off.notes
        assert on.notes["rescue"] == "failed"
        assert on.iterations - off.iterations == on.notes["rescue_iterations"]
        n = len(off.notes["history"])
        assert on.notes["history"][:n] == off.notes["history"]
        assert [s[0] for s in on.notes["history_segments"]] == [
            "picard", "anderson 5", "anderson 20", "continuation"]


# ======================================================================
# A loop that converges with its face settled does not move
# ======================================================================
class TestASettledLoopDoesNotMove:
    def test_switched_on_and_off(self):
        t = _module("test_unsaturated_v127")
        mesh = t._dam_mesh(0.7)
        props = {"m": HydraulicProperties(
            ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
            gardner_n=3.0)}
        bcs = t._dam_bcs(mesh)
        kw = dict(relaxation=0.4, max_iterations=250, tolerance=1e-5)
        _s, on = _solve(mesh, props, bcs, True, **kw)
        _s, off = _solve(mesh, props, bcs, False, **kw)
        assert on.converged and "rescue" not in on.notes, on.notes
        assert list(on.total_head) == list(off.total_head)
        assert (on.converged, on.iterations) == (off.converged, off.iterations)
        assert sorted(on.seepage_nodes) == sorted(off.seepage_nodes)
        assert on.notes == off.notes
