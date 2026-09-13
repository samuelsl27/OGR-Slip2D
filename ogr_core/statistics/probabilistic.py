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
    unwritable_variables,
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
#: The serialised surface types a statistical loop knows how to seed, and
#: what each one is seeded FROM. ENUMERATED, never sniffed from the shape
#: of the dictionary: dispatching on the shape IS defect D59.
#: ``CompositeSurface.to_dict`` carries ``radius``, so ``"radius" in
#: surface_dict`` read a composite as a circle; and
#: ``WeakLayerSurface.to_dict`` carries neither ``radius`` nor
#: ``polyline``, so it fell through to ``SlipSurface.from_dict`` and
#: raised ``KeyError('polyline')`` from OUTSIDE the sample loop, taking
#: every method and both analyses down with it.
_CIRCLE_SEEDED = ("circle", "composite")
_POLYLINE_SEEDED = ("polyline",)


def _surface_type(surface_dict) -> Optional[str]:
    """The serialised type, with the ONE fallback this module still owes.

    ``run_global_minimum`` accepts a bare dictionary as ``det.surface``
    (the ``else det.surface`` branch of its own loop), and such a
    dictionary need not carry a ``type`` at all. A centre and a radius
    without a type therefore still name a circle — deliberately, and not
    as a leftover of the shape-sniffing this module just stopped doing:
    dropping it would break that contract as a side effect rather than as
    a decision.
    """
    if not isinstance(surface_dict, dict) or not surface_dict:
        return None
    stype = surface_dict.get("type")
    if stype is None and "radius" in surface_dict:
        return "circle"
    return stype


def _rebuild_surface(surface_dict: dict):
    """The SEED of the surface every sample re-evaluates.

    What comes out is the seed of the deterministic surface, not a copy of
    it: a circle WITHOUT endpoints, so that each sample resolves its own
    sliding mass, applies its own reverse curvature and its own tension
    crack and — with Composite Surfaces enabled — clips itself against the
    floor of the model again. That is the mechanism v0.1.131 (D36) put
    here, and the one ``CompositeSurface.to_dict`` names in its own
    docstring: "re-clipping the same circle against the same model gives
    the same composite, which is what the probabilistic sampler relies
    on". Measured over the four composite models of the verification bank
    and seven method-model pairs, the re-clipped surface is the
    deterministic one to all seventeen digits.

    A composite is therefore seeded FROM ITS CIRCLE on purpose, and not
    for want of a ``CompositeSurface.from_dict``. Rebuilding the object
    from the dictionary was measured and is WORSE: the dictionary does not
    carry ``tension_crack_wall``, and endpoints that arrive already
    truncated skip the truncation that would deduce it again, so a model
    with a filled tension crack loses its water thrust — +0.35 % on the
    UNSAFE side on the composite model of verification problem 57, where
    re-clipping is exact.

    Returns ``None`` for a serialised surface this loop cannot seed, so
    the caller can say so and carry on with the other methods.
    """
    from ogr_slip2d.surface import SlipCircle, SlipSurface

    stype = _surface_type(surface_dict)
    if stype in _CIRCLE_SEEDED:
        return SlipCircle(
            centre_x=float(surface_dict["centre_x"]),
            centre_y=float(surface_dict["centre_y"]),
            radius=float(surface_dict["radius"]),
        )
    if stype in _POLYLINE_SEEDED:
        return SlipSurface.from_dict(surface_dict)
    return None


def _evaluate_on(project, search, surface):
    """Evaluate a known surface on a (possibly modified) project."""
    from ogr_slip2d.surface import SlipCircle

    if isinstance(surface, SlipCircle):
        return search.evaluate_circle(project, surface)
    return search.evaluate_surface(project, surface)


def _composite_surfaces(project) -> bool:
    """Composite Surfaces, as the project the SAMPLES run on carries it.

    Read exactly as ``BaseSearch._candidate_surfaces`` reads it, missing
    attribute included, so the two cannot disagree about what the option
    says.
    """
    try:
        return bool(project.settings.search.composite_surfaces)
    except AttributeError:
        return False


