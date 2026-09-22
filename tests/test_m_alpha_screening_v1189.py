# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The m-alpha criterion is applied to the methods the reference applies
it to, and to no others.

INVARIANT PROTECTED
-------------------
``checks.base_m_alphas`` evaluates Bishop's denominator,
``cos a + s*sin a*tan phi/F``, for every method. For two families that is
not the quantity the method divides by: the Ordinary Method forms no such
denominator at all, and the prescribed-inclination family divides by
``cos(a - t) - orient*(tan phi/F)*sin(a - t)``, which carries its own
interslice inclination.

Until v0.1.189 the exclusion existed only in the reporting NOTE. The
CHECK screened those methods anyway — so a surface could be thrown out of
a search by a denominator its own method never formed, while the note
alongside had already declared it had nothing to say about it. Two copies
of a decision are two decisions.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
It does not claim the FORM should be per method. Every method that IS
screened is screened with Bishop's denominator, exactly as the reference
does. ``TestTheFormIsNotDecidedByTheOnlyPublishedTable`` measures what
that costs and then asserts, in as many words, that the only published
slice table this project holds CANNOT decide it: all three forms clear
the 0.2 limit there with room to spare. A case that cannot decide is not
dressed up as one that can.

THE PUBLISHED EVIDENCE, AND WHY IT IS AN IDENTITY
-------------------------------------------------
The reference's two worked reports run all seven methods over the SAME
population and print, per method, the count of each error code alongside
the count of invalid surfaces. For the Ordinary Method and for
Lowe-Karafiath the printed codes ADD UP to the printed invalid count with
no -112 term at all. So the absence is an accounting identity, not an
unprinted zero — there is no surface left over for one to hide in. And
Lowe-Karafiath is not merely absent from the run: it reports 37 and 129
surfaces under -111, so it saw the same steep-based surfaces of which
Bishop discarded 97, and discarded none of them for this reason.

WHY NOTHING HERE IS A SNAPSHOT
------------------------------
The anchors are the two published reports above; the identity
``n_alpha == cos a * m_alpha``; the published James Bay slice table,
imported from ``test_james_bay_v1158`` rather than retyped; and the
closed-form ceilings that the 0.2 limit becomes under ``phi = 0``. No
case fixes a factor of safety against what this code prints today.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Run against the v0.1.188 tree: 7 of the 21 cases FAIL, 14 PASS.

FOUR fail on MEASURED BEHAVIOUR or on content, and they are the defect:
the two rule-7 doors (there the Ordinary Method's surface is rejected,
``bad = [14, 15, 16, 17]``, and the search marks it inadmissible), the
decision missing from the docstring, and ``analysis_runner`` declaring
its own copy of the set instead of importing one.

THREE fail on ABSENCE of a module symbol, which is weak discrimination
and is labelled as such.

