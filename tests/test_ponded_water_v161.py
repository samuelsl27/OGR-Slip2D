# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Ponded water: free-standing water resting on the slope.

Before v0.1.61 a water table drawn above the ground gave the pore
pressure its full head but applied NO load, so the ``W − u·b`` term went
strongly negative and a submerged slope came back with a NEGATIVE factor
of safety (−1.61 for 30 ft of water, −3.32 for 60 ft, against a published
1.60). This file locks down the fix.

The primary anchor is an EXTERNAL, PUBLISHED case, not a captured value:

    Verification problem #70 of the reference program's Slope Stability
    Verification Manual (Part III), itself taken from Duncan & Wright
    (2005), figure 6.27, page 88. A homogeneous submerged slope with
    c' = 100 psf, φ' = 20°, γ = 128 pcf, analysed with the water table
    30 ft AND 60 ft above the crest. Referee factor of safety = 1.60
    for both, by Bishop, Spencer and GLE.

Two things make that case worth its weight:

  * the referee value pins the magnitude, and
  * **the answer is the same for both water depths**. Adding water on top
    of an already-submerged slope must change nothing, because the extra
    weight and the extra hydrostatic thrust cancel exactly. A sign error,
    a wrong moment arm or a missing component all break that invariance.

The second anchor is the equivalence of the two procedures for water in
Duncan & Wright: total unit weights plus boundary water forces plus pore
pressures must give the same answer as buoyant unit weights γ' = γ − γ_w
with no water at all.

Note on units: the case is imperial (ft, psf, pcf) while the project
nominally stores kN/m³. The factor of safety is dimensionless and the
inputs are internally consistent, so the numbers carry through unchanged.
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import QApplication

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    Polyline,
    TensionCrackProperties,
    Vertex,
    WaterLevelMode,
)
from ogr_core.materials import Material, PorePressureType
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project import Project
from ogr_slip2d import (
    BishopSimplified,
    GLEMorgensternPrice,
    JanbuSimplified,
    LoweKarafiath,
    OrdinaryFellenius,
    SlipCircle,
    Spencer,
    slice_surface,
)
from ogr_slip2d.search import GridSearch

# --- Verification #70 -------------------------------------------------
GAMMA_W = 62.4        # pcf
GAMMA = 128.0         # pcf, total unit weight
COHESION = 100.0      # psf
PHI = 20.0            # degrees
CREST_Y = 45.0
# Critical circle published with the case (Bishop)
CIRCLE = dict(centre_x=49.42, centre_y=88.56, radius=76.08)
REFEREE_FOS = 1.60

_WINDOWS: list = []


def _external():
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(140, 0), Vertex(140, 45),
        Vertex(105, 45), Vertex(30, 15), Vertex(0, 15),
    ], closed=True)
    ext.ensure_ccw()
    return ext


def _base_project(name="v70"):
    p = Project(name)
    p.add_boundary(Boundary(polyline=_external(), btype=BoundaryType.EXTERNAL))
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def ponded(wt_y, btype=BoundaryType.WATER_TABLE):
    """Total unit weight, water surface at ``wt_y``, hydrostatic u."""
    p = _base_project()
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-10, wt_y), Vertex(150, wt_y)], closed=False),
        btype=btype))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=COHESION,
                                          friction_angle=PHI),
        unit_weight=GAMMA, sat_unit_weight=GAMMA, use_sat_unit_weight=True,
        pore_pressure=PorePressureType.WATER_TABLE)]
    return p


def buoyant():
    """The equivalent procedure: buoyant unit weight, no water at all."""
    p = Project("v70-buoyant")
    p.add_boundary(Boundary(polyline=_external(), btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=COHESION,
                                          friction_angle=PHI),
        unit_weight=GAMMA - GAMMA_W)]
    return p


def fos(project, method, n=50):
    ev = GridSearch(method=method, num_slices=n, min_area=0.0)
    r = ev.evaluate_circle(project, SlipCircle(**CIRCLE))
    assert r is not None, "circle produced no slices"
    return r.fos


def _slices(project, n=50):
    sl = slice_surface(project, SlipCircle(**CIRCLE), num_slices=n)
    assert sl is not None
    return sl


# The three methods the reference itself reports for this case. They are
# the ones that satisfy moment equilibrium (or solve for the inter-slice
# inclination), which is what makes the equivalence exact.
RIGOROUS = [("Bishop", BishopSimplified()),
            ("Spencer", Spencer()),
            ("GLE", GLEMorgensternPrice())]


