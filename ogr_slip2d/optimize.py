# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Surface optimisation — phase M4.

Refines a non-circular slip surface by **random walking** (Greco, 1996):
perturb one vertex at random, recompute the factor of safety, keep the
change when it lowers it, and stop when a whole pass over the vertices
yields no improvement.

It is not only a post-process for Block or Path Search — it works as a
search method in its own right, starting from a single user-defined
surface.

Three points where the implementation makes a choice the reference leaves
open, each stated in the code rather than left to be inferred:

* **A pass, not a single failure, ends the run.** Stopping at the first
  rejected perturbation would abandon a surface that only needed a
  different vertex moved. The run ends when every vertex has been tried
  without improvement.
* **The step shrinks as the walk converges.** A fixed step either crawls
  at the start or cannot settle at the end; halving it after each
  unproductive pass gives both.
* **Every candidate goes through the admissibility filter.** Optimisation
  chases a lower factor of safety, which is exactly the direction in
  which kinematically impossible surfaces lie, so the check that guards
  the search must guard this too — otherwise the "improvement" is an
  artefact.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OptimizeSettings:
    """Options of the random-walk optimisation."""

    enabled: bool = False
    max_iterations: int = 400
    tolerance: float = 1e-4        # improvement below this ends the run
    # Initial perturbation, as a fraction of the surface's own length, so
    # the same settings behave alike on a 10 m and a 200 m slope.
    step_fraction: float = 0.05
    min_step_fraction: float = 0.002
    seed: Optional[int] = None
    # Vertices to work with. A Path or Block Search surface may have only
    # three or four, leaving one or two movable points — far too few for
    # a random walk to reshape anything. Densifying first is what makes
    # the method effective, and it is why the reference calls it a search
    # rather than a mere post-process.
    densify_to: int = 12
    # Whether the two end points may move. Keeping them fixed preserves
    # the entry and exit found by the search; freeing them lets the whole
    # surface migrate, which is occasionally what is wanted.
    move_endpoints: bool = False

    def to_dict(self) -> dict:
        return {"enabled": self.enabled,
                "max_iterations": self.max_iterations,
                "tolerance": self.tolerance,
                "step_fraction": self.step_fraction,
                "min_step_fraction": self.min_step_fraction,
                "seed": self.seed, "densify_to": self.densify_to,
                "move_endpoints": self.move_endpoints}

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizeSettings":
        return cls(enabled=bool(d.get("enabled", False)),
                   max_iterations=int(d.get("max_iterations", 400)),
                   tolerance=float(d.get("tolerance", 1e-4)),
                   step_fraction=float(d.get("step_fraction", 0.05)),
                   min_step_fraction=float(
                       d.get("min_step_fraction", 0.002)),
                   seed=d.get("seed"),
                   densify_to=int(d.get("densify_to", 12)),
                   move_endpoints=bool(d.get("move_endpoints", False)))


@dataclass
class OptimizeReport:
    """What the walk did."""

    initial_fos: float = math.nan
    final_fos: float = math.nan
    iterations: int = 0
    accepted: int = 0
    rejected: int = 0
    passes: int = 0
    notes: dict = field(default_factory=dict)

    @property
    def improvement(self) -> float:
        if not (math.isfinite(self.initial_fos)
                and math.isfinite(self.final_fos)):
            return 0.0
        return self.initial_fos - self.final_fos

    @property
    def improved(self) -> bool:
        return self.improvement > 0.0

    def summary(self) -> str:
        return (f"{self.initial_fos:.4f} → {self.final_fos:.4f} "
                f"({self.improvement:+.4f}) in {self.iterations} "
                f"evaluations, {self.accepted} accepted")


def _densify(points, target: int) -> list:
    """Insert vertices along a polyline until it has ``target`` of them.

    Points are added on the LONGEST segment each time, so the extra
    freedom goes where the surface is least defined instead of bunching
    up at one end.
    """
    pts = list(points)
    while len(pts) < target and len(pts) >= 2:
        lengths = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        i = lengths.index(max(lengths))
        a, b = pts[i], pts[i + 1]
        pts.insert(i + 1, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0))
    return pts