The 14 that PASS do so BY DESIGN — the published counts and their
accounting identity, the three forms on James Bay, the two ceilings, the
threshold equivalence, the family inference, and the CONTROL that a
screened method is still rejected — because they say what the defect IS
by reading published data and arithmetic rather than the fix.
"""
from __future__ import annotations

import ast
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_checks_v132 import _DEGENERATE, _eval_poly  # noqa: E402
from test_slide_validation_ej1 import _ej1_project  # noqa: E402
from test_james_bay_v1158 import JB_F729, JB_THETA  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent

# ======================================================================
# The reference's two worked reports, as published. Per method:
#   (valid, invalid, {error code: count})
# Read off ``Slide2d_Ej_1_General`` and ``Slide2d_Ej_2_General``. The
# product is not named here or anywhere in the code, per the project's
# rule on its reference documentation; what is used is the arithmetic.
# ======================================================================
EJ1 = {
    "ordinary/fellenius":     (3379, 1472, {-103: 183, -106: 1, -107: 2,
                                            -108: 1055, -1000: 231}),
    "bishop simplified":      (3277, 1574, {-103: 183, -106: 1, -107: 2,
                                            -108: 1060, -112: 97,
                                            -1000: 231}),
    "janbu simplified":       (3264, 1587, {-103: 183, -106: 1, -107: 2,
                                            -108: 1079, -112: 91,
                                            -1000: 231}),
    "janbu corrected":        (3264, 1587, {-103: 183, -106: 1, -107: 2,
                                            -108: 1079, -112: 91,
                                            -1000: 231}),
    "spencer":                (3237, 1614, {-103: 183, -106: 1, -107: 2,
                                            -108: 1083, -111: 4,
                                            -112: 110, -1000: 231}),
    "lowe-karafiath":         (2450, 2401, {-103: 183, -106: 1, -107: 2,
                                            -108: 1947, -111: 37,
                                            -1000: 231}),
    "gle/morgenstern-price":  (3222, 1629, {-103: 183, -106: 1, -107: 2,
                                            -108: 1086, -111: 15,
                                            -112: 111, -1000: 231}),
}

#: Only the two counts and the -112 term are needed from the second
#: report; the full code breakdown is checked on the first.
EJ2_112 = {
    "ordinary/fellenius": None, "bishop simplified": 225,
    "janbu simplified": 146, "janbu corrected": 146, "spencer": 250,
    "lowe-karafiath": None, "gle/morgenstern-price": 248,
}
EJ2_INVALID = {
    "ordinary/fellenius": 1411, "lowe-karafiath": 2722,
}

#: How the report's names map onto this program's ids. Written out rather
#: than guessed, because two of them differ by more than punctuation.
ID_DE = {
    "ordinary/fellenius": "ordinary_fellenius",
    "bishop simplified": "bishop_simplified",
    "janbu simplified": "janbu_simplified",
    "janbu corrected": "janbu_corrected",
    "spencer": "spencer",
    "lowe-karafiath": "lowe_karafiath",
    "gle/morgenstern-price": "gle_morgenstern_price",
}



def _eval_con(method_id: str, pts=None):
    """The same surface as ``test_checks_v132``, through one named method.

    ``_eval_poly`` there fixes Spencer, and the whole point here is to
    put TWO methods on ONE surface: the screened one must still be
    rejected while the unscreened one is kept. The geometry is imported
    rather than retyped so the two files cannot drift apart.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipSurface
    p = _ej1_project()
    surf = SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in (pts or _DEGENERATE)],
        closed=False))
    ev = GridSearch(method=get_method(method_id)(), num_slices=18,
                    min_area=0.0)
    return ev.evaluate_surface(p, surf)


def _m_alpha(a: float, tan_phi: float, F: float, s: float = 1.0) -> float:
    return math.cos(a) + s * math.sin(a) * tan_phi / F


def _n_alpha(a: float, tan_phi: float, F: float, s: float = 1.0) -> float:
    return (math.cos(a) ** 2) * (1.0 + s * math.tan(a) * tan_phi / F)


def _d_theta(a: float, t: float, tan_phi: float, F: float) -> float:
    """The prescribed-inclination denominator, at ``orient = -1``, which
    is the orientation in which it reads as the published sheet does."""
    return math.cos(a - t) + math.sin(a - t) * tan_phi / F


def _source(rel: str) -> str:
    return io.open(_ROOT / rel, encoding="utf-8").read()


# ======================================================================
class TestThePublishedEvidence:
    """What the two reports say, and why the silence is a zero."""

    def test_the_error_codes_account_for_every_invalid_surface(self):
        """The case that turns "not printed" into "none".

        If the printed codes summed to LESS than the printed invalid
        count there would be surfaces unaccounted for, and a suppressed
        -112 could be hiding among them. They do not.
        """
        for name, (_valid, invalid, codes) in EJ1.items():
            assert sum(codes.values()) == invalid, (name, sum(codes.values()),
                                                    invalid)

    def test_the_same_population_reached_every_method(self):
        """So Lowe-Karafiath saw the very surfaces Bishop discarded 97 of."""
        poblaciones = {v + i for v, i, _ in EJ1.values()}
        assert poblaciones == {4851}, poblaciones

    def test_two_methods_never_report_the_code_in_either_example(self):
        sin_112 = {n for n, (_v, _i, c) in EJ1.items() if -112 not in c}
        assert sin_112 == {"ordinary/fellenius", "lowe-karafiath"}, sin_112
        assert {n for n, v in EJ2_112.items() if v is None} == sin_112

    def test_and_the_silent_one_was_not_silent_about_everything(self):
        """Lowe-Karafiath is screened by other codes in both examples, so
        it ran. -111 is the witness."""
        assert EJ1["lowe-karafiath"][2][-111] == 37
        assert EJ1["lowe-karafiath"][2][-108] > EJ1["bishop simplified"][2][-108]

    def test_the_second_report_closes_the_same_way(self):
        for name, invalid in EJ2_INVALID.items():
            assert EJ2_112[name] is None, name
            assert invalid > 0, name

    def test_the_screened_set_is_exactly_what_the_reports_print(self):
        from ogr_slip2d.checks import M_ALPHA_SCREENED
        con_112 = {ID_DE[n] for n, (_v, _i, c) in EJ1.items() if -112 in c}
        assert set(M_ALPHA_SCREENED) == con_112, (
            sorted(M_ALPHA_SCREENED), sorted(con_112))


