# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Probabilistic analysis engine — Phase P2 of the probabilistic plan.

Implements the **Global Minimum** analysis type of the reference:

1. A regular DETERMINISTIC analysis is run first, to locate the slip
   surface with the overall (global minimum) factor of safety.
2. The probabilistic analysis is then carried out **on that surface**,
   repeating the stability calculation N times with the samples drawn for
   each random variable.
3. The Probability of Failure is the number of samples giving a factor of
   safety below 1, divided by N.

A point the reference stresses and that this implementation honours:
**each analysis method can produce a different global minimum**, so the
probabilistic run is carried out independently on the critical surface of
every method requested.

Every sample is evaluated on a **clone** of the project (Phase P1), so
the user's model is never modified.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from .distributions import SampleStatistics, SamplingMethod
from .random_variables import (
    apply_sample,
    clone_project,
    sample_project_variables,
)


class ProbabilisticType:
    GLOBAL_MINIMUM = "global_minimum"
    OVERALL_SLOPE = "overall_slope"


@dataclass
class MethodProbabilisticResult:
    """Probabilistic outcome for one analysis method."""

    method_id: str = ""
    deterministic_fos: float = math.nan
    surface: Optional[dict] = None          # surface.to_dict()
    statistics: SampleStatistics = field(default_factory=SampleStatistics)
    failed_samples: int = 0                 # samples that could not be
    #                                         evaluated at all
    notes: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    @property
    def probability_of_failure(self) -> float:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> float:
        return self.statistics.reliability_index()

    @property
    def mean_fos(self) -> float:
        return self.statistics.mean

    def summary(self) -> dict:
        st = self.statistics
        return {
            "method": self.method_id,
            "deterministic_fos": self.deterministic_fos,
            "samples": st.n,
            "mean_fos": st.mean,
            "std_dev": st.std_dev,
            "min_fos": st.minimum,
            "max_fos": st.maximum,
            "pf": st.probability_of_failure(),
            "reliability_index": st.reliability_index(),
            "reliability_index_lognormal":
                st.lognormal_reliability_index(),
            "failed_samples": self.failed_samples,
        }


@dataclass
class ProbabilisticResult:
    """Result of a full probabilistic run (one entry per method)."""

    by_method: dict = field(default_factory=dict)
    num_samples: int = 0
    sampling_method: str = SamplingMethod.MONTE_CARLO.value
    analysis_type: str = ProbabilisticType.GLOBAL_MINIMUM
    variables: list = field(default_factory=list)   # keys, for reporting
    # Sampled values per variable key, kept in the SAME order as the
    # computed factors of safety so a scatter plot is a plain zip.
    samples: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.by_method)

    def summary(self) -> list:
        return [r.summary() for r in self.by_method.values()]


# ======================================================================
def _rebuild_surface(surface_dict: dict):
    """Rebuild a surface object from its serialised form so it can be
    re-evaluated against a modified project."""
    from ogr_slip2d.surface import SlipCircle, SlipSurface

    if not surface_dict:
        return None
    if surface_dict.get("type") == "circle" or "radius" in surface_dict:
        return SlipCircle(
            centre_x=float(surface_dict["centre_x"]),
            centre_y=float(surface_dict["centre_y"]),
            radius=float(surface_dict["radius"]),
        )
    return SlipSurface.from_dict(surface_dict)


def _evaluate_on(project, search, surface):
    """Evaluate a known surface on a (possibly modified) project."""
    from ogr_slip2d.surface import SlipCircle

    if isinstance(surface, SlipCircle):
        return search.evaluate_circle(project, surface)
    return search.evaluate_surface(project, surface)


