# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.356 (D285) — a road of the steady rescue is accepted only when its
answer settles the seepage face.

The defect
----------
When the Picard loop of ``solve_unsaturated`` fails, ``_rescue`` tries
Anderson acceleration (depth 5, then 20) and then continuation with
Newton's method. Each road took the first state that reached the tolerance
with its seepage-face set at rest, without asking the face condition
(``_unsettled_nodes``). Each road starts a switch budget of its own and can
freeze a node of the face in the wrong state: the road was taken, the final
check of ``solve_unsaturated`` reported the face unsettled, and the roads
after it never ran.

The case
--------
Problem 4 of the groundwater verification bank, the earth dam with a toe
drain of Harr (1990): polygon (0, 0)-(22, 0)-(23.5, 1.5)-(12.5, 5)-(10, 5),
head 4 on the upstream face, head 0 at the focus of the drain (22, 0), the
drain face at 45 degrees free to seep. Its permeability falls six decades
over 0.5 kPa (log-linear between the two points of a user curve). The mesh
is the generator's at 2400 target elements (2307 T3); w = 0.4 and ONE Picard
pass, so that the rescue takes over at once (the idiom of
``test_picard_history_v1269``). Measured in the bank (``_auditoria/P6_0356``):
switched off, Anderson is taken with one face node left free under a
pressure 67 times the band; switched on, both Anderson depths are set aside
and the continuation settles the face. The case depends on the mesh (with
2000 or 3000 elements it does not arise), so the element count is asserted
first: another mesh fails saying so, not with a puzzling number.

The invariants
--------------
* switched off, the defect: the run is reported unconverged with the face
  unsettled, a road of Anderson is taken and the continuation is never
  called (counted, since its part of the history only appears when it
  reaches t = 1);
* switched on, the continuation settles it: converged, every face node
  obeys the condition, judged here with the solver's own bands but without
  its ``_unsettled_nodes``; and the answer is the fixed point the loop
  reaches ALONE with 200 passes -- same face, heads within the loop's
  tol / w -- which is the consistency with an already validated road
  (rule 1), while the field the defect published is 3.7 cm away from it;
* when no road settles (a switch budget of 1), the state published is the
  one published before, to the bit, still reported unconverged; only the
  iteration count and the published series grow;
* a rescue whose first road settles, and a loop that converges, do not
  move.

