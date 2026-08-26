# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Surface optimisation — phase M4, completed in v0.1.104.

Refines a non-circular slip surface by **random walking** (Greco, 1996):
perturb one vertex at random, recompute the factor of safety, keep the
change when it lowers it, and stop when the surface stops moving.

It is not only a post-process for Block or Path Search — it works as a
search method in its own right, starting from a single user-defined
surface.

v0.1.104 — until now this module was reachable ONLY from the menu action
and from hand-written scripts: the thirteen ``optimize_*`` settings that
configure it were editable, saved to the ``.ogr`` and read by nobody
(defect D08, anomaly A9-1). They arrive here now, so every field of
:class:`OptimizeSettings` below either matches one of them or is marked as
this program's own.

Four points where the implementation makes a choice the reference leaves
open, each stated in the code rather than left to be inferred:

* **A pass, not a single failure, ends the run.** Stopping at the first
  rejected perturbation would abandon a surface that only needed a
  different vertex moved. A pass is the unit of progress here.
* **The step shrinks as the walk converges.** A fixed step either crawls
  at the start or cannot settle at the end; reducing it after each
  unproductive pass gives both. How much it shrinks is the reference's
  own *Step Reduction Factor*.
* **Every candidate goes through the admissibility filter.** Optimisation
  chases a lower factor of safety, which is exactly the direction in
  which kinematically impossible surfaces lie, so the check that guards
  the search must guard this too — otherwise the "improvement" is an
  artefact. The reference makes the same point its own way, with the
  *Use checks for depth, elevation, concave surface* option.
* **The convergence window counts PASSES, not evaluations** — see
  :func:`_converged`. This is the one mapping in the module that is not
  literal, and it is the one most worth reading.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from typing import Optional

#: How many of the most recent passes the convergence criterion averages
#: over. The reference states the number explicitly ("the average safety
#: factor of the last five iterations, including the current iteration"),
#: so it is a constant of the criterion and not a tuning knob.
_CONVERGENCE_WINDOW = 5

#: Automatic minimum distance between the slip surface and the ground, as a
#: fraction of the model's own relief, used when *Snap Shallow Surfaces to
#: Slope* is on and *Specify Distance* is off. The reference says only that
#: "the program will automatically determine a minimum allowable depth" and
#: does not publish the rule.
#:
#: Relative and not absolute, by the project's rule that a geometric
#: tolerance has to read the same in millimetres and in metres. The value is
#: a judgement, biased towards snapping slightly more rather than less: the
#: reference's own worked example shows that snapping RAISES the factor of
#: safety (1.644 to 1.658), so erring here errs on the safe side. Its
#: magnitude comes from the reference's own Specify Distance default, 0.01 m
#: on a model some tens of metres high — a few parts in ten thousand of the
#: relief — rounded up one step.
_SNAP_AUTO_REL_DEPTH = 1e-3

#: Trial directions probed per vertex when *Explore All Vertices Before
#: Moving Surface* is on. The reference says the "optimal direction of
#: movement" is determined for each vertex but not how; a random walk has
#: no gradient to follow, so the direction is the best of a small fan.
#: Three keeps the cost of one pass within a small multiple of the
#: one-at-a-time pass it replaces, which is what makes the two options
#: comparable at the same iteration budget.
_EXPLORE_PROBES = 3


