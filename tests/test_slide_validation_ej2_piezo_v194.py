# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The first reference case in this project that carries PORE PRESSURE.

WHAT INVARIANT THIS PROTECTS, and why it could not exist before.

``Ej_1`` and ``Ej_2`` are both DRY. Every water path of the limit-equilibrium
engine — ``pore_pressure_at``, the per-material water-surface assignment, the
Hu coefficient, and above all what each of the seven methods DOES with u —
therefore had no external value to be measured against, for eighty versions.
This file is that value: the Ej_2 geometry with a Piezometric Line assigned to
Materials 2 and 3, run by the reference program, whose report publishes the
per-slice pore pressure and effective normal stress.

Three anchors, in increasing order of strength:

1. **u AT EVERY SLICE BASE** (``TestPorePressureReachesTheSlice``). Taken from
   the reference's own Slice Data table for Bishop. This pins the water model
   itself — interpolation along the piezo line, which material it applies to,
   Hu = 1, gamma_w = 9.81 — independently of any method.

2. **THE EFFECTIVE NORMAL STRESS OF THE ORDINARY METHOD**
   (``TestOrdinaryUsesTheCorrectedPorePressure``). This is the anchor that
   found the bug this file was written for. The reference resolves the
   pore-pressure force over the base's VERTICAL PROJECTION,

       N' = W*cos(a) - u*l*cos^2(a)            (Turnbull & Hvorslev, 1967)

   where this program used ``u*l``. The two are IDENTICAL at alpha = 0 and
   diverge as cos^2(alpha), so no dry model can tell them apart — which is
   exactly why it survived. Measured on this circle before the fix: the
   effective normal stress was out by up to 118 %, five slices of 25 came out
   in tension that should not have, and the factor of safety was **-24.7 %**.

   The anchor is the reference's published sigma' column, not a captured
   output.

3. **THE SEVEN FACTORS OF SAFETY** on the reference's own critical circles
   (``TestTheSevenMethods``). Four of the seven agree to 0.5 %. THREE DO NOT,
   and they are pinned separately and deliberately in
   ``TestKnownDivergences`` — see that class for why writing them down as
   "passing" would have been the wrong thing to do.

Reference: Slide2d_Ej_2_Piezo_Line.htm / .slim, in
``referencias/Ejemplos/Ej_2/Ej_2_Piezometric_Line/``. That directory is NOT
part of the repository, so every number below is written out by hand with its
provenance, and the model is built in code — the suite has to run from a clean
checkout.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# --- The model, verbatim from the reference .sli ----------------------
# piezos: 1  vertices: [12, 11, 15, 16, 3]
#   12 = (-50, 30)   11 = (15, 30)   15 = (35, 50)
#   16 = (55, 50)    3  = (100, 55)
# NOTE: Ej_2_Geometria_Piezometric_Line.txt says (60, 50) for the fourth
# vertex. The .sli and the .ogr both say (55, 50); the .txt is wrong.
PIEZO = [(-50.0, 30.0), (15.0, 30.0), (35.0, 50.0), (55.0, 50.0), (100.0, 55.0)]

# material types:  soil1 water: 1 wtable: 0     -> no water surface
#                  soil2 water: 1 piezo: 1      -> Piezometric Line 1, Hu = 1
#                  soil3 water: 1 piezo: 1      -> Piezometric Line 1, Hu = 1
GAMMA_W = 9.81
NUM_SLICES = 25

# Reference critical circles (Global Minimums block of the .htm)
SMALL = (12.380952, 61.315789, 30.40817)   # fellenius, bishop, spencer,
                                           # lowe-karafiath, gle
BIG = (17.619048, 50.789474, 20.95412)     # janbu simplified, janbu corrected

REFERENCE_FOS = [
    ("ordinary_fellenius", 0.797225, SMALL),
    ("bishop_simplified", 0.674931, SMALL),
    ("janbu_simplified", 0.568860, BIG),
    ("janbu_corrected", 0.612772, BIG),
    ("spencer", 0.687672, SMALL),
    ("lowe_karafiath", 0.703504, SMALL),
    ("gle_morgenstern_price", 0.680394, SMALL),
]

