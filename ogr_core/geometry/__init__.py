# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Geometric primitives and operations for OGR Core."""
from .block_object import (BlockObjectKind, BlockObjectSpec,
                           PolylinePointMode, block_group_of, block_groups,
                           block_spec_of, infer_block_kind)
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
from .ground import (bedrock_surface, distance_to_profile, envelope_y_at,
                     ray_ground_exit,
                     ground_surface, lower_y_at, upper_y_at,
                     zero_thickness_spans)
from .primitives import Polyline, Vertex, segments_of
from .tension_crack import TensionCrackProperties, WaterLevelMode
from .regions import MaterialRegion, build_regions, region_at_point, regions_available
from .transforms import (
    apply_to_many,
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
    # v0.1.111 — and of the floor of the model, which Composite Surfaces
    # makes a slip surface follow instead of crossing.
    "bedrock_surface",
    "envelope_y_at",
    # v0.1.120 — true distance to the ground profile, for the
    # undrained strength measured from the slope face.
    "distance_to_profile",
    # v0.1.257 — where a Block Search projection leaves the soil (D238).
    "ray_ground_exit",
    "lower_y_at",
    "upper_y_at",
    "zero_thickness_spans",
    # v0.1.232 (D109) — the four Block Search objects, stored on the object
    "BlockObjectKind",
    "BlockObjectSpec",
    "PolylinePointMode",
    "block_group_of",
    "block_groups",
    "block_spec_of",
    "infer_block_kind",
]
