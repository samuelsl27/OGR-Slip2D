# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D87 — Overall Slope accumulates the statistics of a SURFACE, so its identity
has to be the surface: its type and its geometry to the last digit, extent
included. And the critical probabilistic surface is only named among the
surfaces that had a factor of safety in EVERY sample of the run.

**The invariants.**

1. Two evaluations share a key if and only if they are the same surface:
   same serialised type, same centre and radius, same extent (or the same
   vertices). Until v0.1.236 ``_surface_key`` rounded centre and radius to
   0.5 model units and left the extent and the type out, so the two
   DISJOINT sliding masses of one circle shared a key, a composite shared
   its uncut circle's, and two different circles of a grid less than half a
   unit apart shared one too — on bank problem 36, 746 of its 1570 keys
   gathered circles that are not the same, and two of them decided the
   critical probabilistic surface it published.
2. A probability of failure is a property of ONE surface over the samples:
   PF(S) = P[F(S, X) < 1]. Pooling two surfaces gives the PF of a mixture,
   and counting a surface only in the samples where the search happened to
   report it biases it, because which one it reports depends on X. So the
   candidate set is the surfaces with a factor in every counted sample,
   and then PF(critical probabilistic) <= PF(run) holds by construction —
   the property the reference documents for it (never above the PF of the
   whole run). The reference also says when there is none: the surface has
   to be present in every sample, which only the Grid, Slope, Path and
   Block searches guarantee (the guided ones analyse different surfaces
   every sample); the optimised surfaces are left out (and so is the walk
   the Slope Search adds after its population, which is one: both are
   marked in ``SearchResult.steered``); and it is not offered when the
   search minimises Ky.

The models: the notched slope of ``test_statistical_rebuild_v1154`` (Fredlund
and Krahn 1977, problem 22, with a notch in its crest), whose published
circle has two masses — with Composite Surfaces on, the engine answers for
the notch below a cohesion of about 160 psf and for the clipped deep mass
above it (measured in v0.1.236: 0.9684 at 150, 1.0360 at 170) — and the
slope of ``test_overall_slope_v137``, whose grid circles answer for one mass.

No assertion fixes a factor of safety.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MID = "bishop_simplified"


def _old_key(sd, tol=0.5):
    """The key of v0.1.236, written out for the contrasts of rule 7."""
    from ogr_core.statistics.probabilistic import _surface_type
    st = _surface_type(sd)
    if st is None:
        return ""
    if st in ("circle", "composite"):
        return "c:%d:%d:%d" % (round(sd["centre_x"] / tol),
                               round(sd["centre_y"] / tol),
                               round(sd["radius"] / tol))
    verts = ((sd.get("polyline") or {}).get("vertices") if st == "polyline"
             else sd.get("vertices")) or []
    if not verts:
        return ""
    return "p:" + ":".join("%d,%d" % (round(v[0] / tol), round(v[1] / tol))
                           for v in verts)


def _notched():
    import test_statistical_rebuild_v1154 as V
    return V._notched(), V


def _masses():
    """The two chords of the notched circle, from the engine's chord walk."""
    from ogr_core.geometry import ground_surface
    p, V = _notched()
    return V._circle().candidate_chords(ground_surface(p.external_boundary()))


def _named(extent):
    """The notched circle naming ONE of its masses."""
    import test_statistical_rebuild_v1154 as V
    c = V._circle()
    c.x_left, c.x_right = extent
    return c


def _circle_dict(extent=None, cls="circle"):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import CompositeSurface, SlipCircle
    import test_statistical_rebuild_v1154 as V
    c = SlipCircle(centre_x=V._XC, centre_y=V._YC, radius=V._R)
    if extent is not None:
        c.x_left, c.x_right = extent
    if cls == "circle":
        return c.to_dict()
    bedrock = Polyline(vertices=[Vertex(0.0, 15.0), Vertex(180.0, 15.0)])
    return CompositeSurface(circle=c, bedrock=bedrock, x_left=c.x_left,
                            x_right=c.x_right).to_dict()


def _round(extent):
    return tuple(round(x, 6) for x in extent)


def _extent(sd):
    return _round((sd["x_left"], sd["x_right"]))


def _polyline_dict(*xy):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in xy])).to_dict()


