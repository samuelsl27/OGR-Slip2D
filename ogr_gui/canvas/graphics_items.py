# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
QGraphicsScene items that render the geotechnical model.

Each class corresponds to a domain object (Boundary, Material region,
DistributedLoad, SupportInstance, ...) and is responsible only for its
own rendering + hover tooltip. All items operate in *model coordinates*
(not pixels); the Y axis is flipped at the view level so that positive
Y points upward (engineering convention).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsSimpleTextItem,
)

from ogr_core.geometry import Boundary, BoundaryType
from ogr_core.loads import DistributedLoad, LineLoad
from ogr_core.materials import Material
from ogr_core.support import SupportInstance


# ----------------------------------------------------------------------
# Base: every item stores a back-reference to its domain object. Hover
# produces rich tooltips from the domain's ``tooltip_html()``.
# ----------------------------------------------------------------------
class DomainItem(QGraphicsPathItem):
    """Base class for graphics items that represent a domain object."""

    def __init__(self, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._hover = False

    def hoverEnterEvent(self, ev) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().hoverLeaveEvent(ev)


# ======================================================================
class BoundaryItem(DomainItem):
    """Rendering of a :class:`Boundary`."""

    def __init__(self, boundary: Boundary, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self.boundary = boundary
        self.setToolTip(f"<b>{boundary.name}</b><br>{boundary.btype.display_name}")
        self.setZValue(self._z_for_type(boundary.btype))
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        path = QPainterPath()
        verts = self.boundary.polyline.vertices
        if verts:
            path.moveTo(verts[0].x, verts[0].y)
            for v in verts[1:]:
                path.lineTo(v.x, v.y)
            if self.boundary.polyline.closed:
                path.closeSubpath()
        self.setPath(path)

        color = QColor(self.boundary.color or "#000000")
        pen = QPen(color, self.boundary.line_width)
        pen.setCosmetic(True)  # width in pixels, independent of zoom
        self.setPen(pen)

        # v0.1.6 — boundary items draw LINES only; region fill is handled
        # separately by resolve_regions() → _region_to_item(). Doing both
        # would double-paint and confuse the user.
        self.setBrush(Qt.NoBrush)

    # ------------------------------------------------------------------
    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        super().paint(painter, option, widget)
        if self._hover:
            # Highlight: draw a thin halo around the path
            halo = QPen(QColor(255, 200, 0, 200), 3)
            halo.setCosmetic(True)
            painter.setPen(halo)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.path())

    # ------------------------------------------------------------------
    @staticmethod
    def _z_for_type(btype: BoundaryType) -> float:
        return {
            BoundaryType.EXTERNAL: 1.0,
            BoundaryType.MATERIAL: 2.0,
            BoundaryType.WATER_TABLE: 5.0,
            BoundaryType.PIEZOMETRIC: 5.0,
            BoundaryType.DRAWDOWN: 4.0,
            BoundaryType.TENSION_CRACK: 6.0,
            BoundaryType.BLOCK_SEARCH_OBJECT: 7.0,
            # Above the material boundaries it crosses, below the water
            # surfaces: a joint is a line the surface follows, and the
            # thing a user needs to see is where it runs relative to the
            # layers, not relative to the piezometric line.
            BoundaryType.WEAK_LAYER: 3.0,
        }.get(btype, 1.0)


# ======================================================================
class MaterialRegionItem(DomainItem):
    """Shaded closed region representing a material assignment."""

    def __init__(
        self,
        boundary: Boundary,
        material: Material,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.boundary = boundary
        self.material = material
        self.setToolTip(material.tooltip_html())
        self.setZValue(1.5)
        self.refresh()

    def refresh(self) -> None:
        path = QPainterPath()
        verts = self.boundary.polyline.vertices
        if verts:
            path.moveTo(verts[0].x, verts[0].y)
            for v in verts[1:]:
                path.lineTo(v.x, v.y)
            path.closeSubpath()
        self.setPath(path)
        c = QColor(self.material.color)
        self.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 110)))
        pen = QPen(c.darker(150), 1.0)
        pen.setCosmetic(True)
        self.setPen(pen)


