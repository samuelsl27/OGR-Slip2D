# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Hydraulic / pore-pressure computation utilities.

Populated progressively by future OGR FEM2D coupling.
"""
from .water_pressure_grid import GridValueType, WaterPressureGrid  # noqa: F401
from .hydraulic_properties import (  # noqa: F401
    HydraulicProperties,
    UnsaturatedModel,
)
from .permeability_models import (  # noqa: F401
    MATERIAL_LIBRARY,
    PermeabilityModel,
    SimpleSoilType,
    available_models,
    library_for,
    register_model,
)