# Slice Data, Global Minimum Query (bishop simplified): "Pore Pressure [kPa]".
# 25 slices, left to right. The last two are zero because the piezometric line
# passes BELOW the slip surface there.
REF_U = [
    4.40493, 13.031, 21.2862, 29.1626, 36.6508, 43.7392, 50.4143, 56.6598,
    62.4565, 67.7818, 72.6088, 76.9054, 80.6333, 83.746, 86.1867, 87.8848,
    88.7511, 88.6705, 82.4726, 69.9263, 56.041, 40.2185, 21.747, 0.0, 0.0,
]

# Slice Data, Global Minimum Query (ordinary/fellenius): "Effective Normal
# Stress [kPa]". This is the column that identifies the pore-pressure
# convention, because it is the only place the two candidate formulas differ.
REF_SIGMA_EFF_ORDINARY = [
    4.48474, 13.1198, 21.1378, 28.4858, 35.1146, 40.98, 46.0426, 50.2673,
    53.6266, 56.0956, 57.6587, 58.3053, 58.033, 56.849, 54.7688, 51.8199,
    48.0432, 43.497, 40.3704, 38.1004, 34.3274, 29.1327, 22.6617, 13.4697,
    2.6228,
]

_CACHE: dict = {}


# ======================================================================
def _project():
    """The reference model, built in code (see the module docstring)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ej2-piezo")
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))

    m1 = Material(name="Material 1", unit_weight=20,
                  strength=MohrCoulomb(cohesion=20, friction_angle=35))
    m2 = Material(name="Material 2", unit_weight=20,
                  strength=MohrCoulomb(cohesion=15, friction_angle=28))
    m3 = Material(name="Material 3", unit_weight=20,
                  strength=MohrCoulomb(cohesion=26, friction_angle=30))
    p.materials = [m1, m2, m3]

    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(60, 60), Vertex(100, 65)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(25, 40), Vertex(100, 55)], closed=False),
        btype=BoundaryType.MATERIAL))

    piezo = Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in PIEZO], closed=False),
        btype=BoundaryType.PIEZOMETRIC)
    p.add_boundary(piezo)

    # Material 1 keeps Water Surface = None, exactly as the reference report
    # lists it. Only Materials 2 and 3 take the piezometric line, with Hu = 1.
    for m in (m2, m3):
        m.pore_pressure = PorePressureType.PIEZO_LINE
        m.water_surface_id = piezo.id
        m.hu = 1.0

    regs = p.resolve_regions()
    ordered = sorted(regs, key=lambda r: r.centroid()[1])
    p.assign_material_at(*ordered[0].centroid(), m3.id)
    p.assign_material_at(*ordered[1].centroid(), m2.id)
    p.assign_material_at(*ordered[2].centroid(), m1.id)
    return p


def _result(method_id: str, circle):
    """One method on one reference circle, memoised.

    ``check_m_alpha`` is off so that the comparison measures the FORMULATION
    and not the admissibility filter; the reference does filter on m-alpha,
    which is why its valid-surface counts differ from ours.
    """
    key = (method_id, circle)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    try:
        m = get_method(method_id)(tolerance=0.005, max_iterations=50,
                                  initial_fos=1.0, iterate_steffensen=True)
    except TypeError:                      # methods without the full kwargs
        m = get_method(method_id)()
    gs = GridSearch(method=m, num_slices=NUM_SLICES, min_area=0.0,
                    check_m_alpha=False)
    cx, cy, r = circle
    _CACHE[key] = gs.evaluate_circle(
        _project(), SlipCircle(centre_x=cx, centre_y=cy, radius=r))
    return _CACHE[key]


# ======================================================================
class TestPorePressureReachesTheSlice:
    """Anchor 1 — u at every slice base, against the reference's own table."""

    def test_u_matches_the_reference_at_every_slice(self):
        res = _result("bishop_simplified", SMALL)
        assert res is not None and res.is_valid
        slices = list(res.slices)
        assert len(slices) == NUM_SLICES, len(slices)
        for i, (s, ref) in enumerate(zip(slices, REF_U)):
            if ref == 0.0:
                assert s.pore_pressure == 0.0, (i, s.pore_pressure)
            else:
                err = abs(s.pore_pressure - ref) / ref
                assert err < 1e-4, (i, s.pore_pressure, ref, err)

    def test_material_one_stays_dry(self):
        """Water Surface = None must mean u = 0, whatever else is drawn.

        Rule 7 read backwards: leaving a material unassigned has to keep
        meaning something once the Assign dialog can write the field.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = _project()
        m1 = p.materials[0]
        # A point well below the piezometric line, inside Material 1's range.
        assert pore_pressure_at(p, Vertex(80.0, 40.0), m1, 65.0) == 0.0

    def test_u_follows_the_line_and_not_the_ground(self):
        """u = gamma_w*(y_piezo - y), the closed form, at a chosen point.

        An identity rather than a captured number: at x = 0 the piezometric
        line is flat at y = 30, so a base 10 m below it must carry exactly
        10*gamma_w.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = _project()
        m3 = p.materials[2]
        got = pore_pressure_at(p, Vertex(0.0, 20.0), m3, 30.0)
        assert math.isclose(got, 10.0 * GAMMA_W, rel_tol=1e-12), got


