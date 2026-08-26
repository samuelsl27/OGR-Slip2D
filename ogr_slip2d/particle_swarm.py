# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Particle Swarm search, with a MULTIMODAL mode that returns several
distinct local minima instead of one.

Why a swarm, and why its particles are circles
----------------------------------------------

A slope rarely has one critical region. Every search in this program
returns the single worst surface it found and says nothing about whether
another mechanism exists a few metres away — which is the thing an
engineer needs in order to decide where to reinforce. Answering that
needs a POPULATION method: a single-trajectory search like simulated
annealing has one surface at a time and nothing to spread out over the
basins.

Each particle here is a CIRCLE, encoded as the three numbers that
generate one in :class:`ogr_slip2d.search.SlopeFrame` — where the surface
daylights on the toe side, where it enters on the crest side, and its
inclination at the toe. Three consequences follow, and all three are the
reason for the choice:

* the search space is a box with real bounds (the Slope Limits and the
  angle window), so "a radius of 10 % of the span of the search space"
  means something without a dimension having to be invented;
* a generated circle always daylights, instead of being rejected;
* it reuses ``SlopeSearch._circle_from_point_tangent_point``, which has
  been generating circles since v0.1.17.

Non-circular surfaces are produced afterwards by the optimisation, which
is the same division of labour the reference documents: its own swarm
searches spherical or ellipsoidal surfaces and its surface-altering
optimisation reshapes the winners.

The update rules, and where they come from
------------------------------------------

Particle swarm optimisation is Kennedy, J. and Eberhart, R. (1995),
"Particle swarm optimization", *Proceedings of the IEEE International
Conference on Neural Networks*, 1942-1948.

The reference program documents the two forms it uses, and they are the
ones implemented here::

    S_{i+1} = S_i + V_i
    unimodal:    V_i = rand1 (SG - S_i) + rand2 (SB - S_i)
    multimodal:  V_i = rand1 (N1 - S_i) + rand2 (N2 - S_i)

with SG the best position found by the whole swarm, SB the best found by
that particle, and N1, N2 the two nearest neighbouring particles.

**Where this departs from the canonical algorithm, said out loud**: the
form above carries NO inertia term and no constriction factor — the
canonical update is ``V_{i+1} = w V_i + c1 r1 (pbest - x) + c2 r2
(gbest - x)``. The documented form is the one reproduced, because the
object here is to reproduce the documented behaviour, not to write the
best swarm; a note in :meth:`ParticleSwarmSearch._step` says so at the
point where it matters.

Replacing the two global attractors by the nearest neighbours is what
turns a swarm that converges on one optimum into one that settles on
several. It is the idea of Qu, B.Y., Suganthan, P.N. and Das, S. (2013),
"A distance-based locally informed particle swarm model for multimodal
optimization", *IEEE Transactions on Evolutionary Computation* **17**(3)
387-402, whose neighbourhoods are likewise Euclidean and whose point is
that no niching parameter has to be chosen for the SEARCH.

What makes a minimum a different minimum
----------------------------------------

A niching parameter is still needed to REPORT, and the reference states
it: a radius, defaulting to 10 % of the span of the search space, which
"filters out the surfaces that are similar and only takes the most
critical local minima in each region". The algorithm that does it is the
species-seed identification of Li, X. (2004), "Adaptively choosing
neighbourhood bests using species in a particle swarm optimizer for
multimodal function optimization", *GECCO 2004*, LNCS **3102** 105-116:
sort by fitness, let the best unassigned particle found a species,
assign everything within the radius to it, repeat.

**The factor of safety plays no part in that decision**, and that is the
source's choice rather than an omission. Two mechanisms with the same
factor in different parts of the slope are two answers; the same
mechanism found twice is one.

For the wider context of these methods on slip surfaces see Cheng, Y.M.,
Li, L., Chi, S.-C. and Wei, W.B. (2007), "Performance studies on six
heuristic global optimization methods in the location of critical slip
surface", *Computers and Geotechnics* **34**(6) 462-484.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import random
from typing import Optional

from ogr_core.project import Project

from .search import (BaseSearch, PathSearch, SearchResult, SlopeSearch,
                     slope_frame)
