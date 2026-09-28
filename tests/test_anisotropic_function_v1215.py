# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.215 — the Anisotropic Strength Function reads its table at the
inclination of the slice base, and a slope made of it can be analysed at
all (defect D195).

THE DEFECT. Since v0.1.126 ``shear_strength_ctx`` called
``self._c_phi(angle, local_bedding)`` while this class's ``_c_phi`` takes
the angle only, so the FIRST slice of any analysis raised ``TypeError``
inside ``BishopSimplified._local_c_phi``, which every one of the nine
methods calls. No test solved a slope with the model (the v0.1.15 file only
checks that its id is registered) and no material of the verification
bench uses it, so it went unseen for ninety versions.

WHICH ANGLE. The model is a table of (angle, c, phi) against the
inclination of the slice base itself, measured counter-clockwise from the
horizontal in [-90, 90]: that is how the reference program documents this
strength type ("angular ranges of slice base inclination ... ordered
counter-clockwise from -90 to +90"), with no bedding in it -- the table IS
the anisotropy. The slicer's ``alpha = atan2(dy, dx)`` with ``dx > 0`` is
the same convention. So the angle passed is the absolute one, and a bedding
direction in the context must change nothing: that is pinned below, since
it is the decision the fix embodies.

THE REFERENCES (rule 1):

* the function written by hand (see v0.1.218 below);
* an identity: a table whose every row holds the same (c, phi) IS
  Mohr-Coulomb, so the nine methods must return exactly Mohr-Coulomb's
  factor on the same circle;
* the Ordinary Method on a dry circle is a closed sum, so its factor must
  equal ``sum(c(a)*l + W*cos(a)*tan(phi(a))) / sum(W*weight_arm_ratio)``
  with c(a) and phi(a) from the hand-written function at each base.

The last two also show the table moves the number (rule 7): the default
table and a constant one give different factors on the same circle.

DISCRIMINATION, measured on the v0.1.214 tree: 8 of the 9 cases fail with
the TypeError. The ninth is the guard that the hand-written function gives
the two anchor values, which does not touch the engine.

v0.1.218 (D209) -- CHANGED ON PURPOSE. The table is now a list of RANGES,
``rows`` of (angle to, c, phi), as the reference documents the strength
type, and no longer points interpolated linearly: so the hand-written
function, the default table and the two anchors had to change with it.
What this file protects is unchanged -- the angle is the ABSOLUTE base
inclination, a bedding in the context changes nothing, a slope of the model
can be analysed by the nine methods -- and the ranges themselves are pinned
in ``test_anisotropic_function_ranges_v1218``. The old anchors were c = 10,
phi = 20 at +30 deg and c = 12.5, phi = 22.5 at -45 deg on the old default
points (-90, 20, 30), (0, 5, 15), (90, 20, 30); on the new default table,
the example the reference documentation draws, they are the ranges
(0, 90] -> (5, 10) and [-90, -30] -> (10, 35).
"""
from __future__ import annotations

import math

#: The default table of the model (also the dialog's default): the example
#: the reference documentation draws for this strength type.
DEFAULT_ROWS = [(-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0)]
#: A dry circle on the slope below whose bases run from about -18 to +62
#: degrees, so two ranges of the table are read.
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30

_CACHE: dict = {}


# ======================================================================
def _by_hand(angle_deg, rows=DEFAULT_ROWS):
    """The table read as ranges, written out independently of the class:
    the first row whose 'angle to' is at or above the angle."""
    for angle_to, c, phi in rows:
        if angle_deg <= angle_to:
            return c, phi
    raise AssertionError(angle_deg)


def _model(rows=None):
    from ogr_core.materials.builtin_models import AnisotropicStrengthFunction
    return AnisotropicStrengthFunction(rows=rows)


def _ctx(angle_deg, bedding_deg=None):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(angle_deg),
                        bedding_angle_deg=bedding_deg)


def _project(strength):
    """A dry homogeneous 1V:1.67H slope, 12 m high, on a 10 m foundation
    (the slope of the v0.1.15 strength-model tests)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h = 12.0
    toe = 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("anisotropic function")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="soil", unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _solve(key, strength, method_id):
    k = (key, method_id)
    if k in _CACHE:
        return _CACHE[k]
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _project(strength)
    circle = SlipCircle(*CIRCLE)
    slices = slice_surface(p, circle, num_slices=N_SLICES)
    assert slices is not None
    res = method_registry()[method_id]().compute_fos(p, circle, slices)
    _CACHE[k] = res
    return res


def _nine():
    from ogr_slip2d.methods import method_registry
    ids = sorted(method_registry())
    assert len(ids) == 9, ids
    return ids


# ======================================================================
class TestTheTableIsReadAtTheBaseInclination:
    """The model against the function written by hand."""

    def test_at_plus_30_degrees(self):
        tau = _model().shear_strength_ctx(50.0, _ctx(30.0))
        want = 5.0 + 50.0 * math.tan(math.radians(10.0))
        assert math.isclose(tau, want, rel_tol=1e-12), (tau, want)

    def test_at_minus_45_degrees(self):
        tau = _model().shear_strength_ctx(50.0, _ctx(-45.0))
        want = 10.0 + 50.0 * math.tan(math.radians(35.0))
        assert math.isclose(tau, want, rel_tol=1e-12), (tau, want)

    def test_the_hand_function_agrees_with_those_two_values(self):
        """Guard: the independent reading the slope tests rely on is the
        one the two anchors above were worked out with."""
        assert _by_hand(30.0) == (5.0, 10.0)
        assert _by_hand(-45.0) == (10.0, 35.0)

    def test_a_bedding_direction_changes_nothing(self):
        """The angle is the ABSOLUTE base inclination: the model has no
        bedding, so a context carrying one must give the same strength."""
        for angle in (30.0, -45.0, 61.7):
            a = _model().shear_strength_ctx(50.0, _ctx(angle))
            b = _model().shear_strength_ctx(50.0, _ctx(angle, 30.0))
            assert a == b, (angle, a, b)


class TestASlopeOfItCanBeAnalysed:
    """Nine methods, one circle, no exception."""

    def test_the_nine_methods_return_a_factor(self):
        for mid in _nine():
            res = _solve("default", _model(), mid)
            assert res.fos is not None and res.fos > 0.0, (
                mid, res.reason, res.error_message)

    def test_each_base_reads_the_table_at_its_own_inclination(self):
        """``_local_c_phi``, the one linearisation every method uses,
        returns the hand-written (c, tan phi) of each base's angle."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _solve("default", _model(), "bishop_simplified")
        angles = [math.degrees(s.base_angle) for s in res.slices.slices]
        assert min(angles) < -10.0 and max(angles) > 50.0, angles
        for s in res.slices.slices:
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 40.0)
            c_h, phi_h = _by_hand(math.degrees(s.base_angle))
            assert math.isclose(c, c_h, rel_tol=1e-9), (s.index, c, c_h)
            assert math.isclose(tan_phi, math.tan(math.radians(phi_h)),
                                rel_tol=1e-9), (s.index, tan_phi, phi_h)

    def test_a_constant_table_is_mohr_coulomb(self):
        """Identity: with the same (c, phi) in every row the model IS
        Mohr-Coulomb, so every method returns Mohr-Coulomb's factor."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        flat = [(0.0, 8.0, 25.0), (90.0, 8.0, 25.0)]
        for mid in _nine():
            a = _solve("flat", _model(flat), mid).fos
            b = _solve("mc", MohrCoulomb(cohesion=8.0, friction_angle=25.0),
                       mid).fos
            assert a is not None and b is not None, mid
            assert math.isclose(a, b, rel_tol=1e-9), (mid, a, b)

    def test_the_table_moves_the_factor(self):
        """Rule 7: the default table and a constant one are different
        materials, and every method must see that."""
        flat = [(0.0, 8.0, 25.0), (90.0, 8.0, 25.0)]
        for mid in _nine():
            a = _solve("default", _model(), mid).fos
            b = _solve("flat", _model(flat), mid).fos
            assert abs(a - b) / b > 1e-3, (mid, a, b)


class TestTheOrdinaryMethodIsAClosedSum:
    """On a dry circle the Ordinary Method has no iteration: its factor
    is the sum of c(a)*l + W*cos(a)*tan(phi(a)) over the sum of the
    weight's moment arm, with c and phi from the hand-written table."""

    def test_the_factor_is_the_hand_sum(self):
        res = _solve("default", _model(), "ordinary_fellenius")
        slices = res.slices.slices
        driving_raw = sum(s.weight * math.sin(s.base_angle) for s in slices)
        sign = 1.0 if driving_raw >= 0 else -1.0
        num = 0.0
        den = 0.0
        for s in slices:
            c, phi = _by_hand(math.degrees(s.base_angle))
            n = s.weight * math.cos(s.base_angle)
            assert n > 0.0, s.index       # no clipping on this circle
            num += c * s.base_length + n * math.tan(math.radians(phi))
            den += sign * s.weight * s.weight_arm_ratio
        want = num / den
        assert math.isclose(res.fos, want, rel_tol=1e-10), (res.fos, want)
