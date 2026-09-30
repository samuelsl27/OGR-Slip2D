# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.225 — Anisotropic Linear interpolates the TANGENT of the friction
angle, as the reference's equations write it (defect D216 of the
verification bank).

THE DEFECT. Between A and B the reference documentation defines, with
t = (|α| − A)/(B − A),

    c = c1(1 − t) + c2·t        tan φ = tan φ1(1 − t) + tan φ2·t

(its equation images ``eq_aniso_linear5`` and ``eq_aniso_linear9``, and the
text: "the cohesion and the tangent of the friction angle can be computed
for any plane orientation"). ``AnisotropicLinear._c_phi_for_angle``
interpolated the angle itself, ``phi1 + t·(phi2 − phi1)``. At the ends the
two agree; between them they do not: with φ1 = 15° and φ2 = 30°, at t = 0.5
the equations give tan φ = 0.42265, φ = 22.9113°, and OGR gave 22.5°.

THE REFERENCES (rule 1): the equations written by hand in the three zones,
with a negative angle and one folded past 90 degrees; and an identity -- on
a PLANAR surface every base has the same α, so the model must be exactly a
Mohr-Coulomb material with that α's (c, φ), in the nine methods.

What does NOT move: the two ends (t ≤ 0 and t ≥ 1), bit for bit; and the
verification bank, which has no Anisotropic Linear material. A project saved
before this version keeps its parameters, which mean what they meant; what
was wrong was the formula, so there is no migration to refuse.

THE RULE: 0 ≤ A ≤ B (``rules.anisotropic_linear_refusal``); the reference
calls A "an angular range on either side of the bedding plane orientation"
and B − A the width of the transition.

DISCRIMINATION, measured on the v0.1.224 tree: 5 of the 8 cases fail
there, all by behaviour: the transition-zone values, the 22.9113° case, the
planar identity (Bishop 2.71658 against 2.73128) and the two cases of the
rule. The ends, the step and the valid A and B pass.
"""
from __future__ import annotations

import math

P = dict(c1=5.0, phi1=15.0, c2=20.0, phi2=30.0, A=10.0, B=30.0)

H, TOE, SLOPE, BETA = 12.0, 30.0, 30.96, 25.0
CREST = TOE + H / math.tan(math.radians(SLOPE))
N_SLICES = 51


def _al(bedding=0.0, **over):
    from ogr_core.materials.builtin_models import AnisotropicLinear
    kw = dict(P, bedding_angle=bedding)
    kw.update(over)
    return AnisotropicLinear(**kw)


def _by_hand(alpha_deg, p=P, bedding=0.0):
    """(c, tan φ) from the reference's equations, written out."""
    delta = abs(alpha_deg - bedding) % 180.0
    if delta > 90.0:
        delta = 180.0 - delta
    t = (delta - p["A"]) / (p["B"] - p["A"])
    t = min(max(t, 0.0), 1.0)
    tan1 = math.tan(math.radians(p["phi1"]))
    tan2 = math.tan(math.radians(p["phi2"]))
    return (p["c1"] * (1.0 - t) + p["c2"] * t,
            tan1 * (1.0 - t) + tan2 * t)


def _tau(model, alpha_deg, sigma=80.0):
    from ogr_core.materials.strength_model import SliceContext
    return model.shear_strength_ctx(
        sigma, SliceContext(base_angle_rad=math.radians(alpha_deg)))


# ======================================================================
class TestTheEquations:

    def test_the_three_zones_by_hand(self):
        m = _al()
        for alpha in (0.0, 5.0, 10.0, 12.5, 15.0, 20.0, 25.0, 29.0, 30.0,
                      45.0, 90.0, -20.0, -27.0, 160.0, -170.0):
            c, tan_phi = _by_hand(alpha)
            assert math.isclose(_tau(m, alpha), c + 80.0 * tan_phi,
                                rel_tol=1e-13), alpha

    def test_the_midpoint_of_the_transition(self):
        """t = 0.5: the reference's 22.9113 degrees, not 22.5."""
        c, phi = _al()._c_phi_for_angle(20.0)
        want = math.degrees(math.atan(
            0.5 * (math.tan(math.radians(15.0))
                   + math.tan(math.radians(30.0)))))
        assert math.isclose(want, 22.9113369, abs_tol=5e-8), want
        assert math.isclose(phi, want, rel_tol=1e-12), phi
        assert math.isclose(c, 12.5, rel_tol=1e-12), c

    def test_the_ends_are_the_two_strengths_bit_for_bit(self):
        m = _al()
        bedding = 5.0 + 80.0 * math.tan(math.radians(15.0))
        rock = 20.0 + 80.0 * math.tan(math.radians(30.0))
        for alpha in (0.0, 4.0, 10.0, -9.0):
            assert _tau(m, alpha) == bedding, alpha
        # Not 30.0 itself: degrees(radians(30)) is 29.999999999999996, a
        # hair inside the transition.
        for alpha in (35.0, 60.0, 90.0, -45.0):
            assert _tau(m, alpha) == rock, alpha

    def test_a_is_equal_to_b_is_a_step(self):
        m = _al(A=20.0, B=20.0)
        assert _tau(m, 19.9) == 5.0 + 80.0 * math.tan(math.radians(15.0))
        assert _tau(m, 20.1) == 20.0 + 80.0 * math.tan(math.radians(30.0))


class TestAPlaneIsMohrCoulomb:
    """Every base of a planar surface has the same α: the model is then
    the Mohr-Coulomb material with that α's (c, φ), whatever the method."""

    def _project(self, strength):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.project import Project
        ext = Polyline(vertices=[
            Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
            Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("plane")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="bedded", unit_weight=20.0,
                                strength=strength)]
        return p

    def _fos(self, strength, method_id):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipSurface
        p = self._project(strength)
        daylight = TOE + H / math.tan(math.radians(BETA))
        plane = SlipSurface(polyline=Polyline(vertices=[
            Vertex(TOE, 0.0), Vertex(daylight, H)]))
        sl = slice_surface(p, plane, num_slices=N_SLICES)
        m = method_registry()[method_id]()
        m.tolerance = 1e-12
        res = m.compute_fos(p, plane, sl)
        assert res.fos is not None, (method_id, res.reason)
        return res.fos

    def test_in_the_nine_methods(self):
        from ogr_core.materials import MohrCoulomb
        from ogr_slip2d.methods import method_registry
        c, tan_phi = _by_hand(BETA)
        mc = MohrCoulomb(cohesion=c,
                         friction_angle=math.degrees(math.atan(tan_phi)))
        for mid in sorted(method_registry()):
            a = self._fos(_al(), mid)
            b = self._fos(mc, mid)
            assert math.isclose(a, b, rel_tol=1e-11), (mid, a, b)


class TestTheRule:

    def _code(self, **over):
        from ogr_core.project.rules import strength_model_refusal
        why = strength_model_refusal(_al(**over), "bedded")
        return None if why is None else why.code

    def test_valid_a_and_b(self):
        assert self._code() is None
        assert self._code(A=0.0, B=0.0) is None
        assert self._code(A=10.0, B=120.0) is None

    def test_what_it_refuses(self):
        assert self._code(A=-5.0) == "anisotropic_linear_ab"
        assert self._code(A=40.0, B=30.0) == "anisotropic_linear_ab"
        assert self._code(B=float("nan")) == "anisotropic_linear_ab"

    def test_the_analysis_and_the_api_ask_it(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        from ogr_core.materials import Material
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = Project("rule")
        p.materials = [Material(name="bedded", strength=_al(A=40.0,
                                                            B=30.0))]
        assert any("'bedded'" in s and "0 <= A <= B" in s
                   for s in check_analysis_settings(p))
        try:
            strength_from_spec({"model": "anisotropic_linear",
                                "params": dict(P, A=40.0, B=30.0)})
        except InvalidArgument as exc:
            assert "A <= B" in str(exc)
        else:
            raise AssertionError("the API accepted A > B")
