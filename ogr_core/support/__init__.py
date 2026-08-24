# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Structural support / reinforcement plugin system.

7 built-in support types matching Slide's catalogue:
    - End Anchored
    - Grouted Tieback
    - Grouted Tieback with Friction
    - Soil Nail
    - Pile / Micropile
    - Geosynthetic
    - User Defined

Plus :class:`SupportPattern` for batch creation of regular rows, and
:class:`BondProfile` (v0.1.116), the interface shear strength sampled
along a reinforcement that the two stress-dependent pullout laws need.
"""
from .bond import (
    DEFAULT_SEGMENTS,
    BondProfile,
    build_bond_profile,
    sigma_v_effective_at,
    soil_shear_strength_at,
)
from .support import (
    EndAnchored,
    ForceApplication,
    ForceOrientation,
    Geosynthetic,
    GroutedTieback,
    GroutedTiebackFriction,
    PileMicropile,
    SoilNail,
    SupportInstance,
    SupportPattern,
    SupportType,
    UserDefined,
    register_support,
    support_from_dict,
    interface_shear,
    support_registry,
)

__all__ = [
    "SupportType",
    "SupportInstance",
    "SupportPattern",
    "ForceApplication",
    "ForceOrientation",
    "EndAnchored",
    "GroutedTieback",
    "GroutedTiebackFriction",
    "SoilNail",
    "PileMicropile",
    "Geosynthetic",
    "UserDefined",
    "support_registry",
    "support_from_dict",
    "register_support",
    "interface_shear",
    "BondProfile",
    "build_bond_profile",
    "sigma_v_effective_at",
    "soil_shear_strength_at",
    "DEFAULT_SEGMENTS",
]
