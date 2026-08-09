# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Hydraulic / pore-pressure computation utilities.

Populated progressively by future OGR FEM2D coupling.
"""
from .water_pressure_grid import GridValueType, WaterPressureGrid  # noqa: F401
from .water_surfaces import (  # noqa: F401
    ASSIGNABLE_WATER_SURFACE_TYPES,
    WATER_SURFACE_TYPES,
    interp_y_on_polyline,
    resolve_water_surface,
    water_surface_index,
    water_surface_label,
    water_surface_y_at,
    water_surfaces,
    water_table_y_at,
)
from .ponded_water import (  # noqa: F401
    PONDING_BOUNDARY_TYPES,
    ponded_depth_at,
    ponded_water_level_at,
)
from .drawdown_levels import (  # noqa: F401
    drawdown_boundary,
    drawdown_line_is_inverted,
    ground_elevation_span,
    level_project,
    levels_at,
    model_x_span,
    project_at_level,
)
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
