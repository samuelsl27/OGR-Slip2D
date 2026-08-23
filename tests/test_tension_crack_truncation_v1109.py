# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A tension crack TERMINATES the slip surface. That is the invariant here.

From v0.1.7 to v0.1.108 it did not. The crack only ever added a water
thrust, and only when there was water in it, so a DRY crack changed
nothing whatsoever and a wet one changed the wrong thing. The arc ran on
past the crack to its intersection with the ground, and every metre of
that extra arc contributed shear resistance across a plane that cannot
carry any. Ten problems of the verification bank have a tension crack;
none of them reproduced its published factor of safety, and every error
was on the **unsafe** side, because arc in excess is resistance in
excess.

What a tension crack does, and where each rule comes from
---------------------------------------------------------
Soil cannot carry tension, so near the crest of a slope the interslice
forces of a limit-equilibrium solution go negative and the shear
resistance they imply is fictitious. A tension crack removes it by
ending the slip surface where it reaches the crack, and closing the
failure mass with a VERTICAL wall up to the ground surface. The soil
between that wall and the arc keeps all of its weight — it drives, and
it has no base of its own to resist on. Duncan & Wright (2005), *Soil
Strength and Slope Stability*, chapter 14, and the classical treatments
that shorten the arc while leaving the wedge in the weight.

Three consequences are tested one by one below:

* **only the crest end is truncated.** The crack forms at the head of the
  slide; the toe is in compression. Soil that happens to lie inside the
  crack zone at the TOE end therefore keeps every bit of its strength.
* **the crest must be inside the crack zone** for anything to happen.
* **a surface with no shear plane at all** — one lying entirely inside
  the crack zone — is discarded rather than answered.

Why the tests are shaped the way they are
-----------------------------------------
The strongest checks here need no published number at all:

1. a homogeneous φ = 0 slope, where moment equilibrium gives
   ``F = c·L_arc·R / M`` in closed form. With a tension crack, ``L_arc``
   is the TRUNCATED arc and ``M`` is the driving moment of the whole
   mass, wedge included — so one identity pins the truncation and the
   weight together. Both sides are computed here, by Simpson quadrature
   over the geometry, and never from the slices under test;
2. the geometric identity ``base_y(x_end) == crack_line_y(x_end)``,
   checked against the model's own crack boundary.

The published anchor is ACADS 1(b) (Giam & Donald 1989), whose referee
factor of safety is 1.65. It is deliberately the last test and not the
first: a factor of safety can be right for the wrong reasons, and the
two identities above cannot.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.geometry.tension_crack import (
    TensionCrackProperties, WaterLevelMode,
)
from ogr_core.hydraulic.water_surfaces import interp_y_on_polyline
from ogr_core.materials import Material
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project import Project
from ogr_slip2d.methods import get_method
from ogr_slip2d.slicer import _ground_surface_from_external, slice_surface
from ogr_slip2d.surface import SlipCircle, SlipSurface


# ======================================================================
# 1. The φ = 0 slope, and its closed form
# ======================================================================
#
# Ground: flat at y = 20 out to x = 30, a 2:3 face up to (60, 40), flat
# at y = 40 from there. The crest is on the RIGHT, by twenty metres, so
# no test below depends on which failure direction happens to be
# declared — that is a separate question with its own file.
_C = 40.0
_GAMMA = 19.0
_CIRCLE = dict(centre_x=55.0, centre_y=58.0, radius=34.0)


def _ground_y(x: float) -> float:
    """The profile above, written out so the closed form owns a copy.

    Deliberately NOT read from the project: a closed form that asks the
    code under test where the ground is has stopped being independent of
    it.
    """
    if x <= 30.0:
        return 20.0
    if x >= 60.0:
        return 40.0
    return 20.0 + (x - 30.0) * 20.0 / 30.0


