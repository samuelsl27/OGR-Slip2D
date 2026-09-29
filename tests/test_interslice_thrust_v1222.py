# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The interslice march of the interpretation: the line of thrust is in
moment equilibrium (v0.1.222, D221) and the prescribed-inclination family
marches with the ratios it solved with (v0.1.222, D220).

INVARIANT PROTECTED
-------------------
``postprocess._march`` re-solves each slice at the method's F to show the
interslice forces E and X, the line of thrust (where they act) and the free
body of a slice. Two things were wrong with what it showed:

* D221 -- the height of each thrust came from the moment balance of the
  slice about its base midpoint with the known moments entered with the
  wrong sign, so no slice was in moment equilibrium: two equal horizontal
  thrusts came out at opposite heights, and on the slope of
  ``test_support_normal_v1137`` the line sat on the base. With the sign
  right, the line is traversed from BOTH free ends and the traversals meet
  at the centre slice, whose faces take their average: a traversal from one
  end carries the moment imbalance of the whole mass (a force-equilibrium
  method has one) to the far end, where E -> 0 made it 2968 slice heights.
* D220 -- Corps #2 and Lowe-Karafiath published, at each interior boundary,
  the tangent of the average of the inclinations of its two slices, while
  their recursion inclines the force there at the one of the slice on its
  left; the march could not give back their normals (5.95 and 2.79 apart).

What is asserted, none of it a snapshot:

* two forces in equilibrium are collinear: through a frictionless slice on
  a horizontal base with nothing else that has a moment, the thrust keeps
  its height (statics; the old line mirrored it about the base);
* every slice balances its moments, written out here with the
  anticlockwise convention and independently of the march, except the two
  next to the centre one, which carry half of the imbalance each; and that
  imbalance is the moment of the external forces about any point, which
  does not depend on the line at all (a check on the bookkeeping here);
* both free ends of the line sit on the base;
* the three methods of the family give back their own normals, on the bare
  slope, with an active and a passive nail, and mirrored;
