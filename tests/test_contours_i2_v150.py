# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.50 — Contour engine (Interpret phase I2).

The contour engine is deliberately free of Qt — it returns plain hex
strings — so the value-to-colour mapping can be tested, and reused for
reports, without a display.

What the tests fix in place:

* **Banded, not smooth, by default.** An engineering contour plot reads
  as discrete intervals because that is how a reader takes a number off a
  colour scale; every value inside a band must therefore get exactly the
  same colour.
* **Clamping, not discarding.** A value outside the range keeps the end
  colour, so narrowing the range to study a detail does not blank out the
  rest of the model.
* **Auto-range ignores outliers.** A single factor of safety of 40 must
  not squash every meaningful value into one band.
* **One source of truth.** The legend and the canvas must ask the SAME
  settings object for the colour of a value, so a change of palette or
  range cannot leave them disagreeing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_gui.contours import (  # noqa: E402
    DEFAULT_PALETTE,
    PALETTES,
    SCALAR_FIELDS,
    ContourMode,
    ContourSettings,
    available_fields,
    sample_palette,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []


def _is_hex(c) -> bool:
    return (isinstance(c, str) and c.startswith("#") and len(c) == 7
            and all(ch in "0123456789abcdefABCDEF" for ch in c[1:]))


# ======================================================================
class TestPalettes:
    def test_every_palette_has_stops(self):
        for name, stops in PALETTES.items():
            assert stops, name
            assert all(_is_hex(c) for c in stops), name

    def test_default_palette_exists(self):
        assert DEFAULT_PALETTE in PALETTES

    def test_sampling_returns_the_end_stops(self):
        for name, stops in PALETTES.items():
            assert sample_palette(name, 0.0).lower() == stops[0].lower()
            assert sample_palette(name, 1.0).lower() == stops[-1].lower()

    def test_sampling_interpolates(self):
        mid = sample_palette("Greyscale", 0.5)
        assert _is_hex(mid)
        assert mid.lower() not in [c.lower()
                                   for c in PALETTES["Greyscale"][:1]]

    def test_out_of_range_is_clamped(self):
        assert sample_palette("Viridis", -5.0) == \
            sample_palette("Viridis", 0.0)
        assert sample_palette("Viridis", 5.0) == \
            sample_palette("Viridis", 1.0)

    def test_unknown_palette_falls_back(self):
        assert _is_hex(sample_palette("does-not-exist", 0.5))

    def test_accessible_palette_offered(self):
        """A report may have to remain readable in print and to readers
        with colour vision deficiency."""
        assert "Accessible" in PALETTES
        assert "Greyscale" in PALETTES


# ======================================================================
class TestBanding:
    def test_values_in_one_band_share_a_colour(self):
        """This is what makes a contour plot readable: a band is one
        colour, so a reader can match it against the legend."""
        s = ContourSettings(vmin=0.0, vmax=1.0, intervals=4)
        a = s.colour_for(0.01)
        b = s.colour_for(0.24)
        assert a == b
        assert s.colour_for(0.26) != a

    def test_smooth_mode_does_not_band(self):
        s = ContourSettings(vmin=0.0, vmax=1.0, intervals=4,
                            mode=ContourMode.SMOOTH)
        assert s.colour_for(0.01) != s.colour_for(0.24)

    def test_level_boundaries(self):
        s = ContourSettings(vmin=1.0, vmax=2.0, intervals=4)
        lv = s.levels()
        assert len(lv) == 5
        assert abs(lv[0] - 1.0) < 1e-12
        assert abs(lv[-1] - 2.0) < 1e-12
        assert abs(lv[1] - 1.25) < 1e-12

    def test_band_colours_count(self):
        s = ContourSettings(intervals=7)
        assert len(s.band_colours()) == 7
        assert all(_is_hex(c) for c in s.band_colours())

    def test_level_index_bounds(self):
        s = ContourSettings(vmin=0.0, vmax=1.0, intervals=5)
        assert s.level_index(-10.0) == 0
        assert s.level_index(10.0) == 4
        assert 0 <= s.level_index(0.5) <= 4


class TestRangeHandling:
    def test_values_outside_the_range_are_clamped(self):
        """Narrowing the range to study a detail must not blank out the
        rest of the model."""
        s = ContourSettings(vmin=1.0, vmax=2.0, intervals=4)
        assert s.colour_for(-100.0) == s.colour_for(1.0)
        assert s.colour_for(100.0) == s.colour_for(1.999)

    def test_degenerate_range_does_not_divide_by_zero(self):
        s = ContourSettings(vmin=1.5, vmax=1.5)
        assert s.span > 0
        assert _is_hex(s.colour_for(1.5))

    def test_non_finite_value_is_safe(self):
        s = ContourSettings()
        assert _is_hex(s.colour_for(float("nan")))
        assert _is_hex(s.colour_for(float("inf")))

    def test_reverse_flips_the_mapping(self):
        a = ContourSettings(vmin=0.0, vmax=1.0, mode=ContourMode.SMOOTH)
        b = ContourSettings(vmin=0.0, vmax=1.0, mode=ContourMode.SMOOTH,
                            reverse=True)
        assert a.colour_for(0.0) == b.colour_for(1.0)
        assert a.colour_for(1.0) == b.colour_for(0.0)


class TestAutoRange:
    def test_ignores_extreme_outliers(self):
        """One surface at 40 must not squash the rest into a single
        band."""
        values = [1.0 + 0.01 * i for i in range(100)] + [40.0]
        s = ContourSettings()
        s.fit_to(values)
        assert s.vmin <= 1.0
        assert s.vmax < 5.0, s.vmax

    def test_keeps_the_low_end_exactly(self):
        """The low end is what matters in stability, so it is taken
        as-is rather than trimmed."""
        values = [0.7, 1.0, 1.5, 2.0]
        s = ContourSettings()
        s.fit_to(values)
        assert abs(s.vmin - 0.7) < 1e-12

    def test_constant_data_gives_a_usable_range(self):
        s = ContourSettings()
        s.fit_to([2.0] * 20)
        assert s.vmax > s.vmin

    def test_empty_data_leaves_the_range_alone(self):
        s = ContourSettings(vmin=0.0, vmax=3.0)
        s.fit_to([])
        assert (s.vmin, s.vmax) == (0.0, 3.0)


class TestFormattingAndSerialisation:
    def test_decimal_and_scientific(self):
        s = ContourSettings(decimals=3)
        assert s.format_value(0.5) == "0.500"
        s.scientific = True
        assert "e" in s.format_value(0.5)

    def test_round_trip(self):
        s = ContourSettings(mode=ContourMode.LINES, palette="Viridis",
                            vmin=0.5, vmax=4.0, intervals=12,
                            reverse=True, field="pore_pressure",
                            decimals=3, scientific=True)
        s2 = ContourSettings.from_dict(s.to_dict())
        assert s2.mode == ContourMode.LINES
        assert s2.palette == "Viridis"
        assert s2.intervals == 12
        assert s2.reverse is True
        assert s2.field == "pore_pressure"
        assert s2.colour_for(2.0) == s.colour_for(2.0)


class TestAvailableFields:
    def test_fos_offered_when_a_search_exists(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        r = GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                       grid_y=(62, 80), grid_nx=3, grid_ny=3,
                       radius_increment=10, min_radius=15,
                       num_slices=14, min_area=0.5).run(p)
        assert "fos" in available_fields(p, r)

    def test_hydraulic_fields_only_with_a_seepage_result(self):
        """Offering a field with no data behind it is worse than not
        offering it."""
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        assert "pore_pressure" not in available_fields(p, None)

    def test_every_field_has_a_label(self):
        for key in ("fos", "pore_pressure", "total_head",
                    "pressure_head"):
            assert key in SCALAR_FIELDS


# ======================================================================
@_requires_qt
class TestDialog:
    def _dlg(self, values=None):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.contour_options_dialog import (
            ContourOptionsDialog,
        )
        return ContourOptionsDialog(ContourSettings(), ["fos"],
                                    values or [1.0, 1.5, 2.0, 2.5], None)

    def test_offers_every_mode_and_palette(self):
        d = self._dlg()
        assert d.cbo_mode.count() == 5
        assert d.cbo_palette.count() == len(PALETTES)

    def test_auto_range_disables_the_bounds(self):
        d = self._dlg()
        d.chk_auto.setChecked(True)
        assert d.sp_min.isEnabled() is False
        d.chk_auto.setChecked(False)
        assert d.sp_min.isEnabled() is True

    def test_auto_range_fits_the_data(self):
        d = self._dlg(values=[2.0, 2.5, 3.0])
        d.chk_auto.setChecked(False)
        d.chk_auto.setChecked(True)
        assert abs(d.sp_min.value() - 2.0) < 1e-6

    def test_interval_size_is_reported(self):
        d = self._dlg()
        d.chk_auto.setChecked(False)
        d.sp_min.setValue(0.0)
        d.sp_max.setValue(1.0)
        d.sp_int.setValue(4)
        assert d.lbl_step.text().startswith("0.25")

    def test_preview_follows_the_settings(self):
        d = self._dlg()
        before = d.preview._settings.palette
        d.cbo_palette.setCurrentIndex(
            d.cbo_palette.findData("Viridis"))
        assert d.preview._settings.palette == "Viridis" != before

    def test_accept_collects_everything(self):
        d = self._dlg()
        d.chk_auto.setChecked(False)
        d.sp_int.setValue(11)
        d.chk_rev.setChecked(True)
        d.cbo_mode.setCurrentIndex(d.cbo_mode.findData(ContourMode.LINES))
        d._accept()
        assert d.settings.intervals == 11
        assert d.settings.reverse is True
        assert d.settings.mode == ContourMode.LINES

    def test_defaults_restore(self):
        d = self._dlg()
        d.sp_int.setValue(30)
        d._defaults()
        assert d.sp_int.value() == ContourSettings().intervals


# ======================================================================
@_requires_qt
class TestInterpretIntegration:
    def _window(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.i18n import set_language
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        r = GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                       grid_y=(62, 80), grid_nx=3, grid_ny=3,
                       radius_increment=10, min_radius=15,
                       num_slices=14, min_area=0.5).run(p)
        w = InterpretWindow(p, {"bishop_simplified": r}, None)
        _WINDOWS.append(w)
        return p, r, w

    def test_legend_and_canvas_share_one_source_of_truth(self):
        """A change of palette or range must be reflected in both
        without further plumbing, so both must hold the SAME callable."""
        _p, _r, w = self._window()
        assert w.legend._colour_fn == w.contours.colour_for
        assert w.canvas._contour_colour_fn == w.contours.colour_for

    def test_palette_change_propagates(self):
        _p, _r, w = self._window()
        before = w.contours.band_colours()[0]
        w.contours.palette = "Viridis"
        w._refresh_legend()
        assert w.contours.band_colours()[0] != before
        assert w.legend._colour_fn(w.contours.vmin) == \
            w.contours.colour_for(w.contours.vmin)

    def test_auto_range_follows_the_results(self):
        _p, r, w = self._window()
        values = [e.fos for e in r.evaluations if e.is_valid]
        assert w.contours.vmin <= min(values) + 1e-9

    def test_contour_mode_off_clears_the_canvas_override(self):
        _p, _r, w = self._window()
        w.contours.mode = ContourMode.OFF
        w._refresh_legend()
        assert w.canvas._contour_colour_fn is None

    def test_field_values_for_fos(self):
        _p, r, w = self._window()
        assert len(w.current_field_values()) == r.valid_count

    def test_contour_options_in_the_view_menu(self):
        _p, _r, w = self._window()
        for act in w.menuBar().actions():
            if act.menu() is not None and act.text() == "View":
                texts = [a.text() for a in act.menu().actions()
                         if a.text()]
                assert any("Contour Options" in t for t in texts), texts
                return
        raise AssertionError("no View menu")

    def test_canvas_override_can_be_cleared(self):
        _p, _r, w = self._window()
        w.canvas.set_contour_colour_fn(None)
        assert w.canvas._contour_colour_fn is None
