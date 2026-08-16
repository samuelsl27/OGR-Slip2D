# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Contour engine — Interpret phase I2.

Turns a scalar field into colours: the palettes, the value-to-colour
mapping and the discretisation into levels. Deliberately **free of Qt**,
returning plain ``#rrggbb`` strings, so the mapping can be tested — and
reused for reports or exports — without a display.

Design points:

* **Banded by default, not smooth.** Engineering contour plots read as
  discrete intervals because that is how a reader extracts a number from
  a colour. A continuous gradient looks prettier and is harder to use, so
  ``FILLED`` snaps each value to the centre of its band and a separate
  ``SMOOTH`` mode is offered for those who want the gradient.
* **The range is separate from the palette.** Clamping outside values to
  the end colours (rather than leaving them uncoloured) means a user who
  narrows the range to inspect a detail still sees the whole model.
* **Auto-ranging ignores outliers.** A single surface with a factor of
  safety of 40 would otherwise squash every meaningful value into one
  band, so the automatic range uses a percentile.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class ContourMode(Enum):
    """How the scalar field is drawn."""

    OFF = "off"
    LINES = "lines"                  # iso-lines only
    FILLED = "filled"                # banded fill
    FILLED_LINES = "filled_lines"    # banded fill with iso-lines
    SMOOTH = "smooth"                # continuous gradient


# Palettes as ordered colour stops. The first two mirror the convention
# used by geotechnical software (red = unsafe), the rest are offered
# because a report may need a colour-blind-safe or greyscale figure.
PALETTES: dict[str, tuple[str, ...]] = {
    # v0.1.82 — the reference program's default factor-of-safety legend,
    # sampled pixel by pixel from a screenshot of the Ej_1 run supplied
    # with the benchmark (`referencias/Ejemplos/Ej_1/`, Interpret view).
    # These are MEASURED values, not a formula guessed from the look of
    # it: 24 bands over a fixed 0–6 range, i.e. one band per 0.25, with
    # the last band carrying everything at or above 6 ("6.000+").
    #
    # They happen to trace an HSV hue ramp from 0° (red) to 230° in 10°
    # steps, with the final band snapped to a pure 240° blue — but the
    # ramp is a description of the measurement, not its source, so the
    # measurement is what is written down.
    "Slide rainbow": (
        "#ff0000", "#ff2a00", "#ff5500", "#ff7f00", "#ffaa00", "#ffd400",
        "#feff00", "#d4ff00", "#a9ff00", "#7fff00", "#55ff00", "#2aff00",
        "#00ff00", "#00ff2a", "#00ff54", "#00ff7f", "#00ffa9", "#00ffd4",
        "#00ffff", "#00d4ff", "#00a9ff", "#007fff", "#0054ff", "#0000ff",
    ),
    "Stability": ("#dc1e1e", "#f06428", "#f5a03c", "#f5d750",
                  "#c8dc64", "#8cc864", "#64a064", "#6e6e78"),
    "Hot to cold": ("#b2182b", "#ef8a62", "#fddbc7", "#f7f7f7",
                    "#d1e5f0", "#67a9cf", "#2166ac"),
    "Viridis": ("#440154", "#414487", "#2a788e", "#22a884",
                "#7ad151", "#fde725"),
    "Blue to red": ("#2166ac", "#67a9cf", "#d1e5f0", "#fddbc7",
                    "#ef8a62", "#b2182b"),
    "Greyscale": ("#1a1a1a", "#4d4d4d", "#808080", "#b3b3b3",
                  "#e6e6e6"),
    # Colour-blind safe (Okabe-Ito derived), for figures that must remain
    # readable in print and to readers with colour vision deficiency.
    "Accessible": ("#332288", "#117733", "#44AA99", "#88CCEE",
                   "#DDCC77", "#CC6677", "#882255"),
}

DEFAULT_PALETTE = "Slide rainbow"

# Palettes whose stops ARE the bands, one colour each, rather than a
# continuous ramp to be sampled. When the interval count matches the stop
# count the colour is taken straight from the list, which is the only way
# to reproduce a reference legend exactly: sampling a 24-stop ramp at band
# centres lands halfway between every pair of measured colours.
DISCRETE_PALETTES = frozenset({"Slide rainbow"})


def _hex_to_rgb(value: str):
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _rgb_to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def sample_palette(name: str, t: float) -> str:
    """Colour at position ``t`` in [0, 1] of a palette, interpolated."""
    stops = PALETTES.get(name) or PALETTES[DEFAULT_PALETTE]
    if len(stops) == 1:
        return stops[0]
    t = 0.0 if not math.isfinite(t) else min(max(t, 0.0), 1.0)
    pos = t * (len(stops) - 1)
    i = min(int(pos), len(stops) - 2)
    f = pos - i
    a, b = _hex_to_rgb(stops[i]), _hex_to_rgb(stops[i + 1])
    return _rgb_to_hex(tuple(a[k] + f * (b[k] - a[k]) for k in range(3)))


