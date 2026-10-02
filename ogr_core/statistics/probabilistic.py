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
    #: v0.1.201 — the index, into ``ProbabilisticResult.samples``, of the
    #: sample behind each factor of ``statistics.values``. A failed sample
    #: produces no factor, so without this the two lists stop lining up at
    #: the first failure: the scatter data and the CSV export zipped them
    #: and paired every later factor with the NEXT sample's values.
    sample_index: list = field(default_factory=list)
    #: v0.1.238 (D89) — counted samples that answered for another sliding
    #: mass of the deterministic circle (``_MassSwitches``); the sentence,
    #: when there are any, is ``notes["mass_switch"]``.
    mass_switches: int = 0

    # ------------------------------------------------------------------
    # v0.1.169 (D127) — ``Optional`` because the statistic they delegate to
    # answers ``None`` with no samples. In THIS class the guard of
    # ``run_global_minimum`` means such an instance never reaches a
    # consumer; the annotation still says so, because the default-built
    # instance exists and the type is the contract, not the itinerary.
    @property
    def probability_of_failure(self) -> Optional[float]:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> Optional[float]:
        return self.statistics.reliability_index()

    @property
    def mean_fos(self) -> Optional[float]:
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
            "lost_by_cause": self.notes.get("lost_by_cause"),
            "mass_switches": self.mass_switches,        # v0.1.238 (D89)
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
    #: Everything the run has to say, ONE SENTENCE PER ELEMENT. ``notes``
    #: above is the same content flattened into the two keys the status bar
    #: prints; this is that content unflattened, which is what the notes
    #: panel needs. ``AnalysisNotesPanel._split`` groups by a ``"<mid>: "``
    #: prefix, so several lost methods joined into ONE string hang entirely
    #: off the first one's identifier -- measured, and that is defect D129.
    #:
    #: A sentence about ONE method arrives prefixed ``"<mid>: "``; a
    #: sentence about the run arrives bare and falls under "Model". A LIST
    #: and not a dict keyed by method on purpose: a second sentence about
    #: the same method -- D88 is going to add one -- is one more element,
    #: not a ``notes[mid]`` overwritten.
    note_lines: list = field(default_factory=list)

    @property
    def reported(self):
        """The method a one-line summary speaks for: the first one that
        actually has a sample.

        v0.1.169 (D127). Defined next to ``ok`` because ``ok`` is exactly
        the claim that this is not ``None``, and the two must not be able
        to drift apart. It is also what spares every caller a dead "--"
        branch: past a checked ``ok`` this is never ``None``, so nothing
        formats a missing number and nothing has to pretend it might.

        It matters most in Overall Slope, where a method that lost every
        search KEEPS its entry in ``by_method`` (see ``run_overall_slope``)
        and ``next(iter(...))`` could hand back exactly that one.
        """
        return next((r for r in self.by_method.values()
                     if r.statistics.n > 0), None)

    @property
    def ok(self) -> bool:
        # NOT ``bool(self.by_method)`` any more: an entry with zero samples
        # is not a result, it is the absence of one wearing the shape of
        # one -- which is defect D127 and, in its wider form, D20.
        return self.reported is not None

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

    v0.1.208 (D189) — the slicer now gives a crest that arrives ON the
    crack line its wall back (``slicer.CRACK_WALL_ON_LINE``). That is what
    rescues the POLYLINE branch below, which is rebuilt from its
    dictionary and ends on the line: until then every sample of a critical
    polyline under a water-filled crack was evaluated without the thrust
    (on the phi = 0 slope of ``test_tension_crack_truncation_v1109``,
    1.0535 against 0.9750). The circle seed stays for the reason above:
    each sample resolves its own mass.

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


#: v0.1.236 (D93) — what a statistical run says when it is handed the
#: design-factored copy an analysis computes on instead of the model. A
#: constant because the three runs say the same thing.
_FACTORED_COPY = (
    "The project handed to this statistical run is the design-factored copy "
    "an analysis computes on, not the model: its samples would overwrite "
    "factored values with unfactored ones and be factored a second time. "
    "Pass the model itself; every sample is prepared like the analysis.")


def _analysis_copy(project):
    """``project`` as an analysis computes on it.

    v0.1.236 (D93) — ``prepare_analysis_project``: the design standard's
    factored copy with the Generalized links resolved, or the project
    itself when there is nothing to prepare, so a model without a standard
    and without links is evaluated exactly as before. It is the default
    ``prepare`` of the three statistical runs and the project their method
    and evaluator are configured from, which is what the analysis door
    (``analysis_runner.run_configured_statistics``) passes explicitly.
    """
    from ogr_core.project import prepare_analysis_project
    return prepare_analysis_project(project)[0]


def _is_factored_copy(project) -> bool:
    """Whether ``project`` is the copy ``apply_design_factors`` returned.

    ``getattr`` and not the attribute, because a project pickled before
    v0.1.236 does not carry the flag and is a model, not a copy.
    """
    return bool(getattr(project, "design_factored_copy", False))


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
def _publish_note(result, key: str, sentence: str) -> None:
    """Say ``sentence`` under ``key``, and keep it as its own line.

    v0.1.170 (D129). ``notes`` is what the status bar prints, and a status
    bar takes ONE string, so several sentences under the same key have to
    be joined. ``note_lines`` is that same content BEFORE the join, because
    the notes panel groups by the ``"<mid>: "`` prefix and a joined string
    hangs entirely off the first prefix in it.

    CONCATENATES, never assigns. The rule is not this function's invention:
    the stale-variable warning of v0.1.164 (D91) may already be sitting in
    ``warning``, and overwriting it would close one silence by opening the
    one before it. Making it a property of the WRITER rather than of each
    call site is the whole point -- ten sites copying the same two lines is
    exactly how the string and the list stop being the same content.
    """
    previous = result.notes.get(key)
    result.notes[key] = (previous + "; " + sentence if previous
                         else sentence)
    result.note_lines.append(sentence)


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
        _publish_note(
            result, "error",
            "none of the %d random variables matches the model: %s"
            % (len(active), ", ".join(orphans)))
        return True
    # Partial: the ones that DO write still carry a meaningful sampling, so
    # the run goes on. What it may not do is go on quietly.
    _publish_note(
        result, "warning",
        "%d of the %d random variables no longer match the model and were "
        "not sampled: %s" % (len(orphans), len(active), ", ".join(orphans)))
    return False


