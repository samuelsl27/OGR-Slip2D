# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Statistical distributions and samplers — Phase P0 of the probabilistic
plan.

Provides the seven distributions of the reference specification (Normal,
Uniform, Triangular, Beta, Exponential, Lognormal, Gamma) plus the two
sampling methods (Monte Carlo and Latin Hypercube).

Relative minimum / maximum
--------------------------
A subtle but important point of the reference: the minimum and maximum a
user enters for a random variable are **relative** values, i.e. distances
measured from the mean, so the variable is truncated to

    [ mean - relative_min ,  mean + relative_max ]

This is how an engineer naturally states uncertainty ("the cohesion is
5 kPa, give or take 2") and it also guarantees the sampled values stay
physically sensible — a negative friction angle, for instance, can never
be generated.

Truncation is applied by **inverse-CDF mapping**, not by rejection:

    u' = F(lo) + u · [ F(hi) - F(lo) ]      x = F⁻¹(u')

Rejection sampling would break the Latin Hypercube stratification (some
strata would lose their sample), whereas remapping the uniform variate
preserves it exactly.

Latin Hypercube
---------------
The unit interval is divided into N equal strata, one uniform variate is
drawn inside each, and the resulting set is shuffled independently for
every variable. This "stratified sampling with random selection within
each stratum" reproduces the input distribution far more smoothly than
plain Monte Carlo for the same N.

SciPy is used for the distributions whose inverse CDF has no closed form
(Normal, Beta, Gamma, Lognormal); it is already a core dependency of the
suite. Uniform, Triangular and Exponential are implemented analytically
and therefore work with no dependency at all.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    from scipy import stats as _st
except ImportError:  # pragma: no cover
    _st = None

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None


class DistributionType(Enum):
    NONE = "none"
    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    BETA = "beta"
    EXPONENTIAL = "exponential"
    LOGNORMAL = "lognormal"
    GAMMA = "gamma"


class SamplingMethod(Enum):
    MONTE_CARLO = "monte_carlo"
    LATIN_HYPERCUBE = "latin_hypercube"


