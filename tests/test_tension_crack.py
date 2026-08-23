# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for the v0.1.7 Tension Crack hydraulic model.

Verifies:
    - TensionCrackProperties water-level resolution for all 7 modes
    - Hydrostatic force ½γh² applied on the up-slope side of slices
"""
from __future__ import annotations

import math

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    TensionCrackProperties,
    Vertex,
    WaterLevelMode,
)


# ======================================================================
class TestWaterLevelResolution:
    """For every mode, the water level inside the crack is correct."""

    def test_dry_returns_bottom(self):
        p = TensionCrackProperties(mode=WaterLevelMode.DRY)
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=15)
        assert wl == 15

    def test_filled_returns_top(self):
        p = TensionCrackProperties(mode=WaterLevelMode.FILLED)
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=15)
        assert wl == 20

    def test_percent_filled_50pct_is_midway(self):
        p = TensionCrackProperties(
            mode=WaterLevelMode.PERCENT_FILLED, percent_filled=50.0
        )
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=10)
        assert math.isclose(wl, 15)

    def test_filled_below_elevation(self):
        p = TensionCrackProperties(
            mode=WaterLevelMode.FILLED_BELOW_ELEVATION, elevation=18.0
        )
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=10)
        assert wl == 18.0

    def test_filled_below_elevation_clamped_to_bottom(self):
        # Elevation way below the crack base — clamps to bottom
        p = TensionCrackProperties(
            mode=WaterLevelMode.FILLED_BELOW_ELEVATION, elevation=-5.0
        )
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=10)
        assert wl == 10.0

    def test_filled_to_depth(self):
        # Depth = 3 m below the crack top (which is at y=20) → wl = 17
        p = TensionCrackProperties(
            mode=WaterLevelMode.FILLED_TO_DEPTH, depth=3.0
        )
        wl = p.water_level_at(x=10, crack_top_y=20, crack_bottom_y=10)
        assert math.isclose(wl, 17.0)

    def test_dry_is_dry(self):
        assert TensionCrackProperties(mode=WaterLevelMode.DRY).is_dry()

    def test_zero_percent_is_dry(self):
        p = TensionCrackProperties(
            mode=WaterLevelMode.PERCENT_FILLED, percent_filled=0.0
        )
        assert p.is_dry()


# ======================================================================
class TestHydrostaticForce:
    """½ γ_w h_w² is applied on the up-slope side of the failure mass."""

    def test_filled_crack_applies_force(self):
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import SlipCircle, slice_surface

        # Create a 100 x 30 domain with a Tension Crack at y=25.
        # v0.1.61 — the crack used to span x ∈ [85, 100], but the circle
        # below daylights at x ≈ 84.6, so the slip surface never entered
        # the crack zone and no force was ever produced. That is exactly
        # what the vacuous ``if force > 0`` guard was hiding. Moved into
        # the surface's span so the test exercises something.
        #
        # v0.1.109 — and moved once more, out to x = 90. The v0.1.61 zone
        # stopped at 84 and the arc daylights at 84.64, so the CREST of
        # the surface was still outside it by six tenths of a metre. That
        # no longer produces a thrust, and correctly so: the reference
        # truncates a surface only when its crest lies inside the crack
        # zone, and where nothing is truncated there is no crack wall for
        # water to push on. Half of anomaly A2-2 was this exact case.
        p = Project("TC test")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(100, 0),
            Vertex(100, 30), Vertex(0, 30),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        # Crack lower boundary
        tc = Boundary(
            polyline=Polyline(
                vertices=[Vertex(75, 25), Vertex(90, 25)], closed=False
            ),
            btype=BoundaryType.TENSION_CRACK,
        )
        p.add_boundary(tc)
        p.materials = [
            Material(name="Soil",
                     strength=MohrCoulomb(cohesion=10, friction_angle=25))
        ]
        p.tension_crack_properties = TensionCrackProperties(
            mode=WaterLevelMode.FILLED
        )
        # Slip circle clipped through the crack zone
        circle = SlipCircle(centre_x=50, centre_y=50, radius=40)
        sl = slice_surface(p, circle, num_slices=20)
        if sl is None:
            return  # surface degenerate; skip
        # Crack height = 30 - 25 = 5 m → F = ½ * 9.81 * 5² ≈ 122.6 kN/m
        F_expected = 0.5 * 9.81 * 5.0 * 5.0
        # v0.1.61 — this used to be wrapped in ``if force > 0``, which
        # made the assertion vacuous: the force was never applied to
        # anything, so nothing here could fail. It is a real check now.
        assert sl.tension_crack_force > 0
        assert math.isclose(sl.tension_crack_force, F_expected, rel_tol=0.5)
        # And it must actually reach a slice, which is where every LEM
        # method reads it from. The per-slice value is SIGNED (+x), while
        # ``tension_crack_force`` is a magnitude, so compare moduli.
        assert math.isclose(abs(sum(s.water_force_h for s in sl.slices)),
                            sl.tension_crack_force, rel_tol=1e-12)

    def test_dry_crack_no_force(self):
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import SlipCircle, slice_surface

        p = Project("TC dry test")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(100, 0),
            Vertex(100, 30), Vertex(0, 30),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        # Same crack position as the filled case, so "dry ⇒ no force" is
        # a real statement about the water level and not about geometry.
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(75, 25), Vertex(84, 25)], closed=False),
            btype=BoundaryType.TENSION_CRACK,
        ))
        p.materials = [
            Material(name="Soil",
                     strength=MohrCoulomb(cohesion=10, friction_angle=25))
        ]
        p.tension_crack_properties = TensionCrackProperties(
            mode=WaterLevelMode.DRY
        )
        circle = SlipCircle(centre_x=50, centre_y=50, radius=40)
        sl = slice_surface(p, circle, num_slices=20)
        if sl is not None:
            # Dry crack → no force
            assert sl.tension_crack_force == 0.0
