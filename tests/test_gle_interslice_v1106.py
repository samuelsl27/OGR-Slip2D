# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The inter-slice force system of Spencer and GLE, pinned by ANALYTIC IDENTITIES.

WHAT INVARIANT THIS PROTECTS, and why nothing weaker would do.

For its first eighty versions this program's Spencer and GLE returned the
Bishop factor of safety, on a circle, to six figures. Not approximately: the
moment branch contained no lambda anywhere, so F_m(lambda) was a constant, and
the root F_f = F_m therefore landed on Bishop whatever lambda did. Two more
defects sat on top of it. All three are described, with the measurements, in
``docs/audits/spencer_gle_interslice_v179.md``.

Nothing in that failure was visible from a factor of safety, because Bishop is
a perfectly plausible answer. What makes it visible is that the General Limit
Equilibrium system has EXACT anchors — cases where its answer must equal
another method's, to every figure — and this file is those anchors.

    I1  F_f(lambda = 0)  IS  Janbu simplified
    I2  F_m(lambda = 0)  IS  Bishop simplified          (circular surface)
    I3  F_f(lambda)      IS  the Modified Swedish recursion at theta = atan
                             lambda, for EVERY lambda
    I4  GLE with f(x) constant  IS  Spencer

I1 and I2 are Fredlund and Krahn (1977): at lambda = 0 the inter-slice forces
are horizontal, there is no inter-slice shear, and each branch degenerates
into a method this program already has. They are not approximations of each
other — they are the same equation, so the tolerance here is 1e-6 relative and
not a percentage.

I3 is the strongest of the four. Spencer's assumption is a CONSTANT
inter-slice inclination, which is exactly what the Modified Swedish method
prescribes; the difference is only that Spencer solves for it and the Corps
methods are told it. So the force branch of Spencer at lambda must reproduce
``PrescribedInclinationMethod._march`` at theta = atan(lambda) — and that
recursion is validated term by term against the worked example of USACE
EM 1110-2-1902, Appendix G, whose published inter-slice force and base normal
columns it reproduces (``tests/test_modified_swedish_v198.py``). I3 therefore
anchors Spencer to a case solved by hand, slice by slice, in a published
manual.

I4 is what stops the two methods drifting apart: they share one solver, and
this says so in numbers.

``TestTheMethodIsAMethod`` is the rule-7 case: it shows that lambda MOVES the
answer. Without it every identity above could be satisfied by the broken code
of v0.1.105, which agreed with Bishop precisely because lambda did nothing.

References:
    Fredlund, D.G. & Krahn, J. (1977). "Comparison of slope stability methods
        of analysis." Can. Geotech. J. 14(3), 429-439.
    Spencer, E. (1967). "A method of analysis of the stability of embankments
        assuming parallel inter-slice forces." Geotechnique 17(1), 11-26.
    USACE (2003). "Slope Stability", EM 1110-2-1902, Appendices C and G.
    Ching, R.K.H. & Fredlund, D.G. (1983). "Some difficulties associated with
        the limit equilibrium method of slices." Can. Geotech. J. 20(4),
        661-672 — on the spurious roots that ``TestSpuriousRoots`` covers.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# Relative agreement demanded of an IDENTITY. Two forms of the same equation
# differ only by the fixed-point tolerance below, never by "a bit".
IDENTITY_TOL = 1e-6

# Tight enough that the stopping criterion cannot be mistaken for signal;
# see ``tests/test_convergence_tolerance_v198.py``.
TIGHT = 1e-10

NUM_SLICES = 25

# lambda values the identities are checked at. Positive and modest, which is
# where the roots of real slopes actually sit once the inter-slice forces
# reach the base normal (0.39 to 0.63 on the reference cases, against 0.68 to
# 3.21 before v0.1.106).
LAMBDAS = (0.0, 0.2, 0.45, 0.7)