# ======================================================================
class TestTheSetsCannotDriftApart:
    """One origin, one partition, and a method born tomorrow fails this
    file rather than inheriting a defect in silence."""

    def test_every_registered_method_falls_in_exactly_one_bucket(self):
        from ogr_slip2d.checks import M_ALPHA_SCREENED
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.methods.modified_swedish import (
            PrescribedInclinationMethod)
        reg = set(method_registry())
        prescrita = {mid for mid, cls in method_registry().items()
                     if getattr(cls, "_march", None)
                     is PrescribedInclinationMethod._march}
        from ogr_slip2d.checks import NO_M_ALPHA_DENOMINATOR
        cubos = (set(M_ALPHA_SCREENED), prescrita,
                 set(NO_M_ALPHA_DENOMINATOR))
        union = set().union(*cubos)
        assert union == reg, sorted(reg ^ union)
        for i, a in enumerate(cubos):
            for b in cubos[i + 1:]:
                assert a.isdisjoint(b), (sorted(a), sorted(b))

    def test_the_stronger_statement_is_a_subset_of_the_weaker(self):
        from ogr_slip2d.checks import (M_ALPHA_SCREENED,
                                       NO_M_ALPHA_DENOMINATOR)
        assert NO_M_ALPHA_DENOMINATOR.isdisjoint(M_ALPHA_SCREENED)

    def test_the_note_imports_the_set_instead_of_declaring_one(self):
        """By AST and not by grep.

        A grep cannot tell a reference from a mention in a docstring, and
        that difference already let a closure check through once. What
        must hold is that ``analysis_runner`` binds the name by IMPORT
        and assigns it nowhere.
        """
        arbol = ast.parse(_source("ogr_slip2d/analysis_runner.py"))
        importa = any(
            isinstance(n, ast.ImportFrom)
            and any(a.name == "NO_M_ALPHA_DENOMINATOR" for a in n.names)
            for n in ast.walk(arbol))
        assert importa, "analysis_runner no importa el conjunto"
        for n in ast.walk(arbol):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    assert not (isinstance(t, ast.Name)
                                and "NO_M_ALPHA_DENOMINATOR" in t.id), (
                        "analysis_runner vuelve a declarar el conjunto")

    def test_the_family_inference_is_measured_on_this_program(self):
        """The two Corps procedures are in by FAMILY INFERENCE — neither
        report runs them. The inference is weak about the reference and
        STRONG about this program, and this is the strong half: the three
        share one recursion and override only the theta rule.
        """
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.methods.modified_swedish import (
            PrescribedInclinationMethod)
        reg = method_registry()
        for mid in ("corps_engineers_1", "corps_engineers_2",
                    "lowe_karafiath"):
            cls = reg[mid]
            assert cls._march is PrescribedInclinationMethod._march, mid
            assert cls._theta_angles is not (
                PrescribedInclinationMethod._theta_angles), mid