# ======================================================================
class TestOrdinaryUsesTheCorrectedPorePressure:
    """Anchor 2 — the bug this file was written for.

    ``N' = W*cos(a) - u*l*cos^2(a)`` (Turnbull & Hvorslev 1967), not ``u*l``.
    """

    def test_effective_normal_stress_matches_the_reference(self):
        res = _result("ordinary_fellenius", SMALL)
        assert res is not None and res.is_valid
        for i, (s, ref) in enumerate(zip(res.slices,
                                         REF_SIGMA_EFF_ORDINARY)):
            l = s.base_length
            cos_a = math.cos(s.base_angle)
            sigma = (s.weight * cos_a / l) - s.pore_pressure * cos_a * cos_a
            err = abs(sigma - ref) / abs(ref)
            # The last two slices carry u = 0 and are very steep, where the
            # chord-vs-arc difference of the slicer dominates; they say
            # nothing about the pore-pressure convention, so they are held
            # to a looser bound on purpose.
            limit = 0.06 if i >= 23 else 0.005
            assert err < limit, (i, sigma, ref, err)

    def test_the_uncorrected_form_would_fail_this_same_check(self):
        """The discriminating power of the anchor, made explicit.

        Without this test the one above could pass for the wrong reason —
        a tolerance loose enough to admit both formulas. It is not: the
        uncorrected ``u*l`` is out by more than 100 % on this circle.
        """
        res = _result("ordinary_fellenius", SMALL)
        worst = 0.0
        for s, ref in zip(res.slices, REF_SIGMA_EFF_ORDINARY):
            sigma = (s.weight * math.cos(s.base_angle) / s.base_length
                     - s.pore_pressure)          # the OLD, uncorrected form
            worst = max(worst, abs(sigma - ref) / abs(ref))
        assert worst > 1.0, worst

    def test_no_slice_is_driven_into_false_tension(self):
        """Five of 25 came out in tension with the uncorrected term.

        The code used to explain those away as the method's own weakness,
        citing Whitman & Bailey (1967). They were made by the water term.
        """
        res = _result("ordinary_fellenius", SMALL)
        assert res.details["negative_effective_normal"] == 0, res.details

    def test_a_dry_model_cannot_tell_the_two_forms_apart(self):
        """Why eighty versions of dry benchmarks never saw this.

        u = 0 makes ``u*l`` and ``u*l*cos^2(a)`` the same number, so the
        whole error is proportional to u*(1 - cos^2(a)). This is the reason
        the fix cannot move Ej_1 or Ej_2, and it is worth asserting rather
        than asserting the unchanged values themselves.
        """
        from ogr_core.materials import PorePressureType
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _project()
        for m in p.materials:
            m.pore_pressure = PorePressureType.NONE
        gs = GridSearch(method=get_method("ordinary_fellenius")(),
                        num_slices=NUM_SLICES, min_area=0.0,
                        check_m_alpha=False)
        cx, cy, r = SMALL
        res = gs.evaluate_circle(p, SlipCircle(centre_x=cx, centre_y=cy,
                                               radius=r))
        assert res is not None and res.is_valid
        for s in res.slices:
            assert s.pore_pressure == 0.0
        # 1.114420 is the DRY reference value for this circle, from
        # Slide2d_Ej_2_General.htm — a different run of the same geometry.
        assert abs(res.fos - 1.114420) / 1.114420 < 0.005, res.fos