# ======================================================================
class TestVerification70:
    """The published case, reproduced."""

    def test_referee_factor_of_safety_30ft(self):
        for name, m in RIGOROUS:
            f = fos(ponded(75.0), m)
            assert abs(f - REFEREE_FOS) / REFEREE_FOS < 0.005, (name, f)

    def test_referee_factor_of_safety_60ft(self):
        for name, m in RIGOROUS:
            f = fos(ponded(105.0), m)
            assert abs(f - REFEREE_FOS) / REFEREE_FOS < 0.005, (name, f)

    #: How far each method may drift when the pond is raised. Bishop is
    #: EXACT, and so is Janbu simplified; Spencer and GLE are not, for a
    #: reason measured in v0.1.106 and stated in the case below.
    DEPTH_INVARIANCE = {"Bishop": 1e-6, "Spencer": 1e-3, "GLE": 1e-3}

    def test_invariant_to_the_depth_of_water_above_the_slope(self):
        """The signature of a correct treatment: on an already-submerged
        slope the added weight and the added thrust cancel exactly, so
        raising the water changes nothing.

        EXACTLY, for a method whose equation is a ratio of global sums:
        Bishop holds this to 1e-12. Spencer and GLE hold it to 3e-4, and
        v0.1.106 measured why rather than widening the number quietly —
        see ``test_the_two_lambda_methods_are_only_nearly_invariant``.
        """
        for name, m in RIGOROUS:
            a = fos(ponded(75.0), m)
            b = fos(ponded(105.0), m)
            tol = self.DEPTH_INVARIANCE[name]
            assert math.isclose(a, b, rel_tol=tol), (name, a, b, tol)

    def test_the_two_lambda_methods_are_only_nearly_invariant(self):
        """WHY Spencer and GLE get 1e-3 above, pinned so it cannot be taken
        for rounding. Reported under rule 6 in v0.1.106, not corrected.

        Their defining assumption is ``X = lambda * E`` where ``E`` is the
        TOTAL inter-slice force — Fredlund and Krahn (1977) write it that
        way, and the pressure of the water standing on the vertical face
        between two slices is part of it. Raise the pond and every ``E``
        grows, so at a FIXED lambda the inter-slice shear grows with it and
        the two branches move a lot:

            lambda = 0.0    F_f and F_m invariant to 9e-13   (they ARE Janbu
                                                              simplified and
                                                              Bishop)
            lambda = 0.1    F_f moves 16 %,  F_m moves 0.6 %
            lambda = 0.2    F_f moves 45 %,  F_m moves 1.3 %

        What rescues the answer is that the CROSSING moves with them: the
        root lambda shifts until F_f = F_m lands almost where it did, and
        the factor of safety ends up 3e-4 apart instead of 16 %. "Almost"
        is the honest word, and this case is where it is written down.

        The way out is the effective/total fork that
        ``PrescribedInclinationMethod`` already offers the Corps methods
        (``MethodsSettings.interslice_forces``, v0.1.98), extended to these
        two. It is NOT done here: docs/PENDIENTES.md section 7 records that
        the datum needed to settle effective-versus-total is still missing,
        and the reference's own Spencer separates from its own Bishop by
        +1.888 % on the piezometric model where OGR with TOTAL forces gives
        +2.14 % — which is evidence for keeping totals, not against.

        The two assertions are a two-sided tripwire: the drift must be
        small enough to be a distribution effect, and large enough that it
        has not silently been fixed without this note being updated.
        """
        for name in ("Spencer", "GLE"):
            m = dict(RIGOROUS)[name]
            a = fos(ponded(75.0), m)
            b = fos(ponded(105.0), m)
            drift = abs(a - b) / b
            assert drift < 1e-3, (name, a, b, drift)
            assert drift > 1e-5, (
                f"{name} is now invariant to {drift:.1e}. If the inter-slice "
                f"assumption was moved onto EFFECTIVE forces, this case and "
                f"docs/PENDIENTES.md section 7 both need rewriting.")

    def test_the_lambda_zero_branches_are_exactly_invariant(self):
        """And the control that identifies the mechanism rather than naming
        a suspect: with no inter-slice shear there is no total-force
        assumption to be sensitive to, and the exactness comes back."""
        from ogr_slip2d import JanbuSimplified
        for m in (BishopSimplified(tolerance=1e-9),
                  JanbuSimplified(tolerance=1e-9)):
            a = fos(ponded(75.0), m)
            b = fos(ponded(105.0), m)
            assert math.isclose(a, b, rel_tol=1e-9), (m.METHOD_ID, a, b)

    def test_ponded_water_is_never_negative_factor_of_safety(self):
        """The v0.1.60 behaviour: u carried the whole head, the water's
        weight carried none of it, and the factor of safety went below
        zero — worse the deeper the water."""
        for _, m in RIGOROUS:
            assert fos(ponded(75.0), m) > 0.0
            assert fos(ponded(105.0), m) > 0.0