# ======================================================================
@dataclass
class ContourSettings:
    """Everything the contour dialog collects."""

    mode: ContourMode = ContourMode.FILLED
    palette: str = DEFAULT_PALETTE
    vmin: float = 0.0
    vmax: float = 6.0
    intervals: int = 24
    reverse: bool = False
    auto_range: bool = False
    field: str = "fos"           # which scalar is being contoured
    # Number formatting, shared with the legend
    decimals: int = 3
    scientific: bool = False
    opacity: float = 1.0

    # ------------------------------------------------------------------
    @property
    def span(self) -> float:
        return max(self.vmax - self.vmin, 1e-12)

    def normalised(self, value: float) -> float:
        """Value mapped to [0, 1], clamped.

        Clamping (rather than returning None outside the range) means a
        user who narrows the range to study a detail still sees the whole
        model, drawn in the end colours.
        """
        if not math.isfinite(value):
            return 0.0
        t = (value - self.vmin) / self.span
        t = min(max(t, 0.0), 1.0)
        return 1.0 - t if self.reverse else t

    def level_index(self, value: float) -> int:
        """Which band a value falls in, 0 .. intervals-1."""
        n = max(1, self.intervals)
        idx = int(self.normalised(value) * n)
        return min(max(idx, 0), n - 1)

    def colour_for(self, value: float) -> str:
        """Colour of a value, honouring the mode.

        ``FILLED`` snaps to the centre of the band so the plot reads as
        discrete intervals, which is how an engineer takes a number off a
        colour scale. ``SMOOTH`` interpolates continuously.
        """
        if self.mode == ContourMode.SMOOTH:
            return sample_palette(self.palette, self.normalised(value))
        n = max(1, self.intervals)
        stops = PALETTES.get(self.palette)
        if (self.palette in DISCRETE_PALETTES and stops
                and len(stops) == n):
            # One measured colour per band: index it, do not interpolate.
            return stops[self.level_index(value)]
        centre = (self.level_index(value) + 0.5) / n
        return sample_palette(self.palette, centre)

    # ------------------------------------------------------------------
    def band_label(self, i: int) -> str:
        """Label of band ``i``: its lower bound, or ``"6.000+"`` for the
        last one.

        The mapping saturates (``normalised`` clamps), so everything above
        ``vmax`` shares the top band's colour. Labelling that band with a
        plain number would claim a precision the plot does not have; the
        reference writes it with a trailing ``+`` and so do we.
        """
        n = max(1, self.intervals)
        v = self.vmin + self.span * min(i, n) / n
        text = self.format_value(v)
        return f"{text}+" if i >= n else text

    def levels(self) -> list:
        """Boundary values of the bands, ``intervals + 1`` of them."""
        n = max(1, self.intervals)
        return [self.vmin + self.span * i / n for i in range(n + 1)]

    def band_colours(self) -> list:
        """One colour per band, for drawing the legend."""
        n = max(1, self.intervals)
        return [self.colour_for(self.vmin + self.span * (i + 0.5) / n)
                for i in range(n)]

    def format_value(self, v: float) -> str:
        if self.scientific:
            return f"{v:.{self.decimals}e}"
        return f"{v:.{self.decimals}f}"

    # ------------------------------------------------------------------
    def fit_to(self, values, percentile: float = 0.98) -> None:
        """Set the range from data, ignoring extreme outliers.

        A single surface with a factor of safety of 40 would otherwise
        squash every meaningful value into one band, so the upper bound
        comes from a percentile rather than the maximum. The minimum is
        taken as-is: the low end is exactly what matters in stability.
        """
        vals = sorted(v for v in values if math.isfinite(v))
        if not vals:
            return
        lo = vals[0]
        k = min(len(vals) - 1, int(round(percentile * (len(vals) - 1))))
        hi = vals[k]
        if hi <= lo:
            hi = lo + max(abs(lo) * 0.1, 1.0)
        self.vmin, self.vmax = float(lo), float(hi)

    def to_dict(self) -> dict:
        return {"mode": self.mode.value, "palette": self.palette,
                "vmin": self.vmin, "vmax": self.vmax,
                "intervals": self.intervals, "reverse": self.reverse,
                "auto_range": self.auto_range, "field": self.field,
                "decimals": self.decimals, "scientific": self.scientific,
                "opacity": self.opacity}

    # ------------------------------------------------------------------
    @classmethod
    def for_field(cls, field: str) -> "ContourSettings":
        """Sensible starting point for a given scalar.

        The factor of safety gets the reference program's default legend:
        a FIXED 0–6 range in 24 bands. Fixed is the point — auto-ranging a
        factor of safety puts one deep-seated surface at 31 in the top of
        the scale and squashes everything a reader cares about, 0.8 to
        1.5, into the first band. The hydraulic fields keep the automatic
        range, because a total head in metres does not live in 0–6 and no
        fixed range would suit two models.
        """
        if field == "fos":
            return cls(field="fos")          # the dataclass defaults
        return cls(field=field, palette="Hot to cold", intervals=8,
                   auto_range=True, decimals=2)

    @classmethod
    def from_dict(cls, d: dict) -> "ContourSettings":
        return cls(
            mode=ContourMode(d.get("mode", "filled")),
            palette=str(d.get("palette", DEFAULT_PALETTE)),
            vmin=float(d.get("vmin", 0.0)),
            vmax=float(d.get("vmax", 6.0)),
            intervals=int(d.get("intervals", 24)),
            reverse=bool(d.get("reverse", False)),
            auto_range=bool(d.get("auto_range", False)),
            field=str(d.get("field", "fos")),
            decimals=int(d.get("decimals", 3)),
            scientific=bool(d.get("scientific", False)),
            opacity=float(d.get("opacity", 1.0)),
        )


# ======================================================================
# Scalar fields available for contouring
# ======================================================================
SCALAR_FIELDS = {
    "fos": "Factor of safety",
    "pore_pressure": "Pore pressure",
    "total_head": "Total head",
    "pressure_head": "Pressure head",
}


def available_fields(project, search_result=None) -> list:
    """Which scalar fields the current results can actually contour.

    Offering a field with no data behind it is worse than not offering
    it, so the list is built from what exists: factors of safety come
    from the search, the hydraulic fields from a seepage result.
    """
    out = []
    if search_result is not None and getattr(
            search_result, "evaluations", None):
        out.append("fos")
    seepage = getattr(project, "seepage_result", None)
    if seepage is not None and getattr(seepage, "total_head", None):
        out.extend(["pore_pressure", "total_head", "pressure_head"])
    return out
