# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.157 (D58) — slip surfaces the user defines by hand.

The invariant these protect is rule 7 in its purest form: a control the
user believes the analysis respects must move the number.

``Add Surface (centre and radius)`` built a ``SlipCircle``, appended it to
an attribute invented on the instance by ``hasattr``, and stopped there.
``user_surfaces`` appeared THREE times in the whole repository, all three
consecutive lines of that one method: nothing serialised it, nothing drew
it, nothing analysed it. The circle did not survive a save — while
``is_dirty`` still made the interface ask the user to save for it. The
action shipped in the first public release (v0.1.59) and the finding was
already written in the v0.1.131 changelog without a ticket.

What is anchored here, in the order the surface travels:

* it SURVIVES a round trip through the .ogr, and a file written before
  this version still loads (there is nothing to migrate: the attribute was
  never written to a file at all);
* the engine EVALUATES it, and its factor of safety is exactly what
  ``evaluate_circle`` gives for the same circle — an identity between two
  paths, not a snapshot of what the code prints today;
* it COMPETES for the global minimum and wins when its factor is lower,
  which is the reference's definition of the global minimum: the lowest of
  ALL surfaces analysed;
* the search COUNTERS do not move, because ``total_count`` is a checkable
  identity against the population the reference documents and a surface
  the search never generated is not part of it;
* the user's own circle comes out of the analysis UNTOUCHED;
* the notes carry none of the three substrings the verification bank
  reserves for its D40 check.

