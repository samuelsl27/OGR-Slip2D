# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slip-surface search engines.

Two search strategies are provided:

    - :class:`GridSearch` — grid of circle centres × radius increments.
      Classical "Swedish" search for circular surfaces.
    - :class:`SlopeSearch` — sample circles that emerge at the toe of
      the slope with random angles / radii.

Both return a :class:`SearchResult` containing every evaluated surface
sorted by ascending Factor of Safety.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from ogr_core.project import Project
from ogr_core.project.settings import WeakLayerHandling

from .methods import LEMMethod, LEMResult
from .rapid_drawdown import RapidDrawdownError, drawdown_gap
from .slicer import slice_surface
from .surface import SlipCircle, WeakLayerSurface, lowest_elevation


# ----------------------------------------------------------------------
def _base_kwargs(legacy: dict) -> dict:
    """The :class:`BaseSearch` arguments every search takes by keyword.

    v0.1.102 — these are PROJECT settings, not per-search ones, so all six
    strategies accept them and all six used to pop them out of their own
    ``**legacy_kwargs`` with the same four lines copied six times.

    Consolidated because the copies were not merely repetitive, they were
    the trap: a new shared argument added to ``build_search`` lands in
    ``**legacy_kwargs`` and is **absorbed without a word**. That is how
    anomaly A37-1 would have happened a second time, one search at a time.
    Here it can only be forgotten once, and a test walks the six branches
    to make sure it has not been.
    """
    return {
        "reject_tensile": bool(legacy.pop("reject_tensile", False)),
        "tensile_tolerance": float(legacy.pop("tensile_tolerance", 0.05)),
        "tensile_percent": float(legacy.pop("tensile_percent", 95.0)),
        "check_m_alpha": bool(legacy.pop("check_m_alpha", True)),
        "min_elevation": legacy.pop("min_elevation", None),
        "min_depth": legacy.pop("min_depth", None),
        # v0.1.118 — the Slope Limits. They belong here, and not in four of
        # the six branches, because the reference is unambiguous that they
        # "ALWAYS serve as a filter for valid surfaces, regardless of the
        # Surface Type or the Search Method being used". Four searches
        # declared the argument, only ONE was ever given it, and the two
        # that did not declare it could not have honoured it at all.
        "slope_limits": legacy.pop("slope_limits", None),
        # v0.1.104 — Optimize Surfaces. Every search ACCEPTS them for the
        # reason above (a shared argument must be forgettable only once),
        # but only the three non-circular branches of ``build_search`` are
        # given one: the reference offers the option for Surface Type =
        # Non-Circular alone.
        "optimize": _optimize_argument(legacy.pop("optimize", None)),
        "optimize_seed": legacy.pop("optimize_seed", None),
        # v0.1.127 — the seismic analysis modes, here for the same
        # reason as the six above: it decides what the search MINIMISES,
        # so a search that never received it would quietly go on hunting
        # the lowest factor of safety while the report said Ky.
        "seismic_analysis": legacy.pop("seismic_analysis", None),
        # v0.1.129 — the focus objects, here for the same reason as the
        # eight above and with a twist of its own. The reason: they are a
        # PROJECT setting, drawn on the model and saved in the .ogr, so
        # the seven branches of ``build_search`` are exactly where one of
        # them gets forgotten — and six of them had been, since v0.1.55.
        # The twist: two searches DECLARED the argument, stored it in
        # ``self.focus_objects`` under a comment claiming it was "applied
        # BEFORE evaluation", and never read it again. So handing them the
        # value alone would have fixed nothing while looking fixed, which
        # is why the reading moved down into ``BaseSearch`` where every
        # search shares one. Defect D33.
        "focus_objects": list(legacy.pop("focus_objects", None) or ()),
    }


def _optimize_argument(value):
    """Refuse the boolean ``optimize`` Path Search took until v0.1.104.

    ``PathSearch(..., optimize=True)`` used to mean "run the private random
    walk over the best five surfaces". The argument now belongs to every
    search and carries an :class:`~ogr_slip2d.optimize.OptimizeSettings`,
    so a stale ``True`` would be absorbed by ``**legacy_kwargs`` and mean
    something else entirely.

    Refusing is the only answer that cannot be mistaken for having worked —
    the same argument ``_shadow_setting_problems`` makes for the settings
    that were renamed in v0.1.103, and the reason ``_base_kwargs`` exists
    at all. ``False`` is refused too, though it happens to mean what the
    default already does: a caller who wrote it deserves to be told the
    argument is gone rather than to keep writing it into new code.
    """
    if isinstance(value, bool):
        raise TypeError(
            "The boolean 'optimize' argument was removed in v0.1.104: Path "
            "Search no longer carries an optimiser of its own, and the "
            "argument now takes an OptimizeSettings (or None) and applies "
            "to every non-circular search. Pass "
            "optimize=OptimizeSettings(enabled=True) to optimise, or drop "
            "the argument not to.")
    return value


# v0.1.127 — what a search MINIMISES.
#
# Until now that was always the factor of safety, so every comparison in
# this file said ``a.fos < b.fos`` and every one of them meant the same
# thing. The seismic modes break that: asked for the critical seismic
# coefficient, the reference reports "the surface which requires the
# LOWEST value of Ky", and that surface is not in general the one with the
# lowest factor — the reference says as much, calling its Ky surface
# "quite different from the critical surface".
#
# So the comparison becomes a function, in ONE place, and the seven
# searches consult it instead of reading ``.fos``. Its default IS
# ``.fos``, which is what makes the change provable: with the seismic
# modes off, every search must return output that is bit for bit what it
# returned before, and that is the test.
#
# There is no third objective. The Newmark mode also minimises Ky, because
# the displacement of a rigid block is non-increasing in the critical
# acceleration — so the surface that moves the most IS the one with the
# lowest Ky, and integrating a record inside the search would buy nothing.
OBJECTIVE_FOS = "fos"
OBJECTIVE_KY = "ky"


def surface_score(result, objective: str = OBJECTIVE_FOS) -> float:
    """The scalar to minimise for one surface. Lower is more critical.

    ``math.inf`` for a surface that has no answer under this objective,
    so it can never win a comparison and never has to be special-cased at
    the call sites.
    """
    if result is None or not result.is_valid:
        return math.inf
    if objective == OBJECTIVE_KY:
        ky = (result.details or {}).get("ky")
        if ky is None or not math.isfinite(ky):
            return math.inf
        return float(ky)
    return result.fos


@dataclass
class SearchResult:
    """Aggregate result of a surface-search run."""

    method_id: str
    evaluations: list[LEMResult] = field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0
    # v0.1.24 — generation attempts made (searches that count VALID
    # surfaces, e.g. Path Search, report the true attempt count here).
    attempts: int = 0
    # v0.1.104 — the surface Optimize Surfaces produced, when it ran and
    # improved on what the search found. It is ALSO appended to
    # ``evaluations``, so ``critical`` finds it the ordinary way; this
    # attribute exists so a report can say that the answer came from the
    # optimisation rather than from the search, which is the one thing the
    # factor of safety alone cannot tell you.
    optimized: Optional[LEMResult] = None
    # v0.1.126 — the DISTINCT local minima, best first. Empty for the six
    # searches that predate the multimodal one, so nothing that reads a
    # SearchResult today has to change: ``critical`` is still the answer,
    # and it is still the lowest of everything evaluated. A search that
    # fills this is saying something extra — that it looked for several
    # and these are the ones it can tell apart — not something different.
    minima: list = field(default_factory=list)
    # v0.1.127 — the quantity this run minimised. "fos" for every run
    # that predates the seismic modes and for every run with them off,
    # which is why nothing downstream had to learn a new name.
    objective: str = OBJECTIVE_FOS
    # v0.1.121 — lines the run needs to say once, not once per surface.
    # Weak-layer case generation is the first user: when a surface is cut by
    # more layers than the case limit allows, the set of cases is truncated,
    # and a truncated case set reads exactly like full coverage unless it is
    # said out loud. ``run_analysis`` folds these into its warnings.
    notes: list = field(default_factory=list)

    def score(self, result) -> float:
        """This run's objective, evaluated on one of its surfaces."""
        return surface_score(result, self.objective)

    @property
    def critical(self) -> Optional[LEMResult]:
        """Most critical surface among the ADMISSIBLE ones.

        v0.1.32 — surfaces rejected by the post-analysis checks are kept
        in ``evaluations`` (search algorithms that steer on the factor of
        safety need them) but never reported as the critical surface. If
        every surface is inadmissible the checks are ignored rather than
        returning nothing, so the user always gets an answer plus the
        warning in ``inadmissible_count``.
        """
        valid = [r for r in self.evaluations if r.is_valid]
        if not valid:
            return None
        ok = [r for r in valid if getattr(r, "admissible", True)]
        pool = ok or valid
        best = min(pool, key=self.score)
        if self.objective != OBJECTIVE_FOS and math.isinf(self.score(best)):
            # Nothing has an answer under the active objective — every
            # surface failed to yield a Ky, say. Falling back to the factor
            # of safety would answer a different question in silence, so
            # there is no critical surface to report.
            return None
        return best

    @property
    def total_count(self) -> int:
        """Every surface the search GENERATED, valid or not.

        v0.1.83 — the honest denominator, and the reason it needs its own
        name: ``len(evaluations)`` is not it. A surface that could not be
        analysed has no ``LEMResult`` to store, so it never reaches that
        list, yet it was generated and the reference counts it. On the
        Ej_1 benchmark grid the two differ by 1697 of 4851.

        The reference documents the population exactly — (X intervals + 1)
        × (Y intervals + 1) × (Radius Increment + 1) — so this is a
        checkable identity, not a bookkeeping preference.
        """
        return self.valid_count + self.invalid_count

    @property
    def inadmissible_count(self) -> int:
        return sum(1 for r in self.evaluations
                   if r.is_valid and not getattr(r, "admissible", True))

    @property
    def analysed_count(self) -> int:
        """Surfaces that both converged AND survived the post-checks.

        v0.1.84 — the number to report to the user, and the reason it is
        not ``valid_count``: a surface screened out by the m-alpha or
        tensile check has a converged factor of safety, so it counts as
        valid, but it can never be the critical surface. With the m-alpha
        check off by default that gap was always zero; with it on, as the
        reference has it, the panel would have claimed 2966 valid
        surfaces while 64 of them were barred from ever being the answer.
        The reference makes the same choice: its report lists surfaces
        screened by error code -112 under "Number of Invalid Surfaces".
        """
        return max(0, self.valid_count - self.inadmissible_count)

    @property
    def min_fos(self) -> float:
        c = self.critical
        return c.fos if c else math.inf

    def valid(self) -> list[LEMResult]:
        return [r for r in self.evaluations if r.is_valid]

    def top_n(self, n: int = 10) -> list[LEMResult]:
        return sorted(self.valid(), key=self.score)[:n]