# ======================================================================
#: How a method lost its samples, one stem per analysis type. Constants and
#: not a boolean flag, because the two sentences differ in what they say
#: happened and a flag would hide that behind a call site.
#: Why a method never entered the sample loop at all. Constants because
#: ``run_sensitivity`` says the same two things, and a second copy of a
#: sentence is how two copies start to differ.
#:
#: The first reuses the words ``analysis_runner`` has published since
#: v0.1.77 for this SAME precondition on the deterministic path -- "a
#: method ticked but not registered leaves a trace". It does not name the
#: method because ``_method_lines`` puts the name on; the deterministic
#: path writes the id inside the sentence because it has no prefix
#: convention to lean on.
_NO_METHOD = "not a registered analysis method, so it was not computed."
_NO_DETERMINISTIC = ("the deterministic run left no critical surface for "
                     "this method, so there is nothing to re-evaluate.")

_STEM_GM = "failed on the deterministic critical surface"
_STEM_OS = "produced no valid surface"

#: v0.1.237 (D87) — why an Overall Slope method names no critical
#: probabilistic surface, in its ``notes["critical_probabilistic"]``. The
#: reference does not offer the surface for a search that steers on its own
#: factors nor with the Ky objective; the other two follow from what the
#: surface is. Interpret shows them through ``tr()`` BY VALUE, so each has
#: its Spanish entry in ``ogr_gui/i18n`` and a test keeps the two in step.
_CPS_STEERED = (
    "No critical probabilistic surface: this search steers on the "
    "factors of safety it computes, so it analyses different surfaces "
    "in every sample and none of them has a probability of failure of "
    "its own. It is computed for the Grid, Slope, Path and Block "
    "searches.")
_CPS_KY = (
    "No critical probabilistic surface: the search minimised the "
    "critical seismic coefficient Ky, and the critical probabilistic "
    "surface is defined on the factor of safety.")
_CPS_TOO_FEW = (
    "No critical probabilistic surface: too few valid samples to "
    "estimate one.")
_CPS_NOT_IN_EVERY_SAMPLE = (
    "No critical probabilistic surface: no surface of the search had a "
    "factor of safety in every sample, and a probability of failure "
    "counted over some of the samples only is not comparable with the "
    "others.")


def _critical_probabilistic_excluded(search, run) -> Optional[str]:
    """Why this run's search can name no critical probabilistic surface.

    v0.1.237 (D87) — the two exclusions the reference makes for a search as
    a whole, decided on the objects themselves. ``getattr`` with a default,
    because ``search_factory`` is the caller's and may hand back any object
    with a ``run``: one that does not claim to regenerate its surfaces is
    not taken to.
    """
    from ogr_slip2d.search import OBJECTIVE_FOS

    if not getattr(search, "SAME_SURFACES_EVERY_SAMPLE", False):
        return _CPS_STEERED
    if getattr(run, "objective", OBJECTIVE_FOS) != OBJECTIVE_FOS:
        return _CPS_KY
    return None


def _extent(surface) -> Optional[tuple]:
    """``(x_left, x_right)`` of a surface or of its dictionary, or None.

    v0.1.238 (D89) — which sliding mass of a circle an evaluation answered
    for. Within one run the geometry does not change, so the same mass
    comes back with the same extent to the last digit (the same arithmetic
    on the same ground: what ``_surface_key`` stands on, D87) and another
    mass with another extent — two masses of one circle are disjoint
    chords. So the extent alone tells them apart, and it is read off the
    object without ``to_dict()``, which on a composite redraws it.
    """
    if isinstance(surface, dict):
        x_left, x_right = surface.get("x_left"), surface.get("x_right")
    else:
        x_left = getattr(surface, "x_left", None)
        x_right = getattr(surface, "x_right", None)
    if x_left is None or x_right is None:
        return None
    return (float(x_left), float(x_right))


def _circle_of(surface) -> Optional[tuple]:
    """``(centre_x, centre_y, radius)`` of a circle-based surface, or None.

    A composite is its circle clipped and a weak-layer surface carries its
    base circle, so both answer; a polyline does not.
    """
    if isinstance(surface, dict):
        stype = _surface_type(surface)
        if stype == "weak_layer":
            return _circle_of(surface.get("base") or {})
        if stype not in _CIRCLE_SEEDED:
            return None
        values = (surface.get("centre_x"), surface.get("centre_y"),
                  surface.get("radius"))
    else:
        if not hasattr(surface, "radius") and hasattr(surface, "base"):
            return _circle_of(surface.base)
        values = (getattr(surface, "centre_x", None),
                  getattr(surface, "centre_y", None),
                  getattr(surface, "radius", None))
    if any(v is None for v in values):
        return None
    return tuple(float(v) for v in values)


class _MassSwitches:
    """Counted samples that answered for ANOTHER sliding mass of the
    deterministic circle.

    v0.1.238 (D89). D36 (v0.1.131) seeds every sample with the circle and
    no endpoints on purpose, so that each sample resolves its own mass, and
    ``_best_of_masses`` keeps the lower factor — which is right. What was
    missing is saying so: on a circle with two masses, a sampled parameter
    that crosses the point where the critical mass changes makes those
    samples answer for the other one, and measured on the notched slope of
    ``test_statistical_rebuild_v1154`` with the cohesion of its upper soil
    between 50 and 450 psf, the ten samples below 1 of forty were all of
    them from the notch — the probability of failure belonged entirely to
    a mass the deterministic answer is not. Counting changes no number.

    A deterministic surface without an extent (a dictionary written
    without one) or without a circle (a polyline, which keeps its ends) is
    not watched: there is nothing to compare, or no mass to change.
    """

    def __init__(self, deterministic_surface):
        self.home = _extent(deterministic_surface)
        self.circle = _circle_of(deterministic_surface)
        self.count = 0
        self.below_one = 0
        self.at: dict = {}          # extent -> samples that answered for it

    @property
    def watching(self) -> bool:
        return self.home is not None and self.circle is not None

    def see(self, result) -> bool:
        """Count ``result`` if it is the deterministic circle answering for
        another mass; a different circle is not a change of mass."""
        if not self.watching:
            return False
        surface = getattr(result, "surface", None)
        extent = _extent(surface)
        if (extent is None or extent == self.home
                or _circle_of(surface) != self.circle):
            return False
        self.count += 1
        self.at[extent] = self.at.get(extent, 0) + 1
        if result.fos < 1.0:
            self.below_one += 1
        return True

    def where(self) -> str:
        """The masses it went to; how many went to each only when there is
        more than one, since otherwise the head of the sentence says it."""
        if len(self.at) == 1:
            (xl, xr), = self.at
            return "x from %.2f to %.2f" % (xl, xr)
        return "; ".join("x from %.2f to %.2f in %d" % (xl, xr, n)
                         for (xl, xr), n in sorted(self.at.items()))

    def sentence(self, head: str, below_one: Optional[int] = None) -> str:
        """``head`` says what changed mass, in the caller's words; with
        ``below_one`` (the samples under 1 of the run), how much of the
        probability of failure is theirs."""
        text = "%s (%s), not for its own (x from %.2f to %.2f)" % (
            head, self.where(), self.home[0], self.home[1])
        if below_one:
            text += ("; %d of the %d with a factor below 1 are among them, "
                     "and the probability of failure counts them"
                     % (self.below_one, below_one))
        return text + "."


#: v0.1.239 (D88) — the refusal of the probe below. No ": " inside: the
#: panel groups a line by the first one, which ``_method_lines`` puts after
#: the method id.
_NOT_ITSELF = (
    "The deterministic critical surface does not re-evaluate to itself on "
    "the project the samples run on (it answers for x from %.2f to %.2f, "
    "%s, instead of x from %.2f to %.2f, %s); a setting that decides the "
    "sliding mass, such as Composite Surfaces or a surface filter, differs "
    "between the two runs, so this method was skipped.")


def _does_not_reevaluate_to_itself(project, prepare, search, surface,
                                   surface_dict) -> Optional[str]:
    """Why the deterministic surface is not itself on the samples' project.

    v0.1.239 (D88). The guard of v0.1.154 (``_cannot_reevaluate``) refuses
    a composite whose samples run with Composite Surfaces off, and nothing
    else: the other direction passes it. A deterministic run with the
    option OFF gives a circle that answers for one mass; samples with it ON
    answer for another, and on the notched slope of
    ``test_statistical_rebuild_v1154`` the result reported 3.3585 as the
    deterministic factor over samples around 1.38 (−59 %), with no note. A
    surface filter set only on the samples' project does the same (+141 %).
    The guard cannot see either: it would have to know the settings the
    deterministic surface came from, and they do not travel.

    So the question is asked of the MECHANISM, which needs no such memory:
    the seed of the deterministic surface, evaluated once on the project
    the samples run on — prepared as they are, with no sample applied — by
    the samples' own evaluator, has to come back as the same surface: the
    same type and the same extent. Within one geometry the same mass comes
    back to the last digit (D87, D89), so any difference is a different
    mechanism. Symmetric by construction, and for any setting that decides
    the mass, not only for the one the guard knows.

    Direct dispatch on purpose, not through ``_evaluate_on``: tests patch
    that global to count and to fail sample evaluations, and the probe is
    not a sample. An exception, no result or a surface without an extent
    refuses nothing: the samples will say what they find. A deterministic
    surface without an extent (a dictionary written without one) or a
    polyline (it keeps its ends) is not probed.
    """
    home = _extent(surface_dict)
    if home is None:
        return None
    from ogr_slip2d.surface import SlipCircle

    try:
        unperturbed = prepare(clone_project(project))
        if isinstance(surface, SlipCircle):
            r = search.evaluate_circle(unperturbed, surface)
        else:
            r = search.evaluate_surface(unperturbed, surface)
    except Exception:  # noqa: BLE001 - see the docstring
        return None
    there = _extent(getattr(r, "surface", None))
    if there is None:
        return None
    home_type = _surface_type(surface_dict)
    there_type = _surface_type(r.surface.to_dict())
    if there == home and there_type == home_type:
        return None
    return _NOT_ITSELF % (there[0], there[1], there_type,
                          home[0], home[1], home_type)


def _accumulate_surfaces(run, per_surface: dict) -> None:
    """One factor per surface of ``run``, under its key in ``per_surface``.

    v0.1.237 (D87). ONE per surface and sample — a surface met twice in a
    run is one surface met once — so that "a factor in every sample" can be
    read off the count. What the search steered to (``SearchResult.
    steered``: a walk, an optimisation; ``optimized`` too, for a result
    that predates the list) is left out, as the reference leaves out the
    optimised surfaces: another sample would not have produced it.

    v0.1.202 — admissible ones only: an inadmissible surface has no factor
    of safety to accumulate.
    """
    left_out = {id(r) for r in (getattr(run, "steered", None) or ())}
    optimized = getattr(run, "optimized", None)
    if optimized is not None:
        left_out.add(id(optimized))
    seen: set = set()
    for ev in run.evaluations:
        if id(ev) in left_out or not counts_as_sample(ev):
            continue
        sd = ev.surface.to_dict() if hasattr(ev.surface, "to_dict") else None
        key = _surface_key(sd)
        if not key or key in seen:
            continue
        seen.add(key)
        sp = per_surface.get(key)
        if sp is None:
            sp = SurfaceProbability(surface=sd)
            per_surface[key] = sp
        sp.statistics.values.append(ev.fos)


def counts_as_sample(r) -> bool:
    """Whether an evaluated sample HAS a factor of safety.

    v0.1.202 — valid AND admissible. The reference defines the probability
    of failure over the VALID analyses only ("if the safety factor could
    not be calculated for some analyses, then numtotal = total number of
    VALID analyses"), and it reports a surface with m_alpha < 0.2, or with
    a tensile base when that check is on, as an INVALID surface with an
    error code in place of the factor (-112, -120). ``is_valid`` alone
    counted those samples as survivors or failures.
    """
    return (r is not None and r.is_valid
            and bool(getattr(r, "admissible", True)))


_CODE_LABELS = {-120: "-120 tensile stress", -112: "-112 m-alpha",
                -101: "inadmissible (-101)"}


def _sample_failure(exc, r) -> str:
    """Label the way ONE sample was lost, for counting.

    v0.1.169 (D127). The ficha asks for "the reason of the last failed
    sample, which the ``except`` has", and that is both less than this
    module can say and, in one case, nothing at all: measured, a sample
    whose ``LEMResult`` comes back with ``is_valid`` false never reaches
    the ``except``, and before this version the two routes produced an
    identical state — ``ok`` true, ``pf`` nan, an empty ``notes``.

    They are three distinguishable outcomes, not one. And since v0.1.152
    (D56) an invalid result carries ``reason``, one of ``ALL_REASONS``,
    put there so a caller can "GROUP by reason instead of matching free
    text" — which is why these are COUNTED rather than kept one at a
    time. The reference reports exactly that shape: a code and how many
    surfaces gave it.
    """
    if exc is not None:
        return "raised %s" % type(exc).__name__
    if r is None:
        return "no result"
    if r.is_valid and not getattr(r, "admissible", True):
        # v0.1.202 — screened out: the reference's error code, from the
        # one mapping (``interpretation.error_code``).
        from ogr_slip2d.interpretation import error_code
        return _CODE_LABELS.get(error_code(r), "inadmissible")
    return getattr(r, "reason", "") or getattr(r, "error_message",
                                               "") or "unstated"


def _search_failure(exc, run) -> str:
    """The same, for an Overall Slope iteration, which loses a whole
    SEARCH and not one evaluation.

    ``run is None`` and ``run.critical is None`` are not the same fault —
    the first is a factory or a search that blew up on its own terms, the
    second a search that ran and found nothing admissible — and today's
    code collapses them into one counter.
    """
    if exc is not None:
        return "raised %s" % type(exc).__name__
    if run is None:
        return "no result"
    if run.critical is not None:
        # v0.1.202 — ``critical`` falls back to an inadmissible surface
        # when the search found no admissible one; that sample has no
        # factor of safety either.
        return "no admissible surface"
    return "no critical surface"


def _counted_reasons(counts: dict) -> str:
    """``"zero_driving x 17, raised ValueError x 3"``.

    Ordered by frequency and then by name, never by insertion, so two runs
    over the same data read the same way.
    """
    return ", ".join("%s x %d" % (k, n) for k, n in
                     sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _no_sample_note(num_samples: int, stem: str, counts: dict) -> str:
    """Why this method has no probability of failure.

    THE SENTENCE MAY NOT BLAME THE VARIABLE RANGES. That is the lesson of
    v0.1.154 (D59), whose test demands in as many words that the reason
    not accuse the ranges, which are innocent when the fault is a surface
    that cannot be formed or a strength the method cannot solve. The 20 %
    warning keeps its own wording and its own threshold; this is a
    different sentence for a different state, and it names the measured
    cause instead of guessing at one.

    v0.1.170 (D129) — the ``"<mid>: "`` prefix is NOT written here any
    more. It goes on once, in ``_method_lines``. The three sentences of
    ``_cannot_reevaluate`` never carried it, so the panel filed them under
    "Model" and the user read "this method was skipped" without being told
    WHICH -- an invariant honoured by two writers out of five is not an
    invariant. What stays under ``notes[mid]`` is the bare fact, which is
    what ``StatisticsWindow`` needs: there the method is already the
    combo's own label, and a sentence repeating it would be noise.
    """
    if not counts:
        return ("no sample was drawn, so this method has no probability "
                "of failure.")
    return ("all %d samples %s, so this method has no probability of "
            "failure. Reasons: %s."
            % (num_samples, stem, _counted_reasons(counts)))


def _method_lines(result, lost: list) -> list:
    """One line per lost method, ``"<mid>: <sentence>"``.

    v0.1.170 (D129). THE ONE PLACE the method's name is put on, so the
    invariant "a sentence about a method names it" holds by construction
    instead of depending on each writer having remembered. ``lost`` is the
    explicit list the loops built; the dictionary is never asked which of
    its keys look like method ids.

    ``str.partition(": ")`` in the panel takes the FIRST occurrence, and
    measured none of the three ``_cannot_reevaluate`` sentences contains
    one while ``_no_sample_note`` only reaches its own in "Reasons: ...",
    which comes later -- so the prefix put here is always the one that
    decides the group.
    """
    return ["%s: %s" % (mid, result.notes[mid]) for mid in lost
            if mid in result.notes]


def _publish_method_losses(result, lost: list) -> None:
    """Put the lost methods where the interface actually looks.

    v0.1.169 (D127). Two things the ficha gets wrong and that this
    function is the answer to. It asks for ``mres.notes["error"]``, and
    NOBODY in the program reads a per-method ``notes``: ``main_window``
    reads ``res.notes``, the notes of the RESULT — so a reason written
    there is a note that does not exist, which is what
    ``test_statistical_rebuild_v1154`` calls the state worth avoiding.
    And a method that does not survive has its ``mres`` discarded whole,
    so there is nothing left to carry it.

    ``lost`` is an EXPLICIT list the two loops append to, never something
    deduced by asking which keys of ``notes`` are not ``"error"`` or
    ``"warning"``. Dispatching on the shape of a dictionary instead of on
    what the code knows is literally D59.

    The partial case — one method answers and another loses everything —
    is published as a ``warning`` and CONCATENATED, never assigned: the
    stale-variable warning of v0.1.164 (D91) may already be sitting in
    that key, and overwriting it would close one silence by opening the
    one before it.
    """
    lines = _method_lines(result, lost)
    # First, and with no guard in front of it: a line has to reach the
    # panel even when the roll-up below declines to publish it because
    # ``error`` is already taken.
    result.note_lines.extend(lines)

    if result.ok:
        if lines:
            previous = result.notes.get("warning")
            text = "; ".join(lines)
            result.notes["warning"] = (previous + "; " + text if previous
                                       else text)
        return

    if "error" in result.notes:
        return
    # The v0.1.154 roll-up, keyed on ``ok`` rather than on an empty
    # ``by_method``: in Overall Slope the entry STAYS (see
    # ``run_overall_slope``), so "no method survived" and "the dictionary
    # is empty" stopped being the same statement.
    #
    # v0.1.170 (D129) — ``rest`` does not CLASSIFY, it CONSERVES. It never
    # asks what a key means; it carries whatever another writer left that
    # this function did not render itself. That is what saves the
    # ``"variables"`` key of ``run_sensitivity`` without this function
    # having to know such a key exists -- and the day D88 adds another one,
    # ``rest`` carries it unaided.
    lost_keys = set(lost)
    rest = [str(v) for k, v in result.notes.items()
            if k != "warning" and k not in lost_keys]
    joined = "; ".join(lines + rest)
    # Structural, not defensive: with nothing lost and nothing else to say
    # -- a healthy run -- this writes no key at all, which is what
    # ``test_nothing_is_said_when_nothing_was_lost`` demands and what the
    # ``if not lost: return`` used to provide. That early return had to go:
    # a sensitivity run whose every variable is an orphan arrives here with
    # ``lost`` EMPTY and still owes the user an ``error``.
    if joined:
        result.notes["error"] = joined


def _publish_method_warnings(result) -> None:
    """Surface what a SURVIVING method had to say.

    v0.1.170 (D129). ``mres.notes`` is read by nobody in the program: the
    20 % sentence of ``run_global_minimum`` and the failed-search sentence
    of ``run_overall_slope`` have been written there and never shown. This
    puts them on ``note_lines`` and NOWHERE else -- ``notes`` is the status
    bar's one-line headline, and a per-method detail does not belong in a
    headline. It also means every assertion that already exists about
    ``notes`` on a partly-failed run keeps the answer it had.

    Only the ``warning`` key, and only for a method that HAS samples. Both
    limits are measured rather than tidy:

    * a healthy Overall Slope run carries ``surfaces_tracked`` -- 115 and
      116 on the two methods of the reference model -- so surfacing
      ``mres.notes`` wholesale would turn a diagnostic count into a note on
      every sound run, which is regla 7 with its sign flipped;
    * a method that lost everything KEEPS its entry in Overall Slope and
      already has a line from ``_method_lines``; without the ``n > 0``
      filter it would be named twice for one fault.

    The sentence and the threshold are NOT touched: this version opens the
    channel, it does not rewrite the note.

    v0.1.238 (D89) — and the ``mass_switch`` sentence, under a key of its
    own so the 20 % one stays word for word. The count itself
    (``mass_switches``) is a field, not a note, for the reason
    ``surfaces_tracked`` is not published: a number on every sound run is
    not a sentence.
    """
    for mid, mres in result.by_method.items():
        if getattr(mres.statistics, "n", 0) <= 0:
            continue
        notes = getattr(mres, "notes", None) or {}
        for key in ("warning", "mass_switch"):
            said = notes.get(key)
            if said:
                result.note_lines.append("%s: %s" % (mid, said))


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
    prepare: Optional[Callable] = None,
) -> ProbabilisticResult:
    """Run a Global Minimum probabilistic analysis.

    Args:
        project: the MODEL the user edits (never modified), not the
            design-factored copy an analysis computes on: that copy is
            refused with a note (v0.1.236, D93), because sampling it would
            write unfactored values over factored ones and factor them again.
        critical_surfaces: ``method_id -> LEMResult`` from the
            deterministic run (``analysis_runner.run_analysis``, which
            computes on the prepared copy). Each method keeps its OWN
            critical surface, as the reference specifies. Said because the
            default ``prepare`` turned the old mismatch round: a caller who
            computes its deterministic surface on the RAW model while a
            design standard is on gets factored samples next to an
            unfactored ``deterministic_fos``. Nothing here can tell which
            model a ``LEMResult`` came from.
        variables: the :class:`RandomVariable` list.
        num_samples: N.
        sampling: Monte Carlo or Latin Hypercube.
        seed: for reproducibility.
        num_slices: slicing used in the repeated evaluations.
        method_factory: ``method_id -> LEMMethod``; defaults to
            ``analysis_runner.build_method`` on the project as the analysis
            prepares it, which is the one place that configures a method
            from the project (v0.1.108).
        progress_cb: called as ``(done, total)``.
        prepare: ``project -> project`` applied to every sampled clone
            after its sample, before it is evaluated (v0.1.201), so a
            sampled value is factored like the deterministic one instead of
            overwriting a factored parameter with an unfactored value. None
            means the analysis preparation (``prepare_analysis_project``:
            the design standard's factors and the Generalized links), as
            the analysis door passes it (v0.1.236, D93); until then None
            left the clone as sampled, and a direct caller put unfactored
            samples next to a factored deterministic surface. Pass
            ``lambda clone: clone`` for the model exactly as sampled.

    Returns:
        A :class:`ProbabilisticResult`, empty when no variable is random.
    """
    from ogr_slip2d.analysis_runner import build_evaluator, build_method

    result = ProbabilisticResult(
        num_samples=num_samples, sampling_method=sampling.value,
        analysis_type=ProbabilisticType.GLOBAL_MINIMUM)

    # v0.1.236 (D93) — refused before anything is drawn (``_FACTORED_COPY``).
    if _is_factored_copy(project):
        _publish_note(result, "error", _FACTORED_COPY)
        return result
    # v0.1.236 (D93) — the samples are prepared like the analysis unless the
    # caller says how, and the method and the evaluator are configured from
    # the same prepared, unsampled project, as the door configures them from
    # its ``factored``. Measured before the change on the slope of
    # ``test_cli_wiring_v177`` with EC7 DA1-C2: the door 0.9071 / PF 0.850,
    # a direct call with the same deterministic surface and no ``prepare``
    # 1.1333 / PF 0.120. Without a standard and without links the prepared
    # project IS the project, so nothing else moves.
    if prepare is None:
        prepare = _analysis_copy

    active = [rv for rv in variables if rv.distribution.is_random]
    if not active:
        _publish_note(
            result, "error",
            "No random variables defined. At least one model input "
            "parameter must be given a statistical distribution.")
        return result
    if not critical_surfaces:
        _publish_note(
            result, "error",
            "No deterministic result: run the regular analysis first so "
            "the global minimum surface is known.")
        return result
    configured = _analysis_copy(project)

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

        v0.1.236 (D93) — from ``configured``, the project as the analysis
        prepares it, which is what the door's own factory builds on.
        """
        if method_factory is not None:
            return method_factory(mid)
        return build_method(configured, mid, num_slices)

    total = num_samples * max(1, len(critical_surfaces))
    done = 0
    # v0.1.169 (D127) — the methods that come back with nothing, named as
    # the loop loses them. See ``_publish_method_losses`` for why this is a
    # list and not something read back off ``result.notes``.
    lost: list = []

    for mid, det in critical_surfaces.items():
        method = _make_method(mid)
        if method is None or det is None:
            # v0.1.170 (D129) — a bare ``continue`` until this version, and
            # that is a THIRD route to the same defect: a method vanishing
            # from the results without a word. Reachable and not
            # theoretical -- ``build_method`` answers ``None`` for a
            # method_id that is not in the registry, which is exactly how
            # "Janbu Corrected" could be ticked and produce nothing.
            result.notes[mid] = (_NO_METHOD if method is None
                                 else _NO_DETERMINISTIC)
            lost.append(mid)
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
            lost.append(mid)
            continue
        surface = _rebuild_surface(sd)
        if surface is None:
            continue
        # v0.1.235 (D92) — the search the PROJECT configures, not one
        # assembled here. Until this version this line was a bare
        # ``GridSearch`` with the method and the admissibility screens and
        # nothing else, so the Surface Filters, the Slope Limits, the focus
        # objects, the seismic mode and the Minimum Area of the
        # deterministic run never reached a sample: on a circle with two
        # sliding masses every sample could answer for the mass the
        # deterministic run had filtered out. ``build_evaluator`` is the one
        # door, and it takes the method built above as it is.
        search = build_evaluator(configured, mid, method=method,
                                 num_slices=num_slices)
        # v0.1.239 (D88) — and the other direction of the guard above, asked
        # of the mechanism: the surface has to come back as itself on the
        # project the samples run on.
        mismatch = _does_not_reevaluate_to_itself(project, prepare, search,
                                                  surface, sd)
        if mismatch is not None:
            result.notes[mid] = mismatch
            lost.append(mid)
            continue

        mres = MethodProbabilisticResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan),
            surface=sd if isinstance(sd, dict) else None,
        )
        values: list[float] = []
        counts: dict = {}
        switches = _MassSwitches(sd)            # v0.1.238 (D89)
        for i in range(num_samples):
            clone = clone_project(project)
            one = {k: v[i] for k, v in samples.items()}
            apply_sample(clone, active, one)
            exc = None
            try:
                clone = prepare(clone)
                r = _evaluate_on(clone, search, surface)
            except Exception as e:  # noqa: BLE001
                r, exc = None, e
            if counts_as_sample(r):
                values.append(r.fos)
                mres.sample_index.append(i)
                switches.see(r)
            else:
                # A sample can make the surface unsolvable (for instance a
                # very low strength). It is counted separately rather than
                # dropped silently, because a large count means the
                # distributions are unrealistic.
                mres.failed_samples += 1
                # v0.1.169 (D127) — and counted BY CAUSE, because the
                # exception, the missing result and the declared reason of
                # D56 are three different faults that the single counter
                # above cannot tell apart.
                label = _sample_failure(exc, r)
                counts[label] = counts.get(label, 0) + 1
            done += 1
            if progress_cb and done % 25 == 0:
                progress_cb(done, total)

        if not values:
            # v0.1.169 (D127) — nothing survived, so there is no
            # probability of failure to publish. The method does NOT enter
            # ``by_method``: that is what makes ``ok`` false without an
            # ``ok`` to assign, and it is why the interface cannot reach a
            # ``None`` where it formats a number.
            #
            # Before the guard, ``SampleStatistics(values=[])`` answered
            # ``pf`` nan and ``beta`` -inf -- the latter because
            # ``nan >= 1.0`` is False -- and the status bar printed
            # "PF = nan %, beta = -inf" with ``ok`` true and no error at
            # all.
            result.notes[mid] = _no_sample_note(num_samples, _STEM_GM,
                                                counts)
            lost.append(mid)
            continue

        mres.statistics = SampleStatistics(values=values)
        # v0.1.238 (D89) — said, and only said: no number moves.
        mres.mass_switches = switches.count
        if switches.count:
            mres.notes["mass_switch"] = switches.sentence(
                "%d of %d samples answered for another sliding mass of the "
                "deterministic circle" % (switches.count, len(values)),
                sum(1 for v in values if v < 1.0))
        # The 20 % warning and its wording are untouched, and it is now
        # only reached when at least one sample DID survive -- which is
        # exactly where "check the variable ranges" still means something.
        # With 20 of 20 lost it used to be written onto an ``mres`` nobody
        # would ever read.
        if mres.failed_samples:
            # v0.1.202 — by cause, whenever any sample was lost: since
            # samples screened out (-112, -120) have no factor of safety
            # either, "how many, and why" is part of the answer.
            mres.notes["lost_by_cause"] = _counted_reasons(counts)
        if mres.failed_samples > 0.2 * num_samples:
            # The sentence stays as it was (test_probabilistic_all_failed_
            # v1169 holds it); the causes are in ``lost_by_cause``.
            mres.notes["warning"] = (
                f"{mres.failed_samples} of {num_samples} samples could "
                f"not be evaluated; check the variable ranges.")
        result.by_method[mid] = mres

    # v0.1.154 — if no method survived, the reason rises to the key the
    # interface actually prints: ``_compute_statistics`` looks only at
    # ``notes['error']``, and only when the run comes back empty.
    # v0.1.169 (D127) — and if SOME method survived, the ones that did not
    # stop being silent: the partial case used to leave its reason under
    # ``notes[mid]``, a key no consumer reads.
    _publish_method_losses(result, lost)
    _publish_method_warnings(result)

    if progress_cb:
        progress_cb(total, total)
    return result


# ======================================================================
@dataclass
class SurfaceProbability:
    """Probability statistics accumulated for ONE slip surface across the
    samples of an Overall Slope run.

    v0.1.237 (D87) — one factor per sample in which the search analysed it
    with an admissible factor, under its exact identity (``_surface_key``).
    Only one with a factor in every counted sample can be the critical
    probabilistic surface.
    """

    surface: Optional[dict] = None
    statistics: SampleStatistics = field(default_factory=SampleStatistics)
    times_global_minimum: int = 0

    @property
    def probability_of_failure(self) -> Optional[float]:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> Optional[float]:
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
    #: v0.1.201 — see ``MethodProbabilisticResult.sample_index``.
    sample_index: list = field(default_factory=list)
    #: v0.1.238 (D89) — counted samples whose critical surface was the
    #: deterministic circle answering for another sliding mass. Another
    #: circle is not a change of mass: that is the moving minimum this
    #: analysis exists to find.
    mass_switches: int = 0

    @property
    def probability_of_failure(self) -> Optional[float]:
        return self.statistics.probability_of_failure()

    @property
    def reliability_index(self) -> Optional[float]:
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
            # v0.1.169 (D127) — ``None`` and not ``math.nan``: no eligible
            # surface means there is no such probability, and the same
            # policy that governs an empty sampling governs its absence.
            "critical_probabilistic_pf": (
                cp.probability_of_failure if cp else None),
            "critical_probabilistic_beta": (
                cp.reliability_index if cp else None),
            # v0.1.237 (D87) — and why there is none, when there is none.
            "critical_probabilistic_note":
                self.notes.get("critical_probabilistic"),
            "mass_switches": self.mass_switches,        # v0.1.238 (D89)
            "failed_samples": self.failed_samples,
            "lost_by_cause": self.notes.get("lost_by_cause"),
        }


def _exact(value) -> str:
    """A coordinate as the shortest text that reads back as the same float.

    ``float`` first, so the integer 4 and the float 4.0 — one coordinate —
    are one text; ``+ 0.0`` folds -0.0 onto 0.0, the one pair of equal
    floats that print differently.
    """
    return repr(float(value) + 0.0)


def _surface_key(sd: dict) -> str:
    """Identity of a surface for accumulating statistics across samples.

    v0.1.237 (D87) — the TYPE and the GEOMETRY TO THE LAST DIGIT, extent
    included, and nothing rounded. Until v0.1.236 a circle was its centre
    and radius rounded to 0.5 model units, which merged three kinds of
    surface that are not the same surface: the two disjoint sliding masses
    of one circle, a composite and the uncut circle it was clipped from,
    and two circles of a grid less than half a unit apart. Measured on
    bank problem 36 (a 20 x 20 grid at 1.0 x 1.25 m, ten radius
    increments): 746 of its 1570 keys gathered circles that differ, and two
    of them hid the critical probabilistic surface — the circle with the
    lowest reliability index shared its key with its neighbour of the next
    radius, and the mixture lost.

    No tolerance, because where the key decides something none is needed:
    the critical probabilistic surface is only named for a search that
    regenerates the same surfaces in every sample
    (``BaseSearch.SAME_SURFACES_EVERY_SAMPLE``), and such a search
    regenerates them to the last digit — the same arithmetic on the same
    geometry. A tolerance can only merge, and what it merges is a mixture
    whose probability of failure belongs to no surface. (The old 0.5 was
    also absolute, in the model's units.) For a search that steers on its
    own factors the minima differ in some digit from sample to sample, so
    ``distinct_minima`` counts each of them: that is what they are.
    """
    stype = _surface_type(sd)
    if stype is None:
        return ""
    if stype in _CIRCLE_SEEDED:
        key = "%s:%s:%s:%s" % (stype, _exact(sd["centre_x"]),
                               _exact(sd["centre_y"]), _exact(sd["radius"]))
        x_left, x_right = sd.get("x_left"), sd.get("x_right")
        if x_left is None or x_right is None:
            # A circle never resolved onto a mass, or a dictionary written
            # without its extent: still a key, just not the key of a mass.
            return key
        return "%s:%s:%s" % (key, _exact(x_left), _exact(x_right))
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
        # ``weak_layer`` publishes its drawn vertices at the root. Until
        # v0.1.154 they all collapsed onto the empty key "p:", which merged
        # surfaces that are not the same surface.
        verts = sd.get("vertices") or []
    if not verts:
        # No key rather than the bare "p:" every vertexless surface used
        # to share: the caller skips an empty key, and skipping one
        # surface is better than merging it with all the others.
        return ""
    # v0.1.237 (D87) — the type after the prefix: two types with the same
    # vertices are still two surfaces.
    return "p:%s:" % stype + ":".join(
        "%s,%s" % (_exact(v[0]), _exact(v[1])) for v in verts)


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
    prepare: Optional[Callable] = None,
) -> ProbabilisticResult:
    """Run an **Overall Slope** probabilistic analysis.

    ``project`` and ``prepare`` as in :func:`run_global_minimum`: the model,
    never the design-factored copy (refused), and every sampled clone
    prepared like the analysis when ``prepare`` is None (v0.1.236, D93).
    The search is the caller's (``search_factory``), so nothing else here
    is configured from the prepared project.

    The ENTIRE SEARCH is repeated ``num_samples`` times, loading a new
    set of random-variable samples each time, so the location of the
    global minimum is NOT assumed fixed — which is the whole point of
    this analysis type, and what distinguishes it from Global Minimum.

    The probability of failure keeps the same definition: the number of
    analyses giving a factor of safety below 1, divided by the number of
    samples.

    In addition, the **critical probabilistic surface** is determined:
    the individual surface with the maximum probability of failure (ties
    broken by the lower reliability index), which as the reference
    stresses *need not be the deterministic critical surface*.

    v0.1.237 (D87) — what "individual surface" means. A probability of
    failure is a property of ONE surface over the samples, PF(S) =
    P[F(S, X) < 1], so:

    * a surface is its type and its geometry to the last digit, extent
      included (``_surface_key``): pooling two surfaces gives the PF of a
      mixture, which belongs to neither;
    * a candidate has a factor in EVERY counted sample. Counting a surface
      only in the samples where the search happened to report it biases
      its PF — which mass of a circle the engine reports depends on X —
      and leaves it incomparable with the others. With every candidate
      counted over the run's own samples, PF(critical probabilistic) <=
      PF(run) holds by construction, as the reference documents it;
    * what the search steered to (``SearchResult.steered``) never enters;
    * there is none, with the reason in ``notes["critical_probabilistic"]``,
      for a search that steers on its own factors
      (``SAME_SURFACES_EVERY_SAMPLE`` false), with the Ky objective — the
      reference's two exclusions —, with fewer than ``min_evaluations``
      counted samples, or when no surface had a factor in every sample.

    ``search_factory`` is a callable ``method_id -> BaseSearch`` that
    builds a fully configured search, so the run honours exactly the same
    search settings as a normal analysis.

    Be aware this is **substantially more expensive** than the Global
    Minimum type: a full search per sample.
    """
    result = ProbabilisticResult(
        num_samples=num_samples, sampling_method=sampling.value,
        analysis_type=ProbabilisticType.OVERALL_SLOPE)

    # v0.1.236 (D93) — as in ``run_global_minimum``. Measured before the
    # change on the slope of ``test_cli_wiring_v177`` with EC7 DA1-C2, 40
    # searches: the door 0.9064 / PF 0.850, a direct call without
    # ``prepare`` 1.1325 / PF 0.125.
    if _is_factored_copy(project):
        _publish_note(result, "error", _FACTORED_COPY)
        return result
    if prepare is None:
        prepare = _analysis_copy

    active = [rv for rv in variables if rv.distribution.is_random]
    if not active:
        _publish_note(
            result, "error",
            "No random variables defined. At least one model input "
            "parameter must be given a statistical distribution.")
        return result
    if not method_ids:
        _publish_note(result, "error", "No analysis method selected.")
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
    lost: list = []

    for mid in method_ids:
        det = (deterministic or {}).get(mid)
        ores = OverallSlopeResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan))
        per_surface: dict = {}
        minima_keys: set = set()
        values: list[float] = []
        counts: dict = {}
        # v0.1.237 (D87) — why this method names no critical probabilistic
        # surface, once something says so; until then, there may be one.
        why_not: Optional[str] = None
        switches = _MassSwitches(getattr(det, "surface", None))   # D89

        for i in range(num_samples):
            clone = clone_project(project)
            apply_sample(clone, active, {k: v[i] for k, v in
                                         samples.items()})
            exc = None
            try:
                clone = prepare(clone)
                search = search_factory(mid)
                run = search.run(clone)
            except Exception as e:  # noqa: BLE001
                run, exc = None, e
            done += 1
            if progress_cb:
                progress_cb(done, total)
            if run is None or not counts_as_sample(run.critical):
                ores.failed_samples += 1
                # v0.1.169 (D127) — a search that blew up and a search that
                # ran and found nothing admissible are not the same fault,
                # and the counter above cannot tell them apart.
                label = _search_failure(exc, run)
                counts[label] = counts.get(label, 0) + 1
                continue

            values.append(run.critical.fos)
            ores.sample_index.append(i)
            switches.see(run.critical)

            # Per-surface statistics for the critical probabilistic
            # surface; v0.1.237 (D87): not for a search that cannot have
            # one, which spares a guided search the bookkeeping too.
            if why_not is None:
                why_not = _critical_probabilistic_excluded(search, run)
            if why_not is None:
                _accumulate_surfaces(run, per_surface)

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
        # ties broken by the lower reliability index, among the surfaces
        # with a factor in EVERY counted sample (v0.1.237, D87; see the
        # docstring). ``_accumulate_surfaces`` adds at most one factor per
        # sample, so a full count is exactly that.
        if values and why_not is None:
            if len(values) < min_evaluations:
                why_not = _CPS_TOO_FEW
            else:
                eligible = [sp for sp in per_surface.values()
                            if sp.statistics.n == len(values)]
                if eligible:
                    ores.critical_probabilistic = max(
                        eligible,
                        key=lambda sp: (sp.probability_of_failure,
                                        -sp.reliability_index))
                else:
                    why_not = _CPS_NOT_IN_EVERY_SAMPLE
        if values and why_not is not None:
            # Only with samples: a method that has none is lost, and
            # ``_publish_method_losses`` already says so.
            ores.notes["critical_probabilistic"] = why_not
        ores.mass_switches = switches.count
        if switches.count:
            ores.notes["mass_switch"] = switches.sentence(
                "%d of %d samples had the deterministic circle as their "
                "critical surface, answering for another sliding mass"
                % (switches.count, len(values)),
                sum(1 for v in values if v < 1.0))
        ores.notes["surfaces_tracked"] = len(per_surface)
        if ores.failed_samples:
            ores.notes["lost_by_cause"] = _counted_reasons(counts)
        if ores.failed_samples:
            ores.notes["warning"] = (
                f"{ores.failed_samples} of {num_samples} searches "
                f"produced no valid surface.")
        if not values:
            # v0.1.169 (D127) — same state as in ``run_global_minimum``,
            # said the same way, and DELIBERATELY not fixed the same way:
            # here the entry stays in ``by_method``.
            #
            # ``test_overall_slope_v137.test_failed_searches_counted`` runs
            # five searches that all raise and then asserts
            # ``res.by_method[mid].failed_samples == 5``. That is this very
            # state, it is green today, and the ficha for D127 lists that
            # file as untouchable -- so removing the entry here would be a
            # KeyError, not a fix. What turns the run off is ``ok``, which
            # now asks for a sample and not for a key. Anyone "unifying"
            # the two loops will break that test; this comment is why.
            result.notes[mid] = _no_sample_note(num_samples, _STEM_OS,
                                                counts)
            lost.append(mid)
        result.by_method[mid] = ores

    # v0.1.169 (D127) — the roll-up this function never had. Until now a
    # run in which every search of every method failed came back ``ok``
    # with ``pf`` nan and an empty ``notes``.
    _publish_method_losses(result, lost)
    _publish_method_warnings(result)

    return result


# ======================================================================
def sample_pairs(result, method_id: str, key: str) -> list:
    """``[(sample index, sampled value of key, factor of safety)]`` for
    the samples of ``method_id`` that produced a factor.

    v0.1.201 — paired by the sample's own index. The scatter data and the
    statistics export zipped the samples with the factors, and a failed
    sample shifted every later pair by one. A result without the index
    (built before this version) cannot be paired honestly and gives [].
    """
    m = (getattr(result, "by_method", None) or {}).get(method_id)
    col = (getattr(result, "samples", None) or {}).get(key)
    if m is None or col is None:
        return []
    idx = list(getattr(m, "sample_index", None) or [])
    values = list(m.statistics.values)
    if len(idx) != len(values):
        return []
    return [(i, col[i], f) for i, f in zip(idx, values)]
