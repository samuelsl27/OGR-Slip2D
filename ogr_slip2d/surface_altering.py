# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Surface Altering — the second technique of *Optimize Surfaces* (v0.1.260,
D259).

The random walk of :mod:`ogr_slip2d.optimize` (Greco, 1996) moves one vertex
at a time by a random amount and keeps the move when the factor of safety
drops. It is a local search, and from far away it gets stuck: on the gabion
wall of verification problem 109 it starts from a Block Search surface at
F ~ 5 and stays at 2.16 (Bishop) and 4.8 (Spencer, GLE), with the published
mechanism, under the wall, at 1.8.

Surface Altering reshapes the WHOLE surface in a fixed sequence of small
bounded problems, each solved by a derivative-free trust-region method. The
scheme is described step by step in "Structure of Surface Altering", the
document the reference's help gives for it; its two sources are
Powell, M.J.D. (2009), *The BOBYQA algorithm for bound constrained
optimization without derivatives*, DAMTP 2009/NA06, University of Cambridge,
and Cheng, Y.M. (2003), "Location of critical failure surface and some
further studies on slope stability analysis", *Computers and Geotechnics*
30(3), 255-267, for the bounds that keep the surface convex. The surface is
a polyline of n control points. One pass is:

* **A — the ends.** Each end moves ALONG the ground (by arc length, so it can
  run down a vertical face), the other end fixed, and every point in between
  moves in proportion to its abscissa, ``d_i = d_a (x_i - x_b) / (x_a - x_b)``
  (Eq. 1). Read as a vector: the interior points follow the end's
  displacement, both of its components. The literal reading, one component
  only, puts a concave kink at the end as soon as it moves along a sloping
  face, which the document's own aim ("keeps the surface convex and
  ordered") rules out. Bounded by the Slope Limit window the end is in and
  by a fraction ``_END_REACH`` of the width.
* **B — interior pairs.** A pair of interior points stays fixed and the two
  ends move, the points outside the pair in proportion about the nearer one
  of it; then the ends stay fixed and the pair slides along the line through
  it, the interior points in proportion.
* **C — curvature.** The interior points move vertically, in sequence, left
  to right and then right to left. Each is bounded statically (inside the
  model, under the chord of the two ends, no further than 1.5 times their
  distance) and dynamically: never above the chord from the point before it
  to the last point, never below the line through the two points before it.
  The displacement asked for is rescaled from the static range onto the
  dynamic one, ``d' = d D / S`` (Eq. 2), so every surface proposed is convex.
* **D — weak layers.** After each C, every interior point is offered the
  elevation of each weak layer of the model at its abscissa, and the move is
  kept if it lowers the factor.

The document solves each step with BOBYQA. This module uses COBYQA
(Ragonneau, T.M. and Zhang, Z., the successor of Powell's methods, in SciPy
from 1.14), which is derivative-free, honours bounds and is deterministic.

Cheng (2003) is not yet in hand: the dynamic bounds here follow the scheme
as the document describes it, and are to be checked against the paper.

Everything the evaluation decides is decided by the search the surface came
from (``evaluate_surface``: the slicer and its refusals, the weak-layer
cases, the Slope Limits, the Surface Filters, the m-alpha and tensile
checks, the focus), exactly as for the random walk. Nothing here is random,
and the seed is not read.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Callable, Optional

#: The steps one pass runs, in order. A module tuple so that a test can run
#: a subset (restoring it afterwards); an analysis always runs all four.
STEPS = ("A", "B", "C", "D")

#: How far one step may move an end, as a fraction of the surface's width
#: (the document's alpha; it gives no value). Below 1 by necessity: it is
#: what keeps the denominator of Eq. 1 from changing sign, so that the
#: proportional move keeps x strictly increasing and a convex surface
#: convex. 0.5 never compresses a surface below half its width in one step;
#: passes compound, so larger migrations remain reachable. Fixed a priori:
#: its sensitivity on the verification bank is reported, never tuned to.
_END_REACH = 0.5

#: Interior pairs per pass in step B: the outermost, a middle and the
#: innermost symmetric pair. "Several combinations", at a bounded cost.
_PAIRS_PER_PASS = 3

