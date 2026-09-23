# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.192 — a surface rejected by the Tensile Stress Check is exported as
-120, the code the reference gives it, and not as the generic -101.

THE INVARIANT. *Export Raw Data* writes, for every surface a search
analysed, its factor of safety or a negative error code in its place. The
window decided the code by reading the NOTE: "m_alpha" in it gave -112, a
factor that did not converge -111, and everything else -101 (defect D177).
The engine's own note for the tensile screen says "(error -120)", and -120
is the code the reference defines for "tensile effective normal stress on
the base of a slice exceeds the tensile strength of the material" — yet the
export filed it with the generic failures. Since v0.1.191 (D165) a rock
surface can be admitted or rejected by its tension, which is what made the
distinction worth drawing.

The fix gives the screen a MACHINE-READABLE reason instead of making the
window guess from prose: ``LEMResult.admissibility_reason``, set by
``BaseSearch._is_admissible`` from ``checks.screen_surface``, with the
values in ``methods.base.ALL_SCREENS``. It is kept out of ``reason`` on
purpose: ``reason`` is the machine half of ``error_message`` and is empty on
a result that succeeded, and a screened surface has a perfectly converged
factor of safety.

What must NOT move, and is checked here: -112 for the m-alpha screen, -111
for a factor that did not converge, the note text the engine writes (read
by the search, by Optimize Surfaces and by this window).

THE ANCHOR is the reference's own code table, not a captured export: each
row is built so that exactly one of the four conditions holds, and the
screened ones go through the REAL ``_is_admissible`` of a search, so the
reason is the one the engine records and not one set by hand.

WHAT THIS FILE DISCRIMINATES against the v0.1.191 tree. MEASURED, by copying
this file into a ``git worktree`` at that commit and running it there. Of
the 9 cases, **8 fail and 1 passes**, and the eight are not equal:

  fail  every_tensile_rejection_exports_as_minus_120  (BEHAVIOUR: exports
                                                       '-101'; imports
                                                       nothing new)
        tension_is_minus_120                          (BEHAVIOUR)
        a_tension_rejection_carries_its_reason        (WEAK: fails on the
        an_m_alpha_rejection_carries_its_reason        absence of
        check_surface_keeps_its_two_value_contract     ``SCREEN_*``,
        the_reason_travels_in_to_dict                  ``ALL_SCREENS`` or
        the_screens_are_not_failure_reasons            ``screen_surface``)
        a_result_screened_by_both_is_reported_as_...

  pass  the_other_three_codes_do_not_move             (guard: -112, -111
                                                       and -101 must not
                                                       move, and did not)

Six of the eight fail only because a name did not exist, which is weak
discrimination and is said so. The end-to-end case was added for exactly
that reason: before it, one test in eight failed on behaviour.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except Exception:  # noqa: BLE001
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


#: A circle for the rows' geometry. ``_raw_data_rows`` asks every surface
#: for ``to_dict()``, so a result without one cannot be exported at all.
_CIRCLE = (40.0, 60.0, 30.0)


