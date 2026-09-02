# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.145 — Truncation variance and variance propagation (defect D49).

D49 reported that the reliability index of verification problem 28 came
out systematically HIGH — the slope looking more reliable than it is —
and pointed at the sampler: three of its variables truncate the cohesion
at zero, which for c1 lands at -2.70 sigma, and a truncation narrows a
distribution.

Both halves of that were measurable, and neither test existed:

* how much a truncation at about three sigma actually narrows a normal.
  test_statistics_v133 checks the LIMITS of the truncation (minimum,
  maximum, no sample lost) but never its VARIANCE, so nothing pinned the
  magnitude. It is 1.3 % at +-3 sigma and 2.1 % at -2.70/+3.00 sigma —
  an order of magnitude short of the 10-20 % D49 was chasing;

* whether any dispersion is lost between the sampled inputs and the
  reported sigma of the factor of safety. With frictionless soil the
  factor of safety is EXACTLY linear in the cohesions, so

      Var[F] = a^T Sigma a,   a_i = dF/dc_i

  holds to machine precision against the REALISED sample covariance.
  That is an analytic identity, not a snapshot: it fails the moment a
  sample stops reaching a slice, and it is what would have caught a real
  variance loss.

Both are external checks. The truncated normal's moments are the closed
form of Johnson, Kotz & Balakrishnan (1994), Continuous Univariate
Distributions, vol. 1, ch. 13; the propagation identity is the exact
variance of a linear form.

The closed form is compared against a MIDPOINT QUADRATURE of the
quantile function, u = (i + 1/2)/N, not against a random sample. The
mapping under test is a deterministic inverse-CDF remap, so quadrature
converges as O(1/N^2) — 1e-7 at N = 20000 — while Monte Carlo would only
give 0.5 % and could not resolve the 1.3 % effect it has to measure.
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
    apply_sample,
    available_variables,
    clone_project,
    run_global_minimum,
)
from ogr_slip2d.analysis_runner import build_method  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

# Quadrature nodes. 20000 puts the closed form within 1e-7, so the 1e-5
# tolerance below is a hundredfold margin and still a hundred times
# tighter than the effect it has to resolve.
_NODES = 20000

# The surface used for the propagation identity: it cuts all three
# materials with comparable influence (dF/dc = 0.0028 / 0.0046 / 0.0047),
# so the OFF-DIAGONAL terms of the covariance carry real weight. A
# surface grazing a single layer would pass the identity without ever
# exercising them.
_CIRCLE = (70.0, 55.0, 45.0)
_SLICES = 18


def _normal_pdf(z):
    return math.exp(-z * z / 2.0) / math.sqrt(2.0 * math.pi)


def _normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _closed_form(mean, std_dev, rel_min, rel_max):
    """Mean and standard deviation of a normal truncated to
    [mean - rel_min, mean + rel_max] (Johnson, Kotz & Balakrishnan 1994,
    vol. 1, ch. 13)."""
    a = -abs(rel_min) / std_dev
    b = abs(rel_max) / std_dev
    z = _normal_cdf(b) - _normal_cdf(a)
    m = (_normal_pdf(a) - _normal_pdf(b)) / z
    var = 1.0 + (a * _normal_pdf(a) - b * _normal_pdf(b)) / z - m * m
    return mean + std_dev * m, std_dev * math.sqrt(var)


def _quadrature(dist, n=_NODES):
    """Mean and standard deviation of the mapping, by midpoint rule."""
    xs = dist.values_from_uniforms([(i + 0.5) / n for i in range(n)])
    m = sum(xs) / n
    return m, math.sqrt(sum((x - m) ** 2 for x in xs) / n)


# The two truncations that actually occur in verification problem 28:
# fifteen of its eighteen variables sit at +-3 sigma, and the three
# cohesions whose 3 sigma would go negative are clipped at zero instead.
_SYMMETRIC = dict(mean=43.0, std_dev=8.2, rel_min=24.6, rel_max=24.6)
_CLIPPED_AT_ZERO = dict(mean=55.0, std_dev=20.4, rel_min=55.0, rel_max=61.2)


