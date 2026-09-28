# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.216 — in the Ordinary Method a support's normal force enters the
effective normal BEFORE it is clipped and before the envelope is read
(defect D198).

THE FORM (rule 1: the method's own derivation). The Ordinary Method resolves
every known force on a slice perpendicular to its base and neglects the
side forces (Fellenius 1936; the C-12 form, USACE EM 1110-2-1902, 2003,
Appendix C, and Eq. 6.57 of Duncan, Wright & Brandon, 2014, with the pore
force taken over the base's vertical projection, Turnbull & Hvorslev 1967).
A support's force is one more known force: its component normal to the
base, ``T_N``, adds to the base normal exactly, so the effective normal the
strength is read at is

    N' + T_N = W cos(a) - u*l*cos^2(a) + T_N,

and the resistance of the slice is ``c*l + max(0, N' + T_N)*tan(phi')``,
with ``(c, tan phi')`` the envelope linearised at ``max(0, N' + T_N)/l``.

WHAT WAS WRONG. Both paths linearised the envelope at the soil's stress
alone, already clipped, and added ``T_N*tan(phi')`` afterwards. So:

* where ``N' < 0 < N' + T_N`` the resistance was ``c*l + T_N*tan(phi')``,
  not ``c*l + (N' + T_N)*tan(phi')``;
* a support that LIFTS the base (``T_N < 0``) could take the resistance
  below ``c*l``, since nothing clipped the sum;
* the ``negative_effective_normal`` counter did not see the support;
* with an envelope that depends on the stress, ``tan(phi')`` came from a
  stress that was not the method's.

The witnesses: the nail of ``test_support_normal_v1137`` on its circle (50
slices, it crosses slice 46), at 90 deg on a dry slope (N' = 4.17, T_N =
-18.71 kN/m: it lifts the base out of compression) and at 0 deg with
ru = 1.3 (N' = -1.25, T_N = +23.45: it pushes the base out of tension).
Both paths of the method are checked, the circle and the same mass as a
polyline (the general moment path).

The expected strength is written out here from the slice and from
``resolve_support_terms`` -- not read from anything the method publishes.

CONTROLS: without a support the method is bit for bit what it was, with the
switch ``methods.ordinary.SUPPORT_IN_EFFECTIVE_NORMAL`` on or off; and the
switch moves the factor of the lifting witness (rule 7).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ORD = "ordinary_fellenius"
_CACHE: dict = {}

#: (angle of the nail in degrees, ru): the two witnesses.
LIFTS = (90.0, 0.0)
PUSHES = (0.0, 1.3)


# ======================================================================
class _Switch:
    """``ordinary.SUPPORT_IN_EFFECTIVE_NORMAL`` set and PUT BACK (the
    runner has no teardown). ``getattr``: on a tree without it, setting it
    does nothing, which is the old reading, so the cases fail on the
    number."""

    def __init__(self, on: bool):
        self.on = on

    def __enter__(self):
        from ogr_slip2d.methods import ordinary
        self.old = getattr(ordinary, "SUPPORT_IN_EFFECTIVE_NORMAL", None)
        ordinary.SUPPORT_IN_EFFECTIVE_NORMAL = self.on
        return self

    def __exit__(self, *exc):
        from ogr_slip2d.methods import ordinary
        if self.old is None:
            vars(ordinary).pop("SUPPORT_IN_EFFECTIVE_NORMAL", None)
        else:
            ordinary.SUPPORT_IN_EFFECTIVE_NORMAL = self.old
        return False


def _project(witness, power=False, support=True):
    from ogr_core.materials import PorePressureType
    from ogr_core.materials.builtin_models import PowerCurve
    from test_support_normal_v1137 import _nail, _project as _base
    angle, ru = witness
    p = _base(_nail(angle, False) if support else None, capacity=60.0)
    m = p.materials[0]
    if ru:
        m.pore_pressure = PorePressureType.RU_COEFFICIENT
        m.ru = ru
    if power:
        m.strength = PowerCurve(a=3.4, b=0.6, c=0.0, d=0.15, waviness=0.0)
    return p


def _surface(kind):
    from test_own_base_stress_v1210 import _polyline_of
    from test_support_normal_v1137 import _circle
    return _circle() if kind == "circle" else _polyline_of(_circle())


def _solve(witness, kind="circle", power=False, support=True, on=True):
    key = (witness, kind, power, support, on)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES
        p = _project(witness, power=power, support=support)
        surf = _surface(kind)
        sl = slice_surface(p, surf, num_slices=NSLICES)
        with _Switch(on):
            res = method_registry()[ORD]().compute_fos(p, surf, sl)
        assert res.fos is not None, (res.reason, res.error_message)
        _CACHE[key] = (p, surf, sl, res)
    return _CACHE[key]


def _t_n(p, surf, sl):
    """``T_N`` per slice, from the support terms themselves."""
    from ogr_slip2d.support_integration import resolve_support_terms
    sign = 1.0 if sum(s.weight * math.sin(s.base_angle)
                      for s in sl.slices) >= 0 else -1.0
    sup = resolve_support_terms(p, surf, sl, sign)
    return [sup.n_press[i] if sup.present else 0.0
            for i in range(len(sl.slices))]


def _n_eff(s):
    """The soil's own effective normal, C-12 form, dry of any load but the
    weight and ``u`` (no seismic, no ponded water in these witnesses)."""
    ca = math.cos(s.base_angle)
    return s.weight * ca - s.pore_pressure * s.base_length * ca * ca


def _expected_strengths(p, surf, sl):
    from ogr_slip2d.methods.bishop import BishopSimplified
    t_n = _t_n(p, surf, sl)
    out = []
    for s, t in zip(sl.slices, t_n):
        star = max(0.0, _n_eff(s) + t) / s.base_length
        c, tan_phi = BishopSimplified._local_c_phi(s, s.material, star)
        out.append((c + star * tan_phi) * s.base_length)
    return out


def _crossed(p, surf, sl):
    t_n = _t_n(p, surf, sl)
    hit = [i for i, t in enumerate(t_n) if t]
    assert hit, "the nail crosses no base"
    return hit


# ======================================================================
class TestTheWitnessesAreWhatTheyClaim:
    """Guards: each witness has the slice it is named after."""

    def test_the_lifting_nail_takes_a_base_out_of_compression(self):
        for kind in ("circle", "polyline"):
            p, surf, sl, _res = _solve(LIFTS, kind)
            t_n = _t_n(p, surf, sl)
            assert any(_n_eff(s) > 0.0 > _n_eff(s) + t
                       for s, t in zip(sl.slices, t_n)), kind

    def test_the_pushing_nail_takes_a_base_out_of_tension(self):
        for kind in ("circle", "polyline"):
            p, surf, sl, _res = _solve(PUSHES, kind)
            t_n = _t_n(p, surf, sl)
            assert any(_n_eff(s) < 0.0 < _n_eff(s) + t
                       for s, t in zip(sl.slices, t_n)), kind


class TestTheStrengthIsCPlusTheClippedSumTimesTanPhi:

    def _check(self, witness, kind, power):
        p, surf, sl, res = _solve(witness, kind, power)
        want = _expected_strengths(p, surf, sl)
        got = res.base_shear_strength
        assert len(got) == len(want)
        for k, (g, w) in enumerate(zip(got, want)):
            assert abs(g - w) <= 1e-9 * max(1.0, abs(w)), (
                witness, kind, power, k, g, w)

    def test_lifting_nail_mohr_coulomb(self):
        for kind in ("circle", "polyline"):
            self._check(LIFTS, kind, False)

    def test_pushing_nail_mohr_coulomb(self):
        for kind in ("circle", "polyline"):
            self._check(PUSHES, kind, False)

    def test_with_a_curved_envelope_the_tangent_is_read_at_the_sum(self):
        for witness in (LIFTS, PUSHES, (-15.0, 0.0)):
            for kind in ("circle", "polyline"):
                self._check(witness, kind, True)

    def test_a_lifting_support_never_takes_it_below_c_l(self):
        from test_support_normal_v1137 import COH
        for kind in ("circle", "polyline"):
            p, surf, sl, res = _solve(LIFTS, kind)
            for k, (g, s) in enumerate(zip(res.base_shear_strength,
                                           sl.slices)):
                assert g >= COH * s.base_length * (1.0 - 1e-12), (kind, k)
            for i in _crossed(p, surf, sl):
                cl = COH * sl.slices[i].base_length
                assert abs(res.base_shear_strength[i] - cl) <= 1e-9 * cl, (
                    kind, i, res.base_shear_strength[i], cl)


class TestTheCounterSeesTheSupport:
    """``negative_effective_normal`` counts the bases whose effective
    normal, support included, is negative."""

    def test_both_witnesses(self):
        for witness in (LIFTS, PUSHES):
            for kind in ("circle", "polyline"):
                p, surf, sl, res = _solve(witness, kind)
                t_n = _t_n(p, surf, sl)
                want = sum(1 for s, t in zip(sl.slices, t_n)
                           if _n_eff(s) + t < 0.0)
                got = res.details["negative_effective_normal"]
                assert got == want, (witness, kind, got, want)


class TestControls:

    def test_without_a_support_the_switch_changes_nothing(self):
        for witness in (LIFTS, PUSHES):
            for kind in ("circle", "polyline"):
                for power in (False, True):
                    a = _solve(witness, kind, power, support=False, on=False)
                    b = _solve(witness, kind, power, support=False, on=True)
                    assert a[3].fos == b[3].fos, (witness, kind, power)
                    assert (a[3].base_shear_strength
                            == b[3].base_shear_strength), (witness, kind)

    def test_the_switch_moves_the_lifting_witness(self):
        """Rule 7."""
        for kind in ("circle", "polyline"):
            a = _solve(LIFTS, kind, on=False)[3].fos
            b = _solve(LIFTS, kind, on=True)[3].fos
            assert b > a * (1.0 + 1e-6), (kind, a, b)
