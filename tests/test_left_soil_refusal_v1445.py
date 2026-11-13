# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D420 (v0.1.445) — a circle that leaves the External Boundary between its two
crossings with the ground says so, at every door, and the census counts it
as the reference's −103.

The invariant
-------------
``_candidate_surfaces`` drops a sliding mass that runs outside the External
Boundary (through the floor: ``leaves_soil_region``; through a side: reverse
curvature whose crack would lie outside the model). When NO mass of a circle
is left, the circle

* records why (``_last_refusal``), so the run's note on a hand-drawn circle,
  ``evaluate_surfaces`` and the agent's ``surface_evaluate`` say it, in
  English and in Spanish, and none of them blames a filter, "does not meet
  the ground twice" or "does not cut the model" — the three sentences of
  v0.1.444, all false;
* is counted ONCE as −103 (``SearchResult.leaves_external``), in series and
  in parallel, and the census (``invalid_summary``) and the interpretation
  window's summary list it under that code.

The other drops of the same generator (reverse curvature with the option
off or with no place for the crack, a mass inside the zone of the Tension
Crack boundary) record their own reason and are NOT −103. No factor and no
critical surface moves: the same masses are analysed (``_V1444``).

The census counts the search's POPULATION: the Slope Search's refinement
walk evaluates circles that are not members of it, and what they count
(−103, and the −101 of D263, which had the same defect since v0.1.261) is
put back. The window says "Every surface evaluated successfully." only of a
run that rejected nothing, in its summary and in the filter's "Error code:".

The references (rule 1)
-----------------------
* **Published:** the reference's report of the worked example Ej_1 gives −103
  to 183 of its 4851 circles, for every method (``EJ1`` of
  ``test_m_alpha_screening_v1189``, read off that report). Its grid
  (``test_slide_validation_ej1``) is run here IN PARALLEL, because the count
  has to come back from the workers (D255). The report of Ej_2 gives it to
  287 of 4840 (the header of ``test_slide_validation_ej2_v184``, whose grid
  run this file shares when both are in one process). Those references are
  why this file takes several seconds.
* **Closed form:** on the demo slope (floor y = 0, crest y = 25 up to x = 25,
  toe y = 15 from x = 35) a circle whose lowest point ``cy − R`` is under the
  floor, and whose crossings with the crest and with the toe lie on either
  side of ``cx`` inside the model, leaves the model through its floor.
  Computed here from that geometry, without the program, for every circle the
  grid x 20..35, y 20..30, 7 x 7 x 11 evaluates: 12 of 539.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_m_alpha_screening_v1189 import EJ1  # noqa: E402
from test_slide_validation_ej1 import _GRID, _ej1_project  # noqa: E402

#: Measured with 0.1.444 (7ac4a6b), not by this code: the critical surfaces
#: of the two grids and the composite factor of the circle below. The change
#: drops nothing that was analysed, so none of them may move.
_V1444 = {
    "ej1_ordinary": (0.8495347997998, 84.0, 66.0, 41.501435828443405),
    "demo_bishop": (1.1156330031782293, 35.0, 28.333333333333336,
                    12.833285258113925),
    "composite_bishop": 4.3123,
}

#: The circle of the ficha: it cuts the ground at x = 4.604 and 45.396 and
#: dips to y = -1, under the floor of the demo slope.
_CIRCLE = (25.0, 20.0, 21.0)
#: One of the eleven of Ej_1 whose reverse-curvature crack falls outside the
#: model, at x = 40 - 41.26 < 0 (found by the run of this version).
_SIDE = (40.0, 30.0, 41.26036921299639)
#: The three sentences of 0.1.444, all false of ``_CIRCLE``.
_FALSE = ("Minimum Area", "meet the ground twice", "does not cut the model",
          "Área mínima", "corta dos veces", "no corta el modelo")
