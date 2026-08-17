# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Geometric primitives and operations for OGR Core."""
from .boundary import Boundary
from .boundary_type import BoundaryType
from .cleanup import (
    cleanup_boundaries,
    find_intersections,
    has_self_intersections,
    remove_duplicate_vertices,
    simplify_rdp,
)
from .expand_shrink import (
    ExpandShrinkError,
    ExpandShrinkResult,
    expand_shrink_external,
)
from .ground import (ground_surface, lower_y_at, upper_y_at,
                     zero_thickness_spans)
from .primitives import Polyline, Vertex, segments_of
from .tension_crack import TensionCrackProperties, WaterLevelMode
from .regions import MaterialRegion, build_regions, region_at_point, regions_available
from .transforms import (
    apply_to_many,
    change_slope_angle,
    convert_boundary,
    offset_polygon,
    rotate,
    scale,
    translate,
)

__all__ = [
    "Boundary",
    "BoundaryType",
    "Polyline",
    "Vertex",
    "segments_of",
    "cleanup_boundaries",
    "find_intersections",
    "has_self_intersections",
    "remove_duplicate_vertices",
    "simplify_rdp",
    "translate",
    "rotate",
    "scale",
    "offset_polygon",
    "change_slope_angle",
    "convert_boundary",
    "apply_to_many",
    "MaterialRegion",
    "build_regions",
    "region_at_point",
    "regions_available",
    # v0.1.6 expand/shrink
    "ExpandShrinkError",
    "ExpandShrinkResult",
    "expand_shrink_external",
    # v0.1.7 tension crack
    "TensionCrackProperties",
    "WaterLevelMode",
    # v0.1.84 — the single definition of the ground surface
    "ground_surface",
    "lower_y_at",
    "upper_y_at",
    "zero_thickness_spans",
]
