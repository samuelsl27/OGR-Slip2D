# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.282 (D276) — a converged transient time step carries what it
publishes, and what the transient's tolerance measures is written down.

The defect: ``TransientSeepageSolver.step`` published ``step_result`` (the
last UNRELAXED linear solve) as the stage's field, while the state carried
to the next step and to ``stored_water`` was the RELAXED iterate. The two
differ by up to tolerance·(1 - w)/w — measured on the bank's transients
(w = 0.3): 1.6-2.2e-4 m at tolerance 1e-4, the bound itself. The published
heads were not the ones the stored water and the next step used.

What these tests protect:

* a converged step returns as its state the very heads it publishes (to the
  bit), with w < 1 (``TRANSIENT_CARRY_LAST_SOLVE``);
* the switch moves the number (rule 7): off, the carried state differs from
  the published one, and by LESS than tolerance·(1 - w)/w — the identity
  that follows from the stop test w·max|H_new - H| < tol (rule 1);
* the stored water of a stage is that of its published heads;
* with w = 1 the switch changes nothing (relaxed = unrelaxed), which is why
  the erfc, Terzaghi, Ferris and Celia runs do not move;
* a step that does not converge still carries its relaxed iterate;
* the tolerance is judged on the RELAXED change (declared, as in the steady
  solver, D267): the last unrelaxed change of a converged step is below
  tol / w.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402

CURVE = [(0.0, 1e-5), (10.0, 1e-6), (100.0, 1e-8)]
TOL = 1e-6


def _column():
    """A 2 m column one element wide, the water table at 0.5 m and the head
    at its base raised to 1.5 m at t = 0 (as in test_retention_dialog_v1268),
    with a user curve: the unsaturated zone takes water as the front rises."""
    from ogr_fem2d.mesh.mesh import Element, Mesh, Node
    from ogr_fem2d.solvers.seepage import BCType, SeepageBoundaryConditions
    dz, rows = 0.1, 20
    nodes = [Node(2 * j + k, k * dz, j * dz)
             for j in range(rows + 1) for k in (0, 1)]
    elements = []
    for j in range(rows):
        a, b, c, d = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
        elements.append(Element(len(elements), (a, b, c), "m"))
        elements.append(Element(len(elements), (a, c, d), "m"))
    mesh = Mesh(nodes=nodes, elements=elements, target_size=dz)
    bcs = SeepageBoundaryConditions()
    for nid in (0, 1):
        bcs.add_node(nid, BCType.TOTAL_HEAD, 1.5)
    hp = HydraulicProperties(ks=1e-5, model=PermeabilityModel.USER_DEFINED,
                             user_curve=list(CURVE), wc_alpha=1.0, vg_n=1.5,
                             wc_sat=0.4, wc_res=0.05, specific_storage=1e-3)
    return mesh, {"m": hp}, bcs


def _solver(w, **kw):
    mesh, props, bcs = _column()
    s = seepage.TransientSeepageSolver(mesh, props, gamma_w=9.81,
                                       relaxation=w, tolerance=TOL,
                                       max_picard=kw.pop("max_picard", 300),
                                       **kw)
    return s, mesh, bcs


def _first_step(w, **kw):
    s, mesh, bcs = _solver(w, **kw)
    H0 = [0.5] * mesh.node_count
    return s.step(bcs, H0, 900.0, set())


def _with(flag, body):
    old = seepage.TRANSIENT_CARRY_LAST_SOLVE
    seepage.TRANSIENT_CARRY_LAST_SOLVE = flag
    try:
        return body()
    finally:
        seepage.TRANSIENT_CARRY_LAST_SOLVE = old


class TestAConvergedStepCarriesWhatItPublishes:
    def test_to_the_bit(self):
        H, _act, ok, _it, res = _first_step(0.5)
        assert ok
        assert H == res.total_head

    def test_the_switch_moves_it_within_the_bound(self):
        w = 0.5
        H, _act, ok, _it, res = _with(False, lambda: _first_step(w))
        assert ok
        d = max(abs(x - y) for x, y in zip(H, res.total_head))
        assert 0.0 < d < TOL * (1.0 - w) / w, d

    def test_the_stored_water_is_that_of_the_published_heads(self):
        from ogr_fem2d.solvers.seepage import TransientStage
        s, _mesh, bcs = _solver(0.5, time_steps=3)
        res = s.solve_transient([TransientStage(time=2700.0, label="45 min",
                                                bcs=bcs)],
                                initial_head=[0.5] * _mesh.node_count)
        r = res[-1]
        assert r.converged
        assert r.notes["stored_water"] == s.stored_water(r.total_head)

    def test_with_w_one_nothing_changes(self):
        on = _with(True, lambda: _first_step(1.0))
        off = _with(False, lambda: _first_step(1.0))
        assert on[0] == off[0] and on[4].total_head == off[4].total_head

    def test_an_unconverged_step_carries_its_relaxed_iterate(self):
        H, _act, ok, _it, res = _first_step(0.5, max_picard=1)
        assert not ok
        assert H != res.total_head


class TestWhatTheToleranceMeasures:
    def test_the_relaxed_change_is_judged(self):
        """The loop stops on w·max|H_new - H| < tol, so the last UNRELAXED
        change (the published history) is below tol / w, not below tol."""
        w = 0.5
        _H, _act, ok, _it, res = _first_step(w)
        assert ok
        assert res.notes["history"][-1] < TOL / w