# ======================================================================
# The model — ACADS problem 1(a), geometry and properties from the TEXT of
# the statement, not from any figure. Same model as
# ``tests/test_acads_validation_v178.py``; repeated rather than imported
# because the runner loads test modules independently.
# ======================================================================
def _acads_1a(kh: float = 0.0, with_water: bool = False):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(20, 20), Vertex(70, 20), Vertex(70, 35),
        Vertex(50, 35), Vertex(30, 25), Vertex(20, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ACADS 1(a)")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil = Material(name="Soil", unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=3.0, friction_angle=19.6))
    p.materials = [soil]

    if with_water:
        # A piezometric line well inside the mass, so u is non-zero over most
        # of the base. Its only job here is to make the identities carry pore
        # pressure: the water path is validated elsewhere.
        from ogr_core.materials import PorePressureType
        piezo = Boundary(polyline=Polyline(
            vertices=[Vertex(20, 23), Vertex(45, 27), Vertex(70, 31)],
            closed=False), btype=BoundaryType.PIEZOMETRIC)
        p.add_boundary(piezo)
        soil.pore_pressure = PorePressureType.PIEZO_LINE
        soil.water_surface_id = piezo.id
        soil.hu = 1.0

    if kh:
        p.seismic.enabled = True
        p.seismic.kh = kh
        p.seismic.kv = 0.0
    return p


def _circle():
    """A circle that cuts this slope from crest to toe.

    Chosen by hand rather than taken from a figure: an identity holds on ANY
    admissible surface, so a published critical circle would add a dependency
    and no coverage.
    """
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=33.0, centre_y=52.0, radius=28.0)


_CACHE: dict = {}


def _slices(kh: float = 0.0, with_water: bool = False):
    key = (kh, with_water)
    if key not in _CACHE:
        from ogr_slip2d.slicer import slice_surface
        p = _acads_1a(kh, with_water)
        sl = slice_surface(p, _circle(), NUM_SLICES)
        assert sl is not None and len(sl.slices) == NUM_SLICES, (
            "the chosen circle must slice this slope cleanly")
        _CACHE[key] = (p, sl)
    return _CACHE[key]


def _system(kh: float = 0.0, with_water: bool = False, shape=None):
    """The :class:`GLESystem` for the chosen circle, built as the methods do."""
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.support_integration import resolve_support_terms

    p, sl = _slices(kh, with_water)
    circle = _circle()
    slide_sign = 1.0 if sum(
        s.weight * math.sin(s.base_angle) for s in sl) >= 0 else -1.0
    sup = resolve_support_terms(p, circle, sl, slide_sign)
    s_list = sl.slices
    if shape is None:
        shape = [1.0] * (len(s_list) + 1)
    return GLESystem(s_list, shape, kh, 0.0, slide_sign,
                     circle.radius, circle.centre_y, sup, None,
                     tolerance=TIGHT), slide_sign, sl


def _fos(method_id: str, kh: float = 0.0, with_water: bool = False) -> float:
    """The factor of safety of another method on the very same circle."""
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.search import GridSearch

    p, _ = _slices(kh, with_water)
    method = method_registry()[method_id](tolerance=TIGHT)
    res = GridSearch(method=method, num_slices=NUM_SLICES,
                     min_area=0.0).evaluate_circle(p, _circle())
    assert res is not None and math.isfinite(res.fos), method_id
    return float(res.fos)


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12)


# ======================================================================
class TestI1ForceBranchAtZeroLambdaIsJanbuSimplified:
    """Fredlund and Krahn (1977): with horizontal inter-slice forces and no
    inter-slice shear, the force-equilibrium branch IS Janbu simplified.

    This is the identity that measured 0.497 to 0.794 before v0.1.106, because
    the force numerator summed ``S*cos(a)`` where the horizontal equilibrium
    of the whole mass gives ``S*sec(a)``.
    """

    def _check(self, kh: float, with_water: bool):
        system, _, _ = _system(kh, with_water)
        force, _ = system.states(0.0)
        assert force is not None, "the force branch must solve at lambda = 0"
        janbu = _fos("janbu_simplified", kh, with_water)
        assert _rel(force.fos, janbu) < IDENTITY_TOL, (
            f"kh={kh} water={with_water}: F_f(0)={force.fos!r} "
            f"janbu_simplified={janbu!r}")

    def test_dry(self):
        self._check(0.0, False)

    def test_with_pore_pressure(self):
        self._check(0.0, True)

    def test_with_earthquake(self):
        """The seismic term enters the recursion as an external horizontal
        load, and its SIGN is what this case pins: applied the wrong way it
        holds the mass back instead of driving it, and the identity breaks."""
        self._check(0.15, False)


