# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Optimize Surfaces has to reach the calculation, and every knob has to bite.

WHAT INVARIANT THIS PROTECTS — rule 7, thirteen times over. ``SearchSettings``
declared thirteen ``optimize_*`` fields. They were editable in the Surface
Options dialog, written to the ``.ogr``, shown again on reopening, and read by
NOTHING outside ``ogr_gui``: ``build_search`` never passed one of them to a
search. Ticking "Optimize Surfaces" on a Block Search changed nothing at all,
to the last digit. That is anomaly A9-1, defect D08, and it is the same shape
as the partial factors that were configurable without being applied between
v0.1.52 and v0.1.57, and as the two Surface Filters of A37-1.

What was NOT broken, and it matters for reading the rest of this file: the
optimiser itself. ``ogr_slip2d.optimize.optimize_surface`` has implemented
Greco (1996) since v0.1.55, the menu action *Optimize Surfaces…* has always
reached it, and the second published scenario of the reference bank's problem
9 was produced with it from a script. What was dead was the checkbox.

AND ITS MIRROR IMAGE, found while closing it. Path Search DID optimise — every
run, unconditionally — because ``path_optimize`` defaulted to True and the
dialog never showed it, while the "Optimize Surfaces" checkbox on the Path
Search panel wrote ``optimize_enabled``, which nothing read. Visible name
dead, hidden name live: the shape of the six pairs D07b closed in v0.1.103.
There is one optimisation now, and one control for it.

THIS FILE ASSERTS ONE FACTOR OF SAFETY, and says where it comes from.
Everything else is a DIFFERENCE (two runs of one model must disagree), an
IDENTITY (what comes back satisfies the constraint, by definition of the
constraint) or a COUNT. None of those is a number this code printed, so none
can consecrate a bug.

THE VALUE ANCHOR (rule 1) is ``TestAgainstThePublishedNonCircularMinimum``
below: Yamagami and Ueta (1988) published the non-circular minimum of the
slope that ``validacion/casos/002-yamagami-ueta-1988`` holds, and the
verification manual that reproduces it says in its own table heading that it
got there "using Random search with Monte-Carlo optimization" — this option,
switched on. Janbu simplified and not Spencer or GLE, because those two are
under an open audit on this very model
(``docs/audits/spencer_gle_interslice_v179.md``) and ``caso.md`` excludes them
from the case on purpose.

COST. The expensive kind: a search plus a random walk per case. Every run is
cached and shared, the budgets are deliberately small, and no test here needs
a converged minimum — only two runs of one population disagreeing.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: Small on purpose: nothing below needs a converged minimum.
_NUM_SURFACES = 120
_NUM_SLICES = 20
#: Enough for the walk to move the number without dominating the file.
_MAX_ITERATIONS = 300
#: The bank's own seed, so a number quoted here can be reproduced there.
_SEED = 10116