def _tension_rejected():
    """A converged result with one slice base in tension on a soil (whose
    tensile allowance is zero), screened by a real search."""
    from test_tensile_strength_rock_v1191 import _flat_result

    from ogr_core.materials import MohrCoulomb
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    res = _flat_result([-10.0] + [5.0] * 9,
                       MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    res.surface = SlipCircle(*_CIRCLE)
    search = GridSearch(method=BishopSimplified(), reject_tensile=True,
                        check_m_alpha=False)
    assert search._is_admissible(res) is False
    return res


def _m_alpha_rejected():
    """The degenerate wedge of ``test_checks_v132``, which the m-alpha
    screen rejects, screened by a real search with ONLY that check on."""
    from test_checks_v132 import _DEGENERATE, _eval_poly
    res = _eval_poly(_DEGENERATE, check_m_alpha=True)
    assert res is not None and res.is_valid and res.admissible is False
    return res


def _not_converged():
    from ogr_slip2d.methods.base import REASON_NOT_CONVERGED, LEMResult
    from ogr_slip2d.surface import SlipCircle
    return LEMResult(fos=1.2, converged=False, iterations=50,
                     method_id="bishop_simplified",
                     surface=SlipCircle(*_CIRCLE), slices=[],
                     error_message="did not converge",
                     reason=REASON_NOT_CONVERGED)


def _generic_inadmissible():
    """Converged, inadmissible, and by neither screen — the shape the
    relaxed-thrust flag of the lambda solver has."""
    from ogr_slip2d.methods.base import LEMResult
    from ogr_slip2d.surface import SlipCircle
    return LEMResult(fos=1.3, converged=True, iterations=5,
                     method_id="spencer", surface=SlipCircle(*_CIRCLE),
                     slices=[], admissible=False,
                     admissibility_note="interslice thrust relaxed")


def _codes(*results):
    from ogr_gui.interpret_window import InterpretWindow
    fake = SimpleNamespace(search_result=SimpleNamespace(
        evaluations=list(results)))
    return [row[5] for row in InterpretWindow._raw_data_rows(fake)]


# ======================================================================
class TestTheEngineNamesTheScreen:

    def test_a_tension_rejection_carries_its_reason(self):
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        res = _tension_rejected()
        assert res.admissibility_reason == SCREEN_TENSILE_STRESS
        # The note is the one the engine always wrote, untouched.
        assert res.admissibility_note == \
            "tensile stress on 1 slice base(s) (error -120)"
        # And the contract of ``reason``: empty, because it succeeded.
        assert res.reason == "" and res.is_valid

    def test_an_m_alpha_rejection_carries_its_reason(self):
        from ogr_slip2d.methods.base import SCREEN_M_ALPHA
        res = _m_alpha_rejected()
        assert res.admissibility_reason == SCREEN_M_ALPHA
        assert "m_alpha" in res.admissibility_note
        assert res.reason == ""

    def test_the_screens_are_not_failure_reasons(self):
        from ogr_slip2d.methods.base import ALL_REASONS, ALL_SCREENS
        assert ALL_SCREENS and not (ALL_SCREENS & ALL_REASONS)

    def test_check_surface_keeps_its_two_value_contract(self):
        """Every existing caller unpacks two values; the third lives in
        ``screen_surface``, which ``check_surface`` wraps."""
        from ogr_slip2d.checks import check_surface, screen_surface
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        res = _tension_rejected()
        ok, note = check_surface(res, tensile=True)
        ok3, screen, note3 = screen_surface(res, tensile=True)
        assert (ok, note) == (ok3, note3) == (False, res.admissibility_note)
        assert screen == SCREEN_TENSILE_STRESS

    def test_the_reason_travels_in_to_dict(self):
        """On a result the engine produced end to end (the hand-built one
        carries its slices as a bare list, which ``to_dict`` cannot walk),
        and through the strict JSON encoder the suite uses for D56."""
        import json
        from ogr_slip2d.methods.base import SCREEN_M_ALPHA
        d = _m_alpha_rejected().to_dict()
        assert d["admissibility_reason"] == SCREEN_M_ALPHA
        back = json.loads(json.dumps(d, allow_nan=False))
        assert back["admissibility_reason"] == SCREEN_M_ALPHA


# ======================================================================
@_requires_qt
class TestTheExportWritesTheReferenceCode:

    def test_tension_is_minus_120(self):
        assert _codes(_tension_rejected()) == ["-120"]

    def test_the_other_three_codes_do_not_move(self):
        assert _codes(_m_alpha_rejected(), _not_converged(),
                      _generic_inadmissible()) == ["-112", "-111", "-101"]

    def test_a_result_screened_by_both_is_reported_as_tension(self):
        """``screen_surface`` tests tension first and stops, so a surface
        failing both screens is recorded — and exported — as tension."""
        from test_checks_v132 import _DEGENERATE, _eval_poly
        from ogr_slip2d.checks import screen_surface
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        res = _eval_poly(_DEGENERATE, reject_tensile=True,
                         check_m_alpha=True)
        ok_t, _s, _n = screen_surface(res, tensile=True, m_alpha=False)
        ok_m, _s, _n = screen_surface(res, tensile=False, m_alpha=True)
        if ok_t or ok_m:
            # Not a case that fails both: say so instead of passing empty.
            raise AssertionError(f"the wedge does not fail both screens "
                                 f"(tensile ok={ok_t}, m-alpha ok={ok_m})")
        assert res.admissibility_reason == SCREEN_TENSILE_STRESS
        assert _codes(res) == ["-120"]


_WINDOWS = []


# ======================================================================
@_requires_qt
class TestARealSearchThroughTheRealWindow:
    """End to end, and importing nothing that v0.1.191 lacked: a grid search
    on the Ej1 slope with the tensile check on, shown in the interpretation
    window the user exports from. The rows are picked by the engine's NOTE,
    which both trees write, so on the old tree this fails on what it
    exports and not on a missing name."""

    def test_every_tensile_rejection_exports_as_minus_120(self):
        from test_slide_validation_ej1 import _ej1_project

        import ogr_slip2d as M
        from ogr_gui.i18n import set_language
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.search import GridSearch
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        r = GridSearch(method=M.BishopSimplified(), grid_x=(70, 100),
                       grid_y=(58, 84), grid_nx=4, grid_ny=4,
                       radius_increment=8, min_radius=12, num_slices=14,
                       min_area=0.5, reject_tensile=True,
                       check_m_alpha=True).run(p)
        w = InterpretWindow(p, {"bishop_simplified": r}, None)
        _WINDOWS.append(w)
        rows = w._raw_data_rows()
        assert len(rows) == len(r.evaluations)
        tensile = [row[5] for ev, row in zip(r.evaluations, rows)
                   if "(error -120)" in (ev.admissibility_note or "")]
        # Guard on the guard: the case has to contain the thing it tests.
        assert tensile, "no surface of this grid failed the tensile check"
        assert set(tensile) == {"-120"}, sorted(set(tensile))
        # And -120 is not handed to anything else.
        others = [row[5] for ev, row in zip(r.evaluations, rows)
                  if "(error -120)" not in (ev.admissibility_note or "")]
        assert "-120" not in others
