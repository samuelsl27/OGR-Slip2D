# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tension Crack hydraulic properties (v0.1.7).

Defines how water inside a Tension Crack zone exerts hydrostatic
pressure on the slip-surface walls. Per the Slide reference
(Define_Tension_Crack.htm).

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WaterLevelMode(Enum):
    """How the water level inside the Tension Crack is specified."""
    DRY = "dry"                              # crack empty, no hydrostatic force
    FILLED = "filled"                        # 100% saturated (default in Slide)
    PERCENT_FILLED = "percent_filled"        # 0-100 % of crack depth
    FILLED_BELOW_ELEVATION = "filled_below_elevation"  # absolute Y datum
    FILLED_TO_DEPTH = "filled_to_depth"      # depth from crack top
    USE_WATER_TABLE = "use_water_table"      # water level = WT y(x)
    USE_PIEZOMETRIC = "use_piezometric"      # water level = piezo y(x)


@dataclass
class TensionCrackProperties:
    """Hydraulic properties of the Tension Crack zone.

    See ``Define_Tension_Crack.htm``: defines how water inside the
    tension crack exerts hydrostatic pressure on slip-surface walls.

    The unit weight of water (γ_w) is taken from project settings
    (Pore Fluid Unit Weight), not from this object.

    The water level is determined by ``mode``:
      - DRY: no water → no hydrostatic force
      - FILLED: water level = top of crack (crest of slope)
      - PERCENT_FILLED: water level = bottom + percent_filled/100 * height
      - FILLED_BELOW_ELEVATION: water level = ``elevation`` (absolute y)
      - FILLED_TO_DEPTH: water level = top - ``depth``
      - USE_WATER_TABLE: water level = WT.y_at(x), clipped to crack range
      - USE_PIEZOMETRIC: water level = Piezo.y_at(x)
    """
    mode: WaterLevelMode = WaterLevelMode.FILLED
    percent_filled: float = 100.0     # for PERCENT_FILLED mode
    elevation: float = 0.0            # for FILLED_BELOW_ELEVATION mode
    depth: float = 0.0                # for FILLED_TO_DEPTH mode
    piezo_id: Optional[str] = None    # for USE_PIEZOMETRIC mode

    # ------------------------------------------------------------------
    def water_level_at(
        self,
        x: float,
        crack_top_y: float,
        crack_bottom_y: float,
        water_table=None,
        piezos: Optional[dict] = None,
    ) -> float:
        """Resolve the water y-level at column ``x`` inside the crack.

        ``crack_top_y`` is the slope surface y at column x;
        ``crack_bottom_y`` is the tension-crack-boundary y at column x.

        Returns the y-coordinate of the water surface, clamped to
        ``[crack_bottom_y, crack_top_y]``. If the crack is dry, returns
        ``crack_bottom_y`` (no water column).
        """
        if self.mode == WaterLevelMode.DRY:
            return crack_bottom_y
        if self.mode == WaterLevelMode.FILLED:
            return crack_top_y

        if self.mode == WaterLevelMode.PERCENT_FILLED:
            f = max(0.0, min(100.0, self.percent_filled)) / 100.0
            return crack_bottom_y + f * (crack_top_y - crack_bottom_y)

        if self.mode == WaterLevelMode.FILLED_BELOW_ELEVATION:
            return max(crack_bottom_y, min(crack_top_y, self.elevation))

        if self.mode == WaterLevelMode.FILLED_TO_DEPTH:
            wl = crack_top_y - self.depth
            return max(crack_bottom_y, min(crack_top_y, wl))

        if self.mode == WaterLevelMode.USE_WATER_TABLE and water_table is not None:
            wl = _y_on_polyline(water_table.polyline, x)
            if wl is None:
                return crack_bottom_y
            return max(crack_bottom_y, min(crack_top_y, wl))

        if self.mode == WaterLevelMode.USE_PIEZOMETRIC and piezos is not None:
            piezo = piezos.get(self.piezo_id) if self.piezo_id else None
            if piezo is None:
                return crack_bottom_y
            wl = _y_on_polyline(piezo.polyline, x)
            if wl is None:
                return crack_bottom_y
            return max(crack_bottom_y, min(crack_top_y, wl))

        return crack_bottom_y

    def is_dry(self) -> bool:
        if self.mode == WaterLevelMode.DRY:
            return True
        if self.mode == WaterLevelMode.PERCENT_FILLED and self.percent_filled <= 0:
            return True
        return False

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "percent_filled": self.percent_filled,
            "elevation": self.elevation,
            "depth": self.depth,
            "piezo_id": self.piezo_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TensionCrackProperties":
        return cls(
            mode=WaterLevelMode(data.get("mode", "filled")),
            percent_filled=float(data.get("percent_filled", 100.0)),
            elevation=float(data.get("elevation", 0.0)),
            depth=float(data.get("depth", 0.0)),
            piezo_id=data.get("piezo_id"),
        )


# ----------------------------------------------------------------------
def _y_on_polyline(polyline, x: float) -> Optional[float]:
    """Linear-interpolate the y of a polyline at column ``x``.

    Assumes the polyline is monotonically increasing in x. Returns None
    if x lies outside the polyline's x-range.
    """
    verts = polyline.vertices
    if len(verts) < 2:
        return None
    for i in range(len(verts) - 1):
        x1, y1 = verts[i].x, verts[i].y
        x2, y2 = verts[i + 1].x, verts[i + 1].y
        if min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9:
            if abs(x2 - x1) < 1e-12:
                return y1
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return None