class TestTruncatedNormalVariance:
    def test_mean_and_sigma_match_the_closed_form(self):
        for spec in (_SYMMETRIC, _CLIPPED_AT_ZERO):
            d = Distribution(DT.NORMAL, **spec)
            m_t, s_t = _closed_form(**spec)
            m_q, s_q = _quadrature(d)
            assert abs(m_q - m_t) <= 1e-5 * max(1.0, abs(m_t))
            assert abs(s_q / s_t - 1.0) <= 1e-5

    def test_a_three_sigma_truncation_narrows_by_about_two_percent(self):
        """The magnitude D49 rested on, pinned.

        The defect assumed that clipping the cohesion at zero (-2.70
        sigma) narrows the distribution by roughly 10 %. It narrows it by
        2.1 %; the symmetric +-3 sigma case by 1.3 %. If either ever
        moves far from these, the sampler has changed meaning and every
        dispersion the verification bank publishes is up for
        re-measurement.
        """
        _, s_sym = _quadrature(Distribution(DT.NORMAL, **_SYMMETRIC))
        _, s_clip = _quadrature(Distribution(DT.NORMAL, **_CLIPPED_AT_ZERO))
        assert 0.985 < s_sym / _SYMMETRIC["std_dev"] < 0.989
        assert 0.977 < s_clip / _CLIPPED_AT_ZERO["std_dev"] < 0.981

    def test_a_wide_range_leaves_sigma_untouched(self):
        """Control: with the limits far out the mapping must return the
        nominal sigma, or the truncation is being applied where it was
        not asked for.

        The tolerance here is 1e-4 rather than the 1e-5 above, and the
        reason is the quadrature, not the code. Past about six sigma the
        remap is effectively the untruncated quantile function, whose
        derivative blows up at u -> 0 and u -> 1; the midpoint rule then
        loses its O(1/N^2) rate in the tails and falls to O(1/N)
        (measured: -3.3e-5 at N = 20000, -3.3e-6 at N = 200000). Even so
        it is a hundredfold margin against the 1.3-2.1 % that the real
        truncations produce.
        """
        d = Distribution(DT.NORMAL, mean=43.0, std_dev=8.2,
                         rel_min=8.2 * 12, rel_max=8.2 * 12)
        _, s = _quadrature(d)
        assert abs(s / 8.2 - 1.0) < 1e-4


# ======================================================================
def _phi_zero_project():
    """The ej1 model with every friction angle at zero.

    Frictionless soil is what makes the identity exact: with phi = 0 the
    Bishop m-alpha loses its dependence on F and the factor of safety
    becomes a plain linear form in the cohesions, so the variance of a
    linear combination applies with no first-order approximation. The
    cohesions are scaled so the factor lands near unity, which changes
    none of the influence coefficients — they do not depend on c.
    """
    p = _ej1_project()
    for m in p.materials:
        m.strength.params["friction_angle"] = 0.0
        m.strength.params["cohesion"] *= 5.0
    return p


def _cohesion_vars(project, cov=0.25):
    out = []
    for mat in project.materials:
        v = [x for x in available_variables(project)
             if x.param == "cohesion" and x.target_id == mat.id][0]
        c = mat.strength.params["cohesion"]
        v.distribution = Distribution(DT.NORMAL, mean=c, std_dev=cov * c,
                                      rel_min=3 * cov * c,
                                      rel_max=3 * cov * c)
        out.append(v)
    return out


def _surface():
    return SlipCircle(centre_x=_CIRCLE[0], centre_y=_CIRCLE[1],
                      radius=_CIRCLE[2])


def _fos(project, variables, sample):
    clone = clone_project(project)
    apply_sample(clone, variables, sample)
    search = GridSearch(
        method=build_method(project, "bishop_simplified", _SLICES),
        num_slices=_SLICES, min_area=0.0)
    r = search.evaluate_circle(clone, _surface())
    return None if r is None or not r.is_valid else r.fos


def _influence(project, variables):
    """dF/dc_i by finite difference. Exact, because F is linear in c."""
    base = {v.key: v.distribution.mean for v in variables}
    f0 = _fos(project, variables, base)
    return f0, [_fos(project, variables,
                     {**base, v.key: v.distribution.mean + 1.0}) - f0
                for v in variables]