# ======================================================================
class TestTheSevenMethods:
    """Anchor 3 — the four methods that agree with the reference."""

    AGREE = ("ordinary_fellenius", "bishop_simplified",
             "janbu_simplified", "janbu_corrected")

    def test_within_half_a_percent(self):
        worst = []
        for method_id, ref, circle in REFERENCE_FOS:
            if method_id not in self.AGREE:
                continue
            res = _result(method_id, circle)
            assert res is not None, method_id
            assert res.is_valid, (method_id, res.error_message)
            err = abs(res.fos - ref) / ref
            worst.append((method_id, res.fos, ref, err))
            assert err < 0.005, (method_id, res.fos, ref, err)
        assert len(worst) == 4

    def test_the_slice_geometry_matches_the_reference(self):
        """Same mass, so the factors compare like for like."""
        res = _result("bishop_simplified", SMALL)
        sd = res.surface.to_dict()
        assert abs(sd["x_left"] - 16.141) < 0.01, sd["x_left"]
        assert abs(sd["x_right"] - 42.126) < 0.01, sd["x_right"]
        area = sum(s.width * max(s.height, 0.0) for s in res.slices)
        # Reference: Total Slice Area = 160.25 m2
        assert abs(area - 160.25) / 160.25 < 0.005, area


# ======================================================================
class TestKnownDivergences:
    """The three methods that do NOT agree, pinned deliberately.

    Writing these down with a tolerance loose enough to "pass" would be the
    snapshot test rule 1 forbids: it would consecrate the defect. Writing
    them down as expected divergences of a MEASURED size does the opposite —
    it makes the gap visible, and it makes anyone who narrows it come here
    and say so.

    * **lowe-karafiath, -10.9 %** — ``interslice_water_thrust``
      (``external_forces.py``), applied by this method and no other. Removing
      it lands on +0.09 % here and BREAKS Duncan & Wright verification #70
      (a submerged slope goes from 1.609 to 5.000 and stops being invariant
      to water depth). Both formulations are self-consistent; they differ in
      whether the prescribed inclination theta = (beta+alpha)/2 applies to
      the TOTAL or to the EFFECTIVE inter-slice force. Settling it needs one
      datum this project does not have: the reference's own Lowe-Karafiath
      value on a model with ponded water.
    * **spencer, -2.0 %** and **gle, -0.8 %** — not a pore-pressure defect.
      ``spencer.py`` builds its resisting term as Bishop's numerator with an
      m_alpha that carries no lambda, so the inter-slice vertical force never
      reaches the base normal, and the method tracks Bishop far too closely.
      Open since v0.1.79 in ``docs/audits/spencer_gle_interslice_v179.md``;
      this model is the first to make it measurable, because it is the first
      where the true separation is bigger than the noise.
    """

    EXPECTED = {
        "lowe_karafiath": (-0.109, 0.02),
        "spencer": (-0.020, 0.01),
        "gle_morgenstern_price": (-0.008, 0.01),
    }

    def test_each_divergence_is_the_size_it_was_measured_to_be(self):
        for method_id, ref, circle in REFERENCE_FOS:
            if method_id not in self.EXPECTED:
                continue
            expected, band = self.EXPECTED[method_id]
            res = _result(method_id, circle)
            assert res is not None and res.is_valid, method_id
            rel = (res.fos - ref) / ref
            assert abs(rel - expected) < band, (
                method_id, res.fos, ref, rel, expected)

    def test_the_reference_separates_spencer_from_bishop_and_we_do_not(self):
        """The signature of the open audit, as a number.

        The reference moves Spencer from +0.09 % above its own Bishop when
        dry to +1.89 % above it with water. This program stays at 0.0 % in
        both. That contrast is the measurement the audit was missing.
        """
        b = _result("bishop_simplified", SMALL).fos
        s = _result("spencer", SMALL).fos
        ours = (s - b) / b
        theirs = (0.687672 - 0.674931) / 0.674931
        assert theirs > 0.018, theirs
        assert abs(ours) < 0.002, ours
