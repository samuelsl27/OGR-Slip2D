# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Boundary classification for the geotechnical model.

Every polyline in the model is classified as one of these types, which
determines both its visual rendering and its role in the numerical
solver.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from enum import Enum, auto


class BoundaryType(Enum):
    """Role of a polyline in the geotechnical model."""

    EXTERNAL = auto()
    """Outer envelope of the slope model. Exactly one per project."""

    MATERIAL = auto()
    """Internal interface separating two materials."""

    WATER_TABLE = auto()
    """Phreatic surface — active hydraulic boundary."""

    PIEZOMETRIC = auto()
    """Piezometric line — defines pore pressure distribution."""

    DRAWDOWN = auto()
    """Rapid drawdown water level."""

    TENSION_CRACK = auto()
    """Upper discontinuity where tensile strength is assumed zero."""

    BLOCK_SEARCH_OBJECT = auto()
    """Block Search object (window / line / point / polyline) used to
    generate non-circular slip-surface vertices in a Block Search."""

    WEAK_LAYER = auto()
    """Polyline carrying a strength of its own — a joint or an interface
    the slip surface travels ALONG instead of crossing.

    v0.1.121. Unlike every other member of this enum it is not model
    geometry: it is never intersected with other boundaries and it never
    defines a material region. Its strength comes from the material named
    by ``Boundary.material_id``.
    """

    @property
    def display_name(self) -> str:
        mapping = {
            BoundaryType.EXTERNAL: "External Boundary",
            BoundaryType.MATERIAL: "Material Boundary",
            BoundaryType.WATER_TABLE: "Water Table",
            BoundaryType.PIEZOMETRIC: "Piezometric Line",
            BoundaryType.DRAWDOWN: "Drawdown Line",
            BoundaryType.TENSION_CRACK: "Tension Crack",
            BoundaryType.BLOCK_SEARCH_OBJECT: "Block Search Object",
            BoundaryType.WEAK_LAYER: "Weak Layer",
        }
        return mapping[self]

    @property
    def default_color(self) -> str:
        """Default hex color used for rendering (customizable per project)."""
        mapping = {
            BoundaryType.EXTERNAL: "#2c2c2c",
            BoundaryType.MATERIAL: "#8b4513",
            BoundaryType.WATER_TABLE: "#1e90ff",
            BoundaryType.PIEZOMETRIC: "#4169e1",
            BoundaryType.DRAWDOWN: "#00bfff",
            BoundaryType.TENSION_CRACK: "#dc143c",
            BoundaryType.BLOCK_SEARCH_OBJECT: "#9932cc",
            BoundaryType.WEAK_LAYER: "#6a5acd",
        }
        return mapping[self]