# ======================================================================
class TestDuncanWrightEquivalence:
    """Total weights + water forces + u  ≡  buoyant weights, no water."""

    def test_rigorous_methods_agree_with_the_buoyant_procedure(self):
        for name, m in RIGOROUS:
            a = fos(ponded(75.0), m)
            b = fos(buoyant(), m)
            assert abs(a - b) / b < 0.005, (name, a, b)

    def test_force_methods_agree_within_their_own_accuracy(self):
        """Janbu ignores inter-slice shear and Lowe-Karafiath prescribes
        the inter-slice inclination, so neither reproduces the identity
        exactly — but both must stay close, and both must be invariant to
        the depth of water."""
        for name, m in (("Janbu", JanbuSimplified()),
                        ("Lowe-Karafiath", LoweKarafiath())):
            a = fos(ponded(75.0), m)
            b = fos(buoyant(), m)
            assert abs(a - b) / b < 0.02, (name, a, b)
            c = fos(ponded(105.0), m)
            assert abs(c - a) / a < 0.01, (name, a, c)


# ======================================================================
class TestForceDecomposition:
    """Water in still contact with a sloping surface exerts p = γ_w·d
    NORMAL to it. The vertical component is the weight of the water
    column; the horizontal one integrates to the classical thrust."""

    def test_horizontal_thrust_matches_the_hydrostatic_identity(self):
        """Σ F_h = ½γ_w·d₁² − ½γ_w·d₂², the difference of the thrusts on
        the two vertical end faces. Follows from integrating γ_w·(y_w −
        y_g)·y_g′ along the ground, and holds for any slice count."""
        for wt in (75.0, 105.0):
            for n in (25, 100):
                sl = _slices(ponded(wt), n)
                got = sum(s.water_force_h for s in sl.slices)
                d1 = wt - sl.slices[0].top_y_left
                d2 = wt - sl.slices[-1].top_y_right
                exact = 0.5 * GAMMA_W * (d1 * d1 - d2 * d2)
                assert math.isclose(got, exact, rel_tol=1e-9), (wt, n, got,
                                                                exact)

    def test_vertical_load_is_the_weight_of_the_water_column(self):
        """Σ water_weight = γ_w · (area of water standing over the mass).

        The ground of this model is two straight pieces, so the area
        integrates in closed form: a trapezium over the slope from
        (30, 15) to (105, 45), plus a rectangle over the crest bench.
        """
        wt = 75.0
        sl = _slices(ponded(wt), 400)
        x_l = sl.slices[0].base_x_left
        x_r = sl.slices[-1].base_x_right
        # Daylights at the toe break and on the crest bench. The left
        # endpoint carries the root-finder's tolerance, hence abs_tol.
        assert math.isclose(x_l, 30.0, abs_tol=1e-3)
        assert x_r > 105.0

        # ∫ (wt − y_ground) dx, in two pieces. The slope rises 30 over 75.
        x_mid = 105.0
        y_at = lambda x: 15.0 + 0.4 * (x - 30.0)
        area = (wt - y_at(x_l) + wt - 45.0) * 0.5 * (x_mid - x_l)  # trapezium
        area += (wt - 45.0) * (x_r - x_mid)                        # rectangle
        expect = GAMMA_W * area

        got = sum(s.water_weight for s in sl.slices)
        # The only discretisation error is the single slice straddling
        # the slope break at x = 105.
        assert math.isclose(got, expect, rel_tol=1e-4), (got, expect)

    def test_no_water_surface_means_no_water_forces(self):
        sl = _slices(buoyant())
        assert all(s.water_weight == 0.0 for s in sl.slices)
        assert all(s.water_force_h == 0.0 for s in sl.slices)