# ======================================================================
class TestRuleSevenThroughBothDoors:
    """The setting has to move the number, and both doors have to agree.

    The same surface, the same slicing: a method that is screened is
    still rejected, one that is not is now kept. If only one door moved,
    the other would be the next D111.
    """

    def test_the_measurement_is_unchanged_for_the_method_left_out(self):
        """The value is still computed and still below the limit. What
        changed is the verdict, not the arithmetic — which is why
        ``base_m_alphas`` was not touched."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT, base_m_alphas
        r = _eval_con("ordinary_fellenius")
        assert r is not None and r.is_valid
        assert min(base_m_alphas(r)) < M_ALPHA_LIMIT, min(base_m_alphas(r))

    def test_door_one_the_check_no_longer_rejects_it(self):
        from ogr_slip2d.checks import check_surface, m_alpha_check
        r = _eval_con("ordinary_fellenius")
        ok, bad = m_alpha_check(r)
        assert ok and not bad, bad
        passed, why = check_surface(r, m_alpha=True)
        assert passed and why is None, why

    def test_door_two_the_search_no_longer_marks_it(self):
        r = _eval_con("ordinary_fellenius")
        assert getattr(r, "admissible", True) is True
        assert not (r.admissibility_note or "")

    def test_the_control_a_screened_method_is_still_rejected(self):
        """Same surface, same geometry. Without this the two cases above
        would also pass on a tree where the check had simply been turned
        off."""
        from ogr_slip2d.checks import m_alpha_check
        r = _eval_poly(_DEGENERATE)          # Spencer, which IS screened
        ok, bad = m_alpha_check(r)
        assert not ok and bad, bad
        assert getattr(r, "admissible", True) is False


# ======================================================================
class TestTheFormIsNotDecidedByTheOnlyPublishedTable:
    """What the inherited form costs, and why the case in hand cannot
    settle it."""

    def test_the_three_forms_on_the_published_sheet(self):
        F, t = 1.17, math.radians(JB_THETA)
        bishop, janbu, theta = [], [], []
        for (_b, ad, _W, _l, _c, phi) in JB_F729:
            a, tp = math.radians(ad), math.tan(math.radians(phi))
            bishop.append(_m_alpha(a, tp, F))
            janbu.append(_n_alpha(a, tp, F))
            theta.append(_d_theta(a, t, tp, F))
        assert abs(min(bishop) - 0.7230) < 5e-4, min(bishop)
        assert abs(min(janbu) - 0.5181) < 5e-4, min(janbu)
        assert abs(min(theta) - 0.6896) < 5e-4, min(theta)

    def test_and_they_are_not_even_governed_by_the_same_slice(self):
        """Which says the three are not one number in three coats: moving
        the form moves WHICH base the note talks about."""
        F, t = 1.17, math.radians(JB_THETA)
        bishop, janbu = [], []
        for (_b, ad, _W, _l, _c, phi) in JB_F729:
            a, tp = math.radians(ad), math.tan(math.radians(phi))
            bishop.append(_m_alpha(a, tp, F))
            janbu.append(_n_alpha(a, tp, F))
        assert bishop.index(min(bishop)) != janbu.index(min(janbu))

    def test_the_published_case_cannot_decide_it(self):
        """All three clear the limit, and by a long way. This is the
        measurement D111 asked for and the reason it does not settle the
        FORM."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        F, t = 1.17, math.radians(JB_THETA)
        for f in (lambda a, tp: _m_alpha(a, tp, F),
                  lambda a, tp: _n_alpha(a, tp, F),
                  lambda a, tp: _d_theta(a, t, tp, F)):
            peor = min(f(math.radians(ad), math.tan(math.radians(phi)))
                       for (_b, ad, _W, _l, _c, phi) in JB_F729)
            assert peor > 2.5 * M_ALPHA_LIMIT, peor

    def test_janbus_denominator_is_bishops_scaled_by_the_cosine(self):
        for a_deg in (-78.0, -43.7, 0.0, 30.0, 70.0):
            for tp in (0.0, 0.4, 1.0):
                for F in (0.8, 1.17, 2.5):
                    a = math.radians(a_deg)
                    assert abs(_n_alpha(a, tp, F)
                               - math.cos(a) * _m_alpha(a, tp, F)) < 1e-15

    def test_so_the_same_number_would_be_a_different_criterion(self):
        """0.2 on ``n_alpha`` is ``0.2/cos a`` on ``m_alpha``: the limit
        is glued to the form it was published for."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        for a_deg in (0.0, 20.0, 40.0, 57.2, 70.0):
            a = math.radians(a_deg)
            equivalente = M_ALPHA_LIMIT / math.cos(a)
            tp, F = 0.5, 1.2
            por_n = _n_alpha(a, tp, F) >= M_ALPHA_LIMIT
            por_m = _m_alpha(a, tp, F) >= equivalente
            assert por_n == por_m, a_deg

    def test_the_two_ceilings_under_no_friction(self):
        """Closed form, and 15 degrees apart. Imported rather than
        written out, so that moving the limit moves this test."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        bishop = math.degrees(math.acos(M_ALPHA_LIMIT))
        janbu = math.degrees(math.acos(math.sqrt(M_ALPHA_LIMIT)))
        assert abs(bishop - 78.463) < 0.001, bishop
        assert abs(janbu - 63.435) < 0.001, janbu
        assert abs((bishop - janbu) - 15.028) < 0.002, bishop - janbu

    def test_the_decision_is_written_where_the_measurement_is(self):
        """A documented decision that lives only in a changelog is a
        decision nobody reading the function will find. Read from the
        docstring by AST, not grepped from the file: the module docstring
        of ``checks.py`` already contains the token -112, so a grep over
        the file would pass without anybody deciding anything.
        """
        from ogr_slip2d.checks import base_m_alphas
        doc = base_m_alphas.__doc__ or ""
        for trozo in ("n_alpha", "0.7230", "0.5181", "0.6896",
                      "78.463", "63.435", "M_ALPHA_SCREENED"):
            assert trozo in doc, trozo
