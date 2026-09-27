# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.210 — the admissibility checks judge each surface as ITS OWN method
solved it (defect D172).

THE INVARIANT, in two halves.

1. The Tensile Stress Check tests the effective normal stress of the
   method's own solution, ``sigma' = N/l - u``. Each method publishes the
   total base normal of its solution in ``details["solved_base_normal"]``
   -- Spencer, GLE and the prescribed-inclination family their
   ``base_normal_force``, the Ordinary Method its cos^2-corrected normal
   plus the support's ``T_N`` -- and Bishop and both Janbu publish none,
   because the check's fallback form IS their own normal.
2. Both checks linearise the envelope at the stress the solver linearised
   it at, support included: each method publishes the load it added to
   ``w_total`` in ``details["sigma_support_load"]``. The m-alpha
   DENOMINATOR stays Bishop's for every screened method (D61, D111).

THE EXTERNAL REFERENCE (rule 1). The Ej_2 piezometric model, whose report
publishes the per-slice stresses of every method on one circle (the model
and the Ordinary column live in ``tests/test_slide_validation_ej2_piezo_v194.py``
and are imported from there, untouched). Which normal to test is not a
choice either: USACE EM 1110-2-1902 (2003), Appendix C, C-10.a, asks for
the CALCULATED normal forces of the analysis to be examined, and the base
normal "is consequently different for the various methods" (Krahn 2003,
Can. Geotech. J. 40, p. 645).

WHAT WAS WRONG, measured:
* with the check on, the Ej_2 toe slice came out in tension for the
  Ordinary Method, Spencer, GLE and Lowe-Karafiath (-0.06, -0.71, -0.73 and
  -0.61 kPa) where their published columns read +4.48, +33.2, +2.47 and
  +22.7: every method was judged with Bishop's normal at its own factor of
  safety, a hybrid no method but Bishop's and Janbu's computes;
* on a nail crossing a base at 51.4 deg under a power-curve envelope, the
  checks linearised at 9.457 kPa where Bishop and Janbu had 20.43 and
  Spencer, GLE and the family 33.69 (inclined at -15 deg), because the
  support never reached ``checks``.

WHY NOT THE CRITERION THE DEFECT REPORT WROTE. It asked for the identity
with ``base_normal_force`` for Bishop and Janbu on a model with a support.
That identity was ALREADY exact on v0.1.209 -- ``base_forces_no_interslice_
shear`` leaves the support out of ``N`` by a documented decision, exactly
as the check did -- so it could not see the defect, and after the fix it
fails whenever there is a support. What the solver used is rebuilt here
instead from its own primitives, and for an ACTIVE support in closed form:
the vertical load of an active support is exactly ``-f_v``.

WHY A NAIL AT -15 DEG. A horizontal active nail has ``f_v = 0``, so Bishop
and Janbu add nothing and every witness for them passes on the old tree.
The guards below check that each family's load is large on the crossed
slice.

