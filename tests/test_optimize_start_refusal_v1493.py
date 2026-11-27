# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Optimize says why it could not evaluate its start (v0.1.493, D436).

THE INVARIANT THIS FILE PROTECTS is that a walk which cannot evaluate its
starting surface says the reason the search recorded, by the same rule as
the door of one surface (``evaluate_surfaces``, v0.1.446, D403): the reason
recorded, else the filters active, else the sentence of always. Until this
version every such start was blamed on the slicer ("refused it whole"), a
Minimum Area, a weak layer and a polyline over the ground alike.

WHY THIS IS NOT A SNAPSHOT. Nothing here records a number. The reference of
each case is the OTHER door: what ``evaluate_surfaces`` says of the same
surface, on the same model. Two doors saying different things of one surface
is the defect; the test asks that they say the same reason.

The three cases are the ficha's table: the demo slope's Path Search critical
surface with a Minimum Area of 1e6 (no reason recorded, a filter active); the
joint of ``test_weak_layer_v1121`` with the base-angle ceiling at 10 degrees
(``weak_layer_steep``); and a polyline on the demo slope that rises above the
ground (``base_above_ground``). With the tree of 0.1.492 the three fail. Then
two controls: an evaluation that raises says the sentence of always and does
not read a reason left by an earlier one, and a focus object that removes the
start is named (the owner's decision of 2026-11-27).
"""
from __future__ import annotations

MID = "bishop_simplified"
_CACHE = {}


def _demo_critical():
    """The demo slope set to Path Search, and its critical surface: computed
    once for the file, as the ficha measured it (1.13577)."""
    if "crit" not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        p = _demo_path()
        _CACHE["crit"] = build_search(p, MID).run(p).critical.surface
    return _CACHE["crit"]


def _demo_path():
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    s = p.settings.search
    s.surface_type, s.search_method, s.path_num_surfaces = (
        "non_circular", "path", 20)
    return p


def _joint():
    """The weak-layer joint of ``test_weak_layer_v1121``, 40 slices, with the
    ceiling on the base angle of a weak-layer clip at 10 degrees."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    e = Polyline([Vertex(x, y) for x, y in ((0, 0), (40, 0), (40, 10),
                                           (10, 10))], closed=True)
    p = Project("capa debil")
    p.boundaries.append(Boundary(polyline=e, btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Suelo", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
    junta = Material(name="Junta", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=20.0))
    p.materials.append(junta)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(2, 2), Vertex(30, 10)]),
        btype=BoundaryType.WEAK_LAYER, material_id=junta.id))
    p.settings.advanced.max_base_angle_deg = 10.0
    p.settings.methods.num_slices = 40
    return p


def _polyline(points):
    from ogr_core.geometry import Polyline, Vertex

    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in points], closed=False))


def _both_doors(p, surface):
    """``(what Optimize says, what evaluate_surfaces says)`` of ``surface``."""
    from ogr_slip2d.analysis_runner import (evaluate_surfaces,
                                            run_configured_optimization)
    _b, res, rep, _f, _w = run_configured_optimization(
        p, MID, surface, max_iterations=20)
    assert res is None, "the start was evaluated: the case does not hold"
    given = [str(w) for w in evaluate_surfaces(p, surface, [MID]).warnings
             if str(w).startswith(MID + ": ")]
    assert given, "evaluate_surfaces said nothing of the surface"
    return rep.notes["error"], given[-1][len(MID + ": "):]


def _same_reason(error, given):
    from ogr_slip2d import search_note_messages as SN
    assert error.code == SN.OPT_START_REFUSED_BECAUSE, str(error)
    assert error.args["reason"]["text"] == given, (str(error), given)
    assert "slicer refused it whole" not in str(error)


# ----------------------------------------------------------------------
class TestTheStartSaysTheSameReason:
    def test_a_minimum_area_is_named(self):
        p = _demo_path()
        p.settings.search.min_area = 1e6
        error, given = _both_doors(p, _demo_critical())
        _same_reason(error, given)
        assert "Minimum Area 1e+06" in str(error)

    def test_a_weak_layer_is_named(self):
        sup = _polyline(((2, 2), (16, 1), (30, 10)))
        error, given = _both_doors(_joint(), sup)
        _same_reason(error, given)
        assert "weak layer" in str(error)

    def test_a_base_above_the_ground_says_so(self):
        from ogr_slip2d import search_note_messages as SN
        sup = _polyline(((10, 25), (28, 23), (30, 21), (35, 15)))
        error, given = _both_doors(_demo_path(), sup)
        _same_reason(error, given)
        assert error.args["reason"]["code"] == (SN.REFUSED
                                                + "base_above_ground")


class TestWhatIsNotKnownIsNotInvented:
    def test_an_evaluation_that_raises_says_the_sentence_of_always(self):
        """And a reason an earlier evaluation left on the search is not read
        as this one's."""
        from ogr_slip2d import OptimizeSettings, optimize_surface
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import build_search
        p = _demo_path()
        search = build_search(p, MID)
        search._last_refusal = "weak_layer_steep"

        def boom(project, surface):
            raise RuntimeError("no")

        search.evaluate_surface = boom
        _b, res, rep = optimize_surface(p, search, _demo_critical(),
                                        OptimizeSettings(max_iterations=5))
        assert res is None
        assert rep.notes["error"] == SN.search_note(SN.OPT_START_REFUSED)

    def test_a_focus_object_that_removes_the_start_is_named(self):
        from ogr_slip2d import (FocusKind, FocusObject, OptimizeSettings,
                                optimize_surface)
        from ogr_slip2d import search_note_messages as SN
        from ogr_slip2d.analysis_runner import build_search
        p = _demo_path()
        search = build_search(p, MID)
        search.focus_objects = [FocusObject(kind=FocusKind.POINT,
                                            points=[(-500.0, -500.0)],
                                            tolerance=0.1)]
        _b, res, rep = optimize_surface(p, search, _demo_critical(),
                                        OptimizeSettings(max_iterations=5))
        assert res is None
        error = rep.notes["error"]
        assert error.code == SN.OPT_START_REFUSED_BECAUSE, str(error)
        assert error.args["reason"]["code"] == SN.REFUSED + "outside_focus"
        assert "focus object" in str(error)
