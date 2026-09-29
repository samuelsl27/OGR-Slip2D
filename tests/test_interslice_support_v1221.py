# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The interslice march of the interpretation carries the reinforcement the
method applied (v0.1.221, D212).

INVARIANT PROTECTED
-------------------
``postprocess._march`` re-solves each slice's equilibrium at the method's F
and with its inter-slice ratios, to show the interslice forces, the line of
thrust and the free body of a slice. It has to apply the loads the method
applied, and since v0.1.214 (D173) it did -- the water, the earthquake and
its sense -- except the reinforcement. So on a reinforced slope it showed the
equilibrium of a bare one, and since v0.1.216 (D196) its base normal parted
from the column the method publishes on every crossed slice: on the -15 deg
nail of ``test_support_normal_v1137`` it gave 6.686 kN/m on slice 46 where
Bishop's own normal is 15.607 (6.565 against 15.381 with Janbu).

Each method now publishes the force it applied per slice
(``details["support_force"]``: the normal part whole and the tangential part
mobilised at ``t_active + t_passive/F``, the same vector in every family)
and its moment about the base midpoint (``details["support_moment"]``). The
march adds the force to the slice's two force balances and the moment to its
line of thrust, and reads the strength where the method did.

What is asserted, none of it a snapshot:

* with X = 0 (Bishop, both Janbu) the march's N IS the published column, to
  1e-9, on an active and on a passive nail;
* Janbu's own balance, which is horizontal, closes again at the free end;
* Corps of Engineers #1, whose inclination is one constant, reproduces its
  own normals exactly -- the other two members of that family do not even
  without a support, for a reason of their own (D220, reported apart);
* Spencer and GLE march as close to their own solution as they do on the
  bare slope, where without the support they miss it by an order more;
* each slice satisfies both force balances with the support, and its moment
  balance with the support's moment;