# ======================================================================
class TestTheKeyIsTheSurface:

    def test_the_premise_the_circle_has_two_disjoint_masses(self):
        m = _masses()
        assert len(m) == 2, m
        (_a0, a1), (b0, _b1) = m
        assert a1 < b0, m                      # disjoint, left to right

    def test_the_two_masses_get_two_keys(self):
        from ogr_core.statistics.probabilistic import _surface_key
        a, b = _masses()
        ka, kb = _surface_key(_circle_dict(a)), _surface_key(_circle_dict(b))
        assert ka and kb and ka != kb, (ka, kb)
        assert _old_key(_circle_dict(a)) == _old_key(_circle_dict(b))

    def test_a_composite_is_not_its_uncut_circle_even_on_one_extent(self):
        """The type is part of the identity, not only the extent."""
        from ogr_core.statistics.probabilistic import _surface_key
        extent = (56.0, 158.0)
        kc = _surface_key(_circle_dict(extent))
        kk = _surface_key(_circle_dict(extent, cls="composite"))
        assert kc and kk and kc != kk, (kc, kk)

    def test_two_circles_of_a_grid_closer_than_the_old_rounding(self):
        """The pair that decided the critical probabilistic surface of bank
        problem 36 (grid centre (4, 18.75), two consecutive radii): one key
        in v0.1.236, ``c:8:38:28``, for two circles with different masses
        and factors (1.3404 and 1.5541 at the mean)."""
        from ogr_core.statistics.probabilistic import _surface_key
        a = {"type": "circle", "centre_x": 4.0, "centre_y": 18.75,
             "radius": 13.775, "x_left": 5.01, "x_right": 17.26}
        b = {"type": "circle", "centre_x": 4.0, "centre_y": 18.75,
             "radius": 14.126, "x_left": 0.77, "x_right": 17.62}
        assert _old_key(a) == _old_key(b) == "c:8:38:28"
        assert _surface_key(a) != _surface_key(b)

    def test_any_digit_separates_and_nothing_else_does(self):
        """Exact, not quantised: a surface that differs anywhere is another
        surface, and the same surface keeps its key through the JSON round
        trip a saved result goes through, and whether a coordinate arrives
        as an integer or as a float."""
        from ogr_core.statistics.probabilistic import _surface_key
        a, _b = _masses()
        d = _circle_dict(a)
        nudged = _circle_dict((a[0] + 1e-9, a[1]))
        assert _surface_key(d) != _surface_key(nudged)
        assert _surface_key(json.loads(json.dumps(d))) == _surface_key(d)
        as_int = {"type": "circle", "centre_x": 4, "centre_y": 18,
                  "radius": 14, "x_left": 1, "x_right": 17}
        as_float = {k: (float(v) if k != "type" else v)
                    for k, v in as_int.items()}
        assert _surface_key(as_int) == _surface_key(as_float)

    def test_polylines_are_exact_too_and_keep_their_prefix(self):
        """v1154 pins the ``p:`` prefix of a vertex-keyed surface."""
        from ogr_core.statistics.probabilistic import _surface_key
        a = _polyline_dict((0.0, 0.0), (10.0, -4.0), (20.0, 0.0))
        b = _polyline_dict((0.0, 0.0), (10.0, -4.000001), (20.0, 0.0))
        assert _surface_key(a).startswith("p:")
        assert _old_key(a) == _old_key(b)
        assert _surface_key(a) != _surface_key(b)

    def test_a_dictionary_without_type_or_extent_is_still_a_circle(self):
        """The ``_surface_type`` fallback for a bare dictionary stays, and a
        circle with no extent has a key — just not the one of any mass."""
        from ogr_core.statistics.probabilistic import _surface_key
        bare = {"centre_x": 1.0, "centre_y": 2.0, "radius": 3.0}
        typed = dict(bare, type="circle")
        assert _surface_key(bare) == _surface_key(typed) != ""
        assert _surface_key(typed) != _surface_key(
            dict(typed, x_left=0.0, x_right=2.0))

    def test_the_tolerance_is_gone(self):
        """Rule 7: a parameter that no longer does anything is not kept."""
        import inspect

        from ogr_core.statistics.probabilistic import _surface_key
        assert list(inspect.signature(_surface_key).parameters) == ["sd"]


