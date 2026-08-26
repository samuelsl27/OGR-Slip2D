# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.126 — the Particle Swarm search, and its multimodal mode: several
distinct local minima instead of one.

What these tests protect
------------------------

**The two failure modes of verification problem 103.** Guo, S. and
Griffiths, D.V. (2020), "Failure mechanisms in two-layer undrained
slopes", *Canadian Geotechnical Journal* **57**(10) 1617-1621, publish
the geometry in full — H = 18 m, cot(beta) = 2, depth ratio D = 2,
cu1 = 60 kPa, unit weight 20 kN/m3 — and their Table 2 publishes the
strength ratio at which the critical mechanism switches from DEEP
(tangent to the firm base, through the stronger foundation) to SHALLOW
(inside the embankment alone). For cot(beta) = 2 and D = 2 that ratio is
Pcrit = 1.5.

The manual of the reference program replicates the same slope and
publishes eight factors of safety inside its figure 103.3, four of which
matter here::

              ratio 1.4   ratio 1.5   ratio 1.6
    deep        1.215       1.290       1.366
    shallow       -         1.324       1.315   <- the global minimum at 1.6

and concludes that "the split into the two failure modes must occur
somewhere between the 1.5 and 1.6 ratios". Its own uni-modal search
reports 1.366 at ratio 1.6 — the DEEP branch — while its multimodal one
finds the 1.315 below it. That is the whole argument for the feature,
published by the reference and not commented on there.

**The identity that costs nothing to check and catches most mistakes.**
The shallow mechanism never touches the foundation, so its factor of
safety CANNOT depend on cu2. Measured with a circular grid before any of
this was written: 1.3580 at ratio 1.5 and 1.3580 at ratio 1.6, the same
circle, digit for digit.

**What "significant" means.** The reference states it: a radius, 10 % of
the span of the search space by default, and NOT a difference in factor
of safety. ``TestWhatMakesAMinimumDistinct`` pins the algorithm — the
species-seed identification of Li (2004) — on synthetic input where the
right answer is known by inspection, so a failure there is about the
grouping rule and not about a slope.

**Reproducibility.** Three of the six searches promised since v0.1.74
that the same seed gives the same answer. A swarm is the most stochastic
thing in the program and has to keep that promise too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402

from ogr_core.geometry import (  # noqa: E402
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
)
from ogr_core.materials import Material  # noqa: E402
from ogr_core.materials.builtin_models import Undrained  # noqa: E402
from ogr_core.project import Project  # noqa: E402
from ogr_slip2d.methods import method_registry  # noqa: E402
from ogr_slip2d.particle_swarm import (  # noqa: E402
    ParticleSwarmSearch,
    species_seeds,
)
from ogr_slip2d.search import GridSearch  # noqa: E402

_H = 18.0
_CU1 = 60.0
_GAMMA = 20.0
_SEED = 20260826

#: Swarm size for the tests. Smaller than the reference default of 50 so
#: the file stays affordable; large enough that both basins of problem
#: 103 are populated, which was checked before the number was fixed.
_N = 24
_ITER = 20
_SLICES = 30


def _p103(cu2: float) -> Project:
    """The two-layer undrained slope, with the manual's own extents.

    Measured off the panels of figure 103.3 in pixels: 2.27 H behind the
    crest and 1.33 H beyond the toe, not the 6 H and 5 H the paper used
    to kill boundary effects. It makes almost no difference — 1.3022
    against 1.3043 on the deep branch — and using the manual's is the
    honest choice when comparing against the manual's numbers.
    """
    left = 2.22 * _H
    x_toe = left + 2.0 * _H
    right = x_toe + 1.33 * _H
    p = Project("p103")
    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(right, 0.0), Vertex(right, _H),
        Vertex(x_toe, _H), Vertex(left, 2.0 * _H), Vertex(0.0, 2.0 * _H),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0.0, _H), Vertex(right, _H)], closed=False),
        btype=BoundaryType.MATERIAL))
    emb = Material(name="embankment", unit_weight=_GAMMA,
                   strength=Undrained(cohesion=_CU1))
    fnd = Material(name="foundation", unit_weight=_GAMMA,
                   strength=Undrained(cohesion=cu2))
    p.materials = [emb, fnd]
    p.resolve_regions()
    p.assign_material_at(left + 1.0, 1.5 * _H, emb.id)
    p.assign_material_at(left + 1.0, 0.5 * _H, fnd.id)
    p.settings.methods.num_slices = _SLICES
    return p


