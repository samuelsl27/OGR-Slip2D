# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.385 (V7 of the compute audit, and D380) — the doors that evaluate a
surface outside a search freeze the project's region caches as a search does,
and answer as before; and a copy no longer inherits the freeze of the project
it was taken from.

V7. A Global Minimum sample, a sensitivity point, the probe of D88, a walk of
Optimize and a fixed surface (``evaluate_surfaces``) were evaluated outside
any search, and each evaluation rebuilt the region signature about a hundred
times (K19: 129 162 calls, 41 % of its samples). ``search.frozen_evaluation``
freezes them as ``BaseSearch.run`` does.
- **The oracle:** the same evaluation with the freeze made neutral
  (``Project.regions_frozen`` replaced by a block that freezes nothing, and
  put back in ``finally``). The freeze is a cache, so every float, note and
  count must match.
- **The helper's rules, pinned:** nothing when already frozen; the weak-band
  cache of the search emptied on both sides; the body never caught; and,
  when entering raises, the evaluation runs unfrozen (Optimize keeps refusing
  its start) except in ``evaluate_surfaces``, which keeps raising.

D380. ``detached_copy``, and ``clone_project`` through it, copied the freeze
depth. A copy made while its project was frozen trusted its caches for good,
the bond profiles of a tieback among them, and a water table moved 5 m gave
F = 1.9559 where the unfrozen evaluation gives 1.9019. The drawdown level
copies, shallow and made inside the freeze on purpose, shared the source's
bond profiles: filled by an agent's read while the window computed, they
gave the lowered level the profile of the full reservoir (B-bar 0.8197 for
0.6287). The oracle is the unfrozen evaluation of the same model.

Every test is well under a second.
"""
import contextlib
import dataclasses

from ogr_core.project import Project

MID = "bishop_simplified"


def _anchored():
    """A clay slope under a water table with a friction tieback, whose bond
    profile reads the water: what a stale bond cache gets wrong."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.support import GroutedTiebackFriction, SupportInstance
    p = Project(name="frozen evaluation")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                             Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay", strength=MohrCoulomb(cohesion=8.0,
                                                   friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=PorePressureType.WATER_TABLE)
    p.add_material(m)
    wt = Boundary(polyline=Polyline(vertices=[Vertex(0, 14), Vertex(50, 9)]),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    st = GroutedTiebackFriction(adhesion=10.0, friction_angle_bond=30.0,
                                bond_length_percent=60.0, grout_diameter=0.15,
                                out_of_plane_spacing=1.5,
                                tensile_capacity=1.0e3, plate_capacity=1.0e3)
    p.support_types.append(st)
    p.supports.append(SupportInstance(type_id=st.TYPE_ID,
                                      head=Vertex(30.0, 20.0),
                                      tail=Vertex(14.0, 14.0)))
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=30.0, centre_y=35.0, radius=21.0)


def _evaluator(p):
    from ogr_slip2d.analysis_runner import build_evaluator
    return build_evaluator(p, MID, num_slices=25)


def _variables(p):
    """The clay's cohesion and the water table's offset, both normal."""
    from ogr_core.statistics import (Distribution, DistributionType,
                                     available_variables)
    from ogr_core.statistics.random_variables import (RandomVariable,
                                                      VariableKind)
    coh = [v for v in available_variables(p)
           if v.param == "cohesion" and v.target_id == p.materials[0].id][0]
    coh.distribution = Distribution(DistributionType.NORMAL, mean=8.0,
                                    std_dev=2.0, rel_min=5.0, rel_max=5.0)
    water = RandomVariable(kind=VariableKind.WATER_TABLE, target_id="",
                           param="offset",
                           distribution=Distribution(
                               DistributionType.NORMAL, mean=0.0, std_dev=3.0,
                               rel_min=6.0, rel_max=6.0))
    return [coh, water]


@contextlib.contextmanager
def _neutral_freeze():
    """``Project.regions_frozen`` that freezes nothing: the oracle."""
    real = Project.__dict__["regions_frozen"]

    @contextlib.contextmanager
    def neutral(self):
        yield self

    Project.regions_frozen = neutral
    try:
        yield
    finally:
        Project.regions_frozen = real


def _repr(obj):
    """A dataclass result as text: floats by ``repr`` (exact, -0.0 apart)."""
    return repr(dataclasses.asdict(obj)) if dataclasses.is_dataclass(obj) \
        else repr(obj)