#: The −103 of the reference's report of Ej_2, written in the header of
#: ``test_slide_validation_ej2_v184`` (not a constant there).
_EJ2_PUBLISHED_103 = 287
#: The counters the census reads, named here and not imported.
_CENSUS = ("_leaves_external", "_misses_ground", "_outside_slope_limits")

_CACHE: dict = {}


def _spanish(note) -> str:
    from ogr_gui.core_messages import note_text
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        return note_text(note)
    finally:
        set_language(before)


def _inner_code(note) -> str:
    """The code of a note, the method's wrapper taken off."""
    from ogr_core.messages import METHOD_NOTE
    if getattr(note, "code", "") == METHOD_NOTE:
        return note.args["note"]["code"]
    return getattr(note, "code", "")


def _demo(min_area="default", composite=False):
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    s = p.settings.search
    if min_area != "default":
        s.min_area = min_area
    s.composite_surfaces = composite
    s.grid_nx = s.grid_ny = s.radius_increment = 3
    return p


def _circle(c=_CIRCLE):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=c[0], centre_y=c[1], radius=c[2])


def _recording(run):
    """``run()`` with every circle the search evaluates recorded, its result
    and the refusal it left: ``(value, [((cx, cy, r), result, refusal)])``."""
    import ogr_slip2d.search as S
    real = S.BaseSearch.evaluate_circle
    seen = []

    def spy(self, project, circle):
        res = real(self, project, circle)
        seen.append(((circle.centre_x, circle.centre_y, circle.radius), res,
                     getattr(self, "_last_refusal", None)))
        return res

    S.BaseSearch.evaluate_circle = spy
    try:
        return run(), seen
    finally:
        S.BaseSearch.evaluate_circle = real


def _demo_grid():
    """The grid x 20..35, y 20..30, 7 x 7 x 11 of the demo slope, Bishop, in
    series, once for the file."""
    if "demo" not in _CACHE:
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import build_search
        p = build_demo_project()
        s = p.settings.search
        s.grid_x_min, s.grid_x_max, s.grid_y_min, s.grid_y_max = 20, 35, 20, 30
        s.grid_nx = s.grid_ny = 6
        s.radius_increment = 10
        p.settings.advanced.parallel_search = False
        search = build_search(p, "bishop_simplified")
        sr, seen = _recording(lambda: search.run(p))
        _CACHE["demo"] = (sr, seen)
    return _CACHE["demo"]


def _ej1_parallel():
    """The reference grid of Ej_1, Ordinary, with the pool when the machine
    has one, once for the file: ``(result, pool used, workers)``."""
    if "ej1" not in _CACHE:
        import ogr_slip2d.search as S
        from ogr_slip2d.methods import get_method
        p = _ej1_project()
        p.settings.advanced.parallel_search = True
        p.settings.advanced.parallel_cpu_percent = 100
        workers = S._worker_count(p, 4851)
        real = S._parallel_grid_run
        used = []

        def spy(*a, **k):
            out = real(*a, **k)
            used.append(out is not None)
            return out

        S._parallel_grid_run = spy
        try:
            sr = S.GridSearch(method=get_method("ordinary_fellenius")(),
                              **_GRID).run(p)
        finally:
            S._parallel_grid_run = real
        _CACHE["ej1"] = (sr, used, workers)
    return _CACHE["ej1"]


def _wall_grid():
    """D77's wall: 27 circles, none of which cuts the ground (D263)."""
    if "wall" not in _CACHE:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        wall = [(0, 0), (24, 0), (24, 15), (8.4, 15), (8.4, 12), (7.2, 12),
                (7.2, 9), (6, 9), (6, 6), (0, 6)]
        e = Polyline(vertices=[Vertex(x, y) for x, y in wall], closed=True)
        e.ensure_ccw()
        p = Project("wall")
        p.add_boundary(Boundary(polyline=e, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="fill", unit_weight=18.0,
                                strength=MohrCoulomb(cohesion=0,
                                                     friction_angle=34))]
        _CACHE["wall"] = GridSearch(
            method=BishopSimplified(), slope_limits=((0.0, 6.5), (8.4, 24.0)),
            min_radius=0.0, num_slices=12, grid_x=(-24.0, -22.1),
            grid_y=(15.0, 16.8), grid_nx=2, grid_ny=2, radius_increment=2,
            min_area=2.0).run(p)
    return _CACHE["wall"]


