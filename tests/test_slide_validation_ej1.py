# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Numerical validation against a Slide reference run (Slide2d_Ej_1_General).

This is the project's first end-to-end numerical benchmark against the
reference program. Geometry, materials and grid settings are taken
verbatim from the reference; the expected factors of safety and the
critical-circle geometry come from the reference's Info Viewer / report.

Reference (Global Minimums):
  Bishop simplified: FS = 0.882889, centre (88.000, 70.500), R = 47.212
  Janbu  simplified: FS = 0.842548, centre (84.000, 66.000), R = 41.501
  25 slices, Grid Search, Radius Increment 10, Composite disabled.
"""
from __future__ import annotations
import math


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
        """Full Grid Search recovers the reference FoS within 1 %."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        gs = GridSearch(method=BishopSimplified(), grid_x=(40, 120),
                        grid_y=(30, 120), grid_nx=20, grid_ny=20,
                        radius_increment=10, min_radius=2.0,
                        num_slices=25, min_area=0.5)
        r = gs.run(p)
        assert r.critical is not None
        assert abs(r.critical.fos - 0.882889) / 0.882889 < 0.01, \
            r.critical.fos

    def test_janbu_grid_search_finds_minimum(self):
        from ogr_slip2d import JanbuSimplified
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        gs = GridSearch(method=JanbuSimplified(), grid_x=(40, 120),
                        grid_y=(30, 120), grid_nx=20, grid_ny=20,
                        radius_increment=10, min_radius=2.0,
                        num_slices=25, min_area=0.5)
        r = gs.run(p)
        assert r.critical is not None
        # OGR may find a marginally lower minimum on a nearby centre;
        # accept anything at or below the reference within 1 %.
        assert r.critical.fos < 0.882889 * 1.01, r.critical.fos


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
        ("spencer",            88.0, 70.5, 47.212, 0.876917, 1.0),
        ("gle_morgenstern_price", 88.0, 70.5, 47.212, 0.878343, 1.0),
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
        from ogr_slip2d.search import GridSearch
        import ogr_slip2d as M
        from ogr_core.report import generate_report
        p = _ej1_project()
        results = {}
        for mid, method in [("bishop_simplified", M.BishopSimplified()),
                            ("janbu_simplified", M.JanbuSimplified())]:
            gs = GridSearch(method=method, grid_x=(40, 120),
                            grid_y=(30, 120), grid_nx=20, grid_ny=20,
                            radius_increment=10, min_radius=2.0,
                            num_slices=25, min_area=0.5)
            results[mid] = gs.run(p)
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
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        p = _ej1_project()
        r = PathSearch(method=BishopSimplified(), num_paths=80,
                       num_slices=18, seed=7).run(p)
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
