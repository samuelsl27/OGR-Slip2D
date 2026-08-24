# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Structural support (reinforcement) plugin system.

v0.1.14 — complete rewrite aligned with the Slide2/Slide3 documentation.
All support types are computed in **kN per unit width of slope** (kN/m),
consistent with the slice-based LEM convention.

Implemented support types (mirroring Slide):

    1. End Anchored                   — constant force, anchor at tail
    2. Grouted Tieback                — 3 failure modes: tensile / pullout / stripping
    3. Grouted Tieback with Friction  — same, pullout governed by τ_int = c + σ·tanφ
    4. Soil Nail                      — Grouted Tieback with bond = 100%
    5. Pile / Micropile               — constant shear force across slip
    6. Geosynthetic                   — tensile + pullout (interface)
    7. User-Defined                   — capacity-vs-distance table

Every support computes a **force diagram** along its length: at each
point along the bolt axis, the available support force is the MINIMUM
of all applicable failure-mode capacities. When the slip surface
intersects the bolt at distance ``d`` from the head, the available
force is ``force_at(d, total_length)`` (per unit width of slope).

Force application (Slide convention):
    - **Active** (Method A in Duncan & Wright 2005): the support force
      acts BEFORE displacement (post-tensioned anchors, ties). Enters
      the FoS equation by REDUCING the driving moment.
    - **Passive** (Method B): the support force develops only AFTER
      displacement (untensioned dowels, piles). Enters the FoS by
      INCREASING the resisting moment, divided by F in the iteration.

Force orientation at slip-surface intersection (Slide convention):
    - tangent_to_slip — force aligned with slip surface
    - parallel_to_support — force along bolt axis (default for tieback/end)
    - bisector — bisects the two above (default for soil nail)
    - horizontal — only used for piles
    - perpendicular_to_pile — pile-shear mode
    - user_defined — arbitrary angle from positive horizontal

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Optional
from uuid import uuid4


# ======================================================================
# Enums
# ======================================================================
class ForceApplication(Enum):
    """How the support force enters the LEM equilibrium equations.

    Following Duncan & Wright (2005) Chapter 8:
        - ACTIVE  (Method A): support reduces the DRIVING force
        - PASSIVE (Method B): support increases the RESISTING force,
          divided by F in the iteration (more conservative)
    """
    ACTIVE = "active"
    PASSIVE = "passive"


class ForceOrientation(Enum):
    """Direction of the support force at the slip-surface intersection."""
    TANGENT_TO_SLIP = "tangent_to_slip"
    PARALLEL_TO_SUPPORT = "parallel_to_support"
    BISECTOR = "bisector"
    HORIZONTAL = "horizontal"
    PERPENDICULAR_TO_PILE = "perpendicular_to_pile"
    USER_DEFINED = "user_defined"


# ======================================================================
# Base class & registry
# ======================================================================
class SupportType(ABC):
    """Base class for all support property plugins.

    Subclasses must override:
        - PARAMETERS: dict mapping param_name → (default, unit, description)
        - force_at(distance_from_head, total_length) → kN/m
        - to_dict / from_dict
    """

    TYPE_ID: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    DESCRIPTION: ClassVar[str] = ""
    DEFAULT_ORIENTATION: ClassVar[ForceOrientation] = (
        ForceOrientation.TANGENT_TO_SLIP
    )
    DEFAULT_APPLICATION: ClassVar[ForceApplication] = (
        ForceApplication.ACTIVE
    )
    # GUI declaration: {param_name: (default_value, unit_label, description)}
    PARAMETERS: ClassVar[dict] = {}
    # GUI tabs: groups parameters into tabs e.g. {"General": ["spacing"],
    #           "Pullout": ["bond_strength", "adhesion"]}
    PARAMETER_TABS: ClassVar[dict] = {}
    # Whether this type supports shear capacity (extra perpendicular force)
    SUPPORTS_SHEAR: ClassVar[bool] = False

    @abstractmethod
    def force_at(
        self, distance_from_head: float, total_length: float,
    ) -> float:
        """Available support force at the slip intersection, kN/m of slope.

        Returns the MINIMUM of all applicable failure-mode capacities
        at the given distance from the head end.
        """

    def shear_at(
        self, distance_from_head: float, total_length: float,
    ) -> float:
        """Optional perpendicular shear force at the intersection.

        Returns 0 by default. Soil Nail and Grouted Tieback override
        when the ``shear_capacity`` parameter is enabled.
        """
        return 0.0

    @abstractmethod
    def to_dict(self) -> dict: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "SupportType": ...

    # ----- v0.1.14 — UI metadata stored as private attrs ------------
    def _extras_dict(self) -> dict:
        """Return the optional GUI-side metadata stashed on the
        SupportType (display name, color, force application, etc.)
        in JSON-serialisable form."""
        out: dict = {}
        if hasattr(self, "_display_name"):
            out["_display_name"] = getattr(self, "_display_name")
        if hasattr(self, "_color"):
            out["_color"] = getattr(self, "_color")
        if hasattr(self, "_user_angle_deg"):
            out["_user_angle_deg"] = float(getattr(self, "_user_angle_deg"))
        fa = getattr(self, "_force_application", None)
        if fa is not None:
            out["_force_application"] = fa.value if hasattr(fa, "value") else str(fa)
        fo = getattr(self, "_orientation", None)
        if fo is not None:
            out["_orientation"] = fo.value if hasattr(fo, "value") else str(fo)
        return out

    def _apply_extras(self, data: dict) -> None:
        """Restore GUI-side metadata from a dict produced by
        :meth:`_extras_dict`."""
        if "_display_name" in data:
            self._display_name = data["_display_name"]
        if "_color" in data:
            self._color = data["_color"]
        if "_user_angle_deg" in data:
            self._user_angle_deg = data["_user_angle_deg"]
        if "_force_application" in data:
            try:
                self._force_application = ForceApplication(data["_force_application"])
            except (ValueError, KeyError):
                pass
        if "_orientation" in data:
            try:
                self._orientation = ForceOrientation(data["_orientation"])
            except (ValueError, KeyError):
                pass

    def axial_capacity(
        self, length_along: float, total_length: float,
    ) -> float:
        """Back-compat alias used by older v0.1.13 callers."""
        return self.force_at(length_along, total_length)


