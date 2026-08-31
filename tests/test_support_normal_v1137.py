# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A support is a LINE LOAD on the slice it crosses, so the friction its
normal component mobilises is whatever that slice's own equilibrium
yields — never a term added outside ``m_α``.

WHAT INVARIANT THIS PROTECTS

``m_α`` is not a normalisation with a free outside. It is what is left of
solving a slice's VERTICAL equilibrium for N (Bishop 1955):

    N·cos α + S·sin α = W + P      →      N = (W + P − …) / m_α

so ANY external force P on that slice reaches the base divided by ``m_α``,
exactly as the weight does. From v0.1.64 to v0.1.136 Bishop instead
credited the base ``T_N·tan φ'`` whole, outside ``m_α``. The two agree only
as α → 0 — the file that carried the term called the difference
"second-order for the usual near-horizontal bases" for seventy-two
versions — and the ratio ``cos α / m_α`` that separates them is 0.71 on the
fixture below, at a base of 51°.

What settles the modelling question is not the two equations everyone
quotes from the reference. Those are written in the words *resisting force*
and *driving force*: they are GLOBAL, and they say nothing about where
``m_α`` goes. What does say it is the reference's page on WHERE a support
force is applied — at the point where it cuts the surface, to the base of a
single slice, and there "the applied force is simply a line load".

WHY ORDINARY IS RIGHT TO KEEP THE TERM RAW, AND IS THE CONTROL

Fellenius does not resolve the slice vertically; it resolves PERPENDICULAR
TO THE BASE, where ``N = W·cos α + T_N`` is exact and there is no ``m_α``
to divide by. The same physical statement therefore gives the two methods
different arithmetic, and this file asserts BOTH forms on the SAME fixture:
if someone ever "unifies" them, one of the two tests fails.

THE ANCHORS BEHIND THE CHANGE, WHICH LIVE ELSEWHERE

* An IDENTITY. The same force, at the same point, must give the same
  factor of safety whether it reaches the solver as a support or as a
  distributed load — that is the definition of a free body, not a
  convention. ``test_efp_wall_v1122`` measures it: Bishop used to fail it
  by −0.276 % AT EVERY SLICE COUNT, the signature of a formulation error
  rather than of discretisation, and now falls to −0.010 / +0.0016 /
  +0.0006 % at 25 / 100 / 400 slices.

* PUBLISHED VALUES, on surfaces the manual gives with centre, radius and
  both daylight points: the tiered geosynthetic walls of Leshchinsky and
  Han (2004), verification problems 87, 92 and 94, whose figures publish
  the critical surface of BISHOP with reinforcement crossing it and bases
  running 37° to 73°.

      problem 87      Bishop  +35.7 %  →  −0.7 %       published 1.040
      problem 94      Bishop  +35.4 %  →  −0.6 %       published 1.040

  The sharpest signal was already in the baseline and needed no change to
  see: on those circles, with the identical support force, Fellenius sat
  at +1.4 % while Bishop sat at +35 %. Only one of the two normalises by
  ``m_α``, and it was the one that was wrong.

WHAT THIS FILE DOES NOT CLAIM

