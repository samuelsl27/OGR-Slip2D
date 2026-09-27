# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.213 — a curved strength envelope is read at the normal stress each
method RESOLVES on the slice base, iterated to the fixed point, and not at
the Fellenius estimate (defect D84).

THE DEFECT. Every method linearises the envelope once per slice,
``tau ~ c + sigma'*tan(phi)``, and applies that straight line to the stress
its own equilibrium puts on the base. Until v0.1.213 the line was the
tangent at ``max(0, W*cos(a) - u*l)/l``. On a concave envelope a tangent
taken anywhere but at the resolved stress lies ABOVE the curve there, and one
taken at a clipped zero, on a curve through the origin, is ZERO. So the
method was not solving limit equilibrium with the material's envelope.
Measured as the strength the solver used against the envelope at the stress
of its own solution: +2.0 to +2.2 % in the sum on the five-slice surface of
Perry (1993), and -21 % on the critical surface of problem 41, where four
slices had none at all.

THE INVARIANTS.

1. SELF-CONSISTENCY, an identity. At the fixed point the straight line each
   slice resisted with gives the envelope's own value at the stress the
   solution put on that base, for the eight methods that iterate. With the
   switch ``ENVELOPE_AT_OWN_STRESS`` off it does not: the control.
2. The moment identity of v0.1.213's D81 with a curved envelope. Fed back
   into Bishop's own balance about its axis, the published normals and
   strengths return the factor of safety. On the composite surface of Baker
   (2003) example 2 with the power curve that closed to -4.5e-4 before,
   because the published strength and the one the solver used were read at
   different stresses; now it closes to 1e-10.
3. The one published case with a GIVEN surface (rule 1). Verification
   problem 40, Perry (1993), Janbu simplified on the five slices of its
   statement: the manual publishes 0.944. At the Fellenius point it came
   out +3.2 %; at the fixed point +0.5 %. Perry's own paper gives 0.98,
   which the Fellenius point is nearer to, but that paper is not available
   and how it read the envelope is not known, so it is recorded and not
   asserted.
4. Rule 7: the switch moves the number on problems 40 and 41, and leaves a
   Mohr-Coulomb model bit for bit where it was, because a straight envelope
   never enters the loop.
5. The checks judge where the solver read: the stress the m-alpha check
   linearises at is the one published in ``details["envelope_stress"]``.
6. The loop says what it did (``envelope_passes``, ``envelope_converged``),
   and a fixed point that is not reached makes the surface unconverged with
   its own reason instead of publishing a factor that is not the envelope's.

DISCRIMINATION against the v0.1.212 tree: see the changelog of v0.1.213.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

METHODS = ("bishop_simplified", "janbu_simplified", "janbu_corrected",
           "spencer", "gle_morgenstern_price", "lowe_karafiath",
           "corps_engineers_1", "corps_engineers_2")
#: The published factor of problem 40 (Janbu simplified, the given surface
#: in five slices), and Perry's own, recorded only.
PUBLISHED_40 = 0.944
PERRY_40 = 0.98

_CACHE: dict = {}


# ======================================================================
def _switch(on):
    """Set the switch; returns the old value to put back in ``finally``.

    Through ``getattr`` so that on a tree without the switch the cases fail
    on BEHAVIOUR rather than on a missing name: there setting it does
    nothing, which is exactly the old reading."""
    from ogr_slip2d.methods import base
    old = getattr(base, "ENVELOPE_AT_OWN_STRESS", None)
    base.ENVELOPE_AT_OWN_STRESS = on
    return old


def _restore(old):
    from ogr_slip2d.methods import base
    if old is None:
        vars(base).pop("ENVELOPE_AT_OWN_STRESS", None)
    else:
        base.ENVELOPE_AT_OWN_STRESS = old


