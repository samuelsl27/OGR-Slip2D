# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.357 — the shear strength of the two Hoek-Brown models IS the Mohr
envelope of their criterion (defect D171 of the verification bank).

THE DEFECT. Both models computed

    h = 1 + a·mb·(mb·σn/σci + s)^(a−1),   τ = σn·(h − 1)·√h/(h + 1)

which is the parametric form of Balmer (1952) with σ3 replaced by σn and
σ1 − σ3 by σn·(h − 1). That is not the envelope: it gives τ(0) = 0 where the
criterion has 307.5 kPa with the default constants, and at σn = 145 kPa it
puts the strength INSIDE the uniaxial-compression circle of the rock mass
itself. On Hoek's (1990) worked example it gave 541.2 kPa for the published
661.0; on the slope of Hammah et al. (2005), Bishop 0.788 for the published
1.153.

THE DECISION. The envelope is evaluated exactly: for a given σ'n the σ'3 of
its tangent failure circle is solved in the parametric form of Balmer
(1952) as corrected by Hoek, Carranza-Torres & Corkum (2002, eqs. 8–10), and
the slope of the envelope there is tan φi = (k − 1)/(2·√k), k = dσ'1/dσ'3
(Hoek 1990, eq. 11 for a = 0.5). The envelope ends at the biaxial tensile
strength σt = −s·σci/mb (Hoek et al. 2002, eq. 7), the tension v0.1.191
(D165) already gave the Tensile Stress Check, with τ = 0.

THE REFERENCES (rule 1):

* an IDENTITY of the criterion, exact by construction: the points of the
  parametric form are generated FROM σ'3 here, with no inversion, and the
  model has to return their τ at their σ'n;