The numbers below are never hard-coded: every factor of safety is compared
against the other path that computes it, so a change in the engine moves
both sides together and this file keeps testing what it says it tests.
"""
from __future__ import annotations

import json
import os


# The demo slope of ``examples/quick_slope.py``. A search coarse enough
# that a hand-placed circle can beat it, which is the whole point of case 2.
_GRID = dict(grid_x=(10, 40), grid_y=(25, 55), grid_nx=6, grid_ny=6,
             radius_increment=5, num_slices=25, min_area=0.5)

# A circle on the demo slope whose factor is BELOW the coarse search's
# minimum. Chosen well away from r ≈ 17.47, where the arc stops daylighting
# at the toe (x ≈ 35) and starts emerging on the flat ground beyond it
# (x ≈ 43): that transition is physical — toe circle against deep-seated
# circle — but a test sitting on it would be measuring the boundary.
_WINNER = dict(centre_x=39.0, centre_y=32.0, radius=17.4)


def _give(project, *circles):
    """Attach surfaces by ASSIGNMENT, never by appending to the field.

    Deliberate, and it is what makes these tests evidence: assignment works
    on the version before this one too — Python lets anyone set an
    attribute — so a failure there is the DEFECT (the surface is dropped by
    the save, or ignored by the run), not the absence of the field.
    """
    project.user_surfaces = list(circles)
    return project


def _project():
    from examples.quick_slope import build_demo_slope
    return build_demo_slope()


def _run(project):
    from ogr_slip2d import BishopSimplified, GridSearch
    return GridSearch(method=BishopSimplified(), **_GRID).run(project)


def _evaluate_alone(project, **circle):
    """The same circle through the other public door, for the identity."""
    from ogr_slip2d import BishopSimplified, GridSearch
    from ogr_slip2d.surface import SlipCircle
    ev = GridSearch(method=BishopSimplified(),
                    num_slices=_GRID["num_slices"],
                    min_area=_GRID["min_area"])
    return ev.evaluate_circle(project, SlipCircle(**circle))


class TestPersistence:
    """The circle survives the file. It did not before."""

    def test_round_trip_through_the_ogr(self, tmp_path):
        from ogr_core.project import Project
        from ogr_slip2d.surface import SlipCircle

        p = _give(Project(name="round trip"),
                  SlipCircle(centre_x=1.5, centre_y=2.5, radius=3.5),
                  SlipCircle(centre_x=-4.0, centre_y=9.0, radius=12.25))
        ids = [c.id for c in p.user_surfaces]

        out = tmp_path / "rt.ogr"
        p.save(out)
        back = Project.load(out)

        assert len(back.user_surfaces) == 2
        assert [(c.centre_x, c.centre_y, c.radius)
                for c in back.user_surfaces] == [
                    (1.5, 2.5, 3.5), (-4.0, 9.0, 12.25)]
        # The identity travels too: without it a surface cannot be told
        # apart from another with the same geometry.
        assert [c.id for c in back.user_surfaces] == ids

    def test_endpoints_are_not_stored(self, tmp_path):
        """x_left/x_right are a RESULT, not something the user typed."""
        from ogr_core.project import Project
        from ogr_slip2d.surface import SlipCircle

        p = _give(Project(name="endpoints"),
                  SlipCircle(centre_x=1.0, centre_y=2.0, radius=3.0))
        out = tmp_path / "e.ogr"
        p.save(out)
        back = Project.load(out)
        assert back.user_surfaces[0].x_left is None
        assert back.user_surfaces[0].x_right is None

    def test_a_file_without_the_key_still_loads(self, tmp_path):
        """Every .ogr written before v0.1.157 is such a file."""
        from ogr_core.project import Project

        p = Project(name="old file")
        out = tmp_path / "old.ogr"
        p.save(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        data.pop("user_surfaces", None)
        out.write_text(json.dumps(data), encoding="utf-8")

        assert Project.load(out).user_surfaces == []

    def test_a_fresh_project_has_the_field(self):
        """Declared on the class, not conjured by ``hasattr``."""
        from ogr_core.project import Project
        assert Project(name="fresh").user_surfaces == []


class TestTheNumberMoves:
    """Rule 7: the surface changes the published factor of safety."""

    def test_it_is_evaluated_at_all(self):
        p = _project()
        assert _run(p).user_evaluations == []
        _give(p, _circle(**_WINNER))
        assert len(_run(p).user_evaluations) == 1

    def test_it_wins_the_global_minimum_and_the_number_changes(self):
        p = _project()
        without = _run(p)
        assert not without.is_user_surface(without.critical)

        _give(p, _circle(**_WINNER))
        with_it = _run(p)

        assert with_it.is_user_surface(with_it.critical)
        assert with_it.critical.fos < without.critical.fos
        assert with_it.min_fos < without.min_fos

    def test_the_factor_is_the_one_the_other_door_gives(self):
        """An identity between two paths, not a captured number.

        The engine may change what this circle is worth; what may not
        change is that the run and ``evaluate_circle`` disagree about it.
        """
        p = _project()
        _give(p, _circle(**_WINNER))
        reported = _run(p).critical
        alone = _evaluate_alone(p, **_WINNER)
        assert alone is not None and alone.is_valid
        assert reported.fos == alone.fos

    def test_removing_it_restores_the_search_minimum_exactly(self):
        p = _project()
        before = _run(p).critical.fos
        _give(p, _circle(**_WINNER))
        assert _run(p).critical.fos != before
        p.user_surfaces = []
        assert _run(p).critical.fos == before

    def test_it_joins_the_drawn_population(self):
        """``valid()`` is what the canvas, Interpret and the exporters read."""
        p = _project()
        n = len(_run(p).valid())
        _give(p, _circle(**_WINNER))
        assert len(_run(p).valid()) == n + 1


class TestTheCountersDoNotLie:
    """The counters describe the SEARCH, and must keep doing so.

    ``total_count`` is checkable against the population the reference
    documents — (X intervals + 1)·(Y + 1)·(Radius Increment + 1). A surface
    the search never generated cannot enter that count without breaking an
    identity that three validation files rest on.
    """

    def test_search_counters_are_untouched(self):
        p = _project()
        without = _run(p)
        _give(p, _circle(**_WINNER))
        with_it = _run(p)

        assert with_it.total_count == without.total_count
        assert with_it.valid_count == without.valid_count
        assert with_it.invalid_count == without.invalid_count
        assert with_it.inadmissible_count == without.inadmissible_count
        assert with_it.analysed_count == without.analysed_count

    def test_the_population_identity_still_holds(self):
        p = _project()
        _give(p, _circle(**_WINNER))
        result = _run(p)
        expected = ((_GRID["grid_nx"] + 1) * (_GRID["grid_ny"] + 1)
                    * (_GRID["radius_increment"] + 1))
        assert result.total_count == expected

    def test_evaluations_stays_the_search_alone(self):
        p = _project()
        n = len(_run(p).evaluations)
        _give(p, _circle(**_WINNER))
        after = _run(p)
        assert len(after.evaluations) == n
        assert len(after.all_evaluations()) == n + 1


class TestInertWhenThereAreNone:
    """The guarantee the 190 bank models rest on."""

    def test_a_project_without_them_is_unchanged(self):
        p = _project()
        a, b = _run(p), _run(_project())
        assert a.user_evaluations == [] and b.user_evaluations == []
        assert a.critical.fos == b.critical.fos
        assert a.total_count == b.total_count
        assert a.notes == b.notes

    def test_all_evaluations_is_the_same_list_object(self):
        """No copy where there is nothing to join: this runs per method."""
        result = _run(_project())
        assert result.all_evaluations() is result.evaluations


class TestTheFactoredCopy:
    """The design standard analyses a COPY, and the copy must carry them.

    ``apply_design_factors`` builds it with ``Project.from_dict(
    project.to_dict())``, so a field added to the constructor but not to
    the serialisation would vanish exactly here — silently, and only for
    the users who switched partial factors on.
    """

    def test_the_surface_survives_the_factored_copy(self):
        from ogr_core.project.design_factors import apply_design_factors

        p = _project()
        _give(p, _circle(**_WINNER))
        ds = p.settings.design_standard
        ds.enabled = True
        ds.standard = "custom"
        ds.factor_cohesion = 1.25
        factored, _report = apply_design_factors(p)

        assert factored is not p
        assert len(factored.user_surfaces) == 1
        assert factored.user_surfaces[0].radius == _WINNER["radius"]

    def test_it_still_competes_with_partial_factors_on(self):
        from ogr_slip2d.analysis_runner import run_analysis

        p = _project()
        ds = p.settings.design_standard
        ds.enabled = True
        ds.standard = "custom"
        ds.factor_cohesion = 1.25
        without = run_analysis(p, ["bishop_simplified"])
        _give(p, _circle(**_WINNER))
        with_it = run_analysis(p, ["bishop_simplified"])

        a = without.results["bishop_simplified"]
        b = with_it.results["bishop_simplified"]
        assert len(b.user_evaluations) == 1
        assert b.critical.fos <= a.critical.fos


class TestTheResultsFile:
    """The .h5 export must contain the surface the run reported.

    Before v0.1.157 that was automatic: everything reported came from
    ``evaluations``, which is what the writer walks. Now a user surface can
    BE the critical one, so it has to be written too — in its own group,
    because ``n_surfaces`` is the SEARCH population and is checked against
    the count the reference documents.
    """

    def test_user_surfaces_are_exported_without_moving_the_count(self,
                                                                 tmp_path):
        h5py = _h5py_or_skip()
        if h5py is None:
            return
        from ogr_core.project import save_results

        p = _project()
        _give(p, _circle(**_WINNER))
        result = _run(p)
        out = tmp_path / "r.h5"
        save_results(out, result, project_id="t")

        with h5py.File(out, "r") as f:
            # The search's own group is untouched, name and count.
            assert f.attrs["n_surfaces"] == len(result.evaluations)
            assert len(f["surfaces"]) == len(result.evaluations)
            # And the user's surface is there, in its own group.
            assert f.attrs["n_user_surfaces"] == 1
            assert len(f["user_surfaces"]) == 1
            assert (f["user_surfaces"]["surface_00000"].attrs["radius"]
                    == _WINNER["radius"])

    def test_no_extra_group_when_there_are_none(self, tmp_path):
        """A file from an ordinary run is the file it always was."""
        h5py = _h5py_or_skip()
        if h5py is None:
            return
        from ogr_core.project import save_results

        out = tmp_path / "plain.h5"
        save_results(out, _run(_project()), project_id="t")
        with h5py.File(out, "r") as f:
            assert "user_surfaces" not in f
            assert "n_user_surfaces" not in f.attrs


def _h5py_or_skip():
    try:
        import h5py
    except ImportError:
        return None
    return h5py


class TestTheProjectIsNotModified:
    """A calculation must not change the user's model."""

    def test_the_stored_circle_keeps_its_endpoints_unset(self):
        p = _project()
        circle = _circle(**_WINNER)
        _give(p, circle)
        _run(p)
        assert circle.x_left is None
        assert circle.x_right is None

    def test_the_same_circle_answers_the_same_twice(self):
        """The poison v0.1.131 removed: a second run on the same object."""
        p = _project()
        _give(p, _circle(**_WINNER))
        assert _run(p).critical.fos == _run(p).critical.fos


