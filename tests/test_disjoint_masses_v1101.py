# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A surface that cuts the ground four times has to answer for the WORST mass.

WHAT INVARIANT THIS PROTECTS. A circle that crosses the ground more than twice
does not define one failure mechanism: it defines several DISJOINT sliding
masses, and the factor of safety of that circle is the lowest of them. Walking
the masses was added to ``BaseSearch.evaluate_circle`` in v0.1.84;
``evaluate_surface``, the other public door into the same engine, kept its own
copy of the loop with the walk missing and resolved the circle onto the first
mass from the LEFT — whichever that happens to be. Until v0.1.101 the same
circle therefore had two factors of safety, and which one you got depended on
which method you called.

THE CASE, AND WHY IT IS NOT ARBITRARY. Problem 27 of the reference verification
bank — Malkawi & Sarma (2001), taken in turn from the XSTABL v5 reference
manual (Sharma 1996) — publishes its critical circle in the statement, centre
(59.52, 219.21) and R = 157.68 ft. That arc passes 0.0054 ft ABOVE the toe
vertex (38, 63), so it cuts the ground FOUR times and defines two masses: a
0.9 ft lens between x = 17.62 and 37.95, which is not a mechanism at all, and
the real 22 ft failure between x = 38.01 and 169.89. Measured on 0.1.100,
``evaluate_surface`` answered for the LENS: Bishop 34.32 against 1.4071, a
factor of 24, with no warning of any kind.

THIS IS NOT A SNAPSHOT TEST. Three independent things are asserted and none of
them is a number this code printed:

* the GEOMETRY — four crossings and where they fall — follows from coordinates
  labelled one by one on figure 27.1 and from the published circle;
* the SELECTION is an identity: the factor returned for the whole circle must
  equal the MINIMUM of the factors of its masses evaluated one at a time. That
  is the definition of a critical mechanism among candidates, not a measurement;
* the VALUE is anchored to what the source publishes for that exact circle
  (table 27.2, both programs it reports), which is what says the mass picked is
  the RIGHT one and not merely the lower one.

ONE DATUM HERE IS MEASURED, NOT PUBLISHED, and it has to be said plainly: the
phreatic surface of problem 27 is only DRAWN in the figure, never tabulated. The
coordinates below were recovered by pixel measurement at 400 dpi and cross-
checked three ways (the drawn circle's own radius, the model's vertical edges,
and the stretch where the water table daylights along the labelled ground from
x = 0 to 63). It carries the uncertainty of a measurement, which is why the
published values are asserted to 1 % — the tolerance the project already uses
for a published critical circle in test_published_cases_v179.py.

WHY THE WALK IS FOR CIRCLES ONLY. A polyline carries its own vertices, so one
that crosses the ground more than twice has to rise ABOVE it in between, and a
slice whose base sits above its own top is a surface the slicer refuses whole
since v0.1.100. There are no masses to choose between — there is one invalid
surface, already reported as one. The last classes pin both halves of that:
0.05 ft of poke-through is enough to have a polyline discarded, and the arc of
one mass alone is analysed normally.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: Figure 27.1, ground surface, labelled vertex by vertex (feet).
_GROUND = [(0, 68), (22, 67), (38, 63), (63, 73), (101, 88), (138, 103),
           (200, 110)]

#: The undulating bedrock, the base of the external boundary, right to left.
_BEDROCK = [(200, 76), (161, 58), (133, 56), (113, 64), (94, 65), (78, 56),
            (51, 26), (29, 24), (0, 15)]

#: Soil 1 / Soil 2 contact, a straight line from a labelled ground vertex.
_CONTACT = [(101, 88), (200, 99)]

#: MEASURED, not published — see the note in the module docstring. Coincides
#: with the ground as far as x = 63, where the water table daylights at the toe.
_WATER_TABLE = [
    (0, 68.0), (22, 67.0), (38, 63.0), (63, 73.0),
    (66, 73.51), (73, 74.51), (80, 76.95), (87, 78.46), (94, 79.69),
    (101, 80.87), (108, 82.16), (115, 83.23), (122, 84.17), (129, 85.10),
    (136, 85.85), (143, 86.60), (150, 87.37), (157, 87.99), (164, 88.57),
    (171, 89.23), (178, 90.01), (185, 90.62), (192, 91.22), (200, 91.85),
]

