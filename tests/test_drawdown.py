# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The arithmetic of the B-bar drawdown model, slice by slice.

This file checks the pieces; ``test_drawdown_bbar_v169`` checks the
answer against Morgenstern (1963). Neither is enough alone — a formula
that reproduces a published factor of safety can still be assembled
wrongly at the edges, and a formula whose arithmetic checks out can still
be the wrong formula, which is what happened here.

What this file used to say, and why it was wrong
------------------------------------------------
Until v0.1.69 it asserted ``Δu = B̄·γ_w·(y_drawdown − y_wt)`` with the
drawdown line ABOVE the water table, and a test named
``test_drawdown_below_wt_no_excess`` locked in the idea that a drawdown
line below the water table was "not a drawdown situation". It was the
only situation: the water table is the initial level and the drawdown
line the final, lower one, in this model as in the other three. Every
assertion below is the same arithmetic with the two levels the right way
round, plus the two things the old model could not see at all — the
ground surface, and the ponded water.

The model, in one line per term::

    Δσ_v = −γ_w·(h_ponded,initial − h_ponded,final)   capped by the ground
    u    = max(0, u_initial + B̄·Δσ_v)                 undrained materials
    u    = u at the final level                       everything else
"""
from __future__ import annotations

import math

GAMMA_W = 9.81

# Wide enough that a circle tangent at the point of interest still
# daylights on the top surface well inside the block — see ``_u_at``.
WIDTH = 200.0
X_PROBE = 100.0
HALF_CHORD = 40.0


def _make_project(b_bar=None, drawdown_y=None, rapid=True, initial_y=25.0,
                  ground_y=30.0):
    """A block of soil with a reservoir standing over its flat top.

    The top is at ``ground_y`` and both levels are above it by default,
    so every point has a full ponded column over it and Δσ_v is simply
    the difference of the two levels — the case where the old formula and
    the new one have the same magnitude, and only the sign and the
    labelling differ.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    p = Project("dd")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(WIDTH, 0),
        Vertex(WIDTH, ground_y), Vertex(0, ground_y),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    # Initial reservoir level.
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(0, initial_y),
                                    Vertex(WIDTH, initial_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    if drawdown_y is not None:
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, drawdown_y), Vertex(WIDTH, drawdown_y)],
                closed=False),
            btype=BoundaryType.DRAWDOWN))
    p.settings.groundwater.rapid_drawdown = rapid
    p.settings.groundwater.rapid_drawdown_method = "b_bar"
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W

    mat = Material(
        name="Soil",
        strength=MohrCoulomb(cohesion=10, friction_angle=25),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    if b_bar is not None:
        mat.b_bar = b_bar
        mat.undrained_behaviour = True
    p.materials = [mat]
    return p, mat


def _u_at(project, y, ground_y, n=20):
    """Pore pressure the drawdown model gives at depth, via the slices.

    Goes through the real path — slice at the final level, then overwrite
    the undrained slices — rather than calling a formula directly, which
    is how the old model came to be tested in a place the analysis never
    reached.

    The circle is chosen so its lowest point sits at ``(X_PROBE, y)`` and
    it daylights ``HALF_CHORD`` either side: from ``c² = 2·r·d − d²`` with
    ``d`` the depth below the ground surface, ``r = (c² + d²)/(2d)``.
    Picking a fixed large radius instead fails silently — the circle
    leaves through the sides of the block and ``slice_surface`` returns
    None.
    """
    from ogr_core.hydraulic.drawdown_levels import level_project
    from ogr_slip2d.rapid_drawdown import b_bar_pore_pressures
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle

    d = ground_y - y
    assert d > 0, "the probe point must lie below the ground surface"
    r = (HALF_CHORD ** 2 + d ** 2) / (2.0 * d)
    surface = SlipCircle(centre_x=X_PROBE, centre_y=y + r, radius=r)
    sl = slice_surface(level_project(project, True), surface, num_slices=n)
    assert sl is not None, "the probe circle does not fit in the block"
    b_bar_pore_pressures(project, sl)
    best = min(sl.slices, key=lambda s: abs(s.x_centre - X_PROBE))
    return best.pore_pressure


# ======================================================================
class TestBBarDrawdown:
    """Δu = B̄·Δσ_v, with the levels the way the reference states them."""

    def test_no_drawdown_line_means_total_drawdown(self):
        """Ground at 20 under a reservoir at 25: 5 m of ponded water,
        and an undrawn final level takes all of it away.

        u_initial at y = 5 is γw·20; u = γw·20 − 1.0·γw·5 = γw·15.
        """
        p, mat = _make_project(b_bar=1.0, drawdown_y=None, ground_y=20.0)
        assert math.isclose(_u_at(p, 5, 20.0), GAMMA_W * 15, rel_tol=0.01)

    def test_rapid_off_ignores_the_drawdown_line(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at

        p, mat = _make_project(b_bar=1.0, drawdown_y=10.0, rapid=False)
        # Nothing wraps the method, so the pore pressure is the plain
        # steady-state one from the water table at 25.
        assert math.isclose(pore_pressure_at(p, Vertex(X_PROBE, 5), mat),
                            GAMMA_W * 20, rel_tol=0.01)

    def test_with_no_ponded_water_there_is_nothing_to_shed(self):
        """25 → 10 over ground at 30: neither level stands on the ground,
        so Δσ_v = 0 and the initial pore pressure is retained in full.

        This is the case the old model got right by accident and the one
        that hid the rest: the gap between the two water surfaces and the
        ponded column removed happen to be unrelated here, and only the
        second one is the vertical stress change.
        """
        p, mat = _make_project(b_bar=1.0, drawdown_y=10.0, ground_y=30.0)
        assert math.isclose(_u_at(p, 5, 30.0), GAMMA_W * 20, rel_tol=0.01)

    def test_the_ponded_column_is_what_counts(self):
        """The ground surface between the two levels — the whole point.

        Ground at 15, reservoir 25 → 10, probe at y = 0. The column
        standing over the point goes from 10 m to NOTHING, because the
        final level is below the ground there:

            Δσ_v = −γw·(10 − 0) = −γw·10
            u    = γw·25 − 1.0·γw·10 = γw·15

        Not γw·15 because of the water surfaces being 15 m apart — they
        are — but because 10 m of water came off the ground. The two
        numbers differ here, and this is the geometry of the whole
        upstream face of a real dam.
        """
        p, mat = _make_project(b_bar=1.0, drawdown_y=10.0, ground_y=15.0)
        assert math.isclose(_u_at(p, 0, 15.0), GAMMA_W * 15, rel_tol=0.02)

    def test_half_transfer_keeps_half_the_excess(self):
        """Same geometry, B̄ = 0.5: u = γw·25 − 0.5·γw·10 = γw·20."""
        p, mat = _make_project(b_bar=0.5, drawdown_y=10.0, ground_y=15.0)
        assert math.isclose(_u_at(p, 0, 15.0), GAMMA_W * 20, rel_tol=0.02)

    def test_a_freely_draining_material_follows_the_final_level(self):
        """v0.1.62's flag, now with a consequence that is visible.

        Same geometry again. Without ``undrained_behaviour`` the slice
        keeps the pore pressure the final level gives it, γw·10 — lower
        than any of the undrained answers above, which is the ordering
        the reference states for a free-draining zone.
        """
        p, mat = _make_project(b_bar=1.0, drawdown_y=10.0, ground_y=15.0)
        mat.undrained_behaviour = False
        assert math.isclose(_u_at(p, 0, 15.0), GAMMA_W * 10, rel_tol=0.02)

    def test_the_excess_never_goes_negative(self):
        """A drawdown large enough to overshoot is clamped at zero
        rather than turned into suction the analysis would lean on.

        Ground at 5, reservoir 25 → 6, B̄ = 3: Δσ_v = −γw·19 and
        u_initial = γw·21, so the raw sum is −36·γw.
        """
        p, mat = _make_project(b_bar=3.0, drawdown_y=6.0, ground_y=5.0)
        assert _u_at(p, 4, 5.0) == 0.0
