# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.103 — the search does the amount of work the setting the
user can see asks for.

**The invariant**: every project here is built BY CODE, never through the
Surface Options dialog, and that is the whole point. Six settings used to
exist twice — the name the interface showed and saved, and the name the
engine read — and the dialog wrote BOTH from the same widget. So from the
interface they always agreed and nothing looked wrong; a project built by
a script kept the name that was not consumed, and the analysis silently
ran on the other one's default. A test driving the dialog would have
passed throughout.

What it cost, measured on the reference bank: a Path Search that declared
5000 surfaces generated 500 (the recorded run shows 608 generated, 505
valid — 500 plus the five the optimisation post-process adds), and an
Auto Refine that published 10 iterations ran 5. A sparser search finds a
worse critical surface, i.e. a HIGHER factor of safety, so the direction
of the error was unsafe.

Rule 7: each test below measures the work actually done, not the number
that was declared.
"""
from __future__ import annotations
import math


def _slope(name: str = "effort"):
    """A small slope with 10 m of foundation under the toe.

    Deliberately modest — these tests measure counts, not factors of
    safety, so every surface evaluated beyond the minimum is wasted time.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 10.0
    beta = math.radians(35.0)
    toe = 20.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -8.0), Vertex(45, -8.0), Vertex(45, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=19,
                            strength=MohrCoulomb(cohesion=10,
                                                 friction_angle=25))]
    p.settings.methods.num_slices = 15
    p.settings.statistics.seed = 20260823
    return p


def _path_project(num_surfaces: int):
    p = _slope(f"path-{num_surfaces}")
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "path"
    s.path_num_surfaces = num_surfaces
    # v0.1.104 — ``s.path_optimize = False`` stood here, "so valid_count is
    # the generator's own count". The field is gone: Path Search no longer
    # optimises unless asked, so that IS the count now, and assigning the
    # retired name is refused by ``check_analysis_settings`` — which is the
    # guard this file's own last test checks.
    return p


