# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The m-alpha check reads the sign the METHOD formed its denominator with.

INVARIANT PROTECTED
-------------------
``m_alpha = cos(a) + s*sin(a)*tan(phi)/F`` is not symmetric in ``a``, so
it means nothing unless ``s`` is the sign the method itself used. Until
v0.1.189 ``checks`` did not ask: it RE-DERIVED ``s`` from
``sign(sum W*sin a)``, which is Bishop's sum. Janbu derives its own from
``sign(sum w_total*tan a)`` — the ponded water rides inside ``w_total``,
and ``tan`` weights a steep base far more heavily than ``sin`` — so the
guess can come out backwards, and then the check reports an ordinary
slice as one with negative resistance.

That is the v0.1.82 anomaly, which this project has written down as "the
criterion was never wrong, it was being read in the mirror". v0.1.82
fixed the mirror for Bishop and left the guess in place.

WHY IT CANNOT REACH THE OTHER METHODS, WHICH IS HALF THE CLAIM
--------------------------------------------------------------
Bishop, Spencer, GLE, the Ordinary Method and the prescribed-inclination
family all derive theirs from ``sign(sum W*(1-kv)*sin a)``, and
``(1-kv) >= 0`` is a constant non-negative factor, which cannot invert a
sum. ``TestWhatCannotDiffer`` sweeps ``kv`` and shows it. A ficha that
exaggerates gets discounted whole, so the reach is stated exactly:
``janbu_simplified`` and ``janbu_corrected``, and nothing else.

WHY NOTHING HERE IS A SNAPSHOT
------------------------------
No case below fixes a factor of safety, or any other number, against
what this code prints today. The anchors are:

* the CLOSED FORM of the branch difference, ``m(+1) - m(-1) =
  2*sin(a)*tan(phi)/F``, which is algebra on Bishop's (1955) definition
  and is what makes ``phi = 0`` a control rather than an anecdote;
* the IDENTITY ``n_alpha == cos(a)*m_alpha`` between Janbu's denominator
  and Bishop's, recomputed here from the two expressions as the two
  solvers write them, never imported — it is what licenses reading
  Janbu's sign inside Bishop's form at all;
* the ALGEBRA of ``(1-kv)``, which bounds the defect's reach;
* an arithmetic WITNESS, three slices whose numbers are computed here
  from ``math.cos/sin/tan`` and not pasted, where the two sums disagree
  and the verdict flips;
* and the sign convention of the prescribed-inclination family, read
  back out of its own recursion and compared with the closed form.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Run against the v0.1.188 tree: 5 of the 18 cases FAIL, 13 PASS. The
split is measured, and the five are not all the same strength — saying
so is the point, because a failure that only means "the symbol is not
there yet" proves less than one that means "the engine answers
differently".

TWO fail on MEASURED BEHAVIOUR, and they are the defect itself:
``test_the_check_follows_the_declared_sign`` (there the two readings come
back identical, because the old check re-derives instead of reading) and
``test_and_the_difference_is_exactly_the_closed_form`` (0.0 where the
closed form wants -0.193).

THREE fail on ABSENCE, which is weak discrimination and is labelled as
such: ``test_janbu_publishes_its_own_sum_and_not_bishops`` on a missing
dictionary key, and two more on a missing module symbol.

