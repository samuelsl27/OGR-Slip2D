# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.212 — stage 1 of the multi-stage rapid drawdown no longer fixes the
consolidation state from a pass that did not converge, and no longer drops
the verdict its own method gave on it (defect D202).

THE INVARIANTS.

1. A stage-1 pass that comes back with a factor but ``converged=False``
   makes ``rapid_drawdown_fos`` raise ``DrawdownStageUnconverged`` (a
   ``DrawdownStageFailed``), and ``MultiStageDrawdownMethod`` returns the
   surface INVALID: ``fos=None``, the pass's own reason, the unconverged
   factor in ``details["drawdown_stage_fos"]`` and -111 in the export.
   Nothing past stage 1 runs. It is checked BEFORE the precondition
   FS1 >= 1, so an unconverged FS1 < 1 is not reported as "the procedure
   does not apply": that is a claim about the slope, and an unconverged
   factor supports no claim about the slope.
2. A stage-1 pass that converged but that its own method declared
   INADMISSIBLE (Spencer and GLE with the inter-slice thrust relaxed)
   leaves the drawdown result inadmissible, with a note naming stage 1 and
   the same factor of safety: the method's verdict on the state everything
   else is built from, carried as it would be in an ordinary analysis.

WHAT WAS WRONG. Stage 1 was checked for having a factor and for being >= 1,
and for nothing else. ``_stage1_state`` then fixed sigma'_fc and
tau_fc = s / FS1 on every slice from a pass that was not a solution. Since
D112b (v0.1.210) the verdict that travels with the answer is the one of the
pass that PRODUCED it, stage 2 or 3, so a stage 2 or 3 that produces the
answer without converging already makes the surface invalid. Stage 1 FIXES
state instead of iterating it and never produces the answer, so its verdict
was always dropped.

THE WITNESS IS NATURAL, AND ON A PUBLISHED SECTION. On the Appendix G slope
of EM 1110-2-1902 (Corps of Engineers 1970, 2003), the fixture of
``test_drawdown_usace_v169``, the prescribed-inclination family cannot
bracket the circle (69, 110, 89.159...) at the full reservoir. Corps of
Engineers #1 and #2 hand back F1 = 5.0, the TOP of their own sampling grid
(``REASON_NO_FORCE_BRACKET``), and with tau_fc = s / 5.0 the drawdown came
back VALID at 1.7093, where Bishop (1955) and Spencer (1967), which converge
on the same circle at F1 ~= 1.85, give 1.947. That error has no fixed
sign: tau_fc is inversely proportional to F1, so a fallback BELOW the true
F1 raises the undrained strength instead, which is the unsafe side.

THE DECISION (the owner's, 2026-09-27). Invalid with the pass's reason,
which is the rule D112b applies to stages 2 and 3 and D194 to a stage with
no factor at all. And an inadmissible stage 1 belongs to the same defect,
because it is the same verdict lost, so it comes back inadmissible with a
note. A stage 2 that does not converge while the drained cap does is only
MEASURED here: the ficha forbids touching what D112b, D194 and D200 do with
stages 2 and 3. It is open as D203.

WHY TWO CASES ARE SYNTHETIC. Bishop's own ``not_converged`` (the last
iterate) and an inadmissible stage 1 are not reached by any published case,
so Bishop marks its FIRST call, which is stage 1, on the published
Pilarcitos case (Duncan, Wright & Wong 1990) of ``test_rapid_drawdown_v168``.
The census of the bank's problems 095-098 says how often the real ones
occur (``_tools/censo_p3_desembalse.py --salida D202_etapa1``).

DISCRIMINATION against the v0.1.211 tree. MEASURED, by copying this file into
a ``git worktree`` at 03c9447 and running it there -- not predicted. Of the
16 cases, **10 fail and 6 pass**, all ten by BEHAVIOUR:

  fail  the_witness_comes_back_invalid_with_its_reason  (valid, 1.7093)
        rapid_drawdown_fos_raises_the_declared_error   (accepted)
        nothing_past_stage_one_runs                    (18 calls, not 1)
        the_last_iterate_is_refused_too                (valid)
        an_unconverged_factor_below_one_is_not_called_not_applicable
                                                       ("not applicable")
        a_search_counts_it_invalid_and_carries_on      (valid)
        the_export_writes_no_converged_factor          (no code: valid)
        the_verdict_travels_with_a_note_naming_stage_one  (admitted)
        the_export_writes_any_other_rejection          (no code: admitted)
        the_verdict_travels_through_the_cycling_branch_too  (admitted)

  pass  the two witness guards, the_factor_is_the_one_the_unmarked_method_
        reaches and the three controls of TestWhatDoesNotMove.

