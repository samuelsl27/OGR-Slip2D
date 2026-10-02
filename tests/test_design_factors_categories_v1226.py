# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.226 — the design standard factors every strength model by the
CATEGORY of its parameters, not by their names (defect D224 of the
verification bank).

THE DEFECT. ``design_factors.py`` divided a parameter when its NAME was on
a list: ``cohesion``, ``cohesion_top``, ``undrained_strength``,
``constant_c`` or ``c`` by the cohesion factor, and the tangent of
``friction_angle``, ``phi`` or ``friction_angle_top`` by the friction one.
So Anisotropic Linear, the anisotropic function's rows, the rules of
Generalized Anisotropic, the τ–σ'ₙ tables, SHANSEP, Vertical Stress Ratio,
Hoek-Brown, Barton-Bandis, φb and the rapid-drawdown envelopes were NOT
factored and nothing said so; the undrained models with depth were
factored in part (cu(z) = c_top/γ + Δc·z) or not at all (``cohesion_datum``);
the power curve had only its ``c`` divided; cu took the COHESION factor,
where EN 1997-1 (Annex A) gives γcu = 1.4 against γc' = 1.25; and
``factor_resistance`` (γR;e = 1.1 in DA2) was applied nowhere.

THE DECISION, with its sources: the four categories of material factor of
the reference documentation's design-standard dialog -- c', tan φ', cu and
"Shear strength (other models)" -- each model saying which one its
parameters are, and γR;e dividing the four (Frank et al. 2004, §11.5: the
over-design factor is F/(γG·γR;e)). γτ = γφ' in the Eurocode 7 presets is
a decision: EN 1997-1 does not define it.

THE REFERENCES (rule 1): strength reduction. With the four factors equal
to γ, every model's strength is divided by γ at every σ'ₙ, and since the
limit-equilibrium equations read strength only through τ/F, the factor of
safety of the factored copy is F/γ in every method -- the identity the
reference's own Eurocode 7 tutorial shows (F = 1.37, DA1-C2: 1.096 =
1.37/1.25).