from .surface import SlipCircle

#: Fraction of the swarm relocated at random at the end of an iteration
#: when the enhanced algorithm is on.
#:
#: The reference documents the modification —"randomly relocates a
#: portion of the particles having the highest factor of safety at the
#: end of each iteration"— and does NOT publish the portion. A fifth is
#: this program's own choice: enough that a swarm which has collapsed
#: onto one basin keeps probing elsewhere, small enough that four fifths
#: of the population still carry the search forward. It is declared here
#: rather than buried so that the number can be argued with.
_ENHANCED_RELOCATED_FRACTION = 0.2

#: The angle window the swarm searches when the user has not set one.
#:
#: It is WIDER than the Slope Search's, and the difference is not a
#: preference. That window's upper limit is (beta - 5) degrees, which
#: presumes a circle leaving the ground AT THE TOE; a deep-seated
#: mechanism daylights well beyond it, on the flat, and needs a much
#: steeper tangent there. Measured on verification problem 103: the
#: critical deep circle wants +49.5 degrees where (beta - 5) is +21.6, so
#: with the narrow window the swarm never reached that basin at all — the
#: minimum came back at 1.4167 against a grid's 1.3036, and not one of
#: the reported minima was the deep mechanism. Widened, the swarm finds
#: it and reports it.
#:
#: The Slope Search is left alone: it recovers the deep circle through
#: its local refinement stage, which perturbs centre and radius directly
#: and so escapes the window its generation works in. And the reference
#: gives its own swarm no angle controls at all — "requires no user
#: defined search objects" — so inheriting a limit written for a
#: different search would be borrowing a restriction nobody stated.
#:
#: 85 and not 90: a tangent at 90 degrees is a vertical surface at the
#: exit point, which the base-angle admissibility check rejects anyway.
_WIDE_ANGLE_LO = -85.0
_WIDE_ANGLE_HI = 85.0

#: A particle that cannot be evaluated is not simply dropped: it keeps
#: its place in the swarm with an infinite factor, so the population size
#: stays what the user asked for and the neighbour geometry does not
#: silently change from one iteration to the next.
_INVALID = math.inf


class _Particle:
    """One trial circle, as a point of the unit cube plus its history."""

    __slots__ = ("u", "v", "fos", "best_u", "best_fos", "result")

    def __init__(self, u):
        self.u = list(u)
        self.v = [0.0, 0.0, 0.0]
        self.fos = _INVALID
        self.best_u = list(u)
        self.best_fos = _INVALID
        self.result = None


def _distance(a, b) -> float:
    """Euclidean distance in the unit cube.

    The cube is why this is meaningful: two abscissae in metres and an
    angle in radians have no common distance until they are normalised,
    and a radius quoted as a percentage of the search space has no
    meaning until they are.
    """
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def species_seeds(items, radius: float) -> list:
    """Species seeds of ``items``, best first.

    ``items`` is a sequence of ``(key_position, fos, payload)``. Returns
    the payloads of the seeds: the best item overall, then the best of
    what is left outside the radius of every seed already taken, and so
    on. Li (2004), section 3.

    Ties in ``fos`` are broken by the original order, so the same input
    always gives the same seeds — a search that promised reproducibility
    from a seed cannot have its REPORTING depend on sort instability.
    """
    order = sorted(range(len(items)), key=lambda i: (items[i][1], i))
    seeds = []
    taken_positions = []
    for i in order:
        pos, fos, payload = items[i]
        if not math.isfinite(fos):
            continue
        if any(_distance(pos, p) < radius for p in taken_positions):
            continue
        taken_positions.append(pos)
        seeds.append(payload)
    return seeds