The 18 calls are the witness on v0.1.211: stage 1, stage 2 and sixteen
passes of the drained cap, all built on a stage-1 state that was the top
of a sampling grid. The run is archived in the bank as
``_auditoria/D202_etapa1/discriminacion_d202_test_v1212_en_0.1.211.txt``.
"""
from __future__ import annotations

import math

N_SLICES = 25        # Pilarcitos, as in test_rapid_drawdown_v168
N_APPG = 50          # the Appendix G slope, as in test_drawdown_usace_v169
DW = "duncan_wright"

#: The circle of the ficha. Its full-reservoir pass is the one the
#: prescribed-inclination family cannot bracket.
WITNESS = dict(centre_x=69.0, centre_y=110.0, radius=89.15947223075534)

#: The top of the F grid the prescribed-inclination family samples
#: (``PrescribedInclinationMethod._force_balance``), which is what it hands
#: back as its "sampled F of smallest residual" on the witness.
GRID_TOP = 5.0


# ----------------------------------------------------------------------
def _appg():
    from test_drawdown_usace_v169 import _appendix_g
    return _appendix_g()                 # Duncan-Wright-Wong, 103 -> 24 ft


def _witness():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**WITNESS)


def _pilarcitos():
    from test_rapid_drawdown_v168 import _circle, _pilarcitos
    return _pilarcitos(), _circle()


def _stage1(method, project, surface, n):
    """What the method alone answers at the full reservoir."""
    from ogr_slip2d.rapid_drawdown import level_project
    from ogr_slip2d.slicer import slice_surface
    p1 = level_project(project, use_drawdown=False)
    return method.compute_fos(p1, surface,
                              slice_surface(p1, surface, num_slices=n))


def _wrapped(inner, project, surface, n):
    from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
    from ogr_slip2d.slicer import slice_surface
    return MultiStageDrawdownMethod(inner, DW, num_slices=n).compute_fos(
        project, surface, slice_surface(project, surface, num_slices=n))


def _bishop(mark, fos=None):
    """Bishop whose FIRST call -- stage 1 -- returns its own result, marked.

    ``"unconverged"``: ``converged=False`` with ``REASON_NOT_CONVERGED`` and
    the shared note, the last iterate of an iteration that ran out of
    passes (with ``fos`` in place of its own factor if given).
    ``"inadmissible"``: ``admissible=False`` with a note, the way Spencer and
    GLE mark a relaxed inter-slice thrust.
    """
    from ogr_slip2d.methods.base import REASON_NOT_CONVERGED
    from ogr_slip2d.methods.bishop import BishopSimplified

    class _Marked(BishopSimplified):
        calls = 0

        def compute_fos(self, project, surface, slices):
            self.calls += 1
            r = super().compute_fos(project, surface, slices)
            if self.calls == 1 and mark == "unconverged":
                if fos is not None:
                    r.fos = fos
                r.converged = False
                r.error_message = self.NOT_CONVERGED_NOTE
                r.reason = REASON_NOT_CONVERGED
            elif self.calls == 1 and mark == "inadmissible":
                r.admissible = False
                r.admissibility_note = "synthetic: the thrust is relaxed"
            return r

    return _Marked()


# ======================================================================
class TestTheWitnessIsReal:
    """Guards: without these the cases below prove nothing."""

    def test_corps_cannot_bracket_stage_one_on_this_circle(self):
        from ogr_slip2d.methods.base import REASON_NO_FORCE_BRACKET
        from ogr_slip2d.methods.modified_swedish import (CorpsOfEngineers1,
                                                         CorpsOfEngineers2)
        p, c = _appg(), _witness()
        for cls in (CorpsOfEngineers1, CorpsOfEngineers2):
            r1 = _stage1(cls(), p, c, N_APPG)
            assert r1.fos is not None and not r1.converged, (
                cls.__name__, r1.fos, r1.converged)
            assert r1.reason == REASON_NO_FORCE_BRACKET, r1.reason
            # The fallback is the top of the sampling grid, so the old
            # precondition FS1 >= 1 let it through.
            assert math.isclose(r1.fos, GRID_TOP, rel_tol=1e-12), r1.fos

    def test_the_circle_itself_is_solvable(self):
        """Bishop and Spencer converge on it: what fails is the family's
        bracket, not the slope."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.spencer import Spencer
        p, c = _appg(), _witness()
        for m in (BishopSimplified(), Spencer()):
            r1 = _stage1(m, p, c, N_APPG)
            assert r1.converged and r1.fos > 1.0, (m.METHOD_ID, r1.fos)