def _phi0_slope(crack_y=None, mode=WaterLevelMode.DRY, cohesion=_C):
    """The slope above, with an optional HORIZONTAL crack at ``crack_y``."""
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 40),
        Vertex(60, 40), Vertex(30, 20), Vertex(0, 20)], closed=True)
    ext.ensure_ccw()
    p = Project("phi0 tension crack")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if crack_y is not None:
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, crack_y), Vertex(100, crack_y)],
            closed=False), btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(name="Clay", unit_weight=_GAMMA,
                            strength=MohrCoulomb(cohesion=cohesion,
                                                 friction_angle=0.0))]
    p.tension_crack_properties = TensionCrackProperties(mode=mode)
    return p


def _analysed(project, num_slices=160, circle=None):
    """Slice the fixture circle and hand back the surface AS ANALYSED."""
    c = circle if circle is not None else SlipCircle(**_CIRCLE)
    sl = slice_surface(project, c, num_slices=num_slices)
    return c, sl


def _fos(project, num_slices=160, method="bishop_simplified", circle=None):
    c, sl = _analysed(project, num_slices, circle)
    assert sl is not None, "the fixture surface must be sliceable"
    return float(get_method(method)(tolerance=1e-10)
                 .compute_fos(project, c, sl).fos)


def _closed_form(x_l: float, x_r: float, cohesion=_C) -> float:
    """``F = c·L_arc·R / M`` for a homogeneous φ = 0 mass.

    With φ = 0 and no pore pressure, Bishop's moment equation collapses
    to exactly this: the numerator ``Σ [c·b + (W − u·b)·tanφ] / m_α``
    becomes ``Σ c·b/cos α = c·L_arc`` and the denominator ``Σ W·sin α``
    is the driving moment divided by R. Bishop (1955).

    ``L_arc`` is the true arc length, R·Δθ, and ``M`` a Simpson
    quadrature of ``γ·(y_ground − y_arc)·(x − x_c)`` over the span, both
    computed here from the geometry alone.
    """
    cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
    l_arc = r * (math.asin((x_r - cx) / r) - math.asin((x_l - cx) / r))

    n = 20001                       # odd, so Simpson closes
    h = (x_r - x_l) / (n - 1)
    total = 0.0
    for i in range(n):
        x = x_l + i * h
        arc = cy - math.sqrt(max(r * r - (x - cx) ** 2, 0.0))
        f = _GAMMA * (_ground_y(x) - arc) * (x - cx)
        total += (1 if i in (0, n - 1) else (4 if i % 2 else 2)) * f
    moment = abs(total * h / 3.0)
    return cohesion * l_arc * r / moment


class TestTheClosedFormHoldsOnTheTruncatedArc:
    """The one test that pins truncation and weight to the same identity.

    Truncate the arc but drop the wedge above the crack and the driving
    moment falls, so the factor of safety rises. Keep the wedge but leave
    the arc alone and the resistance rises instead. Only the pair — short
    arc, whole mass — satisfies ``F = c·L_arc·R/M``, so only the pair
    passes here.
    """

    _CRACK_Y = 34.0

    def test_it_converges_to_the_closed_form(self):
        p = _phi0_slope(crack_y=self._CRACK_Y)
        errors = {}
        for n in (40, 160, 640):
            c, sl = _analysed(p, num_slices=n)
            assert sl is not None
            expected = _closed_form(c.x_left, c.x_right)
            got = float(get_method("bishop_simplified")(tolerance=1e-10)
                        .compute_fos(p, c, sl).fos)
            errors[n] = abs(got / expected - 1.0)
        # A slice base is a CHORD, so the sum of them approaches the arc
        # from below as O(1/n²) — see the note in ``slice_surface``. What
        # is asserted is that behaviour, not one lucky number.
        assert errors[40] < 2e-3, errors
        assert errors[640] < 1e-5, errors
        assert errors[640] < errors[160] < errors[40], errors

    def test_the_arc_really_was_shortened(self):
        """Otherwise the identity above could hold on the wrong arc."""
        bare, _ = _analysed(_phi0_slope(crack_y=None))
        cut, _ = _analysed(_phi0_slope(crack_y=self._CRACK_Y))
        assert math.isclose(bare.x_left, cut.x_left, rel_tol=1e-12)
        assert cut.x_right < bare.x_right - 4.0, (cut.x_right, bare.x_right)

    def test_a_dry_crack_moves_the_number(self):
        """Rule 7, on the case that used to be a no-op.

        The guard removed in v0.1.109 read ``not ...is_dry()``, so a dry
        tension crack was a control the user could set and the analysis
        could not feel. Adding the boundary must change the answer, and
        it must change it DOWNWARDS: the arc can only get shorter.
        """
        bare = _fos(_phi0_slope(crack_y=None))
        cut = _fos(_phi0_slope(crack_y=self._CRACK_Y))
        assert cut < bare, (cut, bare)
        assert (bare - cut) / bare > 0.01, (bare, cut)


