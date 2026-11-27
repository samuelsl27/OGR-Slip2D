# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D403 (v0.1.446) — a note about a refused surface is about that surface, and
the door of one surface names the filter that removed it.

The invariants
--------------
* **The note "no valid surface" is the SEARCH's.** ``run`` takes the
  slicer's counts (``_outside_model``, ``_orphan_material``,
  ``_unsliceable``) before the user's surfaces, so a hand-drawn circle the
  slicer refuses does not join the search's refusals: the note is the same
  word for word with and without it (an identity, A/B on D77's wall, whose
  27 circles miss the ground), and the circle keeps its own note. In
  v0.1.445 the note gained "; 1 that crossed a region with no material" (or
  "; 1 that the slicer refused"), 28 refusals of "27 generated".
* **The door of one surface says why.** ``evaluate_surfaces`` (and the
  agent's ``surface_evaluate`` behind it) gives the reason the search
  recorded; with none recorded and filters active, it names those filters
  with the run's own fragments (``search.given_no_result_filtered``). The
  grazing circle of D346 (radius 5, 0.1 m into the face, ~0.13 m² of mass)
  said "the surface does not cut the model" there while the run named the
  Minimum Area 1 the model never declared; with a Minimum Area of 0 it is
  priced (D369).
  The Slope Limits are never among those filters: when they remove a
  surface they record why. With no External Boundary the default stays.
* **The ceiling of a weak-layer clip records its reason**
  (``weak_layer_steep``): it was said only in the run's note, so the door
  said "does not cut the model" and a hand-drawn polyline's note blamed the
  Minimum Area. On the joint of ``test_weak_layer_v1121`` with a 10 deg
  ceiling (its base is 15.9 deg), both now say it.
* **The door carries what the search noted while evaluating**, as a run
  does: the ceiling's note with its angles (with "automatic cases" it drops
  the clipped case and the unclipped one is the answer, 4.005 for 1.598,
  which the door gave without a word) and the cap on the weak-layer cases.

No number and no filter moves: the user's surfaces are still filtered (the
owner's decision; the reference's help says its surface filters do not
apply to user-defined surfaces). The factors below were measured with
v0.1.445 (dc27320), not by this code, and are here only to show the
surfaces are priced when nothing removes them.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Measured with 0.1.445 (dc27320), not by this code.
_V1445 = {
    # the grazing circle of D346 with a Minimum Area of 0, Bishop
    "grazing_area_zero": 11.84305595821084,
    # the joint of test_weak_layer_v1121 through evaluate_surfaces, 40
    # slices, no ceiling, Bishop
    "joint_40_slices": 1.5983612099990314,
    # the same with "automatic cases" and a 10 deg ceiling: the unclipped
    # case (measured by the adversarial review of 0.1.446, the same in
    # 0.1.445)
    "joint_auto_cases_ceiling": 4.005282776854345,
}

_WALL = [(0, 0), (24, 0), (24, 15), (8.4, 15), (8.4, 12), (7.2, 12),
         (7.2, 9), (6, 9), (6, 6), (0, 6)]

_CACHE: dict = {}


def _inner_code(note) -> str:
    """The code of a note, the method's wrapper taken off."""
    from ogr_core.messages import METHOD_NOTE
    if getattr(note, "code", "") == METHOD_NOTE:
        return note.args["note"]["code"]
    return getattr(note, "code", "")


def _spanish(note) -> str:
    from ogr_gui.core_messages import note_text
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        return note_text(note)
    finally:
        set_language(before)


def _wall(variant: str, with_circle: bool):
    """D77's wall (27 circles, none cuts the ground), its only region in a
    deleted material ("ghost") or sliced into 2 ("2 slices"), and a
    hand-drawn circle the slicer refuses, or none."""
    key = ("wall", variant, with_circle)
    if key not in _CACHE:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        ext = Polyline(vertices=[Vertex(x, y) for x, y in _WALL], closed=True)
        ext.ensure_ccw()
        p = Project("wall")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="fill", unit_weight=18.0,
                                strength=MohrCoulomb(cohesion=0,
                                                     friction_angle=34))]
        if with_circle:
            p.user_surfaces = [SlipCircle(centre_x=10.0, centre_y=10.0,
                                          radius=9.5)]
        slices = 12
        if variant == "ghost":
            p.region_assignments = [{"x": 12.0, "y": 5.0,
                                     "material_id": "ghost"}]
            p.resolve_regions()
        else:
            slices = 2
        _CACHE[key] = GridSearch(
            method=BishopSimplified(), slope_limits=((0.0, 6.5), (8.4, 24.0)),
            min_radius=0.0, num_slices=slices, grid_x=(-24.0, -22.1),
            grid_y=(15.0, 16.8), grid_nx=2, grid_ny=2, radius_increment=2,
            min_area=2.0).run(p)
    return _CACHE[key]


def _grazing():
    """The grazing circle of D346: radius 5, 0.1 m into the face."""
    from ogr_slip2d.surface import SlipCircle
    d, n = 5.0 - 0.1, 1 / math.sqrt(2)
    return SlipCircle(centre_x=30 + d * n, centre_y=20 + d * n, radius=5.0)


