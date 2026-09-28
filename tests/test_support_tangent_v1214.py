# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — on a circle, a support declared tangent to the slip surface is one
more BASE SHEAR: its moment about the centre is |F|·R exactly (defect D151 of
the verification bank, closed on a premise that had to be corrected first).

WHAT THE RECORD SAID, AND WHAT WAS MEASURED. D151 read the second-order
residue a ``TANGENT_TO_SLIP`` support kept after D144 (v0.1.178, the moment
taken as the cross product at the crossing) as a DIRECTION error: the force
follows the slice's chord and not the arc's tangent. Measured on the
tangential fixture of ``test_support_active_passive_v1115`` (circle
(38, 26, 20)), that is not where the residue lives. The crossing itself is
computed on the polyline of CHORDS, so ``|P − C| < R``:

    40 slices   |P−C|/R − 1 = −3.45e-5    chord vs tangent at P: 0.065°
                (the direction accounts for −6.4e-7 of the moment)

Taking the arc's tangent at P would leave the moment at ``|F|·|P−C|``, never
``|F|·R``, and would give the force a component normal to the chord that two
tests fix at zero.

THE DECISION (the owner, 2026-09-27). The circular moment equation of Bishop
(1955) takes every base shear with arm R: on the arc the shear is tangent at
every point, so its moment is R times its magnitude wherever it acts, and the
chord is only where the force balance of the slice is written. A support
tangent to the slip surface is, for the method, one more base shear: it keeps
the chord's direction in the force balance (``n_press = 0``,
``t_active = |F|``) and gets the shear's arm in the moment, ``|F|·R``. That is
what OGR did for this orientation until v0.1.177, when the two chord errors
cancelled; now it is stated rather than accidental. The shear vector a nail
adds (``SUPPORTS_SHEAR``) is not tangent and keeps the cross product at its
crossing, and so do the other orientations, bit for bit.

THE INVARIANTS.

1. ``moment_active = |F|`` (the moment over R) and ``n_press = 0``, exactly,
   at 20, 50 and 200 slices; the same for PASSIVE.
2. A nail with a shear vector: the axial part gives ``+|F|`` and the vector
   ``V`` its cross product at the crossing.
3. HORIZONTAL, USER_DEFINED and PARALLEL_TO_SUPPORT are bit for bit what they
   were (switch on against switch off).
4. Rule 7: with ``TANGENT_AS_BASE_SHEAR`` off the moment is D144's cross
   product again, short of ``|F|`` by second order.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

CAPACITY = 20.0
SWEEP = (20, 50, 200)


def _switch(on):
    from ogr_slip2d import support_integration as si
    old = getattr(si, "TANGENT_AS_BASE_SHEAR", None)
    si.TANGENT_AS_BASE_SHEAR = on
    return old


def _restore(old):
    from ogr_slip2d import support_integration as si
    if old is None:
        vars(si).pop("TANGENT_AS_BASE_SHEAR", None)
    else:
        si.TANGENT_AS_BASE_SHEAR = old


def _tangent_project(application=None):
    """The fixture of ``test_support_active_passive_v1115``: a constant
    capacity, TANGENT_TO_SLIP, crossing the circle (38, 26, 20)."""
    from ogr_core.support import ForceApplication
    from test_support_active_passive_v1115 import _project
    return _project(application or ForceApplication.ACTIVE, friction=0.0,
                    cohesion=30.0, capacity=CAPACITY)


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _terms(project, n, on=True):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import resolve_support_terms
    sl = slice_surface(project, _circle(), num_slices=n)
    sign = 1.0 if sum(s.weight * math.sin(s.base_angle)
                      for s in sl.slices) >= 0 else -1.0
    old = _switch(on)
    try:
        return sl, sign, resolve_support_terms(project, _circle(), sl, sign)
    finally:
        _restore(old)


