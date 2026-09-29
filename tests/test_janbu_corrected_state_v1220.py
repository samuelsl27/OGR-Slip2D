# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Janbu Corrected corrects the NUMBER; its state is the one its equilibrium
was solved at (v0.1.220, D211).

INVARIANT PROTECTED
-------------------
Janbu Corrected iterates Janbu's force equilibrium on the factor F0 and then
reports F = f0*F0 (Janbu 1973; Duncan, Wright & Brandon 2014, Fig. 6.13,
"F0 = factor of safety from force equilibrium solution with horizontal
interslice forces"). The correction is empirical and re-solves nothing, so
the only equilibrium state there is -- base normals, mobilised shear, the
stress a curved envelope is read at -- is the one at F0. Everything this
file checks follows from that:

* F = f0*F0 holds exactly with a CURVED envelope too, where until v0.1.219
  the fixed point of D84 read its stress at f0*F0 and the two Janbu solved
  different equilibria;
* the published columns, the envelope point and the checks of Janbu
  Corrected are Janbu Simplified's, bit for bit on the same surface;
* each slice closes its vertical equilibrium with the published normal and
  the EQUILIBRIUM shear tau = s/F0 (Duncan, Wright & Brandon 2014, Eqs.
  6.1-6.2), and the set closes Janbu's own horizontal balance;
* the readers follow the state: the m-alpha verdict (the reference prints
  the SAME count of every error code for the two Janbu in both worked
  reports, 91 and 146 at -112; this program counted 90 against 92 in the
  Ej_1 grid, and the four circles that made the difference are checked
  here), the interslice march, stage 1 of the multi-stage drawdown and the
  mobilised shear of the interpretation, which also shows the F it used.

WHY NOTHING HERE IS A SNAPSHOT
------------------------------
Every anchor is an identity between two computations or an equilibrium
equation written out here; the one external number, the reference's equal
counts, enters as "the two Janbu agree on these circles", not as a count.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.219 tree: see ``_auditoria/P4_0220`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

JS, JC = "janbu_simplified", "janbu_corrected"
#: The circles of the Ej_1 grid on which the two Janbu disagreed at -112
#: until v0.1.220 (three rejected by the simplified only, one by the
#: corrected only): (centre x, centre y, radius) as the grid generates them.
EJ1_WITNESS = ((56.0, 30.0, 21.299394349), (72.0, 30.0, 16.404773718),
               (76.0, 30.0, 20.659261662), (84.0, 30.0, 20.672781845))

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _switch(on):
    """Set ``methods.janbu.STATE_AT_EQUILIBRIUM_FOS``; returns the old value
    for ``_restore`` in a ``finally``. Through ``getattr``, so that on a tree
    without it the cases fail on behaviour rather than on a name."""
    from ogr_slip2d.methods import janbu
    old = getattr(janbu, "STATE_AT_EQUILIBRIUM_FOS", None)
    janbu.STATE_AT_EQUILIBRIUM_FOS = on
    return old


def _restore(old):
    from ogr_slip2d.methods import janbu
    if old is None:
        vars(janbu).pop("STATE_AT_EQUILIBRIUM_FOS", None)
    else:
        janbu.STATE_AT_EQUILIBRIUM_FOS = old


def _model(kind):
    """(project, surface, slices): the dry 2:1 slope with Mohr-Coulomb, or
    the problem-41 polyline with a power curve and ru = 0.3."""
    from ogr_slip2d.slicer import slice_surface
    if kind == "mc":
        from test_slide_sign_by_method_v1189 import _circle, _slope
        p, surf, n = _slope(), _circle(), 25
    else:
        from test_zero_strength_slices_v1213 import (N_41, OUTLINE_41,
                                                     SURFACE_41, _power,
                                                     _project, _surface)
        p = _project(OUTLINE_41, _power(), ru=0.3)
        surf, n = _surface(SURFACE_41), N_41
    return p, surf, slice_surface(p, surf, num_slices=n)


def _solve(kind, method_id, state=True):
    key = (kind, method_id, state)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.methods import method_registry
    p, surf, sl = _model(kind)
    m = method_registry()[method_id]()
    m.tolerance = 1e-12
    m.max_iterations = 400
    old = _switch(state)
    try:
        res = m.compute_fos(p, surf, sl)
    finally:
        _restore(old)
    assert res.fos is not None and res.converged, (kind, method_id,
                                                   res.error_message)
    _CACHE[key] = (p, surf, sl, res)
    return _CACHE[key]


def _f0_of(res):
    return res.fos / res.details["janbu_f0"]


def _close(a, b, rel=1e-12):
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


# ======================================================================
class TestTheCorrectionIsOnTheNumber:

    def test_with_a_power_curve_the_corrected_factor_is_f0_times_the_simplified(self):
        """With a curved envelope the two Janbu solved different equilibria
        until v0.1.220: the corrected one read its stress at f0*F0."""
        *_x, js = _solve("power", JS)
        *_x, jc = _solve("power", JC)
        f0 = jc.details["janbu_f0"]
        assert _close(jc.fos, f0 * js.fos), (jc.fos, f0 * js.fos)

    def test_and_with_mohr_coulomb_as_it_always_was(self):
        """Control: the point does not matter for a straight envelope."""
        *_x, js = _solve("mc", JS)
        *_x, jc = _solve("mc", JC)
        assert _close(jc.fos, jc.details["janbu_f0"] * js.fos)

    def test_the_factor_of_the_equilibrium_is_published(self):
        *_x, js = _solve("power", JS)
        *_x, jc = _solve("power", JC)
        assert jc.details.get("equilibrium_fos") == js.fos
        from ogr_slip2d.checks import equilibrium_fos
        assert equilibrium_fos(jc) == js.fos
        assert equilibrium_fos(js) == js.fos


# ======================================================================
class TestTheStateIsTheSolvedOne:

    def test_the_columns_are_the_simplified_ones(self):
        for kind in ("mc", "power"):
            *_x, js = _solve(kind, JS)
            *_x, jc = _solve(kind, JC)
            for name in ("base_normal_force", "base_shear_strength",
                         "base_shear_force"):
                a, b = getattr(js, name), getattr(jc, name)
                assert len(a) == len(b) and all(
                    _close(x, y) for x, y in zip(a, b)), (kind, name)

    def test_the_envelope_is_read_at_the_same_point(self):
        *_x, js = _solve("power", JS)
        *_x, jc = _solve("power", JC)
        a = js.details.get("envelope_stress")
        b = jc.details.get("envelope_stress")
        assert a is not None and b is not None
        assert all((x is None and y is None) or _close(x, y)
                   for x, y in zip(a, b))

    def test_each_slice_closes_with_the_equilibrium_shear(self):
        """``N cos a + s*S sin a = W_total`` with S = tau_f*l/F0."""
        from ogr_slip2d.external_forces import slice_forces
        for kind in ("mc", "power"):
            *_x, sl, jc = _solve(kind, JC)
            s = jc.details["slide_sign"]
            f_eq = _f0_of(jc)
            for sli, n, t in zip(sl.slices, jc.base_normal_force,
                                 jc.base_shear_strength):
                lhs = (n * math.cos(sli.base_angle)
                       + s * (t / f_eq) * math.sin(sli.base_angle))
                w = slice_forces(sli).w_total
                assert abs(lhs - w) <= 1e-9 * max(1.0, abs(w)), (
                    kind, sli.index, lhs, w)

    def test_the_set_closes_janbus_own_horizontal_balance(self):
        """``sum(S cos a - s N sin a) = 0``, the equation Janbu solves; with
        no water and no earthquake on this slope nothing else enters. At
        f0*F0 it missed by more than 1 %
        (``test_janbu_base_forces_v1107``, before v0.1.220)."""
        *_x, sl, jc = _solve("mc", JC)
        s = jc.details["slide_sign"]
        f_eq = _f0_of(jc)
        mob = [t / f_eq for t in jc.base_shear_strength]
        total = sum(m * math.cos(x.base_angle) - s * n * math.sin(x.base_angle)
                    for x, n, m in zip(sl.slices, jc.base_normal_force, mob))
        assert abs(total) <= 1e-6 * sum(abs(m) for m in mob), total


# ======================================================================
class TestTheReadersFollowTheState:

    def test_the_checks_judge_the_simplified_state(self):
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        for kind in ("mc", "power"):
            *_x, js = _solve(kind, JS)
            *_x, jc = _solve(kind, JC)
            assert all(_close(a, b) for a, b in
                       zip(base_m_alphas(js), base_m_alphas(jc))), kind
            assert all(_close(a, b) for a, b in
                       zip(base_effective_stresses(js),
                           base_effective_stresses(jc))), kind

    @staticmethod
    def _codes(method_id):
        from ogr_slip2d.interpretation import error_code
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from test_slide_validation_ej1 import _GRID, _ej1_project
        p = _ej1_project()
        ev = GridSearch(method=get_method(method_id)(),
                        num_slices=_GRID["num_slices"],
                        min_area=_GRID["min_area"])
        return [error_code(ev.evaluate_circle(p, SlipCircle(
            centre_x=x, centre_y=y, radius=r))) for x, y, r in EJ1_WITNESS]

    def test_the_ej1_witness_circles_get_one_verdict(self):
        """The reference prints the same -112 count for the two Janbu; these
        are the four circles on which this program disagreed with itself."""
        a, b = self._codes(JS), self._codes(JC)
        assert a == b, (a, b)
        assert -112 in a, a                       # guard: they ARE screened

    def test_the_march_is_the_published_column(self):
        """The interslice march of the interpretation re-solves the slices at
        the F the state was formed at, and with X = 0 its N is the column."""
        from ogr_slip2d.postprocess import compute_interslice_state
        for kind in ("mc", "power"):
            *_x, jc = _solve(kind, JC)
            st = compute_interslice_state(jc)
            assert st.ok
            assert all(abs(a - b) <= 1e-9 * max(1.0, abs(b))
                       for a, b in zip(st.N, jc.base_normal_force)), kind

    def test_stage_one_of_the_drawdown_reads_one_solution(self):
        """tau_fc = (c' + sigma'_fc tan phi')/F must be the mobilised shear
        S/l of the same stage-1 solution (Duncan, Wright & Brandon 2014,
        Eqs. 9.2-9.4): with Janbu Corrected, the strength over F0."""
        from ogr_slip2d.rapid_drawdown import _stage1_state
        p, surf, sl, jc = _solve("mc", JC)
        state = _stage1_state(p, surf, sl, jc)
        f_eq = _f0_of(jc)
        for (_xl, _xr, _sig, tau), s, strength in zip(
                state, sl.slices, jc.base_shear_strength):
            want = strength / s.base_length / f_eq
            assert abs(tau - want) <= 1e-9 * max(1.0, abs(want)), (
                s.index, tau, want)

    def test_the_mobilised_shear_shown_is_the_equilibriums(self):
        from ogr_slip2d.interpretation import slice_rows
        *_x, jc = _solve("mc", JC)
        f_eq = _f0_of(jc)
        for row in slice_rows(jc):
            assert _close(row["tau_m"], row["tau_f"] / f_eq), row["index"]

    def test_the_slice_panel_says_which_f(self):
        """The panel prints the factor it divides by, so tau_f/tau_m can be
        read against something: F0 for Janbu Corrected, F for the rest."""
        from ogr_gui.interpret_window import _SliceDataDock
        fields = dict(_SliceDataDock.FIELDS)
        get_f = fields["Equilibrium factor of safety F"]
        get_tau = fields["Mobilised shear τ_m = τ_f/F (kPa)"]
        *_x, sl, jc = _solve("mc", JC)
        *_x, js = _solve("mc", JS)
        s = sl.slices[3]
        assert abs(get_f(s, jc) - round(_f0_of(jc), 4)) < 1e-12
        assert abs(get_f(s, js) - round(js.fos, 4)) < 1e-12
        tau_f = jc.base_shear_strength[3] / s.base_length
        assert abs(get_tau(s, jc) - round(tau_f / _f0_of(jc), 2)) < 1e-9


# ======================================================================
class TestTheSwitchMovesTheNumber:
    """Rule 7: off, the state is formed at f0*F0 again, as until v0.1.219."""

    def test_off_the_columns_leave_the_simplified_ones(self):
        *_x, js = _solve("mc", JS)
        *_x, jc = _solve("mc", JC, state=False)
        assert any(not _close(a, b) for a, b in
                   zip(js.base_normal_force, jc.base_normal_force))
        assert "equilibrium_fos" not in jc.details

    def test_off_the_power_curve_solves_another_equilibrium(self):
        *_x, js = _solve("power", JS)
        *_x, jc = _solve("power", JC, state=False)
        f0 = jc.details["janbu_f0"]
        assert abs(jc.fos / (f0 * js.fos) - 1.0) > 1e-6, (jc.fos, js.fos)

    def test_off_the_witness_circles_disagree_again(self):
        old = _switch(False)
        try:
            a = TestTheReadersFollowTheState._codes(JS)
            b = TestTheReadersFollowTheState._codes(JC)
        finally:
            _restore(old)
        assert a != b, (a, b)
