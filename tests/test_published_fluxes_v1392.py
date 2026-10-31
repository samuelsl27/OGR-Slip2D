# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The seepage solver computes element fluxes for the results it publishes.

WHAT INVARIANT THIS PROTECTS.

V13 of the compute audit (v0.1.392). Every linear solve of the seepage
solver computed the Darcy velocity and gradient of every element, and the
Picard loops that call it read only the heads and the reactions: the
steady unsaturated solve publishes its final solve, a transient step its
last solve, and ``solve_transient`` the last step of each stage. Bank
05/015 (1-D consolidation, two meshes) computed the fluxes 1600 times for
the 20 stage results it publishes, 05/004 (a steady unsaturated dam) 58
times for 2. Now the inner solves leave them out and the published result
gets them, from its own heads and ``kr``. 05/015 went from 61.2-61.7 s to
49.6-50.0 s and 05/004 from 9.1-9.8 s to 7.0-7.7 s (one fresh process per
run, ABBA), every published field identical. Class A: the same function on
the same numbers.

1. **What is published is v0.1.391's, to the bit:** the steady unsaturated
   solve, a transient step, and the stages of a transient — once with
   fluxes left out where the solver now leaves them out, once with every
   solve computing them as v0.1.391 did — heads, pressures, velocities,
   gradients, reactions and counters compared.
2. **Every published result carries fluxes equal to ``element_fluxes`` of
   its own heads and ``kr``,** computed in the test: the steady solve, a
   step returned by ``step``, a stage, and a stage whose steps did not
   converge.
3. **They are computed once per published result:** counted on a subclass.
   ``solve`` still computes them by default, and ``fluxes=False`` leaves
   them out without moving the heads or the reactions.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib

CURVE = [(0.0, 1e-5), (10.0, 1e-6), (100.0, 1e-8)]


def _column(top=None):
    """A 2 m column one element wide under a head of 1.5 m at its base,
    with a user curve: the zone above the water takes water as it rises
    (the model of test_transient_carried_state_v1282). ``top``, a head at
    its top as well: water flows, and the zone above it is unsaturated, so
    a steady solve has passes to make (without it the steady field is the
    hydrostatic one, whatever ``kr``)."""
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
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
    if top is not None:
        for nid in (2 * rows, 2 * rows + 1):
            bcs.add_node(nid, BCType.TOTAL_HEAD, top)
    hp = HydraulicProperties(ks=1e-5, model=PermeabilityModel.USER_DEFINED,
                             user_curve=list(CURVE), wc_alpha=1.0, vg_n=1.5,
                             wc_sat=0.4, wc_res=0.05, specific_storage=1e-3)
    return mesh, {"m": hp}, bcs


def _transient(top=None, **kw):
    from ogr_fem2d.solvers.seepage import TransientSeepageSolver
    mesh, props, bcs = _column(top)
    s = TransientSeepageSolver(mesh, props, gamma_w=9.81, relaxation=0.5,
                               tolerance=1e-6,
                               max_picard=kw.pop("max_picard", 300),
                               time_steps=kw.pop("time_steps", 3), **kw)
    return s, mesh, bcs


def _stages(bcs):
    from ogr_fem2d.solvers.seepage import TransientStage
    return [TransientStage(time=0.0, label="t0", bcs=bcs),
            TransientStage(time=900.0, label="a", bcs=bcs),
            TransientStage(time=3600.0, label="b", bcs=bcs)]


@contextlib.contextmanager
def _as_v0_1_391():
    """Every solve computes its fluxes, as in v0.1.391; given back on exit."""
    import ogr_fem2d.solvers.seepage as SP
    saved = (SP.SeepageSolver.__dict__["solve"],
             SP.TransientSeepageSolver.__dict__["_solve_linear_step"],
             SP.TransientSeepageSolver.__dict__["_step"])
    solve, linear, step = saved

    def solve_all(self, bcs, kr=None, extra_dirichlet=None, *, fluxes=True):
        return solve(self, bcs, kr, extra_dirichlet, fluxes=True)

    def linear_all(self, bcs, kr, extra, diag, extra_q, fluxes=True):
        return linear(self, bcs, kr, extra, diag, extra_q, fluxes=True)

    def step_all(self, bcs, H, dt, active=None, *, fluxes=True):
        return step(self, bcs, H, dt, active, fluxes=True)

    SP.SeepageSolver.solve = solve_all
    SP.TransientSeepageSolver._solve_linear_step = linear_all
    SP.TransientSeepageSolver._step = step_all
    try:
        yield
    finally:
        (SP.SeepageSolver.solve,
         SP.TransientSeepageSolver._solve_linear_step,
         SP.TransientSeepageSolver._step) = saved


def _fields(res):
    return (repr(res.total_head), repr(res.pressure_head),
            repr(res.pore_pressure), repr(res.velocity), repr(res.gradient),
            repr(res.reactions), res.converged, res.iterations,
            sorted(getattr(res, "seepage_nodes", None) or []))


def _own_fluxes(solver, res):
    from ogr_core.fem.seepage_data import element_fluxes
    return element_fluxes(solver.mesh, solver.props_for, res.total_head,
                          res.kr)


