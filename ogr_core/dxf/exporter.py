# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF exporter — the mirror of the importer.

Built on the same philosophy as the import side: the engine is separate
from the dialog so a whole export can be scripted, the options are
explicit, and the result is verifiable.

**Round-trip is the design goal.** Geometry is written to the *same*
layer names the importer recognises, so a model exported and re-imported
must come back unchanged. That is not a nicety: it is the strongest
statement that both halves agree on what the layers mean, and it is what
the tests check. A user can therefore export a model, edit it in CAD, and
bring it back.

Everything beyond the boundaries — supports, loads, the FE mesh, the
critical slip surface, annotations — goes to layers **prefixed
``OGR_X_``** ("export only"). Those are drawings *of results*, not model
inputs, and re-importing them as geometry would be wrong. Keeping them on
distinct names means the importer ignores them by default instead of
turning a load arrow into a material boundary.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from ogr_core.geometry import BoundaryType

from .reader import UNIT_FACTORS
from .importer import KIND_TO_BOUNDARY

try:
    import ezdxf
except ImportError:  # pragma: no cover
    ezdxf = None

# Model boundary type -> layer name. Deliberately the inverse of the
# importer's mapping, so a round trip lands on the same types.
# Model boundary type -> layer name. Derived from the importer's own
# mapping so the two halves can never drift apart: adding a geometry type
# to KIND_TO_BOUNDARY automatically gives it an export layer.
_KIND_LAYER_NAMES = {
    "external": "OGR_EXTERNAL",
    "material": "OGR_MATERIAL",
    "water_table": "OGR_WATER_TABLE",
    "piezo": "OGR_PIEZO",
    "drawdown": "OGR_DRAWDOWN",
    "tension_crack": "OGR_CRACK",
    # v0.1.121 — a weak layer is model input like any other boundary, so it
    # goes out and comes back on its own layer. The material it names does
    # NOT survive the trip: DXF carries geometry, and a re-imported joint has
    # to be assigned one, exactly as a re-imported material boundary has.
    "weak_layer": "OGR_WEAK_LAYER",
}
BOUNDARY_TO_LAYER = {
    btype: _KIND_LAYER_NAMES[kind.value]
    for kind, btype in KIND_TO_BOUNDARY.items()
    if kind.value in _KIND_LAYER_NAMES
}

# Export-only layers: drawings of results, never model inputs.
LAYER_SUPPORT = "OGR_SUPPORT"          # re-importable as supports
LAYER_LOADS = "OGR_X_LOADS"
LAYER_MESH = "OGR_X_MESH"
LAYER_SURFACE = "OGR_X_SLIP_SURFACE"
LAYER_ANNOTATION = "OGR_X_ANNOTATION"

# AutoCAD Color Index per layer, so the drawing is readable when opened.
_LAYER_COLOURS = {
    "OGR_EXTERNAL": 7,        # white / black
    "OGR_MATERIAL": 3,        # green
    "OGR_WATER_TABLE": 5,     # blue
    "OGR_PIEZO": 4,           # cyan
    "OGR_DRAWDOWN": 6,        # magenta
    "OGR_CRACK": 1,           # red
    "OGR_WEAK_LAYER": 140,    # slate blue, as on the canvas
    LAYER_SUPPORT: 2,         # yellow
    LAYER_LOADS: 30,          # orange
    LAYER_MESH: 8,            # dark grey
    LAYER_SURFACE: 1,         # red
    LAYER_ANNOTATION: 7,
}


@dataclass
class ExportOptions:
    """What to write and how."""

    unit: str = "m"
    boundaries: bool = True
    supports: bool = True
    loads: bool = True
    mesh: bool = False           # off by default: thousands of entities
    slip_surface: bool = True
    annotations: bool = True
    # Arrow size for loads, as a fraction of the model diagonal
    arrow_pct: float = 2.0


@dataclass
class ExportReport:
    """What was written."""

    entities: dict = field(default_factory=dict)
    layers: list = field(default_factory=list)
    path: str = ""
    skipped: list = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def total(self) -> int:
        return sum(self.entities.values())

    def count(self, layer: str, n: int = 1) -> None:
        self.entities[layer] = self.entities.get(layer, 0) + n

    def summary(self) -> str:
        if not self.ok:
            return self.error or "failed"
        parts = [f"{k}: {v}" for k, v in sorted(self.entities.items())]
        return f"{self.total} entities — " + ", ".join(parts)


# ======================================================================
def _scaled(points, factor):
    """Model metres -> drawing units."""
    inv = 1.0 / factor if factor else 1.0
    return [(x * inv, y * inv) for x, y in points]


