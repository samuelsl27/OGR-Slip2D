# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.119 — Simulated Annealing may not converge worse than a
circle, and its randomness must live in its own generator.

**The invariant** is the one ``test_search_inequality_v1118`` states for
the Path and Block searches, now for the third non-circular one: the space
of circles is contained in the space of polylines, so whatever a grid
search finds, the annealing has to be able to reach. When it cannot, the
number the user is shown is too HIGH — a mechanism that exists and was not
reported. Defect D22.

**What was wrong**, because it is not what the pendiente predicted and the
next person will otherwise re-walk that road. ``_evaluate_polyline`` asked
a candidate for ``is_valid`` and never for ``admissible``;
``SearchResult.critical`` asks for both. So the annealing was descending
towards surfaces the program then refuses to publish. Measured on the slope
below at 300 generation steps: 83-98 % of the evaluated population was
inadmissible (``m_alpha < 0.2``, Whitman & Bailey 1967), the last fifty
evaluations were inadmissible in every seed tried, and the local phase
converged to 0.500 — the floor of a guard written in v0.1.17 to stop
exactly this — while 1.36 was reported. The reported number was the best
admissible surface the walk happened to cross on the way in: a by-product.

That also explains the symptom the pendiente could not: MORE effort made
the answer WORSE (1.3631 at 300 steps, 1.4341 at 1000), because a bigger
budget is a better descent into the wrong basin. The fix it predicted —
``ngen`` 1000 instead of 50, ``nepsilon`` 5 instead of 3 — was measured one
change at a time and does nothing; the budget one makes it worse still.

The second half was the formulation's, not a bug of arithmetic: Su (2009)
section 2.1 counts ``n = 2N - 2`` degrees of freedom because "the two
extremity points of the failure surface can only move along the slope
line". This search froze them at the toe and crest of the steepest ground
segment, so on the slope below every surface it could express entered and
left within x = [30.00, 50.00] while the critical circle daylights at 30.03
and 51.45.

Three things this file protects, all of which were real:

* the annealing must not STEER by surfaces it will not report;
* the two extremities must move;
* the seed must be the search's own, not ``random.seed()`` on the module.
  The test that existed reproduced and passed for the wrong reason: a
  global re-seed also reproduces. Non-interference is a second property and
  nothing checked it.

Note what is NOT asserted, because it was measured and is false: that a
single annealing run always lands below the discretised circle. Over
fifteen runs on three models, three came out above it, by up to 1.2 %. It
is a stochastic global optimiser and one draw is one draw; the honest
statement is over the small set of runs an engineer would actually make,
which is what ``_best_of`` below does. Picking the lucky seed instead would
be the kind of test this project calls a snapshot.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_search_inequality_v1118 import (  # noqa: E402
    _chord_reference, _layered_slope)


