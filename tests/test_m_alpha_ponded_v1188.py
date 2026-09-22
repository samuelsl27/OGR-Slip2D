# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The two admissibility checks linearise the envelope at ONE stress.

INVARIANT PROTECTED
-------------------
``checks.base_effective_stresses`` and ``checks.base_m_alphas`` both hand
a normal stress to ``BishopSimplified._local_c_phi``, which returns
``(c, tan phi)`` *evaluated at that stress*. If they estimate it
differently, the tensile check and the m-alpha check judge the same slice
at two different stresses — and the m-alpha check is on by default, so
the disagreement decides which surfaces a search is allowed to keep.

THE BUG THIS EXISTS FOR (D113)
------------------------------
v0.1.67 taught ``base_effective_stresses`` that the base carries the
ponded water standing on the slice as well as the soil; leaving it out
had made that check judge a reservoir-loaded slope with about a third of
the real normal force, "the difference between 'in tension' and not".
``base_m_alphas``, the same loop fifteen lines below, was not taught, and
stayed on the bare soil weight for a hundred and twenty-one versions.

It only shows where BOTH conditions meet in one slice: the envelope must
depend on sigma (on a straight Mohr-Coulomb line ``tan phi`` is the same
at every stress, so the two estimates agree) and there must be water
standing on the slice (otherwise the two estimates ARE the same number).
``TestOnlyBothConditionsTogetherMoveIt`` runs that 2x2 as a table.

WHY NOTHING HERE IS A SNAPSHOT
------------------------------
No test below fixes a factor of safety, or any other number, against
what this code prints today. The anchors are:

* the CLOSED FORM of the power-curve tangent, ``dtau/dsigma =
  a*b*(sigma + d)^(b-1) + tan(W)`` (``PowerCurve.tangent_slope``), which
  is differential calculus on the published envelope and not a
  measurement — ``test_the_tangent_is_the_closed_form`` computes it here
  from a, b and d and compares;
* the definition ``m_alpha = cos(alpha) + s*sin(alpha)*tan(phi)/F``
  (Bishop 1955, as the module docstring of ``checks.py`` states it),
  recomputed independently from the slice geometry;
* IDENTITY between the two functions: the stress one of them linearises
  at must be the stress the other linearises at. That is the defect
  stated as an equation, and it is true or false regardless of what
  either one returns.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.187 tree, 5 of the 12 cases FAIL and 7 PASS, and the
split is not an accident:

* the five that fail all read ``checks.base_m_alphas`` — the identity
  against the wet estimate, the identity between the two checks, the two
  rule-7 cases and the verdict;
* the seven that pass do so BY DESIGN, because they state what the
  defect IS by reading the engine directly rather than the fix: the
  three fixture guards, the closed-form tangent, and the 2x2 attribution
  table with its two controls, which compare this file's own two
  recomputations and would hold on any tree.

The one-line correction to ``test_checks_v132.py`` that went with this
change does NOT discriminate either, and saying so matters: that test
recomputed ``m_alpha`` with the dry estimate while its own docstring
claimed it reproduced the solver's, and it passed on both trees because
its model has no water at all. It was the guard that should have caught
this and could not.

