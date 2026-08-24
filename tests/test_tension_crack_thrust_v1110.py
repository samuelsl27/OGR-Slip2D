# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The thrust of water in a tension crack is ½·γ_w·h_w², and h_w is the water
standing on the wall THIS surface opened — not the depth of the crack
boundary. That is the invariant here, and it is anomaly A2-2.

What went wrong, and how it was measured
----------------------------------------
Until v0.1.108 the thrust was resolved from the crack BOUNDARY, so every
surface under the same boundary got the same force. On verification
problem 2 the horizontal thrust came out at −73.46 kN for three different
circles — the Bishop critical one, the Janbu one, and a 1.58 m circle
beside the crest that never reaches the crack base at all. 73.46 is
½·9.81·3.87², the crack's full depth. That 1.58 m circle encloses 2.5 m²
of soil weighing 50 kN, so it was handed a thrust LARGER THAN ITS OWN
WEIGHT, returned 0.96 where the same circle without a crack returns 9.67,
and the search dutifully reported it as the critical surface. The search
was never broken: it was finding the true minimum of a wrongly computed
field.

v0.1.109 removed the cause rather than the symptom. Truncating the arc at
the crack (defect D13) leaves a vertical WALL, and the thrust is now
integrated over that wall, so the wet depth is the real one by
construction and a surface that opens no wall receives nothing.

Why an identity and not a snapshot
----------------------------------
A recorded force reproduces whatever the code does today, bug included.
The law has a shape — quadratic in depth — and the shape is what is
asserted: three water depths on the SAME wall give forces in the ratio of
the squares of those depths, and each equals ½·γ_w·h_w² computed here from
the geometry. Terzaghi (1943), *Theoretical Soil Mechanics*: the resultant
of a hydrostatic pressure distribution on a vertical face of height h_w,
acting at h_w/3 above its base.

Which of these tests can actually fail, measured and not assumed
---------------------------------------------------------------
The pre-0.1.109 algorithm was restored underneath this file and the whole
of it re-run: **five of the eleven tests fail on it**, and knowing which
six do not is the more useful half.

**Section 1 passes unchanged**, and that is worth writing down rather
than hiding. On a HORIZONTAL crack under a FLAT crest the depth at the
outermost slice and the height of the wall are the same number, so the
identity cannot tell the two implementations apart — which is also
exactly why the 73.46 kN of problem 2 looked right on the published
circle for a hundred versions. Section 1 pins the law; it does not catch
the bug. A first draft of this file stopped there and would have passed
on the defect it was named after.

What catches the bug is section 3, and by an unbounded margin rather than
a tolerance: a crack zone lying over the TOE of the slide opens no wall,
so the thrust is zero, while the old code found a slice inside the
boundary's x range and handed that surface **680.7 kN** on a crack it
never opened — dragging the factor of safety from 1.1112 to 0.7892, a
29 % fall out of a boundary the mechanism cannot see. That margin does
not shrink with the slice count, and the depth-read-half-a-slice-from-
the-wall difference does: at 60 slices it is 0.036 m, and it converges
away. A test whose discrimination vanishes as the mesh refines is a test
that will stop working.

Section 2 fails on the old code too, and while measuring it something
else fell out: under the old algorithm more water in the crack RAISED the
factor of safety (1.0714 empty → 1.1241 full). The thrust was landing on
a slice it did not belong to, with a sense that held the slope up.

Rule 7 is the other half of section 2. ``percent_filled`` has existed
since v0.1.7 and has a spin box in the dialog, but until now it was only
ever tested on ``TensionCrackProperties.water_level_at`` — a pure
function two layers below the analysis. Nothing checked that turning that
dial moves the FACTOR OF SAFETY, which is the only thing the user is
asking it to do.

