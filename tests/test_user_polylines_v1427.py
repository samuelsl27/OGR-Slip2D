# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.427 (D357, first step) — non-circular slip surfaces the user defines
by hand, kept in the model.

Until this version a hand-made slip surface could only be a circle
(``Project.user_surfaces``): the operations layer refused a polyline, the
window had no tool to draw one, and a polyline could only be priced once
through ``surface_evaluate`` and was forgotten. The non-vertical slice
method of D357 hangs its interface angles and strengths on the vertices of
a surface that stays, so the surface comes first, in its own version.

What is anchored here, in the order the surface travels:

* it SURVIVES the .ogr, and only when there is one: a project without
  polylines writes no key, so its fingerprints (``model_hash`` and
  ``document_hash`` summarise the whole ``to_dict``) are the ones every
  earlier version computed, and a file written before this version loads
  with none. It travels with the design-factored copy, which is made
  through ``to_dict``/``from_dict``, and with an undo step;
* it is a surface or it is refused: drawn right to left it is the same
  surface, kept left to right; a step back in x or a vertical segment is
  refused, because the engine slices in x;
* ONE rule decides that (``checked_points``) and EVERY door asks it: the
  window and ``user_surface_add`` when the surface is made,
  ``surface_evaluate`` for one priced once, and the run for a stored one,
  which is not re-checked when the file is read. ``SlipSurface`` sorts its
  vertices by x, so a door that does not ask prices ANOTHER surface without
  a word: until this version ``surface_evaluate`` did exactly that, and the
  review of this version found the run would have too. A stored surface
  with nothing to slice (a hand-edited file, a script) is refused with its
  note and stops nothing;
* every note names the polyline by its number, its vertices and its ends,
  so two drawn from the same crest to the same toe get two notes; and each
  thing that can happen to one in a run is said, in a REAL run: refused by
  the slicer, removed by a filter, no factor, a factor the checks reject;
* a NON-CIRCULAR run evaluates it, and for every registered method its
  factor of safety is EXACTLY what ``evaluate_surfaces`` gives for the same
  polyline, the other door: an identity, not a captured number (the
  pattern of ``tests/test_user_surfaces_v1157.py``);
* it competes for the global minimum, wins it when its factor is lower,
  and the run says so; the search's own population does not move;
* its ends are put on the External Boundary by the ENGINE before it is
  analysed — the rule ``surface_evaluate`` applied alone until this
  version — and the user's own polyline comes out of the run untouched;
* a CIRCULAR run skips it and says so, as a non-circular run does with the
  circles;
* the operations layer adds and deletes it with the refusals of its type;
* the window: two actions of its own, reachable from the menu bar, greyed
  under the circular type while the circle actions keep theirs; the drawn
  polyline is ONE undo step, and the canvas draws it. A greyed entry says
  why on the status bar (its status tip, D289b). A drawing that is not a
  surface is said so in the user's language and STAYS on the canvas, to be
  corrected; the window refuses one that reaches it under a circular type.