def _solve(problem, method_id, own_stress=True, tolerance=None):
    key = (problem, method_id, own_stress, tolerance)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from test_zero_strength_slices_v1213 import (N_40, N_41, OUTLINE_40,
                                                 OUTLINE_41, SURFACE_40,
                                                 SURFACE_41, _power,
                                                 _project, _surface)
    if problem == "40":
        p = _project(OUTLINE_40, _power(a=2.0, b=0.7))
        surf, n = _surface(SURFACE_40), N_40
    else:
        p = _project(OUTLINE_41, _power(), ru=0.3)
        surf, n = _surface(SURFACE_41), N_41
    slices = slice_surface(p, surf, num_slices=n)
    m = method_registry()[method_id]()
    if tolerance is not None:
        m.tolerance = tolerance
    old = _switch(own_stress)
    try:
        res = m.compute_fos(p, surf, slices)
    finally:
        _restore(old)
    assert res.fos is not None, (problem, method_id, res.reason)
    _CACHE[key] = (p, res)
    return p, res


def _strength_gap(res):
    """(worst slice, whole surface): the strength the solver resisted with,
    against the envelope at the stress of its own solution, relative."""
    from ogr_slip2d.checks import base_effective_stresses
    from ogr_slip2d.methods.bishop import BishopSimplified
    env = res.details.get("envelope_stress")
    own = base_effective_stresses(res)
    worst, used_sum, true_sum = 0.0, 0.0, 0.0
    for i, s in enumerate(res.slices.slices):
        if env is not None and env[i] is not None:
            point = max(0.0, env[i])
        else:
            from ogr_slip2d.external_forces import slice_forces
            w = slice_forces(s).w_total
            point = max(0.0, w * math.cos(s.base_angle)
                        - s.pore_pressure * s.base_length) / s.base_length
        c, t = BishopSimplified._local_c_phi(s, s.material, point)
        sig = max(0.0, own[i])
        used = max(0.0, c + sig * t)
        true = s.material.strength.shear_strength(sig)
        worst = max(worst, abs(used - true) / max(1.0, true))
        used_sum += used * s.base_length
        true_sum += true * s.base_length
    return worst, (used_sum - true_sum) / true_sum


# ======================================================================
class TestSelfConsistency:

    def test_the_strength_used_is_the_envelope_at_the_resolved_stress(self):
        for problem in ("40", "41"):
            for mid in METHODS:
                _p, res = _solve(problem, mid)
                assert res.converged, (problem, mid, res.reason)
                worst, _whole = _strength_gap(res)
                assert worst < 1e-5, (problem, mid, worst)

    def test_the_control_at_the_fellenius_point_does_not(self):
        """Switch off: the gap the defect is, measured by the same yardstick.
        Perry's surface OVER-estimates, problem 41 UNDER-estimates."""
        _p, res = _solve("40", "bishop_simplified", own_stress=False)
        _w, whole = _strength_gap(res)
        assert whole > 0.015, whole
        _p, res = _solve("41", "bishop_simplified", own_stress=False)
        _w, whole = _strength_gap(res)
        assert whole < -0.15, whole


