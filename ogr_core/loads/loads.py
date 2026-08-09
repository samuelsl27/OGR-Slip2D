# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
External loads applied to the geotechnical model.

Implements three load classes:
    - DistributedLoad : pressure [kN/m²] acting on a boundary segment
    - LineLoad        : force per unit length [kN/m] at a point
    - SeismicLoad     : pseudo-static body force applied to every slice

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

from ..geometry.primitives import Vertex


class LoadOrientation(Enum):
    NORMAL_TO_BOUNDARY = "normal_to_boundary"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    ANGLE_FROM_HORIZONTAL = "angle_from_horizontal"
    ANGLE_TO_BOUNDARY = "angle_to_boundary"


class LoadDistribution(Enum):
    CONSTANT = "constant"
    TRIANGULAR = "triangular"
    TRAPEZOIDAL = "trapezoidal"


# ----------------------------------------------------------------------
@dataclass
class DistributedLoad:
    """Pressure-type load applied along a boundary segment.

    Units:  magnitude in kN/m² (kPa).
    """

    start: Vertex
    end: Vertex
    magnitude_1: float = 0.0
    magnitude_2: Optional[float] = None
    """None or equal to magnitude_1 means uniform pressure."""
    orientation: LoadOrientation = LoadOrientation.NORMAL_TO_BOUNDARY
    angle_deg: float = 0.0
    distribution: LoadDistribution = LoadDistribution.CONSTANT
    # v0.1.75 — whether this load's VERTICAL component contributes to the
    # change in vertical stress that generates excess pore pressure in
    # the materials beneath it. Off by default: a load that was never
    # asked to generate excess keeps not generating it.
    creates_excess_pore_pressure: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""

    def pressure_at(self, t: float) -> float:
        """Linear interpolation between m1 and m2. 0 ≤ t ≤ 1."""
        if self.distribution == LoadDistribution.CONSTANT or self.magnitude_2 is None:
            return self.magnitude_1
        return self.magnitude_1 + (self.magnitude_2 - self.magnitude_1) * t

    def direction_vector(self) -> tuple[float, float]:
        """Unit vector giving the global direction of the load."""
        if self.orientation == LoadOrientation.VERTICAL:
            return (0.0, -1.0)
        if self.orientation == LoadOrientation.HORIZONTAL:
            return (1.0, 0.0)
        if self.orientation == LoadOrientation.NORMAL_TO_BOUNDARY:
            dx = self.end.x - self.start.x
            dy = self.end.y - self.start.y
            L = math.hypot(dx, dy) or 1.0
            # Rotate -90° (into the slope, assuming CCW boundary)
            return (dy / L, -dx / L)
        if self.orientation == LoadOrientation.ANGLE_FROM_HORIZONTAL:
            a = math.radians(self.angle_deg)
            return (math.cos(a), math.sin(a))
        if self.orientation == LoadOrientation.ANGLE_TO_BOUNDARY:
            dx = self.end.x - self.start.x
            dy = self.end.y - self.start.y
            L = math.hypot(dx, dy) or 1.0
            tx, ty = dx / L, dy / L
            a = math.radians(self.angle_deg)
            # Rotate tangent by angle
            return (tx * math.cos(a) - ty * math.sin(a),
                    tx * math.sin(a) + ty * math.cos(a))
        return (0.0, -1.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "distributed",
            "name": self.name,
            "start": [self.start.x, self.start.y],
            "end": [self.end.x, self.end.y],
            "magnitude_1": self.magnitude_1,
            "magnitude_2": self.magnitude_2,
            "orientation": self.orientation.value,
            "angle_deg": self.angle_deg,
            "distribution": self.distribution.value,
            "creates_excess_pore_pressure":
                self.creates_excess_pore_pressure,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DistributedLoad":
        return cls(
            start=Vertex(*data["start"]),
            end=Vertex(*data["end"]),
            magnitude_1=data["magnitude_1"],
            magnitude_2=data.get("magnitude_2"),
            orientation=LoadOrientation(data["orientation"]),
            angle_deg=data.get("angle_deg", 0.0),
            distribution=LoadDistribution(data.get("distribution", "constant")),
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            creates_excess_pore_pressure=bool(
                data.get("creates_excess_pore_pressure", False)),
        )

    def tooltip_html(self) -> str:
        mag = f"{self.magnitude_1:g}"
        if self.magnitude_2 is not None and self.magnitude_2 != self.magnitude_1:
            mag = f"{self.magnitude_1:g} → {self.magnitude_2:g}"
        return (
            f"<b>Distributed Load</b><br>"
            f"Magnitude: {mag} kN/m²<br>"
            f"Orientation: {self.orientation.value}<br>"
            f"Distribution: {self.distribution.value}"
        )


# ----------------------------------------------------------------------
@dataclass
class LineLoad:
    """Concentrated force per unit out-of-plane length at a point."""

    point: Vertex
    magnitude: float = 0.0  # kN/m
    orientation: LoadOrientation = LoadOrientation.VERTICAL
    angle_deg: float = 0.0
    # v0.1.75 — see DistributedLoad above. A line load is a concentrated
    # force, so the vertical STRESS it produces depends on the width it
    # is smeared over; see ``ogr_core.hydraulic.excess_pore_pressure``
    # for what that means in practice.
    creates_excess_pore_pressure: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""

    def direction_vector(self) -> tuple[float, float]:
        if self.orientation == LoadOrientation.VERTICAL:
            return (0.0, -1.0)
        if self.orientation == LoadOrientation.HORIZONTAL:
            return (1.0, 0.0)
        if self.orientation == LoadOrientation.ANGLE_FROM_HORIZONTAL:
            a = math.radians(self.angle_deg)
            return (math.cos(a), math.sin(a))
        return (0.0, -1.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "line",
            "name": self.name,
            "point": [self.point.x, self.point.y],
            "magnitude": self.magnitude,
            "orientation": self.orientation.value,
            "angle_deg": self.angle_deg,
            "creates_excess_pore_pressure":
                self.creates_excess_pore_pressure,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineLoad":
        return cls(
            point=Vertex(*data["point"]),
            magnitude=data["magnitude"],
            orientation=LoadOrientation(data["orientation"]),
            angle_deg=data.get("angle_deg", 0.0),
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            creates_excess_pore_pressure=bool(
                data.get("creates_excess_pore_pressure", False)),
        )

    def tooltip_html(self) -> str:
        return (
            f"<b>Line Load</b><br>"
            f"Magnitude: {self.magnitude:g} kN/m<br>"
            f"Orientation: {self.orientation.value}"
        )


# ----------------------------------------------------------------------
@dataclass
class SeismicLoad:
    """Pseudo-static seismic inertial body force.

    Applied to every slice as F = W · k, where W is the slice weight
    and k the seismic coefficient.

    Convention:
        kh positive → in the direction of failure
        kv positive → downward
    """

    kh: float = 0.0
    kv: float = 0.0
    enabled: bool = False
    # v0.1.75 — only the VERTICAL coefficient can generate excess pore
    # pressure, because only it changes the vertical stress. The
    # horizontal one never does, whatever this flag says.
    creates_excess_pore_pressure: bool = False

    def to_dict(self) -> dict:
        return {"kh": self.kh, "kv": self.kv, "enabled": self.enabled,
                "creates_excess_pore_pressure":
                    self.creates_excess_pore_pressure}

    @classmethod
    def from_dict(cls, data: dict) -> "SeismicLoad":
        return cls(
            kh=data.get("kh", 0.0),
            kv=data.get("kv", 0.0),
            enabled=data.get("enabled", False),
            creates_excess_pore_pressure=bool(
                data.get("creates_excess_pore_pressure", False)),
        )
