# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The reported base normal must be the one the method actually used.

v0.1.61 added ponded water and updated the equilibrium equations to carry
it: every method's iteration uses ``slice_forces(...).w_total``, soil plus
the water standing on the slice. What it did NOT update was the
post-analysis block that fills ``LEMResult.base_normal_force`` (called
``base_normal`` until v0.1.107), which stayed on
``s.weight`` — the soil alone.

The gap was measured on the Pilarcitos dam geometry, with a reservoir over
the upstream face:

    slice   W soil   W water   w_total   N reported   N from w_total
        4     1121      6755      7876         1630             7256
        8     1749      5928      7677         2339             6876
       12     2007      5101      7108         2657             6181

A factor of three, on a number that is not merely displayed: it feeds
``checks.base_effective_stresses``, and therefore the tensile-stress
admissibility check that can invalidate a surface. The same omission was
in ``checks`` itself.

A second inconsistency lived in the same block: the effective normal
stress on the base is ``N/l − u`` with l the base LENGTH, and it was
computed as ``N/b − u`` with b the slice width — a factor cos α, and a
disagreement with ``checks.base_effective_stresses``, which had it right.
(The ``u·b`` inside Bishop's factor-of-safety numerator is a different
quantity and is correct as it stands: it comes out of the equilibrium
algebra, not from a stress definition.)

The anchor is an ANALYTIC IDENTITY, not a captured number. Bishop's
simplified method assumes zero interslice shear, so the vertical
equilibrium of each slice is exactly

    N·cos α + slide_sign · S · sin α = W_total

with ``S = [c·l + (N − u·l)·tan φ] / F`` the mobilised base shear. That is
the very equation Bishop's expression for N is a rearrangement of, so it
must hold slice by slice on the values reported — and it cannot hold if W
is missing the water.
"""
from __future__ import annotations

import math

GAMMA_W = 62.4          # lb/ft³, imperial to match the published geometry


def _pilarcitos(with_reservoir=True):
    """The upstream slope of a dam, optionally with the reservoir on it.

    Geometry of the published Pilarcitos case, which is where the defect
    was found; the reservoir at y = 72 stands over the whole upstream
    face, so the ponded load dominates the soil weight.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
        Vertex(205, 78), Vertex(145, 58),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("pil")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if with_reservoir:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, 72), Vertex(265, 72)],
                              closed=False),
            btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="Embankment", unit_weight=135.0, sat_unit_weight=135.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
        pore_pressure=(PorePressureType.WATER_TABLE if with_reservoir
                       else PorePressureType.NONE),
    )]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=52.0, centre_y=186.0, radius=158.2)


def _run(p):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    assert sl is not None
    return BishopSimplified().compute_fos(p, _circle(), sl)


# ======================================================================
class TestTheFixtureReallyHasPondedWater:
    """Guard the guard: without water on the slices the identity below
    would hold trivially for the old code too."""

    def test_the_water_dominates_the_soil_weight(self):
        from ogr_slip2d.slicer import slice_surface
        p = _pilarcitos()
        sl = slice_surface(p, _circle(), num_slices=25)
        w_soil = sum(s.weight for s in sl.slices)
        w_water = sum(s.water_weight for s in sl.slices)
        assert w_water > w_soil, (w_soil, w_water)


class TestVerticalEquilibriumHolds:
    """The identity. It is what the reported normal MEANS."""

    def _check(self, p):
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _run(p)
        assert math.isfinite(res.fos) and res.fos > 0
        slices = res.slices.slices
        normals = res.base_normal_force
        assert len(normals) == len(slices)

        driving = sum(s.weight * math.sin(s.base_angle) for s in slices)
        slide_sign = 1.0 if driving >= 0 else -1.0
        f = res.fos

        for s, N in zip(slices, normals):
            l = max(s.base_length, 1e-9)
            u = s.pore_pressure
            w_total = s.weight + s.water_weight
            sigma_eff = max(0.0, N / l - u)
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                       sigma_eff)
            shear = (c * l + (N - u * l) * tan_phi) / f
            lhs = (N * math.cos(s.base_angle)
                   + slide_sign * shear * math.sin(s.base_angle))
            assert abs(lhs - w_total) / max(abs(w_total), 1.0) < 1e-6, (
                s.index, lhs, w_total)

    def test_with_a_reservoir_on_the_slope(self):
        self._check(_pilarcitos(with_reservoir=True))

    def test_without_any_water(self):
        """The case that already worked, kept so the fix cannot be a
        rearrangement that only happens to suit the wet case."""
        self._check(_pilarcitos(with_reservoir=False))


class TestTheNormalCarriesTheWater:
    def test_it_is_far_above_the_soil_weight_alone(self):
        """Before the fix the reported normal was BELOW the soil weight
        resolved on the base, because that is all it knew about."""
        res = _run(_pilarcitos())
        slices = res.slices.slices
        bigger = 0
        for s, N in zip(slices, res.base_normal_force):
            if N > 1.5 * s.weight:
                bigger += 1
        assert bigger > len(slices) // 2, bigger

    def test_removing_the_reservoir_lowers_every_normal(self):
        wet = _run(_pilarcitos(with_reservoir=True))
        dry = _run(_pilarcitos(with_reservoir=False))
        assert sum(wet.base_normal_force) > 2.0 * sum(dry.base_normal_force)


class TestTheAdmissibilityCheckSeesTheWater:
    """``base_effective_stresses`` fed the tensile-stress check with the
    soil weight alone, which is the difference between a slice in tension
    and one under a reservoir."""

    def test_the_effective_stresses_are_positive_under_a_reservoir(self):
        from ogr_slip2d.checks import base_effective_stresses
        res = _run(_pilarcitos())
        sigmas = base_effective_stresses(res)
        assert sigmas
        # A slope loaded by 30 ft of water is in compression on its base.
        assert min(sigmas) > 0.0, min(sigmas)

    def test_it_agrees_with_the_method_that_produced_it(self):
        """The two used to disagree by a factor cos α on top of the water.
        They are computed independently, so agreeing is a real check."""
        from ogr_slip2d.checks import base_effective_stresses
        res = _run(_pilarcitos())
        from_checks = base_effective_stresses(res)
        from_method = [
            N / max(s.base_length, 1e-9) - s.pore_pressure
            for s, N in zip(res.slices.slices, res.base_normal_force)
        ]
        for a, b in zip(from_checks, from_method):
            assert abs(a - b) / max(abs(b), 1.0) < 1e-6, (a, b)