def _slope_walk():
    """A Slope Search of the demo slope's shape with its floor at y = 14,
    1 m under the toe, Ordinary, 100 surfaces of 10 slices, in series, once:
    ``(result, population, walk)``, what the circles of each part added to
    the census counters. A circle of the refinement walk is told apart by
    the walk's loop variable (``_it``) in the caller's frame; the premise
    test fails loudly if that ever stops finding one."""
    if "walk" not in _CACHE:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        import ogr_slip2d.search as S
        from ogr_slip2d.analysis_runner import build_search
        shape = [(0, 14), (50, 14), (50, 15), (35, 15), (25, 25), (0, 25)]
        e = Polyline(vertices=[Vertex(x, y) for x, y in shape], closed=True)
        e.ensure_ccw()
        p = Project("walk")
        p.add_boundary(Boundary(polyline=e, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="soil", unit_weight=19.0,
                                strength=MohrCoulomb(cohesion=5,
                                                     friction_angle=30))]
        s = p.settings.search
        s.search_method, s.surface_type = "slope", "circular"
        s.num_surfaces, s.num_slices = 100, 10
        p.settings.advanced.parallel_search = False
        search = build_search(p, "ordinary_fellenius")
        population = dict.fromkeys(_CENSUS, 0)
        walk = dict.fromkeys(_CENSUS, 0)
        real = S.BaseSearch.evaluate_circle

        def spy(self, project, circle):
            before = {c: getattr(self, c, 0) for c in _CENSUS}
            res = real(self, project, circle)
            into = walk if "_it" in sys._getframe(1).f_locals else population
            for c in _CENSUS:
                into[c] += getattr(self, c, 0) - before[c]
            return res

        S.BaseSearch.evaluate_circle = spy
        try:
            sr = search.run(p)
        finally:
            S.BaseSearch.evaluate_circle = real
        _CACHE["walk"] = (sr, population, walk)
    return _CACHE["walk"]


#: The ground of the demo slope: crest, face and toe.
_DEMO_GROUND = ((0.0, 25.0), (25.0, 25.0), (35.0, 15.0), (50.0, 15.0))


def _ground_crossings(c) -> list:
    """The abscissae where the circle ``c`` meets the demo ground, from the
    circle-segment equation."""
    cx, cy, r = c
    out = []
    for (x1, y1), (x2, y2) in zip(_DEMO_GROUND, _DEMO_GROUND[1:]):
        dx, dy = x2 - x1, y2 - y1
        a = dx * dx + dy * dy
        b = 2 * ((x1 - cx) * dx + (y1 - cy) * dy)
        k = (x1 - cx) ** 2 + (y1 - cy) ** 2 - r * r
        disc = b * b - 4 * a * k
        if disc < 0:
            continue
        for t in ((-b - math.sqrt(disc)) / (2 * a),
                  (-b + math.sqrt(disc)) / (2 * a)):
            if 0.0 <= t <= 1.0:
                out.append(x1 + t * dx)
    return out


def _leaves_by_closed_form(c) -> bool:
    """Whether a circle of the demo slope leaves it through the floor, from
    the geometry alone: its lowest point ``(cx, cy - R)`` under y = 0, and a
    crossing with the ground on either side of the centre, so that point is
    on the arc between them."""
    cx, cy, r = c
    xs = _ground_crossings(c)
    return (cy - r < 0.0 and any(x < cx for x in xs)
            and any(x > cx for x in xs))


