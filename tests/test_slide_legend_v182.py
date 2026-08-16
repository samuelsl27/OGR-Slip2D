# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.82 — The reference factor-of-safety legend, and what it colours.

**The invariant.** The colour of a factor of safety is one number's worth
of information, and it must mean the same thing in three places at once:
the contoured slip-centre grid, the slip surfaces drawn over the model,
and the legend that explains both. Before this version only the grid was
coloured — surfaces were a single fixed green — so the legend explained a
mapping that two of the three views did not use.

**The colours are measured, not invented.** They were sampled pixel by
pixel from the Interpret window of the Ej_1 run supplied with the
benchmark (``referencias/Ejemplos/Ej_1/``): 24 bands over a FIXED 0–6
range, running red to blue. They are asserted here as literals because
that is what they are — data read off a reference, the same standing this
project gives a published factor of safety.

**Fixed range, not automatic.** Auto-ranging a factor of safety is
actively harmful: one deep-seated surface at 31 stretches the scale and
squashes 0.8–1.5, the only region a reader cares about, into the first
band. That is exactly what the screenshots of our own Interpret showed
(0.90 → 31.34). The hydraulic fields keep the automatic range, because a
total head in metres does not live in 0–6.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_gui.contours import (  # noqa: E402
    DEFAULT_PALETTE,
    DISCRETE_PALETTES,
    PALETTES,
    ContourMode,
    ContourSettings,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []

# Sampled from the reference legend, top (0.000) to bottom (6.000+).
_MEASURED = [
    "#ff0000", "#ff2a00", "#ff5500", "#ff7f00", "#ffaa00", "#ffd400",
    "#feff00", "#d4ff00", "#a9ff00", "#7fff00", "#55ff00", "#2aff00",
    "#00ff00", "#00ff2a", "#00ff54", "#00ff7f", "#00ffa9", "#00ffd4",
    "#00ffff", "#00d4ff", "#00a9ff", "#007fff", "#0054ff", "#0000ff",
]


# ======================================================================
class TestTheMeasuredPalette:
    def test_the_palette_is_the_measurement(self):
        assert list(PALETTES["Slide rainbow"]) == _MEASURED

    def test_it_is_the_default_for_a_factor_of_safety(self):
        assert DEFAULT_PALETTE == "Slide rainbow"
        s = ContourSettings.for_field("fos")
        assert s.palette == "Slide rainbow"
        assert (s.vmin, s.vmax, s.intervals) == (0.0, 6.0, 24)

    def test_bands_are_indexed_not_interpolated(self):
        """A 24-stop ramp sampled at band centres lands halfway between
        every pair of measured colours, so none of the reference colours
        would ever actually be drawn. Discrete palettes are indexed."""
        assert "Slide rainbow" in DISCRETE_PALETTES
        s = ContourSettings.for_field("fos")
        # Band i covers [0.25 i, 0.25 (i+1)).
        for i, want in enumerate(_MEASURED):
            v = 0.25 * i + 0.125
            assert s.colour_for(v).lower() == want, (i, v, s.colour_for(v))

    def test_a_failing_surface_is_red_and_a_safe_one_is_not(self):
        """The convention the whole scale exists to carry."""
        s = ContourSettings.for_field("fos")
        assert s.colour_for(0.10).lower() == "#ff0000"
        assert s.colour_for(0.883).lower().startswith("#ff")
        # 5.6 falls in band 22 (5.50–5.75); 5.9 is already in the last.
        assert s.colour_for(5.6).lower() == "#0054ff"

    def test_everything_above_six_shares_the_last_band(self):
        s = ContourSettings.for_field("fos")
        assert s.colour_for(6.0) == s.colour_for(31.34)
        assert s.colour_for(6.0).lower() == "#0000ff"

    def test_the_last_label_says_it_saturates(self):
        """Labelling the top boundary "6.000" would claim the scale stops
        there when in fact everything above it is drawn the same."""
        s = ContourSettings.for_field("fos")
        assert s.band_label(0) == "0.000"
        assert s.band_label(2) == "0.500"
        assert s.band_label(24) == "6.000+"


class TestRangePolicyPerField:
    def test_factor_of_safety_does_not_auto_range(self):
        s = ContourSettings.for_field("fos")
        assert s.auto_range is False

    def test_hydraulic_fields_still_do(self):
        """A total head in metres has no natural fixed range, and no one
        value would suit two models."""
        for field in ("total_head", "pore_pressure", "pressure_head"):
            s = ContourSettings.for_field(field)
            assert s.auto_range is True, field
            assert s.palette != "Slide rainbow", field

    def test_the_same_factor_of_safety_is_always_the_same_colour(self):
        """What a fixed range buys, and it is not extra resolution.

        With auto-range the scale is rebuilt from whatever the current
        result happens to contain, so 0.883 comes out one colour for
        Bishop and another for Janbu on the same model — and a different
        one again after the grid is widened. Nothing on screen can then be
        compared with anything else, which is what the reference's fixed
        0–6 default exists to prevent.
        """
        run_a = [0.88 + 0.01 * i for i in range(40)]
        run_b = run_a + [4.0 + 0.5 * i for i in range(30)]
        a, b = ContourSettings(auto_range=True), ContourSettings(
            auto_range=True)
        a.fit_to(run_a)
        b.fit_to(run_b)
        probes = [1.00, 1.10, 1.20]
        assert any(a.colour_for(v) != b.colour_for(v) for v in probes), (
            [(a.colour_for(v), b.colour_for(v)) for v in probes])

        fa, fb = (ContourSettings.for_field("fos"),
                  ContourSettings.for_field("fos"))
        assert fa.auto_range is False and fb.auto_range is False
        assert all(fa.colour_for(v) == fb.colour_for(v)
                   for v in probes + [0.883])


# ======================================================================
@_requires_qt
class TestSurfacesCarryTheLegendColour:
    """The point of the whole change: a surface must be drawn in the
    colour its factor of safety has in the legend."""

    def _interpret(self):
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
                       radius_increment=8, min_radius=15, num_slices=14,
                       min_area=0.5).run(p)
        w = InterpretWindow(p, {"bishop_simplified": r}, None)
        _WINDOWS.append(w)
        return p, r, w

    def test_surface_pen_is_the_legend_colour(self):
        from PySide6.QtGui import QColor

        from ogr_gui.canvas.canvas_view import SlipSurfaceItem
        _p, _r, w = self._interpret()
        w._set_surface_mode("all")
        drawn = [it for it in w.canvas._result_items
                 if isinstance(it, SlipSurfaceItem)
                 and not it.is_critical and not it.is_selected]
        assert drawn, "nothing drawn to check"
        for it in drawn:
            want = QColor(w.contours.colour_for(it.fos))
            assert it.pen().color().name() == want.name(), (
                it.fos, it.pen().color().name(), want.name())

    def test_two_different_factors_get_two_different_colours(self):
        """Guards against a colour function that is wired up but constant
        — which is what a fixed green was."""
        from ogr_gui.canvas.canvas_view import SlipSurfaceItem
        _p, _r, w = self._interpret()
        w._set_surface_mode("all")
        drawn = [it for it in w.canvas._result_items
                 if isinstance(it, SlipSurfaceItem) and not it.is_critical]
        colours = {it.pen().color().name() for it in drawn}
        assert len(colours) > 1, colours

    def test_the_legend_shows_the_same_bands(self):
        _p, _r, w = self._interpret()
        assert w.legend._bands == list(w.contours.band_colours())
        assert w.legend._labels[-1].endswith("+")

    def test_legend_paints_without_error(self):
        from PySide6.QtGui import QPixmap
        _p, _r, w = self._interpret()
        w.legend.resize(120, 400)
        pm = QPixmap(120, 400)
        w.legend.render(pm)

    def test_there_is_only_one_legend(self):
        """The Summary dock used to carry a second, hard-coded colour
        table (red ≤ 1.00 … grey > 3.00) copied from a colour function
        the canvas no longer uses. Two legends for one plot, disagreeing
        with each other, is worse than none."""
        _p, _r, w = self._interpret()
        html = w.summary_dock.label.text()
        assert "heatmap legend" not in html.lower()
        for stale in ("#dc1e1e", "#f06428", "#6e6e78"):
            assert stale not in html.lower(), stale

    def test_switching_to_lines_mode_drops_the_bands(self):
        """The banded legend describes a banded plot; a smooth plot must
        not be explained with swatches it never draws."""
        _p, _r, w = self._interpret()
        w.contours.mode = ContourMode.SMOOTH
        w._refresh_legend()
        assert w.legend._bands is None