# ======================================================================
# 2. Where the surface ends
# ======================================================================
class TestTheSurfaceEndsOnTheCrackLine:
    """A geometric identity, and stronger than any factor of safety.

    Anomalies A2-1 and A12-1 were both found this way: on verification
    problem 2 the reference publishes an exit at x = 53.776, where the
    circle meets the crack line, and OGR ran on to 56.043, where it meets
    the ground; on problem 12 the published entry is 19.570 and OGR gave
    17.585, two metres deeper into the crack.
    """

    def test_the_end_lands_on_the_crack_and_not_on_the_ground(self):
        crack_y = 34.0
        p = _phi0_slope(crack_y=crack_y)
        tc = next(b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK)
        c, sl = _analysed(p)
        assert sl is not None
        assert math.isclose(c.base_y_at(c.x_right), crack_y, abs_tol=1e-6)
        # …and that is NOT where the ground is, or the test is vacuous.
        ground = _ground_surface_from_external(p.external_boundary())
        assert interp_y_on_polyline(ground, c.x_right) > crack_y + 1.0
        assert math.isclose(
            interp_y_on_polyline(tc.polyline, c.x_right), crack_y,
            abs_tol=1e-9)

    def test_the_wall_runs_from_the_crack_up_to_the_ground(self):
        p = _phi0_slope(crack_y=34.0)
        c, _ = _analysed(p)
        x, y_bottom, y_top = c.tension_crack_wall
        assert math.isclose(x, c.x_right, rel_tol=1e-12)
        assert math.isclose(y_bottom, 34.0, abs_tol=1e-6)
        assert math.isclose(y_top, 40.0, abs_tol=1e-9)
        # The canvas draws from this list; a wall the drawing does not
        # know about leaves the surface stopping in mid-air.
        assert (x, y_bottom, y_top) in c.tension_cracks

    def test_the_last_slice_is_as_tall_as_the_crack(self):
        """The wedge above the crack is IN the mass, not cut off it.

        Its vertical face is the crack; its top is still the ground. If
        the mass had been cut at the crack instead of terminated there,
        the outermost slice would be flat.
        """
        p = _phi0_slope(crack_y=34.0)
        _, sl = _analysed(p, num_slices=40)
        assert sl.slices[-1].height > 5.0, sl.slices[-1].height