def _sample_covariance(samples, keys):
    n = len(samples[keys[0]])
    mu = [sum(samples[k]) / n for k in keys]
    return [[sum((samples[ki][t] - mu[i]) * (samples[kj][t] - mu[j])
                 for t in range(n)) / (n - 1)
             for j, kj in enumerate(keys)] for i, ki in enumerate(keys)]


class _Critical:
    """The deterministic result the engine expects: a surface and its
    factor. Only the surface is read back."""

    def __init__(self, surface):
        self.surface = surface
        self.fos = float("nan")


def _run(project, variables, sampling, seed, n=200):
    return run_global_minimum(
        project, {"bishop_simplified": _Critical(_surface())}, variables,
        num_samples=n, sampling=sampling, seed=seed, num_slices=_SLICES)


def _identity_error(project, variables, sampling, seed, n=200):
    res = _run(project, variables, sampling, seed, n)
    mres = res.by_method["bishop_simplified"]
    assert mres.failed_samples == 0
    _, a = _influence(project, variables)
    keys = [v.key for v in variables]
    cov = _sample_covariance(res.samples, keys)
    predicted = sum(a[i] * cov[i][j] * a[j]
                    for i in range(len(a)) for j in range(len(a)))
    return abs(mres.statistics.std_dev ** 2 / predicted - 1.0)


class TestVariancePropagation:
    def test_factor_is_exactly_linear_in_cohesion(self):
        """The licence for the identity below. Without friction the
        factor is a linear form, so a step of 2 must move it exactly
        twice what a step of 1 moves it."""
        p = _phi_zero_project()
        vs = _cohesion_vars(p)
        base = {v.key: v.distribution.mean for v in vs}
        f0 = _fos(p, vs, base)
        for v in vs:
            f1 = _fos(p, vs, {**base, v.key: v.distribution.mean + 1.0})
            f2 = _fos(p, vs, {**base, v.key: v.distribution.mean + 2.0})
            assert abs((f2 - f0) - 2.0 * (f1 - f0)) < 1e-12

    def test_every_material_moves_the_factor(self):
        """Guards the surface itself: if it ever stops cutting all three
        layers the identity still passes, but stops testing the
        off-diagonal terms it was chosen for."""
        p = _phi_zero_project()
        f0, a = _influence(p, _cohesion_vars(p))
        assert 0.5 < f0 < 1.5
        assert min(a) > 0.0
        assert min(a) / max(a) > 0.5

    def test_sampled_variance_equals_analytic_propagation(self):
        p = _phi_zero_project()
        assert _identity_error(p, _cohesion_vars(p), SM.MONTE_CARLO, 7) < 1e-9

    def test_identity_holds_under_latin_hypercube(self):
        p = _phi_zero_project()
        assert _identity_error(p, _cohesion_vars(p),
                               SM.LATIN_HYPERCUBE, 11) < 1e-9

    def test_identity_holds_with_a_declared_correlation(self):
        """The identity is about the REALISED covariance, not about an
        assumption of independence: rank-reordering two variables must
        move sigma exactly as the sample covariance says it should."""
        p = _phi_zero_project()
        vs = _cohesion_vars(p)
        vs[1].correlated_with = vs[0].key
        vs[1].correlation = 0.7
        assert _identity_error(p, vs, SM.MONTE_CARLO, 13) < 1e-9

    def test_a_declared_correlation_widens_the_factor(self):
        """And it must actually move the number — a correlation that
        changed no dispersion would be a setting that does nothing."""
        p = _phi_zero_project()
        plain = _run(p, _cohesion_vars(p), SM.MONTE_CARLO, 13)
        vs = _cohesion_vars(p)
        vs[1].correlated_with = vs[0].key
        vs[1].correlation = 0.7
        tied = _run(p, vs, SM.MONTE_CARLO, 13)
        assert (tied.by_method["bishop_simplified"].statistics.std_dev
                > 1.05
                * plain.by_method["bishop_simplified"].statistics.std_dev)
