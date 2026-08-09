# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Corps of Engineers' own Appendix G example, on a FIXED slip surface.

What this settles that Pilarcitos could not
-------------------------------------------
The Pilarcitos case in ``test_rapid_drawdown_v168`` compares minima: our
search against the published critical value. That is the honest thing to
do there, but it leaves a gap — a composite envelope that is slightly
wrong can be masked by a search that lands on a slightly different
circle. In particular the ``min(R, effective)`` rule the Corps two-stage
procedure applies could not be told apart from its neighbours by ±3 %
agreement on a searched minimum.

This case closes that gap. **One circle, given: centre (169.5, 210),
radius 210 ft.** No search, no grid, no room to compensate. And the SAME
circle carries two published numbers by two procedures:

    Army Corps of Engineers, 2 stage ..... 1.35   (referee)
    Duncan, Wright and Wong, 3 stage ..... 1.44   (referee)

Reproducing both from one geometry is a much stronger statement than
either alone, and their ratio is nearly insensitive to anything about
the model except the composite envelope itself.

Where the geometry comes from
-----------------------------
Verification problems #95 and #96 of the reference documentation, which
share one figure — that is how it is known they share a geometry. The
figure is a raster image inside the PDF, but every vertex carries its
coordinate pair as a printed label, so nothing here is digitised by eye:
the numbers below are read off the drawing, not measured on it.

One discrepancy, reported rather than smoothed over: the prose of both
problems says the initial water level is at **elevation 110 ft**, while
the figure labels the initial water table's two ends **(0, 103)** and
**(380, 103)**. 110 is the crest elevation, so the prose looks like it
picked up the wrong number from the drawing. The figure is taken as
authoritative and ``test_the_prose_elevation_does_not_fit`` shows why:
at 110 the reservoir stands level with the crest and the answers move
away from both published values.

A detail worth noticing, because it says the geometry was read right:
the given circle is tangent to the foundation at x = 169.5 and daylights
on the upstream face at exactly (72, 24) — the point where the final
reservoir level meets the slope.

References:
    Corps of Engineers (1970). *Engineering and Design — Stability of
        Earth and Rock-Fill Dams*, EM 1110-2-1902, Appendix G.
    Corps of Engineers (2003). *Slope Stability*, EM 1110-2-1902,
        Appendix G: Procedures and Examples for Rapid Drawdown.
"""
from __future__ import annotations

import math

GAMMA_W = 62.4          # pcf

# Referee values, both on the circle below.
PUBLISHED = {"corps_2": 1.35, "duncan_wright": 1.44}

# The one slip surface the problem gives.
CIRCLE = dict(centre_x=169.5, centre_y=210.0, radius=210.0)

INITIAL_Y = 103.0       # from the figure; the prose says 110 — see above
FINAL_Y = 24.0


# ======================================================================
def _appendix_g(initial_y=INITIAL_Y, final_y=FINAL_Y, undrained=True,
                procedure="duncan_wright"):
    """The Appendix G slope, vertex by labelled vertex."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.drawdown_envelopes import REnvelope
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(380, 0), Vertex(380, 110),
        Vertex(350, 110), Vertex(330, 110), Vertex(312, 110),
        Vertex(296, 104), Vertex(268, 92), Vertex(246, 84),
        Vertex(222, 74), Vertex(201, 67), Vertex(170, 57),
        Vertex(135, 45), Vertex(105, 35),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("EM 1110-2-1902 Appendix G")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, initial_y),
                                    Vertex(385, initial_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, final_y),
                                    Vertex(385, final_y)], closed=False),
        btype=BoundaryType.DRAWDOWN))
    m = Material(
        name="Embankment", unit_weight=135.0, sat_unit_weight=135.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    m.undrained_behaviour = undrained
    m.drawdown_envelope = REnvelope(c_r=1200.0, phi_r_deg=16.0)
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.settings.groundwater.set_advanced_option("rapid_drawdown")
    p.settings.groundwater.rapid_drawdown_method = procedure
    return p


def _circle(**kw):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**{**CIRCLE, **kw})


def _run(project, procedure, surface=None, n=50):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    return rapid_drawdown_fos(project, surface or _circle(),
                              BishopSimplified(), num_slices=n,
                              procedure=procedure)