#: Evaluations a sub-problem may spend per free variable, on top of the
#: 2n + 1 points COBYQA needs to build its first quadratic model.
_EVALS_PER_VARIABLE = 10

#: COBYQA's trust-region radii on the variables scaled to [-1, 1] by their
#: bounds, so both are relative to each sub-problem's own box and therefore
#: to the size of the model. 0.1 is COBYQA's own guidance ("one tenth of the
#: greatest expected change"); 1e-6 is the order of the slicer's tolerance.
_INITIAL_TR = 0.1
_FINAL_TR = 1e-6

#: Step C's static bound, from the document: no point moves further than
#: 1.5 times the distance between the two ends.
_CHORD_REACH = 1.5

#: A pass that moves no vertex by more than this fraction of the width has
#: converged ("no significant difference in the input geometry").
_GEOMETRY_TOL_REL = 1e-6

#: An end within this fraction of the width from the ground is on it; one
#: further away (a tension-crack end, for instance) stays where it is.
_ON_GROUND_REL = 1e-6

#: Two polylines that agree to this fraction of the width are one surface,
#: evaluated once.
_KEY_REL = 1e-12


class _BudgetExhausted(Exception):
    """The evaluation budget is spent: stop where we are."""


@dataclass
class SaoContext:
    """What :func:`alter` needs from :func:`optimize.optimize_surface`."""

    project: object
    opts: object                      # OptimizeSettings
    rep: object                       # OptimizeReport
    evaluate: Callable                # points -> LEMResult | None
    objective: Callable               # LEMResult -> float (FS or Ky)
    start_pts: list
    start_res: object
    start_score: float
    concave_ceiling: float
    windows: Optional[tuple] = None   # the search's Slope Limit windows


# ======================================================================
# Pure geometry
# ======================================================================
def _line_y(a, b, x: float) -> float:
    """Elevation at ``x`` of the line through ``a`` and ``b``."""
    if b[0] == a[0]:
        return max(a[1], b[1])
    return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])


def _monotone(pts) -> bool:
    return all(b[0] > a[0] for a, b in zip(pts, pts[1:]))


class GroundPath:
    """The ground surface as a path measured by arc length.

    Built from the vertices of ``ground_surface``: left to right, x never
    decreasing, a vertical face carried as two vertices with the same x.
    Measuring by arc length is what lets an end move up or down a vertical
    face, which a position given by x alone cannot (fig. 2 of the document).
    """

    def __init__(self, points) -> None:
        pts = []
        for x, y in points:
            p = (float(x), float(y))
            if not pts or p != pts[-1]:
                pts.append(p)
        self.pts = pts
        self.s = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.s.append(self.s[-1] + math.dist(a, b))

    @property
    def length(self) -> float:
        return self.s[-1]

    def point_at(self, s: float) -> tuple:
        """The point at arc length ``s`` (clamped to the path)."""
        if s <= 0.0:
            return self.pts[0]
        if s >= self.s[-1]:
            return self.pts[-1]
        i = min(bisect.bisect_right(self.s, s) - 1, len(self.pts) - 2)
        a, b = self.pts[i], self.pts[i + 1]
        seg = self.s[i + 1] - self.s[i]
        t = 0.0 if seg <= 0.0 else (s - self.s[i]) / seg
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    def locate(self, x: float, y: float) -> tuple:
        """``(distance, s)`` of the point of the path nearest ``(x, y)``."""
        best = None
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            span = dx * dx + dy * dy
            t = 0.0 if span <= 0.0 else max(0.0, min(1.0, (
                (x - a[0]) * dx + (y - a[1]) * dy) / span))
            px, py = a[0] + t * dx, a[1] + t * dy
            d = math.hypot(x - px, y - py)
            if best is None or d < best[0]:
                best = (d, self.s[i] + t * math.sqrt(span))
        return best if best is not None else (math.inf, 0.0)

    def window(self, lo: float, hi: float) -> tuple:
        """The arc-length range of the points whose x lies in ``[lo, hi]``.

        A vertical face at x = lo or x = hi is inside, all of it: the Slope
        Limits are abscissae and an end on that face has that abscissa.
        """
        pts, s = self.pts, self.s
        if pts[0][0] >= lo:
            s_lo = 0.0
        else:
            s_lo = s[-1]
            for i, (a, b) in enumerate(zip(pts, pts[1:])):
                if b[0] >= lo:
                    t = 0.0 if b[0] == a[0] else (lo - a[0]) / (b[0] - a[0])
                    s_lo = s[i] + max(0.0, min(1.0, t)) * (s[i + 1] - s[i])
                    break
        if pts[-1][0] <= hi:
            s_hi = s[-1]
        else:
            s_hi = 0.0
            for i in range(len(pts) - 2, -1, -1):
                a, b = pts[i], pts[i + 1]
                if a[0] <= hi:
                    if b[0] <= hi:
                        s_hi = s[i + 1]
                    else:
                        t = (hi - a[0]) / (b[0] - a[0])
                        s_hi = s[i] + max(0.0, min(1.0, t)) * (s[i + 1] - s[i])
                    break
        return s_lo, s_hi