# ======================================================================
class TestTheReferences:

    def test_ej1_counts_the_published_minus_103(self):
        from ogr_slip2d.interpretation import invalid_summary
        sr, used, workers = _ej1_parallel()
        published = {codes[-103] for _v, _i, codes in EJ1.values()}
        assert published == {183}, published
        assert sr.leaves_external == 183
        assert invalid_summary(sr)["by_code"][-103] == 183
        if workers >= 2:
            # the count came back from the workers (D255)
            assert used == [True], used

    def test_ej2_counts_the_published_minus_103(self):
        from test_slide_validation_ej2_v184 import _grid_search

        from ogr_slip2d.interpretation import invalid_summary
        sr = _grid_search("bishop_simplified")
        assert sr.leaves_external == _EJ2_PUBLISHED_103
        assert invalid_summary(sr)["by_code"][-103] == _EJ2_PUBLISHED_103

    def test_ej1_critical_does_not_move(self):
        sr, _used, _w = _ej1_parallel()
        fos, cx, cy, r = _V1444["ej1_ordinary"]
        c = sr.critical
        assert abs(c.fos - fos) < 1e-9, c.fos
        assert (c.surface.centre_x, c.surface.centre_y) == (cx, cy)
        assert abs(c.surface.radius - r) < 1e-9

    def test_the_closed_form_on_the_demo_grid(self):
        from ogr_slip2d.interpretation import invalid_summary
        sr, seen = _demo_grid()
        assert len(seen) == 539
        closed = {c for c, _r, _w in seen if _leaves_by_closed_form(c)}
        said = {c for c, r, why in seen
                if r is None and why == "leaves_external"}
        assert len(closed) == 12
        assert said == closed
        assert sr.leaves_external == 12
        assert invalid_summary(sr)["by_code"][-103] == 12

    def test_the_demo_critical_does_not_move(self):
        sr, _seen = _demo_grid()
        fos, cx, cy, r = _V1444["demo_bishop"]
        assert abs(sr.critical.fos - fos) < 1e-9, sr.critical.fos
        assert (sr.critical.surface.centre_x,
                sr.critical.surface.centre_y) == (cx, cy)
        assert abs(sr.critical.surface.radius - r) < 1e-9