def _swarm(**kw) -> ParticleSwarmSearch:
    opts = dict(method=method_registry()["spencer"](), num_slices=_SLICES,
                num_particles=_N, num_iterations=_ITER, seed=_SEED)
    opts.update(kw)
    return ParticleSwarmSearch(**opts)


def _lowest(surface) -> float:
    """The lowest elevation a surface reaches, circle or polyline.

    Both shapes turn up here: the swarm's particles are circles, and if
    the optimisation is on each reported minimum has been reshaped into a
    polyline. Asking the surface rather than assuming a radius is what
    lets the same test read either.
    """
    pl = getattr(surface, "polyline", None)
    if pl is not None and getattr(pl, "vertices", None):
        return min(v.y for v in pl.vertices)
    return surface.centre_y - surface.radius


def _is_deep(result) -> bool:
    """A minimum that reaches below the toe level is the deep mechanism.

    The two mechanisms are told apart by WHERE THEY RUN and not by their
    factor of safety, which is the same distinction the multimodal search
    itself makes.
    """
    return _lowest(result.surface) < _H - 1.0


# ======================================================================
class TestWhatMakesAMinimumDistinct:
    """The grouping rule, on input whose answer is obvious."""

    def test_two_far_apart_are_two(self):
        items = [((0.0, 0.0, 0.0), 1.5, "a"), ((1.0, 1.0, 1.0), 1.2, "b")]
        assert species_seeds(items, 0.3) == ["b", "a"]

    def test_two_close_together_are_one_and_the_better_wins(self):
        items = [((0.0, 0.0, 0.0), 1.5, "a"), ((0.01, 0.0, 0.0), 1.2, "b")]
        assert species_seeds(items, 0.3) == ["b"]

    def test_the_factor_of_safety_does_not_group_anything(self):
        """Two mechanisms with almost the same factor in different parts
        of the slope are two answers. The reference's filter is a
        distance and only a distance; grouping by factor as well would
        merge exactly the pair the search exists to separate."""
        items = [((0.0, 0.0, 0.0), 1.2000, "a"),
                 ((1.0, 1.0, 1.0), 1.2001, "b")]
        assert len(species_seeds(items, 0.3)) == 2

    def test_a_bigger_radius_reports_fewer(self):
        items = [((0.0, 0.0, 0.0), 1.5, "a"),
                 ((0.2, 0.0, 0.0), 1.4, "b"),
                 ((1.0, 1.0, 1.0), 1.3, "c")]
        assert len(species_seeds(items, 0.1)) == 3
        assert len(species_seeds(items, 0.5)) == 2

    def test_unevaluable_entries_are_not_minima(self):
        items = [((0.0, 0.0, 0.0), float("inf"), "a"),
                 ((1.0, 1.0, 1.0), 1.3, "c")]
        assert species_seeds(items, 0.1) == ["c"]


# ======================================================================
class TestTheSwarmFindsBothMechanisms:
    """Problem 103, and the structure the manual publishes."""

    def test_multimodal_separates_deep_from_shallow(self):
        r = _swarm(multiple_minima=True).run(_p103(90.0))   # ratio 1.5
        assert len(r.minima) >= 2, (
            "only %d minimum reported on the ratio the reference calls "
            "the transition" % len(r.minima))
        kinds = {_is_deep(m) for m in r.minima}
        assert kinds == {True, False}, (
            "the minima are all of one kind: %r"
            % [(round(m.fos, 4), _is_deep(m)) for m in r.minima])

    def test_unimodal_reports_exactly_one(self):
        r = _swarm(multiple_minima=False).run(_p103(90.0))
        assert len(r.minima) == 1
        assert r.minima[0].fos == pytest.approx(r.critical.fos, rel=1e-12)

    def test_the_shallow_branch_does_not_depend_on_the_foundation(self):
        """An exact identity: that mechanism never enters the foundation,
        so raising cu2 cannot move it. Any drift is the search, not the
        physics, which is why the tolerance is loose but the statement is
        not."""
        shallow = {}
        for cu2 in (90.0, 96.0):
            r = _swarm(multiple_minima=True).run(_p103(cu2))
            vals = [m.fos for m in r.minima if not _is_deep(m)]
            assert vals, "no shallow minimum at cu2 = %g" % cu2
            shallow[cu2] = min(vals)
        a, b = shallow[90.0], shallow[96.0]
        assert abs(a - b) / a < 0.02, (
            "the shallow branch moved with cu2: %.4f against %.4f" % (a, b))

    def test_the_deep_branch_rises_with_the_foundation(self):
        """And this one MUST move: it runs through the foundation, so its
        factor is very nearly proportional to cu2. The reference's own
        numbers give 1.290/1.215 = 1.0617 from ratio 1.4 to 1.5."""
        deep = {}
        for cu2 in (84.0, 90.0):
            r = _swarm(multiple_minima=True).run(_p103(cu2))
            vals = [m.fos for m in r.minima if _is_deep(m)]
            assert vals, "no deep minimum at cu2 = %g" % cu2
            deep[cu2] = min(vals)
        ratio = deep[90.0] / deep[84.0]
        assert 1.02 < ratio < 1.11, (
            "deep branch went %.4f -> %.4f, ratio %.4f, against the 1.0617 "
            "the reference publishes" % (deep[84.0], deep[90.0], ratio))


