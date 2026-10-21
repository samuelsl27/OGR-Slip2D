# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Focus objects: moved to :mod:`ogr_core.geometry.focus`.

v0.1.343 (D337) -- the project stores its focus objects and the core
rebuilds them on load, so they are the core's. This module re-exports every
name the old one defined, the same objects, so ``from ogr_slip2d.focus
import ...`` keeps working everywhere.

Author: Samuel Sáez López (UPCT)
"""
from ogr_core.geometry.focus import (  # noqa: F401
    FocusKind,
    _seg_circle_crosses,
    _closest_distance,
    _orient,
    _on_segment,
    _segments_cross,
    _polyline_point_distance,
    _signed_distance_point_line,
    _point_in_polygon,
    FocusObject,
    _distance_point_line,
    accepts,
    accepts_surface,
    filter_circles,
)