Cost: about 30 s (six solves of the 2307-element mesh, cached, and four of
a small dam). Every test restores the module switch it touches (rule 5).
"""
from __future__ import annotations

import importlib.util
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

GAMMA_W = 9.81
KS = 1.0e-5
#: six decades over 0.5 kPa (kPa, as every user curve since v0.1.200)
CURVE = [(0.0, KS), (0.5, KS * 1.0e-6)]
FOCUS = (22.0, 0.0)
OUTLINE = [(0.0, 0.0), FOCUS, (23.5, 1.5), (12.5, 5.0), (10.0, 5.0)]
HEAD = 4.0
W, TOL = 0.4, 1.0e-6
ELEMENTS, T3 = 2400, 2307
ROADS = ["picard", "anderson 5", "anderson 20", "continuation"]


# ======================================================================
# The toe-drain dam
# ======================================================================
def _project():
    from shapely.geometry import Polygon

    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    p = Project("toe-drain dam")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="Dam", unit_weight=20.0, sat_unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(
        ks=KS, model=PermeabilityModel.USER_DEFINED, user_curve=list(CURVE))
    p.materials = [m]
    for reg in p.resolve_regions():
        pt = Polygon([(v.x, v.y) for v in reg.polygon.vertices]
                     ).representative_point()
        p.assign_material_at(pt.x, pt.y, m.id)
    return p


def _bcs(mesh):
    """Head 4 on the upstream face up to y = 4 and 0 at the focus; the
    upstream face above the water, the crest, the downstream slope and the
    drain face free to seep; the base impervious."""
    b = SeepageBoundaryConditions()
    for i in mesh.boundary_node_ids():
        x, y = mesh.nodes[i].x, mesh.nodes[i].y
        if abs(x - FOCUS[0]) < 1e-6 and abs(y - FOCUS[1]) < 1e-6:
            b.add_node(i, BCType.TOTAL_HEAD, 0.0)
        elif x <= 10.0 + 1e-6 and abs(y - 0.5 * x) < 1e-4:
            if y <= HEAD + 1e-6:
                b.add_node(i, BCType.TOTAL_HEAD, HEAD)
            else:
                b.add_node(i, BCType.UNKNOWN)
        elif abs(y) < 1e-9:
            continue
        else:
            b.add_node(i, BCType.UNKNOWN)
    return b


_CACHE: dict = {}


def _case():
    if "case" not in _CACHE:
        from ogr_fem2d.mesh import generate_mesh_for_project
        p = _project()
        mesh = generate_mesh_for_project(p, target_elements=ELEMENTS)
        props = {m.id: m.hydraulic for m in p.materials}
        _CACHE["case"] = (mesh, props, _bcs(mesh))
    return _CACHE["case"]


class _CountContinuations:
    """Counts the calls to the continuation, whatever they return."""

    def __enter__(self):
        self.calls = 0
        self.real = UnsaturatedSeepageSolver._continuation_newton
        spy = self

        def counted(solver, *args, **kwargs):
            spy.calls += 1
            return spy.real(solver, *args, **kwargs)
        UnsaturatedSeepageSolver._continuation_newton = counted
        return self

    def __exit__(self, *exc):
        UnsaturatedSeepageSolver._continuation_newton = self.real
        return False


def _solve(settled, passes=1, budget=None):
    """(result, calls to the continuation), with ``RESCUE_SETTLED_FACE``
    set to ``settled`` for the run."""
    key = (settled, passes, budget)
    if key not in _CACHE:
        mesh, props, bcs = _case()
        kw = {} if budget is None else {"max_node_switches": budget}
        old = seepage.RESCUE_SETTLED_FACE
        try:
            seepage.RESCUE_SETTLED_FACE = settled
            with _CountContinuations() as spy:
                r = UnsaturatedSeepageSolver(
                    mesh, props, gamma_w=GAMMA_W, relaxation=W,
                    max_iterations=passes, tolerance=TOL,
                    **kw).solve_unsaturated(bcs)
        finally:
            seepage.RESCUE_SETTLED_FACE = old
        _CACHE[key] = (r, spy.calls)
    return _CACHE[key]


def _breaches(r):
    """Face nodes whose condition the published field breaks, with the
    solver's bands: p_tol from the element size, q_tol from the largest
    nodal flux of the saturated solve. A node held at P = 0 must not take
    water in; a free one must not be under pressure."""
    mesh, props, bcs = _case()
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
class TestSwitchedOffTheDefect:
    def test_the_mesh_is_the_one_measured(self):
        mesh, _props, _bcs = _case()
        assert mesh.element_count == T3, (
            "not the mesh this case was measured on", mesh.element_count)

    def test_anderson_is_taken_with_the_face_unsettled(self):
        r, calls = _solve(False)
        assert r.converged is False
        assert r.notes["rescue"].startswith("anderson"), r.notes
        assert r.notes["unsettled_nodes"] >= 1, r.notes
        assert r.notes["frozen_nodes"] >= 1, r.notes
        assert r.notes["warning"].code == "seepage.face_unsettled"
        assert calls == 0                  # the continuation never ran

    def test_and_the_published_field_breaks_the_face(self):
        r, _calls = _solve(False)
        assert _breaches(r)


class TestTheContinuationSettlesIt:
    def test_converged_by_the_continuation(self):
        r, calls = _solve(True)
        assert calls == 1
        assert r.converged, r.notes
        assert r.notes["rescue"] == "continuation-newton", r.notes
        assert r.notes["unsettled_nodes"] == 0
        assert r.notes["frozen_nodes"] == 0
        assert "warning" not in r.notes
        assert [s[0] for s in r.notes["history_segments"]] == ROADS
        assert r.notes["rescue_residual"] < TOL

    def test_every_face_node_obeys_the_condition(self):
        r, _calls = _solve(True)
        assert _breaches(r) == []

    def test_it_is_the_fixed_point_the_loop_reaches_alone(self):
        """Rule 1. The loop alone, given 200 passes, converges without the
        rescue; a converged loop lies within tol / w of the fixed point
        (``test_picard_tolerance_v1272``), and the rescued answer must lie
        there too (measured 2.1e-6 m), while the field the defect
        published is centimetres away (measured 3.7e-2 m)."""
        r, _calls = _solve(True)
        ref, _calls = _solve(True, passes=200)
        assert ref.converged and "rescue" not in ref.notes, ref.notes
        assert sorted(ref.seepage_nodes) == sorted(r.seepage_nodes)
        assert _max_dh(r, ref) < TOL / W, _max_dh(r, ref)
        off, _calls = _solve(False)
        assert _max_dh(off, ref) > 1e-3, _max_dh(off, ref)


class TestWhenNoRoadSettles:
    """A switch budget of 1: every road freezes the same node."""

    def test_the_state_published_is_the_one_published_before(self):
        on, calls_on = _solve(True, budget=1)
        off, calls_off = _solve(False, budget=1)
        assert (calls_on, calls_off) == (1, 0)
        assert on.converged is False and off.converged is False
        assert list(on.total_head) == list(off.total_head)
        assert sorted(on.seepage_nodes) == sorted(off.seepage_nodes)
        for k in ("rescue", "rescue_residual", "frozen_nodes",
                  "unsettled_nodes"):
            assert on.notes[k] == off.notes[k], k
        w_on, w_off = on.notes["warning"], off.notes["warning"]
        assert (str(w_on), w_on.code, w_on.args) \
            == (str(w_off), w_off.code, w_off.args)

    def test_only_the_count_and_the_series_grow(self):
        on, _calls = _solve(True, budget=1)
        off, _calls = _solve(False, budget=1)
        extra = on.notes["rescue_iterations"] - off.notes["rescue_iterations"]
        assert extra > 0
        assert on.iterations - off.iterations == extra
        n = len(off.notes["history"])
        assert on.notes["history"][:n] == off.notes["history"]
        assert [s[0] for s in on.notes["history_segments"]] == ROADS
        assert [s[0] for s in off.notes["history_segments"]] == ROADS[:2]


# ======================================================================
# Where no road is set aside, the switch changes nothing
# ======================================================================
def _gardner_dam():
    """The rectangular Gardner dam of ``test_unsaturated_v127``, as
    ``test_picard_history_v1269`` uses it."""
    if "gardner" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t127_d285", Path(__file__).parent / "test_unsaturated_v127.py")
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        mesh = t._dam_mesh(0.7)
        props = {"m": HydraulicProperties(
            ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
            gardner_n=3.0)}
        _CACHE["gardner"] = (mesh, props, t._dam_bcs(mesh))
    return _CACHE["gardner"]


def _both(passes):
    mesh, props, bcs = _gardner_dam()
    out = []
    old = seepage.RESCUE_SETTLED_FACE
    try:
        for settled in (True, False):
            seepage.RESCUE_SETTLED_FACE = settled
            out.append(UnsaturatedSeepageSolver(
                mesh, props, relaxation=W, max_iterations=passes,
                tolerance=1e-5).solve_unsaturated(bcs))
    finally:
        seepage.RESCUE_SETTLED_FACE = old
    return out


def _identical(a, b):
    assert list(a.total_head) == list(b.total_head)
    assert (a.converged, a.iterations) == (b.converged, b.iterations)
    assert sorted(a.seepage_nodes or []) == sorted(b.seepage_nodes or [])
    assert a.notes == b.notes


class TestWhatNoRoadSetAsideDoesNotMove:
    def test_a_rescue_whose_first_road_settles(self):
        on, off = _both(1)
        assert on.converged and on.notes["rescue"].startswith("anderson"), \
            on.notes
        _identical(on, off)

    def test_a_loop_that_converges(self):
        on, off = _both(250)
        assert on.converged and "rescue" not in on.notes, on.notes
        _identical(on, off)