# ======================================================================
class TestWhichSearchesAnalyseTheSameSurfaces:
    """The reference names four searches as the ones that analyse the same
    surfaces in every sample — Grid, Slope, Path and Block; the guided ones
    steer on their own factors."""

    def test_the_four_that_do(self):
        from ogr_slip2d.search import (BlockSearch, GridSearch, PathSearch,
                                       SlopeSearch)
        for cls in (GridSearch, SlopeSearch, PathSearch, BlockSearch):
            assert cls.SAME_SURFACES_EVERY_SAMPLE is True, cls.__name__

    def test_the_ones_that_steer(self):
        from ogr_slip2d.particle_swarm import ParticleSwarmSearch
        from ogr_slip2d.search import (AutoRefineNonCircularSearch,
                                       AutoRefineSearch, BaseSearch,
                                       SimulatedAnnealingSearch)
        for cls in (BaseSearch, AutoRefineSearch, AutoRefineNonCircularSearch,
                    SimulatedAnnealingSearch, ParticleSwarmSearch):
            assert cls.SAME_SURFACES_EVERY_SAMPLE is False, cls.__name__

    def test_the_slope_search_names_its_walk_and_regenerates_the_rest(self):
        """Its population comes from the seed and the geometry; its
        refinement walk from the factors. On the v137 slope, at the two ends
        of the cohesion range: the population is the same to the last digit,
        and every walked surface is in ``evaluations`` and in ``steered``."""
        import test_overall_slope_v137 as T
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.statistics.probabilistic import _surface_key
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch

        def run(c):
            p = T._ej1_project()
            m = p.materials[0]
            m.strength = MohrCoulomb(
                cohesion=c, friction_angle=m.strength.params["friction_angle"])
            r = SlopeSearch(method=BishopSimplified(), num_surfaces=60,
                            num_slices=14, seed=7).run(p)
            walked = {id(e) for e in r.steered}
            assert r.steered and walked <= {id(e) for e in r.evaluations}
            return {_surface_key(e.surface.to_dict())
                    for e in r.evaluations if id(e) not in walked}

        weak, strong = run(3.0), run(27.0)
        assert len(weak) > 20 and weak == strong

    def test_the_premise_a_grid_regenerates_its_surfaces_bit_for_bit(self):
        """What the flag stands on, on the v137 slope: the two ends of the
        cohesion range its wide variable samples, the same circles to the
        last digit (measured: 176 of 176)."""
        import test_overall_slope_v137 as T
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.statistics.probabilistic import _surface_key

        def keys(c):
            p = T._ej1_project()
            m = p.materials[0]
            m.strength = MohrCoulomb(
                cohesion=c, friction_angle=m.strength.params["friction_angle"])
            return {_surface_key(r.surface.to_dict())
                    for r in T._search().run(p).evaluations}

        weak, strong = keys(3.0), keys(27.0)
        assert len(weak) > 100 and weak == strong


# ======================================================================
class _Circles:
    """A search that evaluates the given circles in every sample, as given:
    a circle with its extent set names that mass, one without lets the
    engine choose (the lower factor)."""

    SAME_SURFACES_EVERY_SAMPLE = True

    def __init__(self, evaluator, circles, objective="fos", optimized=None,
                 steered=()):
        self.evaluator, self.circles = evaluator, circles
        self.objective, self.optimized = objective, optimized
        self.steered = steered

    def run(self, project):
        from ogr_core.statistics.probabilistic import counts_as_sample
        evs = [self.evaluator.evaluate_circle(project, c)
               for c in self.circles]
        evs = [r for r in evs if r is not None]
        opt = None
        if self.optimized is not None:
            opt = self.evaluator.evaluate_circle(project, self.optimized)
            evs.append(opt)        # as BaseSearch does with ``optimized``
        steered = [self.evaluator.evaluate_circle(project, c)
                   for c in self.steered]
        evs += steered             # as the Slope Search does with its walk
        valid = [r for r in evs if counts_as_sample(r)]
        return types.SimpleNamespace(
            critical=min(valid, key=lambda r: r.fos) if valid else None,
            evaluations=evs, objective=self.objective, optimized=opt,
            steered=steered)


class _Steered(_Circles):
    SAME_SURFACES_EVERY_SAMPLE = False