WHAT THIS FILE DOES NOT CLAIM. Not the unexplained 1.3-4.9 kPa between the
own stress of Spencer, GLE and Lowe-Karafiath and their published columns
(D201). Not that the Ordinary Method's ``base_normal_force`` is right: it
is the uncorrected ``N`` (D197), which is why that method publishes its own
normal separately. Not that including ``T_N`` in the Ordinary Method's
stress is validated: it follows from its resistance ``+ T_N*tan(phi')``
and is written as a decision.

DISCRIMINATION against the v0.1.209 tree. MEASURED, by copying this file into
a ``git worktree`` at a6eceda and running it there. Of the 26 cases, **16
fail and 10 pass**:

  fail  bishop_circle, bishop_polyline, janbu_simplified, janbu_corrected,
        spencer_gle_and_the_family              (behaviour: residual 0.54
                                                 and 0.72 on that tree)
        its_effective_stress_is_the_published_column (behaviour: 16.77 kPa)
        bishops_normal_carries_its_vertical_load  (behaviour: 12.83 vs 32.35)
        spencer_is_tested_with_its_own_normal      (behaviour)
        no_false_error_120                         (behaviour: the Ordinary
                                                    toe slice rejected)
        the_own_stress_is_nearer_the_published_... (behaviour)
        the_tensile_stress_is_the_methods_own      (text)
        a_passive_support_is_read_from_the_last_pass, the_active_load_is_
        minus_f_v, its_total_normal_is_the_published_base_normal_stress,
        its_strength_is_c_plus_its_stress_times_tan_phi,
        the_support_load_is_asked_of_the_method    (WEAK: a key or a
                                                    parameter that is not)

  pass  the two fixture guards, the published-compression guard,
        it_publishes_no_support_load (guard), bishop_is_still_rejected_...
        (control) and the five of TestWhatDoesNotMove (controls).

The run is archived in the bank as
``_auditoria/D172_sigma_propia/discriminacion_test_v1210_en_0.1.209.txt``.
"""
from __future__ import annotations

import copy
import math

# --- Published per-method slice columns, Ej_2 piezometric report ------
# (the reference's report in ``referencias/Ejemplos/Ej_2/Ej_2_Piezometric_Line/``,
# Global Minimum Query of each method, all on the same circle; 25 slices left
# to right; kPa). The reference folder is not in the repository, so the
# numbers are written out by hand.
PUB_BASE_NORMAL_ORDINARY = [
    8.88967, 26.1508, 42.424, 57.6484, 71.7654, 84.7192, 96.4569, 106.927,
    116.083, 123.877, 130.267, 135.211, 138.666, 140.595, 140.955, 139.705,
    136.794, 132.168, 122.843, 108.027, 90.3684, 69.3512, 44.4087, 13.4697,
    2.6228,
]
PUB_SIGMA_EFF = {
    "spencer": [
        33.2046, 40.1313, 45.0576, 48.3109, 50.1546, 50.803, 50.4316,
        49.1843, 47.182, 44.5248, 41.2965, 37.5708, 33.4083, 28.8637,
        23.9847, 18.8156, 13.3999, 7.77913, 6.01276, 12.4536, 14.2709,
        15.5754, 16.5428, 14.3347, -4.55734],
    "gle_morgenstern_price": [
        2.4722, 16.4475, 30.3554, 43.1645, 53.8303, 61.4899, 65.6136,
        66.0843, 63.1938, 57.5576, 49.9945, 41.3795, 32.5251, 24.0908,
        16.5415, 10.1507, 5.02641, 1.14369, 2.04748, 13.1242, 18.5412,
        22.373, 23.447, 15.6563, -10.0625],
    "lowe_karafiath": [
        22.6895, 32.5045, 40.7155, 47.3511, 52.4433, 56.0285, 58.1466,
        58.844, 58.1723, 56.1928, 52.9723, 48.5916, 43.1437, 36.7357,
        29.4923, 21.5557, 13.0855, 4.25401, 0.119687, 1.36208, 1.6651,
        2.33568, 14.3838, 19.2396, -3.61147],
    "bishop_simplified": [
        -0.789536, 5.8191, 11.7331, 16.9842, 21.5975, 25.594, 28.9896,
        31.7962, 34.0226, 35.6717, 36.7446, 37.2362, 37.1392, 36.4393,
        35.118, 33.1479, 30.4957, 27.1151, 25.455, 36.7274, 35.4748,
        32.4084, 27.0595, 14.4166, -11.2749],
}

NAIL_ANGLE = -15.0
FAMILY_NF = ("spencer", "gle_morgenstern_price", "corps_engineers_1",
             "lowe_karafiath")
BISHOP_JANBU = ("bishop_simplified", "janbu_simplified", "janbu_corrected")
_CACHE: dict = {}


# ======================================================================
def _ej2(method_id):
    from test_slide_validation_ej2_piezo_v194 import SMALL, _result
    res = _result(method_id, SMALL)
    assert res is not None and res.is_valid, method_id
    return res


def _tested(res, percent=95.0):
    """Slice indices the Tensile Stress Check tests, toe first -- written
    out from the rule, not imported, so the guard does not lean on it."""
    sl = list(res.slices)
    order = list(range(len(sl)))
    if not sl[0].top_y_left < sl[-1].top_y_right:
        order.reverse()
    return order[:int(round(len(sl) * percent / 100.0))]


def _hybrid(res):
    """Bishop's normal at this result's factor of safety, written out:
    what every method was judged with until v0.1.210."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    F = res.fos
    s_sum = sum(s.weight * math.sin(s.base_angle) for s in res.slices)
    sgn = 1.0 if s_sum >= 0 else -1.0
    out = []
    for s in res.slices:
        a, l, u = s.base_angle, max(s.base_length, 1e-12), s.pore_pressure
        w = s.weight + getattr(s, "water_weight", 0.0)
        sig = max(0.0, w * math.cos(a) - u * l) / l
        c, t = BishopSimplified._local_c_phi(s, s.material, sig)
        m = math.cos(a) + sgn * math.sin(a) * t / F
        out.append((w - sgn * (c * l * math.sin(a)
                               - u * l * t * math.sin(a)) / F) / m / l - u)
    return out


def _support_project(active=True, angle=NAIL_ANGLE, power=True):
    from ogr_core.materials.builtin_models import PowerCurve
    from test_support_normal_v1137 import _nail, _project
    p = _project(_nail(angle, active))
    if power:
        p.materials[0].strength = PowerCurve(a=3.4, b=0.6, c=0.0, d=0.15,
                                             waviness=0.0)
    return p


def _solve(method_id, active=True, surface="circle", power=True):
    key = (method_id, active, surface, power)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES, _circle
        from ogr_slip2d.methods import base
        p = _support_project(active, power=power)
        surf = _circle() if surface == "circle" else _polyline_of(_circle())
        sl = slice_surface(p, surf, num_slices=NSLICES)
        # v0.1.213 (D84) -- at the Fellenius point, switch off: this file
        # rebuilds the solver's stress ESTIMATE from its support load, which
        # since then is the first pass and the switch-off path of a curved
        # envelope (the rest is read at the method's own stress, and the
        # checks follow ``details["envelope_stress"]``; that half is pinned
        # in ``test_envelope_own_stress_v1213.py``). Restored in ``finally``.
        old = base.ENVELOPE_AT_OWN_STRESS
        base.ENVELOPE_AT_OWN_STRESS = False
        try:
            res = method_registry()[method_id]().compute_fos(p, surf, sl)
        finally:
            base.ENVELOPE_AT_OWN_STRESS = old
        assert res.is_valid, (method_id, res.error_message)
        _CACHE[key] = (p, surf, sl, res)
    return _CACHE[key]


def _polyline_of(circle, n=41):
    """``circle`` resampled as a polyline of ``n`` vertices, to reach
    Bishop's general (non-circular) branch on the same mass. Sampled from
    the circle's own slice bases rather than invented, so it daylights and
    the same nail crosses it -- the trick of
    ``tests/test_support_noncircular_v1140.py``."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipSurface
    from test_support_normal_v1137 import _project
    sl = slice_surface(_project(None), circle, num_slices=200)
    pts = [(sl.slices[0].base_x_left, sl.slices[0].base_y_left)]
    pts += [(s.base_x_right, s.base_y_right) for s in sl.slices]
    idx = [round(i * (len(pts) - 1) / (n - 1)) for i in range(n)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(*pts[i]) for i in idx]))


def _terms(p, surf, sl, res):
    from ogr_slip2d.support_integration import resolve_support_terms
    return resolve_support_terms(p, surf, sl,
                                 float(res.details.get("slide_sign", 1.0)))


def _check_sigmas(res):
    """The stresses ``base_m_alphas`` linearises the envelope at, observed
    by wrapping ``_local_c_phi`` -- the descriptor is put back in
    ``finally``, since the runner has no teardown."""
    from ogr_slip2d import checks
    from ogr_slip2d.methods.bishop import BishopSimplified as B
    seen = []
    desc = B.__dict__["_local_c_phi"]
    real = desc.__func__

    def spy(s, material, sigma):
        seen.append(sigma)
        return real(s, material, sigma)

    B._local_c_phi = staticmethod(spy)
    try:
        checks.base_m_alphas(res)
    finally:
        B._local_c_phi = desc
    return seen


def _rebuilt(res, load):
    """The solver's own stress estimate, rebuilt from ``load`` per slice."""
    from ogr_slip2d.external_forces import slice_forces
    kv = float(res.details.get("kv") or 0.0)
    out = []
    for k, s in enumerate(res.slices):
        w = slice_forces(s, 0.0, kv).w_total + load[k]
        l = s.base_length
        out.append(max(0.0, w * math.cos(s.base_angle)
                       - s.pore_pressure * l) / max(l, 1e-9))
    return out


def _residual(a, b):
    assert a and len(a) == len(b), (len(a), len(b))
    return max(abs(x - y) / max(1.0, abs(y)) for x, y in zip(a, b))


def _crossed(sup):
    return next(k for k, v in enumerate(sup.n_press)
                if v or sup.t_active[k] or sup.t_passive[k])


def _without(res, *keys):
    out = copy.copy(res)
    out.details = {k: v for k, v in (res.details or {}).items()
                   if k not in keys}
    return out


# ======================================================================
class TestTheOrdinaryMethodIsJudgedByItsOwnStress:
    """External: the Ordinary Method's published columns on Ej_2."""

    def test_its_effective_stress_is_the_published_column(self):
        from ogr_slip2d.checks import base_effective_stresses
        from test_slide_validation_ej2_piezo_v194 import (
            REF_SIGMA_EFF_ORDINARY,
        )
        got = base_effective_stresses(_ej2("ordinary_fellenius"))
        worst = max(abs(g - r) for g, r in zip(got, REF_SIGMA_EFF_ORDINARY))
        assert worst < 1e-3, worst          # measured 5.3e-4 kPa

    def test_its_total_normal_is_the_published_base_normal_stress(self):
        res = _ej2("ordinary_fellenius")
        n = res.details["solved_base_normal"]
        got = [N / s.base_length for N, s in zip(n, res.slices)]
        worst = max(abs(g - r) for g, r in zip(got, PUB_BASE_NORMAL_ORDINARY))
        assert worst < 2e-3, worst          # measured 1.2e-3 kPa


class TestTheToeIsNotInTension:
    """External: with the check on, a method is not rejected where its own
    published column is in compression on every tested slice -- and still
    is where its published column is in tension."""

    def test_the_published_columns_are_in_compression_where_tested(self):
        """Guard: the external fact the next case rests on."""
        from test_slide_validation_ej2_piezo_v194 import (
            REF_SIGMA_EFF_ORDINARY,
        )
        cols = dict(PUB_SIGMA_EFF, ordinary_fellenius=REF_SIGMA_EFF_ORDINARY)
        for mid in ("ordinary_fellenius", "spencer", "gle_morgenstern_price",
                    "lowe_karafiath"):
            tested = _tested(_ej2(mid))
            assert min(cols[mid][i] for i in tested) > 0.0, mid

    def test_no_false_error_120(self):
        from ogr_slip2d.checks import tensile_stress_check
        for mid in ("ordinary_fellenius", "spencer", "gle_morgenstern_price",
                    "lowe_karafiath"):
            ok, bad = tensile_stress_check(_ej2(mid))
            assert ok, (mid, bad)

    def test_bishop_is_still_rejected_where_its_column_is_in_tension(self):
        """Control: the check did not become permissive. Bishop's published
        column is -0.79 kPa on the toe slice, which is tested."""
        from ogr_slip2d.checks import tensile_stress_check
        res = _ej2("bishop_simplified")
        toe = _tested(res)[0]
        assert PUB_SIGMA_EFF["bishop_simplified"][toe] < 0.0
        ok, bad = tensile_stress_check(res)
        assert not ok and toe in bad, bad

    def test_the_own_stress_is_nearer_the_published_than_the_hybrid(self):
        from ogr_slip2d.checks import base_effective_stresses
        for mid in ("spencer", "gle_morgenstern_price", "lowe_karafiath"):
            res = _ej2(mid)
            pub = PUB_SIGMA_EFF[mid]
            own = max(abs(a - b) for a, b in
                      zip(base_effective_stresses(res), pub))
            hyb = max(abs(a - b) for a, b in zip(_hybrid(res), pub))
            assert own < 0.2 * hyb, (mid, own, hyb)


# ======================================================================
class TestTheFixtureCarriesALoadEachFamilyAdds:
    """GUARDS for the support half."""

    def test_the_nail_crosses_one_slice_with_both_loads_large(self):
        from ogr_slip2d.external_forces import slice_forces
        p, surf, sl, res = _solve("bishop_simplified")
        sup = _terms(p, surf, sl, res)
        i = _crossed(sup)
        w = slice_forces(res.slices[i], 0.0, 0.0).w_total
        assert abs(sup.f_v[i]) > 0.5 * w, (sup.f_v[i], w)
        assert abs(sup.f_v[i] - sup.nf_v[i]) > 0.5 * w, (sup.f_v[i],
                                                        sup.nf_v[i], w)

    def test_the_envelope_depends_on_sigma(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        _p, _surf, _sl, res = _solve("bishop_simplified")
        s = res.slices[len(res.slices) // 2]
        _c1, t1 = BishopSimplified._local_c_phi(s, s.material, 10.0)
        _c2, t2 = BishopSimplified._local_c_phi(s, s.material, 35.0)
        assert t1 > 1.2 * t2, (t1, t2)


class TestTheChecksLineariseWhereTheSolverDid:
    """The support half of the defect. Every case fails on v0.1.209 by
    BEHAVIOUR, method by method."""

    def _bishop_janbu(self, mid, surface="circle"):
        p, surf, sl, res = _solve(mid, surface=surface)
        sup = _terms(p, surf, sl, res)
        # closed form: an ACTIVE support loads the slice with -f_v
        want = _rebuilt(res, [-v for v in sup.f_v])
        assert _residual(_check_sigmas(res), want) < 1e-12, mid

    def test_bishop_circle(self):
        self._bishop_janbu("bishop_simplified")

    def test_bishop_polyline(self):
        self._bishop_janbu("bishop_simplified", surface="polyline")

    def test_janbu_simplified(self):
        self._bishop_janbu("janbu_simplified")

    def test_janbu_corrected(self):
        self._bishop_janbu("janbu_corrected")

    def test_spencer_gle_and_the_family(self):
        for mid in FAMILY_NF:
            p, surf, sl, res = _solve(mid)
            sup = _terms(p, surf, sl, res)
            want = _rebuilt(res, [-v for v in sup.nf_v])
            assert _residual(_check_sigmas(res), want) < 1e-12, mid

    def test_the_active_load_is_minus_f_v(self):
        """The closed form the witnesses above rest on, for what Bishop and
        Janbu PUBLISH: ``n_press*cos a - s*sin a*t_active`` is ``-f_v``."""
        for mid in BISHOP_JANBU:
            p, surf, sl, res = _solve(mid)
            sup = _terms(p, surf, sl, res)
            got = res.details["sigma_support_load"]
            for k, v in enumerate(sup.f_v):
                assert abs(got[k] + v) <= 1e-12 * max(1.0, abs(v)), (mid, k)

    def test_a_passive_support_is_read_from_the_last_pass(self):
        """A passive load depends on F; the check reads the published list,
        which is the last pass's, within the convergence tolerance of the
        load at the reported F."""
        from ogr_slip2d.support_integration import support_vertical_load
        p, surf, sl, res = _solve("bishop_simplified", active=False)
        sup = _terms(p, surf, sl, res)
        load = res.details["sigma_support_load"]
        i = _crossed(sup)
        at_f = support_vertical_load(sup, i, res.slices[i].base_angle,
                                     float(res.details["slide_sign"]),
                                     res.fos)
        assert abs(load[i] - at_f) <= 1e-3 * max(1.0, abs(at_f)), (load[i],
                                                                 at_f)
        assert _residual(_check_sigmas(res), _rebuilt(res, load)) < 1e-12


class TestTheTensileNormalTakesTheSupport:
    """The other half: the normal the Tensile Stress Check tests."""

    def test_bishops_normal_carries_its_vertical_load(self):
        from ogr_slip2d.checks import base_effective_stresses
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.methods.bishop import BishopSimplified
        p, surf, sl, res = _solve("bishop_simplified")
        sup = _terms(p, surf, sl, res)
        i = _crossed(sup)
        s = res.slices[i]
        sgn = float(res.details["m_alpha_sign"])
        a, l, u, F = s.base_angle, s.base_length, s.pore_pressure, res.fos
        w = slice_forces(s, 0.0, 0.0).w_total - sup.f_v[i]
        sig = max(0.0, w * math.cos(a) - u * l) / l
        c, t = BishopSimplified._local_c_phi(s, s.material, sig)
        m = math.cos(a) + sgn * math.sin(a) * t / F
        want = (w - sgn * (c * l * math.sin(a)
                           - u * l * t * math.sin(a)) / F) / m / l - u
        got = base_effective_stresses(res)[i]
        assert abs(got - want) <= 1e-9 * max(1.0, abs(want)), (got, want)

    def test_spencer_is_tested_with_its_own_normal(self):
        from ogr_slip2d.checks import base_effective_stresses
        _p, _surf, _sl, res = _solve("spencer")
        want = [N / s.base_length - s.pore_pressure
                for N, s in zip(res.base_normal_force, res.slices)]
        assert _residual(base_effective_stresses(res), want) < 1e-12


class TestTheOrdinaryMethodsOwnForm:
    def test_its_strength_is_c_plus_its_stress_times_tan_phi(self):
        """Internal identity with a support and Mohr-Coulomb: the published
        normal is the one the method's own resistance was built from,
        ``tau*l = c*l + (N - u*l)*tan(phi')`` wherever N' >= 0."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        p, surf, sl, res = _solve("ordinary_fellenius", power=False)
        sup = _terms(p, surf, sl, res)
        n = res.details["solved_base_normal"]
        checked = 0
        for k, s in enumerate(res.slices):
            sig = n[k] / s.base_length - s.pore_pressure
            # Only where the soil's own N' is in compression: below zero the
            # method clips the soil part and keeps T_N (D198, reported).
            if n[k] - s.pore_pressure * s.base_length - sup.n_press[k] < 0.0:
                continue
            c, t = BishopSimplified._local_c_phi(s, s.material, sig)
            want = c * s.base_length + sig * s.base_length * t
            got = res.base_shear_strength[k]
            assert abs(got - want) <= 1e-9 * max(1.0, abs(want)), (k, got,
                                                                  want)
            checked += 1
        assert checked >= len(res.slices) // 2

    def test_it_publishes_no_support_load(self):
        _p, _surf, _sl, res = _solve("ordinary_fellenius")
        assert res.details.get("sigma_support_load") is None


# ======================================================================
class TestWhatDoesNotMove:
    """Controls and guards; these pass on v0.1.209 as well."""

    def test_without_a_support_the_key_is_none_and_nothing_moves(self):
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES, _circle, _project
        p = _project(None)
        sl = slice_surface(p, _circle(), num_slices=NSLICES)
        for mid in ("bishop_simplified", "janbu_simplified", "spencer"):
            res = method_registry()[mid]().compute_fos(p, _circle(), sl)
            assert (res.details or {}).get("sigma_support_load") is None, mid
            bare = _without(res, "sigma_support_load")
            assert base_m_alphas(res) == base_m_alphas(bare), mid

    def test_bishop_without_a_support_is_its_published_normal(self):
        """The D167 identity, exact, on the no-support model."""
        from ogr_slip2d.checks import base_effective_stresses
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES, _circle, _project
        p = _project(None)
        sl = slice_surface(p, _circle(), num_slices=NSLICES)
        res = method_registry()["bishop_simplified"]().compute_fos(
            p, _circle(), sl)
        want = [N / max(s.base_length, 1e-12) - s.pore_pressure
                for N, s in zip(res.base_normal_force, res.slices)]
        got = base_effective_stresses(res)
        assert max(abs(a - b) / max(1.0, abs(b))
                   for a, b in zip(got, want)) == 0.0

    def test_a_malformed_key_reads_as_no_key_and_never_raises(self):
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        _p, _surf, _sl, res = _solve("spencer")
        n = len(res.slices)
        bare = _without(res, "sigma_support_load", "solved_base_normal")
        for bad in ("abc", [float("nan")] * n, [1.0], None, 3.0,
                    [None] * n):
            for key in ("sigma_support_load", "solved_base_normal"):
                probe = _without(res, "sigma_support_load",
                                 "solved_base_normal")
                probe.details[key] = bad
                assert base_m_alphas(probe) == base_m_alphas(bare), (key, bad)
                assert (base_effective_stresses(probe)
                        == base_effective_stresses(bare)), (key, bad)

    def test_the_limits_and_the_sets_are_untouched(self):
        from ogr_slip2d import checks
        assert checks.M_ALPHA_LIMIT == 0.2
        assert checks.M_ALPHA_SCREENED == frozenset({
            "bishop_simplified", "janbu_simplified", "janbu_corrected",
            "spencer", "gle_morgenstern_price"})
        assert checks.NO_M_ALPHA_DENOMINATOR == frozenset(
            {"ordinary_fellenius"})

    def test_the_factor_of_safety_does_not_read_the_new_keys(self):
        """The keys are published AFTER the solve: removing them from a
        result changes what the checks read and nothing else."""
        _p, _surf, _sl, res = _solve("spencer")
        bare = _without(res, "sigma_support_load", "solved_base_normal")
        assert bare.fos == res.fos and bare.is_valid == res.is_valid


class TestTheDecisionIsWritten:
    def _doc(self, fn):
        import re
        return re.sub(r"\s+", " ", fn.__doc__ or "")

    def test_the_support_load_is_asked_of_the_method(self):
        import inspect

        from ogr_slip2d import checks
        par = inspect.signature(checks._base_load_and_sigma).parameters
        assert par["support_load"].kind is inspect.Parameter.KEYWORD_ONLY
        assert par["support_load"].default is inspect.Parameter.empty
        doc = self._doc(checks._base_load_and_sigma)
        assert "reported and not fixed here (D172)" not in doc
        assert "The Ordinary Method publishes none" in doc

    def test_the_tensile_stress_is_the_methods_own(self):
        from ogr_slip2d import checks
        doc = self._doc(checks.base_effective_stresses)
        assert "which is the quantity the reference tests" not in doc
        assert "C-10.a" in doc and "Krahn 2003" in doc
