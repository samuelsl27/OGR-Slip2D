# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.40 — Back Analysis of Support Force.

Determines the support force needed to bring a slip surface to a target
factor of safety, and reports the surface requiring the MAXIMUM force.

The validations below are analytic properties of the formulation rather
than stored numbers:

* at a target equal to the UNSUPPORTED factor of safety the required
  force must be zero — the surface already meets the target;
* the required force must grow monotonically with the target;
* **active and passive coincide exactly at a target of 1.0**, because
  ``D − R/1`` and ``1·D − R`` are the same expression — a clean closed-
  form identity that would break under almost any algebraic slip;
* passive is never below active for targets above 1;
* **the elevation changes the Bishop result but leaves Janbu untouched**,
  which is the behavioural signature the reference calls out: Bishop
  works from moment equilibrium so the elevation sets the moment arm,
  while Janbu uses force equilibrium where a horizontal force enters the
  same way wherever it acts;
* the method is refused for anything other than Bishop, Janbu and Janbu
  Corrected.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.back_analysis import (  # noqa: E402
    SUPPORTED_METHODS,
    required_force,
    run_back_analysis,
)
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.slicer import slice_surface  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)


def _setup():
    p = _ej1_project()
    sl = slice_surface(p, _CIRCLE, num_slices=25)
    fos = GridSearch(method=BishopSimplified(), num_slices=25,
                     min_area=0.0).evaluate_circle(p, _CIRCLE).fos
    return p, sl, fos


def _force(sl, target, method="bishop_simplified", elevation=25.0):
    return required_force(sl, _CIRCLE, target, method, elevation)


class TestRequiredForce:
    def test_zero_at_the_unsupported_factor(self):
        """No support is needed to reach a factor the surface already
        has."""
        _p, sl, fos = _setup()
        r = _force(sl, fos)
        assert r is not None
        assert abs(r.active_force) < 1.0, r.active_force
        assert abs(r.passive_force) < 1.0, r.passive_force

    def test_zero_below_the_unsupported_factor(self):
        """A target the surface already exceeds must report zero, not a
        negative force."""
        _p, sl, fos = _setup()
        r = _force(sl, fos * 0.7)
        assert r.active_force == 0.0
        assert r.passive_force == 0.0

    def test_grows_with_the_target(self):
        _p, sl, _f = _setup()
        vals = [_force(sl, t).passive_force
                for t in (1.0, 1.2, 1.4, 1.6)]
        for a, b in zip(vals, vals[1:]):
            assert b > a, vals

    def test_active_and_passive_coincide_at_unity(self):
        """T_active = D − R/1 and T_passive = 1·D − R are the same
        expression, so the two assumptions must agree exactly at a target
        of 1.0."""
        _p, sl, _f = _setup()
        r = _force(sl, 1.0)
        assert abs(r.active_force - r.passive_force) < 1e-6

    def test_passive_exceeds_active_above_unity(self):
        _p, sl, _f = _setup()
        for t in (1.2, 1.5, 2.0):
            r = _force(sl, t)
            assert r.passive_force > r.active_force, t

    def test_governing_force_is_the_larger(self):
        _p, sl, _f = _setup()
        r = _force(sl, 1.4)
        assert r.governing_force == max(r.active_force, r.passive_force)

    def test_unsupported_fos_not_guessed_by_the_solver(self):
        """``required_force`` must NOT invent an unsupported factor: its
        resisting sum is evaluated at the TARGET, so any ratio derived
        there would be one fixed-point step from the target rather than
        the converged answer. The field stays NaN until the driver fills
        it from a real evaluation."""
        _p, sl, _fos = _setup()
        assert math.isnan(_force(sl, 1.3).unsupported_fos)


class TestElevationBehaviour:
    def test_elevation_changes_bishop(self):
        """Bishop uses moment equilibrium, so the elevation sets the
        moment arm and must change the answer."""
        _p, sl, _f = _setup()
        vals = [_force(sl, 1.3, "bishop_simplified", el).passive_force
                for el in (0.0, 25.0, 40.0)]
        assert len({round(v, 6) for v in vals}) == 3, vals
        # Closer to the centre elevation -> shorter arm -> larger force
        for a, b in zip(vals, vals[1:]):
            assert b > a, vals

    def test_elevation_does_not_change_janbu(self):
        """Janbu considers only force equilibrium, so where a HORIZONTAL
        force acts is irrelevant — the reference states this explicitly."""
        _p, sl, _f = _setup()
        vals = [_force(sl, 1.3, "janbu_simplified", el).passive_force
                for el in (0.0, 10.0, 25.0, 40.0, 60.0)]
        assert max(vals) - min(vals) < 1e-6, vals

    def test_janbu_corrected_also_elevation_independent(self):
        _p, sl, _f = _setup()
        a = _force(sl, 1.3, "janbu_corrected", 0.0).passive_force
        b = _force(sl, 1.3, "janbu_corrected", 45.0).passive_force
        assert abs(a - b) < 1e-6

    def test_force_at_the_centre_elevation_is_undefined(self):
        """A horizontal force applied at the centre elevation has no
        moment arm, so the Bishop force is indeterminate."""
        _p, sl, _f = _setup()
        assert _force(sl, 1.3, "bishop_simplified",
                      _CIRCLE.centre_y) is None


