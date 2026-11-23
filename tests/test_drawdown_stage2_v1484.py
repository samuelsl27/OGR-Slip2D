# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.484 — a stage 2 of the multi-stage rapid drawdown that did not converge
only seeds the drained cap: it is no longer compared with stage 3, nor
published as the factor of stage 2 (defect D203).

THE INVARIANTS.

1. When the stage-2 pass comes back with a factor but ``converged=False``,
   ``rapid_drawdown_fos`` reports ``fos_stage2=None``,
   ``stage2_converged=False`` and the number it stopped at in
   ``stage2_unconverged_fos``. ``MultiStageDrawdownMethod`` publishes the
   same three in ``details``.
2. The answer is then the drained cap's own (``fos == fos_stage3``), with
   the verdict of the pass that produced it (D112b). A reserve factor that
   happens to lie BELOW the cap's fixed point no longer "wins" the
   comparison and hands the surface the unconverged pass. Before, the
   surface was invalid at the reserve.
3. Without a cap to solve it (Lowe-Karafiath's procedure), the answer is
   still the unconverged pass, invalid with its own reason, as before.

WHAT IS NOT MOVED, AND WHY THE DECISION. The owner chose this over
invalidating the surface on two measurements (2026-11-23,
``_tools/sonda_d203.py`` of the bank, ``_auditoria/D203_etapa2/``):

* the cap's fixed point does not depend on its seed (five seeds on the
  critical circle of problem 096, spread 9e-6 < ``CAP_TOL``);
* none of the 1193 unconverged stage-2 passes with a factor in the
  sixteen searches of problems 095-098 moves a minimum or a count of valid
  surfaces.

A converged stage 2 keeps the comparison exactly as it was.

THE WITNESS IS NATURAL, AND ON A PUBLISHED SECTION. The critical circle of
the bank's problem 096, (207.25, 183.333333, 110.79583), on the Appendix G
slope of EM 1110-2-1902, the fixture of ``test_drawdown_usace_v169``.
Corps of Engineers #1 and #2 and Lowe-Karafiath converge at the full
reservoir. At the drawn-down level they cannot bracket stage 2 and hand
back F2 = 5.0, the top of their own F grid (``REASON_NO_FORCE_BRACKET``).
Bishop (1955) converges there at F2 ~= 5.54. The drained cap converges
from that seed in 16 passes. The guards of ``TestTheWitnessIsReal`` say
so, or the cases below prove nothing.

WHY ONE CASE IS SYNTHETIC. A reserve below the fixed point is reached by
no case of the bank, where the reserve is always the top of the grid. So
Corps #1 is marked on its SECOND call (stage 2) with a reserve of 1.0.

DISCRIMINATION against the v0.1.483 tree. MEASURED, by copying this file
into a ``git worktree`` at cc6c2c0 and running it there. Of the 12 cases,
**4 fail and 8 pass**:

  fail  it_is_not_published_as_the_factor_of_stage_two   (5.0)
        the_wrapper_publishes_the_three                  (5.0)
        a_reserve_below_the_fixed_point_does_not_win     (1.0)
        lowe_karafiaths_procedure_stays_invalid          (5.0)

  pass  the four guards, the_answer_is_the_caps_own and a_search_counts_
        it_valid_at_the_caps_factor, and the two controls.

The two invariant cases that pass on v0.1.483 do so because the measured
decision moves no natural number: on the witness the cap's factor already
won. A mutant that keeps the comparison against the reserve
(``stage2_unconverged_fos``) fails only a_reserve_below_the_fixed_point_
does_not_win, and that is the case written for it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

N_APPG = 50          # the Appendix G slope, as in test_drawdown_usace_v169
DW = "duncan_wright"
LK = "lowe_karafiath"

#: The critical circle of the bank's problem 096 for Corps #1, #2 and
#: Lowe-Karafiath on v0.1.483: its stage 2 is the one they cannot bracket.
WITNESS = dict(centre_x=207.25, centre_y=183.333333, radius=110.79583)

#: The top of the F grid of ``PrescribedInclinationMethod._force_balance``.
GRID_TOP = 5.0

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _appg():
    if "p" not in _CACHE:
        from test_drawdown_usace_v169 import _appendix_g
        _CACHE["p"] = _appendix_g()      # Duncan-Wright-Wong, 103 -> 24 ft
    return _CACHE["p"]


def _witness():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**WITNESS)


def _family():
    from ogr_slip2d.methods.lowe_karafiath import LoweKarafiath
    from ogr_slip2d.methods.modified_swedish import (CorpsOfEngineers1,
                                                     CorpsOfEngineers2)
    return (CorpsOfEngineers1, CorpsOfEngineers2, LoweKarafiath)