def stretch_from_end(pts, a: int, d) -> list:
    """Step A, Eq. 1: end ``a`` displaced by the vector ``d``, the other end
    fixed, every point in between moved by ``d`` times its weight
    ``(x_i - x_b) / (x_a - x_b)``. An affine map of determinant
    ``1 + d_x / (x_a - x_b)``: with ``|d_x|`` below the width it is
    positive, so x stays strictly increasing and a convex polyline stays
    convex, exactly."""
    n = len(pts)
    b = n - 1 if a == 0 else 0
    xa, xb = pts[a][0], pts[b][0]
    den = xa - xb
    out = []
    for x, y in pts:
        w = (x - xb) / den
        out.append((x + w * d[0], y + w * d[1]))
    out[a] = (pts[a][0] + d[0], pts[a][1] + d[1])
    out[b] = pts[b]
    return out


def stretch_about_pivots(pts, j: int, k: int, d0, dn) -> list:
    """Step B (i): points ``j`` to ``k`` fixed, the left end displaced by
    ``d0`` and the right end by ``dn``, the points outside the fixed stretch
    moved in proportion about the nearer of ``j`` and ``k`` (Eq. 1 with that
    point as the fixed one)."""
    out = list(pts)
    x0, xj = pts[0][0], pts[j][0]
    for i in range(0, j):
        w = (pts[i][0] - xj) / (x0 - xj)
        out[i] = (pts[i][0] + w * d0[0], pts[i][1] + w * d0[1])
    xn, xk = pts[-1][0], pts[k][0]
    for i in range(k + 1, len(pts)):
        w = (pts[i][0] - xk) / (xn - xk)
        out[i] = (pts[i][0] + w * dn[0], pts[i][1] + w * dn[1])
    out[0] = (pts[0][0] + d0[0], pts[0][1] + d0[1])
    out[-1] = (pts[-1][0] + dn[0], pts[-1][1] + dn[1])
    return out


def slide_pair(pts, j: int, k: int, tj: float, tk: float) -> list:
    """Step B (ii): the ends fixed, points ``j`` and ``k`` moved by ``tj``
    and ``tk`` along the unit direction of the line through them, and every
    other interior point by the piecewise-linear interpolation of those two
    displacements in x (zero at both ends)."""
    n = len(pts)
    (xj, yj), (xk, yk) = pts[j], pts[k]
    length = math.hypot(xk - xj, yk - yj)
    if length <= 0.0:
        return list(pts)
    ux, uy = (xk - xj) / length, (yk - yj) / length
    x0, xn = pts[0][0], pts[-1][0]
    out = list(pts)
    for i in range(1, n - 1):
        x = pts[i][0]
        if i < j:
            f = (x - x0) / (xj - x0)
            t = f * tj
        elif i == j:
            t = tj
        elif i < k:
            f = (x - xj) / (xk - xj)
            t = tj + f * (tk - tj)
        elif i == k:
            t = tk
        else:
            f = (xn - x) / (xn - xk)
            t = f * tk
        out[i] = (pts[i][0] + t * ux, pts[i][1] + t * uy)
    return out


