# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Boundary — a typed polyline participating in the geotechnical model.

A Boundary wraps a Polyline with semantic role (BoundaryType), rendering
hints, and optional material/hydraulic references.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from .boundary_type import BoundaryType
from .primitives import Polyline, Vertex


@dataclass
class Boundary:
    polyline: Polyline
    btype: BoundaryType
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    color: Optional[str] = None
    line_width: float = 1.5
    visible: bool = True
    material_id: Optional[str] = None
    """Reference to a material.

    Meaningful for material boundaries and — since v0.1.121 — for WEAK_LAYER
    boundaries, where it names the material whose strength the slip surface
    mobilises along the layer.
    """
    suppressed: bool = False
    """Excluded from the analysis without being deleted (v0.1.121).

    Only WEAK_LAYER reads it. It exists because an active weak layer lying
    outside the external boundary can make discretisation fail, and deleting
    the layer to find out is not a workflow.
    """

    def __post_init__(self) -> None:
        if self.color is None:
            self.color = self.btype.default_color
        if not self.name:
            self.name = self.btype.display_name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.btype.name,
            "color": self.color,
            "line_width": self.line_width,
            "visible": self.visible,
            "material_id": self.material_id,
            "suppressed": self.suppressed,
            "polyline": self.polyline.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Boundary":
        b = cls(
            polyline=Polyline.from_dict(data["polyline"]),
            btype=BoundaryType[data["type"]],
            name=data.get("name", ""),
            color=data.get("color"),
            line_width=data.get("line_width", 1.5),
            visible=data.get("visible", True),
            material_id=data.get("material_id"),
            suppressed=bool(data.get("suppressed", False)),
        )
        if "id" in data:
            b.id = data["id"]
        return b

    # ---------- convenience ----------
    @property
    def vertices(self) -> list[Vertex]:
        return self.polyline.vertices

    def bounding_box(self) -> tuple[float, float, float, float]:
        return self.polyline.bounding_box()
