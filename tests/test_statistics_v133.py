# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.33 — Statistical core (Phase P0 of the probabilistic plan).

Validation against ANALYTIC targets rather than snapshots:

* each distribution must reproduce its theoretical mean and standard
  deviation from a large sample;
* Uniform and Triangular are checked against their closed-form standard
  deviations (span/sqrt(12) and span/sqrt(24));
* Latin Hypercube must be markedly more accurate than Monte Carlo at the
  same sample count — the reference states 1000 LHS samples give results
  comparable to 5000 Monte Carlo ones;
* truncation by RELATIVE min/max must be strictly respected, and must
  preserve the stratification (no sample lost);
* the c-phi rank correlation must hit the requested coefficient while
  leaving the marginal distribution untouched;
* probability of failure and reliability index against hand-computable
  cases.
"""
from __future__ import annotations

import math
import statistics as pystat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    SampleStatistics,
    SamplingMethod as SM,
    correlate_pair,
    sample_variables,
    uniform_samples,
)

# 6000 LHS samples give a mean error around 1e-3 for these
# distributions, comfortably inside the tolerances asserted below,
# while keeping the whole file under a couple of seconds.
N_BIG = 6000


def _draw(dist, n=N_BIG, method=SM.LATIN_HYPERCUBE, seed=1):
    return sample_variables({"x": dist}, n, method, seed=seed)["x"]


class TestDistributionMoments:
    def test_normal(self):
        d = Distribution(DT.NORMAL, mean=10.0, std_dev=2.0,
                         rel_min=8.0, rel_max=8.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.05
        assert abs(pystat.stdev(s) - 2.0) < 0.05

    def test_uniform_closed_form(self):
        """sigma = span / sqrt(12)."""
        d = Distribution(DT.UNIFORM, mean=10.0, rel_min=3.0, rel_max=3.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.05
        assert abs(pystat.stdev(s) - 6.0 / math.sqrt(12.0)) < 0.05

    def test_triangular_closed_form(self):
        """Symmetric triangular: sigma = span / sqrt(24)."""
        d = Distribution(DT.TRIANGULAR, mean=10.0, rel_min=4.0,
                         rel_max=4.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.05
        assert abs(pystat.stdev(s) - 8.0 / math.sqrt(24.0)) < 0.05

    def test_lognormal(self):
        d = Distribution(DT.LOGNORMAL, mean=10.0, std_dev=2.0,
                         rel_min=9.0, rel_max=20.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.1
        assert abs(pystat.stdev(s) - 2.0) < 0.1
        assert min(s) > 0.0            # lognormal is strictly positive

    def test_gamma(self):
        d = Distribution(DT.GAMMA, mean=10.0, std_dev=2.0,
                         rel_min=9.0, rel_max=20.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.1
        assert abs(pystat.stdev(s) - 2.0) < 0.1

    def test_beta(self):
        d = Distribution(DT.BETA, mean=10.0, std_dev=2.0,
                         rel_min=6.0, rel_max=6.0)
        s = _draw(d)
        assert abs(pystat.mean(s) - 10.0) < 0.1
        assert abs(pystat.stdev(s) - 2.0) < 0.1

    def test_exponential(self):
        d = Distribution(DT.EXPONENTIAL, mean=10.0, rel_min=10.0,
                         rel_max=90.0)
        s = _draw(d)
        # Truncation at 9 means removes a small tail, so the sample mean
        # sits marginally below the nominal one.
        assert 9.5 < pystat.mean(s) <= 10.2
        assert min(s) >= 0.0

    def test_all_seven_distributions_available(self):
        for t in (DT.NORMAL, DT.UNIFORM, DT.TRIANGULAR, DT.BETA,
                  DT.EXPONENTIAL, DT.LOGNORMAL, DT.GAMMA):
            d = Distribution(t, mean=10.0, std_dev=1.5, rel_min=5.0,
                             rel_max=5.0)
            s = _draw(d, n=500)
            assert len(s) == 500, t


class TestTruncation:
    def test_relative_limits_are_respected(self):
        d = Distribution(DT.NORMAL, mean=10.0, std_dev=5.0,
                         rel_min=2.0, rel_max=3.0)
        s = _draw(d)
        assert min(s) >= 8.0 - 1e-9
        assert max(s) <= 13.0 + 1e-9

    def test_asymmetric_limits(self):
        d = Distribution(DT.NORMAL, mean=30.0, std_dev=6.0,
                         rel_min=10.0, rel_max=2.0)
        s = _draw(d)
        assert min(s) >= 20.0 - 1e-9
        assert max(s) <= 32.0 + 1e-9
        assert pystat.mean(s) < 30.0      # skewed by the tighter cap

    def test_truncation_loses_no_samples(self):
        """Truncation is applied by remapping the uniform variate, not by
        rejection, so every requested sample is produced."""
        d = Distribution(DT.NORMAL, mean=10.0, std_dev=10.0,
                         rel_min=0.5, rel_max=0.5)
        assert len(_draw(d, n=777)) == 777

    def test_zero_range_is_deterministic(self):
        d = Distribution(DT.NORMAL, mean=7.0, std_dev=2.0,
                         rel_min=0.0, rel_max=0.0)
        assert d.is_random is False
        assert all(abs(v - 7.0) < 1e-12 for v in _draw(d, n=50))

    def test_none_type_is_deterministic(self):
        d = Distribution(DT.NONE, mean=5.0, rel_min=2.0, rel_max=2.0)
        assert d.is_random is False
        assert all(v == 5.0 for v in _draw(d, n=20))


class TestSampling:
    def test_latin_hypercube_stratifies(self):
        """Exactly one variate must fall inside each of the n strata."""
        n = 500
        us = uniform_samples(n, SM.LATIN_HYPERCUBE)
        strata = sorted(int(u * n) for u in us)
        assert strata == list(range(n))

    def test_monte_carlo_does_not_stratify(self):
        us = uniform_samples(500, SM.MONTE_CARLO)
        strata = sorted(int(u * 500) for u in us)
        assert strata != list(range(500))

    def test_latin_hypercube_is_more_accurate(self):
        """The reference's claim, verified: LHS converges markedly faster
        than Monte Carlo for the same sample count."""
        d = Distribution(DT.NORMAL, mean=10.0, std_dev=2.0,
                         rel_min=8.0, rel_max=8.0)
        err_mc, err_lhs = [], []
        for seed in range(10):
            err_mc.append(abs(pystat.mean(
                _draw(d, 200, SM.MONTE_CARLO, seed)) - 10.0))
            err_lhs.append(abs(pystat.mean(
                _draw(d, 200, SM.LATIN_HYPERCUBE, seed)) - 10.0))
        assert pystat.mean(err_lhs) < pystat.mean(err_mc) / 5.0

    def test_seed_is_reproducible(self):
        d = Distribution(DT.NORMAL, mean=1.0, std_dev=0.2,
                         rel_min=0.6, rel_max=0.6)
        assert _draw(d, 100, seed=7) == _draw(d, 100, seed=7)
        assert _draw(d, 100, seed=7) != _draw(d, 100, seed=8)

    def test_variables_sampled_independently(self):
        a = Distribution(DT.NORMAL, mean=10, std_dev=2, rel_min=6,
                         rel_max=6)
        b = Distribution(DT.NORMAL, mean=30, std_dev=5, rel_min=15,
                         rel_max=15)
        out = sample_variables({"a": a, "b": b}, 2000,
                               SM.LATIN_HYPERCUBE, seed=2)
        assert abs(pystat.correlation(out["a"], out["b"])) < 0.1


class TestCorrelation:
    def _pair(self, n=2000):
        c = sample_variables(
            {"c": Distribution(DT.NORMAL, mean=10, std_dev=2, rel_min=6,
                               rel_max=6)}, n, SM.LATIN_HYPERCUBE,
            seed=3)["c"]
        p = sample_variables(
            {"p": Distribution(DT.NORMAL, mean=30, std_dev=4, rel_min=12,
                               rel_max=12)}, n, SM.LATIN_HYPERCUBE,
            seed=4)["p"]
        return c, p

    def test_requested_coefficient_is_achieved(self):
        c, p = self._pair()
        for rho in (-0.9, -0.7, -0.3, 0.5, 0.8):
            out = correlate_pair(c, p, rho)
            got = pystat.correlation(c, out)
            assert abs(got - rho) < 0.05, (rho, got)

    def test_marginal_distribution_preserved(self):
        """Only the pairing changes: the sorted values are identical."""
        c, p = self._pair(1000)
        out = correlate_pair(c, p, -0.7)
        assert sorted(out) == sorted(p)

    def test_zero_correlation_is_a_no_op(self):
        c, p = self._pair(500)
        assert correlate_pair(c, p, 0.0) == list(p)


class TestSampleStatistics:
    def test_basic_moments(self):
        st = SampleStatistics(values=[1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(st.mean - 3.0) < 1e-12
        assert abs(st.std_dev - pystat.stdev([1, 2, 3, 4, 5])) < 1e-12
        assert st.minimum == 1.0 and st.maximum == 5.0
        assert st.n == 5

    def test_probability_of_failure(self):
        st = SampleStatistics(values=[0.8, 0.9, 1.1, 1.2, 1.5])
        assert abs(st.probability_of_failure() - 0.4) < 1e-12

    def test_probability_of_failure_extremes(self):
        assert SampleStatistics(values=[0.5] * 10
                                ).probability_of_failure() == 1.0
        assert SampleStatistics(values=[2.0] * 10
                                ).probability_of_failure() == 0.0

    def test_reliability_index(self):
        """beta = (mean - 1) / sigma, hand-checked."""
        vals = [1.2, 1.4, 1.6, 1.8, 2.0]
        st = SampleStatistics(values=vals)
        expected = (pystat.mean(vals) - 1.0) / pystat.stdev(vals)
        assert abs(st.reliability_index() - expected) < 1e-12

    def test_lognormal_reliability_index(self):
        st = SampleStatistics(values=[1.2, 1.4, 1.6, 1.8, 2.0])
        assert math.isfinite(st.lognormal_reliability_index())
        assert st.lognormal_reliability_index() > 0

    def test_histogram_counts_everything(self):
        st = SampleStatistics(values=[float(i) / 10 for i in range(100)])
        hist = st.histogram(bins=10)
        assert len(hist) == 10
        assert sum(c for _x, c in hist) == 100

    def test_convergence_ends_at_full_sample(self):
        st = SampleStatistics(values=[1.0 + 0.001 * i for i in range(500)])
        conv = st.convergence(steps=20)
        assert conv[-1][0] == 500
        assert abs(conv[-1][1] - st.mean) < 1e-9

    def test_empty_statistics_are_safe(self):
        st = SampleStatistics()
        assert st.n == 0
        assert math.isnan(st.mean)
        assert math.isnan(st.probability_of_failure())
        assert st.histogram() == []
        assert st.convergence() == []


class TestSerialisation:
    def test_round_trip(self):
        d = Distribution(DT.LOGNORMAL, mean=12.5, std_dev=3.0,
                         rel_min=6.0, rel_max=9.0)
        d2 = Distribution.from_dict(d.to_dict())
        assert d2.dist_type == DT.LOGNORMAL
        assert abs(d2.mean - 12.5) < 1e-12
        assert abs(d2.rel_max - 9.0) < 1e-12
        assert abs(d2.value_from_uniform(0.5)
                   - d.value_from_uniform(0.5)) < 1e-12

    def test_curve_for_plotting(self):
        d = Distribution(DT.NORMAL, mean=10.0, std_dev=2.0, rel_min=6.0,
                         rel_max=6.0)
        curve = d.curve(50)
        assert len(curve) == 50
        assert curve[0][0] >= d.low - 1e-9
        assert curve[-1][0] <= d.high + 1e-9
        peak = max(curve, key=lambda t: t[1])[0]
        assert abs(peak - 10.0) < 0.5
