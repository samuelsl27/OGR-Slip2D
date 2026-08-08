# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Conversion between the R envelope and the Kc = 1 envelope.

The multi-stage rapid-drawdown procedures need different views of the
same IC-U triaxial data: the Corps of Engineers two-stage method wants the
total-stress R envelope, while Lowe-Karafiath and Duncan-Wright-Wong want
the Kc = 1 envelope. Since both are plots of the SAME tests, the
conversion is exact, and a program that accepts either has to be able to
produce the other.

This file is the one that unblocked the whole phase. The equations were
not available in the reference material in an extractable form, so they
were derived from the tangency condition of the total-stress Mohr circle
(the derivation is in the module docstring of
``ogr_core.materials.drawdown_envelopes``) and then checked against **two
independent published cases**, which is what makes them usable here rather
than plausible:

* **Case A** — the Pilarcitos dam exercise: c_R = 60 lb/ft², φ_R = 23°,
  φ' = 45°, published as d = 64 lb/ft², ψ = 24.4°.
* **Case B** — Basso, López and Carrizo (2024), XVII PCSMGE, table 5:
  c_R = 15 kPa, φ_R = 14°, φ' = 28°, published as d = 17 kPa, ψ = 15.7°.

Both published pairs are rounded to two or three figures, so the
tolerances below are the rounding of the source, not a fudge factor.

The φ' trap
-----------
One tutorial calls φ' "the undrained friction angle". It is not: it is the
EFFECTIVE friction angle from the drained envelope of the same tests. Both
cases above are reproduced with φ' (45° and 28°) and neither is reproduced
with φ_R, so the test suite pins that down explicitly — a wrong angle here
would give an envelope that is off by tens of percent while still looking
like a perfectly ordinary strength.
"""
from __future__ import annotations

import math


def _env():
    from ogr_core.materials.drawdown_envelopes import (
        Kc1Envelope, REnvelope, composite_strength,
    )
    return REnvelope, Kc1Envelope, composite_strength


# ======================================================================
class TestPublishedCases:
    """Rule 1: the numbers come from outside this codebase."""

    def test_case_a_pilarcitos(self):
        REnvelope, _K, _c = _env()
        k = REnvelope(c_r=60.0, phi_r_deg=23.0).to_kc1(phi_eff_deg=45.0)
        # Published: d = 64 lb/ft², ψ = 24.4°.
        assert abs(k.d - 64.0) < 0.5, k.d
        assert abs(k.psi_deg - 24.4) < 0.05, k.psi_deg

    def test_case_b_basso_lopez_carrizo_2024(self):
        REnvelope, _K, _c = _env()
        k = REnvelope(c_r=15.0, phi_r_deg=14.0).to_kc1(phi_eff_deg=28.0)
        # Published: d = 17 kPa, ψ = 15.7°.
        assert abs(k.d - 17.0) < 0.1, k.d
        assert abs(k.psi_deg - 15.7) < 0.05, k.psi_deg

    def test_the_effective_angle_is_the_one_that_reproduces_them(self):
        """Using φ_R instead of φ' misses both published cases badly.

        The point of this test is not the wrong number: it is that the
        wrong number is a plausible-looking envelope, so nothing else in
        the program would flag it.
        """
        REnvelope, _K, _c = _env()
        wrong = REnvelope(c_r=60.0, phi_r_deg=23.0).to_kc1(phi_eff_deg=23.0)
        assert abs(wrong.d - 64.0) > 5.0, wrong.d


class TestTheConversionIsExactlyInvertible:
    """Two views of one data set: nothing may be lost going round."""

    CASES = [
        (60.0, 23.0, 45.0),
        (15.0, 14.0, 28.0),
        (2000.0, 18.0, 36.0),   # pumped-storage dam core, DWW (1990)
        (1200.0, 16.0, 30.0),   # USACE benchmark, EM 1110-2-1902 app. G
        (0.0, 25.0, 35.0),      # no cohesion intercept
    ]

    def test_round_trip_to_machine_precision(self):
        REnvelope, _K, _c = _env()
        for c_r, phi_r, phi_e in self.CASES:
            a = REnvelope(c_r=c_r, phi_r_deg=phi_r)
            b = a.to_kc1(phi_e).to_r(phi_e)
            assert abs(b.c_r - c_r) < 1e-9 * max(1.0, abs(c_r)), (c_r, b.c_r)
            assert abs(b.phi_r_deg - phi_r) < 1e-9, (phi_r, b.phi_r_deg)

    def test_round_trip_the_other_way_round(self):
        _R, Kc1Envelope, _c = _env()
        for d, psi, phi_e in [(64.0, 24.4, 45.0), (17.0, 15.7, 28.0)]:
            a = Kc1Envelope(d=d, psi_deg=psi)
            b = a.to_r(phi_e).to_kc1(phi_e)
            assert abs(b.d - d) < 1e-9 * max(1.0, d)
            assert abs(b.psi_deg - psi) < 1e-9


class TestClosedFormProperties:
    """Identities that follow from the derivation, so they hold for any
    input rather than for a captured case."""

    def test_zero_intercept_stays_zero(self):
        """d is proportional to c_R, so c_R = 0 gives d = 0 exactly, and
        the slope is untouched by the intercept."""
        REnvelope, _K, _c = _env()
        k0 = REnvelope(c_r=0.0, phi_r_deg=20.0).to_kc1(30.0)
        k1 = REnvelope(c_r=100.0, phi_r_deg=20.0).to_kc1(30.0)
        assert k0.d == 0.0
        assert abs(k0.psi_deg - k1.psi_deg) < 1e-12

    def test_d_is_linear_in_c_r(self):
        REnvelope, _K, _c = _env()
        a = REnvelope(c_r=10.0, phi_r_deg=20.0).to_kc1(30.0).d
        b = REnvelope(c_r=30.0, phi_r_deg=20.0).to_kc1(30.0).d
        assert abs(b - 3.0 * a) < 1e-12

    def test_a_horizontal_r_envelope_stays_horizontal(self):
        """φ_R = 0 is the φ = 0 undrained case: ψ must come out 0 and the
        intercept must be scaled by cos φ' alone."""
        REnvelope, _K, _c = _env()
        k = REnvelope(c_r=50.0, phi_r_deg=0.0).to_kc1(30.0)
        assert abs(k.psi_deg) < 1e-12
        assert abs(k.d - 50.0 * math.cos(math.radians(30.0))) < 1e-12

    def test_a_vertical_r_envelope_is_refused(self):
        REnvelope, _K, _c = _env()
        try:
            REnvelope(c_r=10.0, phi_r_deg=90.0).to_kc1(30.0)
        except ValueError:
            return
        assert False, "phi_R = 90 deg should be refused, not returned"


