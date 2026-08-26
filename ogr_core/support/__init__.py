# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Structural support / reinforcement plugin system.

8 built-in support types:
    - End Anchored
    - Grouted Tieback
    - Grouted Tieback with Friction
    - Soil Nail
    - Pile / Micropile
    - Geosynthetic
    - User Defined
    - Retaining Wall (EFP)

Plus :class:`SupportPattern` for batch creation of regular rows, and
:class:`BondProfile` (v0.1.116), a per-unit-length quantity sampled along
a reinforcement once per analysis: the interface shear strength of the two
stress-dependent pullout laws, or (v0.1.123) the Ito and Matsui lateral
force per unit depth of a pile in that mode.

:mod:`ogr_core.support.ito_matsui` holds the three published equations of
that mode on their own, with no project and no geometry, so that they can
be checked against their source in isolation.
"""
from .bond import (
    DEFAULT_SEGMENTS,
    BondProfile,
    build_bond_profile,
    equivalent_c_phi_at,
    sigma_v_effective_at,
    soil_shear_strength_at,
)
from .ito_matsui import (
    PHI_SWITCH_RAD,
    clear_spacing,
    lateral_force,
    lateral_force_c_phi,
    lateral_force_cohesionless,
    lateral_force_cohesive,
    n_phi,
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
# Imported for its side effect as much as for the name: the
# ``@register_support`` decorator runs on import, and this package
# ``__init__`` is what guarantees it has run before anything can ask
# the registry for the type.
from .retaining_wall import RetainingWallEFP

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
    "RetainingWallEFP",
    "support_registry",
    "support_from_dict",
    "register_support",
    "interface_shear",
    "BondProfile",
    "build_bond_profile",
    "equivalent_c_phi_at",
    "sigma_v_effective_at",
    "soil_shear_strength_at",
    "DEFAULT_SEGMENTS",
    "PHI_SWITCH_RAD",
    "clear_spacing",
    "n_phi",
    "lateral_force",
    "lateral_force_c_phi",
    "lateral_force_cohesionless",
    "lateral_force_cohesive",
]