# ======================================================================
# 3. Only the crest end
# ======================================================================
class TestOnlyTheCrestEndIsTruncated:
    """The correction has an unsafe side and an OVER-corrected side.

    Read "a tension crack zone" as "a zone with no shear strength" and
    every slice whose base lies inside it loses its resistance — which is
    not what a tension crack is, and not what the reference does. On
    verification problem 2 five of twenty-five slices have their base
    inside the crack zone at the TOE end, and the published factor of
    safety is only reproduced with all five resisting.

    Here the crack is dropped to y = 26, low enough that the arc dives
    below it in the middle and is inside the zone at BOTH ends.
    """

    _CRACK_Y = 26.0

    def test_the_arc_crosses_the_crack_twice(self):
        """Otherwise this whole class tests nothing."""
        from ogr_slip2d.slicer import _surface_crossings

        p = _phi0_slope(crack_y=self._CRACK_Y)
        tc = next(b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK)
        bare, _ = _analysed(_phi0_slope(crack_y=None))
        crossings = _surface_crossings(bare, tc.polyline,
                                       bare.x_left, bare.x_right)
        assert len(crossings) == 2, crossings

    def test_the_crest_side_crossing_wins(self):
        """The rule, verbatim: only truncated to the first region
        from the crest."""
        from ogr_slip2d.slicer import _surface_crossings

        p = _phi0_slope(crack_y=self._CRACK_Y)
        tc = next(b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK)
        bare, _ = _analysed(_phi0_slope(crack_y=None))
        crossings = sorted(_surface_crossings(bare, tc.polyline,
                                              bare.x_left, bare.x_right))
        c, sl = _analysed(p)
        assert sl is not None
        # Crest on the right, so the RIGHTMOST crossing is the one.
        assert math.isclose(c.x_right, crossings[-1], rel_tol=1e-9)
        # The toe end is untouched, even though it too is inside the zone.
        assert math.isclose(c.x_left, bare.x_left, rel_tol=1e-12)

    def test_the_toe_end_keeps_its_strength(self):
        """The closed form again, and now it is doing a second job.

        ``F = c·L_arc·R/M`` counts cohesion over the WHOLE truncated arc,
        including the stretch that lies inside the crack zone at the toe.
        Strip the strength off those slices and the factor of safety
        drops below the identity; this asserts it does not.
        """
        p = _phi0_slope(crack_y=self._CRACK_Y)
        c, sl = _analysed(p, num_slices=640)
        assert sl is not None
        inside = [s for s in sl.slices if s.base_y_mid > self._CRACK_Y]
        assert len(inside) >= 3, "the fixture must have toe slices in the zone"
        expected = _closed_form(c.x_left, c.x_right)
        got = float(get_method("bishop_simplified")(tolerance=1e-10)
                    .compute_fos(p, c, sl).fos)
        assert math.isclose(got, expected, rel_tol=1e-5), (got, expected)


# ======================================================================
# 4. The surface that has no shear plane at all
# ======================================================================
class TestASurfaceInsideTheZoneIsDiscarded:
    """Anomaly A2-2, in the form that made the search fail.

    A circle of R = 1.58 m beside the crest of verification problem 2 —
    2.5 m² of soil, 50 kN of weight — was handed the FULL-depth crack
    thrust of 73.5 kN, more than its own weight, and came out at 0.96
    where the same circle without a crack gives 9.67. Bishop, Spencer and
    GLE all reported it as the critical surface. The search was not
    broken: it found, faithfully, the minimum of a field that was wrong.

    Such a surface has no shear plane. Every bit of it lies inside the
    zone that cannot resist, so there is no arc to write an equilibrium
    on and no wall for water to push against. It is discarded, which is
    what the reference reports too.
    """

    def _tiny(self):
        # Ground is flat at y = 40 for x ≥ 60; this circle daylights at
        # 78 and 84, and dips only to y = 37 — a metre above a crack at
        # y = 34.
        return SlipCircle(centre_x=81.0, centre_y=40.5, radius=3.5)

    def test_without_a_crack_it_is_an_ordinary_surface(self):
        p = _phi0_slope(crack_y=None)
        _, sl = _analysed(p, num_slices=20, circle=self._tiny())
        assert sl is not None
        assert len(sl) >= 3

    def test_with_the_crack_above_it_the_surface_is_refused(self):
        p = _phi0_slope(crack_y=34.0, mode=WaterLevelMode.FILLED)
        _, sl = _analysed(p, num_slices=20, circle=self._tiny())
        assert sl is None

    def test_and_it_never_becomes_the_critical_surface_of_a_search(self):
        """The end the anomaly was actually measured at.

        A refusal that the search does not honour would leave the same
        bogus minimum in the results, so the check is made on the answer
        the search reports, not on the slicer alone.
        """
        from ogr_slip2d.search import GridSearch

        p = _phi0_slope(crack_y=34.0, mode=WaterLevelMode.FILLED)
        res = GridSearch(method=get_method("bishop_simplified")(),
                         grid_x=(45.0, 85.0), grid_y=(40.0, 70.0),
                         grid_nx=7, grid_ny=7, radius_increment=6,
                         min_radius=2.0, num_slices=25,
                         min_area=0.0).run(p)
        crit = res.critical
        assert crit is not None
        # Every surface the search kept ends on the crack line or below
        # it; none is a sliver floating inside the zone.
        assert crit.surface.radius > 10.0, crit.surface.radius