# ======================================================================
class BaseSearch(ABC):
    """Base class for search strategies."""

    def __init__(
        self,
        method: LEMMethod,
        num_slices: int = 30,
        min_area: float = 0.5,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        reject_tensile: bool = False,
        tensile_tolerance: float = 0.05,
        tensile_percent: float = 95.0,
        check_m_alpha: bool = True,
        min_elevation: Optional[float] = None,
        min_depth: Optional[float] = None,
        slope_limits: Optional[tuple] = None,
        optimize=None,
        optimize_seed: Optional[int] = None,
        seismic_analysis=None,
        focus_objects=None,
    ) -> None:
        self.method = method
        self.num_slices = num_slices
        self.min_area = min_area
        self.progress_cb = progress_cb
        # v0.1.102 — the two Surface Filters, applied in ``_best_of_masses``.
        # None means OFF, and it is the default so that a search built by
        # hand behaves as it always did.
        #
        # They were declared in SearchSettings, editable in the dialog and
        # saved to the .ogr since long before this, and NO search had ever
        # been told about either (anomaly A37-1). What that cost, on the
        # back-analysis problem of the XSTABL reference manual (1999), whose
        # statement asks for a minimum depth of 2 m to clear the shallow
        # face slides out of the way: the minimum landed on a 0.64 m skin,
        # factor 0.726, against the 0.764 published for the deep mechanism
        # (0.766 once the filter is honoured).
        # The user sets a filter, gets the identical number back, and
        # concludes there is no deep mechanism — which is rule 7's argument
        # in one sentence.
        self.min_elevation = min_elevation
        self.min_depth = min_depth
        # v0.1.118 — the Slope Limits, ``(x_left, x_right)`` or None for
        # automatic. Two distinct jobs, and only the first is done here:
        #
        # * FILTERING — a mass must daylight within them, for every search
        #   and every surface type. That is done once, in
        #   ``_best_of_masses``, for the same reason the two filters above
        #   are: every search reaches the engine through that method, so a
        #   filter placed anywhere else is one some door can walk around.
        # * GENERATION — the searches that build their candidates from the
        #   slope surface read ``self.slope_limits`` themselves. The
        #   reference exempts exactly one from this, the Block Search,
        #   whose vertices come from user-drawn objects instead.
        self.slope_limits = slope_limits
        # v0.1.129 — the focus objects, and the split is the same one the
        # Slope Limits describe just above, only the other way round:
        #
        # * FILTERING — every search asks ``_focus_rejects`` before it
        #   spends anything on a candidate. NOT in ``_best_of_masses``,
        #   where the other project filters live, and that is deliberate:
        #   by the time a circle reaches that method it has become the
        #   chords it was sliced into, and asking a chord approximation
        #   whether it is tangent to a line is not the question the user
        #   asked. See ``focus.py`` and the ``_chord_reference`` argument
        #   of v0.1.118. So the ask happens where the candidate is still
        #   the thing the search generated.
        # * GENERATION — nothing generates from them. The reference does
        #   (a Focus Point yields exactly one circle per slip centre, with
        #   the Radius Increment switched off), this engine has always
        #   filtered instead, and that difference is older than D33 and
        #   left alone here on purpose: changing it would move every
        #   circular row of the reference bank.
        self.focus_objects = list(focus_objects or ())
        # v0.1.24 — optional kinematic-admissibility filter (anomaly A3).
        # A physically acceptable limit-equilibrium mechanism requires
        # COMPRESSIVE interslice forces; a surface whose force field
        # needs substantial interslice TENSION is not a feasible
        # mechanism, and the reference documentation warns that such
        # surfaces yield a safety factor that is "usually too low".
        # Non-circular searches can generate them (e.g. a deep wedge
        # closed by a near-vertical rising segment), so this filter is
        # available for all searches. Default OFF to preserve existing
        # results; recommended ON for non-circular searches.
        # See Krahn (2003), "The limits of limit equilibrium analyses".
        self.reject_tensile = reject_tensile
        self.tensile_tolerance = tensile_tolerance
        # v0.1.32 — reference-style post-analysis checks (anomaly A3).
        # ``reject_tensile`` now maps onto the documented Tensile Stress
        # Check: negative effective normal stress on slice BASES, tested
        # AFTER the factor of safety has converged, over a percentage of
        # slices measured from the toe. Both default to off, as in the
        # reference, where tensile normal stresses are permitted unless
        # the user opts in.
        self.tensile_percent = tensile_percent
        # v0.1.89 — DEFAULT ON, matching ProjectSettings.advanced, which has
        # said True since v0.1.84. Until now the two disagreed, so the same
        # model gave two different answers depending on which door you came
        # in by: through build_search (interface, CLI, validation cases) the
        # check ran, and constructing a search directly — every test, every
        # script, examples/ — it did not.
        #
        # What that hid, found in v0.1.89 when nine test models stopped being
        # degenerate: with 10 m of foundation under the toe, Simulated
        # Annealing returned FoS 0.500 and Block Search 0.651 on this stable
        # slope, against a circular minimum of 1.1239. Both surfaces closed
        # with a near-vertical segment, where m_alpha goes NEGATIVE and
        # Bishop's formulation divides by it. With the check on: 1.187 and
        # 1.120, and the surfaces still reach 9.5 m below the toe — depth was
        # never the problem, the vertical closing segment was.
        #
        # The comment above, written in v0.1.24, names this exact mechanism
        # ("a deep wedge closed by a near-vertical rising segment") and says
        # the filter is "recommended ON for non-circular searches". It was
        # left off "to preserve existing results" — results that were only
        # stable because no test model had soil to dive into.
        #
        # NOTE the asymmetry, and it is deliberate: reject_tensile stays OFF
        # because the reference permits tensile normal stresses unless the
        # user opts in, while its reports DO filter on m_alpha by default and
        # count the rejects as error -112.
        self.check_m_alpha = check_m_alpha
        # v0.1.104 — Optimize Surfaces: an :class:`OptimizeSettings`, or
        # None for off. None is the default so that a search built by hand
        # behaves as it always did, and it is also what an unticked model
        # produces, so the two doors agree (the v0.1.89 lesson).
        self.optimize = optimize
        # Its own seed, drawn from the project's, because a walk seeded with
        # None would make an analysis unreproducible from the Random Numbers
        # page onwards — which is the promise v0.1.74 went and kept.
        self.optimize_seed = optimize_seed
        # v0.1.127 — a :class:`SeismicAnalysisSettings`, or None for the
        # ordinary factor-of-safety run. None is the default so that a
        # search built by hand behaves exactly as it always did, which is
        # the same contract ``optimize`` above signs.
        self.seismic_analysis = seismic_analysis
        self.objective = (seismic_analysis.objective()
                          if seismic_analysis is not None
                          else OBJECTIVE_FOS)

    # ------------------------------------------------------------------
    def score(self, result: Optional[LEMResult]) -> float:
        """The scalar this search minimises. Lower is more critical.

        Every comparison a search makes between two surfaces goes through
        here, so that "better" has one definition per run instead of one
        per algorithm. With the seismic modes off it returns the factor of
        safety and the searches behave exactly as they did.
        """
        return surface_score(result, self.objective)

    # ------------------------------------------------------------------
    def _is_admissible(self, result: Optional[LEMResult]) -> bool:
        """Reference-style post-analysis admissibility.

        Applied as a POST-FILTER on a converged result — never during the
        iteration — exactly as the reference specifies. Surfaces failing
        the Tensile Stress Check or the m-alpha check are discarded, and
        the reason is recorded on the result for reporting.
        """
        if result is None:
            return True
        if not (self.reject_tensile or self.check_m_alpha):
            return True
        try:
            from .checks import check_surface
            ok, reason = check_surface(
                result,
                tensile=self.reject_tensile,
                tensile_percent=self.tensile_percent,
                m_alpha=self.check_m_alpha,
            )
        except Exception:  # noqa: BLE001
            return True
        if not ok:
            result.admissible = False
            result.admissibility_note = reason or ""
        return ok

    # ------------------------------------------------------------------
    def _analyse(self, project: Project, surface, slices) -> LEMResult:
        """Solve one surface, and never let its arithmetic kill the run.

        Every search reaches the engine through this method —
        :meth:`evaluate_circle` and :meth:`evaluate_surface` are the only
        two doors into ``compute_fos``, and ``optimize`` and the
        probabilistic sampler come in by them as well — so this is the one
        place where the invariant can be stated once: a surface that cannot
        be analysed is counted and explained, it does not end the analysis.

        Two doors, one answer, since v0.1.101: on a CIRCLE the second door
        opens into the first, and both walk the sliding masses through
        :meth:`_best_of_masses`. They used to answer differently on the very
        same circle; see the note on :meth:`evaluate_surface`.

        ``ArithmeticError`` and NOT ``Exception``, deliberately. It covers
        ZeroDivisionError, OverflowError and FloatingPointError, the
        failures that belong to the numbers, while a TypeError or an
        AttributeError still raises loudly, because those are defects in the
        code and hiding one costs far more than it saves. This program has
        already paid for the wide version once: the blanket
        ``except Exception`` in the compute worker turned Slope Search's
        TypeError into a generic "Error" dialog with no results, in every
        release up to v0.1.77 (see the note in ``SlopeSearch.__init__``).

        The one ArithmeticError ever seen in practice — a mass lying
        entirely inside a material with no shear strength, 147 of the 4860
        circles of the problem-27 reference grid — is now answered by the
        methods themselves before any division happens. Reaching this
        handler therefore means something NEW, which is why the message
        carries the exception's own text instead of a fixed phrase.

        v0.1.108 — and it is where the rapid-drawdown guard goes, for the
        same "one place" argument, one level up: a project can ask for a
        drawdown and be handed a method that does not perform one, and the
        answer that comes back is the ordinary drained factor of safety
        with nothing to say it is not the drawdown one (anomaly A98-1,
        +63 % measured on the Appendix G circle). The check is a question
        about the pair, so it belongs where the pair meets.

        It RAISES rather than returning an invalid result, because it is
        not a fact about this surface — every surface of the run would come
        back the same way, and a search that reports "no valid surfaces"
        buries the cause in the invalid-surface report. ``RapidDrawdownError``
        is a ``RuntimeError``, so the handler below does not swallow it.

        Cost on the ordinary path is one attribute read per surface —
        ``rapid_drawdown`` is False — against a solve of a few
        milliseconds, which is the same order of magnitude the v0.1.65
        note settles by counting rather than by the stopwatch.
        """
        gap = drawdown_gap(project, self.method)
        if gap:
            raise RapidDrawdownError(gap)
        try:
            res = self.method.compute_fos(project, surface, slices)
        except ArithmeticError as exc:
            res = LEMResult(
                fos=math.nan,
                converged=False,
                iterations=0,
                method_id=self.method.METHOD_ID,
                surface=surface,
                slices=slices,
                error_message=f"Arithmetic failure: {exc}",
            )
        self._is_admissible(res)     # marks res.admissible in place
        self._solve_ky(project, surface, slices, res)
        return res

    # ------------------------------------------------------------------
    def _solve_ky(self, project, surface, slices, res) -> None:
        """Attach the critical seismic coefficient to a solved surface.

        Here and nowhere else, for the reason every other cross-cutting
        rule in this class is here: ``_analyse`` is the single door the
        seven searches, Optimize Surfaces and the probabilistic sampler
        all reach the engine through, so a Ky computed anywhere else is a
        Ky some door can walk around.

        It costs nothing when the modes are off — one attribute read — and
        about eight extra solves per surface when they are on. That is the
        price of the question, not of this implementation: the coefficient
        is defined by an equation the solver has to be run to evaluate.

        The slices are reused as they are. The slicer does not read the
        seismic coefficient, so they are the right slices for every trial
        value — see ``ogr_slip2d.yield_acceleration``.
        """
        cfg = self.seismic_analysis
        if cfg is None or not cfg.needs_ky:
            return
        if res is None or not res.is_valid:
            return
        from .yield_acceleration import critical_seismic_coefficient
        # ``res.fos`` is FS at the project's OWN horizontal coefficient,
        # which is FS(0) only when that coefficient is zero. Handing it to
        # the solver as the starting point of a scan over kh would be
        # comparing two different questions: a model carrying kh = 0.15
        # would have its scan anchored at the factor WITH the earthquake
        # and then walk kh from zero, so every bracket would be wrong and
        # a plausible Ky would come back. When the project applies a
        # coefficient of its own, the solver is left to evaluate FS(0)
        # itself — one extra solve, and the right question.
        seismic = getattr(project, "seismic", None)
        applied_kh = (float(getattr(seismic, "kh", 0.0) or 0.0)
                      if getattr(seismic, "enabled", False) else 0.0)
        out = critical_seismic_coefficient(
            self.method, project, surface, slices,
            target_fos=float(cfg.ky_target_fos),
            fos_initial=(res.fos if applied_kh == 0.0 else None))
        if res.details is None:
            res.details = {}
        res.details["ky"] = out.ky
        res.details["ky_fos"] = out.fos_at_ky
        if out.note:
            res.details["ky_note"] = out.note

    # ------------------------------------------------------------------
    def _weak_bands(self, project: Project):
        """The project's weak layers, cached for the length of a search.

        Cached under the SAME condition ``_bond_profiles`` uses and for the
        same reason: inside ``regions_frozen()`` the model does not move by
        contract, so building the list once is safe, and outside it the only
        caller is a tooltip. The list itself is cheap; what it saves is a walk
        over every boundary of the model for every trial surface of a grid.
        """
        cached = getattr(self, "_weak_bands_cache", None)
        frozen = getattr(project, "_regions_freeze_depth", 0)
        if cached is not None and frozen:
            return cached
        from .weak_layers import weak_layer_bands
        bands = weak_layer_bands(project)
        if frozen:
            self._weak_bands_cache = bands
        return bands

    def _note(self, line: str) -> None:
        """Record a line to be reported once, however often it is raised."""
        notes = getattr(self, "_pending_notes", None)
        if notes is None:
            notes = self._pending_notes = []
        if line not in notes:
            notes.append(line)

    def _base_angle_ok(self, project: Project, trial, slices) -> bool:
        """Reject a clipped surface whose base turns too steeply to solve.

        A near-vertical base makes the limit-equilibrium equations
        ill-conditioned: ``m_alpha = cos a (1 + tan a tan phi / F)`` collapses
        towards zero as the base approaches the vertical while the normal
        force it divides grows without bound, and every classical formulation
        assumes the base is a shear plane rather than a wall.

        SCOPED TO SURFACES A WEAK LAYER ACTUALLY CLIPPED, and that is a
        deliberate narrowing of what the reference does with the same setting.
        The reference applies its ceiling to every column; applying it here to
        every surface would change results in models that have no weak layers
        at all — including the published cases this project is validated
        against — and a feature is not allowed to move those. The steep base
        this ceiling exists for is the one a joint creates: where a layer
        simply stops, the surface drops back to the arc down a vertical step.
        """
        if not isinstance(trial, WeakLayerSurface):
            return True
        try:
            limit = float(project.settings.advanced.max_base_angle_deg)
        except (AttributeError, TypeError, ValueError):
            return True
        if not (0.0 < limit < 90.0):
            return True
        limit_rad = math.radians(limit)
        for sl in slices:
            if abs(sl.base_angle) > limit_rad:
                self._note(
                    f"A surface clipped by a weak layer was discarded: its "
                    f"steepest slice base is "
                    f"{math.degrees(abs(sl.base_angle)):.1f} deg, past the "
                    f"{limit:.0f} deg ceiling in Project Settings > Advanced."
                )
                return False
        return True

    # ------------------------------------------------------------------
    def _focus_rejects(self, candidate) -> bool:
        """Whether the focus objects rule this candidate out.

        v0.1.129, defect D33. One dispatcher, shared by every search, and
        it asks the predicate that MATCHES WHAT THE SEARCH GENERATED: a
        circle is asked about its centre and radius, a piece-wise linear
        surface about its vertices. The two are not interchangeable — a
        circle re-tested as its own chord approximation answers a
        different question — so the choice is made here once instead of
        by seven callers who could each choose differently.

        ``candidate`` may be a :class:`SlipCircle`, a :class:`SlipSurface`
        or a bare sequence of ``(x, y)``. Returns False with no work at
        all when no focus object is defined, which is the common case.
        """
        if not self.focus_objects:
            return False
        from .focus import accepts_surface as _accepts_surface

        radius = getattr(candidate, "radius", None)
        if radius is not None:
            return self._focus_rejects_circle(
                candidate.centre_x, candidate.centre_y, radius)
        polyline = getattr(candidate, "polyline", None)
        if polyline is not None:
            pts = [(v.x, v.y) for v in polyline.vertices]
        else:
            pts = [(float(p[0]), float(p[1])) for p in candidate]
        return not _accepts_surface(self.focus_objects, pts)

    def _focus_rejects_circle(self, cx: float, cy: float, r: float) -> bool:
        """:meth:`_focus_rejects` for a circle not yet built into one.

        The circle generators ask through here so that a rejected circle
        never costs a :class:`SlipCircle` construction — which carries a
        ``uuid4`` — on top of the two distance calculations that rejected
        it. That ordering is the whole argument for focusing being worth
        using; see ``focus.py``.
        """
        if not self.focus_objects:
            return False
        from .focus import accepts as _accepts_circle
        return not _accepts_circle(self.focus_objects, cx, cy, r)

    def _best_of_masses(self, project: Project, candidates) -> Optional[LEMResult]:
        """The lowest-factor mass among several DISJOINT candidates.

        A surface that crosses the ground more than twice does not define
        one failure mechanism but several separate ones, and the critical
        mechanism is the one with the lowest factor of safety. Choosing
        among them therefore belongs to the engine and not to the caller,
        who has no way of knowing there was more than one.

        Shared by the two public doors — :meth:`evaluate_circle` and
        :meth:`evaluate_surface` — precisely so they cannot drift apart
        again. Until v0.1.101 this loop existed twice: once here, walking
        the masses, and once inside ``evaluate_surface`` with the walk
        missing, so the same circle got two different answers depending on
        which method you called.

        A candidate that cannot be sliced, that resolves to fewer than
        three slices or that fails one of the Surface Filters is skipped,
        not returned: it is not an answer about a shorter surface, it is no
        answer at all. If NO candidate survives the result is ``None``,
        which is what both doors have always returned in that case. Every
        search counts that ``None`` as one invalid surface, so filtering
        moves surfaces from valid to invalid and NEVER moves the total —
        the denominator a user compares between runs stays put (v0.1.83).

        v0.1.102 — this is where the three Surface Filters live, and there
        is exactly one of it. Both public doors pass through here, the six
        searches reach the engine through those doors, and so do Optimize
        Surfaces and the probabilistic sampler; a filter placed anywhere
        else would be a filter some door could walk around.

        Ordered by what each one costs. Minimum Elevation is pure geometry
        and is asked before slicing; Minimum Depth needs the slices by
        definition, so it is asked after them and before the solve.
        """
        best: Optional[LEMResult] = None
        for mass in candidates:
            # v0.1.121 — one mass becomes one surface per weak-layer case, and
            # the worst of them is the answer. It goes HERE, wrapped around the
            # loop that already picks the worst of several disjoint masses,
            # because this method is the single door every search reaches the
            # engine through — the same argument v0.1.102 used for the Surface
            # Filters and v0.1.118 for the Slope Limits. A model with no weak
            # layers yields the mass itself, unchanged and not wrapped, so its
            # numbers cannot move.
            for trial in self._weak_layer_cases(project, mass):
                # Minimum Elevation — the lowest point of the SURFACE (not of
                # the mass) may not go below the user's elevation.
                if self.min_elevation is not None:
                    y_low = lowest_elevation(trial)
                    if y_low is not None and y_low < self.min_elevation:
                        continue
                slices = slice_surface(project, trial, num_slices=self.num_slices)
                if slices is None or len(slices) < 3:
                    continue
                # Slope Limits — both ends of the MASS must daylight inside
                # them. Asked here, after slicing, because that is the first
                # moment the extent is known for a circle: its own endpoints
                # are wherever the arc meets the ground, and on an arc that
                # cuts the ground more than twice each mass has its own pair.
                # A polyline knows its extent earlier, but answering the same
                # question in two places is how the two answers drift apart.
                if self.slope_limits is not None:
                    sl_lo, sl_hi = sorted(self.slope_limits)
                    tol = 1e-9 * max(abs(sl_hi - sl_lo), 1.0)
                    if (slices[0].base_x_left < sl_lo - tol
                            or slices[-1].base_x_right > sl_hi + tol):
                        continue
                # Filter by minimum "area" (here approximated as Σ w_i · h_i)
                area = sum(s.width * max(s.height, 0.0) for s in slices)
                if area < self.min_area:
                    continue
                # Minimum Depth — the MAXIMUM slice height, measured vertically
                # from the slip surface to the ground surface, must EXCEED the
                # value; this is the filter for shallow surfaces. Maximum and
                # not mean, and not per slice: a deep mechanism is deep
                # somewhere, and one thin slice at the toe does not make it
                # shallow. ``Slice.height`` is already that vertical distance,
                # taken to the mean ground elevation over the slice, which is
                # the same column its weight is computed from.
                if self.min_depth is not None:
                    if max(s.height for s in slices) <= self.min_depth:
                        continue
                # v0.1.121 — the base-angle ceiling, asked after slicing
                # because a base angle is a property of a slice.
                if not self._base_angle_ok(project, trial, slices):
                    continue
                res = self._analyse(project, trial, slices)
                if res is None:
                    continue
                if best is None:
                    best = res
                elif res.is_valid and (not best.is_valid
                                       or self.score(res) < self.score(best)):
                    best = res
        return best

    # ------------------------------------------------------------------
    def _weak_layer_cases(self, project: Project, mass):
        """The surfaces to analyse in place of one sliding mass.

        Yields the mass ITSELF when no weak layer reaches it — the same
        object, not a wrapper around it — which is what keeps every model
        without weak layers answering bit for bit as it did before.

        The two policies are read straight off the project rather than
        copied into the search when it is built. That is on purpose: the
        settings that were mirrored into search objects are exactly the ones
        that spent versions being edited in the dialog and read by nobody
        (D07b, D08), and the cure was to have the name the user sees be the
        name the engine consumes.
        """
        bands = self._weak_bands(project)
        if not bands:
            yield mass
            return
        from .weak_layers import weak_layer_variants
        search = getattr(getattr(project, "settings", None), "search", None)
        handling = getattr(search, "weak_layer_handling",
                           WeakLayerHandling.HIGHEST.value)
        max_log2 = getattr(search, "weak_layer_max_cases_log2", 6)
        yield from weak_layer_variants(
            mass, bands, handling=handling, max_cases_log2=max_log2,
            note_cb=self._note,
        )

    # ------------------------------------------------------------------
    def evaluate_circle(
        self, project: Project, circle: SlipCircle
    ) -> Optional[LEMResult]:
        # v0.1.11 — Early-skip: bbox-only checks before doing the
        # full slicing pass. We reject circles that obviously cannot
        # produce a valid failure surface.
        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:
            xmin = ymin = xmax = ymax = None
        if xmin is not None:
            cx, cy, R = circle.centre_x, circle.centre_y, circle.radius
            # Skip 1: circle bbox does not overlap model bbox at all
            if (cx + R < xmin or cx - R > xmax
                    or cy + R < ymin or cy - R > ymax):
                return None
            # Skip 2: circle is so high above the model that it
            # cannot intersect the ground (centre well above bbox top
            # AND lower edge above bbox top → no possible intersection)
            if cy - R > ymax:
                return None
            # Skip 3: circle so deep below the bottom that lower edge
            # is more than radius below the model bottom (non-physical)
            if cy + R < ymin:
                return None

        # v0.1.84 — a circle that crosses the ground more than twice
        # defines several DISJOINT sliding masses, and the critical
        # mechanism is the one with the lowest factor of safety. Until now
        # the first mass from the left was taken and the rest discarded
        # unseen; on the Ej_2 reference model that resolved Slide's own
        # critical circle onto a 62 m² lens of level ground beyond the toe
        # (driving moment ≈ 0, so no factor of safety at all) instead of
        # the 184 m² slope failure at FoS = 1.155, and the true critical
        # circle was thrown away as invalid.
        best = self._best_of_masses(
            project, self._candidate_surfaces(project, circle))
        # v0.1.131 — the caller's circle comes out EXACTLY as it went in,
        # and that is a rule rather than tidiness. Until now this method
        # wrote the analysed extent back onto the argument "so the drawing
        # and the number agree", and by v0.1.130 nothing drew from that
        # object any more: the canvas, the exporters and the reports all
        # read ``result.surface``, which carries the analysed mass with its
        # endpoints, its cracks and its wall. The write fed nobody and
        # poisoned the NEXT call on the same object.
        #
        # What it cost, measured on verification problem 22 (Fredlund and
        # Krahn 1977) with Composite Surfaces on: the first call answers for
        # the clipped surface, Bishop 1.3809 against the paper's 1.377; the
        # second call on the SAME object answers 1.9806, the unclipped arc
        # running five feet below the floor of the model. That is defect
        # D15 exactly as v0.1.111 closed it, coming back through the
        # endpoints written here — because a circle that arrives with its
        # endpoints set takes the "named mass" branch of
        # ``_candidate_surfaces`` and is never re-resolved.
        #
        # And it was not a masking defect, which is what its report said:
        # ``run_global_minimum`` and ``run_sensitivity`` rebuild ONE surface
        # and evaluate it on every sample, so a probabilistic run of that
        # model reported 1.3809 for the first sample and 1.9806 for all the
        # rest — five identical samples, no perturbation at all, four wrong.
        return best

    # ------------------------------------------------------------------
    def _candidate_surfaces(self, project: Project, circle: SlipCircle):
        """Yield every sliding mass of ``circle`` that is worth analysing.

        Each is a fresh :class:`SlipCircle` with its endpoints already
        resolved and its reverse curvature already treated, so the caller
        only has to slice and solve. Fresh in every case, the caller's own
        object included: nothing yielded here is the argument, so no caller
        can be left holding a circle this method changed (v0.1.131, D36).

        A circle that ARRIVES with its endpoints set names one mass, and
        only that mass is yielded — no walk over the chords, and reverse
        curvature not revisited, because whatever set those endpoints ran
        already. It still gets the composite clipping and the containment
        rule, which is what makes it the same kind of surface as a mass
        this method resolved itself.

        Masses that leave the soil region are dropped, which is the
        reference's documented behaviour for non-composite circular
        surfaces and what its report counts as error −103. Containment is
        judged on the surface as finally analysed — after any
        reverse-curvature tension crack has moved an endpoint — because
        that is the surface the factor of safety belongs to.

        With Composite Surfaces enabled the mass is CLIPPED to the floor of
        the model instead of being dropped, which is what that option
        means and what it is for: a bedrock horizon is modelled by shaping
        the lower edge of the External Boundary, and a circular search then
        follows it.

        v0.1.111 — until now the option only skipped the rejection, so the
        escaping circle was analysed WHOLE, with slices whose bases stood
        several feet below the model and whose weight came from soil that
        does not exist. On the published circle of verification problem 22
        (Fredlund and Krahn 1977) the arc reached y = 10 against a floor at
        y = 15, only 2 of its 30 slices sat in the weak layer that governs
        the problem, and Bishop came out at 1.9806 against a published
        1.377 to 1.382: +43 %, on the unsafe side. The docstring of this
        very method said the opposite of what the code did — it promised
        the circle would "follow the boundary instead of being rejected by
        it" — which is how the defect survived the reading that found it
        twice.
        """
        from ogr_core.geometry import ground_surface
        from .slicer import (
            _reverse_curvature_mode, apply_tension_crack_truncation,
        )
        from .surface import compose_with_bedrock, leaves_soil_region

        external = project.external_boundary()
        if external is None:
            return
        try:
            composite = bool(project.settings.search.composite_surfaces)
        except AttributeError:
            composite = False
        ext_verts = list(external.polyline.vertices)

        if circle.x_left is not None and circle.x_right is not None:
            # Endpoints that ARRIVE set NAME one sliding mass, and that is a
            # feature the program uses: it is how a caller asks about a mass
            # other than the critical one, so they are honoured and the walk
            # over the chords is skipped. What they may not be is a way past
            # the rules that decide whether the surface exists at all.
            #
            # v0.1.131 — until now they were. This branch handed the circle
            # straight back, so a named mass got neither the composite
            # clipping nor the containment rule: on verification problem 22
            # a pre-resolved circle measured 1.9806 against the 1.3809 of
            # the clipped one, and with the option OFF the same circle —
            # which ``leaves_soil_region`` refuses outright, ``None`` — came
            # back with a factor of safety as soon as its endpoints were
            # set, weighing five feet of soil the model does not contain.
            # That is the reference's error -103 through the back door.
            #
            # On a COPY, and not on the caller's object: ``slice_surface``
            # writes the tension-crack truncation back onto whatever it is
            # handed, so yielding the argument itself would leak the very
            # mutation ``evaluate_circle`` above stopped making.
            #
            # Reverse curvature is deliberately NOT re-applied, for the
            # reason v0.1.82 gives in the slicer: a cached pair of endpoints
            # is never re-cracked, because whatever moved it ran already.
            named = replace(
                circle, tension_cracks=list(circle.tension_cracks or []))
            if composite:
                named = compose_with_bedrock(named, external)
            elif leaves_soil_region(named, ext_verts,
                                    named.x_left, named.x_right):
                return
            yield named
            return

        ground = ground_surface(external)
        chords = circle.candidate_chords(ground)
        if not chords:
            return
        mode = _reverse_curvature_mode(project)

        for x_l, x_r in chords:
            trial = SlipCircle(centre_x=circle.centre_x,
                               centre_y=circle.centre_y,
                               radius=circle.radius)
            trial.x_left, trial.x_right = x_l, x_r
            if not trial.apply_reverse_curvature(ground, mode=mode):
                continue
            # v0.1.109 — the user's Tension Crack boundary, applied
            # BEFORE containment is judged. ``slice_surface`` would
            # truncate this trial anyway, so what this call buys is the
            # order: containment is judged "on the surface as finally
            # analysed", exactly as the docstring above promises, and a
            # trial lying entirely inside the crack zone is dropped here
            # instead of being sliced first and refused after.
            lim = apply_tension_crack_truncation(
                project, trial, ground, trial.x_left, trial.x_right)
            if lim is None:
                continue        # entirely within the tension crack zone
            trial.x_left, trial.x_right = lim
            if composite:
                # Clipping REPLACES the containment rule rather than
                # joining it: a clipped surface is inside the soil by
                # construction, so there is nothing left for
                # ``leaves_soil_region`` to reject. A circle that never
                # dipped comes back unchanged, which is what keeps every
                # model without escaping surfaces answering exactly as it
                # did before.
                trial = compose_with_bedrock(trial, external)
            elif leaves_soil_region(
                    trial, ext_verts, trial.x_left, trial.x_right):
                continue
            yield trial

    # ------------------------------------------------------------------
    def evaluate_surface(
        self, project: Project, surface
    ) -> Optional[LEMResult]:
        """Evaluate any SurfaceProtocol (circular or non-circular).

        v0.1.101 — a CIRCLE is handed to :meth:`evaluate_circle`, and that
        is not a convenience. Until now this door sliced the circle
        directly, and ``slice_surface`` resolves an unresolved circle onto
        the FIRST sliding mass from the left, which on a circle that
        crosses the ground more than twice is whichever mass happens to
        come first — not the critical one. The walk over the masses was
        added to ``evaluate_circle`` in v0.1.84 and this door was left
        outside it, so the same circle gave two different answers
        depending on which public method you called.

        What that cost, on the reference circle of verification problem 27
        (Malkawi & Sarma 2001, after XSTABL v5): the arc grazes the toe
        vertex (38, 63) from 0.0054 ft above it, so it cuts the ground
        FOUR times and defines a 0.9 ft lens between x = 17.62 and 37.95
        as well as the real 22 ft mechanism between x = 38.01 and 169.89.
        This door answered for the lens — Bishop 34.32 against 1.4071, a
        factor of 24 — with no warning of any kind. Janbu corrected,
        34.53 against 1.4026; Spencer and GLE, 34.20 against 1.4071.

        A POLYLINE needs no such walk, and gets none. Its own vertices fix
        where it runs, so a polyline crossing the ground more than twice
        has to RISE ABOVE it in between — and a slice whose base sits above
        its own top is not a mass to choose between, it is a surface the
        slicer refuses whole since v0.1.100 (see the note in
        ``slice_surface``). Measured on the same problem-27 geometry: a
        vertex lifted 0.05 ft over the ground is already enough to have the
        polyline discarded.

        The judgement is made at the slice boundaries, so a poke-through
        narrower than the boundary spacing is not seen as one — but neither
        is it analysed: the surface that gets sliced is the chord polygon
        through the vertices, which runs below the ground, and the factor
        returned belongs to that surface. It is a different mechanism from
        the circle, not a wrong answer about it.
        """
        if isinstance(surface, SlipCircle):
            return self.evaluate_circle(project, surface)
        # v0.1.126 — and a polyline gets the containment rule a circle has
        # had since v0.1.84. It never did, and every surface an
        # optimisation produces is a polyline: on verification problem 103
        # the walk took the critical surface to y = -4.83 under a model
        # whose floor is y = 0 and came back with 1.0902 where the clipped
        # surface gives 1.2676. Outside the regions the slicer falls back
        # on the FIRST material, which on that model is the weakest of the
        # two, so leaving the model was rewarded. Anomaly D48.
        if self._leaves_soil(project, surface):
            return None
        return self._best_of_masses(project, (surface,))

    def _leaves_soil(self, project: Project, surface) -> bool:
        """Whether a non-circular surface dips below the External."""
        from ogr_core.geometry import BoundaryType
        from .surface import polyline_leaves_soil

        pl = getattr(surface, "polyline", None)
        verts = list(getattr(pl, "vertices", ()) or ())
        if not verts:
            return False
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                return polyline_leaves_soil(verts, list(b.polyline.vertices))
        return False

    # ------------------------------------------------------------------
    def run(self, project: Project) -> SearchResult:
        """Run the search with the project's region caches frozen.

        v0.1.93 — a template method purely so the freeze cannot be
        forgotten by one search or one caller. Resolving the material at a
        point revalidates the regions cache by rebuilding a signature over
        every boundary vertex, about twice per slice; on the Ej_2 reference
        grid that was 41 % of the run, for a model that by contract does
        not change while it is being analysed.

        It is here rather than in ``analysis_runner.build_search`` for the
        reason v0.1.89 records above: when the interface and direct
        construction come in by different doors, the two end up behaving
        differently. Tests, scripts and ``examples/`` all build their
        search by hand.

        v0.1.104 — and it is why Optimize Surfaces attaches HERE too. The
        option is a post-process over the population the search produced,
        so every one of the six searches would otherwise have to remember
        to run it, and five of them would be right until the sixth was
        written. The freeze covers it as well, which it must: the walk
        evaluates thousands of surfaces against the same unchanging model.
        """
        self._weak_bands_cache = None
        self._pending_notes = []
        with project.regions_frozen():
            result = self._run(project)
            if self.optimize is not None and self.optimize.enabled:
                self._optimize_result(project, result)
            # v0.1.121 — anything the run decided it had to say. Attached
            # after the optimisation so a note raised while optimising is
            # carried too.
            for line in getattr(self, "_pending_notes", ()):
                if line not in result.notes:
                    result.notes.append(line)
            return result

    # ------------------------------------------------------------------
    def _optimize_result(self, project: Project, result) -> None:
        """Run Optimize Surfaces over what the search found.

        The reference documents the behaviour exactly, and two sentences of
        it decide everything here: "this option will perform the
        optimization on EVERY SURFACE generated by the search", and "the
        only result which will be displayed [...] is the (new) optimized
        Global Minimum surface. [...] All intermediate slip surfaces
        generated by the optimization are NOT stored. [...] the original
        surfaces which existed BEFORE the optimization will still be
        displayed."

        So: the search's own population is left untouched, every selected
        surface is walked, and only the BEST of the walks is added. Whether
        a surface is walked as it is generated or afterwards is not
        observable in the answer — only the minimum survives either way -
        so it is done afterwards, where the selection can be made once.

        CIRCLES ARE SKIPPED, and so is anything else without a polyline of
        its own. A circle has three degrees of freedom and no vertices to
        move, and the reference offers this option for Surface Type =
        Non-Circular only. Skipping rather than refusing matters because a
        non-circular search can still return a circular mass.
        """
        from .optimize import optimize_surface

        opts = self.optimize
        # v0.1.126 — a search that reports SEVERAL minima optimises each
        # of them and keeps each. Folding them into the ordinary path
        # would keep only the best walk, which is exactly the information
        # a multimodal search exists to produce.
        if getattr(result, "minima", None):
            self._optimize_each_minimum(project, result)
            return
        targets = self._surfaces_to_optimize(result)
        if not targets:
            return

        # EVERY walk gets the SAME seed, and that is a decision worth the
        # three lines it takes to justify. The obvious alternative — draw a
        # sub-seed per surface from one generator - makes a walk's random
        # stream depend on how many surfaces happened to be selected before
        # it, so the walk that starts from the global minimum is a
        # different walk under "All" than under "Global Minimum". Measured
        # on a 120-surface Block Search: "All" then came back with 1.1229
        # against Global Minimum's 1.1129, WORSE for doing strictly more
        # work, and nothing said so. Sharing the seed makes the wider
        # choice contain the narrower one, so "All" can never lose to
        # "Global Minimum". The walks do not collapse onto each other:
        # each starts from a different surface with a different vertex
        # count and a different shuffle order.
        walk = replace(opts, seed=self.optimize_seed)
        best = None
        for i, start in enumerate(targets):
            # Reported BEFORE the guards below, so a walk that comes back
            # unusable still advances the bar. With "All" this loop is the
            # bulk of the run, and a bar that stalls on the failures reads
            # as a hung analysis.
            if self.progress_cb is not None and len(targets) > 1:
                self.progress_cb(i + 1, len(targets))
            _surface, res, _rep = optimize_surface(
                project, self, start.surface, walk)
            if res is None or not res.is_valid:
                continue
            if not getattr(res, "admissible", True):
                continue
            if best is None or self.score(res) < self.score(best):
                best = res

        if best is None:
            return
        # Only worth reporting when it beat what the search found: an
        # optimisation that ends where it started has produced no new
        # surface, and adding one would inflate the count for nothing.
        critical = result.critical
        if critical is not None and self.score(best) >= self.score(critical):
            return
        result.optimized = best
        result.evaluations.append(best)
        result.valid_count += 1

    def _optimize_each_minimum(self, project: Project, result) -> None:
        """Walk every reported minimum, and keep every walk.

        The ordinary path keeps the single best walk because there is a
        single answer to improve. Here each minimum is a different
        mechanism, so a walk that lowers one of them says nothing about
        the others and may not replace them.

        A minimum found by the swarm is a CIRCLE, and the ordinary path
        skips circles on the grounds that they have no vertices to move.
        That is right for a circular search, whose whole answer is a
        circle; it is wrong here, because the reference's own division of
        labour is that the swarm finds circles and the optimisation
        reshapes them. So a circle is discretised onto its own arc first
        — onto ``densify_to`` points, which are ON the circle rather than
        the chord polygon a coarser sampling would give.
        """
        from .optimize import optimize_surface

        opts = replace(self.optimize, seed=self.optimize_seed)
        kept = []
        improved = None
        for i, r in enumerate(result.minima):
            if self.progress_cb is not None and len(result.minima) > 1:
                self.progress_cb(i + 1, len(result.minima))
            start = self._as_optimisable(r.surface, opts.densify_to)
            keep = r
            if start is not None:
                _s, res, _rep = optimize_surface(project, self, start, opts)
                if (res is not None and res.is_valid
                        and getattr(res, "admissible", True)
                        and self.score(res) < self.score(r)):
                    result.evaluations.append(res)
                    result.valid_count += 1
                    keep = res
                    if improved is None or self.score(res) < self.score(improved):
                        improved = res
            kept.append(keep)
        result.minima = sorted(kept, key=self.score)
        # ``optimized`` means "the answer came from the walk, not the
        # search", so it is only set when the walk actually produced the
        # global minimum.
        if improved is not None and result.minima \
                and result.minima[0] is improved:
            result.optimized = improved

    @staticmethod
    def _as_optimisable(surface, n_points: int):
        """A surface the random walk can move, or None.

        A polyline is already one. A circle becomes ``n_points`` samples
        of its own arc between the endpoints it was resolved onto —
        points ON the circle, so the starting surface is the circle to
        within the sampling and not a coarser polygon inscribed in it.
        """
        if getattr(surface, "polyline", None) is not None:
            return surface
        if not isinstance(surface, SlipCircle):
            return None
        x0 = getattr(surface, "x_left", None)
        x1 = getattr(surface, "x_right", None)
        if x0 is None or x1 is None or not (x1 > x0):
            return None
        from ogr_core.geometry import Polyline, Vertex
        from .surface import SlipSurface

        n = max(3, int(n_points))
        cx, cy, r = surface.centre_x, surface.centre_y, surface.radius
        pts = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            d = r * r - (x - cx) ** 2
            if d < 0.0:
                return None
            pts.append(Vertex(x, cy - math.sqrt(d)))
        return SlipSurface(polyline=Polyline(vertices=pts, closed=False))

    def _surfaces_to_optimize(self, result) -> list:
        """The *Surfaces to Optimize* group, as a list of results.

        Global Minimum, All, or Factor of Safety Less Than — the three
        exclusive choices of the reference's settings dialog. Anything
        inadmissible or without a polyline is dropped here rather than
        inside the walk, so the cost of the choice is visible in one place.
        """
        opts = self.optimize
        target = getattr(opts, "target", "global_minimum")
        if target == "all":
            pool = [r for r in result.evaluations if r.is_valid]
        elif target == "fos_less_than":
            pool = [r for r in result.evaluations
                    if r.is_valid and r.fos < opts.fos_threshold]
        else:
            crit = result.critical
            pool = [crit] if crit is not None else []
        return [r for r in pool
                if getattr(r, "admissible", True)
                and getattr(getattr(r, "surface", None), "polyline", None)
                is not None]

    @abstractmethod
    def _run(self, project: Project) -> SearchResult: ...