_SUPPORT_REGISTRY: dict[str, type[SupportType]] = {}


def register_support(cls: type[SupportType]) -> type[SupportType]:
    if not cls.TYPE_ID:
        raise ValueError(f"{cls.__name__} has no TYPE_ID")
    _SUPPORT_REGISTRY[cls.TYPE_ID] = cls
    return cls


def support_registry() -> dict[str, type[SupportType]]:
    return dict(_SUPPORT_REGISTRY)


def support_from_dict(data: dict) -> SupportType:
    tid = data["type_id"]
    if tid not in _SUPPORT_REGISTRY:
        raise KeyError(f"Unknown support type: {tid}")
    return _SUPPORT_REGISTRY[tid].from_dict(data)


def _default_orientation(type_id: str) -> ForceOrientation:
    """``DEFAULT_ORIENTATION`` of a support type, by id.

    An unknown id falls back to TANGENT_TO_SLIP rather than raising: a
    project may carry a support whose plugin is not loaded, and losing
    the whole model over a default is worse than analysing it with one.
    """
    cls = _SUPPORT_REGISTRY.get(type_id)
    return (cls.DEFAULT_ORIENTATION if cls is not None
            else ForceOrientation.TANGENT_TO_SLIP)


def _default_application(type_id: str) -> ForceApplication:
    """``DEFAULT_APPLICATION`` of a support type, by id. See above."""
    cls = _SUPPORT_REGISTRY.get(type_id)
    return (cls.DEFAULT_APPLICATION if cls is not None
            else ForceApplication.ACTIVE)


