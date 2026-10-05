# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.259, defects D256 and D257, and the API's end tolerance — what "on
the ground" means is one thing, said once, and a refusal says its own
reason.

Invariants protected:

1. **A base that rises above the ground between the two ends is refused
   with its own reason** (D256). The slicer refuses a surface whose base
   corner is above the ground by more than ``ABOVE_GROUND_REL`` of its
   width, and gave a reason only when that corner was one of the two ends
   (D244). An interior corner fell into the "could not be sliced" count,
   whose note asks for more slices. No slice count cures it: the mass would
   be in the air there. Measured on verification problem 109 before its
   joints were corrected: 4000 of the 5088 surfaces its Block Search formed
   were refused here, and none of 40 could be sliced with 500 slices. Now
   the refusal travels as ``REFUSED_BASE_ABOVE_GROUND``, the search counts
   it apart, the result carries the count to the census of rejected
   surfaces, and the note names the cause. No number moves: the surfaces
   were refused before too.
2. **The API puts on the boundary every end that is not on it** (the
   reference moves an end entered by hand "to the nearest point on the
   External Boundary"). Until v0.1.258 it left alone an end within 1e-6 of
   the model's diagonal measured PERPENDICULAR to the boundary, while the
   slicer judges the VERTICAL offset against 1e-6 of the surface's width.
   On a steep face the vertical is several times the perpendicular, so the
   API could leave an end that the slicer then refused: the optimised
   Bishop polyline of problem 109, archived to four decimals, came back
   "not analysed". An end on the boundary to round-off is still untouched.
3. **The Block Search throws away an object's point above the ground with
   a tolerance relative to the model** (D257). It used to be an absolute
   1e-6 in the model's own units: the same model in metres and in
   millimetres did not keep the same candidates (AGENTS.md: geometric
   tolerances are relative to the size of the model). The switch
   ``ogr_slip2d.search.BLOCK_CHAIN_GUARD_RELATIVE`` gives the absolute one
   back; it is used here to show what the rule changes.

COST. A dozen single-surface evaluations, two API calls and four Block
Searches of 40 candidates. A few seconds.
"""
from __future__ import annotations

import math

_SLICES = 30
#: The slicer's literal reason, written out so that against an engine
#: without it only the behaviour fails, not the import.
_BASE_ABOVE = "base_above_ground"


def _slope(scale=1.0):
    """A 20 m slope: flat toe at y = 10, face to (40, 30), crest at 30
    (the slope of ``test_polyline_endpoints_v1258``), every length times
    ``scale`` and the cohesion with it, so that a millimetre model is the
    metre model with every number of the same meaning."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    pts = [(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (40.0, 30.0), (20.0, 10.0),
           (0.0, 10.0)]
    p = Project("D256")
    ext = Polyline(vertices=[Vertex(x * scale, y * scale) for x, y in pts],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0 * scale,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    p.settings.methods.num_slices = _SLICES
    return p


def _poly(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


#: Ends on the ground: (15, 10) on the toe flat and (48, 30) on the crest.
#: The face is y = x - 10 between x = 20 and 40.
_ON = [(15.0, 10.0), (24.0, 6.0), (34.0, 9.0), (42.0, 18.0), (48.0, 30.0)]
_WIDTH = 48.0 - 15.0


def _bump(dy):
    """``_ON`` with a vertex on the face at x = 30 (where the face is at
    y = 20) lifted ``dy`` above it: the base rises above the ground
    between the two ends."""
    return _ON[:2] + [(30.0, 20.0 + dy)] + _ON[2:]


def _evaluate(p, pts):
    from ogr_slip2d.analysis_runner import build_search
    s = build_search(p, "bishop_simplified")
    return s.evaluate_surface(p, _poly(pts)), s


# ======================================================================
class TestABaseInTheAirSaysWhy:
    """Invariant 1."""

    def test_the_slicer_refuses_it_with_its_reason(self):
        """Fails on v0.1.258: refused with no reason at all."""
        from ogr_slip2d.slicer import slice_surface
        why = []
        assert slice_surface(_slope(), _poly(_bump(0.5)), num_slices=_SLICES,
                             reasons=why) is None
        assert why == [_BASE_ABOVE]

    def test_more_slices_do_not_cure_it(self):
        """The premise of the new note: the old one's remedy is wrong."""
        from ogr_slip2d.slicer import slice_surface
        for n in (_SLICES, 120, 500):
            assert slice_surface(_slope(), _poly(_bump(1e-3)),
                                 num_slices=n) is None, n

    def test_the_search_counts_it_apart_and_says_it(self):
        res, s = _evaluate(_slope(), _bump(1e-3))
        assert res is None
        assert getattr(s, "_base_above_ground", 0) == 1
        assert getattr(s, "_unsliceable", 0) == 0
        assert "rises above the ground" in s.refusal_text()

    def test_the_run_note_names_the_cause_not_the_slice_count(self):
        """Through ``BaseSearch.run``, with a search whose generation step
        is two given surfaces: one in the air between its ends, one fine."""
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.interpretation import ERROR_OTHER, invalid_summary
        from ogr_slip2d.search import SearchResult
        p = _slope()
        s = build_search(p, "bishop_simplified")

        def _run(project):
            r = SearchResult(method_id=s.method.METHOD_ID,
                             objective=s.objective)
            for pts in (_bump(1e-3), _ON):
                r.attempts += 1
                e = s.evaluate_surface(project, _poly(pts))
                if e is None:
                    r.invalid_count += 1
                    continue
                r.evaluations.append(e)
                if e.is_valid:
                    r.valid_count += 1
            return r

        s._run = _run
        out = s.run(p)
        assert getattr(out, "bases_above_ground", 0) == 1
        lines = [n for n in out.notes if "rose above the ground" in n]
        assert len(lines) == 1, out.notes
        assert not any("Use more slices" in n for n in out.notes), out.notes
        census = invalid_summary(out)
        assert census["by_code"].get(ERROR_OTHER) == 1
        assert census["by_reason"].get(
            "the base rises above the ground surface between the ends") == 1

    def test_controls_inside_the_tolerance_and_at_an_end(self):
        """A vertex on the face within ``ABOVE_GROUND_REL`` of the width is
        on the ground, and the slicer slices the surface with no reason; an
        END above the ground keeps the reason it had (D244). The slicer is
        asked and not the solver: what the rule decides is whether the
        surface is sliced (Bishop has no physical root for this shape, which
        touches the face from below)."""
        from ogr_slip2d.slicer import slice_surface
        why = []
        assert slice_surface(_slope(), _poly(_bump(1e-7)), num_slices=_SLICES,
                             reasons=why) is not None
        assert why == []
        why = []
        assert slice_surface(_slope(), _poly([(15.0, 10.5)] + _ON[1:]),
                             num_slices=_SLICES, reasons=why) is None
        assert why == ["end_above_ground"]


# ======================================================================
class TestTheApiPutsAnEndOffASteepFaceOnIt:
    """Invariant 2. A face of 80 degrees: from (20, 10) to (21.75, 20)."""

    _FACE = ((20.0, 10.0), (21.75, 20.0))

    def _ws(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="steep")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [60, 0], [60, 20], [21.75, 20], [20, 10],
                         [0, 10]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb", "params": {
                               "cohesion": 10.0, "friction_angle": 30.0}}}]})
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], num_slices=_SLICES)
        return ws, pid

    #: The middle of the face, and an end 4e-5 to its left, in the air.
    _MID = (20.875, 15.0)
    _OFF = 4e-5

    def _surface(self, left):
        return [list(left), [23.875, 13.0], [32.875, 13.5], [45.875, 20.0]]

    def test_the_premise_inside_the_old_tolerance_outside_the_slicers(self):
        """4e-5 to the left of the face at mid-height is 3.9e-5 from it,
        inside 1e-6 of this model's diagonal (6.3e-5), and 2.3e-4 above the
        face at its own x, outside 1e-6 of the width (2.5e-5)."""
        (x0, y0), (x1, y1) = self._FACE
        x = self._MID[0] - self._OFF
        face_y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        perp = self._OFF * (y1 - y0) / math.hypot(x1 - x0, y1 - y0)
        assert perp < 1e-6 * math.hypot(60.0, 20.0)
        assert self._MID[1] - face_y > 1e-6 * (45.875 - x)

    def test_it_is_moved_onto_the_face_and_priced(self):
        """Fails on v0.1.258: left alone, then refused by the slicer."""
        from ogr_api import call
        ws, pid = self._ws()
        out = call(ws, "surface_evaluate", project_id=pid, surface={
            "type": "polyline",
            "points": self._surface((self._MID[0] - self._OFF, self._MID[1]))})
        fos = (out["methods"].get("bishop_simplified") or {}).get("fos")
        assert fos is not None, out.get("notes")
        assert any("first vertex" in n for n in out.get("notes") or [])
        on = call(ws, "surface_evaluate", project_id=pid, surface={
            "type": "polyline", "points": self._surface(self._MID)})
        assert math.isclose(fos, on["methods"]["bishop_simplified"]["fos"],
                            rel_tol=1e-4)

    def test_an_end_on_the_face_is_untouched(self):
        from ogr_api import call
        ws, pid = self._ws()
        out = call(ws, "surface_evaluate", project_id=pid, surface={
            "type": "polyline", "points": self._surface(self._MID)})
        assert not out.get("notes")