# ======================================================================
# Parallel grid evaluation (v0.1.97)
#
# The circles of a Grid Search are INDEPENDENT: each one is sliced and
# solved from the project alone, nothing is carried between them, and
# ``regions_frozen`` already guarantees by contract that the project does
# not change while it is analysed. So splitting them across processes
# cannot change a result — and the test that guards this demands
# BIT-IDENTICAL output, not agreement to a tolerance.
#
# Processes, not threads: every inner loop here is pure Python, so the GIL
# would serialise them straight back.
#
# Only Grid Search is parallel so far. The random searches (Simulated
# Annealing, Path, Block) would need their seed derived per batch to keep
# the reproducibility promise of v0.1.74, and Auto Refine feeds each
# iteration from the previous one. Saying so is cheaper than letting a
# user wonder why one search got faster and another did not.

#: Below this many circles the process pool costs more than it saves. On
#: Windows every worker re-imports the package, which is most of the
#: ~0.5 s startup, so the floor is deliberately generous.
_PARALLEL_MIN_CIRCLES = 400

#: More workers than this and the per-process import cost and the parent's
#: deserialisation start to dominate. Measured, not guessed: see the
#: changelog for v0.1.97.
_MAX_WORKERS = 8


def _worker_count(project, n_circles: int) -> int:
    """How many processes this run should use. 1 means "stay sequential".

    Two controls, both on the Project Settings page:

    * ``parallel_search`` — off means off, on every model and every size.
      A user who wants the machine left alone must be able to say so once
      and have it stick.
    * ``parallel_cpu_percent`` — the share of the logical processors the
      search may occupy. It rounds DOWN to a whole process and never below
      one, so 1 % is "as little as possible", not "none": switching the
      feature off is the checkbox's job, and a percentage that silently
      meant off would be a second way to say the same thing.

    Independently of both, a small search stays in-process: below
    ``_PARALLEL_MIN_CIRCLES`` the pool costs more than it saves, and that
    is what keeps a 25-circle test from starting eight interpreters.
    """
    import os

    adv = getattr(getattr(project, "settings", None), "advanced", None)
    if not getattr(adv, "parallel_search", True):
        return 1
    if n_circles < _PARALLEL_MIN_CIRCLES:
        return 1
    try:
        pct = int(getattr(adv, "parallel_cpu_percent", 50))
    except (TypeError, ValueError):
        pct = 50
    pct = max(1, min(100, pct))
    total = os.cpu_count() or 1
    return max(1, min(_MAX_WORKERS, int(total * pct / 100)))


def _grid_batch(payload):
    """Worker entry point. Must stay importable at module level.

    Returns the partial :class:`SearchResult` for one contiguous run of
    grid centres.
    """
    search, project, centres, done_before, total = payload
    with project.regions_frozen():
        return search._run_centres(project, centres, done_before, total)


def _parallel_grid_run(search, project, centres, workers):
    """Evaluate ``centres`` across processes, or return None to fall back.

    Returning None rather than raising is deliberate: a machine that
    cannot start a process pool — a frozen build, a sandbox, a platform
    without fork or spawn — must still compute the right answer, just
    slower. A failure to parallelise is not a failure to analyse.
    """
    from concurrent.futures import ProcessPoolExecutor

    n = len(centres)
    if n < workers:
        return None
    # MANY MORE BATCHES THAN WORKERS, and that is the whole trick.
    #
    # One batch per worker looks natural and measured badly: the cost of a
    # grid centre varies by more than an order of magnitude — centres over
    # the slope generate circles that slice and solve, centres far from it
    # are rejected by the bounding-box test almost for free — and the
    # visiting order is column by column, so contiguous batches hand one
    # worker several expensive columns and another several cheap ones.
    # Measured on the Ej_2 grid with Lowe-Karafiath: one batch per worker
    # gave x1.85 on 7 workers, which is most of the gain thrown away
    # waiting for the slowest batch.
    #
    # Splitting finer lets the pool schedule dynamically. ``map`` still
    # returns results in the order the batches were submitted, so the
    # merged ``evaluations`` list stays byte-identical to the sequential
    # one — the ordering guarantee does not depend on which worker got
    # what, only on the batches being contiguous and reassembled in order.
    n_batches = min(n, workers * 8)
    size, extra = divmod(n, n_batches)
    batches, start = [], 0
    for i in range(n_batches):
        stop = start + size + (1 if i < extra else 0)
        batches.append((start, stop))
        start = stop

    # ``progress_cb`` is very often a bound Qt signal or a closure, and
    # neither survives pickling. The callback belongs to the parent
    # anyway, so it is stripped for the trip and restored afterwards.
    cb = search.progress_cb
    search.progress_cb = None
    try:
        payloads = [(search, project, centres[a:b], a, n)
                    for a, b in batches if b > a]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parts = list(pool.map(_grid_batch, payloads))
    except Exception:  # noqa: BLE001 - see the docstring
        return None
    finally:
        search.progress_cb = cb

    if cb is not None:
        cb(n, n)

    merged = SearchResult(method_id=search.method.METHOD_ID,
                          objective=search.objective)
    for part in parts:
        merged.evaluations.extend(part.evaluations)
        merged.valid_count += part.valid_count
        merged.invalid_count += part.invalid_count
        merged.attempts += part.attempts
    return merged


# ======================================================================
class GridSearch(BaseSearch):
    """Grid Search (circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm:

    1. A rectangular grid of slip-circle CENTRES is defined (Auto Grid
       or Add Grid). With ``grid_nx`` × ``grid_ny`` intervals there are
       (grid_nx+1)·(grid_ny+1) centres.
    2. For each centre, the **Slope Limits** determine the relevant
       "slope surface" (the segments of the External between the
       limits). Suitable MINIMUM and MAXIMUM radii are computed from the
       distances between the centre and that slope surface, so every
       generated circle actually intersects the slope.
    3. The **Radius Increment** is the NUMBER OF INTERVALS between the
       minimum and maximum radius; the number of circles per centre is
       therefore (Radius Increment + 1).

    The previous implementation used ``radius_increment`` as a metric
    step size and swept from a fixed minimum to the bbox diagonal,
    generating large numbers of useless circles and missing the
    per-centre radius bracketing. This version matches Slide.
    """

    def __init__(
        self,
        method: LEMMethod,
        grid_x: tuple[float, float] | None = None,
        grid_y: tuple[float, float] | None = None,
        grid_nx: int = 10,
        grid_ny: int = 10,
        radius_increment: float = 10.0,
        # v0.1.88 — was 2.0. The reference has no minimum-radius control at
        # all, so any non-zero default made the out-of-the-box sampling
        # differ from it at every centre whose nearest ground point is
        # closer than that. Kept as an option because excluding tiny
        # circles is a legitimate thing to want; zero by default because
        # reproducing the reference is what the default is for.
        min_radius: float = 0.0,
        num_slices: int = 30,
        min_area: float = 0.5,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        **legacy_kwargs,
    ) -> None:
        # v0.1.129 — ``focus_objects`` used to be this search's OWN named
        # argument, and it was the only search that ever received one. It
        # now travels through ``_base_kwargs`` like every other project
        # setting, so a caller passing it positionally still works and
        # every other search gets it too. Defect D33.
        super().__init__(
            method, num_slices, min_area, progress_cb,
            **_base_kwargs(legacy_kwargs),
        )
        self.grid_x = grid_x
        self.grid_y = grid_y
        # The grid actually swept, filled in by ``_centres``. None until
        # the search has run, because with grid_x = None it is not known
        # before then.
        self.grid_x_used = None
        self.grid_y_used = None
        self.grid_nx = max(2, grid_nx)
        self.grid_ny = max(2, grid_ny)
        # radius_increment is the NUMBER OF INTERVALS (Slide convention).
        # Accept floats for back-compat but use as an integer count.
        self.radius_increment = max(1, int(round(radius_increment)))
        self.min_radius = min_radius

    # ------------------------------------------------------------------
    def _auto_grid(self, project: Project) -> tuple[tuple[float, float], tuple[float, float]]:
        xmin, ymin, xmax, ymax = project.bounding_box()
        dx = xmax - xmin
        dy = ymax - ymin
        gx = (xmin + 0.2 * dx, xmax - 0.2 * dx)
        gy = (ymax, ymax + 0.8 * dy)  # above the ground
        return gx, gy

    # ------------------------------------------------------------------
    def _slope_surface(self, project):
        """The ground profile between the Slope Limits, **ends included**.

        v0.1.88 — the clip now INTERPOLATES the two limit abscissae instead
        of filtering vertices by x. It has to: the radius bracket below is
        measured to the two limit POINTS, and a limit falling between two
        vertices used to yield no point at all — the segment it cut was
        dropped whole, the surface ended at the last vertex strictly inside,
        and both ends of the bracket were then measured to the wrong place.
        """
        from ogr_core.geometry import BoundaryType, Vertex
        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return []
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if self.slope_limits is None or len(top) < 2:
            return top
        x0, x1 = sorted(self.slope_limits)
        x0 = max(x0, top[0].x)
        x1 = min(x1, top[-1].x)
        # Relative to the profile's own width, not absolute: the same model
        # in millimetres and in metres has to clip identically.
        tol = 1e-9 * max(top[-1].x - top[0].x, 1e-300)
        if x1 - x0 <= tol:
            # Limits that cross, or collapse onto one abscissa, describe no
            # surface at all. Falling back to the whole profile keeps the
            # search running on something meaningful instead of returning a
            # result computed from a single point.
            return top
        y0 = PathSearch._interpolate_top_y(top, x0)
        y1 = PathSearch._interpolate_top_y(top, x1)
        if y0 is None or y1 is None:
            return top
        # Strict comparison, so a profile vertex sitting exactly on a limit
        # is not emitted twice: the interpolated end already carries it.
        inner = [v for v in top if x0 + tol < v.x < x1 - tol]
        return [Vertex(x0, y0)] + inner + [Vertex(x1, y1)]

    # ------------------------------------------------------------------
    @staticmethod
    def _distance_to_surface(xc, yc, pts) -> float:
        """Shortest distance from a centre to the slope surface POLYLINE.

        The nearest point is the foot of a perpendicular when that foot
        falls inside a segment and a VERTEX when it does not, and both cases
        occur among the reference centres — at Ej_2's (12.381, 87.632) the
        nearest point is the vertex (40, 55), not any perpendicular foot. So
        clamping the projection parameter to [0, 1] is not a nicety; taking
        distances to vertices only (which is what this class did until
        v0.1.88) is a different and wrong measurement.
        """
        best = float("inf")
        for a, b in zip(pts[:-1], pts[1:]):
            dx = b.x - a.x
            dy = b.y - a.y
            L2 = dx * dx + dy * dy
            if L2 <= 0.0:
                t = 0.0
            else:
                t = ((xc - a.x) * dx + (yc - a.y) * dy) / L2
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            d = math.hypot(xc - (a.x + t * dx), yc - (a.y + t * dy))
            if d < best:
                best = d
        return best

    # The sampled range is inset by this fraction of its own width at each
    # end. MEASURED, not chosen — see _radius_bracket. It is a constant of
    # the rule: the A1/A2 pair (same grid, Radius Increment 1 and 10) gives
    # byte-identical bracket ends, so the inset does not depend on how many
    # circles are asked for.
    RADIUS_INSET = 0.05

    def _radius_bracket(self, xc, yc, slope_pts):
        """The (r_min, r_max) sampled at one grid centre.

        v0.1.88 — DERIVED FROM MEASUREMENT, replacing two versions of
        inference from a drawing. *Grid Search* says only that "suitable
        Minimum and Maximum radii are determined, based on the distances
        from the slip center to the slope surface", and v0.1.84 recorded
        that reading the accompanying figure literally made one reference
        model better and the other twice as bad. The rule below is not a
        reading of the figure: it is read off the reference's own output.

        The rule
        --------
        With ``S`` the slope surface (the ground profile between the Slope
        Limits) and ``P_L``, ``P_R`` the two limit points::

            d_min = distance from the centre to the nearest point of S
            d_max = min(|C - P_L|, |C - P_R|)      # the limit reached FIRST
            delta = RADIUS_INSET * (d_max - d_min)

            r_min = d_min + delta
            r_max = d_max - delta

        and Radius Increment intervals give ``rinc + 1`` equally spaced
        radii across ``[r_min, r_max]``.

        Two consequences worth stating, because both were bugs before:

        * ``d_max >= d_min`` is a THEOREM, not a case to guard: ``P_L`` and
          ``P_R`` are points OF ``S``, so their distances cannot be below
          the minimum distance to ``S``. This function therefore never
          fails, and the population of a grid is exactly
          ``(nx+1)(ny+1)(rinc+1)`` — the denominator v0.1.83 fixed. An
          earlier draft returned None when ``d_max == d_min`` and silently
          dropped Ej_1's whole ``x = 120`` column, 4851 circles down to
          4620.
        * when ``d_min == d_max`` (the centre sits directly above a limit
          point) the rule yields ``rinc + 1`` IDENTICAL radii, and that is
          what the reference does too: at Ej_1's (120, 30) it emits eleven
          circles of R = 5.

        How it was measured
        -------------------
        ``referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`` holds six
        Slide models run for this. Their ``.s01`` output lists, per centre,
        every generated circle as ``(r, yleft, x1, y1, x2, y2, yright,
        fs..., b1)``, so the bracket is READ rather than fitted — which is
        what unblocked this, since four fitted numbers could never have
        settled it (rule 1). The models come in pairs: Radius Increment 1
        (exactly two circles, the two ends) and 10 (eleven), on the same
        grid, for two geometries — one failing left-to-right, one
        right-to-left.

            check                                          worst error
            68 bracket ends, both geometries, rinc 1 & 10   5.7e-14
            441 centres of Ej_1's reference grid            4.0e-08 *
            440 centres of Ej_2's reference grid            7.0e-13
            uniform spacing, rinc+1 circles per centre      8.4e-13

        (*) that outlier is one centre, Ej_1's (52, 48), which lies exactly
        ON the slope face so ``d_min`` is 0: the reference prints
        2.601922406 where the rule gives 2.601922366, 1.5e-8 relative. Its
        own numerics in the degenerate case, not a disagreement.

        Decisively, the rule generates the two critical radii that no
        previous bracket could reach: 47.2124436 at Ej_1's (88, 70.5), the
        4th of its 11, and 60.2564659 at Ej_2's (-3.333, 87.632), the 4th
        of its 11. Both reference global minima are now IN the sampled
        population, and the searches land on the reference's own centre and
        radius rather than on a neighbour:

            case            method        before            after
            Ej_1            Bishop        +0.18 %           +0.02 %
            Ej_1            Janbu simpl.  -0.55 %           +0.13 %
            Ej_2            Bishop        +0.95 %           -0.07 %
            Ej_2            Janbu simpl.  +0.83 %           -0.03 %

        The five PUBLISHED cases of ``validacion/casos/`` — an independent
        check, since none of them is a Slide run — all stay inside their
        declared tolerances, moving by at most 0.24 % and in both
        directions. Both facts are tabulated in
        ``docs/audits/grid_radius_rule_v188.md``.

        What is NOT measured
        --------------------
        In all six models the Slope Limits sit at their automatic position,
        which coincides with the ends of the ground profile. The data
        therefore cannot distinguish "the limit points" from "the ends of
        the profile", nor whether ``d_min`` is measured over the clipped
        surface or the whole one. What is implemented is the documented
        reading — "the slope surface is simply the segments of the External
        Boundary between the Slope Limits" — so narrowing the limits
        narrows the radii. Confirming it needs one more Slide model with
        the limits moved inward to an abscissa that is NOT a profile
        vertex; until that exists, this paragraph is the honest statement of
        what the rule rests on.

        ``min_radius`` is an OGR control with no counterpart in the
        reference (which offers Minimum Elevation and Minimum Depth
        instead). It acts as a floor on ``d_min``, and its default is 0 so
        that the out-of-the-box sampling is the reference's exactly.
        """
        if not slope_pts or len(slope_pts) < 2:
            return None
        d_min = max(self._distance_to_surface(xc, yc, slope_pts),
                    self.min_radius)
        # The FIRST limit reached as the radius grows, not the farthest one:
        # past it the circle no longer daylights inside the Slope Limits.
        d_max = min(math.hypot(xc - slope_pts[0].x, yc - slope_pts[0].y),
                    math.hypot(xc - slope_pts[-1].x, yc - slope_pts[-1].y))
        # max() only matters when min_radius has been raised above d_min,
        # which is the one way the caller can break the theorem above.
        d_max = max(d_max, d_min)
        delta = self.RADIUS_INSET * (d_max - d_min)
        return d_min + delta, d_max - delta

    # ------------------------------------------------------------------
    def _centres(self, project: Project) -> list:
        """Every grid centre, in the order the sequential run visits them.

        Split out of ``_run`` so a parallel run can hand each worker a
        CONTIGUOUS slice of this list and concatenate the partial results
        in the same order. That is what makes the parallel path produce a
        byte-for-byte identical ``evaluations`` list rather than merely an
        equivalent one.
        """
        gx = self.grid_x or self._auto_grid(project)[0]
        gy = self.grid_y or self._auto_grid(project)[1]
        # v0.1.102 — remembered because the caller cannot work it out: with
        # no user grid the extent comes from the model's bounding box, and
        # ``grid_x`` is None. ``grid_edge_note`` needs the grid that was
        # actually swept to say whether the answer came off its edge.
        self.grid_x_used = gx
        self.grid_y_used = gy
        nx_pts = self.grid_nx + 1
        ny_pts = self.grid_ny + 1
        xs = [gx[0] + (gx[1] - gx[0]) * i / (nx_pts - 1) for i in range(nx_pts)]
        ys = [gy[0] + (gy[1] - gy[0]) * j / (ny_pts - 1) for j in range(ny_pts)]
        return [(xc, yc) for xc in xs for yc in ys]

    def _run(self, project: Project) -> SearchResult:
        centres = self._centres(project)
        n_circles = self.radius_increment + 1
        workers = _worker_count(project, len(centres) * n_circles)
        if workers > 1:
            out = _parallel_grid_run(self, project, centres, workers)
            if out is not None:
                return out
        return self._run_centres(project, centres, 0, len(centres))

    def _run_centres(self, project: Project, centres: list,
                     done_before: int, total: int) -> SearchResult:
        """Evaluate a contiguous run of grid centres.

        ``done_before`` and ``total`` exist only so the progress callback
        keeps reporting against the WHOLE grid while a worker sees a slice
        of it.
        """
        slope_pts = self._slope_surface(project)

        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)
        processed = done_before
        n_circles = self.radius_increment + 1  # circles per centre

        if True:
            for xc, yc in centres:
                processed += 1
                if self.progress_cb:
                    self.progress_cb(processed, total)

                bracket = self._radius_bracket(xc, yc, slope_pts)
                if bracket is None:
                    # No slope surface at all: nothing can be generated
                    # here. Counted rather than skipped, for the same
                    # reason as below.
                    result.invalid_count += n_circles
                    continue
                r_min, r_max = bracket
                for k in range(n_circles):
                    if n_circles > 1:
                        r = r_min + (r_max - r_min) * k / (n_circles - 1)
                    else:
                        r = r_min
                    if r <= 0:
                        # Only reachable when the centre IS a limit point,
                        # so d_min = d_max = 0. Counted, not skipped: the
                        # population has to stay (nx+1)(ny+1)(rinc+1)
                        # whatever the geometry does — see total_count.
                        result.invalid_count += 1
                        continue
                    if self._focus_rejects_circle(xc, yc, r):
                        continue
                    circle = SlipCircle(centre_x=xc, centre_y=yc, radius=r)
                    res = self.evaluate_circle(project, circle)
                    # v0.1.83 — a circle that could not be analysed is
                    # still a circle that was GENERATED, and it has to
                    # appear in the totals. Until now ``res is None`` fell
                    # through counting nothing at all, so 1697 of the 4851
                    # circles of the reference grid simply vanished: the
                    # window reported "2966 / 3154" for a population of
                    # 4851. Worse, the denominator MOVED when a search
                    # option changed (2633 with reverse curvature off),
                    # which is the one thing a number a user compares
                    # between runs must never do.
                    if res is None:
                        result.invalid_count += 1
                        continue
                    if res.is_valid and not (0.2 <= res.fos <= 100.0):
                        result.invalid_count += 1
                        continue
                    result.evaluations.append(res)
                    if res.is_valid:
                        result.valid_count += 1
                    else:
                        result.invalid_count += 1

        return result


