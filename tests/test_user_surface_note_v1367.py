# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.367 (D346) — the note of a hand-drawn circle that gives no result says
WHY when the search knows it, and a filter that is the search's default is
said to be one.

The finding (the fifth interface test, 0.1.355, H8): the circle of centre
(200, 200) and radius 5 over the demo slope got "… produced no result …
Filters active on this run that can remove it: Minimum Area 1.". Read:

* the search knew the reason — ``evaluate_circle`` counts the circle in
  ``_count_misses_ground`` and records ``REFUSED_MISSES_GROUND`` — and the
  note never asked it;
* "Minimum Area 1" is not a setting of the model (``min_area`` is null): it
  is the search's fallback, which the analysis door hands every search
  (``_MIN_AREA_FALLBACK``). So the note "no filter is active" could never be
  reached through an analysis;
* and ``_last_refusal`` was not reset before each hand-drawn circle, so a
  circle could have been given the reason the search loop left behind.

What these tests protect:

* the ticket's circle gets the new note, ``search.user_misses_ground``, in
  English and in Spanish ("no corta dos veces el terreno");
* a circle the search DID evaluate, whose tiny mass the default Minimum Area
  removes, gets the filters note with the filter said to be the default;
  with the area declared by the model, it is said without that label;
* another reason the search knows (``unsliceable``) is said through
  ``search.user_refused``, with the reason nested;
* the reason is this circle's: one left by the search before it is not used.
"""
from __future__ import annotations

import math
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


@contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


def _demo_with(circle, **search):
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    for k, v in search.items():
        setattr(p.settings.search, k, v)
    p.user_surfaces = [circle]
    return p


def _user_notes(project):
    """The notes about hand-drawn circles of a real run, unwrapped from
    their method."""
    from ogr_core.messages import METHOD_NOTE
    from ogr_slip2d.analysis_runner import run_analysis
    out = run_analysis(project, ["bishop_simplified"])
    return [w.args["note"] for w in out.warnings
            if getattr(w, "code", "") == METHOD_NOTE
            and w.args["note"]["code"].startswith("search.user_")]


def _said(nested):
    """The note, in the language now set."""
    from ogr_core.messages import Coded
    from ogr_gui.core_messages import note_text
    return note_text(Coded(nested["text"], nested["code"], nested["args"]))


def _circle(x, y, r):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=x, centre_y=y, radius=r)


def _grazing_circle():
    """A circle of radius 5 that dips 0.1 m into the demo's slope face
    (from the crest (25, 25) to the toe (35, 15)) at its middle point: a
    mass of about 0.13 m², which the default Minimum Area of 1 removes."""
    r, sag = 5.0, 0.1
    n = (1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0))   # out of the soil
    d = r - sag
    return _circle(30.0 + d * n[0], 20.0 + d * n[1], r)


# ======================================================================
class TestTheTicketsCircle:

    def test_it_says_it_does_not_cut_the_ground(self):
        notes = _user_notes(_demo_with(_circle(200.0, 200.0, 5.0)))
        assert [n["code"] for n in notes] == ["search.user_misses_ground"], \
            notes
        assert notes[0]["text"] == (
            "The user-defined surface at centre (200, 200) with radius 5 "
            "produced no result, so it is not in the reported population. "
            "It does not cut the ground surface twice inside the External "
            "Boundary, so there is no sliding mass to analyse.")
        with _spanish():
            said = _said(notes[0])
        assert said == (
            "La superficie definida por el usuario con centro en (200, 200) "
            "y radio 5 no dio ningún resultado, así que no está en la "
            "población informada. No corta dos veces el terreno dentro del "
            "contorno exterior, así que no hay ninguna masa deslizante que "
            "analizar."), said
        assert "Área mínima" not in said


class TestADefaultFilterIsSaidToBeOne:

    def test_the_default_minimum_area(self):
        notes = _user_notes(_demo_with(_grazing_circle()))
        assert [n["code"] for n in notes] == [
            "search.user_no_result_filtered"], notes
        frags = [f["code"] for f in notes[0]["args"]["filters"]]
        assert "search.filter.min_area_default" in frags, frags
        assert ("Minimum Area 1 (the search's default, not a setting of "
                "this model)") in notes[0]["text"], notes[0]["text"]
        with _spanish():
            said = _said(notes[0])
        assert ("Área mínima 1 (valor por defecto de la búsqueda, no un "
                "ajuste de este modelo)") in said, said

    def test_a_declared_minimum_area_is_said_plainly(self):
        notes = _user_notes(_demo_with(_grazing_circle(), min_area=1.0))
        assert [n["code"] for n in notes] == [
            "search.user_no_result_filtered"], notes
        frags = [f["code"] for f in notes[0]["args"]["filters"]]
        assert "search.filter.min_area" in frags, frags
        assert "search.filter.min_area_default" not in frags
        assert "search's default" not in notes[0]["text"]


# ======================================================================
def _search_with(evaluate):
    """The demo's configured search, its circle evaluation replaced."""
    from ogr_slip2d.analysis_runner import build_search
    p = _demo_with(_circle(30.0, 30.0, 12.0))
    search = build_search(p, "bishop_simplified")
    search.evaluate_circle = evaluate
    return p, search


def _notes_of(project, search):
    from ogr_slip2d.search import SearchResult
    search._pending_notes = []
    result = SearchResult(method_id="bishop_simplified")
    search._evaluate_user_surfaces(project, result)
    return [n for n in search._pending_notes
            if str(getattr(n, "code", "")).startswith("search.user_")]


class TestAnotherReasonAndWhoseItIs:

    def test_a_known_reason_is_said(self):
        def refused(project, circle):
            search._last_refusal = "unsliceable"
            return None
        p, search = _search_with(refused)
        notes = _notes_of(p, search)
        assert [n.code for n in notes] == ["search.user_refused"], notes
        assert notes[0].args["reason"]["code"] == \
            "search.refused_surface.unsliceable"
        assert notes[0].endswith(
            "The search says why: the surface was not analysed: the slicer "
            "refused it (more mandatory cuts than slices, a degenerate width "
            "or a tension crack it could not place)."), notes[0]
        from ogr_gui.core_messages import note_text
        with _spanish():
            said = note_text(notes[0])
        assert "La búsqueda dice por qué:" in said and said != notes[0], said

    def test_the_reason_left_by_the_search_is_not_this_circles(self):
        def filtered(project, circle):
            return None                          # no reason recorded
        p, search = _search_with(filtered)
        search._last_refusal = "unsliceable"     # left by the search loop
        notes = _notes_of(p, search)
        assert [n.code for n in notes] == [
            "search.user_no_result_filtered"], notes