class TestTheNotes:
    """Said when it happened, and only then."""

    def test_a_user_minimum_is_announced(self):
        p = _project()
        _give(p, _circle(**_WINNER))
        notes = " ".join(_run(p).notes)
        assert "user defined by hand" in notes

    def test_silent_when_the_search_wins(self):
        """A note on every analysis is noise; rule 7 asks the opposite."""
        p = _project()
        # A circle with a HIGHER factor than the search minimum.
        _give(p, _circle(centre_x=30.0, centre_y=32.0, radius=14.0))
        result = _run(p)
        assert not result.is_user_surface(result.critical)
        assert not [n for n in result.notes if "user defined by hand" in n]

    def test_silent_when_there_are_no_user_surfaces(self):
        assert _run(_project()).notes == []

    def test_an_unanalysable_surface_says_so_and_names_itself(self):
        p = _project()
        # Far outside the model: no ground to meet.
        _give(p, _circle(centre_x=500.0, centre_y=500.0, radius=3.0))
        notes = [n for n in _run(p).notes if "produced no result" in n]
        assert len(notes) == 1
        # It names the circle, so the reader does not have to guess which.
        assert "500" in notes[0] and "radius 3" in notes[0]

    def test_a_non_circular_analysis_says_it_skipped_them(self):
        from ogr_core.project.settings import SurfaceType

        p = _project()
        _give(p, _circle(**_WINNER))
        p.settings.search.surface_type = SurfaceType.NON_CIRCULAR.value
        result = _run(p)
        assert result.user_evaluations == []
        assert [n for n in result.notes if "Non-Circular" in n]

    def test_no_note_carries_the_reserved_substrings(self):
        """The verification bank decides D40 by reading the note text.

        Wider than it looks: "unstable" contains "stable" and "ahead"
        contains "head", so the check is on the substrings themselves.
        """
        from ogr_core.project.settings import SurfaceType

        collected = []
        for setup in ("wins", "rejected", "non_circular"):
            p = _project()
            if setup == "wins":
                _give(p, _circle(**_WINNER))
            elif setup == "rejected":
                _give(p, _circle(centre_x=500.0, centre_y=500.0,
                                 radius=3.0))
            else:
                _give(p, _circle(**_WINNER))
                p.settings.search.surface_type = (
                    SurfaceType.NON_CIRCULAR.value)
            collected += list(_run(p).notes)

        assert collected, "no notes were produced, so nothing was checked"
        forbidden = (("stable", "head"), ("edge of the search grid",),
                     ("path_optimize",))
        for note in collected:
            low = note.lower()
            for bits in forbidden:
                assert not all(bit in low for bit in bits), (bits, note)