@dataclass
class OptimizeSettings:
    """Options of the random-walk optimisation.

    The defaults are the reference panel's own, field for field, and NOT
    this module's historical ones (400 evaluations and a 1e-4 tolerance).
    That is deliberate: from v0.1.104 the same optimisation is reached from
    two doors — the *Optimize Surfaces* checkbox of the search options and
    the *Optimize Surfaces…* menu action — and v0.1.89 is on record for what
    happens when two doors into one calculation carry different defaults.
    """

    enabled: bool = False

    # ---- Surfaces to Optimize. Read by the search's post-pass, not by
    # ``optimize_surface`` itself, which is handed ONE surface; they live
    # here so that one object carries the whole panel.
    target: str = "global_minimum"   # global_minimum | all | fos_less_than
    fos_threshold: float = 1.5

    # ---- Optimization Options
    max_iterations: int = 4000
    #: Convergence criterion, NOT an acceptance threshold — see
    #: :func:`_converged` for what "iteration" maps onto here.
    tolerance: float = 1e-9
    #: "a factor (0 to 1) which determines the relative distance by which
    #: vertices are moved, during each iteration". 0.5 is the documented
    #: recommendation and was hard-coded here until v0.1.104.
    step_reduction_factor: float = 0.5
    #: Largest concave angle tolerated between adjacent segments, in
    #: degrees. 0.0 means none at all, which is what the reference's
    #: unticked checkbox means: "if this checkbox is not selected, then
    #: concave angles will not be allowed".
    max_concave_angle_deg: float = 5.0
    #: "if this checkbox is selected, then the optimal direction of movement
    #: will be determined for each vertex, and all vertices will be moved at
    #: once".
    explore_all_vertices: bool = False

    # ---- Snap Shallow Surfaces to Slope
    snap_shallow_to_slope: bool = True
    #: ``None`` means AUTOMATIC, which is the unticked *Specify Distance*.
    snap_distance: Optional[float] = None

    #: *Use checks for depth, elevation, concave surface*. Off makes the
    #: walk ignore the Surface Filters and the concave rule, which is the
    #: only way any of them can be turned off for the optimisation alone.
    use_surface_checks: bool = True

    # ---- This program's own, with no counterpart in the reference panel.
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
                "target": self.target,
                "fos_threshold": self.fos_threshold,
                "max_iterations": self.max_iterations,
                "tolerance": self.tolerance,
                "step_reduction_factor": self.step_reduction_factor,
                "max_concave_angle_deg": self.max_concave_angle_deg,
                "explore_all_vertices": self.explore_all_vertices,
                "snap_shallow_to_slope": self.snap_shallow_to_slope,
                "snap_distance": self.snap_distance,
                "use_surface_checks": self.use_surface_checks,
                "step_fraction": self.step_fraction,
                "min_step_fraction": self.min_step_fraction,
                "seed": self.seed, "densify_to": self.densify_to,
                "move_endpoints": self.move_endpoints}

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizeSettings":
        base = cls()
        snap = d.get("snap_distance", base.snap_distance)
        return cls(enabled=bool(d.get("enabled", base.enabled)),
                   target=str(d.get("target", base.target)),
                   fos_threshold=float(
                       d.get("fos_threshold", base.fos_threshold)),
                   max_iterations=int(
                       d.get("max_iterations", base.max_iterations)),
                   tolerance=float(d.get("tolerance", base.tolerance)),
                   step_reduction_factor=float(d.get(
                       "step_reduction_factor", base.step_reduction_factor)),
                   max_concave_angle_deg=float(d.get(
                       "max_concave_angle_deg", base.max_concave_angle_deg)),
                   explore_all_vertices=bool(d.get(
                       "explore_all_vertices", base.explore_all_vertices)),
                   snap_shallow_to_slope=bool(d.get(
                       "snap_shallow_to_slope", base.snap_shallow_to_slope)),
                   snap_distance=(None if snap is None else float(snap)),
                   use_surface_checks=bool(d.get(
                       "use_surface_checks", base.use_surface_checks)),
                   step_fraction=float(
                       d.get("step_fraction", base.step_fraction)),
                   min_step_fraction=float(
                       d.get("min_step_fraction", base.min_step_fraction)),
                   seed=d.get("seed"),
                   densify_to=int(d.get("densify_to", base.densify_to)),
                   move_endpoints=bool(
                       d.get("move_endpoints", base.move_endpoints)))


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


# ======================================================================
# The geometry of the concave constraint
# ======================================================================
def max_concave_angle_deg(points) -> float:
    """Largest CONCAVE turn of a left-to-right polyline, in degrees.

    Sign convention, and it is the one ``BlockSearch._is_convex_down`` and
    ``SimulatedAnnealingSearch._is_convex`` already use, so the three cannot
    disagree about what "convex" means: with the vertices ordered by
    increasing x, the cross product of two consecutive edges is POSITIVE at
    a vertex that dips like a bowl. That is the shape a sliding mass has,
    and it is what the reference draws as the valid surface.

    A vertex whose cross product is NEGATIVE bends the other way — the
    surface kinks up into the mass — and that is a *concave* angle. Its
    size is how far past straight the polyline turns: 0 degrees on a
    straight line, growing as the kink sharpens.

    Returns 0.0 for a polyline with no concave vertex, and for anything
    with fewer than three points.
    """
    pts = list(points)
    worst = 0.0
    for i in range(1, len(pts) - 1):
        ax = pts[i][0] - pts[i - 1][0]
        ay = pts[i][1] - pts[i - 1][1]
        bx = pts[i + 1][0] - pts[i][0]
        by = pts[i + 1][1] - pts[i][1]
        cross = ax * by - ay * bx
        if cross >= 0.0:
            continue                      # bowl-side turn: not concave
        dot = ax * bx + ay * by
        worst = max(worst, abs(math.degrees(math.atan2(cross, dot))))
    return worst