# ======================================================================
class TestTheThreeDoorsSayIt:

    def _check(self, note):
        en = str(note)
        es = _spanish(note)
        assert "runs outside the External Boundary" in en, en
        assert "-103" in en
        assert "contorno exterior" in es and "-103" in es, es
        for bad in _FALSE:
            assert bad not in en and bad not in es, (bad, en, es)

    def test_the_run_says_it_of_a_hand_drawn_circle(self):
        from ogr_slip2d.analysis_runner import run_analysis
        for min_area in ("default", 0.0):
            p = _demo(min_area=min_area)
            p.user_surfaces = [_circle()]
            out = run_analysis(p, ["bishop_simplified"])
            assert out.results["bishop_simplified"].user_evaluations == []
            mine = [w for w in out.warnings
                    if _inner_code(w).startswith("search.user_")]
            assert [_inner_code(w) for w in mine] == ["search.user_refused"]
            self._check(mine[0])

    def test_evaluate_surfaces_says_it(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        for min_area in ("default", 0.0):
            out = evaluate_surfaces(_demo(min_area=min_area), _circle(),
                                    ["bishop_simplified"])
            assert out.results == {"bishop_simplified": None}
            assert [_inner_code(w) for w in out.warnings] == [
                "search.refused_surface.leaves_external"]
            self._check(out.warnings[0])

    def test_the_agent_hears_it(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            got = call(ws, "surface_evaluate", project_id=pid, surface={
                "type": "circle", "centre_x": _CIRCLE[0],
                "centre_y": _CIRCLE[1], "radius": _CIRCLE[2]},
                methods=["bishop_simplified"])
        finally:
            ws.shutdown()
        assert got["methods"]["bishop_simplified"] is None
        inner = [w["args"]["note"]["code"] for w in got["warning_codes"]]
        assert inner == ["search.refused_surface.leaves_external"]
        text = " ".join(got["notes"])
        assert "runs outside the External Boundary" in text
        for bad in _FALSE:
            assert bad not in text, bad

    def test_a_named_mass_says_it_and_is_counted(self):
        """With its ends already set the circle takes the other branch of
        ``_candidate_surfaces``; the same reason, and one −103."""
        from ogr_core.geometry import ground_surface
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import frozen_evaluation
        p = _demo()
        named = _circle()
        (named.x_left, named.x_right), = named.candidate_chords(
            ground_surface(p.external_boundary()))
        search = build_search(p, "bishop_simplified")
        search._leaves_external = 0
        with frozen_evaluation(search, p, fallback=False):
            assert search.evaluate_surface(p, named) is None
        assert search._last_refusal == "leaves_external"
        assert search._leaves_external == 1

    def test_composite_surfaces_still_price_it(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_demo(composite=True), _circle(),
                                ["bishop_simplified"])
        r = out.results["bishop_simplified"]
        assert r is not None and out.warnings == []
        assert abs(r.fos - _V1444["composite_bishop"]) < 5e-5, r.fos


# ======================================================================
class TestTheSideAndTheOtherDrops:

    def _evaluate(self, p, c):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import frozen_evaluation
        search = build_search(p, "bishop_simplified")
        search._leaves_external = 0
        with frozen_evaluation(search, p, fallback=False):
            res = search.evaluate_surface(p, _circle(c))
        return res, search._last_refusal, search._leaves_external, search

    def test_the_side_exit_is_minus_103_with_its_own_words(self):
        res, why, n, search = self._evaluate(_ej1_project(), _SIDE)
        assert res is None and n == 1
        assert why == "reverse_curvature_side"
        text = str(search.refusal_text())
        assert "leaves through a side of the External Boundary" in text
        assert "-103" in text
        assert "lado del contorno exterior" in _spanish(
            search.refusal_text())

    def test_the_option_off_is_its_own_reason_and_not_counted(self):
        p = _ej1_project()
        p.settings.search.create_tension_crack_reverse_curvature = False
        res, why, n, search = self._evaluate(p, _SIDE)
        assert res is None and n == 0
        assert why == "reverse_curvature_discarded"
        assert "-103" not in str(search.refusal_text())

    def test_the_tension_crack_zone_is_its_own_reason(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _demo()
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, 22), Vertex(27, 22)],
                              closed=False),
            btype=BoundaryType.TENSION_CRACK))
        res, why, n, search = self._evaluate(p, (10.0, 30.0, 5.5))
        assert res is None and n == 0
        assert why == "tension_crack_zone"
        for bad in _FALSE:
            assert bad not in str(search.refusal_text()), bad

    def test_apply_reverse_curvature_still_returns_a_bool(self):
        from ogr_core.geometry import ground_surface
        from ogr_core.geometry.slip_circle import REVERSE_CURVATURE_SIDE
        p = _ej1_project()
        ground = ground_surface(p.external_boundary())
        c = _circle(_SIDE)
        (c.x_left, c.x_right), *_ = c.candidate_chords(ground)
        why: list = []
        assert c.apply_reverse_curvature(ground, reasons=why) is False
        assert why == [REVERSE_CURVATURE_SIDE]
        c2 = _circle(_SIDE)
        (c2.x_left, c2.x_right), *_ = c2.candidate_chords(ground)
        assert c2.apply_reverse_curvature(ground) is False