class ParticleSwarmSearch(BaseSearch):
    """Particle Swarm search over circular surfaces, uni- or multimodal.

    ``multiple_minima=False`` reproduces the ordinary search: one answer,
    the global minimum. ``True`` reports every distinct local minimum the
    swarm settled on, in :attr:`SearchResult.minima`.
    """

    def __init__(
        self,
        method,
        num_particles: int = 50,
        num_iterations: int = 50,
        multiple_minima: bool = False,
        niche_radius_pct: float = 10.0,
        enhanced: bool = True,
        initial_angle_lower_deg: float = _WIDE_ANGLE_LO,
        initial_angle_upper_deg: Optional[float] = _WIDE_ANGLE_HI,
        num_slices: int = 30,
        min_area: float = 0.5,
        seed: Optional[int] = 1234,
        progress_cb=None,
        **legacy_kwargs,
    ) -> None:
        from .search import _base_kwargs

        super().__init__(method=method, num_slices=num_slices,
                         **_base_kwargs(legacy_kwargs))
        # Floors rather than exceptions: these arrive from a settings file
        # that a user can edit by hand, and a swarm of zero particles is
        # not a configuration to refuse, it is one to make sense of. Two
        # is the smallest swarm the multimodal update can even express —
        # it needs two neighbours that are not itself.
        self.num_particles = max(3, int(num_particles))
        self.num_iterations = max(1, int(num_iterations))
        self.multiple_minima = bool(multiple_minima)
        self.niche_radius = max(0.0, float(niche_radius_pct)) / 100.0
        self.enhanced = bool(enhanced)
        self.initial_angle_lower_deg = initial_angle_lower_deg
        self.initial_angle_upper_deg = initial_angle_upper_deg
        self.min_area = min_area
        self.progress_cb = progress_cb
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------
    def _evaluate(self, project, frame, result, u):
        """Factor of safety of the circle at ``u``, and its result.

        Returns ``(fos, LEMResult or None)``. Everything generated is
        appended to ``result.evaluations``, valid or not, so the counts
        the user is shown are the counts the search really made.
        """
        xt, xc, theta = frame.circle_params(*u)
        yt = PathSearch._interpolate_top_y(frame.top, xt)
        yc = PathSearch._interpolate_top_y(frame.top, xc)
        if yt is None or yc is None or abs(xc - xt) < 0.5:
            result.invalid_count += 1
            return _INVALID, None
        circle = SlopeSearch._circle_from_point_tangent_point(
            xt, yt, theta, xc, yc, frame.to_right)
        if circle is None:
            result.invalid_count += 1
            return _INVALID, None
        cx, cy, radius = circle
        if radius <= 0 or radius > 50.0 * max(frame.height, 1.0):
            result.invalid_count += 1
            return _INVALID, None

        res = self.evaluate_circle(
            project, SlipCircle(centre_x=cx, centre_y=cy, radius=radius))
        if res is None:
            result.invalid_count += 1
            return _INVALID, None
        # The same absurd-factor guard the Slope Search applies. A circle
        # whose driving moment is almost zero reports an enormous factor
        # and would otherwise sit in the swarm as a perfectly ordinary
        # bad particle, dragging neighbours towards a region that is not
        # a mechanism at all.
        if res.is_valid and not (0.2 <= res.fos <= 100.0):
            result.invalid_count += 1
            return _INVALID, None
        result.evaluations.append(res)
        if not res.is_valid:
            result.invalid_count += 1
            return _INVALID, None
        result.valid_count += 1
        return res.fos, res

    # ------------------------------------------------------------------
    def _neighbours(self, swarm, i):
        """The two particles nearest to ``swarm[i]``, itself excluded."""
        me = swarm[i].u
        ranked = sorted(
            (j for j in range(len(swarm)) if j != i),
            key=lambda j: (_distance(me, swarm[j].u), j))
        return ranked[0], ranked[1] if len(ranked) > 1 else ranked[0]

    def _step(self, swarm, global_best_u):
        """One velocity-and-position update for the whole swarm.

        The two forms are the reference's own, and neither carries an
        inertia term or a constriction factor. That is a departure from
        the canonical algorithm of Kennedy and Eberhart (1995) and it is
        deliberate: what is being reproduced is the documented behaviour.
        Adding inertia would be a different search that happens to share
        the name.
        """
        for i, p in enumerate(swarm):
            if self.multiple_minima:
                j, k = self._neighbours(swarm, i)
                a = swarm[j].best_u if math.isfinite(swarm[j].best_fos) \
                    else swarm[j].u
                b = swarm[k].best_u if math.isfinite(swarm[k].best_fos) \
                    else swarm[k].u
            else:
                a = global_best_u
                b = p.best_u if math.isfinite(p.best_fos) else p.u
            r1 = self.rng.random()
            r2 = self.rng.random()
            for d in range(3):
                p.v[d] = r1 * (a[d] - p.u[d]) + r2 * (b[d] - p.u[d])
                # Reflect off the walls instead of clamping to them. A
                # clamp piles particles onto the face of the cube, where
                # they stop moving and stop informing their neighbours;
                # the reflection keeps them in the search.
                nu = p.u[d] + p.v[d]
                if nu < 0.0:
                    nu = -nu
                elif nu > 1.0:
                    nu = 2.0 - nu
                p.u[d] = 0.0 if nu < 0.0 else (1.0 if nu > 1.0 else nu)

    # ------------------------------------------------------------------
    def _run(self, project: Project) -> SearchResult:
        result = SearchResult(method_id=self.method.METHOD_ID)
        frame = slope_frame(project, self.initial_angle_lower_deg,
                            self.initial_angle_upper_deg)
        if frame is None:
            return result

        swarm = [_Particle([self.rng.random() for _ in range(3)])
                 for _ in range(self.num_particles)]
        global_best_u = list(swarm[0].u)
        global_best_fos = _INVALID

        total = self.num_iterations * self.num_particles
        done = 0
        for it in range(self.num_iterations):
            for p in swarm:
                p.fos, p.result = self._evaluate(project, frame, result, p.u)
                if p.fos < p.best_fos:
                    p.best_fos = p.fos
                    p.best_u = list(p.u)
                if p.fos < global_best_fos:
                    global_best_fos = p.fos
                    global_best_u = list(p.u)
                done += 1
            if self.progress_cb is not None:
                self.progress_cb(done, total)

            if it < self.num_iterations - 1:
                self._step(swarm, global_best_u)
                if self.enhanced:
                    self._relocate_worst(swarm)

        result.minima = self._report_minima(swarm, project, frame, result)
        return result

    # ------------------------------------------------------------------
    def _relocate_worst(self, swarm) -> None:
        """Scatter the worst particles again.

        The reference's own modification, and it earns its keep in the
        multimodal case: a swarm whose species have all converged has
        nothing left to explore with, and the particles sitting on the
        highest factors are the ones contributing least.
        """
        n = int(round(_ENHANCED_RELOCATED_FRACTION * len(swarm)))
        if n <= 0:
            return
        # Ties by index, so the same seed relocates the same particles.
        order = sorted(range(len(swarm)),
                       key=lambda i: (-swarm[i].fos
                                      if math.isfinite(swarm[i].fos)
                                      else -math.inf, i))
        for i in order[:n]:
            swarm[i].u = [self.rng.random() for _ in range(3)]
            swarm[i].v = [0.0, 0.0, 0.0]

    def _report_minima(self, swarm, project, frame, result) -> list:
        """The distinct minima to report, best first.

        In the one-minimum mode this is the global minimum alone, and it
        is still filled in: a caller should not have to ask which mode
        produced the result to know where to look.
        """
        finals = []
        for p in swarm:
            if not math.isfinite(p.best_fos):
                continue
            res = p.result if (p.result is not None
                               and abs(p.fos - p.best_fos) < 1e-12) else None
            if res is None:
                # The particle's best is not where it currently stands, so
                # the surface has to be rebuilt. Re-evaluating rather than
                # remembering every result keeps the swarm's memory to
                # three numbers per particle.
                fos, res = self._evaluate(project, frame, result, p.best_u)
                if res is None:
                    continue
            finals.append((tuple(p.best_u), p.best_fos, res))

        if not finals:
            return []
        if not self.multiple_minima:
            best = min(finals, key=lambda t: t[1])
            return [best[2]]
        # The radius is a fraction of the span of the unit cube, and the
        # span meant is the DIAGONAL: the reference speaks of one radius
        # for the whole space, not one per axis.
        radius = self.niche_radius * math.sqrt(3.0)
        return species_seeds(finals, radius)