def _converged(history: list, tolerance: float) -> bool:
    """The reference's convergence criterion, on the right unit.

    Documented as: "when the difference in safety factor between the
    current iteration, and the average safety factor of the last five
    iterations (including the current iteration), is less than the
    Tolerance, then the optimization is considered to have converged".

    **What an "iteration" maps onto here, and why it is not an
    evaluation.** In the reference an iteration MOVES the surface: the
    optimal direction is worked out for a vertex and the vertex is then
    moved, so a run of iterations that barely changes the factor of safety
    really does mean the walk has settled. In this implementation the unit
    of work is a random trial, and most trials are rejected — with the
    documented default tolerance of 1e-9, five consecutive rejections would
    be enough to declare convergence, and five consecutive rejections are
    ordinary at any point in a random walk. The equivalent unit is the PASS
    over the vertices, which is already where the loop decides that nothing
    moved; that is what this window holds.
    """
    if len(history) < _CONVERGENCE_WINDOW:
        return False
    window = history[-_CONVERGENCE_WINDOW:]
    return abs(window[-1] - sum(window) / len(window)) < tolerance


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


def _evaluator_for(search, opts: "OptimizeSettings"):
    """The object candidates are scored against.

    Normally the search itself, so the optimisation honours exactly the
    same method, slicing and admissibility settings as the search that
    produced the starting surface. With *Use checks for depth, elevation,
    concave surface* off it is a SHALLOW COPY with the two Surface Filters
    cleared — shallow so it shares the method and the caches, and a copy so
    that the caller's search comes out of the optimisation unchanged.
    """
    if opts.use_surface_checks:
        return search
    relaxed = copy.copy(search)
    relaxed.min_elevation = None
    relaxed.min_depth = None
    return relaxed


def _ground_y(ground_vertices, x: float) -> Optional[float]:
    """Ground elevation at ``x``, or None outside the profile.

    v0.1.114 — through :func:`envelope_y_at`, because the profile steps at a
    vertical face and this used to return on the FIRST segment spanning
    ``x``. It already knew a vertical segment is worth its top end; what it
    did not know is that the segment BEFORE the step also spans that
    abscissa and comes first, so at the foot of a wall it answered with the
    bench and never reached the step at all.
    """
    vs = ground_vertices
    if not vs:
        return None
    if x < vs[0].x:
        return vs[0].y if abs(x - vs[0].x) < 1e-9 else None
    from ogr_core.geometry import Polyline, envelope_y_at
    y = envelope_y_at(Polyline(vertices=list(vs)), x)
    if y is not None:
        return y
    return vs[-1].y if abs(x - vs[-1].x) < 1e-9 else None


def _snap_shallow(project, points, distance: Optional[float]):
    """Lift near-surface vertices onto the ground and trim flush ends.

    "This will automatically remove very shallow portions at the ends of
    the slip surface, and the safety factor will be re-calculated."

    Returns ``(points, moved, distance_used)``; ``points`` is unchanged and
    ``moved`` is 0 when there is nothing shallow, so the caller can skip the
    re-evaluation. The two END vertices are never candidates: they lie on
    the ground by construction, which is not the artefact this option exists
    to remove.
    """
    from ogr_core.geometry import ground_surface

    external = project.external_boundary()
    if external is None:
        return list(points), 0, distance
    ground = list(ground_surface(external).vertices)
    if len(ground) < 2:
        return list(points), 0, distance
    if distance is None:
        relief = max(v.y for v in ground) - min(v.y for v in ground)
        distance = _SNAP_AUTO_REL_DEPTH * relief
    if distance <= 0.0:
        return list(points), 0, distance

    pts = list(points)
    moved = 0
    for i in range(1, len(pts) - 1):
        gy = _ground_y(ground, pts[i][0])
        if gy is None:
            continue
        if 0.0 <= gy - pts[i][1] < distance:
            pts[i] = (pts[i][0], gy)
            moved += 1
    if not moved:
        return list(points), 0, distance

    # Trim the flush run at each end: a vertex that now sits ON the ground
    # makes everything outside it a zero-thickness sliver, and that sliver
    # is precisely what was being removed.
    def _on_ground(p) -> bool:
        gy = _ground_y(ground, p[0])
        return gy is not None and abs(gy - p[1]) < 1e-9

    while len(pts) > 3 and _on_ground(pts[1]):
        pts.pop(0)
    while len(pts) > 3 and _on_ground(pts[-2]):
        pts.pop()
    return pts, moved, distance