def _slope():
    """A 12 m slope on 10 m of foundation.

    The same geometry ``test_surface_filters_v1102.py`` and the Slope Search
    tests use, and for the same reason: the foundation gives a non-circular
    surface somewhere to go.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("optimize wiring")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "block"
    s.block_num_surfaces = _NUM_SURFACES
    s.optimize_max_iterations = _MAX_ITERATIONS
    p.settings.methods.num_slices = _NUM_SLICES
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.random_numbers.seed = _SEED
    return p


_CACHE: dict = {}


def _run(**settings):
    """One configured search, run the way the application runs it.

    Through ``build_search`` deliberately: the defect was that the dialog and
    the engine disagreed, so a test that built the search by hand would have
    passed all along.
    """
    key = tuple(sorted((k, repr(v)) for k, v in settings.items()))
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        p = _slope()
        for name, value in settings.items():
            setattr(p.settings.search, name, value)
        search = build_search(p, "bishop_simplified")
        _CACHE[key] = (p, search.run(p))
    return _CACHE[key]


# ======================================================================
class TestTheCheckboxMovesTheNumber:
    """The headline of D08, and it is a DIFFERENCE, not a value."""

    def test_ticking_it_lowers_the_factor_of_safety(self):
        """A Block Search, one model, one seed, one setting changed.

        This is the assertion the defect asks for. It cannot pass by
        accident: with the box unticked the optimisation never runs, and
        the walk only ever accepts a surface with a LOWER factor, so a
        difference of any size in the right direction can only have come
        from the wiring being there.
        """
        _, off = _run()
        _, on = _run(optimize_enabled=True)
        assert off.critical is not None and on.critical is not None
        assert on.critical.fos < off.critical.fos, (
            off.critical.fos, on.critical.fos)

    def test_unticked_changes_absolutely_nothing(self):
        """The other half of rule 7, and the harder half to get right.

        A setting that is off must leave the analysis bit-identical, counts
        included — otherwise the wiring has quietly changed the search for
        everybody who never asked for it.
        """
        _, off = _run()
        _, again = _run(optimize_target="all",
                        optimize_max_iterations=99,
                        optimize_snap_shallow_to_slope=False)
        assert again.critical.fos == off.critical.fos
        assert again.valid_count == off.valid_count
        assert again.invalid_count == off.invalid_count
        assert len(again.evaluations) == len(off.evaluations)
        assert again.optimized is None

    def test_the_search_population_is_left_alone(self):
        """"the original surfaces which existed BEFORE the optimization
        will still be displayed" — so exactly ONE surface is added, the
        optimised global minimum, and the invalid count never moves."""
        _, off = _run()
        _, on = _run(optimize_enabled=True)
        assert on.optimized is not None
        assert len(on.evaluations) == len(off.evaluations) + 1
        assert on.valid_count == off.valid_count + 1
        assert on.invalid_count == off.invalid_count
        assert on.critical is on.optimized

    def test_it_is_reproducible_from_the_project_seed(self):
        """v0.1.74 promised that a pseudo-random run "will give exactly the
        same results". The walk draws at random too, so it needs the seed
        as much as the search does; with none it would answer differently
        every time and nothing would say so."""
        from ogr_slip2d.analysis_runner import build_search
        first = None
        for _ in range(2):
            p = _slope()
            p.settings.search.optimize_enabled = True
            r = build_search(p, "bishop_simplified").run(p)
            if first is None:
                first = r.critical.fos
            else:
                assert r.critical.fos == first


# ======================================================================
class TestAgainstThePublishedNonCircularMinimum:
    """Rule 1: an EXTERNAL value, and one obtained WITH this option on.

    Yamagami, T. and Ueta, Y. (1988), "Search for noncircular slip surfaces
    by the Morgenstern-Price method", Proc. 6th Int. Conf. on Numerical
    Methods in Geomechanics, Innsbruck, 1219-1223, publish the non-circular
    minimum of this slope: Janbu simplified 1.185, Spencer 1.339. Greco
    (1996) reanalysed the same slope and agrees. The verification manual
    that reproduces it heads its second table "Noncircular - using Random
    search with Monte-Carlo optimization", which is the option under test.

    The circular minimum of the same slope is HIGHER — Bishop 1.348,
    Fellenius 1.282, both already pinned by
    ``validacion/casos/002-yamagami-ueta-1988`` — so there is a published
    gap for the optimisation to close, and the direction of the claim is
    fixed by the sources rather than by this code.
    """

    #: Yamagami and Ueta (1988), non-circular, Janbu simplified.
    _PUBLISHED = 1.185
    #: The published value is a target the search has to REACH, not one it
    #: has to hit: a Block Search of this size on a slope with no weak
    #: layer to follow will not land on the authors' surface. What is
    #: asserted is that optimisation moves towards it and does not
    #: overshoot it by more than a search of this budget could explain.
    _OVERSHOOT = 0.10

    def _case(self, **settings):
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import build_search
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        p = Project.load(
            root / "validacion" / "casos" / "002-yamagami-ueta-1988"
            / "modelo.ogr")
        s = p.settings.search
        s.surface_type = "non_circular"
        s.search_method = "block"
        s.block_num_surfaces = _NUM_SURFACES
        s.optimize_max_iterations = _MAX_ITERATIONS
        p.settings.methods.num_slices = _NUM_SLICES
        p.settings.random_numbers.seed = _SEED
        for name, value in settings.items():
            setattr(s, name, value)
        return build_search(p, "janbu_simplified").run(p)

    def test_optimisation_moves_towards_the_published_value(self):
        key = ("yu88", tuple(sorted(())))
        if key not in _CACHE:
            _CACHE[key] = (self._case(), self._case(optimize_enabled=True))
        off, on = _CACHE[key]
        assert off.critical is not None and on.critical is not None
        plain, optimised = off.critical.fos, on.critical.fos
        # Towards, and from above: the search's own answer must be above
        # the published minimum, or the premise is wrong and the assertion
        # below would be measuring nothing.
        assert plain > self._PUBLISHED, (plain, self._PUBLISHED)
        assert optimised < plain, (plain, optimised)
        assert optimised > self._PUBLISHED * (1.0 - self._OVERSHOOT), (
            "the walk went BELOW the published non-circular minimum by "
            "more than a search of this budget can explain, which is the "
            "direction inadmissible surfaces lie in: %.4f against %.3f"
            % (optimised, self._PUBLISHED))


# ======================================================================
class TestEverySettingBites:
    """Rule 7, once per field. Twelve of these thirteen had no reader and
    no editor at all before v0.1.104."""

    def test_target_all_walks_every_surface_and_global_minimum_walks_one(self):
        """"All - this option will perform the optimization on EVERY
        SURFACE generated by the search."

        The selection IS the setting, so that is what is asserted, as an
        identity: one starting surface against every valid one. Asserting
        instead that "All" comes back with a lower factor would be a claim
        about this model rather than about the setting - and it happens to
        be false here, because on a population this small the global
        minimum is already the best place to start from.
        """
        p_gm, gm = _run(optimize_enabled=True)
        p_all, every = _run(optimize_enabled=True, optimize_target="all")
        from ogr_slip2d.analysis_runner import build_search
        one = build_search(p_gm, "bishop_simplified")
        one.optimize = p_gm.settings.optimize_kwargs()["optimize"]
        many = build_search(p_all, "bishop_simplified")
        many.optimize = p_all.settings.optimize_kwargs()["optimize"]
        assert len(one._surfaces_to_optimize(gm)) == 1
        assert len(many._surfaces_to_optimize(every)) > 1

    def test_target_all_can_never_lose_to_the_global_minimum(self):
        """And the containment that makes the choice safe to offer.

        Every walk is seeded alike, so the walk that starts from the
        global minimum is the SAME walk under either target and "All" can
        only add to it. Without that, "All" came back 1.1229 against
        1.1129 on this very model - worse for doing strictly more work,
        and silent about it. See the note in ``BaseSearch._optimize_result``.
        """
        _, gm = _run(optimize_enabled=True)
        _, every = _run(optimize_enabled=True, optimize_target="all")
        assert every.critical.fos <= gm.critical.fos + 1e-12, (
            gm.critical.fos, every.critical.fos)

    def test_the_threshold_decides_which_surfaces_are_walked(self):
        """"Factor of Safety Less Than" filters out high-factor starting
        points. A threshold below every surface leaves nothing to walk, so
        the answer must be the unoptimised one, to the last digit."""
        _, off = _run()
        _, none_selected = _run(optimize_enabled=True,
                                optimize_target="fos_less_than",
                                optimize_fos_threshold=0.001)
        assert none_selected.optimized is None
        assert none_selected.critical.fos == off.critical.fos

        _, all_selected = _run(optimize_enabled=True,
                               optimize_target="fos_less_than",
                               optimize_fos_threshold=1e6)
        assert all_selected.critical.fos < off.critical.fos

    def test_more_iterations_never_give_a_worse_answer(self):
        """The budget is a budget: a longer walk searches a superset of
        what a shorter one from the same seed searched."""
        _, short = _run(optimize_enabled=True, optimize_max_iterations=40)
        _, long_ = _run(optimize_enabled=True, optimize_max_iterations=600)
        assert long_.critical.fos <= short.critical.fos + 1e-12
        assert long_.critical.fos < short.critical.fos

    def test_a_loose_tolerance_stops_the_walk_earlier(self):
        """The documented criterion: converged when the factor of safety
        differs from the mean of the last five by less than Tolerance. A
        tolerance of 1 is satisfied by anything, so the walk must stop as
        soon as the window fills, spending far less of its budget."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        tight = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=1, tolerance=1e-9))[2]
        loose = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=1, tolerance=1.0))[2]
        assert loose.iterations < tight.iterations, (
            tight.summary(), loose.summary())
        assert loose.passes < tight.passes

    def test_the_step_reduction_factor_changes_the_walk(self):
        """"a factor (0 to 1) which determines the relative distance by
        which vertices are moved". Same seed, same surface, same budget:
        only the schedule differs, so any difference in the answer is the
        setting."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        slow = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=2,
            step_reduction_factor=0.9))[2]
        fast = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=2,
            step_reduction_factor=0.1))[2]
        assert slow.final_fos != fast.final_fos, (
            slow.summary(), fast.summary())

    def test_the_concave_limit_is_an_identity_on_what_comes_back(self):
        """"you can define the maximum allowable concave angle between
        adjacent segments"; unticked, "concave angles will not be allowed".

        An identity, so it cannot be a capture: every surface the walk
        returns satisfies the limit it was given — unless the surface it
        STARTED from already broke it, which the ceiling deliberately
        allows so that a Block Search wedge is not made unoptimisable.
        """
        from ogr_slip2d.optimize import (
            OptimizeSettings, max_concave_angle_deg, optimize_surface)
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        start = max_concave_angle_deg(
            [(v.x, v.y) for v in surface.polyline.vertices])
        for limit in (0.0, 5.0):
            best, _res, _rep = optimize_surface(
                p, search, surface, OptimizeSettings(
                    max_iterations=_MAX_ITERATIONS, seed=3,
                    max_concave_angle_deg=limit,
                    # the snap moves vertices AFTER the walk and answers to
                    # a different rule; excluded so this identity is about
                    # one thing.
                    snap_shallow_to_slope=False))
            got = max_concave_angle_deg(
                [(v.x, v.y) for v in best.polyline.vertices])
            assert got <= max(limit, start) + 1e-9, (limit, start, got)

    def test_the_concave_limit_changes_the_answer(self):
        """And it is not vacuous: a limit that forbids concave angles and
        one that tolerates twenty degrees explore different populations."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        strict = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=4,
            max_concave_angle_deg=0.0, snap_shallow_to_slope=False))[2]
        loose = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=4,
            max_concave_angle_deg=20.0, snap_shallow_to_slope=False))[2]
        assert strict.final_fos != loose.final_fos, (
            strict.summary(), loose.summary())

    def test_exploring_all_vertices_is_a_different_walk(self):
        """"the optimal direction of movement will be determined for each
        vertex, and all vertices will be moved at once" — against one
        vertex at a time. Same seed, same budget."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        one_at_a_time = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=5,
            explore_all_vertices=False))[2]
        all_at_once = optimize_surface(p, search, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=5,
            explore_all_vertices=True))[2]
        assert one_at_a_time.final_fos != all_at_once.final_fos, (
            one_at_a_time.summary(), all_at_once.summary())
        # And the pass is genuinely a combined move, not a relabelling: it
        # spends several evaluations per vertex, so it makes far fewer.
        assert all_at_once.passes < one_at_a_time.passes
        # The report has to add up in this mode too. It did not while the
        # remembered-but-not-committed probes went uncounted, and a report
        # whose arithmetic depends on which option is on is a report that
        # cannot be checked.
        for rep in (one_at_a_time, all_at_once):
            assert rep.accepted + rep.rejected == rep.iterations, rep.summary()

    def test_snapping_is_an_identity_on_the_returned_surface(self):
        """"if any vertex of the slip surface is within this distance of
        the slope surface, then the vertex will automatically be snapped up
        to the slope". So afterwards no interior vertex is inside the band,
        which is an identity and not a capture."""
        from ogr_slip2d.optimize import (
            OptimizeSettings, _ground_y, optimize_surface)
        from ogr_core.geometry import ground_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        distance = 0.75
        best, _res, _rep = optimize_surface(
            p, search, surface, OptimizeSettings(
                max_iterations=_MAX_ITERATIONS, seed=6,
                snap_shallow_to_slope=True,
                snap_distance=distance))
        ground = list(ground_surface(p.external_boundary()).vertices)
        pts = [(v.x, v.y) for v in best.polyline.vertices]
        for x, y in pts[1:-1]:
            gy = _ground_y(ground, x)
            if gy is None:
                continue
            gap = gy - y
            assert not (0.0 < gap < distance - 1e-9), (x, y, gy, gap)

    def test_snapping_changes_the_answer(self):
        """Rule 7 for the option itself, and note the direction is NOT
        asserted: the reference's own worked example shows the factor going
        UP after snapping (1.644 to 1.658), because what it removes is a
        sliver that was never a mechanism."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p)
        surface = run.critical.surface
        common = dict(max_iterations=_MAX_ITERATIONS, seed=7)
        off = optimize_surface(p, search, surface, OptimizeSettings(
            snap_shallow_to_slope=False, **common))[2]
        on = optimize_surface(p, search, surface, OptimizeSettings(
            snap_shallow_to_slope=True, snap_distance=1.5, **common))[2]
        assert on.final_fos != off.final_fos, (off.summary(), on.summary())
        assert on.notes.get("snapped_vertices")

    def test_the_surface_checks_can_be_switched_off_for_the_walk(self):
        """*Use checks for depth, elevation, concave surface* is what ties
        this option to the Surface Filters of D07. With the checks on, the
        walk must respect a Minimum Depth; with them off it need not, and
        the two therefore cannot give the same answer on a model where the
        filter bites."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        surface = run.critical.surface
        deep = self._evaluator(p, min_depth=6.0)
        checked = optimize_surface(p, deep, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=8,
            use_surface_checks=True, snap_shallow_to_slope=False))[2]
        unchecked = optimize_surface(p, deep, surface, OptimizeSettings(
            max_iterations=_MAX_ITERATIONS, seed=8,
            use_surface_checks=False, snap_shallow_to_slope=False))[2]
        assert checked.final_fos != unchecked.final_fos, (
            checked.summary(), unchecked.summary())

    def test_turning_the_checks_off_leaves_the_search_untouched(self):
        """It evaluates against a COPY. A filter cleared for the walk and
        left cleared on the search would silently disarm the next thing to
        use it — which is how a filter goes missing in the first place."""
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p, run = _run()
        search = self._evaluator(p, min_depth=6.0)
        optimize_surface(p, search, run.critical.surface, OptimizeSettings(
            max_iterations=20, seed=9, use_surface_checks=False))
        assert search.min_depth == 6.0

    # ------------------------------------------------------------------
    @staticmethod
    def _evaluator(project, **kwargs):
        """A search object used only to score candidates."""
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import BlockSearch
        cls = method_registry()["bishop_simplified"]
        return BlockSearch(method=cls(), num_slices=_NUM_SLICES,
                           min_area=0.0, **kwargs)


# ======================================================================
class TestTheOptionKnowsWhereItDoesNotApply:
    """Rule 7's minimum when a control CANNOT be honoured: say so."""

    def test_a_circular_search_says_the_setting_was_ignored(self):
        """The reference offers Optimize Surfaces for Surface Type =
        Non-Circular. A circle has no vertices to move, so the honest
        answer is a note, not a silently ignored tick."""
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _slope()
        p.settings.search.search_method = "grid"
        p.settings.search.surface_type = "circular"
        p.settings.search.optimize_enabled = True
        notes = " ".join(settings_warnings(p))
        assert "Optimize Surfaces" in notes and "ignored" in notes

    def test_optimising_every_surface_says_what_it_costs(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _slope()
        p.settings.search.optimize_enabled = True
        p.settings.search.optimize_target = "all"
        notes = " ".join(settings_warnings(p))
        assert "ALL surfaces" in notes

    def test_a_circular_search_is_not_optimised(self):
        """And the note is not the only guard: the option must not reach a
        circular branch at all."""
        from ogr_slip2d.analysis_runner import build_search
        p = _slope()
        p.settings.search.search_method = "grid"
        p.settings.search.surface_type = "circular"
        p.settings.search.optimize_enabled = True
        assert build_search(p, "bishop_simplified").optimize is None


# ======================================================================
class TestPathOptimizeIsRetired:
    """The mirror image of D08, closed with it.

    ``path_optimize`` defaulted to True and no dialog showed it, so Path
    Search optimised on every run while the checkbox the user could see
    wrote a setting nothing read. Retiring it CHANGES what Path Search
    returns by default, and that is the point: the behaviour is now the one
    the model asks for.
    """

    def test_the_field_is_gone(self):
        from dataclasses import fields
        from ogr_core.project.settings import SearchSettings
        assert "path_optimize" not in {f.name for f in fields(SearchSettings)}

    def test_a_stored_model_carrying_it_is_told_what_changed(self):
        """The note fires on True — the value every model has, because
        nothing could ever set it to anything else — since True is the one
        that used to optimise and now does not."""
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings.from_dict({"path_optimize": True})
        notes = " ".join(s._migration_notes)
        assert "path_optimize" in notes and "optimize" in notes
        # Ticked, the behaviour is unchanged, so there is nothing to say.
        quiet = SearchSettings.from_dict({"path_optimize": True,
                                          "optimize_enabled": True})
        assert quiet._migration_notes == []
        # And False never optimised, so neither is there anything to say.
        off = SearchSettings.from_dict({"path_optimize": False})
        assert off._migration_notes == []

    def test_assigning_it_by_hand_refuses_the_analysis(self):
        """A dataclass takes any attribute you hand it without a word, so a
        script setting ``s.path_optimize = True`` would look like a setting
        and reach nothing. The refusal is the only answer that cannot be
        mistaken for having worked — the same guard v0.1.103 built."""
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _slope()
        p.settings.search.path_optimize = True
        problems = " ".join(check_analysis_settings(p))
        assert "path_optimize" in problems

    def test_path_search_optimises_only_when_asked(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _slope()
        p.settings.search.search_method = "path"
        p.settings.search.path_num_surfaces = 40
        assert build_search(p, "bishop_simplified").optimize is None
        p.settings.search.optimize_enabled = True
        built = build_search(p, "bishop_simplified")
        assert built.optimize is not None and built.optimize.enabled
        assert built.optimize_seed == p.settings.analysis_seed()


# ======================================================================
class TestTheSettingsReachTheOptimiserUnchanged:
    """One place turns settings into arguments; this is what it must say.

    The mapping is not the identity in two places, and both are places a
    reader would guess wrong: an unticked *Maximum Concave Angle* means a
    limit of ZERO, not "no limit", and an unticked *Specify Distance* means
    automatic, so the number the box shows must not travel.
    """

    def test_every_field_arrives(self):
        p = _slope()
        s = p.settings.search
        s.optimize_enabled = True
        s.optimize_target = "fos_less_than"
        s.optimize_fos_threshold = 1.25
        s.optimize_max_iterations = 321
        s.optimize_tolerance = 1e-7
        s.optimize_step_reduction_factor = 0.25
        s.optimize_max_concave_angle_enabled = True
        s.optimize_max_concave_angle_deg = 12.5
        s.optimize_explore_all_vertices = True
        s.optimize_snap_shallow_to_slope = True
        s.optimize_snap_specify_distance = True
        s.optimize_snap_distance = 0.4
        s.optimize_use_depth_elevation_concave_checks = False
        o = p.settings.optimize_kwargs()["optimize"]
        assert o.enabled is True
        assert o.target == "fos_less_than"
        assert o.fos_threshold == 1.25
        assert o.max_iterations == 321
        assert o.tolerance == 1e-7
        assert o.step_reduction_factor == 0.25
        assert o.max_concave_angle_deg == 12.5
        assert o.explore_all_vertices is True
        assert o.snap_shallow_to_slope is True
        assert o.snap_distance == 0.4
        assert o.use_surface_checks is False

    def test_an_unticked_concave_box_means_zero_not_infinity(self):
        p = _slope()
        s = p.settings.search
        s.optimize_enabled = True
        s.optimize_max_concave_angle_enabled = False
        s.optimize_max_concave_angle_deg = 5.0
        assert p.settings.optimize_kwargs()["optimize"].max_concave_angle_deg \
            == 0.0

    def test_an_unticked_distance_box_means_automatic(self):
        p = _slope()
        s = p.settings.search
        s.optimize_enabled = True
        s.optimize_snap_specify_distance = False
        s.optimize_snap_distance = 0.4
        assert p.settings.optimize_kwargs()["optimize"].snap_distance is None

    def test_unticked_produces_no_settings_object_at_all(self):
        p = _slope()
        assert p.settings.optimize_kwargs() == {"optimize": None}

    def test_the_defaults_are_the_same_on_both_sides(self):
        """The v0.1.89 lesson: two doors into one calculation must not
        carry different defaults. ``OptimizeSettings`` is reached from the
        checkbox and from the *Optimize Surfaces…* menu action."""
        from ogr_core.project.settings import SearchSettings
        from ogr_slip2d.optimize import OptimizeSettings
        d, o = SearchSettings(), OptimizeSettings()
        assert o.target == d.optimize_target
        assert o.fos_threshold == d.optimize_fos_threshold
        assert o.max_iterations == d.optimize_max_iterations
        assert o.tolerance == d.optimize_tolerance
        assert o.step_reduction_factor == d.optimize_step_reduction_factor
        assert d.optimize_max_concave_angle_enabled
        assert o.max_concave_angle_deg == d.optimize_max_concave_angle_deg
        assert o.explore_all_vertices == d.optimize_explore_all_vertices
        assert o.snap_shallow_to_slope == d.optimize_snap_shallow_to_slope
        assert not d.optimize_snap_specify_distance and o.snap_distance is None
        assert (o.use_surface_checks
                == d.optimize_use_depth_elevation_concave_checks)


# ======================================================================
class TestTheDialogCanClearTheBox:
    """Found while closing D08: the checkbox could be ticked and never
    un-ticked. Three panels showed it, ``apply`` folded them with an OR,
    and all three start from the same stored value — so clearing it in one
    left the other two holding True and the OR put it straight back."""

    @staticmethod
    def _app():
        """One QApplication for the process; building a widget without one
        does not raise, it takes the interpreter down."""
        from PySide6.QtWidgets import QApplication
        return QApplication.instance() or QApplication([])

    def _dialog(self, project):
        from ogr_gui.dialogs import SurfaceOptionsDialog
        self._app()
        return SurfaceOptionsDialog(project)

    def test_unticking_in_one_panel_clears_the_setting(self):
        p = _slope()
        p.settings.search.optimize_enabled = True
        d = self._dialog(p)
        assert all(b.isChecked() for b in d._optimize_boxes)
        # The Simulated Annealing panel, while Block Search is selected:
        # the one the user cannot see is exactly the one that used to win.
        d._sa_optimize.setChecked(False)
        d.apply()
        assert p.settings.search.optimize_enabled is False

    def test_ticking_in_one_panel_sets_it(self):
        p = _slope()
        d = self._dialog(p)
        d._p_optimize.setChecked(True)
        d.apply()
        assert p.settings.search.optimize_enabled is True

    def test_the_three_panels_never_disagree(self):
        p = _slope()
        d = self._dialog(p)
        for box in (d._sa_optimize, d._p_optimize, d._b_optimize):
            box.setChecked(True)
            assert all(b.isChecked() for b in d._optimize_boxes)
            box.setChecked(False)
            assert not any(b.isChecked() for b in d._optimize_boxes)

    def test_the_settings_dialog_writes_every_field(self):
        from ogr_gui.dialogs import OptimizeSettingsDialog
        p = _slope()
        self._app()
        d = OptimizeSettingsDialog(p)
        d.rb_all.setChecked(True)
        d.sb_iterations.setValue(1234)
        d.sb_step.setValue(0.25)
        d.cb_concave.setChecked(False)
        d.cb_explore.setChecked(True)
        d.g_snap.setChecked(False)
        d.cb_checks.setChecked(False)
        d.apply()
        s = p.settings.search
        assert s.optimize_target == "all"
        assert s.optimize_max_iterations == 1234
        assert s.optimize_step_reduction_factor == 0.25
        assert s.optimize_max_concave_angle_enabled is False
        assert s.optimize_explore_all_vertices is True
        assert s.optimize_snap_shallow_to_slope is False
        assert s.optimize_use_depth_elevation_concave_checks is False

    def test_the_settings_dialog_round_trips_what_it_was_given(self):
        from ogr_gui.dialogs import OptimizeSettingsDialog
        p = _slope()
        s = p.settings.search
        s.optimize_target = "fos_less_than"
        s.optimize_fos_threshold = 1.05
        s.optimize_snap_specify_distance = True
        s.optimize_snap_distance = 0.33
        self._app()
        d = OptimizeSettingsDialog(p)
        assert d.rb_threshold.isChecked()
        assert d.sb_threshold.value() == 1.05
        assert d.cb_distance.isChecked()
        d.apply()
        assert s.optimize_target == "fos_less_than"
        assert s.optimize_fos_threshold == 1.05
        assert s.optimize_snap_distance == 0.33
