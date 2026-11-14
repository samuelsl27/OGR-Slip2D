# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D417 (v0.1.454) — the critical probabilistic surface of an Overall Slope run
is chosen among every surface analysed in every sample, the user's included.

The invariant
-------------
An Overall Slope run repeats the whole search per sample. The factor of a
sample is its critical surface's (``run.critical``), which includes the
surfaces the user defined: the search evaluates them after its population.
But the per-surface bookkeeping (``_accumulate_surfaces``) read only
``run.evaluations``, so a surface of the user never accumulated a factor,
never was a candidate for the critical probabilistic surface, and was never
counted as a sample's global minimum. Measured with v0.1.453 on the demo
slope (Path Search of 5, Janbu, the polyline ``_WINNER`` of
``test_user_polylines_v1427``, a normal cohesion with a deviation of 20 % of
its mean, 40 Latin Hypercube samples): the polyline was the global minimum of
all 40 samples and the run's PF 2.5 %, while the critical probabilistic
surface published was one of the search, with PF 0 and 0 times the global
minimum — on the unsafe side, without a note. By the owner's decision (option
a) the user's surfaces accumulate like the search's, through
``all_evaluations_of``; what the search steered to (``steered``, the
optimised surfaces) stays out, as the reference leaves its optimised surfaces
out.

The reference (rule 1)
----------------------
Identities of the definition. The reference's local help ("Critical
Probabilistic Surface", Interpret) names it the surface of lowest
reliability index of all the slip surfaces analysed that exist in every
sample; OGR takes the highest probability of failure, ties broken by the
lower index. A surface the user defined is analysed in every sample with the
same geometry, so:

* the PF of the critical probabilistic surface is the fraction of samples in
  which the polyline's factor is below 1, recounted here by evaluating the
  polyline again on each sample (``evaluate_surfaces``, the door of
  ``surface_evaluate``), not read off the run;
* ``times_global_minimum`` is the number of samples whose critical surface
  is the polyline: the samples where the polyline's factor IS the sample's
  factor, the minimum over all the surfaces.

The premise, measured and asserted: with a deviation of 30 % and a range of
±60 % over 30 samples the polyline is the global minimum of every sample
and fails in 3 of them (PF 0.1), so the identity does not rest on one.

Without user surfaces the result is the one of the v0.1.453 function,
substituted in the same process, bit for bit.

Two more, from the review of 0.1.454:

* a second polyline of the user that never governs is counted in every
  sample all the same (a mutant that counted a surface of the user only
  where it governs survived the first test, whose polyline governs every
  sample);