# ======================================================================
# 1. End Anchored
# ======================================================================
@register_support
@dataclass
class EndAnchored(SupportType):
    """End Anchored bolt — mechanically anchored at the tail end only.

    Slide: "the load applied to the sliding mass will be CONSTANT,
    regardless of where a slip surface intersects the length of the
    support. The applied load, PER UNIT WIDTH OF SLOPE, is simply
    equal to the Anchor Capacity divided by the Out of Plane Spacing."
    """
    TYPE_ID: ClassVar[str] = "end_anchored"
    DISPLAY_NAME: ClassVar[str] = "End Anchored"
    DESCRIPTION: ClassVar[str] = (
        "Mechanically end-anchored rock bolt or deadman anchor. The "
        "force is constant along the bolt — equal to the anchor "
        "capacity divided by out-of-plane spacing."
    )
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    PARAMETERS: ClassVar[dict] = {
        "anchor_capacity": (200.0, "kN",
            "Maximum load an individual anchor can sustain before "
            "failure (pullout, tensile or plate, whichever is lowest)"),
        "out_of_plane_spacing": (1.5, "m",
            "Out-of-plane bolt spacing (centre-to-centre)"),
    }

    anchor_capacity: float = 200.0       # kN per anchor
    out_of_plane_spacing: float = 1.5    # m

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        if self.out_of_plane_spacing <= 0:
            return 0.0
        # Constant force, regardless of slip-surface position
        return self.anchor_capacity / self.out_of_plane_spacing

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EndAnchored":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 2. Grouted Tieback
# ======================================================================
@register_support
@dataclass
class GroutedTieback(SupportType):
    """Grouted Tieback — tensioned cable/bar with grouted bond zone.

    Implements the three Slide failure modes:

    **Pullout**  F_p = (bond_strength · L_o) / spacing
                  L_o = length of bond zone BEHIND the slip surface

    **Tensile**  F_t = tensile_capacity / spacing
                  tendon ultimate strength

    **Stripping** F_s = (plate_capacity + bond_strength · L_i) / spacing
                   L_i = length of bond zone BETWEEN head and slip
                   (only relevant if plate_capacity < tensile_capacity)

    The available force at any intersection is the MINIMUM of the
    three failure modes that apply at that location.
    """
    TYPE_ID: ClassVar[str] = "grouted_tieback"
    DISPLAY_NAME: ClassVar[str] = "Grouted Tieback"
    DESCRIPTION: ClassVar[str] = (
        "Tensioned tieback with grouted bond zone. Computes 3 failure "
        "modes: pullout (bond), tensile (tendon), stripping (plate)."
    )
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    SUPPORTS_SHEAR: ClassVar[bool] = True
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (600.0, "kN",
            "Ultimate tensile capacity of the tendon"),
        "plate_capacity": (300.0, "kN",
            "Capacity of the plate/wedge assembly at the head. If "
            "≥ tensile_capacity, stripping cannot occur."),
        "bond_strength": (150.0, "kN/m",
            "Pullout strength per unit length of bond zone"),
        "bond_length_percent": (30.0, "%",
            "Length of bonded zone as % of total bolt length "
            "(0–100%, located at the tail end)"),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane spacing of tiebacks"),
        "shear_capacity": (0.0, "kN",
            "Optional perpendicular shear capacity (0 = disabled)"),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile / Plate": ["tensile_capacity", "plate_capacity",
                            "shear_capacity"],
        "Pullout": ["bond_strength", "bond_length_percent"],
        "Geometry": ["out_of_plane_spacing"],
    }

    tensile_capacity: float = 600.0
    plate_capacity: float = 300.0
    bond_strength: float = 150.0
    bond_length_percent: float = 30.0
    out_of_plane_spacing: float = 2.0
    shear_capacity: float = 0.0

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return 0.0
        bond_len = total_length * self.bond_length_percent / 100.0
        free_len = total_length - bond_len
        x = max(0.0, min(distance_from_head, total_length))

        # L_o: length of bond BEHIND the slip (towards tail)
        if x <= free_len:
            L_o = bond_len
        else:
            L_o = max(0.0, total_length - x)

        # L_i: length of bond AHEAD of the slip (towards head)
        if x <= free_len:
            L_i = 0.0
        else:
            L_i = x - free_len

        f_pullout = (self.bond_strength * L_o) / s
        f_tensile = self.tensile_capacity / s
        # Stripping is plate + however much bond is on the head side
        f_stripping = (self.plate_capacity + self.bond_strength * L_i) / s

        return max(0.0, min(f_pullout, f_tensile, f_stripping))

    def shear_at(self, distance_from_head: float, total_length: float) -> float:
        if self.out_of_plane_spacing <= 0:
            return 0.0
        return max(0.0, self.shear_capacity / self.out_of_plane_spacing)

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GroutedTieback":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 3. Grouted Tieback with Friction
# ======================================================================
@register_support
@dataclass
class GroutedTiebackFriction(SupportType):
    """Grouted Tieback whose pullout depends on σ' via Mohr-Coulomb.

    τ_bond = adhesion + σ'_n · tan(φ_bond)

    The pullout force across the bond zone is the integral of τ_bond
    over the bond surface area:

        F_pullout = ∫_bond τ_bond · (π · D_grout) dL  / spacing

    Because σ' depends on depth, the integral requires knowledge of
    the average σ' along the bond. As a first approximation we use
    the user-provided ``adhesion`` as the average bond shear stress
    (i.e. the φ_bond contribution is folded into adhesion). For
    depth-dependent behaviour, future versions can integrate σ' from
    the slope geometry.

    Bond surface area per metre of bond:
        A_bond/L = π · D_grout
    """
    TYPE_ID: ClassVar[str] = "grouted_tieback_friction"
    DISPLAY_NAME: ClassVar[str] = "Grouted Tieback with Friction"
    DESCRIPTION: ClassVar[str] = (
        "Grouted tieback whose pullout strength is governed by a "
        "Mohr-Coulomb law (adhesion + σ·tanφ) on the grout/soil "
        "interface. Bond surface area is computed from the grout "
        "diameter."
    )
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    SUPPORTS_SHEAR: ClassVar[bool] = True
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (600.0, "kN",
            "Ultimate tensile capacity of the tendon"),
        "plate_capacity": (300.0, "kN",
            "Plate/wedge assembly capacity"),
        "bond_length_percent": (30.0, "%",
            "Length of bonded zone as % of total length"),
        "grout_diameter": (0.15, "m",
            "Outer diameter of the grout annulus (used for the "
            "bond surface area)"),
        "adhesion": (60.0, "kPa",
            "Adhesion (cohesion) at the grout/soil interface"),
        "friction_angle_bond": (25.0, "deg",
            "Friction angle at the grout/soil interface"),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane spacing of tiebacks"),
        "shear_capacity": (0.0, "kN", "Optional shear capacity"),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile / Plate": ["tensile_capacity", "plate_capacity",
                            "shear_capacity"],
        "Pullout (Friction)": ["adhesion", "friction_angle_bond",
                               "grout_diameter", "bond_length_percent"],
        "Geometry": ["out_of_plane_spacing"],
    }

    tensile_capacity: float = 600.0
    plate_capacity: float = 300.0
    bond_length_percent: float = 30.0
    grout_diameter: float = 0.15
    adhesion: float = 60.0
    friction_angle_bond: float = 25.0
    out_of_plane_spacing: float = 2.0
    shear_capacity: float = 0.0

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return 0.0
        bond_len = total_length * self.bond_length_percent / 100.0
        free_len = total_length - bond_len
        x = max(0.0, min(distance_from_head, total_length))

        if x <= free_len:
            L_o = bond_len
            L_i = 0.0
        else:
            L_o = max(0.0, total_length - x)
            L_i = x - free_len

        # Bond perimeter
        perim = math.pi * self.grout_diameter
        # Effective shear stress on bond — using adhesion as
        # depth-averaged σ-contribution (first-order). The friction
        # angle contributes via the user-tuned adhesion.
        tau_bond = self.adhesion  # kPa, → kN/m²
        f_pullout = (tau_bond * perim * L_o) / s
        f_tensile = self.tensile_capacity / s
        f_stripping = (self.plate_capacity
                       + tau_bond * perim * L_i) / s
        return max(0.0, min(f_pullout, f_tensile, f_stripping))

    def shear_at(self, distance_from_head: float, total_length: float) -> float:
        if self.out_of_plane_spacing <= 0:
            return 0.0
        return max(0.0, self.shear_capacity / self.out_of_plane_spacing)

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GroutedTiebackFriction":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 4. Soil Nail (= Grouted Tieback with 100% bond)
# ======================================================================
@register_support
@dataclass
class SoilNail(SupportType):
    """Soil Nail — fully-bonded grouted reinforcement (no free length).

    Slide: "The Soil Nail support type is equivalent to Grouted
    Tieback support with Bond Length = 100%." The three failure modes
    (tensile, pullout, stripping) are computed with the bond running
    the entire length.

    Force diagram:
        Pullout:   F_p(x) = bond_strength · (L - x) / spacing
        Stripping: F_s(x) = (plate_capacity + bond_strength · x) / spacing
        Tensile:   F_t    = tensile_capacity / spacing  (constant)
    """
    TYPE_ID: ClassVar[str] = "soil_nail"
    DISPLAY_NAME: ClassVar[str] = "Soil Nail"
    DESCRIPTION: ClassVar[str] = (
        "Fully-bonded soil nail (no free length). Computes 3 failure "
        "modes along the full length: tensile, pullout, stripping."
    )
    # v0.1.113 — both corrected. The reference's own page for this
    # support type states that the applied force is ALWAYS parallel to
    # the nail, and that the default force application is Passive
    # "since there is normally no initial loading or tensioning of a
    # soil nail". This project had BISECTOR + ACTIVE, which is what the
    # user got out of the box. It is an interface convention, not a
    # published formula, so it is cited as such and not attributed to an
    # author. Confirmed independently by the verification problems that
    # use soil nails: both declare Passive in their own tables.
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.PASSIVE
    SUPPORTS_SHEAR: ClassVar[bool] = True
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (100.0, "kN",
            "Tensile capacity of the nail (tendon ultimate)"),
        "plate_capacity": (50.0, "kN",
            "Capacity of the head plate. If 0, stripping force can "
            "still be developed from the bond but only on the head side."),
        "bond_strength": (30.0, "kN/m",
            "Pullout strength per unit length of nail"),
        "out_of_plane_spacing": (1.5, "m",
            "Out-of-plane spacing of soil nails"),
        "shear_capacity": (0.0, "kN",
            "Optional perpendicular shear capacity (dowel action). 0 "
            "= disabled."),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile / Plate": ["tensile_capacity", "plate_capacity",
                            "shear_capacity"],
        "Pullout": ["bond_strength"],
        "Geometry": ["out_of_plane_spacing"],
    }

    tensile_capacity: float = 100.0
    plate_capacity: float = 50.0
    bond_strength: float = 30.0
    out_of_plane_spacing: float = 1.5
    shear_capacity: float = 0.0

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return 0.0
        x = max(0.0, min(distance_from_head, total_length))
        L_o = max(0.0, total_length - x)  # bond behind slip
        L_i = x                            # bond ahead of slip
        f_pullout = (self.bond_strength * L_o) / s
        f_tensile = self.tensile_capacity / s
        f_stripping = (self.plate_capacity + self.bond_strength * L_i) / s
        return max(0.0, min(f_pullout, f_tensile, f_stripping))

    def shear_at(self, distance_from_head: float, total_length: float) -> float:
        if self.out_of_plane_spacing <= 0:
            return 0.0
        return max(0.0, self.shear_capacity / self.out_of_plane_spacing)

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SoilNail":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 5. Pile / Micropile
# ======================================================================
@register_support
@dataclass
class PileMicropile(SupportType):
    """Pile / Micropile — constant transverse shear force.

    Slide: "A pile will apply a constant force to a slip surface,
    regardless of where it is intersected. The applied load PER UNIT
    WIDTH OF SLOPE is simply equal to the Pile Shear Strength
    divided by the Out of Plane Spacing."

    The pile-shear strength is the user-provided force the pile
    cross-section can resist transversely (computed externally from
    bending / shear capacity of the structural member).
    """
    TYPE_ID: ClassVar[str] = "pile_micropile"
    DISPLAY_NAME: ClassVar[str] = "Pile / Micropile"
    DESCRIPTION: ClassVar[str] = (
        "Pile or micropile providing transverse shear resistance. "
        "The applied force is constant along the pile = pile_shear "
        "÷ spacing."
    )
    # v0.1.113 — was PERPENDICULAR_TO_PILE. The reference's default is
    # TANGENTIAL to the slip surface, and it gives the mechanical reason:
    # a pile fails in shear THROUGH its cross-section on the slip plane,
    # so the force it mobilises acts in that plane. Perpendicular-to-pile
    # exists as an option for a force independent of the surface, but it
    # is not the default.
    DEFAULT_ORIENTATION = ForceOrientation.TANGENT_TO_SLIP
    DEFAULT_APPLICATION = ForceApplication.PASSIVE
    PARAMETERS: ClassVar[dict] = {
        "pile_shear_strength": (100.0, "kN",
            "Lateral shear strength of the pile cross-section"),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane spacing of piles"),
    }

    pile_shear_strength: float = 100.0
    out_of_plane_spacing: float = 2.0

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        s = self.out_of_plane_spacing
        if s <= 0:
            return 0.0
        return self.pile_shear_strength / s

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PileMicropile":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 6. Geosynthetic / Geotextile
# ======================================================================
@register_support
@dataclass
class Geosynthetic(SupportType):
    """Geosynthetic — sheet reinforcement (geotextile, geogrid).

    Slide: "The Pullout Strength options for the Grouted Tieback with
    Friction support type are the same as described for the
    Geosynthetic support type." For a geosynthetic, pullout occurs
    along BOTH surfaces of the sheet:

        F_pullout(x) = 2 · τ_int · L_emb(x) / spacing

    where τ_int = c_int + σ'_v · tan(φ_int), and L_emb(x) is the
    shorter side (towards head or tail) — whichever is being pulled.
    spacing = 1.0 m for geosynthetics (force per unit width of slope).

    Alternative input modes (per Slide):
        - Adhesion & Friction Angle (Mohr-Coulomb)
        - Coefficient of Interaction (Ci) × soil strength
        - Friction Factor (F* α)

    We expose all three via ``pullout_mode``.
    """
    TYPE_ID: ClassVar[str] = "geosynthetic"
    DISPLAY_NAME: ClassVar[str] = "Geosynthetic"
    DESCRIPTION: ClassVar[str] = (
        "Geotextile or geogrid sheet reinforcement. Computes tensile "
        "and pullout (interface) failure modes. Pullout acts on BOTH "
        "surfaces of the sheet."
    )
    # v0.1.113 — application was ACTIVE. A sheet is normally laid
    # untensioned, so the reference defaults it to Passive; the
    # orientation is genuinely the user's choice for this type, and
    # parallel is the one that matches the sheet's own axis.
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.PASSIVE
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (50.0, "kN/m",
            "Tensile capacity of the sheet per metre of slope width"),
        "pullout_mode": ("mohr_coulomb", "-",
            "Pullout strength model: mohr_coulomb | coefficient | "
            "friction_factor"),
        "adhesion": (0.0, "kPa",
            "Interface adhesion (only used in Mohr-Coulomb mode)"),
        "friction_angle_interface": (25.0, "deg",
            "Interface friction angle (Mohr-Coulomb mode)"),
        "coefficient_of_interaction": (0.8, "-",
            "Ci: τ_int = Ci · τ_soil (used in coefficient mode)"),
        "friction_factor": (0.6, "-",
            "F·α: τ_int = (F·α) · σ'_v (used in friction-factor mode)"),
        "reference_elevation": (0.0, "m",
            "Reference elevation for computing σ'_v (vertical stress)"),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile": ["tensile_capacity"],
        "Pullout & Stripping": ["pullout_mode", "adhesion",
                                "friction_angle_interface",
                                "coefficient_of_interaction",
                                "friction_factor",
                                "reference_elevation"],
    }

    tensile_capacity: float = 50.0
    pullout_mode: str = "mohr_coulomb"
    adhesion: float = 0.0
    friction_angle_interface: float = 25.0
    coefficient_of_interaction: float = 0.8
    friction_factor: float = 0.6
    reference_elevation: float = 0.0

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        if total_length <= 0:
            return 0.0
        # Pullout length: shorter side of the geosynthetic measured
        # from the intersection point
        L_a = max(0.0, distance_from_head)            # ahead of slip
        L_b = max(0.0, total_length - distance_from_head)  # behind slip
        L_pull = min(L_a, L_b)
        # Interface shear (Slide form, depth-averaged):
        #   τ_int ≈ adhesion + σ_avg · tan(φ_int)
        # With no σ info at this level we use adhesion as average
        # (users can tune adhesion to reflect average σ·tanφ for the
        # slope; the GUI shows all three input modes).
        if self.pullout_mode == "mohr_coulomb":
            tau = self.adhesion  # kPa
        elif self.pullout_mode == "coefficient":
            # Without material strength here we fold via tensile_capacity
            # heuristic. The real Slide computation reaches into the
            # material the sheet passes through; we approximate with
            # tensile_capacity / total_length × Ci as a placeholder
            # (users tuning this should switch to mohr_coulomb mode).
            tau = self.coefficient_of_interaction * 10.0  # placeholder
        elif self.pullout_mode == "friction_factor":
            tau = self.friction_factor * 10.0  # placeholder
        else:
            tau = self.adhesion

        # 2-sided pullout: τ acts on both surfaces of the sheet
        f_pullout = 2.0 * tau * L_pull  # kN/m
        f_tensile = self.tensile_capacity
        if L_pull <= 0:
            return f_tensile
        return max(0.0, min(f_pullout, f_tensile))

    def to_dict(self) -> dict:
        # Serialise only public dataclass fields; private GUI
        # metadata (display_name, color, force_application, etc.) goes
        # into an 'extras' sub-dict.
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Geosynthetic":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# 7. User-Defined
# ======================================================================
@register_support
@dataclass
class UserDefined(SupportType):
    """User-defined support type — capacity vs distance from head.

    The user provides a list of (distance_from_head, force_per_anchor)
    pairs. Linear interpolation between points; constant extrapolation
    outside the table range. Divided by ``out_of_plane_spacing``.
    """
    TYPE_ID: ClassVar[str] = "user_defined"
    DISPLAY_NAME: ClassVar[str] = "User Defined"
    DESCRIPTION: ClassVar[str] = (
        "Custom support whose capacity-vs-distance is read from a "
        "table. Use this when none of the pre-defined types fits."
    )
    DEFAULT_ORIENTATION = ForceOrientation.PARALLEL_TO_SUPPORT
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    PARAMETERS: ClassVar[dict] = {
        "out_of_plane_spacing": (1.0, "m", "Out-of-plane spacing"),
        # ``points`` is edited via a table widget in the GUI
    }

    out_of_plane_spacing: float = 1.0
    points: list = field(default_factory=lambda: [
        (0.0, 100.0), (5.0, 200.0), (10.0, 100.0),
    ])

    def force_at(self, distance_from_head: float, total_length: float) -> float:
        s = self.out_of_plane_spacing if self.out_of_plane_spacing > 0 else 1.0
        if not self.points:
            return 0.0
        pts = sorted(self.points)
        x = max(0.0, distance_from_head)
        if x <= pts[0][0]:
            return pts[0][1] / s
        if x >= pts[-1][0]:
            return pts[-1][1] / s
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            if x0 <= x <= x1:
                f = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
                return (y0 + f * (y1 - y0)) / s
        return 0.0

    def to_dict(self) -> dict:
        d = {
            "type_id": self.TYPE_ID,
            "out_of_plane_spacing": self.out_of_plane_spacing,
            "points": list(self.points),
        }
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "UserDefined":
        extras = data.get("_extras", {})
        inst = cls(
            out_of_plane_spacing=data.get("out_of_plane_spacing", 1.0),
            points=[tuple(p) for p in data.get("points", [])],
        )
        if extras:
            inst._apply_extras(extras)
        return inst