The model is the upstream face of a dam with the reservoir standing on
it — the geometry of ``test_base_normal_v167.py``, which v0.1.67 already
used because the ponded load there dominates the soil weight (measured
below: about four times it). Its material is a power curve so the
envelope depends on sigma; the Mohr-Coulomb arm of the table is the same
model with the same water and a straight envelope, which is what makes
the attribution a control and not an anecdote.
"""
from __future__ import annotations

import math

GAMMA_W = 9.81                       # kN/m3
GAMMA = 20.0                         # kN/m3
WATER_Y = 72.0                       # reservoir level, above the face

# Power-curve envelope, tau = c + a*(sigma + d)^b + sigma*tan(W). ``b``
# below 1 is what makes the tangent fall as sigma grows, which is the
# whole reason the estimate matters; with the parameter default b = 1.0
# the envelope is a straight line and this file would test nothing.
POWER = dict(a=3.4, b=0.6, c=0.0, d=0.15, waviness=0.0)

CIRCLE = dict(centre_x=52.0, centre_y=186.0, radius=158.2)
N_SLICES = 25

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _project(power: bool = True, ponded: bool = True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.builtin_models import PowerCurve
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
        Vertex(205, 78), Vertex(145, 58),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ponded-power")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if ponded:
        # Only a WATER_TABLE ponds. A piezometric line drawn at the same
        # height would not, which is the rule fixed in
        # ``test_ponded_water_v161.py``.
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, WATER_Y),
                                        Vertex(265, WATER_Y)], closed=False),
            btype=BoundaryType.WATER_TABLE))
    strength = (PowerCurve(**POWER) if power
                else MohrCoulomb(cohesion=0.0, friction_angle=45.0))
    p.materials = [Material(
        name="fill", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=strength,
        pore_pressure=(PorePressureType.WATER_TABLE if ponded
                       else PorePressureType.NONE))]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def _surface():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**CIRCLE)


def _result(power: bool = True, ponded: bool = True):
    """The converged result, shared between cases of the same class.

    Slicing and converging the same four models once per test would pay
    for the same arithmetic dozens of times; a file that did exactly
    that went from 48 s to 12 s by sharing its starting geometry.
    """
    key = (power, ponded)
    if key not in _CACHE:
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        p = _project(power, ponded)
        surf = _surface()
        sl = slice_surface(p, surf, num_slices=N_SLICES)
        assert sl is not None, (power, ponded)
        res = BishopSimplified().compute_fos(p, surf, sl)
        assert res.fos is not None and res.is_valid, (power, ponded,
                                                      res.error_message)
        _CACHE[key] = res
    return _CACHE[key]


def _slide_sign(slices) -> float:
    driving = sum(s.weight * math.sin(s.base_angle) for s in slices)
    return 1.0 if driving >= 0 else -1.0


def _sigma(s, with_water: bool) -> float:
    """The two estimates, written out rather than imported.

    Importing ``checks._base_load_and_sigma`` would make every assertion
    below a tautology. The point is an INDEPENDENT recomputation.
    """
    l = max(s.base_length, 1e-12)
    w = s.weight + (getattr(s, "water_weight", 0.0) if with_water else 0.0)
    return max(0.0, w * math.cos(s.base_angle) - s.pore_pressure * l) / l


def _m_alphas(res, with_water: bool) -> list[float]:
    """``m_alpha`` from Bishop's definition, at one of the two estimates."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    slices = list(res.slices)
    sgn = _slide_sign(slices)
    out = []
    for s in slices:
        _c, tan_phi = BishopSimplified._local_c_phi(
            s, s.material, _sigma(s, with_water))
        out.append(math.cos(s.base_angle)
                   + sgn * math.sin(s.base_angle) * tan_phi / res.fos)
    return out


