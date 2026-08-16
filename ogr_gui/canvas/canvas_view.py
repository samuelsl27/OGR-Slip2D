# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
CanvasView — the interactive 2D viewport (v0.2.0).

Interactive features:
    - Middle-mouse-button pan (always on, regardless of active tool)
    - Tool-mode system: SELECT, PAN (hand cursor drag), ZOOM_WINDOW
      (rubber-band rectangle), ZOOM_MOUSE (click-to-zoom centred on cursor)
    - Wheel zoom centred on cursor
    - Full set of display-option flags that control per-layer rendering

The Y axis is flipped (``scale(1, -1)``) so that positive Y points up,
matching the engineering convention.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QMouseEvent,
    QPainter,
    QPen,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from ogr_core.geometry import BoundaryType, Vertex
from ogr_core.project import Project

from .graphics_items import (
    BoundaryItem,
    DistributedLoadItem,
    LineLoadItem,
    MaterialRegionItem,
    SlipRadiiItem,
    SlipSurfaceItem,
    SupportItem,
    VertexHandleItem,
)
from .snap_engine import SnapEngine, SnapSettings, nice_step
from .tool_mode import ToolMode
from ogr_gui.i18n import tr  # noqa: E402


# ----------------------------------------------------------------------
# Helper — module-level distance function used by the hit-test methods
# ----------------------------------------------------------------------
def _point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """Shortest distance from (px, py) to segment [(ax, ay)-(bx, by)]."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


# ----------------------------------------------------------------------
def _region_to_item(region, material):
    """Turn a :class:`MaterialRegion` into a QGraphicsPathItem."""
    from PySide6.QtGui import QPainterPath, QPolygonF
    from PySide6.QtWidgets import QGraphicsPathItem

    verts = region.polygon.vertices
    if len(verts) < 3:
        return None
    poly = QPolygonF([QPointF(v.x, v.y) for v in verts])
    path = QPainterPath()
    path.addPolygon(poly)
    path.closeSubpath()
    item = QGraphicsPathItem(path)
    if material is not None:
        color = QColor(material.color) if hasattr(material, "color") else QColor("#d4a373")
        color.setAlphaF(0.55)
        item.setBrush(QBrush(color))
        pen = QPen(color.darker(130), 0.6)
    else:
        grey = QColor(220, 220, 220, 110)
        item.setBrush(QBrush(grey))
        pen = QPen(QColor(170, 170, 170), 0.5)
    pen.setCosmetic(True)
    item.setPen(pen)
    item.setZValue(-1)
    mat_name = getattr(material, "name", None) or "(unassigned)"
    area = region.area
    item.setToolTip(
        f"<b>Region</b><br>Material: {mat_name}<br>Area: {area:.2f} m²"
    )
    return item


# ======================================================================
@dataclass
class DisplayOptions:
    """Per-layer visibility and styling flags, bound to the Display
    Options dialog. Toggling an attribute triggers a canvas re-render."""

    # Boundaries
    show_external: bool = True
    show_material: bool = True
    show_water_table: bool = True
    show_fem_mesh: bool = True
    show_piezometric: bool = True
    show_tension_crack: bool = True
    show_boundary_vertices: bool = True
    line_width: float = 1.5

    color_external: str = "#2c2c2c"
    color_material: str = "#8b4513"
    color_water_table: str = "#1e90ff"
    color_piezometric: str = "#4169e1"
    color_tension_crack: str = "#dc143c"

    # Miscellaneous
    show_ruler: bool = True
    show_grid: bool = True
    grayscale: bool = False
    scale_display_items_on_zoom: bool = True
    show_support_face_plates: bool = True
    show_coordinates_last_vertex: bool = False
    # v0.1.15 — visibility toggles for non-boundary entity types
    show_supports: bool = True
    show_loads: bool = True
    show_selected_support_force: bool = True   # force-direction overlay

    # Stress / Mesh (future FEM overlay)
    show_mesh: bool = False
    show_node_numbers: bool = False
    show_element_numbers: bool = False

    # Water / hydraulic overlays
    show_water_pressure_grid: bool = False
    show_flow_vectors: bool = False
    show_ponded_water: bool = True
    ponded_water_fill: bool = False
    ponded_water_hatch: bool = True

    # Boundary conditions (FEM)
    show_boundary_conditions: bool = True
    show_boundary_condition_values: bool = True


# ======================================================================
class CanvasView(QGraphicsView):
    """Interactive 2D view over the geotechnical model."""

    cursor_moved = Signal(float, float)
    status_message = Signal(str)
    tool_mode_changed = Signal(object)

    # v0.1.2 — interactive editing signals
    boundary_drawn = Signal(object)
    boundary_clicked = Signal(int)
    vertex_moved = Signal(int, int, float, float)
    vertex_inserted = Signal(int, int, float, float)
    vertex_deleted = Signal(int, int)
    point_picked = Signal(float, float)
    # v0.1.8 — emitted after the user clicks two points (distributed loads)
    segment_picked = Signal(float, float, float, float)
    # v0.1.8 — load right-click action (action, kind, index)
    load_action_requested = Signal(str, str, int)
    # v0.1.9 — emitted on Move Boundary drag release (boundary_idx, dx, dy)
    boundary_dragged = Signal(int, float, float)
    # v0.1.9 — right-click on empty area / region (x, y, global_pos for menu)
    canvas_right_click_xy = Signal(float, float, object)
    # v0.1.9 — right-click context menu actions (action_name, target_idx)
    boundary_action_requested = Signal(str, int)
    vertex_action_requested = Signal(str, int, int)  # action, b_idx, v_idx
    # v0.1.14 — emitted when a support is left-clicked (Delete Support)
    support_clicked = Signal(int)        # index in project.supports
    # v0.1.14 — right-click on a support (action, support_idx)
    support_action_requested = Signal(str, int)

    # v0.1.12 — generic scene-coordinate signals for the Interpret window
    # (Query Slice Data, hover preview of slip surfaces over a grid).
    # These fire on every left click / mouse move when the canvas is in
    # SELECT mode and Interpret has connected to them.
    scene_clicked = Signal(float, float)
    scene_hovered = Signal(float, float)

    # v0.1.3 — snap / drawing signals
    snap_changed = Signal(object)           # emits SnapResult
    drawing_state_changed = Signal(bool)    # True while a draw is in progress
    vertex_drag_finished = Signal(int, object)  # (boundary_idx, Boundary snapshot BEFORE drag)

    # v0.1.4 — raw canvas click (scene coords) emitted in ASSIGN_MATERIAL mode
    canvas_click_xy = Signal(float, float)

    # ------------------------------------------------------------------
    def __init__(self, project: Project | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self.setBackgroundBrush(QBrush(QColor("#fafafa")))

        # Flip Y so positive Y is up (engineering convention)
        t = QTransform()
        t.scale(1.0, -1.0)
        self.setTransform(t)

        # State
        self.project: Project | None = None
        self._snap_settings = SnapSettings()
        self.snap_engine = SnapEngine(self._snap_settings)
        self.display_options = DisplayOptions()
        self._result_items: list = []

        # Tool-mode / interaction
        self._tool_mode = ToolMode.SELECT
        self._panning = False
        self._pan_last_pos = QPointF()
        self._zw_rubber: Optional[QGraphicsRectItem] = None
        self._zw_start_scene: Optional[QPointF] = None

        # v0.1.2 — interactive drawing state
        self._draw_points: list[tuple[float, float]] = []
        self._draw_preview_items: list = []
        # Vertex dragging
        self._dragging_vertex: Optional[tuple[int, int]] = None  # (boundary_idx, vertex_idx)
        # v0.1.9 — interactive boundary drag (click + hold + release)
        self._dragging_boundary: Optional[int] = None  # boundary index
        self._drag_boundary_origin: Optional[tuple[float, float]] = None
        self._drag_boundary_orig_verts: Optional[list[tuple[float, float]]] = None
        self._vertex_drag_start_boundary = None  # pre-drag snapshot for undo

        # v0.1.3 — snap state for visual overlay
        self._last_snap = None
        self._last_cursor_scene: Optional[QPointF] = None

        # v0.1.4 — selection filter (set by MainWindow when changed)
        self.selection_filter = None

        if project is not None:
            self.set_project(project)

        # v0.1.15 — flag so the first real showEvent re-runs zoom_all
        # once the widget has a valid size (avoids the start-up render
        # glitch where fitInView ran against a 0×0 viewport).
        self._did_initial_fit = False

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # The first time the canvas is actually shown it finally has a
        # real viewport size. Re-fit so the grid/ruler use a sane scale.
        if not getattr(self, "_did_initial_fit", False):
            self._did_initial_fit = True
            self.zoom_all()
            self.viewport().update()

    # ==================================================================
    # Public API
    # ==================================================================
    def set_project(self, project: Project) -> None:
        self.project = project
        project.add_listener(lambda evt: self.refresh_scene())
        self.refresh_scene()
        self.zoom_all()

    def refresh(self) -> None:
        """Alias for :meth:`refresh_scene`.

        v0.1.17 — several MainWindow flows (material assignment, load
        editing, …) call ``canvas.refresh()``; without this alias those
        calls raised ``AttributeError`` inside Qt slots, silently
        aborting the rest of the handler (status messages, etc.).
        """
        self.refresh_scene()

    @property
    def snap_settings(self) -> SnapSettings:
        return self._snap_settings

    def set_display_options(self, opts: DisplayOptions) -> None:
        self.display_options = opts
        self.refresh_scene()

    # ----- Tool mode management ---------------------------------------
    @property
    def tool_mode(self) -> ToolMode:
        return self._tool_mode

    def set_tool_mode(self, mode: ToolMode) -> None:
        # Cancel any active rubber-band
        if self._zw_rubber is not None:
            self.scene().removeItem(self._zw_rubber)
            self._zw_rubber = None
            self._zw_start_scene = None

        self._tool_mode = mode
        self.setDragMode(
            QGraphicsView.RubberBandDrag if mode == ToolMode.SELECT
            else QGraphicsView.NoDrag
        )
        shape = getattr(Qt, mode.cursor_name, Qt.ArrowCursor)
        self.viewport().setCursor(QCursor(shape))

        hint = mode.status_message
        if hint:
            self.status_message.emit(hint)
        self.tool_mode_changed.emit(mode)

    # ==================================================================
    # Scene refresh
    # ==================================================================
    def refresh_scene(self) -> None:
        scene = self.scene()
        scene.clear()
        self._result_items.clear()
        if self.project is None:
            return

        xmin, ymin, xmax, ymax = self.project.bounding_box()
        pad = max((xmax - xmin) * 0.5, (ymax - ymin) * 0.5, 10.0)
        scene.setSceneRect(
            QRectF(xmin - pad, ymin - pad,
                   (xmax - xmin) + 2 * pad, (ymax - ymin) + 2 * pad)
        )

        opts = self.display_options
        lw = opts.line_width

        # Background grayscale
        self.setBackgroundBrush(
            QBrush(QColor("#e8e8e8" if opts.grayscale else "#fafafa"))
        )

        # v0.1.6 — Material regions.
        # Regions emerge from the planar subdivision of
        # External ∪ Material Boundaries. Water Table, Piezometric Lines,
        # Tension Crack and Drawdown do NOT split regions — they are
        # overlays drawn on top. Material assignment is resolved from
        # the user's click history, with the first material of the
        # project as the Slide-style default.
        if opts.show_material:
            try:
                regions = self.project.resolve_regions()
            except Exception:  # noqa: BLE001
                regions = []
            for region in regions:
                mid = getattr(region, "material_id", None)
                mat = self.project.material_by_id(mid) if mid else None
                item = _region_to_item(region, mat)
                if item is not None:
                    scene.addItem(item)

        # Boundary outlines, with per-type visibility & colour override
        for b in self.project.boundaries:
            if not b.visible:
                continue
            if not self._type_visible(b.btype):
                continue
            override = self._color_for_type(b.btype)
            item = BoundaryItem(b)
            if override:
                pen = QPen(QColor(override), lw)
                pen.setCosmetic(True)
                item.setPen(pen)
            scene.addItem(item)
            if opts.show_boundary_vertices:
                for v in b.vertices:
                    scene.addItem(VertexHandleItem(v.x, v.y))

        # v0.1.7 — Tension Crack zone (vertical-line pattern, blue/gray)
        for tc in self.project.boundaries:
            if tc.btype != BoundaryType.TENSION_CRACK:
                continue
            if not self._type_visible(tc.btype):
                continue
            self._draw_tension_crack_pattern(scene, tc)

        # v0.1.61 — ponded water: the region between the ground and a
        # water surface drawn ABOVE it. The three display flags below have
        # existed since v0.1.23 and were read by nobody, so the checkbox
        # in Display Options did nothing at all.
        if getattr(opts, "show_ponded_water", True):
            self._draw_ponded_water(scene, opts)

        # v0.1.9 — letters W / P / D on water surfaces
        for b in self.project.boundaries:
            if not b.visible or not self._type_visible(b.btype):
                continue
            if b.btype == BoundaryType.WATER_TABLE:
                self._draw_water_surface_label(scene, b, "W", QColor("#0a72d4"))
            elif b.btype == BoundaryType.PIEZOMETRIC:
                self._draw_water_surface_label(scene, b, "P", QColor("#0a72d4"))
            elif b.btype == BoundaryType.DRAWDOWN:
                self._draw_water_surface_label(scene, b, "D", QColor("#0a72d4"))

        # v0.1.25 — FE mesh (seepage analysis): element edges drawn
        # thin and grey beneath everything else, so the model geometry
        # stays readable on top of the mesh.
        fem = getattr(self.project, "fem_mesh", None)
        if fem is not None and getattr(opts, "show_fem_mesh", True) \
                and fem.element_count:
            mpen = QPen(QColor(120, 140, 160, 170), 0)
            mpen.setCosmetic(True)
            drawn = set()
            for e in fem.elements:
                a, b, c = e.nodes
                for u, v in ((a, b), (b, c), (c, a)):
                    key = (u, v) if u < v else (v, u)
                    if key in drawn:
                        continue
                    drawn.add(key)
                    n1, n2 = fem.nodes[u], fem.nodes[v]
                    it = scene.addLine(n1.x, n1.y, n2.x, n2.y, mpen)
                    it.setZValue(-5)

        # v0.1.23 — Water Pressure Grid points (blue markers + value)
        wpg = getattr(self.project, "water_pressure_grid", None)
        if wpg is not None and wpg.points:
            from PySide6.QtGui import QPolygonF
            pen = QPen(QColor("#0a72d4"), 0)
            pen.setCosmetic(True)
            brush = QBrush(QColor(30, 120, 220, 120))
            for (px, py, val) in wpg.points:
                tri = QPolygonF([
                    QPointF(px - 0.8, py + 0.9),
                    QPointF(px + 0.8, py + 0.9),
                    QPointF(px, py - 0.4),
                ])
                it = scene.addPolygon(tri, pen, brush)
                it.setZValue(18)
                lbl = scene.addText(f"{val:g}")
                lbl.setDefaultTextColor(QColor("#0a72d4"))
                f = lbl.font()
                f.setPointSizeF(6.5)
                lbl.setFont(f)
                lbl.setPos(px + 0.9, py + 2.2)
                lbl.setTransform(
                    lbl.transform().scale(1.0, -1.0), False)
                lbl.setZValue(18)

        # v0.1.8 — Slip-circle search grid (user-defined or auto)
        self._draw_slip_search_grid(scene)

        # Loads
        for load in self.project.distributed_loads:
            scene.addItem(DistributedLoadItem(load))
        for load in self.project.line_loads:
            scene.addItem(LineLoadItem(load))

        # Supports — v0.1.15 honours DisplayOptions.show_supports
        if self.display_options.show_supports:
            from ogr_core.support import support_registry
            reg = support_registry()
            # Build lookup of per-project support type defs (with their
            # tuned parameter values), keyed by TYPE_ID. Used for tooltip
            # force-diagram preview.
            proj_types = {
                st.TYPE_ID: st for st in
                getattr(self.project, "support_types", []) or []
            }
            for s in self.project.supports:
                display = reg[s.type_id].DISPLAY_NAME if s.type_id in reg else s.type_id
                type_obj = proj_types.get(s.type_id)
                scene.addItem(SupportItem(s, display, support_type_obj=type_obj))

        self.viewport().update()

    def _type_visible(self, btype: BoundaryType) -> bool:
        opts = self.display_options
        return {
            BoundaryType.EXTERNAL: opts.show_external,
            BoundaryType.MATERIAL: opts.show_material,
            BoundaryType.WATER_TABLE: opts.show_water_table,
            BoundaryType.PIEZOMETRIC: opts.show_piezometric,
            BoundaryType.DRAWDOWN: True,
            BoundaryType.TENSION_CRACK: opts.show_tension_crack,
        }.get(btype, True)

    def _color_for_type(self, btype: BoundaryType) -> Optional[str]:
        opts = self.display_options
        return {
            BoundaryType.EXTERNAL: opts.color_external,
            BoundaryType.MATERIAL: opts.color_material,
            BoundaryType.WATER_TABLE: opts.color_water_table,
            BoundaryType.PIEZOMETRIC: opts.color_piezometric,
            BoundaryType.TENSION_CRACK: opts.color_tension_crack,
        }.get(btype)

    # ------------------------------------------------------------------
    def display_search_result(
        self,
        search_result,
        selected_id: str | None = None,
        hover_id: str | None = None,
        hover_surface_dict: dict | None = None,
        surface_mode: str = "minimum",
        fos_filter: tuple | None = None,
        query_ids=None,
        error_filter: str | None = None,
        invalid_reason_fn=None,
    ) -> None:
        """Render the search result on the canvas.

        v0.1.12 — supports selection and hover highlights:
            - ``selected_id``  → surface drawn in PURPLE (clicked in list)
            - ``hover_id``     → surface drawn dashed grey (transient)
            - ``hover_surface_dict`` → render an arbitrary surface for
              hover (used when previewing a grid centre's slip-circle
              that is not yet in top_n)
            - ``critical``     → drawn in RED (lowest FoS overall)

        v0.1.20 — ``surface_mode`` selects how many surfaces are drawn,
        mirroring the Interpret "Data" menu:
            - ``"global_min"`` → heatmap + the critical surface only
            - ``"minimum"``    → heatmap + the lowest-FoS surface AT EACH
                                 slip-centre grid point
            - ``"all"``        → heatmap + every valid surface

        v0.1.82 — three corrections, all of them to what the modes mean:

        * *Minimum Surfaces* used to be ``top_n(30)``, the thirty lowest
          factors of safety in the whole result. Those thirty come from a
          handful of neighbouring centres, so the picture said nothing
          about the rest of the grid. The documented meaning is one
          surface per grid centre — the minimum AT that centre — which is
          also what makes the surfaces and the contoured grid two views of
          the same numbers.
        * *All Surfaces* drew the lowest factors of safety FIRST, so every
          later, higher-FoS surface painted over them: the one thing the
          reader needs to see ended up underneath. Drawing runs from the
          highest factor of safety down, so the lowest are drawn last and
          stay visible.
        * Surfaces are coloured by their factor of safety through
          ``colour_fn`` instead of a single green, so the cloud carries
          information rather than just extent.

        ``fos_filter`` is the Filter Surfaces state: ``(lo, hi, limit)``,
        applied to *minimum* and *all*. The critical surface is never
        filtered away — losing the global minimum because a filter is
        active is how a reader ends up reading the wrong number.
        """
        scene = self.scene()
        for item in self._result_items:
            if item.scene() is scene:
                scene.removeItem(item)
        self._result_items.clear()

        if search_result is None:
            return

        # FoS heat-map of the centres grid (Slide-style)
        self._draw_fos_heatmap(scene, search_result)

        critical_id = None
        if search_result.critical:
            critical_id = search_result.critical.surface.to_dict().get("id")
        colour_fn = getattr(self, "_contour_colour_fn", None)

        # "Surfaces With Error Code" — a view of its own, not a filter on
        # top of the normal one: the reference shows ONLY the invalid
        # surfaces of the chosen kind, in purple, with the valid ones
        # hidden, because the question being asked is "what failed here",
        # not "how does this compare".
        if error_filter is not None and invalid_reason_fn is not None:
            self._draw_invalid_surfaces(scene, search_result, error_filter,
                                        invalid_reason_fn)
            self.viewport().update()
            return

        # Choose the set of surfaces to render according to the mode.
        if surface_mode == "global_min":
            surfaces = [search_result.critical] if search_result.critical else []
        elif surface_mode == "all":
            surfaces = list(search_result.valid())
        else:  # "minimum" (default)
            surfaces = self._minimum_per_centre(search_result)

        if surface_mode in ("minimum", "all"):
            surfaces = self._apply_fos_filter(surfaces, fos_filter,
                                              critical_id)

        # A Query is something the user deliberately singled out, so it
        # survives the display mode and the filter alike. Without this,
        # switching to Global Minimum silently erased it.
        query_ids = set(query_ids or ())
        if query_ids:
            shown = {r.surface.to_dict().get("id") for r in surfaces}
            surfaces = surfaces + [
                r for r in search_result.valid()
                if r.surface.to_dict().get("id") in query_ids - shown]

        # Highest factor of safety first, so the lowest are drawn LAST and
        # remain visible under everything else.
        surfaces = sorted(surfaces, key=lambda r: -r.fos)
        self.last_surface_count = len(surfaces)

        faint = (surface_mode == "all")
        for r in surfaces:
            sd = r.surface.to_dict()
            sid = sd.get("id")
            is_crit = (sid == critical_id)
            is_sel = (selected_id is not None and sid == selected_id)
            is_qry = (sid in query_ids)
            is_hov = (
                hover_id is not None
                and sid == hover_id
                and not is_crit
                and not is_sel
            )
            item = SlipSurfaceItem(
                sd, r.fos,
                is_critical=is_crit,
                is_selected=is_sel,
                is_hover=is_hov,
                is_query=is_qry,
                colour_fn=colour_fn,
            )
            # In "all" mode the cloud is context, so it is drawn thin and
            # translucent — but it keeps its FoS colour, which is the
            # information the mode exists to show.
            if faint and not (is_crit or is_sel or is_qry):
                item.setOpacity(0.45)
                item.setZValue(1.0)
            scene.addItem(item)
            self._result_items.append(item)

        # Radial lines: the reference draws them for the Global Minimum
        # and for every Query. They locate the centre of rotation and give
        # a Query something clickable when the arc is buried.
        radii_for = list(query_ids)
        if search_result.critical is not None and critical_id is not None:
            radii_for.append(critical_id)
        for r in surfaces:
            sd = r.surface.to_dict()
            if sd.get("id") not in radii_for:
                continue
            colour = "#e63946" if sd.get("id") == critical_id else "#000000"
            radii = SlipRadiiItem(sd, colour=colour)
            scene.addItem(radii)
            self._result_items.append(radii)

        # Hover preview for an arbitrary surface (e.g. a grid centre
        # whose circle is NOT among those drawn)
        if hover_surface_dict is not None:
            fos_h = hover_surface_dict.get("_hover_fos", float("inf"))
            preview = SlipSurfaceItem(
                hover_surface_dict, fos_h,
                is_critical=False, is_selected=False, is_hover=True,
            )
            scene.addItem(preview)
            self._result_items.append(preview)
            radii = SlipRadiiItem(hover_surface_dict, colour="#505050")
            scene.addItem(radii)
            self._result_items.append(radii)

        self.viewport().update()

    # ------------------------------------------------------------------
    def _draw_invalid_surfaces(self, scene, search_result, reason,
                               invalid_reason_fn) -> None:
        """Draw the invalid surfaces of one error code, in purple."""
        drawn = 0
        for ev in search_result.evaluations:
            if invalid_reason_fn(ev) != reason:
                continue
            sd = ev.surface.to_dict()
            # A surface rejected before it was ever sliced has no
            # endpoints, so there is nothing to draw for it.
            if sd.get("type") == "circle" and (sd.get("x_left") is None
                                               or sd.get("x_right") is None):
                continue
            item = SlipSurfaceItem(sd, ev.fos)
            pen = item.pen()
            pen.setColor(QColor("#7d3c98"))
            pen.setWidthF(1.4)
            item.setPen(pen)
            item.setToolTip(f"{reason}")
            scene.addItem(item)
            self._result_items.append(item)
            drawn += 1
        self.last_surface_count = drawn

    @staticmethod
    def _minimum_per_centre(search_result) -> list:
        """The lowest-FoS surface at each slip-centre grid point.

        Non-circular results have no centres grid, so they fall back to
        every valid surface — which is what the reference does too: the
        Minimum Surfaces option is documented as applying to a circular
        Grid Search only.
        """
        best: dict = {}
        loose: list = []
        for r in search_result.valid():
            sd = r.surface.to_dict()
            cx = sd.get("centre_x")
            cy = sd.get("centre_y")
            if cx is None or cy is None:
                loose.append(r)
                continue
            key = (round(cx, 6), round(cy, 6))
            if key not in best or r.fos < best[key].fos:
                best[key] = r
        return list(best.values()) + loose

    @staticmethod
    def _apply_fos_filter(surfaces: list, fos_filter, critical_id) -> list:
        """Filter by factor-of-safety range and/or by lowest-N.

        The critical surface always survives: a filter is a way of looking
        at the result, not a way of hiding its answer.
        """
        if not fos_filter:
            return surfaces
        lo, hi, limit = fos_filter
        kept = [r for r in surfaces
                if (lo is None or r.fos >= lo)
                and (hi is None or r.fos <= hi)]
        if limit:
            kept = sorted(kept, key=lambda r: r.fos)[:int(limit)]
        if critical_id is not None and not any(
                r.surface.to_dict().get("id") == critical_id for r in kept):
            crit = next((r for r in surfaces
                         if r.surface.to_dict().get("id") == critical_id),
                        None)
            if crit is not None:
                kept.append(crit)
        return kept

    # ==================================================================
    # v0.1.8 — FoS heatmap on the search grid
    # ==================================================================
    def _draw_fos_heatmap(self, scene, search_result) -> None:
        """Draw a coloured grid showing min-FoS per grid centre.

        Colour scheme (Slide-style):
            FoS ≤ 1.0   → red
            1.0 < FoS ≤ 1.5 → orange
            1.5 < FoS ≤ 2.0 → yellow
            2.0 < FoS ≤ 3.0 → light green
            3.0 < FoS       → dark grey
        """
        from PySide6.QtGui import QBrush, QPen
        from PySide6.QtWidgets import QGraphicsRectItem

        valid = search_result.valid()
        if not valid:
            return

        # Group by (round(xc, 3), round(yc, 3)) → keep min FoS
        from collections import defaultdict
        bucket: dict[tuple[float, float], float] = defaultdict(
            lambda: float("inf")
        )
        for r in valid:
            sd = r.surface.to_dict()
            cx = sd.get("centre_x") or sd.get("center_x")
            cy = sd.get("centre_y") or sd.get("center_y")
            if cx is None or cy is None:
                continue
            key = (round(cx, 3), round(cy, 3))
            if r.fos < bucket[key]:
                bucket[key] = r.fos

        if not bucket:
            return

        # Determine grid spacing from sorted unique x's and y's
        xs = sorted({k[0] for k in bucket.keys()})
        ys = sorted({k[1] for k in bucket.keys()})
        if len(xs) < 2 or len(ys) < 2:
            return
        # Use the median spacing for cell size (robust to gaps)
        def _med_diff(arr):
            diffs = [arr[i + 1] - arr[i] for i in range(len(arr) - 1) if arr[i + 1] > arr[i]]
            if not diffs:
                return 1.0
            diffs.sort()
            return diffs[len(diffs) // 2]
        cell_w = _med_diff(xs)
        cell_h = _med_diff(ys)

        # Paint each cell
        no_pen = QPen(Qt.NoPen)
        for (xc, yc), fos in bucket.items():
            # v0.1.50 — the colour function can be overridden by the
            # contour settings; falling back to the built-in convention
            # keeps every other caller working unchanged.
            fn = getattr(self, "_contour_colour_fn", None)
            color = QColor(fn(fos)) if fn is not None \
                else self._fos_to_color(fos)
            color.setAlpha(200)  # semi-transparent so the model shows
            rect = QGraphicsRectItem(
                xc - cell_w / 2,
                yc - cell_h / 2,
                cell_w,
                cell_h,
            )
            rect.setPen(no_pen)
            rect.setBrush(QBrush(color))
            rect.setZValue(0.5)  # behind the slip surface lines
            rect.setToolTip(f"Centre ({xc:.2f}, {yc:.2f}) — FoS = {fos:.3f}")
            scene.addItem(rect)
            self._result_items.append(rect)

    def set_contour_colour_fn(self, fn) -> None:
        """Override the value-to-colour mapping of the result heatmap.

        Set to None to restore the built-in convention.
        """
        self._contour_colour_fn = fn

    @staticmethod
    def _fos_to_color(fos: float):
        """Map an FoS to a colour using the Slide convention."""
        if fos <= 1.0:
            return QColor(220, 30, 30)        # red
        if fos <= 1.25:
            return QColor(240, 100, 40)       # red-orange
        if fos <= 1.5:
            return QColor(245, 160, 60)       # orange
        if fos <= 1.75:
            return QColor(245, 215, 80)       # yellow
        if fos <= 2.0:
            return QColor(200, 220, 100)      # yellow-green
        if fos <= 2.5:
            return QColor(140, 200, 100)      # green
        if fos <= 3.0:
            return QColor(100, 160, 100)      # dark green
        return QColor(110, 110, 120)          # dark gray (very stable)

    # ==================================================================
    # v0.1.9 — Vertex right-click context menu
    # ==================================================================
    def _show_vertex_context_menu(self, global_pos, hit) -> None:
        """Popup menu over a vertex: Move / Insert before / Delete."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        bi, vi = hit
        if not (0 <= bi < len(self.project.boundaries)):
            return
        b = self.project.boundaries[bi]
        if not (0 <= vi < len(b.polyline.vertices)):
            return
        v = b.polyline.vertices[vi]

        menu = QMenu(self)
        info = QAction(
            f"Vertex {vi + 1}/{len(b.polyline.vertices)} — "
            f"({v.x:.3f}, {v.y:.3f})", self,
        )
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        for label, action_id in (
            ("Move Vertex", "move"),
            ("Insert Vertex (after)", "insert"),
            ("Edit Coordinates…", "edit_coords"),
            ("Delete Vertex", "delete"),
        ):
            a = QAction(label, self)
            a.triggered.connect(
                lambda _checked=False, aid=action_id:
                self.vertex_action_requested.emit(aid, bi, vi)
            )
            menu.addAction(a)
        menu.exec(global_pos)

    # ==================================================================
    # v0.1.9 — Boundary (line) right-click context menu
    # ==================================================================
    def _show_boundary_context_menu(self, global_pos, bidx: int) -> None:
        """Popup menu over a boundary line."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        if not (0 <= bidx < len(self.project.boundaries)):
            return
        b = self.project.boundaries[bidx]

        menu = QMenu(self)
        info = QAction(f"{b.btype.display_name} — {b.name}", self)
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        # Common actions
        common_actions = [
            ("Move Boundary", "move_boundary"),
            ("Edit Coordinates…", "edit_coords"),
            ("Convert Boundary…", "convert"),
            ("Delete Boundary", "delete"),
        ]
        for label, aid in common_actions:
            a = QAction(label, self)
            a.triggered.connect(
                lambda _c=False, aid=aid: self.boundary_action_requested.emit(aid, bidx)
            )
            menu.addAction(a)

        # Type-specific extras
        if b.btype == BoundaryType.TENSION_CRACK:
            menu.addSeparator()
            a = QAction("Define Tension Crack…", self)
            a.triggered.connect(
                lambda _c=False: self.boundary_action_requested.emit(
                    "define_tension_crack", bidx,
                )
            )
            menu.addAction(a)
        elif b.btype == BoundaryType.EXTERNAL:
            menu.addSeparator()
            for label, aid in (
                ("Expand / Shrink…", "expand_shrink"),
                ("Change Slope Angle…", "change_slope"),
            ):
                a = QAction(label, self)
                a.triggered.connect(
                    lambda _c=False, aid=aid: self.boundary_action_requested.emit(aid, bidx)
                )
                menu.addAction(a)

        menu.exec(global_pos)

    # ==================================================================
    # v0.1.15 — Support right-click context menu
    # ==================================================================
    def _show_support_context_menu(self, global_pos, sidx: int) -> None:
        """Popup over a support: Properties / Stretch / Convert / Delete."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        if sidx < 0 or sidx >= len(self.project.supports):
            return
        s = self.project.supports[sidx]
        menu = QMenu(self)
        from ogr_core.support import support_registry
        reg = support_registry()
        type_name = reg[s.type_id].DISPLAY_NAME if s.type_id in reg else s.type_id

        info = QAction(f"Support — {s.name or type_name}", self)
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        for label, aid in (
            ("Properties…", "support_properties"),
            ("Stretch", "support_stretch"),
            ("Modify Pattern…", "support_modify_pattern"),
            ("Delete", "support_delete"),
        ):
            a = QAction(label, self)
            a.triggered.connect(
                lambda _c=False, aid=aid: self.support_action_requested.emit(
                    aid, sidx,
                )
            )
            menu.addAction(a)

        menu.exec(global_pos)

    # ==================================================================
    # v0.1.8 — Load right-click context menu
    # ==================================================================
    def _show_load_context_menu(self, global_pos, hit) -> None:
        """Popup menu over a load (Modify / Delete)."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        kind, idx = hit
        menu = QMenu(self)
        if kind == "distributed":
            load = self.project.distributed_loads[idx]
            label = f"Distributed Load — {load.magnitude_1:.1f} kN/m²"
        else:
            load = self.project.line_loads[idx]
            label = f"Line Load — {load.magnitude:.1f} kN/m"

        info = QAction(label, self)
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        act_modify = QAction("Modify…", self)
        act_modify.triggered.connect(
            lambda: self.load_action_requested.emit("modify", kind, idx)
        )
        menu.addAction(act_modify)

        act_delete = QAction("Delete", self)
        act_delete.triggered.connect(
            lambda: self.load_action_requested.emit("delete", kind, idx)
        )
        menu.addAction(act_delete)
        menu.exec(global_pos)

    # ==================================================================
    # v0.1.4 — Right-click drawing context menu
    # ==================================================================
    def _show_drawing_context_menu(self, global_pos) -> None:
        """Popup menu shown while the user is drawing a boundary."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        menu = QMenu(self)
        mode = self._tool_mode
        can_close = (
            mode.draws_closed_polygon and len(self._draw_points) >= 3
        )
        can_finish = len(self._draw_points) >= 2
        can_undo = bool(self._draw_points)

        act_done = QAction("Done", self)
        act_done.setEnabled(can_finish)
        act_done.triggered.connect(lambda: self._finish_drawing())
        menu.addAction(act_done)

        act_close = QAction("Close Boundary", self)
        act_close.setEnabled(can_close)
        act_close.triggered.connect(
            lambda: self._finish_drawing(force_close=True)
        )
        menu.addAction(act_close)

        act_undo = QAction("Undo last vertex", self)
        act_undo.setEnabled(can_undo)
        act_undo.triggered.connect(self._undo_last_point)
        menu.addAction(act_undo)

        menu.addSeparator()

        # Snap toggles (show tick if active)
        s = self.snap_settings
        for label, attr in [("Snap", "snap"), ("Ortho", "ortho"),
                            ("OSnap", "osnap")]:
            a = QAction(label, self)
            a.setCheckable(True)
            a.setChecked(getattr(s, attr))

            def _toggler(checked: bool, name=attr) -> None:
                setattr(self.snap_settings, name, checked)
                self.viewport().update()

            a.toggled.connect(_toggler)
            menu.addAction(a)

        menu.addSeparator()

        act_coords = QAction("Coordinate Table...", self)
        act_coords.triggered.connect(self._show_coord_table_dialog)
        menu.addAction(act_coords)

        menu.addSeparator()

        act_cancel = QAction("Cancel", self)
        act_cancel.triggered.connect(self._cancel_drawing)
        menu.addAction(act_cancel)

        menu.exec(global_pos)

    def _undo_last_point(self) -> None:
        if self._draw_points:
            self._draw_points.pop()
            self._update_draw_preview(
                live_cursor=(self._last_cursor_scene.x(),
                              self._last_cursor_scene.y())
                if self._last_cursor_scene is not None else None
            )
            self.viewport().update()

    def _show_coord_table_dialog(self) -> None:
        """Open the spreadsheet coord editor against the in-progress draw."""
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
            QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Vertex Coordinate Table"))
        dlg.resize(340, 400)
        root = QVBoxLayout(dlg)

        table = QTableWidget(len(self._draw_points), 2)
        table.setHorizontalHeaderLabels(["X", "Y"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r, (x, y) in enumerate(self._draw_points):
            table.setItem(r, 0, QTableWidgetItem(f"{x:.4f}"))
            table.setItem(r, 1, QTableWidgetItem(f"{y:.4f}"))
        root.addWidget(table, 1)

        row_btns = QHBoxLayout()
        btn_add = QPushButton(tr("Add Row"))
        btn_del = QPushButton(tr("Delete Row"))
        def _add():
            r = table.currentRow()
            r = r + 1 if r >= 0 else table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem("0.0000"))
            table.setItem(r, 1, QTableWidgetItem("0.0000"))
        def _del():
            r = table.currentRow()
            if r >= 0:
                table.removeRow(r)
        btn_add.clicked.connect(_add)
        btn_del.clicked.connect(_del)
        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_del)
        row_btns.addStretch(1)
        root.addLayout(row_btns)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        root.addWidget(btns)

        if dlg.exec() != QDialog.Accepted:
            return
        new_pts: list[tuple[float, float]] = []
        for r in range(table.rowCount()):
            try:
                x = float(table.item(r, 0).text())
                y = float(table.item(r, 1).text())
            except (ValueError, AttributeError):
                continue
            new_pts.append((x, y))
        self._draw_points = new_pts
        self._update_draw_preview()
        self.viewport().update()

    # ==================================================================
    # v0.1.3 — Public API for manual-coordinate input
    # ==================================================================
    def add_manual_point(self, x: float, y: float) -> bool:
        """Add (x, y) to the in-progress drawing, or no-op.

        Called by the status-bar coordinate input field. Returns True
        if the point was added (a drawing mode was active), else False.
        """
        if not self._tool_mode.is_drawing_boundary:
            return False
        self._draw_points.append((x, y))
        self._update_draw_preview()
        return True

    def is_drawing(self) -> bool:
        return bool(self._draw_points) and self._tool_mode.is_drawing_boundary

    # ==================================================================
    # v0.1.2 — interactive drawing / picking helpers
    # ==================================================================
    def _snap_point(self, scene_pt: QPointF):
        """Resolve the cursor through the full snap engine.

        Returns a (QPointF, SnapResult) tuple. The engine already handles
        vertex / line / grid / ortho / osnap. We also cache the snap
        result so that :meth:`drawForeground` can render the glyph.

        v0.1.4: the in-progress polyline (``_draw_points``) is also
        passed as a pseudo-boundary so the user can snap to their own
        vertices while drawing — critical for closing polygons exactly.
        """
        from PySide6.QtCore import QPointF as _QP
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        # Set the reference point for ortho
        if self._draw_points and self._tool_mode.is_drawing_boundary:
            lx, ly = self._draw_points[-1]
            self.snap_engine.set_reference(Vertex(lx, ly))
        else:
            self.snap_engine.set_reference(None)

        # Keep grid spacing aligned with what the user sees
        ppu = self._pixels_per_unit()
        if ppu > 0:
            step = nice_step(60.0 / ppu)
            self.snap_engine.settings.grid_h = step
            self.snap_engine.settings.grid_v = step

        cursor_v = Vertex(scene_pt.x(), scene_pt.y())
        boundaries = list(self.project.boundaries) if self.project else []

        # v0.1.4 — include in-progress draw points as a pseudo-boundary
        if self._draw_points:
            draft_verts = [Vertex(x, y) for (x, y) in self._draw_points]
            draft_pline = Polyline(vertices=draft_verts, closed=False)
            draft_b = Boundary(polyline=draft_pline,
                                btype=BoundaryType.EXTERNAL)
            boundaries = boundaries + [draft_b]

        result = self.snap_engine.resolve(cursor_v, boundaries, ppu)
        self._last_snap = result
        self.snap_changed.emit(result)

        return _QP(result.point.x, result.point.y), result

    def _snap_xy(self, scene_pt: QPointF) -> QPointF:
        """Convenience wrapper that returns only the snapped QPointF."""
        p, _ = self._snap_point(scene_pt)
        return p

    def _finish_drawing(self, *, force_close: bool = False) -> None:
        """Build a Boundary from the collected draw points and emit.

        When ``force_close=True`` or the drawing mode requires a closed
        polygon (External / Material), the first and last point are
        ensured to be distinct and the polyline is flagged closed.
        """
        if len(self._draw_points) < 2:
            self._cancel_drawing()
            return
        mode = self._tool_mode
        btype = mode.boundary_type_drawn
        if btype is None:
            self._cancel_drawing()
            return

        from ogr_core.geometry import Boundary, Polyline, Vertex

        closed = mode.draws_closed_polygon or force_close
        pts = list(self._draw_points)

        # If closed and the last point is the same as the first, drop
        # the duplicate — the Polyline "closed" flag handles the seam.
        if closed and len(pts) >= 3:
            x0, y0 = pts[0]
            xN, yN = pts[-1]
            if abs(xN - x0) < 1e-9 and abs(yN - y0) < 1e-9:
                pts = pts[:-1]

        if closed and len(pts) < 3:
            self.status_message.emit(
                "Need at least 3 distinct points to close a boundary."
            )
            # Don't clear — let the user keep drawing
            return

        vertices = [Vertex(x, y) for (x, y) in pts]
        pline = Polyline(vertices=vertices, closed=closed)
        if closed:
            try:
                pline.ensure_ccw()
            except Exception:  # noqa: BLE001
                pass
        boundary = Boundary(polyline=pline, btype=btype)
        self._clear_draw_preview()
        self._draw_points = []
        self._last_snap = None
        self.boundary_drawn.emit(boundary)
        self.set_tool_mode(ToolMode.SELECT)
        self.viewport().update()

    def _cancel_drawing(self) -> None:
        self._draw_points = []
        self._clear_draw_preview()
        self.status_message.emit("Drawing cancelled.")

    def _clear_draw_preview(self) -> None:
        scene = self.scene()
        for it in self._draw_preview_items:
            if it.scene() is scene:
                scene.removeItem(it)
        self._draw_preview_items.clear()

    def _update_draw_preview(self, live_cursor: Optional[tuple[float, float]] = None) -> None:
        """Redraw the in-progress polyline + a preview segment to the cursor."""
        from PySide6.QtCore import QLineF
        from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem

        scene = self.scene()
        self._clear_draw_preview()
        if not self._draw_points:
            return

        pen_solid = QPen(QColor("#e63946"), 1.8, Qt.SolidLine)
        pen_solid.setCosmetic(True)
        pen_dashed = QPen(QColor("#1e6fc5"), 1.5, Qt.DashLine)
        pen_dashed.setCosmetic(True)

        # Committed segments
        for i in range(len(self._draw_points) - 1):
            x1, y1 = self._draw_points[i]
            x2, y2 = self._draw_points[i + 1]
            ln = QGraphicsLineItem(x1, y1, x2, y2)
            ln.setPen(pen_solid)
            ln.setZValue(9)
            scene.addItem(ln)
            self._draw_preview_items.append(ln)

        # Committed vertex dots
        for x, y in self._draw_points:
            dot = QGraphicsEllipseItem(x - 0.3, y - 0.3, 0.6, 0.6)
            dot.setPen(QPen(QColor("#c0392b"), 0, Qt.NoPen))
            dot.setBrush(QBrush(QColor("#c0392b")))
            dot.setZValue(10)
            scene.addItem(dot)
            self._draw_preview_items.append(dot)

        # Rubber-band preview to cursor
        if live_cursor is not None:
            x1, y1 = self._draw_points[-1]
            x2, y2 = live_cursor
            ln = QGraphicsLineItem(x1, y1, x2, y2)
            ln.setPen(pen_dashed)
            ln.setZValue(9)
            scene.addItem(ln)
            self._draw_preview_items.append(ln)

    # ----- Hit testing --------------------------------------------------
    def _pick_boundary(self, x: float, y: float, tolerance_px: float = 8.0) -> int:
        """Return the index of the nearest boundary within tolerance, or -1.

        Respects :attr:`selection_filter`: boundaries whose type is
        disabled are skipped.
        """
        if self.project is None:
            return -1
        filt = self.selection_filter
        if filt is not None and not filt.boundaries:
            return -1
        px_per_unit = abs(self.transform().m11()) or 1.0
        tol = tolerance_px / px_per_unit

        best_idx = -1
        best_dist = float("inf")
        for i, b in enumerate(self.project.boundaries):
            verts = b.polyline.vertices
            n = len(verts)
            if n < 2:
                continue
            segs = n if b.polyline.closed else n - 1
            for j in range(segs):
                a = verts[j]
                c = verts[(j + 1) % n]
                d = _point_segment_distance(x, y, a.x, a.y, c.x, c.y)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
        return best_idx if best_dist <= tol else -1

    # v0.1.8 — pick a load (distributed or line) under the cursor.
    # Returns ('distributed', index) | ('line', index) | None.
    def _pick_load(self, x: float, y: float, tolerance_px: float = 10.0):
        try:
            px_per_unit = abs(self.transform().m11()) or 1.0
        except Exception:
            px_per_unit = 1.0
        tol = tolerance_px / max(px_per_unit, 1e-9)
        # Distributed loads: distance to the load segment
        for i, load in enumerate(self.project.distributed_loads):
            d = _dist_point_to_segment(
                x, y,
                load.start.x, load.start.y,
                load.end.x, load.end.y,
            )
            if d <= tol:
                return ("distributed", i)
        # Line loads: distance to the point
        for i, load in enumerate(self.project.line_loads):
            d = math.hypot(x - load.point.x, y - load.point.y)
            if d <= tol:
                return ("line", i)
        return None

    def _pick_vertex(self, x: float, y: float, tolerance_px: float = 8.0):
        """Return (boundary_idx, vertex_idx) of the closest vertex, or None."""
        if self.project is None:
            return None
        filt = self.selection_filter
        if filt is not None and not filt.vertices:
            return None
        px_per_unit = abs(self.transform().m11()) or 1.0
        tol = tolerance_px / px_per_unit

        best = None
        best_dist = float("inf")
        for i, b in enumerate(self.project.boundaries):
            for k, v in enumerate(b.polyline.vertices):
                d = math.hypot(v.x - x, v.y - y)
                if d < best_dist:
                    best_dist = d
                    best = (i, k)
        return best if best_dist <= tol else None

    def _pick_support(self, x: float, y: float, tolerance_px: float = 8.0) -> int:
        """Return index of the support whose body is closest to (x, y),
        or -1 if none is within tolerance. v0.1.14.

        v0.1.15 — honours the Selection Filter ``supports`` flag.
        """
        if self.project is None or not getattr(self.project, "supports", None):
            return -1
        filt = self.selection_filter
        if filt is not None and not filt.supports:
            return -1
        px_per_unit = abs(self.transform().m11()) or 1.0
        tol = tolerance_px / px_per_unit
        best = -1
        best_d = float("inf")
        for i, s in enumerate(self.project.supports):
            # Distance from (x, y) to segment head→tail
            hx, hy = s.head.x, s.head.y
            tx, ty = s.tail.x, s.tail.y
            dx = tx - hx
            dy = ty - hy
            L2 = dx * dx + dy * dy
            if L2 < 1e-12:
                d = math.hypot(x - hx, y - hy)
            else:
                t = max(0.0, min(1.0, ((x - hx) * dx + (y - hy) * dy) / L2))
                qx = hx + t * dx
                qy = hy + t * dy
                d = math.hypot(x - qx, y - qy)
            if d < best_d:
                best_d = d
                best = i
        return best if best_d <= tol else -1

    def _pick_support_endpoint(
        self, x: float, y: float, tolerance_px: float = 10.0,
    ):
        """Return (support_idx, 'head'|'tail') of the closest support
        endpoint, or None. v0.1.14."""
        if self.project is None or not getattr(self.project, "supports", None):
            return None
        px_per_unit = abs(self.transform().m11()) or 1.0
        tol = tolerance_px / px_per_unit
        best = None
        best_d = float("inf")
        for i, s in enumerate(self.project.supports):
            for end_name, p in (("head", s.head), ("tail", s.tail)):
                d = math.hypot(p.x - x, p.y - y)
                if d < best_d:
                    best_d = d
                    best = (i, end_name)
        return best if best_d <= tol else None


        """Return (boundary_idx, edge_start_vertex_idx) for the nearest edge."""
        if self.project is None:
            return None
        px_per_unit = abs(self.transform().m11()) or 1.0
        tol = tolerance_px / px_per_unit

        best = None
        best_dist = float("inf")
        for i, b in enumerate(self.project.boundaries):
            verts = b.polyline.vertices
            n = len(verts)
            if n < 2:
                continue
            segs = n if b.polyline.closed else n - 1
            for j in range(segs):
                a = verts[j]
                c = verts[(j + 1) % n]
                d = _point_segment_distance(x, y, a.x, a.y, c.x, c.y)
                if d < best_dist:
                    best_dist = d
                    best = (i, j)
        return best if best_dist <= tol else None

    # ==================================================================
    # Zoom & pan
    # ==================================================================
    def zoom_all(self) -> None:
        if self.project is None or not self.project.boundaries:
            # v0.1.5: on empty project, zoom to a sensible default
            # area (0..50, 0..30) so the grid is visible and the user
            # has somewhere to click.
            self.resetTransform()
            t = QTransform()
            t.scale(1.0, -1.0)
            self.setTransform(t)
            default_rect = QRectF(-5, -5, 60, 40)
            self.scene().setSceneRect(default_rect)
            self.fitInView(default_rect, Qt.KeepAspectRatio)
            tt = self.transform()
            if tt.m22() > 0:
                tt.scale(1.0, -1.0)
                self.setTransform(tt)
            return
        xmin, ymin, xmax, ymax = self.project.bounding_box()
        pad = max((xmax - xmin) * 0.1, (ymax - ymin) * 0.1, 1.0)
        rect = QRectF(xmin - pad, ymin - pad,
                      (xmax - xmin) + 2 * pad, (ymax - ymin) + 2 * pad)
        self.fitInView(rect, Qt.KeepAspectRatio)
        t = self.transform()
        if t.m22() > 0:
            t.scale(1.0, -1.0)
            self.setTransform(t)

    def zoom_to_point(self, x: float, y: float,
                      half_width: Optional[float] = None) -> None:
        """Centre the view on a model coordinate, zooming in.

        Added for the DXF problem report (v0.1.47): a listed problem is
        only actionable if the user can get to it, and a gap of a few
        millimetres in a hundred-metre model is impossible to find by
        panning. ``half_width`` defaults to a small fraction of the model
        so the surroundings stay recognisable instead of filling the view
        with a single vertex.

        The vertical flip of the canvas transform is preserved: the model
        has y upwards, and letting ``fitInView`` reset that would turn the
        drawing upside down.
        """
        if half_width is None:
            if self.project is not None and self.project.boundaries:
                xmin, ymin, xmax, ymax = self.project.bounding_box()
                span = max(xmax - xmin, ymax - ymin, 1.0)
            else:
                span = 10.0
            half_width = span * 0.05
        half_width = max(float(half_width), 1e-6)
        rect = QRectF(x - half_width, y - half_width,
                      2 * half_width, 2 * half_width)
        self.fitInView(rect, Qt.KeepAspectRatio)
        t = self.transform()
        if t.m22() > 0:
            t.scale(1.0, -1.0)
            self.setTransform(t)
        self.centerOn(QPointF(x, y))

    def zoom_by(self, factor: float, center_scene: Optional[QPointF] = None) -> None:
        if center_scene is None:
            self.scale(factor, factor)
            return
        anchor_view = self.mapFromScene(center_scene)
        self.scale(factor, factor)
        new_scene = self.mapToScene(anchor_view)
        delta = new_scene - center_scene
        self.translate(delta.x(), delta.y())

    def set_view_limits(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        rect = QRectF(xmin, ymin, xmax - xmin, ymax - ymin)
        self.fitInView(rect, Qt.KeepAspectRatio)
        t = self.transform()
        if t.m22() > 0:
            t.scale(1.0, -1.0)
            self.setTransform(t)

    # ==================================================================
    # Event handling
    # ==================================================================
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else (1 / 1.15)
        scene_pt = self.mapToScene(event.position().toPoint())
        self.zoom_by(factor, center_scene=scene_pt)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # Middle button always pans
        if event.button() == Qt.MiddleButton:
            self._start_pan(event.position())
            event.accept()
            return

        mode = self._tool_mode

        # v0.1.4 — Right-click during a drawing: open context menu with
        # Done / Close / Undo / Snap / Ortho / OSnap / Coord Table / Cancel
        if event.button() == Qt.RightButton and mode.is_drawing_boundary:
            self._show_drawing_context_menu(event.globalPosition().toPoint())
            event.accept()
            return

        # v0.1.8 — Right-click in SELECT mode over a load → context menu
        if event.button() == Qt.RightButton and mode == ToolMode.SELECT:
            scene_pt = self.mapToScene(event.position().toPoint())

            # Priority order: vertex → load → boundary → region → background
            vhit = self._pick_vertex(scene_pt.x(), scene_pt.y())
            if vhit is not None:
                self._show_vertex_context_menu(
                    event.globalPosition().toPoint(), vhit,
                )
                event.accept()
                return

            lhit = self._pick_load(scene_pt.x(), scene_pt.y())
            if lhit is not None:
                self._show_load_context_menu(
                    event.globalPosition().toPoint(), lhit,
                )
                event.accept()
                return

            # v0.1.15 — right-click on a support
            sidx = self._pick_support(scene_pt.x(), scene_pt.y())
            if sidx >= 0:
                self._show_support_context_menu(
                    event.globalPosition().toPoint(), sidx,
                )
                event.accept()
                return

            bidx = self._pick_boundary(scene_pt.x(), scene_pt.y())
            if bidx >= 0:
                self._show_boundary_context_menu(
                    event.globalPosition().toPoint(), bidx,
                )
                event.accept()
                return

            # Background / region click — emit so MainWindow can show
            # "Assign Material" menu with the click coords
            self.canvas_right_click_xy.emit(scene_pt.x(), scene_pt.y(),
                                             event.globalPosition().toPoint())
            event.accept()
            return

        # ============ v0.1.2 INTERACTIVE TOOLS ============
        if event.button() == Qt.LeftButton:
            # Boundary drawing (click-click-click)
            if mode.is_drawing_boundary:
                scene_pt = self.mapToScene(event.position().toPoint())
                snapped = self._snap_xy(scene_pt)
                # v0.1.4 — auto-close detection: if this click lands
                # on the first vertex (within 1e-6), treat it as
                # "close polygon". Only when ≥ 3 points already placed.
                if (mode.draws_closed_polygon
                        and len(self._draw_points) >= 3):
                    x0, y0 = self._draw_points[0]
                    if (abs(snapped.x() - x0) < 1e-6
                            and abs(snapped.y() - y0) < 1e-6):
                        self._finish_drawing(force_close=True)
                        event.accept()
                        return
                self._draw_points.append((snapped.x(), snapped.y()))
                self._update_draw_preview()
                event.accept()
                return

            # Delete / Copy / Convert / Scale / Rotate / Expand-Shrink / Slope —
            # v0.1.14 — Delete Support: one-click on the support body
            if mode == ToolMode.DELETE_SUPPORT:
                scene_pt = self.mapToScene(event.position().toPoint())
                idx = self._pick_support(scene_pt.x(), scene_pt.y())
                if idx >= 0:
                    self.support_clicked.emit(idx)
                event.accept()
                return

            # one-click hit-test
            if mode in (ToolMode.DELETE_BOUNDARY, ToolMode.COPY_BOUNDARY,
                        ToolMode.CONVERT_BOUNDARY,
                        ToolMode.SCALE_BOUNDARY,
                        ToolMode.ROTATE_BOUNDARY, ToolMode.EXPAND_SHRINK,
                        ToolMode.CHANGE_SLOPE_ANGLE):
                scene_pt = self.mapToScene(event.position().toPoint())
                idx = self._pick_boundary(scene_pt.x(), scene_pt.y())
                if idx >= 0:
                    self.boundary_clicked.emit(idx)
                event.accept()
                return

            # v0.1.9 — Move Boundary: click + hold + drag (like Move Vertex)
            if mode == ToolMode.MOVE_BOUNDARY:
                scene_pt = self.mapToScene(event.position().toPoint())
                idx = self._pick_boundary(scene_pt.x(), scene_pt.y())
                if idx >= 0:
                    b = self.project.boundaries[idx]
                    self._dragging_boundary = idx
                    self._drag_boundary_origin = (scene_pt.x(), scene_pt.y())
                    self._drag_boundary_orig_verts = [
                        (v.x, v.y) for v in b.polyline.vertices
                    ]
                event.accept()
                return

            # v0.1.4 — Assign material: emit RAW xy, MainWindow uses
            # shapely region_at_point to pick the region under the cursor.
            if mode == ToolMode.ASSIGN_MATERIAL:
                scene_pt = self.mapToScene(event.position().toPoint())
                self.canvas_click_xy.emit(scene_pt.x(), scene_pt.y())
                event.accept()
                return

            # v0.1.8 — Loadings (interactive picking)
            if mode == ToolMode.ADD_LINE_LOAD:
                scene_pt = self.mapToScene(event.position().toPoint())
                snapped = self._snap_xy(scene_pt)
                self.point_picked.emit(snapped.x(), snapped.y())
                event.accept()
                return
            # v0.1.10 — Pick grid rectangle (also 2 clicks)
            # v0.1.14 — Add Support (head→tail), Add Support Pattern
            # (2 points along a boundary), Stretch Support (click on
            # endpoint, then new position) all reuse the 2-click flow
            if mode in (
                ToolMode.ADD_DISTRIBUTED_LOAD,
                ToolMode.PICK_GRID_RECT,
                ToolMode.ADD_SUPPORT,
                ToolMode.ADD_SUPPORT_PATTERN,
                ToolMode.STRETCH_SUPPORT,
            ):
                scene_pt = self.mapToScene(event.position().toPoint())
                snapped = self._snap_xy(scene_pt)
                # First click → store; second click → emit segment
                if not self._draw_points:
                    self._draw_points.append((snapped.x(), snapped.y()))
                    self._update_draw_preview()
                else:
                    x0, y0 = self._draw_points[0]
                    self._draw_points.clear()
                    self._update_draw_preview()
                    self.segment_picked.emit(x0, y0, snapped.x(), snapped.y())
                event.accept()
                return

            # Move / Delete vertex — hit-test vertex
            if mode in (ToolMode.MOVE_VERTEX, ToolMode.DELETE_VERTEX):
                scene_pt = self.mapToScene(event.position().toPoint())
                hit = self._pick_vertex(scene_pt.x(), scene_pt.y())
                if hit is not None:
                    bi, vi = hit
                    if mode == ToolMode.MOVE_VERTEX:
                        self._dragging_vertex = hit
                        # Snapshot boundary for undo at release
                        from copy import deepcopy
                        if 0 <= bi < len(self.project.boundaries):
                            self._vertex_drag_start_boundary = deepcopy(
                                self.project.boundaries[bi]
                            )
                        self.viewport().setCursor(QCursor(Qt.ClosedHandCursor))
                    elif mode == ToolMode.DELETE_VERTEX:
                        self.vertex_deleted.emit(bi, vi)
                event.accept()
                return

            # Insert vertex — pick closest edge, emit with world coords
            if mode == ToolMode.INSERT_VERTEX:
                scene_pt = self.mapToScene(event.position().toPoint())
                hit = self._pick_edge(scene_pt.x(), scene_pt.y())
                if hit is not None:
                    bi, vi = hit
                    snapped = self._snap_xy(scene_pt)
                    self.vertex_inserted.emit(bi, vi, snapped.x(), snapped.y())
                event.accept()
                return

        # ============ existing navigation tools ============
        if event.button() == Qt.LeftButton:
            if mode == ToolMode.PAN:
                self._start_pan(event.position())
                event.accept()
                return

            if mode == ToolMode.ZOOM_WINDOW:
                self._zw_start_scene = self.mapToScene(event.position().toPoint())
                self._zw_rubber = QGraphicsRectItem(
                    QRectF(self._zw_start_scene, self._zw_start_scene)
                )
                pen = QPen(QColor("#1e6fc5"), 1.2, Qt.DashLine)
                pen.setCosmetic(True)
                self._zw_rubber.setPen(pen)
                self._zw_rubber.setBrush(QBrush(QColor(30, 111, 197, 40)))
                self.scene().addItem(self._zw_rubber)
                event.accept()
                return

            if mode == ToolMode.ZOOM_MOUSE:
                scene_pt = self.mapToScene(event.position().toPoint())
                self.zoom_by(1.5, center_scene=scene_pt)
                event.accept()
                return

            if event.modifiers() & Qt.ShiftModifier:
                self._start_pan(event.position())
                event.accept()
                return

        if event.button() == Qt.RightButton and mode == ToolMode.ZOOM_MOUSE:
            scene_pt = self.mapToScene(event.position().toPoint())
            self.zoom_by(1 / 1.5, center_scene=scene_pt)
            event.accept()
            return

        # v0.1.12 — generic scene_clicked emission for Interpret tools
        # (Query Slice Data picker etc.). Only on plain left-click in
        # SELECT mode and only if no other handler has consumed the event.
        if (event.button() == Qt.LeftButton
                and mode == ToolMode.SELECT
                and not event.isAccepted()):
            scene_pt = self.mapToScene(event.position().toPoint())
            self.scene_clicked.emit(scene_pt.x(), scene_pt.y())

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        pt = self.mapToScene(event.position().toPoint())
        self.cursor_moved.emit(pt.x(), pt.y())
        self._last_cursor_scene = pt
        # v0.1.12 — generic scene_hovered for Interpret hover preview
        # (slip-surface preview when the cursor is over a grid centre).
        if self._tool_mode == ToolMode.SELECT:
            self.scene_hovered.emit(pt.x(), pt.y())

        # v0.1.3 — when a drawing tool is active, always resolve the
        # snap so glyphs (circle/X/dot) and ortho projection are shown
        # live — even if no vertex has been placed yet.
        if self._tool_mode.is_drawing_boundary or self._tool_mode in (
            ToolMode.MOVE_VERTEX,
            ToolMode.INSERT_VERTEX,
        ):
            snapped, _ = self._snap_point(pt)
            live_pt = (snapped.x(), snapped.y())
            if self._draw_points:
                self._update_draw_preview(live_cursor=live_pt)
            # Trigger a foreground repaint so the snap glyph updates
            self.viewport().update()

        # v0.1.2 — Drag vertex live
        if self._dragging_vertex is not None:
            bi, vi = self._dragging_vertex
            snapped = self._snap_xy(pt)
            self.vertex_moved.emit(bi, vi, snapped.x(), snapped.y())
            event.accept()
            return

        # v0.1.9 — Drag entire boundary live
        if (self._dragging_boundary is not None
                and self._drag_boundary_origin is not None
                and self._drag_boundary_orig_verts is not None):
            ox, oy = self._drag_boundary_origin
            dx = pt.x() - ox
            dy = pt.y() - oy
            bi = self._dragging_boundary
            if 0 <= bi < len(self.project.boundaries):
                b = self.project.boundaries[bi]
                # Apply translation to the in-memory polyline (preview).
                # Final commit happens on mouse release.
                for vi, v in enumerate(b.polyline.vertices):
                    ox0, oy0 = self._drag_boundary_orig_verts[vi]
                    v.x = ox0 + dx
                    v.y = oy0 + dy
                self.refresh()
            event.accept()
            return

        if self._panning:
            delta = event.position() - self._pan_last_pos
            self._pan_last_pos = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return

        if self._zw_rubber is not None and self._zw_start_scene is not None:
            scene_pt = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._zw_start_scene, scene_pt).normalized()
            self._zw_rubber.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # v0.1.2 — finish vertex drag
        if self._dragging_vertex is not None and event.button() == Qt.LeftButton:
            bi, _ = self._dragging_vertex
            snapshot = self._vertex_drag_start_boundary
            self._dragging_vertex = None
            self._vertex_drag_start_boundary = None
            shape = getattr(Qt, self._tool_mode.cursor_name, Qt.ArrowCursor)
            self.viewport().setCursor(QCursor(shape))
            # Emit so MainWindow can wrap the whole drag in a single
            # undoable command
            if snapshot is not None:
                self.vertex_drag_finished.emit(bi, snapshot)
            event.accept()
            return

        # v0.1.9 — finish boundary drag
        if (self._dragging_boundary is not None
                and event.button() == Qt.LeftButton):
            bi = self._dragging_boundary
            origin = self._drag_boundary_origin
            orig_verts = self._drag_boundary_orig_verts
            self._dragging_boundary = None
            self._drag_boundary_origin = None
            self._drag_boundary_orig_verts = None
            if (origin is not None and orig_verts is not None
                    and 0 <= bi < len(self.project.boundaries)):
                pt = self.mapToScene(event.position().toPoint())
                dx = pt.x() - origin[0]
                dy = pt.y() - origin[1]
                # Restore original positions and emit a clean drag-finished
                # event so MainWindow can wrap it in a CommandStack op.
                b = self.project.boundaries[bi]
                for vi, v in enumerate(b.polyline.vertices):
                    ox0, oy0 = orig_verts[vi]
                    v.x = ox0
                    v.y = oy0
                if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                    self.boundary_dragged.emit(bi, dx, dy)
            event.accept()
            return

        if self._panning and event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._end_pan()
            event.accept()
            return

        if (
            self._zw_rubber is not None
            and self._zw_start_scene is not None
            and event.button() == Qt.LeftButton
        ):
            rect = self._zw_rubber.rect()
            self.scene().removeItem(self._zw_rubber)
            self._zw_rubber = None
            start = self._zw_start_scene
            self._zw_start_scene = None

            if rect.width() > 1e-3 and rect.height() > 1e-3:
                self.fitInView(rect, Qt.KeepAspectRatio)
                t = self.transform()
                if t.m22() > 0:
                    t.scale(1.0, -1.0)
                    self.setTransform(t)
            else:
                self.zoom_by(1.5, center_scene=start)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # v0.1.3: Drawing is now finished with right-click.
        # Double-click has no special behaviour for boundary drawing.
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        # v0.1.4 — Enter closes External/Material polygons;
        # otherwise finishes as an open polyline.
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and self._tool_mode.is_drawing_boundary
                and len(self._draw_points) >= 2):
            self._finish_drawing(
                force_close=self._tool_mode.draws_closed_polygon
            )
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            # Cancel any drawing in progress first
            if self._draw_points:
                self._cancel_drawing()
                event.accept()
                return
            self.set_tool_mode(ToolMode.SELECT)
            event.accept()
            return
        super().keyPressEvent(event)

    # ==================================================================
    # Pan helpers
    # ==================================================================
    def _start_pan(self, pos: QPointF) -> None:
        self._panning = True
        self._pan_last_pos = pos
        self.viewport().setCursor(QCursor(Qt.ClosedHandCursor))

    def _end_pan(self) -> None:
        self._panning = False
        shape = getattr(Qt, self._tool_mode.cursor_name, Qt.ArrowCursor)
        self.viewport().setCursor(QCursor(shape))

    # ==================================================================
    # Background
    # ==================================================================
    def _pixels_per_unit(self) -> float:
        return abs(self.transform().m11())

    # ==================================================================
    # v0.1.9 — Slide-style W/P/D labels on water surfaces
    # ==================================================================
    def _draw_water_surface_label(self, scene, boundary, letter: str, color) -> None:
        """Draw a small letter label centred above a water-surface polyline.

        Slide convention: W on a Water Table, P on a Piezometric Line,
        D on a Drawdown Line. The label sits at the midpoint of the
        polyline, slightly above, and uses ItemIgnoresTransformations
        so it stays a fixed size regardless of zoom.
        """
        from PySide6.QtGui import QFont
        # v0.1.61 — QGraphicsItem was used below without ever being
        # imported, in this module or any other, so drawing the W / P / D
        # letter raised NameError and took the whole canvas repaint down
        # with it. Any project with a water surface hit it; it survived
        # because no test drew one.
        from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                                       QGraphicsTextItem)
        verts = boundary.polyline.vertices
        if len(verts) < 2:
            return

        # Midpoint along the polyline (by total length)
        total = 0.0
        for i in range(len(verts) - 1):
            total += math.hypot(
                verts[i + 1].x - verts[i].x,
                verts[i + 1].y - verts[i].y,
            )
        if total < 1e-9:
            return
        target = total / 2.0
        acc = 0.0
        mx, my = verts[0].x, verts[0].y
        for i in range(len(verts) - 1):
            seg = math.hypot(
                verts[i + 1].x - verts[i].x,
                verts[i + 1].y - verts[i].y,
            )
            if acc + seg >= target:
                t = (target - acc) / seg
                mx = verts[i].x + t * (verts[i + 1].x - verts[i].x)
                my = verts[i].y + t * (verts[i + 1].y - verts[i].y)
                break
            acc += seg

        # Background circle anchored at the midpoint, in scene coords
        # so it scales with zoom. Diameter ~2% of bbox short side, with
        # min 0.5 m and max 5 m (heuristic for typical slope models).
        try:
            xmin, ymin, xmax, ymax = self.project.bounding_box()
            bbox_min = min(xmax - xmin, ymax - ymin)
            R = max(0.5, min(5.0, bbox_min * 0.015))
        except Exception:
            R = 1.0

        bg = QGraphicsEllipseItem(mx - R, my - R, 2 * R, 2 * R)
        bg.setBrush(QBrush(QColor(255, 255, 255, 230)))
        pen = QPen(color, 0)
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        bg.setPen(pen)
        bg.setZValue(20.0)
        scene.addItem(bg)

        # Letter, centred. QGraphicsTextItem uses HTML for colour.
        # We use boundingRect.center() to centre the glyph in the disc.
        text = QGraphicsTextItem()
        text.setHtml(
            f'<div style="color:{color.name()}; '
            f'font-family:Arial; font-weight:bold; '
            f'font-size:14pt;">{letter}</div>'
        )
        text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        text.setZValue(21.0)
        # Place the text item at the midpoint and offset by -half its
        # screen size so the glyph centres over the disc.
        text.setPos(mx, my)
        br = text.boundingRect()
        # Apply an additional centering offset using the
        # transformOriginPoint, which combines with the position when
        # ItemIgnoresTransformations is on
        text.setTransformOriginPoint(br.center())
        text.moveBy(-br.width() / 2 / max(1.0, self.transform().m11()),
                     -br.height() / 2 / max(1.0, self.transform().m22()))
        scene.addItem(text)

    # ==================================================================
    # v0.1.8 — Slip-circle search grid visualisation
    # ==================================================================
    def _draw_slip_search_grid(self, scene) -> None:
        """Draw the rectangular search grid as small × markers.

        If the user has defined a grid (Add Grid), uses those bounds.
        Otherwise falls back to the auto-computed grid (above the slope).
        """
        from PySide6.QtGui import QPen
        from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem

        s = self.project.settings.search
        if s.grid_x_min is None or s.grid_x_max is None:
            # Auto grid — derive from bbox
            try:
                xmin, ymin, xmax, ymax = self.project.bounding_box()
            except Exception:
                return
            dx, dy = xmax - xmin, ymax - ymin
            gx = (xmin + 0.2 * dx, xmax - 0.2 * dx)
            gy = (ymax, ymax + 0.8 * dy)
            is_auto = True
        else:
            gx = (s.grid_x_min, s.grid_x_max)
            gy = (s.grid_y_min, s.grid_y_max)
            is_auto = False

        nx = max(2, s.grid_nx)
        ny = max(2, s.grid_ny)

        # Outline rectangle
        rect_pen = QPen(
            QColor(120, 120, 220, 180) if not is_auto else QColor(160, 160, 160, 120),
            0.8,
        )
        rect_pen.setCosmetic(True)
        rect_pen.setStyle(Qt.DashLine)
        rect = QGraphicsRectItem(
            gx[0], gy[0], gx[1] - gx[0], gy[1] - gy[0],
        )
        rect.setPen(rect_pen)
        rect.setZValue(1)
        scene.addItem(rect)

        # Cross markers at each centre
        cross_pen = QPen(
            QColor(80, 80, 200) if not is_auto else QColor(140, 140, 140),
            0.7,
        )
        cross_pen.setCosmetic(True)
        sz = 0.8  # cross half-size in scene units (cosmetic so always visible)
        # Estimate scene cross size adaptively
        try:
            view_w = self.viewport().width() if self.viewport() else 600
            scene_rect = self.sceneRect()
            if scene_rect.width() > 0 and view_w > 0:
                sz = max(0.5, scene_rect.width() / view_w * 4.0)
        except Exception:
            pass

        # v0.1.17 — grid_nx/grid_ny are the number of INTERVALS (Slide
        # convention), so there are (nx+1)·(ny+1) centre points.
        nxp = nx + 1
        nyp = ny + 1
        for i in range(nxp):
            for j in range(nyp):
                xc = gx[0] + (gx[1] - gx[0]) * i / (nxp - 1)
                yc = gy[0] + (gy[1] - gy[0]) * j / (nyp - 1)
                line1 = QGraphicsLineItem(xc - sz, yc, xc + sz, yc)
                line2 = QGraphicsLineItem(xc, yc - sz, xc, yc + sz)
                line1.setPen(cross_pen)
                line2.setPen(cross_pen)
                line1.setZValue(2)
                line2.setZValue(2)
                scene.addItem(line1)
                scene.addItem(line2)

    # ==================================================================
    # v0.1.7 — Tension Crack zone visualisation
    # ==================================================================
    def _ground_polyline(self):
        """Upper envelope of the external boundary, or None.

        v0.1.84 — delegates to :func:`ogr_core.geometry.ground_surface`,
        the same function the slicer and the searches use. What was here
        kept the vertices with ``y >= (y_min + y_max) / 2``, which on the
        Ej_2 reference model discards every vertex of the lower half of
        the profile and returns only its right-hand quarter — so the
        tension-crack zone was being drawn against a ground surface that
        stopped short of most of the slope.
        """
        external = self.project.external_boundary()
        if external is None:
            return None
        if not external.polyline.vertices:
            return None
        from ogr_core.geometry import ground_surface
        return ground_surface(external)

    def _draw_ponded_water(self, scene, opts) -> None:
        """Fill and/or hatch the ponded-water region.

        Ponded water is what a water table (or a drawdown line) defines
        when it is drawn above the external boundary — the body of still
        water resting on the slope. It is NOT created by a piezometric
        line, which is why this only looks at the ponding boundary types.
        """
        from PySide6.QtGui import QBrush, QPen, QPolygonF
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsPolygonItem

        from ogr_core.hydraulic.ponded_water import (
            PONDING_BOUNDARY_TYPES,
            _FEA_METHODS,
            _fea_level_at,
        )
        from ogr_core.hydraulic.pore_pressure import _interp_y_on_polyline

        ground = self._ground_polyline()
        if ground is None:
            return
        surfaces = [b for b in self.project.boundaries
                    if b.btype in PONDING_BOUNDARY_TYPES
                    and b.visible and self._type_visible(b.btype)]
        # v0.1.65 — a seepage analysis prescribes its reservoir through the
        # boundary conditions instead of a drawn polyline. It loads the
        # slope exactly like a drawn one, so it has to be visible like one:
        # a load the user cannot see is a load the user cannot check.
        levels = [(lambda x, wb=wb: _interp_y_on_polyline(wb.polyline, x))
                  for wb in surfaces]
        if self.project.settings.groundwater.method in _FEA_METHODS:
            from ogr_core.hydraulic.ponded_water import _fea_ponding_polyline
            if _fea_ponding_polyline(self.project):
                levels.append(lambda x: _fea_level_at(self.project, x))
        if not levels:
            return

        gx = [v.x for v in ground.vertices]
        x_min, x_max = min(gx), max(gx)
        if x_max <= x_min:
            return

        blue = QColor(60, 130, 220)
        pen = QPen(blue, 0.8)
        pen.setCosmetic(True)
        # Sample densely enough that the region outline follows both the
        # ground breaks and the water surface.
        n = max(60, int((x_max - x_min) / 1.0))
        step = (x_max - x_min) / n

        for level_at in levels:
            # Walk the sampled columns, collecting maximal runs where the
            # water surface is above the ground; each run is one pond.
            run: list[tuple[float, float, float]] = []
            for i in range(n + 1):
                x = x_min + step * i
                y_g = _interp_y_on_polyline(ground, x)
                y_w = level_at(x)
                wet = (y_g is not None and y_w is not None and y_w > y_g)
                if wet:
                    run.append((x, y_g, y_w))
                    continue
                self._emit_pond_run(scene, run, opts, blue, pen,
                                    QPolygonF, QPointF, QBrush,
                                    QGraphicsPolygonItem, QGraphicsLineItem)
                run = []
            self._emit_pond_run(scene, run, opts, blue, pen,
                                QPolygonF, QPointF, QBrush,
                                QGraphicsPolygonItem, QGraphicsLineItem)

    @staticmethod
    def _emit_pond_run(scene, run, opts, blue, pen, QPolygonF, QPointF,
                       QBrush, QGraphicsPolygonItem, QGraphicsLineItem):
        """Render one contiguous ponded stretch."""
        if len(run) < 2:
            return
        if getattr(opts, "ponded_water_fill", False):
            poly = QPolygonF([QPointF(x, yw) for x, _, yw in run]
                             + [QPointF(x, yg) for x, yg, _ in reversed(run)])
            item = QGraphicsPolygonItem(poly)
            fill = QColor(blue)
            fill.setAlpha(60)
            item.setBrush(QBrush(fill))
            item.setPen(QPen(Qt.NoPen))
            item.setZValue(1)
            scene.addItem(item)
        if getattr(opts, "ponded_water_hatch", True):
            # Same vertical-line idiom as the tension-crack pattern, so
            # the two water regions read alike.
            span = run[-1][0] - run[0][0]
            n_lines = max(4, int(span / 2.0))
            for k in range(n_lines + 1):
                t = k / n_lines
                idx = min(len(run) - 1, int(t * (len(run) - 1)))
                x, y_g, y_w = run[idx]
                line = QGraphicsLineItem(x, y_g, x, y_w)
                line.setPen(pen)
                line.setZValue(2)
                scene.addItem(line)

    def _draw_tension_crack_pattern(self, scene, tc_boundary) -> None:
        """Draw the vertical-line pattern of the Tension Crack zone.

        Blue lines = water-filled portion. Gray lines = dry portion.
        The pattern density is 1 line per ~2 m of horizontal extent
        (auto-scaled to the bbox of the crack).
        """
        from PySide6.QtGui import QPen
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QGraphicsLineItem
        from ogr_core.hydraulic.pore_pressure import _interp_y_on_polyline

        external = self.project.external_boundary()
        if external is None:
            return
        # Build the ground surface polyline from the External upper edge
        ground_verts = []
        ext_verts = list(external.polyline.vertices)
        if not ext_verts:
            return
        # Approximate "upper" surface: vertices sorted by y descending
        # then taking those above the horizontal midpoint of bbox
        ymin = min(v.y for v in ext_verts)
        ymax = max(v.y for v in ext_verts)
        y_mid = 0.5 * (ymin + ymax)
        ground_verts = sorted(
            [v for v in ext_verts if v.y >= y_mid],
            key=lambda v: v.x,
        )
        if len(ground_verts) < 2:
            ground_verts = sorted(ext_verts, key=lambda v: v.x)
        from ogr_core.geometry import Polyline as _PL
        ground = _PL(vertices=ground_verts, closed=False)

        tc_verts = tc_boundary.polyline.vertices
        if len(tc_verts) < 2:
            return
        x_min = min(v.x for v in tc_verts)
        x_max = max(v.x for v in tc_verts)
        if x_max <= x_min:
            return

        # Resolve water level inside the crack (using project tc props)
        wt = next(
            (b for b in self.project.boundaries
             if b.btype == BoundaryType.WATER_TABLE),
            None,
        )
        piezos = {
            b.id: b for b in self.project.boundaries
            if b.btype == BoundaryType.PIEZOMETRIC
        }
        props = self.project.tension_crack_properties

        # Draw vertical lines spaced ~2 m apart
        n_lines = max(5, int((x_max - x_min) / 2.0))
        blue_pen = QPen(QColor(60, 130, 220), 0.8)
        blue_pen.setCosmetic(True)
        gray_pen = QPen(QColor(140, 140, 140), 0.8)
        gray_pen.setCosmetic(True)

        for i in range(n_lines + 1):
            x = x_min + (x_max - x_min) * i / n_lines
            y_top = _interp_y_on_polyline(ground, x)
            y_bot = _interp_y_on_polyline(tc_boundary.polyline, x)
            if y_top is None or y_bot is None or y_top <= y_bot:
                continue
            water_y = props.water_level_at(
                x=x,
                crack_top_y=y_top,
                crack_bottom_y=y_bot,
                water_table=wt,
                piezos=piezos,
            )
            water_y = max(y_bot, min(y_top, water_y))
            # Lower part (water): blue
            if water_y > y_bot:
                line_blue = QGraphicsLineItem(x, y_bot, x, water_y)
                line_blue.setPen(blue_pen)
                line_blue.setZValue(2)
                scene.addItem(line_blue)
            # Upper part (dry/air): gray
            if y_top > water_y:
                line_gray = QGraphicsLineItem(x, water_y, x, y_top)
                line_gray.setPen(gray_pen)
                line_gray.setZValue(2)
                scene.addItem(line_gray)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        super().drawBackground(painter, rect)
        if self.display_options.show_grid:
            self._draw_grid(painter, rect)
        if self.display_options.show_ruler:
            self._draw_ruler(painter, rect)

    # v0.1.3 — overlay: snap glyphs and OSNAP extension lines
    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        super().drawForeground(painter, rect)
        from .snap_engine import SnapKind
        snap = self._last_snap
        if snap is None or snap.kind == SnapKind.NONE:
            # No active snap — nothing to draw
            if snap is None or not snap.extension_lines:
                return

        ppu = self._pixels_per_unit() or 1.0

        # Save and reset transform so glyphs are screen-space (constant size)
        painter.save()

        # 1. Extension lines (dashed red) — scene-space so they follow the axes
        if snap is not None and snap.extension_lines:
            pen = QPen(QColor(220, 40, 40, 180), 0.8, Qt.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            # Clip to the visible rect so infinite lines don't crash rendering
            vr = rect
            for a, b in snap.extension_lines:
                # Clip the (effectively infinite) line to ``rect``
                p1 = QPointF(max(vr.left(), min(vr.right(), a.x)),
                             max(vr.top(), min(vr.bottom(), a.y)))
                p2 = QPointF(max(vr.left(), min(vr.right(), b.x)),
                             max(vr.top(), min(vr.bottom(), b.y)))
                # Horizontal vs vertical detection
                if abs(a.y - b.y) < 1e-9:
                    y = a.y
                    if vr.top() <= y <= vr.bottom():
                        painter.drawLine(
                            QPointF(vr.left(), y), QPointF(vr.right(), y)
                        )
                elif abs(a.x - b.x) < 1e-9:
                    x = a.x
                    if vr.left() <= x <= vr.right():
                        painter.drawLine(
                            QPointF(x, vr.top()), QPointF(x, vr.bottom())
                        )

        # 2. Snap glyph at the snapped point — screen-space so it doesn't
        #    zoom with the model
        if snap is not None and snap.kind != SnapKind.NONE:
            sx, sy = snap.point.x, snap.point.y
            painter.resetTransform()
            screen_pt = self.mapFromScene(QPointF(sx, sy))
            pen = QPen(QColor("#ffa500"), 2.0)
            pen.setCosmetic(False)
            painter.setPen(pen)

            if snap.kind == SnapKind.VERTEX:
                # Circle around vertex
                r = 8
                painter.drawEllipse(screen_pt, r, r)
            elif snap.kind == SnapKind.LINE:
                # Draw an X
                r = 7
                painter.drawLine(
                    screen_pt + QPointF(-r, -r), screen_pt + QPointF(r, r)
                )
                painter.drawLine(
                    screen_pt + QPointF(-r, r), screen_pt + QPointF(r, -r)
                )
            elif snap.kind == SnapKind.GRID:
                # Small square
                r = 4
                painter.drawRect(
                    screen_pt.x() - r, screen_pt.y() - r, 2 * r, 2 * r
                )
            elif snap.kind == SnapKind.ENDPOINT:
                # Filled square
                r = 5
                painter.setBrush(QBrush(QColor("#ffa500")))
                painter.drawRect(
                    screen_pt.x() - r, screen_pt.y() - r, 2 * r, 2 * r
                )
                painter.setBrush(QBrush(Qt.NoBrush))
            elif snap.kind == SnapKind.EXTENSION:
                # Small diamond
                r = 5
                pts = [
                    screen_pt + QPointF(0, -r), screen_pt + QPointF(r, 0),
                    screen_pt + QPointF(0, r), screen_pt + QPointF(-r, 0),
                ]
                painter.drawPolyline(pts + [pts[0]])
            elif snap.kind in (SnapKind.ORTHO_H, SnapKind.ORTHO_V):
                # Right-angle glyph
                r = 8
                painter.drawLine(
                    screen_pt + QPointF(-r, 0), screen_pt + QPointF(0, 0)
                )
                painter.drawLine(
                    screen_pt + QPointF(0, 0), screen_pt + QPointF(0, -r)
                )

        painter.restore()

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        scale = self._pixels_per_unit()
        if scale <= 0:
            return
        # v0.1.15 fix — guard against the start-up glitch. When the
        # widget is first constructed the viewport has no real size yet,
        # so fitInView produces an absurd scale → step ≈ 0 → thousands of
        # grid lines pile up at the origin and render as a dense pixel
        # block. Skip drawing until the view is sized and the number of
        # grid lines within the visible rect is reasonable.
        if (not self.viewport().rect().isValid()
                or self.viewport().width() < 2
                or self.viewport().height() < 2):
            return
        step = nice_step(60.0 / scale)
        if step <= 0:
            return
        # If the step would produce an unreasonable number of lines in
        # the visible rect (scale blew up before the first real layout),
        # bail out rather than drawing the dense block.
        if rect.width() / step > 2000 or rect.height() / step > 2000:
            return

        pen_minor = QPen(QColor(220, 220, 220)); pen_minor.setCosmetic(True)
        pen_major = QPen(QColor(180, 180, 180)); pen_major.setCosmetic(True)

        x0 = math.floor(rect.left() / step) * step
        x1 = math.ceil(rect.right() / step) * step
        y0 = math.floor(rect.top() / step) * step
        y1 = math.ceil(rect.bottom() / step) * step

        x = x0
        while x <= x1:
            is_major = abs(round(x / (step * 5)) * (step * 5) - x) < 1e-9
            painter.setPen(pen_major if is_major else pen_minor)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = y0
        while y <= y1:
            is_major = abs(round(y / (step * 5)) * (step * 5) - y) < 1e-9
            painter.setPen(pen_major if is_major else pen_minor)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step

    def _draw_ruler(self, painter: QPainter, rect: QRectF) -> None:
        scale = self._pixels_per_unit()
        if scale <= 0:
            return
        if (not self.viewport().rect().isValid()
                or self.viewport().width() < 2
                or self.viewport().height() < 2):
            return
        step = nice_step(120.0 / scale)
        if step <= 0:
            return
        painter.save()
        painter.resetTransform()
        font = QFont(); font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor(100, 100, 100))

        vr = self.viewport().rect()
        xmin_scene = self.mapToScene(vr.bottomLeft()).x()
        xmax_scene = self.mapToScene(vr.bottomRight()).x()
        x = math.ceil(xmin_scene / step) * step
        while x <= xmax_scene:
            px = self.mapFromScene(QPointF(x, 0)).x()
            painter.drawText(QPointF(px + 2, vr.bottom() - 2), f"{x:g}")
            x += step

        ymin_scene = self.mapToScene(vr.bottomLeft()).y()
        ymax_scene = self.mapToScene(vr.topLeft()).y()
        ylo, yhi = min(ymin_scene, ymax_scene), max(ymin_scene, ymax_scene)
        y = math.ceil(ylo / step) * step
        while y <= yhi:
            py = self.mapFromScene(QPointF(0, y)).y()
            painter.drawText(QPointF(4, py - 2), f"{y:g}")
            y += step
        painter.restore()

    # Backwards-compat helpers -----------------------------------------
    def set_grid_visible(self, on: bool) -> None:
        self.display_options.show_grid = on
        self.viewport().update()

    def set_ruler_visible(self, on: bool) -> None:
        self.display_options.show_ruler = on
        self.viewport().update()

    def set_grayscale(self, on: bool) -> None:
        self.display_options.grayscale = on
        self.setBackgroundBrush(QBrush(QColor("#e8e8e8" if on else "#fafafa")))
        self.viewport().update()


# ----------------------------------------------------------------------
def _dist_point_to_segment(
    px: float, py: float,
    ax: float, ay: float, bx: float, by: float,
) -> float:
    """Euclidean distance from point (px, py) to segment (a, b)."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = max(0.0, min(1.0, t))
    cx = ax + t * dx
    cy = ay + t * dy
    return math.hypot(px - cx, py - cy)