def _recording(cls, *, stage2_fos=None, normal_scale=None):
    """``cls`` that records each pass, and can mark its SECOND call (stage
    2): its factor replaced by ``stage2_fos``, or its base normals -- the
    seed of the cap -- scaled by ``normal_scale``."""

    class _Rec(cls):
        def __init__(self):
            super().__init__()
            self.passes = []

        def compute_fos(self, project, surface, slices):
            r = super().compute_fos(project, surface, slices)
            if len(self.passes) == 1:
                if stage2_fos is not None:
                    r.fos = stage2_fos
                if normal_scale is not None:
                    r.base_normal_force = [normal_scale * n
                                           for n in r.base_normal_force]
            self.passes.append(r)
            return r

    return _Rec()


def _solve(cls, procedure=DW, **mark):
    """``rapid_drawdown_fos`` on the witness, and the method that ran it."""
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    key = (cls.__name__, procedure, tuple(sorted(mark.items())))
    if key not in _CACHE:
        m = _recording(cls, **mark)
        res = rapid_drawdown_fos(_appg(), _witness(), m, num_slices=N_APPG,
                                 procedure=procedure)
        _CACHE[key] = (res, m)
    return _CACHE[key]


def _wrapped(cls, procedure=DW, **mark):
    from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
    from ogr_slip2d.slicer import slice_surface
    p, c = _appg(), _witness()
    return MultiStageDrawdownMethod(
        _recording(cls, **mark), procedure, num_slices=N_APPG).compute_fos(
            p, c, slice_surface(p, c, num_slices=N_APPG))