# ======================================================================
@dataclass
class Distribution:
    """A statistical distribution for one random variable.

    Attributes:
        dist_type: which distribution.
        mean: the deterministic (mean) value of the parameter.
        std_dev: standard deviation, where the distribution uses one.
        rel_min: how far BELOW the mean the variable may go.
        rel_max: how far ABOVE the mean the variable may go.
    """

    dist_type: DistributionType = DistributionType.NORMAL
    mean: float = 0.0
    std_dev: float = 0.0
    rel_min: float = 0.0
    rel_max: float = 0.0

    # ------------------------------------------------------------------
    @property
    def low(self) -> float:
        return self.mean - abs(self.rel_min)

    @property
    def high(self) -> float:
        return self.mean + abs(self.rel_max)

    @property
    def is_random(self) -> bool:
        """False when the variable is effectively deterministic."""
        if self.dist_type == DistributionType.NONE:
            return False
        if self.high - self.low <= 1e-15:
            return False
        if (self.dist_type in (DistributionType.NORMAL,
                              DistributionType.LOGNORMAL)
                and self.std_dev <= 0):
            return False
        return True

    # ------------------------------------------------------------------
    def _frozen(self):
        """The underlying (untruncated) SciPy distribution, or None for
        the analytically-implemented ones."""
        t = self.dist_type
        if t == DistributionType.NORMAL:
            if _st is None:
                return None
            return _st.norm(loc=self.mean, scale=max(self.std_dev, 1e-12))
        if t == DistributionType.LOGNORMAL:
            if _st is None:
                return None
            # Parameterised by the mean and standard deviation of the
            # VARIABLE (not of its logarithm), which is what a user
            # enters; converted to the underlying normal parameters.
            m = max(self.mean, 1e-12)
            s = max(self.std_dev, 1e-12)
            sigma2 = math.log(1.0 + (s * s) / (m * m))
            sigma = math.sqrt(sigma2)
            mu = math.log(m) - 0.5 * sigma2
            return _st.lognorm(s=sigma, scale=math.exp(mu))
        if t == DistributionType.BETA:
            if _st is None:
                return None
            lo, hi = self.low, self.high
            span = max(hi - lo, 1e-12)
            # Method of moments on the standardised variable
            m = min(max((self.mean - lo) / span, 1e-6), 1.0 - 1e-6)
            v = (max(self.std_dev, 1e-12) / span) ** 2
            v = min(v, m * (1.0 - m) * 0.999)
            k = m * (1.0 - m) / v - 1.0
            a = max(m * k, 1e-3)
            b = max((1.0 - m) * k, 1e-3)
            return _st.beta(a, b, loc=lo, scale=span)
        if t == DistributionType.GAMMA:
            if _st is None:
                return None
            m = max(self.mean, 1e-12)
            s = max(self.std_dev, 1e-12)
            theta = (s * s) / m          # scale
            k = m / max(theta, 1e-12)    # shape
            return _st.gamma(a=max(k, 1e-3), scale=max(theta, 1e-12))
        return None

    # ------------------------------------------------------------------
    def cdf(self, x: float) -> float:
        t = self.dist_type
        if t == DistributionType.UNIFORM:
            lo, hi = self.low, self.high
            if hi <= lo:
                return 1.0
            return min(1.0, max(0.0, (x - lo) / (hi - lo)))
        if t == DistributionType.TRIANGULAR:
            lo, hi, c = self.low, self.high, self.mean
            if hi <= lo:
                return 1.0
            if x <= lo:
                return 0.0
            if x >= hi:
                return 1.0
            if x < c:
                return (x - lo) ** 2 / ((hi - lo) * (c - lo)) \
                    if c > lo else 0.0
            if c < hi:
                return 1.0 - (hi - x) ** 2 / ((hi - lo) * (hi - c))
            return 1.0
        if t == DistributionType.EXPONENTIAL:
            lam = 1.0 / max(self.mean, 1e-12)
            return 1.0 - math.exp(-lam * max(x, 0.0))
        frozen = self._frozen()
        if frozen is None:
            return 0.5
        return float(frozen.cdf(x))

    def ppf(self, u: float) -> float:
        """Inverse CDF of the UNTRUNCATED distribution."""
        u = min(max(u, 1e-12), 1.0 - 1e-12)
        t = self.dist_type
        if t == DistributionType.UNIFORM:
            return self.low + u * (self.high - self.low)
        if t == DistributionType.TRIANGULAR:
            lo, hi, c = self.low, self.high, self.mean
            if hi <= lo:
                return lo
            c = min(max(c, lo), hi)
            f_c = (c - lo) / (hi - lo)
            if u < f_c:
                return lo + math.sqrt(u * (hi - lo) * (c - lo))
            return hi - math.sqrt((1.0 - u) * (hi - lo) * (hi - c))
        if t == DistributionType.EXPONENTIAL:
            lam = 1.0 / max(self.mean, 1e-12)
            return -math.log(1.0 - u) / lam
        frozen = self._frozen()
        if frozen is None:
            return self.mean
        return float(frozen.ppf(u))

    def pdf(self, x: float) -> float:
        t = self.dist_type
        if t == DistributionType.UNIFORM:
            lo, hi = self.low, self.high
            return 1.0 / (hi - lo) if lo <= x <= hi and hi > lo else 0.0
        if t == DistributionType.TRIANGULAR:
            lo, hi, c = self.low, self.high, self.mean
            if not (lo <= x <= hi) or hi <= lo:
                return 0.0
            if x < c:
                return 2.0 * (x - lo) / ((hi - lo) * (c - lo)) \
                    if c > lo else 0.0
            if c < hi:
                return 2.0 * (hi - x) / ((hi - lo) * (hi - c))
            return 0.0
        if t == DistributionType.EXPONENTIAL:
            lam = 1.0 / max(self.mean, 1e-12)
            return lam * math.exp(-lam * x) if x >= 0 else 0.0
        frozen = self._frozen()
        if frozen is None:
            return 0.0
        return float(frozen.pdf(x))

    # ------------------------------------------------------------------
    def value_from_uniform(self, u: float) -> float:
        """Map a uniform variate in [0, 1) to a truncated sample.

        Uses inverse-CDF remapping rather than rejection so that Latin
        Hypercube stratification survives the truncation.
        """
        if not self.is_random:
            return self.mean
        lo, hi = self.low, self.high
        c_lo = self.cdf(lo)
        c_hi = self.cdf(hi)
        if c_hi - c_lo < 1e-12:
            return self.mean
        x = self.ppf(c_lo + u * (c_hi - c_lo))
        return min(max(x, lo), hi)

    def values_from_uniforms(self, us) -> list:
        """Vectorised version of :meth:`value_from_uniform`.

        A probabilistic run needs thousands of samples per variable, and
        calling SciPy's scalar ``ppf`` once per sample dominates the cost
        (it is roughly two orders of magnitude slower than a single
        array call). This maps the whole batch at once when NumPy and
        SciPy are available, and falls back to the scalar path otherwise.
        """
        if not self.is_random:
            return [self.mean] * len(us)
        lo, hi = self.low, self.high
        c_lo, c_hi = self.cdf(lo), self.cdf(hi)
        if c_hi - c_lo < 1e-12:
            return [self.mean] * len(us)
        frozen = self._frozen()
        if frozen is not None and _np is not None:
            arr = _np.asarray(us, dtype=float)
            xs = frozen.ppf(c_lo + arr * (c_hi - c_lo))
            xs = _np.clip(xs, lo, hi)
            return [float(v) for v in xs]
        return [self.value_from_uniform(u) for u in us]

    def sample(self, rng: Optional[random.Random] = None) -> float:
        rng = rng or random
        return self.value_from_uniform(rng.random())

    def curve(self, n: int = 100) -> list:
        """(x, pdf) samples across the truncated range, for plotting."""
        lo, hi = self.low, self.high
        if hi <= lo:
            return [(self.mean, 1.0)]
        return [(lo + (hi - lo) * i / (n - 1),
                 self.pdf(lo + (hi - lo) * i / (n - 1))) for i in range(n)]

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"dist_type": self.dist_type.value, "mean": self.mean,
                "std_dev": self.std_dev, "rel_min": self.rel_min,
                "rel_max": self.rel_max}

    @classmethod
    def from_dict(cls, d: dict) -> "Distribution":
        return cls(
            dist_type=DistributionType(d.get("dist_type", "normal")),
            mean=float(d.get("mean", 0.0)),
            std_dev=float(d.get("std_dev", 0.0)),
            rel_min=float(d.get("rel_min", 0.0)),
            rel_max=float(d.get("rel_max", 0.0)),
        )