* rule 7: with ``postprocess.SUPPORT_IN_MARCH`` off the march is the bare
  one (6.686 on slice 46), and on a bare slope nothing moves by a bit.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.220 tree: see ``_auditoria/P4_0221`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

X0 = ("bishop_simplified", "janbu_simplified", "janbu_corrected")
CROSSED = 46
_CACHE: dict = {}


def _solve(method_id, nail="active", tol=None):
    """(slices, result) on the circle of ``test_support_normal_v1137`` with
    its -15 deg nail, active or passive, or with none."""
    key = (method_id, nail, tol)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import (NSLICES, _circle, _nail,
                                               _project)
        p = _project(None if nail is None
                     else _nail(-15.0, nail == "active"))
        c = _circle()
        sl = slice_surface(p, c, num_slices=NSLICES)
        m = method_registry()[method_id]()
        if tol is not None:
            m.tolerance = tol
            m.max_iterations = 400
        res = m.compute_fos(p, c, sl)
        assert res.fos is not None, (method_id, nail, res.error_message)
        _CACHE[key] = (p, c, sl, res)
    return _CACHE[key]


def _state(res, on=True):
    """The march, with ``postprocess.SUPPORT_IN_MARCH`` as asked and put
    back (the runner has no teardown)."""
    from ogr_slip2d import postprocess as pp
    old = getattr(pp, "SUPPORT_IN_MARCH", None)
    pp.SUPPORT_IN_MARCH = on
    try:
        return pp.compute_interslice_state(res)
    finally:
        if old is None:
            vars(pp).pop("SUPPORT_IN_MARCH", None)
        else:
            pp.SUPPORT_IN_MARCH = old


def _gap(a, b):
    return max(abs(x - y) / max(1.0, abs(y)) for x, y in zip(a, b))


def _solved(res):
    return res.details.get("solved_base_normal") or res.base_normal_force


# ======================================================================
class TestTheFixtureCarriesTheNail:

    def test_slice_46_is_crossed_and_its_column_carries_the_support(self):
        """Guard: without this the identities below could pass on a slope
        where the nail does nothing."""
        *_x, bare = _solve("bishop_simplified", None)
        for nail in ("active", "passive"):
            *_x, res = _solve("bishop_simplified", nail)
            load = res.details.get("sigma_support_load")
            assert load and abs(load[CROSSED]) > 1.0, (nail, load)
            assert (res.base_normal_force[CROSSED]
                    > 2.0 * bare.base_normal_force[CROSSED]), nail


# ======================================================================
class TestWithNoInterSliceShearTheMarchIsTheColumn:
    """Bishop (1955) and Janbu (1954) solve the vertical equilibrium of each
    slice with X = 0; the march does the same, so its N is theirs."""

    def test_active_nail(self):
        for mid in X0:
            *_x, res = _solve(mid, "active")
            st = _state(res)
            assert st.ok, mid
            assert _gap(st.N, res.base_normal_force) < 1e-9, (
                mid, st.N[CROSSED], res.base_normal_force[CROSSED])

    def test_passive_nail(self):
        for mid in X0:
            *_x, res = _solve(mid, "passive")
            st = _state(res)
            assert st.ok, mid
            assert _gap(st.N, res.base_normal_force) < 1e-9, mid

    def test_janbu_closes_its_own_horizontal_balance(self):
        """Janbu's equation IS the horizontal balance of the mass, so its
        march has to close at the free end, reinforcement included; solved
        tightly, to 1e-9 of the largest thrust."""
        for nail in ("active", "passive"):
            *_x, res = _solve("janbu_simplified", nail, tol=1e-12)
            st = _state(res)
            assert st.ok and st.relative_closure < 1e-9, (
                nail, st.relative_closure)


# ======================================================================
class TestTheForceMethodsKeepTheirOwnState:

    def test_corps_one_reproduces_its_normals(self):
        """One constant inclination, published as it was solved: the march
        is the method's own recursion and gives back its normals, to the
        tolerance of the method's root (the secant of the march closes the
        residual it leaves: 1e-8 on the passive nail, 1e-15 on the active
        one). Without the support in the march they part by 0.81."""
        for nail in ("active", "passive"):
            *_x, res = _solve("corps_engineers_1", nail)
            st = _state(res)
            assert st.ok and _gap(st.N, _solved(res)) < 1e-6, nail

    def test_spencer_and_gle_as_close_as_on_the_bare_slope(self):
        """The march with their ratios only has to close (see
        ``test_postprocess_v122``), not to reproduce their N: it re-solves
        with the ratio scaled by a secant. So the yardstick is the bare
        slope: with the nail they must stay as close to their own solution
        as they are without one (a factor of two of room), and close."""
        for mid in ("spencer", "gle_morgenstern_price"):
            *_x, bare = _solve(mid, None)
            g0 = _gap(_state(bare).N, _solved(bare))
            for nail in ("active", "passive"):
                *_x, res = _solve(mid, nail)
                st = _state(res)
                assert st.ok and st.relative_closure < 1e-6, (
                    mid, nail, st.relative_closure)
                assert _gap(st.N, _solved(res)) <= 2.0 * g0, (
                    mid, nail, _gap(st.N, _solved(res)), g0)


# ======================================================================
class TestEachSliceIsInEquilibriumWithItsSupport:

    def _loads(self, p, c, res, i):
        """The slice, its loads and the ACTIVE nail's force on it, written
        out from the resolved terms rather than read from what the method
        publishes: its normal part whole and its tangential part along the
        base, resisting (Active: nothing is divided by F)."""
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.support_integration import resolve_support_terms
        s = res.slices.slices[i]
        f = slice_forces(s, 0.0, 0.0)
        sgn = res.details["slide_sign"]
        sup = resolve_support_terms(p, c, res.slices, sgn)
        assert sup.t_passive[i] == 0.0          # the fixture is Active
        a = s.base_angle
        fx = sup.nf_h[i] + sgn * sup.t_active[i] * math.cos(a)
        fy = sup.nf_v[i] + sgn * sup.t_active[i] * math.sin(a)
        return s, f, fx, fy

    def test_both_force_balances_of_the_crossed_slice(self):
        p, c, _sl, res = _solve("bishop_simplified", "active")
        st = _state(res)
        s, f, fx, fy = self._loads(p, c, res, CROSSED)
        assert math.hypot(fx, fy) > 1.0, (fx, fy)       # guard: it acts
        a = s.base_angle
        nx, ny, tx, ty = -math.sin(a), math.cos(a), math.cos(a), math.sin(a)
        n, sh = st.N[CROSSED], st.S[CROSSED]
        e_l, e_r = st.E[CROSSED], st.E[CROSSED + 1]
        x_l, x_r = st.X[CROSSED], st.X[CROSSED + 1]
        h = f.h_water          # no earthquake on this slope
        sum_x = n * nx + sh * tx + e_l - e_r + h + fx
        sum_y = n * ny + sh * ty + x_l - x_r - f.w_total + fy
        scale = max(abs(f.w_total), abs(fx), abs(fy))
        assert abs(sum_x) < 1e-9 * scale and abs(sum_y) < 1e-9 * scale, (
            sum_x, sum_y)

    def test_the_published_moment_is_the_nails(self):
        """About the base midpoint, the moment of the nail's normal part at
        its crossing; its tangential part runs along the chord through that
        point and has none. Written out here from the support's own
        effect, not from the terms the method resolved."""
        from ogr_slip2d.support_integration import compute_support_effects
        p, c, sl, res = _solve("bishop_simplified", "active")
        effs = [e for e in compute_support_effects(p, c, sl)
                if e.slice_index == CROSSED]
        assert len(effs) == 1, len(effs)
        e = effs[0]
        s = sl.slices[CROSSED]
        a = s.base_angle
        t_n = e.force_h * math.sin(a) - e.force_v * math.cos(a)
        nfh, nfv = t_n * math.sin(a), -t_n * math.cos(a)
        x_c = 0.5 * (s.base_x_left + s.base_x_right)
        y_c = 0.5 * (s.base_y_left + s.base_y_right)
        want = ((e.intersection_x - x_c) * nfv
                - (e.intersection_y - y_c) * nfh)
        got = res.details["support_moment"][CROSSED]
        assert abs(want) > 1e-3, want                    # guard: it has one
        assert abs(got - want) <= 1e-9 * max(1.0, abs(want)), (got, want)

    def test_the_line_of_thrust_takes_it(self):
        """The march adds the published moment to the slice's own moment
        balance, so the application height of the next thrust moves by
        exactly that moment over it. Asserted in size, not in sign: the sign
        with which that balance treats its known moments is wrong, reported
        apart (D221) and not this version's to change."""
        from ogr_slip2d import postprocess as pp
        *_x, res = _solve("bishop_simplified", "active")
        st = _state(res)
        slist = list(res.slices)
        details = res.details
        n = len(slist)
        zero_m = [0.0] * n
        bare_m = pp._march(slist, [0.0] * (n + 1),
                           details.get("equilibrium_fos", res.fos), 0.0, 0.0,
                           slide_sign=details["slide_sign"],
                           support_force=details["support_force"],
                           support_moment=zero_m,
                           support_load=details["sigma_support_load"])
        dy = st.y_thrust[CROSSED + 1] - bare_m.y_thrust[CROSSED + 1]
        m_sup = details["support_moment"][CROSSED]
        e_r = st.E[CROSSED + 1]
        assert abs(abs(dy * e_r) - abs(m_sup)) <= 1e-9 * max(1.0, abs(m_sup)), (
            dy * e_r, m_sup)


# ======================================================================
class TestWhatTheMethodsPublish:

    def test_every_family_publishes_the_force_and_its_moment(self):
        for mid in X0 + ("spencer", "gle_morgenstern_price",
                         "corps_engineers_1", "lowe_karafiath",
                         "ordinary_fellenius"):
            *_x, res = _solve(mid, "passive")
            f = res.details.get("support_force")
            m = res.details.get("support_moment")
            n = len(res.slices.slices)
            assert f is not None and len(f) == n, mid
            assert m is not None and len(m) == n, mid
            assert math.hypot(*f[CROSSED]) > 1.0, (mid, f[CROSSED])

    def test_the_vertical_part_is_the_load_bishop_and_janbu_add(self):
        """``-f_y`` is ``support_vertical_load``, the load their vertical
        equilibrium carries, bit for bit."""
        for mid in X0:
            for nail in ("active", "passive"):
                *_x, res = _solve(mid, nail)
                load = res.details["sigma_support_load"]
                force = res.details["support_force"]
                assert all(-fy == ld for (_fx, fy), ld in zip(force, load)), (
                    mid, nail)

    def test_a_bare_slope_publishes_none(self):
        for mid in X0 + ("spencer", "corps_engineers_1"):
            *_x, res = _solve(mid, None)
            assert res.details.get("support_force") is None, mid
            assert res.details.get("support_moment") is None, mid


# ======================================================================
class TestTheSwitchMovesTheNumber:
    """Rule 7."""

    def test_off_the_march_is_the_bare_one(self):
        """Off, slice 46 goes back to the number the defect was measured
        at, and leaves the column."""
        *_x, res = _solve("bishop_simplified", "active")
        st = _state(res, on=False)
        assert abs(st.N[CROSSED] - 6.686) < 5e-4, st.N[CROSSED]
        assert _gap(st.N, res.base_normal_force) > 0.5

    def test_on_a_bare_slope_nothing_moves_by_a_bit(self):
        for mid in ("bishop_simplified", "spencer"):
            *_x, res = _solve(mid, None)
            on, off = _state(res, True), _state(res, False)
            for name in ("N", "S", "E", "X", "y_thrust"):
                assert getattr(on, name) == getattr(off, name), (mid, name)