The 13 that PASS do so BY DESIGN, because they state what the defect IS
by reading the engine rather than the fix: the closed form, the two
identities, the ``(1-kv)`` sweep, the witness arithmetic, the family's
sign trap and the fallback. A test that passes on both trees is not
evidence of the fix, and it is labelled here rather than left to look
like one.
"""
from __future__ import annotations

import math

GAMMA = 19.5                         # kN/m3
GAMMA_W = 9.81                       # kN/m3

_CACHE: dict = {}

#: The five methods the criterion is applied to, and which therefore have
#: to declare the sign their denominator carried. Read from the engine
#: rather than typed, so that moving the set moves this file.
def _screened():
    from ogr_slip2d.checks import M_ALPHA_SCREENED
    return sorted(M_ALPHA_SCREENED)


def _not_screened():
    from ogr_slip2d.checks import M_ALPHA_SCREENED
    from ogr_slip2d.methods import method_registry
    return sorted(set(method_registry()) - set(M_ALPHA_SCREENED))


# ----------------------------------------------------------------------
def _slope():
    """A plain 2:1 homogeneous slope that all nine methods can solve.

    v0.1.193 (D174) -- it took ``kv`` and ``kh`` until this version and wrote
    them to ``p.settings.seismic``, which holds the Ky and Newmark options and
    is read by no method: the earthquake lives on ``p.seismic``. No case ever
    passed them, so the branch was dead; it is gone rather than corrected,
    because a parameter nobody passes is the kind of setting that does
    nothing (rule 7). The ``(1 - kv)`` sweep of ``TestWhatCannotDiffer`` is
    arithmetic on the slices and never went through here.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(120, 0), Vertex(120, 40),
        Vertex(70, 40), Vertex(30, 20), Vertex(0, 20),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("slide-sign-slope")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="fill", unit_weight=GAMMA,
                            sat_unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=12.0,
                                                 friction_angle=28.0))]
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=55.0, centre_y=62.0, radius=48.0)


def _solve(method_id: str):
    """One converged result per method, shared across cases.

    Nine methods times a dozen cases would pay for the same arithmetic
    over and over; a file that did exactly that went from 48 s to 12 s
    by sharing its geometry.
    """
    key = method_id
    if key not in _CACHE:
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        p = _slope()
        surf = _circle()
        sl = slice_surface(p, surf, num_slices=25)
        assert sl is not None, key
        res = get_method(method_id)().compute_fos(p, surf, sl)
        _CACHE[key] = res
    return _CACHE[key]


# ----------------------------------------------------------------------
# The two sums, written out from their two definitions. Importing either
# solver's would make every assertion below a tautology.
# ----------------------------------------------------------------------
def _bishop_sum(slices, kv: float = 0.0) -> float:
    return sum(s.weight * (1.0 - kv) * math.sin(s.base_angle)
               for s in slices)


def _janbu_sum(slices, kh: float = 0.0, kv: float = 0.0) -> float:
    from ogr_slip2d.external_forces import slice_forces
    return sum(slice_forces(s, kh, kv).w_total * math.tan(s.base_angle)
               for s in slices)


def _sgn(x: float) -> float:
    return 1.0 if x >= 0 else -1.0


def _m_alpha(alpha: float, tan_phi: float, F: float, s: float) -> float:
    """Bishop (1955), written here and never imported."""
    return math.cos(alpha) + s * math.sin(alpha) * tan_phi / F


def _n_alpha(alpha: float, tan_phi: float, F: float, s: float) -> float:
    """Janbu's denominator, as ``methods/janbu.py`` forms it."""
    return (math.cos(alpha) ** 2) * (
        1.0 + s * math.tan(alpha) * tan_phi / F)


