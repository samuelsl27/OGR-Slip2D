# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Corps of Engineers #1 draws its line to the TOP of a tension crack
(v0.1.224, D223).

INVARIANT PROTECTED
-------------------
Corps #1 inclines every interslice force parallel to one line: in this
program, interpretation 1 of Duncan, Wright & Brandon (2014, Fig. 6.14a),
the line joining the points where the failure surface meets the ground. A
tension crack truncates the mass at its crest end; the failure surface --
the slip surface and the crack -- reaches the ground at the TOP of the
crack. Until v0.1.223 the line went to its BOTTOM, a point of the slip
surface below the ground.

What is asserted, none of it a snapshot:

* the external check, verification problem 27 with its 11 ft crack, dry and
  with 6 ft of water (Malkawi, Hassan & Sarma 2001; tables 27.4a/b, where
  the reference program and XSTABL publish the same differences between
  methods): Corps #2 is 0.007 (dry) and 0.006 (wet) above Corps #1 and
  Lowe-Karafiath 0.010 below it in both. Those two methods do not depend on
  the ends of the mass, so the differences isolate the line of Corps #1;
  the tolerance is the rounding of two three-decimal numbers, 0.001. The
  line to the bottom missed by 0.02 (rule 7);
* the slices carry the wall the crack left, and a mass it did not truncate
  carries none;
* a mirror image -- the crack at the other end -- gives the same factor;
* an end with no crack does not move by a bit: it is where the slip
  surface meets the ground, even where that is not the end slice's top.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.223 tree: see ``_auditoria/P4_0224`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

#: Tables 27.4a/b (both programs): Corps #2 - Corps #1, Lowe-Karafiath -
#: Corps #1.
PUBLISHED = {False: (0.007, -0.010), True: (0.006, -0.010)}


def _chord(on):
    """Context: ``modified_swedish.CHORD_TO_CRACK_TOP`` as asked, put back
    afterwards (the runner has no teardown)."""
    import contextlib

    @contextlib.contextmanager
    def cm():
        from ogr_slip2d.methods import modified_swedish as ms
        old = getattr(ms, "CHORD_TO_CRACK_TOP", None)
        ms.CHORD_TO_CRACK_TOP = on
        try:
            yield
        finally:
            if old is None:
                vars(ms).pop("CHORD_TO_CRACK_TOP", None)
            else:
                ms.CHORD_TO_CRACK_TOP = old
    return cm()


