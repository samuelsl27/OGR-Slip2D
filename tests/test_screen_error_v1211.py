# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.211 — a post-analysis check that raises REJECTS the surface and says so
(defect D184).

THE INVARIANT. No door admits a surface its checks could not evaluate
without a note. ``checks.screen_surface`` answers ``(False, SCREEN_ERROR,
note)`` when the Tensile Stress Check or the m-alpha check raises, with the
exception named in the note; ``BaseSearch._is_admissible`` marks the result
inadmissible with that note and reason; the raw-data export writes -101;
and the surface cannot be the critical one while another is admissible.

WHAT WAS WRONG. ``_is_admissible`` wrapped the screen in ``except
Exception: return True``. A check that raised left the surface ADMITTED,
with no note, no reason and no warning, so it could win the search: a
failure of the measurement read as a verdict, the shape of D94. The
owner's decision (2026-09-26) is to reject and declare, not to admit with a
note and not to let the search die: see ``SCREEN_ERROR`` in
``ogr_slip2d/methods/base.py``.

WHY A SYNTHETIC FAILURE. Neither the suite nor verification problems
095-098 raise inside the checks (the census is ``_tools/censo_p3_desembalse.py``
and ``_tools/censo_cribado_suite_d184.py`` in the verification bank), so the
exception has to be made: a material whose strength raises when the checks
linearise it, which is where both checks call into the model. The number
the test compares is not a factor of safety but a verdict, and the reference
for it is the decision, not the code.

WHY -101 AND NOT -112. The reference gives no code to "the checks could not
be evaluated"; -101 is its "any other rejection". The export used to map a
note containing ``m_alpha`` to -112, and an exception's own text can say
``m_alpha_sign`` -- so that case is tested with exactly that text.

DISCRIMINATION against the v0.1.210 tree. MEASURED, by copying this file into
a ``git worktree`` at e983574 and running it there. Of the 12 cases, **7 fail
and 5 pass**:

  fail  screen_surface_declares_the_exception        (behaviour: raises)
        the_search_door_rejects_it_with_note_and_reason (behaviour: admitted)
        no_combination_of_checks_admits_it_silently (behaviour: admitted)
        it_exports_as_minus_101_even_if_the_text_says_m_alpha (behaviour)
        check_surface_keeps_its_two_value_contract  (behaviour: raises)
        it_cannot_be_the_critical_surface_while_another_is_admissible
                                                    (behaviour)
        the_screen_is_not_a_failure_reason          (WEAK: a constant)

  pass  the_result_keeps_its_factor_and_validity (guard) and the four
        controls.

