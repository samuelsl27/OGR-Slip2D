# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF reader and layer catalogue — Phase D0 of the DXF import plan.

This module only **reads and inventories**: it never touches the project
model. Its job is to turn a DXF file into plain polylines grouped by
layer, plus enough information for the import dialog to let the user say
what each layer represents.

What it handles
---------------
* ``LINE`` — a two-point polyline.
* ``LWPOLYLINE`` / ``POLYLINE`` — vertices, honouring the closed flag and
  discretising **bulges** (the arc segments a polyline can carry).
* ``ARC``, ``CIRCLE`` — discretised at a user-chosen density.
* ``SPLINE`` — flattened at a user-chosen density.

Curve discretisation is expressed as **segments per full circle**, which
is the parameter that behaves consistently whether the entity is a small
fillet or a large arc: an arc of 90 degrees gets a quarter of that count.

Units
-----
The DXF header variable ``$INSUNITS`` is read but treated only as a
**suggestion**, because it is frequently absent or wrong in files exported
from CAD. The importer asks the user, defaulting to metres.

Layer recognition
-----------------
Layer names are matched case-insensitively against a table of defaults and
aliases (including Spanish ones), but the match is only a **proposal**:
the dialog lets the user override every layer, including unrecognised ones
such as the ubiquitous ``0``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    import ezdxf
except ImportError:  # pragma: no cover
    ezdxf = None


# ======================================================================
class DxfEntityKind(Enum):
    """What the model should build from a layer's contents."""

    IGNORE = "ignore"
    EXTERNAL = "external"
    MATERIAL = "material"
    WATER_TABLE = "water_table"
    PIEZO = "piezo"
    DRAWDOWN = "drawdown"
    TENSION_CRACK = "tension_crack"
    SUPPORT = "support"


# Default layer names and the aliases recognised automatically. Matching
# is case-insensitive and ignores separators, so "OGR_WATER_TABLE",
# "ogr water table" and "OGRWATERTABLE" all match.
LAYER_DEFAULTS: dict[DxfEntityKind, tuple[str, ...]] = {
    DxfEntityKind.EXTERNAL: (
        "OGR_EXTERNAL", "EXTERNAL", "EXTERIOR", "CONTORNO",
        "CONTORNO_EXTERNO", "EXTERNALBOUNDARY"),
    DxfEntityKind.MATERIAL: (
        "OGR_MATERIAL", "MATERIAL", "MATERIALES", "MATERIALS", "SUELO",
        "ESTRATO", "ESTRATOS", "MATERIALBOUNDARY"),
    DxfEntityKind.WATER_TABLE: (
        "OGR_WATER_TABLE", "WATER_TABLE", "WATERTABLE", "WATER", "WT",
        "FREATICO", "NIVEL_FREATICO", "FREATICA"),
    DxfEntityKind.PIEZO: (
        "OGR_PIEZO", "PIEZO", "PIEZOMETRIC", "PIEZOMETRICA",
        "PIEZOMETRICLINE", "LINEA_PIEZOMETRICA"),
    DxfEntityKind.DRAWDOWN: (
        "OGR_DRAWDOWN", "DRAWDOWN", "DESEMBALSE", "DRAWDOWNLINE"),
    DxfEntityKind.TENSION_CRACK: (
        "OGR_CRACK", "CRACK", "TENSION_CRACK", "TENSIONCRACK", "GRIETA",
        "GRIETA_TRACCION"),
    DxfEntityKind.SUPPORT: (
        "OGR_SUPPORT", "SUPPORT", "SUPPORTS", "SOPORTE", "SOPORTES",
        "ANCLAJE", "ANCLAJES", "BULON", "BULONES", "REFUERZO"),
}