# ======================================================================
class TestTheSwarmIsASearch:
    """It has to be as good as the searches it sits beside."""

    def test_it_is_reproducible(self):
        a = _swarm(multiple_minima=True).run(_p103(90.0))
        b = _swarm(multiple_minima=True).run(_p103(90.0))
        assert [round(m.fos, 12) for m in a.minima] == \
            [round(m.fos, 12) for m in b.minima]

    def test_it_does_not_find_much_less_than_a_grid(self):
        """The inequality of v0.1.118, applied to the new search: the
        circles a grid tries are in the swarm's space too, so the swarm
        may not come back much higher. Five per cent, because a swarm of
        24 particles is a coarse instrument and the point is to catch a
        broken search, not to grade this one."""
        project = _p103(84.0)
        g = GridSearch(method=method_registry()["spencer"](),
                       num_slices=_SLICES, grid_nx=8, grid_ny=8,
                       radius_increment=8)
        grid = g.run(project).critical
        pso = _swarm().run(project).critical
        assert pso.fos < grid.fos * 1.05, (
            "swarm %.4f against grid %.4f" % (pso.fos, grid.fos))


# ======================================================================
class TestRuleSeven:
    """Every setting has to move the number, or the count."""

    def test_one_min_or_several_changes_the_count(self):
        one = _swarm(multiple_minima=False).run(_p103(90.0))
        many = _swarm(multiple_minima=True).run(_p103(90.0))
        assert len(many.minima) > len(one.minima)

    def test_the_radius_changes_the_count(self):
        wide = _swarm(multiple_minima=True, niche_radius_pct=60.0).run(
            _p103(90.0))
        narrow = _swarm(multiple_minima=True, niche_radius_pct=2.0).run(
            _p103(90.0))
        assert len(narrow.minima) > len(wide.minima), (
            "%d with a 2 %% radius against %d with 60 %%"
            % (len(narrow.minima), len(wide.minima)))

    def test_the_swarm_size_moves_the_number(self):
        small = _swarm(num_particles=6, num_iterations=5).run(_p103(90.0))
        big = _swarm(num_particles=40, num_iterations=25).run(_p103(90.0))
        assert small.critical.fos != pytest.approx(big.critical.fos,
                                                   rel=1e-9)
        assert big.critical.fos <= small.critical.fos

    def test_the_enhanced_algorithm_moves_the_number(self):
        """Its portion is this program's own choice — the reference does
        not publish one — so the least that can be asked of it is that it
        decides something."""
        on = _swarm(enhanced=True).run(_p103(90.0))
        off = _swarm(enhanced=False).run(_p103(90.0))
        assert on.critical.fos != pytest.approx(off.critical.fos, rel=1e-9)


# ======================================================================
class TestWhatMustNotMove:

    def test_the_other_searches_report_no_minima(self):
        """``SearchResult.minima`` is new, and every search that predates
        it has to leave it empty — otherwise a reader would take a grid's
        cloud for a set of distinct mechanisms."""
        g = GridSearch(method=method_registry()["spencer"](),
                       num_slices=_SLICES, grid_nx=5, grid_ny=5,
                       radius_increment=5)
        assert g.run(_p103(84.0)).minima == []