# ======================================================================
class VertexHandleItem(QGraphicsEllipseItem):
    """Draggable vertex handle. Small coloured dot sitting on a vertex."""

    RADIUS_PX = 4.0

    def __init__(
        self,
        x: float,
        y: float,
        parent: QGraphicsItem | None = None,
    ) -> None:
        r = self.RADIUS_PX
        super().__init__(-r, -r, 2 * r, 2 * r, parent)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#ffffff")))
        pen = QPen(QColor("#1e6fc5"), 1.2)
        pen.setCosmetic(True)
        self.setPen(pen)
        # v0.1.7 — vertex handles must NOT be Qt-movable. The canvas
        # controls all vertex drags via the MOVE_VERTEX tool, which
        # routes through the CommandStack so changes are undoable and
        # persisted. If we leave ItemIsMovable=True, Qt drags the
        # handle visually in SELECT mode without notifying the model,
        # which is the bug Samuel reported in v0.1.6.
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10.0)
        self.setToolTip(f"Vertex ({x:.3f}, {y:.3f})")

    def hoverEnterEvent(self, ev) -> None:  # noqa: N802
        self.setBrush(QBrush(QColor("#ffcc33")))
        super().hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev) -> None:  # noqa: N802
        self.setBrush(QBrush(QColor("#ffffff")))
        super().hoverLeaveEvent(ev)


# ======================================================================
class DistributedLoadItem(DomainItem):
    """Distributed pressure load drawn as a row of arrows with the
    magnitude annotated midway along the segment."""

    ARROW_LENGTH_PX = 18.0

    def __init__(
        self, load: DistributedLoad, parent: QGraphicsItem | None = None
    ) -> None:
        super().__init__(parent)
        self.load = load
        self.setToolTip(load.tooltip_html())
        self.setZValue(8.0)
        pen = QPen(QColor("#d35400"), 1.8)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor("#d35400")))
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        path = QPainterPath()
        p1 = QPointF(self.load.start.x, self.load.start.y)
        p2 = QPointF(self.load.end.x, self.load.end.y)
        # Base line
        path.moveTo(p1)
        path.lineTo(p2)

        # Arrows: use cosmetic length in world units ≈ px / scale
        # Item-level coordinates are world → we rely on ItemIgnoresTransformations
        # via cosmetic pen. For arrow length we choose a world value that scales
        # with segment length.
        seg_len = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
        if seg_len < 1e-6:
            self.setPath(path)
            return

        dx, dy = self.load.direction_vector()
        L = max(0.08 * seg_len, 0.5)
        n_arrows = max(3, int(seg_len / max(0.15 * seg_len, 0.8)))
        for i in range(n_arrows + 1):
            t = i / n_arrows
            tx = p1.x() + t * (p2.x() - p1.x())
            ty = p1.y() + t * (p2.y() - p1.y())
            # Arrow shaft: from (tx,ty) - L*(dx,dy) to (tx,ty)
            sx = tx - L * dx
            sy = ty - L * dy
            path.moveTo(sx, sy)
            path.lineTo(tx, ty)
            # Arrow head (small triangle)
            # Perpendicular to (dx, dy):
            px_, py_ = -dy, dx
            hw = 0.25 * L
            hl = 0.4 * L
            h1x, h1y = tx - hl * dx + hw * px_, ty - hl * dy + hw * py_
            h2x, h2y = tx - hl * dx - hw * px_, ty - hl * dy - hw * py_
            path.moveTo(tx, ty)
            path.lineTo(h1x, h1y)
            path.moveTo(tx, ty)
            path.lineTo(h2x, h2y)

        self.setPath(path)

    # ------------------------------------------------------------------
    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        super().paint(painter, option, widget)
        # Magnitude label at the midpoint
        p1 = self.load.start
        p2 = self.load.end
        mx = 0.5 * (p1.x + p2.x)
        my = 0.5 * (p1.y + p2.y)
        label = f"{self.load.magnitude_1:.1f} kN/m²"
        if self.load.magnitude_2 is not None and self.load.magnitude_2 != self.load.magnitude_1:
            label = f"{self.load.magnitude_1:.1f} → {self.load.magnitude_2:.1f} kN/m²"

        painter.save()
        painter.resetTransform()
        # Convert scene point to viewport via painter world transform
        view_pt = painter.worldTransform().map(QPointF(mx, my))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#d35400"))
        painter.drawText(view_pt + QPointF(6, -6), label)
        painter.restore()


