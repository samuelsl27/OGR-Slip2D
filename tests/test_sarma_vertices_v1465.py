# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.465 (D357) — Sarma's data per vertex of a user's non-circular surface.

WHAT THIS VERSION ADDS

``UserPolylineSurface.vertex_data``: the face angle and the face c and φ of
Sarma's method at interior vertices, by coordinates, checked by one rule
(``checked_vertex_data``), written to the file only when there is one, hung
on the engine's surface (``slip_surface_of``) and read by the method
(``SarmaNonVertical.wedges_for``); the API's ``sarma`` block and
``user_surface_edit``; a table in the window and dotted rays on the canvas.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The published problems 4 and 5** of the verification manual (from Hoek
   1987), given as a user's polyline with their data (the interface of the
   4 from its kink to the face at x = 82.85; table 5.2 of the 5): through
   the stored polyline as a run reads it, ``evaluate_surfaces`` and the
   API's ``surface_evaluate``, the published 1.198 and 1.091 at ±1 % and the
   bank's tool at 1e-6, and the factor of ``build_wedges`` with the same
   data to the bit.
2. **Rule 7**: the angle, the c and the φ given at a vertex each move the
   number; and the precedences: a vertex's angle over the policy, a
   vertex's strength over the given one and the materials'.
3. **The file and the copies**: no ``sarma`` key without data (the
   fingerprint does not move); the data survive a polyline drawn right to
   left, the design copy and a crack that keeps the vertex; one the crack
   cuts off is not applied and the run says so.
4. **The design standard**: F_design = F/γ with c and tan φ of the materials
   and of the vertices divided by the same γ (the pattern of v1464; Frank
   et al. 2004, §2.4.7.3).
5. **The API and the window**: ``user_surface_edit`` replaces the data in one
   undo step and refuses a bad datum with its reason; the table writes them
   in one step, the action is in the menu and greyed with a reason without a
   polyline, and the rays are drawn.
6. **What the review of v0.1.465 found**, each pinned: the data travel with
   the surface through the three doors that rebuild it (a weak layer's
   copy, the statistics' seed, Optimize's walk), the same F to the bit; one
   bad row of a hand-edited file costs only itself (the F of the other
   rows, a note naming the polyline, a report and a canvas that do not
   break); a given strength the method cannot take does not stop a run
   with a norm, and one it can is divided on the copy with or without
   Sarma in the list; the threshold of a horizontal face is the method's;
   OK on the table without an edit writes nothing new; the table says the
   rule in the user's language; a datum a crack cuts off is said per
   polyline; and a statistical run says the hand-given strength is fixed.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402


def _up4():
    from ogr_core.geometry.user_polyline import UserPolylineSurface
    return UserPolylineSurface.from_points(
        list(W63._SURFACE4), vertex_data=[
            {"x": W63._KINK4[0], "y": W63._KINK4[1],
             "angle": W63._THETA4}])


def _up5():
    from ogr_core.geometry.user_polyline import UserPolylineSurface
    rows = [{"x": v[0], "y": v[1], "angle": t[0], "c": t[1], "phi": t[2]}
            for v, t in zip(W63._SURFACE5[1:-1], W63._TABLE52)]
    return UserPolylineSurface.from_points(list(W63._SURFACE5),
                                           vertex_data=rows)


def _sarma(project, n=2):
    project.settings.sarma.num_slices = n
    project.settings.sarma.tolerance = 1e-12
    return project


def _door(project, surface):
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    out = evaluate_surfaces(project, surface, ["sarma"])
    return out.results["sarma"], out.warnings


def _stored(project, up, notes=None):
    """The stored polyline as a non-circular run reads it; ``notes``, a
    list, receives the codes of the search's notes."""
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.search import SearchResult
    project.settings.search.surface_type = "non_circular"
    project.user_polylines = [up]
    search = build_search(project, "sarma")
    result = SearchResult(method_id="sarma")
    search._evaluate_user_surfaces(project, result)
    if notes is not None:
        notes.extend(getattr(n, "code", None)
                     for n in getattr(search, "_pending_notes", ()))
    return result.user_evaluations[0]