# ======================================================================
# 5. The thrust is measured on the wall that exists
# ======================================================================
class TestTheThrustFollowsTheRealWall:
    """Anomaly A2-2 again, in its measurable form.

    The horizontal thrust on verification problem 2 came out at −73.46 kN
    for three different circles: the Bishop critical one, the Janbu one,
    and one that never reaches the crack base at all. 73.46 is
    ½·9.81·3.87², the crack's FULL depth — the geometry of the boundary,
    not of the surface.

    A sloping crack base gives two surfaces two different wall heights,
    and ½γ_w h² has to follow both.
    """

    def _sloping_crack(self, mode=WaterLevelMode.FILLED):
        """Same slope, but a crack base that is not parallel to the ground.

        The ground climbs 20 m over the face while the crack base climbs
        8 over the whole model, so the crack's depth varies along it —
        8.6 m where the upper flat begins, 4.0 m at the far edge — and
        two surfaces cutting it at different abscissas open walls of
        different heights.
        """
        p = _phi0_slope(crack_y=None, mode=mode)
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(30, 28.0), Vertex(100, 36.0)], closed=False),
            btype=BoundaryType.TENSION_CRACK))
        return p

    def _wall_and_thrust(self, project, circle):
        c, sl = _analysed(project, num_slices=60, circle=circle)
        assert sl is not None, "the fixture surface must be sliceable"
        return c.tension_crack_wall, sl.tension_crack_force, sl

    def test_two_different_walls_give_two_different_thrusts(self):
        p = self._sloping_crack()
        wall_a, f_a, _ = self._wall_and_thrust(
            p, SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0))
        wall_b, f_b, _ = self._wall_and_thrust(
            self._sloping_crack(),
            SlipCircle(centre_x=45.0, centre_y=44.0, radius=22.0))
        h_a = wall_a[2] - wall_a[1]
        h_b = wall_b[2] - wall_b[1]
        assert abs(h_a - h_b) > 0.5, (h_a, h_b)
        gamma_w = 9.81
        assert math.isclose(f_a, 0.5 * gamma_w * h_a ** 2, rel_tol=1e-9)
        assert math.isclose(f_b, 0.5 * gamma_w * h_b ** 2, rel_tol=1e-9)
        # …and therefore in the ratio of the squares, which is the shape
        # of the law rather than two numbers that happen to match.
        assert math.isclose(f_a / f_b, (h_a / h_b) ** 2, rel_tol=1e-9)

    def test_the_thrust_reaches_the_slice_at_the_wall(self):
        """Every LEM method reads it from the slice, not from ``Slices``."""
        p = self._sloping_crack()
        wall, force, sl = self._wall_and_thrust(
            p, SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0))
        loaded = [s for s in sl.slices if abs(s.water_force_h) > 1e-12]
        assert len(loaded) == 1, len(loaded)
        assert math.isclose(abs(loaded[0].water_force_h), force,
                            rel_tol=1e-12)
        # The wall is one END of the mass, so the loaded slice is the
        # outermost one on that side and cannot be anything else.
        assert loaded[0] is sl.slices[-1]

    def test_a_dry_crack_still_truncates_but_pushes_nothing(self):
        wet = self._sloping_crack(mode=WaterLevelMode.FILLED)
        dry = self._sloping_crack(mode=WaterLevelMode.DRY)
        c_wet, sl_wet = _analysed(wet, num_slices=60)
        c_dry, sl_dry = _analysed(dry, num_slices=60)
        assert c_wet.tension_crack_wall == c_dry.tension_crack_wall
        assert sl_wet.tension_crack_force > 0.0
        assert sl_dry.tension_crack_force == 0.0
        assert all(s.water_force_h == 0.0 for s in sl_dry.slices)


