# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.211 — a stage of the multi-stage rapid drawdown whose method produces
no factor of safety makes the SURFACE invalid, with that pass's own reason,
instead of ending the whole run (defect D194).

THE INVARIANT. Whatever stage fails -- stage 1 (full reservoir), stage 2
(undrained strengths) or any pass of stage 3 (the drained cap) --
``rapid_drawdown_fos`` raises ``DrawdownStageFailed`` naming the stage, and
``MultiStageDrawdownMethod`` returns ``fos=None`` with the reason the inner
pass gave (``REASON_NON_PHYSICAL_FOS`` if it gave none). A search that meets
such a surface counts it as invalid and carries on. "The procedure does not
apply" (``REASON_DRAWDOWN_NOT_APPLICABLE``) stays for the procedure's
preconditions.

WHAT WAS WRONG. Since D56 (v0.1.152) a method with no factor returns
``fos=None``, and the drained cap tested ``math.isfinite(r3.fos)``: a
``TypeError`` that neither the wrapper (``RapidDrawdownError``) nor
``BaseSearch._analyse`` (``ArithmeticError``) catches, so one surface ended
the search. Stages 1 and 2 did check for None, but turned it into
"not applicable", which is a claim about the slope, not about the solver.
The owner's decision (2026-09-26): invalid with the pass's reason in all
three stages, and NOT the last pass that had a factor -- the cap only lowers
strengths, so an earlier pass is an upper bound on the capped factor.

WHY A SYNTHETIC FAILURE. On the verification bank no drawdown pass of
problems 095-098 comes back without a factor (``_tools/censo_p3_desembalse.py``),
so the failing pass is made: Bishop, returning ``fos=None`` on its k-th call
(the reproduction in the ficha). The fixture is the published Pilarcitos
case (Duncan, Wright & Wong 1990), validated in
``tests/test_rapid_drawdown_v168.py``, whose drained cap takes several
passes on this circle -- guarded below, since a cap that never ran would
make the stage-3 cases vacuous.