# ======================================================================
class TestTheSignIsAskedOfTheMethodThatFormedIt:
    """The contract: the method declares it, the check reads it."""

    def test_every_screened_method_publishes_the_sign(self):
        for mid in _screened():
            res = _solve(mid)
            assert res.fos is not None and res.is_valid, (mid,
                                                          res.error_message)
            det = res.details or {}
            assert "m_alpha_sign" in det, mid
            assert det["m_alpha_sign"] in (1.0, -1.0), (mid,
                                                        det["m_alpha_sign"])

    def test_the_methods_that_form_no_such_denominator_do_not(self):
        """And this is the half that is easy to get wrong.

        The Ordinary Method forms no denominator at all; the
        prescribed-inclination family forms one that is NOT
        ``cos a + s*sin a*tan phi/F`` for any ``s`` (see
        ``TestThePrescribedFamilySignTrap``). Publishing a sign for
        either would be inventing a quantity no method computes. They do
        still declare the sense of sliding they derived, which is a
        different thing and is used for the supports.
        """
        for mid in _not_screened():
            res = _solve(mid)
            assert res.fos is not None and res.is_valid, (mid,
                                                          res.error_message)
            det = res.details or {}
            assert "m_alpha_sign" not in det, mid
            assert "slide_sign" in det, mid

    def test_the_check_follows_the_declared_sign(self):
        """The defect stated as an experiment.

        The same converged result is read twice, once with each declared
        sign. If the check re-derives instead of reading, the two come
        back identical — which is exactly what the v0.1.188 tree does.
        """
        from ogr_slip2d.checks import base_m_alphas
        res = _solve("bishop_simplified")
        det = dict(res.details or {})
        try:
            res.details = dict(det, m_alpha_sign=1.0)
            plus = base_m_alphas(res)
            res.details = dict(det, m_alpha_sign=-1.0)
            minus = base_m_alphas(res)
        finally:
            res.details = det
        assert plus != minus
        worst = max(abs(a - b) for a, b in zip(plus, minus))
        assert worst > 1e-6, worst

    def test_and_the_difference_is_exactly_the_closed_form(self):
        """``m(+1) - m(-1) = 2*sin(a)*tan(phi)/F``, term by term.

        This is what makes the previous case a statement about Bishop's
        definition rather than about two lists that happen to differ.
        """
        from ogr_slip2d.checks import base_m_alphas
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _solve("bishop_simplified")
        det = dict(res.details or {})
        try:
            res.details = dict(det, m_alpha_sign=1.0)
            plus = base_m_alphas(res)
            res.details = dict(det, m_alpha_sign=-1.0)
            minus = base_m_alphas(res)
        finally:
            res.details = det
        n = 0
        for s, p, m in zip(res.slices, plus, minus):
            l = max(s.base_length, 1e-12)
            from ogr_slip2d.external_forces import slice_forces
            w = slice_forces(s).w_total
            sig = max(0.0, w * math.cos(s.base_angle)
                      - s.pore_pressure * l) / l
            _c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sig)
            want = 2.0 * math.sin(s.base_angle) * tan_phi / res.fos
            assert abs((p - m) - want) < 1e-12, (s.index, p - m, want)
            n += 1
        assert n >= 20, n          # the case must not pass on an empty loop


# ======================================================================
class TestJanbuDerivesItFromAnotherSum:
    """The one method the guess could not reach — and did not."""

    def test_janbu_publishes_its_own_sum_and_not_bishops(self):
        for mid in ("janbu_simplified", "janbu_corrected"):
            res = _solve(mid)
            assert res.is_valid, mid
            got = (res.details or {})["m_alpha_sign"]
            assert got == _sgn(_janbu_sum(res.slices)), mid

    def test_the_two_sums_are_genuinely_two_expressions(self):
        """Not merely two names for one number.

        On this dry slope they happen to agree in SIGN — and they must,
        or the null control of the witness below would be vacuous — but
        the sums themselves are different numbers, because ``tan``
        weights a steep base more than ``sin`` does.
        """
        res = _solve("janbu_simplified")
        b, j = _bishop_sum(res.slices), _janbu_sum(res.slices)
        assert abs(b - j) > 1e-6 * max(abs(b), abs(j)), (b, j)
        assert _sgn(b) == _sgn(j)          # here, but not everywhere


