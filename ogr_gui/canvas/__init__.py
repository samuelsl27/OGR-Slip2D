# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Interactive 2D canvas (QGraphicsScene-based)."""
from .canvas_view import CanvasView, DisplayOptions
from .graphics_items import (
    BoundaryItem,
    DistributedLoadItem,
    LineLoadItem,
    MaterialRegionItem,
    SlipSurfaceItem,
    SupportItem,
    VertexHandleItem,
)
from .snap_engine import SnapEngine, SnapSettings, nice_step
from .tool_mode import ToolMode

__all__ = [
    "CanvasView",
    "DisplayOptions",
    "ToolMode",
    "BoundaryItem",
    "MaterialRegionItem",
    "DistributedLoadItem",
    "LineLoadItem",
    "SupportItem",
    "VertexHandleItem",
    "SlipSurfaceItem",
    "SnapEngine",
    "SnapSettings",
    "nice_step",
]