class TestTheInterface:
    """Reachable, conditioned, and reversible."""

    def _window(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        return MainWindow()

    def test_both_actions_are_reachable_from_the_menu_bar(self):
        w = self._window()
        reachable = set()
        for act in w.menuBar().actions():
            menu = act.menu()
            if menu is None:
                continue
            for sub in menu.actions():
                if sub.text():
                    reachable.add(sub.text())
                if sub.menu():
                    for deep in sub.menu().actions():
                        if deep.text():
                            reachable.add(deep.text())
        for key in ("surf_centre_radius", "surf_manage"):
            assert w._actions[key].text() in reachable

    def test_they_follow_the_surface_type(self):
        from ogr_core.project.settings import SurfaceType

        w = self._window()
        for value, expected in ((SurfaceType.CIRCULAR.value, True),
                                (SurfaceType.NON_CIRCULAR.value, False)):
            w.project.settings.search.surface_type = value
            w.refresh_action_availability()
            for key in ("surf_centre_radius", "surf_manage"):
                assert w._actions[key].isEnabled() is expected

    def test_the_canvas_draws_them(self):
        w = self._window()
        w.canvas.refresh_scene()
        empty = len(w.canvas.scene().items())
        _give(w.project, _circle(centre_x=25.0, centre_y=30.0,
                                 radius=12.0))
        w.canvas.refresh_scene()
        assert len(w.canvas.scene().items()) > empty

    def test_refreshing_with_one_is_no_longer_a_no_op(self):
        """The old action's only visible effect was to CLEAR the canvas."""
        w = self._window()
        _give(w.project, _circle(centre_x=25.0, centre_y=30.0,
                                 radius=12.0))
        w.canvas.refresh_scene()
        with_one = len(w.canvas.scene().items())
        w.project.user_surfaces = []
        w.canvas.refresh_scene()
        assert with_one > len(w.canvas.scene().items())


def _circle(**kwargs):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**kwargs)
