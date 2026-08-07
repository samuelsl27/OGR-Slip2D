# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tool modes for the interactive canvas.

A tool mode is the current interactive state of the canvas — navigating,
drawing a boundary, picking a vertex, applying a transformation. Exactly
one mode is active at any moment; it dictates how mouse events are
interpreted by :class:`CanvasView`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from enum import Enum


class ToolMode(Enum):
    """The currently active interaction tool."""

    # ----- Default / navigation -----
    SELECT = "select"
    PAN = "pan"
    ZOOM_WINDOW = "zoom_window"
    ZOOM_MOUSE = "zoom_mouse"
    MEASURE = "measure"

    # ----- Boundary drawing (click-click-click) -----
    DRAW_EXTERNAL = "draw_external"
    DRAW_MATERIAL = "draw_material"
    DRAW_WATER_TABLE = "draw_water_table"
    DRAW_DRAWDOWN = "draw_drawdown"
    DRAW_PIEZOMETRIC = "draw_piezometric"
    DRAW_TENSION_CRACK = "draw_tension_crack"
    DRAW_BLOCK_SEARCH = "draw_block_search"

    # ----- Boundary CRUD -----
    DELETE_BOUNDARY = "delete_boundary"
    MOVE_BOUNDARY = "move_boundary"
    COPY_BOUNDARY = "copy_boundary"
    ASSIGN_MATERIAL = "assign_material"
    CONVERT_BOUNDARY = "convert_boundary"

    # ----- Vertex-level edits -----
    MOVE_VERTEX = "move_vertex"
    INSERT_VERTEX = "insert_vertex"
    DELETE_VERTEX = "delete_vertex"

    # ----- Transformations (click pivot point) -----
    SCALE_BOUNDARY = "scale_boundary"
    ROTATE_BOUNDARY = "rotate_boundary"
    EXPAND_SHRINK = "expand_shrink"                # menu entry (old)
    DRAW_EXPAND_SHRINK = "draw_expand_shrink"      # interactive draw mode (Slide-style)
    CHANGE_SLOPE_ANGLE = "change_slope_angle"

    # ----- Loads / supports / surfaces (placeholders for v0.1.3+) -----
    ADD_DISTRIBUTED_LOAD = "add_distributed_load"
    ADD_LINE_LOAD = "add_line_load"
    # v0.1.10 — pick a rectangle (2 corners) for the slip-circle search grid
    PICK_GRID_RECT = "pick_grid_rect"
    ADD_SUPPORT = "add_support"
    ADD_SUPPORT_PATTERN = "add_support_pattern"   # v0.1.14
    DELETE_SUPPORT = "delete_support"             # v0.1.14
    STRETCH_SUPPORT = "stretch_support"           # v0.1.14
    ADD_SURFACE_3PT = "add_surface_3pt"
    ADD_SURFACE_CR = "add_surface_cr"

    # ==================================================================
    @property
    def is_drawing_boundary(self) -> bool:
        """True if this is a multi-click boundary-drawing mode."""
        return self in {
            ToolMode.DRAW_EXTERNAL,
            ToolMode.DRAW_MATERIAL,
            ToolMode.DRAW_WATER_TABLE,
            ToolMode.DRAW_DRAWDOWN,
            ToolMode.DRAW_PIEZOMETRIC,
            ToolMode.DRAW_TENSION_CRACK,
            ToolMode.DRAW_BLOCK_SEARCH,
            ToolMode.DRAW_EXPAND_SHRINK,
        }

    @property
    def draws_closed_polygon(self) -> bool:
        """Only the External Boundary auto-closes (Slide convention).

        Material Boundaries are OPEN polylines: regions emerge from their
        intersection with the External Boundary and with each other, via
        planar subdivision — not by closing each Material boundary into
        its own polygon. See ``Add_Material_Boundary.htm`` in the Slide
        reference.
        """
        return self in (ToolMode.DRAW_EXTERNAL, ToolMode.DRAW_BLOCK_SEARCH)

    @property
    def boundary_type_drawn(self):
        """Maps drawing modes to their :class:`BoundaryType`."""
        from ogr_core.geometry import BoundaryType
        return {
            ToolMode.DRAW_EXTERNAL: BoundaryType.EXTERNAL,
            ToolMode.DRAW_MATERIAL: BoundaryType.MATERIAL,
            ToolMode.DRAW_WATER_TABLE: BoundaryType.WATER_TABLE,
            ToolMode.DRAW_DRAWDOWN: BoundaryType.DRAWDOWN,
            ToolMode.DRAW_PIEZOMETRIC: BoundaryType.PIEZOMETRIC,
            ToolMode.DRAW_TENSION_CRACK: BoundaryType.TENSION_CRACK,
            ToolMode.DRAW_BLOCK_SEARCH: BoundaryType.BLOCK_SEARCH_OBJECT,
        }.get(self)

    # ------------------------------------------------------------------
    @property
    def cursor_name(self) -> str:
        return {
            ToolMode.SELECT: "ArrowCursor",
            ToolMode.PAN: "OpenHandCursor",
            ToolMode.ZOOM_WINDOW: "CrossCursor",
            ToolMode.ZOOM_MOUSE: "CrossCursor",
            ToolMode.MEASURE: "CrossCursor",
            ToolMode.DRAW_EXTERNAL: "CrossCursor",
            ToolMode.DRAW_MATERIAL: "CrossCursor",
            ToolMode.DRAW_WATER_TABLE: "CrossCursor",
            ToolMode.DRAW_DRAWDOWN: "CrossCursor",
            ToolMode.DRAW_PIEZOMETRIC: "CrossCursor",
            ToolMode.DRAW_TENSION_CRACK: "CrossCursor",
            ToolMode.DELETE_BOUNDARY: "PointingHandCursor",
            ToolMode.MOVE_BOUNDARY: "SizeAllCursor",
            ToolMode.COPY_BOUNDARY: "PointingHandCursor",
            ToolMode.ASSIGN_MATERIAL: "PointingHandCursor",
            ToolMode.CONVERT_BOUNDARY: "PointingHandCursor",
            ToolMode.MOVE_VERTEX: "SizeAllCursor",
            ToolMode.INSERT_VERTEX: "CrossCursor",
            ToolMode.DELETE_VERTEX: "PointingHandCursor",
            ToolMode.SCALE_BOUNDARY: "CrossCursor",
            ToolMode.ROTATE_BOUNDARY: "CrossCursor",
            ToolMode.EXPAND_SHRINK: "PointingHandCursor",
            ToolMode.DRAW_EXPAND_SHRINK: "CrossCursor",
            ToolMode.CHANGE_SLOPE_ANGLE: "CrossCursor",
            ToolMode.ADD_DISTRIBUTED_LOAD: "CrossCursor",
            ToolMode.ADD_LINE_LOAD: "CrossCursor",
            ToolMode.PICK_GRID_RECT: "CrossCursor",
            ToolMode.ADD_SUPPORT: "CrossCursor",
            ToolMode.ADD_SUPPORT_PATTERN: "CrossCursor",
            ToolMode.DELETE_SUPPORT: "PointingHandCursor",
            ToolMode.STRETCH_SUPPORT: "PointingHandCursor",
            ToolMode.ADD_SURFACE_3PT: "CrossCursor",
            ToolMode.ADD_SURFACE_CR: "CrossCursor",
        }.get(self, "ArrowCursor")

    @property
    def status_message(self) -> str:
        return {
            ToolMode.SELECT: "",
            ToolMode.PAN: "Pan: drag to move the view, Esc to exit",
            ToolMode.ZOOM_WINDOW: "Zoom Window: drag a rectangle, Esc to cancel",
            ToolMode.ZOOM_MOUSE: "Zoom Mouse: left-click zooms in, right-click zooms out, Esc to exit",
            ToolMode.MEASURE: "Measure: click two points, Esc to finish",
            ToolMode.DRAW_EXTERNAL: "Draw External Boundary: click to add vertices, Enter or right-click to close, Esc to cancel",
            ToolMode.DRAW_MATERIAL: "Draw Material Boundary: click to add vertices, Enter or right-click to close, Esc to cancel",
            ToolMode.DRAW_WATER_TABLE: "Draw Water Table: click to add vertices, Enter or right-click to finish, Esc to cancel",
            ToolMode.DRAW_DRAWDOWN: "Draw Drawdown Line: click to add vertices, Enter or right-click to finish, Esc to cancel",
            ToolMode.DRAW_PIEZOMETRIC: "Draw Piezometric Line: click to add vertices, Enter or right-click to finish, Esc to cancel",
            ToolMode.DRAW_TENSION_CRACK: "Draw Tension Crack: click to add vertices, Enter or right-click to finish, Esc to cancel",
            ToolMode.DRAW_EXPAND_SHRINK: "Expand/Shrink External: FIRST point must be ON the External (green cross). Intermediate points go OUTSIDE (expand) or INSIDE (shrink). LAST point must be ON the External. Esc to cancel.",
            ToolMode.DELETE_BOUNDARY: "Click a boundary to delete it, Esc to exit",
            ToolMode.MOVE_BOUNDARY: "Click a boundary and drag to move it, Esc to exit",
            ToolMode.COPY_BOUNDARY: "Click a boundary to duplicate it, Esc to exit",
            ToolMode.ASSIGN_MATERIAL: "Click a material boundary to assign the current material, Esc to exit",
            ToolMode.CONVERT_BOUNDARY: "Click a boundary to convert its type, Esc to exit",
            ToolMode.MOVE_VERTEX: "Click a vertex and drag to move it, Esc to exit",
            ToolMode.INSERT_VERTEX: "Click on an edge to insert a new vertex, Esc to exit",
            ToolMode.DELETE_VERTEX: "Click a vertex to delete it, Esc to exit",
            ToolMode.SCALE_BOUNDARY: "Click a boundary to scale, then enter scale factor, Esc to exit",
            ToolMode.ROTATE_BOUNDARY: "Click a boundary, then pivot point, then target angle, Esc to exit",
            ToolMode.EXPAND_SHRINK: "Click the External boundary to expand/shrink, Esc to exit",
            ToolMode.CHANGE_SLOPE_ANGLE: "Click the External boundary, then pivot point, Esc to exit",
            ToolMode.ADD_DISTRIBUTED_LOAD: "Click start and end points on a boundary",
            ToolMode.ADD_LINE_LOAD: "Click a point to place the line load",
            ToolMode.PICK_GRID_RECT: "Click two opposite corners of the slip-circle search grid",
            ToolMode.ADD_SUPPORT: "Click head, then tail of the support",
            ToolMode.ADD_SUPPORT_PATTERN: (
                "Click two points along a boundary to define the "
                "pattern segment; supports will be generated at the "
                "configured spacing."
            ),
            ToolMode.DELETE_SUPPORT: (
                "Click a support to delete it. Esc to exit."
            ),
            ToolMode.STRETCH_SUPPORT: (
                "Click near the head or tail end of a support to grab "
                "it, then click the new position. Esc to cancel."
            ),
            ToolMode.ADD_SURFACE_3PT: "Click three points to define a circular surface",
            ToolMode.ADD_SURFACE_CR: "Click the centre, then a point on the circle",
        }.get(self, "")