# ======================================================================
@dataclass
class SlopeFrame:
    """The sampling frame a circle-generating search works in.

    Three numbers define one trial circle: the abscissa where it leaves
    the ground on the toe side, the abscissa where it enters on the crest
    side, and the inclination of the surface at the toe. Everything else
    — the centre, the radius — follows from those by construction.

    v0.1.126 — extracted from ``SlopeSearch._run`` so the Particle Swarm
    search can search THE SAME space rather than inventing a second one.
    Two doors into one calculation carrying different frames is the shape
    of defect this project has already paid for twice (v0.1.89, D07b), and
    a niching radius quoted as "10 % of the search space" means nothing
    at all unless the space is one thing.

    ``to_right`` says whether the crest is to the right of the toe, and
    the two windows are stored already ordered, low first.
    """

    top: list
    toe_x0: float
    toe_x1: float
    crest_x0: float
    crest_x1: float
    ang_lo: float          # radians
    ang_hi: float          # radians
    to_right: bool
    beta_deg: float
    height: float

    def circle_params(self, u_toe: float, u_crest: float, u_ang: float):
        """Map a point of the unit cube onto ``(x_toe, x_crest, theta)``.

        The unit cube is what makes a distance between two particles
        comparable across the three axes: two abscissae in metres and an
        angle in radians cannot be added up otherwise. It is also what
        gives "10 % of the span of the search space" a meaning that does
        not change with the model's units.
        """
        def _c(u):
            return 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)

        return (self.toe_x0 + _c(u_toe) * (self.toe_x1 - self.toe_x0),
                self.crest_x0 + _c(u_crest) * (self.crest_x1 - self.crest_x0),
                self.ang_lo + _c(u_ang) * (self.ang_hi - self.ang_lo))


def slope_frame(project: Project,
                initial_angle_lower_deg: float = -45.0,
                initial_angle_upper_deg: Optional[float] = None
                ) -> Optional[SlopeFrame]:
    """Build the :class:`SlopeFrame` of ``project``, or None.

    None means the model cannot be framed at all — no external boundary,
    or a ground profile with fewer than two points — and the caller
    returns an empty result rather than guessing.
    """
    from ogr_core.geometry import BoundaryType

    ext = None
    for b in project.boundaries:
        if b.btype == BoundaryType.EXTERNAL:
            ext = b
            break
    if ext is None:
        return None
    ext_verts = ext.polyline.vertices
    if len(ext_verts) < 3:
        return None

    top = PathSearch._ground_profile(ext_verts)
    if len(top) < 2:
        return None

    x_left = top[0].x
    x_right = top[-1].x
    y_max = max(v.y for v in ext_verts)
    y_min = min(v.y for v in ext_verts)
    H = y_max - y_min

    # Locate slope face (steepest segment) → toe/crest + β
    steepest_i = 0
    steepest = -1.0
    for i in range(len(top) - 1):
        ddx = top[i + 1].x - top[i].x
        ddy = top[i + 1].y - top[i].y
        if abs(ddx) < 1e-9:
            continue
        s = abs(ddy / ddx)
        if s > steepest:
            steepest = s
            steepest_i = i
    face_a = top[steepest_i]
    face_b = top[steepest_i + 1]
    beta_deg = math.degrees(math.atan2(
        abs(face_b.y - face_a.y), abs(face_b.x - face_a.x)))
    toe_pt = face_a if face_a.y <= face_b.y else face_b
    crest_pt = face_b if face_a.y <= face_b.y else face_a
    to_right = crest_pt.x > toe_pt.x
    face_lo_x = min(face_a.x, face_b.x)
    face_hi_x = max(face_a.x, face_b.x)
    face_w = max(face_hi_x - face_lo_x, 1e-6)

    # Entry (toe-side) and exit (crest-side) sampling ranges along x.
    # Generous ranges (extending onto the flat shelf and plateau) so
    # the search can reach deep-seated circles whose daylight points
    # are well beyond the slope face — these often govern the
    # critical FoS.
    if to_right:
        toe_x0 = max(x_left, toe_pt.x - 0.8 * face_w)
        toe_x1 = toe_pt.x + 0.6 * face_w
        crest_x0 = crest_pt.x - 0.4 * face_w
        crest_x1 = min(x_right, crest_pt.x + 1.5 * face_w)
    else:
        toe_x0 = toe_pt.x - 0.6 * face_w
        toe_x1 = min(x_right, toe_pt.x + 0.8 * face_w)
        crest_x0 = max(x_left, crest_pt.x - 1.5 * face_w)
        crest_x1 = crest_pt.x + 0.4 * face_w
        toe_x0, toe_x1 = min(toe_x0, toe_x1), max(toe_x0, toe_x1)
        crest_x0, crest_x1 = min(crest_x0, crest_x1), max(crest_x0, crest_x1)

    # Initial-angle window (radians, descending into slope). Use a
    # wide window so both shallow and deep-seated circles are
    # generated: from steep (toward −70°) up to nearly horizontal.
    ang_lo = math.radians(initial_angle_lower_deg)
    if initial_angle_upper_deg is not None:
        ang_hi = math.radians(initial_angle_upper_deg)
    else:
        # v0.1.24 FIX (anomaly A2): same root cause as A1 — the
        # documented Upper Angle is +(β − 5)°. The tangent of a
        # toe-exiting circle at the toe RISES towards the crest
        # (e.g. +15.5° for the reference case), so negating this
        # limit excluded the true critical circle from the search
        # and the reported FoS was ~1.05 instead of ~0.89.
        ang_hi = math.radians(max(beta_deg - 5.0, 5.0))
    # Broaden downward so deep circles (steep exit tangents) appear
    ang_lo = min(ang_lo, math.radians(-70.0))
    if ang_lo > ang_hi:
        ang_lo, ang_hi = ang_hi, ang_lo

    return SlopeFrame(top=top, toe_x0=toe_x0, toe_x1=toe_x1,
                      crest_x0=crest_x0, crest_x1=crest_x1,
                      ang_lo=ang_lo, ang_hi=ang_hi, to_right=to_right,
                      beta_deg=beta_deg, height=H)


class SlopeSearch(BaseSearch):
    """Slope Search (circular) — the documented random two-point method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm,
    which is the circular analogue of the Path Search:

    1. The Slope Limits define the segment(s) of ground surface used
       for the slip-surface ENTRY and EXIT points.
    2. For each candidate, TWO points are randomly generated on the
       ground surface within the Slope Limits — one on the toe side
       (the exit, lower) and one on the crest side (the entry, upper).
    3. A circular arc is fitted through those two surface points. The
       THIRD constraint that makes the circle unique is the *Initial
       Angle at Toe* — the inclination of the slip surface where it
       emerges at the toe. By default Slide samples this angle randomly
       within an admissible window; the circle centre is then the
       intersection of (a) the perpendicular bisector of the two
       surface points and (b) the line through the toe point normal to
       the chosen tangent direction.

    This produces circles that actually daylight on the slope surface
    between the Slope Limits, rather than arbitrary circles spanning the
    whole bounding box (the old behaviour).
    """

    def __init__(
        self,
        method: LEMMethod,
        num_surfaces: int = 1000,
        num_slices: int = 30,
        min_area: float = 0.5,
        initial_angle_lower_deg: float = -45.0,
        initial_angle_upper_deg: Optional[float] = None,
        seed: Optional[int] = 42,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        **legacy_kwargs,
    ) -> None:
        # v0.1.77 — the admissibility arguments are forwarded here for
        # the same reason the other five searches forward them: the
        # Tensile Stress and m-alpha checks are project settings, not
        # per-search ones. Until this version SlopeSearch was the only
        # search that did not accept them, and since the GUI passes them
        # to every search, picking Slope Search raised a TypeError that
        # the blanket ``except Exception`` in the compute worker turned
        # into a generic "Error" dialog with no results — for every
        # release since the first public one.
        super().__init__(
            method, num_slices, min_area, progress_cb,
            **_base_kwargs(legacy_kwargs),
        )
        self.num_surfaces = num_surfaces
        self.initial_angle_lower_deg = initial_angle_lower_deg
        self.initial_angle_upper_deg = initial_angle_upper_deg
        self.rng = random.Random(seed)

    def _run(self, project: Project) -> SearchResult:
        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)

        # v0.1.126 — the frame moved to ``slope_frame`` so the Particle
        # Swarm search reads the SAME one. Nothing about it changed; the
        # suite is the proof, since every Slope Search result in it is
        # pinned.
        frame = slope_frame(project, self.initial_angle_lower_deg,
                            self.initial_angle_upper_deg)
        if frame is None:
            return result
        top = frame.top
        to_right = frame.to_right
        toe_x0, toe_x1 = frame.toe_x0, frame.toe_x1
        crest_x0, crest_x1 = frame.crest_x0, frame.crest_x1
        ang_lo, ang_hi = frame.ang_lo, frame.ang_hi
        H = frame.height

        best = []  # (fos, cx, cy, r)
        for i in range(self.num_surfaces):
            if self.progress_cb and (i % 50 == 0):
                self.progress_cb(i, self.num_surfaces)

            # Two surface points: toe (exit) and crest (entry)
            xt = self.rng.uniform(toe_x0, toe_x1)
            xc = self.rng.uniform(crest_x0, crest_x1)
            yt = PathSearch._interpolate_top_y(top, xt)
            yc = PathSearch._interpolate_top_y(top, xc)
            if yt is None or yc is None:
                result.invalid_count += 1
                continue
            if abs(xc - xt) < 0.5:
                result.invalid_count += 1
                continue

            theta = self.rng.uniform(ang_lo, ang_hi)
            circle = self._circle_from_point_tangent_point(
                xt, yt, theta, xc, yc, to_right,
            )
            if circle is None:
                result.invalid_count += 1
                continue
            cx, cy, radius = circle
            if radius <= 0 or radius > 50.0 * max(H, 1.0):
                result.invalid_count += 1
                continue

            if self._focus_rejects_circle(cx, cy, radius):
                # v0.1.129 — the reference documents the focus objects for
                # the Grid Search AND for this one, and until now only the
                # Grid Search had ever been handed any. Defect D33.
                continue

            from .surface import SlipCircle
            sc = SlipCircle(centre_x=cx, centre_y=cy, radius=radius)
            res = self.evaluate_circle(project, sc)
            if res is not None:
                if res.is_valid and not (0.2 <= res.fos <= 100.0):
                    result.invalid_count += 1
                    continue
                result.evaluations.append(res)
                if res.is_valid:
                    result.valid_count += 1
                    best.append((self.score(res), cx, cy, radius))
                else:
                    result.invalid_count += 1
            else:
                result.invalid_count += 1

        # v0.1.17 — local refinement (gradient-free hill-descent) on the
        # best few circles, mirroring Slide's surface optimisation. This
        # is what lets the Slope Search converge onto the same critical
        # circle the Grid Search finds, instead of stopping at the best
        # random sample.
        if best:
            from .surface import SlipCircle
            best.sort(key=lambda t: t[0])
            for k in range(min(8, len(best))):
                f0, cx, cy, r = best[k]
                cur_f, cur = f0, (cx, cy, r)
                span = max(0.15 * r, 1.0)
                for _it in range(120):
                    step = span * (1.0 - _it / 120.0)
                    tcx = cur[0] + self.rng.uniform(-step, step)
                    tcy = cur[1] + self.rng.uniform(-step, step)
                    tr = cur[2] + self.rng.uniform(-step, step)
                    if tr <= 0:
                        continue
                    if self._focus_rejects_circle(tcx, tcy, tr):
                        # The refinement walk has to respect the focus too,
                        # or the search would step off it after finding a
                        # focused minimum and report the escape.
                        continue
                    sc = SlipCircle(centre_x=tcx, centre_y=tcy, radius=tr)
                    res = self.evaluate_circle(project, sc)
                    if res is None or not res.is_valid:
                        continue
                    if not (0.2 <= res.fos <= 100.0):
                        continue
                    result.evaluations.append(res)
                    result.valid_count += 1
                    if self.score(res) < cur_f:
                        cur_f = self.score(res)
                        cur = (tcx, tcy, tr)

        if self.progress_cb:
            self.progress_cb(self.num_surfaces, self.num_surfaces)
        return result

    @staticmethod
    def _circle_from_point_tangent_point(x1, y1, tangent_angle,
                                         x2, y2, to_right):
        """Determine the circle passing through (x1,y1) and (x2,y2) whose
        tangent at (x1,y1) has the given inclination ``tangent_angle``
        (radians from +x axis).

        Geometry: the centre lies on the line through (x1,y1)
        perpendicular to the tangent direction, AND on the perpendicular
        bisector of the chord (x1,y1)-(x2,y2). Intersect the two.

        Returns (cx, cy, radius) or None if degenerate / centre below
        the surface.
        """
        # Normal to the tangent at point 1 (perpendicular direction)
        # tangent unit vector:
        tx, ty = math.cos(tangent_angle), math.sin(tangent_angle)
        # normal direction (rotate 90°): (-ty, tx)
        nx, ny = -ty, tx
        # Line 1: P1 + s*(nx,ny)  → centre is somewhere on this line.
        # Line 2: perpendicular bisector of P1-P2.
        mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
        # chord direction
        cdx, cdy = x2 - x1, y2 - y1
        # bisector direction (perp to chord): (-cdy, cdx)
        bx, by = -cdy, cdx
        # Solve P1 + s*(nx,ny) = M + t*(bx,by)
        # → s*nx - t*bx = mx - x1 ; s*ny - t*by = my - y1
        det = nx * (-by) - (-bx) * ny
        if abs(det) < 1e-12:
            return None
        rhs_x = mx - x1
        rhs_y = my - y1
        s = (rhs_x * (-by) - (-bx) * rhs_y) / det
        cx = x1 + s * nx
        cy = y1 + s * ny
        radius = math.hypot(cx - x1, cy - y1)
        # The centre must be ABOVE the surface points for a valid
        # slip circle (concave-up arc daylighting on the slope).
        if cy < max(y1, y2):
            return None
        return (cx, cy, radius)