# ======================================================================
class LineLoadItem(DomainItem):
    """Single-arrow line load with a magnitude label."""

    def __init__(self, load: LineLoad, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self.load = load
        self.setToolTip(load.tooltip_html())
        self.setZValue(8.0)
        pen = QPen(QColor("#d35400"), 2.0)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.refresh()

    def refresh(self) -> None:
        path = QPainterPath()
        dx, dy = self.load.direction_vector()
        L = max(abs(self.load.magnitude) / 20.0, 1.0)
        x0 = self.load.point.x - L * dx
        y0 = self.load.point.y - L * dy
        x1 = self.load.point.x
        y1 = self.load.point.y
        path.moveTo(x0, y0)
        path.lineTo(x1, y1)
        # Head
        px_, py_ = -dy, dx
        hw, hl = 0.25 * L, 0.35 * L
        path.moveTo(x1, y1)
        path.lineTo(x1 - hl * dx + hw * px_, y1 - hl * dy + hw * py_)
        path.moveTo(x1, y1)
        path.lineTo(x1 - hl * dx - hw * px_, y1 - hl * dy - hw * py_)
        self.setPath(path)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        super().paint(painter, option, widget)
        painter.save()
        painter.resetTransform()
        view_pt = painter.worldTransform().map(
            QPointF(self.load.point.x, self.load.point.y)
        )
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#d35400"))
        painter.drawText(view_pt + QPointF(8, -2), f"{self.load.magnitude:.1f} kN/m")
        painter.restore()


# ======================================================================
class SupportItem(DomainItem):
    """Reinforcement (nail, tieback, anchor) drawn from head to tail.

    v0.1.14 — full rendering with:
        - Color-coded per support type (Slide convention)
        - Arrowhead at the tail to indicate the bolt direction
        - Length & angle annotation shown on hover
        - Rich HTML tooltip showing all key properties
    """

    # Slide-style colors per support type
    _TYPE_COLORS = {
        "end_anchored": "#1f77b4",            # blue
        "grouted_tieback": "#ff7f0e",         # orange
        "grouted_tieback_friction": "#d62728",  # red
        "soil_nail": "#2ca02c",               # green
        "pile_micropile": "#9467bd",          # purple
        "geosynthetic": "#8c564b",            # brown
        "user_defined": "#7f7f7f",            # grey
        "retaining_wall_efp": "#17becf",      # teal
    }

    def __init__(
        self,
        support: SupportInstance,
        support_type_display: str = "",
        support_type_obj=None,
        parent: QGraphicsItem | None = None,
        project=None,
    ) -> None:
        super().__init__(parent)
        self.support = support
        self.support_type_obj = support_type_obj
        # Use the support's saved color, or fall back to the type default
        color = support.color
        if color in ("#4b0082", "", None):
            color = self._TYPE_COLORS.get(support.type_id, "#4b0082")
        self._draw_color = color

        # Rich tooltip
        tooltip = (
            f"<b>{support.name or support_type_display}</b><br>"
            f"<i>Type:</i> {support_type_display}<br>"
            f"<i>Length:</i> {support.length():.2f} m<br>"
            f"<i>Axis:</i> {support.axis_angle_deg():.1f}°<br>"
            f"<i>Application:</i> {support.force_application.value}<br>"
            f"<i>Orientation:</i> "
            f"{support.orientation.value.replace('_', ' ')}"
        )
        if support_type_obj is not None:
            try:
                # v0.1.116 — the two stress-dependent pullout laws need
                # the interface strength sampled along the bolt, so the
                # tooltip builds one instead of falling back to the
                # zero-stress envelope. Without it a geosynthetic in
                # coefficient or friction-factor mode reads 0 kN/m here
                # while the analysis uses a real number, and the two
                # disagreeing is worse than either.
                bond = None
                if project is not None and getattr(
                        support_type_obj, "NEEDS_BOND_PROFILE", False):
                    from ogr_core.support import build_bond_profile
                    bond = build_bond_profile(
                        project, support, support_type_obj)
                F0 = support_type_obj.force_at(0, support.length(), bond)
                Fmid = support_type_obj.force_at(
                    0.5 * support.length(), support.length(), bond
                )
                # v0.1.122 — "force at head" is a lie for a type whose
                # profile is INTEGRATED from the crest: there the integral
                # is zero by definition, and reporting it as a capacity
                # reads as "this support does nothing".
                if getattr(support_type_obj, "MEASURED_FROM_TOP", False):
                    Fend = support_type_obj.force_at(
                        support.length(), support.length(), bond)
                    tooltip += (
                        f"<br><i>Force at midpoint:</i> {Fmid:.1f} kN/m"
                        f"<br><i>Force at the foot:</i> {Fend:.1f} kN/m"
                    )
                else:
                    tooltip += (
                        f"<br><i>Force at head:</i> {F0:.1f} kN/m"
                        f"<br><i>Force at midpoint:</i> {Fmid:.1f} kN/m"
                    )
            except Exception:  # noqa: BLE001
                pass
        self.setToolTip(tooltip)

        self.setZValue(7.0)
        pen = QPen(QColor(self._draw_color), 2.5)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.refresh()

    def refresh(self) -> None:
        import math as _m
        path = QPainterPath()
        h = self.support.head
        t = self.support.tail
        # Bolt body
        path.moveTo(h.x, h.y)
        path.lineTo(t.x, t.y)
        dx = t.x - h.x
        dy = t.y - h.y
        L = _m.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux

        # Face plate at head (perpendicular tick of length 6% of bolt L)
        plate = max(0.04 * L, 0.3)
        path.moveTo(h.x + plate * nx, h.y + plate * ny)
        path.lineTo(h.x - plate * nx, h.y - plate * ny)

        # Arrowhead at tail (small triangle pointing along the bolt axis)
        ah = max(0.05 * L, 0.4)  # arrowhead size
        # Tip is at the tail; barbs at 35° from the bolt direction
        cos_b = _m.cos(_m.radians(150))
        sin_b = _m.sin(_m.radians(150))
        # Rotate (ux, uy) by ±150° to get the two barbs
        bx1 = ux * cos_b - uy * sin_b
        by1 = ux * sin_b + uy * cos_b
        bx2 = ux * cos_b + uy * sin_b
        by2 = -ux * sin_b + uy * cos_b
        # Move pen to the tail, draw the two barbs
        path.moveTo(t.x, t.y)
        path.lineTo(t.x + ah * bx1, t.y + ah * by1)
        path.moveTo(t.x, t.y)
        path.lineTo(t.x + ah * bx2, t.y + ah * by2)
        self.setPath(path)


# ======================================================================
class SupportForceArrow(QGraphicsPathItem):
    """v0.1.15 — overlay arrow showing the force vector applied by a
    support on the critical slip surface.

    Drawn from the intersection point of the support with the slip
    surface, in the direction the force is applied (resolved by the
    LEM solver). Includes a magnitude label.

    The arrow length is scaled so that ``max_force`` maps to a
    pixel length of ``screen_max_px`` (passed externally).
    """

    def __init__(
        self,
        intersection_x: float,
        intersection_y: float,
        force_angle_rad: float,
        force_magnitude: float,
        is_active: bool = True,
        scene_unit_per_force: float = 0.05,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        import math as _m
        # Arrow geometry
        L_arrow = max(force_magnitude * scene_unit_per_force, 0.5)
        dx = L_arrow * _m.cos(force_angle_rad)
        dy = L_arrow * _m.sin(force_angle_rad)
        path = QPainterPath()
        path.moveTo(intersection_x, intersection_y)
        path.lineTo(intersection_x + dx, intersection_y + dy)
        # Arrowhead
        ah = max(0.15 * L_arrow, 0.2)
        cos_b = _m.cos(_m.radians(150))
        sin_b = _m.sin(_m.radians(150))
        ux = dx / L_arrow if L_arrow > 0 else 1.0
        uy = dy / L_arrow if L_arrow > 0 else 0.0
        bx1 = ux * cos_b - uy * sin_b
        by1 = ux * sin_b + uy * cos_b
        bx2 = ux * cos_b + uy * sin_b
        by2 = -ux * sin_b + uy * cos_b
        tip_x = intersection_x + dx
        tip_y = intersection_y + dy
        path.moveTo(tip_x, tip_y)
        path.lineTo(tip_x + ah * bx1, tip_y + ah * by1)
        path.moveTo(tip_x, tip_y)
        path.lineTo(tip_x + ah * bx2, tip_y + ah * by2)
        self.setPath(path)

        color = QColor("#d62728") if is_active else QColor("#1f77b4")
        pen = QPen(color, 2.5)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(8.5)
        self.setToolTip(
            f"<b>Support force</b><br>"
            f"Magnitude: {force_magnitude:.1f} kN/m<br>"
            f"Angle: {_m.degrees(force_angle_rad):.1f}°<br>"
            f"Mode: {'Active' if is_active else 'Passive'}"
        )


# ======================================================================
class SlipSurfaceItem(QGraphicsPathItem):
    """Slip circle / non-circular surface with its FoS label.

    v0.1.12 — supports both ``type='circle'`` (SlipCircle) and
    ``type='polyline'`` (SlipSurface) representations. The polyline
    case is drawn directly from its ``vertices`` list.

    Visual states:
        - Critical (lowest FoS in the result set): bold red
        - Selected (clicked in the surface list): bold purple
        - Queried (v0.1.82): black, as in the reference
        - Hover-preview: dashed grey (lower z-order, transient)
        - Default: the legend colour of its factor of safety, or faint
          green when no colour function is supplied
    """

    def __init__(
        self,
        surface_dict: dict,
        fos: float,
        is_critical: bool = False,
        is_selected: bool = False,
        is_hover: bool = False,
        parent: QGraphicsItem | None = None,
        colour_fn=None,
        is_query: bool = False,
    ) -> None:
        super().__init__(parent)
        self.surface_dict = surface_dict
        self.fos = fos
        self.is_critical = is_critical
        self.is_selected = is_selected
        self.is_hover = is_hover
        self.is_query = is_query

        path = QPainterPath()
        stype = surface_dict.get("type", "circle")
        if stype == "circle":
            xc = surface_dict["centre_x"]
            yc = surface_dict["centre_y"]
            r = surface_dict["radius"]
            xl = surface_dict.get("x_left")
            xr = surface_dict.get("x_right")
            # v0.1.82 — reverse-curvature tension cracks. The arc is cut
            # at the point of vertical tangency and a vertical segment
            # rises from there to the ground surface; drawing only the arc
            # left the surface visibly "stopping halfway" up the slope.
            cracks = {round(float(c[0]), 9): (float(c[1]), float(c[2]))
                      for c in surface_dict.get("tension_cracks", [])}
            if xl is not None and xr is not None:
                left_crack = cracks.get(round(float(xl), 9))
                if left_crack is not None:
                    path.moveTo(xl, left_crack[1])
                    path.lineTo(xl, left_crack[0])
                n = 60
                for i in range(n + 1):
                    x = xl + (xr - xl) * i / n
                    dx = x - xc
                    disc = r * r - dx * dx
                    if disc < 0:
                        continue
                    y = yc - math.sqrt(disc)
                    if i == 0 and left_crack is None:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                right_crack = cracks.get(round(float(xr), 9))
                if right_crack is not None:
                    path.lineTo(xr, right_crack[1])
        elif stype in ("polyline", "composite"):
            # v0.1.12 — non-circular surface (SlipSurface).
            # to_dict() returns {"type": "polyline", "polyline": {...}}
            # where polyline is itself a Polyline.to_dict() with "vertices".
            #
            # v0.1.111 — and Composite Surfaces, which shares this branch
            # rather than the circular one above ON PURPOSE. A composite
            # carries a centre and a radius, so drawing it as an arc would
            # succeed and would be wrong: the arc is the surface only down
            # to the floor of the model, and below that the analysed
            # surface runs along the boundary. Its ``vertices`` are that
            # analysed surface, and this is the one place where the picture
            # and the number are made to agree.
            verts = surface_dict.get("vertices")
            if not verts:
                pl = surface_dict.get("polyline", {})
                verts = pl.get("vertices", [])
            if len(verts) >= 2:
                # v0.1.109 — a tension crack truncates a non-circular
                # surface too, and the polyline it leaves ends ON the
                # crack line. Without the vertical wall the drawing stops
                # in mid-air, metres below the ground it came from, which
                # is exactly the mismatch between picture and number that
                # the circular branch above was given its own crack list
                # to avoid.
                cracks = {round(float(c[0]), 9): (float(c[1]), float(c[2]))
                          for c in surface_dict.get("tension_cracks", [])}
                first = True
                x = y = None
                for v in verts:
                    if isinstance(v, dict):
                        x, y = v["x"], v["y"]
                    elif isinstance(v, (list, tuple)):
                        x, y = v[0], v[1]
                    else:
                        x, y = v.x, v.y
                    if first:
                        crack = cracks.get(round(float(x), 9))
                        if crack is not None:
                            path.moveTo(x, crack[1])
                            path.lineTo(x, crack[0])
                        else:
                            path.moveTo(x, y)
                        first = False
                    else:
                        path.lineTo(x, y)
                if x is not None:
                    crack = cracks.get(round(float(x), 9))
                    if crack is not None:
                        path.lineTo(x, crack[1])
        self.setPath(path)

        # Pen selection by visual state.
        #
        # v0.1.82 — an ordinary surface is now drawn in the colour its
        # FACTOR OF SAFETY has in the legend, not a fixed green. Without
        # that, a screen full of Minimum Surfaces said only "here are some
        # surfaces"; with it, the reader can see which parts of the slope
        # the low factors of safety come from — which is the whole reason
        # the mode exists. Critical, queried and selected keep their own
        # identifying colours: those are answers to "which one is it?",
        # a different question from "how bad is it?".
        if is_critical:
            pen = QPen(QColor("#e63946"), 2.5)
        elif is_selected:
            pen = QPen(QColor("#9d4edd"), 2.5)  # purple per Samuel's request
        elif is_query:
            pen = QPen(QColor("#000000"), 2.0)
        elif is_hover:
            pen = QPen(QColor(80, 80, 80, 200), 1.6)
            pen.setStyle(Qt.PenStyle.DashLine)
        elif colour_fn is not None:
            try:
                colour = QColor(colour_fn(fos))
            except Exception:  # noqa: BLE001
                colour = QColor(0, 150, 0, 120)
            pen = QPen(colour, 1.2)
        else:
            pen = QPen(QColor(0, 150, 0, 120), 1.2)
        pen.setCosmetic(True)
        self.setPen(pen)
        # Z-order: hover < default < critical < query < selected (top)
        if is_selected:
            self.setZValue(9.5)
        elif is_query:
            self.setZValue(9.2)
        elif is_critical:
            self.setZValue(9.0)
        elif is_hover:
            self.setZValue(7.5)
        else:
            self.setZValue(8.5)
        self.setToolTip(f"Slip surface — FoS = {fos:.3f}")


# ======================================================================
class SlipRadiiItem(QGraphicsPathItem):
    """The two radial lines joining a slip centre to the surface ends.

    v0.1.82 — the reference draws these for the Global Minimum and for
    every Query, and they are not decoration: they are the handle. They
    show where the centre of rotation is relative to the mass, and they
    are the part of a Query the user can click on when the arc itself is
    buried under a hundred other surfaces.
    """

    def __init__(self, surface_dict: dict, colour: str = "#e63946",
                 width: float = 1.0, parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self.surface_dict = surface_dict
        path = QPainterPath()
        # v0.1.111 — a COMPOSITE too: it is a circular surface that was
        # clipped, it has the same centre of rotation, and the two radii to
        # its endpoints are drawn from the same arc. Its moment axis IS
        # this point, so leaving it undrawn would hide exactly what the
        # reader needs to judge the mechanism.
        if surface_dict.get("type", "circle") in ("circle", "composite"):
            xc = surface_dict["centre_x"]
            yc = surface_dict["centre_y"]
            r = surface_dict["radius"]
            for key in ("x_left", "x_right"):
                x = surface_dict.get(key)
                if x is None:
                    continue
                disc = r * r - (x - xc) ** 2
                if disc < 0:
                    continue
                path.moveTo(xc, yc)
                path.lineTo(x, yc - math.sqrt(disc))
        self.setPath(path)
        pen = QPen(QColor(colour), width)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(8.8)