def static_bounds(pts, ground_y: Callable, floor_y: Callable) -> tuple:
    """Step C's static bounds ``(LS, US)``, one per point (zero at the
    ends): how far each interior point may go down and up. Up: no higher
    than the ground, nor than the chord of the two ends, nor 1.5 times the
    distance between them; down: no lower than the floor of the model, nor
    1.5 times that distance. Never negative."""
    n = len(pts)
    reach = _CHORD_REACH * math.dist(pts[0], pts[-1])
    ls, us = [0.0] * n, [0.0] * n
    for i in range(1, n - 1):
        x, y = pts[i]
        g = ground_y(x)
        f = floor_y(x)
        chord = _line_y(pts[0], pts[-1], x)
        up = min(reach, chord - y, (g - y) if g is not None else reach)
        dn = min(reach, (y - f) if f is not None else reach)
        us[i] = max(0.0, up)
        ls[i] = max(0.0, dn)
    return ls, us


def curvature_map(pts, v, ls, us, reverse: bool = False) -> list:
    """Step C, Eq. 2: the interior points displaced vertically in sequence,
    each displacement ``v[i-1]`` (inside ``[-LS_i, US_i]``) rescaled from
    the static range onto the dynamic one.

    The dynamic range of point ``i``, with the points before it already
    moved: under the chord from the point before it to the last point (UD),
    above the line through the two points before it (LD). Where the point
    starts outside it, it is first put on the bound it crosses — the
    document's rule for UD ("the y-coordinate of point P_i will be changed
    such that upper dynamic bound is evaluated as zero"); the same rule for
    LD is this module's own, symmetric extension. The dynamic range has
    priority over the static one, as in the document: the room a point is
    then given is the smaller of the two, so the result is convex at every
    interior vertex for ANY displacement. A point the dynamic rule pushes
    outside its static range (above the ground, say) gives a surface the
    evaluation refuses. ``reverse`` runs the sequence right to left, with
    "before" and "last" mirrored."""
    n = len(pts)
    out = list(pts)
    order = range(n - 2, 0, -1) if reverse else range(1, n - 1)
    end = pts[0] if reverse else pts[-1]
    for i in order:
        x, y0 = pts[i]
        prev = out[i + 1] if reverse else out[i - 1]
        dyn_hi = _line_y(prev, end, x)
        dyn_lo = -math.inf
        two_back = (i <= n - 3) if reverse else (i >= 2)
        if two_back:
            p2 = out[i + 2] if reverse else out[i - 2]
            dyn_lo = _line_y(p2, prev, x)
        # The line through the two points before never rises above the
        # chord from the point before to the last one once those points
        # respect their own UD, so the dynamic range is never empty; the
        # min() is the guard for a start that is not convex.
        y = min(max(y0, dyn_lo), dyn_hi)
        up = max(0.0, min(dyn_hi, y0 + us[i]) - y)
        dn = max(0.0, y - max(dyn_lo, y0 - ls[i]))
        vi = float(v[i - 1])
        if vi > 0.0 and us[i] > 0.0:
            y += vi * up / us[i]
        elif vi < 0.0 and ls[i] > 0.0:
            y += vi * dn / ls[i]
        out[i] = (x, y)
    return out