# ======================================================================
# v0.1.10 — Stub solver classes for the additional Search Methods.
#
# These currently delegate to GridSearch / SlopeSearch (or run a small
# random sweep) so the user can SELECT the method without crashing.
# Full implementations of Block/Path/SA/AutoRefine arrive in v0.2.x.
# ======================================================================
class AutoRefineSearch(BaseSearch):
    """Auto Refine Search (circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm,
    which iteratively narrows the search to the part of the slope that
    produces the lowest safety factors:

    1. The slope surface (between the Slope Limits) is divided into
       ``divisions`` divisions, measured ALONG the slope polyline.
    2. For each PAIR of divisions, ``circles_per_division`` circles are
       generated. The straight line joining the division midpoints sets
       a MINIMUM tangent angle; vertical (90°) sets the MAXIMUM. The
       angular range is split equally (with a small offset) and a circle
       is fitted for each tangent angle.
    3. The FoS of each circle is computed and the AVERAGE FoS associated
       with each division is recorded.
    4. The ``next_iter_fraction`` (e.g. 0.5 = 50%) of divisions with the
       LOWEST average FoS are kept; the rest are discarded. The retained
       divisions form a new, narrowed slope polyline.
    5. Steps 1-4 repeat for ``iterations`` iterations (no convergence
       cut-off — the full count always runs).

    This typically finds a lower FoS than Grid or Slope search for an
    equal number of surfaces.
    """

    def __init__(
        self,
        method,
        divisions: int = 10,
        circles_per_division: int = 10,
        # 10 and not 5: it is what the reference's panel shows next to
        # "Number of Iterations", and matches the settings field the user
        # edits. A second settings field held 5 and it was the one the
        # runner read, so a model built by a script ran half the search it
        # declared (v0.1.103).
        iterations: int = 10,
        next_iter_fraction: float = 0.5,
        num_slices: int = 30,
        min_area: float = 0.5,
        progress_cb=None,
        # Back-compat (old signature used factor/radius_increment)
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            **_base_kwargs(legacy_kwargs),
        )
        self.divisions = max(2, divisions)
        self.circles_per_division = max(1, circles_per_division)
        self.iterations = max(1, iterations)
        # next_iter_fraction may arrive as a percentage (50) or fraction
        # (0.5); normalise to a fraction.
        f = next_iter_fraction
        if f > 1.0:
            f = f / 100.0
        self.next_iter_fraction = min(0.95, max(0.1, f))
        self.min_area = min_area
        self.progress_cb = progress_cb

    # ------------------------------------------------------------------
    # How many circles a given panel of parameters generates. The interface
    # publishes this number BEFORE the run, so it has to be derivable from
    # the parameters alone — and it has to come from here, next to the loop
    # that generates them, because the one time it was computed a second
    # time somewhere else it was computed WRONG (defect D07c(c): the dialog
    # multiplied by the divisions where the loop walks their PAIRS, and
    # published 1000 for a search that generates 4500).
    # ------------------------------------------------------------------
    @staticmethod
    def surfaces_per_iteration(divisions: int,
                               circles_per_division: int) -> int:
        """Circles generated in ONE iteration of the search.

        ``C(d,2)·c`` and not ``d·c``: step 2 of the method generates
        circles between each PAIR of divisions, so the population grows
        with the SQUARE of the divisions — which is why a panel that looks
        modest is a quadratic amount of work.

        Clamped exactly as ``__init__`` clamps, so the number answers for
        the search that would actually be built from these parameters.
        """
        d = max(2, int(divisions))
        return math.comb(d, 2) * max(1, int(circles_per_division))

    @classmethod
    def surfaces_generated(cls, divisions: int, circles_per_division: int,
                           iterations: int) -> int:
        """Circles generated by a whole run.

        Every iteration divides the (narrowed) slope polyline into
        ``divisions`` divisions again, so the count per iteration does not
        change as the search refines — the search area shrinks, the
        population does not.

        This is what the search GENERATES, and it is an upper bound on
        what it ANALYSES: a pair and tangent angle whose construction has
        no valid centre, and a circle a focus object rejects, are skipped
        without ever reaching the solver. Measured on verification problem
        14 (10/10/10): 4500 generated, 3300 analysed — 330 per iteration
        rather than 450. ``SearchResult.total_count`` is the analysed
        population and is the one the verification bank records; this is
        deliberately NOT called ``total_count`` for that reason.
        """
        return (cls.surfaces_per_iteration(divisions, circles_per_division)
                * max(1, int(iterations)))

    # ------------------------------------------------------------------
    def _evaluate_trial(self, project, circle):
        """The result for one generated circle. Here, the circle itself.

        A seam, not a convenience. The non-circular variant of this search
        is the SAME generation and the SAME refinement, and differs only in
        what reaches the solver — so subclassing at this one line is what
        keeps the circular answers identical to the digit. Anything else
        (a second copy of ``_run``, a flag inside the loop) would have the
        two variants drift apart the first time either is touched.
        """
        return self.evaluate_circle(project, circle)

    def _run(self, project) -> SearchResult:
        from ogr_core.geometry import BoundaryType
        from .surface import SlipCircle

        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if len(top) < 2:
            return result

        # Initial slope polyline = ground profile within Slope Limits.
        #
        # v0.1.92 — the clip INTERPOLATES the limit abscissae, as
        # GridSearch._slope_surface has done since v0.1.88. It used to keep
        # the vertices whose x fell between the limits, which throws away the
        # segment a limit cuts through: a limit that is not itself a vertex
        # produced no point at all, and the polyline this search starts from
        # ended at the last vertex strictly inside instead of at the limit.
        #
        # v0.1.88 reported this and did NOT fix it, because there was no
        # measurement saying where the limits belong. There is now: two
        # models run with the limits moved inward to abscissae that are not
        # vertices show the surface reaching exactly to the limit POINTS, to
        # 5e-14. See tests/test_grid_radius_rule_v188.py.
        poly_pts = list(top)
        if self.slope_limits is not None and len(top) >= 2:
            x0, x1 = sorted(self.slope_limits)
            x0 = max(x0, top[0].x)
            x1 = min(x1, top[-1].x)
            span = max(top[-1].x - top[0].x, 1e-300)
            tol = 1e-9 * span            # relative, never absolute
            if x1 - x0 > tol:
                y0 = PathSearch._interpolate_top_y(top, x0)
                y1 = PathSearch._interpolate_top_y(top, x1)
                if y0 is not None and y1 is not None:
                    from ogr_core.geometry import Vertex as _V
                    poly_pts = ([_V(x0, y0)]
                                + [v for v in top if x0 + tol < v.x < x1 - tol]
                                + [_V(x1, y1)])
        if len(poly_pts) < 2:
            poly_pts = list(top)

        # Resample the slope polyline into a dense set of points we can
        # divide evenly along arc length.
        def _resample(pts, n):
            """Return n+1 points equally spaced along the polyline arc."""
            seg = []
            total = 0.0
            for a, b in zip(pts[:-1], pts[1:]):
                d = math.hypot(b.x - a.x, b.y - a.y)
                seg.append(d)
                total += d
            if total < 1e-9:
                return list(pts)
            out = []
            from ogr_core.geometry import Vertex
            for i in range(n + 1):
                target = total * i / n
                acc = 0.0
                placed = False
                for j, d in enumerate(seg):
                    if acc + d >= target - 1e-12:
                        f = (target - acc) / d if d > 1e-12 else 0.0
                        a, b = pts[j], pts[j + 1]
                        out.append(Vertex(a.x + f * (b.x - a.x),
                                          a.y + f * (b.y - a.y)))
                        placed = True
                        break
                    acc += d
                if not placed:
                    out.append(pts[-1])
            return out

        total_iter = self.iterations
        for it in range(total_iter):
            if self.progress_cb:
                self.progress_cb(it, total_iter)
            # Divide the current slope polyline into `divisions` divisions
            div_pts = _resample(poly_pts, self.divisions)
            # midpoint of each division
            mids = []
            for k in range(len(div_pts) - 1):
                ax, ay = div_pts[k].x, div_pts[k].y
                bx, by = div_pts[k + 1].x, div_pts[k + 1].y
                mids.append(((ax + bx) / 2.0, (ay + by) / 2.0))

            # For each PAIR of divisions (i<j) generate circles and
            # accumulate the FoS into BOTH divisions' running averages.
            div_fos_sum = [0.0] * (len(div_pts) - 1)
            div_fos_cnt = [0] * (len(div_pts) - 1)

            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    p1 = mids[i]
                    p2 = mids[j]
                    # The chord direction between the two midpoints.
                    dxm = p2[0] - p1[0]
                    dym = p2[1] - p1[1]
                    chord_ang = math.atan2(dym, dxm)
                    # For a concave-up slip circle through the two
                    # points with the centre ABOVE them, the valid
                    # tangent angles lie roughly from (chord_ang + 90°)
                    # towards (chord_ang + 180°). We sweep this band,
                    # which corresponds to the documented "minimum angle
                    # = slope of joining line, maximum = vertical"
                    # mapped into the construction's convention. Invalid
                    # constructions (centre below points) are filtered.
                    lo = chord_ang + math.radians(92.0)
                    hi = chord_ang + math.radians(178.0)
                    ncpd = self.circles_per_division
                    for c in range(ncpd):
                        # Counted HERE, before the construction can fail:
                        # ``attempts`` is the generation attempts made, and
                        # it is what the interface publishes before the run
                        # (``surfaces_generated``). Counting a candidate
                        # only once it survives would make the published
                        # number unverifiable against any real run, which
                        # is how the dialog drifted in the first place.
                        result.attempts += 1
                        if ncpd > 1:
                            ang = lo + (hi - lo) * c / (ncpd - 1)
                        else:
                            ang = 0.5 * (lo + hi)
                        circle = self._circle_through_two_points_tangent(
                            p1[0], p1[1], p2[0], p2[1], ang)
                        if circle is None:
                            continue
                        cx, cy, r = circle
                        if self._focus_rejects_circle(cx, cy, r):
                            # v0.1.129 — asked HERE, on the circle, and not
                            # inside ``_evaluate_trial``, for two reasons.
                            # It skips instead of counting, as every other
                            # focus rejection does; and the non-circular
                            # variant subclasses that seam, so a candidate
                            # would be judged on the chords it is about to
                            # become rather than on the circle the search
                            # generated. Defect D33.
                            continue
                        sc = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
                        res = self._evaluate_trial(project, sc)
                        if res is None or not res.is_valid:
                            result.invalid_count += 1
                            continue
                        if not (0.2 <= res.fos <= 100.0):
                            result.invalid_count += 1
                            continue
                        result.evaluations.append(res)
                        result.valid_count += 1
                        for d in (i, j):
                            div_fos_sum[d] += self.score(res)
                            div_fos_cnt[d] += 1

            # Average FoS per division; keep the lowest fraction
            div_avg = []
            for d in range(len(div_pts) - 1):
                if div_fos_cnt[d] > 0:
                    div_avg.append((div_fos_sum[d] / div_fos_cnt[d], d))
                else:
                    div_avg.append((float("inf"), d))
            div_avg.sort(key=lambda t: t[0])
            n_keep = max(1, int(round(
                (len(div_pts) - 1) * self.next_iter_fraction)))
            keep_idx = sorted(d for _f, d in div_avg[:n_keep])

            # Build the narrowed slope polyline from the retained
            # divisions (contiguous span from first to last kept index).
            if keep_idx:
                lo_i = keep_idx[0]
                hi_i = keep_idx[-1] + 1
                new_pts = div_pts[lo_i:hi_i + 1]
                if len(new_pts) >= 2:
                    poly_pts = new_pts

        if self.progress_cb:
            self.progress_cb(total_iter, total_iter)
        return result

    @staticmethod
    def _circle_through_two_points_tangent(x1, y1, x2, y2, tangent_angle):
        """Circle passing through two division-midpoints, with the given
        initial tangent angle at the first point.

        For Auto Refine, the tangent direction at the lower point plus
        the requirement to pass through the upper point defines the
        circle. The centre lies on the normal to the tangent at point 1,
        at the distance where it is equidistant from point 2. The centre
        must be ABOVE both points (concave-up daylighting arc).
        Returns (cx, cy, r) or None.
        """
        # Normal direction at point 1 (perpendicular to tangent)
        tx, ty = math.cos(tangent_angle), math.sin(tangent_angle)
        nx, ny = -ty, tx  # rotate +90°
        # Centre = P1 + s·(nx,ny). Solve |C - P2| = |C - P1| = r.
        # |C-P1|² = s²;  |C-P2|² = (P1+s·n - P2)² = s²
        # Expand: (P1-P2)² + 2 s n·(P1-P2) = 0  → s = -(P1-P2)²/(2 n·(P1-P2))
        dx1 = x1 - x2
        dy1 = y1 - y2
        denom = 2.0 * (nx * dx1 + ny * dy1)
        if abs(denom) < 1e-12:
            return None
        s = -(dx1 * dx1 + dy1 * dy1) / denom
        cx = x1 + s * nx
        cy = y1 + s * ny
        r = math.hypot(cx - x1, cy - y1)
        if r <= 1e-6:
            return None
        # Centre must be above both points (valid slip arc)
        if cy < max(y1, y2):
            # try the mirrored normal
            nx, ny = ty, -tx
            denom = 2.0 * (nx * dx1 + ny * dy1)
            if abs(denom) < 1e-12:
                return None
            s = -(dx1 * dx1 + dy1 * dy1) / denom
            cx = x1 + s * nx
            cy = y1 + s * ny
            r = math.hypot(cx - x1, cy - y1)
            if cy < max(y1, y2):
                return None
        return (cx, cy, r)


class AutoRefineNonCircularSearch(AutoRefineSearch):
    """Auto Refine Search (non-circular) — the documented variant.

    v0.1.128, defect D32. The setting ``auto_refine_num_vertices_along
    _surface`` and the membership of AUTO_REFINE in the non-circular
    family had both existed since v0.1.10, and the search behind them had
    not: ``build_search`` never looked at the surface type, so a model
    declaring Non-Circular + Auto Refine saved without complaint, opened
    without complaint and came back with CIRCLES. Rule 7, in the form
    that costs most — a search declared non-circular whose answer equals
    the circular one reads as agreement between the two families, which
    is the very conclusion a verification bank exists to be able to draw.

    The reference documents the method and nothing here was invented:

    1. Circles are generated exactly as the circular Auto Refine
       generates them — same divisions, same pairs, same tangent sweep.
    2. Each circle is converted into a piece-wise linear surface by
       sub-dividing its arc into approximately equal divisions, joining
       the resulting ``num_vertices`` vertices with straight segments,
       and THE FACTOR OF SAFETY IS COMPUTED ON THAT POLYLINE — not on
       the circle it came from.
    3. The refinement (average factor per division, keep the lowest
       fraction, narrow the polyline) proceeds unchanged.
    4. An optimisation search is applied afterwards, and it is ON by
       default for this method: see ``optimize_enabled_for``. Once
       optimised the vertices are no longer bound to any circle, so the
       final surface can carry more vertices than were asked for here.

    **How the answer relates to the circle it came from, measured rather
    than reasoned.** The tempting argument — the chords of a concave-up
    arc lie above it, so a coarse conversion is a shallower surface and
    must read higher — predicts a SIGN, and the sign is not a property of
    the conversion. Bishop against the same arc gives +5.24 % at 4
    vertices falling to +0.30 % on the test slope of
    ``tests/test_auto_refine_noncircular_v1128.py``, and -2.64 % rising
    to -2.56 % on verification problem 77. Opposite directions, and
    neither one settles on zero.

    What does not settle is the moment axis, not the discretisation: a
    polyline has no centre of rotation, the axis built for it is not the
    generating circle's centre, and a moment-only method is entitled to
    notice (anomaly D47, measured in ``moment_axis``). Spencer satisfies
    force AND moment equilibrium, so its answer cannot depend on that
    point, and it converges properly: +0.2920 %, +0.0472 %, +0.0151 %,
    +0.0096 % at 8, 16, 32 and 64 vertices — close to the factor of four
    per doubling an inscribed polygon owes its arc.

    So the count is worth spending and 12 is a fair default, but what a
    coarser one costs is model-dependent in size and in direction, and
    only a complete-equilibrium method can be asked how much of the
    difference is the surface.
    """

    def __init__(self, method, num_vertices: int = 12, **kwargs) -> None:
        super().__init__(method=method, **kwargs)
        # 3 is the floor a polyline needs to bend at all; below it the
        # "surface" is a single chord and the search is not the one the
        # user asked for.
        self.num_vertices = max(3, int(num_vertices))

    # ------------------------------------------------------------------
    def _run(self, project) -> SearchResult:
        """The circular run, plus the one thing it fails at silently.

        A polyline of N vertices has N-1 straight segments, every vertex
        is a mandatory slice boundary, and ``_slice_bounds`` refuses a
        surface whole when the segments outnumber the slices. So a vertex
        count that looks merely ambitious returns NO surfaces at all
        rather than a coarser answer, and the user has asked for a number
        the analysis silently cannot honour — which is the very shape of
        defect this search was written to close.

        ``settings_warnings`` states the part that can be predicted
        (N-1 > slices refuses every surface). It cannot state the rest,
        and the rest is the dangerous half: material boundaries and the
        water table are mandatory cuts too and they differ PER SURFACE,
        so the search does not fail cleanly — it quietly analyses the
        surfaces that cross few layers and drops the ones that cross
        many. Measured on verification problem 77 at 30 slices: 12
        vertices evaluate 69 surfaces, 30 vertices evaluate 40, and
        nothing said that 29 had gone. That is a biased search reported
        as a complete one, so the count is observed here and stated.
        """
        self._unsliceable = 0
        result = super()._run(project)
        if self._unsliceable:
            notes = getattr(self, "_pending_notes", None)
            if notes is not None:
                total = self._unsliceable + result.valid_count
                notes.append(
                    "%d of the %d surfaces this search formed could not be "
                    "sliced and were dropped. Each circle is converted into "
                    "%d vertices, which is %d straight segments, and this "
                    "analysis uses %d slices; every vertex is a mandatory "
                    "slice boundary, and material boundaries and the water "
                    "table take slices of their own. The surfaces lost are "
                    "the ones that cross the most layers, so this is not an "
                    "even thinning of the search. Use fewer vertices or more "
                    "slices." % (self._unsliceable, total, self.num_vertices,
                                 self.num_vertices - 1, self.num_slices))
        return result

    # ------------------------------------------------------------------
    def _evaluate_trial(self, project, circle):
        """The factor of safety of the POLYLINE this circle converts to.

        ``_candidate_surfaces`` does the whole geometric resolution and
        spends no solver on it: it returns each sliding mass of the
        circle with its endpoints resolved, its reverse curvature
        treated, the user's tension crack applied, the composite clipping
        done and containment already judged. That is exactly the step
        this method needs, and it is why the non-circular variant costs
        the same as the circular one — one analysis per mass, not two.

        Every mass is walked and the worst kept, for the reason v0.1.84
        records on ``evaluate_circle``: a circle crossing the ground more
        than twice defines several disjoint masses and the first from the
        left is not necessarily the critical one.

        A mass that is NOT a plain circle passes through unconverted.
        With Composite Surfaces on, a clipped mass is part arc and part
        model floor, and the reference describes the conversion of a
        CIRCLE only — inventing a rule for the composite case is exactly
        what this project's contract forbids. It is still analysed, as
        the composite surface it is.
        """
        polys = []
        for mass in self._candidate_surfaces(project, circle):
            if not isinstance(mass, SlipCircle):
                polys.append(mass)
                continue
            poly = self._arc_polyline(mass, self.num_vertices)
            if poly is None:
                continue
            # The chords sit above the arc, so a mass whose ARC stayed
            # inside the soil can still have a chord break the surface
            # near an endpoint where the ground curves away. That is the
            # containment rule polylines were given in v0.1.126 (D48),
            # and it is judged here on the surface actually analysed.
            if self._leaves_soil(project, poly):
                continue
            polys.append(poly)
        if not polys:
            return None
        best = self._best_of_masses(project, polys)
        if best is None:
            # Contained, and still no answer: the slicer refused it. That
            # is overwhelmingly the segments-against-slices rule, and it
            # is counted rather than assumed — ``_run`` reports the count.
            self._unsliceable = getattr(self, "_unsliceable", 0) + 1
        return best

    # ------------------------------------------------------------------
    @staticmethod
    def _arc_polyline(circle: SlipCircle, n_vertices: int):
        """``n_vertices`` points on the arc, at equal central angles.

        ``n_vertices`` vertices make ``n_vertices - 1`` segments, which is
        the reference's own counting: "if the Number of vertices = 4, a
        circle will be converted into a piecewise linear surface with 3
        segments".

        Equal CENTRAL ANGLE and not equal x, because on a circle equal
        angle is equal arc length, and "sub-dividing the circular arc
        into approximately equal divisions" is what the conversion is
        defined to be. The difference is not cosmetic: near the
        daylighting ends the arc is steep, and equal-x spacing puts its
        longest chords exactly there, where the surface departs most from
        the circle it claims to approximate.

        ``BaseSearch._as_optimisable`` is NOT reused, for three reasons
        that each disqualify it on their own: it requires a circle whose
        endpoints are already resolved, it samples equal x, and it
        returns n+1 points for an argument of n. Changing it to fit here
        would move the Particle Swarm's multimodal answers, which is a
        different search and six models of the reference bank.

        Returns None if the circle is not resolved onto a chord.
        """
        from ogr_core.geometry import Polyline, Vertex
        from .surface import SlipSurface

        x0, x1 = circle.x_left, circle.x_right
        if x0 is None or x1 is None or not (x1 > x0):
            return None
        cx, cy, r = circle.centre_x, circle.centre_y, circle.radius
        if r <= 0.0:
            return None

        def _theta(x):
            """The angle of the LOWER arc point at ``x``.

            Both endpoints lie below the centre, so theta runs in
            (-pi, 0) and increases monotonically with x along the lower
            arc. No wrap-around to unfold, which is the whole reason the
            interpolation below can be a straight lerp.
            """
            d = r * r - (x - cx) ** 2
            if d < 0.0:
                d = 0.0                 # a rounding-width overshoot at
                # the very ends of the chord, not a geometry error
            return math.atan2(-math.sqrt(d), x - cx)

        th0, th1 = _theta(x0), _theta(x1)
        n = max(3, int(n_vertices))
        pts = []
        for i in range(n):
            th = th0 + (th1 - th0) * i / (n - 1)
            pts.append(Vertex(cx + r * math.cos(th), cy + r * math.sin(th)))
        # The ends are pinned to the resolved chord rather than left to
        # the trigonometry: they are where the surface daylights, and a
        # rounding-width drift there is what puts a first or last slice
        # above its own ground.
        pts[0] = Vertex(x0, cy + r * math.sin(th0))
        pts[-1] = Vertex(x1, cy + r * math.sin(th1))

        surface = SlipSurface(polyline=Polyline(vertices=pts, closed=False))
        # The crack travels with the surface: it moved an endpoint of the
        # mass, and the polyline that replaces it describes the same
        # mechanism or it describes nothing.
        surface.tension_cracks = list(
            getattr(circle, "tension_cracks", []) or [])
        surface.tension_crack_wall = getattr(
            circle, "tension_crack_wall", None)
        return surface