The run is archived in the bank as
``_auditoria/D184_cribado/discriminacion_test_v1211_en_0.1.210.txt``.
"""
from __future__ import annotations

from types import SimpleNamespace


class _Raises:
    """A strength model that raises wherever the checks ask it anything."""

    MODEL_ID = "raises_for_d184"
    needs_context = False
    params: dict = {}

    def __init__(self, exc):
        self.exc = exc

    def shear_strength(self, *a, **k):
        raise self.exc

    def tangent_slope(self, *a, **k):
        raise self.exc


def _result(fos=1.5, exc=None, n=6, angle=0.3):
    """A converged Bishop result whose checks raise ``exc`` (or pass, with
    ``exc=None``): positive stresses everywhere, so a clean material passes
    both checks and the only thing that can reject it is the exception."""
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_slip2d.methods.base import LEMResult
    from ogr_slip2d.slicer import Slice

    if exc is None:
        mat = Material(name="clean", strength=MohrCoulomb(cohesion=5.0,
                                                          friction_angle=30.0))
    else:
        mat = SimpleNamespace(name="raises", strength=_Raises(exc))
    dov = [Slice(index=i, x_centre=i + 0.5, width=1.0,
                 base_x_left=float(i), base_x_right=float(i + 1),
                 base_y_left=0.0, base_y_right=0.0, base_angle=angle,
                 base_length=1.0, top_y_left=1.0 + i, top_y_right=2.0 + i,
                 weight=50.0, pore_pressure=0.0, water_weight=0.0,
                 water_force_h=0.0, material=mat) for i in range(n)]
    return LEMResult(fos=fos, converged=True, iterations=1,
                     method_id="bishop_simplified", surface=None, slices=dov)


def _search(**kw):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import GridSearch
    return GridSearch(method=BishopSimplified(), **kw)


# ======================================================================
class TestAScreenThatRaisesIsDeclared:

    # The constant is imported AFTER the behaviour is asserted, so that on a
    # tree without it these cases fail on what the code does, not on a name.

    def test_screen_surface_declares_the_exception(self):
        from ogr_slip2d.checks import screen_surface
        ok, screen, note = screen_surface(
            _result(exc=RuntimeError("boom")), m_alpha=True)
        assert ok is False
        assert "RuntimeError" in note and "boom" in note, note
        from ogr_slip2d.methods.base import SCREEN_ERROR
        assert screen == SCREEN_ERROR

    def test_the_search_door_rejects_it_with_note_and_reason(self):
        res = _result(exc=RuntimeError("boom"))
        ok = _search(check_m_alpha=True)._is_admissible(res)
        assert ok is False, "admitted"
        assert res.admissible is False
        assert "RuntimeError" in res.admissibility_note
        from ogr_slip2d.methods.base import SCREEN_ERROR
        assert res.admissibility_reason == SCREEN_ERROR

    def test_no_combination_of_checks_admits_it_silently(self):
        """Tension only, m-alpha only and both: each check reaches the
        model through the same linearisation, and none may let it in."""
        for kw in (dict(reject_tensile=True, check_m_alpha=False),
                   dict(reject_tensile=False, check_m_alpha=True),
                   dict(reject_tensile=True, check_m_alpha=True)):
            res = _result(exc=ValueError("bad envelope"))
            ok = _search(**kw)._is_admissible(res)
            assert not (ok and not res.admissibility_note), kw
            assert ok is False and res.admissibility_note, kw

    def test_it_exports_as_minus_101_even_if_the_text_says_m_alpha(self):
        from ogr_slip2d.interpretation import ERROR_OTHER, error_code
        res = _result(exc=KeyError("m_alpha_sign"))
        _search(check_m_alpha=True)._is_admissible(res)
        assert "m_alpha" in res.admissibility_note     # the trap is armed
        assert error_code(res) == ERROR_OTHER == -101

    def test_check_surface_keeps_its_two_value_contract(self):
        from ogr_slip2d.checks import check_surface, screen_surface
        res = _result(exc=RuntimeError("boom"))
        ok, note = check_surface(res, m_alpha=True)
        ok3, _screen, note3 = screen_surface(res, m_alpha=True)
        assert (ok, note) == (ok3, note3)
        assert ok is False and note

    def test_it_cannot_be_the_critical_surface_while_another_is_admissible(
            self):
        from ogr_slip2d.search import SearchResult
        search = _search(check_m_alpha=True)
        broken = _result(fos=0.9, exc=RuntimeError("boom"))
        clean = _result(fos=1.3)
        for r in (broken, clean):
            search._is_admissible(r)
        assert clean.admissible is True             # the control is clean
        out = SearchResult(method_id="bishop_simplified",
                           evaluations=[broken, clean], valid_count=2)
        assert out.critical is clean
        assert out.inadmissible_count == 1


class TestWhatTheRejectionIsNot:
    """Guards: a declared rejection is a SCREEN, not a failed calculation."""

    def test_the_screen_is_not_a_failure_reason(self):
        from ogr_slip2d.methods.base import (ALL_REASONS, ALL_SCREENS,
                                             SCREEN_ERROR)
        assert SCREEN_ERROR in ALL_SCREENS
        assert not (ALL_SCREENS & ALL_REASONS)

    def test_the_result_keeps_its_factor_and_validity(self):
        res = _result(fos=1.5, exc=RuntimeError("boom"))
        _search(check_m_alpha=True)._is_admissible(res)
        assert res.fos == 1.5 and res.is_valid and res.reason == ""


class TestWhatDoesNotMove:
    """Controls: these pass on v0.1.210 as well."""

    def test_a_clean_surface_passes(self):
        from ogr_slip2d.checks import screen_surface
        assert screen_surface(_result(), tensile=True,
                              m_alpha=True) == (True, "", None)

    def test_the_tensile_note_is_unchanged(self):
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        from test_tensile_export_code_v1192 import _tension_rejected
        res = _tension_rejected()
        assert res.admissibility_reason == SCREEN_TENSILE_STRESS
        assert res.admissibility_note.startswith("tensile stress on ")
        assert res.admissibility_note.endswith(" slice base(s) (error -120)")

    def test_the_m_alpha_note_is_unchanged(self):
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        from ogr_slip2d.methods.base import SCREEN_M_ALPHA
        from test_tensile_export_code_v1192 import _m_alpha_rejected
        res = _m_alpha_rejected()
        assert res.admissibility_reason == SCREEN_M_ALPHA
        assert res.admissibility_note.startswith(
            "m_alpha < %s on " % M_ALPHA_LIMIT), res.admissibility_note

    def test_both_checks_off_still_admits_without_asking(self):
        """With neither check on the door never calls them: nothing to
        evaluate, so nothing to reject."""
        res = _result(exc=RuntimeError("boom"))
        ok = _search(reject_tensile=False,
                     check_m_alpha=False)._is_admissible(res)
        assert ok is True and res.admissible is True