class TestTheEnvelopeSurvivesASave:
    """It is a new Material field, and the lesson of v0.1.62 was that a
    field nothing serialises is a field that silently disappears."""

    def _material(self, env):
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="Core",
                     strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0))
        m.undrained_behaviour = True
        m.drawdown_envelope = env
        return m

    def test_r_envelope_round_trip(self):
        from ogr_core.materials import Material
        REnvelope, _K, _c = _env()
        m = self._material(REnvelope(c_r=60.0, phi_r_deg=23.0))
        back = Material.from_dict(m.to_dict())
        assert isinstance(back.drawdown_envelope, REnvelope)
        assert back.drawdown_envelope.c_r == 60.0
        assert back.drawdown_envelope.phi_r_deg == 23.0

    def test_kc1_envelope_round_trip(self):
        from ogr_core.materials import Material
        _R, Kc1Envelope, _c = _env()
        m = self._material(Kc1Envelope(d=64.0, psi_deg=24.4))
        back = Material.from_dict(m.to_dict())
        assert isinstance(back.drawdown_envelope, Kc1Envelope)
        assert back.drawdown_envelope.d == 64.0
        assert back.drawdown_envelope.psi_deg == 24.4

    def test_no_envelope_stays_none(self):
        from ogr_core.materials import Material
        m = self._material(None)
        assert Material.from_dict(m.to_dict()).drawdown_envelope is None


class TestCompositeEnvelope:
    """Corps of Engineers (1970): the lower of R and effective."""

    def test_it_is_the_minimum_of_the_two(self):
        REnvelope, _K, composite = _env()
        r = REnvelope(c_r=60.0, phi_r_deg=23.0)
        for sigma in (0.0, 50.0, 104.0, 500.0, 5000.0):
            got = composite(sigma, r, c_eff=0.0, phi_eff_deg=45.0)
            drained = sigma * math.tan(math.radians(45.0))
            assert abs(got - min(r.strength_at(sigma), drained)) < 1e-12
            assert got <= r.strength_at(sigma) + 1e-12
            assert got <= drained + 1e-12

    def test_the_crossover_is_where_the_lines_meet(self):
        """Pilarcitos: 60 + σ·tan23° = σ·tan45° gives σ ≈ 104 psf. Below
        it the effective line governs and, with c' = 0, the strength near
        the toe is very small — which is why this method reports ≈ 0.82
        where the other two report ≈ 1.05."""
        REnvelope, _K, composite = _env()
        r = REnvelope(c_r=60.0, phi_r_deg=23.0)
        sigma_i = 60.0 / (math.tan(math.radians(45.0))
                          - math.tan(math.radians(23.0)))
        assert 100.0 < sigma_i < 110.0, sigma_i
        below = sigma_i - 10.0
        above = sigma_i + 10.0
        assert (composite(below, r, 0.0, 45.0)
                < r.strength_at(below) - 1e-9)
        assert (composite(above, r, 0.0, 45.0)
                < above * math.tan(math.radians(45.0)) - 1e-9)