# ======================================================================
class TestI2MomentBranchAtZeroLambdaIsBishop:
    """Fredlund and Krahn (1977): on a circle, with no inter-slice shear, the
    moment-equilibrium branch IS Bishop simplified.

    This is the identity that measured 0.961 to 0.979 before v0.1.106 — and
    the reason was NOT that ``m_alpha`` lacks lambda, which is a correct
    expression at lambda = 0 where there is no inter-slice shear at all. It
    was that both branches were driven by one shared iterate
    ``F = (F_f + F_m)/2``, so neither was its own fixed point.
    """

    def _check(self, kh: float, with_water: bool):
        system, _, _ = _system(kh, with_water)
        _, moment = system.states(0.0)
        assert moment is not None, "the moment branch must solve at lambda = 0"
        bishop = _fos("bishop_simplified", kh, with_water)
        assert _rel(moment.fos, bishop) < IDENTITY_TOL, (
            f"kh={kh} water={with_water}: F_m(0)={moment.fos!r} "
            f"bishop_simplified={bishop!r}")

    def test_dry(self):
        self._check(0.0, False)

    def test_with_pore_pressure(self):
        self._check(0.0, True)

    def test_with_earthquake(self):
        self._check(0.15, False)


# ======================================================================
class TestI3ForceBranchIsTheModifiedSwedishRecursion:
    """Spencer's assumption IS the Modified Swedish assumption with the
    inclination solved for instead of prescribed.

    So for any lambda, the force branch must equal the recursion of USACE
    EM 1110-2-1902 equation C-19 driven at theta = atan(lambda) — the same
    recursion that reproduces the manual's own worked example slice by slice.
    That makes this the only anchor in the file that reaches a case solved by
    hand in a published document.

    Sign note: theta lives in the TRUE frame, where the Corps engine mirrors
    it by its own marching orientation, so it takes the slide sign.
    """

    def _fixed_theta_method(self):
        from ogr_slip2d.methods.modified_swedish import (
            PrescribedInclinationMethod, TOTAL_INTERSLICE)

        class _FixedTheta(PrescribedInclinationMethod):
            # Not registered: this exists to drive the shared recursion at an
            # inclination of our choosing, not to be a method a user can pick.
            METHOD_ID = "_test_fixed_theta"
            DISPLAY_NAME = "fixed theta"
            theta_val = 0.0

            def _theta_angles(self, slices):
                return [self.theta_val] * len(list(slices))

        # TOTAL forces: the GLE system's E is the total inter-slice force,
        # water on the vertical faces included, which is what Fredlund and
        # Krahn (1977) write. The EFFECTIVE variant would separate it out and
        # the two would no longer be the same system.
        return _FixedTheta(interslice_forces=TOTAL_INTERSLICE)

    def _check(self, kh: float, with_water: bool):
        system, slide_sign, sl = _system(kh, with_water)
        checked = 0
        for lam in LAMBDAS:
            force, _ = system.states(lam)
            if force is None or not force.converged:
                # The fixed point on F can leave the admissible region at a
                # large lambda; that is a property of the iteration, not of
                # the identity, so such a lambda is skipped rather than
                # asserted on. The case below refuses an empty comparison.
                continue
            method = self._fixed_theta_method()
            method.theta_val = math.atan(lam) * slide_sign
            method.tolerance = TIGHT
            fos, converged, _iters, _ctx = method._force_balance(
                sl, kh, 0.0, slide_sign)
            if not (converged and math.isfinite(fos)):
                continue
            assert _rel(force.fos, fos) < IDENTITY_TOL, (
                f"kh={kh} water={with_water} lambda={lam}: "
                f"F_f={force.fos!r} Modified Swedish={fos!r}")
            checked += 1
        assert checked >= 3, (
            f"only {checked} lambda compared; the identity would pass "
            f"vacuously")

    def test_dry(self):
        self._check(0.0, False)

    def test_with_pore_pressure(self):
        self._check(0.0, True)

    def test_with_earthquake(self):
        self._check(0.15, False)


