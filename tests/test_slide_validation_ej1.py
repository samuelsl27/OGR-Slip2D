# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Numerical validation against a Slide reference run (Slide2d_Ej_1_General).

This is the project's first end-to-end numerical benchmark against the
reference program. Geometry, materials and grid settings are taken
verbatim from the reference; the expected factors of safety and the
critical-circle geometry come from the reference's Info Viewer / report.

Reference (Global Minimums):
  Bishop simplified: FS = 0.882889, centre (88.000, 70.500), R = 47.2124436
  Janbu  simplified: FS = 0.842548, centre (84.000, 66.000), R = 41.5014358
  25 slices, Grid Search, Radius Increment 10, Composite disabled.
  Population 21 x 21 x 11 = 4851 circles.

The radii above carry seven decimals since v0.1.88 for a reason: they are
the 5th and 4th of the eleven the reference generates at those centres, and
until v0.1.88 this program generated neither. The cases below therefore
assert the critical CENTRE AND RADIUS, not only the factor of safety —
matching a number from a different surface is agreement by luck. See
tests/test_grid_radius_rule_v188.py for the radius rule itself.
"""
from __future__ import annotations
import math


_GRID_CACHE: dict = {}

# The reference grid, verbatim from Slide2d_Ej_1_General.sli.
#
# min_radius is 0 since v0.1.88: the reference has no minimum-radius control,
# so any floor here samples a different population than the one being
# validated.
_GRID = dict(grid_x=(40, 120), grid_y=(30, 120), grid_nx=20, grid_ny=20,
             radius_increment=10, min_radius=0.0,
             num_slices=25, min_area=0.5)

# (X intervals + 1)(Y intervals + 1)(Radius Increment + 1), the population
# the reference documents and reports.
_EXPECTED_TOTAL = 21 * 21 * 11      # 4851


def _grid_result(method_id: str):
    """The reference Grid Search, run once per method for the whole file.

    4851 circles is about twenty seconds. Six cases across three classes
    interrogate these runs; each starting its own would cost two minutes.
    """
    if method_id not in _GRID_CACHE:
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        _GRID_CACHE[method_id] = GridSearch(
            method=get_method(method_id)(), **_GRID).run(_ej1_project())
    return _GRID_CACHE[method_id]


def _ej1_project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(120, 0), Vertex(120, 25), Vertex(75, 25), Vertex(50, 50),
        Vertex(0, 50), Vertex(0, 30), Vertex(0, 20), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ej1")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m1 = Material(name="Mat1", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=15, friction_angle=25))
    m2 = Material(name="Mat2", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=10, friction_angle=25))
    m3 = Material(name="Mat3", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=19, friction_angle=30))
    p.materials = [m1, m2, m3]
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 30), Vertex(75, 25)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 20), Vertex(120, 10)], closed=False),
        btype=BoundaryType.MATERIAL))
    regs = p.resolve_regions()
    top = max(regs, key=lambda r: r.centroid()[1])
    bot = min(regs, key=lambda r: r.centroid()[1])
    mid = [r for r in regs if r not in (top, bot)][0]
    p.assign_material_at(*top.centroid(), m1.id)
    p.assign_material_at(*mid.centroid(), m2.id)
    p.assign_material_at(*bot.centroid(), m3.id)
    return p


class TestSlideValidationEj1:
    def test_three_regions(self):
        p = _ej1_project()
        assert len(p.resolve_regions()) == 3

    def test_bishop_reference_circle_fos(self):
        """LEM on the EXACT reference critical circle must match Slide
        to within 0.5 %."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        res = ev.evaluate_circle(
            p, SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212))
        assert res is not None
        assert abs(res.fos - 0.882889) / 0.882889 < 0.005, res.fos

    def test_janbu_reference_circle_fos(self):
        from ogr_slip2d import JanbuSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        ev = GridSearch(method=JanbuSimplified(), num_slices=25,
                        min_area=0.0)
        res = ev.evaluate_circle(
            p, SlipCircle(centre_x=84.0, centre_y=66.0, radius=41.501))
        assert res is not None
        assert abs(res.fos - 0.842548) / 0.842548 < 0.005, res.fos

    def test_reference_circle_25_slices(self):
        """The slicer must build exactly 25 slices on the reference
        circle (no off-by-one from endpoint round-off)."""
        from ogr_slip2d.surface import SlipCircle
        from ogr_slip2d.slicer import slice_surface
        p = _ej1_project()
        slices = slice_surface(
            p, SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212),
            num_slices=25)
        assert slices is not None
        assert len(slices) == 25, len(slices)

    def test_non_composite_exit_at_toe(self):
        """With a footed slope the circle must daylight at the toe
        (x≈74.84), not run on to the far re-crossing (x≈100.6)."""
        from ogr_slip2d.surface import SlipCircle
        from ogr_slip2d.slicer import _ground_surface_from_external
        p = _ej1_project()
        ground = _ground_surface_from_external(p.external_boundary())
        c = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        c.intersect_with_ground(ground)
        assert abs(c.x_left - 45.470) < 0.1, c.x_left
        assert abs(c.x_right - 74.842) < 0.2, c.x_right

    def test_bishop_grid_search_finds_minimum(self):
        """Within 0.5 %, and it used to have to be 1 %.

        v0.1.88 — with the measured radius rule the search reaches the
        reference's own critical radius (47.2124436, the 5th of the eleven
        at centre (88, 70.5)), which the previous per-centre bracket never
        generated. +0.18 % -> +0.02 %.
        """
        r = _grid_result("bishop_simplified")
        assert r.critical is not None
        assert abs(r.critical.fos - 0.882889) / 0.882889 < 0.005, \
            r.critical.fos

    def test_bishop_search_lands_on_the_reference_circle(self):
        """The assertion that could not be made before v0.1.88. Matching a
        factor of safety from a different surface is agreement by luck, and
        that is exactly what the old sampling was doing."""
        sd = _grid_result("bishop_simplified").critical.surface.to_dict()
        assert abs(sd["centre_x"] - 88.0) < 1e-6, sd["centre_x"]
        assert abs(sd["centre_y"] - 70.5) < 1e-6, sd["centre_y"]
        assert abs(sd["radius"] - 47.2124436) < 1e-3, sd["radius"]

    def test_janbu_grid_search_finds_minimum(self):
        """v0.1.88 — this used to accept "anything at or below the reference
        within 1 %", because the search landed on centre (80, 61.5) with
        0.8379 (-0.55 %) instead of the reference's (84, 66). It now finds
        the reference's centre and radius, so the assertion can be two-sided.
        """
        r = _grid_result("janbu_simplified")
        assert r.critical is not None
        assert abs(r.critical.fos - 0.842548) / 0.842548 < 0.005, \
            r.critical.fos
        sd = r.critical.surface.to_dict()
        assert abs(sd["centre_x"] - 84.0) < 1e-6, sd["centre_x"]
        assert abs(sd["centre_y"] - 66.0) < 1e-6, sd["centre_y"]
        assert abs(sd["radius"] - 41.5014358) < 1e-3, sd["radius"]

    def test_generated_population_matches_the_reference(self):
        """4851 circles, the identity the reference documents. Ej_1 is the
        model that makes this bite: 21 of its 441 centres sit directly above
        the right Slope Limit, where the radius bracket has zero width."""
        r = _grid_result("bishop_simplified")
        assert r.total_count == _EXPECTED_TOTAL, r.total_count