#: The circle the statement gives. It is the subject of this whole file.
_CIRCLE = dict(centre_x=59.52, centre_y=219.21, radius=157.68)

#: The toe vertex the arc grazes, which is what creates the second mass.
_TOE = (38.0, 63.0)

#: Table 27.2, "given circle", as (first program, second program) for the five
#: methods this program implements. Corps of Engineers #1 and #2 are published
#: there too and do not exist here, so two rows have no counterpart.
_PUBLISHED = {
    "bishop_simplified": (1.396, 1.397),
    "janbu_corrected": (1.391, 1.392),
    "lowe_karafiath": (1.411, 1.413),
    "spencer": (1.402, 1.403),
    "gle_morgenstern_price": (1.398, 1.399),
}

#: The statement's own slice count. NOT a free parameter: the slicer must place
#: a boundary at every crossing of the water table and of the material contact
#: with the slip surface, and if those mandatory cuts outnumber the slices
#: ``slice_surface`` returns None without a word. 30 leaves room; the premise
#: class checks that both masses do slice into 30.
_SLICES = 30

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _project():
    """Problem 27, analysis 1: the given circle, with Soil 2 strengthless.

    Built here and not loaded from the bank, which lives outside this
    repository. Table 27.1: Soil 1 = 500 psf / 14 deg / 116.4 pcf moist /
    124.2 pcf saturated; Soil 2 = 0 / 0 / 116.4 / 116.4. The two unit weights
    of Soil 1 are half the interest of the problem, so ``use_sat_unit_weight``
    is on — without it the 124.2 is stored and never used, and everything below
    the water table is weighed 6.3 % light.

    The statement is explicit that pore pressures use "a correction for the
    inclination of the phreatic surface", i.e. Hu = cos^2(alpha).
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    if "project" in _CACHE:
        return _CACHE["project"]

    p = Project("Malkawi and Sarma (2001) / XSTABL v5 - problem 27")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in
                             _GROUND + [(200, 99)] + _BEDROCK], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))

    soil1 = Material(name="Soil 1", unit_weight=116.4, sat_unit_weight=124.2,
                     use_sat_unit_weight=True,
                     strength=MohrCoulomb(cohesion=500.0, friction_angle=14.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    soil1.auto_hu = True
    soil2 = Material(name="Soil 2", unit_weight=116.4, sat_unit_weight=116.4,
                     use_sat_unit_weight=True,
                     strength=MohrCoulomb(cohesion=0.0, friction_angle=0.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    soil2.auto_hu = True
    p.materials = [soil1, soil2]

    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in _CONTACT], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in _WATER_TABLE], closed=False),
        btype=BoundaryType.WATER_TABLE))

    for region in p.resolve_regions():
        cx, cy = region.centroid()
        material = soil1
        if cx > 101.0 and cy > 88.0:
            # Only the upper-right wedge lies above the contact line.
            if cy > 88.0 + (99.0 - 88.0) * (cx - 101.0) / 99.0:
                material = soil2
        p.assign_material_at(cx, cy, material.id)

    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4       # pcf
    p.settings.groundwater.auto_hu = True
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.interslice_function = "half_sine"
    _CACHE["project"] = p
    return p


def _ground_polyline():
    from ogr_slip2d.slicer import _ground_surface_from_external
    return _ground_surface_from_external(_project().external_boundary())


def _circle(x_left=None, x_right=None):
    """A FRESH circle, optionally pinned to one mass.

    Fresh on every call. Until v0.1.131 that was a necessity rather than a
    style: ``evaluate_circle`` wrote the analysed mass back onto the circle
    it was given, so a reused object carried those bounds into the next
    call and answered for whatever mass came first. It no longer writes
    anything, and the helper stays as it is because pinning a mass by hand
    is exactly what the ``x_left``/``x_right`` arguments are for.
    """
    from ogr_slip2d.surface import SlipCircle
    c = SlipCircle(**_CIRCLE)
    if x_left is not None:
        c.x_left, c.x_right = x_left, x_right
    return c


def _masses():
    """The sliding masses the published circle defines, left to right."""
    if "masses" not in _CACHE:
        _CACHE["masses"] = _circle().candidate_chords(_ground_polyline())
    return _CACHE["masses"]


def _search(method_id):
    """A search built the way ``analysis_runner`` builds one.

    ``build_method`` and not the registry raw: it is the only place that
    attaches the project's convergence settings, and comparing against a
    published value with a different stopping rule compares two things.
    """
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    return GridSearch(method=build_method(_project(), method_id, _SLICES),
                      num_slices=_SLICES, min_area=0.0)


def _fos_per_mass(method_id):
    """The factor of each mass evaluated on its own, and of the whole circle."""
    key = ("per-mass", method_id)
    if key not in _CACHE:
        p, ev = _project(), _search(method_id)
        per_mass = []
        for x_l, x_r in _masses():
            res = ev.evaluate_surface(p, _circle(x_l, x_r))
            assert res is not None, (method_id, x_l, x_r)
            per_mass.append(res.fos)
        _CACHE[key] = (per_mass, ev.evaluate_surface(p, _circle()))
    return _CACHE[key]


# ======================================================================
class TestTheCircleDefinesTwoDisjointMasses:
    """The premise, with no factor of safety anywhere in it.

    If this class fails, nothing below is testing what it claims to test:
    the geometry stopped producing two masses.
    """

    def test_the_arc_grazes_the_toe_vertex_from_above(self):
        """These five thousandths of a foot are the whole anomaly. Below the
        vertex the circle would cut the ground twice and define one mass;
        above it, four times and two masses."""
        arc_y = _circle().base_y_at(_TOE[0])
        assert arc_y is not None
        gap = arc_y - _TOE[1]
        assert 0.0 < gap < 0.01, gap

    def test_the_circle_cuts_the_published_ground_four_times(self):
        """Counted on the labelled profile, independently of the slicer."""
        import math
        ground = _ground_polyline()
        c, roots = _circle(), []
        for p1, p2 in zip(ground.vertices[:-1], ground.vertices[1:]):
            dx, dy = p2.x - p1.x, p2.y - p1.y
            a = dx * dx + dy * dy
            if a < 1e-14:
                continue
            b = 2 * ((p1.x - c.centre_x) * dx + (p1.y - c.centre_y) * dy)
            k = ((p1.x - c.centre_x) ** 2 + (p1.y - c.centre_y) ** 2
                 - c.radius ** 2)
            disc = b * b - 4 * a * k
            if disc < 0:
                continue
            sq = math.sqrt(disc)
            for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                if -1e-9 <= t <= 1 + 1e-9:
                    roots.append(p1.x + t * dx)
        assert len(roots) == 4, sorted(round(r, 4) for r in roots)

    def test_two_masses_a_lens_and_the_real_mechanism(self):
        masses = _masses()
        assert len(masses) == 2, masses
        (a_l, a_r), (b_l, b_r) = masses
        assert abs(a_l - 17.62) < 0.05 and abs(a_r - 37.95) < 0.05, masses
        assert abs(b_l - 38.01) < 0.05 and abs(b_r - 169.89) < 0.05, masses

    def test_one_is_a_skin_and_the_other_is_the_slope(self):
        """0.9 ft against 22 ft. A lens that thin is not a mechanism; it is
        what the circle scrapes off on its way past the toe."""
        from ogr_slip2d.slicer import slice_surface
        depths = []
        for x_l, x_r in _masses():
            sl = slice_surface(_project(), _circle(x_l, x_r),
                               num_slices=_SLICES)
            assert sl is not None, (x_l, x_r)
            # Both masses must actually slice into the count asked for: the
            # water-table and material crossings are mandatory cuts, and too
            # many of them would make the slicer return None in silence.
            assert len(sl) == _SLICES, (x_l, x_r, len(sl))
            depths.append(max(s.height for s in sl))
        assert depths[0] < 1.5, depths
        assert depths[1] > 15.0, depths


class TestTheLowestMassIsTheOneReturned:
    """The invariant itself, stated as an identity."""

    def test_the_factor_returned_is_the_minimum_over_the_masses(self):
        """Not "close to" the minimum: EQUAL to it. Both paths slice the same
        mass with the same bounds, so any difference at all would mean the
        surface analysed was not the one this test evaluated."""
        for method_id in _PUBLISHED:
            per_mass, whole = _fos_per_mass(method_id)
            assert whole is not None, method_id
            assert whole.fos == min(per_mass), (method_id, whole.fos, per_mass)

    def test_the_two_masses_are_far_apart(self):
        """Otherwise the assertion above would pass on a coin toss.

        The spread is 24x for four of the five methods. Lowe-Karafiath is the
        exception and stays in: on the lens it runs into its own ceiling of
        5.0 instead of reporting 34, so it shows a factor of 3.6 — the bound
        below is sized to the weakest of the five, deliberately.
        """
        for method_id in _PUBLISHED:
            per_mass, _ = _fos_per_mass(method_id)
            assert max(per_mass) > 2.0 * min(per_mass), (method_id, per_mass)

    def test_it_returns_the_deep_mass_and_not_the_lens(self):
        """The number on its own does not say which mass it came from."""
        (_, _), (deep_l, deep_r) = _masses()
        for method_id in _PUBLISHED:
            _, whole = _fos_per_mass(method_id)
            assert abs(whole.surface.x_left - deep_l) < 1e-9, method_id
            assert abs(whole.surface.x_right - deep_r) < 1e-9, method_id

    def test_the_two_public_doors_agree(self):
        """The defect in one line: the same circle, the two entry points of
        the engine, one answer — bit for bit, not to a tolerance."""
        p = _project()
        for method_id in _PUBLISHED:
            ev = _search(method_id)
            by_surface = ev.evaluate_surface(p, _circle())
            by_circle = ev.evaluate_circle(p, _circle())
            assert by_surface.fos == by_circle.fos, (
                method_id, by_surface.fos, by_circle.fos)


class TestThePublishedValue:
    """The external anchor: the mass picked has to be the RIGHT one.

    Table 27.2 of the source publishes two independent programs for this exact
    circle, so a discrepancy of ours cannot be blamed on a peculiarity of one
    of them.
    """

    def test_every_published_method_on_the_published_circle(self):
        p = _project()
        for method_id, published in _PUBLISHED.items():
            res = _search(method_id).evaluate_surface(p, _circle())
            assert res is not None and res.is_valid, method_id
            err = min(abs(res.fos - v) / v for v in published)
            assert err < 0.01, (
                f"{method_id}: FS={res.fos:.6f}, published {published[0]} / "
                f"{published[1]}, err {err * 100:.2f} %")


class TestTheSingleMassCaseIsUnchanged:
    """What must not break: a circle with ONE mass takes the route it always
    took, and lands on the same float."""

    #: Inside the slope, well clear of the toe vertex. Checked below, not
    #: assumed, that it defines a single mass AND that it stays inside the
    #: soil — see TestBothDoorsRejectTheSameCircles for why the second half
    #: of that is not idle.
    _PLAIN = dict(centre_x=60.0, centre_y=110.0, radius=45.0)

    def _plain_circle(self):
        from ogr_slip2d.surface import SlipCircle
        return SlipCircle(**self._PLAIN)

    def test_the_control_circle_really_has_one_mass(self):
        chords = self._plain_circle().candidate_chords(_ground_polyline())
        assert len(chords) == 1, chords

    def test_it_matches_slicing_and_solving_by_hand(self):
        """``slice_surface`` + ``compute_fos`` IS the route evaluate_surface
        took before v0.1.101. Same number, or the fix moved something it had
        no business moving."""
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.slicer import slice_surface
        p = _project()
        for method_id in _PUBLISHED:
            surface = self._plain_circle()
            slices = slice_surface(p, surface, num_slices=_SLICES)
            assert slices is not None and len(slices) >= 3, method_id
            direct = build_method(p, method_id, _SLICES).compute_fos(
                p, surface, slices)
            through = _search(method_id).evaluate_surface(
                p, self._plain_circle())
            assert through is not None, method_id
            assert through.fos == direct.fos, (
                method_id, through.fos, direct.fos)


class TestNonCircularSurfacesTakeTheOtherRoute:
    """Why the walk is for circles only.

    A polyline that rises above the ground is not a set of masses to choose
    between: it is one surface, and the slicer throws it away entire.

    NOTE for whoever extends this class: the obvious case — the published arc
    sampled across BOTH masses — does not belong here, and it took a failing
    run to see why. That polyline comes back with an ordinary factor (1.5632)
    because its 0.058 ft excursion over the toe vertex falls between slice
    boundaries: the vertex placed at x = 38.0 is merged away by
    ``_slice_boundaries``, whose tolerance is a thousandth of the failure
    width (0.152 ft here) and which already had a water-table crossing at
    x = 37.9498. What gets analysed is then the chord polygon through the
    vertices, which does run below the ground. That is a DIFFERENT surface
    from the circle, correctly analysed — not a wrong answer about the circle
    — so asserting anything about it here would be asserting the merge
    tolerance, which is not what this file is for.
    """

    def _arc_polyline(self, x0, x1, n=25, lift_at=None, lift_by=0.0):
        """The lower arc between two abscissas, as a polyline.

        With ``lift_at`` the vertex nearest that abscissa is placed
        ``lift_by`` above the GROUND instead of on the arc, which is how the
        surface is made to poke out on purpose.
        """
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.slicer import _interp_y_on_polyline
        from ogr_slip2d.surface import SlipSurface
        c, ground = _circle(), _ground_polyline()
        xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
        vertices = []
        for x in xs:
            y = c.base_y_at(x)
            if lift_at is not None and abs(x - lift_at) < (x1 - x0) / (2 * n):
                y = _interp_y_on_polyline(ground, x) + lift_by
            vertices.append(Vertex(x, y))
        return SlipSurface(polyline=Polyline(vertices=vertices, closed=False))

    def test_a_polyline_that_rises_above_the_ground_is_refused(self):
        """Half a foot out of the slope, and there is no factor of safety to
        report — not a smaller one: none."""
        (_, _), (b_l, b_r) = _masses()
        surface = self._arc_polyline(b_l, b_r, lift_at=45.0, lift_by=0.5)
        assert _search("bishop_simplified").evaluate_surface(
            _project(), surface) is None

    def test_five_hundredths_of_a_foot_are_already_enough(self):
        """The refusal is not a coarse one: what the slicer forgives is
        relative to the failure width and stays down at 1e-6 of it."""
        (_, _), (b_l, b_r) = _masses()
        surface = self._arc_polyline(b_l, b_r, lift_at=45.0, lift_by=0.05)
        assert _search("bishop_simplified").evaluate_surface(
            _project(), surface) is None

    def test_the_arc_of_the_real_mechanism_alone_is_analysed(self):
        """The refusals above have to be about leaving the ground, not about
        polylines. The same arc, untouched, gives an ordinary factor within a
        fraction of a percent of the circle itself — 25 chords against a true
        arc."""
        (_, _), (b_l, b_r) = _masses()
        res = _search("bishop_simplified").evaluate_surface(
            _project(), self._arc_polyline(b_l, b_r))
        assert res is not None and res.is_valid, res
        by_circle = _search("bishop_simplified").evaluate_circle(
            _project(), _circle())
        assert abs(res.fos - by_circle.fos) / by_circle.fos < 0.01, (
            res.fos, by_circle.fos)


class TestBothDoorsRejectTheSameCircles:
    """The other half of one answer: they have to agree on NO answer too.

    Routing circles through ``evaluate_circle`` also gives this door that
    method's two rejections — the bounding-box early skip, and the containment
    rule for non-composite circular surfaces that the reference reports as
    error -103. That is deliberate, and it is the point: a circle whose mass
    leaves the soil is now rejected whichever method you call, instead of
    being rejected by the search and answered for by the evaluator.
    """

    #: One mass, but it dives out through the undulating bedrock.
    _ESCAPING = dict(centre_x=90.0, centre_y=130.0, radius=70.0)

    #: Nowhere near the model at all.
    _FAR = dict(centre_x=1000.0, centre_y=1000.0, radius=5.0)

    def test_the_control_circle_really_does_leave_the_soil(self):
        """The premise, taken from the containment rule itself and not from
        any factor of safety."""
        from ogr_slip2d.surface import SlipCircle, leaves_soil_region
        c = SlipCircle(**self._ESCAPING)
        chords = c.candidate_chords(_ground_polyline())
        assert len(chords) == 1, chords
        x_l, x_r = chords[0]
        c.x_left, c.x_right = x_l, x_r
        vertices = list(_project().external_boundary().polyline.vertices)
        assert leaves_soil_region(c, vertices, x_l, x_r)

    def test_neither_door_answers_for_it(self):
        from ogr_slip2d.surface import SlipCircle
        p, ev = _project(), _search("bishop_simplified")
        assert ev.evaluate_circle(p, SlipCircle(**self._ESCAPING)) is None
        assert ev.evaluate_surface(p, SlipCircle(**self._ESCAPING)) is None

    def test_a_circle_that_cannot_reach_the_model_is_skipped(self):
        """The bounding-box skip, which this door did not have before."""
        from ogr_slip2d.surface import SlipCircle
        p, ev = _project(), _search("bishop_simplified")
        assert ev.evaluate_surface(p, SlipCircle(**self._FAR)) is None