# ======================================================================
def optimize_surface(project, search, surface, settings=None):
    """Random-walk a non-circular surface towards a lower factor.

    Args:
        project: the model (never modified).
        search: a configured search object, used only to evaluate
            candidates — so the optimisation honours exactly the same
            method, slicing and admissibility settings as the search that
            produced the starting surface.
        surface: the starting :class:`SlipSurface`.
        settings: :class:`OptimizeSettings`.

    Returns ``(best_surface, best_result, report)``.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface

    opts = settings or OptimizeSettings()
    rep = OptimizeReport()
    rng = random.Random(opts.seed)

    pts = [(v.x, v.y) for v in surface.polyline.vertices]
    if opts.densify_to and len(pts) < opts.densify_to:
        pts = _densify(pts, opts.densify_to)
    if len(pts) < 3:
        rep.notes["error"] = (
            "Optimisation needs at least three vertices: there is "
            "nothing to move on a two-point surface.")
        return surface, None, rep

    def _make(points):
        return SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in points], closed=False))

    def _evaluate(points):
        try:
            return search.evaluate_surface(project, _make(points))
        except Exception:  # noqa: BLE001
            return None

    best_res = _evaluate(pts)
    if best_res is None or not best_res.is_valid:
        rep.notes["error"] = "The starting surface could not be evaluated."
        return surface, best_res, rep
    rep.initial_fos = best_res.fos
    best_fos = best_res.fos
    best_pts = list(pts)

    length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1.0
    step = length * opts.step_fraction
    min_step = length * opts.min_step_fraction

    first = 0 if opts.move_endpoints else 1
    last = len(pts) if opts.move_endpoints else len(pts) - 1

    stalled = 0
    while rep.iterations < opts.max_iterations and stalled < 6:
        rep.passes += 1
        improved_this_pass = False
        order = list(range(first, last))
        rng.shuffle(order)
        for i in order:
            if rep.iterations >= opts.max_iterations:
                break
            angle = rng.uniform(0.0, 2.0 * math.pi)
            mag = rng.uniform(0.2, 1.0) * step
            trial = list(best_pts)
            trial[i] = (best_pts[i][0] + mag * math.cos(angle),
                        best_pts[i][1] + mag * math.sin(angle))
            # x must stay strictly increasing: a surface that doubles
            # back is not a valid failure mechanism, and generating one
            # would waste an evaluation on a candidate the filters reject.
            if i > 0 and trial[i][0] <= trial[i - 1][0]:
                continue
            if i < len(trial) - 1 and trial[i][0] >= trial[i + 1][0]:
                continue

            res = _evaluate(trial)
            rep.iterations += 1
            # Admissibility matters most here: optimisation chases a
            # LOWER factor, which is exactly where kinematically
            # impossible surfaces live.
            if (res is None or not res.is_valid
                    or not getattr(res, "admissible", True)):
                rep.rejected += 1
                continue
            if res.fos < best_fos - opts.tolerance:
                best_fos = res.fos
                best_pts = trial
                best_res = res
                rep.accepted += 1
                improved_this_pass = True
            else:
                rep.rejected += 1

        if improved_this_pass:
            stalled = 0
        else:
            # A whole pass without improvement: shrink the step rather
            # than stop, because the surface may simply need finer moves.
            # The step is FLOORED instead of being allowed to end the run
            # — exiting the moment it underflows gave a walk of ten
            # evaluations on a four-vertex surface, which optimises
            # nothing. The run ends on the iteration budget, or after
            # several fruitless passes at the finest step.
            if step > min_step:
                step = max(step * 0.5, min_step)
            else:
                stalled += 1

    rep.final_fos = best_fos
    return _make(best_pts), best_res, rep
