# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The ground surface of a boundary with a VERTICAL face is a step, not a ramp.

WHAT INVARIANT THIS PROTECTS. ``ground_surface`` is the one definition of the
ground in this project, and everything downstream reads it: the slicer takes
the weight of every slice from it, the search cuts the arc against it, the
optimiser snaps vertices to it and the canvas draws against it. It is built by
sampling ``upper_y_at`` — the upper envelope of the closed polygon — at the
abscissae where the envelope can change slope, and joining the samples with
straight lines.

That construction is exact only while the envelope is CONTINUOUS. It is not,
the moment the boundary has a vertical face: a retaining wall jumps from the
bench in front of it to its own crest at one abscissa, and a polyline whose x
increases strictly cannot hold a jump. Until v0.1.114 it drew a RAMP up the
face and every consumer believed in the soil under it. On a five-vertex model,
``(0,0) (30,0) (30,10) (10,10) (10,0)``, the flat bench between x = 0 and
x = 10 came back as a 45-degree ramp — ``upper_y_at(5) = 0`` against
``ground_surface`` reading 5.

THE CASE, AND WHY IT IS NOT ARBITRARY. Verification problem 59 of the reference
bank — Pockoski and Duncan (2000), their fifth test slope — is a 20 ft tieback
wall in sand. Its external boundary is labelled vertex by vertex in figure 59.1
and carries a vertical face from (0, 20) down to (0, 0) with a flat bench
running left from the toe to (-10, 0). Measured on 0.1.113: 100 ft2 of soil
that is not there, and the sliding mass the slicer weighed came out 26 % heavy.

WHAT ELSE THE RAMP DID, AND IT IS WORSE THAN THE WEIGHT. Erasing the bench
erases a GROUND CROSSING. The arc of the circle figure 59.2 publishes reaches
the ground exactly at the toe of the wall, which splits the circle into two
sliding masses that touch at a point; with the bench replaced by the ramp that
crossing does not exist, ``candidate_chords`` returns a single chord, and OGR
weighed a 53 ft mass where the reference analyses a 12.6 ft one. The panel of
figure 59.2 publishes both endpoints of its own surface — left (0.000, 0.000),
right (12.583, 24.580) — which is what lets this be checked against something
external rather than against what the code prints.

ONE SUBTLETY THAT COST AN HOUR, AND IT BELONGS HERE. The published radius,
43.975, is ROUNDED. With it the arc passes 0.00145 ft BELOW the toe vertex and
the two masses are genuinely one, so the circle must NOT split — and it does
not. The radius that puts the arc exactly through (0, 0) is 43.973965, and that
is the one that discriminates. A test written on the published rounding alone
would have passed over the defect.

THREE THINGS ARE ASSERTED AND NONE OF THEM IS A NUMBER THIS CODE PRINTED:

* the IDENTITY — the polyline must reproduce ``upper_y_at`` at every abscissa.
  ``upper_y_at`` is the definition of the envelope and reaches it by another
  road, a maximum over the edges, so this is an identity and not a snapshot.
  It is measured as the AREA between the two curves, which must be zero;
* the AREA — for a boundary with a vertical face, the mass the slicer weighs
  must be the mass the polygon encloses, measured with Shapely, an independent
  implementation. It has to converge as the slices are refined, because what is
  left after the fix is ordinary chord-versus-arc discretisation;
* the PUBLISHED ENDPOINTS — the two masses of the problem-59 circle must fall
  on the endpoints the reference prints in its own results panel.

And, because a fix that changes no number is not a fix (rule 7), the factor of
safety on that circle has to MOVE: the ramp was carrying weight. It does, by
8.1 % on the dry model built here and by 9.2 % on the bank's own model, which
adds the water table — and DOWNWARDS, which was not the first guess: the
invented wedge sits over the bench, on the toe half of the mass, where weight
drives more than it resists.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: A vertical cut, five vertices, nothing else. The smallest model that shows
#: the defect: flat bench, vertical face, flat crest.
_CUT = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (10.0, 10.0), (10.0, 0.0)]