# ======================================================================
def run_global_minimum(
    project,
    critical_surfaces: dict,
    variables: list,
    num_samples: int = 1000,
    sampling: SamplingMethod = SamplingMethod.LATIN_HYPERCUBE,
    seed: Optional[int] = None,
    num_slices: int = 25,
    method_factory: Optional[Callable] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> ProbabilisticResult:
    """Run a Global Minimum probabilistic analysis.

    Args:
        project: the deterministic model (never modified).
        critical_surfaces: ``method_id -> LEMResult`` from the
            deterministic run. Each method keeps its OWN critical
            surface, as the reference specifies.
        variables: the :class:`RandomVariable` list.
        num_samples: N.
        sampling: Monte Carlo or Latin Hypercube.
        seed: for reproducibility.
        num_slices: slicing used in the repeated evaluations.
        method_factory: ``method_id -> LEMMethod``; defaults to the
            registry.
        progress_cb: called as ``(done, total)``.

    Returns:
        A :class:`ProbabilisticResult`, empty when no variable is random.
    """
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.search import GridSearch

    result = ProbabilisticResult(
        num_samples=num_samples, sampling_method=sampling.value,
        analysis_type=ProbabilisticType.GLOBAL_MINIMUM)

    active = [rv for rv in variables if rv.distribution.is_random]
    if not active:
        result.notes["error"] = (
            "No random variables defined. At least one model input "
            "parameter must be given a statistical distribution.")
        return result
    if not critical_surfaces:
        result.notes["error"] = (
            "No deterministic result: run the regular analysis first so "
            "the global minimum surface is known.")
        return result

    result.variables = [rv.key for rv in active]
    samples = sample_project_variables(active, num_samples, sampling, seed)
    result.samples = samples

    registry = method_registry()

    def _make_method(mid):
        if method_factory is not None:
            return method_factory(mid)
        cls = registry.get(mid)
        return cls() if cls is not None else None

    total = num_samples * max(1, len(critical_surfaces))
    done = 0

    for mid, det in critical_surfaces.items():
        method = _make_method(mid)
        if method is None or det is None:
            continue
        surface = _rebuild_surface(
            det.surface.to_dict() if hasattr(det.surface, "to_dict")
            else det.surface)
        if surface is None:
            continue
        search = GridSearch(method=method, num_slices=num_slices,
                            min_area=0.0)

        mres = MethodProbabilisticResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan),
            surface=(det.surface.to_dict()
                     if hasattr(det.surface, "to_dict") else None),
        )
        values: list[float] = []
        for i in range(num_samples):
            clone = clone_project(project)
            one = {k: v[i] for k, v in samples.items()}
            apply_sample(clone, active, one)
            try:
                r = _evaluate_on(clone, search, surface)
            except Exception:  # noqa: BLE001
                r = None
            if r is not None and r.is_valid:
                values.append(r.fos)
            else:
                # A sample can make the surface unsolvable (for instance a
                # very low strength). It is counted separately rather than
                # dropped silently, because a large count means the
                # distributions are unrealistic.
                mres.failed_samples += 1
            done += 1
            if progress_cb and done % 25 == 0:
                progress_cb(done, total)

        mres.statistics = SampleStatistics(values=values)
        if mres.failed_samples > 0.2 * num_samples:
            mres.notes["warning"] = (
                f"{mres.failed_samples} of {num_samples} samples could "
                f"not be evaluated; check the variable ranges.")
        result.by_method[mid] = mres

    if progress_cb:
        progress_cb(total, total)
    return result


# ======================================================================
@dataclass
class SurfaceProbability:
    """Probability statistics accumulated for ONE slip surface across the
    samples of an Overall Slope run."""

    surface: Optional[dict] = None
    statistics: SampleStatistics = field(default_factory=SampleStatistics)
    times_global_minimum: int = 0

    @property
    def probability_of_failure(self) -> float:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> float:
        return self.statistics.reliability_index()


@dataclass
class OverallSlopeResult:
    """Outcome of an Overall Slope analysis for one method."""

    method_id: str = ""
    deterministic_fos: float = math.nan
    statistics: SampleStatistics = field(default_factory=SampleStatistics)
    global_minima: list = field(default_factory=list)   # surface dicts
    critical_probabilistic: Optional[SurfaceProbability] = None
    failed_samples: int = 0
    notes: dict = field(default_factory=dict)

    @property
    def probability_of_failure(self) -> float:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> float:
        return self.statistics.reliability_index()

    @property
    def distinct_minima(self) -> int:
        return len(self.global_minima)

    def summary(self) -> dict:
        st = self.statistics
        cp = self.critical_probabilistic
        return {
            "method": self.method_id,
            "deterministic_fos": self.deterministic_fos,
            "samples": st.n,
            "mean_fos": st.mean,
            "std_dev": st.std_dev,
            "min_fos": st.minimum,
            "max_fos": st.maximum,
            "pf": st.probability_of_failure(),
            "reliability_index": st.reliability_index(),
            "distinct_global_minima": self.distinct_minima,
            "critical_probabilistic_pf": (
                cp.probability_of_failure if cp else math.nan),
            "critical_probabilistic_beta": (
                cp.reliability_index if cp else math.nan),
            "failed_samples": self.failed_samples,
        }


def _surface_key(sd: dict, tol: float = 0.5) -> str:
    """Identity of a surface for accumulating statistics across samples.

    Geometry is quantised so that the same candidate generated in two
    different iterations maps to the same key. A grid search regenerates
    an identical set of circles every time, so this groups them exactly;
    for random searches the tolerance merges near-coincident surfaces.
    """
    if not sd:
        return ""
    if "radius" in sd:
        return "c:%d:%d:%d" % (round(sd["centre_x"] / tol),
                               round(sd["centre_y"] / tol),
                               round(sd["radius"] / tol))
    verts = (sd.get("polyline") or {}).get("vertices") or []
    return "p:" + ":".join(
        "%d,%d" % (round(v["x"] / tol), round(v["y"] / tol))
        for v in verts)