# ======================================================================
class TestOnlyWaterTablesPond:
    """The documented, hard rule that separates the two entities: a
    piezometric line drawn above the ground does NOT define ponded
    water, because it records a pressure head, not a body of water."""

    def test_piezometric_line_above_the_ground_does_not_pond(self):
        sl = _slices(ponded(75.0, btype=BoundaryType.PIEZOMETRIC))
        assert all(s.water_weight == 0.0 for s in sl.slices)
        assert all(s.water_force_h == 0.0 for s in sl.slices)

    def test_a_drawdown_line_does_not_pond_by_itself(self):
        """v0.1.69 — it used to, and that was the third of the four
        defects that made the B-bar drawdown return the pre-drawdown
        factor of safety.

        The drawdown line is the reservoir level AFTER the drawdown, so
        while it stood here alongside the water table under a
        highest-wins rule, the post-drawdown analysis carried the weight
        of the reservoir it had just emptied. When the final level does
        pond — and it does, wherever it still stands above the slope —
        it is because ``drawdown_levels.level_project`` has made it the
        water table for that stage. The test below is the same geometry
        run through that projection.
        """
        sl = _slices(ponded(75.0, btype=BoundaryType.DRAWDOWN))
        assert all(s.water_weight == 0.0 for s in sl.slices)
        assert all(s.water_force_h == 0.0 for s in sl.slices)

    def test_the_final_level_ponds_once_it_is_the_water_table(self):
        """The other half: promoted by the level projection, it loads
        the slope exactly as a water table at the same elevation."""
        from ogr_core.hydraulic.drawdown_levels import level_project

        projected = level_project(ponded(75.0, btype=BoundaryType.DRAWDOWN),
                                  use_drawdown=True)
        got = sum(s.water_weight for s in _slices(projected).slices)
        expect = sum(s.water_weight for s in _slices(ponded(75.0)).slices)
        assert got > 0.0
        assert math.isclose(got, expect, rel_tol=1e-9)

    def test_water_surface_below_the_ground_does_not_pond(self):
        # The lowest ground the sliding mass touches is the toe at y = 15
        sl = _slices(ponded(10.0))
        assert all(s.water_weight == 0.0 for s in sl.slices)
        assert all(s.water_force_h == 0.0 for s in sl.slices)


# ======================================================================
class TestSeismicIgnoresPondedWater:
    """Water has no shear strength, so its motion develops no inertial
    force the sliding mass must carry. The reference defines the seismic
    force as 'coefficient × area of slice × unit weight of slice
    material' — the soil, not the water."""

    def test_seismic_force_is_proportional_to_the_soil_weight_only(self):
        from ogr_slip2d.external_forces import slice_forces
        sl = _slices(ponded(75.0))
        for s in sl.slices:
            f = slice_forces(s, kh=0.15, kv=0.0)
            assert math.isclose(f.h_seismic, 0.15 * s.weight, rel_tol=1e-12)
            # ...while the load the base carries does include the water
            assert f.w_total >= f.w_soil

    def test_deeper_water_does_not_increase_the_seismic_force(self):
        from ogr_slip2d.external_forces import slice_forces
        a = sum(slice_forces(s, 0.15, 0.0).h_seismic
                for s in _slices(ponded(75.0)).slices)
        b = sum(slice_forces(s, 0.15, 0.0).h_seismic
                for s in _slices(ponded(105.0)).slices)
        assert math.isclose(a, b, rel_tol=1e-12)


# ======================================================================
class TestRuIncludesPondedWater:
    """The vertical earth pressure that drives the Ru model includes the
    weight of ponded water standing above the point (and excludes
    external loads, which is why the surcharge is absent)."""

    def _u(self, wt_y):
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = _base_project("ru")
        if wt_y is not None:
            p.add_boundary(Boundary(polyline=Polyline(
                vertices=[Vertex(-10, wt_y), Vertex(150, wt_y)], closed=False),
                btype=BoundaryType.WATER_TABLE))
        mat = Material(
            name="Ru", strength=MohrCoulomb(cohesion=10, friction_angle=25),
            unit_weight=120.0, pore_pressure=PorePressureType.RU_COEFFICIENT,
            ru=0.4)
        p.materials = [mat]
        return pore_pressure_at(p, Vertex(10.0, 5.0), mat,
                                ground_surface_y=15.0)

    def test_without_ponding_it_is_ru_gamma_z(self):
        assert math.isclose(self._u(None), 0.4 * 120.0 * 10.0, rel_tol=1e-12)

    def test_with_ponding_the_water_column_is_added(self):
        # 25 ft of water over a ground at y = 15, point 10 ft below it
        expect = 0.4 * (120.0 * 10.0 + GAMMA_W * 25.0)
        assert math.isclose(self._u(40.0), expect, rel_tol=1e-12)


