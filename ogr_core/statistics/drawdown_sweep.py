# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Sweep the drawdown level to find the reservoir elevation that is worst.

Why this exists
---------------
**The total drawdown is not always the critical case.** The reference
documentation contains both behaviours, which is what settles the
question rather than leaving it to taste:

* a homogeneous slope (Morgenstern 1963, verification problems #100 and
  #101) is worst when the reservoir is emptied completely — FoS 1.20
  against 1.41 at half drawdown;
* a zoned dam with a freely draining upstream shell is worst at some
  INTERMEDIATE level. The reference states it outright: *"For this
  example, the minimum safety factor at partial drawdown is lower than
  the minimum safety factor at full drawdown […] For this particular
  model, a minimum safety factor therefore exists at some intermediate
  drawdown level."* The mechanism it gives is that the granular shell
  drains to zero pore pressure under a complete drawdown, while a
  partial one leaves a water table standing in it near the toe.

On such a dam, analysing only the total drawdown reports 1.48 where the
real worst case is 1.30 — 12 % on the unsafe side.

Why it is not a sensitivity analysis
------------------------------------
``sensitivity.run_sensitivity`` already sweeps a parameter and collects
factors of safety, and reusing it here would be wrong. It **fixes the
critical surface** and only re-evaluates it, but the critical surface
MOVES with the reservoir level — on the Morgenstern slope it goes from
(60, 380) r = 380 at total drawdown to (180, 220) r = 180 at half. Held
fixed, the factor of safety comes out up to 10 % high, and the
intermediate minimum this module exists to find can be missed entirely.

So the search is repeated at every level. That is expensive, and it is
the price of the answer being right; ``run_overall_slope`` pays the same
price for the same reason, and this module borrows its ``search_factory``
arrangement so that ``ogr_core`` still never imports ``ogr_slip2d``.

References:
    Morgenstern, N. (1963). "Stability charts for earth slopes during
        rapid drawdown". Géotechnique 13(2), pp. 121-131.
    Duncan, J. M., Wright, S. G. y Wong, K. S. (1990). "Slope Stability
        during Rapid Drawdown". H. Bolton Seed Memorial Symposium,
        vol. 2, pp. 253-272.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..hydraulic.drawdown_levels import (
    ground_elevation_span,
    levels_at,
    project_at_level,
)

DEFAULT_LEVELS = 11

# The elevation stored for the total-drawdown point. It is not a level —
# there is no reservoir — but the chart needs an abscissa, and the lowest
# ground in the model is where "no water left" plots naturally.
TOTAL_DRAWDOWN = None


@dataclass
class MethodSweep:
    """One method's answer at every level swept."""

    method_id: str
    levels: list = field(default_factory=list)      # None = total drawdown
    fos: list = field(default_factory=list)
    surfaces: list = field(default_factory=list)    # dicts, or None
    failed: int = 0

    # ------------------------------------------------------------------
    @property
    def valid(self) -> list:
        """(level, fos, surface) triples that produced a usable answer."""
        return [(lv, f, s) for lv, f, s
                in zip(self.levels, self.fos, self.surfaces)
                if f is not None and math.isfinite(f)]

    def critical(self):
        """(level, fos, surface) of the worst level, or None."""
        v = self.valid
        return min(v, key=lambda t: t[1]) if v else None

    def at_total_drawdown(self):
        """(level, fos, surface) of the total-drawdown point, or None."""
        for lv, f, s in self.valid:
            if lv is None:
                return (lv, f, s)
        return None

    def unsafe_margin(self) -> Optional[float]:
        """How much analysing ONLY the total drawdown would overstate it.

        Returned as a fraction: 0.12 means the total-drawdown factor of
        safety is 12 % above the worst level's. It cannot be negative,
        since the worst level is a minimum over a set the total drawdown
        belongs to; ~0 is the reassuring answer and means the total
        drawdown IS the critical case, as it is on a homogeneous slope.
        ``None`` only when the total drawdown was not swept.
        """
        crit = self.critical()
        total = self.at_total_drawdown()
        if crit is None or total is None or crit[1] <= 0.0:
            return None
        return total[1] / crit[1] - 1.0


@dataclass
class DrawdownSweepResult:
    """The sweep, per method, plus what was actually swept."""

    by_method: dict = field(default_factory=dict)   # method_id -> MethodSweep
    levels: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)

    def worst(self) -> Optional[tuple]:
        """(method_id, level, fos) of the lowest factor of safety seen."""
        best = None
        for mid, sweep in self.by_method.items():
            c = sweep.critical()
            if c is None:
                continue
            if best is None or c[1] < best[2]:
                best = (mid, c[0], c[1])
        return best


