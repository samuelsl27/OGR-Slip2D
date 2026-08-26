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


def _envelope_to_dict(env) -> Optional[dict]:
    """Serialise a drawdown envelope, tagged by which of the two it is."""
    if env is None:
        return None
    from .drawdown_envelopes import Kc1Envelope, REnvelope

    if isinstance(env, REnvelope):
        return {"kind": "r", "c_r": env.c_r, "phi_r_deg": env.phi_r_deg}
    if isinstance(env, Kc1Envelope):
        return {"kind": "kc1", "d": env.d, "psi_deg": env.psi_deg}
    return None


def _envelope_from_dict(d) -> Optional[object]:
    if not d:
        return None
    from .drawdown_envelopes import Kc1Envelope, REnvelope

    kind = d.get("kind")
    if kind == "r":
        return REnvelope(c_r=float(d.get("c_r", 0.0)),
                         phi_r_deg=float(d.get("phi_r_deg", 0.0)))
    if kind == "kc1":
        return Kc1Envelope(d=float(d.get("d", 0.0)),
                           psi_deg=float(d.get("psi_deg", 0.0)))
    return None


@dataclass
class Material:
    """A geotechnical material.

    Attributes:
        name:           user-visible identifier
        strength:       constitutive model instance (plugin)
        unit_weight:    dry/bulk unit weight γ [kN/m³]
        sat_unit_weight: saturated unit weight γsat [kN/m³]
        use_sat_unit_weight: whether γsat is used at all (see below)
        pore_pressure:  pore-pressure model
        ru:             Ru coefficient (if pore_pressure == RU_COEFFICIENT)
        constant_u:     constant pore pressure [kPa] (if CONSTANT)
        water_surface_id: boundary id of associated water-table / piezo line
        hu:             Hu coefficient (None → project default)
        auto_hu:        derive Hu from the water-surface slope
        undrained_behaviour: material develops excess pore pressure
        b_bar:          Skempton's B̄ (only if undrained_behaviour)
        weight_creates_excess: this material's weight loads the ones below
        use_grid:       whether a water-pressure grid governs this material
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
    # v0.1.60 — Distinguishing the unit weight above and below the water
    # table is an OPTION, not something always in force: it only means
    # anything when a water table exists to separate the two zones. Kept
    # last (before ``id``) so the positional order of the older fields is
    # unchanged. Defaults to False for new materials; ``from_dict`` turns
    # it on for legacy projects, which always wrote ``sat_unit_weight``,
    # so that reopening an old file cannot change its factor of safety.
    use_sat_unit_weight: bool = False
    # v0.1.62 — Water parameters that USED to be read with ``getattr`` from
    # attributes no dataclass declared. They existed only if someone
    # injected them at runtime and were silently dropped by ``to_dict``,
    # so a project that set them lost them on save. Declaring them is the
    # whole fix; see ``ogr_core.hydraulic.pore_pressure``.
    #   hu      : Hu coefficient ∈ [0,1]; None → use the project default.
    #             u = γw · Hu · h, with h the vertical distance up to the
    #             assigned water surface.
    #   auto_hu : compute Hu = cos²(α) from the water-surface slope
    #             instead, α being its inclination above the point.
    hu: Optional[float] = None
    auto_hu: bool = False
    # v0.1.62 — Rapid-drawdown / excess pore pressure parameters.
    # ``b_bar`` is Skempton's B̄: Δu = B̄ · Δσv. It only applies to a
    # material that behaves undrained, hence the explicit flag rather than
    # a magic B̄ = 0. The pair defaults to "freely draining, no excess",
    # which is the conservative reading and the reference default; the
    # previous implicit default of B̄ = 1 is restored for legacy projects
    # by ``Project.from_dict`` so that reopening one cannot change its FoS.
    undrained_behaviour: bool = False
    b_bar: float = 0.0
    # v0.1.75 — whether this material's own weight counts towards the
    # change in vertical stress that generates excess pore pressure in
    # the materials BENEATH it. It says nothing about whether this
    # material develops excess pore pressure itself: that is ``b_bar``.
    # An embankment built over a clay foundation typically has this on
    # and B̄ = 0 — it loads the clay without generating excess within
    # itself, which is exactly the case the reference's tutorial walks
    # through.
    weight_creates_excess: bool = False
    # v0.1.67 — undrained envelope for the multi-stage rapid-drawdown
    # procedures, from IC-U triaxial tests. Deliberately NOT a
    # ``StrengthModel`` in the registry: those are selectable as the
    # material's main envelope, and neither of these two is usable as a
    # drained one. A material keeps its effective ``strength`` and gains
    # this alongside it. ``REnvelope`` or ``Kc1Envelope``; either is
    # converted to whichever the chosen procedure needs.
    drawdown_envelope: Optional[object] = None
    # v0.1.72 — Grid On/Off. When the project groundwater method is one of
    # the water-pressure-grid ones, the grid governs every material by
    # default; this is the per-material way out of that default, and the
    # reference exposes it as exactly that — a switch in Water Parameters.
    # Defaults to True so no existing project changes: a file written
    # before the field existed behaves as it always did, with the grid on.
    use_grid: bool = True
    # v0.1.126 — boundary id of the ANISOTROPIC SURFACE that orients this
    # material's bedding, or None for the single global angle its strength
    # model already carries. Only the three anisotropic models read it
    # (Anisotropic Linear, Snowden Modified, Generalized Anisotropic); for
    # anything else it is inert, and that is deliberate rather than an
    # oversight: assigning a fold direction to a Mohr-Coulomb material
    # would be a setting that decides nothing, and the dialog does not
    # offer it.
    #
    # It lives on the MATERIAL and not on the boundary because the link
    # runs that way: several materials may read the same surface, and the
    # surface knows nothing about who reads it.
    anisotropic_surface_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    def gamma_at(self, below_water: bool) -> float:
        """Return the unit weight to use at a given point.

        Uses the saturated unit weight if the point lies below the water
        surface AND the material opts into it; otherwise the bulk/dry
        weight. Note that ``sat_unit_weight`` is the saturated BULK unit
        weight, not the buoyant (submerged) one, so it should always be
        greater than ``unit_weight``.
        """
        if below_water and self.use_sat_unit_weight:
            return self.sat_unit_weight
        return self.unit_weight

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "strength": self.strength.to_dict(),
            "unit_weight": self.unit_weight,
            "sat_unit_weight": self.sat_unit_weight,
            "use_sat_unit_weight": self.use_sat_unit_weight,
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
            "hu": self.hu,
            "auto_hu": self.auto_hu,
            "undrained_behaviour": self.undrained_behaviour,
            "b_bar": self.b_bar,
            "drawdown_envelope": _envelope_to_dict(self.drawdown_envelope),
            "use_grid": self.use_grid,
            "weight_creates_excess": self.weight_creates_excess,
            "anisotropic_surface_id": self.anisotropic_surface_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        m = cls(
            name=data["name"],
            strength=StrengthModel.from_dict(data["strength"]),
            unit_weight=data.get("unit_weight", 20.0),
            sat_unit_weight=data.get("sat_unit_weight", 21.0),
            # v0.1.60 — Files written before the option existed always
            # carried a ``sat_unit_weight`` and always used it below the
            # water table. Defaulting to True in that case keeps every
            # saved project numerically identical when reopened; only
            # files that predate the key AND lack a saturated weight fall
            # back to the new (opt-in) default.
            use_sat_unit_weight=bool(data.get(
                "use_sat_unit_weight", "sat_unit_weight" in data)),
            pore_pressure=PorePressureType(data.get("pore_pressure", "none")),
            ru=data.get("ru", 0.0),
            constant_u=data.get("constant_u", 0.0),
            water_surface_id=data.get("water_surface_id"),
            color=data.get("color", "#d4a373"),
            hatch=data.get("hatch"),
            phi_b=data.get("phi_b", 0.0),
            air_entry_value=data.get("air_entry_value", 0.0),
            hu=data.get("hu"),
            auto_hu=bool(data.get("auto_hu", False)),
            undrained_behaviour=bool(data.get("undrained_behaviour", False)),
            b_bar=float(data.get("b_bar", 0.0)),
            anisotropic_surface_id=data.get("anisotropic_surface_id"),
            drawdown_envelope=_envelope_from_dict(
                data.get("drawdown_envelope")),
            # v0.1.72 — absent in files written before the switch existed,
            # and those all behaved as "grid on"; True is the only default
            # that leaves their pore pressures untouched.
            use_grid=bool(data.get("use_grid", True)),
            # v0.1.75 — absent in older files, and off is the
            # conservative reading: a material that was never asked to
            # load anything keeps not loading it.
            weight_creates_excess=bool(
                data.get("weight_creates_excess", False)),
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
        ]
        # Only show γsat when it can actually affect the analysis, so the
        # tooltip never advertises a number the calculation ignores.
        if self.use_sat_unit_weight:
            rows.append(f"γ<sub>sat</sub> = {self.sat_unit_weight:g} kN/m³")
        for k, v in self.strength.params.items():
            unit = self.strength.PARAMETERS[k][1]
            rows.append(f"{k} = {v:g} {unit}")
        rows.append(f"u-model: {self.pore_pressure.value}")
        return "<br>".join(rows)
