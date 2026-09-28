# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.216 — ``base_normal_force`` is the normal of each method's OWN
equilibrium, support included, in all nine methods (defects D196 and D197).

WHAT THE COLUMN IS NOW. Since v0.1.210 (D172) the Tensile Stress Check
reads, per method, the normal of that method's solution
(``checks.base_effective_stresses``): Spencer, GLE and the prescribed-
inclination family their published normal; Bishop and both Janbu the
vertical equilibrium of a slice with no inter-slice shear, with the support
load their iteration applied; the Ordinary Method its ``N' + u*l + T_N``.
The COLUMN did not follow: Bishop and Janbu left the support out of it
(D196; on the nail below, 12.83 kPa published against 32.35 of their own
normal), and the Ordinary Method published the uncorrected ``W*cos(a)``
(D197), whose ``N/l - u`` is Eq. C-13 of USACE EM 1110-2-1902 (2003) and
Eq. 6.48 of Duncan, Wright & Brandon (2014), the form both warn "can lead
to unrealistically low or negative stresses". The owner chose (2026-09-28)
that the column be the method's own normal, support included.

WHAT PINS IT (rule 1):

* an identity, the column against the check, slice by slice, in the nine
  methods, with a nail active and passive, on a circle and on the same mass
  as a polyline, under Mohr-Coulomb and a power curve;
* a published case: the "Base Normal Stress" column of the reference's
  Ej_2 piezometric report for the Ordinary Method, reproduced from the
  column itself (it was 47.75 kPa out);
