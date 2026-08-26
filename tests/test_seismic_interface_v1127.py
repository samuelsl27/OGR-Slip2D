# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.127 — the seismic analysis reaches a menu, and every control moves.

Three rules of the project contract, applied to what this feature adds to
the interface.

**Rule 3 — reachable from a menu.** A whole module was once implemented,
tested and released invisible because its actions were registered and
never added to the menu bar. *Seismic Records* is a new action and the
records are useless without it, so the bar is walked to find it.

**Rule 2 — every visible string is translated.** Covered in general by
``test_i18n_coverage_v141.py``; what is checked here is the part a
scanner cannot see, that the Seismic page really is built and its widgets
really carry the translated text.

**Rule 7 — no setting may do nothing.** Every control on the Seismic page
is round-tripped through ``apply()`` and read back from the settings the
engine consumes, and the gate that greys out the Newmark controls is
checked to actually gate. Two of this program's own defects were settings
that stored a value nobody read; the cure is a test per control.

The dialogs are constructed, never ``exec``-ed: a modal dialog in code a
test runs blocks for ever without a screen.
"""
from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except Exception:                     # pragma: no cover - no Qt available
    _QT = False

from ogr_core.loads.seismic_record import AccelerationUnit, SeismicRecord
from ogr_core.project import Project

_WINDOWS: list = []


def _app():
    return QApplication.instance() or QApplication([])


def _project_with_records():
    project = Project("seismic interface")
    project.seismic_records.append(SeismicRecord(
        name="First", dt=0.01, accelerations=[0.0, 0.2, -0.3, 0.1],
        source_unit=AccelerationUnit.G))
    project.seismic_records.append(SeismicRecord(
        name="Second", dt=0.02, accelerations=[0.0, 0.4, -0.1],
        source_unit=AccelerationUnit.CM_S2))
    return project


def _settings_dialog(project):
    from ogr_gui.dialogs.project_settings_dialog import ProjectSettingsDialog
    _app()
    dialog = ProjectSettingsDialog(project.settings, None, project=project)
    _WINDOWS.append(dialog)
    return dialog


def _seismic_page(dialog):
    for page in dialog.pages:
        if type(page).__name__ == "_SeismicPage":
            return page
    raise AssertionError("the Seismic page is not in the dialog")


# ======================================================================
class TestItIsReachableFromAMenu:
    """Rule 3, walked on the real menu bar."""

    def test_seismic_records_is_in_the_loading_menu(self):
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.main_window import MainWindow
        _app()
        window = MainWindow()
        _WINDOWS.append(window)
        labels = []
        for action in window.menuBar().actions():
            menu = action.menu()
            if menu is None:
                continue
            for item in menu.actions():
                labels.append(item.text())
        assert any("Seismic Record" in text or "Registros s" in text
                   for text in labels), labels

    def test_the_action_opens_a_dialog_that_can_be_built(self):
        """Constructed, not executed. The action itself is not called
        because it would ``exec`` and never return without a screen."""
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog,
        )
        _app()
        project = _project_with_records()
        dialog = SeismicRecordsDialog(project)
        _WINDOWS.append(dialog)
        assert dialog.list.count() == 2
        assert dialog.list.item(0).text() == "First"


# ======================================================================
class TestTheSeismicPage:
    """Rule 7, control by control."""

    def test_the_page_exists_and_is_named(self):
        if not _QT:
            pytest.skip("Qt not available")
        dialog = _settings_dialog(_project_with_records())
        names = [dialog.nav.item(i).text()
                 for i in range(dialog.nav.count())]
        assert "Seismic" in names
        assert _seismic_page(dialog) is not None

    def test_every_control_survives_apply(self):
        if not _QT:
            pytest.skip("Qt not available")
        project = _project_with_records()
        dialog = _settings_dialog(project)
        page = _seismic_page(dialog)

        page.cb_ky.setChecked(True)
        page.sp_target.setValue(1.25)
        page.cb_newmark.setChecked(True)
        page.cmb_record.setCurrentIndex(2)          # the second record
        page.cmb_polarity.setCurrentIndex(2)        # inverse
        page.cb_upslope.setChecked(True)
        page.sp_scale.setValue(1.75)
        page.apply()

        s = project.settings.seismic
        assert s.compute_ky is True
        assert s.ky_target_fos == pytest.approx(1.25)
        assert s.newmark is True
        assert s.record_id == project.seismic_records[1].id
        assert s.polarity == "inverse"
        assert s.allow_upslope is True
        assert s.scale == pytest.approx(1.75)
        # And the engine reads exactly these.
        assert s.needs_ky and s.objective() == "ky"

    def test_the_record_choice_offers_none_and_every_record(self):
        if not _QT:
            pytest.skip("Qt not available")
        project = _project_with_records()
        page = _seismic_page(_settings_dialog(project))
        assert page.cmb_record.count() == 1 + len(project.seismic_records)
        page.cmb_record.setCurrentIndex(0)
        page.apply()
        assert project.settings.seismic.record_id == ""

    def test_the_newmark_controls_are_gated(self):
        """A polarity nobody reads is a control that does nothing."""
        if not _QT:
            pytest.skip("Qt not available")
        page = _seismic_page(_settings_dialog(_project_with_records()))
        page.cb_newmark.setChecked(False)
        assert not page.cmb_record.isEnabled()
        assert not page.cmb_polarity.isEnabled()
        assert not page.sp_scale.isEnabled()
        page.cb_newmark.setChecked(True)
        assert page.cmb_record.isEnabled()
        assert page.cmb_polarity.isEnabled()
        assert page.sp_scale.isEnabled()

    def test_the_target_factor_is_gated_by_either_mode(self):
        if not _QT:
            pytest.skip("Qt not available")
        page = _seismic_page(_settings_dialog(_project_with_records()))
        page.cb_ky.setChecked(False)
        page.cb_newmark.setChecked(False)
        assert not page.sp_target.isEnabled()
        page.cb_newmark.setChecked(True)
        assert page.sp_target.isEnabled()

    def test_a_project_with_no_records_still_builds_the_page(self):
        if not _QT:
            pytest.skip("Qt not available")
        page = _seismic_page(_settings_dialog(Project("empty")))
        assert page.cmb_record.count() == 1
        page.apply()

    def test_the_dialog_still_works_without_a_project(self):
        """Six callers construct it with settings alone."""
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog,
        )
        _app()
        dialog = ProjectSettingsDialog(Project("no project arg").settings)
        _WINDOWS.append(dialog)
        page = _seismic_page(dialog)
        assert page.cmb_record.count() == 1
        dialog._apply()


# ======================================================================
class TestTheRecordsDialog:
    """It edits a copy, and Cancel really cancels."""

    def test_cancel_leaves_the_project_alone(self):
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog,
        )
        _app()
        project = _project_with_records()
        dialog = SeismicRecordsDialog(project)
        _WINDOWS.append(dialog)
        dialog.list.setCurrentRow(0)
        dialog._delete()
        assert len(dialog.records) == 1
        # apply() was never called, so the project has not moved.
        assert len(project.seismic_records) == 2

    def test_apply_writes_the_edited_list(self):
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog,
        )
        _app()
        project = _project_with_records()
        dialog = SeismicRecordsDialog(project)
        _WINDOWS.append(dialog)
        dialog.list.setCurrentRow(0)
        dialog._rename("Renamed")
        dialog.apply()
        assert project.seismic_records[0].name == "Renamed"

    def test_deleting_the_selected_record_clears_the_selection(self):
        """Otherwise the run would integrate a record that is gone."""
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog,
        )
        _app()
        project = _project_with_records()
        project.settings.seismic.record_id = project.seismic_records[0].id
        dialog = SeismicRecordsDialog(project)
        _WINDOWS.append(dialog)
        dialog.list.setCurrentRow(0)
        dialog._delete()
        dialog.apply()
        assert project.settings.seismic.record_id == ""

    def test_the_time_interval_restates_it_and_does_not_resample(self):
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog,
        )
        _app()
        project = _project_with_records()
        dialog = SeismicRecordsDialog(project)
        _WINDOWS.append(dialog)
        dialog.list.setCurrentRow(0)
        before = list(dialog.records[0].accelerations)
        dialog.sb_dt.setValue(0.05)
        assert dialog.records[0].dt == pytest.approx(0.05)
        assert dialog.records[0].accelerations == before


# ======================================================================
class TestInterpretReportsTheRightQuantity:
    """The window must never label a Ky run "factor of safety"."""

    @staticmethod
    def _result(objective, details):
        from ogr_slip2d.search import SearchResult

        class _Surface:
            def to_dict(self):
                return {"centre_x": 1.0, "centre_y": 2.0, "radius": 3.0}

        class _Item:
            is_valid = True
            admissible = True
            fos = 1.234
            iterations = 7
            surface = _Surface()

            def __init__(self, det):
                self.details = det

        result = SearchResult(method_id="bishop_simplified",
                              objective=objective)
        result.evaluations.append(_Item(details))
        result.valid_count = 1
        return result

    def test_a_plain_run_reports_the_factor_of_safety(self):
        from ogr_gui.interpret_window import (
            _reported_quantity,
            _reported_value,
        )
        result = self._result("fos", {})
        kind, _label = _reported_quantity(result)
        assert kind == "fos"
        assert _reported_value(result, result.critical)[0] == "1.234"

    def test_a_ky_run_reports_the_coefficient(self):
        from ogr_gui.interpret_window import (
            _reported_quantity,
            _reported_value,
        )
        result = self._result("ky", {"ky": 0.1385})
        kind, _label = _reported_quantity(result)
        assert kind == "ky"
        text, tip = _reported_value(result, result.critical)
        assert text == "0.1385"
        assert "1.234" in tip

    def test_a_newmark_run_reports_a_displacement(self):
        from ogr_gui.interpret_window import (
            _reported_quantity,
            _reported_value,
        )
        result = self._result("ky", {"ky": 0.1385,
                                     "newmark_displacement": 0.05042})
        kind, _label = _reported_quantity(result)
        assert kind == "newmark"
        text, tip = _reported_value(result, result.critical)
        assert text.startswith("5.042")
        assert "0.1385" in tip

    def test_no_coefficient_is_not_the_same_as_no_valid_surface(self):
        """Two different sentences, and only one of them sends the user
        to look at the geometry."""
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.interpret_window import _SummaryDock
        _app()
        dock = _SummaryDock()
        _WINDOWS.append(dock)
        result = self._result("ky", {"ky": float("nan")})
        assert result.critical is None
        dock.show_result(result)
        text = dock.label.text()
        assert "critical seismic coefficient" in text
        assert "No valid surfaces" not in text

    def test_a_plain_run_with_nothing_valid_still_says_so(self):
        if not _QT:
            pytest.skip("Qt not available")
        from ogr_gui.interpret_window import _SummaryDock
        _app()
        dock = _SummaryDock()
        _WINDOWS.append(dock)
        result = self._result("fos", {})
        result.evaluations[0].is_valid = False
        result.valid_count = 0
        result.invalid_count = 1
        dock.show_result(result)
        assert "No valid surfaces" in dock.label.text()

# ======================================================================
class TestTheTerminalSaysTheSameThing:
    """The command line and the window are two doors to one answer.

    Both used to print the critical factor of safety under a fixed label.
    With a seismic mode on that label would be wrong in the same way in
    both, so both were changed in the same version; this test exists so
    that a future change to one of them cannot leave the other behind.
    """

    def test_the_column_label_follows_the_objective(self):
        import io
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source = io.open(os.path.join(root, "ogr_cli", "__main__.py"),
                         encoding="utf-8").read()
        assert "Critical Ky" in source
        assert "Newmark disp." in source
        # And it reads the objective off the RESULT, not off the project:
        # a window or a terminal that reads the settings can disagree with
        # the results it is showing.
        assert 'getattr(first, "objective", "fos")' in source