def _demo(min_area="default"):
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    if min_area != "default":
        p.settings.search.min_area = min_area
    return p


def _joint(limit, slices=40):
    """The weak-layer model of ``test_weak_layer_v1121`` (its joint at
    5 kPa / 20 deg), with the ceiling on a weak-layer clip's base."""
    from test_weak_layer_v1121 import _project
    p, _m = _project(joint=(5.0, 20.0))
    p.settings.advanced.max_base_angle_deg = limit
    p.settings.methods.num_slices = slices
    return p


def _joint_surface():
    from test_weak_layer_v1121 import _base_below_the_joint
    return _base_below_the_joint()


# ======================================================================
class TestTheNoteIsOfTheSearch:

    def _note(self, r) -> list:
        return [n for n in r.notes if n.startswith("No trial surface")]

    def test_a_refused_circle_of_the_user_is_not_the_searchs(self):
        for variant in ("ghost", "2 slices"):
            without = self._note(_wall(variant, False))
            assert len(without) == 1, (variant, without)
            assert self._note(_wall(variant, True)) == without, variant

    def test_the_premise_the_wall_finds_nothing_and_says_27(self):
        r = _wall("ghost", False)
        # v0.1.495 (D434) -- changed on purpose: the 27 are the -1000
        assert r.total_count == 27 and r.no_valid_radius == 27
        assert r.misses_ground == 0
        assert "(27 generated)" in self._note(r)[0]

    def test_the_circle_keeps_its_own_note(self):
        for variant, words in (("ghost", "region whose material no longer "
                                "exists"),
                               ("2 slices", "the slicer refused it")):
            own = [n for n in _wall(variant, True).notes
                   if "user-defined surface at centre (10, 10)" in n]
            assert len(own) == 1 and words in own[0], (variant, own)


