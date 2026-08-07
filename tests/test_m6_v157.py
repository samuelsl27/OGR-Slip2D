# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.57 — Design factors, parameter calculator and session registry
(phase M6).

The most consequential part is the first. v0.1.52 made the design-standard
partial factors **configurable**; until now they changed nothing. A
setting that does nothing is worse than no setting, because the user
believes the analysis honours it.

Two implementation choices are load-bearing and tested as such:

* **Factors are applied by transforming a COPY of the project**, not
  inside the solver. Every analysis path then gets them automatically,
  the engine stays a pure limit-equilibrium solver with no notion of any
  design code, and switching the standard off restores the original
  numbers exactly.
* **Friction is factored on tan φ**, as Eurocode 7 specifies — not on φ.
  30° / 1.25 = 24.00°, while atan(tan 30° / 1.25) = 24.79°: small, but
  wrong in a way that would quietly disagree with a hand check.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.materials import (  # noqa: E402
    DISTURBANCE_GUIDANCE,
    GSI_GUIDANCE,
    MI_GUIDANCE,
    calculate_hoek_brown,
)
from ogr_core.project import (  # noqa: E402
    apply_design_factors,
    factor_friction_angle,
)
from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []
_KW = dict(method=BishopSimplified(), grid_x=(70, 105), grid_y=(58, 90),
           grid_nx=4, grid_ny=4, radius_increment=8, min_radius=12,
           num_slices=16, min_area=0.5)


# ======================================================================
class TestFrictionFactoring:
    def test_tangent_not_the_angle(self):
        """Eurocode 7 factors tan φ. The two differ by about 0.8° at
        φ = 30°, γ = 1.25 — enough to disagree with a hand check."""
        got = factor_friction_angle(30.0, 1.25)
        assert abs(got - 24.7912) < 1e-3, got
        assert abs(got - 30.0 / 1.25) > 0.5

    def test_unit_factor_changes_nothing(self):
        assert abs(factor_friction_angle(33.0, 1.0) - 33.0) < 1e-12

    def test_zero_friction_stays_zero(self):
        assert abs(factor_friction_angle(0.0, 1.25)) < 1e-12

    def test_result_is_always_lower(self):
        for phi in (5.0, 15.0, 30.0, 45.0, 60.0):
            assert factor_friction_angle(phi, 1.25) < phi

    def test_invalid_factor_is_ignored(self):
        assert abs(factor_friction_angle(30.0, 0.0) - 30.0) < 1e-12


class TestApplyDesignFactors:
    def test_disabled_returns_the_same_object(self):
        """The feature must cost nothing when unused and cannot perturb
        a result by merely being present."""
        p = _ej1_project()
        p.settings.design_standard.enabled = False
        out, rep = apply_design_factors(p)
        assert out is p
        assert rep.applied is False

    def test_original_project_is_never_modified(self):
        p = _ej1_project()
        before = p.materials[0].strength.params["cohesion"]
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da1c2")
        apply_design_factors(p)
        assert p.materials[0].strength.params["cohesion"] == before

    def test_cohesion_is_divided(self):
        p = _ej1_project()
        c0 = p.materials[0].strength.params["cohesion"]
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da1c2")
        out, _rep = apply_design_factors(p)
        assert abs(out.materials[0].strength.params["cohesion"]
                   - c0 / 1.25) < 1e-9

    def test_friction_uses_the_tangent_rule(self):
        p = _ej1_project()
        phi0 = p.materials[0].strength.params["friction_angle"]
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da1c2")
        out, _rep = apply_design_factors(p)
        expected = factor_friction_angle(phi0, 1.25)
        assert abs(out.materials[0].strength.params["friction_angle"]
                   - expected) < 1e-9

    def test_report_lists_what_changed(self):
        p = _ej1_project()
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da3")
        _out, rep = apply_design_factors(p)
        assert rep.applied is True
        assert len(rep.materials) == len(p.materials)
        assert "eurocode7_da3" in rep.summary()

    def test_all_unity_factors_are_reported_as_a_no_op(self):
        """Enabled with every factor at 1.0 looks like it should do
        something; the report says plainly that it did not."""
        p = _ej1_project()
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("none")
        _out, rep = apply_design_factors(p)
        assert any("nothing changed" in n for n in rep.notes)