# ======================================================================
class TestTheWitnessWhereTheyDisagree:
    """Three slices, arithmetic only, where the guess comes out backwards
    and the verdict flips with it.

    Every number is computed from ``math`` below; none is pasted. The
    shape is the one the reference names for its own -112: a steep base
    in the passive zone, with water standing on it.
    """

    # (base angle deg, soil weight, ponded water weight)
    ROWS = ((-70.0, 100.0, 400.0), (20.0, 500.0, 0.0), (20.0, 500.0, 0.0))
    TAN_PHI = math.tan(math.radians(30.0))
    F = 1.3

    def _sums(self):
        b = sum(w * math.sin(math.radians(a)) for a, w, _ in self.ROWS)
        j = sum((w + ww) * math.tan(math.radians(a))
                for a, w, ww in self.ROWS)
        return b, j

    def test_the_fixture_really_disagrees(self):
        """Guard on the guard.

        Without this the cases below could pass on a fixture where the
        two sums agree, asserting nothing. That is how
        ``test_the_sign_of_the_margin_is_the_verdict`` passed in a vacuum
        in v0.1.185.
        """
        b, j = self._sums()
        assert _sgn(b) == 1.0, b
        assert _sgn(j) == -1.0, j
        assert _sgn(b) != _sgn(j)

    def test_the_wrong_sign_reports_negative_resistance(self):
        b, j = self._sums()
        a = math.radians(self.ROWS[0][0])
        guess = _m_alpha(a, self.TAN_PHI, self.F, _sgn(b))
        truth = _m_alpha(a, self.TAN_PHI, self.F, _sgn(j))
        assert guess < 0.0, guess          # worse than small: negative
        assert truth > 0.2, truth

    def test_and_that_flips_the_verdict(self):
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        b, j = self._sums()
        a = math.radians(self.ROWS[0][0])
        guess = _m_alpha(a, self.TAN_PHI, self.F, _sgn(b))
        truth = _m_alpha(a, self.TAN_PHI, self.F, _sgn(j))
        assert guess < M_ALPHA_LIMIT <= truth, (guess, truth)

    def test_the_null_control_is_phi_zero(self):
        """The arm that separates "the sign matters" from "the water
        matters": with no friction the two signs give the same number,
        exactly, whatever the sums say."""
        a = math.radians(self.ROWS[0][0])
        assert (_m_alpha(a, 0.0, self.F, 1.0)
                == _m_alpha(a, 0.0, self.F, -1.0))


# ======================================================================
class TestWhatCannotDiffer:
    """The algebra that bounds the defect's reach."""

    def test_a_non_negative_factor_cannot_invert_a_sum(self):
        """``(1-kv)`` scales Bishop's sum and never flips it."""
        res = _solve("bishop_simplified")
        base = _sgn(_bishop_sum(res.slices, kv=0.0))
        for kv in (-1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 0.9, 0.999):
            assert _sgn(_bishop_sum(res.slices, kv=kv)) == base, kv

    def test_only_kv_exactly_one_degenerates(self):
        res = _solve("bishop_simplified")
        assert abs(_bishop_sum(res.slices, kv=1.0)) < 1e-9

    def test_janbus_denominator_is_bishops_times_cos(self):
        """``n_alpha == cos(a) * m_alpha``, exactly.

        This is why Janbu's SIGN is readable inside Bishop's form at all:
        ``cos a > 0`` on any real base, so the two forms never differ in
        sign — only in size. It is also written down at
        ``interslice.py``, and recomputed here from the two expressions
        rather than imported from either.
        """
        for a_deg in (-78.0, -43.7, -20.0, 0.0, 15.0, 55.0, 78.0):
            for tan_phi in (0.0, 0.3, 0.7, 1.2):
                for F in (0.5, 1.0, 1.7, 3.0):
                    for s in (1.0, -1.0):
                        a = math.radians(a_deg)
                        n = _n_alpha(a, tan_phi, F, s)
                        m = _m_alpha(a, tan_phi, F, s)
                        assert abs(n - math.cos(a) * m) < 1e-15, (
                            a_deg, tan_phi, F, s)

    def test_the_sign_is_inert_without_friction(self):
        """``m(+1) - m(-1) = 2*sin(a)*tan(phi)/F`` is zero at phi = 0.

        So D112 cannot move a purely cohesive model, however badly the
        two sums disagree there.
        """
        for a_deg in (-70.0, -30.0, 0.0, 45.0):
            a = math.radians(a_deg)
            assert (_m_alpha(a, 0.0, 1.3, 1.0)
                    == _m_alpha(a, 0.0, 1.3, -1.0))