# ======================================================================
class TestTheTangentSupportIsABaseShear:

    def test_the_moment_is_the_capacity_times_r_at_any_mesh(self):
        for n in SWEEP:
            _sl, _sign, sup = _terms(_tangent_project(), n)
            assert sup.present, n
            assert abs(sup.moment_active / CAPACITY - 1.0) < 1e-9, (
                n, sup.moment_active)
            assert sup.moment_passive == 0.0

    def test_and_the_force_balance_still_sees_it_along_the_base(self):
        for n in SWEEP:
            _sl, _sign, sup = _terms(_tangent_project(), n)
            crossed = [i for i, t in enumerate(sup.t_active) if t]
            assert len(crossed) == 1, (n, crossed)
            i = crossed[0]
            assert abs(sup.t_active[i] / CAPACITY - 1.0) < 1e-12, (n, i)
            assert max(abs(v) for v in sup.n_press) < 1e-12 * CAPACITY

    def test_passive_too(self):
        from ogr_core.support import ForceApplication
        for n in SWEEP:
            _sl, _sign, sup = _terms(
                _tangent_project(ForceApplication.PASSIVE), n)
            assert abs(sup.moment_passive / CAPACITY - 1.0) < 1e-9, (
                n, sup.moment_passive)
            assert sup.moment_active == 0.0


class TestAShearVectorKeepsItsCrossProduct:
    """A nail tangent to the surface with a dowel capacity: the axial part is
    a base shear, the perpendicular vector ``V`` is not."""

    AXIAL, SHEAR = 100.0, 30.0

    def _project(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SoilNail, SupportInstance)
        from test_support_active_passive_v1115 import _project
        p = _project(None, friction=0.0, cohesion=30.0)
        # Tensile governs: bond and plate far above it along the whole nail.
        p.support_types = [SoilNail(tensile_capacity=self.AXIAL,
                                    plate_capacity=1e4, bond_strength=1e4,
                                    out_of_plane_spacing=1.0,
                                    shear_capacity=self.SHEAR)]
        p.supports = [SupportInstance(
            type_id="soil_nail", head=Vertex(43.5, 8.0),
            tail=Vertex(54.0, 8.0),
            force_application=ForceApplication.ACTIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
        return p

    def test_axial_times_r_plus_the_cross_product_of_v(self):
        from ogr_slip2d.support_integration import compute_support_effects
        cx, cy, r = 38.0, 26.0, 20.0
        p = self._project()
        for n in SWEEP:
            sl, sign, sup = _terms(p, n)
            (eff,) = compute_support_effects(p, _circle(), sl)
            a = sl.slices[eff.slice_index].base_angle
            axial = (sign * self.AXIAL * math.cos(a),
                     sign * self.AXIAL * math.sin(a))
            vh, vv = eff.force_h - axial[0], eff.force_v - axial[1]
            # Fixture controls: the nail resists, and what is left over is
            # exactly the dowel vector.
            assert sign * (eff.force_h * math.cos(a)
                           + eff.force_v * math.sin(a)) > 0.0
            assert abs(math.hypot(vh, vv) / self.SHEAR - 1.0) < 1e-9, n
            expected = self.AXIAL + sign * (
                (eff.intersection_x - cx) * vv
                - (eff.intersection_y - cy) * vh) / r
            assert abs(sup.moment_active / expected - 1.0) < 1e-9, (
                n, sup.moment_active, expected)


class TestTheOtherOrientationsDoNotMove:

    def test_bit_for_bit(self):
        from ogr_core.support import ForceOrientation
        from test_support_arm_v1178 import _anchor, _project
        for orientation, angle in ((ForceOrientation.HORIZONTAL, None),
                                   (ForceOrientation.USER_DEFINED, 25.0),
                                   (ForceOrientation.PARALLEL_TO_SUPPORT,
                                    None)):
            p = _project([_anchor(41.0, orientation, angle=angle)])
            for n in SWEEP:
                _sl, _s, on = _terms(p, n, True)
                _sl, _s, off = _terms(p, n, False)
                assert on.moment_active == off.moment_active, (orientation, n)
                assert on.t_active == off.t_active
                assert on.n_press == off.n_press


class TestRuleSeven:

    def test_off_it_is_the_cross_product_at_the_crossing_again(self):
        from ogr_slip2d.support_integration import compute_support_effects
        cx, cy, r = 38.0, 26.0, 20.0
        p = _tangent_project()
        sl, sign, off = _terms(p, 40, False)
        (eff,) = compute_support_effects(p, _circle(), sl)
        cross = sign * ((eff.intersection_x - cx) * eff.force_v
                        - (eff.intersection_y - cy) * eff.force_h) / r
        assert abs(off.moment_active - cross) < 1e-12 * CAPACITY
        assert 1e-7 < abs(off.moment_active / CAPACITY - 1.0) < 1e-3, (
            off.moment_active)