The geometry, the closed form and the truncation itself belong to
``test_tension_crack_truncation_v1109.py``, whose fixtures are reused here
so the two files cannot drift apart.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_tension_crack_truncation_v1109 import (  # noqa: E402
    _CIRCLE, _analysed, _phi0_slope,
)

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex  # noqa: E402
from ogr_core.geometry.tension_crack import (  # noqa: E402
    TensionCrackProperties, WaterLevelMode,
)
from ogr_slip2d.methods import get_method  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

# The project default (``GroundwaterSettings.pore_fluid_unit_weight``).
# Written out rather than read from the project for the same reason the
# v1109 file writes out its ground profile: a closed form that asks the
# code under test for its own constants has stopped being independent.
_GAMMA_W = 9.81

# The crack of the fixture slope: horizontal at y = 34 under a crest at
# y = 40, so the wall the fixture circle opens is exactly 6 m tall. Same
# value as the v1109 file, deliberately — the two describe one wall.
_CRACK_Y = 34.0
_WALL_H = 6.0


def _thrust(mode, num_slices=160, circle=None, crack_y=_CRACK_Y, **kwargs):
    """Analyse the fixture and return ``(wall height, thrust, arm, FoS)``.

    Everything downstream of ``slice_surface`` is exercised: the thrust is
    read back from ``Slices`` and the factor of safety from a real method,
    so a force that is computed and then dropped — which is exactly what
    happened between v0.1.7 and v0.1.61 — cannot pass.
    """
    p = _phi0_slope(crack_y=crack_y)
    p.tension_crack_properties = TensionCrackProperties(mode=mode, **kwargs)
    c, sl = _analysed(p, num_slices=num_slices, circle=circle)
    assert sl is not None, "the fixture surface must be sliceable"
    wall = c.tension_crack_wall
    h_wall = 0.0 if wall is None else wall[2] - wall[1]
    fos = float(get_method("bishop_simplified")(tolerance=1e-10)
                .compute_fos(p, c, sl).fos)
    return h_wall, sl.tension_crack_force, sl.tension_crack_arm, fos


# ======================================================================
# 1. The law: ½·γ_w·h_w², at three different water depths
# ======================================================================
class TestTheThrustIsHalfGammaHSquaredAtEveryDepth:
    """The identity the anomaly is written against.

    Three fill levels on one 6 m wall. This section pins the LAW — that
    the force is quadratic in the water column and acts a third of the
    way up it — and it is the part that would catch a future change to
    the formula. It is not the part that catches A2-2: see the module
    docstring, and section 3.
    """

    _FRACTIONS = (25.0, 50.0, 100.0)

    def test_each_depth_matches_the_closed_form(self):
        for pct in self._FRACTIONS:
            h_wall, f, _, _ = _thrust(
                WaterLevelMode.PERCENT_FILLED, percent_filled=pct)
            assert math.isclose(h_wall, _WALL_H, abs_tol=1e-9), h_wall
            h_w = _WALL_H * pct / 100.0
            assert math.isclose(f, 0.5 * _GAMMA_W * h_w ** 2,
                                rel_tol=1e-12), (pct, f)

    def test_the_three_are_in_the_ratio_of_the_squares(self):
        """The shape of the law, not three numbers that happen to match."""
        forces = {pct: _thrust(WaterLevelMode.PERCENT_FILLED,
                               percent_filled=pct)[1]
                  for pct in self._FRACTIONS}
        for a in self._FRACTIONS:
            for b in self._FRACTIONS:
                assert math.isclose(forces[a] / forces[b], (a / b) ** 2,
                                    rel_tol=1e-12), (a, b, forces)
        # …and strictly increasing, so a monotone-but-wrong law is caught
        # as well as a constant one.
        assert forces[25.0] < forces[50.0] < forces[100.0], forces

    def test_the_line_of_action_is_a_third_of_the_way_up(self):
        """Terzaghi (1943): the centroid of a triangular distribution.

        The arm is measured from the crack line — the BASE of the water
        column — and not from the toe of the slope, which is why it is
        asserted against the wall's own bottom.
        """
        for pct in self._FRACTIONS:
            _, _, arm, _ = _thrust(WaterLevelMode.PERCENT_FILLED,
                                   percent_filled=pct)
            h_w = _WALL_H * pct / 100.0
            assert math.isclose(arm, _CRACK_Y + h_w / 3.0,
                                abs_tol=1e-9), (pct, arm)


