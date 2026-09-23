# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.191 — the Tensile Stress Check grants a Hoek-Brown rock mass the
tensile strength of its criterion, instead of the zero it granted every
material whatever the docstring said.

THE INVARIANT. ``checks._material_tensile_strength`` is the allowance the
Tensile Stress Check compares a slice base against. Until v0.1.191 it could
return nothing but 0.0, for three independent reasons, each sufficient
(defect D165): it read the parameters as attributes when they live in
``StrengthModel.params``; the names did not exist either (``sigci``, and
``m`` in the classic model); and its whitelist named
``generalized_hoek_brown``, which is no model's ``MODEL_ID``, while leaving
out ``hoek_brown_classic``, which is one. The allowance now comes from
``StrengthModel.tensile_strength()``, which is zero unless a model's
criterion defines a finite tensile strength, and the two Hoek-Brown models
override it with the parameters of their own instance.

WHAT THIS FILE DOES NOT CLAIM. It does not say the Hoek-Brown shear
envelope is right: it is not (``shear_strength`` gives tau(0) = 0 where the
criterion's Mohr envelope gives 307.5 kPa with the default constants —
defect D171, reported, not fixed here). And when it was written it did not
claim the reach the defect report assumed: ``AdvancedSettings.from_dict``
switched the check off on every reload (D178), so the allowance reached only
runs made in the same session, through the API or the CLI. v0.1.192 closed
D178 — a saved choice now survives reopening — and the allowance reaches
reopened projects too.

WHAT THIS FILE DISCRIMINATES against the v0.1.190 tree. MEASURED, by
copying this file into a ``git worktree`` at that commit and running it
there — not predicted. Of the 18 cases, **11 fail and 7 pass**:

  fail  generalised_hoek_brown_gets_s_sigci_over_mb        (behaviour)
        classic_hoek_brown_gets_s_sigci_over_m             (behaviour)
        the_bracket_vanishes_at_minus_the_allowance        (behaviour)
        the_exponent_a_does_not_move_it                    (behaviour)
        the_uniaxial_value_is_not_the_one_used             (behaviour)
        classic_equals_generalised_at_a_half               (behaviour)
        the_registry_sweep_finds_exactly_the_two           (behaviour)
        mild_tension_on_rock_is_admitted                   (behaviour)
        the_offending_slices_are_exactly_those_past_...    (behaviour)
        no_set_literal_in_checks_names_a_strength_model    (structural:
                                                   the stale list is there)
        the_override_cites_its_source_and_says_...         (WEAK: fails by
                                         the absence of the method itself)

  pass  degenerate_constants_give_zero                     (guard)
        a_strength_that_raises_gives_zero                  (guard)
        no_material_and_no_strength_give_zero              (guard)
        shear_normal_function_stays_at_zero_by_decision    (guard, decision)
        tension_beyond_the_allowance_is_still_rejected     (guard)
        the_same_tension_on_a_soil_is_still_rejected       (guard)
        the_fixture_puts_the_tension_where_the_check_looks (fixture guard)

The seven that pass do so BY DESIGN: the old function returned 0.0 for
everything, which is also the right answer for every input they feed it.
Nine of the eleven that fail do so on a number the check computes, not on
the absence of a symbol.