class TestMethodRestriction:
    def test_supported_methods(self):
        assert set(SUPPORTED_METHODS) == {
            "bishop_simplified", "janbu_simplified", "janbu_corrected"}

    def test_unsupported_method_refused(self):
        _p, sl, _f = _setup()
        for mid in ("spencer", "gle_morgenstern_price", "lowe_karafiath",
                    "ordinary_fellenius"):
            assert _force(sl, 1.3, mid) is None, mid

    def test_invalid_target(self):
        _p, sl, _f = _setup()
        assert _force(sl, 0.0) is None
        assert _force(sl, -1.0) is None
        assert _force(sl, float("nan")) is None


class TestFullRun:
    def _search(self):
        return GridSearch(method=BishopSimplified(), grid_x=(70, 100),
                          grid_y=(60, 85), grid_nx=4, grid_ny=4,
                          radius_increment=8, min_radius=15,
                          num_slices=18, min_area=0.5)

    def test_reports_the_maximum_force_surface(self):
        p = _ej1_project()
        res = run_back_analysis(p, self._search(), target_fos=1.3,
                                elevation=25.0)
        assert res.critical is not None
        assert res.surfaces_analysed > 5
        assert res.required_force > 0

    def test_critical_really_is_the_maximum(self):
        """Re-derive the forces surface by surface and confirm none
        exceeds the reported critical."""
        p = _ej1_project()
        search = self._search()
        res = run_back_analysis(p, search, target_fos=1.3, elevation=25.0)
        run = search.run(p)
        best = 0.0
        for ev in run.evaluations:
            if not ev.is_valid or not ev.slices:
                continue
            r = required_force(ev.slices, ev.surface, 1.3,
                               "bishop_simplified", 25.0)
            if r is not None:
                best = max(best, r.governing_force)
        assert abs(best - res.required_force) < 1e-6

    def test_unsupported_fos_comes_from_the_evaluation(self):
        p = _ej1_project()
        search = self._search()
        res = run_back_analysis(p, search, target_fos=1.3,
                                elevation=25.0)
        assert math.isfinite(res.critical.unsupported_fos)
        assert 0.1 < res.critical.unsupported_fos < 5.0

    def test_summary_fields(self):
        p = _ej1_project()
        res = run_back_analysis(p, self._search(), target_fos=1.4,
                                elevation=30.0)
        s = res.summary()
        for k in ("method", "target_fos", "elevation", "surfaces",
                  "active_force", "passive_force", "required_force"):
            assert k in s
        assert abs(s["target_fos"] - 1.4) < 1e-12
        assert abs(s["elevation"] - 30.0) < 1e-12

    def test_unsupported_method_reports_error(self):
        p = _ej1_project()
        res = run_back_analysis(p, self._search(), target_fos=1.3,
                                method_id="spencer")
        assert res.critical is None
        assert "only available" in res.notes["error"]

    def test_invalid_target_reports_error(self):
        p = _ej1_project()
        res = run_back_analysis(p, self._search(), target_fos=0.0)
        assert res.critical is None
        assert "positive" in res.notes["error"]

    def test_does_not_modify_the_project(self):
        """The back analysis is independent of the main analysis."""
        p = _ej1_project()
        before = p.to_dict()
        run_back_analysis(p, self._search(), target_fos=1.3)
        assert p.to_dict() == before

    def test_progress_callback(self):
        p = _ej1_project()
        seen = []
        run_back_analysis(p, self._search(), target_fos=1.3,
                          progress_cb=lambda d, t: seen.append((d, t)))
        assert seen and seen[-1][0] == seen[-1][1]

    def test_higher_target_needs_more_force(self):
        p = _ej1_project()
        f12 = run_back_analysis(p, self._search(), 1.2, 25.0
                                ).required_force
        f16 = run_back_analysis(p, self._search(), 1.6, 25.0
                                ).required_force
        assert f16 > f12


class TestSettingsAndGui:
    def test_settings_round_trip(self):
        from ogr_core.project import Project
        p = _ej1_project()
        cfg = p.settings.back_analysis
        cfg.enabled = True
        cfg.target_fos = 1.45
        cfg.elevation = 30.0
        cfg.method_id = "janbu_simplified"
        p2 = Project.from_dict(p.to_dict())
        c2 = p2.settings.back_analysis
        assert c2.enabled is True
        assert abs(c2.target_fos - 1.45) < 1e-12
        assert abs(c2.elevation - 30.0) < 1e-12
        assert c2.method_id == "janbu_simplified"

    def test_settings_defaults(self):
        from ogr_core.project.settings import BackAnalysisSettings
        c = BackAnalysisSettings()
        assert c.enabled is False
        assert abs(c.target_fos - 1.3) < 1e-12
        assert c.method_id == "bishop_simplified"

    def test_menu_action_present(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            return
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        assert "back_analysis" in MainWindow()._actions