Cost: two runs of the nine methods on a 5-surface Path Search, shared by the
module, about a dozen one-method runs on the same search, an 18-circle grid,
and one window (about 2.5 s together on the development laptop, the GUI
import included).
"""
from __future__ import annotations

import json
import os

#: A polyline on the demo slope (``examples/quick_slope.py``: crest at
#: y = 25 up to x = 25, a 45 degree face down to the toe at (35, 15), flat
#: ground beyond) whose factor is BELOW the small search's minimum for
#: Bishop and Janbu. Its ends are on the ground: (19, 25) on the crest and
#: (37, 15) beyond the toe.
_WINNER = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]

#: ``_WINNER`` with its two middle vertices swapped, so it steps back in x
#: (31 -> 25). Sorted by x it IS ``_WINNER``: a door that sorts instead of
#: asking the rule prices it with ``_WINNER``'s factor, which is measurable.
_ZIG = [(19.0, 25.0), (31.0, 14.5), (25.0, 18.0), (37.0, 15.0)]

#: The smallest circular grid that still runs (18 circles): the test that
#: uses it reads a note, not the population.
_GRID = dict(grid_x=(10, 40), grid_y=(25, 55), grid_nx=1, grid_ny=1,
             radius_increment=0, num_slices=25, min_area=0.5)


def _project(non_circular: bool = True):
    from examples.quick_slope import build_demo_slope
    from ogr_core.project.settings import SurfaceType
    from ogr_slip2d.analysis_runner import method_registry
    p = build_demo_slope()
    if non_circular:
        s = p.settings.search
        s.surface_type = SurfaceType.NON_CIRCULAR.value
        s.search_method = "path"
        s.path_num_surfaces = 5
        p.settings.methods.enabled_methods = sorted(method_registry())
    return p


def _polyline(points=_WINNER):
    from ogr_slip2d.surface import UserPolylineSurface
    return UserPolylineSurface.from_points(points)


# v0.1.427 -- the runs the tests below only READ, computed once: the
# non-circular run without a polyline and with the winning one. File-local
# (tests/test_shared_test_caches_v1378.py fails if another file reaches it).
_SHARED: dict = {}


def _shared_run(state: str):
    """``run_analysis`` of a fresh non-circular demo slope in ``state``:
    "none" or "winner"."""
    if state not in _SHARED:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _project()
        if state == "winner":
            p.user_polylines = [_polyline()]
        _SHARED[state] = (p, run_analysis(p))
    return _SHARED[state]


# ======================================================================
class TestTheSurface:
    """What the model accepts as a non-circular surface."""

    def test_drawn_right_to_left_it_is_kept_left_to_right(self):
        up = _polyline(list(reversed(_WINNER)))
        assert up.points == _WINNER

    def test_a_step_back_or_a_vertical_segment_is_refused(self):
        from ogr_slip2d.surface import UserPolylineSurface
        for pts in ([(0, 5), (5, 0), (3, 4)],        # back in x
                    [(0, 5), (5, 0), (5, 4), (9, 6)],  # vertical
                    [(0, 5)],                          # one point
                    [(0, 5), (float("nan"), 0)]):      # not a number
            try:
                UserPolylineSurface.from_points(pts)
            except ValueError:
                continue
            raise AssertionError(f"{pts} was accepted")

    def test_each_refusal_says_which_rule(self):
        """``NotASurface.kind``: what lets an interface give the TRUE
        reason in its own language."""
        from ogr_core.geometry.user_polyline import NotASurface, checked_points
        cases = {"not_advancing": _ZIG,
                 "too_few": [(0.0, 5.0)],
                 "not_finite": [(0.0, 5.0), (float("inf"), 0.0)],
                 "not_points": [(0.0, 5.0, 1.0), (9.0, 0.0, 1.0)]}
        for kind, pts in cases.items():
            try:
                checked_points(pts)
            except NotASurface as exc:
                assert exc.kind == kind, (kind, exc.kind)
                assert isinstance(exc, ValueError)
                continue
            raise AssertionError(f"{kind}: {pts} was accepted")

    def test_the_engine_surface_is_fresh_every_time(self):
        """The engine writes on the surface it is handed (the tension-crack
        truncation moves its last vertex); the user's must not move."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import slip_surface_of
        up = _polyline()
        a, b = slip_surface_of(up), slip_surface_of(up)
        assert a is not b and a.polyline is not b.polyline
        a.polyline.vertices[-1] = Vertex(37.0, -99.0)   # what the crack does
        assert up.points == _WINNER
        assert [(v.x, v.y) for v in b.polyline.vertices] == _WINNER