class BlockSearch(BaseSearch):
    """Block Search (non-circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm.
    The sliding mass is treated as active / central / passive "blocks".

    Method (per the Slide documentation):
      1. One random point is generated for each Block Search object. The
         reference REQUIRES the user to draw them; in their absence OGR
         tiles an implicit block region with ``num_groups`` vertical
         windows and samples one point in each. That fallback is ours, not
         the reference's, and it is worth saying so: an unguided random
         search over N free vertices is not the same thing as N windows
         placed by someone who knows where the weak layer runs.
      2. The points are sorted by X-coordinate so the surface is
         kinematically admissible (single-valued, does not reverse).
         That sort is the WHOLE of the admissibility condition; see
         ``_run`` for the two extra filters that used to sit here.
      3. The Left and Right Projection Angles project the surface up to
         the ground surface from the leftmost and rightmost block points.
         Angles are measured CCW from the +x axis (Slide convention):
         the default Left = 135°, Right = 45°. A *range* (start..end)
         may be given, in which case a random angle in the range is
         drawn per surface.
      4. The surface must intersect the slope surface within the Slope
         Limits, otherwise it is discarded.
      5. Repeated for ``num_surfaces`` candidates.

    Options: ``convex_only`` rejects surfaces with a reflex (non-convex)
    vertex, matching the documented "Convex Surfaces Only" checkbox. It is
    the user's option and it is OFF by default, which is why nothing else
    may quietly enforce the same thing.
    """

    def __init__(
        self,
        method,
        num_groups: int = 3,
        left_proj_angle_deg: float = 135.0,
        right_proj_angle_deg: float = 45.0,
        left_start_angle_deg: Optional[float] = None,
        left_end_angle_deg: Optional[float] = None,
        right_start_angle_deg: Optional[float] = None,
        right_end_angle_deg: Optional[float] = None,
        num_surfaces: int = 1000,
        num_slices: int = 30,
        min_area: float = 1.0,
        convex_only: bool = False,
        seed: Optional[int] = None,
        progress_cb=None,
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            **_base_kwargs(legacy_kwargs),
        )
        self.num_groups = max(1, num_groups)
        # Single-angle defaults; ranges override if provided.
        self.left_start = (left_start_angle_deg
                           if left_start_angle_deg is not None
                           else left_proj_angle_deg)
        self.left_end = (left_end_angle_deg
                         if left_end_angle_deg is not None
                         else left_proj_angle_deg)
        self.right_start = (right_start_angle_deg
                            if right_start_angle_deg is not None
                            else right_proj_angle_deg)
        self.right_end = (right_end_angle_deg
                          if right_end_angle_deg is not None
                          else right_proj_angle_deg)
        self.num_surfaces = num_surfaces
        self.min_area = min_area
        self.convex_only = convex_only
        self.seed = seed
        self.progress_cb = progress_cb

    def _run(self, project) -> SearchResult:
        import random
        from ogr_core.geometry import Polyline, Vertex, BoundaryType
        from .surface import SlipSurface

        rng = random.Random(self.seed)
        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)

        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:  # noqa: BLE001
            return result
        dx = xmax - xmin
        dy = ymax - ymin
        if dx < 1e-3 or dy < 1e-3:
            return result

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        ext_verts = ext.polyline.vertices
        top = PathSearch._ground_profile(ext_verts)
        if len(top) < 2:
            return result

        # External polygon for inside-tests
        ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            ext_poly = _Poly([(v.x, v.y) for v in ext_verts])
            if not ext_poly.is_valid:
                ext_poly = ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            ext_poly = None

        # Slope-limits x-range (endpoints must daylight within this)
        if self.slope_limits is not None:
            sl_x0, sl_x1 = sorted(self.slope_limits)
        else:
            sl_x0, sl_x1 = top[0].x, top[-1].x

        # v0.1.17 — collect user-drawn Block Search objects. Each is a
        # Boundary of type BLOCK_SEARCH_OBJECT. Their geometry kind is
        # inferred from the vertex count:
        #   - 1 vertex   → point   (use exactly)
        #   - 2 vertices → line    (sample a random point along it)
        #   - closed 4-vertex → window (sample inside the quad)
        #   - open >2    → polyline (sample a point along it)
        block_objects = [
            b for b in project.boundaries
            if b.btype == BoundaryType.BLOCK_SEARCH_OBJECT
        ]
        use_user_objects = len(block_objects) > 0

        # Block windows: vertical bands over the slope region. Center
        # them on the slope face (the steepest ground segment) so the
        # sampled points fall inside the soil mass, not in the air in
        # front of the toe.
        steepest_i = 0
        steepest = -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            ddy = top[i + 1].y - top[i].y
            if abs(ddx) < 1e-9:
                continue
            sl = abs(ddy / ddx)
            if sl > steepest:
                steepest = sl
                steepest_i = i
        face_lo_x = min(top[steepest_i].x, top[steepest_i + 1].x)
        face_hi_x = max(top[steepest_i].x, top[steepest_i + 1].x)
        face_w = max(face_hi_x - face_lo_x, 1e-6)
        # Windows span from a little before the toe to a little past the
        # crest, where realistic slip surfaces pass.
        #
        # Every fraction below is taken over the MODEL's bounding box, and
        # v0.1.118 leaves them alone deliberately while saying so out loud.
        # They are the same conceptual slip the segment length had — the
        # relief of the model standing in for the height of the slope — and
        # on a model with deep foundation they open a very tall sampling
        # band: 70 m for the four-layer benchmark of Greco (1996) example
        # 4, whose slope is 60 m. But unlike the segment length, these
        # fractions have NO documented value to be corrected to: the
        # reference has the user draw the windows and offers no fallback at
        # all. Changing them would be tuning towards a known answer, which
        # is the one thing that must not happen here. Reported instead.
        x_lo = max(xmin, face_lo_x - 0.3 * face_w)
        x_hi = min(xmax, face_hi_x + 0.5 * face_w)
        y_lo = ymin + 0.05 * dy
        y_hi = ymin + 0.75 * dy

        for ip in range(self.num_surfaces):
            if self.progress_cb and ip % 25 == 0:
                self.progress_cb(ip, self.num_surfaces)

            # 1. one random point per block window (or per user-drawn
            #    Block Search object). Each point must lie INSIDE the
            #    soil mass.
            block_pts = []
            ok = True
            if use_user_objects:
                # Sample one point from each user-drawn search object.
                for bobj in block_objects:
                    pt = self._sample_block_object(bobj, rng)
                    if pt is None:
                        ok = False
                        break
                    px, py = pt
                    # Clip to inside the soil; reject points above ground
                    gy = PathSearch._interpolate_top_y(top, px)
                    if gy is not None and py > gy + 1e-6:
                        ok = False
                        break
                    if ext_poly is not None:
                        from shapely.geometry import Point as _Pt0
                        if not ext_poly.buffer(1e-6 * max(dx, 1.0)).contains(
                                _Pt0(px, py)):
                            ok = False
                            break
                    block_pts.append(Vertex(px, py))
            else:
                # One band per group, and the band is the stand-in for a
                # Block Search Window the user did not draw. Tiling the
                # region is a legitimate arrangement of ``num_groups``
                # windows — the reference lets them overlap, it does not
                # require it — and it is what keeps the sampled vertices
                # spread across the slope instead of clustering.
                #
                # v0.1.118 measured the alternative before keeping this:
                # drawing all ``num_groups`` points from the whole region
                # and sorting them by x, which is what N overlapping
                # windows would give. On the four-layer benchmark of Greco
                # (1996) example 4, 3000 candidates, 2..5 groups:
                #
                #   tiled    1.596973 1.606084 1.668830 1.822153
                #            1852     1623     1214      841  valid
                #   overlap  1.644    1.610    1.603     1.832
                #            1204     1142      831      586  valid
                #
                # The minima differ by less than the noise of a random
                # search and in both directions, while overlapping costs
                # about a third of the yield to near-coincident abscissae.
                # So the tiling stays. The rejection D21 was actually about
                # is the pair of undocumented filters further down.
                for k in range(self.num_groups):
                    bx0 = x_lo + (x_hi - x_lo) * k / self.num_groups
                    bx1 = x_lo + (x_hi - x_lo) * (k + 1) / self.num_groups
                    px = rng.uniform(bx0, bx1)
                    gy = PathSearch._interpolate_top_y(top, px)
                    if gy is None:
                        ok = False
                        break
                    # Named ``cover`` and not ``min_depth``: this is how
                    # far under the ground a sampled vertex must sit, and
                    # ``self.min_depth`` is the Surface Filter, a different
                    # thing applied to the finished mass. The local name
                    # used to shadow it.
                    cover = 0.10 * max(dy, 1.0)
                    hi = min(y_hi, gy - cover)
                    lo = y_lo
                    if hi <= lo:
                        hi = lo + 0.1
                    py = rng.uniform(lo, hi)
                    if ext_poly is not None:
                        from shapely.geometry import Point as _Pt0
                        if not ext_poly.contains(_Pt0(px, py)):
                            ok = False
                            break
                    block_pts.append(Vertex(px, py))
            if not ok or len(block_pts) < 1:
                result.invalid_count += 1
                continue

            # 2. sort by x (kinematic admissibility)
            block_pts.sort(key=lambda v: v.x)

            # 3. projection angles (range → random per surface)
            a_left = math.radians(rng.uniform(
                min(self.left_start, self.left_end),
                max(self.left_start, self.left_end)))
            a_right = math.radians(rng.uniform(
                min(self.right_start, self.right_end),
                max(self.right_start, self.right_end)))

            left_pt = self._project_to_top(
                block_pts[0], a_left, top, xmin, ymax)
            right_pt = self._project_to_top(
                block_pts[-1], a_right, top, xmax, ymax)
            if left_pt is None or right_pt is None:
                result.invalid_count += 1
                continue

            verts = sorted([left_pt] + block_pts + [right_pt],
                           key=lambda v: v.x)
            # dedup near-coincident x
            deduped = [verts[0]]
            for v in verts[1:]:
                if abs(v.x - deduped[-1].x) > 1e-3:
                    deduped.append(v)
            if len(deduped) < 3:
                result.invalid_count += 1
                continue

            # 4. endpoints must daylight within the Slope Limits
            if not (sl_x0 - 1e-6 <= deduped[0].x <= sl_x1 + 1e-6):
                result.invalid_count += 1
                continue
            if not (sl_x0 - 1e-6 <= deduped[-1].x <= sl_x1 + 1e-6):
                result.invalid_count += 1
                continue

            # v0.1.118 — sorting by x IS the kinematic admissibility this
            # search asks for: it is what stops the surface reversing
            # direction, and the reference names no other condition on the
            # generated shape. Two more used to be applied here, both
            # unconditionally and neither documented: interior vertices
            # below the entry-exit chord, and UNIMODALITY (descend to a
            # single minimum, then ascend). They are gone.
            #
            # What they cost, and it is not a matter of taste. Each block
            # point draws its own y independently and uniformly, so the
            # chance that N of them come out unimodal is 2^(N-1)/N! — 1,
            # 0.67, 0.33, 0.13 for N = 2..5. Measured on the four-layer
            # benchmark of Greco (1996) example 4, 3000 candidates each:
            # 1852, 1364, 635, 222 valid, i.e. 1, 0.74, 0.34, 0.12. The
            # filter WAS the acceptance rate. Asking for more groups
            # bought rejection, not freedom, and the reported minimum rose
            # monotonically with the count (defect D21 / anomaly A19-1).
            #
            # The concern they were written for in v0.1.17 — "sawtooth"
            # shapes returning spuriously low factors — is real, and it is
            # now answered where the reference answers it: AFTER the
            # factor converges, by the m-alpha check (on by default since
            # v0.1.89) and the optional Tensile Stress Check. Those two
            # did not exist when these filters were written. Convexity
            # stays, because the reference offers it — as the user's
            # checkbox, not as a standing condition.

            # Convex Surfaces Only filter
            if self.convex_only and len(deduped) >= 3:
                if not self._is_convex_down(deduped):
                    result.invalid_count += 1
                    continue

            # Inside-External validation
            if ext_poly is not None:
                from shapely.geometry import Point as _Pt
                buf = ext_poly.buffer(1e-6 * max(dx, 1.0))
                if any(not buf.contains(_Pt(v.x, v.y)) for v in deduped):
                    result.invalid_count += 1
                    continue

            poly = Polyline(vertices=deduped, closed=False)
            surface = SlipSurface(polyline=poly)
            if self._focus_rejects(surface):
                # v0.1.129 — this search DECLARED ``focus_objects`` since
                # v0.1.55 under a comment saying it applied them before
                # evaluating, and never read the attribute once. Defect
                # D33. Asked before ``evaluate_surface`` because that is
                # where the cost is: 2.18 ms against 0.44 ms to generate,
                # measured on verification problem 78.
                continue
            res = self.evaluate_surface(project, surface)
            if res is None:
                result.invalid_count += 1
                continue
            if res.is_valid and not (0.2 <= res.fos <= 100.0):
                result.invalid_count += 1
                continue
            result.evaluations.append(res)
            if res.is_valid:
                result.valid_count += 1
            else:
                result.invalid_count += 1

        if self.progress_cb:
            self.progress_cb(self.num_surfaces, self.num_surfaces)
        return result

    @staticmethod
    def _sample_block_object(boundary, rng):
        """Sample one point from a Block Search object, per Slide rules.

        point (1 vertex)   → the exact point
        line (2 vertices)  → random point along the segment
        polyline (>2 open) → random point along the polyline
        window (closed quad)→ random point inside the quadrilateral
        Returns (x, y) or None.
        """
        verts = boundary.polyline.vertices
        closed = getattr(boundary.polyline, "closed", False)
        n = len(verts)
        if n == 0:
            return None
        if n == 1:
            return (verts[0].x, verts[0].y)
        if closed and n >= 3:
            # Window: sample inside the polygon via bounding-box rejection
            xs = [v.x for v in verts]
            ys = [v.y for v in verts]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            poly = [(v.x, v.y) for v in verts]
            for _ in range(50):
                px = rng.uniform(x0, x1)
                py = rng.uniform(y0, y1)
                if BlockSearch._point_in_poly(px, py, poly):
                    return (px, py)
            # fallback: centroid
            return (sum(xs) / n, sum(ys) / n)
        # line or open polyline: sample by arc length
        seglens = []
        total = 0.0
        for a, b in zip(verts[:-1], verts[1:]):
            d = math.hypot(b.x - a.x, b.y - a.y)
            seglens.append(d)
            total += d
        if total < 1e-12:
            return (verts[0].x, verts[0].y)
        t = rng.uniform(0.0, total)
        acc = 0.0
        for i, d in enumerate(seglens):
            if acc + d >= t:
                f = (t - acc) / d if d > 1e-12 else 0.0
                a, b = verts[i], verts[i + 1]
                return (a.x + f * (b.x - a.x), a.y + f * (b.y - a.y))
            acc += d
        return (verts[-1].x, verts[-1].y)

    @staticmethod
    def _point_in_poly(x, y, poly) -> bool:
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _is_convex_down(verts) -> bool:
        """True if the polyline is convex when viewed as a slip surface
        (no interior vertex makes a reflex angle pointing downward — the
        cross-products of consecutive edges keep a consistent sign)."""
        sign = 0
        for i in range(1, len(verts) - 1):
            ax = verts[i].x - verts[i - 1].x
            ay = verts[i].y - verts[i - 1].y
            bx = verts[i + 1].x - verts[i].x
            by = verts[i + 1].y - verts[i].y
            cross = ax * by - ay * bx
            if abs(cross) < 1e-12:
                continue
            s = 1 if cross > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
        return True

    @staticmethod
    def _project_to_top(
        start, angle_rad: float, top_verts, x_clip: float, y_clip: float,
    ):
        """March from `start` in the given direction until we cross the
        top profile of the External, return the intersection point."""
        from ogr_core.geometry import Vertex
        x0, y0 = start.x, start.y
        cx, sy = math.cos(angle_rad), math.sin(angle_rad)
        step = 0.5
        max_iters = 10000
        t = 0.0
        prev_above = None
        for _ in range(max_iters):
            t += step
            x = x0 + t * cx
            y = y0 + t * sy
            if x < min(top_verts[0].x, x_clip) - 1.0:
                return None
            if x > max(top_verts[-1].x, x_clip) + 1.0:
                return None
            if y > y_clip + 1.0:
                return None
            top_y = PathSearch._interpolate_top_y(top_verts, x)
            if top_y is None:
                continue
            now_above = y > top_y
            if prev_above is not None and now_above != prev_above:
                return Vertex(x, top_y)
            prev_above = now_above
            if t == step and y > top_y:
                return Vertex(x0, top_y)
        return None


def toe_frame_angle_deg(absolute_deg: float, to_right: bool) -> float:
    """An absolute slip-surface angle, expressed in the toe-to-crest frame.

    The *Initial Angle at Toe* limits are stated as absolute angles,
    measured counter-clockwise from the positive x axis. The Path Search
    generator works in a local frame whose +x runs from the toe towards
    the crest, so for a slope whose crest lies to the LEFT the frame is
    the model's mirrored in x, and a direction at absolute angle t sits at
    180 − t in it.

    The reference states the same thing as a user-facing equivalence: an
    upper angular limit of 30 degrees for a right-to-left failure "is
    equivalent to" 150 degrees for a left-to-right one. 180 − 150 = 30,
    which is this function and is what the test pins.
    """
    return absolute_deg if to_right else 180.0 - absolute_deg


