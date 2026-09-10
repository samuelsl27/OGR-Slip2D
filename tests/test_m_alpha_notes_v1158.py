# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The m-alpha margin note, and the prose around the check it reports on.

**The invariant**: a note that names a method has to be true FOR THAT
METHOD, and a comment that states a default has to state the default the
code actually has.

Both halves are the same failure. The note told Spencer and
GLE/Morgenstern-Price — which satisfy force and moment equilibrium both —
to "compare against a complete-equilibrium method such as Spencer",
sending them to themselves; it called Janbu, Lowe-Karafiath and the two
Corps procedures "a method of moments", which they are not; it fired for
the Ordinary Method of Slices, which forms no such denominator at all;
and it described a clearance larger than the limit itself as "a number
near zero". Meanwhile two comments claimed both admissibility checks were
off by default, for the seventy-four versions from v0.1.84 on,
and a refuted claim about the check survived in the translation
dictionary with no widget left to display it.

None of it moved a number. All of it told the user something untrue about
the number, which is the same class of defect this project keeps finding:
a sentence outliving the measurement that justified it.

Sources for the four branches: Duncan, J. M., Wright, S. G. and Brandon,
T. L. (2014), *Soil Strength and Slope Stability*, 2nd ed., section
14.4.1, which separates the denominator of Spencer's procedure (its
Eq. 14.5, carrying its own interslice inclination) from that of the
Simplified Bishop procedure (Eq. 14.6, the same expression "when the
interslice force inclination (theta) is set to zero"); and section
14.4.2, which names the Ordinary Method of Slices as one of its four
remedies for this problem precisely because the large or negative normal
forces "do not occur" in it.
"""
from __future__ import annotations

import io
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_block_population_v1135 import _cohesive_slope, _STEEP  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_CACHE: dict = {}


def _note_for(method_id: str):
    """``(result, notes)`` for one method on a steep purely cohesive
    surface, evaluated once per method and reused.

    ``phi = 0`` and a back scarp at 74.5 deg put ``m_alpha`` at 0.2676 —
    past the 0.5 the note fires at and clear of the 0.2 the check rejects
    at — which is the band the note exists to describe.
    """
    if method_id not in _CACHE:
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.analysis_runner import m_alpha_margin_note
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import BlockSearch
        from ogr_slip2d.surface import SlipSurface

        cls = method_registry()[method_id]
        search = BlockSearch(method=cls(), num_slices=30)
        poly = Polyline(vertices=[Vertex(x, y) for x, y in _STEEP],
                        closed=False)
        res = search.evaluate_surface(_cohesive_slope(0.0),
                                      SlipSurface(polyline=poly))
        _CACHE[method_id] = (res, m_alpha_margin_note(res))
    return _CACHE[method_id]


def _families():
    """The registered methods grouped by what equilibrium they satisfy."""
    from ogr_slip2d.methods import method_registry
    out = {"complete": [], "force": [], "moment": []}
    for mid, cls in method_registry().items():
        if cls.SATISFIES_FORCE and cls.SATISFIES_MOMENT:
            out["complete"].append(mid)
        elif cls.SATISFIES_FORCE:
            out["force"].append(mid)
        elif cls.SATISFIES_MOMENT:
            out["moment"].append(mid)
    return out


def _source(rel: str) -> str:
    return io.open(_ROOT / rel, encoding="utf-8").read()


# ======================================================================
class TestTheNoteIsTrueOfTheMethodItNames:
    """Defect D104 — four sentences, four families."""

    def test_the_families_are_not_empty(self):
        """Guard for the tests below: if a family had no member the
        assertions about it would pass by being vacuous."""
        fams = _families()
        assert fams["complete"], fams
        assert fams["force"], fams
        assert fams["moment"], fams

    def test_a_complete_method_is_not_sent_to_compare_with_itself(self):
        for mid in _families()["complete"]:
            _res, notes = _note_for(mid)
            assert notes, mid
            note = notes[0]
            assert "method of moments" not in note, (mid, note)
            assert "such as Spencer" not in note, (mid, note)
            assert "satisfies force AND moment equilibrium" in note, (
                mid, note)

    def test_a_force_method_is_not_called_a_method_of_moments(self):
        for mid in _families()["force"]:
            _res, notes = _note_for(mid)
            assert notes, mid
            note = notes[0]
            assert "method of moments" not in note, (mid, note)
            assert "force-equilibrium method is least reliable" in note, (
                mid, note)

    def test_a_moment_method_keeps_the_wording_it_already_had(self):
        """Bishop's sentence was correct and is not disturbed. Ordinary
        is a moment method too and is handled separately below, so it is
        excluded here rather than silently absent."""
        for mid in _families()["moment"]:
            if mid == "ordinary_fellenius":
                continue
            _res, notes = _note_for(mid)
            assert notes, mid
            assert "A method of moments is not reliable there" in notes[0], (
                mid, notes[0])

    def test_the_ordinary_method_gets_no_note_at_all(self):
        """It forms no such denominator: its base normal is the
        projection of the external forces, with nothing to divide by.
        Duncan, Wright & Brandon (2014) 14.4.2 makes it one of the
        remedies for this very problem."""
        _res, notes = _note_for("ordinary_fellenius")
        assert notes == [], notes
        assert "m_alpha" not in _source("ogr_slip2d/methods/ordinary.py")

    def test_every_note_still_names_m_alpha_and_its_value(self):
        """The first half of the sentence is unchanged; other tests and
        the verification bank read it."""
        for members in _families().values():
            for mid in members:
                if mid == "ordinary_fellenius":
                    continue
                _res, notes = _note_for(mid)
                assert re.search(r"m_alpha down to \d\.\d{4}", notes[0]), (
                    mid, notes[0])


# ======================================================================
class TestTheNoteDoesNotContradictItself:
    """Defect D104, fourth branch — measured in the verification bank's
    audits of problems 57 and 83, which called the wording backwards."""

    def test_a_clearance_is_not_described_as_a_number_near_zero(self):
        for mid in _families()["complete"] + _families()["force"] + \
                _families()["moment"]:
            if mid == "ordinary_fellenius":
                continue
            _res, notes = _note_for(mid)
            assert "near zero" not in notes[0], (mid, notes[0])

    def test_the_value_it_divides_by_is_stated_not_characterised(self):
        _res, notes = _note_for("bishop_simplified")
        note = notes[0]
        m = re.search(r"divides the normal force on that base by "
                      r"(\d\.\d{4}), inflating it (\d+\.\d)-fold", note)
        assert m, note
        value, fold = float(m.group(1)), float(m.group(2))
        # The two have to be each other's reciprocal, or the sentence is
        # reporting two different bases.
        assert abs(1.0 / value - fold) < 0.05, (value, fold)

    def test_the_margin_it_reports_is_the_real_margin(self):
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        _res, notes = _note_for("bishop_simplified")
        note = notes[0]
        got = re.search(r"m_alpha down to (\d\.\d{4})", note)
        clr = re.search(r"clears the [\d.]+ limit by (\d\.\d{4})", note)
        assert got and clr, note
        assert abs((float(got.group(1)) - M_ALPHA_LIMIT)
                   - float(clr.group(1))) < 1e-9, note


# ======================================================================
class TestTheLabelAndTheWordingNameTheSameMethod:
    """The runner prefixes each note with its own method id and the note
    now branches on the id inside the result. If those two ever came
    apart, a note would be labelled for one method and worded for
    another, and nothing would say so."""

    def test_every_result_carries_the_id_of_the_method_that_made_it(self):
        from ogr_slip2d.methods import method_registry
        for mid in method_registry():
            res, _notes = _note_for(mid)
            assert res.method_id == mid, (mid, res.method_id)


# ======================================================================
class TestTheNoteCarriesNothingTheBankReserves:
    """v0.1.155 left three substrings spoken for, because the
    verification bank decides whether defect D40 is still closed by
    reading the text of the notes. Checked raw and lower-cased, because
    "unstable" contains "stable" and "ahead" contains "head"."""

    def test_no_branch_carries_a_reserved_substring(self):
        from ogr_slip2d.methods import method_registry
        for mid in method_registry():
            _res, notes = _note_for(mid)
            for note in notes:
                for text in (note, note.lower()):
                    assert not ("stable" in text and "head" in text), note
                    assert "edge of the search grid" not in text, note
                    assert "path_optimize" not in text, note


# ======================================================================
class TestTheProseMatchesTheDefaults:
    """Defect D105 — the same false sentence in two files, and the
    measurement that refutes it is a one-line lookup."""

    def test_the_m_alpha_check_is_on_at_all_three_doors(self):
        import inspect
        from ogr_core.project.settings import AdvancedSettings
        from ogr_slip2d.search import BaseSearch
        assert AdvancedSettings().check_m_alpha is True
        assert AdvancedSettings().check_tensile_stresses is False
        sig = inspect.signature(BaseSearch.__init__)
        assert sig.parameters["check_m_alpha"].default is True
        assert sig.parameters["reject_tensile"].default is False

    def test_the_checks_docstring_does_not_say_both_are_off(self):
        import ogr_slip2d.checks as checks
        doc = checks.__doc__ or ""
        assert "Both checks are **disabled by default**" not in doc
        assert "off" in doc and "on" in doc

    def test_the_search_comment_does_not_say_both_either(self):
        src = _source("ogr_slip2d/search.py")
        assert "Both default to off, as in the" not in src

    def test_the_docstring_cites_both_sources_the_limit_rests_on(self):
        import ogr_slip2d.checks as checks
        doc = checks.__doc__ or ""
        assert "Whitman & Bailey, 1967" in doc or \
               "Whitman & Bailey (1967)" in doc, doc
        assert "Ching & Fredlund (1983)" in doc, doc

    def test_it_says_the_limit_is_not_a_verdict_on_the_factor(self):
        """The source says so twice and the code said it nowhere."""
        doc = (__import__("ogr_slip2d.checks", fromlist=["x"]).__doc__ or "")
        assert "does not by itself mean the factor of safety is wrong" in doc

    def test_it_admits_the_second_source_was_not_read(self):
        """v0.1.84's lesson, applied to a citation: a reference given
        because another document points at it is not evidence, and
        pretending otherwise is how a false sentence gets a footnote."""
        doc = (__import__("ogr_slip2d.checks", fromlist=["x"]).__doc__ or "")
        assert "not** because it has been read" in doc, doc


# ======================================================================
class TestTheRefutedTranslationIsGone:
    """Defect D107 — a claim v0.1.82 disproved, still in the dictionary
    with nothing left to display it."""

    def test_the_dictionary_no_longer_carries_it(self):
        from ogr_gui.i18n import _DICTS
        for lang, table in _DICTS.items():
            for key in table:
                assert "deliberately NOT offered here" not in key, lang

    def test_and_no_widget_wraps_it(self):
        hits = [p for p in (_ROOT / "ogr_gui").rglob("*.py")
                if "deliberately NOT offered here"
                in io.open(p, encoding="utf-8").read()]
        assert hits == [], hits

    def test_the_circle_it_libelled_still_passes_the_check(self):
        """Why the claim was false, kept next to its removal so the two
        cannot drift apart: read with the sense of sliding the solver
        used, the reference-validated critical circle has a minimum
        m_alpha of +0.93, not the -0.01 the removed sentence rested on."""
        sys.path.insert(0, str(Path(__file__).parent))
        from test_slide_validation_ej1 import _ej1_project
        from ogr_slip2d.checks import base_m_alphas, check_surface
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        proj = _ej1_project()
        circle = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(proj, circle, 25)
        res = BishopSimplified().compute_fos(proj, circle, sl)
        assert min(base_m_alphas(res)) > 0.9
        ok, why = check_surface(res, m_alpha=True)
        assert ok is True and why is None, why


# ======================================================================
class TestTheMinus112StringCouplingIsIntact:
    """Not a defect — a tripwire under one.

    ``interpret_window`` decides the published error code -112 by looking
    for the literal ``m_alpha`` inside the admissibility reason that
    ``checks.check_surface`` builds. That is a coupling between two files
    through the spelling of a word, it decides a number the verification
    bank compares against, and it had no test. Renaming the token in
    either file would silently reclassify every rejected surface.
    """

    def test_the_reason_still_contains_the_token(self):
        from ogr_slip2d.checks import check_surface
        from ogr_slip2d.methods import method_registry  # noqa: F401
        res, _notes = _note_for("bishop_simplified")
        # Force a rejection by asking with a limit the surface cannot meet.
        ok, why = check_surface(res, m_alpha=True, m_alpha_limit=0.99)
        assert ok is False
        assert "m_alpha" in (why or ""), why

    def test_and_the_window_still_looks_for_it(self):
        src = _source("ogr_gui/interpret_window.py")
        assert '"m_alpha" in note' in src, (
            "interpret_window no longer keys -112 off this token; the "
            "coupling moved and this tripwire has to move with it")


# ======================================================================
class TestNoneOfThisMovedANumber:
    """The whole point of the version: the prose changed and the
    arithmetic did not."""

    def test_the_factor_of_safety_is_untouched_by_the_note(self):
        """Asking for the note twice, and between two methods, cannot
        change what either of them computed."""
        from ogr_slip2d.analysis_runner import m_alpha_margin_note
        res, _n = _note_for("bishop_simplified")
        before = res.fos
        m_alpha_margin_note(res)
        m_alpha_margin_note(res)
        assert res.fos == before

    def test_the_check_itself_still_rejects_where_it_did(self):
        from ogr_slip2d.checks import M_ALPHA_LIMIT, base_m_alphas
        res, _n = _note_for("bishop_simplified")
        worst = min(base_m_alphas(res))
        assert abs(worst - 0.2676) < 5e-4, worst
        assert worst > M_ALPHA_LIMIT
        assert abs(math.degrees(math.acos(worst)) - 74.5) < 0.1, worst
