# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.272 (D267) — what the tolerance of the unsaturated Picard loop
measures, pinned on the rectangular Gardner dam of ``test_unsaturated_v127``.

The defect as reported, and what was measured instead
-----------------------------------------------------
The loop stops on the RELAXED change w·max|H_new - H|, so the tolerance is
effectively loosened by 1/w. The report took a run with w = 0.1 that ended
0.129 m away from the fixed point (12 900 tolerances) as "converged far
away". It is not: that run comes back ``converged = False``, with one face
node frozen by the switch budget and the warning that the face never
settled. With a budget of 50 the same w converges within 1.3 tolerances.
The relaxed test itself costs little: converged runs lie within one
tolerance of the fixed point for w from 0.2 to 0.8. The criterion was
documented, not changed (it would move every converged model's digits for
nothing measurable); the budget against slow relaxation is D279.

The invariants
--------------
* converged runs with w = 0.2 and w = 0.4 (the groundwater door's) lie
  within the tolerance of the fixed point;
* the fixed point does not depend on w (0.4 and 0.5 solved to 1e-12 agree);
* w = 0.1 with a switch budget of 25 (the default until v0.1.283, D279) is
  REPORTED as not converged, with the face named as the reason, never
  passed off as a converged result;
* with a budget that slow relaxation does not exhaust, w = 0.1 converges
  within twice the tolerance (the relaxed test's 1/w loosening, measured).

The fixed point is solved here, to 1e-12, not read from a stored snapshot.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers.seepage import UnsaturatedSeepageSolver  # noqa: E402

TOL = 1e-5
_CACHE: dict = {}


def _dam():
    if "dam" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t127_d267", Path(__file__).parent / "test_unsaturated_v127.py")
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        mesh = t._dam_mesh(0.7)
        props = {"m": HydraulicProperties(
            ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
            gardner_n=3.0)}
        _CACHE["dam"] = (mesh, props, t._dam_bcs(mesh))
    return _CACHE["dam"]


def _solve(w, tol, **kw):
    key = (w, tol, tuple(sorted(kw.items())))
    if key not in _CACHE:
        mesh, props, bcs = _dam()
        _CACHE[key] = UnsaturatedSeepageSolver(
            mesh, props, relaxation=w, max_iterations=5000, tolerance=tol,
            **kw).solve_unsaturated(bcs)
    return _CACHE[key]


def _off(r):
    ref = _solve(0.5, 1e-12)
    assert ref.converged
    return max(abs(a - b) for a, b in zip(r.total_head, ref.total_head))


class TestTheToleranceOfAConvergedRun:
    def test_the_groundwater_doors_relaxation(self):
        r = _solve(0.4, TOL)
        assert r.converged and "rescue" not in r.notes
        assert _off(r) < TOL, _off(r)              # measured 0.25 tolerance

    def test_a_slower_relaxation(self):
        r = _solve(0.2, TOL)
        assert r.converged
        assert _off(r) < TOL, _off(r)              # measured 0.76 tolerance

    def test_the_fixed_point_does_not_depend_on_the_relaxation(self):
        a, b = _solve(0.4, 1e-12), _solve(0.5, 1e-12)
        assert a.converged and b.converged
        assert sorted(a.seepage_nodes) == sorted(b.seepage_nodes)
        assert max(abs(x - y) for x, y in zip(a.total_head, b.total_head)) \
            < 1e-10


class TestAVerySlowRelaxation:
    def test_is_reported_and_not_passed_off_as_converged(self):
        # v0.1.283 (D279): the DEFAULT budget now scales with 1/w (100 at
        # w = 0.1) and this run converges (test_switch_budget_v1283); the
        # exhausted budget is still reported, so it is asked for explicitly
        r = _solve(0.1, TOL, max_node_switches=25)
        assert _off(r) > 0.05                      # 0.129 m, as reported
        assert r.converged is False
        assert r.notes["unsettled_nodes"] >= 1
        assert r.notes["frozen_nodes"] >= 1
        assert "never settled" in r.notes["warning"]

    def test_converges_once_the_switch_budget_is_not_exhausted(self):
        r = _solve(0.1, TOL, max_node_switches=100)
        assert r.converged
        assert r.notes["frozen_nodes"] == 0
        assert _off(r) < 2 * TOL, _off(r)          # measured 1.3 tolerance
