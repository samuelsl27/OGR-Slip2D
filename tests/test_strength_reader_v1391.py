# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A linearisation resolves the slice's context once, not once per stress.

WHAT INVARIANT THIS PROTECTS.

V12 of the compute audit (v0.1.391). ``local_c_phi`` reads a model's
strength at the slice's stress and its two neighbours to linearise it. For a
model that needs the slice's context, each read went through
``shear_strength_ctx``, and Generalized Anisotropic found the rule that holds
the base at every read: Tutorial 20 resolved 2 779 738 rules for 933 523
linearisations (after v0.1.390). ``StrengthModel.shear_strength_reader``
now gives the strength at a context as a function of the stress alone, and
Generalized Anisotropic resolves the rule once in it, its
``shear_strength_ctx`` being built on the same resolution. Tutorial 20 went
from 36.3-38.2 s to 31.9-32.4 s (one fresh process per run, ABBA), every
evaluation identical. Class A: the same model read at the same stresses.

1. **The linearisation is v0.1.390's, to the bit:** that version's
   ``local_c_phi`` and Generalized Anisotropic ``shear_strength_ctx`` are
   written out below, and (c, tan phi) is compared for every model that
   reads a context — the two inputs of Generalized Anisotropic, Anisotropic
   Linear, SHANSEP — and one that does not, at bases of several angles and
   at stresses near zero (the one-sided secant) and away from it.
2. **One rule per linearisation:** counted, against three.
3. **A model that cannot answer raises what it raised:** a base no rule
   holds, and a rule whose model cannot be built, give the same exception
   type and message.
4. **The formula is not skipped:** a subclass with a ``shear_strength_ctx``
   of its own is read through it, and one that calls the parent's does not
   loop.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from types import SimpleNamespace


def _old_ga_ctx(self, sigma_n_eff, ctx=None):
    """``GeneralizedAnisotropic.shear_strength_ctx`` of v0.1.390, copied."""
    angle = math.degrees(ctx.base_angle_rad) if ctx is not None else 0.0
    if self.angle_or_surface:
        return self._angle_or_surface_strength(sigma_n_eff, ctx, angle)
    m = self._model_for_angle(angle)
    if getattr(m, "needs_context", False):
        return m.shear_strength_ctx(sigma_n_eff, ctx)
    return m.shear_strength(sigma_n_eff)


def _old_local_c_phi(slice_, material, sigma_n_eff, sigma_v_probe=None):
    """``strength_model.local_c_phi`` of v0.1.390, copied, with the
    Generalized Anisotropic reads of v0.1.390 too."""
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    from ogr_core.materials.strength_model import SliceContext
    if material is None:
        return 0.0, 0.0
    sn = max(sigma_n_eff, 0.0)
    strength = material.strength
    c_suction = getattr(slice_, "suction_cohesion", 0.0) or 0.0
    ctx = None
    if getattr(strength, "needs_context", False):
        ctx = SliceContext.from_slice(slice_, sn, sigma_v_probe)

    def _tau(s):
        if ctx is not None:
            if type(strength) is GeneralizedAnisotropic:
                return _old_ga_ctx(strength, s, ctx)
            return strength.shear_strength_ctx(s, ctx)
        return strength.shear_strength(s)

    tau_at_sn = _tau(sn)
    if not math.isfinite(tau_at_sn):
        return 1e12, 0.0
    tan_phi = None
    if ctx is None:
        tangent_fn = getattr(strength, "tangent_slope", None)
        if tangent_fn is not None:
            try:
                tan_phi = tangent_fn(sn)
            except Exception:  # noqa: BLE001 - as in v0.1.390
                tan_phi = None
    if tan_phi is None:
        base_delta = max(0.001, 0.0001 * sn)
        delta = base_delta
        if sn - delta < 0:
            tau_hi = _tau(sn + delta)
            if not math.isfinite(tau_hi):
                return 1e12, 0.0
            tan_phi = (tau_hi - tau_at_sn) / delta
        else:
            tau_lo = _tau(sn - delta)
            tau_hi = _tau(sn + delta)
            if not (math.isfinite(tau_lo) and math.isfinite(tau_hi)):
                return 1e12, 0.0
            tan_phi = (tau_hi - tau_lo) / (2.0 * delta)
    tan_phi = max(0.0, tan_phi)
    c = tau_at_sn - sn * tan_phi
    c = max(0.0, c)
    return c + c_suction, tan_phi


def _slice(deg):
    """The fields a context is built from, for a base at ``deg``."""
    return SimpleNamespace(base_angle=math.radians(deg), width=2.0,
                           weight=180.0, water_weight=0.0,
                           pore_pressure=12.0, top_y_left=20.0,
                           top_y_right=19.0, base_y_left=10.0,
                           base_y_right=9.0, suction_cohesion=0.0)


def _models():
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import (AnisotropicLinear,
                                                   GeneralizedAnisotropic,
                                                   MohrCoulomb, PowerCurve,
                                                   SHANSEP)
    soil = MohrCoulomb(cohesion=5.0, friction_angle=30.0)
    bed = PowerCurve(a=1.2, b=0.8, c=1.0, d=0.0, waviness=0.0)
    rules = GeneralizedAnisotropic(rules=[
        {"model": soil.to_dict(), "angle_min": -90.0, "angle_max": -12.0},
        {"model": bed.to_dict(), "angle_min": -12.0, "angle_max": 12.0},
        {"model": SHANSEP(S=0.3, m=0.8, OCR=1.5).to_dict(),
         "angle_min": 12.0, "angle_max": 90.0}])
    joints = GeneralizedAnisotropic(
        input_type="angle_or_surface", base={"model": soil.to_dict()},
        joints=[{"angle": 25.0, "A": 5.0, "B": 20.0,
                 "model": bed.to_dict()}], mapping="ab")
    out = {
        "rules": rules, "angle_or_surface": joints,
        "anisotropic_linear": AnisotropicLinear(c1=4.0, phi1=18.0, c2=15.0,
                                                phi2=32.0,
                                                bedding_angle=10.0),
        "shansep": SHANSEP(S=0.25, m=0.8, OCR=2.0),
        "mohr_coulomb": soil,
    }
    return {k: Material(name=k, strength=m) for k, m in out.items()}