# ======================================================================
def optimize_surface(project, search, surface, settings=None):
    """Random-walk a non-circular surface towards a lower factor.

    Greco, V.R. (1996), "Efficient Monte Carlo technique for locating
    critical slip surface", *Journal of Geotechnical Engineering* 122(7),
    517-525. A similar algorithm is given by Husein Malkawi, Hassan and
    Sarma (2001).

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

    evaluator = _evaluator_for(search, opts)

    def _make(points):
        return SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in points], closed=False))

    def _evaluate(points):
        try:
            return evaluator.evaluate_surface(project, _make(points))
        except Exception:  # noqa: BLE001
            return None

    best_res = _evaluate(pts)
    if best_res is None or not best_res.is_valid:
        rep.notes["error"] = "The starting surface could not be evaluated."
        return surface, best_res, rep
    rep.initial_fos = best_res.fos
    best_fos = best_res.fos
    best_pts = list(pts)

    # v0.1.127 — the walk descends the RUN's objective, which is the
    # factor of safety unless a seismic mode is on. Two variables and not
    # one because they are two different things: ``best_score`` is what
    # the walk minimises, and ``rep.initial_fos`` / ``rep.final_fos`` are
    # what the report SAYS, and a report that printed a critical seismic
    # coefficient under a heading reading "factor of safety" would be
    # exactly the contradiction this version went and removed from the
    # Interpret window and the terminal.
    #
    # Without this the walk would drag vertices towards a low factor of
    # safety while the run reported the Ky of wherever they ended up —
    # an optimisation optimising something nobody asked for.
    def _objective(res):
        scorer = getattr(evaluator, "score", None)
        return scorer(res) if scorer is not None else res.fos

    best_score = _objective(best_res)

    # The concave ceiling. The limit applies to "slip surfaces generated by
    # the optimization search", so it may not be allowed to outlaw the
    # surface the search HANDED us: a Block Search wedge can already carry a
    # sharper kink than 5 degrees, and a ceiling below it would reject every
    # candidate and turn the walk into a silent no-op. The ceiling is
    # therefore the looser of the two.
    concave_ceiling = math.inf
    if opts.use_surface_checks:
        concave_ceiling = max(float(opts.max_concave_angle_deg),
                              max_concave_angle_deg(pts))

    length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1.0
    step = length * opts.step_fraction
    min_step = length * opts.min_step_fraction
    # Clamped to (0, 1): 1.0 would never refine the step and 0.0 would drop
    # it to the floor on the first unproductive pass.
    reduction = min(max(float(opts.step_reduction_factor), 0.01), 0.99)

    first = 0 if opts.move_endpoints else 1
    last = len(pts) if opts.move_endpoints else len(pts) - 1

    def _admissible(trial, i) -> bool:
        """Cheap rejections, before an evaluation is spent on them."""
        # x must stay strictly increasing: a surface that doubles back is
        # not a valid failure mechanism, and generating one would waste an
        # evaluation on a candidate the filters reject.
        if i > 0 and trial[i][0] <= trial[i - 1][0]:
            return False
        if i < len(trial) - 1 and trial[i][0] >= trial[i + 1][0]:
            return False
        return max_concave_angle_deg(trial) <= concave_ceiling

    def _score(trial):
        """Evaluate one candidate. None when it is not usable."""
        res = _evaluate(trial)
        rep.iterations += 1
        # Admissibility matters most here: optimisation chases a LOWER
        # factor, which is exactly where kinematically impossible surfaces
        # live.
        if (res is None or not res.is_valid
                or not getattr(res, "admissible", True)):
            rep.rejected += 1
            return None
        return res

    history: list = []
    while rep.iterations < opts.max_iterations:
        rep.passes += 1
        order = list(range(first, last))
        rng.shuffle(order)
        improved_this_pass = False

        if opts.explore_all_vertices:
            # "the optimal direction of movement will be determined for each
            # vertex, and all vertices will be moved at once". The reference
            # does not say how that direction is found; here each vertex is
            # probed with a small random fan and the best probe is REMEMBERED
            # rather than committed, so the pass ends with one combined move
            # that is accepted or rejected whole.
            proposal = list(best_pts)
            for i in order:
                if rep.iterations >= opts.max_iterations:
                    break
                local_best = None
                local_score = best_score
                for _probe in range(_EXPLORE_PROBES):
                    if rep.iterations >= opts.max_iterations:
                        break
                    angle = rng.uniform(0.0, 2.0 * math.pi)
                    mag = rng.uniform(0.2, 1.0) * step
                    trial = list(best_pts)
                    trial[i] = (best_pts[i][0] + mag * math.cos(angle),
                                best_pts[i][1] + mag * math.sin(angle))
                    if not _admissible(trial, i):
                        continue
                    res = _score(trial)
                    if res is None:
                        continue
                    if _objective(res) < local_score:
                        local_score = _objective(res)
                        local_best = trial[i]
                        # Counted as accepted although the move is only
                        # REMEMBERED here, not committed: it is a move the
                        # walk decided to take, and leaving it uncounted
                        # would break the report's own arithmetic
                        # (accepted + rejected == iterations) in this mode
                        # and no other.
                        rep.accepted += 1
                    else:
                        rep.rejected += 1
                if local_best is not None:
                    proposal[i] = local_best
            if proposal != best_pts and rep.iterations < opts.max_iterations:
                if max_concave_angle_deg(proposal) <= concave_ceiling:
                    res = _score(proposal)
                    if res is not None and _objective(res) < best_score:
                        best_score = _objective(res)
                        best_fos, best_pts, best_res = res.fos, proposal, res
                        rep.accepted += 1
                        improved_this_pass = True
                    elif res is not None:
                        rep.rejected += 1
        else:
            for i in order:
                if rep.iterations >= opts.max_iterations:
                    break
                angle = rng.uniform(0.0, 2.0 * math.pi)
                mag = rng.uniform(0.2, 1.0) * step
                trial = list(best_pts)
                trial[i] = (best_pts[i][0] + mag * math.cos(angle),
                            best_pts[i][1] + mag * math.sin(angle))
                if not _admissible(trial, i):
                    continue
                res = _score(trial)
                if res is None:
                    continue
                if _objective(res) < best_score:
                    best_score = _objective(res)
                    best_fos = res.fos
                    best_pts = trial
                    best_res = res
                    rep.accepted += 1
                    improved_this_pass = True
                else:
                    rep.rejected += 1

        # v0.1.127 — the OBJECTIVE, not the factor of safety. A
        # stopping rule has to watch the quantity the walk is descending;
        # watching a different one is how a walk stops while the thing it
        # was minimising is still falling. The reference words its
        # criterion as "the difference in safety factor" because until
        # now there was nothing else to descend.
        #
        # NOTE, and it is the cost of the choice: with a seismic mode on,
        # the user's Tolerance is then a tolerance on Ky, whose scale is
        # an order of magnitude below a factor of safety. Said in the
        # changelog, because a setting that quietly changes what it
        # measures is the fault this project keeps finding.
        history.append(best_score)
        # Asked on EVERY pass, improving or not, because that is what the
        # criterion says: it compares the current factor of safety with the
        # average of the last five and stops when they agree. Asking only
        # on unproductive passes would subordinate the user's Tolerance to
        # this module's own step schedule, so a walk told to stop once the
        # factor moves by less than 0.01 would carry on until the step hit
        # its floor — a setting overruled by a detail it knows nothing
        # about, which is rule 7 in miniature.
        if _converged(history, opts.tolerance):
            break
        if improved_this_pass:
            continue
        if step > min_step:
            # A whole pass without improvement: shrink the step rather than
            # stop, because the surface may simply need finer moves. The
            # convergence window is CLEARED, not carried across — a finer
            # step is a fresh chance, and counting passes that failed at the
            # coarse step towards convergence would end the run before the
            # fine one had been tried at all.
            step = max(step * reduction, min_step)
            history.clear()

    # Snap Shallow Surfaces to Slope — after the walk, on its answer, and
    # then re-evaluated, because the factor of safety belongs to the surface
    # as finally shaped. It may come out HIGHER: that is the whole point of
    # the option, and the reference's own example shows it (1.644 to 1.658).
    if opts.snap_shallow_to_slope:
        snapped, moved, used = _snap_shallow(
            project, best_pts, opts.snap_distance)
        if moved:
            res = _evaluate(snapped)
            rep.notes["snap_distance"] = used
            rep.notes["snapped_vertices"] = moved
            if res is not None and res.is_valid:
                rep.notes["fos_before_snap"] = best_fos
                best_pts, best_fos, best_res = snapped, res.fos, res
                best_score = _objective(res)
            else:
                rep.notes["snap"] = (
                    "The snapped surface could not be evaluated; the "
                    "unsnapped one is reported.")

    rep.final_fos = best_fos
    return _make(best_pts), best_res, rep