class TestTheHelper:

    def _search_and_project(self):
        p = _anchored()
        return _evaluator(p), p

    def test_it_freezes_for_the_block_and_empties_the_weak_bands(self):
        from ogr_slip2d.search import frozen_evaluation
        search, p = self._search_and_project()
        search._weak_bands_cache = ["stale"]
        with frozen_evaluation(search, p):
            assert p._regions_freeze_depth == 1
            assert search._weak_bands_cache is None
            search._weak_bands_cache = ["built inside"]
        assert p._regions_freeze_depth == 0
        assert search._weak_bands_cache is None

    def test_already_frozen_it_does_nothing(self):
        from ogr_slip2d.search import frozen_evaluation
        search, p = self._search_and_project()
        with p.regions_frozen():
            search._weak_bands_cache = ["of this run"]
            with frozen_evaluation(search, p):
                assert p._regions_freeze_depth == 1
                assert search._weak_bands_cache == ["of this run"]
            assert search._weak_bands_cache == ["of this run"]
        assert p._regions_freeze_depth == 0

    def test_the_body_is_never_caught(self):
        from ogr_slip2d.search import frozen_evaluation

        class Stop(BaseException):
            """As the window's cancellation, not an Exception."""

        search, p = self._search_and_project()
        for kind in (ValueError, Stop):
            try:
                with frozen_evaluation(search, p):
                    search._weak_bands_cache = ["built inside"]
                    raise kind("from the evaluation")
            except kind as e:
                assert str(e) == "from the evaluation"
                assert e.__context__ is None
            else:
                raise AssertionError("swallowed")
            assert p._regions_freeze_depth == 0
            assert search._weak_bands_cache is None

    def test_when_freezing_raises(self):
        # An assignment with no click point: resolving the regions raises,
        # which used to happen inside the evaluation.
        from ogr_slip2d.search import frozen_evaluation
        search, p = self._search_and_project()
        p.region_assignments = [{"material_id": p.materials[0].id}]
        with frozen_evaluation(search, p):
            assert p._regions_freeze_depth == 0      # unfrozen, as before
        try:
            with frozen_evaluation(search, p, fallback=False):
                raise AssertionError("not reached")
        except KeyError:
            pass
        assert p._regions_freeze_depth == 0