class TestFactorsReachTheAnalysis:
    """The point of the phase: the setting must move the number."""

    def test_material_factors_lower_the_factor_of_safety(self):
        p = _ej1_project()
        base = GridSearch(**_KW).run(p).critical.fos
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da1c2")
        out, _rep = apply_design_factors(p)
        factored = GridSearch(**_KW).run(out).critical.fos
        assert factored < base - 0.05, (base, factored)

    def test_da1c1_leaves_an_unloaded_model_alone(self):
        """DA1 Combination 1 factors ACTIONS only. With no external
        loads there is nothing to factor, so the factor of safety must be
        unchanged — a good check that material factors are not being
        applied where the code does not ask for them."""
        p = _ej1_project()
        base = GridSearch(**_KW).run(p).critical.fos
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset("eurocode7_da1c1")
        out, _rep = apply_design_factors(p)
        assert abs(GridSearch(**_KW).run(out).critical.fos - base) < 1e-9

    def test_da1c2_and_da3_agree_on_an_unloaded_model(self):
        """Their material factors are identical; they differ only in the
        action factors, which have nothing to act on here."""
        results = []
        for std in ("eurocode7_da1c2", "eurocode7_da3"):
            p = _ej1_project()
            p.settings.design_standard.enabled = True
            p.settings.design_standard.apply_preset(std)
            out, _rep = apply_design_factors(p)
            results.append(GridSearch(**_KW).run(out).critical.fos)
        assert abs(results[0] - results[1]) < 1e-9

    def test_switching_off_restores_the_original_number(self):
        p = _ej1_project()
        base = GridSearch(**_KW).run(p).critical.fos
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da3")
        apply_design_factors(p)
        ds.enabled = False
        out, _rep = apply_design_factors(p)
        assert abs(GridSearch(**_KW).run(out).critical.fos - base) < 1e-12


# ======================================================================
class TestParameterCalculator:
    def test_intact_rock_reproduces_the_definitions(self):
        """GSI = 100 with no disturbance must give mb = mi, s = 1 and
        a = 0.5 — the definition the equations reduce to."""
        r = calculate_hoek_brown(100.0, 10.0, 0.0)
        assert abs(r.mb - 10.0) < 1e-9
        assert abs(r.s - 1.0) < 1e-9
        assert abs(r.a - 0.5) < 1e-3

    def test_known_case(self):
        """GSI = 50, mi = 10, D = 0 — Hoek et al. (2002)."""
        r = calculate_hoek_brown(50.0, 10.0, 0.0)
        assert abs(r.mb - 1.6768) < 1e-3, r.mb
        assert abs(r.s - 0.003866) < 1e-5, r.s
        assert abs(r.a - 0.5057) < 1e-3, r.a

    def test_disturbance_reduces_the_constants(self):
        prev = None
        for d in (0.0, 0.5, 1.0, 1.5):
            r = calculate_hoek_brown(50.0, 10.0, d)
            if prev is not None:
                assert r.mb < prev
            prev = r.mb

    def test_d_equal_to_two_is_clamped_not_infinite(self):
        """28 − 14·2 = 0 makes mb undefined; an infinite strength
        constant would silently produce a meaningless envelope."""
        r = calculate_hoek_brown(50.0, 10.0, 2.0)
        assert math.isfinite(r.mb)
        assert r.notes
        assert "clamped" in r.notes[0]

    def test_gsi_is_clamped_with_a_note(self):
        r = calculate_hoek_brown(150.0, 10.0, 0.0)
        assert r.gsi == 100.0
        assert any("clamped" in n for n in r.notes)

    def test_a_approaches_one_half_for_good_rock(self):
        assert calculate_hoek_brown(90.0, 10.0).a < \
            calculate_hoek_brown(20.0, 10.0).a

    def test_guidance_tables_are_populated(self):
        """GSI and D are judgement-based; numbers typed without that
        context are the usual source of a wrong envelope."""
        assert len(MI_GUIDANCE) >= 20
        assert len(GSI_GUIDANCE) >= 5
        assert len(DISTURBANCE_GUIDANCE) >= 5
        assert all(isinstance(v, (int, float)) and v > 0
                   for _n, v in MI_GUIDANCE)

    def test_summary_is_readable(self):
        text = calculate_hoek_brown(60.0, 15.0, 0.7).summary()
        assert "mb" in text and "GSI" in text