class TestAllMethodsValidationEj1:
    """v0.1.19 — validate every available LEM method against the Slide
    reference FoS on its own global-minimum circle, plus the Janbu
    corrected fix (was +2.95 %, now +0.10 %)."""

    # (method_id, centre_x, centre_y, radius, reference FoS, tol %)
    _REF = [
        ("ordinary_fellenius", 84.0, 66.0, 41.501, 0.849535, 0.5),
        ("bishop_simplified",  88.0, 70.5, 47.212, 0.882889, 0.5),
        ("janbu_simplified",   84.0, 66.0, 41.501, 0.842548, 0.5),
        ("janbu_corrected",    88.0, 70.5, 47.212, 0.883036, 0.5),
        # v0.1.106 — these two were the only entries at 1.0 %, and the
        # asymmetry WAS the finding: the two methods that needed double the
        # margin were exactly the two sharing the lambda machinery. They come
        # down to 0.5 % now that the inter-slice forces reach the base normal
        # (0.64 % -> 0.343 % and 0.53 % -> 0.158 %). A tolerance is only
        # allowed to shrink when its cause does; see
        # docs/audits/spencer_gle_interslice_v179.md.
        ("spencer",            88.0, 70.5, 47.212, 0.876917, 0.5),
        ("gle_morgenstern_price", 88.0, 70.5, 47.212, 0.878343, 0.5),
    ]

    @staticmethod
    def _method(mid):
        import ogr_slip2d as M
        return {
            "ordinary_fellenius": M.OrdinaryFellenius,
            "bishop_simplified": M.BishopSimplified,
            "janbu_simplified": M.JanbuSimplified,
            "janbu_corrected": M.JanbuCorrected,
            "spencer": M.Spencer,
            "gle_morgenstern_price": M.GLEMorgensternPrice,
        }[mid]()

    def test_all_methods_reference_circle(self):
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        for mid, cx, cy, r, ref, tol in self._REF:
            ev = GridSearch(method=self._method(mid), num_slices=25,
                            min_area=0.0)
            res = ev.evaluate_circle(
                p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
            assert res is not None, mid
            err = abs(res.fos - ref) / ref * 100
            assert err < tol, f"{mid}: FS={res.fos:.5f} err={err:.2f}%"

    def test_janbu_corrected_factor_under_one_pct(self):
        """The Janbu corrected correction-factor fix must keep the
        result within 0.5 % (regression on the d/L definition)."""
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        import ogr_slip2d as M
        p = _ej1_project()
        ev = GridSearch(method=M.JanbuCorrected(), num_slices=25,
                        min_area=0.0)
        res = ev.evaluate_circle(
            p, SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212))
        assert abs(res.fos - 0.883036) / 0.883036 < 0.005, res.fos