class TestTheMomentIdentityWithACurvedEnvelope:

    @staticmethod
    def _baker2(own_stress):
        """Baker (2003) example 2 with the power curve, on the circle its
        panel publishes, clipped by Composite Surfaces: the case of D81.
        Bishop's own iteration pinned far below the identity's tolerance."""
        key = ("baker2", own_stress)
        if key in _CACHE:
            return _CACHE[key]
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import PowerCurve
        from ogr_core.project import Project
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from test_janbu_base_forces_v1107 import (BAKER2, BAKER2_GAMMA,
                                                  BAKER2_OUTLINE,
                                                  BAKER2_SLICES)
        ext = Polyline(vertices=[Vertex(x, y) for x, y in BAKER2_OUTLINE],
                       closed=True)
        ext.ensure_ccw()
        p = Project("Baker 2003 example 2")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        clay = Material(name="clay", unit_weight=BAKER2_GAMMA,
                        sat_unit_weight=BAKER2_GAMMA,
                        strength=PowerCurve(a=1.107, b=0.86, c=0.0, d=0.0,
                                            waviness=0.0))
        p.materials = [clay]
        p.assign_material_at(*p.resolve_regions()[0].centroid(), clay.id)
        p.settings.search.composite_surfaces = True
        (cx, cy, r), _sigma, _fos = BAKER2["power_curve"]
        m = BishopSimplified()
        m.tolerance, m.max_iterations = 1e-12, 5000
        old = _switch(own_stress)
        try:
            res = GridSearch(method=m, num_slices=BAKER2_SLICES,
                             min_area=0.0).evaluate_circle(
                p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
        finally:
            _restore(old)
        assert res is not None and res.fos is not None
        _CACHE[key] = (p, res)
        return _CACHE[key]

    def _gap(self, own_stress):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.moment_balance import axis_for, moment_terms
        p, res = self._baker2(own_stress)
        sl = res.slices.slices
        w = [slice_forces(s).w_total for s in sl]
        t = moment_terms(axis_for(p, res.surface), sl, w,
                         res.base_shear_strength, res.base_normal_force)
        return (-t.shear / t.driving - res.fos) / res.fos

    def test_it_closes_at_the_fixed_point(self):
        assert abs(self._gap(True)) < 1e-9, self._gap(True)

    def test_it_did_not_at_the_fellenius_point(self):
        assert abs(self._gap(False)) > 1e-4, self._gap(False)


class TestThePublishedCase:

    def test_problem_40_at_the_five_slices_of_its_statement(self):
        _p, res = _solve("40", "janbu_simplified", tolerance=1e-4)
        assert abs(res.fos / PUBLISHED_40 - 1.0) < 0.01, res.fos

    def test_the_fellenius_point_misses_it(self):
        _p, res = _solve("40", "janbu_simplified", own_stress=False,
                         tolerance=1e-4)
        assert res.fos / PUBLISHED_40 - 1.0 > 0.03, res.fos


class TestTheSwitchMovesTheNumber:
    """Rule 7, both ways."""

    def test_it_moves_problems_40_and_41(self):
        for problem in ("40", "41"):
            for mid in METHODS:
                _p, on = _solve(problem, mid)
                _p, off = _solve(problem, mid, own_stress=False)
                assert abs(on.fos - off.fos) > 1e-3 * off.fos, (problem, mid)

    def test_a_straight_envelope_never_enters_the_loop(self):
        from ogr_slip2d.methods import method_registry
        from test_janbu_base_forces_v1107 import _slope
        p, circle, slices = _slope()
        for mid in METHODS:
            out = []
            for on in (True, False):
                old = _switch(on)
                try:
                    r = method_registry()[mid]().compute_fos(p, circle,
                                                             slices)
                finally:
                    _restore(old)
                out.append(r)
            assert out[0].fos == out[1].fos, mid
            assert "envelope_passes" not in out[0].details, mid


class TestTheChecksFollowTheSolver:

    def test_the_m_alpha_check_reads_the_published_stress(self):
        from ogr_slip2d import checks
        from ogr_slip2d.methods.bishop import BishopSimplified as B
        for mid in ("bishop_simplified", "spencer"):
            _p, res = _solve("41", mid)
            env = res.details["envelope_stress"]
            seen = []
            desc = B.__dict__["_local_c_phi"]
            real = desc.__func__

            def spy(s, material, sigma):
                seen.append(sigma)
                return real(s, material, sigma)

            B._local_c_phi = staticmethod(spy)
            try:
                checks.base_m_alphas(res)
            finally:
                B._local_c_phi = desc
            assert seen == [max(0.0, v) for v in env], mid


class TestTheLoopSaysWhatItDid:

    def test_it_converges_well_inside_its_budget(self):
        from ogr_slip2d.methods import base
        for problem in ("40", "41"):
            for mid in METHODS:
                _p, res = _solve(problem, mid)
                d = res.details
                assert d["envelope_converged"] is True, (problem, mid)
                assert 2 <= d["envelope_passes"] <= 10, (problem, mid, d)
                assert d["envelope_passes"] < base.ENVELOPE_MAX_PASSES

    def test_an_unreached_fixed_point_is_reported_not_published(self):
        from ogr_slip2d.methods import base
        from ogr_slip2d.methods.base import REASON_ENVELOPE_NOT_CONVERGED
        old_max = base.ENVELOPE_MAX_PASSES
        base.ENVELOPE_MAX_PASSES = 2
        try:
            _CACHE.pop(("41", "bishop_simplified", True, 1e-9), None)
            _p, res = _solve("41", "bishop_simplified", tolerance=1e-9)
        finally:
            base.ENVELOPE_MAX_PASSES = old_max
            _CACHE.pop(("41", "bishop_simplified", True, 1e-9), None)
        assert not res.converged and not res.is_valid
        assert res.reason == REASON_ENVELOPE_NOT_CONVERGED
        assert res.details["envelope_converged"] is False