def _cannot_reevaluate(project, surface_dict) -> Optional[str]:
    """Why the samples cannot be re-evaluated on this deterministic
    surface, or ``None`` when they can.

    Two refusals, and this docstring states what they cover and nothing
    more. They do NOT promise that every sample answers for the
    deterministic mechanism: with Composite Surfaces on in both runs, a
    sample whose strength falls far enough answers for a DIFFERENT sliding
    mass of the same circle, because ``_best_of_masses`` keeps the lowest
    factor and v0.1.131 (D36) dropped the endpoints on purpose. Measured
    on a two-mass model, a probability of failure of 0.25 was made up
    entirely of samples belonging to the other mass. That is a defect of
    its own and it is reported, not covered here — a guard whose stated
    reason is wider than what it checks is exactly what cost this project
    two versions over m-alpha (v0.1.82-84).

    THE TYPE, because ``_rebuild_surface`` seeds from a circle or from a
    polyline and from nothing else. Until v0.1.154 a surface it could not
    seed reached ``SlipSurface.from_dict`` and raised from outside the
    sample loop: the user lost every method and both analyses at once, and
    the interface printed nothing at all.

    COMPOSITE SURFACES, because a composite is seeded from its circle and
    that circle only becomes composite again while the project the samples
    run on keeps the option on. With it off, the same circle is either
    refused whole by the containment rule — the reference's error -103,
    and then N samples of N are lost under a warning that blames the
    variable ranges, which are innocent — or, when the circle defines more
    than one sliding mass, the OTHER mass answers silently: measured
    +142.97 % on a single evaluation, with no failed sample and no note of
    any kind. Refusing is what v0.1.131 (D36) implies rather than a new
    rule: a surface answers for the project it is asked about, so a
    project that would not produce this surface cannot be handed its
    number.
    """
    if not isinstance(surface_dict, dict) or not surface_dict:
        return ("The deterministic result carries no serialised surface, "
                "so there is nothing to re-evaluate.")
    stype = _surface_type(surface_dict)
    if stype not in _CIRCLE_SEEDED + _POLYLINE_SEEDED:
        return (f"The deterministic critical surface is of type "
                f"'{stype}', which a statistical run cannot re-evaluate; "
                f"this method was skipped.")
    if stype == "composite" and not _composite_surfaces(project):
        return ("The deterministic critical surface is a composite one, "
                "and Composite Surfaces is off in the project the samples "
                "run on, so that surface cannot be formed again; this "
                "method was skipped.")
    return None