class TestReportGeneration:
    """v0.1.19 — PDF report generation smoke tests."""

    def test_generate_report_smoke(self, tmp_path=None):
        import tempfile, os
        from ogr_core.report import generate_report
        p = _ej1_project()
        # The same two runs the validation cases above already paid for.
        # A report smoke test needs a populated SearchResult, not its own
        # search; running one cost forty seconds for no extra coverage.
        results = {mid: _grid_result(mid)
                   for mid in ("bishop_simplified", "janbu_simplified")}
        out = os.path.join(tempfile.gettempdir(), "ogr_test_report.pdf")
        generate_report(p, results, out, author="Test", company="UPCT",
                        title="Test Report")
        assert os.path.exists(out)
        assert os.path.getsize(out) > 2000
        # PDF magic header
        with open(out, "rb") as f:
            assert f.read(4) == b"%PDF"
        os.remove(out)


class TestLoweKarafiathValidationEj1:
    """v0.1.20 — Lowe-Karafiath (force equilibrium, inter-slice angle =
    average of ground-surface and base inclinations). Validated against
    the reference FoS on the rigorous global-minimum circle."""

    def test_lowe_karafiath_reference_circle(self):
        from ogr_slip2d import LoweKarafiath
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        ref = 0.885220
        ev = GridSearch(method=LoweKarafiath(), num_slices=25, min_area=0.0)
        res = ev.evaluate_circle(
            p, SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212))
        assert res is not None
        assert res.converged, "Lowe-Karafiath did not converge"
        err = abs(res.fos - ref) / ref * 100
        assert err < 1.0, f"Lowe-Karafiath FS={res.fos:.5f} err={err:.2f}%"

    def test_lowe_karafiath_registered_as_force_method(self):
        from ogr_slip2d.methods import method_registry
        reg = method_registry()
        assert "lowe_karafiath" in reg
        cls = reg["lowe_karafiath"]
        assert cls.SATISFIES_FORCE is True
        assert cls.SATISFIES_MOMENT is False

    def test_lowe_karafiath_grid_search_no_spurious_low_root(self):
        """A full grid search must not return a spurious very-low FoS:
        the force-equilibrium recursion can develop a pole at small F
        (D_i → 0) that produces a fake low root. The admissibility guard
        (D_i > 0) prunes it, so the critical FoS should track Bishop on
        the same grid to within a few percent."""
        from ogr_slip2d import BishopSimplified, LoweKarafiath
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        kw = dict(grid_x=(60, 110), grid_y=(55, 95), grid_nx=8, grid_ny=8,
                  radius_increment=8, min_radius=10.0, num_slices=20,
                  min_area=0.5)
        rL = GridSearch(method=LoweKarafiath(), **kw).run(p)
        rB = GridSearch(method=BishopSimplified(), **kw).run(p)
        assert rL.critical is not None and rB.critical is not None
        # No spurious collapse: the critical FoS must be physical.
        assert rL.critical.fos > 0.5, rL.critical.fos
        rel = abs(rL.critical.fos - rB.critical.fos) / rB.critical.fos
        assert rel < 0.05, (rL.critical.fos, rB.critical.fos)