* with Random Numbers set to "random", a search that draws its surfaces
  with no seed (Slope, Block, Path) draws other ones in every sample, so it
  names no critical probabilistic surface, with the user's or without: the
  review measured the user's polyline published as the only candidate,
  with PF 0 and never a global minimum (the owner's decision). The grid,
  which draws nothing, keeps the user's circle.

The recount is bit for bit the run's factor: the same arithmetic on the
same sampled model, through another door.

Measured cost: 5.2 s for the file in the runner, imports included: three
runs of 30 samples and 30 evaluations, computed once for the module, and
four runs of 6 samples. Over the 5 s of the rule because each run is a
statistical analysis through its door, deterministic search included, and
every case is an identity of the reference's definition (rule 1).
"""
from __future__ import annotations

import contextlib
import types

_WINNER = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
_METHOD = "janbu_simplified"
_SAMPLES = 30
_SHARED: dict = {}


def _project(with_polyline=True):
    from ogr_core.project.demo import build_demo_project
    from ogr_core.project.settings import SurfaceType
    from ogr_core.statistics import SamplingMethod, available_variables
    from ogr_core.statistics.distributions import (Distribution,
                                                   DistributionType as T)
    from ogr_slip2d.surface import UserPolylineSurface
    p = build_demo_project()
    s = p.settings.search
    s.surface_type = SurfaceType.NON_CIRCULAR.value
    s.search_method = "path"
    s.path_num_surfaces = 5
    s.optimize_enabled = False
    p.settings.methods.enabled_methods = [_METHOD]
    if with_polyline:
        p.user_polylines = [UserPolylineSurface.from_points(_WINNER)]
    rv = next(v for v in available_variables(p)
              if v.key.endswith(":cohesion"))
    m = rv.distribution.mean
    rv.distribution = Distribution(T.NORMAL, m, 0.3 * m, 0.6 * m, 0.6 * m)
    p.random_variables = [rv]
    st = p.settings.statistics
    st.probabilistic_analysis = True
    st.sensitivity_analysis = False
    st.analysis_type = "overall_slope"
    st.num_samples = _SAMPLES
    st.sampling_method = SamplingMethod.LATIN_HYPERCUBE.value
    return p


def _old_accumulate(run, per_surface):
    """``_accumulate_surfaces`` of v0.1.453, written out for the control:
    ``run.evaluations`` alone."""
    from ogr_slip2d.probabilistic import (SurfaceProbability, _surface_key,
                                          counts_as_sample)
    left_out = {id(r) for r in (getattr(run, "steered", None) or ())}
    optimized = getattr(run, "optimized", None)
    if optimized is not None:
        left_out.add(id(optimized))
    seen: set = set()
    for ev in run.evaluations:
        if id(ev) in left_out or not counts_as_sample(ev):
            continue
        sd = ev.surface.to_dict() if hasattr(ev.surface, "to_dict") else None
        key = _surface_key(sd)
        if not key or key in seen:
            continue
        seen.add(key)
        sp = per_surface.get(key)
        if sp is None:
            sp = SurfaceProbability(surface=sd)
            per_surface[key] = sp
        sp.statistics.values.append(ev.fos)


@contextlib.contextmanager
def _old_rule():
    import ogr_slip2d.probabilistic as P
    saved = P._accumulate_surfaces
    P._accumulate_surfaces = _old_accumulate
    try:
        yield
    finally:
        P._accumulate_surfaces = saved


def _run(with_polyline=True, old=False):
    key = (with_polyline, old)
    if key not in _SHARED:
        from ogr_slip2d.analysis_runner import run_configured_statistics
        p = _project(with_polyline)
        if old:
            with _old_rule():
                out = run_configured_statistics(p)
        else:
            out = run_configured_statistics(p)
        _SHARED[key] = (p, out.probabilistic)
    return _SHARED[key]


def _recount():
    """The polyline's factor in each counted sample, evaluated again
    through ``evaluate_surfaces`` on the sampled model."""
    if "recount" not in _SHARED:
        from ogr_api.ops.analysis import surface_from_spec
        from ogr_core.statistics.random_variables import (apply_sample,
                                                          clone_project)
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p, res = _run()
        ores = res.by_method[_METHOD]
        active = [rv for rv in p.random_variables
                  if rv.key in res.variables]
        surface = surface_from_spec({"type": "polyline",
                                     "points": [list(xy) for xy in _WINNER]})
        fos = []
        for i in ores.sample_index:
            clone = clone_project(p)
            apply_sample(clone, active,
                         {k: v[i] for k, v in res.samples.items()})
            out = evaluate_surfaces(clone, surface, [_METHOD])
            fos.append(out.results[_METHOD].fos)
        _SHARED["recount"] = fos
    return _SHARED["recount"]


def _polyline_key():
    from ogr_slip2d.probabilistic import _surface_key
    p, res = _run()
    crit_sd = res.by_method[_METHOD].global_minima[0]
    return _surface_key(crit_sd)


# ======================================================================
class TestThePremise:

    def test_the_polyline_governs_every_sample_and_fails_in_some(self):
        _p, res = _run()
        ores = res.by_method[_METHOD]
        fos = _recount()
        assert len(ores.statistics.values) == _SAMPLES
        assert len(ores.global_minima) == 1, ores.global_minima
        # the same factor, bit for bit: the same arithmetic on the same
        # sampled model, through another door
        assert [a.hex() for a in fos] == [
            b.hex() for b in ores.statistics.values]
        failed = sum(1 for f in fos if f < 1.0)
        assert failed == 3, failed


class TestTheUsersSurfaceIsACandidate:

    def test_the_critical_probabilistic_surface_is_the_polyline(self):
        from ogr_slip2d.probabilistic import _surface_key
        _p, res = _run()
        cps = res.by_method[_METHOD].critical_probabilistic
        assert cps is not None
        assert _surface_key(cps.surface) == _polyline_key()

    def test_its_pf_is_the_recounted_fraction(self):
        _p, res = _run()
        cps = res.by_method[_METHOD].critical_probabilistic
        fos = _recount()
        assert cps.statistics.n == len(fos)
        assert cps.probability_of_failure == \
            sum(1 for f in fos if f < 1.0) / len(fos)
        assert [a.hex() for a in cps.statistics.values] == [
            b.hex() for b in fos]

    def test_times_global_minimum_is_the_recount(self):
        _p, res = _run()
        ores = res.by_method[_METHOD]
        fos = _recount()
        governs = sum(1 for f, g in zip(fos, ores.statistics.values)
                      if f == g)
        assert ores.critical_probabilistic.times_global_minimum == governs
        assert governs == _SAMPLES

    def test_the_v0453_rule_left_it_out(self):
        """The defect, in the same process: with the old bookkeeping the
        published surface is one of the search, with PF 0."""
        from ogr_slip2d.probabilistic import _surface_key
        _p, res = _run(old=True)
        ores = res.by_method[_METHOD]
        cps = ores.critical_probabilistic
        assert _surface_key(cps.surface) != _polyline_key()
        assert cps.probability_of_failure < ores.probability_of_failure
        assert cps.times_global_minimum == 0


class TestWithoutUserSurfacesNothingMoves:

    def test_bit_for_bit_against_the_v0453_function(self):
        from ogr_slip2d.probabilistic import _surface_key
        _p, new = _run(with_polyline=False)
        _p, old = _run(with_polyline=False, old=True)
        # keyed by the variable, whose key carries the material's id, new in
        # every demo project: the values, in order
        assert [[v.hex() for v in vs] for vs in new.samples.values()] == [
            [v.hex() for v in vs] for vs in old.samples.values()]
        a, b = new.by_method[_METHOD], old.by_method[_METHOD]
        assert [v.hex() for v in a.statistics.values] == [
            v.hex() for v in b.statistics.values]
        ca, cb = a.critical_probabilistic, b.critical_probabilistic
        assert _surface_key(ca.surface) == _surface_key(cb.surface)
        assert ca.probability_of_failure == cb.probability_of_failure
        assert ca.reliability_index == cb.reliability_index
        assert ca.times_global_minimum == cb.times_global_minimum
        assert [str(v) for v in a.notes.values()] == [
            str(v) for v in b.notes.values()]
        assert a.notes["surfaces_tracked"] == b.notes["surfaces_tracked"]


def _small(project, samples=6):
    """``project`` run with fewer samples, one more than the five a critical
    probabilistic surface needs (``min_evaluations``): the Overall Slope
    result of the method."""
    from ogr_slip2d.analysis_runner import run_configured_statistics
    project.settings.statistics.num_samples = samples
    out = run_configured_statistics(project)
    return out.probabilistic.by_method[project.settings.methods
                                       .enabled_methods[0]]


class TestAUserSurfaceThatDoesNotGovern:

    def test_it_is_counted_in_every_sample_all_the_same(self):
        """A second polyline, deeper and stronger, never the global minimum:
        it still has a factor in every sample (the review of 0.1.454: a
        mutant counting a surface of the user only where it governs
        survived the first test, whose polyline governs all of them)."""
        from ogr_slip2d.probabilistic import _surface_key
        from ogr_slip2d.surface import UserPolylineSurface
        p = _project()
        p.user_polylines.append(UserPolylineSurface.from_points(
            [(5.0, 25.0), (20.0, 10.0), (40.0, 8.0), (48.0, 15.0)]))
        ores = _small(p)
        # the five of the search and the two of the user
        assert ores.notes["surfaces_tracked"] == 7, ores.notes
        assert len(ores.global_minima) == 1
        assert _surface_key(ores.critical_probabilistic.surface) == \
            _surface_key(ores.global_minima[0])


class TestTheClockSeed:
    """Random Numbers set to "random": a search that draws its surfaces with
    no seed draws other ones in every sample, so it names no critical
    probabilistic surface, with the user's or without (the owner's
    decision in the review of 0.1.454: the user's polyline was the only
    candidate and was published with PF 0). The grid, which draws nothing,
    keeps it."""

    def test_a_search_that_draws_names_none(self):
        from ogr_slip2d import stat_messages as SM
        for with_polyline in (True, False):
            p = _project(with_polyline)
            p.settings.random_numbers.method = "random"
            ores = _small(p)
            assert ores.critical_probabilistic is None, with_polyline
            assert ores.notes["critical_probabilistic"].code == \
                SM.CPS_NOT_IN_EVERY_SAMPLE, ores.notes

    @staticmethod
    def _circular(method):
        """The demo slope with the user's circle of the review, a circular
        search ``method`` and Random Numbers set to "random"."""
        from ogr_slip2d.surface import SlipCircle
        p = _project(with_polyline=False)
        p.settings.random_numbers.method = "random"
        s = p.settings.search
        s.surface_type, s.search_method = "circular", method
        s.grid_nx = s.grid_ny = 3
        s.radius_increment = 3
        # the Slope Search's count (5000 by default); the grid ignores it
        assert hasattr(s, "num_surfaces")
        s.num_surfaces = 20
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        p.user_surfaces = [SlipCircle(centre_x=39.0, centre_y=32.0,
                                      radius=17.4)]
        return p

    def test_the_grid_keeps_the_users_circle(self):
        from ogr_slip2d.probabilistic import _surface_key
        ores = _small(self._circular("grid"))
        cps = ores.critical_probabilistic
        assert cps is not None, ores.notes
        assert _surface_key(cps.surface).startswith("circle:39.0:32.0:17.4"), \
            _surface_key(cps.surface)

    def test_which_searches_draw_from_the_clock(self):
        """Asked of the searches the analysis builds, with no run: Slope,
        Block and Path draw from the clock with "random" and not with
        "pseudo_random"; the grid never. The Slope Search keeps its seed
        only since this version (``SlopeSearch.seed``), and without it the
        user's circle would be the only candidate there (a run of it takes
        19 s: its refinement walk)."""
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.probabilistic import _draws_from_the_clock
        seen = {}
        for method in ("pseudo_random", "random"):
            for stype, search in (("circular", "grid"), ("circular", "slope"),
                                  ("non_circular", "block"),
                                  ("non_circular", "path")):
                p = _project(with_polyline=False)
                p.settings.random_numbers.method = method
                p.settings.search.surface_type = stype
                p.settings.search.search_method = search
                seen[(method, search)] = _draws_from_the_clock(
                    build_search(p, _METHOD))
        assert seen == {
            ("pseudo_random", "grid"): False, ("pseudo_random", "slope"): False,
            ("pseudo_random", "block"): False, ("pseudo_random", "path"): False,
            ("random", "grid"): False, ("random", "slope"): True,
            ("random", "block"): True, ("random", "path"): True}, seen


class TestTheRule:
    """``_accumulate_surfaces`` on a run built by hand: the user's surfaces
    accumulate, the steered and the optimised ones do not, and a surface of
    the user that is also one of the search is counted once."""

    @staticmethod
    def _ev(points, fos):
        """An evaluation whose surface serialises as the evaluated
        polylines of a run do (``{"type": "polyline", ...}``)."""
        sd = {"type": "polyline",
              "polyline": {"vertices": [list(p) for p in points]}}
        surface = types.SimpleNamespace(to_dict=lambda: dict(sd))
        return types.SimpleNamespace(surface=surface, fos=fos, is_valid=True,
                                     admissible=True)

    def _run(self, **kw):
        from ogr_slip2d.probabilistic import _accumulate_surfaces
        run = types.SimpleNamespace(**kw)
        per_surface: dict = {}
        _accumulate_surfaces(run, per_surface)
        return {round(sp.statistics.values[0], 6) for sp in
                per_surface.values()}, per_surface

    def test_the_users_accumulate_and_the_steered_do_not(self):
        a = self._ev([(19.0, 25.0), (37.0, 15.0)], 1.1)
        b = self._ev([(18.0, 25.0), (38.0, 15.0)], 1.2)
        opt = self._ev([(17.0, 25.0), (39.0, 15.0)], 1.3)
        # the user's is not the lowest: it accumulates all the same
        user = self._ev([(19.0, 25.0), (31.0, 14.5), (37.0, 15.0)], 1.5)
        seen, _ = self._run(evaluations=[a, b, opt], user_evaluations=[user],
                            steered=[b], optimized=opt, critical=a)
        assert seen == {1.1, 1.5}, seen

    def test_a_users_surface_of_the_search_counts_once(self):
        a = self._ev([(19.0, 25.0), (37.0, 15.0)], 1.1)
        same = self._ev([(19.0, 25.0), (37.0, 15.0)], 1.1)
        seen, per_surface = self._run(evaluations=[a],
                                      user_evaluations=[same])
        assert len(per_surface) == 1, per_surface
        assert [sp.statistics.n for sp in per_surface.values()] == [1]