# ======================================================================
class TestWhatIsPublishedIsV0_1_391s:
    """Invariant 1."""

    def test_the_steady_unsaturated_solve(self):
        def run():
            s, _mesh, bcs = _transient(top=1.0)
            return _fields(s.solve_unsaturated(bcs))
        new = run()
        with _as_v0_1_391():
            old = run()
        assert new == old

    def test_a_steady_solve_whose_loop_did_not_converge(self):
        """One Picard pass: the loop stops unconverged, and the final state
        is solved at the end (after the rescue), the branch a settled loop
        does not reach."""
        from ogr_fem2d.solvers.seepage import TransientSeepageSolver

        def run():
            mesh, props, bcs = _column(top=1.0)
            s = TransientSeepageSolver(mesh, props, gamma_w=9.81,
                                       relaxation=0.5, tolerance=1e-6,
                                       max_iterations=1)
            res = s.solve_unsaturated(bcs)
            return _fields(res), res, s
        new, res, s = run()
        with _as_v0_1_391():
            old, _res, _s = run()
        assert new == old
        assert res.velocity
        assert (res.velocity, res.gradient) == _own_fluxes(s, res)

    def test_a_step(self):
        def run():
            s, mesh, bcs = _transient()
            H, act, ok, it, res = s.step(bcs, [0.5] * mesh.node_count,
                                         900.0, set())
            return repr(H), sorted(act), ok, it, _fields(res)
        new = run()
        with _as_v0_1_391():
            old = run()
        assert new == old

    def test_the_stages_of_a_transient(self):
        def run():
            s, mesh, bcs = _transient()
            out = s.solve_transient(_stages(bcs),
                                    initial_head=[0.5] * mesh.node_count)
            return [_fields(r) for r in out]
        new = run()
        with _as_v0_1_391():
            old = run()
        assert new == old
        assert len(new) == 3


# ======================================================================
class TestEveryPublishedResultHasItsFluxes:
    """Invariant 2."""

    def test_the_steady_unsaturated_solve(self):
        s, _mesh, bcs = _transient(top=1.0)
        res = s.solve_unsaturated(bcs)
        assert res.velocity
        assert (res.velocity, res.gradient) == _own_fluxes(s, res)

    def test_a_step_returned_by_step(self):
        s, mesh, bcs = _transient()
        *_rest, res = s.step(bcs, [0.5] * mesh.node_count, 900.0, set())
        assert res.velocity
        assert (res.velocity, res.gradient) == _own_fluxes(s, res)

    def test_the_stages(self):
        s, mesh, bcs = _transient()
        out = s.solve_transient(_stages(bcs),
                                initial_head=[0.5] * mesh.node_count)
        advanced = [r for r in out if r.notes.get("time_steps")]
        assert len(advanced) == 2
        for res in advanced:
            assert (res.velocity, res.gradient) == _own_fluxes(s, res)

    def test_a_stage_whose_steps_did_not_converge(self):
        """Two Picard passes per step is not enough here: the stage is
        published not converged, with the fluxes of its last solve."""
        s, mesh, bcs = _transient(max_picard=2)
        out = s.solve_transient(_stages(bcs),
                                initial_head=[0.5] * mesh.node_count)
        res = out[1]
        assert not res.converged
        assert res.velocity
        assert (res.velocity, res.gradient) == _own_fluxes(s, res)


# ======================================================================
class TestOncePerPublishedResult:
    """Invariant 3."""

    def _counting(self, top=None):
        from ogr_fem2d.solvers.seepage import TransientSeepageSolver

        class Counting(TransientSeepageSolver):
            calls = 0

            def _element_fluxes(self, H, kr=None):
                type(self).calls += 1
                return super()._element_fluxes(H, kr)

        mesh, props, bcs = _column(top)
        s = Counting(mesh, props, gamma_w=9.81, relaxation=0.5,
                     tolerance=1e-6, max_picard=300, time_steps=3)
        return s, mesh, bcs

    def test_the_steady_unsaturated_solve(self):
        """v0.1.391 computed them at the saturated start, at every pass and
        at the final solve; now at the final solve only."""
        s, _mesh, bcs = self._counting(top=1.0)
        res = s.solve_unsaturated(bcs)
        assert res.iterations > 5
        assert type(s).calls == 1
        s, _mesh, bcs = self._counting(top=1.0)
        with _as_v0_1_391():
            s.solve_unsaturated(bcs)
        assert type(s).calls == res.iterations + 2

    def test_a_transient(self):
        s, mesh, bcs = self._counting()
        out = s.solve_transient(_stages(bcs),
                                initial_head=[0.5] * mesh.node_count)
        steps = sum(r.notes.get("time_steps", 0) for r in out)
        assert steps > 2
        assert type(s).calls == 2, "one per stage that advanced"

    def test_solve_by_default_and_without(self):
        from ogr_fem2d.solvers.seepage import SeepageSolver
        mesh, props, bcs = _column()
        s = SeepageSolver(mesh, props, gamma_w=9.81)
        full = s.solve(bcs)
        bare = s.solve(bcs, fluxes=False)
        assert full.velocity and full.gradient
        assert bare.velocity == [] and bare.gradient == []
        assert repr(bare.total_head) == repr(full.total_head)
        assert repr(bare.reactions) == repr(full.reactions)