# ----------------------------------------------------------------------
def default_levels(project, n_levels: int = DEFAULT_LEVELS,
                   include_total: bool = True) -> list:
    """Levels to sweep: initial reservoir down to the lowest ground.

    Sweeping above the initial level would be a filling, not a drawdown,
    and sweeping below the toe adds points that all mean total drawdown.
    """
    y_min, _ = ground_elevation_span(project)
    initial, _final = levels_at(project, _mid_x(project))
    if initial is None:
        _, y_max = ground_elevation_span(project)
        initial = y_max
    n = max(2, int(n_levels))
    step = (initial - y_min) / (n - 1)
    levels = [initial - i * step for i in range(n)]
    if include_total:
        levels.append(TOTAL_DRAWDOWN)
    return levels


def _mid_x(project) -> float:
    from ..hydraulic.drawdown_levels import model_x_span
    x0, x1 = model_x_span(project)
    return 0.5 * (x0 + x1)


def run_drawdown_sweep(
    project,
    search_factory: Callable,
    method_ids: list,
    *,
    levels: Optional[list] = None,
    n_levels: int = DEFAULT_LEVELS,
    include_total: bool = True,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> DrawdownSweepResult:
    """Repeat the whole search at each drawdown level.

    ``search_factory`` is a callable ``method_id -> BaseSearch`` that
    builds a fully configured search, so the sweep honours exactly the
    search settings the user chose — the same arrangement
    ``run_overall_slope`` uses, and for the same layering reason.

    ``levels`` is a list of reservoir elevations; ``None`` inside it means
    total drawdown. Left unset, :func:`default_levels` covers the initial
    level down to the lowest ground in ``n_levels`` steps.

    Cost is ``len(levels) × len(method_ids)`` full searches. There is no
    cheaper honest version: fixing the surface is what makes a sweep miss
    the very minimum it was run to find.
    """
    result = DrawdownSweepResult()
    if not method_ids:
        result.notes["error"] = "No analysis method selected."
        return result
    if not project.settings.groundwater.rapid_drawdown:
        result.notes["error"] = (
            "The drawdown level sweep needs a Rapid Drawdown analysis: "
            "enable it in Project Settings > Groundwater > Advanced.")
        return result

    if levels is None:
        levels = default_levels(project, n_levels, include_total)
    result.levels = list(levels)

    total = len(levels) * len(method_ids)
    done = 0
    for mid in method_ids:
        sweep = MethodSweep(method_id=mid)
        for y in levels:
            at = project_at_level(project, y)
            try:
                run = search_factory(mid).run(at)
            except Exception:  # noqa: BLE001
                run = None
            done += 1
            if progress_cb:
                progress_cb(done, total)
            sweep.levels.append(y)
            crit = getattr(run, "critical", None) if run is not None else None
            if crit is None or not math.isfinite(getattr(crit, "fos", math.nan)):
                sweep.fos.append(None)
                sweep.surfaces.append(None)
                sweep.failed += 1
                continue
            sweep.fos.append(crit.fos)
            surface = getattr(crit, "surface", None)
            sweep.surfaces.append(
                surface.to_dict() if hasattr(surface, "to_dict") else None)
        result.by_method[mid] = sweep
    return result