DISCRIMINATION, measured on the v0.1.225 tree: 20 of the 21 cases fail
there. 11 fail by behaviour: cu with the cohesion factor, the suction, the
drawdown envelopes, the power curve, the depth profile, the nine methods
(Anisotropic Linear unfactored), γR;e, DA2, the category in the report, the
permanent-factor note and the command line. 9 fail by a symbol that did not
exist (``design_factored``, the new settings fields, ``from_dict``, the
divisor). The Mohr-Coulomb control passes.
"""
from __future__ import annotations

import math

GAMMA = 1.3            # none of the presets' values, on purpose
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30
SIGMAS = (0.0, 5.0, 40.0, 150.0, 600.0)


def _mf(g=GAMMA):
    from ogr_core.materials.strength_model import MaterialFactors
    return MaterialFactors(cohesion=g, tan_phi=g, undrained=g, shear=g)


def _ctx():
    """A context every model can read: angle, σ'v, depth, the layer top
    and the distance to the slope."""
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(20.0), sigma_v_eff=120.0,
                        depth=7.0, pore_pressure=10.0, y_base=5.0,
                        layer_top_y=12.0, slope_distance=4.0)


def _tau(model, sigma):
    return model.shear_strength_ctx(sigma, _ctx())


def _mc_rules():
    out, lo = [], -90.0
    for hi, c, phi in ((-30.0, 10.0, 35.0), (0.0, 1.0, 20.0),
                       (90.0, 5.0, 10.0)):
        out.append({"angle_min": lo, "angle_max": hi,
                    "model": {"model_id": "mohr_coulomb",
                              "params": {"cohesion": c,
                                         "friction_angle": phi}}})
        lo = hi
    return out


def _instance(mid, cls):
    """A registered model with its defaults, or with something to compute
    with when the default has nothing (Generalized's empty rules)."""
    if mid == "generalized_anisotropic":
        return cls(rules=_mc_rules())
    return cls()


def _project(strength, name="m"):
    """The dry slope of ``test_anisotropic_function_ranges_v1218``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("factors")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name=name, unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _custom(project, c=1.0, phi=1.0, cu=1.0, tau=1.0, r=1.0, perm=1.0,
            var=1.0):
    ds = project.settings.design_standard
    ds.enabled = True
    ds.standard = "custom"
    (ds.factor_cohesion, ds.factor_friction, ds.factor_undrained,
     ds.factor_shear_strength, ds.factor_resistance, ds.factor_permanent,
     ds.factor_variable) = (c, phi, cu, tau, r, perm, var)
    return project


def _fos(project, method_id):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    circle = SlipCircle(*CIRCLE)
    sl = slice_surface(project, circle, num_slices=N_SLICES)
    m = method_registry()[method_id]()
    m.tolerance = 1e-12
    res = m.compute_fos(project, circle, sl)
    assert res.fos is not None, (method_id, res.reason)
    return res.fos


def _factored(project):
    from ogr_core.project import apply_design_factors
    return apply_design_factors(project)


# ======================================================================
class TestEveryModelSaysItsCategory:

    def test_no_built_in_model_is_left_silent(self):
        from ogr_core.materials import REGISTRY
        for mid, cls in REGISTRY.all().items():
            done = _instance(mid, cls).design_factored(_mf())
            assert done.category, mid
            # v0.1.229 (D215) -- changed on purpose: Snowden is no longer
            # the exception. Its transition now blends the two strengths
            # linearly, so each function factored by its own model divides
            # the whole; it needs no note.
            assert done.note is None, (mid, done.note)

    def test_a_model_that_declares_nothing_is_left_alone_and_said(self):
        from ogr_core.materials.strength_model import StrengthModel

        class _Plugin(StrengthModel):
            MODEL_ID = "a_plugin"
            DISPLAY_NAME = "A plugin"

            def shear_strength(self, sigma_n_eff):
                return 7.0

        m = _Plugin()
        done = m.design_factored(_mf())
        assert done.model is m and not done.changes
        assert "NOT factored" in done.note

    def test_a_factor_of_one_changes_nothing_bit_for_bit(self):
        from ogr_core.materials import REGISTRY
        for mid, cls in REGISTRY.all().items():
            m = _instance(mid, cls)
            done = m.design_factored(_mf(1.0))
            assert not done.changes, (mid, done.changes)
            if mid != "infinite_strength":
                for s in SIGMAS:
                    assert _tau(done.model, s) == _tau(m, s), (mid, s)


class TestTheStrengthIsDividedByGamma:
    """Every model, at every σ'ₙ: τ_design = τ/γ."""

    def test_every_model(self):
        from ogr_core.materials import REGISTRY
        # v0.1.229 (D215) -- changed on purpose: Snowden joined; its
        # transition interpolated the angle until then.
        skip = {"infinite_strength", "no_strength"}
        for mid, cls in REGISTRY.all().items():
            if mid in skip:
                continue
            m = _instance(mid, cls)
            f = m.design_factored(_mf()).model
            for s in SIGMAS:
                want = _tau(m, s) / GAMMA
                got = _tau(f, s)
                assert math.isclose(got, want, rel_tol=1e-12,
                                    abs_tol=1e-12), (mid, s, got, want)

    def test_the_users_model_is_never_touched(self):
        from ogr_core.materials import REGISTRY
        for mid, cls in REGISTRY.all().items():
            m = _instance(mid, cls)
            before = m.to_dict()
            m.design_factored(_mf())
            assert m.to_dict() == before, mid


class TestTheFactorOfSafety:
    """F_design = F/γ in the nine methods: strength reduction."""

    def _models(self):
        from ogr_core.materials.builtin_models import (
            SHANSEP, AnisotropicLinear, GeneralizedAnisotropic,
            GeneralizedHoekBrown, MohrCoulomb, UndrainedDepthFromDatum)
        return {
            "mohr_coulomb": MohrCoulomb(cohesion=6.0, friction_angle=24.0),
            "anisotropic_linear": AnisotropicLinear(
                c1=4.0, phi1=18.0, c2=15.0, phi2=33.0, A=5.0, B=45.0),
            "generalized_anisotropic": GeneralizedAnisotropic(
                rules=_mc_rules()),
            "shansep": SHANSEP(S=0.3, m=0.8, OCR=2.0, A=4.0),
            "undrained_depth_datum": UndrainedDepthFromDatum(
                cohesion_datum=15.0, cohesion_change=1.5, datum=12.0),
            "hoek_brown": GeneralizedHoekBrown(sigci=2000.0, mb=1.2,
                                               s=0.0005, a=0.52),
        }

    def test_in_the_nine_methods(self):
        from ogr_slip2d.methods import method_registry
        for name, strength in self._models().items():
            p = _project(strength)
            out, _rep = _factored(_custom(_project(strength), GAMMA, GAMMA,
                                          GAMMA, GAMMA))
            for mid in sorted(method_registry()):
                a = _fos(p, mid)
                b = _fos(out, mid)
                # Measured on v0.1.226: 5.1e-10 at worst (Corps 1 on the
                # Hoek-Brown slope), the iteration's own tolerance.
                assert math.isclose(b, a / GAMMA, rel_tol=5e-9), (
                    name, mid, a, b, a / b)

    def test_the_resistance_factor_divides_all_four(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        mc = MohrCoulomb(cohesion=6.0, friction_angle=24.0)
        p = _project(mc)
        out, _rep = _factored(_custom(_project(mc), r=1.1))
        a = _fos(p, "bishop_simplified")
        b = _fos(out, "bishop_simplified")
        assert math.isclose(b, a / 1.1, rel_tol=1e-9), (a, b)


class TestEachCategoryByHand:

    def test_c_and_tan_phi_with_different_factors(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        out, _ = _factored(_custom(_project(
            MohrCoulomb(cohesion=12.0, friction_angle=20.0)), 1.25, 1.4))
        p = out.materials[0].strength.params
        assert math.isclose(p["cohesion"], 12.0 / 1.25, rel_tol=1e-15)
        assert math.isclose(math.tan(math.radians(p["friction_angle"])),
                            math.tan(math.radians(20.0)) / 1.4,
                            rel_tol=1e-12)

    def test_cu_takes_its_own_factor(self):
        """γcu, not the cohesion factor: 1.4 and 1.25 in set M2."""
        from ogr_core.materials.builtin_models import Undrained
        out, _ = _factored(_custom(_project(Undrained(cohesion=70.0)),
                                   c=1.25, cu=1.4))
        assert math.isclose(out.materials[0].strength.params["cohesion"],
                            50.0, rel_tol=1e-15)

    def test_the_whole_depth_profile_is_a_cu(self):
        from ogr_core.materials.builtin_models import UndrainedDepthFromDatum
        m = UndrainedDepthFromDatum(cohesion_datum=20.0, cohesion_change=2.0,
                                    datum=0.0, cutoff=60.0)
        m.cutoff_enabled = True
        out, _ = _factored(_custom(_project(m), cu=2.0))
        f = out.materials[0].strength
        assert f.cutoff_enabled is True
        for depth in (0.0, 5.0, 17.0, 30.0):
            assert math.isclose(f.cohesion_at(depth), m.cohesion_at(depth) / 2,
                                rel_tol=1e-15), depth

    def test_the_other_models_take_the_shear_strength_factor(self):
        from ogr_core.materials.builtin_models import (BartonBandis,
                                                       PowerCurve,
                                                       ShearNormalFunction)
        for m in (PowerCurve(a=0.7, b=0.8, c=3.0, d=2.0, waviness=5.0),
                  ShearNormalFunction(points=[(0, 5), (100, 45), (300, 110)]),
                  BartonBandis()):
            out, _ = _factored(_custom(_project(m), c=1.9, phi=1.9, tau=1.6))
            f = out.materials[0].strength
            for s in (10.0, 80.0, 250.0):
                assert math.isclose(f.shear_strength(s),
                                    m.shear_strength(s) / 1.6,
                                    rel_tol=1e-12), (type(m).__name__, s)

    def test_the_divisor_survives_a_copy_of_the_copy(self):
        """A statistical run copies the factored project again."""
        from ogr_core.materials.builtin_models import GeneralizedHoekBrown
        from ogr_core.project import Project
        out, _ = _factored(_custom(_project(GeneralizedHoekBrown()),
                                   tau=1.5))
        again = Project.from_dict(out.to_dict())
        assert again.materials[0].strength.design_divisor == 1.5

    def test_suction_goes_with_tan_phi(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        p = _project(MohrCoulomb(cohesion=5.0, friction_angle=30.0))
        p.materials[0].phi_b = 15.0
        out, rep = _factored(_custom(p, phi=1.4))
        assert math.isclose(math.tan(math.radians(out.materials[0].phi_b)),
                            math.tan(math.radians(15.0)) / 1.4,
                            rel_tol=1e-12)
        assert "phi_b" in rep.materials[0]["changes"]

    def test_the_drawdown_envelopes_as_c_and_tan_phi(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.materials.drawdown_envelopes import (Kc1Envelope,
                                                           REnvelope)
        for env, c_attr, a_attr in ((REnvelope(12.0, 18.0), "c_r",
                                     "phi_r_deg"),
                                    (Kc1Envelope(9.0, 22.0), "d",
                                     "psi_deg")):
            p = _project(MohrCoulomb(cohesion=5.0, friction_angle=30.0))
            p.materials[0].drawdown_envelope = env
            out, _ = _factored(_custom(p, c=1.25, phi=1.4))
            f = out.materials[0].drawdown_envelope
            assert math.isclose(getattr(f, c_attr),
                                getattr(env, c_attr) / 1.25, rel_tol=1e-15)
            assert math.isclose(
                math.tan(math.radians(getattr(f, a_attr))),
                math.tan(math.radians(getattr(env, a_attr))) / 1.4,
                rel_tol=1e-12)


class TestThePresets:

    def test_eurocode_7_sets(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        want = {"eurocode7_da1c1": (1.0, 1.0), "eurocode7_da1c2": (1.4, 1.25),
                "eurocode7_da2": (1.0, 1.0), "eurocode7_da3": (1.4, 1.25)}
        for name, (cu, tau) in want.items():
            s = D()
            s.apply_preset(name)
            assert (s.factor_undrained, s.factor_shear_strength) == (cu, tau)

    def test_da2_applies_its_resistance_factor(self):
        """γR;e = 1.1 divides the resistance. Since v0.1.242 (D226a) DA2
        also multiplies the weight by γG = 1.35, which on this c-φ slope is
        no plain division (``test_design_weight_factors_v1242`` holds the
        whole DA2 identity, F/1.485, on an undrained slope): γG is set back
        to 1 here, so that what is measured is the resistance factor."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        mc = MohrCoulomb(cohesion=6.0, friction_angle=24.0)
        p = _project(mc)
        q = _project(mc)
        ds = q.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da2")
        ds.standard = "custom"
        ds.factor_permanent = 1.0
        out, _rep = _factored(q)
        a = _fos(p, "bishop_simplified")
        b = _fos(out, "bishop_simplified")
        assert math.isclose(b, a / 1.1, rel_tol=1e-9), (a, b)

    def test_an_old_file_gets_the_new_factors(self):
        """A file written before 0.1.226: a named standard takes them from
        its preset, a custom one keeps dividing cu by its cohesion factor."""
        from ogr_core.project.settings import DesignStandardSettings as D
        old = {"enabled": True, "standard": "eurocode7_da1c2",
               "factor_permanent": 1.0, "factor_variable": 1.3,
               "factor_cohesion": 1.25, "factor_friction": 1.25,
               "factor_unit_weight": 1.0, "factor_resistance": 1.0}
        s = D.from_dict(old)
        assert (s.factor_undrained, s.factor_shear_strength) == (1.4, 1.25)
        s = D.from_dict(dict(old, standard="custom", factor_cohesion=1.3))
        assert (s.factor_undrained, s.factor_shear_strength) == (1.3, 1.0)
        s = D.from_dict(dict(old, factor_undrained=1.1))
        assert s.factor_undrained == 1.1


class TestTheReport:

    def test_the_permanent_factor_is_said(self):
        """Until v0.1.242 the note said the factor was NOT applied; since
        D226a it says how it is (``test_design_weight_factors_v1242``)."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        _out, rep = _factored(_custom(_project(MohrCoulomb()), perm=1.35))
        assert any("permanent-action factor 1.35 multiplies the weight" in n
                   for n in rep.notes), rep.notes

    def test_a_model_note_reaches_the_report(self):
        """What a model says it could not factor is in the report, with the
        material's name (restored even if the case fails: the runner does
        not run teardown methods)."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.materials.strength_model import FactoredStrength
        real = MohrCoulomb.design_factored
        try:
            MohrCoulomb.design_factored = (
                lambda self, f: FactoredStrength(self, {}, "", note="said"))
            _out, rep = _factored(_custom(_project(MohrCoulomb()), 1.25,
                                          1.25))
        finally:
            MohrCoulomb.design_factored = real
        assert any("said" in n and "'m'" in n for n in rep.notes), rep.notes

    def test_the_report_names_the_category(self):
        from ogr_core.materials.builtin_models import Undrained
        _out, rep = _factored(_custom(_project(Undrained()), cu=1.4))
        assert rep.materials[0]["category"] == "cu"

    def test_the_command_line_prints_the_notes(self, tmp_path):
        from pathlib import Path

        from typer.testing import CliRunner

        from ogr_cli.__main__ import app
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project.units import FailureDirection
        p = _project(MohrCoulomb(cohesion=6.0, friction_angle=24.0))
        p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        p.settings.methods.num_slices = 20
        p.settings.search.grid_nx = 2
        p.settings.search.grid_ny = 2
        p.settings.search.radius_increment = 2
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da2")
        path = Path(tmp_path) / "notes.ogr"
        p.save(path)
        res = CliRunner().invoke(app, ["compute", str(path), "--output",
                                       str(Path(tmp_path) / "r.h5")])
        assert res.exit_code == 0, res.output
        assert "permanent-action factor" in res.output, res.output