# ======================================================================
class TestTensionCrackForceReachesTheResult:
    """From v0.1.7 to v0.1.60 the hydrostatic force of water in a tension
    crack was computed, stored on the Slices, and read by no LEM method
    at all — so a water-filled crack changed nothing and the factor of
    safety came out too high, on the unsafe side."""

    def _project(self, mode):
        p = Project("tc")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
            Vertex(35, 10), Vertex(15, 30), Vertex(0, 30)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 24), Vertex(14, 24)], closed=False),
            btype=BoundaryType.TENSION_CRACK))
        p.materials = [Material(
            name="S", strength=MohrCoulomb(cohesion=20, friction_angle=25))]
        p.tension_crack_properties = TensionCrackProperties(mode=mode)
        return p

    _CIRCLE = dict(centre_x=25.0, centre_y=40.0, radius=25.0)

    def _fos(self, mode, method):
        ev = GridSearch(method=method, num_slices=30, min_area=0.0)
        r = ev.evaluate_circle(self._project(mode), SlipCircle(**self._CIRCLE))
        assert r is not None
        return r.fos

    def test_force_lands_on_a_slice(self):
        sl = slice_surface(self._project(WaterLevelMode.FILLED),
                           SlipCircle(**self._CIRCLE), num_slices=30)
        assert sl.tension_crack_force > 0.0
        # The whole ½γ_w·h² is handed to one slice, nothing lost on the
        # way. The per-slice value is signed (+x); the stored one is a
        # magnitude, hence the modulus.
        assert math.isclose(abs(sum(s.water_force_h for s in sl.slices)),
                            sl.tension_crack_force, rel_tol=1e-12)

    def test_water_in_the_crack_lowers_the_factor_of_safety(self):
        for name, m in (("Bishop", BishopSimplified()),
                        ("Janbu", JanbuSimplified()),
                        ("Spencer", Spencer()),
                        ("GLE", GLEMorgensternPrice()),
                        ("Ordinary", OrdinaryFellenius()),
                        ("Lowe-Karafiath", LoweKarafiath())):
            dry = self._fos(WaterLevelMode.DRY, m)
            wet = self._fos(WaterLevelMode.FILLED, m)
            assert wet < dry, (name, dry, wet)
            # A real effect, not numerical noise
            assert (dry - wet) / dry > 0.01, (name, dry, wet)

    def test_dry_crack_changes_nothing(self):
        sl = slice_surface(self._project(WaterLevelMode.DRY),
                           SlipCircle(**self._CIRCLE), num_slices=30)
        assert sl.tension_crack_force == 0.0
        assert all(s.water_force_h == 0.0 for s in sl.slices)


# ======================================================================
class TestCanvasShowsPondedWater:
    """The three display flags shipped in v0.1.23 and were read by
    nobody, so the checkbox in Display Options did nothing (rule 7)."""

    def _window(self):
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        _WINDOWS.append(w)
        w.project.add_boundary(Boundary(polyline=_external(),
                                        btype=BoundaryType.EXTERNAL))
        return w

    def _count(self, w):
        w.canvas.refresh_scene()
        return len(w.canvas.scene().items())

    def test_the_checkbox_moves_something(self):
        w = self._window()
        w.project.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 55), Vertex(140, 55)], closed=False),
            btype=BoundaryType.WATER_TABLE))
        w.canvas.display_options.show_ponded_water = True
        on = self._count(w)
        w.canvas.display_options.show_ponded_water = False
        off = self._count(w)
        assert on > off

    def test_a_piezometric_line_draws_no_pond(self):
        """Same polyline, same elevation: as a water table it hatches a
        pond, as a piezometric line it must not."""
        w = self._window()
        before = self._count(w)
        line = [Vertex(0, 55), Vertex(140, 55)]
        w.project.add_boundary(Boundary(
            polyline=Polyline(vertices=list(line), closed=False),
            btype=BoundaryType.PIEZOMETRIC))
        w.canvas.display_options.show_ponded_water = True
        piezo_delta = self._count(w) - before

        w2 = self._window()
        w2.project.add_boundary(Boundary(
            polyline=Polyline(vertices=list(line), closed=False),
            btype=BoundaryType.WATER_TABLE))
        w2.canvas.display_options.show_ponded_water = True
        wt_delta = self._count(w2) - before

        # Both add their own line plus a letter; only the water table
        # adds the pond hatching on top.
        assert wt_delta > piezo_delta + 5, (wt_delta, piezo_delta)

    def test_water_surface_label_does_not_crash_the_canvas(self):
        """``QGraphicsItem`` was used in the W/P/D label without ever
        being imported, so any project with a water surface raised
        NameError and took the whole repaint down."""
        w = self._window()
        w.project.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 20), Vertex(140, 20)], closed=False),
            btype=BoundaryType.WATER_TABLE))
        assert self._count(w) > 0