# ======================================================================
class TestTheBlockGuardIsRelative:
    """Invariant 3. A Block Search Polyline inside the soil but for one
    vertex on the face at x = 30, 5e-7 m above it: under the old absolute
    1e-6 in metres (5e-7) and over it in millimetres (5e-4)."""

    _POKE = 5e-7

    def _search(self, scale):
        from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec,
                                       Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_slip2d.analysis_runner import build_search
        p = _slope(scale)
        pts = [(25.0, 9.0), (30.0, 20.0 + self._POKE), (45.0, 25.0)]
        pts = [(x * scale, y * scale) for x, y in pts]
        b = Boundary(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False),
            btype=BoundaryType.BLOCK_SEARCH_OBJECT)
        b.block_object = BlockObjectSpec(BlockObjectKind.POLYLINE,
                                         group_id=1)
        p.add_boundary(b)
        s = p.settings.search
        s.search_method = "block"
        s.surface_type = "non_circular"
        s.block_num_surfaces = 40
        s.block_left_start_angle_deg, s.block_left_end_angle_deg = 135, 165
        s.block_right_start_angle_deg, s.block_right_end_angle_deg = 25, 45
        s.min_area = 0.0
        p.settings.advanced.parallel_search = False
        return p, build_search(p, "bishop_simplified")

    def _evaluated(self, scale, relative=True):
        """How many candidates reached the evaluation, with the switch as
        asked (read with ``getattr``, restored afterwards)."""
        import ogr_slip2d.search as S
        missing = object()
        before = getattr(S, "BLOCK_CHAIN_GUARD_RELATIVE", missing)
        try:
            S.BLOCK_CHAIN_GUARD_RELATIVE = relative
            p, srch = self._search(scale)
            calls = []
            real = srch.evaluate_surface

            def spy(project, surface):
                calls.append(1)
                return real(project, surface)

            srch.evaluate_surface = spy
            srch.run(p)
            return len(calls)
        finally:
            if before is missing:
                del S.BLOCK_CHAIN_GUARD_RELATIVE
            else:
                S.BLOCK_CHAIN_GUARD_RELATIVE = before

    def test_the_premise_the_absolute_guard_depends_on_the_units(self):
        """With the old absolute 1e-6 the millimetre model throws away
        the chains through the poked vertex and the metre model keeps
        them."""
        metres = self._evaluated(1.0, relative=False)
        millimetres = self._evaluated(1000.0, relative=False)
        assert millimetres < metres, (metres, millimetres)

    def test_the_relative_guard_keeps_the_same_candidates_in_both(self):
        """Fails on v0.1.258, whose guard is the absolute one."""
        assert self._evaluated(1.0) == self._evaluated(1000.0)
