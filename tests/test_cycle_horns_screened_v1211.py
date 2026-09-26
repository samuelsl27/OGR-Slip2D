# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.211 — when the drained cap of a rapid drawdown keeps cycling, the
post-analysis checks judge the TWO HORNS of the cycle, each as its pass
solved it, and not the caller's slices at the centre's factor (defect D200).

THE INVARIANT. In the cycling branch (no pass produced the reported factor,
which is the centre of the cycle, v0.1.71) the wrapper's result carries the
two horns in ``screen_states``, and ``checks.screen_surface`` admits the
centre only if BOTH pass every enabled check: tension on every state first,
then m-alpha, with the notes and reasons of D177 unchanged. The slices
published beside the centre are the last horn's, with no forces. Everywhere
else a result has no states and judges itself, as before.

WHAT WAS WRONG. That branch published the CALLER's slices -- the full
reservoir, with the drained materials (phi' = 30 in problem 096) -- and the
checks judged them at a stage-3 factor: a pairing no stage computed. D112b
(v0.1.210) already made the centre's inner verdict that of its two horns;
the owner's decision (2026-09-26) carries the same rule to the screen.

WHY THE CYCLE IS FORCED. On this circle the drained cap settles, so the
branch is reached by the patch ``test_drawdown_passthrough_v1210.py`` uses:
``rapid_drawdown_fos`` is wrapped to drop ``final_result`` and hand two
horns. What distinguishes the two criteria is made the same way that file
makes it: a horn that declares the opposite sign on the drained crest
(min m_alpha 0.226 against 1.011 on the caller's slices with the shared
sign, measured), with the m-alpha limit set between the two; and a horn
whose own solution puts a base in tension, read through
``solved_base_normal`` as D172 reads it.

DISCRIMINATION against the v0.1.210 tree. MEASURED, by copying this file into
a ``git worktree`` at e983574 and running it there. Of the 13 cases, **7 fail
and 6 pass**:

  fail  a_failing_horn_rejects_the_centre           (behaviour)
        the_caller_slices_no_longer_decide          (behaviour)
        the_search_door_reads_the_horns_with_the_unchanged_note (behaviour)
        tension_is_reported_before_m_alpha_across_the_states (behaviour)
        the_published_slices_are_the_last_horns     (behaviour)
        the_states_are_the_two_horns                (WEAK: an attribute)
        the_horns_travel_through_pickle_and_stay_out_of_to_dict
                                                    (WEAK: an attribute)

  pass  the two fixture guards and the four controls.

The run is archived in the bank as
``_auditoria/D194_D200_casquete/discriminacion_d200_test_v1211_en_0.1.210.txt``.
"""
from __future__ import annotations

import copy
import json
import pickle

N_SLICES = 25
LIMIT_BETWEEN = 0.5      # between 0.226 (flipped horn) and 1.011 (caller)
_LAST: dict = {}


def _cycling(flip_horn=False, flip_shared=False, tension_horn=False):
    """The wrapper's result on the drained-crest fixture with the cycling
    branch forced, and the caller's slices. Restores the module patch
    always: the runner has no teardown."""
    import ogr_slip2d.rapid_drawdown as rd
    from ogr_slip2d.methods.janbu import JanbuSimplified
    from ogr_slip2d.slicer import slice_surface
    from test_drawdown_passthrough_v1210 import _circle, _crest_project

    original = rd.rapid_drawdown_fos

    def _no_final(*args, **kwargs):
        out = original(*args, **kwargs)
        horn_a = out.final_result
        horn_b = copy.copy(horn_a)
        horn_b.details = dict(horn_a.details or {})
        if flip_horn:
            horn_b.details["m_alpha_sign"] = \
                -float(horn_b.details["m_alpha_sign"])
        if tension_horn:
            n = len(horn_b.slices.slices)
            horn_b.details["solved_base_normal"] = [-1.0] * n
        if flip_shared:
            out.invariant_details = dict(out.invariant_details)
            out.invariant_details["m_alpha_sign"] = \
                -float(out.invariant_details["m_alpha_sign"])
        out.final_result = None
        out.cycle_horns = (horn_a, horn_b)
        _LAST["res"] = out
        return out

    p = _crest_project()
    c = _circle()
    sl = slice_surface(p, c, num_slices=N_SLICES)
    rd.rapid_drawdown_fos = _no_final
    try:
        w = rd.wrap_for_drawdown(JanbuSimplified(), p,
                                 num_slices=N_SLICES).compute_fos(p, c, sl)
    finally:
        rd.rapid_drawdown_fos = original
    return w, sl, _LAST["res"]


def _as_the_caller(w, sl):
    """What v0.1.210 judged: the caller's slices at the centre's factor."""
    r = copy.copy(w)
    r.slices = sl
    if hasattr(r, "screen_states"):
        r.screen_states = ()
    return r


def _screen(r, **kw):
    from ogr_slip2d.checks import screen_surface
    return screen_surface(r, **kw)


# ======================================================================
class TestTheFixtureTellsTheCriteriaApart:
    """Guards: the synthetic horns fail what the caller's slices pass, and
    the reverse, at the limit the cases below use."""

    def test_a_flipped_horn_fails_where_the_caller_passes(self):
        w, sl, res = _cycling(flip_horn=True)
        ok_a, _s, _n = _screen(res.cycle_horns[0], m_alpha=True,
                               m_alpha_limit=LIMIT_BETWEEN)
        ok_b, _s, _n = _screen(res.cycle_horns[1], m_alpha=True,
                               m_alpha_limit=LIMIT_BETWEEN)
        ok_c, _s, _n = _screen(_as_the_caller(w, sl), m_alpha=True,
                               m_alpha_limit=LIMIT_BETWEEN)
        assert (ok_a, ok_b, ok_c) == (True, False, True)

    def test_a_flipped_shared_sign_fails_the_caller_only(self):
        w, sl, res = _cycling(flip_shared=True)
        ok_c, _s, _n = _screen(_as_the_caller(w, sl), m_alpha=True,
                               m_alpha_limit=LIMIT_BETWEEN)
        assert ok_c is False
        for h in res.cycle_horns:
            assert _screen(h, m_alpha=True,
                           m_alpha_limit=LIMIT_BETWEEN)[0] is True


class TestTheChecksJudgeTheHorns:

    def test_the_published_slices_are_the_last_horns(self):
        w, sl, res = _cycling()
        assert w.slices is not sl, "the caller's slices are published"
        assert w.slices is res.cycle_horns[-1].slices

    def test_the_states_are_the_two_horns(self):
        w, _sl, res = _cycling()
        states = getattr(w, "screen_states", ())
        assert len(states) == 2, "no states: the result judges itself"
        assert all(a is b for a, b in zip(states, res.cycle_horns))

    def test_a_failing_horn_rejects_the_centre(self):
        from ogr_slip2d.methods.base import SCREEN_M_ALPHA
        w, _sl, _res = _cycling(flip_horn=True)
        ok, screen, note = _screen(w, m_alpha=True,
                                   m_alpha_limit=LIMIT_BETWEEN)
        assert (ok, screen) == (False, SCREEN_M_ALPHA), (ok, screen)
        assert note.startswith("m_alpha < %s on " % LIMIT_BETWEEN), note

    def test_the_caller_slices_no_longer_decide(self):
        w, _sl, _res = _cycling(flip_shared=True)
        got = _screen(w, m_alpha=True, m_alpha_limit=LIMIT_BETWEEN)
        assert got == (True, "", None), got

    def test_the_search_door_reads_the_horns_with_the_unchanged_note(self):
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.search import GridSearch
        w, _sl, _res = _cycling(tension_horn=True)
        search = GridSearch(method=JanbuSimplified(), reject_tensile=True,
                            check_m_alpha=False)
        assert search._is_admissible(w) is False, "admitted"
        assert w.admissibility_reason == SCREEN_TENSILE_STRESS
        assert w.admissibility_note.startswith("tensile stress on ")
        assert w.admissibility_note.endswith(" slice base(s) (error -120)")

    def test_tension_is_reported_before_m_alpha_across_the_states(self):
        """Horn b fails both screens: the order D177 wrote -- tension first
        -- holds across states as it does within one."""
        from ogr_slip2d.methods.base import SCREEN_TENSILE_STRESS
        w, _sl, _res = _cycling(flip_horn=True, tension_horn=True)
        ok, screen, _note = _screen(w, tensile=True, m_alpha=True,
                                    m_alpha_limit=LIMIT_BETWEEN)
        assert (ok, screen) == (False, SCREEN_TENSILE_STRESS), (ok, screen)

    def test_the_horns_travel_through_pickle_and_stay_out_of_to_dict(self):
        """The grid search returns results from worker processes; the
        states must survive the trip. ``to_dict`` is the result itself."""
        w, _sl, _res = _cycling()
        back = pickle.loads(pickle.dumps(w))
        assert len(getattr(back, "screen_states", ())) == 2, "no states"
        d = w.to_dict()
        assert "screen_states" not in d
        json.dumps(d, allow_nan=False)


class TestWhatDoesNotMove:
    """Controls: these pass on v0.1.210 as well."""

    def test_both_horns_passing_admit_the_centre(self):
        w, _sl, _res = _cycling()
        assert _screen(w, m_alpha=True,
                       m_alpha_limit=LIMIT_BETWEEN) == (True, "", None)

    def test_the_centre_keeps_its_factor(self):
        w, _sl, res = _cycling(flip_horn=True)
        assert w.fos == res.fos

    def test_the_final_pass_branch_judges_itself(self):
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface
        from test_drawdown_passthrough_v1210 import _circle, _crest_project
        p, c = _crest_project(), _circle()
        sl = slice_surface(p, c, num_slices=N_SLICES)
        w = wrap_for_drawdown(JanbuSimplified(), p,
                              num_slices=N_SLICES).compute_fos(p, c, sl)
        assert tuple(getattr(w, "screen_states", ())) == ()
        assert w.base_normal_force                 # the final pass's forces

    def test_a_result_built_by_hand_judges_itself(self):
        from test_screen_error_v1211 import _result
        r = _result()
        assert tuple(getattr(r, "screen_states", ())) == ()
        assert _screen(r, tensile=True, m_alpha=True) == (True, "", None)