def _diagonal(project) -> float:
    try:
        xmin, ymin, xmax, ymax = project.bounding_box()
        return math.hypot(xmax - xmin, ymax - ymin)
    except Exception:  # noqa: BLE001
        return 1.0


def _arrow(msp, layer, tip, angle_deg, length, factor, report):
    """A load arrow: shaft plus two head strokes.

    Drawn as plain lines rather than a block so the file opens the same
    way in every CAD program, at the cost of a few more entities.
    """
    a = math.radians(angle_deg)
    tail = (tip[0] - length * math.cos(a), tip[1] - length * math.sin(a))
    pts = _scaled([tail, tip], factor)
    msp.add_line(pts[0], pts[1], dxfattribs={"layer": layer})
    report.count(layer)
    head = length * 0.25
    for off in (150.0, -150.0):
        b = a + math.radians(off)
        p2 = (tip[0] + head * math.cos(b), tip[1] + head * math.sin(b))
        q = _scaled([tip, p2], factor)
        msp.add_line(q[0], q[1], dxfattribs={"layer": layer})
        report.count(layer)


# ======================================================================
def export_dxf(project, path, options: Optional[ExportOptions] = None,
               results=None) -> ExportReport:
    """Write ``project`` to a DXF drawing.

    Args:
        project: the model to export (never modified).
        path: destination file.
        options: what to include and in which units.
        results: optional mapping ``method_id -> SearchResult`` whose
            critical surfaces are drawn.
    """
    opts = options or ExportOptions()
    rep = ExportReport(path=str(path))
    if ezdxf is None:
        rep.error = ("The 'ezdxf' package is required to export DXF "
                     "files.")
        return rep

    factor = UNIT_FACTORS.get(opts.unit, 1.0)
    doc = ezdxf.new("R2010", setup=True)
    # Record the units in the header so a CAD program — and our own
    # importer's suggestion — get it right without asking.
    insunits = {"m": 6, "cm": 5, "mm": 4, "km": 17, "ft": 2,
                "in": 1}.get(opts.unit, 6)
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()

    def _layer(name):
        if name not in doc.layers:
            doc.layers.add(name, color=_LAYER_COLOURS.get(name, 7))
        if name not in rep.layers:
            rep.layers.append(name)
        return name

    # ---- boundaries -------------------------------------------------
    if opts.boundaries:
        for b in getattr(project, "boundaries", []):
            layer = BOUNDARY_TO_LAYER.get(b.btype)
            if layer is None:
                rep.skipped.append(b.btype.name)
                continue
            pts = [(v.x, v.y) for v in b.polyline.vertices]
            if len(pts) < 2:
                continue
            closed = bool(getattr(b.polyline, "closed", False))
            # A closed polyline repeated its first point on import; drop
            # the duplicate and use the DXF closed flag instead, so the
            # drawing is idiomatic and the round trip is exact.
            if closed and len(pts) > 2 and \
                    math.dist(pts[0], pts[-1]) < 1e-12:
                pts = pts[:-1]
            msp.add_lwpolyline(_scaled(pts, factor),
                               dxfattribs={"layer": _layer(layer)},
                               close=closed)
            rep.count(layer)

    # ---- supports ---------------------------------------------------
    if opts.supports:
        for s in getattr(project, "supports", []):
            head = getattr(s, "head", None)
            tail = getattr(s, "tail", None)
            if head is None or tail is None:
                continue
            pts = _scaled([(head.x, head.y), (tail.x, tail.y)], factor)
            msp.add_line(pts[0], pts[1],
                         dxfattribs={"layer": _layer(LAYER_SUPPORT)})
            rep.count(LAYER_SUPPORT)

    # ---- loads ------------------------------------------------------
    if opts.loads:
        diag = _diagonal(project)
        length = max(diag * opts.arrow_pct / 100.0, 1e-6)
        for ld in getattr(project, "distributed_loads", []):
            start, end = ld.start, ld.end
            pts = _scaled([(start.x, start.y), (end.x, end.y)], factor)
            msp.add_line(pts[0], pts[1],
                         dxfattribs={"layer": _layer(LAYER_LOADS)})
            rep.count(LAYER_LOADS)
            # Arrows at both ends, pointing at the loaded line
            for p in ((start.x, start.y), (end.x, end.y)):
                _arrow(msp, _layer(LAYER_LOADS), p,
                       getattr(ld, "angle_deg", 270.0) or 270.0,
                       length, factor, rep)
        for ld in getattr(project, "line_loads", []):
            p = (ld.point.x, ld.point.y)
            _arrow(msp, _layer(LAYER_LOADS), p,
                   getattr(ld, "angle_deg", 270.0) or 270.0,
                   length, factor, rep)

    # ---- FE mesh ----------------------------------------------------
    if opts.mesh and getattr(project, "fem_mesh", None) is not None:
        mesh = project.fem_mesh
        try:
            edges = mesh.boundary_edges()
            drawn = set()
            for e in mesh.elements:
                ns = list(e.nodes)
                for a, b in zip(ns, ns[1:] + ns[:1]):
                    key = (min(a, b), max(a, b))
                    if key in drawn:
                        continue
                    drawn.add(key)
                    na, nb = mesh.nodes[a], mesh.nodes[b]
                    pts = _scaled([(na.x, na.y), (nb.x, nb.y)], factor)
                    msp.add_line(pts[0], pts[1],
                                 dxfattribs={"layer": _layer(LAYER_MESH)})
                    rep.count(LAYER_MESH)
            del edges
        except Exception as exc:  # noqa: BLE001
            rep.skipped.append(f"mesh ({exc})")

    # ---- critical slip surface --------------------------------------
    if opts.slip_surface and results:
        from ogr_slip2d.surface import CompositeSurface, SlipCircle
        for mid, sr in results.items():
            crit = getattr(sr, "critical", None)
            if crit is None:
                continue
            surf = crit.surface
            layer = _layer(LAYER_SURFACE)
            if isinstance(surf, CompositeSurface):
                # v0.1.111 — asked BEFORE the circle branch, and asked of
                # the surface rather than reconstructed here: a composite
                # has a centre and a radius, so ``_surface_arc`` would
                # happily draw the arc it was clipped from — a curve that
                # dives below the floor of the model and was never
                # analysed. Exporting that into a drawing someone builds
                # from is worse than exporting nothing.
                pts = surf.drawing_vertices()
            elif isinstance(surf, SlipCircle):
                pts = _surface_arc(surf, crit)
            else:
                pts = [(v.x, v.y) for v in surf.polyline.vertices]
            if len(pts) >= 2:
                msp.add_lwpolyline(_scaled(pts, factor),
                                   dxfattribs={"layer": layer})
                rep.count(LAYER_SURFACE)
            if opts.annotations:
                mid_pt = pts[len(pts) // 2]
                txt = msp.add_text(
                    f"{mid}  FS = {crit.fos:.4f}",
                    dxfattribs={"layer": _layer(LAYER_ANNOTATION),
                                "height": max(
                                    _diagonal(project) * 0.015, 1e-6)
                                / (factor or 1.0)})
                txt.set_placement(_scaled([mid_pt], factor)[0])
                rep.count(LAYER_ANNOTATION)

    # ---- title annotation -------------------------------------------
    if opts.annotations:
        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
            h = max((ymax - ymin) * 0.03, 1e-6)
            title = getattr(project, "name", "") or "OGR Slip2D"
            txt = msp.add_text(
                title, dxfattribs={"layer": _layer(LAYER_ANNOTATION),
                                   "height": h / (factor or 1.0)})
            txt.set_placement(_scaled([(xmin, ymax + h * 2)], factor)[0])
            rep.count(LAYER_ANNOTATION)
        except Exception:  # noqa: BLE001
            pass

    try:
        doc.saveas(str(path))
    except Exception as exc:  # noqa: BLE001
        rep.error = f"Could not write the DXF file: {exc}"
    return rep


def _surface_arc(circle, result, segments: int = 72):
    """The slip surface as it was actually analysed.

    Drawing the whole circle would be misleading — only the arc below
    ground is the failure surface — so the slice base points are used
    directly. They ARE the analysed surface, which also means the drawing
    cannot drift from the calculation by re-deriving the geometry.
    ``segments`` is kept for the fallback path, where no slices are
    available and the arc has to be reconstructed from the circle.
    """
    slices = list(getattr(result, "slices", []) or [])
    if slices:
        pts = [(s.base_x_left, s.base_y_left) for s in slices]
        last = slices[-1]
        pts.append((last.base_x_right, last.base_y_right))
        return pts
    # Fallback: no slices, so rebuild the arc from the circle itself
    pts = []
    x0 = circle.centre_x - circle.radius
    x1 = circle.centre_x + circle.radius
    for i in range(segments + 1):
        x = x0 + (x1 - x0) * i / segments
        dx = x - circle.centre_x
        under = circle.radius ** 2 - dx * dx
        if under < 0:
            continue
        pts.append((x, circle.centre_y - math.sqrt(under)))
    return pts
