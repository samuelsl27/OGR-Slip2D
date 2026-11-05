# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.428 (D396) — the back analysis covers every admissible surface the run
analyses, the ones the user drew by hand included.

The invariant: the support force a back analysis publishes is the largest
that any ADMISSIBLE surface of the run needs, the user's surfaces included.
That is the reference's own definition of the back analysis (the maximum
support force over all the slip surfaces analysed, paraphrased). Until this
version only the search population was read, so with a hand-drawn surface
critical the force of ANOTHER surface was published, on the unsafe side:
190.99 kN/m where the user's polyline needs 259.02 (demo slope, Janbu,
target 1.5, elevation 20), and 145.99 where a user circle needs 166.33.

What is anchored here:

* the identity with the definition: the published force is the maximum
  re-derived surface by surface over ``all_evaluations_of(run)``, under the
  same rule (valid, sliced, admissible, a circle for Bishop);
* on the governing user surface, the two closed forms of the back analysis,
  measured UNCLIPPED (``required_force`` reports a negative force as 0, and a
  polyline of F = 1.12 needs none at a target of 1.0, so the published values
  would compare zeros): the force is zero at the surface's own factor,
  re-solved to 1e-12, to 1e-9 of its weight (D210's identity and tolerance),
  and the active and the passive force are equal at a target of 1.0;
* whose surface governs is said (a note, and ``user_defined`` in the API),
  and its geometry reaches the API, which gave ``{"type": "dict"}`` before;
* an inadmissible surface never governs while an admissible one is there,
  the owner's rule for every surface, and the note says so only when it
  would have. When the checks reject EVERY surface, the one needing the most
  among them governs and that is said, as ``SearchResult.critical`` falls
  back too: 0.1.427 published a force there, and the review of 0.1.428 found
  that the first version of the rule published NaN instead. Measured in the
  version's step 0: no bench model nor any pinned test has an inadmissible
  surface today (the bench's 037: 3097 surfaces, none), so the rule moves
  nothing;
* Bishop leaves out, and says, every surface that is not a circle, the
  user's included, instead of counting it as analysed and answering "no
  surface could be back-analysed" without the reason; the window's box and
  Interpret say that reason too;
* the tolerant accessor: the very list without user surfaces, and the
  ``SimpleNamespace`` doubles that only have ``evaluations``;
* the window shows the three new notes.

Cost: a Path Search of five surfaces and a 64-circle grid, each run a few
times; about a second in all.
"""
from __future__ import annotations

import copy
import math
import os
from contextlib import contextmanager
from types import SimpleNamespace

_WINNER = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
_TARGET, _ELEVATION = 1.5, 20.0


def _polyline_project(method="janbu_simplified", with_polyline=True):
    from examples.quick_slope import build_demo_slope
    from ogr_core.project.settings import SurfaceType
    from ogr_slip2d.surface import UserPolylineSurface
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type = SurfaceType.NON_CIRCULAR.value
    s.search_method = "path"
    s.path_num_surfaces = 5
    s.optimize_enabled = False
    p.settings.methods.enabled_methods = [method]
    ba = p.settings.back_analysis
    ba.method_id, ba.target_fos, ba.elevation = method, _TARGET, _ELEVATION
    if with_polyline:
        p.user_polylines = [UserPolylineSurface.from_points(_WINNER)]
    return p


def _circle_project(with_circle=True):
    """The reviewer's case of 0.1.427: a 64-circle grid on the demo slope
    and a user circle that needs more force than any of the grid's."""
    from examples.quick_slope import build_demo_slope
    from ogr_slip2d.surface import SlipCircle
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "circular", "grid"
    s.grid_x_min, s.grid_x_max = 30.0, 45.0
    s.grid_y_min, s.grid_y_max = 40.0, 55.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    p.settings.methods.enabled_methods = ["janbu_simplified"]
    ba = p.settings.back_analysis
    ba.method_id, ba.target_fos, ba.elevation = (
        "janbu_simplified", _TARGET, _ELEVATION)
    if with_circle:
        p.user_surfaces = [SlipCircle(centre_x=36.0, centre_y=34.0,
                                      radius=20.0)]
    return p


def _rederived(project):
    """``(force, evaluation, is_user)`` of the surface needing the most
    force, re-derived surface by surface through the configured search.

    From the definition itself, the search's surfaces and the user's, and
    not through the version's own accessor: on the tree before it the
    identity must fail by what it computes, not by a missing name."""
    from ogr_core.project import prepare_analysis_project
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.back_analysis import required_force
    from ogr_slip2d.surface import SlipCircle
    cfg = project.settings.back_analysis
    factored, _ = prepare_analysis_project(project)
    run = build_search(factored, cfg.method_id).run(factored)
    users = list(run.user_evaluations)

    def is_user_surface_of(_run, ev):
        return any(r is ev for r in users)

    best = None
    for ev in list(run.evaluations) + users:
        if not ev.is_valid or not ev.slices:
            continue
        if not getattr(ev, "admissible", True):
            continue
        if (cfg.method_id == "bishop_simplified"
                and not isinstance(ev.surface, SlipCircle)):
            continue
        r = required_force(ev.slices, ev.surface, cfg.target_fos,
                           cfg.method_id, cfg.elevation, project=factored)
        if r is None or not math.isfinite(r.governing_force):
            continue
        if best is None or r.governing_force > best[0]:
            best = (r.governing_force, ev, is_user_surface_of(run, ev))
    return best, run, factored


# v0.1.428 -- the runs these tests only read, computed once. File-local
# (tests/test_shared_test_caches_v1378.py fails if another file reaches it).
_SHARED: dict = {}


def _back(name):
    if name not in _SHARED:
        from ogr_slip2d.analysis_runner import run_configured_back_analysis
        project = {"polyline": lambda: _polyline_project(),
                   "polyline_none": lambda: _polyline_project(
                       with_polyline=False),
                   "circle": lambda: _circle_project(),
                   "circle_none": lambda: _circle_project(
                       with_circle=False),
                   "bishop": lambda: _polyline_project(
                       "bishop_simplified")}[name]()
        _SHARED[name] = (project, run_configured_back_analysis(project)[0])
    return _SHARED[name]


# ======================================================================
class TestTheAccessor:

    def test_without_user_surfaces_it_is_the_same_list(self):
        from ogr_slip2d.search import SearchResult, all_evaluations_of
        sr = SearchResult(method_id="bishop_simplified")
        sr.evaluations.append(object())
        assert all_evaluations_of(sr) is sr.evaluations

    def test_with_user_surfaces_the_search_first_then_the_users(self):
        from ogr_slip2d.search import (SearchResult, all_evaluations_of,
                                       is_user_surface_of)
        a, b = object(), object()
        sr = SearchResult(method_id="bishop_simplified")
        sr.evaluations.append(a)
        sr.user_evaluations.append(b)
        assert all_evaluations_of(sr) == [a, b]
        assert is_user_surface_of(sr, b) and not is_user_surface_of(sr, a)

    def test_a_double_with_only_evaluations(self):
        """What three tests and two bench checks build."""
        from ogr_slip2d.search import all_evaluations_of, is_user_surface_of
        a, b = object(), object()
        only = SimpleNamespace(evaluations=[a])
        assert all_evaluations_of(only) is only.evaluations
        assert not is_user_surface_of(only, a)
        both = SimpleNamespace(evaluations=[a], user_evaluations=[b])
        assert all_evaluations_of(both) == [a, b]
        assert is_user_surface_of(both, b)
        assert all_evaluations_of(SimpleNamespace()) == []


# ======================================================================
class TestTheUsersPolylineGoverns:
    """Janbu, a Path Search of five surfaces, and the user's polyline."""

    def test_the_force_is_the_maximum_over_every_admissible_surface(self):
        project, res = _back("polyline")
        best, _run, _f = _rederived(project)
        assert best is not None
        assert res.required_force == best[0], (res.required_force, best[0])
        assert best[2], "the polyline was chosen to need the most force"

    def test_it_is_the_users_and_that_is_said(self):
        from ogr_slip2d import run_messages as RM
        _p, res = _back("polyline")
        assert res.critical.user_defined
        assert res.notes["user_governs"].code == RM.BACK_USER_GOVERNS

    def test_without_it_the_search_governs_with_less(self):
        """The number this version moves, and the one it does not: without
        the polyline the published force is the search's, as before."""
        _p, without = _back("polyline_none")
        _p, res = _back("polyline")
        assert not without.critical.user_defined
        assert "user_governs" not in without.notes
        assert without.required_force < res.required_force
        assert res.surfaces_analysed == without.surfaces_analysed + 1

    def test_the_closed_forms_on_the_governing_surface(self):
        """Unclipped, from the method's own sums, as
        tests/test_back_analysis_loads_v1220.py measures them."""
        from ogr_slip2d.back_analysis import _sums_at_fixed_fos
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.methods import method_registry
        project, _res = _back("polyline")
        best, _run, factored = _rederived(project)
        _f, ev, _u = best
        cfg = project.settings.back_analysis
        method = method_registry()[cfg.method_id]()
        method.tolerance, method.max_iterations = 1e-12, 400
        solved = method.compute_fos(factored, ev.surface, ev.slices)
        assert solved.converged and solved.fos is not None
        own = solved.fos
        weight = sum(slice_forces(s).w_total for s in ev.slices)

        def forces(target):
            r, d, arm = _sums_at_fixed_fos(
                ev.slices, ev.surface, target, 0.0, 0.0, cfg.elevation,
                cfg.method_id, stress_fos=target, project=factored)
            return (d - r / target) / arm, (target * d - r) / arm

        active, passive = forces(own)
        assert abs(active) <= 1e-9 * weight, (active, weight)
        assert abs(passive) <= 1e-9 * weight, (passive, weight)
        active, passive = forces(1.0)
        assert active < 0.0                       # F = 1.12: none needed
        assert abs(active - passive) <= 1e-9 * weight, (active, passive)

    def test_the_api_carries_its_geometry_and_whose_it_is(self):
        from ogr_api.results import back_analysis_summary
        _p, res = _back("polyline")
        surface = back_analysis_summary(res)["critical_surface"]
        assert surface["type"] == "polyline", surface
        assert surface["user_defined"] is True
        got = [tuple(v) for v in surface["vertices"]]
        assert len(got) == len(_WINNER)
        for (x, y), (gx, gy) in zip(_WINNER, got):
            assert abs(gx - x) < 1e-6 and abs(gy - y) < 1e-6, got
        _p, without = _back("polyline_none")
        assert "user_defined" not in back_analysis_summary(without)[
            "critical_surface"]


# ======================================================================
class TestAUserCircleGoverns:
    """The same, with a circle in a circular run."""

    def test_the_force_is_the_maximum_and_it_is_the_users(self):
        project, res = _back("circle")
        best, _run, _f = _rederived(project)
        assert res.required_force == best[0]
        assert best[2] and res.critical.user_defined
        _p, without = _back("circle_none")
        assert without.required_force < res.required_force
        assert not without.critical.user_defined


# ======================================================================
class TestAnInadmissibleSurfaceNeverGoverns:
    """The rule, with the real evaluations of the polyline run: the driver
    gets them through a search that hands back the run it was given, the
    pattern of tests/test_back_analysis_loads_v1220.py."""

    def _drive(self, project, run):
        from ogr_slip2d.back_analysis import run_back_analysis
        cfg = project.settings.back_analysis
        search = SimpleNamespace(run=lambda _p: run, slice_store=None)
        return run_back_analysis(project, search, cfg.target_fos,
                                 cfg.elevation, cfg.method_id)

    def test_one_that_would_have_governed_does_not_and_it_is_said(self):
        from ogr_slip2d import run_messages as RM
        project, _res = _back("polyline")
        _best, run, factored = _rederived(project)
        theirs = _rederived(_polyline_project(with_polyline=False))[0][0]
        mine = copy.copy(run.user_evaluations[0])
        mine.admissible = False
        fake = SimpleNamespace(evaluations=run.evaluations,
                               user_evaluations=[mine])
        res = self._drive(factored, fake)
        assert res.required_force == theirs, (res.required_force, theirs)
        assert not res.critical.user_defined
        note = res.notes["inadmissible_governed"]
        assert note.code == RM.BACK_INADMISSIBLE_GOVERNED
        assert note.args["n"] == 1

    def test_one_that_needed_less_is_not_said(self):
        project, _res = _back("polyline_none")
        _best, run, factored = _rederived(project)
        res = self._drive(factored, SimpleNamespace(
            evaluations=list(run.evaluations)))
        weakest = min((ev for ev in run.evaluations if ev.is_valid),
                      key=lambda ev: -ev.fos)          # the highest factor
        marked = copy.copy(weakest)
        marked.admissible = False
        population = [marked if ev is weakest else ev
                      for ev in run.evaluations]
        again = self._drive(factored, SimpleNamespace(evaluations=population))
        assert again.required_force == res.required_force
        assert "inadmissible_governed" not in again.notes


    def test_when_the_checks_reject_every_surface_the_most_needed_governs(
            self):
        """As ``critical`` falls back to every surface when none is
        admissible, so does the back analysis, and it says so."""
        from ogr_slip2d import run_messages as RM
        project, _res = _back("polyline")
        best, run, factored = _rederived(project)
        everyone = []
        for ev in list(run.evaluations) + list(run.user_evaluations):
            marked = copy.copy(ev)
            marked.admissible = False
            everyone.append(marked)
        user = everyone[len(run.evaluations):]
        res = self._drive(factored, SimpleNamespace(
            evaluations=everyone[:len(run.evaluations)],
            user_evaluations=user))
        assert res.required_force == best[0], (res.required_force, best[0])
        assert res.critical.user_defined
        assert res.notes["all_inadmissible"].code == RM.BACK_ALL_INADMISSIBLE
        assert "inadmissible_governed" not in res.notes
        assert "error" not in res.notes


# ======================================================================
class TestBishopLeavesOutWhatIsNotACircle:

    def test_left_out_said_and_not_counted(self):
        """Every valid surface of the run with slices, the search's and the
        user's polyline: none is a circle."""
        from ogr_core.project import prepare_analysis_project
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.analysis_runner import build_search
        project, res = _back("bishop")
        factored, _ = prepare_analysis_project(project)
        run = build_search(factored, "bishop_simplified").run(factored)
        sliced = [ev for ev in list(run.evaluations)
                  + list(run.user_evaluations) if ev.is_valid and ev.slices]
        assert run.user_evaluations and any(
            ev is run.user_evaluations[0] for ev in sliced)
        assert res.surfaces_analysed == 0
        assert res.critical is None
        note = res.notes["not_circular_skipped"]
        assert note.code == RM.BACK_NOT_CIRCULAR_LEFT_OUT
        assert note.args["n"] == len(sliced), (note.args, len(sliced))
        # the reason, not "check the target factor and the search settings"
        assert res.notes["error"] is note

    def test_interpret_says_the_same_reason(self):
        """Interpret prices the critical surface; with Bishop and a polyline
        it said back analysis is "only available for Bishop"."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QInputDialog
        QApplication.instance() or QApplication([])
        from ogr_gui.core_messages import note_text
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.analysis_runner import run_analysis
        project = _polyline_project("bishop_simplified")
        result = run_analysis(project).results["bishop_simplified"]
        w = InterpretWindow(project, {"bishop_simplified": result}, None)
        said = []
        try:
            with _swap(QInputDialog, "getDouble",
                       staticmethod(lambda *a, **k: (1.5, True))), \
                    _swap(w, "_info", lambda text, *a: said.append(text)):
                w._back_analysis_report()
        finally:
            w.close()
            w.deleteLater()
        assert said == [note_text(RM.run_note(
            RM.BACK_NOT_CIRCULAR_LEFT_OUT, n=1))], said


# ======================================================================
_MISSING = object()


@contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


class TestTheWindowShowsTheNewNotes:

    def _window_run(self, res):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QDialog
        QApplication.instance() or QApplication([])
        import ogr_slip2d.analysis_runner as runner
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w.act_load_demo()
        said = []
        try:
            with _swap(runner, "run_configured_back_analysis",
                       lambda project, **kw: (res, None, [])), \
                    _swap(QDialog, "exec",
                          lambda self: QDialog.DialogCode.Accepted), \
                    _swap(w, "_info", lambda text, *a: said.append(text)):
                w._back_analysis()
            return said, dict(w.last_task_notes)
        finally:
            panel = getattr(w, "_analysis_notes_panel", None)
            if panel is not None:
                panel.close()
            w.project.is_dirty = False
            w.close()
            w.deleteLater()

    def test_with_no_result_the_box_says_the_reason(self):
        from ogr_gui.core_messages import note_text
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.back_analysis import BackAnalysisResult
        why = RM.run_note(RM.BACK_NOT_CIRCULAR_LEFT_OUT, n=6)
        res = BackAnalysisResult(method_id="bishop_simplified",
                                 notes={"not_circular_skipped": why,
                                        "error": why})
        said, _notes = self._window_run(res)
        assert len(said) == 1 and note_text(why) in said[0], said
        assert said[0].count(note_text(why)) == 1, said[0]

    def test_they_reach_the_notes_panel(self):
        """The run is faked: what is under test is that the window reads the
        three keys; the driver that writes them is tested above."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QDialog
        QApplication.instance() or QApplication([])
        import ogr_slip2d.analysis_runner as runner
        from ogr_gui.core_messages import note_line
        from ogr_gui.main_window import MainWindow
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.back_analysis import (BackAnalysisResult,
                                              BackAnalysisSurfaceResult)
        own = {"not_circular_skipped": RM.run_note(
                   RM.BACK_NOT_CIRCULAR_LEFT_OUT, n=3),
               "inadmissible_governed": RM.run_note(
                   RM.BACK_INADMISSIBLE_GOVERNED, n=1),
               "user_governs": RM.run_note(RM.BACK_USER_GOVERNS)}
        res = BackAnalysisResult(
            method_id="janbu_simplified", surfaces_analysed=5,
            critical=BackAnalysisSurfaceResult(
                active_force=10.0, passive_force=12.0, unsupported_fos=1.1,
                user_defined=True),
            notes=dict(own))
        w = MainWindow()
        w.act_load_demo()
        try:
            with _swap(runner, "run_configured_back_analysis",
                       lambda project, **kw: (res, None, [])), \
                    _swap(QDialog, "exec",
                          lambda self: QDialog.DialogCode.Accepted), \
                    _swap(w, "_info", lambda *a: None):
                w._back_analysis()
            notes = w.last_task_notes.get("back_analysis")
            assert notes, w.last_task_notes
            lines = {note_line(n) for _m, ns in notes for n in ns}
            for n in own.values():
                assert note_line(n) in lines, (n, lines)
        finally:
            panel = getattr(w, "_analysis_notes_panel", None)
            if panel is not None:
                panel.close()
            w.project.is_dirty = False
            w.close()
            w.deleteLater()