DISCRIMINATION against the v0.1.210 tree. MEASURED, by copying this file into
a ``git worktree`` at e983574 and running it there. Of the 10 cases, **7 fail
and 3 pass**:

  fail  a_cap_pass_raises_the_declared_error        (behaviour: TypeError)
        the_second_cap_pass_is_named                (behaviour: TypeError)
        the_wrapper_returns_the_surface_invalid_with_its_reason
                                                    (behaviour: TypeError)
        a_pass_with_no_reason_falls_back            (behaviour: TypeError)
        a_search_survives_it                        (behaviour: TypeError)
        stages_one_and_two_carry_their_reason_too   (behaviour: "not
                                                     applicable")
        it_is_still_a_rapid_drawdown_error          (WEAK: a class)

  pass  the_drained_cap_takes_several_passes (guard) and the two controls.

The run is archived in the bank as
``_auditoria/D194_D200_casquete/discriminacion_d194_test_v1211_en_0.1.210.txt``.
"""
from __future__ import annotations

N_SLICES = 25
DW = "duncan_wright"


def _failing(k, reason="m_alpha_collapsed"):
    """Bishop that returns no factor on its ``k``-th call (1 = stage 1,
    2 = stage 2, 3 = the first pass of the drained cap, 4 = the second)."""
    from ogr_slip2d.methods.base import LEMResult
    from ogr_slip2d.methods.bishop import BishopSimplified

    class _Failing(BishopSimplified):
        calls = 0

        def compute_fos(self, project, surface, slices):
            self.calls += 1
            if self.calls == k:
                return LEMResult(fos=None, converged=False, iterations=0,
                                 method_id=self.METHOD_ID, surface=surface,
                                 slices=slices, error_message="synthetic",
                                 reason=reason)
            return super().compute_fos(project, surface, slices)

    return _Failing()


def _fixture():
    from ogr_slip2d.slicer import slice_surface
    from test_rapid_drawdown_v168 import _circle, _pilarcitos
    p, c = _pilarcitos(), _circle()
    return p, c, slice_surface(p, c, num_slices=N_SLICES)


def _raised(k):
    """What ``rapid_drawdown_fos`` raises when call ``k`` has no factor."""
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    p, c, _sl = _fixture()
    try:
        rapid_drawdown_fos(p, c, _failing(k), num_slices=N_SLICES,
                           procedure=DW)
    except Exception as exc:                                # noqa: BLE001
        return exc
    raise AssertionError("call %d without a factor was accepted" % k)


def _wrapped(k, reason="m_alpha_collapsed"):
    from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
    p, c, sl = _fixture()
    return MultiStageDrawdownMethod(_failing(k, reason), DW,
                                    num_slices=N_SLICES).compute_fos(p, c, sl)


# ======================================================================
class TestTheFixtureReachesTheCap:
    """Guard: without two capped passes the stage-3 cases prove nothing."""

    def test_the_drained_cap_takes_several_passes(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        p, c, _sl = _fixture()
        res = rapid_drawdown_fos(p, c, BishopSimplified(),
                                 num_slices=N_SLICES, procedure=DW)
        assert res.n_cap_passes >= 2, res.n_cap_passes


class TestAStageWithoutAFactor:

    # The exception is caught as ANY exception and named by its class, so
    # that on a tree without ``DrawdownStageFailed`` these cases fail on
    # the TypeError the code raises, not on an import.

    def test_a_cap_pass_raises_the_declared_error(self):
        exc = _raised(3)
        assert type(exc).__name__ == "DrawdownStageFailed", repr(exc)
        assert exc.stage == 3
        assert exc.result.reason == "m_alpha_collapsed"
        assert "pass 1" in str(exc), str(exc)

    def test_the_second_cap_pass_is_named(self):
        exc = _raised(4)
        assert type(exc).__name__ == "DrawdownStageFailed", repr(exc)
        assert exc.stage == 3 and "pass 2" in str(exc), str(exc)

    def test_the_wrapper_returns_the_surface_invalid_with_its_reason(self):
        w = _wrapped(3)
        assert w.fos is None and not w.is_valid
        assert w.reason == "m_alpha_collapsed", w.reason
        assert "Stage 3" in w.error_message, w.error_message
        assert w.details["drawdown_stage_failed"] == 3

    def test_stages_one_and_two_carry_their_reason_too(self):
        from ogr_slip2d.methods.base import REASON_DRAWDOWN_NOT_APPLICABLE
        for k in (1, 2):
            w = _wrapped(k, reason="active_support_exceeds_driving")
            assert not w.is_valid, k
            assert w.reason == "active_support_exceeds_driving", (k, w.reason)
            assert w.reason != REASON_DRAWDOWN_NOT_APPLICABLE
            assert w.details["drawdown_stage_failed"] == k

    def test_a_pass_with_no_reason_falls_back(self):
        from ogr_slip2d.methods.base import ALL_REASONS, REASON_NON_PHYSICAL_FOS
        w = _wrapped(3, reason="")
        assert w.reason == REASON_NON_PHYSICAL_FOS
        assert w.reason in ALL_REASONS

    def test_a_search_survives_it(self):
        """The whole point: one such surface no longer ends the run."""
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.search import GridSearch
        p, c, _sl = _fixture()
        search = GridSearch(method=MultiStageDrawdownMethod(
            _failing(3), DW, num_slices=N_SLICES),
            num_slices=N_SLICES, min_area=0.0)
        res = search.evaluate_circle(p, c)
        assert res is not None and not res.is_valid
        assert res.reason == "m_alpha_collapsed"

    def test_it_is_still_a_rapid_drawdown_error(self):
        """Guard: a caller that refuses a drawdown on that error keeps
        refusing it."""
        from ogr_slip2d.rapid_drawdown import (DrawdownStageFailed,
                                               RapidDrawdownError)
        assert issubclass(DrawdownStageFailed, RapidDrawdownError)


class TestWhatDoesNotMove:
    """Controls: these pass on v0.1.210 as well."""

    def test_a_slope_unstable_before_the_drawdown_is_still_not_applicable(
            self):
        from ogr_core.materials import MohrCoulomb
        from ogr_slip2d.methods.base import REASON_DRAWDOWN_NOT_APPLICABLE
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        p, c, sl = _fixture()
        for m in p.materials:
            m.strength = MohrCoulomb(cohesion=0.0, friction_angle=12.0)
        w = MultiStageDrawdownMethod(BishopSimplified(), DW,
                                     num_slices=N_SLICES).compute_fos(p, c, sl)
        assert not w.is_valid
        assert w.reason == REASON_DRAWDOWN_NOT_APPLICABLE, w.reason

    def test_a_method_that_always_answers_keeps_its_number(self):
        """A pass-through subclass reaches the same factor, stage by stage,
        as the method itself: the new guards cost nothing on the path with
        a factor."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        p, c, _sl = _fixture()
        a = rapid_drawdown_fos(p, c, BishopSimplified(), num_slices=N_SLICES,
                               procedure=DW)
        b = rapid_drawdown_fos(p, c, _failing(10 ** 6), num_slices=N_SLICES,
                               procedure=DW)
        assert (a.fos, a.fos_stage1, a.fos_stage2, a.fos_stage3,
                a.n_cap_passes) == (b.fos, b.fos_stage1, b.fos_stage2,
                                    b.fos_stage3, b.n_cap_passes)
        assert a.fos_stage3 <= a.fos_stage2        # the cap only lowers