# ======================================================================
class TestI4GLEWithAConstantShapeIsSpencer:
    """f(x) = 1 everywhere is Spencer's assumption, so the two must agree
    exactly — not to a tolerance, to the same arithmetic."""

    def test_same_factor_of_safety(self):
        from ogr_slip2d.methods.gle import GLEMorgensternPrice, constant
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        out = {}
        for name, method in (
                ("spencer", Spencer(tolerance=TIGHT)),
                ("gle", GLEMorgensternPrice(tolerance=TIGHT,
                                            interslice_func=constant))):
            res = GridSearch(method=method, num_slices=NUM_SLICES,
                             min_area=0.0).evaluate_circle(p, _circle())
            assert res is not None and math.isfinite(res.fos), name
            out[name] = res
        assert _rel(out["spencer"].fos, out["gle"].fos) < IDENTITY_TOL, out
        assert abs(out["spencer"].details["lambda"]
                   - out["gle"].details["lambda"]) < 1e-9, out

    def test_the_half_sine_is_a_different_answer(self):
        """And the default shape must NOT give the same number, or the shape
        function would be a setting that does nothing (rule 7)."""
        from ogr_slip2d.methods.gle import GLEMorgensternPrice, constant
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        got = {}
        for name, f in (("constant", constant), ("half_sine", None)):
            kw = {"interslice_func": f} if f is not None else {}
            res = GridSearch(
                method=GLEMorgensternPrice(tolerance=TIGHT, **kw),
                num_slices=NUM_SLICES, min_area=0.0
            ).evaluate_circle(p, _circle())
            got[name] = float(res.fos)
        assert _rel(got["constant"], got["half_sine"]) > 1e-5, got


# ======================================================================
class TestTheMethodIsAMethod:
    """Rule 7, applied to lambda itself.

    Every identity above is satisfied by a solver in which lambda does
    nothing, because all four are stated at lambda = 0 or compare two force
    branches. These are the cases that would have failed in v0.1.105.
    """

    def test_the_moment_branch_depends_on_lambda(self):
        """The whole defect, in one assertion. F_m(lambda) was a CONSTANT: the
        base normal omitted the inter-slice shear difference, so lambda never
        reached the moment equation and the root F_f = F_m could not land
        anywhere but Bishop."""
        system, _, _ = _system()
        _, m0 = system.states(0.0)
        _, m1 = system.states(0.5)
        assert m0 is not None and m1 is not None
        assert _rel(m1.fos, m0.fos) > 1e-3, (m0.fos, m1.fos)

    def test_spencer_separates_from_bishop(self):
        """And the separation must survive into the published number."""
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        res = GridSearch(method=Spencer(tolerance=TIGHT),
                         num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        bishop = _fos("bishop_simplified")
        assert res is not None and res.converged, res
        assert _rel(res.fos, bishop) > 1e-4, (res.fos, bishop)

    def test_the_base_normal_carries_the_interslice_shear(self):
        """N must MOVE with lambda, which is the mechanism underneath both
        cases above."""
        system, _, _ = _system()
        f0, _ = system.states(0.0)
        f1, _ = system.states(0.5)
        assert f0 is not None and f1 is not None
        moved = max(_rel(b, a) for a, b in zip(f0.normals, f1.normals))
        assert moved > 1e-3, moved


# ======================================================================
class TestSpuriousRoots:
    """``F_f(lambda) - F_m(lambda)`` has more than one zero, and only one of
    them is a solution.

    Soil transmits no tension across a vertical face, so a crossing whose
    inter-slice thrust is net tensile is arithmetic without a stress state
    behind it. Ching and Fredlund (1983) is the reference for rejecting them.

    This could not arise before v0.1.106 for a plain reason: the solver never
    formed E at all, and F_m did not depend on lambda, so the difference was
    monotone by construction.
    """

    def test_a_net_tensile_thrust_is_rejected(self):
        from ogr_slip2d.interslice import BranchState, thrust_is_admissible

        compressive = BranchState(
            fos=1.0, converged=True, passes=1, normals=[], resisting=[],
            boundary_e=[0.0, 10.0, 30.0, 12.0, 0.0], boundary_x=[])
        tensile = BranchState(
            fos=1.0, converged=True, passes=1, normals=[], resisting=[],
            boundary_e=[0.0, -10.0, -30.0, 5.0, 0.0], boundary_x=[])
        assert thrust_is_admissible(compressive)
        assert not thrust_is_admissible(tensile)

    def test_the_ends_do_not_decide_it(self):
        """The two free ends carry no inter-slice force at all, so whatever
        the recursion leaves there must not enter the test."""
        from ogr_slip2d.interslice import BranchState, thrust_is_admissible

        state = BranchState(
            fos=1.0, converged=True, passes=1, normals=[], resisting=[],
            boundary_e=[-1e9, 10.0, 30.0, 12.0, -1e9], boundary_x=[])
        assert thrust_is_admissible(state)

    def test_the_solved_surface_is_in_compression(self):
        """The lambda the method actually returns must be an admissible one."""
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        res = GridSearch(method=Spencer(tolerance=TIGHT),
                         num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        interior = res.details["interslice_e"][1:-1]
        assert interior, res.details
        assert math.fsum(interior) > 0.0, interior


# ======================================================================
class TestWhatTheMethodsNowReport:
    """Spencer and GLE fill the per-slice columns for the first time.

    Not cosmetic: ``rapid_drawdown._stage1_state`` reads ``base_normal_force`` to
    recover the stage-1 consolidation state, and an empty list made the
    two-stage drawdown apply undrained strength to ZERO slices — the same
    trap that ``modified_swedish`` documents for the Corps methods in v0.1.98.
    """

    def test_both_methods_publish_the_per_slice_columns(self):
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        for method in (Spencer(tolerance=TIGHT),
                       GLEMorgensternPrice(tolerance=TIGHT)):
            res = GridSearch(method=method, num_slices=NUM_SLICES,
                             min_area=0.0).evaluate_circle(p, _circle())
            for name in ("base_normal_force", "base_shear_force",
                         "base_shear_strength"):
                col = getattr(res, name)
                assert len(col) == NUM_SLICES, (method.METHOD_ID, name, col)
                assert all(math.isfinite(v) for v in col), (
                    method.METHOD_ID, name)

    def test_the_interslice_forces_are_reported_in_slice_order(self):
        """n+1 boundary values, both ends free, and the peak inside — a thrust
        that grows from the toe and returns to zero at the crest."""
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        res = GridSearch(method=Spencer(tolerance=TIGHT),
                         num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        e = res.details["interslice_e"]
        x = res.details["interslice_x"]
        assert len(e) == NUM_SLICES + 1, len(e)
        assert len(x) == NUM_SLICES + 1, len(x)
        assert x[0] == 0.0 and x[-1] == 0.0, (x[0], x[-1])
        peak = max(range(len(e)), key=lambda i: e[i])
        assert 0 < peak < len(e) - 1, (peak, e)


# ======================================================================
class TestI3AlsoHoldsWithReinforcement:
    """The support sign inside the recursion, pinned by the same identity.

    ``I3`` above covers pore pressure and an earthquake but NOT a support, and
    that gap cost a diagnosis: on verification problem 85 the two methods
    returned NaN, and the first hypothesis was that ``h_drive`` carried the
    support the wrong way round. Driving the Corps recursion at
    ``theta = atan(lambda)`` WITH the same support answers it in one line —
    the two agree to 1e-9, so the sign is right and the NaN was the thrust
    criterion (see ``TestTheThrustCriterionIsAPreference``).

    The support enters both engines as a cartesian external force, so this is
    a like-for-like comparison. Bishop is deliberately NOT compared here: it
    splits a support into a tangential and a normal part instead, which is a
    different modelling choice rather than a different arithmetic — which is
    also why ``I2`` is not asserted for the reinforced case.
    """

    @staticmethod
    def project_with_nail():
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SoilNail, SupportInstance)

        ext = Polyline(vertices=[
            Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, 10.0),
            Vertex(40.0, 10.0), Vertex(20.0, 0.0), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("nail")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="S", unit_weight=18,
                                strength=MohrCoulomb(cohesion=8,
                                                     friction_angle=20))]
        p.support_types = [SoilNail(tensile_capacity=30, plate_capacity=20,
                                    bond_strength=8, out_of_plane_spacing=3.0)]
        p.supports = [SupportInstance(
            # The tail has to sit OUTSIDE the circle or the nail never
            # crosses the slip surface and carries no force at all — which is
            # how the first draft of this fixture "passed" nothing.
            type_id="soil_nail", head=Vertex(28.0, 4.0),
            tail=Vertex(52.0, 4.0),
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
        return p

    CIRCLE = dict(centre_x=30.0, centre_y=22.0, radius=24.0)

    def test_the_force_branch_matches_the_corps_recursion(self):
        from ogr_slip2d.interslice import GLESystem
        from ogr_slip2d.methods.modified_swedish import (
            PrescribedInclinationMethod, TOTAL_INTERSLICE)
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        from ogr_slip2d.surface import SlipCircle

        class _FixedTheta(PrescribedInclinationMethod):
            METHOD_ID = "_test_fixed_theta_sup"
            DISPLAY_NAME = "fixed theta"
            theta_val = 0.0

            def _theta_angles(self, slices):
                return [self.theta_val] * len(list(slices))

        p = self.project_with_nail()
        circle = SlipCircle(**self.CIRCLE)
        sl = slice_surface(p, circle, NUM_SLICES)
        assert sl is not None and len(sl.slices) == NUM_SLICES
        slide_sign = 1.0 if sum(
            s.weight * math.sin(s.base_angle) for s in sl) >= 0 else -1.0
        sup = resolve_support_terms(p, circle, sl, slide_sign)
        assert sup.present, "the fixture must actually place a support"

        system = GLESystem(sl.slices, [1.0] * (len(sl.slices) + 1), 0.0, 0.0,
                           slide_sign, circle.radius, circle.centre_y, sup,
                           None, tolerance=TIGHT)
        checked = 0
        for lam in LAMBDAS:
            force, _ = system.states(lam)
            if force is None or not force.converged:
                continue
            method = _FixedTheta(interslice_forces=TOTAL_INTERSLICE)
            method.theta_val = math.atan(lam) * slide_sign
            method.tolerance = TIGHT
            fos, converged, _i, _c = method._force_balance(
                sl, 0.0, 0.0, slide_sign, None, sup)
            if not (converged and math.isfinite(fos)):
                continue
            assert _rel(force.fos, fos) < IDENTITY_TOL, (
                "lambda=%r: F_f=%r Modified Swedish=%r" % (lam, force.fos, fos))
            checked += 1
        assert checked >= 2, checked

    def test_the_support_raises_the_factor_of_safety(self):
        """Rule 7 on the support itself, in this solver. A reinforcement that
        does not move the number would be worse than no reinforcement."""
        import copy

        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle

        p = self.project_with_nail()
        bare = copy.deepcopy(p)
        bare.supports = []
        out = []
        for proj in (bare, p):
            res = GridSearch(method=Spencer(tolerance=TIGHT),
                             num_slices=NUM_SLICES, min_area=0.0
                             ).evaluate_circle(proj, SlipCircle(**self.CIRCLE))
            assert res is not None and math.isfinite(res.fos), proj.supports
            out.append(float(res.fos))
        assert out[1] > out[0] * 1.001, out


# ======================================================================
class TestTheThrustCriterionIsAPreference:
    """It rejects a spurious root; it does not veto a surface.

    A slope can have no admissible lambda at all — verification problem 85
    puts 9000 kN/m of anchorage into one slope and every lambda leaves the
    soil faces in net tension. Whether that tension is real or an artefact of
    concentrating the reinforcement is not something v0.1.106 answers, and
    turning the answer into a NaN without answering it loses coverage for
    nothing: v0.1.105 returned 1.568 there, against a published 1.575.

    So the outer search samples again with the criterion off when the strict
    pass found nothing, and SAYS SO.
    """

    def test_a_net_tensile_state_is_still_recognised_as_such(self):
        """The criterion itself has not been weakened — only its authority."""
        from ogr_slip2d.interslice import BranchState, thrust_is_admissible

        tensile = BranchState(
            fos=1.0, converged=True, passes=1, normals=[], resisting=[],
            boundary_e=[0.0, -5.0, -9.0, -4.0, 0.0], boundary_x=[])
        assert not thrust_is_admissible(tensile)

    def test_the_strict_pass_is_what_runs_first(self):
        """A system starts strict. If it did not, the spurious roots of
        ``TestSpuriousRoots`` would come back without anything failing."""
        system, _, _ = _system()
        assert system.strict is True

    def test_a_solved_surface_reports_whether_its_thrust_is_admissible(self):
        """So a relaxed answer can never be mistaken for a clean one."""
        from ogr_slip2d.methods.spencer import Spencer
        from ogr_slip2d.search import GridSearch

        p, _ = _slices()
        res = GridSearch(method=Spencer(tolerance=TIGHT),
                         num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        assert res.details.get("thrust_admissible") is True, res.details
        assert not res.error_message, res.error_message