# ======================================================================
class TestTheFixtureReallyExercisesTheDefect:
    """Guard the guard. Both conditions have to be present, and neither
    is asserted from a model_id: they are measured."""

    def test_the_ponded_water_dominates_the_soil_weight(self):
        slices = list(_result().slices)
        w_soil = sum(s.weight for s in slices)
        w_water = sum(getattr(s, "water_weight", 0.0) for s in slices)
        assert w_water > w_soil, (w_soil, w_water)

    def test_the_dry_estimate_saturates_to_zero_under_the_reservoir(self):
        """The old failure mode is not "a bit low": it is pinned at zero.

        With the reservoir full, ``u*l`` on these slices is about
        1200 kN/m while the soil weight alone is about 300, so
        ``max(0, W_soil*cos(alpha) - u*l)`` clamps to zero on EVERY
        slice. The envelope then gets linearised at sigma = 0, which for
        a power curve with b < 1 is where the tangent is steepest — so
        the dry estimate does not merely shift ``m_alpha``, it reports
        the flattest surface as the strongest. It is the same symptom
        v0.1.67 found on Pilarcitos, where "all the undrained strengths
        came out zero" for exactly this reason, left behind in the
        sibling function for a hundred and twenty-one versions.
        """
        slices = list(_result().slices)
        wet = [s for s in slices if getattr(s, "water_weight", 0.0) > 0.0]
        assert len(wet) > 0
        assert all(_sigma(s, False) == 0.0 for s in wet)
        lifted = [s for s in wet if _sigma(s, True) > 0.0]
        assert lifted, "the water never lifts the estimate off the floor"

    def test_the_envelope_depends_on_sigma_and_the_control_does_not(self):
        """Measured through ``_local_c_phi``, not read off a model_id.

        A list of model ids is exactly the kind of check that goes stale
        the day a new strength model is born; the property that matters
        is whether ``tan phi`` moves, so that is what is asked.
        """
        from ogr_slip2d.methods.bishop import BishopSimplified as B
        power = list(_result(True, True).slices)[0].material
        line = list(_result(False, True).slices)[0].material
        _c1, t1 = B._local_c_phi(None, power, 5.0)
        _c2, t2 = B._local_c_phi(None, power, 500.0)
        assert abs(t1 - t2) > 1e-3, (t1, t2)
        _c3, t3 = B._local_c_phi(None, line, 5.0)
        _c4, t4 = B._local_c_phi(None, line, 500.0)
        # The straight line is not exactly constant: Mohr-Coulomb has no
        # ``tangent_slope``, so ``_local_c_phi`` takes a centred secant
        # and at 500 kPa that subtracts two numbers of order 300 to
        # recover a difference of order 0.06. The residue is ~1e-10,
        # nine orders below the power curve's.
        assert abs(t3 - t4) < 1e-6, (t3, t4)


# ======================================================================
class TestOneEstimateForBothChecks:
    """The identity. It is the defect written as an equation."""

    def test_base_m_alphas_uses_the_estimate_that_carries_the_water(self):
        from ogr_slip2d.checks import base_m_alphas
        res = _result()
        got = base_m_alphas(res)
        want = _m_alphas(res, with_water=True)
        assert len(got) == len(want) == len(list(res.slices))
        for i, (g, w) in enumerate(zip(got, want)):
            assert abs(g - w) < 1e-12, (i, g, w)

    def test_the_two_checks_linearise_at_the_same_stress(self):
        """``base_effective_stresses`` already carried the water (v0.1.67).

        Recovering the stress each function used is possible because both
        are built on ``_local_c_phi``: if they agreed on sigma they agree
        on ``tan phi``, and then the m_alpha that the stress function
        divides by is the m_alpha the other function publishes. Checking
        the two recomputations against ONE estimate is the same statement
        with one fewer step.
        """
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        res = _result()
        slices = list(res.slices)
        sgn = _slide_sign(slices)
        from ogr_slip2d.methods.bishop import BishopSimplified
        want = []
        for s in slices:
            l = max(s.base_length, 1e-12)
            u = s.pore_pressure
            W = s.weight + getattr(s, "water_weight", 0.0)
            c_loc, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, _sigma(s, True))
            m_alpha = (math.cos(s.base_angle)
                       + sgn * math.sin(s.base_angle) * tan_phi / res.fos)
            N = (W - sgn * (c_loc * l * math.sin(s.base_angle)
                            - u * l * tan_phi * math.sin(s.base_angle))
                 / res.fos) / m_alpha
            want.append(N / l - u)
        got = base_effective_stresses(res)
        for i, (g, w) in enumerate(zip(got, want)):
            assert abs(g - w) <= 1e-9 * max(1.0, abs(w)), (i, g, w)
        # and the denominator that produced them is the published one
        for g, w in zip(base_m_alphas(res), _m_alphas(res, True)):
            assert abs(g - w) < 1e-12

    def test_the_tangent_is_the_closed_form(self):
        """External anchor: differential calculus on the envelope.

        ``tau = c + a*(sigma + d)^b + sigma*tan(W)`` differentiates to
        ``a*b*(sigma + d)^(b-1) + tan(W)``. Computed here from a, b, d
        and W, not read from the model.
        """
        from ogr_slip2d.methods.bishop import BishopSimplified
        a, b = POWER["a"], POWER["b"]
        d, W = POWER["d"], POWER["waviness"]
        res = _result()
        checked = 0
        for s in list(res.slices):
            sigma = _sigma(s, True)
            _c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma)
            closed = (a * b * ((sigma + d) ** (b - 1.0))
                      + math.tan(math.radians(W)))
            assert abs(tan_phi - closed) <= 1e-12 * max(1.0, closed), (
                sigma, tan_phi, closed)
            checked += 1
        assert checked > 0          # a loop that asserts nothing is not a test