Nothing about the two Janbu. They still add the term raw, and for them
that is an open, measured defect with both of its branches written down at
the term in ``ogr_slip2d/methods/janbu.py`` — not this derivation.
"""
from __future__ import annotations

import math

H = 12.0
TOE = 30.0
CREST = 37.0          # slope face (30, 0) → (37, 12), about 60°
PHI = 32.0
COH = 5.0
#: Chosen so the reinforcement cuts the surface at a base of 51°, where
#: ``cos α / m_α`` is 0.71 — the raw and the normalised forms are then
#: unmistakably different numbers rather than a rounding apart.
NSLICES = 50


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=34.0, centre_y=20.0, radius=15.0)


def _project(support=None, capacity=60.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import SoilNail

    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("normal-term")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    if support is not None:
        p.support_types = [SoilNail(tensile_capacity=capacity,
                                    plate_capacity=0.75 * capacity,
                                    bond_strength=0.2 * capacity,
                                    out_of_plane_spacing=2.0)]
        p.supports = [support]
    return p


def _nail(angle_deg, active=True):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="soil_nail",
        head=Vertex(36.5, 10.5), tail=Vertex(52.0, 10.5),
        force_application=(ForceApplication.ACTIVE if active
                           else ForceApplication.PASSIVE),
        orientation=ForceOrientation.USER_DEFINED,
        user_angle_deg=angle_deg)


def _slices(p):
    from ogr_slip2d.slicer import slice_surface
    return slice_surface(p, _circle(), num_slices=NSLICES)


def _terms(p, sl):
    from ogr_slip2d.support_integration import resolve_support_terms
    return resolve_support_terms(p, _circle(), sl, 1.0)


def _fos(cls, p, sl=None):
    return cls().compute_fos(p, _circle(), sl if sl is not None
                             else _slices(p))


def _purely_normal_angle():
    """The force direction that presses the crossed slice onto its base.

    Derived from that slice's own geometry, so ``T_S`` is zero BY
    CONSTRUCTION and only the normal component is under test. The tests
    below assert it really is zero rather than trusting the derivation.
    """
    p = _project(_nail(0.0))
    sl = _slices(p)
    sup = _terms(p, sl)
    i = next(k for k, v in enumerate(sup.n_press) if v or sup.t_active[k])
    a = sl.slices[i].base_angle
    # Inward base normal n = (−sin α, cos α); pressing means −n.
    return math.degrees(math.atan2(-math.cos(a), math.sin(a))), a


# ======================================================================
class TestTheNormalTermIsInsideMAlpha:
    """Bishop's converged equation, rebuilt term by term from the slices.

    Not a captured factor of safety: the two candidate numerators are
    written out at the factor of safety the solver reached, and only one
    of them closes the equation. That is what makes this an anchor rather
    than a snapshot — it would still discriminate if every number in the
    fixture changed.
    """

    def _converged(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        ang, a = _purely_normal_angle()
        p = _project(_nail(ang))
        sl = _slices(p)
        sup = _terms(p, sl)
        res = _fos(BishopSimplified, p, sl)
        assert res.converged, res.error_message
        return p, sl, sup, res.fos, a

    def _rebuild(self, sl, sup, fos, inside):
        """Bishop's numerator over its denominator, at ``fos``.

        ``inside`` picks which of the two formulations to write: the
        support's vertical load inside ``m_α`` with the rest of the slice,
        or ``T_N·tan φ'`` added outside it.
        """
        from ogr_slip2d.methods.bishop import BishopSimplified
        tan_phi = math.tan(math.radians(PHI))
        num = 0.0
        for k, s in enumerate(sl.slices):
            m_alpha = (math.cos(s.base_angle)
                       + math.sin(s.base_angle) * tan_phi / fos)
            c, t = BishopSimplified._local_c_phi(s, s.material, 0.0)
            extra = (sup.n_press[k] * math.cos(s.base_angle) if inside
                     else 0.0)
            num += (c * s.width
                    + (s.weight + extra - s.pore_pressure * s.width) * t
                    ) / m_alpha
            if not inside:
                num += sup.n_press[k] * tan_phi
        den = (math.fsum(s.weight * s.weight_arm_ratio for s in sl.slices)
               - sup.total_active_t())
        return num / den

    def test_the_fixture_really_is_a_pure_normal_on_a_steep_base(self):
        """Guards the discrimination itself. If the tangential part stopped
        being zero, or the base flattened, the two forms below would
        converge and the file would pass without testing anything."""
        _p, _sl, sup, fos, a = self._converged()
        assert abs(sup.total_active_t()) < 1e-9, sup.total_active_t()
        assert abs(sum(sup.n_press)) > 1.0, sup.n_press
        assert math.degrees(a) > 45.0, math.degrees(a)
        tan_phi = math.tan(math.radians(PHI))
        ratio = math.cos(a) / (math.cos(a) + math.sin(a) * tan_phi / fos)
        assert ratio < 0.8, ratio

    def test_bishop_closes_its_equation_with_the_m_alpha_form(self):
        _p, sl, sup, fos, _a = self._converged()
        got = self._rebuild(sl, sup, fos, inside=True)
        assert abs(got - fos) / fos < 1e-3, (got, fos)

    def test_and_does_not_close_it_with_the_raw_form(self):
        """The discrimination, stated as a ratio so it does not depend on
        how tightly the solver was asked to converge."""
        _p, sl, sup, fos, _a = self._converged()
        inside = abs(self._rebuild(sl, sup, fos, inside=True) - fos)
        raw = abs(self._rebuild(sl, sup, fos, inside=False) - fos)
        assert raw > 50.0 * inside, (raw, inside)

    def test_ordinary_closes_ITS_equation_with_the_raw_form(self):
        """The control, on the same fixture and the same support.

        Fellenius resolves perpendicular to the base, so ``N = W·cos α +
        T_N`` and the gain is exactly ``T_N·tan φ'`` over ΣR — no ``m_α``
        anywhere. Asserting both forms in one file is the point: they are
        different methods, not an inconsistency to be tidied away.
        """
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        ang, _a = _purely_normal_angle()
        p = _project(_nail(ang))
        sl = _slices(p)
        sup = _terms(p, sl)
        bare = _fos(OrdinaryFellenius, _project())
        got = _fos(OrdinaryFellenius, p, sl).fos
        tan_phi = math.tan(math.radians(PHI))
        expected = bare.fos * (1.0 + sum(sup.n_press) * tan_phi
                               / sum(bare.base_shear_strength))
        assert abs(got - expected) / expected < 1e-6, (got, expected)


# ======================================================================
class TestBishopNoLongerFliesApartFromTheRigorousMethods:
    """The shape of verification problems 87 to 94, reduced to a fixture.

    Bishop and Spencer agree closely on this slope with no reinforcement.
    Before v0.1.137 they still agreed bare and separated by 14 % to 40 %
    as soon as a support crossed a steep base, while the manual publishes
    its own Bishop and Spencer within 0.5 % of each other on four of the
    eight. That divergence is what the normal term was doing.
    """

    #: Deliberately a PURELY NORMAL support, at four capacities. Any
    #: support with a tangential part also shrinks the Active denominator
    #: ``D − T_S``, and past some capacity that alone separates the two
    #: methods — which would make this class pass for the wrong reason.
    #: With ``T_S = 0`` the only thing left that can separate them is the
    #: normal term, so the trend across the four IS the measurement.
    CAPACITIES = (60.0, 200.0, 400.0, 800.0)

    def _gap(self, capacity, active=True):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.spencer import Spencer
        ang, _a = _purely_normal_angle()
        p = _project(_nail(ang, active=active), capacity=capacity)
        sl = _slices(p)
        b = _fos(BishopSimplified, p, sl).fos
        s = _fos(Spencer, p, sl).fos
        return 100.0 * (b - s) / s

    def test_bare_they_agree(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.spencer import Spencer
        p = _project()
        sl = _slices(p)
        b = _fos(BishopSimplified, p, sl).fos
        s = _fos(Spencer, p, sl).fos
        assert abs(b - s) / s < 0.02, (b, s)

    def test_reinforcement_does_not_pull_them_apart(self):
        gaps = [self._gap(c) for c in self.CAPACITIES]
        assert all(abs(g) < 2.0 for g in gaps), gaps

    def test_the_gap_does_not_grow_with_the_support_force(self):
        """The signature of the defect, and the reason four capacities and
        not one. Charging the base ``T_N·tan φ'`` instead of
        ``T_N·cos α·tan φ'/m_α`` overpays by a FIXED FRACTION of the force,
        so the disagreement scaled with it: +0.99, +2.67, +4.62, +5.30 %
        across these four before v0.1.137. A single capacity could be
        explained away as a tolerance; a trend cannot.
        """
        gaps = [self._gap(c) for c in self.CAPACITIES]
        assert abs(gaps[-1]) < 4.0 * abs(gaps[0]) + 1.5, gaps
        assert max(gaps) - min(gaps) < 2.5, gaps

    def test_the_same_holds_for_a_passive_support(self):
        gaps = [self._gap(c, active=False) for c in self.CAPACITIES]
        assert all(abs(g) < 2.0 for g in gaps), gaps


# ======================================================================
class TestTheTermIsStillAlive:
    """Guards against the other way to make those numbers agree — dropping
    the normal term altogether, which was measured in D44 and is NOT what
    this version did."""

    def test_pressing_raises_the_factor_and_lifting_lowers_it(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        ang, _a = _purely_normal_angle()
        bare = _fos(BishopSimplified, _project()).fos
        press = _fos(BishopSimplified, _project(_nail(ang))).fos
        lift = _fos(BishopSimplified, _project(_nail(ang + 180.0))).fos
        assert press > bare, (bare, press)
        assert lift < bare, (bare, lift)

    def test_the_gain_is_not_rounding(self):
        """If the normal term had simply been deleted, a purely normal
        support would change Bishop by nothing at all."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        ang, _a = _purely_normal_angle()
        bare = _fos(BishopSimplified, _project()).fos
        press = _fos(BishopSimplified, _project(_nail(ang))).fos
        assert (press - bare) / bare > 0.01, (bare, press)