class TestSearchAnomaliesA1A2:
    """v0.1.24 — regression tests for anomalies A1 (Path Search) and A2
    (Slope Search), both caused by the same sign error in the documented
    'Initial Angle at Toe' upper limit: it was applied as −(β − 5)°
    instead of +(β − 5)°, collapsing the admissible window to a sliver of
    steeply-diving directions and making the true critical surface
    impossible to generate."""

    def test_a2_slope_search_matches_reference(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch
        p = _ej1_project()
        r = SlopeSearch(method=BishopSimplified(), num_surfaces=400,
                        num_slices=18, seed=7).run(p)
        assert r.critical is not None
        # Reference Bishop global minimum for this model is 0.882889.
        err = abs(r.critical.fos - 0.882889) / 0.882889
        assert err < 0.05, f"Slope Search FoS={r.critical.fos:.4f}"
        # Before the fix only ~23 % of surfaces were valid.
        assert r.valid_count > 200, r.valid_count

    def test_a1_path_search_finds_critical_surface(self):
        """v0.1.104 — the optimisation is now ASKED FOR, and the band below
        is untouched.

        Until v0.1.104 this call optimised without saying so: Path Search
        carried a private random walk switched on by ``path_optimize``,
        which defaulted to True and which no dialog ever showed. Removing
        it left this search unoptimised, and unoptimised it comes back with
        1.027 instead of the 0.6-to-1.0 band asserted here.

        The band is a reference claim and is NOT what gets adjusted: it says
        a Path Search must land in the physical range of the circular
        minimum (0.883) rather than at the 1.60 the pre-A1 sign error gave.
        What is restored is the CONFIGURATION the test was written against,
        stated this time instead of inherited from a hidden default.
        """
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.optimize import OptimizeSettings
        from ogr_slip2d.search import PathSearch
        p = _ej1_project()
        r = PathSearch(method=BishopSimplified(), num_paths=80,
                       num_slices=18, seed=7,
                       optimize=OptimizeSettings(enabled=True,
                                                 max_iterations=200)).run(p)
        assert r.critical is not None
        # Non-circular surfaces may be more critical than the circular
        # minimum (0.883), but must be in the same physical range — the
        # pre-fix value was 1.60.
        assert 0.6 < r.critical.fos < 1.0, r.critical.fos

    def test_a1_path_search_counts_valid_surfaces(self):
        """'Number of Surfaces' means VALID surfaces: generation must
        continue until the requested count is reached (attempt-capped)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _ej1_project()
        n = 60
        r = PathSearch(method=BishopSimplified(), num_paths=n,
                       num_slices=18, seed=11).run(p)
        assert r.valid_count >= n, (r.valid_count, n)
        assert r.attempts >= r.valid_count

    def test_initial_angle_window_includes_reference_tangent(self):
        """The reference critical circle leaves the toe rising at about
        +15.5° towards the crest; that direction must lie inside the
        default Initial-Angle-at-Toe window (it did not before the fix)."""
        beta_deg = 45.0          # reference slope face
        ang_lo, ang_hi = -45.0, beta_deg - 5.0
        assert ang_lo <= 15.5 <= ang_hi