# ======================================================================
class TestThePrescribedFamilySignTrap:
    """Why that family gets no ``m_alpha_sign``, and why the obvious
    answer would have been false.

    With ``alpha_n = orient*a`` and ``theta_n = orient*t``, the
    denominator ``_march`` forms is, back in the true frame,

        D = cos(a - t) - orient*(tan phi/F)*sin(a - t)

    because this family writes a MINUS where Bishop writes a plus. So the
    friction term carries ``-orient`` and not ``+orient``, and
    ``cos a + s*sin a*tan phi/F`` is not a quantity the family forms for
    ANY ``s``.
    """

    def test_the_denominator_carries_minus_orient(self):
        for a_deg in (-40.0, -5.0, 12.0, 55.0):
            for t_deg in (0.0, 2.7, 18.4):
                for orient in (1.0, -1.0):
                    for aF in (0.0, 0.35, 0.9):
                        a, t = math.radians(a_deg), math.radians(t_deg)
                        an, tn = orient * a, orient * t
                        # exactly the expression in ``_march``
                        got = math.cos(an - tn) - aF * math.sin(an - tn)
                        want = (math.cos(a - t)
                                - orient * aF * math.sin(a - t))
                        assert abs(got - want) < 1e-15, (a_deg, t_deg,
                                                         orient, aF)

    def test_at_theta_zero_it_is_bishops_form_with_minus_orient(self):
        """Which is what makes ``slide_sign`` the wrong thing to write:
        the family's sign enters as ``-orient``, and ``orient`` is not
        ``slide_sign`` — the recursion picks whichever mirror solves."""
        for a_deg in (-40.0, 12.0, 55.0):
            for orient in (1.0, -1.0):
                a = math.radians(a_deg)
                aF = 0.35
                got = math.cos(orient * a) - aF * math.sin(orient * a)
                assert abs(got - _m_alpha(a, aF, 1.0, -orient)) < 1e-15, (
                    a_deg, orient)


# ======================================================================
class TestTheFallbackIsNecessityNotCourtesy:
    """A result with no ``details`` must behave exactly as before."""

    def test_a_result_without_the_key_uses_the_inherited_sum(self):
        from ogr_slip2d.checks import base_m_alphas
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _solve("bishop_simplified")
        det = dict(res.details or {})
        try:
            res.details = {}
            got = base_m_alphas(res)
        finally:
            res.details = det
        sgn = _sgn(sum(s.weight * math.sin(s.base_angle)
                       for s in res.slices))
        from ogr_slip2d.external_forces import slice_forces
        for s, g in zip(res.slices, got):
            l = max(s.base_length, 1e-12)
            w = slice_forces(s).w_total
            sig = max(0.0, w * math.cos(s.base_angle)
                      - s.pore_pressure * l) / l
            _c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sig)
            assert abs(g - _m_alpha(s.base_angle, tan_phi, res.fos,
                                    sgn)) < 1e-12, s.index

    def test_a_declared_sign_of_zero_is_not_trusted(self):
        """Zero is not a sign. It falls back rather than becoming +1 by
        ``copysign``, which would be a silent answer."""
        from ogr_slip2d.checks import base_m_alphas
        res = _solve("bishop_simplified")
        det = dict(res.details or {})
        try:
            res.details = {}
            plain = base_m_alphas(res)
            res.details = dict(m_alpha_sign=0.0)
            zero = base_m_alphas(res)
        finally:
            res.details = det
        assert plain == zero
