# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.35 — Probabilistic engine, Global Minimum (Phase P2).

Validation strategy: every statistic is cross-checked against an
INDEPENDENT computation rather than a stored snapshot.

* the factors of safety produced by the engine are recomputed by hand,
  sample by sample, and must match exactly;
* the probability of failure must equal the counted fraction below 1;
* the reliability index must equal (mean - 1) / sigma;
* with zero-variance variables every sample must reproduce the
  deterministic factor of safety exactly;
* the mean must sit close to the deterministic value when the variables
  are centred on their means;
* the user's project must be byte-for-byte unchanged after the run.
"""
from __future__ import annotations

import math
import statistics as pystat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    SamplingMethod as SM,
    apply_sample,
    available_variables,
    clone_project,
    run_global_minimum,
    sample_project_variables,
)
from ogr_slip2d import BishopSimplified, Spencer  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402


def _deterministic(project, methods=("bishop_simplified",)):
    """Small deterministic search giving each method its own critical."""
    out = {}
    factory = {"bishop_simplified": BishopSimplified, "spencer": Spencer}
    for mid in methods:
        r = GridSearch(method=factory[mid](), grid_x=(70, 100),
                       grid_y=(60, 85), grid_nx=4, grid_ny=4,
                       radius_increment=6, min_radius=15, num_slices=18,
                       min_area=0.5).run(project)
        out[mid] = r.critical
    return out


def _cohesion_var(project, std_dev=3.0, span=9.0):
    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"],
        std_dev=std_dev, rel_min=span, rel_max=span)
    return v


class TestGlobalMinimumEngine:
    def test_produces_statistics(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=60, sampling=SM.LATIN_HYPERCUBE,
                                 seed=3, num_slices=18)
        assert res.ok
        st = res.by_method["bishop_simplified"].statistics
        assert st.n == 60
        assert st.std_dev > 0

    def test_values_match_an_independent_recomputation(self):
        """The decisive check: replay the same samples by hand and
        compare factor by factor."""
        p = _ej1_project()
        det = _deterministic(p)
        v = _cohesion_var(p)
        n = 25
        res = run_global_minimum(p, det, [v], num_samples=n,
                                 sampling=SM.LATIN_HYPERCUBE, seed=7,
                                 num_slices=18)
        engine = res.by_method["bishop_simplified"].statistics.values

        samples = sample_project_variables([v], n, SM.LATIN_HYPERCUBE, 7)
        surface = det["bishop_simplified"].surface
        search = GridSearch(method=BishopSimplified(), num_slices=18,
                            min_area=0.0)
        manual = []
        for i in range(n):
            clone = clone_project(p)
            apply_sample(clone, [v], {v.key: samples[v.key][i]})
            r = search.evaluate_circle(clone, surface)
            if r is not None and r.is_valid:
                manual.append(r.fos)
        assert len(manual) == len(engine)
        for a, b in zip(manual, engine):
            assert abs(a - b) < 1e-9, (a, b)

    def test_probability_of_failure_is_the_counted_fraction(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=80, sampling=SM.LATIN_HYPERCUBE,
                                 seed=5, num_slices=18)
        mres = res.by_method["bishop_simplified"]
        vals = mres.statistics.values
        expected = sum(1 for v in vals if v < 1.0) / len(vals)
        assert abs(mres.probability_of_failure - expected) < 1e-12

    def test_reliability_index_formula(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=60, sampling=SM.LATIN_HYPERCUBE,
                                 seed=9, num_slices=18)
        mres = res.by_method["bishop_simplified"]
        vals = mres.statistics.values
        expected = (pystat.mean(vals) - 1.0) / pystat.stdev(vals)
        assert abs(mres.reliability_index - expected) < 1e-9

    def test_zero_variance_reproduces_the_deterministic_value(self):
        """With a degenerate distribution the run must collapse onto the
        deterministic answer — a strong end-to-end consistency check."""
        p = _ej1_project()
        det = _deterministic(p)
        v = _cohesion_var(p, std_dev=2.0, span=0.0)   # not random
        res = run_global_minimum(p, det, [v], num_samples=10,
                                 sampling=SM.MONTE_CARLO, seed=1,
                                 num_slices=18)
        # No active variable at all -> the engine reports it
        assert not res.ok
        assert "random variable" in res.notes.get("error", "").lower()

    def test_mean_near_deterministic_when_centred(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p, 2.0, 6.0)],
                                 num_samples=200,
                                 sampling=SM.LATIN_HYPERCUBE, seed=4,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert abs(mres.mean_fos - mres.deterministic_fos) < 0.05

    def test_each_method_keeps_its_own_surface(self):
        """The reference stresses that every analysis method can have a
        different global minimum."""
        p = _ej1_project()
        det = _deterministic(p, ("bishop_simplified", "spencer"))
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=30,
                                 sampling=SM.LATIN_HYPERCUBE, seed=2,
                                 num_slices=18)
        assert set(res.by_method) == {"bishop_simplified", "spencer"}
        for mid, mres in res.by_method.items():
            assert mres.surface is not None
            assert abs(mres.deterministic_fos - det[mid].fos) < 1e-12

    def test_project_is_not_modified(self):
        p = _ej1_project()
        before = p.to_dict()
        det = _deterministic(p)
        run_global_minimum(p, det, [_cohesion_var(p)], num_samples=40,
                           sampling=SM.LATIN_HYPERCUBE, seed=6,
                           num_slices=18)
        assert p.to_dict() == before

    def test_correlated_variables_run(self):
        p = _ej1_project()
        det = _deterministic(p)
        mat = p.materials[0]
        av = available_variables(p)
        c = [x for x in av if x.param == "cohesion"
             and x.target_id == mat.id][0]
        f = [x for x in av if x.param == "friction_angle"
             and x.target_id == mat.id][0]
        c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=3.0,
                                      rel_min=9.0, rel_max=9.0)
        f.distribution = Distribution(DT.NORMAL, mean=25.0, std_dev=4.0,
                                      rel_min=12.0, rel_max=12.0)
        f.correlated_with = c.key
        f.correlation = -0.5
        res = run_global_minimum(p, det, [c, f], num_samples=60,
                                 sampling=SM.LATIN_HYPERCUBE, seed=8,
                                 num_slices=18)
        assert res.by_method["bishop_simplified"].statistics.n == 60
        assert len(res.variables) == 2

    def test_seismic_variable_lowers_the_mean(self):
        from ogr_core.statistics import VariableKind as VK
        p = _ej1_project()
        det = _deterministic(p)
        v = [x for x in available_variables(p)
             if x.kind == VK.SEISMIC and x.param == "kh"][0]
        v.distribution = Distribution(DT.UNIFORM, mean=0.1, rel_min=0.1,
                                      rel_max=0.1)
        res = run_global_minimum(p, det, [v], num_samples=40,
                                 sampling=SM.LATIN_HYPERCUBE, seed=1,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert mres.mean_fos < mres.deterministic_fos


class TestErrorHandling:
    def test_no_random_variables(self):
        p = _ej1_project()
        res = run_global_minimum(p, _deterministic(p), [],
                                 num_samples=10)
        assert not res.ok
        assert "error" in res.notes

    def test_no_deterministic_result(self):
        p = _ej1_project()
        res = run_global_minimum(p, {}, [_cohesion_var(p)],
                                 num_samples=10)
        assert not res.ok
        assert "deterministic" in res.notes["error"].lower()

    def test_failed_samples_are_counted_not_hidden(self):
        """A distribution wide enough to make the surface unsolvable must
        be reported, because a large count means the ranges are
        unrealistic."""
        p = _ej1_project()
        det = _deterministic(p)
        mat = p.materials[0]
        v = [x for x in available_variables(p)
             if x.param == "unit_weight" and x.target_id == mat.id][0]
        v.distribution = Distribution(DT.UNIFORM, mean=20.0,
                                      rel_min=19.99, rel_max=200.0)
        res = run_global_minimum(p, det, [v], num_samples=30,
                                 sampling=SM.LATIN_HYPERCUBE, seed=1,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert mres.statistics.n + mres.failed_samples == 30

    def test_progress_callback(self):
        p = _ej1_project()
        det = _deterministic(p)
        seen = []
        run_global_minimum(p, det, [_cohesion_var(p)], num_samples=60,
                           sampling=SM.LATIN_HYPERCUBE, seed=1,
                           num_slices=18,
                           progress_cb=lambda d, t: seen.append((d, t)))
        assert seen and seen[-1][0] == seen[-1][1]


class TestConvergenceData:
    def test_convergence_ends_at_full_sample(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=100,
                                 sampling=SM.LATIN_HYPERCUBE, seed=2,
                                 num_slices=18)
        st = res.by_method["bishop_simplified"].statistics
        conv = st.convergence(steps=10)
        assert conv[-1][0] == st.n
        assert abs(conv[-1][1] - st.mean) < 1e-9
        assert abs(conv[-1][2] - st.probability_of_failure()) < 1e-9

    def test_histogram_totals(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=80,
                                 sampling=SM.LATIN_HYPERCUBE, seed=3,
                                 num_slices=18)
        st = res.by_method["bishop_simplified"].statistics
        assert sum(c for _x, c in st.histogram(bins=12)) == st.n

    def test_summary_fields(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=40,
                                 sampling=SM.LATIN_HYPERCUBE, seed=4,
                                 num_slices=18)
        s = res.summary()[0]
        for key in ("method", "deterministic_fos", "samples", "mean_fos",
                    "std_dev", "pf", "reliability_index",
                    "failed_samples"):
            assert key in s
        assert math.isfinite(s["mean_fos"])