class PathSearch(BaseSearch):
    """Path Search (non-circular) — XSTABL "Irregular Surface Search".

    v0.1.17 — reimplemented to follow the algorithm documented by
    Rocscience for Slide2, which is itself modelled on the "Irregular
    Surface Search" of the slope-stability program XSTABL. The previous
    (v0.1.15/16) implementation used a unimodal depth-profile heuristic
    that produced reasonable shapes but did not match the documented
    method. The XSTABL method is:

    1. **Initiation point** — randomly generated on the ground surface
       within the toe-side HALF of the Slope Limits. The slide ALWAYS
       starts at the toe and progresses towards the crest, regardless of
       the Failure Direction. Until v0.1.118 the window was derived from
       the slope FACE instead, and on a model with a bench in front of the
       toe that excluded the answer — see ``_run``.

    2. **First segment** — emitted from the initiation point at a random
       *Initial Angle at Toe*. The default angular window is
       [45° below horizontal, (β − 5°)], where β is the inclination of
       the ground-surface segment at the initiation point. Angles follow
       Slide's convention (CCW-positive from +x axis); for a
       right-to-left failure the surface descends into the slope.

    3. **Subsequent segments** — each of fixed ``segment_length``
       (default ≈ 0.3·H, H = the height of the SLOPE, which is the relief
       of the ground profile between the Slope Limits and NOT the relief
       of the model — see ``_run``). The direction of each new
       segment is drawn randomly but constrained to keep the surface
       *kinematically admissible* (concave-up: the segment angle rotates
       monotonically upward, never folding back down). This is the XSTABL
       admissibility rule and prevents the "impossible" wavy surfaces.

    4. **Termination** — the surface is grown until it re-emerges on the
       ground surface. The exit point must lie within the Slope Limits,
       otherwise the surface is discarded: the limits FILTER the endpoint,
       they do not place it.

    5. **Minimum Elevation** — no vertex may go below the lower limit of
       the External boundary (or a user Minimum Elevation).

    6. **Optimize Surfaces** is NOT part of this search. Until v0.1.104
       it was: a private random walk over the best five surfaces, run
       unconditionally because the field that switched it on defaulted to
       True and no dialog ever showed it, while the "Optimize Surfaces"
       checkbox of the Path Search panel wrote a setting no analysis read.
       There is now one optimisation, in ``BaseSearch.run``, driven by
       that checkbox, and every non-circular search reaches it the same
       way. See ``ogr_slip2d.optimize`` and defect D08.

    All randomness is reproducible when ``seed`` is given (Slide's
    Pseudo-Random mode).
    """

    def __init__(
        self,
        method,
        # The reference calls this "Number of Surfaces" and means the count
        # of VALID surfaces; the loop below stops on exactly that, so the
        # two names were the same quantity all along. It was called
        # ``num_paths`` until v0.1.103, which is why the settings field the
        # user edits and the one the engine read could drift apart.
        num_surfaces: int = 5000,
        num_slices: int = 30,
        # v0.1.129 — the ONLY search of the seven that did not name this,
        # so ``build_search`` could not hand it one and the line below
        # pinned it at 1.0 whatever the project said. A user who set 50 to
        # clear the shallow skins off a Path Search got the identical
        # number back. Defect D51.
        min_area: float = 1.0,
        segment_length: Optional[float] = None,
        # ``None`` on either angle means AUTOMATIC. A value is an ABSOLUTE
        # angle, counter-clockwise from the model's +x axis; ``_run``
        # converts it into the toe-to-crest frame the generator works in.
        initial_angle_upper_deg: Optional[float] = None,
        initial_angle_lower_deg: Optional[float] = None,
        min_elevation: Optional[float] = None,
        convex_only: bool = False,
        # ``slope_limits`` arrives through ``**legacy_kwargs`` and
        # ``_base_kwargs``, like every other project-level setting. It is
        # not optional decoration here: this search is DEFINED in terms of
        # the limits — they bound the initiation range and they filter the
        # exit point — and until v0.1.118 it had no such argument at all,
        # so a user who narrowed them to steer a Path Search moved nothing
        # and was not told. Defect D21 / anomaly A19-1.
        seed: Optional[int] = None,
        progress_cb=None,
        max_segments: int = 30,
        max_attempts_factor: int = 20,
        **legacy_kwargs,
    ) -> None:
        # ``min_elevation`` is this search's OWN named argument and wins
        # over whatever ``_base_kwargs`` would default it to: Path Search
        # has used it since it was written as the floor of its vertex
        # sampling (``_y_floor``), and it is the same elevation the base
        # class now filters on. Passing it here makes the two agree —
        # generation stays above the floor AND anything that slipped below
        # it anyway is discarded, which is what the filter promises.
        # Pre-v0.1.103 name for the same count.
        if "num_paths" in legacy_kwargs:
            num_surfaces = legacy_kwargs.pop("num_paths")
        _base = _base_kwargs(legacy_kwargs)
        _base["min_elevation"] = min_elevation
        super().__init__(
            method=method, num_slices=num_slices, min_area=min_area,
            **_base,
        )
        self.num_surfaces = num_surfaces
        # v0.1.24 — cap on generation attempts (num_surfaces × factor)
        self.max_attempts_factor = max(1, max_attempts_factor)
        # segment_length None → auto (0.3·H) computed in run()
        self.segment_length = segment_length
        self.initial_angle_upper_deg = initial_angle_upper_deg
        self.initial_angle_lower_deg = initial_angle_lower_deg
        self.convex_only = convex_only
        self.seed = seed
        self.progress_cb = progress_cb
        self.max_segments = max(5, max_segments)
        # Back-compat: older callers passed num_vertices / min_area /
        # min_angle_deg / max_angle_deg. Absorb silently.
        self.num_vertices = legacy_kwargs.get("num_vertices", 8)
        if "min_angle_deg" in legacy_kwargs:
            self.initial_angle_lower_deg = legacy_kwargs["min_angle_deg"]
        # v0.1.103 — ``max_angle_deg`` was absorbed and then never read, so
        # a caller passing it got the automatic upper limit and no warning.
        if "max_angle_deg" in legacy_kwargs:
            self.initial_angle_upper_deg = legacy_kwargs["max_angle_deg"]
        # External polygon + ground profile, set in run()
        self._ext_poly = None
        self._top = None
        self._y_floor = None

    # ------------------------------------------------------------------
    def _run(self, project) -> SearchResult:
        import random
        from ogr_core.geometry import BoundaryType, Polyline, Vertex
        from .surface import SlipSurface

        rng = random.Random(self.seed)
        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        ext_verts = ext.polyline.vertices
        if len(ext_verts) < 3:
            return result

        # Ground profile (real upper contour, sorted by x)
        top = self._ground_profile(ext_verts)
        if len(top) < 2:
            return result
        self._top = top

        # External polygon for inside-tests
        self._ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            self._ext_poly = _Poly([(v.x, v.y) for v in ext_verts])
            if not self._ext_poly.is_valid:
                self._ext_poly = self._ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            self._ext_poly = None

        x_left = top[0].x
        x_right = top[-1].x
        y_min = min(v.y for v in ext_verts)
        self._y_floor = (self.min_elevation if self.min_elevation is not None
                         else y_min)

        # Slope Limits — the stretch of ground within which a surface may
        # daylight. Automatic (None) means the whole ground profile, which
        # is where the reference puts the two markers when the External
        # Boundary is created.
        if self.slope_limits is not None:
            sl_x0, sl_x1 = sorted(self.slope_limits)
            sl_x0 = max(sl_x0, x_left)
            sl_x1 = min(sl_x1, x_right)
            if sl_x1 - sl_x0 <= 1e-9:
                return result
        else:
            sl_x0, sl_x1 = x_left, x_right

        # v0.1.118 — H is the height of the SLOPE, not of the model, and
        # the difference is the whole of defect D21 on this search. The
        # recommendation the segment length follows is "approximately 0.3H,
        # where H is the maximum height of the slope"; ``y_max - y_min``
        # over the External Boundary measures instead the model's total
        # relief, which includes every metre of FOUNDATION under the toe —
        # soil the slip surface may pass through but that is no part of any
        # slope. On the four-layer benchmark of Greco (1996) example 4 the
        # slope is 60 m over 40 m of foundation, so the old reading gave
        # 100: segments of 30 m, eight vertices for a 150 m mass, and a
        # polyline too coarse to follow the arc it was competing with. The
        # same critical circle read 1.4332 as an arc and 1.4470 in eight
        # chords — the whole of the gap the anomaly reported.
        #
        # The relief of the GROUND PROFILE is the faithful measure, and it
        # is taken between the Slope Limits because that is the slope being
        # searched. Not ``crest.y - toe.y`` of the steepest face: on a
        # benched slope the steepest face is one bench, not the slope.
        ys = [v.y for v in top if sl_x0 - 1e-9 <= v.x <= sl_x1 + 1e-9]
        for xe in (sl_x0, sl_x1):
            ye = self._interpolate_top_y(top, xe)
            if ye is not None:
                ys.append(ye)
        H = (max(ys) - min(ys)) if ys else 0.0

        # Segment length default ≈ 0.3 H (see above for what H is)
        seg_len = self.segment_length
        if seg_len is None or seg_len <= 0:
            seg_len = max(0.3 * H, (sl_x1 - sl_x0) * 0.05, 1e-3)

        # Locate the slope face (steepest ground segment) → defines the
        # toe / crest and the Slope-Limits ranges.
        #
        # v0.1.73 — with a strict ``>`` the FIRST steepest segment won,
        # so a symmetric embankment (two faces of equal inclination)
        # always chose the LEFT one, by iteration order and nothing else.
        # That is the one place in this search where the geometry really
        # is ambiguous, and where the Failure Direction is the missing
        # information rather than a second opinion on something already
        # answered: everything below still derives the toe as the lower
        # end of the chosen face, because the reference is explicit that
        # Path Search starts at the toe regardless of the direction.
        slopes = []
        for i in range(len(top) - 1):
            dx = top[i + 1].x - top[i].x
            dy = top[i + 1].y - top[i].y
            if abs(dx) < 1e-9:
                continue
            slopes.append((i, abs(dy / dx)))
        steepest_i = 0
        if slopes:
            steepest = max(s for _, s in slopes)
            # Near-ties only. A face that is genuinely the steepest keeps
            # winning whatever the direction is set to, so an ordinary
            # single-face slope cannot be changed by this setting.
            tied = [i for i, s in slopes if s >= steepest * (1.0 - 1e-6)]
            if len(tied) > 1:
                from .failure_direction import crest_is_on_the_right
                # The mass exits at the toe, so pick the face whose toe
                # lies on the side it is declared to move towards: the
                # left-hand face for a right-to-left failure.
                def _toe_x(i):
                    a, b = top[i], top[i + 1]
                    return a.x if a.y <= b.y else b.x
                steepest_i = (min(tied, key=_toe_x)
                              if crest_is_on_the_right(project)
                              else max(tied, key=_toe_x))
            else:
                steepest_i = tied[0]
        face_a = top[steepest_i]
        face_b = top[steepest_i + 1]
        # Slope angle β (magnitude) of the face
        beta = math.atan2(abs(face_b.y - face_a.y),
                          abs(face_b.x - face_a.x))
        beta_deg = math.degrees(beta)
        # left_low: True if the toe is on the LEFT (ground rises to the
        # right). The toe is the lower end of the slope face.
        left_low = face_a.y <= face_b.y
        toe_pt = face_a if face_a.y <= face_b.y else face_b
        crest_pt = face_b if face_a.y <= face_b.y else face_a
        # Failure progresses from toe to crest. The slip surface moves
        # horizontally from the toe towards the crest.
        to_right = crest_pt.x > toe_pt.x  # crest is to the right of toe

        face_lo_x = min(face_a.x, face_b.x)
        face_hi_x = max(face_a.x, face_b.x)
        face_w = max(face_hi_x - face_lo_x, 1e-6)

        # Initiation range: the HALF of the Slope Limits closest to the toe.
        #
        # v0.1.118 — this is the documented rule, and it replaces a window
        # of our own that was derived from the slope FACE:
        # ``[toe - 0.15 w, toe + 0.55 w]``. The two are not close. On the
        # four-layer benchmark of Greco (1996) example 4 the face rule gave
        # [42, 126] while the reference gives [0, 130] — and the manual
        # PUBLISHES the entry point of the critical surface it found, at
        # x = 39.18, which the face rule can never sample. Nor can it reach
        # x = 29.37, where the critical circle of the ordinary grid search
        # on the same model daylights. The search was not returning a worse
        # surface than the grid: it was forbidden from starting where the
        # answer starts, and its own minimum came out pinned against the
        # left edge of the window, which is what a clipped optimum looks
        # like. Defect D21 / anomaly A19-1.
        sl_mid = 0.5 * (sl_x0 + sl_x1)
        if toe_pt.x <= sl_mid:
            init_x0, init_x1 = sl_x0, sl_mid
        else:
            init_x0, init_x1 = sl_mid, sl_x1

        # The endpoint is FILTERED by the Slope Limits and nothing else:
        # "the Slope Limits do not influence the location of the endpoint,
        # but are used as a filter". ``crest_target`` is a separate matter —
        # it steers the turn-up schedule below, is a heuristic of ours with
        # no counterpart in the reference, and keeps the crest-side window
        # it has always used so that only the FILTER changes here.
        if to_right:
            crest_target = 0.5 * ((crest_pt.x - 0.55 * face_w)
                                  + min(x_right, crest_pt.x + 0.6 * face_w))
        else:
            crest_target = 0.5 * (max(x_left, crest_pt.x - 0.6 * face_w)
                                  + (crest_pt.x + 0.55 * face_w))

        # Initial-angle window (radians), in the local toe-to-crest frame:
        # +x runs from the toe towards the crest.
        #
        # v0.1.103 — the limits ARRIVE as absolute angles, counter-clockwise
        # from the model's +x axis, because that is the convention the
        # control the user edits is stated in. The reference makes the frame
        # change explicit: an upper limit of 30 degrees for a right-to-left
        # failure "is equivalent to" 150 degrees for a left-to-right one.
        # That equivalence IS the reflection below — mirroring x maps an
        # absolute angle t onto 180 − t here, and 180 − 150 = 30.
        #
        # Before v0.1.103 the settings stored this frame directly, under a
        # name the interface never showed, so the angle boxes the user could
        # tick reached nothing at all.
        # Lower = 45° below horizontal, i.e. diving into the slope.
        ang_lo = math.radians(
            toe_frame_angle_deg(self.initial_angle_lower_deg, to_right)
            if self.initial_angle_lower_deg is not None else -45.0)
        if self.initial_angle_upper_deg is not None:
            ang_hi = math.radians(
                toe_frame_angle_deg(self.initial_angle_upper_deg, to_right))
        else:
            # v0.1.24 FIX (anomaly A1): the documented Upper Angle is
            # +(β − 5)°, NOT −(β − 5)°. In this local frame the +x axis
            # points from the toe towards the crest, so a POSITIVE angle
            # means the first segment RISES as it advances into the
            # slope — which is exactly what a toe-exiting slip surface
            # does (its base is shallow at the toe and steepens towards
            # the crest). Negating the limit collapsed the admissible
            # window to a ~5° sliver of steeply-diving directions
            # ([−45°, −40°] for a 45° face), making the true critical
            # surface geometrically impossible to generate: 97 % of
            # paths were discarded and the reported FoS was ~1.60
            # instead of ~0.88.
            ang_hi = math.radians(max(beta_deg - 5.0, 5.0))
        if ang_lo > ang_hi:
            ang_lo, ang_hi = ang_hi, ang_lo

        # v0.1.24 — per the documented behaviour, "Number of Surfaces" is
        # the number of VALID surfaces generated: invalid ones are
        # discarded and do NOT count towards the total. We therefore keep
        # generating until num_surfaces valid surfaces exist, capped at
        # max_attempts_factor× attempts so a pathological model cannot
        # spin forever.
        attempts = 0
        max_attempts = self.num_surfaces * self.max_attempts_factor
        while (result.valid_count < self.num_surfaces
               and attempts < max_attempts):
            ip = attempts
            attempts += 1
            if self.progress_cb and ip % 25 == 0:
                self.progress_cb(min(result.valid_count, self.num_surfaces),
                                 self.num_surfaces)
            verts = self._generate_path_xstabl(
                rng, top, init_x0, init_x1, sl_x0, sl_x1, crest_target,
                seg_len, ang_lo, ang_hi, to_right, self._y_floor,
            )
            if verts is None or len(verts) < 3:
                result.invalid_count += 1
                continue
            poly = Polyline(vertices=verts, closed=False)
            surface = SlipSurface(polyline=poly)
            if self._focus_rejects(surface):
                # v0.1.129 — this search did not even ACCEPT a focus
                # object, so the ten non-circular models of the reference
                # bank whose two cases differ only by their focus were the
                # same calculation twice. Defect D33.
                #
                # The rejection stays inside the ``max_attempts`` budget
                # rather than getting one of its own: a focus deliberately
                # narrows the space, so it is right that fewer valid
                # surfaces come out of the same effort. Measured on
                # problem 78, a tangent focus passes 2.2 % of what the
                # generator produces, and rejecting HERE rather than after
                # the solve is what keeps that a x3 and not a x45.
                continue
            res = self.evaluate_surface(project, surface)
            if res is None:
                result.invalid_count += 1
                continue
            if res.is_valid and not (0.2 <= res.fos <= 100.0):
                result.invalid_count += 1
                continue
            result.evaluations.append(res)
            if res.is_valid:
                result.valid_count += 1
            else:
                result.invalid_count += 1

        if self.progress_cb:
            self.progress_cb(self.num_surfaces, self.num_surfaces)
        result.attempts = attempts
        return result

    # ------------------------------------------------------------------
    def _generate_path_xstabl(
        self, rng, top, init_x0, init_x1, sl_x0, sl_x1, crest_target,
        seg_len, ang_lo, ang_hi, to_right, y_floor,
    ):
        """Grow one irregular surface following the XSTABL method.

        Returns a left-to-right-ordered list of Vertex, or None if the
        surface is invalid (doesn't re-emerge within the Slope Limits,
        goes below the floor, or exceeds the segment budget).
        """
        from ogr_core.geometry import Vertex

        # 1. Initiation point on the ground surface
        x_start = rng.uniform(init_x0, init_x1)
        y_start = self._interpolate_top_y(top, x_start)
        if y_start is None:
            return None

        # 2. First segment: random initial angle in the window. The
        #    horizontal march direction is from toe towards crest.
        hdir = 1.0 if to_right else -1.0
        angle = rng.uniform(ang_lo, ang_hi)  # negative = descending
        # Per-surface "depth aggressiveness": controls how long the
        # surface stays deep before turning up. Low → shallow surfaces,
        # high → deep surfaces. Sampling a range gives a good spread of
        # candidate depths so the search finds the true critical one.
        depth_factor = rng.uniform(0.55, 1.6)
        # Build the surface as a list of points marching towards crest.
        pts = [(x_start, y_start)]
        cx, cy = x_start, y_start
        prev_angle = angle
        max_seg = self.max_segments
        emerged = False

        for seg in range(max_seg):
            # March horizontally towards the crest by seg_len projected.
            dx = hdir * seg_len * math.cos(angle)
            dy = seg_len * math.sin(angle)
            nx, ny = cx + dx, cy + dy

            # Floor check
            if ny < y_floor - 1e-9:
                # Clamp the descent: don't go below the floor
                return None

            # Has it re-emerged at/above the ground surface?
            ty = self._interpolate_top_y(top, nx)
            if ty is not None and ny >= ty - 1e-6:
                # Interpolate the exact crossing on the last segment so
                # the surface ends exactly on the ground.
                # Linear solve along the segment for y == ground.
                cross = self._segment_ground_crossing(
                    cx, cy, nx, ny, top)
                if cross is not None:
                    pts.append(cross)
                    emerged = True
                    break
                else:
                    pts.append((nx, ty))
                    emerged = True
                    break

            pts.append((nx, ny))
            cx, cy = nx, ny

            # 3. Next segment angle: rotate upward (towards the crest)
            #    monotonically to stay concave-up / admissible. The turn
            #    rate adapts so the surface aims to re-emerge near the
            #    crest: the closer the horizontal distance to the exit
            #    range, the more strongly it turns up. This keeps the
            #    XSTABL admissibility (monotone upward rotation) while
            #    greatly improving the fraction of surfaces that emerge
            #    inside the Slope Limits.
            remaining = abs(crest_target - cx)
            total = abs(crest_target - x_start) + 1e-9
            progress = max(0.0, min(1.0, 1.0 - remaining / total))
            # depth_factor < 1 → turns up sooner (shallow); > 1 → stays
            # deeper longer (deep-seated). Raising progress to this power
            # shifts the whole turn-up schedule.
            sched = progress ** depth_factor
            target_angle = ang_lo + sched * (math.radians(55.0) - ang_lo)
            jitter = rng.uniform(-0.12, 0.18)
            angle = max(prev_angle, target_angle + jitter)  # monotone up
            angle = min(angle, math.radians(80.0))
            prev_angle = angle

        if not emerged or len(pts) < 3:
            return None

        # 4. The endpoint must daylight WITHIN THE SLOPE LIMITS. That is
        #    the whole of the rule: the limits filter the endpoint, they do
        #    not place it.
        ex = pts[-1][0]
        if not (sl_x0 - 1e-6 <= ex <= sl_x1 + 1e-6):
            return None

        # Order left→right
        if pts[0][0] > pts[-1][0]:
            pts = pts[::-1]
        # Enforce strict x-monotonicity (XSTABL surfaces are single-valued
        # in x). Drop any backtracking points.
        mono = [pts[0]]
        for p in pts[1:]:
            if p[0] > mono[-1][0] + 1e-9:
                mono.append(p)
        if len(mono) < 3:
            return None

        # 5. Inside-External validation (definitive guard)
        if self._ext_poly is not None:
            from shapely.geometry import Point as _Pt
            buf = self._ext_poly.buffer(1e-6 * max(
                abs(mono[-1][0] - mono[0][0]), 1.0))
            for (px, py) in mono:
                if not buf.contains(_Pt(px, py)):
                    return None

        # 6. Optional convex-only filter (concave-up admissibility vs the
        #    entry-exit chord)
        if self.convex_only:
            x0, y0 = mono[0]
            xn, yn = mono[-1]
            if xn - x0 > 1e-9:
                for (px, py) in mono[1:-1]:
                    t = (px - x0) / (xn - x0)
                    if py > y0 + t * (yn - y0) + 1e-6:
                        return None

        return [Vertex(px, py) for (px, py) in mono]

    @staticmethod
    def _segment_ground_crossing(x0, y0, x1, y1, top):
        """Find where the segment (x0,y0)->(x1,y1) first crosses the
        ground profile, returning (x, y) or None."""
        # Sample the segment and the ground; find sign change of
        # (seg_y - ground_y).
        N = 12
        prev_t = 0.0
        prev_diff = None
        for i in range(N + 1):
            t = i / N
            sx = x0 + t * (x1 - x0)
            sy = y0 + t * (y1 - y0)
            gy = PathSearch._interpolate_top_y(top, sx)
            if gy is None:
                prev_diff = None
                prev_t = t
                continue
            diff = sy - gy
            if prev_diff is not None and prev_diff < 0 <= diff:
                # Crossing between prev_t and t — bisect a little
                a, b = prev_t, t
                for _ in range(20):
                    m = 0.5 * (a + b)
                    mx = x0 + m * (x1 - x0)
                    my = y0 + m * (y1 - y0)
                    mg = PathSearch._interpolate_top_y(top, mx)
                    if mg is None:
                        break
                    if my - mg < 0:
                        a = m
                    else:
                        b = m
                mx = x0 + b * (x1 - x0)
                mg = PathSearch._interpolate_top_y(top, mx)
                return (mx, mg if mg is not None else y1)
            prev_diff = diff
            prev_t = t
        return None

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _ground_profile(ext_verts):
        """Real upper contour of the External (not the convex hull),
        sorted by x. For each distinct x, the maximum y over all edges.

        v0.1.84 — delegates to :func:`ogr_core.geometry.ground_surface`.
        This was the only one of the project's three ground-surface
        implementations that walked the edges rather than the vertices, so
        it is the one the shared function generalises; keeping a private
        copy here would have re-created the divergence that produced the
        Ej_2 anomaly.
        """
        from ogr_core.geometry import ground_surface
        if len(ext_verts) < 3:
            return list(ext_verts)
        return list(ground_surface(list(ext_verts)).vertices)

    @staticmethod
    def _interpolate_top_y(top_verts, x: float) -> Optional[float]:
        """Ground elevation at ``x`` on a profile from ``_ground_profile``.

        v0.1.114 — through :func:`envelope_y_at`. The profile steps at a
        vertical face, and returning on the first segment that spans ``x``
        answered with the branch the winding happened to put first: at the
        foot of a wall, the bench in front of it instead of its crest.
        """
        from ogr_core.geometry import Polyline, envelope_y_at
        if x < top_verts[0].x - 1e-9 or x > top_verts[-1].x + 1e-9:
            return None
        return envelope_y_at(Polyline(vertices=list(top_verts)), x)