# ======================================================================
@_requires_qt
class TestParameterCalculatorDialog:
    def _dlg(self):
        from ogr_gui.dialogs.parameter_calculator_dialog import (
            ParameterCalculatorDialog,
        )
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language("en")
        return ParameterCalculatorDialog(None)

    def test_calculates_on_open(self):
        d = self._dlg()
        assert d.result_params is not None
        assert d.lbl_mb.text() not in ("", "—")

    def test_updates_live(self):
        d = self._dlg()
        before = d.lbl_mb.text()
        d.sp_gsi.setValue(80.0)
        assert d.lbl_mb.text() != before

    def test_lithology_pick_fills_mi(self):
        """GSI and D are judgement-based; the tables are shown beside the
        fields rather than hidden behind help."""
        d = self._dlg()
        i = d.cbo_mi.findText("Granite — 32")
        assert i > 0
        d.cbo_mi.setCurrentIndex(i)
        assert abs(d.sp_mi.value() - 32.0) < 1e-9

    def test_small_s_avoids_showing_zero(self):
        """s spans orders of magnitude: fixed decimals would show
        0.000000 for a poor rock mass."""
        d = self._dlg()
        d.sp_gsi.setValue(15.0)
        assert "e-" in d.lbl_s.text(), d.lbl_s.text()

    def test_note_shown_for_d_two(self):
        d = self._dlg()
        d.sp_d.setValue(2.0)
        assert "clamped" in d.lbl_note.text()

    def test_button_only_for_generalised_hoek_brown(self):
        """mb, s and a are derived quantities; for Mohr-Coulomb the
        calculator would be meaningless."""
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        d = MaterialPropertiesDialog(p.materials, None)
        _WINDOWS.append(d)
        # isHidden reflects the explicit hide; isVisible would be False
        # for every child of a window that has not been shown.
        assert d.btn_gsi.isHidden() is True
        d.cbo_strength.setCurrentIndex(
            d.cbo_strength.findData("hoek_brown"))
        assert d.btn_gsi.isHidden() is False
        d.cbo_strength.setCurrentIndex(
            d.cbo_strength.findData("mohr_coulomb"))
        assert d.btn_gsi.isHidden() is True


@_requires_qt
class TestSessionRegistry:
    def _windows(self, n=2):
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        MainWindow._sessions.clear()
        out = [MainWindow() for _ in range(n)]
        _WINDOWS.extend(out)
        return out

    def test_windows_register_themselves(self):
        from ogr_gui.main_window import MainWindow
        wins = self._windows(2)
        assert len(MainWindow._sessions) == 2
        assert all(w in MainWindow._sessions for w in wins)

    def test_closing_deregisters(self):
        """Otherwise the menu would list windows that no longer exist."""
        from ogr_gui.main_window import MainWindow
        w1, w2 = self._windows(2)
        w2.close()
        assert w2 not in MainWindow._sessions
        assert w1 in MainWindow._sessions

    def test_label_marks_unsaved_changes(self):
        w1, _w2 = self._windows(2)
        w1.project.name = "Slope A"
        w1.project.is_dirty = False
        assert "*" not in w1.session_label()
        w1.project.is_dirty = True
        assert "*" in w1.session_label()

    def test_menu_lists_every_session(self):
        w1, _w2 = self._windows(2)
        w1.project.name = "Slope A"
        _w2.project.name = "Slope B"
        w1._rebuild_window_menu()
        texts = [a.text() for a in w1._window_menu.actions() if a.text()]
        assert any("Slope A" in t for t in texts)
        assert any("Slope B" in t for t in texts)

    def test_menu_is_rebuilt_and_cannot_go_stale(self):
        from ogr_gui.main_window import MainWindow
        w1, w2 = self._windows(2)
        w2.project.name = "Doomed"
        w1._rebuild_window_menu()
        assert any("Doomed" in a.text()
                   for a in w1._window_menu.actions() if a.text())
        w2.close()
        w1._rebuild_window_menu()
        assert not any("Doomed" in a.text()
                       for a in w1._window_menu.actions() if a.text())

    def test_menu_offers_new_and_close(self):
        w1, _w2 = self._windows(2)
        w1._rebuild_window_menu()
        texts = [a.text() for a in w1._window_menu.actions() if a.text()]
        assert "New Window" in texts
        assert "Close Window" in texts

    def test_new_window_is_independent(self):
        """Two windows editing one project would let a change in one
        invalidate results shown in the other with no sign of it."""
        (w1,) = self._windows(1)
        w3 = w1._new_window()
        _WINDOWS.append(w3)
        assert w3.project is not w1.project