class TestTheDoorsAnswerAsUnfrozen:
    """Each door, frozen, against the same call with a neutral freeze. The
    statistical runs share one model and one deterministic result, which
    neither changes: built twice, they would carry two material ids (the
    variables are keyed by them) and two surface ids (the result publishes
    the deterministic surface's)."""

    @staticmethod
    def _both(action):
        frozen = action()
        with _neutral_freeze():
            neutral = action()
        return frozen, neutral

    def test_global_minimum(self):
        from ogr_core.statistics import SamplingMethod
        from ogr_slip2d.probabilistic import run_global_minimum
        p = _anchored()
        variables = _variables(p)
        det = _evaluator(p).evaluate_circle(p, _circle())

        def run():
            return run_global_minimum(p, {MID: det}, variables,
                                      num_samples=8,
                                      sampling=SamplingMethod.MONTE_CARLO,
                                      seed=11, num_slices=25)

        frozen, neutral = self._both(run)
        assert frozen.by_method[MID].sample_index
        assert _repr(frozen) == _repr(neutral)

    def test_sensitivity(self):
        from ogr_slip2d.sensitivity import run_sensitivity
        p = _anchored()
        variables = _variables(p)
        det = _evaluator(p).evaluate_circle(p, _circle())

        def run():
            return run_sensitivity(p, {MID: det}, variables, intervals=4,
                                   num_slices=25)

        frozen, neutral = self._both(run)
        assert frozen.by_method[MID]
        assert _repr(frozen) == _repr(neutral)

    def test_a_walk_of_optimize(self):
        from test_optimize_start_v1187 import (_good_start, _search, _slope,
                                               _walk)

        def run():
            p = _slope()
            best, res, rep = _walk(p, _search(p), _good_start(),
                                   max_iterations=60)
            return (repr([(v.x, v.y) for v in best.polyline.vertices]),
                    repr(res.fos), _repr(rep))

        frozen, neutral = self._both(run)
        assert frozen == neutral

    def test_a_fixed_surface(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces

        def run():
            out = evaluate_surfaces(_anchored(), _circle(), [MID])
            r = out.results[MID]
            return (repr(r.fos), r.iterations, repr(r.base_normal_force),
                    repr(sorted((k, repr(v)) for k, v in r.details.items())),
                    out.warnings)

        frozen, neutral = self._both(run)
        assert frozen == neutral


class TestWhatTheFreezeSaves:
    """Counted, not timed: the region signature per sample, and per walk."""

    @staticmethod
    def _counting(action):
        calls = [0]
        real = Project.__dict__["_regions_cache_key"]

        def counted(self):
            calls[0] += 1
            return real(self)

        Project._regions_cache_key = counted
        try:
            action()
            frozen = calls[0]
            calls[0] = 0
            with _neutral_freeze():
                action()
            return frozen, calls[0]
        finally:
            Project._regions_cache_key = real

    def test_a_walk_of_optimize_rebuilds_it_on_entering_only(self):
        from test_optimize_start_v1187 import (_good_start, _search, _slope,
                                               _walk)
        p = _slope()
        frozen, unfrozen = self._counting(
            lambda: _walk(p, _search(p), _good_start(), max_iterations=40))
        assert frozen <= 3, frozen
        assert unfrozen >= 20 * max(frozen, 1), (frozen, unfrozen)

    def test_two_signatures_a_sample_on_a_polyline(self):
        # The other branch of _evaluate_on: a non-circular deterministic
        # surface, as Path, Block or Auto Refine leave.
        from test_optimize_start_v1187 import _good_start, _slope, _surface
        from ogr_core.statistics import (Distribution, DistributionType,
                                         SamplingMethod, available_variables)
        from ogr_slip2d.probabilistic import run_global_minimum
        n, p = 6, _slope()
        coh = [v for v in available_variables(p) if v.param == "cohesion"][0]
        coh.distribution = Distribution(DistributionType.NORMAL, mean=8.0,
                                        std_dev=2.0, rel_min=5.0, rel_max=5.0)
        det = _evaluator(p).evaluate_surface(p, _surface(_good_start()))
        assert det is not None and det.fos is not None
        frozen, unfrozen = self._counting(lambda: run_global_minimum(
            p, {MID: det}, [coh], num_samples=n,
            sampling=SamplingMethod.MONTE_CARLO, seed=3, num_slices=25))
        assert frozen <= 2 * (n + 1) + 2, frozen
        assert unfrozen >= 10 * frozen, (frozen, unfrozen)

    def test_two_signatures_a_sample(self):
        from ogr_core.statistics import SamplingMethod
        from ogr_slip2d.probabilistic import run_global_minimum
        calls = [0]
        real = Project.__dict__["_regions_cache_key"]

        def counted(self):
            calls[0] += 1
            return real(self)

        n = 6
        p = _anchored()
        det = _evaluator(p).evaluate_circle(p, _circle())
        Project._regions_cache_key = counted
        try:
            run_global_minimum(p, {MID: det}, _variables(p), num_samples=n,
                               sampling=SamplingMethod.MONTE_CARLO, seed=3,
                               num_slices=25)
            frozen = calls[0]
            calls[0] = 0
            with _neutral_freeze():
                run_global_minimum(p, {MID: det}, _variables(p),
                                   num_samples=n,
                                   sampling=SamplingMethod.MONTE_CARLO,
                                   seed=3, num_slices=25)
            unfrozen = calls[0]
        finally:
            Project._regions_cache_key = real
        # the samples and the probe: two each on entering, none inside
        assert frozen <= 2 * (n + 1) + 2, frozen
        assert unfrozen >= 10 * frozen, (frozen, unfrozen)


class TestAFixedSurfaceStillRaises:
    """``evaluate_surfaces`` entered the freeze itself and let a model that
    cannot be frozen raise out of it; it keeps doing so, without the
    fallback the other doors take (where it would answer None instead)."""

    def test_an_assignment_with_no_click_point(self):
        # A circle far from the model: one that cuts it raises the same
        # KeyError from the slicer anyway; this one, unfrozen, would be
        # turned down for missing the ground and answer None.
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipCircle
        p = _anchored()
        p.region_assignments = [{"material_id": p.materials[0].id}]
        far = SlipCircle(centre_x=500.0, centre_y=500.0, radius=10.0)
        try:
            evaluate_surfaces(p, far, [MID])
        except KeyError:
            pass
        else:
            raise AssertionError("the freeze's error was swallowed")
        assert p._regions_freeze_depth == 0


class TestOptimizeStillRefusesItsStart:
    """Where freezing raises, Optimize walks unfrozen, and its start is
    refused as before (OPT_START_REFUSED), not raised to the menu."""

    def test_an_assignment_with_no_click_point(self):
        from test_optimize_start_v1187 import (_good_start, _search, _slope,
                                               _walk)
        from ogr_slip2d import search_note_messages as SN
        p = _slope()
        p.region_assignments = [{"material_id": p.materials[0].id}]
        _best, res, rep = _walk(p, _search(p), _good_start(),
                                max_iterations=5)
        assert res is None
        assert rep.notes["error"] == SN.search_note(SN.OPT_START_REFUSED)
        assert p._regions_freeze_depth == 0


class TestOptimizeEmptiesTheCacheBeforeItsCopy:
    """With the surface checks off, Optimize scores against a SHALLOW copy
    of the search, which takes the weak-band cache as it finds it. Frozen,
    that copy would trust bands another run left there; the freeze is
    entered before the copy is made, and empties them first."""

    def test_bands_left_by_another_model_do_not_reach_the_walk(self):
        from test_optimize_start_v1187 import (_good_start, _search, _slope,
                                               _walk)
        from test_weak_layer_statistics_v1251 import _two_joints
        from ogr_slip2d.weak_layers import weak_layer_bands
        stale = weak_layer_bands(_two_joints("highest"))
        assert stale

        def run(left):
            p = _slope()
            search = _search(p)
            search._weak_bands_cache = left
            best, res, rep = _walk(p, search, _good_start(),
                                   max_iterations=40,
                                   use_surface_checks=False)
            return (repr([(v.x, v.y) for v in best.polyline.vertices]),
                    repr(res.fos), _repr(rep))

        assert run(stale) == run(None)


class TestACopyDoesNotInheritTheFreeze:
    """D380."""

    def test_copies_made_while_frozen_are_not_frozen(self):
        from ogr_core.project.copies import detached_copy
        from ogr_core.statistics.random_variables import clone_project
        p = _anchored()
        with p.regions_frozen():
            copies = (detached_copy(p), detached_copy(p, cold_caches=False),
                      clone_project(p))
        assert [c._regions_freeze_depth for c in copies] == [0, 0, 0]

    def test_a_sample_copied_while_frozen_reads_its_own_water(self):
        from ogr_core.statistics.random_variables import (RandomVariable,
                                                          VariableKind,
                                                          apply_sample,
                                                          clone_project)
        water = RandomVariable(kind=VariableKind.WATER_TABLE, target_id="",
                               param="offset")
        parent = _anchored()
        search = _evaluator(parent)
        for offset in (5.0,):
            alone = clone_project(parent)
            apply_sample(alone, [water], {water.key: offset})
            want = search.evaluate_circle(alone, _circle()).fos
            with parent.regions_frozen():
                search.evaluate_circle(parent, _circle())   # bond cache built
                born = clone_project(parent)
            apply_sample(born, [water], {water.key: offset})
            got = search.evaluate_circle(born, _circle()).fos
            assert repr(got) == repr(want), offset

    def test_a_drawdown_level_reads_its_own_water(self):
        # The window's analysis freezes the live model; an agent's read
        # fills its bond profiles meanwhile (here, by hand); the lowered
        # level must still build its own. B-bar goes through the level copy
        # (``drawdown_levels.level_project``) the multi-stage procedures use
        # too; on this model those answer "not applicable".
        from ogr_slip2d.support_integration import _bond_profiles
        for procedure, cohesion in (("b_bar", 8.0), ("b_bar", 20.0)):
            p = _drawdown(procedure, cohesion)
            ev = _evaluator(p)
            want = ev.evaluate_circle(p, _circle()).fos
            with p.regions_frozen():
                _bond_profiles(p)
                assert p._support_bond_cache
                got = ev.evaluate_circle(p, _circle()).fos
            assert want is not None and repr(got) == repr(want), procedure


def _drawdown(procedure, cohesion):
    """The clay slope with a full reservoir lowered by a drawdown line, an
    undrained material and a pile whose bond profile reads the water."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.support import SupportInstance
    from ogr_core.support.support import PileMicropile
    p = Project(name="drawdown and pile")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                             Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay", strength=MohrCoulomb(cohesion=cohesion,
                                                   friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=PorePressureType.WATER_TABLE)
    m.undrained_behaviour = True
    m.b_bar = 1.0
    p.add_material(m)
    wt = Boundary(polyline=Polyline(vertices=[Vertex(-1, 22), Vertex(51, 22)]),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-1, 16), Vertex(51, 16)]),
        btype=BoundaryType.DRAWDOWN))
    gw = p.settings.groundwater
    gw.rapid_drawdown = True
    gw.rapid_drawdown_method = procedure
    st = PileMicropile(failure_mode="ito_matsui", out_of_plane_spacing=2.0,
                       pile_diameter=0.6)
    p.support_types.append(st)
    p.supports.append(SupportInstance(type_id=st.TYPE_ID,
                                      head=Vertex(30.0, 20.0),
                                      tail=Vertex(30.0, 4.0)))
    return p