def _problem_27(crack, wet=False, mirror=False):
    """Verification problem 27 (Malkawi, Hassan & Sarma 2001), imperial
    units: two soils on an undulating rock floor under a measured water
    table with Hu = cos^2. ``crack``: the zero-strength upper soil replaced
    by an 11 ft tension crack zone along the same line, dry or with 6 ft of
    water (5 ft below its lip); otherwise the two soils. ``mirror``: the
    same model reflected about x = 0. The model of the verification bank,
    written here because a test does not read the bank."""
    from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                   TensionCrackProperties, Vertex,
                                   WaterLevelMode)
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    sx = -1.0 if mirror else 1.0

    def line(pts, closed=False):
        vs = [Vertex(sx * x, y) for x, y in pts]
        if mirror:
            vs.reverse()
        pl = Polyline(vertices=vs, closed=closed)
        if closed:
            pl.ensure_ccw()
        return pl

    ground = [(0, 68), (22, 67), (38, 63), (63, 73), (101, 88), (138, 103),
              (200, 110)]
    floor = [(200, 76), (161, 58), (133, 56), (113, 64), (94, 65), (78, 56),
             (51, 26), (29, 24), (0, 15)]
    contact = [(101, 88), (200, 99)]
    water = [(0, 68.0), (22, 67.0), (38, 63.0), (63, 73.0), (66, 73.51),
             (73, 74.51), (80, 76.95), (87, 78.46), (94, 79.69),
             (101, 80.87), (108, 82.16), (115, 83.23), (122, 84.17),
             (129, 85.10), (136, 85.85), (143, 86.60), (150, 87.37),
             (157, 87.99), (164, 88.57), (171, 89.23), (178, 90.01),
             (185, 90.62), (192, 91.22), (200, 91.85)]
    p = Project("problem-27")
    p.add_boundary(Boundary(polyline=line(ground + [(200, 99)] + floor,
                                          closed=True),
                            btype=BoundaryType.EXTERNAL))
    soil1 = Material(name="Soil 1", unit_weight=116.4, sat_unit_weight=124.2,
                     use_sat_unit_weight=True,
                     strength=MohrCoulomb(cohesion=500.0, friction_angle=14.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    soil1.auto_hu = True
    p.materials = [soil1]
    if crack:
        p.add_boundary(Boundary(polyline=line(contact),
                                btype=BoundaryType.TENSION_CRACK))
        p.tension_crack_properties = (
            TensionCrackProperties(mode=WaterLevelMode.FILLED_TO_DEPTH,
                                   depth=5.0) if wet else
            TensionCrackProperties(mode=WaterLevelMode.DRY))
    else:
        soil2 = Material(name="Soil 2", unit_weight=116.4,
                         sat_unit_weight=116.4, use_sat_unit_weight=True,
                         strength=MohrCoulomb(cohesion=0.0,
                                              friction_angle=0.0),
                         pore_pressure=PorePressureType.WATER_TABLE)
        soil2.auto_hu = True
        p.materials.append(soil2)
        p.add_boundary(Boundary(polyline=line(contact),
                                btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=line(water),
                            btype=BoundaryType.WATER_TABLE))
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        x = sx * cx
        mat = soil1
        if (not crack and x > 101.0
                and cy > 88.0 + 11.0 * (x - 101.0) / 99.0):
            mat = p.materials[1]
        p.assign_material_at(cx, cy, mat.id)
    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.groundwater.auto_hu = True
    p.settings.methods.tolerance = 1e-8
    return p, SlipCircle(centre_x=sx * 59.52, centre_y=219.21, radius=157.68)


def _on(mid, crack, wet=False, mirror=False, on=True):
    """The result of ``mid`` on the given circle, 30 slices, through the
    door the bank uses (``evaluate_circle`` keeps the real mechanism and not
    the thin lens the circle also cuts off at the toe)."""
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    p, c = _problem_27(crack, wet, mirror)
    with _chord(on):
        r = GridSearch(method=build_method(p, mid, 30), num_slices=30,
                       min_area=0.0).evaluate_circle(p, c)
    assert r is not None and r.fos is not None, (mid, crack, wet)
    return r


def _differences(wet, on=True):
    c1 = _on("corps_engineers_1", True, wet, on=on).fos
    return (_on("corps_engineers_2", True, wet, on=on).fos - c1,
            _on("lowe_karafiath", True, wet, on=on).fos - c1)


class TestTheCrackedProblem27:

    def test_the_published_differences(self):
        for wet in (False, True):
            got = _differences(wet)
            for g, published in zip(got, PUBLISHED[wet]):
                assert abs(g - published) <= 0.001, (wet, got, published)

    def test_the_line_to_the_bottom_missed_them(self):
        """Rule 7: +0.026 and +0.010 where both programs publish +0.007
        and -0.010 (dry)."""
        for wet in (False, True):
            got = _differences(wet, on=False)
            assert abs(got[0] - PUBLISHED[wet][0]) > 0.01, (wet, got)


class TestTheWall:

    def test_the_slices_carry_it_at_the_end_it_closes(self):
        r = _on("corps_engineers_1", True)
        wall = r.slices.tension_crack_wall
        assert wall is not None
        x, y_bottom, y_top = wall
        assert x == r.slices[-1].base_x_right, (x, r.slices[-1].base_x_right)
        assert y_top - y_bottom > 5.0, wall                 # an 11 ft crack
        assert y_top > r.slices[-1].base_y_right

    def test_a_mass_the_crack_did_not_truncate_has_none(self):
        r = _on("corps_engineers_1", False)
        assert getattr(r.slices, "tension_crack_wall", None) is None

    def test_a_mirror_image_is_the_same_problem(self):
        """The crack at the left end, where the code reads the other end:
        the same factor, and not the one the line to the bottom gave."""
        for wet in (False, True):
            f = _on("corps_engineers_1", True, wet).fos
            old = _on("corps_engineers_1", True, wet, on=False).fos
            assert abs(f - old) > 1e-3 * f, (wet, f, old)       # guard
            fm_r = _on("corps_engineers_1", True, wet, mirror=True)
            assert abs(fm_r.fos - f) <= 1e-9 * f, (wet, f, fm_r.fos)
            assert fm_r.slices.tension_crack_wall[0] == \
                fm_r.slices[0].base_x_left


class TestWithoutACrackNothingMoves:

    def test_problem_27_bit_for_bit(self):
        on = _on("corps_engineers_1", False, on=True)
        off = _on("corps_engineers_1", False, on=False)
        assert on.fos == off.fos
        assert on.base_normal_force == off.base_normal_force

    def test_the_nail_slope_bit_for_bit(self):
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from test_support_normal_v1137 import NSLICES, _circle, _project
        p, c = _project(None), _circle()
        sl = slice_surface(p, c, num_slices=NSLICES)
        assert getattr(sl, "tension_crack_wall", None) is None
        out = []
        for on in (True, False):
            with _chord(on):
                out.append(method_registry()["corps_engineers_1"]()
                           .compute_fos(p, c, sl).fos)
        assert out[0] == out[1], out