class SimulatedAnnealingSearch(BaseSearch):
    """Hybrid Simulated Annealing (HSA) Search for non-circular surfaces.

    Implements the algorithm from:
        Su, X. (2009). Global Optimization of General Failure Surfaces
        in Slope Analysis by Hybrid Simulated Annealing.
        University of Waterloo / Rocscience Inc.

    HSA = VFSA (Very Fast Simulated Annealing) + LMC (Local Monte-Carlo).

    Phase 1 — VFSA (global search):
      - Control variables: x_2..x_{N-1} and y_2..y_{N-1} parameterized
        to [0, 1] (endpoints x_1, x_N are fixed on the slope; y_1, y_N
        are computed by interpolating the External top profile at those x)
      - Bounds for x: each x_m lives in division [D_{m-1}, D_m]
      - Bounds for y: dynamic — depend on neighbouring vertices
        (Cheng 2007). y_m_min = ymin of bbox, y_m_max = min(slope,
        line through neighbours) so we don't generate self-intersecting
        surfaces by default.
      - State generation: Cauchy distribution
            r = sgn(u-0.5) · T_gen · [(1 + 1/T_gen)^|2u-1| - 1]
      - Acceptance: 1 / (1 + exp(dE/T_accept))
      - Schedule: T_k = T_0 · exp(-c · k^(1/n)), c = 8 by default
        (Su 2009 section 2.1.6, eqs. 10-11; 1 to 10 all adequate)
      - Ratio control: if accept/reject ratio > 2 → halve T_accept
        (more selective); if < 0.5 → double it (less selective)

    Phase 2 — LMC (local refinement, Greco 1996):
      - For each vertex, try 8 directional moves (N_x, N_y) ∈ {-1,0,1}²
      - On success, repeat the same direction (extrapolation)
      - On failure for all 8 directions of one vertex, shrink that
        vertex's step size by factor (1 - eps), eps=0.75 default
      - Stop when all step sizes < tolerance OR no improvement after
        a full pass over all vertices
      - The two EXTREMITIES move too (v0.1.119), in x only, with their
        y read off the ground profile so they keep daylighting; their
        travel is bounded by the Slope Limits. Su (2009) section 2.1
        counts n = 2N - 2 for exactly this reason.

    What the search may STEER by, and it is not the same as what it may
    evaluate: only surfaces that survive the post-analysis checks. See
    :meth:`_steer` — until v0.1.119 it steered by all of them, including
    the ones :attr:`SearchResult.critical` refuses to report, and that was
    defect D22.

    Convex-only mode: rejects candidate surfaces whose curvature
    changes sign (kappa < 0 anywhere), preserving downward-concave
    failure shapes typical of weak-layer slopes.
    """

    def __init__(
        self,
        method,
        initial_vertices: int = 9,
        generation_steps: int = 200,
        tolerance: float = 1e-3,
        # n_eps of the stopping criterion — Su (2009) section 2.1.7: the
        # search stops when the global optimum has not improved by more
        # than the tolerance in n_eps consecutive outer runs. Section 3.1
        # adopts N_eps = 5, which is also what the setting declares; until
        # v0.1.131 the loop broke on a hand-written 3 and nobody read the
        # setting at all (D07c(a)).
        num_fos_compared_before_stopping: int = 5,
        # c in T_k = T_0 exp(-c k^(1/n)) — Su (2009) section 2.1.6, eqs.
        # (10)-(11). Was called ``temperature_factor`` and defaulted to a
        # geometric cooling rate of 0.97 until v0.1.103; that value was
        # stored, clamped and never read, while the schedule below used a
        # hard-coded 8.0.
        temperature_coefficient: float = 8.0,
        convex_only: bool = False,
        num_slices: int = 30,
        min_area: float = 1.0,
        seed: Optional[int] = 1234,
        progress_cb=None,
        **legacy_kwargs,
    ) -> None:
        # Pre-v0.1.103 name, and it held a DIFFERENT quantity: a geometric
        # cooling rate, not the c of the exponential schedule. 0.97 and 8.0
        # are not one number in two units, so there is nothing to convert —
        # and absorbing it in silence is exactly how it came to be stored,
        # clamped and never read for eighty-odd versions.
        if "temperature_factor" in legacy_kwargs:
            raise TypeError(
                "temperature_factor was a geometric cooling rate and no "
                "analysis ever read it. Pass temperature_coefficient "
                "instead: it is the c of T_k = T_0 exp(-c k^(1/n)), which "
                "the schedule does use (Su 2009, section 2.1.6).")
        super().__init__(
            method=method, num_slices=num_slices,
            **_base_kwargs(legacy_kwargs),
        )
        self.seed = seed
        self.initial_vertices = max(4, initial_vertices)
        self.generation_steps = max(10, generation_steps)
        self.tolerance = tolerance
        # Below 1 it is not a criterion: it would stop without having
        # compared the optimum against anything.
        self.num_fos_compared_before_stopping = max(
            1, int(num_fos_compared_before_stopping))
        # Su (2009) reports 1.0 to 10.0 as the adequate range and adopts
        # 8.0; the bounds keep a stored value inside it.
        self.temperature_coefficient = max(1.0, min(10.0,
                                                    temperature_coefficient))
        self.convex_only = convex_only
        self.min_area = min_area
        self.progress_cb = progress_cb

    # ==================================================================
    # Top-level: HSA = VFSA + LMC
    # ==================================================================
    def _run(self, project) -> SearchResult:
        result = SearchResult(method_id=self.method.METHOD_ID,
                              objective=self.objective)
        # v0.1.119 — a generator of its OWN, not ``random.seed()`` on the
        # module. The old line reproduced (it re-seeded on every run, so two
        # runs agreed) and still broke rule 5: it left the process-wide
        # stream wherever the annealing happened to leave it, so anything
        # drawing from ``random`` afterwards — another search, a
        # probabilistic sampler, a test — inherited a state decided by this
        # one. Reproducibility and non-interference are two properties, and
        # only the first one was ever checked.
        import random as _random
        rng = _random.Random(self.seed)
        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:
            return result
        dx = xmax - xmin
        dy = ymax - ymin
        if dx < 1e-3 or dy < 1e-3:
            return result

        # External top profile (slope ground line)
        from ogr_core.geometry import BoundaryType
        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        # Real ground profile (upper contour), reused from PathSearch.
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if len(top) < 2:
            return result

        # External polygon for inside-tests
        self._ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            self._ext_poly = _Poly(
                [(v.x, v.y) for v in ext.polyline.vertices])
            if not self._ext_poly.is_valid:
                self._ext_poly = self._ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            self._ext_poly = None

        # Locate the slope face (steepest ground segment) → toe / crest.
        steepest_i = 0
        steepest = -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            ddy = top[i + 1].y - top[i].y
            if abs(ddx) < 1e-9:
                continue
            s = abs(ddy / ddx)
            if s > steepest:
                steepest = s
                steepest_i = i
        face_a = top[steepest_i]
        face_b = top[steepest_i + 1]
        toe_pt = face_a if face_a.y <= face_b.y else face_b
        crest_pt = face_b if face_a.y <= face_b.y else face_a

        # Fixed slip-surface endpoints near the toe and crest of the
        # slope face (the surface daylights here). These bracket the
        # SA's inner vertices.
        N = self.initial_vertices
        x1 = min(toe_pt.x, crest_pt.x)
        xN = max(toe_pt.x, crest_pt.x)

        # v0.1.119 — and the Slope Limits bracket the bracket. They used to
        # reach this search only as the mass filter in ``_best_of_masses``,
        # so a project that narrowed them past the toe or the crest got NO
        # SURFACE AT ALL: phase 1 kept starting from a pair of endpoints
        # outside the limits and every candidate it built was thrown away
        # after being analysed. A filter the generator does not know about
        # is a filter that can reject an entire search, which is the shape
        # of D21's Block Search finding as well.
        if self.slope_limits is not None:
            sl_lo, sl_hi = sorted(self.slope_limits)
            x1, xN = max(x1, sl_lo), min(xN, sl_hi)
            if xN - x1 < 1e-9:
                return result

        # Phase 1 — VFSA
        best_verts, best_fos = self._vfsa(
            project, result, x1, xN, ymin, ymax, top, N, dx, dy, rng,
        )

        # Phase 2 — LMC (local refinement, only if VFSA produced something)
        if best_verts is not None:
            best_verts, best_fos = self._lmc(
                project, result, best_verts, best_fos, ymin, ymax, top, dx,
                rng,
            )

        if self.progress_cb:
            self.progress_cb(self.generation_steps, self.generation_steps)
        return result

    # ==================================================================
    # Helpers
    # ==================================================================
    @staticmethod
    def _interp_top_y(top, x):
        if x < top[0].x or x > top[-1].x:
            return None
        for v1, v2 in zip(top[:-1], top[1:]):
            if v1.x <= x <= v2.x:
                if abs(v2.x - v1.x) < 1e-12:
                    return (v1.y + v2.y) / 2.0
                t = (x - v1.x) / (v2.x - v1.x)
                return v1.y + t * (v2.y - v1.y)
        return None

    @staticmethod
    def _is_convex(verts):
        """Check that the polyline is convex (downward-concave) — i.e.
        no sign changes in the cross-product of consecutive segments."""
        if len(verts) < 3:
            return True
        sign = None
        for i in range(1, len(verts) - 1):
            ax = verts[i].x - verts[i - 1].x
            ay = verts[i].y - verts[i - 1].y
            bx = verts[i + 1].x - verts[i].x
            by = verts[i + 1].y - verts[i].y
            cross = ax * by - ay * bx
            if abs(cross) < 1e-9:
                continue
            s = 1 if cross > 0 else -1
            if sign is None:
                sign = s
            elif s != sign:
                return False
        return True

    @staticmethod
    def _cauchy_step(u, T_gen):
        """VFSA Cauchy generator — Eq (8) in Su 2009.

            r = sgn(u-0.5) · T · [(1 + 1/T)^|2u-1| - 1]
        """
        sign = 1.0 if u >= 0.5 else -1.0
        # Numerical guard: T_gen very small → (1 + 1/T_gen) huge → overflow
        T = max(T_gen, 1e-6)
        try:
            base = 1.0 + 1.0 / T
            exponent = abs(2 * u - 1)
            # Clamp exponential argument to avoid overflow
            log_val = exponent * math.log(base)
            if log_val > 50:
                power = math.exp(50)
            else:
                power = math.exp(log_val)
            return sign * T * (power - 1.0)
        except (OverflowError, ValueError):
            # Fall back to a small random step
            return sign * T * 0.1

    def _evaluate_polyline(self, project, verts):
        """Evaluate the candidate non-circular surface. Returns
        (LEMResult, fos) or (None, None) if invalid/unphysical.

        v0.1.17 — added the same physical-admissibility guards used by
        the Path and Block searches, to stop the SA from chasing
        degenerate surfaces (tiny slivers, sawtooth shapes) that yield
        spurious sub-unity FoS values.
        """
        from ogr_core.geometry import Polyline
        from .surface import SlipSurface
        if len(verts) < 3:
            return None, None
        if self.convex_only and not self._is_convex(verts):
            return None, None

        # (a) strictly increasing in x (single-valued surface)
        for a, b in zip(verts[:-1], verts[1:]):
            if b.x <= a.x + 1e-9:
                return None, None

        # (b) interior vertices must lie below the entry-exit chord
        #     (concave-up / kinematically admissible slip mass)
        x0v, y0v = verts[0].x, verts[0].y
        xnv, ynv = verts[-1].x, verts[-1].y
        if xnv - x0v > 1e-9:
            for vv in verts[1:-1]:
                tt = (vv.x - x0v) / (xnv - x0v)
                chord = y0v + tt * (ynv - y0v)
                if vv.y > chord + 1e-6:
                    return None, None

        # (c) unimodal (single valley): y descends to a minimum then
        #     ascends — rejects sawtooth wedge shapes
        ys = [v.y for v in verts]
        imin = ys.index(min(ys))
        for a in range(1, imin + 1):
            if ys[a] > ys[a - 1] + 1e-6:
                return None, None
        for a in range(imin + 1, len(ys)):
            if ys[a] < ys[a - 1] - 1e-6:
                return None, None

        # (d) minimum area of the sliding mass (reject slivers)
        area = 0.0
        for a, b in zip(verts[:-1], verts[1:]):
            # area between chord-top and surface (trapezoids vs entry-exit
            # chord); use simple |∫(chord - surface) dx|
            tt0 = (a.x - x0v) / (xnv - x0v) if xnv > x0v else 0.0
            tt1 = (b.x - x0v) / (xnv - x0v) if xnv > x0v else 0.0
            c0 = y0v + tt0 * (ynv - y0v)
            c1 = y0v + tt1 * (ynv - y0v)
            area += 0.5 * ((c0 - a.y) + (c1 - b.y)) * (b.x - a.x)
        if abs(area) < max(self.min_area, 0.5):
            return None, None

        # (e) every vertex inside the External polygon (definitive guard
        #     against surfaces poking outside the soil mass)
        if getattr(self, "_ext_poly", None) is not None:
            from shapely.geometry import Point as _Pt
            buf = self._ext_poly.buffer(1e-6 * max(xnv - x0v, 1.0))
            for vv in verts:
                if not buf.contains(_Pt(vv.x, vv.y)):
                    return None, None

        poly = Polyline(vertices=verts, closed=False)
        surface = SlipSurface(polyline=poly)
        if self._focus_rejects(surface):
            # v0.1.129 — a focused annealing must not accept a move that
            # leaves the focus, or the walk would wander off it and report
            # where it landed. Rejected like any other inadmissible
            # candidate: the step is simply not taken. Defect D33.
            return None, None
        res = self.evaluate_surface(project, surface)
        if res is None or not res.is_valid:
            return None, None
        # v0.1.17 wrote this floor to stop the search "chasing degenerate
        # surfaces [...] that yield spurious sub-unity FoS values". It was a
        # bandage over the defect fixed in v0.1.119 (see ``_steer``): those
        # surfaces are not degenerate geometry, they are surfaces the
        # m-alpha check bars from ever being the answer, and the annealing
        # was descending into them until it hit this very number. It stays
        # because a factor below 0.5 on a candidate the checks DO accept is
        # still not something to steer a random walk by, but it is no longer
        # what keeps the search out of the forbidden basin.
        if not (0.5 <= res.fos <= 100.0):
            return None, None
        return res, self.score(res)

    # ------------------------------------------------------------------
    def _steer(self, project, result, verts):
        """Evaluate a candidate, record it, and say whether it may GUIDE.

        v0.1.119 — the defect this method exists to make impossible.
        ``_evaluate_polyline`` asks for ``is_valid`` and never asked for
        ``admissible``; :attr:`SearchResult.critical` asks for both. So the
        annealing was minimising a function whose minimum sits on surfaces
        the program then refuses to publish, and the number the user saw was
        the best admissible surface it happened to cross on the way in — a
        by-product, not a result.

        Measured on the v0.1.17 test slope, ``generation_steps`` = 300:
        83-98 % of the evaluated population was inadmissible (``m_alpha <
        0.2``, Whitman & Bailey 1967), the LAST FIFTY evaluations were
        inadmissible in every seed tried, and the local phase converged to
        0.500 — the floor of the guard in ``_evaluate_polyline`` — while
        1.36 was reported. It also explains why more effort made the answer
        WORSE (1.3631 at 300 steps, 1.4341 at 1000): a bigger budget is a
        better descent into the wrong basin.

        ``optimize.py`` learned this in v0.1.104 and says it in one line:
        "optimisation chases a LOWER factor, which is exactly where
        kinematically impossible surfaces live". This search is from
        v0.1.17 and never heard it.

        The surface is still COUNTED — appended to ``evaluations`` and to
        ``valid_count`` — so ``inadmissible_count`` and ``total_count`` keep
        meaning here what they mean in the other five searches. Only the
        steering changes.

        Returns ``(result, fos)`` when the candidate may guide the search,
        ``(None, None)`` otherwise.
        """
        res, fos = self._evaluate_polyline(project, verts)
        if res is None:
            return None, None
        result.evaluations.append(res)
        result.valid_count += 1
        if not getattr(res, "admissible", True):
            return None, None
        return res, fos

    # ==================================================================
    # Phase 1 — Very Fast Simulated Annealing
    # ==================================================================
    @staticmethod
    def _bootstrap_parameters(n_inner, D, top, y_floor, dy, ymax,
                              x1, xN, y1, yN, rng, attempt):
        """Parameters of an admissible starting surface.

        The inner vertices are placed on a bowl hanging below the chord
        that joins the entry and exit points:

            y(t) = chord(t) - depth * sin(pi * t) ** power

        which is single-valued in x, lies below the chord and has ONE
        low point — the three conditions the admissibility filters check.
        ``depth`` and ``power`` are randomised (and the depth is shrunk
        on successive attempts) so the bootstrap still explores, while
        every candidate it produces is valid by construction.

        Returns the ``(P_X, P_Y)`` parameters in [0, 1] expected by the
        annealing, so the search continues from here unchanged.
        """
        import math as _m

        depth_cap = max(1e-6, y1 - y_floor if y1 > y_floor else 1.0)
        depth_cap = max(depth_cap, max(y1, yN) - y_floor)
        # Shrink with the attempt number: a shallower bowl always fits
        depth = depth_cap * (0.65 * (0.85 ** attempt)) * (
            0.6 + 0.4 * rng.random())
        power = 0.8 + 1.4 * rng.random()
        skew = 0.35 + 0.3 * rng.random()      # position of the low point

        P_X = []
        P_Y = []
        for m in range(1, n_inner + 1):
            # Keep x near the middle of its division, with mild jitter
            px = 0.35 + 0.3 * rng.random()
            P_X.append(px)
            xm = D[m - 1] + px * (D[m] - D[m - 1])
            t = (xm - x1) / max(xN - x1, 1e-9)
            chord = y1 + t * (yN - y1)
            # Asymmetric bowl: warp t so the low point sits at ``skew``
            tw = t ** (_m.log(0.5) / _m.log(max(skew, 1e-6))) \
                if 0 < skew < 1 else t
            drop = depth * (_m.sin(_m.pi * min(max(tw, 0.0), 1.0))
                            ** power)
            ym = chord - drop

            top_y_here = SimulatedAnnealingSearch._interp_top_y(top, xm)
            y_top = top_y_here if top_y_here is not None else ymax
            ym_max = y_top - 0.05 * dy
            ym_min = y_floor
            if ym_max <= ym_min:
                ym_max = ym_min + 0.1
            ym = min(max(ym, ym_min + 1e-9), ym_max - 1e-9)
            P_Y.append((ym - ym_min) / max(ym_max - ym_min, 1e-12))
        return P_X, P_Y

    def _vfsa(self, project, result, x1, xN, ymin, ymax, top, N, dx, dy,
              random):
        """Run the VFSA loop. Returns (best_verts, best_fos).

        ``random`` is the search's own :class:`random.Random`, not the
        module — see the note in :meth:`_run`.
        """
        from ogr_core.geometry import Vertex

        # Slope endpoint y-values (snap to top profile)
        y1 = self._interp_top_y(top, x1)
        yN = self._interp_top_y(top, xN)
        if y1 is None or yN is None:
            return None, None

        # Equi-divisions for x-bounds (Eq. 3 in Su 2009)
        # We have N vertices, so N-2 inner ones, with N-1 divisions
        D = [x1 + i * (xN - x1) / (N - 1) for i in range(N)]

        # Bounds for inner y. The lower bound must NOT plunge to the
        # bottom of the bounding box (that produces absurdly deep, narrow
        # surfaces with spurious sub-unity FoS). v0.1.17 — clamp the
        # floor near the toe elevation, allowing the surface to dip a
        # reasonable fraction of the slope height below the toe.
        y_toe = min(self._interp_top_y(top, x1) or ymin,
                    self._interp_top_y(top, xN) or ymin)
        slope_h = ymax - y_toe
        y_floor = y_toe - 0.15 * max(slope_h, 1.0)
        y_floor = max(y_floor, ymin)

        def _denormalize(P_X, P_Y):
            """Convert parameterised values in [0,1] to actual (x, y)
            coords for inner vertices."""
            inner = []
            for m in range(1, N - 1):
                # x_m within division [D_{m-1}, D_m]
                # Wait — paper says D_m = x1 + (m-1)*(xN-x1)/(N-2)
                # so for m=1 first inner vertex, x in [D_0, D_1]
                xm = D[m - 1] + P_X[m - 1] * (D[m] - D[m - 1])
                # Dynamic upper bound for y_m: interpolation between
                # neighbours (or top profile) prevents auto-intersection
                top_y_here = self._interp_top_y(top, xm)
                y_top = top_y_here if top_y_here is not None else ymax
                ym_max = y_top - 0.05 * dy  # below ground surface
                ym_min = y_floor
                if ym_max <= ym_min:
                    ym_max = ym_min + 0.1
                ym = ym_min + P_Y[m - 1] * (ym_max - ym_min)
                inner.append(Vertex(xm, ym))
            return [Vertex(x1, y1)] + inner + [Vertex(xN, yN)]

        # Initialize parameters (all in [0,1])
        n_inner = N - 2
        n = 2 * n_inner  # total control variables
        P_X = [random.random() for _ in range(n_inner)]
        P_Y = [random.random() for _ in range(n_inner)]

        # Bootstrap: build a valid initial surface.
        #
        # v0.1.39 (anomaly A5) — the previous bootstrap drew every inner
        # vertex INDEPENDENTLY at random and relied on the result
        # happening to pass the admissibility filters. The decisive one
        # is unimodality (the surface must descend to a single low point
        # and then rise): for n independently ordered values the chance
        # of that is about 2^(n-1)/n!, i.e. well under 1 % for the
        # default 9 vertices. The search therefore failed COMPLETELY for
        # unlucky seeds — 200 rejections and not a single evaluation —
        # which is exactly the reported anomaly.
        #
        # The fix is to construct the starting surface so that it
        # satisfies the constraints BY CONSTRUCTION: a bowl hanging below
        # the entry-exit chord, whose depth profile is a single smooth
        # arc. Randomness now controls the depth and the asymmetry of the
        # bowl instead of each vertex independently, so every draw is
        # admissible and the annealing always has somewhere to start.
        #
        # v0.1.119 — "admissible" above meant the geometric filters. The
        # start must now also survive the post-analysis checks, because that
        # is what the walk steers by; ``fallback`` holds the best candidate
        # that passed the geometry and failed the checks, so a model where
        # NO admissible start can be found still gets a search rather than
        # an empty result. Which end of that trade matters is settled:
        # test_annealing_bootstrap_v139 exists because returning nothing at
        # all is the worst outcome here.
        best_verts = None
        best_fos = None
        fallback = None

        def _bootstrap_try(verts):
            nonlocal best_verts, best_fos, fallback
            res, fos = self._evaluate_polyline(project, verts)
            if res is None:
                return False
            result.evaluations.append(res)
            result.valid_count += 1
            if not getattr(res, "admissible", True):
                if fallback is None or fos < fallback[1]:
                    fallback = (verts, fos)
                return False
            best_verts, best_fos = verts, fos
            return True

        for attempt in range(60):
            P_X, P_Y = self._bootstrap_parameters(
                n_inner, D, top, y_floor, dy, ymax, x1, xN, y1, yN,
                random, attempt)
            if _bootstrap_try(_denormalize(P_X, P_Y)):
                break
        if best_verts is None:
            # Last resort: the plain random draw, in case an unusual
            # geometry defeats the constructed bowl.
            for _ in range(200):
                P_X = [random.random() for _ in range(n_inner)]
                P_Y = [random.random() for _ in range(n_inner)]
                if _bootstrap_try(_denormalize(P_X, P_Y)):
                    break
        if best_verts is None and fallback is not None:
            best_verts, best_fos = fallback
        if best_verts is None:
            return None, None

        # Initial temperatures (Su 2009 Section 2.1.3)
        T_gen = 1.0
        T_accept = best_fos  # initial acceptance T = current FoS
        c = self.temperature_coefficient

        # External annealing iterations
        K = max(4, int(self.generation_steps / 50))  # outer loop count
        Ngen0 = max(20, self.generation_steps // K)  # inner loop size

        no_improve_passes = 0
        last_best = best_fos

        for k in range(1, K + 1):
            n_accepted = 0
            n_rejected = 0
            # Inner loop: Ngen Cauchy random walks (paper has Ngen ~ 1000n
            # but we scale to user's generation_steps)
            Ngen = max(10, Ngen0 // (2 ** (k - 1)))

            for _ in range(Ngen):
                # Cauchy random walk for ALL control variables
                cand_X = list(P_X)
                cand_Y = list(P_Y)
                for i in range(n_inner):
                    u = random.random()
                    r_step = self._cauchy_step(u, T_gen)
                    new_p = cand_X[i] + r_step
                    # Bounds check (Section 2.1.9): truncate to [0, 1]
                    cand_X[i] = max(0.001, min(0.999, new_p))
                for i in range(n_inner):
                    u = random.random()
                    r_step = self._cauchy_step(u, T_gen)
                    new_p = cand_Y[i] + r_step
                    cand_Y[i] = max(0.001, min(0.999, new_p))

                verts = _denormalize(cand_X, cand_Y)
                r, f = self._steer(project, result, verts)
                if r is None:
                    continue

                # Acceptance: Eq (9) in Su 2009
                dE = f - best_fos
                if dE <= 0:
                    P_accept = 1.0
                else:
                    # Guard against overflow when T_accept is very small
                    arg = dE / max(T_accept, 1e-9)
                    if arg > 50:
                        P_accept = 0.0
                    else:
                        P_accept = 1.0 / (1.0 + math.exp(arg))
                if random.random() <= P_accept:
                    P_X = cand_X
                    P_Y = cand_Y
                    if f < best_fos - self.tolerance:
                        best_fos = f
                        best_verts = verts
                    n_accepted += 1
                else:
                    n_rejected += 1

            # ---- Schedule (Eqs 10-11) ----
            try:
                exp_arg = -c * (k ** (1.0 / max(n, 1)))
                exp_arg = max(-50.0, exp_arg)
                cooling = math.exp(exp_arg)
            except (OverflowError, ValueError):
                cooling = 0.5
            T_accept = max(1e-6, T_accept * cooling)
            T_gen = max(1e-6, T_gen * cooling)

            # ---- Ratio control (Section 2.1.8) ----
            if n_rejected > 0:
                ratio = n_accepted / n_rejected
                if ratio > 2.0:
                    T_accept *= 0.5
                elif ratio < 0.5:
                    T_accept *= 2.0

            # ---- Stopping criterion (Section 2.1.7) ----
            # n_eps is the setting, not a constant: "if there has not been
            # any visible improvement for the global optimum in the previous
            # n_eps consecutive runs, the algorithm is to be stopped"
            # (Su 2009, section 2.1.7).
            if best_fos < last_best - self.tolerance:
                last_best = best_fos
                no_improve_passes = 0
            else:
                no_improve_passes += 1
            if no_improve_passes >= self.num_fos_compared_before_stopping:
                break

            if self.progress_cb:
                self.progress_cb(k * Ngen0, K * Ngen0)

        return best_verts, best_fos

    # ==================================================================
    # Phase 2 — Local Monte-Carlo (Greco 1996, Su 2009 Section 2.2)
    # ==================================================================
    def _lmc(
        self, project, result, verts, fos, ymin, ymax, top, dx, random,
    ):
        """Local Monte-Carlo refinement of the surface from VFSA.

        v0.1.119 — the two extremity vertices are control variables here,
        as they are in the formulation: Su (2009) section 2.1 counts
        ``n = 2N - 2`` degrees of freedom precisely because "the two
        extremity points of the failure surface can only move along the
        slope line" — they move, on a line. This search froze them at the
        toe and the crest of the steepest ground segment and never touched
        them again, so on the v0.1.17 test slope every surface it could
        express entered and left within x = [30.00, 50.00] while the
        critical circle daylights at 30.03 and 51.45. Freeing them took the
        worst of seven seeds from 1.3781 to 1.1862.

        An endpoint moves in x only; its y is read off the ground profile,
        so it keeps daylighting. Its travel is bounded by the Slope Limits
        when the project declares them — which is where they finally reach
        the GENERATION of this search and not only the mass filter in
        ``_best_of_masses``.
        """
        from ogr_core.geometry import Vertex

        if len(verts) < 4:
            return verts, fos

        # Step sizes per vertex (one per (vertex, axis))
        # Initial step ~ 5% of dx
        step_x = [0.05 * dx for _ in verts]
        step_y = [0.05 * dx for _ in verts]
        eps = 0.75   # step reduction factor per Su 2009
        min_step = self.tolerance * dx * 0.1

        # Where an endpoint is allowed to travel to.
        end_lo, end_hi = top[0].x, top[-1].x
        if self.slope_limits is not None:
            sl_lo, sl_hi = sorted(self.slope_limits)
            end_lo, end_hi = max(end_lo, sl_lo), min(end_hi, sl_hi)

        # 8 cardinal+diagonal directions
        DIRS = [
            (-1, -1), (-1, 0), (-1, 1),
            ( 0, -1),          ( 0, 1),
            ( 1, -1), ( 1, 0), ( 1, 1),
        ]

        max_passes = 15  # hard cap on outer LMC passes
        max_total_evals = 2 * self.generation_steps  # hard cap on # of evals
        evals_done = 0

        def _moved(cand, i, Nx, Ny, Rx, Ry):
            """The i-th vertex displaced, or None if the move is not one.

            An endpoint slides along the ground: only x is a degree of
            freedom, y follows the profile.
            """
            x = cand[i].x + Nx * Rx * step_x[i]
            if i == 0 or i == len(cand) - 1:
                if not (end_lo <= x <= end_hi):
                    return None
                y = self._interp_top_y(top, x)
                if y is None:
                    return None
                return Vertex(x, y)
            return Vertex(x, cand[i].y + Ny * Ry * step_y[i])

        def _ordered(cand, i):
            """x still strictly increasing around the moved vertex."""
            if i > 0 and cand[i].x <= cand[i - 1].x:
                return False
            if i < len(cand) - 1 and cand[i].x >= cand[i + 1].x:
                return False
            return True

        for pass_idx in range(max_passes):
            improved_anywhere = False
            for i in range(len(verts)):
                if evals_done >= max_total_evals:
                    return verts, fos

                # Skip vertex if its step has already shrunk below threshold
                if step_x[i] < min_step and step_y[i] < min_step:
                    continue

                # ---- Exploration phase ----
                best_dir = None
                best_local_fos = fos
                best_cand = None
                Rx = random.uniform(-0.5, 0.5)
                Ry = random.uniform(-0.5, 0.5)
                if abs(Rx) < 0.1: Rx = 0.1 if Rx >= 0 else -0.1
                if abs(Ry) < 0.1: Ry = 0.1 if Ry >= 0 else -0.1

                for (Nx, Ny) in DIRS:
                    if Nx == 0 and Ny == 0:
                        continue
                    cand = [Vertex(v.x, v.y) for v in verts]
                    moved = _moved(cand, i, Nx, Ny, Rx, Ry)
                    if moved is None:
                        continue
                    cand[i] = moved
                    if not _ordered(cand, i):
                        continue
                    r, f = self._steer(project, result, cand)
                    evals_done += 1
                    if r is None:
                        continue
                    if f < best_local_fos - self.tolerance:
                        best_local_fos = f
                        best_dir = (Nx, Ny)
                        best_cand = cand
                    if evals_done >= max_total_evals:
                        if best_cand is not None:
                            verts = best_cand
                            fos = best_local_fos
                        return verts, fos

                if best_cand is not None:
                    # ---- Extrapolation phase ----
                    verts = best_cand
                    fos = best_local_fos
                    improved_anywhere = True
                    Nx, Ny = best_dir
                    for _ in range(5):  # cap extrapolation
                        if evals_done >= max_total_evals:
                            return verts, fos
                        cand = [Vertex(v.x, v.y) for v in verts]
                        moved = _moved(cand, i, Nx, Ny, Rx, Ry)
                        if moved is None:
                            break
                        cand[i] = moved
                        if not _ordered(cand, i):
                            break
                        r, f = self._steer(project, result, cand)
                        evals_done += 1
                        if r is None or f >= fos - self.tolerance:
                            break
                        verts = cand
                        fos = f
                else:
                    # No direction improved → shrink steps for this vertex
                    step_x[i] *= (1.0 - eps)
                    step_y[i] *= (1.0 - eps)

            if not improved_anywhere:
                # Check if all step sizes are below threshold
                all_done = all(
                    step_x[i] < min_step and step_y[i] < min_step
                    for i in range(len(verts))
                )
                if all_done:
                    break

        return verts, fos
