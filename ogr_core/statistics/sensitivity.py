# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Sensitivity analysis — Phase P4 of the probabilistic plan.

A sensitivity analysis varies each selected input parameter across its
range and observes the effect on the computed factor of safety, which
identifies the parameters that matter most for the stability of a slope.

Following the reference specification:

* the range between the actual MINIMUM and MAXIMUM (derived from the
  *relative* values entered by the user: ``mean - rel_min`` to
  ``mean + rel_max``) is divided into **50 equal intervals**, giving 51
  evaluation points;
* the factor of safety is recomputed on the **global minimum slip
  surface** for each of those values;
* while one variable is being swept, **all other variables are held at
  their mean (deterministic) value**;
* the process is repeated for each selected variable, one at a time,
  even when several are selected.

A sensitivity analysis is NOT a probabilistic analysis: only the minimum
and maximum of each variable are used, the distribution shape plays no
part, and no probability of failure comes out of it.

Two conveniences are added on top of the specification because they make
the results directly usable:

* the x-axis can be expressed as **percent of range**, which is how
  several variables with different units are compared on one plot;
* the sweep records where the curve **crosses a target factor of
  safety**, i.e. the parameter value at which the slope reaches the
  design threshold.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from .random_variables import clone_project, set_value

DEFAULT_INTERVALS = 50


@dataclass
class VariableSensitivity:
    """Sweep of one variable for one analysis method."""

    key: str = ""
    label: str = ""
    values: list = field(default_factory=list)     # parameter values
    fos: list = field(default_factory=list)        # matching factors
    mean_value: float = math.nan
    deterministic_fos: float = math.nan
    #: Why this variable has no sweep. v0.1.164 (D91) — a variable whose
    #: target no longer exists in the model used to be swept anyway, and
    #: every point answered the SAME factor: a flat curve that reads as
    #: "this parameter does not matter", which is the opposite of what
    #: happened. A named variable with no points says the truth; dropping
    #: it silently would only move the lie.
    note: str = ""

    # ------------------------------------------------------------------
    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def min_fos(self) -> float:
        return min(self.fos) if self.fos else math.nan

    @property
    def max_fos(self) -> float:
        return max(self.fos) if self.fos else math.nan

    @property
    def fos_range(self) -> float:
        """Span of the factor of safety over the variable's range — the
        natural measure of how influential the parameter is."""
        if not self.fos:
            return 0.0
        return max(self.fos) - min(self.fos)

    @property
    def is_increasing(self) -> bool:
        """True when a larger parameter value gives a larger factor of
        safety (cohesion), False when it lowers it (seismic load)."""
        if len(self.fos) < 2:
            return True
        return self.fos[-1] >= self.fos[0]

    def percent_of_range(self) -> list:
        """x-axis as 0-100 % of the variable's range, so variables with
        different units can share a plot."""
        if self.n < 2:
            return [50.0] * self.n
        lo, hi = self.values[0], self.values[-1]
        span = hi - lo
        if abs(span) < 1e-15:
            return [50.0] * self.n
        return [100.0 * (v - lo) / span for v in self.values]

    def crossing(self, target: float = 1.0) -> Optional[float]:
        """Parameter value at which the factor of safety crosses
        ``target``, by linear interpolation, or None if it never does."""
        for (x0, f0), (x1, f1) in zip(zip(self.values, self.fos),
                                      zip(self.values[1:], self.fos[1:])):
            if (f0 - target) == 0.0:
                return x0
            if (f0 - target) * (f1 - target) < 0:
                t = (target - f0) / (f1 - f0)
                return x0 + t * (x1 - x0)
        return None


