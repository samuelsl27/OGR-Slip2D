# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.215 — the back analysis of support force reads a curved strength
envelope where the method reads it (defect D204).

THE IDENTITY (rule 1: consistency with a validated path). The back analysis
holds the factor of safety at a target and solves for the horizontal
support force in closed form. At the factor the method itself gives the
surface with NO support, that force is zero: the resisting and driving sums
of the back analysis are the method's own sums. v0.1.202 protected it for
Mohr-Coulomb (``test_back_analysis_v140``, ``test_block4_v1202``).

WHAT BROKE IT. Since v0.1.213 (D84) the methods read an envelope whose
tangent depends on the stress at the stress they RESOLVE, iterated to the
fixed point; the back analysis kept reading it at the Fellenius estimate
``max(0, W cos a - u l)/l``. With a power curve the two sums parted: on
the surface below, with Janbu, the passive force before the clip at zero
came out +2096 kN/m (46 % of the driving sum) where it is zero; on the
archived critical surface of verification problem 41, -107.5 kN/m, the
unsafe side. ``required_force`` clips negatives to zero, which hides the
defect exactly at the identity, so these cases read the UNCLIPPED force
``(F*D - R)/arm`` from ``_sums_at_fixed_fos``.

THE FIX, AND WHY IT IS EXACT. With the inter-slice shear neglected, the
normal of a slice in Bishop and Janbu comes from its VERTICAL equilibrium,
into which a horizontal support force does not enter. So with F fixed the
stress of each slice depends only on that slice's own (c, tan phi), and the
fixed point sigma' -> (c, tan phi) -> N(F) -> sigma' closes slice by slice.
It must land on the point the method settled on: pinned below against the
method's published ``details["envelope_stress"]``.

JANBU CORRECTED is found at the CORRECTED factor and summed at F/f0: its
solver iterates on the uncorrected factor, but its fixed point reads its
own stress from the published result, whose factor is the corrected one.
The case that shows the point at F/f0 missing is the proof that the choice
matters, not a preference.

BISHOP keeps a residual that is NOT this defect: its back-analysis driving
sum takes ``sin a`` where the solver takes the weight's own moment arm
(``weight_arm_ratio``), reported as a defect of its own. The Bishop case
subtracts that gap explicitly, computed from the slices, so what remains is
the envelope alone.

CONTROLS: with ``methods.base.ENVELOPE_AT_OWN_STRESS`` off the identity
holds too (the old reading on both sides); with Mohr-Coulomb the sums are
bit for bit those of the old code; and the switch moves the sums of a
curved envelope (rule 7).

TOLERANCE: 1e-9 of the total weight, with the methods solved to a factor
tolerance of 1e-12. At their default tolerance on F (1e-3) the identity is
only as good as the solver's F, which left -0.18 kN/m (1e-5 of the weight)
on the Janbu case with the fix in place and did not separate the fix from
that noise; solved tightly, every case leaves 1e-11 to 3e-9 kN/m, on and
off. The defect is 0.12 of the weight.

