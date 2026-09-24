# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.201 (spec 008, F3b) — statistics, back analysis, optimisation and the
Interpret questions, for the agent and through one door.

Invariants protected
--------------------
**One door** (owner's decision, 2026-09-24). Statistics, back analysis and
optimisation run what a plain Compute runs: the design-factored copy, the
settings checks, the project's settings and seed.

* With the design standard OFF the numbers are exactly the old path's —
  the door must cost nothing when unused.
* With a standard ON a zero-variance sample must reproduce the FACTORED
  deterministic factor. The interface factored the deterministic run and
  not the samples, so a histogram put over-design factors next to
  unfactored factors of safety.
* A back analysis at a target of exactly 1.0 has its active and passive
  forces equal — an identity of the formulation, through the API.
* An optimisation is reproducible from the project's seed, and is a NEW
  result: the interface overwrote the critical surface, factor and slices
  of the stored result in place and left its forces from the old surface.

**The samples keep their index.** A failed sample produces no factor, and
the scatter data and the statistics export zipped samples with factors, so
every pair after the first failure was shifted. With a factor that grows
with the sampled cohesion, correctly paired points are monotone and the
shifted zip is not.

**Interpretation, measured against something external**:

* the slice table of the Ej_2 worked report (Ordinary method), now through
  ``interpretation.slice_rows``;
* the area of a circular segment, R²(θ − sin θ)/2, for ``surface_area``
  (the interface's column read 0.0 on every row);
* a point on the unsliced upper side of a circle is not on its slip
  surface.

**Refusals change nothing, and the inventory has no pending action.**
"""
from __future__ import annotations

import atexit
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 6.0, "friction_angle": 22.0}}
_CACHE: dict = {}


def _ws():
    from ogr_api import Workspace
    ws = Workspace()
    atexit.register(ws.shutdown)
    return ws


def _slope(ws, *, standard="off", samples=30, prob=True, sens=False):
    """A 10 m slope facing left, a small circular grid, Bishop."""
    from ogr_api import call
    pid = call(ws, "project_new", name="Stats")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [60, 0], [60, 20], [40, 20], [20, 10],
                     [0, 10]],
        "materials": [{"name": "Soil", "unit_weight": 19,
                       "strength": _SOIL}]})
    call(ws, "analysis_configure", project_id=pid,
         methods=["bishop_simplified"], surface_type="circular",
         search_method="grid", num_slices=25,
         grid={"x_min": 15, "x_max": 35, "y_min": 25, "y_max": 45,
               "nx": 3, "ny": 3},
         radius_increment=3, failure_direction="right_to_left",
         design_standard=standard)
    call(ws, "settings_set", project_id=pid, changes={
        "statistics.probabilistic_analysis": prob,
        "statistics.sensitivity_analysis": sens,
        "statistics.num_samples": samples,
        "statistics.sampling_method": "latin_hypercube",
        "statistics.sensitivity_intervals": 6})
    return pid


def _cohesion_key(ws, pid):
    from ogr_api import call
    avail = call(ws, "random_variable_list", project_id=pid)["available"]
    return next(v["key"] for v in avail if v["key"].endswith(":cohesion"))


# ======================================================================
# Random variables
# ======================================================================
class TestRandomVariables:
    def test_a_new_variable_starts_from_the_models_value(self):
        from ogr_api import call
        ws = _ws()
        pid = _slope(ws)
        key = _cohesion_key(ws, pid)
        out = call(ws, "random_variable_set", project_id=pid, key=key)
        d = out["variable"]["distribution"]
        got = (d["mean"], d["std_dev"], d["rel_min"], d["rel_max"])
        assert max(abs(g - e) for g, e in zip(got, (6.0, 0.6, 1.8, 1.8))
                   ) < 1e-12, got
        assert out["variable"]["is_random"]

    def test_the_mean_follows_the_model(self):
        from ogr_api import call
        ws = _ws()
        pid = _slope(ws)
        key = _cohesion_key(ws, pid)
        call(ws, "random_variable_set", project_id=pid, key=key)
        call(ws, "material_set", project_id=pid, material="Soil",
             strength={"model": "mohr_coulomb",
                       "params": {"cohesion": 9.0, "friction_angle": 22.0}})
        out = call(ws, "random_variable_set", project_id=pid, key=key,
                   std_dev=1.0)
        assert out["variable"]["distribution"]["mean"] == 9.0
        assert any("Mean updated" in n for n in out["notes"])

    def test_refusals_change_nothing(self):
        from ogr_api import InvalidArgument, NotFound, call
        ws = _ws()
        pid = _slope(ws)
        key = _cohesion_key(ws, pid)
        call(ws, "random_variable_set", project_id=pid, key=key)
        before = json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                            default=str)
        for kw, exc in ((dict(key="material:nope:x"), NotFound),
                        (dict(key=key, std_dev=-1.0), InvalidArgument),
                        (dict(key=key, correlated_with=key,
                              correlation=0.5), InvalidArgument),
                        (dict(key=key, correlated_with="other:x:y",
                              correlation=0.5), InvalidArgument),
                        (dict(key=key, correlation=0.5), InvalidArgument)):
            with pytest.raises(exc):
                call(ws, "random_variable_set", project_id=pid, **kw)
            assert json.dumps(ws.get(pid).project.to_dict(),
                              sort_keys=True, default=str) == before, kw

    def test_deleting_clears_correlations_to_it(self):
        from ogr_api import call
        ws = _ws()
        pid = _slope(ws)
        avail = call(ws, "random_variable_list", project_id=pid)[
            "available"]
        c = next(v["key"] for v in avail if v["key"].endswith(":cohesion"))
        f = next(v["key"] for v in avail
                 if v["key"].endswith(":friction_angle"))
        call(ws, "random_variable_set", project_id=pid, key=c)
        call(ws, "random_variable_set", project_id=pid, key=f,
             correlated_with=c, correlation=-0.5)
        call(ws, "random_variable_delete", project_id=pid, key=c)
        (rv,) = ws.get(pid).project.random_variables
        assert rv.key == f and rv.correlated_with is None
        assert rv.correlation == 0.0


# ======================================================================
# Statistics through the door
# ======================================================================
def _stats_project(standard="off", std=None, samples=30):
    """A project (not a workspace) with the cohesion random."""
    from ogr_api import call
    ws = _ws()
    pid = _slope(ws, standard=standard, samples=samples)
    key = _cohesion_key(ws, pid)
    kw = {} if std is None else dict(std_dev=std, rel_min=std,
                                     rel_max=std)
    call(ws, "random_variable_set", project_id=pid, key=key, **kw)
    return ws, pid, key


class TestStatisticsThroughTheDoor:
    def test_pf_and_beta_are_the_counted_ones(self):
        """Through the job: PF is the fraction counted below 1 and beta is
        (mean - 1) / sigma of the stored factors."""
        from ogr_api import call
        ws, pid, _key = _stats_project(samples=40)
        out = call(ws, "statistics_run", project_id=pid, wait_seconds=300)
        assert out["state"] == "done", out
        m = out["summary"]["probabilistic"]["methods"][0]
        _h, res = ws.find_result(out["result_id"])
        vals = res.payload()["probabilistic"].by_method[
            "bishop_simplified"].statistics.values
        n = len(vals)
        mean = sum(vals) / n
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))
        assert m["samples"] == n == 40
        assert abs(m["pf"] - sum(v < 1.0 for v in vals) / n) < 1e-15
        assert abs(m["reliability_index"] - (mean - 1.0) / sd) < 1e-9
        hist = call(ws, "results_query", result_id=out["result_id"],
                    view="histogram", bins=8)["bins"]
        assert sum(c for _x, c in hist) == n

    def test_zero_variance_reproduces_the_factored_deterministic(self):
        """The discriminating case of the door: with EC7 DA1-C2 on, a
        sample equal to the mean must give the FACTORED deterministic
        factor. The old path evaluated the samples unfactored."""
        from ogr_slip2d.analysis_runner import run_configured_statistics
        for standard in ("off", "eurocode7_da1c2"):
            ws, pid, _key = _stats_project(standard, std=1e-9, samples=5)
            out = run_configured_statistics(ws.get(pid).project)
            det = out.deterministic["bishop_simplified"].fos
            vals = out.probabilistic.by_method[
                "bishop_simplified"].statistics.values
            assert vals and max(abs(v - det) for v in vals) < 1e-6, (
                standard, det, vals)

    def test_with_the_standard_off_it_is_the_old_path(self):
        from ogr_core.statistics import SamplingMethod, run_global_minimum
        from ogr_slip2d.analysis_runner import (run_analysis,
                                                run_configured_statistics)
        ws, pid, _key = _stats_project(samples=12)
        p = ws.get(pid).project
        new = run_configured_statistics(p).probabilistic
        det = {mid: sr.critical for mid, sr in
               run_analysis(p, ["bishop_simplified"]).results.items()}
        old = run_global_minimum(
            p, det, list(p.random_variables), num_samples=12,
            sampling=SamplingMethod.LATIN_HYPERCUBE,
            seed=p.settings.analysis_seed(),
            num_slices=p.settings.methods.num_slices)
        a = new.by_method["bishop_simplified"].statistics.values
        b = old.by_method["bishop_simplified"].statistics.values
        assert a == b and len(a) == 12

    def test_a_failed_sample_does_not_shift_the_pairs(self):
        """Every third sample fails (through ``prepare``). The factor
        grows with the cohesion, so the pairs sorted by cohesion must be
        sorted by factor; the old zip is not."""
        from ogr_core.statistics import (SamplingMethod, run_global_minimum,
                                         sample_pairs)
        from ogr_slip2d.analysis_runner import run_analysis
        ws, pid, key = _stats_project(samples=24)
        p = ws.get(pid).project
        det = {mid: sr.critical for mid, sr in
               run_analysis(p, ["bishop_simplified"]).results.items()}
        calls = [0]

        def prepare(clone):
            calls[0] += 1
            if calls[0] % 3 == 0:
                raise RuntimeError("an unsolvable sample")
            return clone

        res = run_global_minimum(p, det, list(p.random_variables),
                                 num_samples=24,
                                 sampling=SamplingMethod.MONTE_CARLO,
                                 seed=7, prepare=prepare)
        m = res.by_method["bishop_simplified"]
        assert m.failed_samples == 8 and len(m.sample_index) == 16
        pairs = sorted((v, f) for _i, v, f in sample_pairs(
            res, "bishop_simplified", key))
        fs = [f for _v, f in pairs]
        assert fs == sorted(fs)
        shifted = sorted(zip(res.samples[key], m.statistics.values))
        assert [f for _v, f in shifted] != sorted(f for _v, f in shifted)

    def test_it_refuses_what_it_cannot_run(self):
        from ogr_api import NotConfigured, call
        ws = _ws()
        pid = _slope(ws)
        with pytest.raises(NotConfigured):       # no variable
            call(ws, "statistics_run", project_id=pid)
        pid2 = _slope(ws, prob=False)
        call(ws, "random_variable_set", project_id=pid2,
             key=_cohesion_key(ws, pid2))
        with pytest.raises(NotConfigured):       # nothing switched on
            call(ws, "statistics_run", project_id=pid2)


# ======================================================================
# Back analysis
# ======================================================================
class TestBackAnalysisThroughTheDoor:
    def test_active_equals_passive_at_unity(self):
        """At a target of 1.0 the two forces are the same number: the
        identity test_back_analysis_v140 checks on the engine, here
        through the agent's job."""
        from ogr_api import call
        ws = _ws()
        pid = _slope(ws)
        out = call(ws, "back_analysis_run", project_id=pid, target_fos=1.0,
                   elevation=5.0, wait_seconds=300)
        s = out["summary"]
        assert s["surfaces"] > 0
        assert abs(s["active_force"] - s["passive_force"]) < 1e-6, s

    def test_off_is_the_old_path_and_on_moves_it(self):
        from ogr_slip2d.analysis_runner import (build_search,
                                                run_configured_back_analysis)
        from ogr_slip2d.back_analysis import run_back_analysis
        forces = {}
        for standard in ("off", "eurocode7_da1c2"):
            ws = _ws()
            p = ws.get(_slope(ws, standard=standard)).project
            new, rep, _w = run_configured_back_analysis(
                p, target_fos=1.3, elevation=5.0)
            old = run_back_analysis(p, build_search(p, "bishop_simplified"),
                                    1.3, 5.0, "bishop_simplified")
            forces[standard] = (new.required_force, old.required_force,
                                rep.applied)
        new, old, applied = forces["off"]
        assert new == old and not applied
        new, old, applied = forces["eurocode7_da1c2"]
        assert applied and new > old, forces


# ======================================================================
# Optimisation
# ======================================================================
def _block(ws):
    import test_optimize_wiring_v1104 as ow
    return ws.add(ow._slope()).id


class TestOptimisationThroughTheDoor:
    def test_reproducible_and_a_new_result(self):
        from ogr_api import call
        ws = _ws()
        pid = _block(ws)
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        start = run["summary"]["methods"][0]["critical"]["fos"]
        outs = [call(ws, "optimize_run", result_id=run["result_id"],
                     max_iterations=150, wait_seconds=300)
                for _ in range(2)]
        a, b = (o["summary"]["final_fos"] for o in outs)
        assert a == b and a <= start + 1e-12, (a, b, start)
        assert outs[0]["result_id"] != run["result_id"]
        again = call(ws, "results_get", result_id=run["result_id"],
                     view="critical")["critical"]["bishop_simplified"]
        assert again["fos"] == start
        opt = call(ws, "results_get", result_id=outs[0]["result_id"],
                   view="critical")["critical"]["bishop_simplified"]
        assert abs(opt["fos"] - a) < 1e-6       # stored to 6 decimals

    def test_a_circle_is_refused(self):
        from ogr_api import Conflict, call
        ws = _ws()
        pid = _slope(ws)
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        with pytest.raises(Conflict):
            call(ws, "optimize_run", result_id=run["result_id"])


# ======================================================================
# Interpretation
# ======================================================================
class TestInterpretation:
    def test_the_slice_table_is_the_references(self):
        """Row 1 of the Ej_2 report, Ordinary method, as
        test_interpret_slice_data_v187 checks it through the panel."""
        from test_interpret_slice_data_v187 import _ej2_reference_result
        from ogr_slip2d.interpretation import slice_rows
        _p, res = _ej2_reference_result()
        row = slice_rows(res)[0]
        for k, ref in (("width", 1.04705), ("weight", 9.40306),
                       ("cohesion", 26.0), ("friction_angle", 30.0),
                       ("tau_f", 31.082), ("tau_m", 27.8907),
                       ("sigma_n", 8.80223), ("sigma_n_eff", 8.80223),
                       ("pore_pressure", 0.0)):
            assert abs(row[k] - ref) <= 1e-3 * max(1.0, abs(ref)), (k, row[k])

    def test_the_area_is_the_circular_segments(self):
        """A circle under flat ground: the sliding mass is the segment
        R²(θ - sin θ)/2; the slices replace the arc by chords, which
        costs O(1/n²)."""
        from ogr_api import call
        from ogr_slip2d.interpretation import surface_area
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        ws = _ws()
        pid = call(ws, "project_new", name="Box")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
            "materials": [{"name": "S", "unit_weight": 19,
                           "strength": _SOIL}]})
        n = 50
        res = GridSearch(method=get_method("ordinary_fellenius")(),
                         num_slices=n, min_area=0.0).evaluate_circle(
            ws.get(pid).project,
            SlipCircle(centre_x=10.0, centre_y=18.0, radius=10.0))
        theta = 2.0 * math.acos(0.8)
        exact = 0.5 * 100.0 * (theta - math.sin(theta))
        area = surface_area(res)
        assert 0 < exact - area < 2.0 * exact / n ** 2, (area, exact)

    def test_a_point_on_the_unsliced_side_is_not_on_the_surface(self):
        from ogr_api import call
        from ogr_slip2d.interpretation import (surface_path,
                                               surfaces_through_point)
        ws = _ws()
        pid = _slope(ws)
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        _h, res = ws.find_result(run["result_id"])
        sr = res.payload()["results"]["bishop_simplified"]
        crit = sr.critical
        sd = crit.surface.to_dict()
        top = (sd["centre_x"], sd["centre_y"] + sd["radius"])
        on_top = [r for _d, r in surfaces_through_point(sr, *top, 0.01)]
        assert crit not in on_top
        mid = surface_path(crit)[len(surface_path(crit)) // 2]
        on_base = [r for _d, r in surfaces_through_point(sr, *mid, 0.01)]
        assert crit in on_base
        got = call(ws, "results_query", result_id=run["result_id"],
                   view="surfaces_through_point", point_xy=list(mid),
                   tolerance=0.01)
        assert got["count"] == len(on_base)

    def test_an_intercept_at_zero_is_not_missing(self):
        from types import SimpleNamespace

        from ogr_slip2d.interpretation import slope_intercepts
        surf = SimpleNamespace(x_range=lambda: (-3.0, 8.0),
                               to_dict=lambda: {"x_left": 0.0,
                                                "x_right": 5.0})
        assert slope_intercepts(SimpleNamespace(surface=surf)) == (0.0, 5.0)

    def test_the_census_adds_up_and_filters_by_code(self):
        from ogr_api import call
        from ogr_slip2d.interpretation import error_code
        ws = _ws()
        pid = _slope(ws)
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        rid = run["result_id"]
        census = call(ws, "results_query", result_id=rid,
                      view="invalid_summary")["census"]
        _h, res = ws.find_result(rid)
        sr = res.payload()["results"]["bishop_simplified"]
        codes = [error_code(r) for r in sr.evaluations]
        assert sum(census["by_code"].values()) == sum(
            c is not None for c in codes)
        raw = call(ws, "results_query", result_id=rid, view="raw_data",
                   n=5)
        assert raw["rows"] == len(sr.evaluations)
        for code, count in census["by_code"].items():
            got = call(ws, "results_query", result_id=rid, view="filter",
                       code=int(code), n=1000)
            assert got["count"] == count
            assert all(s["error_code"] == int(code)
                       for s in got["surfaces"])

    def test_parameters_a_view_does_not_read_are_refused(self):
        from ogr_api import Conflict, call
        ws = _ws()
        pid = _slope(ws)
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        with pytest.raises(Conflict):
            call(ws, "results_query", result_id=run["result_id"],
                 view="raw_data", bins=4)
        with pytest.raises(Conflict):
            call(ws, "results_query", result_id=run["result_id"],
                 view="histogram")


# ======================================================================
# Inventory, and the interface
# ======================================================================
class TestNothingIsPending:
    def test_every_action_is_mapped_or_ui_only(self):
        from ogr_api.inventory import PENDING, PENDING_CEILING, coverage
        assert PENDING == {} and PENDING_CEILING == 0
        assert coverage()["mapped"] == 113


def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


class TestTheInterface:
    def test_a_new_project_drops_the_old_statistics(self):
        if _qt() is None:
            return
        from ogr_core.project import Project
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        try:
            w._prob_result = object()
            w._sens_result = object()
            w._back_analysis_result = object()
            w._attach_project(Project("Other"))
            assert w._prob_result is None and w._sens_result is None
            assert w._back_analysis_result is None
            assert not w._actions["stat_show"].isEnabled()
        finally:
            w.close()
            w.deleteLater()

    def test_optimize_surfaces_makes_a_new_result(self):
        if _qt() is None:
            return
        import test_optimize_wiring_v1104 as ow
        from PySide6.QtWidgets import QInputDialog

        from ogr_gui.main_window import MainWindow
        from ogr_slip2d.analysis_runner import build_search
        p = ow._slope()
        sr = build_search(p, "bishop_simplified").run(p)
        crit = sr.critical
        before = (crit.fos, crit.surface, crit.slices)
        w = MainWindow()
        raw = QInputDialog.getInt
        QInputDialog.getInt = staticmethod(
            lambda *a, **k: (ow._MAX_ITERATIONS, True))
        try:
            w._attach_project(p)
            w.last_search_results = {"bishop_simplified": sr}
            w.last_search_result = sr
            w._optimize_surfaces()
            new = w.last_search_results["bishop_simplified"]
            assert new is not sr and new.optimized is not None
            assert (crit.fos, crit.surface, crit.slices) == before
            assert len(new.evaluations) == len(sr.evaluations) + 1
        finally:
            QInputDialog.getInt = raw
            w.close()
            w.deleteLater()
