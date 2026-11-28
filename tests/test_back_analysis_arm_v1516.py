# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D467 (v0.1.516) — with the force above the centre of the circle, Bishop's
back analysis no longer says «no support needed».

The invariant
-------------
Bishop sees the horizontal force T of the back analysis only through its
moment about the centre of the circle, with the arm ``(y_c − y_T)/R``
(Bishop 1955; ``back_analysis._sums_at_fixed_fos``). With the force ABOVE
the centre the arm is negative, and then any force into the slope LOWERS
both factors: the active one, R/(D + T·|arm|), and the passive one,
(R − T·|arm|)/D. No force into the slope can bring such a surface up to
the target. Until 0.1.515 the count gave a negative force for it, and the
clip to zero («the surface already exceeds the target») published 0 kN/m:
a false «no support needed», on the unsafe side, for a surface below the
target. Measured on problem 037 of the bank (target 1.5): 50 circles below
the target, with the force between their centre and their crest, came out
with T from −1151 to −34 662 kN/m before the clip and 0 after
(``_auditoria/P10_D467/medir_d467.py``).

The owner's decision (2026-11-28): such a surface is left out with its
note and counted apart, as the ones the force does not touch (D418). The
rule is geometric and exact (the sign of the arm), so no factor is read.
Checked here, on a circle of the demo slope whose centre (28, 22) lies
below its crest (it enters the crest at y = 25 and leaves the face at
y = 17.76):

* the premise: with the force at y = 23.5 the arm is −0.25 and the force
  before the clip is negative; with ``ARM_ABOVE_CENTRE_REFUSED`` off it
  publishes the old 0;
* with the rule, the surface carries the note, no force, and the run
  leaves it out, counts it, and says so, as the error when nothing else
  is left;
* beside a surface the force can help, that one governs, and the note
  says the other was left out;
* the control: with the force at y = 20, below the centre, the force is
  the one of before, to the last bit, with the rule on and off;
* Janbu, which has no arm, gives the same force whatever the rule;
* the window's path (``required_force_of_result``) says the same note.

Cost: one circle evaluated twice; well under 1 s.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent))

_CENTRE = (28.0, 22.0)
_R = 6.0
_ABOVE = 23.5       # between the centre (22) and the crest (25)
_BELOW = 20.0       # between the exit on the face (17.76) and the centre
_EV: dict = {}


def _ev(mid="bishop_simplified", centre=_CENTRE, radius=_R):
    key = (mid, centre, radius)
    if key not in _EV:
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.surface import SlipCircle
        p = build_demo_project()
        p.settings.methods.enabled_methods = [mid]
        p.settings.methods.tolerance = 1e-12
        p.settings.methods.max_iterations = 400
        ev = build_search(p, mid).evaluate_circle(
            p, SlipCircle(centre_x=centre[0], centre_y=centre[1],
                          radius=radius))
        assert ev is not None and ev.is_valid
        _EV[key] = (p, ev)
    return _EV[key]


def _force(ev, p, y, mid="bishop_simplified"):
    from ogr_slip2d.back_analysis import required_force
    return required_force(ev.slices, ev.surface, 1.3 * ev.fos, mid, y,
                          project=p)


def _with_rule(on, fn):
    from ogr_slip2d import back_analysis as BA
    saved = BA.ARM_ABOVE_CENTRE_REFUSED
    BA.ARM_ABOVE_CENTRE_REFUSED = on
    try:
        return fn()
    finally:
        BA.ARM_ABOVE_CENTRE_REFUSED = saved


def _drive(p, evaluations, target, y, mid="bishop_simplified"):
    from ogr_slip2d.back_analysis import run_back_analysis
    search = NS(run=lambda _p: NS(evaluations=list(evaluations)),
                slice_store=None)
    return run_back_analysis(p, search, target, y, mid)


class TestTheArmAboveTheCentre:
    def test_the_premise_a_negative_arm_and_the_old_zero(self):
        from ogr_slip2d.back_analysis import (_sums_at_fixed_fos,
                                              force_touches, ground_of,
                                              mass_top_range)
        p, ev = _ev()
        lo, hi = mass_top_range(ev.slices, ground_of(p))
        assert lo < _CENTRE[1] < _ABOVE < hi
        assert force_touches((lo, hi), _ABOVE)
        target = 1.3 * ev.fos
        resisting, driving, arm = _sums_at_fixed_fos(
            ev.slices, ev.surface, target, 0.0, 0.0, _ABOVE,
            "bishop_simplified", stress_fos=target, project=p)
        assert math.isclose(arm, (22.0 - 23.5) / 6.0, rel_tol=1e-12)
        assert (driving - resisting / target) / arm < 0.0
        old = _with_rule(False, lambda: _force(ev, p, _ABOVE))
        assert old.active_force == 0.0 and not old.notes

    def test_the_surface_carries_the_note_and_no_force(self):
        p, ev = _ev()
        r = _with_rule(True, lambda: _force(ev, p, _ABOVE))
        assert "above_centre" in r.notes
        assert r.notes["above_centre"].code == "run.back_surface_above_centre"
        assert math.isnan(r.active_force) and math.isnan(r.passive_force)
        assert math.isnan(r.governing_force)

    def test_the_run_leaves_it_out_and_says_so(self):
        p, ev = _ev()
        out = _drive(p, [ev], 1.3 * ev.fos, _ABOVE)
        assert out.critical is None
        assert out.surfaces_above_centre == 1
        assert out.notes["error"].code == "run.back_none_above_centre"
        assert out.summary()["surfaces_above_centre"] == 1

    def test_beside_a_surface_it_can_help_that_one_governs(self):
        p, ev = _ev()
        # a deeper circle whose centre is above the crest: the force at
        # 23.5 is below its centre
        p2, ev2 = _ev(centre=(28.0, 32.0), radius=14.0)
        assert p2 is not p
        target = 1.3 * max(ev.fos, ev2.fos)
        out = _drive(p, [ev, ev2], target, _ABOVE)
        assert out.critical is not None
        assert out.critical.governing_force > 0.0
        assert out.surfaces_above_centre == 1
        assert out.notes["above_centre_skipped"].code == \
            "run.back_above_centre_left_out"

    def test_control_below_the_centre_the_force_of_before(self):
        p, ev = _ev()
        on = _with_rule(True, lambda: _force(ev, p, _BELOW))
        off = _with_rule(False, lambda: _force(ev, p, _BELOW))
        assert not on.notes
        assert on.active_force > 0.0
        assert on.active_force == off.active_force
        assert on.passive_force == off.passive_force

    def test_janbu_has_no_arm(self):
        p, ev = _ev("janbu_simplified")
        on = _with_rule(True, lambda: _force(ev, p, _ABOVE,
                                             "janbu_simplified"))
        off = _with_rule(False, lambda: _force(ev, p, _ABOVE,
                                               "janbu_simplified"))
        assert not on.notes
        assert on.active_force == off.active_force
        assert on.passive_force == off.passive_force

    def test_the_windows_path_says_the_same(self):
        from ogr_slip2d.back_analysis import required_force_of_result
        p, ev = _ev()
        res = NS(slices=ev.slices, surface=ev.surface, fos=ev.fos,
                 details={}, method_id="bishop_simplified")
        r = required_force_of_result(res, 1.3 * ev.fos, _ABOVE, p)
        assert r.notes["above_centre"].code == \
            "run.back_surface_above_centre"