# ======================================================================
class TestOneAnswerPerCircle:
    """R1 of the plan: the reason and the count only when NO mass is left.

    No circle of the grids measured (Ej_1, Ej_2, the demo slope) has a mass
    that leaves the model beside one that is analysed, so the case is made by
    hand on the reference circle of Ej_2 that defines two masses (the lens
    beyond the toe and the slope failure, ``test_slide_validation_ej2_v184``):
    the lens is ruled out of the soil by a stand-in for the containment rule.
    """

    def _run(self, *, lens_leaves, slope_in_crack=False):
        from test_slide_validation_ej2_v184 import BIG, _ej2_project

        import ogr_slip2d.slicer as SL
        import ogr_slip2d.surface as SU
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        real_ls, real_tc = SU.leaves_soil_region, SL.apply_tension_crack_truncation

        def ls(circle, ext, x_l, x_r):
            if lens_leaves and x_r < 15.0:
                return True
            return real_ls(circle, ext, x_l, x_r)

        def tc(project, surface, ground, x_l, x_r):
            if slope_in_crack and x_l > 10.0:
                return None
            return real_tc(project, surface, ground, x_l, x_r)

        SU.leaves_soil_region, SL.apply_tension_crack_truncation = ls, tc
        try:
            g = GridSearch(method=BishopSimplified(), num_slices=25,
                           min_area=0.0)
            g._leaves_external = 0
            g._last_refusal = None
            res = g.evaluate_circle(_ej2_project(), _circle(BIG))
        finally:
            SU.leaves_soil_region = real_ls
            SL.apply_tension_crack_truncation = real_tc
        return res, g._last_refusal, g._leaves_external

    def test_a_mass_left_answers_for_the_circle(self):
        res, why, n = self._run(lens_leaves=True)
        assert res is not None and res.surface.x_left > 15.0
        assert n == 0
        assert why != "leaves_external"

    def test_leaving_the_model_is_said_before_another_drop(self):
        res, why, n = self._run(lens_leaves=True, slope_in_crack=True)
        assert res is None
        assert (why, n) == ("leaves_external", 1)


# ======================================================================
class TestTheWalkIsNotThePopulation:
    """The Slope Search's refinement walk: a step that fails counts in
    neither ``valid_count`` nor ``invalid_count``, so what it counts is not
    the census's. Measured with this version's first draft: −103 = 79 where
    the population has 10, and −101 = 159 where it has none."""

    def test_the_premise_the_walk_meets_both(self):
        _sr, population, walk = _slope_walk()
        assert walk["_leaves_external"] > 0, walk
        assert walk["_misses_ground"] > 0, walk
        assert population["_leaves_external"] > 0, population

    def test_the_census_is_the_population(self):
        from ogr_slip2d.interpretation import invalid_summary
        sr, population, _walk = _slope_walk()
        assert sr.leaves_external == population["_leaves_external"]
        assert sr.misses_ground == population["_misses_ground"]
        assert sr.outside_slope_limits == population["_outside_slope_limits"]
        assert invalid_summary(sr)["by_code"].get(-103, 0) == population[
            "_leaves_external"]