* the drawdown's own consistency (Duncan, Wright & Brandon 2014, Eqs.
  9.2-9.4): the stage-1 state is ONE solution, so its shear
  ``(c' + sigma'_fc*tan(phi'))/F`` must be the mobilised shear ``S/l`` of
  the solution it came from. With the Ordinary Method's uncorrected normal
  it was not.

WHAT DOES NOT MOVE: every factor of safety outside the drawdown, bit for
bit, switch on or off -- the column is post-processing, and in the Ordinary
Method's general path the list its moment balance uses is NOT the column
(the trap: it is the same variable name up to v0.1.215). Without a support
the Bishop/Janbu column is bit for bit what it was.

RULE 7: each switch moves its number -- the Bishop/Janbu normal on the
crossed slice, and the Ordinary Method's factor inside the drawdown of
Appendix G.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

NINE = ("ordinary_fellenius", "bishop_simplified", "janbu_simplified",
        "janbu_corrected", "spencer", "gle_morgenstern_price",
        "corps_engineers_1", "corps_engineers_2", "lowe_karafiath")
X0 = ("bishop_simplified", "janbu_simplified", "janbu_corrected")
ORD = "ordinary_fellenius"

_CACHE: dict = {}


# ======================================================================
class _Switch:
    """A module switch set and PUT BACK (the runner has no teardown).
    ``getattr``: on a tree without it, setting it does nothing, which is
    the old reading, so the cases fail on the number."""

    def __init__(self, module, name, on):
        self.module, self.name, self.on = module, name, on

    def __enter__(self):
        import importlib
        self.mod = importlib.import_module(self.module)
        self.old = getattr(self.mod, self.name, None)
        setattr(self.mod, self.name, self.on)
        return self

    def __exit__(self, *exc):
        if self.old is None:
            vars(self.mod).pop(self.name, None)
        else:
            setattr(self.mod, self.name, self.old)
        return False


def _d196(on):
    return _Switch("ogr_slip2d.methods.bishop",
                   "SUPPORT_IN_PUBLISHED_NORMAL", on)


def _d197(on):
    return _Switch("ogr_slip2d.methods.ordinary", "PUBLISH_OWN_NORMAL", on)


def _nail_project(active, power, support=True):
    from ogr_core.materials.builtin_models import PowerCurve
    from test_support_normal_v1137 import _nail, _project
    p = _project(_nail(-15.0, active) if support else None)
    if power:
        p.materials[0].strength = PowerCurve(a=3.4, b=0.6, c=0.0, d=0.15,
                                             waviness=0.0)
    return p


def _nail_surface(kind):
    from test_own_base_stress_v1210 import _polyline_of
    from test_support_normal_v1137 import _circle
    return _circle() if kind == "circle" else _polyline_of(_circle())


def _solve_nail(mid, active=True, kind="circle", power=False,
                support=True, on=True):
    key = ("nail", mid, active, kind, power, support, on)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES
        p = _nail_project(active, power, support)
        surf = _nail_surface(kind)
        sl = slice_surface(p, surf, num_slices=NSLICES)
        with _d196(on), _d197(on):
            res = method_registry()[mid]().compute_fos(p, surf, sl)
        _CACHE[key] = (p, surf, sl, res)
    return _CACHE[key]


def _column_stress(res):
    return [N / max(s.base_length, 1e-12) - s.pore_pressure
            for N, s in zip(res.base_normal_force, res.slices)]


def _crossed(p, surf, sl, res):
    from ogr_slip2d.support_integration import resolve_support_terms
    sup = resolve_support_terms(p, surf, sl,
                                float(res.details.get("slide_sign", 1.0)))
    hit = [i for i in range(len(sl.slices))
           if abs(sup.n_press[i]) + abs(sup.f_v[i]) > 0.0]
    assert hit, "the nail crosses no base"
    return hit


# ======================================================================
class TestTheColumnIsTheChecksNormal:
    """The identity, nine methods, support included."""

    def test_nine_methods_active_and_passive_on_the_circle(self):
        from ogr_slip2d.checks import base_effective_stresses
        for mid in NINE:
            for active in (True, False):
                for power in (False, True):
                    _p, _s, _sl, res = _solve_nail(mid, active, "circle",
                                                   power)
                    if res.fos is None:
                        continue
                    col = _column_stress(res)
                    own = base_effective_stresses(res)
                    assert len(col) == len(own), mid
                    for k, (a, b) in enumerate(zip(col, own)):
                        assert abs(a - b) <= 1e-9 * max(1.0, abs(b)), (
                            mid, active, power, k, a, b)

    def test_the_three_x0_methods_on_the_polyline(self):
        """Bishop's general branch and both Janbu on the same mass."""
        from ogr_slip2d.checks import base_effective_stresses
        for mid in X0 + (ORD,):
            for active in (True, False):
                _p, _s, _sl, res = _solve_nail(mid, active, "polyline")
                assert res.fos is not None, (mid, res.reason)
                col = _column_stress(res)
                own = base_effective_stresses(res)
                for k, (a, b) in enumerate(zip(col, own)):
                    assert abs(a - b) <= 1e-9 * max(1.0, abs(b)), (
                        mid, active, k, a, b)

    def test_every_method_the_witness_names_gave_a_factor(self):
        """Guard: the identity above did not pass by skipping."""
        for mid in NINE:
            _p, _s, _sl, res = _solve_nail(mid)
            assert res.fos is not None, (mid, res.reason)

    def test_the_crossed_slice_is_where_the_column_moved(self):
        """Rule 7, D196: the switch moves the Bishop/Janbu normal on the
        slice the nail crosses (12.83 -> 32.35 kPa on Bishop's)."""
        for mid in X0:
            p, surf, sl, on = _solve_nail(mid, on=True)
            off = _solve_nail(mid, on=False)[3]
            for i in _crossed(p, surf, sl, on):
                a = off.base_normal_force[i]
                b = on.base_normal_force[i]
                assert abs(b - a) > 1e-3 * max(1.0, abs(a)), (mid, i, a, b)


class TestNoFactorMoves:
    """The column is post-processing."""

    def test_bishop_and_janbu_with_the_nail(self):
        for mid in X0:
            for active in (True, False):
                for kind in ("circle", "polyline"):
                    a = _solve_nail(mid, active, kind, on=False)[3]
                    b = _solve_nail(mid, active, kind, on=True)[3]
                    assert a.fos == b.fos, (mid, active, kind, a.fos, b.fos)

    def test_without_a_support_the_column_is_what_it_was(self):
        for mid in X0:
            a = _solve_nail(mid, support=False, on=False)[3]
            b = _solve_nail(mid, support=False, on=True)[3]
            assert a.base_normal_force == b.base_normal_force, mid
            assert a.fos == b.fos, mid


# ======================================================================
def _ej2_polyline():
    """The Ej_2 piezometric mass as a polyline, sampled from the bases of
    its reference circle: a WET general path for the Ordinary Method."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle, SlipSurface
    from test_slide_validation_ej2_piezo_v194 import SMALL, _project
    cx, cy, r = SMALL
    sl = slice_surface(_project(), SlipCircle(centre_x=cx, centre_y=cy,
                                              radius=r), num_slices=200)
    pts = [(sl.slices[0].base_x_left, sl.slices[0].base_y_left)]
    pts += [(s.base_x_right, s.base_y_right) for s in sl.slices]
    # Eleven vertices: each is a mandatory cut, and the reference's 25
    # slices cannot spend more cuts than they have.
    idx = [round(i * (len(pts) - 1) / 10) for i in range(11)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(*pts[i]) for i in idx]))


def _ordinary_ej2(kind, on):
    key = ("ej2", kind, on)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        from test_slide_validation_ej2_piezo_v194 import (NUM_SLICES, SMALL,
                                                          _project)
        p = _project()
        surf = (SlipCircle(*SMALL) if kind == "circle" else _ej2_polyline())
        sl = slice_surface(p, surf, num_slices=NUM_SLICES)
        with _d197(on):
            res = method_registry()[ORD]().compute_fos(p, surf, sl)
        assert res.fos is not None, (kind, res.reason)
        _CACHE[key] = res
    return _CACHE[key]


class TestTheOrdinaryMethodsColumn:
    """D197: C-12, the published table, and nothing else moves."""

    def test_it_reproduces_the_published_base_normal_stress(self):
        from test_own_base_stress_v1210 import PUB_BASE_NORMAL_ORDINARY
        res = _ordinary_ej2("circle", True)
        got = [N / s.base_length
               for N, s in zip(res.base_normal_force, res.slices)]
        assert len(got) == len(PUB_BASE_NORMAL_ORDINARY)
        worst = max(abs(a - b) for a, b in zip(got,
                                               PUB_BASE_NORMAL_ORDINARY))
        assert worst < 2e-3, worst

    def test_and_the_published_effective_normal_stress(self):
        """Through the interpretation's slice table, the reader."""
        from ogr_slip2d.interpretation import slice_rows
        from test_slide_validation_ej2_piezo_v194 import (
            REF_SIGMA_EFF_ORDINARY)
        rows = slice_rows(_ordinary_ej2("circle", True))
        got = [r["sigma_n_eff"] for r in rows]
        worst = max(abs(a - b) for a, b in zip(got, REF_SIGMA_EFF_ORDINARY))
        assert worst < 2e-3, worst

    def test_its_factor_does_not_move_on_the_circle_or_a_wet_polyline(self):
        """The general path's moment balance keeps its own list."""
        for kind in ("circle", "polyline"):
            a = _ordinary_ej2(kind, False).fos
            b = _ordinary_ej2(kind, True).fos
            assert a == b, (kind, a, b)

    def test_the_polyline_is_wet(self):
        """Guard: C-12 and C-13 differ only where u*(1 - cos^2 a) != 0."""
        res = _ordinary_ej2("polyline", True)
        assert any(s.pore_pressure > 1.0 and abs(s.base_angle) > 0.2
                   for s in res.slices)


# ======================================================================
def _appendix_g_ordinary(procedure, on):
    key = ("apg", procedure, on)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        from test_drawdown_usace_v169 import _appendix_g, _circle
        with _d197(on):
            _CACHE[key] = rapid_drawdown_fos(
                _appendix_g(procedure=procedure), _circle(),
                method_registry()[ORD](), num_slices=50,
                procedure=procedure)
    return _CACHE[key]


class TestTheDrawdownReadsTheSolutionItCameFrom:
    """Duncan, Wright & Brandon (2014), Eqs. 9.2-9.4."""

    def test_the_stage_one_shear_is_the_mobilised_shear(self):
        """tau_fc = (c' + sigma'_fc*tan(phi'))/F1 must be S/l of the same
        stage-1 solution, slice by slice."""
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.rapid_drawdown import _stage1_state
        from ogr_slip2d.slicer import slice_surface
        from test_drawdown_usace_v169 import _appendix_g, _circle
        p = _appendix_g()
        sl = slice_surface(p, _circle(), num_slices=50)
        res = method_registry()[ORD]().compute_fos(p, _circle(), sl)
        assert res.fos is not None
        state = _stage1_state(p, _circle(), sl, res)
        wet = 0
        for (_xl, _xr, _sig, tau), s, strength in zip(
                state, sl.slices, res.base_shear_strength):
            want = strength / s.base_length / res.fos
            assert abs(tau - want) <= 1e-9 * max(1.0, abs(want)), (
                s.index, tau, want)
            wet += s.pore_pressure > 0.0
        assert wet > 10, wet

    def test_the_switch_moves_the_drawdown_factor(self):
        """Rule 7, D197, on the given circle of Appendix G (published by
        other methods: 1.35 two-stage, 1.44 Duncan-Wright)."""
        for proc in ("corps_2", "duncan_wright"):
            a = _appendix_g_ordinary(proc, False).fos
            b = _appendix_g_ordinary(proc, True).fos
            assert b > a * 1.05, (proc, a, b)