#: Problem 59, figure 59.1, labelled vertex by vertex (feet).
_P59_EXT = [(-50.0, -30.0), (40.0, -30.0), (40.0, 35.0), (0.0, 20.0),
            (0.0, 0.0), (-10.0, 0.0), (-50.0, -15.0)]

#: Figure 59.2 results panel: centre and radius of the critical surface.
_P59_CENTRE = (-30.872, 31.315)
_P59_RADIUS = 43.975

#: Figure 59.2 results panel: "Left Slip Surface Endpoint" and "Right Slip
#: Surface Endpoint" of that same surface.
_P59_LEFT_END = (0.0, 0.0)
_P59_RIGHT_END = (12.583, 24.580)

#: The radius that puts the arc exactly through the published left endpoint.
#: See the module docstring: the published 43.975 is rounded and misses it.
_P59_RADIUS_EXACT = math.hypot(_P59_CENTRE[0], _P59_CENTRE[1])


# ----------------------------------------------------------------------
def _verts(pairs):
    from ogr_core.geometry import Vertex
    return [Vertex(x, y) for x, y in pairs]


def _gap_area(pairs, n=40000):
    """Area between ``upper_y_at`` and the polyline ``ground_surface`` returns.

    Zero for an envelope that carries its jumps, and the area of the invented
    soil for one that ramps across them.
    """
    from ogr_core.geometry import envelope_y_at, ground_surface, upper_y_at
    vs = _verts(pairs)
    profile = ground_surface(vs)
    x0 = min(v.x for v in vs)
    x1 = max(v.x for v in vs)
    dx = (x1 - x0) / n
    area = 0.0
    for k in range(n + 1):
        x = x0 + dx * k
        truth = upper_y_at(vs, x)
        drawn = envelope_y_at(profile, x)
        if truth is None or drawn is None:
            continue
        area += abs(drawn - truth) * dx
    return area