# ======================================================================
class TestPersistence:
    """The polyline survives the file, and costs nothing when absent."""

    def test_round_trip_through_the_ogr(self, tmp_path):
        from ogr_core.project import Project
        p = Project(name="round trip")
        p.user_polylines = [_polyline(), _polyline([(0, 3), (2.5, 1.25),
                                                    (4, 3)])]
        ids = [s.id for s in p.user_polylines]
        out = tmp_path / "rt.ogr"
        p.save(out)
        back = Project.load(out)
        assert [s.points for s in back.user_polylines] == [
            _WINNER, [(0.0, 3.0), (2.5, 1.25), (4.0, 3.0)]]
        assert [s.id for s in back.user_polylines] == ids
        # A list of its own: the circles' list did not get them.
        assert back.user_surfaces == []

    def test_no_polyline_writes_no_key_and_moves_no_fingerprint(self):
        """The 19 166 .ogr of the verification bank keep their hashes."""
        from ogr_api.snapshot import document_hash, model_hash
        p = _project()
        assert "user_polylines" not in p.to_dict()
        before = (model_hash(p), document_hash(p))
        p.user_polylines = [_polyline()]
        assert "user_polylines" in p.to_dict()
        assert model_hash(p) != before[0]
        p.user_polylines = []
        assert (model_hash(p), document_hash(p)) == before

    def test_a_file_without_the_key_still_loads(self, tmp_path):
        """Every .ogr written before v0.1.427 is such a file."""
        from ogr_core.project import Project
        out = tmp_path / "old.ogr"
        Project(name="old file").save(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "user_polylines" not in data
        assert Project.load(out).user_polylines == []

    def test_a_stored_surface_is_not_rechecked_on_load(self, tmp_path):
        """A hand-edited file that steps back in x still opens: losing the
        whole model for one surface would be worse. The run refuses it
        (``TestOneRuleForEveryDoor``)."""
        from ogr_core.project import Project
        p = Project(name="hand edited")
        p.user_polylines = [_polyline()]
        out = tmp_path / "edited.ogr"
        p.save(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        data["user_polylines"][0]["points"] = [[0, 5], [5, 0], [3, 4]]
        out.write_text(json.dumps(data), encoding="utf-8")
        assert Project.load(out).user_polylines[0].points == [
            (0.0, 5.0), (5.0, 0.0), (3.0, 4.0)]

    def test_it_travels_with_the_design_copy(self):
        from ogr_core.project import prepare_analysis_project
        p = _project()
        p.user_polylines = [_polyline()]
        p.settings.design_standard.enabled = True
        copy, _rep = prepare_analysis_project(p)
        assert copy is not p
        assert [(s.id, s.points) for s in copy.user_polylines] == [
            (p.user_polylines[0].id, _WINNER)]

    def test_an_undo_step_captures_it(self):
        from ogr_core.project.commands import LIGHT_ATTRS, SnapshotCommand
        p = _project()
        cmd = SnapshotCommand(
            "Add user surface",
            lambda project: project.user_polylines.append(_polyline()),
            attrs=LIGHT_ATTRS)
        cmd.execute(p)
        assert cmd.changed and len(p.user_polylines) == 1
        cmd.undo(p)
        assert p.user_polylines == []


# ======================================================================
class TestTheNonCircularRun:
    """Rule 7: the stored polyline moves the published factor of safety."""

    def test_it_is_evaluated_by_every_method(self):
        _p, none = _shared_run("none")
        _p, winner = _shared_run("winner")
        for mid, r in winner.results.items():
            assert none.results[mid].user_evaluations == [], mid
            assert len(r.user_evaluations) == 1, mid

    def test_each_factor_is_the_one_the_other_door_gives(self):
        """An identity between two paths, for each registered method.

        ``evaluate_surfaces`` is the door ``surface_evaluate`` uses; the run
        and it may change together, never apart.
        """
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import slip_surface_of
        p, winner = _shared_run("winner")
        alone = evaluate_surfaces(p, slip_surface_of(p.user_polylines[0]))
        assert set(alone.results) == set(winner.results)
        for mid, r in winner.results.items():
            ran = r.user_evaluations[0]
            assert alone.results[mid] is not None, mid
            assert ran.is_valid and alone.results[mid].is_valid, mid
            assert ran.fos == alone.results[mid].fos, (mid, ran.fos,
                                                       alone.results[mid].fos)

    def test_it_wins_the_global_minimum_when_lower_and_says_so(self):
        from ogr_slip2d import search_note_messages as SN
        _p, none = _shared_run("none")
        _p, winner = _shared_run("winner")
        won = 0
        for mid, r in winner.results.items():
            searched = none.results[mid].critical
            mine = r.user_evaluations[0]
            said = [n for n in r.notes
                    if getattr(n, "code", None) == SN.USER_PL_REPORTED]
            if mine.fos < searched.fos and getattr(mine, "admissible", True):
                won += 1
                assert r.critical is mine, mid
                assert r.is_user_surface(r.critical), mid
                assert len(said) == 1, (mid, r.notes)
            else:
                assert r.critical.fos == searched.fos, mid
                assert not r.is_user_surface(r.critical), mid
                assert said == [], mid
        # The precondition of the test: the polyline was chosen to beat the
        # search for Bishop and Janbu. If a better search beats it, choose
        # another polyline; the identities above still hold.
        assert won >= 2, won

    def test_the_search_population_does_not_move(self):
        _p, none = _shared_run("none")
        _p, winner = _shared_run("winner")
        for mid, r in winner.results.items():
            n = none.results[mid]
            assert [e.fos for e in r.evaluations] == [
                e.fos for e in n.evaluations], mid
            assert r.total_count == n.total_count, mid

    def test_the_users_polyline_comes_out_untouched(self):
        """In a model where the engine writes on its copy twice: an end off
        the ground is moved onto it, and a tension crack truncates the
        surface at its upper end. The stored points do not move."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_slip2d.analysis_runner import run_analysis
        off = [(19.0, 25.4)] + _WINNER[1:]
        p = _bishop_only()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0.0, 22.0), Vertex(25.0, 22.0)], closed=False),
            btype=BoundaryType.TENSION_CRACK))
        p.user_polylines = [_polyline(off)]
        res = run_analysis(p).results["bishop_simplified"]
        analysed = res.user_evaluations[0].surface.polyline.vertices[0]
        # the engine's copy was truncated at the crack ...
        assert abs(analysed.y - 22.0) < 1e-9, (analysed.x, analysed.y)
        # ... and the user's surface is as it was given
        assert p.user_polylines[0].points == off

    def test_an_end_off_the_ground_is_moved_and_said(self):
        """The engine's rule now, not only ``surface_evaluate``'s: the run
        and the operation give the same factor for the same off-ground end.

        Both through the CONFIGURED search: a search built by hand carries
        the method's own default tolerance, not the project's, and the two
        factors then differ by the convergence (2.4e-4 measured here).
        """
        from ogr_api import Workspace, call
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import run_analysis
        off = [(19.0, 25.4)] + _WINNER[1:]
        p = _project()
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        p.user_polylines = [_polyline(off)]
        res = run_analysis(p).results["bishop_simplified"]
        moved = [n for n in res.notes
                 if getattr(n, "code", None) == SN.USER_PL_END_MOVED]
        assert len(moved) == 1, res.notes
        assert p.user_polylines[0].points == off       # stored as given
        ran = res.user_evaluations[0].fos
        ws = Workspace()
        try:
            pid = ws.add(p).id
            out = call(ws, "surface_evaluate", project_id=pid,
                       surface={"type": "polyline", "points": off},
                       methods=["bishop_simplified"])
            api = out["methods"]["bishop_simplified"]["fos"]
            assert abs(api - ran) <= 2e-6 * abs(ran), (api, ran)
        finally:
            ws.shutdown()

    def test_an_end_that_cannot_be_moved_is_refused_with_its_note(self):
        from ogr_slip2d import BishopSimplified, PathSearch
        from ogr_slip2d import search_note_messages as SN
        # The first end outside the model, left of its side x = 0, and the
        # next vertex at x = -1: the nearest point of the External to the
        # end is (0, 20), past that vertex, so the moved polyline would step
        # back in x — another surface, refused rather than made.
        p = _project()
        p.user_polylines = [_polyline([(-5.0, 20.0), (-1.0, 15.0),
                                       (37.0, 15.0)])]
        res = PathSearch(method=BishopSimplified(), num_surfaces=1,
                         num_slices=p.settings.methods.num_slices).run(p)
        codes = [getattr(n, "code", None) for n in res.notes]
        assert res.user_evaluations == []
        assert SN.USER_PL_SNAP_REFUSED in codes, res.notes


# ======================================================================
def _bishop_only():
    p = _project()
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    return p


def _refused_by(op, spec, **kw):
    """The ``InvalidArgument`` operation ``op`` raises for ``spec``."""
    from ogr_api import InvalidArgument, Workspace, call
    ws = Workspace()
    try:
        pid = ws.add(_bishop_only()).id
        try:
            call(ws, op, project_id=pid, surface=spec, **kw)
        except InvalidArgument as exc:
            return exc
        raise AssertionError(f"{op} accepted {spec}")
    finally:
        ws.shutdown()


class TestOneRuleForEveryDoor:
    """``checked_points`` decides whether a hand-made polyline is a surface,
    and every door that takes one asks it."""

    def test_the_model_refuses_it(self):
        from ogr_core.geometry.user_polyline import checked_points
        for door in (checked_points, _polyline):
            try:
                door(_ZIG)
            except ValueError as exc:
                assert "advance in x" in str(exc), exc
                continue
            raise AssertionError(f"{door} accepted it")

    def test_both_operations_refuse_it(self):
        spec = {"type": "polyline", "points": [list(q) for q in _ZIG]}
        for op, kw in (("user_surface_add", {}),
                       ("surface_evaluate",
                        {"methods": ["bishop_simplified"]})):
            exc = _refused_by(op, spec, **kw)
            assert "advance in x" in str(exc), (op, exc)

    def test_surface_evaluate_names_a_vertical_segment_for_what_it_is(self):
        """Until this version a vertical segment came back as "Moving the
        ends of the polyline onto the External Boundary would make x stop
        increasing": a move nobody had asked for."""
        spec = {"type": "polyline",
                "points": [[19.0, 25.0], [25.0, 18.0], [25.0, 16.0],
                           [37.0, 15.0]]}
        exc = _refused_by("surface_evaluate", spec,
                          methods=["bishop_simplified"])
        assert "advance in x" in str(exc), exc

    def test_surface_evaluate_still_takes_one_right_to_left(self):
        """What did not change: the same surface given from the other end
        is priced the same, bit for bit."""
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = ws.add(_bishop_only()).id
            got = [call(ws, "surface_evaluate", project_id=pid,
                        surface={"type": "polyline",
                                 "points": [list(q) for q in pts]},
                        methods=["bishop_simplified"])
                   ["methods"]["bishop_simplified"]["fos"]
                   for pts in (_WINNER, list(reversed(_WINNER)))]
        finally:
            ws.shutdown()
        assert got[0] is not None and got[0] == got[1], got

    def test_the_run_refuses_a_stored_one_and_says_so(self):
        """Stored without ``from_points`` (a hand-edited file, a script): the
        run does not price it as the sorted surface, ``_WINNER``."""
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.surface import UserPolylineSurface
        p = _bishop_only()
        p.user_polylines = [UserPolylineSurface(points=list(_ZIG))]
        res = run_analysis(p).results["bishop_simplified"]
        assert res.user_evaluations == []
        said = [n for n in res.notes
                if getattr(n, "code", None) == SN.USER_PL_NOT_A_SURFACE]
        assert len(said) == 1, res.notes
        assert p.user_polylines[0].points == _ZIG      # left as stored

    def test_a_stored_one_with_nothing_to_slice_stops_nothing(self):
        """No points, one point, a coordinate that is not a number: each is
        refused with its note, and the good surface beside them is still
        analysed."""
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.surface import UserPolylineSurface
        import numpy as np
        p = _bishop_only()
        p.user_polylines = [
            UserPolylineSurface(points=[]),
            UserPolylineSurface(points=[(19.0, 25.0)]),
            UserPolylineSurface(points=[(19.0, float("nan")),
                                        (37.0, 15.0)]),
            # what only a script can store: a file holding it does not load
            UserPolylineSurface(points=[(x, y, 0.0) for x, y in _WINNER]),
            UserPolylineSurface(points=[None, (37.0, 15.0)]),
            UserPolylineSurface(points=[{"x": 19.0, "y": 25.0},
                                        {"x": 37.0, "y": 15.0}]),
            _polyline()]
        res = run_analysis(p).results["bishop_simplified"]
        said = [n for n in res.notes
                if getattr(n, "code", None) == SN.USER_PL_NOT_A_SURFACE]
        assert len(said) == 6, res.notes
        assert len(res.user_evaluations) == 1
        assert res.user_evaluations[0].is_valid
        # an array is a list of pairs: analysed, with the list's factor
        q = _bishop_only()
        q.user_polylines = [UserPolylineSurface(points=np.array(_WINNER))]
        got = run_analysis(q).results["bishop_simplified"].user_evaluations
        assert len(got) == 1
        assert got[0].fos == res.user_evaluations[0].fos


# ======================================================================
def _notes(res, code):
    return [n for n in res.notes if getattr(n, "code", None) == code]


class TestEveryNoteOfARun:
    """What can happen to a stored polyline in a run, each in a REAL run
    and each said with its code (the samples of test_search_notes_v1349
    only render the sentences)."""

    def _run(self, *polylines, **settings):
        from ogr_slip2d.analysis_runner import run_analysis
        p = _bishop_only()
        for path, value in settings.items():
            obj, attr = path.split("__")
            setattr(getattr(p.settings, obj), attr, value)
        p.user_polylines = [_polyline(pts) for pts in polylines]
        return run_analysis(p).results["bishop_simplified"]

    def test_refused_by_the_slicer_with_its_reason(self):
        from ogr_slip2d import search_note_messages as SN
        # between x = 35 and 36 its base is above the toe ground (y = 15)
        res = self._run([(20.0, 25.0), (26.0, 19.0), (32.0, 15.2),
                         (36.0, 15.0)])
        said = _notes(res, SN.USER_PL_REFUSED)
        assert len(said) == 1 and res.user_evaluations == [], res.notes
        assert "rises above the ground" in str(said[0])

    def test_removed_by_a_filter_names_the_filter(self):
        from ogr_slip2d import search_note_messages as SN
        res = self._run(_WINNER, search__min_depth=12.0)
        said = _notes(res, SN.USER_PL_NO_RESULT_FILTERED)
        assert len(said) == 1 and res.user_evaluations == [], res.notes
        assert "Minimum Depth" in str(said[0])

    def test_no_factor_says_so(self):
        from ogr_slip2d import search_note_messages as SN
        # Bishop iterates on F; one iteration does not converge
        res = self._run(_WINNER, methods__max_iterations=1)
        assert len(res.user_evaluations) == 1
        assert not res.user_evaluations[0].is_valid
        assert len(_notes(res, SN.USER_PL_NO_FACTOR)) == 1, res.notes

    def test_a_factor_the_checks_reject_is_said(self):
        """m-alpha rejects it: F = 0.22 against a published 1.38, which
        would otherwise sit in the population without a word."""
        from ogr_slip2d import search_note_messages as SN
        res = self._run([(19.0, 25.0), (31.0, 8.0), (34.0, 16.0)])
        mine = res.user_evaluations[0]
        assert mine.is_valid and not mine.admissible
        assert res.critical is not mine
        said = _notes(res, SN.USER_PL_INADMISSIBLE)
        assert len(said) == 1, res.notes
        assert "m_alpha" in str(said[0])

    def test_two_with_the_same_ends_get_two_notes(self):
        from ogr_slip2d import search_note_messages as SN
        other = [(19.0, 25.0), (24.0, 17.0), (31.0, 14.0), (37.0, 15.0)]
        res = self._run(_WINNER, other, search__min_depth=12.0)
        said = _notes(res, SN.USER_PL_NO_RESULT_FILTERED)
        assert len(said) == 2, res.notes
        assert "surface 1 (" in str(said[0]) and "surface 2 (" in str(said[1])

    def test_circles_and_polylines_each_by_their_own_type(self):
        """Both lists full, as after the user switches the type: each run
        analyses its own kind and says it skipped the other."""
        from ogr_core.project.settings import SurfaceType
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.surface import SlipCircle
        p = _bishop_only()
        p.user_polylines = [_polyline()]
        p.user_surfaces = [SlipCircle(centre_x=39.0, centre_y=32.0,
                                      radius=17.4)]
        res = run_analysis(p).results["bishop_simplified"]
        assert [type(r.surface).__name__ for r in res.user_evaluations] == [
            "SlipSurface"]
        assert len(_notes(res, SN.USER_CIRCULAR_SKIPPED)) == 1
        p.settings.search.surface_type = SurfaceType.CIRCULAR.value
        p.settings.search.search_method = "grid"
        res = run_analysis(p).results["bishop_simplified"]
        assert [type(r.surface).__name__ for r in res.user_evaluations] == [
            "SlipCircle"]
        assert len(_notes(res, SN.USER_PL_SKIPPED)) == 1


# ======================================================================
class TestTheCircularRun:

    def test_it_skips_the_polylines_and_says_so(self):
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d import search_note_messages as SN
        p = _project(non_circular=False)
        p.user_polylines = [_polyline(), _polyline()]
        res = GridSearch(method=BishopSimplified(), **_GRID).run(p)
        assert res.user_evaluations == []
        skipped = [n for n in res.notes
                   if getattr(n, "code", None) == SN.USER_PL_SKIPPED]
        assert len(skipped) == 1, res.notes
        assert "2 user-defined non-circular surfaces" in str(skipped[0])


# ======================================================================
class TestTheOperations:
    """``user_surface_add`` / ``user_surface_delete`` take the polylines."""

    def _ws(self, surface_type="non_circular"):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="polylines")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [50, 0], [50, 15], [35, 15], [25, 25],
                         [0, 25]],
            "materials": [{"name": "Soil", "unit_weight": 19.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 10.0,
                                                   "friction_angle": 25.0}}}],
            "settings": {"search.surface_type": surface_type,
                         "search.search_method": (
                             "path" if surface_type == "non_circular"
                             else "grid")}})
        return ws, pid

    def test_add_and_delete(self):
        from ogr_api import call
        ws, pid = self._ws()
        try:
            out = call(ws, "user_surface_add", project_id=pid,
                       surface={"type": "polyline",
                                "points": [list(p) for p in
                                           reversed(_WINNER)]})
            assert out["count"] == 1
            project = ws.get(pid).project
            assert project.user_polylines[0].points == _WINNER
            assert out["surface"]["id"] == project.user_polylines[0].id
            call(ws, "user_surface_delete", project_id=pid,
                 surface=out["surface"]["id"])
            assert project.user_polylines == []
        finally:
            ws.shutdown()

    def test_all_deletes_both_kinds(self):
        from ogr_api import call
        from ogr_slip2d.surface import SlipCircle
        ws, pid = self._ws()
        try:
            call(ws, "user_surface_add", project_id=pid,
                 surface={"type": "polyline", "points": _WINNER})
            project = ws.get(pid).project
            project.user_surfaces = [SlipCircle(centre_x=30.0, centre_y=40.0,
                                                radius=20.0)]
            out = call(ws, "user_surface_delete", project_id=pid,
                       surface="all")
            assert out["deleted"] == 2
            assert project.user_polylines == [] and \
                project.user_surfaces == []
        finally:
            ws.shutdown()

    def test_project_get_reads_an_empty_list_not_an_unknown_section(self):
        """The file writes the key only when there is a polyline (the
        fingerprints); the section exists anyway, empty, as its twin
        ``user_surfaces`` does."""
        from ogr_api import call
        ws, pid = self._ws()
        try:
            got = call(ws, "project_get", project_id=pid,
                       section="user_polylines")
            assert got["data"] == []
            call(ws, "user_surface_add", project_id=pid,
                 surface={"type": "polyline", "points": _WINNER})
            got = call(ws, "project_get", project_id=pid,
                       section="user_polylines")
            assert [d["points"] for d in got["data"]] == [
                [list(q) for q in _WINNER]]
            assert "user_polylines" not in json.dumps(_project().to_dict())
        finally:
            ws.shutdown()

    def test_the_refusals(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws, pid = self._ws(surface_type="circular")
        try:
            before = json.dumps(ws.get(pid).project.to_dict(),
                                sort_keys=True, default=str)
            for exc, spec in (
                    (Conflict, {"type": "polyline", "points": _WINNER}),
                    (InvalidArgument, {"type": "polyline",
                                       "points": [[0, 5], [5, 0], [3, 4]]}),
                    (InvalidArgument, {"type": "polyline",
                                       "points": [[0, 5]]})):
                try:
                    call(ws, "user_surface_add", project_id=pid,
                         surface=spec)
                except exc:
                    continue
                raise AssertionError(f"{spec} was not refused")
            after = json.dumps(ws.get(pid).project.to_dict(),
                               sort_keys=True, default=str)
            assert after == before
        finally:
            ws.shutdown()


# ======================================================================
_WINDOWS: list = []


def _window():
    """One window for the file: each one lives until the process ends."""
    if not _WINDOWS:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        _WINDOWS.append(MainWindow())
    w = _WINDOWS[0]
    from ogr_core.project.settings import SurfaceType
    w.project.user_polylines = []
    w.project.user_surfaces = []
    w.project.settings.search.surface_type = SurfaceType.NON_CIRCULAR.value
    w.command_stack.clear()
    w.refresh_action_availability()
    return w


def _drawn(points):
    from ogr_core.geometry import Polyline, Vertex
    return Polyline(vertices=[Vertex(x, y) for x, y in points], closed=False)


class TestTheInterface:
    """Reachable, conditioned, drawn and reversible."""

    def test_both_actions_are_reachable_from_the_menu_bar(self):
        w = _window()
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
        for key in ("surf_polyline_add", "surf_polyline_manage"):
            assert w._actions[key].text() in reachable, key

    def test_they_follow_the_surface_type_opposite_to_the_circles(self):
        from ogr_core.project.settings import SurfaceType
        w = _window()
        for value, circles in ((SurfaceType.CIRCULAR.value, True),
                               (SurfaceType.NON_CIRCULAR.value, False)):
            w.project.settings.search.surface_type = value
            w.refresh_action_availability()
            for key in ("surf_centre_radius", "surf_three_points",
                        "surf_manage"):
                assert w._actions[key].isEnabled() is circles, key
            for key in ("surf_polyline_add", "surf_polyline_manage"):
                assert w._actions[key].isEnabled() is (not circles), key

    def test_a_greyed_entry_says_why_on_the_status_bar(self):
        """Its status tip, which is what D289b's filter shows for a greyed
        menu entry: no menu shows a tooltip."""
        from ogr_core.project.settings import SurfaceType
        w = _window()
        for value, enabled in ((SurfaceType.CIRCULAR.value, False),
                               (SurfaceType.NON_CIRCULAR.value, True)):
            w.project.settings.search.surface_type = value
            w.refresh_action_availability()
            for key in ("surf_polyline_add", "surf_polyline_manage"):
                act = w._actions[key]
                assert act.isEnabled() is enabled, key
                assert bool(act.statusTip()) is (not enabled), key

    def test_the_action_enters_the_draw_mode(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        try:
            w._actions["surf_polyline_add"].trigger()
            assert w.canvas.tool_mode == ToolMode.DRAW_USER_SURFACE
        finally:
            w.canvas.set_tool_mode(ToolMode.SELECT)

    def test_a_drawing_that_is_not_a_surface_stays_to_be_corrected(self):
        """Said in the user's words, with the TRUE reason, and the points
        stay for Undo last vertex: the mode is not left."""
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import tr
        w = _window()
        try:
            for pts, reason in (
                    (_ZIG, "always in the same direction"),
                    ([(19.0, 25.0), (25.0, float("nan")), (37.0, 15.0)],
                     "two finite coordinates")):
                w.canvas.set_tool_mode(ToolMode.DRAW_USER_SURFACE)
                w.canvas._draw_points = list(pts)
                w.canvas._finish_drawing()
                assert w.canvas.tool_mode == ToolMode.DRAW_USER_SURFACE
                assert len(w.canvas._draw_points) == len(pts)
                assert w.project.user_polylines == []
                said = w.ogr_status.currentMessage()
                assert reason in said, said
                assert tr("Use Undo last vertex (right-click) or press Esc "
                          "to cancel.") in said, said
        finally:
            w.canvas._draw_points = []
            w.canvas.set_tool_mode(ToolMode.SELECT)

    def test_the_canvas_delivers_what_was_clicked(self):
        """``_finish_drawing`` of the mode, without the mouse: the points
        go out on the mode's own signal and the mode is left."""
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        try:
            w.canvas.set_tool_mode(ToolMode.DRAW_USER_SURFACE)
            w.canvas._draw_points = list(reversed(_WINNER))
            w.canvas._finish_drawing()
            assert w.canvas.tool_mode == ToolMode.SELECT
            assert [s.points for s in w.project.user_polylines] == [_WINNER]
        finally:
            w.canvas.set_tool_mode(ToolMode.SELECT)

    def test_a_drawn_polyline_is_one_undo_step(self):
        w = _window()
        w.canvas.user_surface_drawn.emit(_drawn(_WINNER))
        assert len(w.project.user_polylines) == 1
        assert w.command_stack.history() == (["Add user surface"], [])
        w.act_undo()
        assert w.project.user_polylines == []
        w.act_redo()
        assert [s.points for s in w.project.user_polylines] == [_WINNER]

    def test_a_polyline_that_is_not_a_surface_is_refused(self):
        """Called directly, not through the signal: a slot's exception is
        swallowed by Qt, and a handler that crashed would leave the same
        empty model and history behind. The reason is said."""
        w = _window()
        w._on_user_surface_drawn(_drawn([(0, 5), (5, 0), (3, 4)]))
        assert w.project.user_polylines == []
        assert w.command_stack.history() == ([], [])
        said = w.ogr_status.currentMessage()
        assert "always in the same direction" in said, said
        assert "The surface was not added." in said, said

    def test_under_a_circular_type_the_window_refuses_it_too(self):
        """The mode can outlive a change of type (Surface Options, an
        agent): the window then refuses what ``user_surface_add`` refuses,
        with the same reason."""
        from ogr_core.project.settings import SurfaceType
        w = _window()
        w.project.settings.search.surface_type = SurfaceType.CIRCULAR.value
        w._on_user_surface_drawn(_drawn(_WINNER))
        assert w.project.user_polylines == []
        assert w.command_stack.history() == ([], [])
        said = w.ogr_status.currentMessage()
        assert "Surface Type = Non-Circular" in said, said

    def test_the_canvas_draws_them(self):
        from PySide6.QtWidgets import QGraphicsPathItem
        w = _window()

        def paths():
            return sum(isinstance(i, QGraphicsPathItem)
                       for i in w.canvas.scene().items())

        w.canvas.refresh_scene()
        empty = paths()
        w.project.user_polylines = [_polyline()]
        w.canvas.refresh_scene()
        assert paths() == empty + 1
        w.project.user_polylines = []
        w.canvas.refresh_scene()
        assert paths() == empty

    def test_a_hand_edited_one_stops_neither_the_canvas_nor_the_manager(
            self):
        from PySide6.QtWidgets import QGraphicsPathItem, QInputDialog
        from ogr_slip2d.surface import UserPolylineSurface
        w = _window()

        def paths():
            return sum(isinstance(i, QGraphicsPathItem)
                       for i in w.canvas.scene().items())

        w.canvas.refresh_scene()
        empty = paths()
        w.project.user_polylines = [
            UserPolylineSurface(points=[]),
            UserPolylineSurface(points=[(19.0, float("nan")), (37.0, 15.0)]),
            UserPolylineSurface(points=list(_ZIG))]   # drawn as given
        # What a hand-edited FILE can hold. A point that is not a pair (only
        # a script can store one) breaks the snapshot every window step
        # takes, as garbage in any list of the model does since before this
        # version, and is not written to a file the loader could not read
        # back; the run refuses it by name (TestOneRuleForEveryDoor).
        w.canvas.refresh_scene()
        assert paths() == empty + 1
        listed = []
        raw = QInputDialog.__dict__.get("getItem")
        try:
            QInputDialog.getItem = staticmethod(
                lambda _parent, _title, _label, items, *a, **k:
                (listed.extend(items), ("", False))[1])
            w._manage_user_polylines()
        finally:
            if raw is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw
        assert len(listed) == 4                     # three and "delete all"
        w.project.user_polylines = []

    def test_the_manager_deletes_one_or_all(self):
        """The one chosen, not the first: two polylines with the same ends
        and the same number of vertices, and the SECOND one picked. Each
        deletion is one undo step."""
        from PySide6.QtWidgets import QInputDialog
        from ogr_gui.i18n import tr
        w = _window()
        twin = [(19.0, 25.0), (24.0, 17.0), (31.0, 14.0), (37.0, 15.0)]
        w.project.user_polylines = [_polyline(), _polyline(twin)]
        keep = w.project.user_polylines[0].id
        raw = QInputDialog.__dict__.get("getItem")
        try:
            QInputDialog.getItem = staticmethod(
                lambda _parent, _title, _label, items, *a, **k:
                (items[1], True))
            w._manage_user_polylines()
            assert [s.id for s in w.project.user_polylines] == [keep]
            assert w.command_stack.history() == (["Delete user surfaces"],
                                                 [])
            w.act_undo()
            assert [s.points for s in w.project.user_polylines] == [
                _WINNER, twin]
            QInputDialog.getItem = staticmethod(
                lambda *a, **k: (tr("(delete all)"), True))
            w._manage_user_polylines()
            assert w.project.user_polylines == []
        finally:
            if raw is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw
