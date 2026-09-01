# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The BASE NORMAL of Spencer and GLE, tied to a published hand calculation.

WHAT INVARIANT THIS PROTECTS, and why the file next to it did not protect it.

``tests/test_gle_interslice_v1106.py`` pins the inter-slice force system with
four analytic identities, and its identity I3 is the strongest: the force
branch of Spencer at lambda IS the prescribed-inclination recursion of
USACE EM 1110-2-1902 equation C-19 driven at theta = atan(lambda). That
recursion is in turn validated term by term against the manual's own worked
example, whose Figure G-7b publishes the BASE NORMAL of its twelve slices
(``tests/test_modified_swedish_v198.py``).

But I3 asserts on ``force.fos`` and on nothing else. The per-slice normals
were never compared, so the chain stopped one link short of the published
column — and the two branches do not compute N with the same expression:

    interslice.solve_branch
        N = [W + X_R - X_L - (c'l - u*l*tanphi')*sin(a)/F] / m_a
    modified_swedish._base_forces
        N = (W + dZ_v + k0*sin(a)) / (cos(a) - a*sin(a))

Those differ in three signs, which is only harmless because the second one
marches in a mirrored frame. Nothing said so in numbers.

This file says it in numbers. It is the missing link, and it matters because
``base_normal_force`` is not merely reported: ``rapid_drawdown._stage1_state``
recovers the stage-1 consolidation state from it, and the effective stress
``N/l - u`` derived from it is what the verification bench compares against a
published maximum effective normal stress.

    I5  Spencer's per-slice N at lambda  IS  the prescribed-inclination
        recursion's per-slice N at theta = atan(lambda)

Written while measuring D38, which reported the maximum effective normal
stress of Spencer as 11-12 % high on one bench problem and named
``spencer._base_forces`` as the component at fault. The identity holds to the
fixed-point tolerance in every scenario below, on bases from -32 to +62
degrees, so that attribution is wrong: whatever that problem disagrees about,
it is not the arithmetic of the base normal.

``TestTheNormalIsAFunctionOfLambda`` is the rule-7 case. Without it the
identity above would be satisfied by a solver in which lambda did nothing to
N — which is exactly the shape of the defect v0.1.106 came from.

References:
    Spencer, E. (1967). "A method of analysis of the stability of embankments
        assuming parallel inter-slice forces." Geotechnique 17(1), 11-26.
    Fredlund, D.G. & Krahn, J. (1977). "Comparison of slope stability methods
        of analysis." Can. Geotech. J. 14(3), 429-439.
    USACE (2003). "Slope Stability", EM 1110-2-1902, Appendix C (equations
        C-19 to C-21) and Appendix G (Figure G-7b, the published base normal
        column).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# An IDENTITY, not an agreement: the two forms are the same equation, so the
# only thing that may separate them is the fixed point each one stopped at.
IDENTITY_TOL = 1e-6

# Tight enough that the stopping criterion cannot be mistaken for signal.
TIGHT = 1e-10

NUM_SLICES = 25

# The same lambdas as I3, which is where the roots of real slopes sit.
LAMBDAS = (0.0, 0.2, 0.45, 0.7)


# ======================================================================
# The model — ACADS problem 1(a). Repeated rather than imported, exactly as
# ``test_gle_interslice_v1106.py`` repeats it: the runner loads test modules
# independently and they cannot import one another.
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


def _circle(steep: bool = False):
    """The surface the identity is checked on.

    ``steep`` is the second one deliberately: it reaches -31.6 to +61.8
    degrees of base angle, where ``m_a = cos(a) + sin(a)*tanphi'/F`` and the
    ``cos(a - theta) - ...`` denominator of the marching form are furthest
    apart. An identity that only ever saw gentle bases would not be testing
    the frame the two expressions live in.
    """
    from ogr_slip2d.surface import SlipCircle
    if steep:
        return SlipCircle(centre_x=38.0, centre_y=45.0, radius=24.0)
    return SlipCircle(centre_x=33.0, centre_y=52.0, radius=28.0)


_CACHE: dict = {}


def _slices(kh: float = 0.0, with_water: bool = False, steep: bool = False):
    key = (kh, with_water, steep)
    if key not in _CACHE:
        from ogr_slip2d.slicer import slice_surface
        p = _acads_1a(kh, with_water)
        sl = slice_surface(p, _circle(steep), NUM_SLICES)
        assert sl is not None and len(sl.slices) == NUM_SLICES, (
            "the chosen circle must slice this slope cleanly")
        _CACHE[key] = (p, sl)
    return _CACHE[key]


def _system(kh: float = 0.0, with_water: bool = False, steep: bool = False):
    """The :class:`GLESystem` for the chosen circle, built as Spencer builds it."""
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.support_integration import resolve_support_terms

    p, sl = _slices(kh, with_water, steep)
    circle = _circle(steep)
    slide_sign = 1.0 if sum(
        s.weight * math.sin(s.base_angle) for s in sl) >= 0 else -1.0
    sup = resolve_support_terms(p, circle, sl, slide_sign)
    s_list = sl.slices
    return GLESystem(s_list, [1.0] * (len(s_list) + 1), kh, 0.0, slide_sign,
                     circle.radius, circle.centre_y, sup, None,
                     tolerance=TIGHT), slide_sign, sl


def _fixed_theta_method():
    """The shared marching recursion, driven at an inclination of our choice."""
    from ogr_slip2d.methods.modified_swedish import (
        PrescribedInclinationMethod, TOTAL_INTERSLICE)

    class _FixedTheta(PrescribedInclinationMethod):
        # Not registered: this exists to drive the shared recursion, not to
        # be a method a user can pick.
        METHOD_ID = "_test_fixed_theta_normal"
        DISPLAY_NAME = "fixed theta"
        theta_val = 0.0

        def _theta_angles(self, slices):
            return [self.theta_val] * len(list(slices))

    # TOTAL forces: the GLE system's E is the total inter-slice force, water
    # on the vertical faces included, which is what Fredlund and Krahn (1977)
    # write. The EFFECTIVE variant separates it out and the two would no
    # longer be the same system.
    return _FixedTheta(interslice_forces=TOTAL_INTERSLICE)


def _paired_normals(lam, system, slide_sign, sl, kh):
    """``(spencer, marching)`` base-normal columns in SLICE order, or ``None``.

    Both branches converge independently; ``None`` means one of them left the
    admissible region at this lambda, which is a property of the iteration and
    not of the identity. The caller refuses an empty comparison.
    """
    force, _moment = system.states(lam)
    if force is None or not force.converged:
        return None
    method = _fixed_theta_method()
    # theta lives in the TRUE frame, where the marching engine mirrors it by
    # its own orientation, so it takes the slide sign.
    method.theta_val = math.atan(lam) * slide_sign
    method.tolerance = TIGHT
    fos, converged, _iters, ctx = method._force_balance(
        sl, kh, 0.0, slide_sign)
    if not (converged and math.isfinite(fos)) or ctx is None:
        return None
    marching, _shears, _strengths = method._base_forces(list(sl), ctx, fos)
    if not marching:
        return None
    # ``solve_branch`` works in marching order; the marching method never
    # reorders its slices, it mirrors the angles instead.
    return system.to_slice_order(force.normals), marching


# ======================================================================
class TestI5SpencerBaseNormalIsTheMarchingRecursion:
    """Spencer's assumption IS the prescribed-inclination assumption with the
    angle solved for instead of given — and that applies to every quantity the
    two solve for, not only to the factor of safety.

    So at any lambda the per-slice base normal of the force branch must equal
    the one the marching recursion reports at theta = atan(lambda), which is
    the column EM 1110-2-1902 Figure G-7b publishes.
    """

    def _check(self, kh: float, with_water: bool, steep: bool = False):
        system, slide_sign, sl = _system(kh, with_water, steep)
        checked = 0
        for lam in LAMBDAS:
            pair = _paired_normals(lam, system, slide_sign, sl, kh)
            if pair is None:
                continue
            spencer, marching = pair
            assert len(spencer) == len(marching) == NUM_SLICES, (
                f"lambda={lam}: {len(spencer)} vs {len(marching)} normals")
            scale = max(abs(v) for v in marching)
            worst = max(abs(a - b) for a, b in zip(spencer, marching))
            assert worst / scale < IDENTITY_TOL, (
                f"kh={kh} water={with_water} steep={steep} lambda={lam}: "
                f"worst |dN| = {worst!r} on a peak of {scale!r}\n"
                f"  spencer  = {[round(v, 4) for v in spencer]}\n"
                f"  marching = {[round(v, 4) for v in marching]}")
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

    def test_on_a_steeply_inclined_base(self):
        self._check(0.0, False, steep=True)


# ======================================================================
class TestTheNormalIsAFunctionOfLambda:
    """Rule 7, applied to the base normal.

    Every assertion above would also hold for a solver whose N ignored the
    inter-slice shear entirely — both branches would simply be wrong in the
    same way, which is the shape of the v0.1.105 defect. So the inter-slice
    shear has to be shown MOVING the normal, and moving it the way the
    mechanics says: lambda tilts the inter-slice forces, each slice hangs
    partly off its neighbours, and the peak base normal drops.
    """

    def test_lambda_moves_the_normal(self):
        system, slide_sign, sl = _system(0.0, False)
        peaks = {}
        for lam in LAMBDAS:
            pair = _paired_normals(lam, system, slide_sign, sl, 0.0)
            if pair is not None:
                peaks[lam] = max(pair[0])
        assert len(peaks) >= 3, f"not enough converged lambdas: {peaks}"
        lo, hi = min(peaks), max(peaks)
        drop = (peaks[lo] - peaks[hi]) / peaks[lo]
        # Measured -5.16 % on this circle between lambda 0 and 0.7. The bar is
        # set well below that: this asserts the term is WIRED, not its size.
        assert drop > 0.01, (
            f"inter-slice shear moves the peak base normal by only "
            f"{100 * drop:.3f} % between lambda {lo} and {hi}: {peaks}")

    def test_at_zero_lambda_the_normal_is_the_no_shear_one(self):
        """lambda = 0 is horizontal inter-slice forces, so X_R - X_L vanishes
        and the normal must be the one Bishop and Janbu compute with no
        inter-slice shear at all (Fredlund and Krahn 1977)."""
        from ogr_slip2d.methods.bishop import base_forces_no_interslice_shear

        system, slide_sign, sl = _system(0.0, False)
        pair = _paired_normals(0.0, system, slide_sign, sl, 0.0)
        assert pair is not None, "lambda = 0 must converge"
        spencer, _marching = pair
        force, _moment = system.states(0.0)
        plain, _s, _t = base_forces_no_interslice_shear(
            list(sl), 0.0, 0.0, slide_sign, force.fos)
        scale = max(abs(v) for v in plain)
        worst = max(abs(a - b) for a, b in zip(spencer, plain))
        assert worst / scale < IDENTITY_TOL, (
            f"at lambda = 0 the normal is not the no-shear one: worst "
            f"|dN| = {worst!r} on a peak of {scale!r}")