def _rows5(skip=(), **change):
    """Table 5.2 as rows, without the rows ``skip`` (their indices) and with
    ``change`` on the row of (80, 11)."""
    rows = []
    for i, (a, t) in enumerate(zip(W63._SURFACE5[1:-1], W63._TABLE52)):
        if i in skip:
            continue
        row = {"x": a[0], "y": a[1], "angle": t[0], "c": t[1], "phi": t[2]}
        if a == W63._SURFACE5[5]:
            row.update(change)
        rows.append(row)
    return rows


# ======================================================================
class TestThePublishedCases:

    def test_problem_4(self):
        from ogr_slip2d.surface import slip_surface_of
        for wet in (False, True):
            p, s, angles = W63._problem4(wet)
            want = W63._f(W63._wedges(p, s, vertex_angles=angles))
            p = _sarma(W63._problem4(wet)[0])
            got, _w = _door(p, slip_surface_of(_up4()))
            assert got.fos == want, (wet, got.fos, want)
            assert abs(got.fos / W63._PUBLISHED4[wet] - 1.0) <= 0.01
            assert abs(got.fos - W63._TOOL4[wet]) <= 1e-6
            # stored, the run puts its ends on the ground first (the head
            # (128, 67.6737) is 1e-4 above it), so it is the tool's to 1e-6
            # and not the bits of the unmoved surface
            stored = _stored(_sarma(W63._problem4(wet)[0]), _up4())
            assert abs(stored.fos - W63._TOOL4[wet]) <= 1e-6, (wet,
                                                                stored.fos)

    def test_problem_5(self):
        from ogr_slip2d.surface import slip_surface_of
        p, s, angles, strengths = W63._problem5(1.0)
        want = W63._f(W63._wedges(p, s, vertex_angles=angles,
                                  vertex_strength=strengths))
        p = _sarma(W63._problem5(1.0)[0])
        got, _w = _door(p, slip_surface_of(_up5()))
        assert got.fos == want, (got.fos, want)
        assert abs(got.fos / W63._PUBLISHED5 - 1.0) <= 0.01
        assert abs(got.fos - W63._TOOL5[1.0, "fixed"]) <= 1e-6

    def test_the_api(self):
        from ogr_api import Workspace, call
        p = _sarma(W63._problem4(False)[0])
        want = _door(_sarma(W63._problem4(False)[0]),
                     __import__("ogr_slip2d.surface", fromlist=["x"])
                     .slip_surface_of(_up4()))[0].fos
        ws = Workspace()
        pid = ws.add(p).id
        out = call(ws, "surface_evaluate", project_id=pid, surface={
            "type": "polyline", "points": [list(v) for v in W63._SURFACE4],
            "sarma": [{"x": 108.0, "y": 6.4, "angle": W63._THETA4}]},
            methods=["sarma"])
        got = out["methods"]["sarma"]["fos"]
        assert abs(got - want) <= 1e-6 * want, (got, want)  # 6 decimals


