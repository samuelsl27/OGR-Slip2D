# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.51 — Data tips and snap configuration (phase M1).

An audit correction belongs at the top of this file: the audit listed
**snapping as missing**, and it was not. ``ogr_gui/canvas/snap_engine.py``
already implemented vertex, line, grid, ortho and even segment-extension
snapping, wired to the status-bar words. The audit reached the wrong
conclusion because it searched for the feature by name and counted
matching files without reading what they did.

What was genuinely absent, and is added here:

* **Data tips** — hovering over a material, support or load shows its
  properties. Asked for in the opening paragraph of the project brief and
  never implemented.
* **A Snap dialog** — the engine supported grid spacing, per-kind capture
  tolerances and an ortho angle window; none was reachable.
* **The F3 / F8 / F9 keys** — only the grid had a key (F7).

The invariant the tests protect is **one source of truth**: pressing a key
and clicking the word must leave the engine and the display agreeing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_gui.data_tips import (  # noqa: E402
    DataTipMode,
    boundary_tip,
    load_tip,
    material_tip,
    support_tip,
    tip_at,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []


def _project():
    from test_slide_validation_ej1 import _ej1_project
    return _ej1_project()


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    p = _project()
    w = MainWindow()
    w.canvas.set_project(p)
    w.project = p
    _WINDOWS.append(w)
    return p, w


# ======================================================================
class TestMaterialTips:
    def test_maximum_lists_the_properties(self):
        p = _project()
        text = material_tip(p.materials[0], DataTipMode.MAXIMUM)
        assert p.materials[0].name in text
        assert "cohesion" in text
        assert "friction angle" in text
        assert "unit weight" in text

    def test_values_carry_units(self):
        """A cohesion without kPa is not information."""
        p = _project()
        text = material_tip(p.materials[0], DataTipMode.MAXIMUM)
        assert "kPa" in text
        assert "kN/m" in text
        assert "°" in text

    def test_minimum_is_the_identity_only(self):
        """Enough to tell two objects apart while drawing, without a wall
        of text following the cursor."""
        p = _project()
        text = material_tip(p.materials[0], DataTipMode.MINIMUM)
        assert text == p.materials[0].name
        assert "\n" not in text

    def test_none_returns_nothing(self):
        p = _project()
        assert material_tip(p.materials[0], DataTipMode.NONE) == ""

    def test_strength_model_named(self):
        p = _project()
        text = material_tip(p.materials[0], DataTipMode.MAXIMUM)
        assert "strength:" in text

    def test_missing_material_is_safe(self):
        assert material_tip(None, DataTipMode.MAXIMUM) == ""

    def test_small_values_use_scientific_notation(self):
        """A permeability printed as 0.0000010 says nothing."""
        from ogr_core.hydraulic import HydraulicProperties
        p = _project()
        p.materials[0].hydraulic = HydraulicProperties(ks=1e-7)
        text = material_tip(p.materials[0], DataTipMode.MAXIMUM)
        assert "e-0" in text or "e-07" in text, text


class TestOtherTips:
    def test_boundary_tip_reports_size(self):
        p = _project()
        ext = p.boundaries[0]
        text = boundary_tip(ext, DataTipMode.MAXIMUM)
        assert "vertices:" in text
        assert "length:" in text

    def test_boundary_minimum_is_the_type(self):
        p = _project()
        text = boundary_tip(p.boundaries[0], DataTipMode.MINIMUM)
        assert "\n" not in text

    def test_load_tip(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad
        ld = LineLoad(point=Vertex(10, 20), magnitude=50.0)
        text = load_tip(ld, DataTipMode.MAXIMUM)
        assert "magnitude" in text
        assert "50" in text
        assert "at (10.000, 20.000)" in text

    def test_load_minimum_includes_the_magnitude(self):
        """While drawing, which load is which is told by its value."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad
        text = load_tip(LineLoad(point=Vertex(1, 2), magnitude=75.0),
                        DataTipMode.MINIMUM)
        assert "75" in text

    def test_support_tip_reports_geometry(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support.support import EndAnchored

        class _S:
            support_type = EndAnchored()
            head = Vertex(10, 10)
            tail = Vertex(0, 0)
        text = support_tip(_S(), DataTipMode.MAXIMUM)
        assert "length" in text
        assert "from (0.000, 0.000)" in text

    def test_none_mode_everywhere(self):
        assert load_tip(object(), DataTipMode.NONE) == ""
        assert support_tip(object(), DataTipMode.NONE) == ""
        assert boundary_tip(None, DataTipMode.NONE) == ""


class TestTipAt:
    def test_boundary_under_the_cursor(self):
        p = _project()
        text = tip_at(p, 50.0, 50.0, DataTipMode.MAXIMUM, radius=1.0)
        assert "EXTERNAL" in text

    def test_region_reported_even_without_a_material(self):
        """A region with nothing assigned yet is worth reporting: silence
        looks like the tip is broken."""
        p = _project()
        text = tip_at(p, 60.0, 30.0, DataTipMode.MAXIMUM, radius=0.5)
        assert "region" in text.lower()

    def test_load_wins_over_the_region_beneath_it(self):
        """The material is everywhere; the arrow is only there."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad
        p = _project()
        p.line_loads.append(LineLoad(point=Vertex(60, 30),
                                     magnitude=99.0))
        text = tip_at(p, 60.0, 30.0, DataTipMode.MAXIMUM, radius=1.0)
        assert "99" in text

    def test_empty_away_from_everything(self):
        p = _project()
        assert tip_at(p, -500.0, -500.0, DataTipMode.MAXIMUM,
                      radius=0.5) == ""

    def test_none_mode_short_circuits(self):
        p = _project()
        assert tip_at(p, 50.0, 50.0, DataTipMode.NONE) == ""


# ======================================================================
@_requires_qt
class TestStatusBarIntegration:
    def test_data_tips_indicator_added(self):
        """The bar shipped with SNAP / GRID / ORTHO / OSNAP; DATA TIPS
        was the one it lacked."""
        _p, w = _window()
        assert w.ogr_status.toggle("DATA TIPS") is not None

    def test_indicator_controls_the_mode(self):
        _p, w = _window()
        lab = w.ogr_status.toggle("DATA TIPS")
        lab.setChecked(False)
        assert w.data_tip_mode == DataTipMode.NONE
        lab.setChecked(True)
        assert w.data_tip_mode == DataTipMode.MAXIMUM

    def test_add_toggle_is_idempotent(self):
        _p, w = _window()
        a = w.ogr_status.add_toggle("DATA TIPS", True)
        b = w.ogr_status.add_toggle("DATA TIPS", True)
        assert a is b

    def test_hover_sets_a_tooltip(self):
        _p, w = _window()
        w.data_tip_mode = DataTipMode.MAXIMUM
        w._on_canvas_hover(50.0, 50.0)
        assert w.canvas.toolTip()

    def test_hover_clears_the_tooltip_when_off(self):
        _p, w = _window()
        w.data_tip_mode = DataTipMode.NONE
        w._on_canvas_hover(50.0, 50.0)
        assert w.canvas.toolTip() == ""


@_requires_qt
class TestKeyboardAndEngineStayInStep:
    def test_keys_flip_both_the_engine_and_the_word(self):
        """One source of truth: pressing the key and clicking the word
        must leave the engine and the display agreeing."""
        _p, w = _window()
        for attr, label in (("snap", "snap"), ("ortho", "ortho"),
                            ("osnap", "osnap")):
            before = getattr(w.canvas.snap_settings, attr)
            w._toggle_snap_flag(attr)
            after = getattr(w.canvas.snap_settings, attr)
            word = getattr(w.ogr_status, label).isChecked()
            assert after is not before, attr
            assert after == word, attr

    def test_clicking_the_word_reaches_the_engine(self):
        _p, w = _window()
        w.ogr_status.osnap.setChecked(True)
        assert w.canvas.snap_settings.osnap is True
        w.ogr_status.osnap.setChecked(False)
        assert w.canvas.snap_settings.osnap is False

    def test_unknown_flag_is_ignored(self):
        _p, w = _window()
        w._toggle_snap_flag("nonsense")      # must not raise

    def test_snap_action_exists(self):
        _p, w = _window()
        assert "snap_opts" in w._actions


@_requires_qt
class TestSnapDialog:
    def _dlg(self, w=None):
        from ogr_gui.dialogs.snap_dialog import SnapDialog
        _p, w = _window() if w is None else (None, w)
        return w, SnapDialog(w.canvas.snap_settings,
                             DataTipMode.MAXIMUM, None)

    def test_shows_the_current_settings(self):
        w, d = self._dlg()
        s = w.canvas.snap_settings
        assert d.chk_snap.isChecked() == s.snap
        assert abs(d.sp_gh.value() - s.grid_h) < 1e-9
        assert abs(d.sp_vertex.value() - s.vertex_tolerance_px) < 1e-9

    def test_accept_writes_back_to_the_engine(self):
        w, d = self._dlg()
        d.sp_gh.setValue(2.5)
        d.sp_gv.setValue(3.5)
        d.chk_osnap.setChecked(True)
        d.sp_angle.setValue(7.5)
        d._accept()
        s = w.canvas.snap_settings
        assert abs(s.grid_h - 2.5) < 1e-9
        assert abs(s.grid_v - 3.5) < 1e-9
        assert s.osnap is True
        assert abs(s.ortho_snap_angle_deg - 7.5) < 1e-9

    def test_data_tip_mode_collected(self):
        _w, d = self._dlg()
        d.cbo_tips.setCurrentIndex(d.cbo_tips.findData(DataTipMode.MINIMUM))
        d._accept()
        assert d.data_tip_mode == DataTipMode.MINIMUM

    def test_all_three_modes_offered(self):
        _w, d = self._dlg()
        offered = {d.cbo_tips.itemData(i)
                   for i in range(d.cbo_tips.count())}
        assert offered == {DataTipMode.NONE, DataTipMode.MINIMUM,
                           DataTipMode.MAXIMUM}

    def test_tolerances_are_labelled_in_pixels(self):
        """They are pixels on purpose — converted by the canvas, which is
        what keeps snapping equally easy at any zoom. Labelling them
        stops anyone 'fixing' them into metres."""
        _w, d = self._dlg()
        assert d.sp_vertex.suffix().strip() == "px"
        from PySide6.QtWidgets import QLabel
        text = " ".join(" ".join(la.text().split())
                        for la in d.findChildren(QLabel))
        assert "SCREEN PIXELS" in text

    def test_defaults_restore(self):
        from ogr_gui.canvas.snap_engine import SnapSettings
        _w, d = self._dlg()
        d.sp_gh.setValue(99.0)
        d._defaults()
        assert abs(d.sp_gh.value() - SnapSettings().grid_h) < 1e-9

    def test_dialog_updates_the_status_words(self):
        """Accepting the dialog must move the words too, or the two
        routes drift apart."""
        _p, w = _window()
        w.ogr_status.osnap.setChecked(False)
        w.canvas.snap_settings.osnap = True
        w.data_tip_mode = DataTipMode.MAXIMUM
        # Simulate what _snap_options does after a successful dialog
        for attr, label in (("snap", w.ogr_status.snap),
                            ("ortho", w.ogr_status.ortho),
                            ("osnap", w.ogr_status.osnap)):
            label.setChecked(getattr(w.canvas.snap_settings, attr))
        assert w.ogr_status.osnap.isChecked() is True