* rule 7: each switch moves its number, and neither moves a force.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.221 tree: see ``_auditoria/P4_0222`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

FAMILY = ("corps_engineers_1", "corps_engineers_2", "lowe_karafiath")
BALANCED = ("spencer", "gle_morgenstern_price", "corps_engineers_1",
            "corps_engineers_2", "lowe_karafiath", "janbu_simplified",
            "bishop_simplified")
_CACHE: dict = {}


def _solve(method_id, case="bare"):
    """The result of ``method_id`` on one of the fixtures: the circle of
    ``test_support_normal_v1137`` bare, with its -15 deg nail active or
    passive, or mirrored about x = 0; or the ponded dam face of
    ``test_interslice_ponded_v1214`` with an earthquake."""
    key = (method_id, case)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        if case == "ponded":
            from ogr_slip2d.surface import SlipCircle
            from test_interslice_ponded_v1214 import (CIRCLE, N_SLICES,
                                                      _project as _pond)
            p = _pond(True, 0.1, 0.05)
            c = SlipCircle(**CIRCLE)
            sl = slice_surface(p, c, num_slices=N_SLICES)
        else:
            from test_support_normal_v1137 import (NSLICES, _circle, _nail,
                                                   _project)
            nail = {"active": _nail(-15.0, True),
                    "passive": _nail(-15.0, False)}.get(case)
            p = _project(nail)
            c = _circle()
            if case == "mirrored":
                p, c = _mirrored(p, c)
            sl = slice_surface(p, c, num_slices=NSLICES)
        res = method_registry()[method_id]().compute_fos(p, c, sl)
        assert res.fos is not None, (method_id, case, res.error_message)
        _CACHE[key] = res
    return _CACHE[key]


def _solve_fresh(method_id):
    """The bare slope solved now, under whatever switches are set, and not
    cached: the cache holds the default recursion."""
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from test_support_normal_v1137 import NSLICES, _circle, _project
    p, c = _project(None), _circle()
    sl = slice_surface(p, c, num_slices=NSLICES)
    return method_registry()[method_id]().compute_fos(p, c, sl)


def _mirrored(p, c):
    """The same model reflected about x = 0, as
    ``test_failure_direction_v173._mirrored`` does: the two are provably
    the same problem."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipCircle
    for b in p.boundaries:
        vs = [Vertex(-v.x, v.y) for v in reversed(b.polyline.vertices)]
        b.polyline = Polyline(vertices=vs, closed=b.polyline.closed)
        if b.polyline.closed:
            b.polyline.ensure_ccw()
    return p, SlipCircle(centre_x=-c.centre_x, centre_y=c.centre_y,
                         radius=c.radius)


def _state(res, balanced=True, as_solved=True):
    """The march with the two switches as asked, put back afterwards (the
    runner has no teardown). ``as_solved`` acts through what the result
    publishes, so off, the ratios are published again under it."""
    from ogr_slip2d import postprocess as pp
    from ogr_slip2d.methods import modified_swedish as ms
    old = (getattr(pp, "THRUST_LINE_BALANCED", None),
           getattr(ms, "BOUNDARY_RATIOS_AS_SOLVED", None))
    pp.THRUST_LINE_BALANCED = balanced
    ms.BOUNDARY_RATIOS_AS_SOLVED = as_solved
    try:
        if not as_solved:
            res = _resolve(res)
        return pp.compute_interslice_state(res)
    finally:
        for mod, name, val in ((pp, "THRUST_LINE_BALANCED", old[0]),
                               (ms, "BOUNDARY_RATIOS_AS_SOLVED", old[1])):
            if val is None:
                vars(mod).pop(name, None)
            else:
                setattr(mod, name, val)


def _resolve(res):
    """A copy of ``res`` whose ratios are published again under the current
    value of the switch: the solve itself does not read it."""
    import copy
    from ogr_slip2d.methods import method_registry
    out = copy.copy(res)
    out.details = dict(res.details)
    out.details["boundary_ratios"] = (
        method_registry()[res.method_id]()._boundary_ratios(res.slices))
    return out


def _centroid(s):
    """Centroid of the slice quadrilateral (the shoelace formula), written
    here rather than borrowed from the module under test."""
    pts = [(s.base_x_left, s.base_y_left), (s.base_x_right, s.base_y_right),
           (s.base_x_right, s.top_y_right), (s.base_x_left, s.top_y_left)]
    a2 = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cr = x0 * y1 - x1 * y0
        a2 += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    return cx / (3.0 * a2), cy / (3.0 * a2)


def _loads(res, s):
    """The loads the method applied to slice ``s``: soil weight at its
    centroid, the rest of the vertical load (water, surface loads) where the
    slicer puts it, above the base midpoint, and the earthquake at the
    centroid, pushing the mass the way the method had it slide
    (``details["slide_sign"]`` is the sense the shear resists)."""
    from ogr_slip2d.external_forces import slice_forces
    kh = float(res.details.get("kh", 0.0) or 0.0)
    kv = float(res.details.get("kv", 0.0) or 0.0)
    f = slice_forces(s, kh, kv)
    return f, -res.details["slide_sign"] * f.h_seismic


def _residuals(res, st):
    """The anticlockwise moment about its base midpoint of every force on
    each slice, which equilibrium makes zero."""
    out = []
    sup_m = st.support_moment or [0.0] * len(res.slices)
    for i, s in enumerate(res.slices):
        f, h_seis = _loads(res, s)
        x_c = 0.5 * (s.base_x_left + s.base_x_right)
        y_c = 0.5 * (s.base_y_left + s.base_y_right)
        x_g, y_g = _centroid(s)
        # The left face pushes the slice with (E, X), the right one with
        # (-E, -X); the moment of F = (Fx, Fy) at (px, py) is
        # (px - x_c)*Fy - (py - y_c)*Fx.
        m = ((s.base_x_left - x_c) * st.X[i]
             - (st.y_thrust[i] - y_c) * st.E[i])
        m += (-(s.base_x_right - x_c) * st.X[i + 1]
              + (st.y_thrust[i + 1] - y_c) * st.E[i + 1])
        m += -(x_g - x_c) * f.w_soil
        m += -(y_g - y_c) * h_seis
        m += y_c * s.water_force_h - s.water_force_h_moment
        m += sup_m[i]
        out.append(m)
    return out


def _external_moment(res, st):
    """The moment about the origin of every force on the mass that is not
    an interslice force between two of its slices -- base normal and shear,
    loads, support, and whatever the march leaves at its right end. The
    sum of the residuals above is this, whatever the line of thrust."""
    total = 0.0
    sup_f = st.support_force or [[0.0, 0.0]] * len(res.slices)
    sup_m = st.support_moment or [0.0] * len(res.slices)
    for i, s in enumerate(res.slices):
        f, h_seis = _loads(res, s)
        a = s.base_angle
        x_c = 0.5 * (s.base_x_left + s.base_x_right)
        y_c = 0.5 * (s.base_y_left + s.base_y_right)
        x_g, y_g = _centroid(s)
        fx = -st.N[i] * math.sin(a) + st.S[i] * math.cos(a)
        fy = st.N[i] * math.cos(a) + st.S[i] * math.sin(a)
        total += x_c * fy - y_c * fx
        total += -x_g * f.w_soil - x_c * (f.w_total - f.w_soil)
        total += -y_g * h_seis - s.water_force_h_moment
        total += sup_m[i] + x_c * sup_f[i][1] - y_c * sup_f[i][0]
    last = res.slices[-1]
    total += -last.base_x_right * st.X[-1] + st.y_thrust[-1] * st.E[-1]
    return total


def _scale(res, st):
    top = max(max(s.top_y_left, s.top_y_right) for s in res.slices)
    bot = min(min(s.base_y_left, s.base_y_right) for s in res.slices)
    return max(1.0, st.e_max * (top - bot))


def _gap(a, b):
    return max(abs(x - y) / max(1.0, abs(y)) for x, y in zip(a, b))


def _solved(res):
    return res.details.get("solved_base_normal") or res.base_normal_force


# ======================================================================
def _flat_mass():
    """Seven slices built by hand: a steep base at each end, five
    frictionless slices on a horizontal base in between, all 1 m wide and
    4 m tall. With X = 0 each middle slice is pushed by two equal horizontal
    thrusts and nothing else has a moment about its base midpoint (the
    weight of a rectangle stands over it), so equilibrium demands that the
    two be collinear."""
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_slip2d.slicer import Slice
    rough = Material(name="rough", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    smooth = Material(name="smooth", unit_weight=20.0,
                      strength=MohrCoulomb(cohesion=0.0, friction_angle=0.0))
    ys = [2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0]
    out = []
    for i in range(7):
        x0, x1, y0, y1 = float(i), float(i + 1), ys[i], ys[i + 1]
        area = 0.5 * ((4.0 - y0) + (4.0 - y1))
        out.append(Slice(
            index=i, x_centre=x0 + 0.5, width=1.0,
            base_x_left=x0, base_x_right=x1, base_y_left=y0, base_y_right=y1,
            base_angle=math.atan2(y1 - y0, 1.0),
            base_length=math.hypot(1.0, y1 - y0),
            top_y_left=4.0, top_y_right=4.0, weight=20.0 * area,
            material=rough if i in (0, 6) else smooth))
    return out


class TestTwoForcesInEquilibriumAreCollinear:

    def _march(self, balanced):
        from ogr_slip2d import postprocess as pp
        old = getattr(pp, "THRUST_LINE_BALANCED", None)
        pp.THRUST_LINE_BALANCED = balanced
        try:
            return pp._march(_flat_mass(), [0.0] * 8, 1.5, 0.0, 0.0,
                             slide_sign=1.0)
        finally:
            if old is None:
                vars(pp).pop("THRUST_LINE_BALANCED", None)
            else:
                pp.THRUST_LINE_BALANCED = old

    def test_the_thrust_keeps_its_height_through_a_smooth_slice(self):
        st = self._march(True)
        assert st.ok
        e = st.E[1]
        assert abs(e) > 1.0, st.E                  # guard: there is a thrust
        assert all(st.E[j] == e for j in range(1, 7)), st.E
        # Slices 1 and 5, one in each traversal, and 3, the centre one.
        for i in (1, 3, 5):
            assert abs(st.y_thrust[i + 1] - st.y_thrust[i]) < 1e-12, (
                i, st.y_thrust)

    def test_the_old_line_mirrored_it_about_the_base(self):
        """Rule 7, and the defect as measured: with the known moments
        entered with the old sign, the thrust leaving slice 1 came out at
        minus the height it entered at (the base is at y = 0)."""
        st = self._march(False)
        h = st.y_thrust[1]
        assert abs(h) > 1e-3, h
        assert abs(st.y_thrust[2] + h) < 1e-12, st.y_thrust


# ======================================================================
class TestEverySliceBalancesItsMoments:

    def _check(self, res, st, label):
        res_m = _residuals(res, st)
        n = len(res_m)
        m = n // 2
        tol = 1e-9 * _scale(res, st)
        off = [i for i, r in enumerate(res_m)
               if i not in (m - 1, m + 1) and abs(r) > tol]
        assert not off, (label, off, [res_m[i] for i in off])
        assert abs(res_m[m - 1] - res_m[m + 1]) <= tol, (
            label, res_m[m - 1], res_m[m + 1])
        # Bookkeeping: the residuals add up to the moment of the external
        # forces, which the line of thrust cannot change.
        assert abs(sum(res_m) - _external_moment(res, st)) <= tol, (
            label, sum(res_m), _external_moment(res, st))
        return res_m[m - 1] + res_m[m + 1]

    def test_on_the_bare_slope(self):
        for mid in BALANCED:
            res = _solve(mid)
            st = _state(res)
            assert st.ok, mid
            self._check(res, st, mid)

    def test_with_the_nail(self):
        """The support's moment is one of the known moments (D212)."""
        for mid in ("spencer", "corps_engineers_2", "bishop_simplified"):
            for case in ("active", "passive"):
                res = _solve(mid, case)
                st = _state(res)
                assert st.support_moment, (mid, case)      # guard: it acts
                self._check(res, st, (mid, case))

    def test_under_a_pond_in_an_earthquake(self):
        """The water on the face and the earthquake, with kh and kv, are
        known moments too."""
        for mid in ("spencer", "lowe_karafiath", "janbu_simplified"):
            res = _solve(mid, "ponded")
            assert res.details.get("kh") == 0.1, mid        # guard
            st = _state(res)
            assert st.ok, mid
            assert any(abs(s.water_force_h) > 1.0 for s in res.slices)
            self._check(res, st, mid)

    def test_a_force_method_leaves_its_imbalance_at_the_centre(self):
        """Corps #1 does not satisfy the moment balance of the mass: its
        imbalance is not small, and it is all at the centre."""
        res = _solve("corps_engineers_1")
        st = _state(res)
        total = self._check(res, st, "corps_engineers_1")
        assert abs(total) > 1e-3 * _scale(res, st), total


# ======================================================================
class TestTheFreeEndsSitOnTheBase:

    def test_both_ends(self):
        for mid in BALANCED:
            res = _solve(mid)
            st = _state(res)
            sl = res.slices
            assert st.y_thrust[0] == sl[0].base_y_left, mid
            assert st.y_thrust[-1] == sl[-1].base_y_right, (
                mid, st.y_thrust[-1], sl[-1].base_y_right)


# ======================================================================
class TestTheFamilyMarchesWithItsOwnRatios:
    """The march is the family's own recursion once it has the ratios the
    recursion used, so it gives back the method's normals, to the tolerance
    of the method's root (the secant of the march closes the residual the
    root leaves: 1e-8 on the passive nail, 1e-15 elsewhere)."""

    def test_bare_and_with_the_nail(self):
        for mid in FAMILY:
            for case in ("bare", "active", "passive"):
                res = _solve(mid, case)
                st = _state(res)
                assert st.ok and st.relative_closure < 1e-6, (
                    mid, case, st.relative_closure)
                assert _gap(st.N, _solved(res)) < 1e-6, (
                    mid, case, _gap(st.N, _solved(res)))

    def test_mirrored(self):
        """The recursion keeps the order of the slices when it mirrors the
        geometry for the other sense of sliding, so the rule holds in both
        senses."""
        for mid in FAMILY:
            res = _solve(mid, "mirrored")
            st = _state(res)
            assert st.ok and _gap(st.N, _solved(res)) < 1e-6, (
                mid, _gap(st.N, _solved(res)))

    def test_the_old_ratios_part_from_the_method(self):
        """Rule 7: with the averaged ratios the march is not the method's
        state for the two members whose inclination varies (5.95 and 2.79
        on this slope), and Corps #1, whose inclination is one constant,
        publishes the same ratios bit for bit either way.

        Changed on purpose in v0.1.223 (D222): the recursion now inclines
        each boundary at the average of its two slices, which is what the
        ratios published before this fix said. So the switch moves the
        number against the recursion of v0.1.222 (``THETA_AT_BOUNDARY``
        off), where it was measured, and with D222 on the two publications
        are one and the same list."""
        from ogr_slip2d.methods import modified_swedish as ms
        for mid in ("corps_engineers_2", "lowe_karafiath"):
            ms.THETA_AT_BOUNDARY = False
            try:
                res = _solve_fresh(mid)
            finally:
                ms.THETA_AT_BOUNDARY = True
            assert _gap(_state(res).N, _solved(res)) < 1e-6, mid
            st = _state(res, as_solved=False)
            assert _gap(st.N, _solved(res)) > 1.0, (
                mid, _gap(st.N, _solved(res)))
            res = _solve(mid)
            new = _resolve(res).details["boundary_ratios"]
            ms.BOUNDARY_RATIOS_AS_SOLVED = False
            try:
                old = _resolve(res).details["boundary_ratios"]
            finally:
                ms.BOUNDARY_RATIOS_AS_SOLVED = True
            assert new == old, mid
        res = _solve("corps_engineers_1")
        new = _resolve(res).details["boundary_ratios"]
        from ogr_slip2d.methods import modified_swedish as ms
        ms.BOUNDARY_RATIOS_AS_SOLVED = False
        try:
            old = _resolve(res).details["boundary_ratios"]
        finally:
            ms.BOUNDARY_RATIOS_AS_SOLVED = True
        assert new == old


# ======================================================================
class TestTheSwitchMovesTheLineAndNothingElse:
    """Rule 7 for ``THRUST_LINE_BALANCED``: off, the line is the old one
    (on this slope Spencer's right free end came out at y = -608 237 m),
    and no force moves by a bit either way."""

    def test_off_the_line_is_the_old_one(self):
        res = _solve("spencer")
        on, off = _state(res), _state(res, balanced=False)
        assert on.y_thrust[-1] == res.slices[-1].base_y_right
        assert abs(off.y_thrust[-1]) > 1e3, off.y_thrust[-1]
        res_off = _residuals(res, off)
        assert sum(abs(r) > 1e-3 for r in res_off) > len(res_off) // 2

    def test_no_force_moves(self):
        for mid in ("spencer", "corps_engineers_2", "bishop_simplified"):
            res = _solve(mid, "active")
            on, off = _state(res), _state(res, balanced=False)
            for name in ("N", "S", "E", "X", "support_force",
                         "support_moment"):
                assert getattr(on, name) == getattr(off, name), (mid, name)