THE ANCHORS ARE IDENTITIES, NOT SNAPSHOTS. The tensile strength is the
root of the bracket of the criterion itself — set sigma'1 = sigma'3 =
sigma_t in sigma'1 = sigma'3 + sigma_ci*(mb*sigma'3/sigma_ci + s)^a and the
bracket must vanish — so the tests check THAT, on instances with
non-default constants whose numbers are written here: an override that
read the class defaults instead of the instance, which is the shape of
D165 itself, cannot pass them. The registry is swept, not listed.
"""
from __future__ import annotations

import ast
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: Non-default constants on purpose, written here and not read from the
#: model: reading ``PARAMETERS`` instead of ``params`` is exactly what
#: D165 was, and default constants would not tell the two apart.
GHB = dict(sigci=30000.0, mb=1.7, s=0.0039, a=0.62)
GHB_SIGMA_T = 0.0039 * 30000.0 / 1.7          # 68.8235... kPa
HBC = dict(sigci=20000.0, m=0.5, s=0.002)
HBC_SIGMA_T = 0.002 * 20000.0 / 0.5           # 80.0 kPa

CAPABLE = frozenset({"hoek_brown", "hoek_brown_classic"})


def _allowance(strength) -> float:
    from ogr_core.materials import Material
    from ogr_slip2d.checks import _material_tensile_strength
    return _material_tensile_strength(Material(name="rock",
                                               strength=strength))


def _ghb(**over):
    from ogr_core.materials import GeneralizedHoekBrown
    return GeneralizedHoekBrown(**dict(GHB, **over))


def _hbc(**over):
    from ogr_core.materials import HoekBrown
    return HoekBrown(**dict(HBC, **over))


# ======================================================================
class TestTheAllowanceIsTheRootOfTheBracket:
    """Hoek, Carranza-Torres & Corkum (2002): sigma'1 = sigma'3 = sigma_t."""

    def test_generalised_hoek_brown_gets_s_sigci_over_mb(self):
        got = _allowance(_ghb())
        assert abs(got - GHB_SIGMA_T) <= 1e-12 * GHB_SIGMA_T, (got,
                                                               GHB_SIGMA_T)

    def test_classic_hoek_brown_gets_s_sigci_over_m(self):
        got = _allowance(_hbc())
        assert abs(got - HBC_SIGMA_T) <= 1e-12 * HBC_SIGMA_T, (got,
                                                               HBC_SIGMA_T)

    def test_the_bracket_vanishes_at_minus_the_allowance(self):
        """The identity itself: at sigma'3 = -sigma_t the base of the power
        is zero, so sigma'1 = sigma'3 there, which is biaxial tension."""
        t = _allowance(_ghb())
        assert t > 0.0
        bracket = GHB["mb"] * (-t) / GHB["sigci"] + GHB["s"]
        assert abs(bracket) <= 1e-15, bracket

    def test_the_exponent_a_does_not_move_it(self):
        """The root of (mb*x/sigci + s)^a does not depend on a. The
        defect report said the expression held 'only with a = 0.5'; it is
        the UNIAXIAL strength (sigma'1 = 0) that depends on a."""
        seen = [_allowance(_ghb(a=a)) for a in (0.5, 0.55, 0.62, 0.65)]
        assert all(v > 0.0 for v in seen), seen
        assert max(seen) - min(seen) <= 1e-12 * max(seen), seen

    def test_the_uniaxial_value_is_not_the_one_used(self):
        """What was NOT chosen, written out so the choice is visible. With
        a = 0.5 the uniaxial root has a closed form (Hoek & Brown 1980),
        and it is not s*sigci/m: it differs by O(s/m^2)."""
        sci, m, s = HBC["sigci"], HBC["m"], HBC["s"]
        uniaxial = 2.0 * s * sci / (m + math.sqrt(m * m + 4.0 * s))
        used = _allowance(_hbc())
        assert used > 0.0
        assert abs(uniaxial - used) / used > 1e-3, (uniaxial, used)
        assert uniaxial < used

    def test_classic_equals_generalised_at_a_half(self):
        c = _allowance(_hbc())
        g = _allowance(_ghb(sigci=HBC["sigci"], mb=HBC["m"], s=HBC["s"],
                            a=0.5))
        assert c > 0.0
        assert abs(c - g) <= 1e-12 * c, (c, g)


# ======================================================================
class TestOnlyTheTwoRockModelsGetOne:
    """The whitelist is not typed anywhere; it is what the registry says."""

    def test_the_registry_sweep_finds_exactly_the_two(self):
        import ogr_core.materials  # noqa: F401  - registers the models
        from ogr_core.materials.registry import REGISTRY
        nonzero = set()
        for mid, cls in REGISTRY.all().items():
            if _allowance(cls()) != 0.0:
                nonzero.add(mid)
        assert nonzero == set(CAPABLE), nonzero

    def test_no_set_literal_in_checks_names_a_strength_model(self):
        """The hand-typed whitelist is what went stale, so none may come
        back. The two method sets of checks.py (M_ALPHA_SCREENED and
        NO_M_ALPHA_DENOMINATOR) name METHODS and must stay: the test looks
        only for strength-model ids."""
        from ogr_core.materials.registry import REGISTRY
        ids = set(REGISTRY.ids())
        src = io.open(_ROOT / "ogr_slip2d" / "checks.py",
                      encoding="utf-8").read()
        bad = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Set):
                names = {e.value for e in node.elts
                         if isinstance(e, ast.Constant)
                         and isinstance(e.value, str)}
                if names & ids:
                    bad.append(sorted(names))
        assert bad == [], bad

    def test_shear_normal_function_stays_at_zero_by_decision(self):
        """GUARD, and a decision rather than a fact: the reference lists the
        Shear-Normal Function among the models that CAN have a finite
        tensile strength, and no source gives the rule. A table that starts
        at (-50, 0) does reach tau = 0 in tension, so 'it cannot happen' is
        NOT the reason; 'nobody has published how' is."""
        from ogr_core.materials.builtin_models import ShearNormalFunction
        f = ShearNormalFunction(points=[(-50.0, 0.0), (0.0, 20.0),
                                        (100.0, 60.0)])
        assert f.shear_strength(-50.0) == 0.0     # the table does get there
        assert _allowance(f) == 0.0


# ======================================================================
class TestAnAllowanceNeverBreaksTheCheck:
    """GUARDS: ``BaseSearch._is_admissible`` swallows any exception and
    ADMITS the surface, so a crash here would let a failing surface
    through. Every degenerate input comes back as the conservative 0.0."""

    def test_degenerate_constants_give_zero(self):
        for over in (dict(mb=0.0), dict(mb=-1.0), dict(s=0.0), dict(s=-0.1),
                     dict(sigci=0.0), dict(sigci=-10.0),
                     dict(mb=float("nan")), dict(sigci=float("inf"))):
            assert _allowance(_ghb(**over)) == 0.0, over
        for over in (dict(m=0.0), dict(s=0.0), dict(sigci=-1.0)):
            assert _allowance(_hbc(**over)) == 0.0, over

    def test_a_strength_that_raises_gives_zero(self):
        from ogr_slip2d.checks import _material_tensile_strength

        class _Broken:
            MODEL_ID = "hoek_brown"

            def tensile_strength(self):
                raise RuntimeError("boom")

        class _Mat:
            strength = _Broken()

        assert _material_tensile_strength(_Mat()) == 0.0

    def test_no_material_and_no_strength_give_zero(self):
        from ogr_slip2d.checks import _material_tensile_strength

        class _Bare:
            strength = object()

        assert _material_tensile_strength(None) == 0.0
        assert _material_tensile_strength(_Bare()) == 0.0


# ======================================================================
def _flat_result(stresses, strength, fos=1.5):
    """A converged Bishop result on flat bases, built by hand.

    With alpha = 0 on every base, m_alpha = 1 and N = W exactly, so the
    effective normal stress the check computes is W/l - u to the last bit:
    each slice is given the stress it is meant to carry and nothing is
    left to a solver. The ground rises to the right, so the toe is slice 0
    and the 95 % the check tests are the first slices of the list.
    """
    from ogr_core.materials import Material
    from ogr_slip2d.methods.base import LEMResult
    from ogr_slip2d.slicer import Slice

    mat = Material(name="rock", strength=strength)
    out = []
    for i, sigma in enumerate(stresses):
        # 50 kN/m on a 1 m base: every pore pressure below comes out >= 0,
        # so no slice needs suction to carry the stress it is given.
        weight, ell = 50.0, 1.0
        u = weight / ell - sigma
        out.append(Slice(
            index=i, x_centre=i + 0.5, width=ell,
            base_x_left=float(i), base_x_right=float(i + 1),
            base_y_left=0.0, base_y_right=0.0,
            base_angle=0.0, base_length=ell,
            top_y_left=1.0 + i, top_y_right=2.0 + i,
            weight=weight, pore_pressure=u,
            water_weight=0.0, water_force_h=0.0,
            material=mat,
        ))
    return LEMResult(fos=fos, converged=True, iterations=1,
                     method_id="bishop_simplified", surface=None,
                     slices=out)


class TestTheVerdictMoves:
    """Rule 7: the allowance must change which surfaces are admissible."""

    N = 20
    MILD = 5          # a slice well inside the tested 95 %
    DEEP = 8

    def _stresses(self, mild, deep=None):
        s = [25.0] * self.N
        s[self.MILD] = mild
        if deep is not None:
            s[self.DEEP] = deep
        return s

    def test_the_fixture_puts_the_tension_where_the_check_looks(self):
        """GUARD on the fixture: the stress the check computes IS the one
        written, and the slice is inside the tested fraction."""
        from ogr_slip2d.checks import _toe_ordered_slices, \
            base_effective_stresses
        res = _flat_result(self._stresses(-0.5 * GHB_SIGMA_T), _ghb())
        got = base_effective_stresses(res)[self.MILD]
        assert abs(got + 0.5 * GHB_SIGMA_T) <= 1e-12 * GHB_SIGMA_T, got
        tested = _toe_ordered_slices(res)[:round(self.N * 0.95)]
        assert self.MILD in tested and self.DEEP in tested

    def test_mild_tension_on_rock_is_admitted(self):
        """The surface D165 was about: rejected with a zero allowance,
        admitted with the rock's own."""
        from ogr_slip2d.checks import check_surface
        res = _flat_result(self._stresses(-0.5 * GHB_SIGMA_T), _ghb())
        ok, why = check_surface(res, tensile=True)
        assert ok and why is None, why

    def test_tension_beyond_the_allowance_is_still_rejected(self):
        """GUARD: the allowance is finite, not a switch that admits all."""
        from ogr_slip2d.checks import check_surface
        res = _flat_result(self._stresses(-1.5 * GHB_SIGMA_T), _ghb())
        ok, why = check_surface(res, tensile=True)
        assert not ok and "error -120" in why, why

    def test_the_same_tension_on_a_soil_is_still_rejected(self):
        """GUARD: only a model whose criterion has a tensile strength gets
        one. Same stresses, Mohr-Coulomb, zero allowance."""
        from ogr_core.materials import MohrCoulomb
        from ogr_slip2d.checks import check_surface
        res = _flat_result(self._stresses(-0.5 * GHB_SIGMA_T),
                           MohrCoulomb(cohesion=50.0, friction_angle=35.0))
        ok, why = check_surface(res, tensile=True)
        assert not ok and "error -120" in why, why

    def test_the_offending_slices_are_exactly_those_past_the_allowance(self):
        from ogr_slip2d.checks import tensile_stress_check
        res = _flat_result(self._stresses(-0.5 * GHB_SIGMA_T,
                                          deep=-1.5 * GHB_SIGMA_T), _ghb())
        ok, bad = tensile_stress_check(res)
        assert not ok and bad == [self.DEEP], bad


# ======================================================================
class TestTheSourceSaysWhatItIs:
    """Weak by construction — a literal — and here for one reason: the
    formula is an INFERENCE of this program, and the sources are cited and
    NOT held, which is the convention checks.py:40-44 already keeps. A
    docstring that dropped either admission would be claiming more."""

    def test_the_override_cites_its_source_and_says_it_is_not_read(self):
        import re
        from ogr_core.materials import GeneralizedHoekBrown
        doc = re.sub(r"\s+", " ",
                     GeneralizedHoekBrown.tensile_strength.__doc__ or "")
        for tok in ("Hoek, Carranza-Torres & Corkum (2002)",
                    "does not depend on a", "inference", "not read"):
            assert tok in doc, tok
