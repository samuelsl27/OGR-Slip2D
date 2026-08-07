# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.52 — Project Settings completed (phase M2).

The dialog carried four of the nine pages the specification describes.
The missing five — Transient, Statistics, Random Numbers, Design Standard
and Advanced — held data that already existed in the model and was
reachable from other dialogs; what was absent was the central place to
see and change it.

Two additions to the model were needed:

* **RandomNumberSettings** — a pseudo-random stream is reproducible, which
  is what makes a probabilistic result defensible in a report; a
  clock-seeded one explores differently between runs, which is how you
  check a conclusion is not an artefact of one seed.
* **DesignStandardSettings** — partial factors with Eurocode 7 presets,
  **off by default**, because applying them silently would change every
  factor of safety the user has ever compared against.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.project import Project  # noqa: E402
from ogr_core.project.settings import (  # noqa: E402
    DesignStandardSettings,
    RandomNumberSettings,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_DIALOGS = []

_EXPECTED_PAGES = ["General", "Methods", "Groundwater", "Transient",
                   "Statistics", "Random Numbers", "Design Standard",
                   "Advanced", "Project Summary"]


def _dialog(project=None):
    from ogr_gui.dialogs.project_settings_dialog import (
        ProjectSettingsDialog,
    )
    from ogr_gui.i18n import set_language
    QApplication.instance() or QApplication([])
    set_language("en")
    p = project or Project(name="settings")
    d = ProjectSettingsDialog(p.settings, None)
    _DIALOGS.append(d)
    return p, d


def _pages(d):
    return {d.nav.item(i).text(): d.pages[i]
            for i in range(d.nav.count())}


# ======================================================================
class TestRandomNumberSettings:
    def test_pseudo_random_is_reproducible(self):
        s = RandomNumberSettings(method="pseudo_random", seed=42)
        assert s.effective_seed() == 42

    def test_random_is_clock_seeded(self):
        """None tells the sampler to seed itself, so successive runs
        explore differently."""
        s = RandomNumberSettings(method="random", seed=42)
        assert s.effective_seed() is None

    def test_defaults(self):
        s = RandomNumberSettings()
        assert s.method == "pseudo_random"
        assert s.seed > 0

    def test_round_trip(self):
        p = Project(name="x")
        p.settings.random_numbers.method = "random"
        p.settings.random_numbers.seed = 777
        p2 = Project.from_dict(p.to_dict())
        assert p2.settings.random_numbers.method == "random"
        assert p2.settings.random_numbers.seed == 777


class TestDesignStandardSettings:
    def test_off_by_default(self):
        """Applying partial factors silently would change every factor of
        safety previously compared against."""
        s = DesignStandardSettings()
        assert s.enabled is False
        assert s.standard == "none"
        assert s.factor_cohesion == 1.0

    def test_presets_load_their_factors(self):
        s = DesignStandardSettings()
        assert s.apply_preset("eurocode7_da1c2") is True
        assert abs(s.factor_cohesion - 1.25) < 1e-9
        assert abs(s.factor_friction - 1.25) < 1e-9

    def test_da1c1_factors_actions_not_materials(self):
        """DA1 Combination 1 factors the actions; the material factors
        stay at unity."""
        s = DesignStandardSettings()
        s.apply_preset("eurocode7_da1c1")
        assert s.factor_permanent > 1.0
        assert abs(s.factor_cohesion - 1.0) < 1e-9

    def test_none_preset_resets_to_unity(self):
        s = DesignStandardSettings()
        s.apply_preset("eurocode7_da3")
        s.apply_preset("none")
        assert all(abs(getattr(s, a) - 1.0) < 1e-9 for a in
                   ("factor_permanent", "factor_variable",
                    "factor_cohesion", "factor_friction"))

    def test_custom_leaves_the_values_alone(self):
        s = DesignStandardSettings()
        s.factor_cohesion = 1.4
        assert s.apply_preset("custom") is False
        assert abs(s.factor_cohesion - 1.4) < 1e-9
        assert s.standard == "custom"

    def test_every_preset_is_complete(self):
        for name in DesignStandardSettings.PRESETS:
            s = DesignStandardSettings()
            assert s.apply_preset(name) is True, name
            assert all(getattr(s, a) > 0 for a in
                       ("factor_permanent", "factor_variable",
                        "factor_cohesion", "factor_friction",
                        "factor_unit_weight", "factor_resistance"))

    def test_round_trip_excludes_the_preset_table(self):
        """PRESETS is a class constant, not state; serialising it would
        bloat every project file."""
        p = Project(name="x")
        p.settings.design_standard.apply_preset("eurocode7_da2")
        p.settings.design_standard.enabled = True
        data = p.to_dict()
        assert "PRESETS" not in data["settings"]["design_standard"]
        p2 = Project.from_dict(data)
        assert p2.settings.design_standard.standard == "eurocode7_da2"
        assert p2.settings.design_standard.enabled is True


# ======================================================================
@_requires_qt
class TestDialogStructure:
    def test_all_nine_pages_present(self):
        _p, d = _dialog()
        assert [d.nav.item(i).text() for i in range(d.nav.count())] == \
            _EXPECTED_PAGES

    def test_every_page_can_apply(self):
        _p, d = _dialog()
        for name, page in _pages(d).items():
            assert hasattr(page, "apply"), name

    def test_apply_does_not_raise_on_a_fresh_project(self):
        _p, d = _dialog()
        d._apply()

    def test_navigation_switches_the_stack(self):
        _p, d = _dialog()
        d.nav.setCurrentRow(4)
        assert d.stack.currentIndex() == 4


@_requires_qt
class TestTransientPage:
    def test_reports_the_stage_count(self):
        p = Project(name="x")
        p.settings.groundwater.transient_stages = [
            {"time": 10.0, "calculate_sf": True},
            {"time": 20.0, "calculate_sf": False}]
        _p, d = _dialog(p)
        page = _pages(d)["Transient"]
        assert "2 stage" in page.lbl_stages.text()
        assert "1 with" in page.lbl_stages.text()

    def test_enabling_is_exclusive(self):
        """Advanced groundwater options are mutually exclusive."""
        p = Project(name="x")
        p.settings.groundwater.set_advanced_option("rapid_drawdown")
        _p, d = _dialog(p)
        page = _pages(d)["Transient"]
        page.chk_enabled.setChecked(True)
        page.apply()
        assert p.settings.groundwater.transient is True
        assert p.settings.groundwater.rapid_drawdown is False

    def test_solver_options_written(self):
        p, d = _dialog()
        page = _pages(d)["Transient"]
        page.sp_steps.setValue(9)
        page.sp_iter.setValue(55)
        page.apply()
        assert p.settings.groundwater.transient_time_steps == 9
        assert p.settings.groundwater.transient_max_iterations == 55

    def test_auto_time_steps_shown_as_auto(self):
        _p, d = _dialog()
        page = _pages(d)["Transient"]
        page.sp_steps.setValue(0)
        assert page.sp_steps.specialValueText() == "Auto"


@_requires_qt
class TestStatisticsPage:
    def test_writes_every_field(self):
        p, d = _dialog()
        page = _pages(d)["Statistics"]
        page.chk_prob.setChecked(True)
        page.chk_sens.setChecked(True)
        page.cbo_type.setCurrentIndex(
            page.cbo_type.findData("overall_slope"))
        page.cbo_sampling.setCurrentIndex(
            page.cbo_sampling.findData("latin_hypercube"))
        page.sp_samples.setValue(2500)
        page.sp_intervals.setValue(25)
        page.apply()
        st = p.settings.statistics
        assert st.probabilistic_analysis is True
        assert st.sensitivity_analysis is True
        assert st.analysis_type == "overall_slope"
        assert st.sampling_method == "latin_hypercube"
        assert st.num_samples == 2500
        assert st.sensitivity_intervals == 25

    def test_both_analysis_types_offered(self):
        _p, d = _dialog()
        page = _pages(d)["Statistics"]
        offered = {page.cbo_type.itemData(i)
                   for i in range(page.cbo_type.count())}
        assert offered == {"global_minimum", "overall_slope"}

    def test_both_sampling_methods_offered(self):
        _p, d = _dialog()
        page = _pages(d)["Statistics"]
        offered = {page.cbo_sampling.itemData(i)
                   for i in range(page.cbo_sampling.count())}
        assert offered == {"monte_carlo", "latin_hypercube"}


@_requires_qt
class TestRandomNumbersPage:
    def test_seed_disabled_for_a_clock_seeded_run(self):
        """A seed is meaningless there, so it is disabled rather than
        left looking effective."""
        _p, d = _dialog()
        page = _pages(d)["Random Numbers"]
        page.cbo_method.setCurrentIndex(
            page.cbo_method.findData("random"))
        assert page.sp_seed.isEnabled() is False
        page.cbo_method.setCurrentIndex(
            page.cbo_method.findData("pseudo_random"))
        assert page.sp_seed.isEnabled() is True

    def test_writes_the_settings(self):
        p, d = _dialog()
        page = _pages(d)["Random Numbers"]
        page.sp_seed.setValue(12345)
        page.apply()
        assert p.settings.random_numbers.seed == 12345

    def test_explains_the_difference(self):
        from PySide6.QtWidgets import QLabel
        _p, d = _dialog()
        page = _pages(d)["Random Numbers"]
        text = " ".join(" ".join(la.text().split())
                        for la in page.findChildren(QLabel))
        assert "reproducible" in text


@_requires_qt
class TestDesignStandardPage:
    def test_factors_only_editable_when_custom(self):
        """A named standard defines its factors; letting the user edit
        them while it is selected would misrepresent the standard."""
        _p, d = _dialog()
        page = _pages(d)["Design Standard"]
        page.chk_enabled.setChecked(True)
        page.cbo_std.setCurrentIndex(
            page.cbo_std.findData("eurocode7_da2"))
        assert page.factors["factor_cohesion"].isEnabled() is False
        page.cbo_std.setCurrentIndex(page.cbo_std.findData("custom"))
        assert page.factors["factor_cohesion"].isEnabled() is True

    def test_selecting_a_standard_loads_its_factors(self):
        _p, d = _dialog()
        page = _pages(d)["Design Standard"]
        page.chk_enabled.setChecked(True)
        page.cbo_std.setCurrentIndex(
            page.cbo_std.findData("eurocode7_da1c2"))
        assert abs(page.factors["factor_cohesion"].value() - 1.25) < 1e-9

    def test_everything_disabled_when_off(self):
        _p, d = _dialog()
        page = _pages(d)["Design Standard"]
        page.chk_enabled.setChecked(False)
        assert page.cbo_std.isEnabled() is False
        assert page.factors["factor_cohesion"].isEnabled() is False

    def test_writes_the_settings(self):
        p, d = _dialog()
        page = _pages(d)["Design Standard"]
        page.chk_enabled.setChecked(True)
        page.cbo_std.setCurrentIndex(
            page.cbo_std.findData("eurocode7_da3"))
        page.apply()
        assert p.settings.design_standard.enabled is True
        assert p.settings.design_standard.standard == "eurocode7_da3"


@_requires_qt
class TestAdvancedPage:
    def test_writes_every_field(self):
        p, d = _dialog()
        page = _pages(d)["Advanced"]
        page.chk_tensile.setChecked(False)
        page.chk_steffensen.setChecked(False)
        page.sp_initial.setValue(1.5)
        page.sp_lmin.setValue(-2.0)
        page.sp_lmax.setValue(2.0)
        page.apply()
        adv = p.settings.advanced
        assert adv.check_tensile_stresses is False
        assert adv.iterate_steffensen is False
        assert abs(adv.min_initial_fs - 1.5) < 1e-9
        assert abs(adv.max_lambda - 2.0) < 1e-9

    def test_m_alpha_is_deliberately_absent(self):
        """It rejects the reference-validated critical circle, so it is a
        diagnostic rather than a validity criterion and stays with the
        search options. The page says so."""
        from PySide6.QtWidgets import QLabel
        _p, d = _dialog()
        page = _pages(d)["Advanced"]
        text = " ".join(" ".join(la.text().split())
                        for la in page.findChildren(QLabel))
        assert "m-alpha" in text
        assert not any("m-alpha" in w.text().lower()
                       for w in page.findChildren(
                           type(page.chk_tensile)))