* Hoek (1990), Int. J. Rock Mech. Min. Sci. 27(3), p. 229 — a PUBLISHED
  worked example of the classic criterion (σc 60 MPa, m 0.238, s 0.000063:
  τ 0.6610 MPa, φi 41.896° and ci 0.2124 MPa at σ'n 0.5 MPa) and its closed
  form for a = 0.5 (eqs. 9–12, Bray's solution reported in Hoek 1983), an
  independent formula;
* Hammah, Yacoub, Corkum & Curran (2005), ARMA/USRMS 05-810, Table 2 — a
  PUBLISHED limit-equilibrium factor of safety with a Generalized Hoek-Brown
  rock mass: Bishop 1.153, Spencer 1.152 on a 10 m slope at 45°.

The tangent cannot be checked through a factor of safety: at the fixed
point of ``ENVELOPE_AT_OWN_STRESS`` (D84) the factor depends on τ alone, so
a tangent missing the design divisor moved F by 3e-10 (measured on v0.1.356
with a prototype). It is checked here at the level of the model.

DISCRIMINATION, measured by copying this file into a ``git archive`` of
v0.1.356 and running that tree's runner without the editable finder: 12 of
the 15 cases fail there (Hammah's Bishop 0.808 on the archived circle;
Hoek's τ 541.2; the closed form; both Balmer identities; the tensile end,
where v0.1.356 returned τ(1e-6) > 0; the uniaxial circle; s = 0; the four
of the refusal). The three that pass there are guards that only this code
could break: the design divisor of the tangent (the old tangent was a
difference over ``shear_strength``, so it followed by construction), no
refusal inside the domain, and the tangent being the derivative.
"""
from __future__ import annotations

import math

# Hammah et al. (2005), Example 1 (Table 1 and Fig. 3): the critical circles
# found by a grid and a multi-start local search on this version
# (`_auditoria/P7_0357/hammah_ej1.json` of the verification bank).
HAMMAH_BISHOP_CIRCLE = (13.582360896582735, 22.711356502870487, 14.711356502863769)
HAMMAH_SPENCER_CIRCLE = (13.688278080221208, 22.430063606253725, 14.430063606252524)


def _ghb(**kw):
    from ogr_core.materials import GeneralizedHoekBrown
    return GeneralizedHoekBrown(**kw)


def _hbc(**kw):
    from ogr_core.materials import HoekBrown
    return HoekBrown(**kw)


def _balmer_from_x(x, sigci, mb, s, a):
    """(σ'n, τ, k) of the tangency point of the failure circle at
    x = mb·σ'3/σci + s: Hoek, Carranza-Torres & Corkum (2002), eqs. 8-10,
    forward, with no inversion. σ'3 is formed from x so that the offset from
    the tensile end is not lost to cancellation."""
    s3 = (x - s) * sigci / mb
    k = 1.0 + a * mb * x ** (a - 1.0)
    d = sigci * x ** a
    return s3 + d / (k + 1.0), d * math.sqrt(k) / (k + 1.0), k


def _hoek1990(sn, sc, m, s):
    """Closed form of the envelope for a = 0.5, Hoek (1990), eqs. 9-12:
    (τ, φi in degrees)."""
    h = 1.0 + 16.0 * (m * sn + s * sc) / (3.0 * m * m * sc)
    th = math.radians((90.0 + math.degrees(math.atan(1.0 / math.sqrt(h ** 3 - 1.0)))) / 3.0)
    phi = math.atan(1.0 / math.sqrt(4.0 * h * math.cos(th) ** 2 - 1.0))
    return (1.0 / math.tan(phi) - math.cos(phi)) * m * sc / 8.0, math.degrees(phi)


_SETS = ((50000.0, 2.5, 0.004), (30000.0, 0.067, 2.5e-5), (2000.0, 1.2, 5e-4))


class TestTheEnvelopeIsTheCriterions:

    def _points(self, sigci, mb, s, a):
        # from 1e-3 of the way above the tensile end to ten times σci; nearer
        # σt the σ'n of the input itself cannot hold the offset
        for e in range(-60, 41):
            x = s * 10 ** (e / 20.0)
            yield _balmer_from_x(x, sigci, mb, s, a)

    def test_generalized_reproduces_balmer(self):
        for a in (0.5, 0.6, 0.619):
            for sigci, mb, s in _SETS:
                m = _ghb(sigci=sigci, mb=mb, s=s, a=a)
                for sn, tau, k in self._points(sigci, mb, s, a):
                    assert math.isclose(m.shear_strength(sn), tau, rel_tol=1e-9), (a, sigci, sn)
                    if sn >= 0.0:
                        slope = (k - 1.0) / (2.0 * math.sqrt(k))
                        assert math.isclose(m.tangent_slope(sn), slope, rel_tol=1e-9), (a, sn)

    def test_classic_reproduces_balmer_at_half(self):
        for sigci, m_, s in _SETS:
            m = _hbc(sigci=sigci, m=m_, s=s)
            for sn, tau, _k in self._points(sigci, m_, s, 0.5):
                assert math.isclose(m.shear_strength(sn), tau, rel_tol=1e-9), (sigci, sn)

    def test_tangent_is_the_derivative(self):
        m = _ghb(sigci=30000.0, mb=0.067, s=2.5e-5, a=0.619)
        for sn in (0.0, 1.0, 30.0, 120.0, 900.0, 20000.0):
            d = max(1e-3, 1e-6 * sn)
            secant = (m.shear_strength(sn + d) - m.shear_strength(max(sn - d, 0.0))) / (sn + d - max(sn - d, 0.0))
            assert math.isclose(m.tangent_slope(sn), secant, rel_tol=1e-4), sn


class TestHoek1990:
    """The worked example of Hoek (1990), p. 229, and its closed form."""

    def test_the_published_example(self):
        m = _hbc(sigci=60000.0, m=0.238, s=0.000063)
        tau = m.shear_strength(500.0)
        phi = math.degrees(math.atan(m.tangent_slope(500.0)))
        assert abs(tau - 661.0) <= 0.05, tau
        # one unit of the last printed digit, not half: the paper carries
        # rounded intermediates (h 1.1927, θ 46.7174 where the exact is
        # 46.7173), and the exact φi, 41.89668, would round to 41.897
        assert abs(phi - 41.896) <= 0.001, phi
        assert abs(tau - 500.0 * math.tan(math.radians(phi)) - 212.4) <= 0.05
        # and the second example: σ'3 = 0.25 MPa gives σ'n 0.5940 and τ 0.7429
        assert abs(m.shear_strength(594.0) - 742.9) <= 0.1

    def test_the_closed_form_for_a_half(self):
        m = _hbc(sigci=60000.0, m=0.238, s=0.000063)
        g = _ghb(sigci=60000.0, mb=0.238, s=0.000063, a=0.5)
        for sn in (0.0, 10.0, 100.0, 500.0, 3000.0, 30000.0):
            tau, phi = _hoek1990(sn / 1000.0, 60.0, 0.238, 0.000063)
            assert math.isclose(m.shear_strength(sn), 1000.0 * tau, rel_tol=1e-9), sn
            assert math.isclose(g.shear_strength(sn), 1000.0 * tau, rel_tol=1e-9), sn
            assert math.isclose(m.tangent_slope(sn), math.tan(math.radians(phi)), rel_tol=1e-9), sn


class TestTheEndsOfTheEnvelope:

    def test_it_ends_at_the_tensile_strength(self):
        for m in (_ghb(), _ghb(sigci=30000.0, mb=0.067, s=2.5e-5, a=0.619), _hbc()):
            st = -m.tensile_strength()
            assert m.shear_strength(st) == 0.0
            assert m.shear_strength(st - 1.0) == 0.0
            assert m.shear_strength(st + 1e-3 * abs(st)) > 0.0

    def test_it_touches_the_uniaxial_compression_circle(self):
        sigci, mb, s, a = 50000.0, 2.5, 0.004, 0.5
        m = _ghb(sigci=sigci, mb=mb, s=s, a=a)
        sn0, tau0, _k = _balmer_from_x(s, sigci, mb, s, a)      # σ'3 = 0
        assert math.isclose(m.shear_strength(sn0), tau0, rel_tol=1e-9)
        # and no failure circle of the criterion rises above it
        for s3 in (-0.5 * s * sigci / mb, 0.0, 100.0, 1000.0, 10000.0):
            s1 = s3 + sigci * (mb * s3 / sigci + s) ** a
            c, r = 0.5 * (s1 + s3), 0.5 * (s1 - s3)
            for j in range(1, 200):
                sg = s3 + (s1 - s3) * j / 200.0
                assert math.sqrt(max(r * r - (sg - c) ** 2, 0.0)) <= m.shear_strength(sg) + 1e-9 * sigci

    def test_no_s_puts_the_end_at_zero_and_the_tangent_stays_finite(self):
        m = _ghb(sigci=50000.0, mb=2.5, s=0.0, a=0.5)
        assert m.shear_strength(0.0) == 0.0
        t = m.tangent_slope(0.0)
        assert math.isfinite(t) and t > 0.0


class TestTheDesignDivisor:

    def test_divides_the_strength_and_the_tangent(self):
        from ogr_core.materials.strength_model import MaterialFactors
        for m in (_ghb(sigci=30000.0, mb=0.067, s=2.5e-5, a=0.619), _hbc()):
            out = m.design_factored(MaterialFactors(cohesion=1.0, tan_phi=1.0, undrained=1.0, shear=1.3)).model
            for sn in (0.0, 50.0, 600.0):
                assert math.isclose(out.shear_strength(sn), m.shear_strength(sn) / 1.3, rel_tol=1e-12)
                assert math.isclose(out.tangent_slope(sn), m.tangent_slope(sn) / 1.3, rel_tol=1e-12)


class TestHammahExample1:
    """Hammah, Yacoub, Corkum & Curran (2005), Table 2: limit equilibrium on a
    homogeneous 10 m slope at 45° (their Table 1 and Fig. 3: toe and crest
    platforms of 15 m, an 8 m foundation, γ 25 kN/m³, σci 30 MPa, mb 0.067,
    s 2.5e-5, a 0.619), Bishop 1.153 and Spencer 1.152. The envelope of
    v0.1.356 gave 0.788 and 0.787 on the same slope."""

    def _project(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.project import Project
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(40, 0), Vertex(40, 18),
                                 Vertex(25, 18), Vertex(15, 8), Vertex(0, 8)], closed=True)
        ext.ensure_ccw()
        p = Project("Hammah et al. 2005, example 1")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        rock = Material(name="rock", unit_weight=25.0,
                        strength=_ghb(sigci=30000.0, mb=0.067, s=2.5e-5, a=0.619))
        p.materials = [rock]
        p.assign_material_at(*p.resolve_regions()[0].centroid(), rock.id)
        return p

    def _fos(self, p, circle, method_id):
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        c = SlipCircle(*circle)
        m = method_registry()[method_id]()
        m.tolerance = 1e-9
        res = m.compute_fos(p, c, slice_surface(p, c, num_slices=50))
        assert res.fos is not None, (method_id, res.reason)
        return res.fos

    def test_bishop_and_spencer_within_two_percent(self):
        p = self._project()
        for mid, circle, published in (("bishop_simplified", HAMMAH_BISHOP_CIRCLE, 1.153),
                                       ("spencer", HAMMAH_SPENCER_CIRCLE, 1.152)):
            f = self._fos(p, circle, mid)
            # measured on v0.1.357: -0.36 % and -0.21 %
            assert abs(f - published) <= 0.02 * published, (mid, f)

    def test_the_circles_are_local_minima(self):
        """The two circles came from a grid and a multi-start local search;
        a version that moved the minimum away from them would make the first
        test measure some other circle."""
        p = self._project()
        for mid, circle in (("bishop_simplified", HAMMAH_BISHOP_CIRCLE),
                            ("spencer", HAMMAH_SPENCER_CIRCLE)):
            f = self._fos(p, circle, mid)
            for i in range(3):
                for sign in (-1.0, 1.0):
                    v = list(circle)
                    v[i] += sign * 0.2
                    assert self._fos(p, tuple(v), mid) >= f - 1e-6, (mid, i, sign)


class TestTheDomainIsRefused:
    """The inversion has exactly one root only for σci > 0, mb > 0, s >= 0
    and 0 < a <= 1; until v0.1.357 any constants computed in silence."""

    def test_outside_it_a_coded_refusal(self):
        from ogr_core.project.rules import strength_model_refusal
        for kw in ({"a": 1.2}, {"a": 0.0}, {"mb": 0.0}, {"sigci": -1.0},
                   {"s": -0.1}, {"a": float("nan")}):
            why = strength_model_refusal(_ghb(**kw), "rock")
            assert why is not None and why.code == "hoek_brown_domain", kw
            assert why.message.args["why"]["code"] == "strength.hoek_brown.domain"
        why = strength_model_refusal(_hbc(m=0.0), "rock")
        assert why is not None and why.code == "hoek_brown_classic_domain"
        assert why.message.args["why"]["code"] == "strength.hoek_brown_classic.domain"

    def test_inside_it_nothing(self):
        from ogr_core.project.rules import strength_model_refusal
        for m in (_ghb(), _ghb(a=1.0), _ghb(s=0.0), _hbc(), _hbc(s=0.0)):
            assert strength_model_refusal(m, "rock") is None, m.params

    def test_the_analysis_refuses_the_material(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = TestHammahExample1()._project()
        assert not check_analysis_settings(p)
        p.materials[0].strength.params["a"] = 1.2
        problems = check_analysis_settings(p)
        assert any(getattr(m, "code", "") == "strength.material"
                   and m.args["why"]["code"] == "strength.hoek_brown.domain"
                   for m in problems), problems

    def test_it_says_it_in_spanish(self):
        from ogr_core.project.rules import strength_model_refusal
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            said = note_text(strength_model_refusal(_ghb(a=1.2), "rock").message)
        finally:
            set_language(before)
        assert "La envolvente necesita" in said and "a = 1.2" in said, said
