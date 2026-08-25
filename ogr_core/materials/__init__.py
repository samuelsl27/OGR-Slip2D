# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Material-property management with plugin-based constitutive laws."""
from . import builtin_models  # noqa: F401  — ensures registration on import
from .builtin_models import (
    GeneralizedHoekBrown,
    HoekBrown,
    Hyperbolic,
    InfiniteStrength,
    MohrCoulomb,
    NoStrength,
    PowerCurve,
    Undrained,
    UndrainedDepthFromDatum,
    UndrainedDepthFromLayerTop,
    UndrainedDistanceToSlope,
    VerticalStressRatio,
)
from .material import Material, PorePressureType
from .registry import REGISTRY, register
from .strength_model import StrengthModel

__all__ = [
    "Material",
    "PorePressureType",
    "StrengthModel",
    "REGISTRY",
    "register",
    "MohrCoulomb",
    "Undrained",
    "InfiniteStrength",
    "NoStrength",
    "HoekBrown",
    "GeneralizedHoekBrown",
    "PowerCurve",
    "Hyperbolic",
    "VerticalStressRatio",
    "UndrainedDepthFromLayerTop",
    "UndrainedDepthFromDatum",
    "UndrainedDistanceToSlope",
]

from .parameter_calculator import (  # noqa: E402,F401
    DISTURBANCE_GUIDANCE,
    GSI_GUIDANCE,
    MI_GUIDANCE,
    HoekBrownParameters,
    calculate_hoek_brown,
)