# ======================================================================
class TestItMovesTheNumber:
    """Rule 7. A correction that cannot change a result is not one.

    These are the assertions that FAIL against the v0.1.187 tree, where
    ``base_m_alphas`` estimates sigma from the bare soil weight.
    """

    def test_the_published_m_alpha_is_not_the_dry_one(self):
        from ogr_slip2d.checks import base_m_alphas
        res = _result()
        got = base_m_alphas(res)
        dry = _m_alphas(res, with_water=False)
        moved = [i for i in range(len(got))
                 if abs(got[i] - dry[i]) > 1e-6 * max(1.0, abs(dry[i]))]
        assert moved, "the two estimates are indistinguishable here"
        assert max(abs(got[i] - dry[i]) for i in moved) > 1e-3

    def test_the_minimum_moves_by_a_measurable_amount(self):
        from ogr_slip2d.checks import base_m_alphas
        res = _result()
        wet, dry = min(base_m_alphas(res)), min(_m_alphas(res, False))
        assert wet < dry            # more stress, flatter tangent, lower m
        assert (dry - wet) / dry > 0.01, (dry, wet)


# ======================================================================
class TestItMovesAVerdict:
    """Not a decimal: which surfaces the check is willing to keep."""

    def test_a_limit_between_the_two_minima_splits_the_verdict(self):
        """``limit`` is an argument of ``m_alpha_check``, so this asks the
        real question — is there a threshold the correction moves the
        answer across? — without bending the model until its minimum
        happens to land near the default 0.2. Bending the geometry to hit
        a constant would be fitting the test to the answer.
        """
        from ogr_slip2d.checks import base_m_alphas, m_alpha_check
        res = _result()
        wet, dry = min(base_m_alphas(res)), min(_m_alphas(res, False))
        assert wet < dry
        limit = 0.5 * (wet + dry)
        passed, bad = m_alpha_check(res, limit=limit)
        assert not passed and bad, (limit, wet, dry)
        # and with the dry estimate the same limit would have accepted it
        assert all(v >= limit for v in _m_alphas(res, False))


# ======================================================================
class TestOnlyBothConditionsTogetherMoveIt:
    """The 2x2. It is what says the cause is the cause.

    It is also, executed, the reason the verification bank does not move:
    no problem in it has a sigma-dependent envelope AND ponded water, and
    either one alone changes nothing.
    """

    def test_the_attribution_table(self):
        rows = {}
        for power in (True, False):
            for ponded in (True, False):
                res = _result(power, ponded)
                wet = _m_alphas(res, True)
                dry = _m_alphas(res, False)
                rows[(power, ponded)] = max(
                    abs(a - b) for a, b in zip(wet, dry))
        # only the corner with both conditions moves
        assert rows[(True, True)] > 1e-3, rows
        for key in ((True, False), (False, True), (False, False)):
            assert rows[key] < 1e-6, (key, rows)

    def test_without_water_the_two_estimates_are_the_same_number(self):
        for power in (True, False):
            res = _result(power, ponded=False)
            for s in list(res.slices):
                assert _sigma(s, True) == _sigma(s, False)

    def test_with_water_but_a_straight_envelope_nothing_moves(self):
        """The control that separates "the water matters" from "the
        estimate matters": here the water is present and the stresses do
        differ, yet ``m_alpha`` does not, because a straight envelope has
        the same tangent everywhere."""
        from ogr_slip2d.checks import base_m_alphas
        res = _result(power=False, ponded=True)
        wet_slices = [s for s in list(res.slices)
                      if getattr(s, "water_weight", 0.0) > 0.0]
        assert wet_slices                       # the water IS there
        assert any(_sigma(s, True) > _sigma(s, False) for s in wet_slices)
        for g, d in zip(base_m_alphas(res), _m_alphas(res, False)):
            assert abs(g - d) < 1e-6 * max(1.0, abs(d))