# ======================================================================
class TestTheDoorNamesTheFilter:

    def test_evaluate_surfaces_names_the_default_minimum_area(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_demo(), _grazing(), ["bishop_simplified"])
        assert out.results == {"bishop_simplified": None}
        note, = out.warnings
        assert _inner_code(note) == "search.given_no_result_filtered"
        text = str(note)
        assert ("no reason was recorded; filters active that can remove it: "
                "Minimum Area 1 (the search's default, not a setting of this "
                "model)." in text), text
        assert "does not cut the model" not in text
        es = _spanish(note)
        assert ("filtros activos que pueden quitarla: Área mínima 1 (valor "
                "por defecto de la búsqueda" in es), es

    def test_the_slope_limits_are_not_named(self):
        """They always record why when they remove a surface, so with no
        reason recorded they did not: Slope Limits [0, 60] contain the whole
        demo slope and were named at the door and in the run's note."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces, run_analysis
        p = _demo()
        s = p.settings.search
        s.slope_limit_left, s.slope_limit_right = 0.0, 60.0
        door, = evaluate_surfaces(p, _grazing(), ["bishop_simplified"]).warnings
        assert _inner_code(door) == "search.given_no_result_filtered"
        codes = [f["code"] for f in door.args["note"]["args"]["filters"]]
        assert codes == ["search.filter.min_area_default"], codes
        s.grid_nx = s.grid_ny = s.radius_increment = 3
        p.user_surfaces = [_grazing()]
        run = [w for w in run_analysis(p, ["bishop_simplified"]).warnings
               if _inner_code(w) == "search.user_no_result_filtered"]
        assert len(run) == 1 and "Slope Limits" not in str(run[0]), run

    def test_a_model_without_an_external_boundary_keeps_the_default(self):
        """No surface cuts a model with no External Boundary, and the search
        leaves without a reason: the default is the true sentence, not the
        Minimum Area."""
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipCircle
        p = Project("empty")
        p.materials = [Material(name="soil", unit_weight=18.0,
                                strength=MohrCoulomb(cohesion=5,
                                                     friction_angle=30))]
        out = evaluate_surfaces(p, SlipCircle(centre_x=10.0, centre_y=20.0,
                                              radius=12.0),
                                ["bishop_simplified"], allow_unconfigured=True)
        assert out.results == {"bishop_simplified": None}
        mine = [w for w in out.warnings if str(w).startswith("bishop")]
        assert [_inner_code(w) for w in mine] == [
            "search.refused_surface.default"], [str(w) for w in mine]

    def test_the_door_and_the_run_name_the_same_filters(self):
        """The fragments are the run's own, value for value."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces, run_analysis
        door, = evaluate_surfaces(_demo(), _grazing(),
                                  ["bishop_simplified"]).warnings
        p = _demo()
        s = p.settings.search
        s.grid_nx = s.grid_ny = s.radius_increment = 3
        p.user_surfaces = [_grazing()]
        run = [w for w in run_analysis(p, ["bishop_simplified"]).warnings
               if _inner_code(w) == "search.user_no_result_filtered"]
        assert len(run) == 1, run
        assert (door.args["note"]["args"]["filters"]
                == run[0].args["note"]["args"]["filters"])

    def test_the_agent_hears_it(self):
        from ogr_api import Workspace, call
        c = _grazing()
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            got = call(ws, "surface_evaluate", project_id=pid, surface={
                "type": "circle", "centre_x": c.centre_x,
                "centre_y": c.centre_y, "radius": c.radius},
                methods=["bishop_simplified"])
        finally:
            ws.shutdown()
        assert got["methods"]["bishop_simplified"] is None
        text = " ".join(got["notes"])
        assert "Minimum Area 1 (the search's default" in text, text
        assert "does not cut the model" not in text

    def test_with_no_minimum_area_it_is_priced(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_demo(0.0), _grazing(), ["bishop_simplified"])
        r = out.results["bishop_simplified"]
        assert r is not None and out.warnings == []
        assert abs(r.fos - _V1445["grazing_area_zero"]) < 1e-9, r.fos

    def test_a_recorded_reason_comes_before_the_filters(self):
        """The circle of D420 leaves the External Boundary: it says that,
        with the Minimum Area active, and not the filters."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipCircle
        out = evaluate_surfaces(_demo(), SlipCircle(
            centre_x=25.0, centre_y=20.0, radius=21.0), ["bishop_simplified"])
        assert [_inner_code(w) for w in out.warnings] == [
            "search.refused_surface.leaves_external"]

    def test_no_reason_and_no_filter_keeps_the_default(self):
        from ogr_slip2d.analysis_runner import _given_refusal, build_search
        p = _demo(0.0)
        search = build_search(p, "bishop_simplified")
        assert search._user_surface_filters(p) == []
        search._last_refusal = None
        assert (_given_refusal(search, p).code
                == "search.refused_surface.default")


# ======================================================================
class TestTheCeilingSaysWhy:

    def test_the_premise_the_joint_is_priced_without_the_ceiling(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_joint(90.0), _joint_surface(),
                                ["bishop_simplified"])
        r = out.results["bishop_simplified"]
        assert r is not None
        assert abs(r.fos - _V1445["joint_40_slices"]) < 1e-9, r.fos

    def test_evaluate_surfaces_says_the_ceiling(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_joint(10.0), _joint_surface(),
                                ["bishop_simplified"])
        assert out.results == {"bishop_simplified": None}
        mine = [w for w in out.warnings
                if _inner_code(w).startswith("search.")]
        # the note the run gives, with its angles, and the reason
        assert [_inner_code(w) for w in mine] == [
            "search.weak_layer_steep",
            "search.refused_surface.weak_layer_steep"], [str(w) for w in mine]
        assert "15.9 deg, past the 10 deg ceiling" in str(mine[0]), mine[0]
        for w in mine:
            assert "does not cut the model" not in str(w)
            assert "Minimum Area" not in str(w)
        assert "Ángulo máximo de base en recortes de capa débil" in _spanish(
            mine[1])

    def test_with_automatic_cases_the_door_says_the_clipped_case_fell(self):
        """With "automatic cases" the ceiling drops the clipped case and the
        unclipped one is the answer: the door gave its factor without a word
        (4.005 for the 1.598 of the clipped case), as the run does not."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p = _joint(10.0)
        p.settings.search.weak_layer_handling = "auto_cases"
        out = evaluate_surfaces(p, _joint_surface(), ["bishop_simplified"])
        r = out.results["bishop_simplified"]
        assert r is not None
        assert abs(r.fos - _V1445["joint_auto_cases_ceiling"]) < 1e-9, r.fos
        codes = [_inner_code(w) for w in out.warnings]
        assert "search.weak_layer_steep" in codes, [str(w) for w in out.warnings]

    def test_the_cap_on_the_cases_is_said_at_the_door(self):
        """``weak_layer_variants`` says it through the search's notes: one
        layer, and no case allowed to combine."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p = _joint(90.0)
        s = p.settings.search
        s.weak_layer_handling, s.weak_layer_max_cases_log2 = "auto_cases", 0
        out = evaluate_surfaces(p, _joint_surface(), ["bishop_simplified"])
        assert out.results["bishop_simplified"] is not None
        said = [str(w) for w in out.warnings
                if "automatic case generation" in str(w)]
        assert len(said) == 1 and said[0].startswith("bishop_simplified: "), \
            [str(w) for w in out.warnings]

    def test_the_run_says_it_of_a_hand_drawn_polyline(self):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.analysis_runner import run_analysis
        p = _joint(10.0)
        p.user_polylines = [UserPolylineSurface.from_points(
            [(v.x, v.y) for v in _joint_surface().polyline.vertices])]
        s = p.settings.search
        s.surface_type, s.search_method = "non_circular", "path"
        s.path_num_surfaces = 5
        mine = [str(w) for w in run_analysis(p, ["bishop_simplified"]).warnings
                if "user-defined non-circular surface 1" in str(w)]
        assert len(mine) == 1, mine
        assert ("The search says why: the surface was not analysed: a weak "
                "layer clips it") in mine[0], mine[0]
        assert "Minimum Area" not in mine[0]
