# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Material: a named bundle of physical properties.

A Material couples a :class:`StrengthModel` with the unit weights, pore-pressure
configuration, and visual rendering attributes. This is what the user
"paints" onto regions of the model.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

from .strength_model import StrengthModel


class PorePressureType(Enum):
    """How pore pressure u is computed for a point inside this material."""

    NONE = "none"
    WATER_TABLE = "water_table"
    PIEZO_LINE = "piezometric"
    RU_COEFFICIENT = "ru"
    CONSTANT = "constant"
    FEM_SEEPAGE = "fem"  # coupled from OGR FEM2D result


@dataclass
class Material:
    """A geotechnical material.

    Attributes:
        name:           user-visible identifier
        strength:       constitutive model instance (plugin)
        unit_weight:    dry/bulk unit weight γ [kN/m³]
        sat_unit_weight: saturated unit weight γsat [kN/m³]
        pore_pressure:  pore-pressure model
        ru:             Ru coefficient (if pore_pressure == RU_COEFFICIENT)
        constant_u:     constant pore pressure [kPa] (if CONSTANT)
        water_surface_id: boundary id of associated water-table / piezo line
        color:          hex color for canvas rendering
        hatch:          optional hatch-pattern identifier
    """

    name: str
    strength: StrengthModel
    unit_weight: float = 20.0
    sat_unit_weight: float = 21.0
    pore_pressure: PorePressureType = PorePressureType.NONE
    ru: float = 0.0
    constant_u: float = 0.0
    water_surface_id: Optional[str] = None
    color: str = "#d4a373"
    hatch: Optional[str] = None
    # v0.1.26 — hydraulic (permeability) properties for the seepage
    # analysis. Independent of the strength model, mirroring the
    # reference where hydraulic properties are a separate dialog on the
    # same material list.
    hydraulic: Optional["HydraulicProperties"] = None
    # v0.1.28 — Unsaturated shear strength (extended Mohr-Coulomb,
    # Fredlund et al. 1978). Only meaningful when the pore pressures come
    # from a seepage analysis and can be negative.
    #   phi_b            : unsaturated shear strength angle [deg]
    #   air_entry_value  : matric suction below which the SATURATED phi'
    #                      still governs (bilinear envelope)
    # Both default to 0, which makes matric suction contribute NOTHING to
    # strength -- the conservative choice, and the reference default.
    phi_b: float = 0.0
    air_entry_value: float = 0.0
    id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    def gamma_at(self, below_water: bool) -> float:
        """Return the unit weight to use at a given point.

        Uses saturated unit weight if the slice base lies below the water
        surface; otherwise uses bulk/dry weight.
        """
        return self.sat_unit_weight if below_water else self.unit_weight

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "strength": self.strength.to_dict(),
            "unit_weight": self.unit_weight,
            "sat_unit_weight": self.sat_unit_weight,
            "pore_pressure": self.pore_pressure.value,
            "ru": self.ru,
            "constant_u": self.constant_u,
            "water_surface_id": self.water_surface_id,
            "color": self.color,
            "hatch": self.hatch,
            "hydraulic": (self.hydraulic.to_dict()
                          if self.hydraulic is not None else None),
            "phi_b": self.phi_b,
            "air_entry_value": self.air_entry_value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        m = cls(
            name=data["name"],
            strength=StrengthModel.from_dict(data["strength"]),
            unit_weight=data.get("unit_weight", 20.0),
            sat_unit_weight=data.get("sat_unit_weight", 21.0),
            pore_pressure=PorePressureType(data.get("pore_pressure", "none")),
            ru=data.get("ru", 0.0),
            constant_u=data.get("constant_u", 0.0),
            water_surface_id=data.get("water_surface_id"),
            color=data.get("color", "#d4a373"),
            hatch=data.get("hatch"),
            phi_b=data.get("phi_b", 0.0),
            air_entry_value=data.get("air_entry_value", 0.0),
        )
        if "id" in data:
            m.id = data["id"]
        # v0.1.26 — hydraulic properties (seepage analysis)
        hyd = data.get("hydraulic")
        if hyd:
            from ..hydraulic.hydraulic_properties import HydraulicProperties
            m.hydraulic = HydraulicProperties.from_dict(hyd)
        return m

    # ------------------------------------------------------------------
    def tooltip_html(self) -> str:
        """Rich tooltip rendered when the user hovers over a region in the GUI."""
        color_swatch = (
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{self.color};border:1px solid #000;"></span>'
        )
        rows = [
            f"<b>{color_swatch}&nbsp;{self.name}</b>",
            f"<i>{self.strength.DISPLAY_NAME}</i>",
            "<hr>",
            f"γ = {self.unit_weight:g} kN/m³",
            f"γ<sub>sat</sub> = {self.sat_unit_weight:g} kN/m³",
        ]
        for k, v in self.strength.params.items():
            unit = self.strength.PARAMETERS[k][1]
            rows.append(f"{k} = {v:g} {unit}")
        rows.append(f"u-model: {self.pore_pressure.value}")
        return "<br>".join(rows)