# ======================================================================
# Instance — placement of a support in the model
# ======================================================================
@dataclass
class SupportInstance:
    """A concrete placement of a support in the model.

    Attributes:
        type_id: ``SupportType.TYPE_ID`` of the property type used
        head: head end, at the slope FACE — where the plate is. Not a
            free choice: ``force_at`` measures the stripping length
            from here and the pullout length from the tail, and
            ``_support_force_angle`` points the parallel force head →
            tail because that is the way a bolt in tension pulls.
        tail: tail end (anchor end, inside the slope)
        force_application: Active / Passive. ``None`` means "whatever
            this support type declares" — see below.
        orientation: how the support force vector aligns with the
            slip surface. ``None`` means "whatever this support type
            declares".
        user_angle_deg: only used if orientation = USER_DEFINED
        name, color, id: bookkeeping

    v0.1.112 — ``orientation`` and ``force_application`` default to
    ``None`` and are resolved in ``__post_init__`` against the support
    type's ``DEFAULT_ORIENTATION`` / ``DEFAULT_APPLICATION``. Before
    that they were plain dataclass defaults, so an instance built in
    code was born TANGENT_TO_SLIP + ACTIVE no matter what its type
    declared: a ``GroutedTieback`` (PARALLEL_TO_SUPPORT) and a
    ``PileMicropile`` (PERPENDICULAR_TO_PILE, PASSIVE) both silently
    ignored their own declaration. The GUI never had the bug — it
    copies the type's values by hand — which is exactly why it went
    unnoticed for so long.
    """
    type_id: str
    head: "Vertex"                    # type: ignore[name-defined]
    tail: "Vertex"                    # type: ignore[name-defined]
    force_application: Optional[ForceApplication] = None
    orientation: Optional[ForceOrientation] = None
    user_angle_deg: float = 0.0
    name: str = ""
    color: str = "#4b0082"
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if self.orientation is None:
            self.orientation = _default_orientation(self.type_id)
        if self.force_application is None:
            self.force_application = _default_application(self.type_id)

    def length(self) -> float:
        from ..geometry.primitives import Vertex  # noqa
        return self.head.distance_to(self.tail)

    def axis_angle_rad(self) -> float:
        """Angle of the support axis (head → tail) from positive x."""
        return math.atan2(
            self.tail.y - self.head.y, self.tail.x - self.head.x,
        )

    def axis_angle_deg(self) -> float:
        return math.degrees(self.axis_angle_rad())

    def intersection_with_polyline(
        self, polyline_xy: list,
    ) -> Optional[tuple]:
        """Find the intersection of (head → tail) with a polyline.

        Returns ``(x, y, distance_from_head)`` of the FIRST intersection,
        or None if there is none.
        """
        n = len(polyline_xy)
        if n < 2:
            return None
        hx, hy = self.head.x, self.head.y
        tx = self.tail.x - hx
        ty = self.tail.y - hy
        for i in range(n - 1):
            sx0, sy0 = polyline_xy[i]
            sx1, sy1 = polyline_xy[i + 1]
            ux = sx1 - sx0
            uy = sy1 - sy0
            denom = tx * uy - ty * ux
            if abs(denom) < 1e-12:
                continue
            s = ((sx0 - hx) * uy - (sy0 - hy) * ux) / denom
            u = ((sx0 - hx) * ty - (sy0 - hy) * tx) / denom
            if 0.0 <= s <= 1.0 and 0.0 <= u <= 1.0:
                ix = hx + s * tx
                iy = hy + s * ty
                d = s * math.hypot(tx, ty)
                return ix, iy, d
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "type_id": self.type_id,
            "head": [self.head.x, self.head.y],
            "tail": [self.tail.x, self.tail.y],
            "force_application": self.force_application.value,
            "orientation": self.orientation.value,
            "user_angle_deg": self.user_angle_deg,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SupportInstance":
        from ..geometry.primitives import Vertex
        return cls(
            type_id=data["type_id"],
            head=Vertex(*data["head"]),
            tail=Vertex(*data["tail"]),
            # A key that is ABSENT means the file never said, so the
            # support type decides; a key that is PRESENT is honoured.
            # Reading it as ``get(..., "active")`` invented a value the
            # file did not contain.
            force_application=(ForceApplication(data["force_application"])
                               if data.get("force_application") else None),
            orientation=(ForceOrientation(data["orientation"])
                         if data.get("orientation") else None),
            user_angle_deg=data.get("user_angle_deg", 0.0),
            name=data.get("name", ""),
            color=data.get("color", "#4b0082"),
            id=data.get("id", str(uuid4())),
        )

    def tooltip_html(self, stype: Optional[SupportType] = None) -> str:
        type_name = stype.DISPLAY_NAME if stype else self.type_id
        return (
            f"<b>{self.name or type_name}</b><br>"
            f"Type: {type_name}<br>"
            f"Length: {self.length():.2f} m<br>"
            f"Axis: {self.axis_angle_deg():.1f}°<br>"
            f"Orientation: {self.orientation.value}<br>"
            f"Application: {self.force_application.value}"
        )