# ======================================================================
# 6. Non-circular surfaces
# ======================================================================
class TestANonCircularSurfaceTruncatesToo:
    """Error code −119 of the reference exists for exactly this.

    Four of the benchmark models with a tension crack are solved with
    Path Search, so a truncation that only knew about circles would leave
    them where they were.
    """

    def _polyline_surface(self):
        # A shallow wedge under the slope face, daylighting on the upper
        # flat at x = 75 where the ground is y = 40.
        return SlipSurface(polyline=Polyline(vertices=[
            Vertex(35.0, 23.33), Vertex(45.0, 22.0), Vertex(60.0, 26.0),
            Vertex(70.0, 34.0), Vertex(75.0, 40.0)], closed=False))

    def test_the_polyline_is_cut_at_the_crack(self):
        p = _phi0_slope(crack_y=34.0)
        s = self._polyline_surface()
        sl = slice_surface(p, s, num_slices=40)
        assert sl is not None
        x_l, x_r = s.x_range()
        assert x_r < 75.0 - 0.5, x_r
        assert math.isclose(s.base_y_at(x_r), 34.0, abs_tol=1e-6)
        assert s.tension_crack_wall is not None
        assert math.isclose(s.tension_crack_wall[0], x_r, rel_tol=1e-12)
        # The drawing follows the polyline itself, so the polyline has to
        # be the truncated one — and the wall has to be recorded, or the
        # drawn surface stops short of the ground.
        assert math.isclose(s.polyline.vertices[-1].x, x_r, rel_tol=1e-12)
        assert s.tension_crack_wall in s.tension_cracks

    def test_the_canvas_can_draw_the_wall_it_left(self):
        """Rule 3’s cousin: a result nobody can see is half a result.

        The polyline branch of ``SlipSurfaceItem`` drew the vertices and
        nothing else, so a truncated non-circular surface would have
        stopped in mid-air several metres below the ground it came from
        — the picture disagreeing with the number. The circular branch
        has drawn its crack since v0.1.82; this is the same list, on the
        same key.
        """
        try:
            from PySide6.QtWidgets import QApplication
            from ogr_gui.canvas.graphics_items import SlipSurfaceItem
        except Exception:                     # pragma: no cover - no Qt
            return
        QApplication.instance() or QApplication([])

        p = _phi0_slope(crack_y=34.0)
        s = self._polyline_surface()
        assert slice_surface(p, s, num_slices=40) is not None
        d = s.to_dict()
        assert d["tension_cracks"], "the wall has to survive to_dict"
        top = max(v.y for v in s.polyline.vertices)
        drawn = SlipSurfaceItem(d, fos=1.5).path().boundingRect()
        # The drawing reaches the GROUND, a wall above the last vertex.
        assert drawn.bottom() > top + 1.0, (drawn.bottom(), top)

    def test_slicing_it_twice_changes_nothing(self):
        """Idempotence, and it is not free.

        The crest of a truncated surface sits ON the crack line rather
        than above it, which is exactly the condition that stops a second
        pass — so this test also pins WHY the trigger is written the way
        it is. Without it a second slicing would find the surface's other
        crossing and cut the mass again.
        """
        p = _phi0_slope(crack_y=26.0)
        s = self._polyline_surface()
        assert slice_surface(p, s, num_slices=40) is not None
        first = s.x_range()
        assert slice_surface(p, s, num_slices=40) is not None
        assert s.x_range() == first
        assert len(s.tension_cracks) == 1, s.tension_cracks


# ======================================================================
# 7. The published anchor
# ======================================================================
def _acads_1b():
    """ACADS problem 1(b) — the slope of 1(a) with a water-filled crack.

    Source
    ------
    Giam, S.K. & Donald, I.B. (1989). *Example problems for testing soil
    slope stability programs.* Civil Engineering Research Report No.
    8/1989, Monash University. Problem **1(b)**: the homogeneous slope of
    1(a) with c' = 32 kPa, φ' = 10°, γ = 20 kN/m³, and a water-filled
    tension crack. Referee factor of safety **1.65**.

    The statement asks for "a suitable tension crack depth" rather than
    giving one, and the depth used here is the Rankine active depth,

        z = 2c / (γ·√Ka),   Ka = (1 − sin φ) / (1 + sin φ)

    Craig (1997), *Soil Mechanics*, 6th ed. — 3.8136 m for these
    properties. Computed rather than written out, so the number and the
    formula cannot drift apart.

    Geometry verbatim from 1(a), which is already in
    ``tests/test_acads_validation_v178.py``; it is repeated rather than
    imported because the runner does not import test modules from each
    other.
    """
    c, phi, gamma = 32.0, 10.0, 20.0
    ka = ((1.0 - math.sin(math.radians(phi)))
          / (1.0 + math.sin(math.radians(phi))))
    z = 2.0 * c / (gamma * math.sqrt(ka))

    ext = Polyline(vertices=[
        Vertex(20, 20), Vertex(70, 20), Vertex(70, 35),
        Vertex(50, 35), Vertex(30, 25), Vertex(20, 25)], closed=True)
    ext.ensure_ccw()
    p = Project("ACADS 1(b)")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(20, 25 - z), Vertex(30, 25 - z),
        Vertex(50, 35 - z), Vertex(70, 35 - z)], closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(name="Soil", unit_weight=gamma,
                            strength=MohrCoulomb(cohesion=c,
                                                 friction_angle=phi))]
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.FILLED)
    return p, z