ANGLES = (-55.0, -12.0, -3.5, 0.0, 7.25, 12.0, 24.0, 41.0, 63.0)
STRESSES = (0.0, 0.0004, 3.0, 87.5, 412.0)


def _hex(pair):
    return tuple(v.hex() for v in pair)


# ======================================================================
class TestTheLinearisationIsV0_1_390s:
    """Invariant 1."""

    def test_every_model_angle_and_stress(self):
        from ogr_core.materials.strength_model import local_c_phi
        n = 0
        for name, mat in _models().items():
            for deg in ANGLES:
                s = _slice(deg)
                for sn in STRESSES:
                    new = local_c_phi(s, mat, sn)
                    old = _old_local_c_phi(s, mat, sn)
                    assert _hex(new) == _hex(old), (name, deg, sn)
                    n += 1
        assert n == 5 * len(ANGLES) * len(STRESSES)

    def test_the_probe_of_zero_strength(self):
        """``sigma_v_probe`` replaces the vertical stress of the context."""
        from ogr_core.materials.strength_model import local_c_phi
        mat = _models()["rules"]
        for deg in ANGLES:
            for probe in (0.0, 50.0, 300.0):
                assert (_hex(local_c_phi(_slice(deg), mat, 10.0, probe))
                        == _hex(_old_local_c_phi(_slice(deg), mat, 10.0,
                                                 probe)))

    def test_shear_strength_ctx_itself(self):
        from ogr_core.materials.strength_model import SliceContext
        for name in ("rules", "angle_or_surface"):
            ga = _models()[name].strength
            for deg in ANGLES:
                ctx = SliceContext(base_angle_rad=math.radians(deg),
                                   sigma_v_eff=90.0)
                for sn in STRESSES:
                    assert (ga.shear_strength_ctx(sn, ctx).hex()
                            == _old_ga_ctx(ga, sn, ctx).hex()), (name, deg)


# ======================================================================
class TestOneRulePerLinearisation:
    """Invariant 2."""

    def test_counted(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.materials.strength_model import local_c_phi
        mat = _models()["rules"]
        real = GeneralizedAnisotropic.__dict__["_model_for_angle"]
        calls = []

        def counting(self, angle):
            calls.append(angle)
            return real(self, angle)

        GeneralizedAnisotropic._model_for_angle = counting
        try:
            local_c_phi(_slice(24.0), mat, 87.5)          # three reads
            assert len(calls) == 1
            local_c_phi(_slice(24.0), mat, 0.0)           # two reads
            assert len(calls) == 2
        finally:
            GeneralizedAnisotropic._model_for_angle = real


# ======================================================================
class TestAModelThatCannotAnswer:
    """Invariant 3."""

    def _raised(self, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - compared, not swallowed
            return type(exc).__name__, str(exc)
        return None

    def test_a_base_no_rule_holds(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import (GeneralizedAnisotropic,
                                                       MohrCoulomb)
        from ogr_core.materials.strength_model import local_c_phi
        gap = Material(name="gap", strength=GeneralizedAnisotropic(rules=[
            {"model": MohrCoulomb(cohesion=5.0, friction_angle=30.0)
             .to_dict(), "angle_min": -20.0, "angle_max": 20.0}]))
        new = self._raised(lambda: local_c_phi(_slice(35.0), gap, 50.0))
        old = self._raised(lambda: _old_local_c_phi(_slice(35.0), gap, 50.0))
        assert new is not None and new == old

    def test_a_rule_that_cannot_be_built(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.materials.strength_model import local_c_phi
        broken = Material(name="broken", strength=GeneralizedAnisotropic(
            rules=[{"model": {"model_id": "no_such_model"},
                    "angle_min": -90.0, "angle_max": 90.0}]))
        new = self._raised(lambda: local_c_phi(_slice(10.0), broken, 50.0))
        old = self._raised(lambda: _old_local_c_phi(_slice(10.0), broken,
                                                    50.0))
        assert new is not None and new == old


# ======================================================================
class TestTheFormulaIsNotSkipped:
    """Invariant 4."""

    def test_a_subclass_with_its_own_formula(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.materials.strength_model import local_c_phi

        class Doubled(GeneralizedAnisotropic):
            def shear_strength_ctx(self, sigma_n_eff, ctx=None):
                return 2.0 * super().shear_strength_ctx(sigma_n_eff, ctx)

        base = _models()["rules"].strength
        twice = Material(name="twice", strength=Doubled(rules=base.rules))
        once = Material(name="once", strength=GeneralizedAnisotropic(
            rules=base.rules))
        # a base the Mohr-Coulomb rule holds: friction to double
        c2, t2 = local_c_phi(_slice(-55.0), twice, 87.5)
        c1, t1 = local_c_phi(_slice(-55.0), once, 87.5)
        assert t1 > 0.0
        assert math.isclose(t2, 2.0 * t1, rel_tol=1e-9)
        assert math.isclose(c2, 2.0 * c1, rel_tol=1e-9, abs_tol=1e-12)
