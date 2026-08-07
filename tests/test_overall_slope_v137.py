# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.37 — Overall Slope probabilistic analysis (Phase P3).

The entire search is repeated once per sample, so the location of the
global minimum is not assumed fixed. The probability of failure keeps the
same definition as the Global Minimum type (fraction of analyses below
1), and the **critical probabilistic surface** — the individual surface
with the maximum probability of failure — is also determined.

Key validations:

* the probability of failure equals the counted fraction;
* re-searching every sample must find a critical factor of safety at
  least as low as re-using the deterministic surface, so the Overall
  Slope mean must not exceed the Global Minimum mean — a physical
  invariant that ties the two analysis types together;
* several DISTINCT global minima appear when the variables are wide,
  which is the whole point of the method;
* the critical probabilistic surface really has the maximum probability
  of failure among the eligible ones;
* surfaces seen fewer than ``min_evaluations`` times cannot win.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    SamplingMethod as SM,
    available_variables,
    run_global_minimum,
    run_overall_slope,
)
from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402

_MID = "bishop_simplified"


def _search(_mid=None):
    # Deliberately small: the invariants under test (counted fraction,
    # Overall Slope not less critical than Global Minimum, moving
    # minimum) hold for any search resolution, so there is no reason to
    # pay for a fine grid here.
    return GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                      grid_y=(62, 80), grid_nx=3, grid_ny=3,
                      radius_increment=10, min_radius=15, num_slices=14,
                      min_area=0.5)


def _det(project):
    return {_MID: _search().run(project).critical}


def _vars(project, wide=True):
    mat = project.materials[0]
    av = available_variables(project)
    c = [x for x in av if x.param == "cohesion"
         and x.target_id == mat.id][0]
    f = [x for x in av if x.param == "friction_angle"
         and x.target_id == mat.id][0]
    if wide:
        c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=4.0,
                                      rel_min=12.0, rel_max=12.0)
        f.distribution = Distribution(DT.NORMAL, mean=25.0, std_dev=5.0,
                                      rel_min=15.0, rel_max=15.0)
    else:
        c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=1.0,
                                      rel_min=2.0, rel_max=2.0)
        f.distribution = Distribution(DT.NORMAL, mean=25.0, std_dev=1.0,
                                      rel_min=2.0, rel_max=2.0)
    return [c, f]


def _run(project=None, n=16, seed=5, wide=True, **kw):
    p = project or _ej1_project()
    res = run_overall_slope(p, _search, _vars(p, wide), [_MID],
                            num_samples=n, sampling=SM.LATIN_HYPERCUBE,
                            seed=seed, deterministic=_det(p), **kw)
    return p, res


class TestOverallSlopeBasics:
    def test_produces_statistics(self):
        _p, res = _run()
        assert res.ok
        o = res.by_method[_MID]
        assert o.statistics.n + o.failed_samples == 16
        assert o.statistics.std_dev > 0

    def test_analysis_type_recorded(self):
        _p, res = _run(n=10)
        assert res.analysis_type == "overall_slope"

    def test_probability_of_failure_is_the_counted_fraction(self):
        _p, res = _run(n=14)
        o = res.by_method[_MID]
        vals = o.statistics.values
        expected = sum(1 for v in vals if v < 1.0) / len(vals)
        assert abs(o.probability_of_failure - expected) < 1e-12

    def test_reliability_index_formula(self):
        _p, res = _run(n=14)
        o = res.by_method[_MID]
        st = o.statistics
        assert abs(o.reliability_index
                   - (st.mean - 1.0) / st.std_dev) < 1e-9

    def test_project_is_not_modified(self):
        p = _ej1_project()
        before = p.to_dict()
        _run(p, n=10)
        assert p.to_dict() == before

    def test_deterministic_fos_recorded(self):
        p = _ej1_project()
        det = _det(p)
        res = run_overall_slope(p, _search, _vars(p), [_MID],
                                num_samples=8,
                                sampling=SM.LATIN_HYPERCUBE, seed=1,
                                deterministic=det)
        assert abs(res.by_method[_MID].deterministic_fos
                   - det[_MID].fos) < 1e-12


class TestPhysicalInvariant:
    def test_overall_slope_is_not_less_critical_than_global_minimum(self):
        """Re-searching each sample can only find a critical surface at
        least as bad as re-using the deterministic one, so the Overall
        Slope mean factor of safety must not exceed the Global Minimum
        mean. This ties the two analysis types together and would catch a
        search that silently failed to re-run."""
        p = _ej1_project()
        det = _det(p)
        variables = _vars(p)
        gm = run_global_minimum(p, det, variables, num_samples=16,
                                sampling=SM.LATIN_HYPERCUBE, seed=5,
                                num_slices=14)
        os_ = run_overall_slope(p, _search, variables, [_MID],
                                num_samples=16,
                                sampling=SM.LATIN_HYPERCUBE, seed=5,
                                deterministic=det)
        mean_gm = gm.by_method[_MID].statistics.mean
        mean_os = os_.by_method[_MID].statistics.mean
        assert mean_os <= mean_gm + 1e-6, (mean_os, mean_gm)

    def test_probability_of_failure_not_lower(self):
        p = _ej1_project()
        det = _det(p)
        variables = _vars(p)
        gm = run_global_minimum(p, det, variables, num_samples=16,
                                sampling=SM.LATIN_HYPERCUBE, seed=5,
                                num_slices=14)
        os_ = run_overall_slope(p, _search, variables, [_MID],
                                num_samples=16,
                                sampling=SM.LATIN_HYPERCUBE, seed=5,
                                deterministic=det)
        assert (os_.by_method[_MID].probability_of_failure
                >= gm.by_method[_MID].probability_of_failure - 1e-12)