class TestAnUnconvergedStageOneInvalidatesTheSurface:

    def test_the_witness_comes_back_invalid_with_its_reason(self):
        from ogr_slip2d.methods.base import REASON_NO_FORCE_BRACKET
        from ogr_slip2d.methods.modified_swedish import (CorpsOfEngineers1,
                                                         CorpsOfEngineers2)
        p, c = _appg(), _witness()
        for cls in (CorpsOfEngineers1, CorpsOfEngineers2):
            w = _wrapped(cls(), p, c, N_APPG)
            assert w.fos is None and not w.is_valid, (cls.__name__, w.fos)
            assert w.reason == REASON_NO_FORCE_BRACKET, w.reason
            assert "Stage 1" in w.error_message, w.error_message
            assert w.details["drawdown_stage_failed"] == 1
            assert math.isclose(w.details["drawdown_stage_fos"], GRID_TOP,
                                rel_tol=1e-12)

    def test_rapid_drawdown_fos_raises_the_declared_error(self):
        # Caught as ANY exception and named by its class, as in the D194
        # test, so that on a tree without the class this fails on the
        # behaviour and not on an import.
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        try:
            rapid_drawdown_fos(_appg(), _witness(), CorpsOfEngineers1(),
                               num_slices=N_APPG, procedure=DW)
        except Exception as exc:                            # noqa: BLE001
            names = [k.__name__ for k in type(exc).__mro__]
            assert names[0] == "DrawdownStageUnconverged", names
            assert "DrawdownStageFailed" in names, names
            assert exc.stage == 1
            return
        raise AssertionError("an unconverged stage 1 was accepted")

    def test_nothing_past_stage_one_runs(self):
        """The inner method is asked ONCE: no undrained strength is built
        from a state that is not a solution."""
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1

        class _Counting(CorpsOfEngineers1):
            calls = 0

            def compute_fos(self, project, surface, slices):
                self.calls += 1
                return super().compute_fos(project, surface, slices)

        m = _Counting()
        _wrapped(m, _appg(), _witness(), N_APPG)
        assert m.calls == 1, m.calls

    def test_the_last_iterate_is_refused_too(self):
        """Not only the fallback of a sampled grid: Bishop's own
        ``not_converged``, on the published Pilarcitos case."""
        from ogr_slip2d.methods.base import REASON_NOT_CONVERGED
        p, c = _pilarcitos()
        w = _wrapped(_bishop("unconverged"), p, c, N_SLICES)
        assert w.fos is None and not w.is_valid
        assert w.reason == REASON_NOT_CONVERGED, w.reason
        assert w.details["drawdown_stage_failed"] == 1

    def test_an_unconverged_factor_below_one_is_not_called_not_applicable(
            self):
        from ogr_slip2d.methods.base import (REASON_DRAWDOWN_NOT_APPLICABLE,
                                             REASON_NOT_CONVERGED)
        p, c = _pilarcitos()
        w = _wrapped(_bishop("unconverged", fos=0.8), p, c, N_SLICES)
        assert not w.is_valid
        assert w.reason == REASON_NOT_CONVERGED, w.reason
        assert w.reason != REASON_DRAWDOWN_NOT_APPLICABLE

    def test_a_search_counts_it_invalid_and_carries_on(self):
        from ogr_slip2d.methods.base import REASON_NO_FORCE_BRACKET
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.search import GridSearch
        search = GridSearch(method=MultiStageDrawdownMethod(
            CorpsOfEngineers1(), DW, num_slices=N_APPG),
            num_slices=N_APPG, min_area=0.0)
        res = search.evaluate_circle(_appg(), _witness())
        assert res is not None and not res.is_valid
        assert res.reason == REASON_NO_FORCE_BRACKET, res.reason

    def test_the_export_writes_no_converged_factor(self):
        from ogr_slip2d.interpretation import ERROR_NOT_CONVERGED, error_code
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        w = _wrapped(CorpsOfEngineers1(), _appg(), _witness(), N_APPG)
        assert error_code(w) == ERROR_NOT_CONVERGED, error_code(w)