def _pairs(n: int) -> list:
    """Step B's symmetric interior pairs ``(j, n-1-j)``: the outermost, a
    middle one and the innermost, without repeats."""
    jmax = (n - 2) // 2
    if n < 4 or jmax < 1:
        return []
    picks = [1, (1 + jmax) // 2, jmax][:_PAIRS_PER_PASS]
    out = []
    for j in picks:
        k = n - 1 - j
        if 0 < j < k < n - 1 and (j, k) not in out:
            out.append((j, k))
    return out


# ======================================================================
# The objective
# ======================================================================
class _Run:
    """The state one alteration carries across its sub-problems: the best
    surface ever evaluated, the cache, the budget and the counts."""

    def __init__(self, ctx: SaoContext) -> None:
        self.ctx = ctx
        self.rep = ctx.rep
        self.best_pts = list(ctx.start_pts)
        self.best_res = ctx.start_res
        self.best_fos = ctx.start_res.fos
        self.best_score = ctx.start_score
        self.width = max(abs(self.best_pts[-1][0] - self.best_pts[0][0]),
                         1e-12)
        self.budget = int(ctx.opts.max_iterations)
        self.cache = {self._key(self.best_pts): self.best_score}
        self.refused = 0
        self.subproblems = 0
        self.snaps = 0
        self.ends_fixed: set = set()

    def _key(self, pts) -> tuple:
        q = _KEY_REL * self.width
        return tuple((round(x / q), round(y / q)) for x, y in pts)

    def value(self, pts) -> Optional[float]:
        """The objective of ``pts``, or None when it is not usable.

        Counting is the random walk's: an evaluation is an iteration, and it
        is accepted when it lowers the best score and rejected otherwise —
        so ``accepted + rejected == iterations``. A polyline that doubles
        back or bends past the concave ceiling is refused before an
        evaluation is spent on it, and counted apart."""
        k = self._key(pts)
        if k in self.cache:
            return self.cache[k]
        if (not _monotone(pts)
                or _max_concave(pts) > self.ctx.concave_ceiling):
            self.refused += 1
            self.cache[k] = None
            return None
        if self.rep.iterations >= self.budget:
            raise _BudgetExhausted
        res = self.ctx.evaluate(pts)
        self.rep.iterations += 1
        if (res is None or not res.is_valid
                or not getattr(res, "admissible", True)):
            self.rep.rejected += 1
            self.cache[k] = None
            return None
        score = self.ctx.objective(res)
        if score < self.best_score:
            self.best_score = score
            self.best_fos = res.fos
            self.best_pts = list(pts)
            self.best_res = res
            self.rep.accepted += 1
        else:
            self.rep.rejected += 1
        self.cache[k] = score
        return score

    def solve(self, mapping: Callable, lb, ub) -> None:
        """Minimise the objective of ``mapping(v)`` over the box
        ``[lb, ub]`` with COBYQA. ``lb <= 0 <= ub``; a variable whose bounds
        coincide is held at 0.

        Inadmissible and unusable candidates get a finite penalty that is
        worse than the start and grows with the distance from it, so the
        quadratic model is pulled back towards valid ground. Never NaN:
        COBYQA replaces it with an enormous barrier that spoils every model
        built through it."""
        import numpy as np
        from scipy.optimize import Bounds, minimize

        lb = np.asarray(lb, dtype=float)
        ub = np.asarray(ub, dtype=float)
        free = ub - lb > 1e-15 * max(1.0, float(np.max(np.abs(ub - lb))))
        if not free.any():
            return
        remaining = self.budget - self.rep.iterations
        if remaining <= 0:
            raise _BudgetExhausted
        n_var = int(free.sum())
        maxfev = min(2 * n_var + 1 + _EVALS_PER_VARIABLE * n_var,
                     remaining + 1)

        def full(w):
            v = np.zeros(len(lb))
            v[free] = w
            return v

        zero = np.zeros(n_var)
        f_ref = self.value(mapping(full(zero)))
        if f_ref is None:
            f_ref = self.best_score
        half = (ub[free] - lb[free]) / 2.0
        delta = max(abs(f_ref), 1e-3)

        def f(w):
            val = self.value(mapping(full(w)))
            if val is None:
                return f_ref + delta * (1.0 + float(np.linalg.norm(w / half)))
            return val

        self.subproblems += 1
        minimize(f, zero, method="COBYQA",
                 bounds=Bounds(lb[free], ub[free]),
                 options={"maxfev": max(maxfev, n_var + 2),
                          "initial_tr_radius": _INITIAL_TR,
                          "final_tr_radius": _FINAL_TR,
                          "scale": True, "disp": False})


def _max_concave(pts) -> float:
    from .optimize import max_concave_angle_deg
    return max_concave_angle_deg(pts)


# ======================================================================
# The steps
# ======================================================================
def _end_state(run: _Run, path: GroundPath, windows, pts, a: int):
    """``(s0, s_lo, s_hi)`` of end ``a`` on the ground path and inside its
    Slope Limit window, or None when it has to stay where it is (not on the
    ground, or in no window)."""
    d, s0 = path.locate(*pts[a])
    if d > _ON_GROUND_REL * run.width:
        run.ends_fixed.add("first" if a == 0 else "last")
        return None
    x = pts[a][0]
    tol = 1e-9 * run.width
    for lo, hi in windows:
        if lo - tol <= x <= hi + tol:
            s_lo, s_hi = path.window(lo, hi)
            return s0, min(s_lo, s0), max(s_hi, s0)
    run.ends_fixed.add("first" if a == 0 else "last")
    return None


def _end_move(path: GroundPath, s0: float, ds: float) -> tuple:
    """The displacement of an end moved ``ds`` along the path. Zero for
    ``ds == 0``, so a sub-problem starts on the surface it was handed."""
    if ds == 0.0:
        return (0.0, 0.0)
    a = path.point_at(s0)
    b = path.point_at(s0 + ds)
    return (b[0] - a[0], b[1] - a[1])


def _end_bounds(state, reach: float) -> tuple:
    if state is None:
        return 0.0, 0.0
    s0, s_lo, s_hi = state
    return -min(s0 - s_lo, reach), min(s_hi - s0, reach)


def _step_a(run: _Run, path: GroundPath, windows) -> None:
    for a in (0, -1):
        base = list(run.best_pts)
        idx = 0 if a == 0 else len(base) - 1
        state = _end_state(run, path, windows, base, idx)
        if state is None:
            continue
        lo, hi = _end_bounds(state, _END_REACH * run.width)
        s0 = state[0]
        run.solve(lambda v, base=base, idx=idx, s0=s0: stretch_from_end(
            base, idx, _end_move(path, s0, float(v[0]))), [lo], [hi])


def _step_b(run: _Run, path: GroundPath, windows) -> None:
    for j, k in _pairs(len(run.best_pts)):
        # (i) the pair fixed, the ends moved.
        base = list(run.best_pts)
        n = len(base)
        left = _end_state(run, path, windows, base, 0)
        right = _end_state(run, path, windows, base, n - 1)
        lo0, hi0 = _end_bounds(left, _END_REACH * (base[j][0] - base[0][0]))
        lon, hin = _end_bounds(right,
                               _END_REACH * (base[-1][0] - base[k][0]))
        s0 = left[0] if left else 0.0
        sn = right[0] if right else 0.0
        run.solve(lambda v, base=base, j=j, k=k, s0=s0, sn=sn:
                  stretch_about_pivots(
                      base, j, k,
                      _end_move(path, s0, float(v[0])) if left else (0, 0),
                      _end_move(path, sn, float(v[1])) if right else (0, 0)),
                  [lo0, lon], [hi0, hin])
        # (ii) the ends fixed, the pair slid along its own line.
        base = list(run.best_pts)
        (xj, yj), (xk, yk) = base[j], base[k]
        length = math.hypot(xk - xj, yk - yj)
        ux = (xk - xj) / length if length > 0.0 else 0.0
        if ux <= 0.0:
            continue
        cap = _CHORD_REACH * math.dist(base[0], base[-1])
        x0, xn = base[0][0], base[-1][0]
        lb = [max(-cap, -_END_REACH * (xj - x0) / ux),
              max(-cap, -_END_REACH * (xk - xj) / (2.0 * ux))]
        ub = [min(cap, _END_REACH * (xk - xj) / (2.0 * ux)),
              min(cap, _END_REACH * (xn - xk) / ux)]
        run.solve(lambda v, base=base, j=j, k=k: slide_pair(
            base, j, k, float(v[0]), float(v[1])), lb, ub)


def _envelopes(project):
    """``(ground_y, floor_y)``: the model's ground and floor at an x."""
    from ogr_core.geometry import (bedrock_surface, envelope_y_at,
                                   ground_surface)
    ext = project.external_boundary()
    if ext is None:
        return (lambda x: None), (lambda x: None)
    top = ground_surface(ext)
    bed = bedrock_surface(ext)
    return ((lambda x: envelope_y_at(top, x)),
            (lambda x: envelope_y_at(bed, x, upper=False)))


def _step_c(run: _Run, envelopes, reverse: bool) -> None:
    base = list(run.best_pts)
    if len(base) < 3:
        return
    ls, us = static_bounds(base, *envelopes)
    lb = [-ls[i] for i in range(1, len(base) - 1)]
    ub = [us[i] for i in range(1, len(base) - 1)]
    run.solve(lambda v, base=base: curvature_map(base, v, ls, us,
                                                 reverse=reverse), lb, ub)


def _step_d(run: _Run, envelopes, bands, reverse: bool) -> None:
    """Weak-layer snapping: each interior point, in C's order, offered the
    elevation of every weak layer at its abscissa within its static
    bounds; kept when it lowers the factor."""
    if not bands:
        return
    n = len(run.best_pts)
    order = range(n - 2, 0, -1) if reverse else range(1, n - 1)
    for i in order:
        base = list(run.best_pts)
        ls, us = static_bounds(base, *envelopes)
        x, y = base[i]
        tol = _ON_GROUND_REL * run.width
        for band in bands:
            yb = band.y_at(x)
            if yb is None or abs(yb - y) <= tol:
                continue
            if not (y - ls[i] - tol <= yb <= y + us[i] + tol):
                continue
            trial = list(base)
            trial[i] = (x, yb)
            before = run.best_score
            run.value(trial)
            if run.best_score < before:
                run.snaps += 1
                break


def alter(ctx: SaoContext) -> tuple:
    """Run Surface Altering from ``ctx.start_pts``.

    Returns ``(best_pts, best_res, best_fos, best_score)``; the report in
    ``ctx.rep`` is filled in place (see :class:`_Run.value` for how
    evaluations are counted). The passes stop when the budget is spent, when
    a pass improves nothing (everything is deterministic, so the next pass
    would repeat it exactly), when a pass moves no vertex by more than
    ``_GEOMETRY_TOL_REL`` of the width, or on the tolerance criterion of the
    reference (the last five passes, as for the random walk)."""
    from ogr_core.geometry import ground_surface

    from .optimize import _converged
    from .weak_layers import weak_layer_bands

    run = _Run(ctx)
    ext = ctx.project.external_boundary()
    path = GroundPath((v.x, v.y) for v in ground_surface(ext).vertices)
    windows = tuple(ctx.windows) if ctx.windows else (
        (path.pts[0][0], path.pts[-1][0]),)
    envelopes = _envelopes(ctx.project)
    bands = weak_layer_bands(ctx.project) if "D" in STEPS else ()
    history: list = []
    stopped = None
    try:
        while True:
            if run.rep.iterations >= run.budget:
                stopped = "budget"
                break
            run.rep.passes += 1
            before_pts = list(run.best_pts)
            before = run.best_score
            if "A" in STEPS:
                _step_a(run, path, windows)
            if "B" in STEPS:
                _step_b(run, path, windows)
            if "C" in STEPS:
                _step_c(run, envelopes, reverse=False)
            if "D" in STEPS:
                _step_d(run, envelopes, bands, reverse=False)
            if "C" in STEPS:
                _step_c(run, envelopes, reverse=True)
            if "D" in STEPS:
                _step_d(run, envelopes, bands, reverse=True)
            history.append(run.best_score)
            if not run.best_score < before:
                stopped = "no_progress"
                break
            moved = max((math.dist(a, b) for a, b in
                         zip(before_pts, run.best_pts)), default=0.0)
            if moved < _GEOMETRY_TOL_REL * run.width:
                stopped = "geometry"
                break
            if _converged(history, float(ctx.opts.tolerance)):
                stopped = "tolerance"
                break
    except _BudgetExhausted:
        stopped = "budget"
    notes = ctx.rep.notes
    notes["stopped_by"] = stopped
    notes["subproblems"] = run.subproblems
    notes["refused_before_evaluation"] = run.refused
    if bands:
        notes["weak_layer_snaps"] = run.snaps
    if run.ends_fixed:
        notes["ends_fixed"] = sorted(run.ends_fixed)
    return run.best_pts, run.best_res, run.best_fos, run.best_score