# ======================================================================
def uniform_samples(n: int, method: SamplingMethod,
                    rng: Optional[random.Random] = None) -> list:
    """``n`` uniform variates in [0, 1) by the requested method.

    Monte Carlo draws them independently. Latin Hypercube divides the
    interval into ``n`` strata, draws one variate inside each and
    shuffles the result.
    """
    rng = rng or random.Random()
    n = max(1, int(n))
    if method == SamplingMethod.LATIN_HYPERCUBE:
        out = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(out)
        return out
    return [rng.random() for _ in range(n)]


def sample_variables(distributions: dict, n: int,
                     method: SamplingMethod = SamplingMethod.MONTE_CARLO,
                     seed: Optional[int] = None,
                     correlate: bool = False) -> dict:
    """Generate ``n`` samples for each distribution.

    ``distributions`` maps a key to a :class:`Distribution`; the result
    maps the same keys to lists of ``n`` sampled values. Each variable
    gets its OWN shuffled stratification, which is what makes the Latin
    Hypercube samples independent across variables.

    v0.1.74 — ``correlate`` keeps the stratification IDENTICAL across
    variables instead: sample *i* then sits in the same stratum of every
    variable, so they move together. The reference exposes this as a
    separate switch on its Random Numbers page because it is a modelling
    choice, not a sampling detail — correlated strata answer "what if
    everything is simultaneously unfavourable", which is a different
    question from the independent case and gives a different, usually
    wider, spread of factors of safety.

    It has no meaning for Monte Carlo, which has no strata to share, and
    is ignored there.
    """
    rng = random.Random(seed)
    out: dict = {}
    shared = None
    if correlate and method == SamplingMethod.LATIN_HYPERCUBE:
        shared = uniform_samples(n, method, rng)
    for key, dist in distributions.items():
        us = shared if shared is not None else uniform_samples(n, method, rng)
        out[key] = dist.values_from_uniforms(us)
    return out


