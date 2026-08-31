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
from typing import TYPE_CHECKING, ClassVar, Optional
from uuid import uuid4

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .bond import BondProfile


# ======================================================================
# Interface shear-strength envelopes
# ======================================================================
def interface_shear(
    sigma_n_eff: float, adhesion: float, friction_angle_deg: float,
    model: str = "linear",
) -> float:
    """Shear strength of a soil/reinforcement interface, kPa.

    Two envelopes, and the parameters mean DIFFERENT things in each —
    which is the single most common way to misuse this input:

    ``linear``
        Mohr-Coulomb on the interface, the classical bond formulation for
        geotextiles in Jewell (1996)::

            tau = a + sigma'_n · tan(delta)

        ``a`` is the strength at zero normal stress and ``delta`` the
        interface friction angle.

    ``hyperbolic``
        The envelope fitted to geosynthetic interface tests by
        Esterhuizen, Filz and Duncan (2001)::

            tau = a_inf · sigma'_n · tan(phi_0)
                  / (a_inf + sigma'_n · tan(phi_0))

        Here ``a_inf`` is the LIMITING strength as sigma_n → ∞, not the
        strength at zero, and ``phi_0`` is the tangent friction angle at
        sigma_n = 0. The curve starts with slope tan(phi_0) and saturates
        at a_inf, so the same pair of numbers describes a completely
        different envelope from the linear one.

    With pore pressure in the analysis the normal stress is effective, so
    both parameters are effective-stress parameters.
    """
    s = max(0.0, sigma_n_eff)
    t = math.tan(math.radians(friction_angle_deg))
    if model == "hyperbolic":
        denom = adhesion + s * t
        if denom <= 0.0:
            return 0.0
        return max(0.0, adhesion * s * t / denom)
    return max(0.0, adhesion + s * t)


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
    # Whether this type supports shear capacity (extra perpendicular force).
    # v0.1.124 — this is now the ENGINE's gate: ``compute_support_effects``
    # asks for ``shear_at`` only when a type declares it. Until then the
    # flag, like the method it guards, was read by nobody.
    SUPPORTS_SHEAR: ClassVar[bool] = False
    # v0.1.116 — whether this type's capacity depends on the stress state
    # along the reinforcement, and therefore needs a ``BondProfile``.
    # False for the four types whose diagram is a constant, a table or a
    # bond strength given directly per metre; building a 50-sample profile
    # for those would cost a search real time for a number nobody reads.
    NEEDS_BOND_PROFILE: ClassVar[bool] = False

    @abstractmethod
    def force_at(
        self, distance_from_head: float, total_length: float,
        bond: "BondProfile | None" = None,
    ) -> float:
        """Available support force at the slip intersection, kN/m of slope.

        Returns the MINIMUM of all applicable failure-mode capacities
        at the given distance from the head end.

        ``bond`` carries the interface shear strength sampled along the
        support (v0.1.116). Only the two stress-dependent types read it;
        passing ``None`` evaluates their law at zero effective stress,
        which is the honest answer when no project is available to supply
        one — a tooltip drawn before the model has geometry, say — and
        which reproduces the pre-v0.1.116 numbers for an interface
        described by adhesion alone.
        """

    def interface_tau(
        self, sigma_v_eff: float, **ctx,
    ) -> float:
        """Interface shear strength at one point, kPa.

        Overridden by the types whose pullout is stress-dependent. The
        keyword context carries ``project``, ``x``, ``y``,
        ``pore_pressure``, ``depth`` and ``axis_angle_rad``; a law that
        needs none of them ignores them all, which is why they arrive as
        keywords rather than as a positional record.
        """
        return 0.0

    def capacity_modes(
        self, distance_from_head: float, total_length: float,
        bond: "BondProfile | None" = None,
    ) -> dict:
        """Capacity of each failure mode at the cut, kN/m of slope.

        The keys are ASCII tokens, not labels: a user-visible name is
        translated GUI-side, which is where ``tr()`` can reach it. An empty
        dict means "this type has no modes to break down" — a constant, a
        table — and the caller then has only the applied force.

        v0.1.124 — the types that HAVE modes compute them here and let
        :meth:`force_at` be the minimum, rather than the other way round.
        Two writings of the same formula drift apart; a test pins
        ``force_at == min(capacity_modes)`` for every registered type.
        """
        return {}

    def station_distances(self, total_length: float) -> tuple:
        """Distances from the head where this type needs a POINT sample.

        v0.1.124 — the companion of :meth:`interface_tau` for what is not a
        per-unit-length quantity. A helical anchor answers with its plate
        positions; every other type answers with nothing and pays nothing.
        """
        return ()

    def station_value(self, sigma_v_eff: float, **ctx) -> float:
        """Value at one of :meth:`station_distances`, in kN.

        Same keyword context as :meth:`interface_tau`, evaluated in the
        same pass over the support.
        """
        return 0.0

    def shear_at(
        self, distance_from_head: float, total_length: float,
    ) -> float:
        """Optional perpendicular shear force at the intersection, kN/m.

        Returns 0 by default. The four types that declare
        ``SUPPORTS_SHEAR`` override it, dividing their shear capacity by
        the out-of-plane spacing like every other capacity here.

        v0.1.124 — what comes back is a SECOND force vector, perpendicular
        to the support axis and pointing against the slide, summed with the
        axial one by ``compute_support_effects``. Until that version this
        method was declared, editable, serialised and read by nobody, so
        the setting behind it could not move the number.
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
        bond: "BondProfile | None" = None,
    ) -> float:
        """Back-compat alias used by older v0.1.13 callers."""
        return self.force_at(length_along, total_length, bond)


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

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
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

    def capacity_modes(self, distance_from_head: float,
                       total_length: float, bond=None) -> dict:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return {}
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

        return {
            "pullout": (self.bond_strength * L_o) / s,
            "tensile": self.tensile_capacity / s,
            # Stripping is plate + however much bond is on the head side
            "stripping": (self.plate_capacity
                          + self.bond_strength * L_i) / s,
        }

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        modes = self.capacity_modes(distance_from_head, total_length, bond)
        if not modes:
            return 0.0
        return max(0.0, min(modes.values()))

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

    The grout annulus is a cylinder of diameter ``D_grout``, so the bond
    surface per metre of bond length is its outer circumference, π·D. The
    three failure modes are then

        pullout     F₁ = π·D · ∫_{L_o} τ ds / S
        tensile     F₂ = T / S
        stripping   F₃ = [P + π·D · ∫_{L_i} τ ds] / S

    with ``L_o`` the bonded length BEYOND the slip surface, ``L_i`` the
    bonded length between the head and the slip surface, and the applied
    force the minimum of the three. τ is the interface envelope of
    :func:`interface_shear` — Jewell (1996) for the linear form,
    Esterhuizen, Filz and Duncan (2001) for the hyperbolic one — and the
    normal stress on the annulus is taken uniform around it and equal to
    the effective VERTICAL stress at that depth.

    v0.1.116 — the integral is real. Until this version the docstring
    promised ``τ = adhesion + σ'_n·tan φ`` and the code computed
    ``tau_bond = self.adhesion``: ``friction_angle_bond`` was declared,
    editable and serialised, and read by nobody. The consequence was not a
    small error but a BINARY answer — no adhesion meant no pullout
    resistance at all at any friction angle, and any adhesion at all meant
    the tendon's whole tensile capacity. See ``bond.py`` for where σ'_n
    comes from and why it cannot come from the slice context.
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
    NEEDS_BOND_PROFILE: ClassVar[bool] = True
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
        "shear_strength_model": ("linear", "-",
            "Interface envelope: linear (Mohr-Coulomb) | hyperbolic. "
            "The two give DIFFERENT meanings to adhesion and friction "
            "angle — see the help for each."),
        "adhesion": (60.0, "kPa",
            "Adhesion at the grout/soil interface. Linear model: the "
            "strength at zero normal stress. Hyperbolic model: the "
            "LIMITING strength at high normal stress."),
        "friction_angle_bond": (25.0, "deg",
            "Friction angle at the grout/soil interface. Hyperbolic "
            "model: the tangent angle at zero normal stress."),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane spacing of tiebacks"),
        "shear_capacity": (0.0, "kN", "Optional shear capacity"),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile / Plate": ["tensile_capacity", "plate_capacity",
                            "shear_capacity"],
        "Pullout (Friction)": ["shear_strength_model", "adhesion",
                               "friction_angle_bond",
                               "grout_diameter", "bond_length_percent"],
        "Geometry": ["out_of_plane_spacing"],
    }

    tensile_capacity: float = 600.0
    plate_capacity: float = 300.0
    bond_length_percent: float = 30.0
    grout_diameter: float = 0.15
    shear_strength_model: str = "linear"
    adhesion: float = 60.0
    friction_angle_bond: float = 25.0
    out_of_plane_spacing: float = 2.0
    shear_capacity: float = 0.0

    def interface_tau(self, sigma_v_eff: float, **ctx) -> float:
        """Grout/soil interface strength at one point, kPa."""
        return interface_shear(sigma_v_eff, self.adhesion,
                               self.friction_angle_bond,
                               self.shear_strength_model)

    def capacity_modes(self, distance_from_head: float,
                       total_length: float, bond=None) -> dict:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return {}
        bond_len = total_length * self.bond_length_percent / 100.0
        free_len = total_length - bond_len
        x = max(0.0, min(distance_from_head, total_length))

        # The bond runs from ``free_len`` to the tail. ``L_i`` is the
        # bonded length on the head side of the slip surface and ``L_o``
        # the bonded length beyond it, so a surface cutting the free
        # length leaves the whole bond resisting pullout and none of it
        # resisting stripping.
        lo_start = max(x, free_len)
        li_end = max(x, free_len)

        perim = math.pi * self.grout_diameter
        if bond is None:
            # No project to measure σ'_n from: the envelope at zero
            # effective stress. For an interface described by adhesion
            # alone this is the exact answer, which is why it reproduces
            # every pre-v0.1.116 number.
            tau0 = self.interface_tau(0.0)
            bond_o = tau0 * max(0.0, total_length - lo_start)
            bond_i = tau0 * max(0.0, li_end - free_len)
        else:
            bond_o = bond.integral(lo_start, total_length)
            bond_i = bond.integral(free_len, li_end)

        return {
            "pullout": perim * bond_o / s,
            "tensile": self.tensile_capacity / s,
            "stripping": (self.plate_capacity + perim * bond_i) / s,
        }

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        modes = self.capacity_modes(distance_from_head, total_length, bond)
        if not modes:
            return 0.0
        return max(0.0, min(modes.values()))

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

    def capacity_modes(self, distance_from_head: float,
                       total_length: float, bond=None) -> dict:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return {}
        x = max(0.0, min(distance_from_head, total_length))
        L_o = max(0.0, total_length - x)  # bond behind slip
        L_i = x                            # bond ahead of slip
        return {
            "pullout": (self.bond_strength * L_o) / s,
            "tensile": self.tensile_capacity / s,
            "stripping": (self.plate_capacity
                          + self.bond_strength * L_i) / s,
        }

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        modes = self.capacity_modes(distance_from_head, total_length, bond)
        if not modes:
            return 0.0
        return max(0.0, min(modes.values()))

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
    """Pile / Micropile — transverse resistance, in one of two modes.

    Unlike every other support here, a pile does not resist along its own
    axis: it resists ACROSS it. Tension and pullout are not failure modes
    for a pile at all — only transverse shear through the section.

    **Shear** (the original mode, and still the default). The pile applies
    a CONSTANT force wherever the slip surface crosses it, equal to the
    pile shear strength divided by the out-of-plane spacing. That strength
    is the force the section can resist transversely, computed outside this
    program from the bending or shear capacity of the structural member.

    **Ito & Matsui** (v0.1.123). The force is not a property of the pile
    but of the SOIL squeezing between the piles of the row, so it depends
    on the spacing, on the diameter, on c, on phi and on depth — and it is
    the integral of that pressure from the top of the pile down to the cut,
    not a constant. See :mod:`ogr_core.support.ito_matsui` for the
    equations and their source, Ito and Matsui (1975).

    That the two modes answer different questions is the point of having
    both. Shear asks how much load the pile can take before it breaks;
    Ito & Matsui asks how much load the ground can hand it in the first
    place. A design needs the smaller of the two, and this program does not
    pick: the mode is the user declaring which one governs.

    Two class declarations become per-INSTANCE here, because they are true
    of one mode and false of the other, and a pile in Shear mode must not
    pay for a mode it is not in:

    * ``NEEDS_BOND_PROFILE`` — sampling the soil 50 times along every pile
      of every analysis, for a constant that never reads it;
    * ``MEASURED_FROM_TOP`` — which would also make a pile drawn exactly
      horizontal be EXCLUDED from the analysis. That is right for a
      pressure profile measured from the crest and wrong for a constant.
    """
    TYPE_ID: ClassVar[str] = "pile_micropile"
    DISPLAY_NAME: ClassVar[str] = "Pile / Micropile"
    DESCRIPTION: ClassVar[str] = (
        "Pile or micropile providing transverse shear resistance. In "
        "Shear mode the applied force is constant along the pile = pile "
        "shear ÷ spacing; in Ito & Matsui mode it is the integrated soil "
        "pressure on the row, which grows with depth."
    )
    # v0.1.113 — was PERPENDICULAR_TO_PILE. The reference default is
    # TANGENTIAL to the slip surface, and it gives the mechanical reason:
    # a pile fails in shear THROUGH its cross-section on the slip plane,
    # so the force it mobilises acts in that plane. Perpendicular-to-pile
    # exists as an option for a force independent of the surface, but it
    # is not the default.
    DEFAULT_ORIENTATION = ForceOrientation.TANGENT_TO_SLIP
    DEFAULT_APPLICATION = ForceApplication.PASSIVE
    PARAMETERS: ClassVar[dict] = {
        "failure_mode": ("shear", "-",
            "How the pile is loaded: shear | ito_matsui. Shear applies a "
            "constant force you provide; Ito & Matsui derives it from the "
            "soil flowing between the piles of the row."),
        "pile_shear_strength": (100.0, "kN",
            "Lateral shear strength of the pile cross-section"),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane spacing of piles, centre to centre. In Ito & "
            "Matsui mode it acts TWICE: as D1 inside the equation and as "
            "the divisor that turns force per pile into force per metre "
            "of slope."),
        "pile_diameter": (0.6, "m",
            "Pile diameter. Only Ito & Matsui reads it, through the "
            "opening between piles D2 = spacing − diameter."),
        "force_location": ("intersection", "-",
            "Where the resultant acts: intersection | centroid. Only the "
            "four methods with a moment equation can tell the two apart."),
    }
    #: Which parameters each mode actually reads — see ``docs/plugins.md``.
    #: A field the chosen mode ignores is disabled in the dialog instead of
    #: sitting there editable and inert. ``MODE_FIELD`` names the combo
    #: that decides; without it the dialog would grey out nothing.
    MODE_FIELD: ClassVar[str] = "failure_mode"
    PARAMETER_USED_BY: ClassVar[dict] = {
        "shear": ("pile_shear_strength", "out_of_plane_spacing"),
        "ito_matsui": ("out_of_plane_spacing", "pile_diameter",
                       "force_location"),
    }

    failure_mode: str = "shear"
    pile_shear_strength: float = 100.0
    out_of_plane_spacing: float = 2.0
    pile_diameter: float = 0.6
    force_location: str = "intersection"

    # ------------------------------------------------------------------
    def _ito(self) -> bool:
        """True when this pile is in Ito & Matsui mode.

        Anything but the exact token is Shear, deliberately: a project
        written by a newer version, or by hand, degrades to the mode that
        needs no soil rather than to an error in the middle of a search.
        """
        return str(self.failure_mode).strip().lower() == "ito_matsui"

    @property
    def NEEDS_BOND_PROFILE(self) -> bool:  # noqa: N802 - shadows a ClassVar
        """Only Ito & Matsui needs the soil sampled along the shaft.

        Shadowing the base ``ClassVar`` with a property is legal, and works
        because the three readers in the program all ask the INSTANCE. Read
        off the CLASS it returns the property object, which is truthy — so
        do not read it off the class.
        """
        return self._ito()

    @property
    def MEASURED_FROM_TOP(self) -> bool:  # noqa: N802 - see above
        """Ito & Matsui measures depth from the top of the pile.

        Cai and Ugai (2000) say it in as many words: Q is the integral
        "from the top of the pile to the depth of the slip circle at the
        pile position". A pile drawn bottom-to-top would otherwise invert
        its own pressure diagram and return a plausible, wrong number.
        """
        return self._ito()

    # ------------------------------------------------------------------
    def interface_tau(self, sigma_v_eff: float, **ctx) -> float:
        """The ``p`` of Ito and Matsui, kN/m of pile per metre of depth.

        What travels in the sampled profile for this type is NOT an
        interface strength — see the module docstring of
        :mod:`ogr_core.support.bond`. It is the lateral force per unit
        thickness of layer that the row takes off the sliding mass, which
        ``force_at`` then integrates down to the cut.

        **Which vertical stress.** The paper writes ``gamma z``, because
        there is no water anywhere in it and its Eq. (8) is the Rankine
        active pressure on the overburden. With effective strength
        parameters that pressure is written on the EFFECTIVE vertical
        stress, which is what arrives here, and the analysis says so when
        there is pore pressure on the pile. Feeding it the total stress
        instead would over-predict the pile force, the unsafe direction.

        **Which c and phi.** The reference itself says "the soil cohesion
        and friction angle (or equivalent values)": the equation is
        Mohr-Coulomb and a material need not be. The equivalent pair comes
        from the same linearisation the nine methods use — see
        :func:`ogr_core.support.bond.equivalent_c_phi_at`.
        """
        if not self._ito():
            return 0.0
        from .bond import equivalent_c_phi_at
        from .ito_matsui import clear_spacing, lateral_force

        d1 = float(self.out_of_plane_spacing)
        d2 = clear_spacing(d1, float(self.pile_diameter))
        if d1 <= 0.0 or d2 <= 0.0:
            # Piles that touch form a continuous wall and the equation
            # diverges there. Reported by the analysis notes; zero here so
            # a search does not die halfway through on a ValueError.
            return 0.0
        c, tan_phi = equivalent_c_phi_at(
            ctx.get("project"), ctx.get("x", 0.0), ctx.get("y", 0.0),
            sigma_v_eff,
            depth=ctx.get("depth", 0.0),
            pore_pressure=ctx.get("pore_pressure", 0.0),
            axis_angle_rad=ctx.get("axis_angle_rad", 0.0),
        )
        return lateral_force(c, math.atan(tan_phi), max(0.0, sigma_v_eff),
                             d1, d2)

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        """Force the pile hands the sliding mass, kN per metre of slope.

        In Ito & Matsui mode this is Cai and Ugai (2000) Eq. (9) without
        its moment arm: ``Q / D1``, with ``Q`` the integral of ``p`` from
        the top of the pile to the cut. Dividing by the spacing is neither
        optional nor a convention — ``p`` is a force per PILE and this
        method must return a force per METRE OF SLOPE, and only ``Q/D1``
        has those units.

        The clamp at zero is on the INTEGRAL, never on the samples.
        ``p`` can come out negative near the surface, where the cohesion
        terms dominate: that is the theory saying no plastic pressure
        develops there, and zeroing it sample by sample would quietly
        raise the total. The analysis reports it instead.
        """
        s = self.out_of_plane_spacing
        if s <= 0:
            return 0.0
        if self._ito():
            if bond is None:
                # No project to sample the soil from — a tooltip drawn
                # before the model has geometry, say. Zero is the honest
                # answer for a force that IS the soil.
                return 0.0
            return max(0.0, bond.integral(0.0, distance_from_head) / s)
        return self.pile_shear_strength / s

    def resultant_arm(self, distance_from_head: float,
                      total_length: float, bond=None) -> float:
        """Distance from the top of the pile to the centroid of ``p``.

        The *location of force* setting: the reference lets the resultant
        act at the slip-surface intersection or at the centroid of the
        pressure diagram above it. First moment over integral, both taken
        with the same piecewise convention, so the answer cannot land
        outside the mobilised length.

        Falls back to the cut itself when there is no diagram above it —
        which is where a zero force acts, and avoids a division by zero.
        """
        d = max(0.0, float(distance_from_head))
        if bond is None:
            return d
        area = bond.integral(0.0, d)
        if abs(area) < 1e-12:
            return d
        return min(d, max(0.0, bond.moment(0.0, d) / area))

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

    A sheet buried in soil has TWO interfaces with it, so pullout
    mobilises both faces. With ``A`` the strip coverage in per cent —
    ``a/(a+b)·100`` for strips of width ``a`` laid at gaps ``b``, so 100 %
    for a continuous sheet — the three failure modes per unit width of
    slope are

        pullout     F₁ = 2·(A/100) · ∫_{L_o} τ ds
        tensile     F₂ = T·A/100
        stripping   F₃ = (A/100) · [C + 2·∫_{L_i} τ ds]

    ``L_i`` runs from the head (the slope face) to the slip surface and
    ``L_o`` from the slip surface to the embedded tail; ``C`` is the
    connection strength at the face. The applied force is the minimum of
    the modes that ``anchorage`` allows: an embedded end that is anchored
    cannot be pulled out, so F₁ drops out.

    The factor of two is not a modelling choice here. FHWA-NHI-10-024
    (Berg, Christopher and Samtani 2009), Eq. 3-2, writes the pullout
    resistance as ``P_r = F*·α·σ'_v·L_e·C`` with the effective unit
    perimeter ``C = 2`` for sheets, and with ``L_e`` measured in the
    resisting zone BEHIND the failure surface.

    Three ways to describe τ, all published:

    ``mohr_coulomb``
        The interface envelope directly — ``τ = a + σ'_n·tan δ`` (linear)
        or the hyperbolic form of Esterhuizen, Filz and Duncan (2001),
        selected by ``shear_strength_model``. See :func:`interface_shear`.

    ``coefficient``
        A fraction of the SURROUNDING SOIL's own strength,
        ``τ = C_i · τ_soil(σ'_n)`` — the bond coefficient of Jewell
        (1996). C_i = 0 takes no strength from the soil and C_i = 1 the
        whole of it. Evaluating τ_soil with the material's own strength
        model rather than with a cohesion and a friction angle read off it
        is what makes this work for a material that is not Mohr-Coulomb.

    ``friction_factor``
        ``τ = F*·σ'_n``, the pullout friction factor of the FHWA equation
        above. The scale-effect correction α (0.6–1.0 for geosynthetics)
        is not a separate input: multiply it into F*, as that guidance
        itself directs. F* may be constant or vary linearly with depth.

    v0.1.116 — all three laws are real. Until this version the first
    returned ``adhesion`` alone (so ``friction_angle_interface`` moved
    nothing) and the other two returned ``coefficient · 10.0`` and
    ``friction_factor · 10.0`` — literal placeholders, so C_i and F*
    moved nothing either. The pullout length was also the SHORTER of the
    two sides rather than the one behind the surface, which happens to
    agree with min(F₁, F₃) only while τ is uniform and C = 0.
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
    NEEDS_BOND_PROFILE: ClassVar[bool] = True
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (50.0, "kN/m",
            "Tensile capacity of the sheet per metre of strip width"),
        "strip_coverage": (100.0, "%",
            "Out-of-plane coverage A = a/(a+b)·100 for strips of width "
            "a laid at gaps b. 100 % for a continuous sheet."),
        "connection_strength": (0.0, "kN/m",
            "Force the connection at the slope face can carry. It is "
            "the force at the head of the diagram; set it to the "
            "tensile capacity to make stripping impossible."),
        "anchorage": ("none", "-",
            "Which ends are anchored: none | slope_face | embedded_end "
            "| both_ends. Pullout is only possible while the embedded "
            "end is free."),
        "pullout_mode": ("mohr_coulomb", "-",
            "Pullout strength model: mohr_coulomb | coefficient | "
            "friction_factor"),
        "shear_strength_model": ("linear", "-",
            "Interface envelope in Mohr-Coulomb mode: linear | "
            "hyperbolic. The two give DIFFERENT meanings to adhesion "
            "and friction angle."),
        "adhesion": (0.0, "kPa",
            "Interface adhesion (Mohr-Coulomb mode). Linear: strength "
            "at zero normal stress. Hyperbolic: the LIMITING strength "
            "at high normal stress."),
        "friction_angle_interface": (25.0, "deg",
            "Interface friction angle (Mohr-Coulomb mode). Hyperbolic: "
            "the tangent angle at zero normal stress."),
        "coefficient_of_interaction": (0.8, "-",
            "Ci: τ_int = Ci · τ_soil, the fraction of the surrounding "
            "soil's own strength the interface develops"),
        "friction_factor": (0.6, "-",
            "F*: τ_int = F* · σ'_v. Multiply the scale-effect factor α "
            "into it. In function mode, the value at the reference "
            "elevation."),
        "friction_factor_mode": ("constant", "-",
            "F* constant, or a function of depth: constant | function"),
        "reference_elevation": (0.0, "m",
            "Elevation at which F* takes its entered value "
            "(function mode)"),
        "reference_depth": (0.0, "m",
            "Depth below the reference elevation at which F* takes its "
            "second value (function mode)"),
        "friction_factor_at_depth": (0.6, "-",
            "F* at the reference depth (function mode)"),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Tensile": ["tensile_capacity", "strip_coverage",
                    "connection_strength", "anchorage"],
        "Pullout & Stripping": ["pullout_mode", "shear_strength_model",
                                "adhesion",
                                "friction_angle_interface",
                                "coefficient_of_interaction",
                                "friction_factor"],
        "F* vs Depth": ["friction_factor_mode", "reference_elevation",
                        "reference_depth", "friction_factor_at_depth"],
    }

    tensile_capacity: float = 50.0
    strip_coverage: float = 100.0
    connection_strength: float = 0.0
    anchorage: str = "none"
    pullout_mode: str = "mohr_coulomb"
    shear_strength_model: str = "linear"
    adhesion: float = 0.0
    friction_angle_interface: float = 25.0
    coefficient_of_interaction: float = 0.8
    friction_factor: float = 0.6
    friction_factor_mode: str = "constant"
    reference_elevation: float = 0.0
    reference_depth: float = 0.0
    friction_factor_at_depth: float = 0.6

    def _friction_factor_at(self, y: float, depth: float) -> float:
        """F* at one point, constant or varying linearly with depth.

        In function mode F* is interpolated between its entered value at
        ``reference_elevation`` and ``friction_factor_at_depth`` at
        ``reference_depth`` BELOW that elevation, and held constant
        outside that range — extrapolating a fitted straight line past
        its data would eventually turn F* negative.

        v0.1.116 — this is what ``reference_elevation`` is for. It was
        declared, editable and serialised since v0.1.14 and read by
        nobody: a second inert control sitting next to the one this
        version came to fix.
        """
        if self.friction_factor_mode != "function":
            return self.friction_factor
        span = self.reference_depth
        if span <= 0.0:
            return self.friction_factor
        # Depth below the reference elevation, not below the ground: the
        # datum is the one the user entered.
        d = self.reference_elevation - y
        t = max(0.0, min(1.0, d / span))
        return (self.friction_factor
                + t * (self.friction_factor_at_depth - self.friction_factor))

    def interface_tau(self, sigma_v_eff: float, **ctx) -> float:
        """Sheet/soil interface strength at one point, kPa."""
        mode = self.pullout_mode
        if mode == "coefficient":
            project = ctx.get("project")
            if project is None:
                # The soil's strength is the whole law here, so without a
                # project there is nothing to take a fraction OF. Zero is
                # the honest answer; inventing one is what v0.1.115 did.
                return 0.0
            from .bond import soil_shear_strength_at
            tau_soil = soil_shear_strength_at(
                project, ctx.get("x", 0.0), ctx.get("y", 0.0), sigma_v_eff,
                depth=ctx.get("depth", 0.0),
                pore_pressure=ctx.get("pore_pressure", 0.0),
                axis_angle_rad=ctx.get("axis_angle_rad", 0.0),
            )
            return max(0.0, self.coefficient_of_interaction * tau_soil)
        if mode == "friction_factor":
            f = self._friction_factor_at(ctx.get("y", 0.0),
                                         ctx.get("depth", 0.0))
            return max(0.0, f * max(0.0, sigma_v_eff))
        return interface_shear(sigma_v_eff, self.adhesion,
                               self.friction_angle_interface,
                               self.shear_strength_model)

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        if total_length <= 0:
            return 0.0
        cover = max(0.0, self.strip_coverage) / 100.0
        x = max(0.0, min(distance_from_head, total_length))

        if bond is None:
            # Evaluated at zero effective stress — see the base class.
            # For the two stress-only laws that is genuinely zero, and
            # saying so beats the placeholder it replaces.
            tau0 = self.interface_tau(0.0)
            bond_i = tau0 * x
            bond_o = tau0 * (total_length - x)
        else:
            bond_i = bond.integral(0.0, x)
            bond_o = bond.integral(x, total_length)

        f_tensile = self.tensile_capacity * cover
        f_stripping = cover * (self.connection_strength + 2.0 * bond_i)
        modes = [f_tensile, f_stripping]
        # Pullout needs a free embedded end. Anchoring it removes the
        # mode outright rather than making it large, because an anchored
        # end is a boundary condition, not a bigger bond.
        if self.anchorage in ("none", "slope_face"):
            modes.append(cover * 2.0 * bond_o)
        return max(0.0, min(modes))

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

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
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

    def intersections_with_polyline(self, polyline_xy: list) -> list:
        """EVERY crossing of (head → tail) with a polyline.

        A list of ``(x, y, distance_from_head)``, ordered along the
        support from the head, empty if it never crosses.

        v0.1.138 — the counting version exists because *how many times*
        is a different question from *where*, and it decides something
        the first crossing cannot answer. A support that crosses the slip
        surface TWICE has both of its ends outside the sliding mass: it
        is a chord through the mass, not an anchor reaching past it, and
        the head/tail check of
        ``ogr_slip2d.support_integration.reversed_support_notes`` has no
        asymmetry left to read. Verification problem 85 is exactly that
        — a horizontal tieback at y = 20 against a shallow critical
        surface that dips to y = 19.92 — and judging it on the first
        crossing alone called a correctly drawn bolt reversed.
        """
        out: list = []
        n = len(polyline_xy)
        if n < 2:
            return out
        hx, hy = self.head.x, self.head.y
        tx = self.tail.x - hx
        ty = self.tail.y - hy
        span = math.hypot(tx, ty)
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
                out.append((hx + s * tx, hy + s * ty, s * span))
        return out

    def intersection_with_polyline(
        self, polyline_xy: list,
    ) -> Optional[tuple]:
        """Find the intersection of (head → tail) with a polyline.

        Returns ``(x, y, distance_from_head)`` of the FIRST intersection,
        or None if there is none. Delegates to
        :meth:`intersections_with_polyline` so the segment arithmetic
        lives in one place: a rule written twice goes stale in one of
        them.
        """
        hits = self.intersections_with_polyline(polyline_xy)
        return hits[0] if hits else None

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