# ======================================================================
class TestTheCensusAndTheWindow:

    def test_a_run_that_found_nothing_names_them(self):
        from types import SimpleNamespace

        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import _RUN_COUNTERS, GridSearch
        g = GridSearch(method=BishopSimplified())
        for name in _RUN_COUNTERS:
            setattr(g, name, 0)
        note = g._no_valid_surface_note(SimpleNamespace(
            leaves_external=12, total_count=539, evaluations=[]))
        assert ("12 circles that leave the External Boundary between their "
                "crossings with the ground") in str(note), str(note)
        assert "12 círculos que salen del contorno exterior" in _spanish(note)

    def test_the_agent_census_has_the_code_and_lists_none(self):
        """``error_codes`` names -103 and counts the twelve; ``filter`` by
        it lists none, because no surface carries it (counted before
        slicing): the identity of D263 holds with what was counted."""
        from ogr_api.ops.statistics import _search_view
        sr, _seen = _demo_grid()

        def view(name, code=None):
            return _search_view(None, sr, name, None, None, None, None, None,
                                None, code, 1000, None, False)

        got = view("error_codes")
        assert "-103" in got["codes"]
        assert got["by_code"]["-103"] == 12
        assert view("filter", code=-103)["count"] == 0

    def test_every_counted_reason_has_its_spanish(self):
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.interpretation import COUNTED_REJECTIONS
        es = _DICTS["es"]
        for _attrs, _code, why in COUNTED_REJECTIONS:
            assert why in es and es[why] != why, why

    @staticmethod
    def _fake(sr, said=None):
        from types import SimpleNamespace

        from ogr_gui.interpret_window import InterpretWindow as W
        fake = SimpleNamespace(
            search_result=sr, _info=(said.append if said is not None
                                     else None),
            invalid_reason=W.invalid_reason,
            _unevaluated_rejections=W._unevaluated_rejections)
        fake._invalid_reasons = lambda: W._invalid_reasons(fake)
        return fake

    def _summary(self, sr) -> list:
        from ogr_gui.interpret_window import InterpretWindow
        said: list = []
        InterpretWindow._query_invalid_summary(self._fake(sr, said))
        return said

    @staticmethod
    def _bare(total, analysed, **counted):
        """A run with no evaluation to list: ``total`` generated,
        ``analysed`` analysed, and the counters given."""
        from types import SimpleNamespace
        return SimpleNamespace(evaluations=[], total_count=total,
                               analysed_count=analysed, valid_count=analysed,
                               focus_rejected=0, **counted)

    def test_the_window_lists_the_minus_103(self):
        from ogr_gui.i18n import current_language, set_language
        sr, _seen = _demo_grid()
        said, = self._summary(sr)
        lines = said.splitlines()
        assert ("  12 × the circle leaves the External Boundary between its "
                "crossings with the ground") in lines, said
        # what the window lists and what it says is "more" add up to the
        # rejections it announces, summed here from its own lines
        rejected = sr.total_count - sr.analysed_count
        assert lines[0] == "%d surface(s) rejected of %d generated:" % (
            rejected, sr.total_count)
        listed = sum(int(line.split(" × ")[0]) for line in lines
                     if line.startswith("  ") and " × " in line)
        assert lines[-1].startswith("%d more were discarded before slicing"
                                    % (rejected - listed)), said
        before = current_language()
        set_language("es")
        try:
            dicho, = self._summary(sr)
        finally:
            set_language(before)
        assert ("  12 × el círculo sale del contorno exterior entre sus "
                "cortes con el terreno") in dicho.splitlines(), dicho

    def test_the_window_does_not_call_a_wall_of_misses_a_success(self):
        """D77's wall: 27 circles that miss the ground and no evaluation;
        the window said "Every surface evaluated successfully."."""
        sr = _wall_grid()
        assert sr.misses_ground == 27 and not sr.evaluations
        said, = self._summary(sr)
        assert "Every surface evaluated successfully." not in said
        assert ("  27 × the circle does not cut the ground surface twice"
                in said.splitlines()), said

    def test_the_window_says_success_only_of_a_clean_run(self):
        assert self._summary(self._bare(10, 10)) == [
            "Every surface evaluated successfully."]

    def test_the_window_with_nothing_listed(self):
        """Only rejections without an evaluation or a code (reverse
        curvature with the option off, every evaluation valid): no "more"
        with nothing before it, and no second blank line."""
        from ogr_gui.i18n import current_language, set_language
        sr = self._bare(10, 8)
        assert self._summary(sr) == [
            "2 surface(s) rejected of 10 generated:\n\n2 were discarded "
            "before slicing, so they carry no error code and cannot be "
            "displayed."]
        before = current_language()
        set_language("es")
        try:
            dicho, = self._summary(sr)
        finally:
            set_language(before)
        assert dicho.splitlines()[-1] == (
            "2 se descartaron antes del dovelado, así que no llevan código "
            "de error y no se pueden mostrar."), dicho

    def test_the_filter_does_not_call_a_wall_of_misses_a_success(self):
        """The filter's "Error code:" with no reason to filter by."""
        from ogr_gui.interpret_window import InterpretWindow as W
        clean = W._no_reason_text(self._fake(self._bare(10, 10)))
        assert clean == "Every surface evaluated successfully."
        unseen = ("No rejected surface can be displayed: they were "
                  "discarded before slicing.")
        assert W._no_reason_text(self._fake(_wall_grid())) == unseen
        assert W._no_reason_text(self._fake(self._bare(10, 8))) == unseen
