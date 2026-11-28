# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.506 — every contoured field that is not the factor of safety starts
with a palette whose lightness grows with the value (OGR FEM2D's proposal
D5, the owner's decision of 2026-11-28).

The invariant
-------------
Until v0.1.505 the hydraulic fields (pore pressure, total head, pressure
head) and the Ky and Newmark scale of a seismic run (D438, v0.1.500)
started with «Hot to cold», a divergent ramp light in the middle: its
lightness rises and then falls, so the order of the values does not read in
a grey copy nor to a reader who does not tell red from green, and none of
those fields has a middle with a meaning. Now:

* they start with ``FIELD_PALETTE``, Viridis, and the lightness of its
  stops, and of the eight bands drawn from it, grows strictly with the
  value; the control, «Hot to cold», does not (it peaks in its middle);
* a Ky run and a Newmark run keep their critical end, now DARK: the band of
  the lowest Ky and the band of the largest displacement (``reverse``) are
  the darkest of their scale;
* the report's figure says the same as the window: ``viridis`` for a Ky
  run, ``viridis_r`` for a Newmark one (the figures themselves are
  ``test_report_figures_seismic_v1450``);
* the factor of safety keeps its measured legend, Rainbow in 24 bands over
  0 to 6 (v0.1.82, the identity the interface guide keeps).

The reference (rule 1): the lightness is CIE 1976 L* of the sRGB colour
(IEC 61966-2-1 for the transfer curve, D65 white, Y from the linear Rec. 709
primaries), computed here from its formula, not from any library of the
program. Cost: arithmetic only, well under a second.
"""
from __future__ import annotations


def _lightness(hex_colour: str) -> float:
    """CIE 1976 L* of an sRGB colour (IEC 61966-2-1; CIE 15:2004)."""
    h = hex_colour.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    f = y ** (1.0 / 3.0) if y > (6.0 / 29.0) ** 3 else (
        y / (3.0 * (6.0 / 29.0) ** 2) + 4.0 / 29.0)
    return 116.0 * f - 16.0


def _increasing(values) -> bool:
    return all(b > a for a, b in zip(values, values[1:]))


class TestTheLightnessGrowsWithTheValue:

    def test_the_formula_on_its_fixed_points(self):
        # black, white and mid grey #777777 (L* 50.03, the textbook value)
        assert abs(_lightness("#000000")) < 1e-9
        assert abs(_lightness("#ffffff") - 100.0) < 1e-9
        assert abs(_lightness("#777777") - 50.03) < 0.01

    def test_viridis_stops_and_bands(self):
        from ogr_gui.contours import FIELD_PALETTE, PALETTES, ContourSettings
        assert FIELD_PALETTE == "Viridis"
        assert _increasing([_lightness(c) for c in PALETTES[FIELD_PALETTE]])
        s = ContourSettings.for_field("total_head")
        s.vmin, s.vmax = 0.0, 1.0
        assert _increasing([_lightness(c) for c in s.band_colours()])

    def test_the_control_hot_to_cold_is_not(self):
        from ogr_gui.contours import PALETTES
        ls = [_lightness(c) for c in PALETTES["Hot to cold"]]
        top = ls.index(max(ls))
        assert 0 < top < len(ls) - 1, ls      # light in its middle


class TestWhichFieldStartsWithIt:

    def test_the_hydraulic_fields(self):
        # the palette by its name, so the old tree fails on the value
        from ogr_gui.contours import ContourSettings
        FIELD_PALETTE = "Viridis"
        for field in ("pore_pressure", "total_head", "pressure_head"):
            s = ContourSettings.for_field(field)
            assert (s.palette, s.reverse, s.auto_range) == (
                FIELD_PALETTE, False, True), field

    def test_the_factor_keeps_its_legend(self):
        from ogr_gui.contours import ContourSettings
        for s in (ContourSettings.for_field("fos"),
                  ContourSettings.for_reported("fos")):
            assert (s.palette, s.vmin, s.vmax, s.intervals, s.auto_range) \
                == ("Rainbow (24 bands)", 0.0, 6.0, 24, False)

    def test_a_ky_run_is_dark_at_its_lowest(self):
        # the palette by its name, so the old tree fails on the value
        from ogr_gui.contours import ContourSettings
        FIELD_PALETTE = "Viridis"
        s = ContourSettings.for_reported("ky")
        assert (s.palette, s.reverse) == (FIELD_PALETTE, False)
        s.vmin, s.vmax = 0.1, 0.4
        lows = _lightness(s.colour_for(0.1001))
        assert lows == min(_lightness(c) for c in s.band_colours())

    def test_a_newmark_run_is_dark_at_its_largest(self):
        # the palette by its name, so the old tree fails on the value
        from ogr_gui.contours import ContourSettings
        FIELD_PALETTE = "Viridis"
        s = ContourSettings.for_reported("newmark")
        assert (s.palette, s.reverse) == (FIELD_PALETTE, True)
        s.vmin, s.vmax = 0.0, 31.0
        top = _lightness(s.colour_for(30.99))
        assert top == min(_lightness(c) for c in s.band_colours())


class TestTheReportSaysTheSame:

    def test_its_colour_maps(self):
        """The colour map ``grid_data`` hands the figure, read in the source
        so that no run is needed (the figures, drawn, are v1450's)."""
        import inspect

        import ogr_api.report_figures as F
        src = inspect.getsource(F.grid_data)
        assert 'out["cmap"] = "viridis"' in src
        assert 'out["cmap"] = "viridis_r"' in src
        assert "RdYlBu" not in src
