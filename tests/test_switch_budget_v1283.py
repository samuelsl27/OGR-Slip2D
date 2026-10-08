# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.283 (D279) — the seepage face's switch budget scales with the
relaxation, so a slow relaxation no longer freezes a face node before the
iterate has settled.

The defect: with ``DEFAULT_MAX_NODE_SWITCHES = 25`` and w = 0.1, the face
set of the rectangular Gardner dam of ``test_unsaturated_v127`` changes at
almost every pass while the relaxed iterate creeps towards the fixed point;
a node at the foot of the face spent its 25 switches and froze held at
P = 0 with water going in. The run came out unconverged, 0.129 m from the
fixed point, and the rescue of D124 could not step in: the frozen set no
longer changes, so the loop "ends" (D267's measurement). With 50 or more
switches it converges within 1.3 tolerances.

What these tests protect:

* the default budget is max(25, ceil(10/w)): 25 for every w >= 0.4 (the
  groundwater door's, so the door and the bank's steady rows keep exactly
  the budget they had), 34 at 0.3, 100 at 0.1;
* with the default budget, w = 0.1 converges on that dam, with no frozen
  node, within twice the tolerance of the fixed point solved to 1e-12
  (rule 1: against the fixed point, not a snapshot);
* switched off, the old budget and the old outcome come back (rule 7);
* a budget given explicitly is not scaled
  (``test_transient_coupling_v1125::test_a_starved_budget…`` still starves).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_fem2d.mesh.mesh import Mesh  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import UnsaturatedSeepageSolver  # noqa: E402


def _helpers():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "t1272_d279", Path(__file__).parent / "test_picard_tolerance_v1272.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    return t


class TestTheBudget:
    def test_it_scales_with_one_over_w(self):
        want = {1.0: 25, 0.5: 25, 0.4: 25, 0.3: 34, 0.2: 50, 0.1: 100}
        for w, n in want.items():
            assert UnsaturatedSeepageSolver(
                Mesh(), relaxation=w).max_node_switches == n, w

    def test_a_given_budget_is_not_scaled(self):
        s = UnsaturatedSeepageSolver(Mesh(), relaxation=0.1,
                                     max_node_switches=1)
        assert s.max_node_switches == 1

    def test_switched_off_it_is_the_old_default(self):
        old = seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA
        seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA = False
        try:
            assert UnsaturatedSeepageSolver(
                Mesh(), relaxation=0.1).max_node_switches == 25
        finally:
            seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA = old


class TestASlowRelaxationConverges:
    def test_with_the_default_budget(self):
        t = _helpers()
        mesh, props, bcs = t._dam()
        r = UnsaturatedSeepageSolver(
            mesh, props, relaxation=0.1, max_iterations=5000,
            tolerance=t.TOL).solve_unsaturated(bcs)
        assert r.converged
        assert r.notes["frozen_nodes"] == 0
        assert t._off(r) < 2 * t.TOL, t._off(r)     # measured 1.3 tolerance

    def test_switched_off_it_freezes_again(self):
        t = _helpers()
        mesh, props, bcs = t._dam()
        old = seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA
        seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA = False
        try:
            r = UnsaturatedSeepageSolver(
                mesh, props, relaxation=0.1, max_iterations=5000,
                tolerance=t.TOL).solve_unsaturated(bcs)
        finally:
            seepage.SWITCH_BUDGET_SCALES_WITH_OMEGA = old
        assert r.converged is False
        assert r.notes["frozen_nodes"] >= 1