# ----------------------------------------------------------------------
def _inv_norm(u: float) -> float:
    """Standard normal inverse CDF (Acklam's rational approximation),
    kept dependency-free so rank correlation works without SciPy."""
    if _st is not None:
        return float(_st.norm.ppf(min(max(u, 1e-12), 1.0 - 1e-12)))
    u = min(max(u, 1e-12), 1.0 - 1e-12)
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if u < p_low:
        q = math.sqrt(-2 * math.log(u))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if u > p_high:
        q = math.sqrt(-2 * math.log(1 - u))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = u - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
        (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ======================================================================
def correlate_pair(values_a: list, values_b: list, rho: float) -> list:
    """Impose a correlation coefficient between two sampled series.

    Used for the cohesion / friction-angle correlation the reference
    offers for Mohr-Coulomb materials, where a negative coefficient is
    the physically usual case (higher cohesion tends to accompany a lower
    friction angle).

    Implemented by rank reordering: ``values_b`` is permuted so that its
    rank order matches a target built from the ranks of ``values_a``.
    This is the standard Iman-Conover idea, and it preserves each
    variable's marginal distribution exactly — only the pairing changes.
    """
    n = len(values_a)
    if n < 2 or len(values_b) != n or abs(rho) < 1e-12:
        return list(values_b)
    rho = max(-1.0, min(1.0, rho))
    rng = random.Random(12345)

    # Van der Waerden normal scores of the ranks of A. Working in normal
    # score space is what makes the achieved coefficient match the
    # requested one; a linear rank mapping overshoots by roughly 10 %.
    ranks_a = sorted(range(n), key=lambda i: values_a[i])
    z_a = [0.0] * n
    for pos, idx in enumerate(ranks_a):
        u = (pos + 0.5) / n
        z_a[idx] = _inv_norm(u)

    # Target scores correlated with z_a at exactly rho
    k = math.sqrt(max(0.0, 1.0 - rho * rho))
    target = [rho * z_a[i] + k * rng.gauss(0.0, 1.0) for i in range(n)]

    order_target = sorted(range(n), key=lambda i: target[i])
    sorted_b = sorted(values_b)
    out = [0.0] * n
    for pos, idx in enumerate(order_target):
        out[idx] = sorted_b[pos]
    return out


# ======================================================================
@dataclass
class SampleStatistics:
    """Summary statistics of a set of computed factors of safety."""

    values: list = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return sum(self.values) / self.n if self.n else float("nan")

    @property
    def std_dev(self) -> float:
        if self.n < 2:
            return 0.0
        m = self.mean
        return math.sqrt(sum((v - m) ** 2 for v in self.values)
                         / (self.n - 1))

    @property
    def minimum(self) -> float:
        return min(self.values) if self.values else float("nan")

    @property
    def maximum(self) -> float:
        return max(self.values) if self.values else float("nan")

    def probability_of_failure(self, threshold: float = 1.0) -> float:
        """PF = fraction of samples with a factor of safety below 1."""
        if not self.n:
            return float("nan")
        return sum(1 for v in self.values if v < threshold) / self.n

    def reliability_index(self, threshold: float = 1.0) -> float:
        """Normal reliability index beta = (mean - 1) / std_dev.

        The number of standard deviations separating the mean factor of
        safety from failure. Undefined when the samples show no scatter.
        """
        s = self.std_dev
        if s <= 0:
            return float("inf") if self.mean >= threshold else float("-inf")
        return (self.mean - threshold) / s

    def lognormal_reliability_index(self, threshold: float = 1.0) -> float:
        """Reliability index assuming the factors of safety are
        lognormally distributed, which is often the better fit because a
        factor of safety cannot be negative."""
        vals = [v for v in self.values if v > 0]
        if len(vals) < 2:
            return float("nan")
        logs = [math.log(v) for v in vals]
        m = sum(logs) / len(logs)
        s = math.sqrt(sum((x - m) ** 2 for x in logs) / (len(logs) - 1))
        if s <= 0:
            return float("inf") if m >= math.log(threshold) else float("-inf")
        return (m - math.log(threshold)) / s

    def histogram(self, bins: int = 20) -> list:
        """(centre, count) pairs for plotting."""
        if not self.values:
            return []
        lo, hi = self.minimum, self.maximum
        if hi - lo < 1e-15:
            return [(lo, self.n)]
        width = (hi - lo) / bins
        counts = [0] * bins
        for v in self.values:
            k = min(bins - 1, int((v - lo) / width))
            counts[k] += 1
        return [(lo + width * (i + 0.5), counts[i]) for i in range(bins)]

    def convergence(self, steps: int = 50) -> list:
        """(n, mean, PF) as the sample count grows — the data behind the
        reference's Samples Convergence Plot, which tells the user how
        many samples are actually needed."""
        if not self.values:
            return []
        out = []
        stride = max(1, self.n // steps)
        run_sum = 0.0
        run_fail = 0
        for i, v in enumerate(self.values, start=1):
            run_sum += v
            if v < 1.0:
                run_fail += 1
            if i % stride == 0 or i == self.n:
                out.append((i, run_sum / i, run_fail / i))
        return out