# The search of the problem statement: a 20 x 20 interval grid over
# (31,34)–(47,49) with 11 circles per point. Shared by the class below,
# because running it twice would be the expensive thing in this file.
_CACHE: dict = {}


def _acads_1b_search(with_crack: bool = True):
    key = ("1b", with_crack)
    if key not in _CACHE:
        from ogr_slip2d.search import GridSearch

        p, _ = _acads_1b()
        if not with_crack:
            p.boundaries = [b for b in p.boundaries
                            if b.btype != BoundaryType.TENSION_CRACK]
        _CACHE[key] = GridSearch(
            method=get_method("bishop_simplified")(tolerance=1e-4),
            grid_x=(31.0, 47.0), grid_y=(34.0, 49.0),
            grid_nx=21, grid_ny=21, radius_increment=11,
            min_radius=3.0, num_slices=25, min_area=0.5).run(p)
    return _CACHE[key]


class TestACADS1bAgainstItsRefereeValue:
    """Giam & Donald (1989), problem 1(b). Referee 1.65.

    Tolerance
    ---------
    5 %, and the looseness is a property of the source rather than of
    this code. The referee value is one arbiter's answer to a problem
    with no known exact solution; the 1989 survey's own programs
    disagreed with each other by more than that, and the commercial
    program this benchmark suite is built against lands 3.3 % below the
    referee on this very problem. A tighter band here would be a band
    fitted to whichever answer we happened to get.

    The sharp checks on this model are the two below it, which need no
    published number at all.
    """

    _REFEREE = 1.65

    def test_the_search_finds_the_referee_value(self):
        fos = float(_acads_1b_search().critical.fos)
        assert abs(fos / self._REFEREE - 1.0) < 0.05, fos

    def test_the_crack_boundary_moves_the_answer(self):
        """Rule 7 on the published model, not on a fixture."""
        with_crack = float(_acads_1b_search(True).critical.fos)
        without = float(_acads_1b_search(False).critical.fos)
        assert with_crack < without, (with_crack, without)
        assert (without - with_crack) / without > 0.05, (without, with_crack)

    def test_the_critical_surface_ends_on_the_crack(self):
        """The geometric identity, on the published model.

        The verification bank measured this end at x = 53.776 for the
        crack depth its own figures resolve with (3.870 m); the Rankine
        depth used here is 3.814 m, so the crossing sits a few
        centimetres further along — which is the point: the end follows
        the crack, wherever the crack is put.
        """
        p, z = _acads_1b()
        tc = next(b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK)
        # The circle the reference publishes for this problem, evaluated
        # rather than searched for: this test is about geometry.
        c = SlipCircle(centre_x=37.562, centre_y=43.223, radius=20.228)
        sl = slice_surface(p, c, num_slices=25)
        assert sl is not None
        assert math.isclose(c.base_y_at(c.x_right),
                            interp_y_on_polyline(tc.polyline, c.x_right),
                            abs_tol=1e-6)
        assert math.isclose(c.x_right, 53.82, abs_tol=0.05), c.x_right
        # The wall is the full depth of the crack here, because the crest
        # daylights on the upper flat where the crack runs parallel to it.
        wall = c.tension_crack_wall
        assert math.isclose(wall[2] - wall[1], z, abs_tol=1e-6)