# ----------------------------------------------------------------------
def _sa_slope():
    """The v0.1.17 annealing slope: H = 12 m, 30.96 deg, 10 m of foundation.

    Kept identical to ``test_sa_autorefine_v117._slope`` on purpose — it is
    the model every measurement of this defect was taken on, from v0.1.89's
    0.500 onwards, so the numbers in the changelog and the numbers here are
    the same numbers.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 12.0
    toe = 30.0
    crest = toe + H / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("d22")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p, toe, crest


def _bishop():
    from ogr_slip2d import BishopSimplified
    return BishopSimplified()


def _annealing(method, seed, *, num_slices=25, steps=300, optimize=True,
               **kw):
    """A search built the way ``build_search`` builds one for this method.

    ``optimize`` defaults to True because that is what the resolved setting
    gives a Simulated Annealing project since v0.1.119, and a test that
    quietly ran a different configuration from the interface would be
    measuring something nobody uses.
    """
    from ogr_slip2d.optimize import OptimizeSettings
    from ogr_slip2d.search import SimulatedAnnealingSearch

    s = SimulatedAnnealingSearch(method=method, initial_vertices=9,
                                 generation_steps=steps,
                                 num_slices=num_slices, seed=seed, **kw)
    if optimize:
        s.optimize = OptimizeSettings(enabled=True)
        s.optimize_seed = 13
    return s


def _best_of(project, method, seeds, **kw):
    """The best of a few runs, and the surface that produced it."""
    best = None
    for seed in seeds:
        r = _annealing(method, seed, **kw).run(project)
        assert r.critical is not None, f"seed {seed} found nothing"
        if best is None or r.min_fos < best.min_fos:
            best = r
    return best


def _circular_minimum(project, method, num_slices=25, **grid):
    from ogr_slip2d.search import GridSearch
    r = GridSearch(method=method, num_slices=num_slices, **grid).run(project)
    assert r.critical is not None, "the grid found nothing"
    return r.critical


# ======================================================================
class TestTheInequalityHoldsForTheAnnealing:
    """The same comparison as D21, against the winning circle redrawn in
    the same number of chords the annealing itself produced — because a
    polyline of n chords inscribed in an arc is not the arc, and always
    reads higher."""

    def test_on_the_annealing_slope(self):
        p, _toe, _crest = _sa_slope()
        circular = _circular_minimum(p, _bishop(), grid_nx=12, grid_ny=12,
                                     radius_increment=20)
        best = _best_of(p, _bishop(), (1234, 3, 42))
        n = len(best.critical.surface.polyline.vertices) - 1
        ref = _chord_reference(p, circular.surface, n)
        assert best.min_fos <= ref + 1e-9, (
            "annealing %.6f > same circle in %d chords %.6f (arc %.6f)"
            % (best.min_fos, n, ref, circular.fos))

    def test_on_the_four_layer_benchmark(self):
        """The model D21 was closed on, so the three non-circular searches
        are finally measured against one another on one problem."""
        p = _layered_slope()
        circular = _circular_minimum(p, _bishop(), num_slices=15,
                                     grid_nx=8, grid_ny=8,
                                     radius_increment=6)
        best = _best_of(p, _bishop(), (11, 5), num_slices=15)
        n = len(best.critical.surface.polyline.vertices) - 1
        ref = _chord_reference(p, circular.surface, n)
        assert best.min_fos <= ref + 1e-9, (
            "annealing %.6f > same circle in %d chords %.6f (arc %.6f)"
            % (best.min_fos, n, ref, circular.fos))


# ======================================================================
class TestAgainstThePublishedNonCircularMinimum:
    """The external reference ``docs/PENDIENTES.md`` said did not exist.

    The slope of ``validacion/casos/002-yamagami-ueta-1988`` — c' = 9.8
    kPa, phi' = 10 deg, gamma = 17.64 kN/m3 — has a published NON-circular
    minimum, which is the quantity a non-circular search is supposed to
    find and which no test of this program had ever been compared against:

    * Yamagami, T. & Ueta, Y. (1988). Search for noncircular slip surfaces
      by the Morgenstern-Price method. Proc. 6th Int. Conf. on Numerical
      Methods in Geomechanics, Innsbruck, 1219-1223. Reported 1.338-1.348.
    * Greco, V. R. (1996). Efficient Monte Carlo technique for locating
      critical slip surface. J. Geotech. Engrg. 122(7), 517-525. Reported
      1.327-1.333 on the same slope.

    Two honesty notes, both of which decide how the test is written:

    * the published values are Morgenstern-Price with f(x) = 1, and the
      method used here is Spencer, which is the constant-f(x) member of
      that family. Close, not identical — so this is a BAND, not a value,
      and the band is the union of the two publications;
    * ``caso.md`` keeps Spencer out of that case's ``esperado.json`` on
      purpose. This test does not overrule that: it asserts a band wide
      enough to catch a gross regression and nothing finer, and it travels
      with the method-independent inequality above.

    What it discriminates is not subtle. Before v0.1.119 the annealing
    returned 1.5026-1.5401 here, 13 % above everything ever published for
    this slope, and above its own circular minimum of 1.3446.
    """

    #: The union of the two publications, with the 0.5 % that separates
    #: Spencer from Morgenstern-Price with f(x) = 1 allowed on each side.
    BAND = (1.327 * 0.995, 1.348 * 1.005)

    @staticmethod
    def _model():
        from ogr_core.project import Project
        return Project.load(
            Path(__file__).resolve().parent.parent / "validacion" / "casos"
            / "002-yamagami-ueta-1988" / "modelo.ogr")

    def test_spencer_lands_in_the_published_band(self):
        from ogr_slip2d import Spencer

        best = _best_of(self._model(), Spencer(), (1234, 2024))
        lo, hi = self.BAND
        assert lo <= best.min_fos <= hi, (
            "annealing %.4f outside the published non-circular band "
            "%.4f..%.4f" % (best.min_fos, lo, hi))

    def test_it_is_below_the_circular_minimum_of_the_same_model(self):
        """The property that does NOT depend on the interslice
        assumption, and the one the pendiente is about."""
        from ogr_slip2d import Spencer

        p = self._model()
        circular = _circular_minimum(p, Spencer(), grid_nx=10, grid_ny=10,
                                     radius_increment=15)
        best = _best_of(p, Spencer(), (1234, 2024))
        assert best.min_fos < circular.fos, (best.min_fos, circular.fos)


# ======================================================================
class TestTheSearchDoesNotSteerByWhatItWillNotPublish:
    """Rule 7, and the root cause in one assertion."""

    def test_the_admissibility_gate_moves_the_number(self):
        """With the m-alpha check off there is nothing to bar, so the walk
        is free to descend where it used to. Same seed, same everything
        else: if the gate ever stops applying, this goes red."""
        p, _toe, _crest = _sa_slope()
        gated = _annealing(_bishop(), 1234).run(p)
        ungated = _annealing(_bishop(), 1234, check_m_alpha=False).run(p)
        assert gated.critical is not None and ungated.critical is not None
        assert abs(gated.min_fos - ungated.min_fos) > 1e-9, (
            gated.min_fos, ungated.min_fos)

    def test_the_population_it_walks_is_almost_all_admissible(self):
        """The measurement, not the mechanism: the walk used to end up
        with 83-98 % of its evaluations barred from ever being the answer,
        and the LAST FIFTY inadmissible in every seed. The threshold is
        deliberately loose — what is being excluded is a search living
        inside the forbidden basin, not a handful of rejects on the way."""
        p, _toe, _crest = _sa_slope()
        r = _annealing(_bishop(), 1234).run(p)
        valid = [q for q in r.evaluations if q.is_valid]
        assert valid
        bad = sum(1 for q in valid if not getattr(q, "admissible", True))
        assert bad / len(valid) < 0.25, (bad, len(valid))

    def test_inadmissible_surfaces_are_still_counted(self):
        """Not steered by, but not hidden either: they were generated and
        analysed, and ``inadmissible_count`` has to keep meaning here what
        it means in the other five searches."""
        p, _toe, _crest = _sa_slope()
        r = _annealing(_bishop(), 1234).run(p)
        assert r.valid_count == len([q for q in r.evaluations if q.is_valid])
        assert r.analysed_count <= r.valid_count


# ======================================================================
class TestTheExtremitiesAreControlVariables:
    """Su (2009) section 2.1: ``n = 2N - 2`` because "the two extremity
    points of the failure surface can only move along the slope line".
    They were nailed to the ends of the steepest ground segment."""

    def test_the_critical_surface_leaves_the_steepest_segment(self):
        p, toe, crest = _sa_slope()
        r = _annealing(_bishop(), 1234).run(p)
        v = r.critical.surface.polyline.vertices
        assert v[0].x < toe - 1e-6 or v[-1].x > crest + 1e-6, (
            "both ends still pinned at [%.3f, %.3f]: %.3f .. %.3f"
            % (toe, crest, v[0].x, v[-1].x))

    def test_the_slope_limits_bound_where_the_ends_may_go(self):
        """Rule 7 — and this is where the Slope Limits reach the
        GENERATION of this search and not only the mass filter."""
        p, _toe, _crest = _sa_slope()
        wide = _annealing(_bishop(), 1234).run(p)
        narrow = _annealing(_bishop(), 1234,
                            slope_limits=(31.0, 49.0)).run(p)
        assert wide.critical is not None and narrow.critical is not None
        assert abs(narrow.min_fos - wide.min_fos) > 1e-9
        for v in narrow.critical.surface.polyline.vertices:
            assert 31.0 - 1e-6 <= v.x <= 49.0 + 1e-6, v.x


# ======================================================================
class TestTheSeedIsTheSearchsOwn:
    """Rule 5. ``random.seed(self.seed)`` on the module reproduced — it
    re-seeded on every run — and still leaked: it left the process-wide
    stream wherever the annealing left it. Reproducibility and
    non-interference are two properties and only the first was checked."""

    def test_two_runs_with_one_seed_agree_exactly(self):
        p, _toe, _crest = _sa_slope()
        a = _annealing(_bishop(), 77).run(p)
        b = _annealing(_bishop(), 77).run(p)
        assert a.min_fos == b.min_fos
        assert a.valid_count == b.valid_count

    def test_the_global_generator_is_not_touched(self):
        p, _toe, _crest = _sa_slope()
        state = random.getstate()
        try:
            random.seed(4321)
            before = random.getstate()
            _annealing(_bishop(), 77).run(p)
            assert random.getstate() == before
        finally:
            random.setstate(state)

    def test_the_answer_does_not_depend_on_the_global_generator(self):
        """The half the old test could not tell apart: a search that
        re-seeds the module also reproduces, so agreeing with itself
        proved nothing about where its numbers came from."""
        p, _toe, _crest = _sa_slope()
        state = random.getstate()
        try:
            random.seed(1)
            a = _annealing(_bishop(), 77).run(p)
            random.seed(999999)
            b = _annealing(_bishop(), 77).run(p)
            assert a.min_fos == b.min_fos
        finally:
            random.setstate(state)

    def test_an_unseeded_search_still_explores(self):
        p, _toe, _crest = _sa_slope()
        vals = {_annealing(_bishop(), None, steps=120).run(p).min_fos
                for _ in range(3)}
        assert len(vals) > 1, vals