# ======================================================================
# 2. Rule 7 — the dial has to move the number
# ======================================================================
class TestTheFillLevelMovesTheFactorOfSafety:
    """A control the analysis cannot feel is worse than no control.

    ``percent_filled`` was reachable from the dialog and covered by unit
    tests on ``water_level_at``, but nothing joined it to a factor of
    safety. This class is that join.

    It also fixes the SIGN, which is not a detail: run on the
    pre-0.1.109 algorithm these two tests fail because more water gave a
    HIGHER factor of safety — 1.0714 with the crack empty against 1.1241
    with it full. Water in a crack cannot stabilise a slope.
    """

    def test_more_water_means_a_lower_factor(self):
        fos = {pct: _thrust(WaterLevelMode.PERCENT_FILLED,
                            percent_filled=pct)[3]
               for pct in (0.0, 25.0, 50.0, 100.0)}
        assert fos[0.0] > fos[25.0] > fos[50.0] > fos[100.0], fos
        # And by an amount worth having, not a rounding digit.
        assert (fos[0.0] - fos[100.0]) / fos[0.0] > 0.01, fos

    def test_an_empty_crack_still_truncates(self):
        """0 % is not "no crack": the arc is short either way.

        A dry crack used to skip the truncation as well as the thrust,
        which is the defect that hid this one. Here the wall exists at
        0 % and carries no water.
        """
        h_wall, f, _, _ = _thrust(WaterLevelMode.PERCENT_FILLED,
                                  percent_filled=0.0)
        assert math.isclose(h_wall, _WALL_H, abs_tol=1e-9), h_wall
        assert f == 0.0, f

    def test_filled_to_depth_measures_from_the_wall_top(self):
        """The third route, and the one the bank actually uses.

        Verification problem 27 specifies "an 11 ft crack with 6 ft of
        water" as ``FILLED_TO_DEPTH`` with depth = 5. The depth comes off
        the top of THE WALL — the ground where the surface exits — so a
        6 m wall with depth 2 leaves 4 m of water, whatever the boundary
        is doing elsewhere.
        """
        for depth in (1.5, 3.0, 4.5):
            h_wall, f, _, _ = _thrust(WaterLevelMode.FILLED_TO_DEPTH,
                                      depth=depth)
            h_w = _WALL_H - depth
            assert math.isclose(h_wall, _WALL_H, abs_tol=1e-9), h_wall
            assert math.isclose(f, 0.5 * _GAMMA_W * h_w ** 2,
                                rel_tol=1e-12), (depth, f)

    def test_filled_to_depth_moves_the_factor_too(self):
        fos = [_thrust(WaterLevelMode.FILLED_TO_DEPTH, depth=d)[3]
               for d in (4.5, 3.0, 1.5)]
        assert fos[0] > fos[1] > fos[2], fos