def run_overall_slope(
    project,
    search_factory: Callable,
    variables: list,
    method_ids: list,
    num_samples: int = 100,
    sampling: SamplingMethod = SamplingMethod.LATIN_HYPERCUBE,
    seed: Optional[int] = None,
    deterministic: Optional[dict] = None,
    min_evaluations: int = 5,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> ProbabilisticResult:
    """Run an **Overall Slope** probabilistic analysis.

    The ENTIRE SEARCH is repeated ``num_samples`` times, loading a new
    set of random-variable samples each time, so the location of the
    global minimum is NOT assumed fixed — which is the whole point of
    this analysis type, and what distinguishes it from Global Minimum.

    The probability of failure keeps the same definition: the number of
    analyses giving a factor of safety below 1, divided by the number of
    samples.

    In addition, the **critical probabilistic surface** is determined:
    the individual surface with the maximum probability of failure (and
    therefore the minimum reliability index), which as the reference
    stresses *need not be the deterministic critical surface*. Statistics
    are accumulated per surface across the iterations, and only surfaces
    evaluated at least ``min_evaluations`` times are eligible, so a
    surface seen once cannot win on a single unlucky sample.

    ``search_factory`` is a callable ``method_id -> BaseSearch`` that
    builds a fully configured search, so the run honours exactly the same
    search settings as a normal analysis.

    Be aware this is **substantially more expensive** than the Global
    Minimum type: a full search per sample.
    """
    result = ProbabilisticResult(
        num_samples=num_samples, sampling_method=sampling.value,
        analysis_type=ProbabilisticType.OVERALL_SLOPE)

    active = [rv for rv in variables if rv.distribution.is_random]
    if not active:
        result.notes["error"] = (
            "No random variables defined. At least one model input "
            "parameter must be given a statistical distribution.")
        return result
    if not method_ids:
        result.notes["error"] = "No analysis method selected."
        return result

    result.variables = [rv.key for rv in active]
    samples = sample_project_variables(active, num_samples, sampling, seed)
    result.samples = samples

    total = num_samples * len(method_ids)
    done = 0

    for mid in method_ids:
        det = (deterministic or {}).get(mid)
        ores = OverallSlopeResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan))
        per_surface: dict = {}
        minima_keys: set = set()
        values: list[float] = []

        for i in range(num_samples):
            clone = clone_project(project)
            apply_sample(clone, active, {k: v[i] for k, v in
                                         samples.items()})
            try:
                search = search_factory(mid)
                run = search.run(clone)
            except Exception:  # noqa: BLE001
                run = None
            done += 1
            if progress_cb:
                progress_cb(done, total)
            if run is None or run.critical is None:
                ores.failed_samples += 1
                continue

            values.append(run.critical.fos)

            # Accumulate per-surface statistics for the critical
            # probabilistic surface
            for ev in run.evaluations:
                if not ev.is_valid:
                    continue
                sd = (ev.surface.to_dict()
                      if hasattr(ev.surface, "to_dict") else None)
                key = _surface_key(sd)
                if not key:
                    continue
                sp = per_surface.get(key)
                if sp is None:
                    sp = SurfaceProbability(surface=sd)
                    per_surface[key] = sp
                sp.statistics.values.append(ev.fos)

            crit_sd = (run.critical.surface.to_dict()
                       if hasattr(run.critical.surface, "to_dict")
                       else None)
            ckey = _surface_key(crit_sd)
            if ckey:
                if ckey not in minima_keys:
                    minima_keys.add(ckey)
                    ores.global_minima.append(crit_sd)
                if ckey in per_surface:
                    per_surface[ckey].times_global_minimum += 1

        ores.statistics = SampleStatistics(values=values)

        # Critical probabilistic surface: maximum probability of failure,
        # ties broken by the lower reliability index.
        eligible = [sp for sp in per_surface.values()
                    if sp.statistics.n >= min_evaluations]
        if eligible:
            ores.critical_probabilistic = max(
                eligible,
                key=lambda sp: (sp.probability_of_failure,
                                -sp.reliability_index))
        ores.notes["surfaces_tracked"] = len(per_surface)
        if ores.failed_samples:
            ores.notes["warning"] = (
                f"{ores.failed_samples} of {num_samples} searches "
                f"produced no valid surface.")
        result.by_method[mid] = ores

    return result