def _p59_project():
    """Problem 59 as far as this file needs it: the boundary and the sand.

    Built here and not loaded from the bank, which lives outside this
    repository. Table 59.1: sand, c = 0, phi = 30 deg, gamma = 120 pcf. No
    water table and no tieback — neither is needed to measure a ground
    envelope, and leaving them out keeps this file from depending on the
    parts of that model that were only ever read off a figure.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    p = Project("Slide2 #59 - tieback wall in sand")
    ext = Polyline(vertices=_verts(_P59_EXT), closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    sand = Material(name="Sand", unit_weight=120.0, sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0))
    p.materials = [sand]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), sand.id)
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    return p


def _p59_circle(radius=_P59_RADIUS):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=_P59_CENTRE[0], centre_y=_P59_CENTRE[1],
                      radius=radius)


def _sliced_area(project, surface, num_slices):
    """The mass the slicer weighs, and the same mass measured with Shapely."""
    from shapely.geometry import Polygon
    from ogr_slip2d.slicer import slice_surface

    sl = slice_surface(project, surface, num_slices=num_slices)
    if sl is None:
        return None
    slices = sl.slices if hasattr(sl, "slices") else sl
    ogr = sum(
        (s.top_y_mid - 0.5 * (s.base_y_left + s.base_y_right))
        * (s.base_x_right - s.base_x_left) for s in slices)
    xs = [slices[0].base_x_left] + [s.base_x_right for s in slices]
    lid = max(v[1] for v in _P59_EXT) + 1e4
    arc = [(x, surface.base_y_at(x)) for x in xs]
    mass = Polygon(arc + [(xs[-1], lid), (xs[0], lid)]).intersection(
        Polygon(_P59_EXT))
    return ogr, mass.area


def _ramped_profile():
    """The profile this module produced BEFORE v0.1.114, rebuilt on purpose.

    Not a stored snapshot: the same breakpoints, sampled the same way, joined
    straight across the jump. It is the only honest way to show that the fix
    moves a number, and it regenerates from the geometry if the geometry ever
    changes.
    """
    import ogr_core.geometry.ground as G
    from ogr_core.geometry import Polyline, Vertex
    vs = _verts(_P59_EXT)
    span = max(v.x for v in vs) - min(v.x for v in vs)
    tol = 1e-9 * span
    return Polyline(vertices=[Vertex(x, G.upper_y_at(vs, x, tol))
                              for x in G._breakpoints(vs, tol)])


# ----------------------------------------------------------------------
class TestTheEnvelopeIsTheDefinition:
    """The polyline must BE the envelope, not an interpolation of it."""

    def test_the_five_vertex_cut_keeps_its_bench(self):
        from ogr_core.geometry import envelope_y_at, ground_surface
        profile = ground_surface(_verts(_CUT))
        for x in (0.0, 2.0, 5.0, 8.0, 9.9):
            assert abs(envelope_y_at(profile, x)) < 1e-9, (
                x, envelope_y_at(profile, x))
        for x in (10.0, 15.0, 30.0):
            assert abs(envelope_y_at(profile, x) - 10.0) < 1e-9, x

    def test_the_face_is_carried_as_a_vertical_segment(self):
        from ogr_core.geometry import ground_surface
        vs = ground_surface(_verts(_CUT)).vertices
        at_face = [v for v in vs if abs(v.x - 10.0) < 1e-9]
        assert len(at_face) == 2, [(v.x, v.y) for v in vs]
        assert {round(v.y, 9) for v in at_face} == {0.0, 10.0}, (
            [(v.x, v.y) for v in at_face])

    def test_no_invented_soil_on_either_model(self):
        assert _gap_area(_CUT) < 1e-6, _gap_area(_CUT)
        assert _gap_area(_P59_EXT) < 1e-6, _gap_area(_P59_EXT)

    def test_a_slope_without_a_vertical_face_is_untouched(self):
        # An ordinary slope must gain nothing: a fix that steps where there
        # is no step would move every model in the suite.
        plain = [(0, 0), (60, 0), (60, 30), (40, 30), (20, 10), (0, 10)]
        from ogr_core.geometry import ground_surface
        vs = ground_surface(_verts(plain)).vertices
        assert len(vs) == len({round(v.x, 9) for v in vs}), (
            [(v.x, v.y) for v in vs])
        assert _gap_area(plain) < 1e-9

    def test_the_floor_steps_too(self):
        # The lower envelope has the defect in mirror image, and Composite
        # Surfaces makes a slip surface follow it.
        from ogr_core.geometry import bedrock_surface, envelope_y_at
        stepped = [(0.0, 0.0), (10.0, 0.0), (10.0, -8.0), (30.0, -8.0),
                   (30.0, 12.0), (0.0, 12.0)]
        floor = bedrock_surface(_verts(stepped))
        assert abs(envelope_y_at(floor, 5.0, upper=False)) < 1e-9
        assert abs(envelope_y_at(floor, 20.0, upper=False) + 8.0) < 1e-9


class TestTheMassWeighedIsTheMassEnclosed:
    """Shapely is the independent measurement, and it must agree."""

    def test_the_area_converges_on_the_polygon(self):
        p = _p59_project()
        previous = None
        for n in (200, 800, 3200):
            ogr, truth = _sliced_area(p, _p59_circle(), n)
            error = abs(ogr - truth) / truth
            assert error < 0.01, (n, ogr, truth)
            if previous is not None:
                # Refining must help. Before v0.1.114 the gap was invented
                # soil, and refining does not touch that.
                assert error < previous, (n, error, previous)
            previous = error
        assert previous < 5e-4, previous


class TestTheTwoMassesOfProblem59:
    """The reference publishes both endpoints of its own critical surface."""

    def test_the_published_radius_is_rounded_and_does_not_split(self):
        from ogr_core.geometry import ground_surface
        arc_at_toe = _p59_circle().base_y_at(_P59_LEFT_END[0])
        assert -0.005 < arc_at_toe < 0.0, arc_at_toe
        chords = _p59_circle().candidate_chords(
            ground_surface(_verts(_P59_EXT)))
        assert len(chords) == 1, chords

    def test_the_exact_arc_splits_at_the_toe_of_the_wall(self):
        from ogr_core.geometry import ground_surface
        circle = _p59_circle(_P59_RADIUS_EXACT)
        assert abs(circle.base_y_at(_P59_LEFT_END[0])) < 1e-9
        chords = circle.candidate_chords(ground_surface(_verts(_P59_EXT)))
        assert len(chords) == 2, chords
        assert abs(chords[0][1] - _P59_LEFT_END[0]) < 1e-6, chords
        assert abs(chords[1][0] - _P59_LEFT_END[0]) < 1e-6, chords

    def test_the_right_mass_is_the_one_the_panel_publishes(self):
        from ogr_core.geometry import ground_surface
        circle = _p59_circle(_P59_RADIUS_EXACT)
        _, right = circle.candidate_chords(ground_surface(_verts(_P59_EXT)))
        x_l, x_r = right
        assert abs(x_l - _P59_LEFT_END[0]) < 0.01, right
        # The panel rounds its endpoints to three decimals and the radius it
        # prints is rounded too, so a hundredth of a foot is the resolution
        # of the published datum and not a tolerance chosen to pass.
        assert abs(x_r - _P59_RIGHT_END[0]) < 0.03, (x_r, _P59_RIGHT_END)
        assert abs(circle.base_y_at(x_r) - _P59_RIGHT_END[1]) < 0.2, (
            circle.base_y_at(x_r), _P59_RIGHT_END)


class TestTheRampWasCarryingWeight:
    """Rule 7: a fix that moves no number is worth nothing."""

    def test_the_ramp_moves_bishop_by_almost_a_tenth(self):
        import ogr_slip2d.slicer as SL
        from ogr_slip2d.methods import get_method

        p = _p59_project()
        method = get_method("bishop_simplified")()

        def fos():
            surface = _p59_circle()
            sl = SL.slice_surface(p, surface, num_slices=50)
            assert sl is not None
            return method.compute_fos(p, surface, sl)

        stepped = fos()
        assert stepped is not None and stepped.converged

        ramp = _ramped_profile()
        assert len(ramp.vertices) == 4, [(v.x, v.y) for v in ramp.vertices]
        real = SL._ground_surface_from_external
        try:
            SL._ground_surface_from_external = lambda external: ramp
            ramped = fos()
        finally:
            SL._ground_surface_from_external = real
        assert ramped is not None and ramped.converged
        # Measured -8.1 % on this dry model (1.0959 stepped against 1.0074
        # ramped) and -9.2 % on the bank's own model, which adds the water
        # table (1.1497 against 1.0439). The bar is set below both because
        # what the assertion has to exclude is numerical noise, not pin a
        # value.
        assert abs(ramped.fos - stepped.fos) > 0.05 * stepped.fos, (
            ramped.fos, stepped.fos)
        # The SIGN, and it is worth writing down because the first guess was
        # the other one: the ramp LOWERS the factor here. The invented wedge
        # sits over the bench, on the toe half of the mass, where its weight
        # drives more than it resists. That is this geometry's answer and not
        # a rule — a phantom wedge behind the crest would push the other way.
        assert ramped.fos < stepped.fos, (ramped.fos, stepped.fos)

    def test_the_state_is_restored(self):
        # Rule 5: this file monkey-patches the slicer, so it has to prove it
        # put it back — a leaked profile would break unrelated files and only
        # when the whole suite runs.
        import ogr_slip2d.slicer as SL
        from ogr_core.geometry import ground_surface
        assert SL._ground_surface_from_external(
            _p59_project().external_boundary()).vertices[2].y == 0.0
        assert len(ground_surface(_verts(_P59_EXT)).vertices) == 5