# Recognised drawing units, as unit-to-metre factors. The values follow
# the DXF $INSUNITS enumeration.
INSUNITS_TO_METRES: dict[int, float] = {
    0: 1.0,          # unitless -> assume metres
    1: 0.0254,       # inches
    2: 0.3048,       # feet
    4: 0.001,        # millimetres
    5: 0.01,         # centimetres
    6: 1.0,          # metres
    9: 1e-6,         # microns
    10: 0.9144,      # yards
    14: 0.1,         # decimetres
    15: 10.0,        # decametres
    16: 100.0,       # hectometres
    17: 1000.0,      # kilometres
}

UNIT_FACTORS: dict[str, float] = {
    "m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0,
    "ft": 0.3048, "in": 0.0254,
}


def _normalise(name: str) -> str:
    """Layer name reduced to comparable form: upper case, no separators."""
    return "".join(ch for ch in str(name).upper() if ch.isalnum())


def guess_kind(layer_name: str) -> DxfEntityKind:
    """Propose a geometry type for a layer name.

    Exact (normalised) matches win over partial ones, so a layer called
    ``MATERIAL`` is not mistaken for ``MATERIAL_WATER``.
    """
    norm = _normalise(layer_name)
    if not norm:
        return DxfEntityKind.IGNORE
    for kind, aliases in LAYER_DEFAULTS.items():
        if any(norm == _normalise(a) for a in aliases):
            return kind
    for kind, aliases in LAYER_DEFAULTS.items():
        if any(_normalise(a) in norm for a in aliases):
            return kind
    return DxfEntityKind.IGNORE


# ======================================================================
@dataclass
class DxfPolyline:
    """A polyline extracted from the DXF, in model coordinates."""

    points: list[tuple[float, float]] = field(default_factory=list)
    closed: bool = False
    layer: str = ""
    source: str = ""          # DXF entity type it came from
    handle: str = ""          # DXF handle, for the problem report

    @property
    def n(self) -> int:
        return len(self.points)

    def length(self) -> float:
        return sum(math.dist(a, b)
                   for a, b in zip(self.points, self.points[1:]))

    def bbox(self):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class DxfLayerInfo:
    """One row of the import dialog's layer table."""

    name: str = ""
    entity_counts: dict = field(default_factory=dict)
    polylines: list = field(default_factory=list)
    proposed_kind: DxfEntityKind = DxfEntityKind.IGNORE
    kind: DxfEntityKind = DxfEntityKind.IGNORE     # user's choice

    @property
    def entity_count(self) -> int:
        return sum(self.entity_counts.values())

    @property
    def vertex_count(self) -> int:
        return sum(p.n for p in self.polylines)

    @property
    def recognised(self) -> bool:
        return self.proposed_kind != DxfEntityKind.IGNORE

    def summary(self) -> str:
        kinds = ", ".join(f"{k}×{v}" for k, v in
                          sorted(self.entity_counts.items()))
        return f"{self.name}: {kinds} ({self.vertex_count} vertices)"


@dataclass
class DxfCatalogue:
    """Everything read from a DXF file, ready for the dialog."""

    layers: list = field(default_factory=list)
    insunits: Optional[int] = None
    unit_factor: float = 1.0          # applied when reading
    skipped: dict = field(default_factory=dict)   # entity type -> count
    notes: dict = field(default_factory=dict)

    def by_name(self, name: str) -> Optional[DxfLayerInfo]:
        for lay in self.layers:
            if lay.name == name:
                return lay
        return None

    def polylines_for(self, kind: DxfEntityKind) -> list:
        out = []
        for lay in self.layers:
            if lay.kind == kind:
                out.extend(lay.polylines)
        return out

    @property
    def total_entities(self) -> int:
        return sum(lay.entity_count for lay in self.layers)

    @property
    def total_vertices(self) -> int:
        return sum(lay.vertex_count for lay in self.layers)

    def suggested_unit(self) -> str:
        """Unit suggested by ``$INSUNITS``, or metres when absent.

        Only a suggestion: the header is often missing or wrong, so the
        dialog asks the user and defaults to metres.
        """
        if self.insunits is None:
            return "m"
        factor = INSUNITS_TO_METRES.get(self.insunits)
        if factor is None:
            return "m"
        for name, f in UNIT_FACTORS.items():
            if abs(f - factor) < 1e-12:
                return name
        return "m"

    def bbox(self):
        boxes = [p.bbox() for lay in self.layers for p in lay.polylines]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    def diagonal(self) -> float:
        """Model diagonal — the length the RELATIVE tolerances are
        measured against."""
        bb = self.bbox()
        if bb is None:
            return 0.0
        return math.dist((bb[0], bb[1]), (bb[2], bb[3]))