def _overall(circles, *, cls=_Circles, key=None, n=30, **kw):
    """Overall Slope on the notched slope, cohesion of the upper soil
    uniform from 50 to 450 psf: about a quarter of the samples fall below
    the switch, so both masses answer in some sample."""
    import ogr_core.statistics.probabilistic as P
    from ogr_core.statistics import (Distribution, DistributionType,
                                     SamplingMethod, available_variables)
    from ogr_slip2d.analysis_runner import build_evaluator
    p, _V = _notched()
    mat = p.materials[0]
    var = [x for x in available_variables(p)
           if x.param == "cohesion" and x.target_id == mat.id][0]
    var.distribution = Distribution(DistributionType.UNIFORM, mean=250.0,
                                    rel_min=200.0, rel_max=200.0)
    min_evaluations = kw.pop("min_evaluations", 5)
    factory = (lambda mid: cls(build_evaluator(p, mid), circles, **kw))
    old = P._surface_key
    if key is not None:
        P._surface_key = key
    try:
        res = P.run_overall_slope(p, factory, [var], [_MID], num_samples=n,
                                  sampling=SamplingMethod.LATIN_HYPERCUBE,
                                  seed=3, min_evaluations=min_evaluations)
    finally:
        P._surface_key = old
    return res


class TestOneSurfaceOneProbability:

    def test_a_surface_reported_in_some_samples_only_is_not_a_candidate(self):
        """The free circle: the engine answers for the notch in the weak
        samples and for the deep mass in the others. Neither mass was
        analysed in every sample, so neither has a probability of failure
        of its own — and the old key pooled both into one surface whose PF
        was simply the run's."""
        from ogr_core.statistics.probabilistic import _CPS_NOT_IN_EVERY_SAMPLE
        import test_statistical_rebuild_v1154 as V
        new = _overall([V._circle()]).by_method[_MID]
        assert new.notes["surfaces_tracked"] == 2
        assert new.critical_probabilistic is None
        assert new.notes["critical_probabilistic"] == _CPS_NOT_IN_EVERY_SAMPLE
        was = _overall([V._circle()], key=_old_key).by_method[_MID]
        assert was.notes["surfaces_tracked"] == 1

    def test_two_surfaces_in_every_sample_are_two_candidates(self):
        """Both masses named, so both are analysed in every sample: each
        has one factor per sample, and the one named critical has the
        higher probability — never above the run's."""
        a, b = _masses()
        res = _overall([_named(a), _named(b)])
        o = res.by_method[_MID]
        cp = o.critical_probabilistic
        assert o.notes["surfaces_tracked"] == 2
        assert cp is not None
        assert cp.statistics.n == o.statistics.n == 30
        assert _extent(cp.surface) in (_round(a), _round(b))
        assert 0.0 < cp.probability_of_failure <= o.probability_of_failure
        assert "critical_probabilistic" not in o.notes
        # The old key cannot tell the two masses apart: one surface. (In
        # v0.1.236 it also took both factors of every sample, 60 of them.)
        was = _overall([_named(a), _named(b)], key=_old_key).by_method[_MID]
        assert was.notes["surfaces_tracked"] == 1

    def test_the_optimised_surface_does_not_enter(self):
        """The reference leaves the optimised surfaces out of the critical
        probabilistic surface, since they change from sample to sample.
        Here it would win: the notch is the weaker mass."""
        a, b = _masses()
        o = _overall([_named(b)], optimized=_named(a)).by_method[_MID]
        cp = o.critical_probabilistic
        assert o.notes["surfaces_tracked"] == 1
        assert _extent(cp.surface) == _round(b)
        assert cp.statistics.n == 30

    def test_what_a_search_steered_to_does_not_enter_either(self):
        """The Slope Search walks from its best circles, steered by their
        factors, and keeps the walk in ``evaluations``: the same thing as
        an optimisation, under another name. ``SearchResult.steered`` says
        which ones, and they stay out like the optimised surface."""
        a, b = _masses()
        o = _overall([_named(b)], steered=[_named(a)]).by_method[_MID]
        cp = o.critical_probabilistic
        assert o.notes["surfaces_tracked"] == 1
        assert _extent(cp.surface) == _round(b)
        # One factor per sample, and none of them the walk's: v0.1.236 had
        # 60 here, the deep mass and the walked notch under one key.
        assert cp.statistics.n == 30

    def test_a_search_that_steers_has_none_and_says_why(self):
        from ogr_core.statistics.probabilistic import _CPS_STEERED
        a, b = _masses()
        o = _overall([_named(a), _named(b)], cls=_Steered).by_method[_MID]
        assert o.critical_probabilistic is None
        assert o.notes["critical_probabilistic"] == _CPS_STEERED
        assert o.notes["surfaces_tracked"] == 0
        # The run itself is untouched: its statistics do not depend on it.
        same = _overall([_named(a), _named(b)]).by_method[_MID]
        assert o.statistics.values == same.statistics.values
        assert o.summary()["critical_probabilistic_note"] == _CPS_STEERED

    def test_the_ky_objective_has_none_and_says_why(self):
        from ogr_core.statistics.probabilistic import _CPS_KY
        a, b = _masses()
        o = _overall([_named(a), _named(b)], objective="ky").by_method[_MID]
        assert o.critical_probabilistic is None
        assert o.notes["critical_probabilistic"] == _CPS_KY

    def test_too_few_samples_says_so(self):
        from ogr_core.statistics.probabilistic import _CPS_TOO_FEW
        a, b = _masses()
        o = _overall([_named(a), _named(b)], n=6,
                     min_evaluations=1000).by_method[_MID]
        assert o.critical_probabilistic is None
        assert o.notes["critical_probabilistic"] == _CPS_TOO_FEW