@dataclass
class SensitivityResult:
    """Full sensitivity run: one sweep per variable per method."""

    by_method: dict = field(default_factory=dict)   # mid -> {key: VS}
    intervals: int = DEFAULT_INTERVALS
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
    def ok(self) -> bool:
        return bool(self.by_method)

    def ranking(self, method_id: Optional[str] = None) -> list:
        """Variables ordered from most to least influential, by the span
        of the factor of safety they produce.

        Returns ``[(key, label, fos_range), ...]``.
        """
        if method_id is None:
            method_id = next(iter(self.by_method), None)
        sweeps = self.by_method.get(method_id, {})
        # A variable with a note was never swept, so its zero span is not a
        # measurement and may not sit at the bottom of the ranking as if it
        # were the least influential parameter (D91).
        rows = [(vs.key, vs.label, vs.fos_range) for vs in sweeps.values()
                if not vs.note]
        rows.sort(key=lambda r: r[2], reverse=True)
        return rows


# ======================================================================
def run_sensitivity(
    project,
    critical_surfaces: dict,
    variables: list,
    intervals: int = DEFAULT_INTERVALS,
    num_slices: int = 25,
    method_factory: Optional[Callable] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> SensitivityResult:
    """Run a sensitivity analysis.

    Args:
        project: the deterministic model (never modified).
        critical_surfaces: ``method_id -> LEMResult`` from the
            deterministic run.
        variables: the :class:`RandomVariable` list; only the minimum and
            maximum of each are used.
        intervals: number of equal intervals (50 in the reference), so
            ``intervals + 1`` values are evaluated.
        num_slices: slicing for the repeated evaluations.
        method_factory: ``method_id -> LEMMethod``; defaults to
            ``analysis_runner.build_method``, which is the one place that
            configures a method from the project (v0.1.108).
        progress_cb: called as ``(done, total)``.

    WHERE THE v0.1.170 (D129) NOTE STOPS, said out loud rather than left to
    be discovered. A method REFUSED by ``_cannot_reevaluate`` now says so
    even when another method answered. A method that entered the loop and
    came out with zero valid points still leaves ``by_method`` without a
    note of its own: when the cause is an orphan variable the sweep carries
    it and the run-wide sentence says it, but when every evaluation simply
    failed the method disappears quietly. That is not fixed here because
    there is no measured reproduction of it, and inventing a sentence for a
    state nobody has seen is the ajuste-que-no-hace-nada of regla 7.
    Promising a wider cover than the guard gives is what cost this project
    two versions over m-alpha (v0.1.82-84).
    """
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch

    from .probabilistic import (
        _NO_DETERMINISTIC,
        _NO_METHOD,
        _cannot_reevaluate,
        _evaluate_on,
        _publish_method_losses,
        _publish_note,
        _rebuild_surface,
    )

    res = SensitivityResult(intervals=intervals)

    usable = [rv for rv in variables
              if abs(rv.distribution.high - rv.distribution.low) > 1e-15]
    if not usable:
        _publish_note(
            res, "error",
            "No variable has a range: enter a relative minimum and "
            "maximum for at least one parameter.")
        return res
    if not critical_surfaces:
        _publish_note(
            res, "error",
            "No deterministic result: run the regular analysis first so "
            "the global minimum surface is known.")
        return res

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

    n_points = max(2, int(intervals) + 1)
    total = len(usable) * n_points * max(1, len(critical_surfaces))
    done = 0
    # v0.1.164 (D91) — gathered across the method loop and answered ONCE at
    # the end, so the run says the sentence the probabilistic engine says
    # instead of one sentence per variable per method. A dict for an
    # ordered set: the same variable is refused by every method.
    orphan_keys: dict = {}
    # v0.1.170 (D129) — the methods this loop loses, named as it loses
    # them. An EXPLICIT list, never something read back off the keys of
    # ``notes``: dispatching on the shape of a dictionary instead of on
    # what the code knows is literally D59, and here it would also be
    # wrong -- ``"variables"`` is a key of ``notes`` and is not a method.
    lost: list = []

    for mid, det in critical_surfaces.items():
        method = _make_method(mid)
        if method is None or det is None:
            # v0.1.170 (D129) — same third route as in
            # ``run_global_minimum``, and the same two sentences: a method
            # that never reached the sweep used to disappear in silence.
            res.notes[mid] = (_NO_METHOD if method is None
                              else _NO_DETERMINISTIC)
            lost.append(mid)
            continue
        sd = (det.surface.to_dict() if hasattr(det.surface, "to_dict")
              else det.surface)
        refusal = _cannot_reevaluate(project, sd)
        if refusal is not None:
            # v0.1.154 (D59) — same as on the probabilistic path: a sweep
            # that disappears without saying why is worse than one that is
            # not run. Measured before this: ok=False, zero points and an
            # empty ``notes``.
            res.notes[mid] = refusal
            lost.append(mid)
            continue
        surface = _rebuild_surface(sd)
        if surface is None:
            continue
        search = GridSearch(method=method, num_slices=num_slices,
                            min_area=0.0)
        sweeps: dict = {}

        for rv in usable:
            lo = rv.distribution.low
            hi = rv.distribution.high
            vs = VariableSensitivity(
                key=rv.key, label=rv.label or rv.key,
                mean_value=rv.distribution.mean,
                deterministic_fos=getattr(det, "fos", math.nan))
            for i in range(n_points):
                x = lo + (hi - lo) * i / (n_points - 1)
                # Every other variable stays at its mean: the clone is
                # rebuilt from the untouched project each time, so only
                # THIS parameter differs from the deterministic model.
                clone = clone_project(project)
                if not set_value(clone, rv, x):
                    # v0.1.164 (D91) — the return has always been there and
                    # nobody read it. The target or the parameter is gone
                    # from the model, so every remaining point would answer
                    # the deterministic factor again: the sweep stops here
                    # and says so instead of drawing a flat line.
                    vs.note = "no longer matches the model: %s" % rv.key
                    orphan_keys[rv.key] = None
                    # The points not evaluated are still counted: the final
                    # ``progress_cb(total, total)`` would hide the gap, but
                    # a bar that jumps at the end is a small lie.
                    done += n_points - i
                    break
                try:
                    r = _evaluate_on(clone, search, surface)
                except Exception:  # noqa: BLE001
                    r = None
                if r is not None and r.is_valid:
                    vs.values.append(x)
                    vs.fos.append(r.fos)
                done += 1
                if progress_cb and done % 20 == 0:
                    progress_cb(done, total)
            if vs.values or vs.note:
                sweeps[rv.key] = vs

        # A method whose every variable was refused contributes nothing to
        # rank, so it does not enter ``by_method`` -- and with no method in
        # it, ``ok`` falls by itself and the roll-up below turns the reasons
        # into the one key the interface prints. The machinery of v0.1.154
        # is reused rather than a second one added.
        if any(not vs.note for vs in sweeps.values()):
            res.by_method[mid] = sweeps

    # v0.1.164 (D91) — one sentence for the whole run. The denominator is
    # ``usable`` and not the stored sweeps: a variable that produced neither
    # points nor a note never reached them. When nothing survived this goes
    # under its own key rather than straight into ``error``, so the v0.1.154
    # roll-up below still gathers a per-method refusal alongside it instead
    # of finding ``error`` taken and dropping it.
    if orphan_keys:
        keys = ", ".join(orphan_keys)
        if res.by_method:
            _publish_note(
                res, "warning",
                "%d of the %d random variables no longer match the model "
                "and were not swept: %s"
                % (len(orphan_keys), len(usable), keys))
        else:
            _publish_note(
                res, "variables",
                "none of the %d random variables matches the model: %s"
                % (len(usable), keys))

    # v0.1.154 — if no method survived, the reason rises to the only key
    # the interface prints.
    # v0.1.170 (D129) — and if SOME method survived, the ones that did not
    # stop being silent. Until this version the roll-up above fired ONLY on
    # ``not res.by_method``, so a run with one method refused and another
    # answering left its reason under ``notes[mid]``, a key no consumer
    # reads. The probabilistic side got this in v0.1.169; this is the half
    # that was left.
    #
    # It runs AFTER the orphan block on purpose, so the concatenation reads
    # "the D91 sentence; the lost method" -- the same order the
    # probabilistic path produces, where ``_stale_variables_stop`` runs
    # before the method loop.
    _publish_method_losses(res, lost)

    if progress_cb:
        progress_cb(total, total)
    return res