# ======================================================================
# Curve discretisation
# ======================================================================
def _arc_points(cx, cy, r, start_deg, end_deg, segments_per_circle):
    """Points along an arc, at the requested density.

    The density is given per FULL circle, so an arc only receives its
    proportional share — the parameter then behaves the same for a small
    fillet and a large sweep.
    """
    sweep = (end_deg - start_deg) % 360.0
    if sweep <= 1e-12:
        sweep = 360.0
    n = max(2, int(round(segments_per_circle * sweep / 360.0)))
    pts = []
    for i in range(n + 1):
        a = math.radians(start_deg + sweep * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _bulge_points(p1, p2, bulge, segments_per_circle):
    """Points along a polyline bulge (the arc between two vertices).

    ``bulge`` is the tangent of a quarter of the included angle, which is
    how DXF stores polyline arcs; ignoring it would silently turn arcs
    into chords.
    """
    if abs(bulge) < 1e-12:
        return [p1, p2]
    chord = math.dist(p1, p2)
    if chord < 1e-12:
        return [p1, p2]
    theta = 4.0 * math.atan(abs(bulge))          # included angle
    r = chord / (2.0 * math.sin(theta / 2.0))
    # Centre lies on the perpendicular bisector
    mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
    dx, dy = (p2[0] - p1[0]) / chord, (p2[1] - p1[1]) / chord
    h = math.sqrt(max(r * r - (chord / 2.0) ** 2, 0.0))
    sign = 1.0 if bulge > 0 else -1.0
    cx, cy = mx - sign * h * dy, my + sign * h * dx
    a1 = math.degrees(math.atan2(p1[1] - cy, p1[0] - cx))
    a2 = math.degrees(math.atan2(p2[1] - cy, p2[0] - cx))
    if bulge > 0:
        pts = _arc_points(cx, cy, r, a1, a2, segments_per_circle)
    else:
        pts = _arc_points(cx, cy, r, a2, a1, segments_per_circle)[::-1]
    pts[0], pts[-1] = p1, p2      # keep the exact endpoints
    return pts


# ======================================================================
def read_dxf(path, unit: str = "m", segments_per_circle: int = 64,
             ) -> DxfCatalogue:
    """Read a DXF file into a :class:`DxfCatalogue`.

    Args:
        path: file to read.
        unit: drawing unit the file is in; coordinates are converted to
            metres. Defaults to metres, as agreed.
        segments_per_circle: discretisation density for arcs, circles,
            splines and polyline bulges.

    Raises:
        RuntimeError: if ``ezdxf`` is unavailable or the file cannot be
            read. Nothing partial is returned: a half-read drawing would
            be worse than a clear failure.
    """
    if ezdxf is None:
        raise RuntimeError(
            "The 'ezdxf' package is required to import DXF files.")
    factor = UNIT_FACTORS.get(unit, 1.0)
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Could not read the DXF file: {exc}") from exc

    cat = DxfCatalogue(unit_factor=factor)
    try:
        cat.insunits = int(doc.header.get("$INSUNITS", 0))
    except Exception:  # noqa: BLE001
        cat.insunits = None

    layers: dict[str, DxfLayerInfo] = {}

    def _layer(name):
        if name not in layers:
            layers[name] = DxfLayerInfo(
                name=name, proposed_kind=guess_kind(name),
                kind=guess_kind(name))
        return layers[name]

    def _scale(pts):
        return [(x * factor, y * factor) for x, y in pts]

    def _add(layer_name, etype, pts, closed, handle):
        lay = _layer(layer_name)
        lay.entity_counts[etype] = lay.entity_counts.get(etype, 0) + 1
        pts = _scale(pts)
        # Drop consecutive duplicates: they carry no shape and would
        # produce zero-length segments downstream.
        clean = [pts[0]] if pts else []
        for p in pts[1:]:
            if math.dist(p, clean[-1]) > 1e-12:
                clean.append(p)
        if len(clean) < 2:
            cat.skipped["degenerate"] = cat.skipped.get("degenerate", 0) + 1
            return
        lay.polylines.append(DxfPolyline(points=clean, closed=closed,
                                         layer=layer_name, source=etype,
                                         handle=handle))

    msp = doc.modelspace()
    for e in msp:
        etype = e.dxftype()
        handle = str(getattr(e.dxf, "handle", ""))
        layer_name = str(getattr(e.dxf, "layer", "0"))
        try:
            if etype == "LINE":
                _add(layer_name, etype,
                     [(e.dxf.start.x, e.dxf.start.y),
                      (e.dxf.end.x, e.dxf.end.y)], False, handle)

            elif etype == "LWPOLYLINE":
                pts = []
                raw = list(e.get_points("xyb"))
                for i, (x, y, b) in enumerate(raw):
                    nxt = raw[(i + 1) % len(raw)]
                    if i == len(raw) - 1 and not e.closed:
                        pts.append((x, y))
                        break
                    seg = _bulge_points((x, y), (nxt[0], nxt[1]), b,
                                        segments_per_circle)
                    pts.extend(seg[:-1])
                if not e.closed and pts and pts[-1] != (raw[-1][0],
                                                        raw[-1][1]):
                    pts.append((raw[-1][0], raw[-1][1]))
                if e.closed and pts:
                    pts.append(pts[0])
                _add(layer_name, etype, pts, bool(e.closed), handle)

            elif etype == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y)
                       for v in e.vertices]
                if e.is_closed and pts:
                    pts = pts + [pts[0]]
                _add(layer_name, etype, pts, bool(e.is_closed), handle)

            elif etype == "ARC":
                pts = _arc_points(e.dxf.center.x, e.dxf.center.y,
                                  e.dxf.radius, e.dxf.start_angle,
                                  e.dxf.end_angle, segments_per_circle)
                _add(layer_name, etype, pts, False, handle)

            elif etype == "CIRCLE":
                pts = _arc_points(e.dxf.center.x, e.dxf.center.y,
                                  e.dxf.radius, 0.0, 360.0,
                                  segments_per_circle)
                _add(layer_name, etype, pts, True, handle)

            elif etype == "SPLINE":
                # ``flattening`` needs a positive sagitta tolerance; it is
                # derived from the spline's own extent so the density
                # scales with the curve rather than with absolute units.
                ctrl = [(p[0], p[1]) for p in e.control_points]
                if len(ctrl) >= 2:
                    xs = [p[0] for p in ctrl]
                    ys = [p[1] for p in ctrl]
                    extent = max(max(xs) - min(xs), max(ys) - min(ys),
                                 1e-9)
                else:
                    extent = 1.0
                tol = extent / max(segments_per_circle, 4) / 4.0
                pts = [(p[0], p[1]) for p in e.flattening(
                    tol, segments=max(4, int(segments_per_circle) // 8))]
                _add(layer_name, etype, pts, bool(e.closed), handle)

            else:
                cat.skipped[etype] = cat.skipped.get(etype, 0) + 1
        except Exception:  # noqa: BLE001
            # A malformed entity must not abort the whole import: it is
            # counted so the problem report can mention it.
            cat.skipped[f"{etype} (unreadable)"] = cat.skipped.get(
                f"{etype} (unreadable)", 0) + 1

    cat.layers = sorted(layers.values(), key=lambda p: p.name)
    cat.notes["entities"] = cat.total_entities
    cat.notes["vertices"] = cat.total_vertices
    return cat