# ======================================================================
class TestPathSearchNumberOfSurfaces:
    """"Number of Surfaces" is the count of VALID surfaces: the generator
    discards the invalid ones and they do not count towards the total.
    That is what the reference says the control means and what the loop
    does, which is why the two names were one quantity all along."""

    def test_the_search_is_built_with_the_field_the_user_edits(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(37)
        search = build_search(p, "bishop_simplified")
        assert search.num_surfaces == 37

    def test_it_generates_as_many_valid_surfaces_as_asked(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(40)
        r = build_search(p, "bishop_simplified").run(p)
        assert r.valid_count == 40, r.valid_count

    def test_asking_for_half_does_half_the_work(self):
        """Not a snapshot: the ratio is the invariant, and it is the
        measurement that would have caught the defect on the bank."""
        from ogr_slip2d.analysis_runner import build_search
        few = build_search(_path_project(20), "bishop_simplified")
        many = build_search(_path_project(40), "bishop_simplified")
        r_few = few.run(_path_project(20))
        r_many = many.run(_path_project(40))
        assert r_few.valid_count == 20
        assert r_many.valid_count == 40

    def test_the_optimisation_pass_adds_at_most_five_more(self):
        """With Optimize Surfaces on, the count overshoots by the handful
        of refined surfaces the post-process appends — which is exactly
        why the bank recorded 505 valid for a target of 500, and how that
        recording identified the target as 500 and not 5000."""
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(30)
        p.settings.search.path_optimize = True
        r = build_search(p, "bishop_simplified").run(p)
        assert 30 <= r.valid_count <= 35, r.valid_count


# ======================================================================
class TestAutoRefineIterations:
    """The reference's panel shows "Number of Iterations: 10" and so did
    the field the interface edited; the engine read a second field that
    defaulted to 5."""

    @staticmethod
    def _run(iterations: int):
        from ogr_slip2d.analysis_runner import build_search
        p = _slope(f"ar-{iterations}")
        s = p.settings.search
        s.search_method = "auto_refine"
        s.auto_refine_divisions_along_slope = 4
        s.auto_refine_circles_per_division = 3
        s.auto_refine_num_iterations = iterations
        totals = []
        search = build_search(
            p, "bishop_simplified",
            progress_cb=lambda done, total: totals.append(total))
        result = search.run(p)
        return search, result, totals

    def test_the_search_is_built_with_the_field_the_user_edits(self):
        search, _r, _t = self._run(7)
        assert search.iterations == 7

    def test_the_loop_really_runs_them(self):
        """``progress_cb``'s second argument is the loop's own bound, so
        it reports the count the search is actually going to walk rather
        than the one the model declared."""
        _s, _r, totals = self._run(6)
        assert totals and set(totals) == {6}, totals

    def test_doubling_the_iterations_doubles_the_surfaces(self):
        _s, r2, _ = self._run(2)
        _s, r4, _ = self._run(4)
        n2, n4 = len(r2.evaluations), len(r4.evaluations)
        assert n2 > 0
        # Divisions and circles are fixed, so the work is linear in the
        # iteration count. Loose bounds: a division whose surfaces all
        # fail can contribute fewer evaluations in either run.
        assert 1.5 * n2 <= n4 <= 2.5 * n2, (n2, n4)


# ======================================================================
class TestPathSegmentLength:
    """Unticked means AUTOMATIC (~0.3·H). The reference is explicit that
    a user-defined length is the exception, not the norm — and until
    v0.1.103 the automatic one was unreachable: the field the engine read
    defaulted to a fixed 5.0 and the checkbox was written past."""

    def test_unticked_asks_the_search_for_its_automatic_length(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(5)
        assert p.settings.search.path_segment_length_manual is False
        assert build_search(p, "bishop_simplified").segment_length is None

    def test_ticked_uses_the_value(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(5)
        p.settings.search.path_segment_length_manual = True
        p.settings.search.path_segment_length_value = 3.25
        assert build_search(p, "bishop_simplified").segment_length == 3.25

    def test_the_checkbox_changes_the_surfaces(self):
        """Rule 7 in one assertion: the control moves the result. Same
        seed both times, so the difference is the segment length."""
        from ogr_slip2d.analysis_runner import build_search
        auto = build_search(_path_project(25), "bishop_simplified").run(
            _path_project(25))
        p = _path_project(25)
        p.settings.search.path_segment_length_manual = True
        p.settings.search.path_segment_length_value = 2.0
        fixed = build_search(p, "bishop_simplified").run(p)
        assert auto.critical is not None and fixed.critical is not None
        assert (auto.critical.fos != fixed.critical.fos
                or auto.attempts != fixed.attempts)


# ======================================================================
class TestInitialAngleAtToe:
    """The angles are absolute, counter-clockwise from +x — the
    convention the control is stated in. The generator works in a
    toe-to-crest frame, so exactly one conversion stands between them."""

    def test_the_reference_equivalence_is_the_conversion(self):
        """An upper angular limit of 30 degrees for a failure running one
        way "is equivalent to" 150 degrees for one running the other.
        That published equivalence IS this mirror, and it is an identity,
        not a captured value."""
        from ogr_slip2d.search import toe_frame_angle_deg
        assert toe_frame_angle_deg(30.0, True) == toe_frame_angle_deg(
            150.0, False)
        # And the mirror is its own inverse.
        for deg in (-45.0, 0.0, 12.5, 90.0, 137.0):
            assert toe_frame_angle_deg(
                toe_frame_angle_deg(deg, False), False) == deg
            assert toe_frame_angle_deg(deg, True) == deg

    def test_unticked_boxes_leave_the_window_automatic(self):
        from ogr_slip2d.analysis_runner import build_search
        search = build_search(_path_project(5), "bishop_simplified")
        assert search.initial_angle_lower_deg is None
        assert search.initial_angle_upper_deg is None

    def test_ticked_boxes_reach_the_generator(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _path_project(5)
        s = p.settings.search
        s.path_initial_angle_at_toe_lower_enabled = True
        s.path_initial_angle_at_toe_lower_deg = -35.0
        s.path_initial_angle_at_toe_upper_enabled = True
        s.path_initial_angle_at_toe_upper_deg = 25.0
        search = build_search(p, "bishop_simplified")
        assert search.initial_angle_lower_deg == -35.0
        assert search.initial_angle_upper_deg == 25.0


# ======================================================================
class TestAnnealingTemperatureCoefficient:
    """c in T_k = T_0·exp(−c·k^(1/n)) — Su (2009), section 2.1.6, eqs.
    (10)-(11), which adopts c = 8.0 and reports 1 to 10 as adequate.

    The field the interface edited held that 8.0 and nothing read it; the
    engine hard-coded 8.0 and the field it DID read held a geometric
    cooling rate of 0.97 that was stored, clamped and never used."""

    @staticmethod
    def _project(c: float):
        p = _slope(f"sa-{c}")
        s = p.settings.search
        s.surface_type = "non_circular"
        s.search_method = "simulated_annealing"
        s.sa_initial_vertices = 6
        s.sa_generation_steps = 150
        s.sa_temperature_coefficient = c
        return p

    def test_the_declared_coefficient_reaches_the_search(self):
        from ogr_slip2d.analysis_runner import build_search
        search = build_search(self._project(3.5), "bishop_simplified")
        assert search.temperature_coefficient == 3.5

    def test_the_default_is_the_constant_the_schedule_always_ran_on(self):
        """Migration guard: 8.0 is what the code hard-coded, so wiring the
        setting up cannot move a single stored result by itself."""
        from ogr_core.project.settings import SearchSettings
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch
        assert SearchSettings().sa_temperature_coefficient == 8.0
        assert SimulatedAnnealingSearch(
            method=BishopSimplified()).temperature_coefficient == 8.0

    def test_it_moves_the_number(self):
        """Rule 7. Same seed, same everything else: a slower cooling
        schedule explores differently, so the two runs cannot agree in
        every particular."""
        from ogr_slip2d.analysis_runner import build_search
        p8, p2 = self._project(8.0), self._project(1.5)
        r8 = build_search(p8, "bishop_simplified").run(p8)
        r2 = build_search(p2, "bishop_simplified").run(p2)
        assert r8.critical is not None and r2.critical is not None
        assert (r8.critical.fos != r2.critical.fos
                or len(r8.evaluations) != len(r2.evaluations))

    def test_the_old_name_is_refused_rather_than_absorbed(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch
        try:
            SimulatedAnnealingSearch(method=BishopSimplified(),
                                     temperature_factor=0.95)
        except TypeError as exc:
            assert "temperature_coefficient" in str(exc)
        else:
            raise AssertionError("a cooling rate was silently absorbed")


# ======================================================================
class TestStoredModelsMigrate:
    """A `.ogr` written before v0.1.103 carries both names of every pair.
    Which one wins is decided by which of the two departs from its own
    default, because that is the only one that shows intent."""

    @staticmethod
    def _s(**stored):
        from ogr_core.project.settings import SearchSettings
        return SearchSettings.from_dict(stored)

    def test_a_script_that_set_the_visible_name_gets_what_it_asked(self):
        """The bank's problem 18: declared 5000, searched 500."""
        s = self._s(path_num_surfaces=5000, path_num_paths=500)
        assert s.path_num_surfaces == 5000

    def test_a_script_that_set_the_retired_name_still_gets_it(self):
        """Three models of the bank set ``path_num_paths`` on purpose and
        left the visible field at its default. Honouring the default
        instead would raise their search sixteen-fold in silence, which is
        the same fault pointing the other way."""
        s = self._s(path_num_surfaces=5000, path_num_paths=300)
        assert s.path_num_surfaces == 300

    def test_a_model_saved_from_the_interface_is_unambiguous(self):
        s = self._s(path_num_surfaces=800, path_num_paths=800)
        assert s.path_num_surfaces == 800

    def test_an_older_format_with_only_the_retired_name(self):
        assert self._s(path_num_paths=250).path_num_surfaces == 250

    def test_auto_refine_iterations_migrate_the_same_way(self):
        assert self._s(auto_refine_num_iterations=10,
                       auto_refine_iterations=5).auto_refine_num_iterations == 10
        assert self._s(auto_refine_num_iterations=10,
                       auto_refine_iterations=7).auto_refine_num_iterations == 7

    def test_zero_segment_length_meant_automatic(self):
        s = self._s(path_segment_length=0.0)
        assert s.path_segment_length_manual is False

    def test_a_fixed_segment_length_ticks_the_box(self):
        s = self._s(path_segment_length=12.0)
        assert s.path_segment_length_manual is True
        assert s.path_segment_length_value == 12.0

    def test_angles_are_reported_rather_than_guessed(self):
        """They were stored in the search's own frame and the field
        replacing them is absolute, so converting needs the failure
        direction — which is not in this block. Guessing would be worse
        than saying so."""
        s = self._s(path_min_angle_deg=-30.0)
        assert any("path_initial_angle_at_toe_lower_deg" in n
                   for n in s._migration_notes)
        assert self._s(path_min_angle_deg=-45.0)._migration_notes == []

    def test_an_unknown_key_no_longer_raises(self):
        assert self._s(a_setting_from_the_future=1).path_num_surfaces == 5000

    def test_the_notes_never_travel_back_into_the_file(self):
        from dataclasses import asdict
        s = self._s(sa_temperature_factor=0.5)
        assert s._migration_notes
        assert "_migration_notes" not in asdict(s)

    def test_every_model_kept_in_the_repository_still_loads(self):
        from pathlib import Path
        from ogr_core.project import Project
        root = Path(__file__).resolve().parent.parent / "validacion" / "casos"
        models = sorted(root.glob("*/modelo.ogr"))
        assert models, "no stored models to check the migration against"
        for m in models:
            p = Project.load(m)
            assert p.settings.search.path_num_surfaces > 0, m.parent.name


# ======================================================================
class TestARetiredNameIsRefusedNotIgnored:
    """A dataclass takes any attribute you hand it. ``s.path_num_paths =
    300`` on a live settings object would therefore still look like a
    setting and still reach nothing — the defect exactly, reintroduced
    from the outside. The run refuses instead."""

    def test_the_analysis_refuses_and_names_the_field_that_works(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _path_project(10)
        p.settings.search.path_num_paths = 300
        problems = check_analysis_settings(p)
        assert any("path_num_surfaces" in why for why in problems), problems

    def test_a_clean_project_raises_nothing(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        assert check_analysis_settings(_path_project(10)) == []