class TestAnInadmissibleStageOneLeavesTheSurfaceInadmissible:

    def test_the_verdict_travels_with_a_note_naming_stage_one(self):
        p, c = _pilarcitos()
        w = _wrapped(_bishop("inadmissible"), p, c, N_SLICES)
        assert w.is_valid, w.error_message       # the factor is kept
        assert not w.admissible
        assert w.admissibility_note.startswith("Stage 1"), (
            w.admissibility_note)
        assert "synthetic: the thrust is relaxed" in w.admissibility_note
        # A verdict of the method, not a post-analysis screen (D177).
        assert w.admissibility_reason == ""
        assert w.details["stage1_admissible"] is False

    def test_the_export_writes_any_other_rejection(self):
        from ogr_slip2d.interpretation import ERROR_OTHER, error_code
        p, c = _pilarcitos()
        w = _wrapped(_bishop("inadmissible"), p, c, N_SLICES)
        assert error_code(w) == ERROR_OTHER, error_code(w)

    def test_the_verdict_travels_through_the_cycling_branch_too(self):
        """With no single pass behind the answer (the drained cap reported
        at the centre of its cycle) the flags are built from nothing but
        the horns, and the stage-1 verdict has to be added to those too."""
        import ogr_slip2d.rapid_drawdown as rd
        from ogr_slip2d.slicer import slice_surface
        p, c = _pilarcitos()
        sl = slice_surface(p, c, num_slices=N_SLICES)
        original = rd.rapid_drawdown_fos

        def _cycling(*a, **k):
            out = original(*a, **k)
            horn = out.final_result
            out.final_result = None
            out.cycle_horns = (horn, horn)
            return out

        rd.rapid_drawdown_fos = _cycling
        try:
            w = rd.MultiStageDrawdownMethod(
                _bishop("inadmissible"), DW,
                num_slices=N_SLICES).compute_fos(p, c, sl)
        finally:
            rd.rapid_drawdown_fos = original
        assert w.is_valid and not w.admissible, (w.is_valid, w.admissible)
        assert w.admissibility_note.startswith("Stage 1"), (
            w.admissibility_note)

    def test_the_factor_is_the_one_the_unmarked_method_reaches(self):
        """Control (passes on v0.1.211 too): only the verdict changes, and
        every stage's number is the plain method's, bit for bit."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        p, c = _pilarcitos()
        a = rapid_drawdown_fos(p, c, BishopSimplified(), num_slices=N_SLICES,
                               procedure=DW)
        b = rapid_drawdown_fos(p, c, _bishop("inadmissible"),
                               num_slices=N_SLICES, procedure=DW)
        assert (a.fos, a.fos_stage1, a.fos_stage2, a.fos_stage3,
                a.n_cap_passes) == (b.fos, b.fos_stage1, b.fos_stage2,
                                    b.fos_stage3, b.n_cap_passes)


class TestWhatDoesNotMove:
    """Controls: these pass on v0.1.211 as well."""

    def test_a_converged_stage_one_is_untouched(self):
        """On the circle the Appendix G publishes, stage 1 converges, and
        the surface comes back valid and admissible with the factor
        ``rapid_drawdown_fos`` reaches."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        from test_drawdown_usace_v169 import _circle
        p = _appg()
        for cls in (CorpsOfEngineers1, BishopSimplified):
            w = _wrapped(cls(), p, _circle(), N_APPG)
            assert w.is_valid and w.admissible, (cls.__name__, w.reason)
            r = rapid_drawdown_fos(p, _circle(), cls(), num_slices=N_APPG,
                                   procedure=DW)
            assert w.fos == r.fos, (cls.__name__, w.fos, r.fos)

    def test_a_converged_stage_one_below_one_is_still_not_applicable(self):
        """Lowe-Karafiath CONVERGES on the witness at the full reservoir,
        below 1: the slope is unstable before the drawdown there, and that
        is still the procedure's precondition, not a failed calculation."""
        from ogr_slip2d.methods.base import REASON_DRAWDOWN_NOT_APPLICABLE
        from ogr_slip2d.methods.lowe_karafiath import LoweKarafiath
        p, c = _appg(), _witness()
        r1 = _stage1(LoweKarafiath(), p, c, N_APPG)
        assert r1.converged and r1.fos < 1.0, (r1.converged, r1.fos)
        w = _wrapped(LoweKarafiath(), p, c, N_APPG)
        assert not w.is_valid
        assert w.reason == REASON_DRAWDOWN_NOT_APPLICABLE, w.reason

    def test_bishop_and_spencer_on_the_witness_are_untouched(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.spencer import Spencer
        p, c = _appg(), _witness()
        for cls in (BishopSimplified, Spencer):
            w = _wrapped(cls(), p, c, N_APPG)
            assert w.is_valid and w.admissible, (
                cls.__name__, w.reason, w.admissibility_note)
