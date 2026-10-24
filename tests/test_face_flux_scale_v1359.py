# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.359 (D364) — the flux band of the seepage face scales with a flow that
exists.

The defect
----------
A node of the seepage face held at P = 0 is released when its inflow exceeds
the flux band, 1e-4 of the largest nodal flux of the first, saturated, solve
(``UnsaturatedSeepageSolver._face_q_tol``). A dam that drains only through
its face has one prescribed level and no applied flux: its saturated solve is
that level, with no flow, and the band was round-off. On the dam of problem
102 without its tailwater it was 5e-24, while the face carries 1.3e-6: any
positive round-off reaction released a held node or counted it unsettled.

The fix, and the owner's decision
---------------------------------
``FACE_FLUX_SCALE_FROM_FLOW``: when the saturated solve carries no flow
(``_saturated_carries_no_flow``, decided from the conditions), the scale is
the largest nodal flux of the first pass solved with the face held, before
the switching that reads it -- the rule each transient step follows since
D269. On the groundwater verification bank it moves one run of 255, by
2.3e-8 m with the same face (``_auditoria/P6_0359``).

The invariants
--------------
* the identity behind the detector: with one level and no applied flux the
  saturated field IS the level (to round-off), and its nodal fluxes are
  round-off next to the flow through the face; two levels, or one level
  with an applied flux, are not detected;
* switched on, on the dam of problem 102 without tailwater, every band the
  switching reads with the face held is 1e-4 of a scale of the order of the
  flow of the answer (measured 1.5 times its largest nodal flux); switched
  off, it is round-off. Rule 7: the switch moves the number it exists for;
* on that dam the new band decides nothing, as in 254 of the 255 runs of the
  bank: heads, face, iteration count and notes are the same on and off;
* with its tailwater the saturated solve has flow, the detector stays off,
  and the band is the saturated one, on and off.

Cost: about 15 s. Every test restores the switch it touches (rule 5).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_fem2d.solvers import (  # noqa: E402
    SIDE_LEFT,
    SIDE_RIGHT,
    apply_reservoir,
    default_boundary_conditions,
    seepage,
)
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageSolver,
    UnsaturatedSeepageSolver,
)

GAMMA_W = 9.81
_CACHE: dict = {}


def _t1125():
    if "t1125" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t1359_t1125", Path(__file__).parent / "test_transient_coupling_v1125.py")
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        _CACHE["t1125"] = t
    return _CACHE["t1125"]


def _dam(tail):
    """The dam of problem 102 (``test_transient_coupling_v1125``) on 1200
    target elements, with or without its tailwater."""
    key = ("dam", tail)
    if key not in _CACHE:
        t = _t1125()
        p, m = t._dam_project(elements=1200)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, t.RESERVOIR, SIDE_LEFT)
        if tail:
            apply_reservoir(bcs, mesh, t.TAILWATER, SIDE_RIGHT)
        _CACHE[key] = (mesh, {m.id: m.hydraulic}, bcs)
    return _CACHE[key]


class _Spy(UnsaturatedSeepageSolver):
    """Records (number of held nodes, q_tol) of every switching decision."""

    def _switch_seepage_face(self, active, switches, unknown, H, reactions,
                             p_tol, q_tol):
        self.seen.append((len(active), q_tol))
        return super()._switch_seepage_face(active, switches, unknown, H,
                                            reactions, p_tol, q_tol)


def _solve(tail, on):
    key = ("solve", tail, on)
    if key not in _CACHE:
        mesh, props, bcs = _dam(tail)
        old = seepage.FACE_FLUX_SCALE_FROM_FLOW
        try:
            seepage.FACE_FLUX_SCALE_FROM_FLOW = on
            s = _Spy(mesh, props, gamma_w=GAMMA_W, relaxation=0.4,
                     max_iterations=400, tolerance=1e-5)
            s.seen = []
            _CACHE[key] = (s, s.solve_unsaturated(bcs))
        finally:
            seepage.FACE_FLUX_SCALE_FROM_FLOW = old
    return _CACHE[key]


def _qmax(r):
    return max(abs(q) for q in r.reactions)


class TestTheDetector:
    def test_one_level_and_no_flux_is_a_saturated_field_with_no_flow(self):
        mesh, props, bcs = _dam(tail=False)
        s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W)
        assert s._saturated_carries_no_flow(bcs)
        first = SeepageSolver(mesh, props, gamma_w=GAMMA_W).solve(bcs)
        level = _t1125().RESERVOIR
        assert max(abs(h - level) for h in first.total_head) < 1e-9 * level
        # what the old band was made of: round-off next to the face's flow
        _s, r = _solve(tail=False, on=True)
        assert _qmax(first) < 1e-12 * _qmax(r), (_qmax(first), _qmax(r))

    def test_two_levels_are_not_detected(self):
        mesh, props, bcs = _dam(tail=True)
        s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W)
        assert not s._saturated_carries_no_flow(bcs)

    def test_one_level_with_an_applied_flux_is_not_detected(self):
        mesh, props, bcs = _dam(tail=False)
        s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W)
        free = next(b.node_id for b in bcs.nodes if b.bc_type == BCType.UNKNOWN)
        with_flow = type(bcs)(nodes=list(bcs.nodes), segments=list(bcs.segments))
        with_flow.add_node(free, BCType.NODAL_FLOW, 1e-7)
        assert not s._saturated_carries_no_flow(with_flow)
        rain = type(bcs)(nodes=list(bcs.nodes), segments=list(bcs.segments))
        a, b = sorted(mesh.boundary_node_ids())[:2]
        rain.add_segment(a, b, 1e-8)
        assert not s._saturated_carries_no_flow(rain)


class TestTheBandOfADamThatDrainsThroughItsFace:
    def test_switched_on_it_is_of_the_order_of_the_flow(self):
        s, r = _solve(tail=False, on=True)
        assert r.converged, r.notes
        read = {q for held, q in s.seen if held}
        assert len(read) == 1, read
        q_tol = read.pop()
        ratio = q_tol / (1e-4 * _qmax(r))
        assert 0.5 < ratio < 5.0, ratio                 # measured 1.5

    def test_switched_off_it_is_round_off(self):
        s, r = _solve(tail=False, on=False)
        read = {q for held, q in s.seen if held}
        assert read and max(read) < 1e-20, read          # measured 5e-24

    def test_and_on_this_dam_it_decides_nothing(self):
        _s, on = _solve(tail=False, on=True)
        _s, off = _solve(tail=False, on=False)
        assert list(on.total_head) == list(off.total_head)
        assert (on.converged, on.iterations) == (off.converged, off.iterations)
        assert sorted(on.seepage_nodes) == sorted(off.seepage_nodes)
        assert on.notes == off.notes


class TestAModelWithFlowKeepsItsBand:
    def test_the_band_is_the_saturated_one_on_and_off(self):
        mesh, props, bcs = _dam(tail=True)
        first = SeepageSolver(mesh, props, gamma_w=GAMMA_W).solve(bcs)
        expected = UnsaturatedSeepageSolver._face_q_tol(_qmax(first))
        for on in (True, False):
            s, r = _solve(tail=True, on=on)
            assert r.converged, r.notes
            assert {q for _held, q in s.seen} == {expected}, on

    def test_and_its_answer_does_not_move(self):
        _s, on = _solve(tail=True, on=True)
        _s, off = _solve(tail=True, on=False)
        assert list(on.total_head) == list(off.total_head)
        assert (on.converged, on.iterations) == (off.converged, off.iterations)
        assert on.notes == off.notes