# ======================================================================
class TestOnARealGrid:
    """The v137 slope and its own search: nothing to separate there, so
    the run reads as before, and the candidate set is the full one."""

    def test_the_critical_probabilistic_surface_has_every_sample(self):
        import test_overall_slope_v137 as T
        _p, res = T._run(n=16, wide=True)
        o = res.by_method[_MID]
        cp = o.critical_probabilistic
        assert cp is not None
        assert cp.statistics.n == o.statistics.n
        assert cp.probability_of_failure <= o.probability_of_failure
        assert "critical_probabilistic" not in o.notes

    def test_the_minima_count_the_same_with_either_key(self):
        """Its circles answer for one mass and its radii are more than half
        a unit apart, so exact identity finds the same distinct minima as
        the old rounding in the three configurations of v137."""
        import ogr_core.statistics.probabilistic as P
        import test_overall_slope_v137 as T
        for n, wide in ((20, True), (10, False), (16, True)):
            _p, new = T._run(n=n, wide=wide)
            old = P._surface_key
            P._surface_key = _old_key
            try:
                _p, was = T._run(n=n, wide=wide)
            finally:
                P._surface_key = old
            assert (new.by_method[_MID].distinct_minima
                    == was.by_method[_MID].distinct_minima), (n, wide)
            assert (new.by_method[_MID].statistics.values
                    == was.by_method[_MID].statistics.values), (n, wide)


# ======================================================================
def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return False
    QApplication.instance() or QApplication([])
    return True


class _Language:
    """Switch the language for one block and put it back (rule 5)."""

    def __init__(self, lang):
        self.lang = lang

    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self.before = current_language()
        set_language(self.lang)

    def __exit__(self, *exc):
        from ogr_gui.i18n import set_language
        set_language(self.before)


class TestTheInterfaceSaysWhichSurface:

    def test_a_row_names_the_mass_and_the_type(self):
        if not _qt():
            return
        from ogr_gui.interpret_window import minimum_row_text
        a, b = _masses()
        with _Language("en"):
            ra = minimum_row_text(1, _circle_dict(a))
            rb = minimum_row_text(1, _circle_dict(b))
            rk = minimum_row_text(1, _circle_dict(b, cls="composite"))
            bare = minimum_row_text(2, _circle_dict())
            poly = minimum_row_text(3, _polyline_dict((1.0, 5.0), (4.0, 2.0),
                                                      (9.0, 6.0)))
        assert ra != rb and "x from 45.84 to 49.70" in ra, (ra, rb)
        assert rk.startswith("1: composite surface") and rk != rb, rk
        assert bare == "2: circle centre (120.00, 90.00) r = 80.00", bare
        assert poly == "3: non-circular surface, x from 1.00 to 9.00", poly

    def test_every_engine_reason_has_its_spanish(self):
        """Interpret looks the engine's sentence up BY VALUE, so a reworded
        sentence would silently stay in English."""
        from ogr_core.statistics import probabilistic as P
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for name in ("_CPS_STEERED", "_CPS_KY", "_CPS_TOO_FEW",
                     "_CPS_NOT_IN_EVERY_SAMPLE"):
            assert getattr(P, name) in es, name

    def test_the_toggle_gives_the_reason_of_the_run(self):
        if not _qt():
            return
        from ogr_core.statistics.probabilistic import _CPS_STEERED
        from ogr_gui.i18n import _DICTS
        import test_interpret_i3_v153 as I
        a, b = _masses()
        prob = _overall([_named(a), _named(b)], cls=_Steered, n=8)
        _p, _r, w = I._interpret()
        w._stat_results = lambda: (prob, None)
        said = []
        w._info = said.append
        with _Language("es"):
            w._toggle_critical_prob(True)
        assert said == [_DICTS["es"][_CPS_STEERED]], said