# ======================================================================
class TestEveryDatumMovesTheNumber:

    def test_each_and_the_precedences(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.surface import slip_surface_of
        base = _door(_sarma(W63._problem5(1.0)[0]),
                     slip_surface_of(_up5()))[0]
        v = W63._SURFACE5[5]                    # (80, 11): (114.775, 0, 18)
        rows = [{"x": a[0], "y": a[1], "angle": t[0], "c": t[1],
                 "phi": t[2]}
                for a, t in zip(W63._SURFACE5[1:-1], W63._TABLE52)]
        for key, value in (("angle", 105.0), ("c", 3.0), ("phi", 24.0)):
            changed = [dict(r) for r in rows]
            for r in changed:
                if (r["x"], r["y"]) == v:
                    r[key] = value
            up = UserPolylineSurface.from_points(list(W63._SURFACE5),
                                                 vertex_data=changed)
            got = _door(_sarma(W63._problem5(1.0)[0]),
                        slip_surface_of(up))[0]
            assert abs(got.fos - base.fos) > 1e-6 * base.fos, (key,)
        # the precedences: the vertex's angle over the policy, its strength
        # over a given one (with the policy vertical, the strength given
        # globally and the vertex's own, the face at v takes the vertex's)
        p = _sarma(W63._problem5(1.0)[0])
        p.settings.sarma.slice_angles = "vertical"
        p.settings.sarma.interslice_strength = "given"
        p.settings.sarma.interslice_cohesion = 9.0
        p.settings.sarma.interslice_phi = 9.0
        res = _door(p, slip_surface_of(_up5()))[0]
        face = next(f for f in res.slices.faces
                    if (f.x_base, f.y_base) == v)
        assert face.angle_source == "vertex"
        assert face.strength_source == "vertex"
        assert face.cohesion == 0.0
        assert abs(face.tan_phi - math.tan(math.radians(18.0))) <= 1e-15


# ======================================================================
class TestTheFileAndTheCopies:

    def test_no_key_without_data_and_the_round_trip(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        bare = UserPolylineSurface.from_points(list(W63._SURFACE4))
        assert "sarma" not in bare.to_dict()
        up = _up4()
        back = UserPolylineSurface.from_dict(up.to_dict())
        assert back.vertex_data == up.vertex_data
        # drawn right to left, the same data at the same vertex
        rev = UserPolylineSurface.from_points(
            list(reversed(W63._SURFACE4)), vertex_data=[
                {"x": 108.0, "y": 6.4, "angle": W63._THETA4}])
        assert rev.vertex_data == up.vertex_data

    def test_bad_data_are_refused_with_their_reason(self):
        from ogr_core.geometry.user_polyline import (NotASurface,
                                                     UserPolylineSurface)
        bad = ([{"x": 0.0, "y": 0.0, "angle": 90.0}],           # an end
               [{"x": 108.0, "y": 6.4, "c": 5.0}],               # c alone
               [{"x": 108.0, "y": 6.4, "angle": 0.0}],           # flat
               [{"x": 108.0, "y": 6.4, "c": 1.0, "phi": 95.0}],
               [{"x": 108.0, "y": 6.4, "angle": math.nan}])
        for rows in bad:
            try:
                UserPolylineSurface.from_points(list(W63._SURFACE4),
                                                vertex_data=rows)
            except NotASurface as exc:
                assert exc.kind == "bad_vertex_data"
                continue
            raise AssertionError(rows)
        # the review: each with its reason and its vertex, for the window to
        # say in its words; a bool is no angle, the method's threshold of a
        # horizontal face is the rule's, and anything but rows is no data
        from ogr_slip2d.sarma.angles import upward
        for rows, reason in (
                ([{"x": 1.0, "y": 1.0, "angle": 90.0}], "not_a_vertex"),
                ([{"y": 6.4, "angle": 90.0}], "no_vertex"),
                ([{"x": 108.0, "y": 6.4, "angle": True}], "angle"),
                ([{"x": 108.0, "y": 6.4, "angle": 1e-14}], "angle"),
                ([{"x": 108.0, "y": 6.4, "angle": 180.0 - 1e-14}], "angle"),
                ([{"x": 108.0, "y": 6.4, "c": 5.0}], "pair"),
                ([{"x": 108.0, "y": 6.4, "c": "a", "phi": 20.0}], "strength"),
                ([{"x": 108.0, "y": 6.4, "angle": 80.0},
                  {"x": 108.0, "y": 6.4, "angle": 85.0}], "twice"),
                (5, "not_rows"), ("abc", "not_rows")):
            try:
                UserPolylineSurface.from_points(list(W63._SURFACE4),
                                                vertex_data=rows)
            except NotASurface as exc:
                assert exc.reason == reason, (rows, exc.reason)
                assert exc.where in (None, (108.0, 6.4), (1.0, 1.0))
                continue
            raise AssertionError(rows)
        assert upward(1e-14) is None and upward(1e-10) is not None
        UserPolylineSurface.from_points(list(W63._SURFACE4), vertex_data=[
            {"x": 108.0, "y": 6.4, "angle": 1e-10}])

    def test_the_design_copy_divides_them(self):
        """Frank et al. (2004): c and tan φ of the materials and of the
        vertices divided by the same γ give F/γ."""
        import test_design_factors_categories_v1226 as D
        from ogr_core.project.design_factors import prepare_analysis_project
        from ogr_slip2d.surface import slip_surface_of

        def model():
            p = _sarma(W63._problem5(1.0)[0])
            p.settings.methods.enabled_methods.append("sarma")
            p.user_polylines = [_up5()]
            return p

        def door(project):
            # the surface handed to the door carries the UNdivided data: the
            # door's copy divides them where the method reads them
            return _door(project, slip_surface_of(
                project.user_polylines[0]))[0].fos

        def stored(project):
            work, _rep = prepare_analysis_project(project)
            return _stored(work, work.user_polylines[0]).fos
        base = door(model())
        for f in (door, stored):
            got = f(D._custom(model(), c=1.25, phi=1.25))
            assert abs(got - base / 1.25) <= 5e-9 * base, (f, got, base)
        _work, rep = prepare_analysis_project(D._custom(model(), c=1.25,
                                                        phi=1.25))
        assert any(m.get("vertex") == W63._SURFACE5[1] for m in rep.materials)

    def test_a_vertex_the_crack_cuts_off_is_said(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.surface import slip_surface_of
        pts = ((10, 10), (20, 5), (24, 4.5), (40, 4), (60, 12), (66, 16.8),
               (70, 20))
        p, _s = W63._slope(load=False, crack=True, surface=pts)
        p.settings.sarma.num_slices = 1
        up = UserPolylineSurface.from_points(list(pts), vertex_data=[
            {"x": 40.0, "y": 4.0, "angle": 95.0},
            {"x": 66.0, "y": 16.8, "angle": 100.0}])      # above y = 16
        res, warnings = _door(p, slip_surface_of(up))
        assert res.is_valid
        kept = next(f for f in res.slices.faces if f.x_base == 40.0)
        assert kept.angle_source == "vertex"
        assert any("did not reach it" in str(x) for x in warnings), warnings
        # and per polyline, whichever surface the run reports (the review)
        notes = []
        p, _s = W63._slope(load=False, crack=True, surface=pts)
        p.settings.sarma.num_slices = 1
        _stored(p, up, notes)
        assert "search.user_polyline_sarma_unused" in notes, notes


# ======================================================================
class TestTheDataTravelWithTheSurface:

    def test_the_three_doors_that_rebuild_a_surface(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.probabilistic import _rebuild_surface
        from ogr_slip2d.surface import SlipSurface, slip_surface_of
        from ogr_slip2d.weak_layers import _own_copy
        s = slip_surface_of(_up5())
        want = _door(_sarma(W63._problem5(1.0)[0]), s)[0].fos
        bare = _door(_sarma(W63._problem5(1.0)[0]), slip_surface_of(
            UserPolylineSurface.from_points(list(W63._SURFACE5))))[0].fos
        assert abs(bare - want) > 1e-3 * want          # the data matter here
        for copy in (_own_copy(s), SlipSurface.from_dict(s.to_dict()),
                     _rebuild_surface(s.to_dict())):
            assert copy.vertex_angles == s.vertex_angles
            assert copy.vertex_strength == s.vertex_strength
            got = _door(_sarma(W63._problem5(1.0)[0]), copy)[0].fos
            assert got == want, (type(copy), got, want)
        # without data the dictionary is the one it always was
        plain = slip_surface_of(UserPolylineSurface.from_points(
            list(W63._SURFACE5)))
        assert set(plain.to_dict()) == {"type", "id", "polyline",
                                        "tension_cracks"}

    def test_optimize_carries_them_and_says_what_it_moved(self):
        from ogr_slip2d.analysis_runner import build_search, sarma_notes
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        from ogr_slip2d.surface import slip_surface_of
        p = _sarma(W63._problem5(1.0)[0])
        s = slip_surface_of(_up5())
        best, res, _rep = optimize_surface(p, build_search(p, "sarma"), s,
                                           OptimizeSettings(max_iterations=40))
        assert best.vertex_angles == s.vertex_angles
        moved = {v for _k, v in res.slices.wedge_fields["unused_vertex_data"]}
        kept = {(v.x, v.y) for v in best.polyline.vertices}
        assert moved and not moved & kept
        assert set(s.vertex_angles) - moved <= kept
        assert any(getattr(n, "code", "") ==
                   "method.sarma_vertex_data_unused" for n in sarma_notes(res))


# ======================================================================
class TestABadRowCostsOnlyItself:

    def test_the_run_the_report_and_the_file(self):
        """A hand-edited file with one bad row: the polyline is analysed with
        the other rows (their F to the bit), and the run names it."""
        import test_design_factors_categories_v1226 as D
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_core.project.design_factors import prepare_analysis_project
        from ogr_slip2d.surface import slip_surface_of
        written = UserPolylineSurface.from_points(
            list(W63._SURFACE5), vertex_data=_rows5()).to_dict()
        for r in written["sarma"]:
            if (r["x"], r["y"]) == W63._SURFACE5[5]:
                r["angle"] = "abc"                 # moves F (rule 7 above)
            if (r["x"], r["y"]) == W63._SURFACE5[4]:
                r["c"] = "abc"                     # what the report reads
        back = UserPolylineSurface.from_dict(written)
        want = _door(_sarma(W63._problem5(1.0)[0]), slip_surface_of(
            UserPolylineSurface.from_points(
                list(W63._SURFACE5), vertex_data=_rows5(skip=(3, 4)))))[0]
        full = _door(_sarma(W63._problem5(1.0)[0]),
                     slip_surface_of(_up5()))[0]
        assert abs(want.fos - full.fos) > 1e-6 * full.fos
        notes = []
        got = _stored(_sarma(W63._problem5(1.0)[0]), back, notes)
        assert abs(got.fos - want.fos) <= 1e-6 * want.fos, (got.fos, want.fos)
        assert "search.user_polyline_sarma_refused" in notes, notes
        assert "search.user_polyline_not_a_surface" not in notes
        # the design report takes the good rows and does not break
        p = _sarma(W63._problem5(1.0)[0])
        p.settings.methods.enabled_methods.append("sarma")
        p.user_polylines = [back]
        _work, rep = prepare_analysis_project(D._custom(p, c=1.25, phi=1.25))
        assert any(m.get("vertex") == W63._SURFACE5[1] for m in rep.materials)
        # anything but a list of rows is no data, not a file that won't load
        for junk in (5, "abc", {"x": 1}, [5, None]):
            again = dict(written, sarma=junk)
            assert UserPolylineSurface.from_dict(again).vertex_data == {}


# ======================================================================
class TestTheDesignCopyAndAGivenStrength:

    def test_always_divided_and_never_a_crash(self):
        """The global given strength is divided on the copy whether or not
        Sarma is in the list (a door can run it), and a value the method
        cannot take is Sarma's own refusal, not a crash of every method."""
        import test_design_factors_categories_v1226 as D
        from ogr_core.project.design_factors import prepare_analysis_project

        def model(c, phi):
            p, _s = W63._slope(load=False)
            p.settings.sarma.interslice_strength = "given"
            p.settings.sarma.interslice_cohesion = c
            p.settings.sarma.interslice_phi = phi
            return D._custom(p, c=1.25, phi=1.25)
        work, rep = prepare_analysis_project(model(4.0, 20.0))
        assert "sarma" not in work.settings.methods.enabled_methods
        assert abs(work.settings.sarma.interslice_cohesion - 3.2) <= 1e-12
        want = math.degrees(math.atan(math.tan(math.radians(20.0)) / 1.25))
        assert abs(work.settings.sarma.interslice_phi - want) <= 1e-12
        assert not any(m["name"] == "Sarma" for m in rep.materials)
        for c, phi in ((None, 20.0), ("abc", 20.0), (4.0, None)):
            work, _rep = prepare_analysis_project(model(c, phi))
            assert work.settings.sarma.interslice_cohesion == c


# ======================================================================
class TestTheStatisticsSayIt:

    def test_the_hand_given_strength_is_said_fixed(self):
        from types import SimpleNamespace
        from ogr_slip2d.probabilistic import _sarma_given_note
        from ogr_slip2d.surface import slip_surface_of

        def said(project, methods, surfaces=None):
            res = SimpleNamespace(notes={}, note_lines=[])
            _sarma_given_note(res, project, methods, surfaces)
            return any(getattr(x, "code", None) == "stat.sarma_given_fixed"
                       for x in res.note_lines)
        p = _sarma(W63._problem5(1.0)[0])
        bare = slip_surface_of(__import__(
            "ogr_core.geometry.user_polyline", fromlist=["x"]
        ).UserPolylineSurface.from_points(list(W63._SURFACE5)))
        assert said(p, ["sarma"], [slip_surface_of(_up5())])
        assert not said(p, ["sarma"], [bare])
        assert not said(p, ["bishop"], [slip_surface_of(_up5())])
        p.user_polylines = [_up5()]
        assert said(p, ["sarma"])                       # Overall Slope
        p.user_polylines = []
        assert not said(p, ["sarma"])
        p.settings.sarma.interslice_strength = "given"
        assert said(p, ["sarma"], [bare])


# ======================================================================
class TestTheApiEdit:

    def test_user_surface_edit(self):
        from ogr_api import InvalidArgument, Workspace, call
        p = _sarma(W63._problem4(False)[0])
        p.settings.search.surface_type = "non_circular"
        p.user_polylines = [W63_bare := __import__(
            "ogr_core.geometry.user_polyline", fromlist=["x"]
        ).UserPolylineSurface.from_points(list(W63._SURFACE4))]
        ws = Workspace()
        pid = ws.add(p).id
        out = call(ws, "user_surface_edit", project_id=pid,
                   surface=W63_bare.id,
                   sarma=[{"x": 108.0, "y": 6.4, "angle": 120.0}])
        assert out["vertices"] == 1
        stored = ws.get(pid).project.user_polylines[0]
        assert stored.vertex_data[(108.0, 6.4)]["angle"] == 120.0
        added = call(ws, "user_surface_add", project_id=pid, surface={
            "type": "polyline", "points": [list(v) for v in W63._SURFACE4],
            "sarma": [{"x": 108.0, "y": 6.4, "c": 4.0, "phi": 20.0}]})
        new = next(s for s in ws.get(pid).project.user_polylines
                   if s.id == added["surface"]["id"])
        assert new.vertex_data[(108.0, 6.4)] == {"angle": None, "c": 4.0,
                                                 "phi": 20.0}
        try:
            call(ws, "user_surface_edit", project_id=pid,
                 surface=W63_bare.id, sarma=[{"x": 108.0, "y": 6.4,
                                              "c": 5.0}])
        except InvalidArgument as exc:
            assert "together" in str(exc)
        else:
            raise AssertionError("a lone c was accepted")
        # the review: anything but rows, and a bool for an angle, are refused
        # with the error of a bad argument, at every door that takes them
        for junk in (5, {"x": 1}, [{"x": 108.0, "y": 6.4, "angle": True}]):
            for op, kw in (("user_surface_edit", {"surface": W63_bare.id,
                                                  "sarma": junk}),
                           ("surface_evaluate", {"surface": {
                               "type": "polyline", "sarma": junk,
                               "points": [list(v) for v in W63._SURFACE4]}})):
                try:
                    call(ws, op, project_id=pid, **kw)
                except InvalidArgument:
                    continue
                raise AssertionError((op, junk))
        assert ws.get(pid).project.user_polylines[0].vertex_data[
            (108.0, 6.4)]["angle"] == 120.0


# ======================================================================
_WINDOWS: list = []


def _window():
    if not _WINDOWS:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        _WINDOWS.append(MainWindow())
    w = _WINDOWS[0]
    from ogr_core.project.settings import SurfaceType
    w.project.user_polylines = []
    w.project.settings.search.surface_type = SurfaceType.NON_CIRCULAR.value
    w.command_stack.clear()
    w.refresh_action_availability()
    return w


class TestTheWindow:

    def test_the_action_is_in_the_menu_and_greyed_with_a_reason(self):
        w = _window()
        act = w._actions["surf_polyline_sarma"]
        assert not act.isEnabled() and act.statusTip()
        menu_actions = [a for m in w.menuBar().actions()
                        for a in (m.menu().actions() if m.menu() else [])]
        assert act in menu_actions
        w.project.user_polylines = [_up4()]
        w.refresh_action_availability()
        assert act.isEnabled()
        w.project.user_polylines = []

    def test_the_table_writes_in_one_step_and_the_rays_are_drawn(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QGraphicsPathItem
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_gui.dialogs.sarma_vertex_dialog import SarmaVertexDialog
        w = _window()
        up = UserPolylineSurface.from_points(list(W63._SURFACE4))
        w.project.user_polylines = [up]
        w.refresh_action_availability()
        raw = SarmaVertexDialog.exec

        def fill_and_accept(dlg):
            dlg.table.item(0, 2).setText("116.5")
            dlg._accept()
            return QDialog.DialogCode.Accepted
        SarmaVertexDialog.exec = fill_and_accept
        try:
            w._edit_user_polyline_sarma()
        finally:
            SarmaVertexDialog.exec = raw
        assert up.vertex_data == {(108.0, 6.4): {"angle": 116.5, "c": None,
                                                 "phi": None}}
        assert w.command_stack.history() == (
            ["Edit Sarma data per vertex"], [])
        dotted = [it for it in w.canvas.scene().items()
                  if isinstance(it, QGraphicsPathItem)
                  and it.pen().style() == Qt.PenStyle.DotLine]
        assert dotted
        # a bad value: not accepted, said under the table, nothing written
        dlg = SarmaVertexDialog(up, w.project.settings.units, w)
        dlg.table.item(0, 3).setText("5")
        dlg._accept()
        assert dlg.result_data() is None and dlg.lbl_error.text()
        w.act_undo()
        assert up.vertex_data == {} or w.project.user_polylines[0] \
            .vertex_data == {}
        w.project.user_polylines = []

    def test_ok_without_an_edit_writes_nothing_new(self):
        """Shown with %g and in the user's units, a stored value read back
        would come back rounded or converted (the review of v0.1.465)."""
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_gui.dialogs.sarma_vertex_dialog import SarmaVertexDialog
        w = _window()
        data = [{"x": 108.0, "y": 6.4, "angle": 80.123456789,
                 "c": 1.0 / 3.0, "phi": 20.123456789}]
        up = UserPolylineSurface.from_points(list(W63._SURFACE4),
                                             vertex_data=data)
        dlg = SarmaVertexDialog(up, w.project.settings.units, w)
        assert dlg.table.item(0, 2).text() == "80.1235"
        dlg._accept()
        assert dlg.result_data() == up.vertex_data
        dlg = SarmaVertexDialog(up, w.project.settings.units, w)
        dlg.table.item(0, 2).setText("80.5")
        dlg._accept()
        assert dlg.result_data()[(108.0, 6.4)] == {
            "angle": 80.5, "c": 1.0 / 3.0, "phi": 20.123456789}

    def test_the_rule_is_said_in_the_users_language(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_gui.dialogs.sarma_vertex_dialog import SarmaVertexDialog
        from ogr_gui.i18n import current_language, set_language
        w = _window()
        up = UserPolylineSurface.from_points(list(W63._SURFACE4))
        was = current_language()
        set_language("es")
        try:
            dlg = SarmaVertexDialog(up, w.project.settings.units, w)
            dlg.table.item(0, 3).setText("5")
            dlg._accept()
            assert dlg.lbl_error.text() == (
                "La cohesión y el ángulo de rozamiento de la cara en (108, "
                "6.4) van juntos."), dlg.lbl_error.text()
            dlg.table.item(0, 2).setText("x")
            dlg._accept()
            assert dlg.lbl_error.text() == "Fila 1: «x» no es un número."
        finally:
            set_language(was)

    def test_the_canvas_draws_only_what_the_rule_accepts(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGraphicsPathItem
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        w = _window()
        written = UserPolylineSurface.from_points(
            list(W63._SURFACE5), vertex_data=_rows5()).to_dict()
        for r in written["sarma"]:
            r["angle"] = "abc"
        w.project.user_polylines = [UserPolylineSurface.from_dict(written)]
        w.canvas.refresh()
        dotted = [it for it in w.canvas.scene().items()
                  if isinstance(it, QGraphicsPathItem)
                  and it.pen().style() == Qt.PenStyle.DotLine]
        assert not dotted
        w.project.user_polylines = []
