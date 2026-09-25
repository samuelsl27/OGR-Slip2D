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


def _admissibility_kwargs(project) -> dict:
    """The project's own screens, for the search a sample is re-evaluated
    with (v0.1.202: a bare ``GridSearch`` always screened m-alpha and
    never the tensile check, whatever the project said)."""
    settings = getattr(project, "settings", None)
    if settings is None or not hasattr(settings, "admissibility_kwargs"):
        return {}
    return settings.admissibility_kwargs()


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
    """
    for mid, mres in result.by_method.items():
        if getattr(mres.statistics, "n", 0) <= 0:
            continue
        said = (getattr(mres, "notes", None) or {}).get("warning")
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
        prepare: ``project -> project`` applied to every sampled clone
            after its sample, before it is evaluated (v0.1.201): the
            analysis door passes the design factors here, so a sampled
            value is factored like the deterministic one instead of
            overwriting a factored parameter with an unfactored value.
            None leaves the clone as sampled.

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
        search = GridSearch(method=method, num_slices=num_slices,
                            min_area=0.0, **_admissibility_kwargs(project))

        mres = MethodProbabilisticResult(
            method_id=mid,
            deterministic_fos=getattr(det, "fos", math.nan),
            surface=sd if isinstance(sd, dict) else None,
        )
        values: list[float] = []
        counts: dict = {}
        for i in range(num_samples):
            clone = clone_project(project)
            one = {k: v[i] for k, v in samples.items()}
            apply_sample(clone, active, one)
            exc = None
            try:
                if prepare is not None:
                    clone = prepare(clone)
                r = _evaluate_on(clone, search, surface)
            except Exception as e:  # noqa: BLE001
                r, exc = None, e
            if counts_as_sample(r):
                values.append(r.fos)
                mres.sample_index.append(i)
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
    samples of an Overall Slope run."""

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
            "failed_samples": self.failed_samples,
            "lost_by_cause": self.notes.get("lost_by_cause"),
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
    prepare: Optional[Callable] = None,
) -> ProbabilisticResult:
    """Run an **Overall Slope** probabilistic analysis.

    ``prepare`` as in :func:`run_global_minimum` (v0.1.201).

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

        for i in range(num_samples):
            clone = clone_project(project)
            apply_sample(clone, active, {k: v[i] for k, v in
                                         samples.items()})
            exc = None
            try:
                if prepare is not None:
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

            # Accumulate per-surface statistics for the critical
            # probabilistic surface
            for ev in run.evaluations:
                # v0.1.202 — admissible ones only: an inadmissible surface
                # has no factor of safety to accumulate.
                if not counts_as_sample(ev):
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