# ======================================================================
class TestTheWitnessIsReal:
    """Guards: without these the cases below prove nothing."""

    def test_the_family_cannot_bracket_stage_two_on_this_circle(self):
        from ogr_slip2d.methods.base import REASON_NO_FORCE_BRACKET
        for cls in _family():
            _res, m = _solve(cls)
            r1, r2 = m.passes[0], m.passes[1]
            assert r1.converged, (cls.__name__, r1.fos, r1.reason)
            assert r2.fos is not None and not r2.converged, (
                cls.__name__, r2.fos)
            assert r2.reason == REASON_NO_FORCE_BRACKET, r2.reason
            assert math.isclose(r2.fos, GRID_TOP, rel_tol=1e-12), r2.fos

    def test_the_circle_itself_is_solvable_at_stage_two(self):
        """Bishop converges there above the family's grid: what fails is
        the bracket, not the slope."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        _res, m = _solve(BishopSimplified)
        r2 = m.passes[1]
        assert r2.converged and r2.fos > GRID_TOP, r2.fos

    def test_the_cap_converges_from_that_seed(self):
        for cls in _family():
            res, m = _solve(cls)
            assert res.n_cap_passes > 0 and res.cap_converged, (
                cls.__name__, res.n_cap_passes, res.cap_converged)
            assert m.passes[-1].converged, cls.__name__

    def test_the_fixed_point_does_not_depend_on_the_seed(self):
        """The premise of the decision, on this circle: the cap seeded with
        the stage-2 normals scaled by 0.8 and by 1.2 lands within
        ``CAP_TOL`` of the unmarked run."""
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        from ogr_slip2d.rapid_drawdown import CAP_TOL
        base, _m = _solve(CorpsOfEngineers1)
        for scale in (0.8, 1.2):
            res, _m = _solve(CorpsOfEngineers1, normal_scale=scale)
            assert abs(res.fos_stage3 - base.fos_stage3) < CAP_TOL, (
                scale, res.fos_stage3, base.fos_stage3)


class TestAnUnconvergedStageTwoOnlySeedsTheCap:

    def test_it_is_not_published_as_the_factor_of_stage_two(self):
        for cls in _family():
            res, _m = _solve(cls)
            assert res.fos_stage2 is None, (cls.__name__, res.fos_stage2)
            assert getattr(res, "stage2_converged", None) is False
            assert math.isclose(getattr(res, "stage2_unconverged_fos", -1.0),
                                GRID_TOP, rel_tol=1e-12)

    def test_the_answer_is_the_caps_own(self):
        for cls in _family():
            res, m = _solve(cls)
            assert res.fos == res.fos_stage3, (cls.__name__, res.fos)
            assert res.final_result is m.passes[-1], cls.__name__

    def test_the_wrapper_publishes_the_three(self):
        for cls in _family():
            w = _wrapped(cls)
            res, _m = _solve(cls)
            assert w.is_valid and w.admissible, (cls.__name__, w.reason)
            assert w.fos == res.fos, (cls.__name__, w.fos, res.fos)
            assert w.details["fos_stage2"] is None, w.details["fos_stage2"]
            assert w.details.get("stage2_converged") is False
            assert math.isclose(w.details.get("stage2_unconverged_fos", -1.0),
                                GRID_TOP, rel_tol=1e-12)

    def test_a_reserve_below_the_fixed_point_does_not_win(self):
        """A stage 2 marked unconverged at 1.0, under the cap's ~1.50: the
        old comparison handed the answer to that pass, invalid at 1.0.

        Only the RULE is checked here, not the cap's number. The mark changes
        the factor and leaves the normals of F = 5.0, a pair no solver hands
        back (the family's fallback returns the state of the F it reports).
        The cap's first step is measured from that factor, so its path
        changes: measured, 20 passes cycling about 1.509, against 16
        converging to 1.5003 unmarked."""
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        base, _m = _solve(CorpsOfEngineers1)
        res, m = _solve(CorpsOfEngineers1, stage2_fos=1.0)
        assert base.fos_stage3 > 1.0 + 0.1          # the guard of the case
        assert res.fos == res.fos_stage3, res.fos
        assert res.fos > 1.0 + 0.1, res.fos
        # The old code handed the answer to the marked pass itself.
        assert res.final_result is not m.passes[1]
        assert res.final_result is m.passes[-1] or (
            res.final_result is None and m.passes[1] not in res.cycle_horns)
        w = _wrapped(CorpsOfEngineers1, stage2_fos=1.0)
        assert w.is_valid and math.isclose(w.fos, res.fos, rel_tol=1e-12), (
            w.fos, w.reason)

    def test_a_search_counts_it_valid_at_the_caps_factor(self):
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.search import GridSearch
        search = GridSearch(method=MultiStageDrawdownMethod(
            CorpsOfEngineers1(), DW, num_slices=N_APPG),
            num_slices=N_APPG, min_area=0.0)
        got = search.evaluate_circle(_appg(), _witness())
        res, _m = _solve(CorpsOfEngineers1)
        assert got is not None and got.is_valid, getattr(got, "reason", None)
        assert got.fos == res.fos, (got.fos, res.fos)


class TestWithoutACapTheUnconvergedPassIsTheAnswer:

    def test_lowe_karafiaths_procedure_stays_invalid(self):
        from ogr_slip2d.methods.base import REASON_NO_FORCE_BRACKET
        from ogr_slip2d.methods.modified_swedish import CorpsOfEngineers1
        res, m = _solve(CorpsOfEngineers1, procedure=LK)
        assert res.n_cap_passes == 0 and res.final_result is m.passes[1]
        assert res.fos_stage2 is None
        w = _wrapped(CorpsOfEngineers1, procedure=LK)
        assert not w.is_valid, (w.fos, w.converged)
        assert w.reason == REASON_NO_FORCE_BRACKET, w.reason
        assert w.details.get("stage2_converged") is False


class TestWhatDoesNotMove:
    """Controls: a converged stage 2 keeps its factor and the comparison."""

    def test_a_converged_stage_two_keeps_its_factor_and_the_comparison(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        res, m = _solve(BishopSimplified)
        assert res.fos_stage2 == m.passes[1].fos, res.fos_stage2
        assert res.fos == min(res.fos_stage2, res.fos_stage3)
        assert getattr(res, "stage2_converged", True) is True
        assert getattr(res, "stage2_unconverged_fos", None) is None
        w = _wrapped(BishopSimplified)
        assert w.details["fos_stage2"] == res.fos_stage2
        assert w.details.get("stage2_converged", True) is True
        assert w.details.get("stage2_unconverged_fos") is None

    def test_pilarcitos_keeps_its_comparison(self):
        """The published case of Duncan, Wright & Wong (1990), both stages
        converged (test_rapid_drawdown_v168): the answer is still the
        smaller of the two, and DWW <= LK."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        from test_rapid_drawdown_v168 import _circle, _pilarcitos
        p, c = _pilarcitos(), _circle()
        dww = rapid_drawdown_fos(p, c, BishopSimplified(), num_slices=25,
                                 procedure=DW)
        lk = rapid_drawdown_fos(p, c, BishopSimplified(), num_slices=25,
                                procedure=LK)
        assert dww.fos_stage2 is not None
        assert dww.fos == min(dww.fos_stage2, dww.fos_stage3)
        assert dww.fos_stage2 == lk.fos_stage2 and dww.fos <= lk.fos