# ======================================================================
# 3. The wall decides which surfaces get a thrust at all
# ======================================================================
class TestOnlyASurfaceThatOpensAWallIsPushed:
    """A2-2 in the form that discriminates, and by how much.

    A crack zone over the TOE of the slide opens no wall: the crack forms
    at the head of a slide, and the toe is in compression. The surface
    therefore receives nothing. The old algorithm asked a different
    question — "is there a crack boundary somewhere under this mass?" —
    found a slice inside the boundary's x range, and read the depth
    there.

    The gap is not a tolerance. On the fixture below the answer is 0 kN
    against 680.7 kN — a factor of safety of 1.1112 against 0.7892 — and
    unlike a depth read half a slice from the wall it does not shrink as
    the slice count grows.
    """

    _TOE_CRACK = [Vertex(0, 18.0), Vertex(45, 18.0)]
    _B = dict(centre_x=45.0, centre_y=44.0, radius=22.0)

    def _with_crack(self, vertices, mode=WaterLevelMode.FILLED, **kwargs):
        p = _phi0_slope(crack_y=None)
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=list(vertices), closed=False),
            btype=BoundaryType.TENSION_CRACK))
        p.tension_crack_properties = TensionCrackProperties(
            mode=mode, **kwargs)
        return p

    def test_a_toe_side_crack_zone_pushes_nothing(self):
        p = self._with_crack(self._TOE_CRACK)
        c, sl = _analysed(p, num_slices=60)
        assert sl is not None, "the fixture surface must be sliceable"
        assert c.tension_crack_wall is None, c.tension_crack_wall
        assert sl.tension_crack_force == 0.0, sl.tension_crack_force
        assert all(s.water_force_h == 0.0 for s in sl.slices)

    def test_the_mass_really_does_reach_that_crack_zone(self):
        """Otherwise the test above is vacuous.

        Six slices of this mass have their centre inside the boundary's
        x range, and the ground stands 11.8 m above the crack line at the
        rightmost of them. Those are precisely the slices the old
        algorithm searched, and 680.7 kN is ½·9.81·11.78².
        """
        p = self._with_crack(self._TOE_CRACK)
        _, sl = _analysed(p, num_slices=60)
        inside = [s for s in sl.slices if 0.0 <= s.x_centre <= 45.0]
        assert len(inside) >= 5, len(inside)
        assert max(s.x_centre for s in inside) > 44.0

    def test_a_toe_side_crack_zone_does_not_move_the_factor_either(self):
        """Rule 7 in reverse: a boundary the mechanism cannot see.

        The counterpart of ``test_a_dry_crack_moves_the_number`` in the
        v1109 file. There, adding a crest crack MUST change the answer;
        here, adding a toe-side one must NOT — and the old code moved it.
        """
        bare, sl_bare = _analysed(_phi0_slope(crack_y=None), num_slices=60)
        p = self._with_crack(self._TOE_CRACK)
        cut, sl_cut = _analysed(p, num_slices=60)
        f_bare = float(get_method("bishop_simplified")(tolerance=1e-10)
                       .compute_fos(_phi0_slope(crack_y=None), bare,
                                    sl_bare).fos)
        f_cut = float(get_method("bishop_simplified")(tolerance=1e-10)
                      .compute_fos(p, cut, sl_cut).fos)
        assert math.isclose(f_bare, f_cut, rel_tol=1e-9), (f_bare, f_cut)

    def test_two_walls_at_the_same_fill_level_differ_by_the_squares(self):
        """The law again, now on walls of two different heights.

        The crack base climbs 8 m over the model while the face climbs
        20, so its depth varies along it and two circles cut it at
        different abscissas: walls of 6.44 m and 8.19 m under the same
        60 % fill.
        """
        pct = 60.0
        sloping = [Vertex(30, 28.0), Vertex(100, 36.0)]
        out = []
        for cd in (_CIRCLE, self._B):
            p = self._with_crack(sloping, WaterLevelMode.PERCENT_FILLED,
                                 percent_filled=pct)
            c, sl = _analysed(p, num_slices=60, circle=SlipCircle(**cd))
            assert sl is not None and c.tension_crack_wall is not None
            wall = c.tension_crack_wall
            out.append((wall[2] - wall[1], sl.tension_crack_force))
        (h_a, f_a), (h_b, f_b) = out
        assert abs(h_a - h_b) > 1.0, (h_a, h_b)
        f = pct / 100.0
        assert math.isclose(f_a, 0.5 * _GAMMA_W * (f * h_a) ** 2,
                            rel_tol=1e-12), (h_a, f_a)
        assert math.isclose(f_b, 0.5 * _GAMMA_W * (f * h_b) ** 2,
                            rel_tol=1e-12), (h_b, f_b)
        assert math.isclose(f_a / f_b, (h_a / h_b) ** 2, rel_tol=1e-12)
