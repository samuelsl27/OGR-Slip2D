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
        rows = [(vs.key, vs.label, vs.fos_range) for vs in sweeps.values()]
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
    """
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch

    from .probabilistic import _evaluate_on, _rebuild_surface

    res = SensitivityResult(intervals=intervals)

    usable = [rv for rv in variables
              if abs(rv.distribution.high - rv.distribution.low) > 1e-15]
    if not usable:
        res.notes["error"] = (
            "No variable has a range: enter a relative minimum and "
            "maximum for at least one parameter.")
        return res
    if not critical_surfaces:
        res.notes["error"] = (
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
                set_value(clone, rv, x)
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
            if vs.values:
                sweeps[rv.key] = vs

        if sweeps:
            res.by_method[mid] = sweeps

    if progress_cb:
        progress_cb(total, total)
    return res