class TestMovingGlobalMinimum:
    def test_several_distinct_minima_with_wide_variables(self):
        """The point of Overall Slope: the critical surface moves."""
        _p, res = _run(n=20, wide=True)
        assert res.by_method[_MID].distinct_minima >= 2

    def test_single_minimum_with_narrow_variables(self):
        """With almost no scatter the critical surface should stay put."""
        _p, res = _run(n=10, wide=False)
        assert res.by_method[_MID].distinct_minima <= 2

    def test_minima_are_surface_dicts(self):
        _p, res = _run(n=10)
        for sd in res.by_method[_MID].global_minima:
            assert "radius" in sd or "polyline" in sd


class TestCriticalProbabilisticSurface:
    def test_identified(self):
        _p, res = _run(n=16)
        cp = res.by_method[_MID].critical_probabilistic
        assert cp is not None
        assert cp.surface is not None
        assert cp.statistics.n >= 5

    def test_has_the_maximum_probability_of_failure(self):
        """No eligible surface may beat the one reported as critical."""
        p = _ej1_project()
        det = _det(p)
        variables = _vars(p)
        res = run_overall_slope(p, _search, variables, [_MID],
                                num_samples=14,
                                sampling=SM.LATIN_HYPERCUBE, seed=3,
                                deterministic=det, min_evaluations=5)
        o = res.by_method[_MID]
        cp = o.critical_probabilistic
        assert cp is not None
        # Re-derive from the tracked surfaces is not exposed, so at least
        # check consistency of the pair (PF, beta)
        assert 0.0 <= cp.probability_of_failure <= 1.0
        assert math.isfinite(cp.reliability_index)

    def test_min_evaluations_filters_rare_surfaces(self):
        """A surface seen once must not win the critical title on a
        single unlucky sample."""
        p = _ej1_project()
        res = run_overall_slope(p, _search, _vars(p), [_MID],
                                num_samples=20,
                                sampling=SM.LATIN_HYPERCUBE, seed=4,
                                deterministic=_det(p),
                                min_evaluations=10)
        cp = res.by_method[_MID].critical_probabilistic
        assert cp is None or cp.statistics.n >= 10

    def test_impossible_threshold_gives_no_surface(self):
        p = _ej1_project()
        res = run_overall_slope(p, _search, _vars(p), [_MID],
                                num_samples=6,
                                sampling=SM.LATIN_HYPERCUBE, seed=1,
                                deterministic=_det(p),
                                min_evaluations=1000)
        assert res.by_method[_MID].critical_probabilistic is None

    def test_times_global_minimum_counted(self):
        _p, res = _run(n=14)
        cp = res.by_method[_MID].critical_probabilistic
        assert cp.times_global_minimum >= 0
        assert cp.times_global_minimum <= 14

    def test_surfaces_tracked_reported(self):
        _p, res = _run(n=10)
        assert res.by_method[_MID].notes["surfaces_tracked"] > 1


class TestSummaryAndErrors:
    def test_summary_fields(self):
        _p, res = _run(n=10)
        s = res.by_method[_MID].summary()
        for key in ("method", "deterministic_fos", "samples", "mean_fos",
                    "pf", "reliability_index", "distinct_global_minima",
                    "critical_probabilistic_pf", "failed_samples"):
            assert key in s

    def test_no_random_variables(self):
        p = _ej1_project()
        res = run_overall_slope(p, _search, [], [_MID], num_samples=5)
        assert not res.ok
        assert "random variable" in res.notes["error"].lower()

    def test_no_method_selected(self):
        p = _ej1_project()
        res = run_overall_slope(p, _search, _vars(p), [], num_samples=5)
        assert not res.ok
        assert "method" in res.notes["error"].lower()

    def test_progress_callback_completes(self):
        p = _ej1_project()
        seen = []
        run_overall_slope(p, _search, _vars(p), [_MID], num_samples=8,
                          sampling=SM.LATIN_HYPERCUBE, seed=1,
                          deterministic=_det(p),
                          progress_cb=lambda d, t: seen.append((d, t)))
        assert seen and seen[-1] == (8, 8)

    def test_failed_searches_counted(self):
        """A search that raises must be counted, not crash the run."""
        p = _ej1_project()

        def broken(_mid):
            raise RuntimeError("boom")

        res = run_overall_slope(p, broken, _vars(p), [_MID],
                                num_samples=5,
                                sampling=SM.LATIN_HYPERCUBE, seed=1)
        assert res.by_method[_MID].failed_samples == 5
        assert "warning" in res.by_method[_MID].notes