# ======================================================================
def _stale_variables_stop(result, project, active, first, applied) -> bool:
    """Record the variables that no longer match the model, and say whether
    the run has to stop before sampling.

    v0.1.164 (D91) — ``apply_sample`` has always returned how many
    parameters it wrote, its docstring says it exists "so the caller can
    detect a definition that no longer matches the model", and both callers
    threw the number away. Measured on problem 12, sampling the cohesion of
    the material the published circle actually crosses: with the target
    intact, mean 0.996063021 / std_dev 0.190636922 / PF 0.450 / beta
    -0.020651714 over 20 distinct values; with a ``target_id`` that no
    longer matches, mean 1.017489184 / std_dev 0.0 / PF 0.0 / beta inf over
    ONE value repeated 20 times — with ``ok`` true and an empty ``notes``.
    A perfectly credible result over a sampling that sampled nothing.

    The count is the TRIGGER and never the verdict. It also falls short
    when two variables share a ``key``, because the sampling dictionary
    collapses them into one column; so what decides is the list
    ``unwritable_variables`` measures, and an empty list says nothing at
    all rather than blaming an orphan that is not there.
    """
    if applied >= len(active):
        return False
    orphans = unwritable_variables(project, active, first)
    if not orphans:
        return False
    if len(orphans) == len(active):
        result.notes["error"] = (
            "none of the %d random variables matches the model: %s"
            % (len(active), ", ".join(orphans)))
        return True
    # Partial: the ones that DO write still carry a meaningful sampling, so
    # the run goes on. What it may not do is go on quietly.
    result.notes["warning"] = (
        "%d of the %d random variables no longer match the model and were "
        "not sampled: %s" % (len(orphans), len(active), ", ".join(orphans)))
    return False


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
        method_factory: ``method_id -> LEMMethod``; defaults to
            ``analysis_runner.build_method``, which is the one place that
            configures a method from the project (v0.1.108).
        progress_cb: called as ``(done, total)``.

    Returns:
        A :class:`ProbabilisticResult`, empty when no variable is random.
    """
    from ogr_slip2d.analysis_runner import build_method
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
    samples = sample_project_variables(
        active, num_samples, sampling, seed,
        # v0.1.74 — the Latin Hypercube stratification switch from
        # the Random Numbers page. Read off the project so both
        # analysis types get it without a second argument to
        # thread through every caller.
        correlate=bool(project.settings.random_numbers.lhs_correlate))
    result.samples = samples

    # v0.1.164 (D91) — the count ``apply_sample`` has always returned, read
    # at last. ONCE per run and on a throwaway clone: a definition that no
    # longer matches is a property of the project and the variables, not of
    # the method, so asking inside the per-method loop would repeat the same
    # answer; and returning from HERE provably leaves ``by_method`` empty,
    # which is what makes ``ok`` false -- there is no ``ok`` to assign.
    probe = clone_project(project)
    first = {k: v[0] for k, v in samples.items() if v}
    applied = apply_sample(probe, active, first)
    if _stale_variables_stop(result, project, active, first, applied):
        return result

    def _make_method(mid):
        """The method as the PROJECT configures it, not as the registry
        hands it over.

        v0.1.108 — this used to fall back to ``registry[mid]()``, a bare
        instance, and no caller in the program ever passed a
        ``method_factory``: not the interface, not the CLI, not the bank
        scripts. So a statistical run of a rapid-drawdown model computed
        the ordinary DRAINED factor of safety on every sample, silently
        (anomaly A98-1 by a third route), and it also dropped the
        convergence settings the user configured — the same fault v0.1.74
        closed for the searches, still open here.
        """
        if method_factory is not None:
            return method_factory(mid)
        return build_method(project, mid, num_slices)

    total = num_samples * max(1, len(critical_surfaces))
    done = 0

    for mid, det in critical_surfaces.items():
        method = _make_method(mid)
        if method is None or det is None:
            continue
        # ONE serialisation per method: the one the refusal reads, the one
        # the seed is built from and the one that travels in the result.
        # Reading the same surface three times could disagree.
        sd = (det.surface.to_dict() if hasattr(det.surface, "to_dict")
              else det.surface)
        refusal = _cannot_reevaluate(project, sd)
        if refusal is not None:
            # v0.1.154 (D59) — said out loud, and per method, because what
            # was measured without it are two worse things: a run that
            # loses every sample and blames the variable ranges for it,
            # and a run that answers for another sliding mass without a
            # word.
            result.notes[mid] = refusal
            continue
        surface = _rebuild_surface(sd)
        if surface is None:
            continue
        search = GridSearch(method=method, num_slices=num_slices,
                            min_area=0.0)

        mres = MethodProbabilisticResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan),
            surface=sd if isinstance(sd, dict) else None,
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

    # v0.1.154 — if no method survived, the reason rises to the key the
    # interface actually prints: ``_compute_statistics`` looks only at
    # ``notes['error']``, and only when the run comes back empty.
    if not result.by_method and "error" not in result.notes and result.notes:
        result.notes["error"] = "; ".join(
            str(v) for v in result.notes.values())

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

    WHAT THIS KEY DOES NOT SEPARATE, said here because the accumulated
    statistics are only as honest as the identity they are accumulated
    under: a circle is keyed by centre and radius alone, so the two
    DISJOINT sliding masses of one circle share a key, and so do a
    composite and the uncut circle it was clipped from. Reported as a
    defect of its own rather than fixed here — putting the extent in the
    key would regroup the samples of every circular model.
    """
    stype = _surface_type(sd)
    if stype is None:
        return ""
    if stype in _CIRCLE_SEEDED:
        return "c:%d:%d:%d" % (round(sd["centre_x"] / tol),
                               round(sd["centre_y"] / tol),
                               round(sd["radius"] / tol))
    # Every serialised surface that is not keyed by its circle is keyed by
    # its vertices, and they are PAIRS: ``Polyline.to_dict`` writes
    # ``[x, y]`` and always has. Reading ``v["x"]`` off a list raised
    # ``TypeError`` on the first valid evaluation of any non-circular
    # search — Block, Path, Auto Refine — or of any optimised surface, and
    # this loop sits outside the ``try`` in ``run_overall_slope``, so the
    # public entry point died. Same root cause as D59: dispatching on the
    # shape of the dictionary instead of on its ``type``.
    if stype in _POLYLINE_SEEDED:
        verts = (sd.get("polyline") or {}).get("vertices") or []
    else:
        # ``composite`` and ``weak_layer`` publish their drawn vertices at
        # the root. Until now they all collapsed onto the empty key "p:",
        # which merged surfaces that are not the same surface.
        verts = sd.get("vertices") or []
    if not verts:
        # No key rather than the bare "p:" every vertexless surface used
        # to share: the caller skips an empty key, and skipping one
        # surface is better than merging it with all the others.
        return ""
    return "p:" + ":".join(
        "%d,%d" % (round(v[0] / tol), round(v[1] / tol))
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
    samples = sample_project_variables(
        active, num_samples, sampling, seed,
        # v0.1.74 — the Latin Hypercube stratification switch from
        # the Random Numbers page. Read off the project so both
        # analysis types get it without a second argument to
        # thread through every caller.
        correlate=bool(project.settings.random_numbers.lhs_correlate))
    result.samples = samples

    # v0.1.164 (D91) — the count ``apply_sample`` has always returned, read
    # at last. ONCE per run and on a throwaway clone: a definition that no
    # longer matches is a property of the project and the variables, not of
    # the method, so asking inside the per-method loop would repeat the same
    # answer; and returning from HERE provably leaves ``by_method`` empty,
    # which is what makes ``ok`` false -- there is no ``ok`` to assign.
    probe = clone_project(project)
    first = {k: v[0] for k, v in samples.items() if v}
    applied = apply_sample(probe, active, first)
    if _stale_variables_stop(result, project, active, first, applied):
        return result

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