# ======================================================================
class TestTheGivenCircle:
    """Rule 1, with the surface handed to us so the search cannot help."""

    def test_the_corps_two_stage_reproduces_its_referee_value(self):
        r = _run(_appendix_g(), "corps_2")
        assert math.isclose(r.fos, PUBLISHED["corps_2"], rel_tol=0.03), (
            f"Corps 2-stage: {r.fos:.4f} vs referee {PUBLISHED['corps_2']}")

    def test_duncan_wright_wong_reproduces_its_referee_value(self):
        r = _run(_appendix_g(), "duncan_wright")
        assert math.isclose(r.fos, PUBLISHED["duncan_wright"],
                            rel_tol=0.03), (
            f"DWW 3-stage: {r.fos:.4f} vs referee "
            f"{PUBLISHED['duncan_wright']}")

    def test_the_gap_between_the_two_procedures_is_the_published_one(self):
        """The ratio, which is where ``min(R, effective)`` shows up.

        Nearly everything else about the model — the slicing, the unit
        weights, the ponded load — is common to both runs and cancels
        here. What does not cancel is that the Corps evaluates a
        composite envelope where Duncan-Wright-Wong interpolate a K_c = 1
        one, so 1.35/1.44 is close to a direct reading of that rule.
        """
        corps = _run(_appendix_g(), "corps_2").fos
        dww = _run(_appendix_g(), "duncan_wright").fos
        published = PUBLISHED["corps_2"] / PUBLISHED["duncan_wright"]
        assert math.isclose(corps / dww, published, rel_tol=0.02), (
            f"ratio {corps / dww:.4f} vs published {published:.4f}")


# ======================================================================
class TestTheGeometryIsTheOneOnTheDrawing:
    """Independent checks that the vertices were read correctly."""

    def test_the_circle_is_tangent_to_the_foundation(self):
        """centre_y == radius, so the lowest point sits on y = 0."""
        assert math.isclose(CIRCLE["centre_y"], CIRCLE["radius"])

    def test_the_circle_daylights_where_the_final_level_meets_the_slope(self):
        """The upstream face is 3:1 from the toe, so y = x/3 there.

        Solving the circle against that line gives x = 72, y = 24 — the
        final reservoir elevation exactly. A misread vertex on the face
        would break this coincidence, so it is a check on the drawing
        having been transcribed and not approximated.
        """
        cx, cy, r = CIRCLE["centre_x"], CIRCLE["centre_y"], CIRCLE["radius"]
        # (x - cx)^2 + (x/3 - cy)^2 = r^2
        a = 1.0 + 1.0 / 9.0
        b = -2.0 * cx - 2.0 * cy / 3.0
        c = cx * cx + cy * cy - r * r
        x = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
        assert math.isclose(x, 72.0, abs_tol=0.05)
        assert math.isclose(x / 3.0, FINAL_Y, abs_tol=0.02)

    def test_the_prose_elevation_would_not_have_changed_the_verdict(self):
        """Rule 6: the 103/110 discrepancy is reported AND measured.

        The first version of this test assumed 110 ft would move the
        answers away from the referee values and so prove the figure
        right. It does not. Both procedures move by about 0.5 %, an
        order of magnitude less than the agreement being claimed:

            Corps 2-stage ... 1.3335 at 103 ft, 1.3261 at 110 ft
            DWW 3-stage ..... 1.4333 at 103 ft, 1.4258 at 110 ft

        The reason is that the extra 7 ft of reservoir sits above the
        top of the slip surface's daylight point on the upstream face,
        where it adds ponded load and pore pressure in near-balance. So
        the figure is still what the geometry is taken from, but nothing
        here rests on that choice — which is worth knowing, because it
        is the one place the source contradicts itself.
        """
        for procedure, published in PUBLISHED.items():
            at_103 = _run(_appendix_g(initial_y=INITIAL_Y), procedure).fos
            at_110 = _run(_appendix_g(initial_y=110.0), procedure).fos
            assert abs(at_110 / at_103 - 1.0) < 0.015, (
                f"{procedure}: {at_103:.4f} at 103 ft against "
                f"{at_110:.4f} at 110 ft — the level now matters and the "
                f"discrepancy in the source has to be resolved")
            assert math.isclose(at_110, published, rel_tol=0.03)


# ======================================================================
class TestTheOrderingHoldsHereToo:
    """Structural facts, independent of any published number."""

    def test_the_corps_is_the_most_conservative(self):
        corps = _run(_appendix_g(), "corps_2").fos
        lk = _run(_appendix_g(), "lowe_karafiath").fos
        dww = _run(_appendix_g(), "duncan_wright").fos
        assert corps < dww <= lk

    def test_stage_one_stands_well_above_unity(self):
        """The procedure assumes the slope stood up with the reservoir
        full; on this case it does, by a wide margin."""
        r = _run(_appendix_g(), "duncan_wright")
        assert r.fos_stage1 > 1.5
        assert r.fos_stage1 > r.fos_stage2