DISCRIMINATION, measured on the v0.1.214 tree: 7 of the 11 cases fail, 5
on behaviour (+2096.44 kN/m for Janbu, -73.82 for Bishop net of its arm
gap, the switch not reaching the sums, no refusal) and 2 on the new name
``_own_stress``. The four that pass there are the two guards on the
witness and the two controls, which v0.1.214 already satisfied.
"""
from __future__ import annotations

import math

JANBUS = ("janbu_simplified", "janbu_corrected")
THREE = ("bishop_simplified",) + JANBUS

#: Verification problem 41 (Jiang, Baker & Yamagami 2003), as
#: ``test_zero_strength_slices_v1213`` builds it: outline, the critical
#: Path Search surface the bench archives, tau = 1.4*sigma'^0.8, ru = 0.3.
OUTLINE_41 = [(0, 0), (93, 0), (93, 10), (85, 10), (5, 30), (0, 30)]
SURFACE_41 = [(13.7554, 27.8112), (16.6576, 22.8278), (19.6772, 17.6429),
              (22.6967, 12.4581), (25.7162, 7.2733), (30.6765, 3.8975),
              (36.1935, 1.539), (42.1071, 0.5244), (48.1009, 0.251),
              (54.0447, 1.0699), (59.9575, 2.0891), (65.6032, 4.1204),
              (71.1937, 6.299), (76.7842, 8.4777), (82.3747, 10.6563)]
#: A circle on the same slope, for Bishop, whose back analysis is written
#: in the circular form of the method.
CIRCLE_41 = (54.9862, 46.9183, 45.443)
N_SLICES = 30
RU = 0.3
TOL_W = 1e-9
#: The methods' tolerance on F for these cases (their default is 1e-3).
SOLVER_TOL = 1e-12

_CACHE: dict = {}


# ======================================================================
def _project(strength):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE_41],
                   closed=True)
    ext.ensure_ccw()
    p = Project("back analysis envelope")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="soil", unit_weight=20.0, sat_unit_weight=20.0,
                   strength=strength,
                   pore_pressure=PorePressureType.RU_COEFFICIENT, ru=RU)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _power():
    from ogr_core.materials.builtin_models import PowerCurve
    return PowerCurve(a=1.4, b=0.8, c=0.0, d=0.0, waviness=0.0)


def _mohr():
    from ogr_core.materials.builtin_models import MohrCoulomb
    return MohrCoulomb(cohesion=5.0, friction_angle=30.0)


def _surface(method_id):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipCircle, SlipSurface
    if method_id == "bishop_simplified":
        return SlipCircle(*CIRCLE_41)
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in SURFACE_41], closed=False))


class _Switch:
    """``base.ENVELOPE_AT_OWN_STRESS`` set for the block and PUT BACK: the
    runner has no teardown, and a switch left off would change every
    later file."""

    def __init__(self, on: bool):
        self.on = on

    def __enter__(self):
        from ogr_slip2d.methods import base
        self.old = base.ENVELOPE_AT_OWN_STRESS
        base.ENVELOPE_AT_OWN_STRESS = self.on
        return self

    def __exit__(self, *exc):
        from ogr_slip2d.methods import base
        base.ENVELOPE_AT_OWN_STRESS = self.old
        return False


def _sums(slices, surface, f_eval, method_id, stress_fos):
    """``_sums_at_fixed_fos`` with the point found at ``stress_fos``. On a
    tree without that argument (v0.1.214) it is called without it, which is
    the old reading: the cases then fail on the number, not on a name."""
    from ogr_slip2d.back_analysis import _sums_at_fixed_fos
    try:
        return _sums_at_fixed_fos(slices, surface, f_eval, 0.0, 0.0, 0.0,
                                  method_id, stress_fos=stress_fos)
    except TypeError:
        return _sums_at_fixed_fos(slices, surface, f_eval, 0.0, 0.0, 0.0,
                                  method_id)


def _solve(key, strength, method_id, own_stress=True):
    """The method's own factor on its surface, with no support, and the
    back-analysis sums at that factor -- both under the same switch."""
    k = (key, method_id, own_stress)
    if k in _CACHE:
        return _CACHE[k]
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    p = _project(strength)
    surf = _surface(method_id)
    slices = slice_surface(p, surf, num_slices=N_SLICES)
    assert slices is not None
    with _Switch(own_stress):
        res = method_registry()[method_id](
            tolerance=SOLVER_TOL, max_iterations=500).compute_fos(
                p, surf, slices)
        assert res.fos is not None and res.converged, (
            method_id, res.reason, res.error_message)
        f_eval = res.fos / _f0(res) if method_id == "janbu_corrected" \
            else res.fos
        sums = _sums(slices.slices, surf, f_eval, method_id, res.fos)
    assert sums is not None, method_id
    out = (res, f_eval, sums)
    _CACHE[k] = out
    return out


def _f0(res):
    return res.details["janbu_f0"]


def _passive_unclipped(f_eval, sums):
    resisting, driving, arm = sums
    return (f_eval * driving - resisting) / arm


def _total_weight(res):
    return sum(s.weight for s in res.slices.slices)


def _bishop_arm_gap(res, f_eval, arm):
    """What Bishop's back analysis owes to ``sin a`` against the solver's
    ``weight_arm_ratio`` (a separate defect), as a passive force."""
    slices = res.slices.slices
    sign = res.details["slide_sign"]
    gap = sum(sign * s.weight * (math.sin(s.base_angle) - s.weight_arm_ratio)
              for s in slices)
    return f_eval * gap / arm


# ======================================================================
class TestTheWitnessIsCurved:
    """Guards: the identity is not satisfied vacuously."""

    def test_most_slices_read_a_stress_dependent_envelope(self):
        from ogr_slip2d.methods import base
        res, _f, _s = _solve("power", _power(), "janbu_simplified")
        cache: dict = {}
        dep = [base._envelope_depends_on_stress(s, cache)
               for s in res.slices.slices]
        assert sum(dep) == len(dep), dep

    def test_the_method_iterated_its_envelope_point(self):
        for mid in THREE:
            res, _f, _s = _solve("power", _power(), mid)
            assert res.details.get("envelope_converged") is True, mid
            assert res.details.get("envelope_passes", 0) > 1, mid


class TestZeroForceAtTheMethodsOwnFactor:
    """The identity, unclipped, with the switch on (the default)."""

    def test_janbu_and_janbu_corrected(self):
        for mid in JANBUS:
            res, f_eval, sums = _solve("power", _power(), mid)
            t = _passive_unclipped(f_eval, sums)
            assert abs(t) < TOL_W * _total_weight(res), (mid, t)

    def test_bishop_up_to_its_moment_arm_gap(self):
        res, f_eval, sums = _solve("power", _power(), "bishop_simplified")
        t = _passive_unclipped(f_eval, sums) \
            - _bishop_arm_gap(res, f_eval, sums[2])
        assert abs(t) < TOL_W * _total_weight(res), t

    def test_required_force_agrees_and_is_not_refused(self):
        """Through the public function: zero passive force, and the
        surface is back-analysed, not left out."""
        from ogr_slip2d.back_analysis import required_force
        for mid in JANBUS:
            res, _f, _s = _solve("power", _power(), mid)
            r = required_force(res.slices, res.surface, res.fos, mid, 0.0)
            assert r is not None and not r.notes, (mid, r and r.notes)
            assert r.passive_force < TOL_W * _total_weight(res), (
                mid, r.passive_force)


class TestThePointIsTheMethodsPoint:
    """Slice by slice, the back analysis finds the stress the method's
    own fixed point settled on -- at the factor that method reads it."""

    def _points(self, mid, stress_fos_of):
        from ogr_slip2d.back_analysis import _own_stress
        from ogr_slip2d.external_forces import seismic_soil_weight
        res, f_eval, _s = _solve("power", _power(), mid)
        fos = stress_fos_of(res, f_eval)
        sign = res.details["slide_sign"]
        worst = 0.0
        for s, want in zip(res.slices.slices,
                           res.details["envelope_stress"]):
            assert want is not None
            l = max(s.base_length, 1e-9)
            sigma0 = max(0.0, seismic_soil_weight(s.weight, 0.0)
                         * math.cos(s.base_angle)
                         - s.pore_pressure * s.base_length) / l
            got = _own_stress(s, s.weight, sigma0, fos, sign)
            worst = max(worst, abs(got - want) / max(1.0, abs(want)))
        return worst

    def test_the_three_methods_at_the_published_factor(self):
        for mid in THREE:
            worst = self._points(mid, lambda res, f_eval: res.fos)
            assert worst < 1e-5, (mid, worst)

    def test_janbu_corrected_at_the_uncorrected_factor_misses(self):
        """The choice of F is forced by the method, not by taste: at F/f0
        the points do NOT match what Janbu Corrected read."""
        worst = self._points("janbu_corrected",
                             lambda res, f_eval: f_eval)
        assert worst > 1e-3, worst


class TestControls:

    def test_with_the_switch_off_the_identity_holds_too(self):
        for mid in JANBUS:
            res, f_eval, sums = _solve("power", _power(), mid,
                                       own_stress=False)
            t = _passive_unclipped(f_eval, sums)
            assert abs(t) < TOL_W * _total_weight(res), (mid, t)

    def test_the_switch_moves_the_sums_of_a_curved_envelope(self):
        """Rule 7: at one and the same factor the two readings differ."""
        res, f_eval, _s = _solve("power", _power(), "janbu_simplified")
        with _Switch(True):
            on = _sums(res.slices.slices, res.surface, f_eval,
                       "janbu_simplified", res.fos)
        with _Switch(False):
            off = _sums(res.slices.slices, res.surface, f_eval,
                        "janbu_simplified", res.fos)
        assert abs(on[0] - off[0]) / off[0] > 1e-2, (on, off)

    def test_mohr_coulomb_is_bit_for_bit_the_old_reading(self):
        """No slice depends on the stress, so the switch changes nothing
        -- not a digit."""
        for mid in THREE:
            res, f_eval, _s = _solve("mohr", _mohr(), mid)
            with _Switch(True):
                on = _sums(res.slices.slices, res.surface, f_eval, mid,
                           res.fos)
            with _Switch(False):
                off = _sums(res.slices.slices, res.surface, f_eval, mid,
                            res.fos)
            assert on == off, (mid, on, off)


class TestAPointThatDoesNotSettleIsRefused:
    """No force rather than a force at a point the method does not use,
    and the refusal is said, not silent."""

    def test_required_force_reports_it(self):
        from ogr_slip2d.back_analysis import required_force
        from ogr_slip2d.methods import base
        res, _f, _s = _solve("power", _power(), "janbu_simplified")
        old = base.ENVELOPE_MAX_PASSES
        base.ENVELOPE_MAX_PASSES = 1
        try:
            r = required_force(res.slices, res.surface, res.fos,
                               "janbu_simplified", 0.0)
        finally:
            base.ENVELOPE_MAX_PASSES = old
        assert r is not None
        assert "envelope_not_settled" in r.notes, r.notes
        assert math.isnan(r.governing_force), r.governing_force