# ======================================================================
# Support Pattern — utility for placing a row of supports along a line
# ======================================================================
@dataclass
class SupportPattern:
    """Specification of a regular row of supports along a boundary.

    Used by the Add Support Pattern dialog to generate multiple
    SupportInstance objects in a single operation.

    Attributes:
        type_id: SupportType.TYPE_ID applied to each generated support
        length: bolt/anchor length (m)
        spacing: along-slope spacing between adjacent bolts (m)
        orientation_mode: 'angle' = fixed angle relative to horizontal,
            'normal' = perpendicular to slope, 'depth' = constant
            vertical depth (Slide convention)
        angle_deg: angle from positive horizontal (used if mode=angle)
        flip_180: rotate generated bolts by 180° (head ↔ tail swap)
    """
    type_id: str
    length: float = 6.0
    spacing: float = 1.5
    orientation_mode: str = "angle"     # angle | normal | depth
    angle_deg: float = -15.0            # negative = pointing down into slope
    flip_180: bool = False
    # v0.1.112 — ``None`` means "ask the support type", exactly as in
    # :class:`SupportInstance`. A pattern is just a factory of instances,
    # so it cannot be the one place that overrides the type's own
    # declaration with a default nobody chose.
    force_application: Optional[ForceApplication] = None
    orientation: Optional[ForceOrientation] = None
    user_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        if self.orientation is None:
            self.orientation = _default_orientation(self.type_id)
        if self.force_application is None:
            self.force_application = _default_application(self.type_id)

    def generate_along_segment(
        self, p1, p2,
    ) -> list:
        """Build a list of SupportInstance along the segment p1 → p2.

        ``p1`` and ``p2`` are tuples or Vertex-likes with ``.x`` and
        ``.y``. Heads are placed on the segment at uniform ``spacing``
        intervals. Tails are computed from the chosen orientation.
        """
        from ..geometry.primitives import Vertex
        if hasattr(p1, "x"):
            x1, y1 = p1.x, p1.y
            x2, y2 = p2.x, p2.y
        else:
            x1, y1 = p1[0], p1[1]
            x2, y2 = p2[0], p2[1]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len < 1e-9 or self.spacing <= 0:
            return []
        # Tangent direction of the segment (head-positioning axis)
        tx = (x2 - x1) / seg_len
        ty = (y2 - y1) / seg_len
        # Slope normal (rotate tangent 90° clockwise, pointing INTO
        # the slope assumed: down-slope of the segment direction)
        nx = ty
        ny = -tx
        # How many supports fit
        n = max(1, int(seg_len // self.spacing) + 1)
        out = []
        for i in range(n):
            t = i * self.spacing
            if t > seg_len + 1e-6:
                break
            hx = x1 + t * tx
            hy = y1 + t * ty
            if self.orientation_mode == "angle":
                ang = math.radians(self.angle_deg)
                dx = math.cos(ang) * self.length
                dy = math.sin(ang) * self.length
            elif self.orientation_mode == "normal":
                dx = nx * self.length
                dy = ny * self.length
            elif self.orientation_mode == "depth":
                # Vertical
                dx = 0.0
                dy = -self.length
            else:
                ang = math.radians(self.angle_deg)
                dx = math.cos(ang) * self.length
                dy = math.sin(ang) * self.length
            if self.flip_180:
                dx, dy = -dx, -dy
            tail_x = hx + dx
            tail_y = hy + dy
            out.append(SupportInstance(
                type_id=self.type_id,
                head=Vertex(hx, hy),
                tail=Vertex(tail_x, tail_y),
                force_application=self.force_application,
                orientation=self.orientation,
                user_angle_deg=self.user_angle_deg,
            ))
        return out

    def to_dict(self) -> dict:
        return {
            "type_id": self.type_id,
            "length": self.length,
            "spacing": self.spacing,
            "orientation_mode": self.orientation_mode,
            "angle_deg": self.angle_deg,
            "flip_180": self.flip_180,
            "force_application": self.force_application.value,
            "orientation": self.orientation.value,
            "user_angle_deg": self.user_angle_deg,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SupportPattern":
        return cls(
            type_id=data["type_id"],
            length=data.get("length", 6.0),
            spacing=data.get("spacing", 1.5),
            orientation_mode=data.get("orientation_mode", "angle"),
            angle_deg=data.get("angle_deg", -15.0),
            flip_180=data.get("flip_180", False),
            force_application=(ForceApplication(data["force_application"])
                               if data.get("force_application") else None),
            orientation=(ForceOrientation(data["orientation"])
                         if data.get("orientation") else None),
            user_angle_deg=data.get("user_angle_deg", 0.0),
        )