# ======================================================================
class TestASurfaceMayNotLeaveTheModel:
    """Anomaly D48, found by running problem 103 through the bank.

    The reference states the rule under *Grid Search* — "if a surface
    extends past the lower limits of the External Boundary, the surface
    is discarded, and is not analyzed" — and OGR had enforced it for
    CIRCLES since v0.1.84 and only for circles. Every surface an
    optimisation produces is a polyline, and the walk moves vertices
    towards a lower factor of safety, which is exactly the direction the
    outside of the model lies in.

    Measured on this model, whose floor is y = 0: the optimised critical
    surface reached y = -4.83, was judged valid AND admissible, and
    returned 1.0902 where the same surface clipped back to y >= 0 returns
    1.2676. Sixteen per cent, on the unsafe side.

    And the reason it paid: outside every material region
    ``Project.material_at`` answers None and the slicer falls back on the
    FIRST material of the project, which here is the embankment at
    cu = 60 kPa, the weaker of the two. Leaving the model was not merely
    permitted, it was rewarded.
    """

    #: The surface the bank run came back with, verbatim.
    ESCAPING = [
        (7.9162, 36.0), (15.8427, 24.4907), (25.1508, 15.0253),
        (27.7386, 12.5913), (35.4125, 5.9983), (41.2165, 1.3804),
        (48.5494, -2.9109), (56.1749, -4.8316), (63.7071, -3.808),
        (71.2195, 0.0072), (74.932, 2.6819), (83.7878, 9.9145),
        (92.7946, 18.0),
    ]

    @staticmethod
    def _surface(pts):
        from ogr_slip2d.surface import SlipSurface
        return SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))

    def _evaluator(self):
        return GridSearch(method=method_registry()["spencer"](),
                          num_slices=50, grid_nx=3, grid_ny=3,
                          radius_increment=3)

    def test_a_surface_below_the_floor_is_refused(self):
        assert self._evaluator().evaluate_surface(
            _p103(84.0), self._surface(self.ESCAPING)) is None

    def test_the_same_surface_inside_the_model_is_analysed(self):
        """The guard has to reject for leaving, not for being deep: the
        same polyline clipped to the floor is a perfectly good surface
        and must still be evaluated."""
        clipped = [(x, max(y, 0.0)) for x, y in self.ESCAPING]
        res = self._evaluator().evaluate_surface(
            _p103(84.0), self._surface(clipped))
        assert res is not None and res.is_valid
        # And it reads HIGHER, which is the whole point: the escape was
        # buying strength it had no right to.
        assert res.fos > 1.2

    def test_a_surface_grazing_the_floor_is_kept(self):
        """The tolerance is relative and the rule is 'below', not 'at'.
        A deep-seated mechanism tangent to the firm base is the most
        ordinary thing in this problem and may not be thrown away."""
        grazing = [(x, max(y, 0.0)) for x, y in self.ESCAPING]
        grazing[7] = (grazing[7][0], 0.0)
        res = self._evaluator().evaluate_surface(
            _p103(84.0), self._surface(grazing))
        assert res is not None and res.is_valid

    def test_the_rule_reads_the_floor_and_not_a_constant(self):
        """``polyline_leaves_soil`` asked directly, so the geometry rule
        is checkable without running an analysis."""
        from ogr_slip2d.surface import polyline_leaves_soil
        ext = [b for b in _p103(84.0).boundaries
               if b.btype == BoundaryType.EXTERNAL][0]
        ev = list(ext.polyline.vertices)
        assert polyline_leaves_soil(
            [Vertex(x, y) for x, y in self.ESCAPING], ev)
        assert not polyline_leaves_soil(
            [Vertex(x, max(y, 0.0)) for x, y in self.ESCAPING], ev)


# ======================================================================
class TestItSaysWhatItIsDoing:
    """Rule 7's minimum: a setting whose consequence is invisible has to
    be said out loud."""

    def _warnings(self, **search_kw):
        from ogr_slip2d.analysis_runner import _optimize_notes
        p = _p103(84.0)
        s = p.settings.search
        s.search_method = "particle_swarm"
        s.surface_type = "non_circular"
        for k, v in search_kw.items():
            setattr(s, k, v)
        return _optimize_notes(s)

    def test_several_minima_without_optimisation_is_announced(self):
        """The reference calls optimisation "strongly recommended with
        PSO, particularly in the case of multiple mins", because without
        it the search is hunting LOCAL minima and the lowest need not be
        the global one. Measured here at ratio 1.4: 1.3329 without and
        1.2538 with."""
        notes = self._warnings(pso_multiple_minima=True,
                               optimize_enabled=False)
        assert any("several minima" in n for n in notes), notes

    def test_nothing_is_said_when_optimisation_is_on(self):
        notes = self._warnings(pso_multiple_minima=True,
                               optimize_enabled=True)
        assert not any("several minima" in n for n in notes), notes

    def test_nothing_is_said_for_a_single_minimum(self):
        """The warning is about the multimodal mode, not about the
        optimisation being off, which is an ordinary choice."""
        notes = self._warnings(pso_multiple_minima=False,
                               optimize_enabled=False)
        assert not any("several minima" in n for n in notes), notes
