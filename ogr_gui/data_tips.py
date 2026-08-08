# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Data Tips — phase M1.

Hovering over a material, a support or a load shows its properties. This
was asked for in the opening paragraph of the project brief and had never
been implemented.

Three modes, as the specification describes:

* ``NONE`` — nothing is shown.
* ``MINIMUM`` — the identity only: the name of the material, the type of
  support, the magnitude of a load. Enough to tell two objects apart
  while drawing, without a wall of text following the cursor.
* ``MAXIMUM`` — the full property list.

The text is built here rather than in the canvas so it can be tested
without a display, and so the same wording can be reused for a report or
a tooltip elsewhere. Values carry their **units**, because a cohesion
without kPa is not information.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Optional


class DataTipMode(Enum):
    NONE = "none"
    MINIMUM = "min"
    MAXIMUM = "max"


# Unit suffix per parameter name. Anything absent is shown unitless.
_UNITS = {
    "cohesion": "kPa", "friction_angle": "°", "unit_weight": "kN/m³",
    "sat_unit_weight": "kN/m³", "constant_u": "kPa", "phi_b": "°",
    "air_entry_value": "kPa", "sigma_ci": "MPa", "sigma_t": "kPa",
    "undrained_strength": "kPa", "cohesion_top": "kPa",
    "ks": "m/s", "specific_storage": "1/m",
    "anchor_capacity": "kN", "tensile_capacity": "kN",
    "plate_capacity": "kN", "bond_strength": "kN/m",
    "out_of_plane_spacing": "m", "in_plane_spacing": "m",
    "length": "m", "magnitude": "kPa", "magnitude_1": "kPa",
    "magnitude_2": "kPa", "angle_deg": "°",
}


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return "—"
        # Small magnitudes such as permeability need scientific notation
        # to say anything at all; 0.0000010 is not readable.
        if value != 0.0 and abs(value) < 1e-3:
            return f"{value:.3e}"
        return f"{value:.4g}"
    return str(value)


def _line(name: str, value) -> str:
    unit = _UNITS.get(name, "")
    label = name.replace("_", " ")
    text = _fmt(value)
    return f"{label}: {text} {unit}".rstrip()


# ======================================================================
def material_tip(material, mode: DataTipMode = DataTipMode.MAXIMUM,
                 region_name: Optional[str] = None) -> str:
    """Properties of a material."""
    if material is None or mode == DataTipMode.NONE:
        return ""
    name = getattr(material, "name", "material")
    if mode == DataTipMode.MINIMUM:
        return name
    lines = [name]
    if region_name:
        lines[0] = f"{name}  ({region_name})"
    strength = getattr(material, "strength", None)
    if strength is not None:
        model = getattr(strength, "DISPLAY_NAME", None) or \
            getattr(strength, "MODEL_ID", "")
        if model:
            lines.append(f"strength: {model}")
        for key, value in (getattr(strength, "params", {}) or {}).items():
            lines.append("  " + _line(key, value))
    attrs = ["unit_weight"]
    # v0.1.60 — γsat only appears when the material opts into it; otherwise
    # the tip would show a value the calculation never uses.
    if getattr(material, "use_sat_unit_weight", False):
        attrs.append("sat_unit_weight")
    for attr in attrs:
        v = getattr(material, attr, None)
        if v:
            lines.append(_line(attr, v))
    pp = getattr(material, "pore_pressure", None)
    if pp is not None:
        lines.append(f"pore pressure: {getattr(pp, 'value', pp)}")
    for attr in ("ru", "constant_u", "phi_b", "air_entry_value"):
        v = getattr(material, attr, None)
        if v:
            lines.append(_line(attr, v))
    hyd = getattr(material, "hydraulic", None)
    if hyd is not None:
        lines.append(_line("ks", getattr(hyd, "ks", None)))
    return "\n".join(lines)


def support_tip(support, mode: DataTipMode = DataTipMode.MAXIMUM) -> str:
    """Properties of a support instance."""
    if support is None or mode == DataTipMode.NONE:
        return ""
    stype = getattr(support, "support_type", None) or support
    label = getattr(stype, "DISPLAY_NAME", None) or \
        getattr(stype, "TYPE_ID", "support")
    if mode == DataTipMode.MINIMUM:
        return str(label)
    lines = [str(label)]
    head = getattr(support, "head", None)
    tail = getattr(support, "tail", None)
    if head is not None and tail is not None:
        lines.append(f"from ({tail.x:.3f}, {tail.y:.3f}) "
                     f"to ({head.x:.3f}, {head.y:.3f})")
        lines.append(_line("length", math.dist((tail.x, tail.y),
                                               (head.x, head.y))))
    for key in (getattr(stype, "PARAMETERS", {}) or {}):
        v = getattr(stype, key, None)
        if v is not None:
            lines.append("  " + _line(key, v))
    for attr, label2 in (("force_application", "application"),
                         ("force_orientation", "orientation")):
        v = getattr(support, attr, None) or getattr(stype, attr, None)
        if v is not None:
            lines.append(f"{label2}: {getattr(v, 'value', v)}")
    return "\n".join(lines)


def load_tip(load, mode: DataTipMode = DataTipMode.MAXIMUM) -> str:
    """Properties of a distributed or line load."""
    if load is None or mode == DataTipMode.NONE:
        return ""
    name = getattr(load, "name", None) or type(load).__name__
    mag = getattr(load, "magnitude", None)
    if mag is None:
        mag = getattr(load, "magnitude_1", None)
    if mode == DataTipMode.MINIMUM:
        return f"{name}: {_fmt(mag)} kPa" if mag is not None else str(name)
    lines = [str(name)]
    for key in ("magnitude", "magnitude_1", "magnitude_2", "angle_deg"):
        v = getattr(load, key, None)
        if v is not None:
            lines.append(_line(key, v))
    for attr in ("orientation", "distribution"):
        v = getattr(load, attr, None)
        if v is not None:
            lines.append(f"{attr}: {getattr(v, 'value', v)}")
    start = getattr(load, "start", None)
    end = getattr(load, "end", None)
    point = getattr(load, "point", None)
    if start is not None and end is not None:
        lines.append(f"from ({start.x:.3f}, {start.y:.3f}) "
                     f"to ({end.x:.3f}, {end.y:.3f})")
    elif point is not None:
        lines.append(f"at ({point.x:.3f}, {point.y:.3f})")
    return "\n".join(lines)


def boundary_tip(boundary, mode: DataTipMode = DataTipMode.MAXIMUM) -> str:
    """Identity and size of a boundary."""
    if boundary is None or mode == DataTipMode.NONE:
        return ""
    label = getattr(boundary.btype, "name", "boundary").replace("_", " ")
    if mode == DataTipMode.MINIMUM:
        return label
    verts = list(boundary.polyline.vertices)
    length = sum(math.dist((a.x, a.y), (b.x, b.y))
                 for a, b in zip(verts, verts[1:]))
    lines = [label, f"vertices: {len(verts)}", _line("length", length)]
    if getattr(boundary.polyline, "closed", False):
        lines.append("closed")
    return "\n".join(lines)


# ======================================================================
def tip_at(project, x: float, y: float,
           mode: DataTipMode = DataTipMode.MAXIMUM,
           radius: float = 1.0) -> str:
    """The data tip for a model position.

    Order of precedence is deliberate: the small, precisely-placed things
    are tested first, because a load arrow sitting on top of a material
    region should describe the arrow — the material is everywhere, the
    arrow is only there.
    """
    if mode == DataTipMode.NONE:
        return ""

    # Loads
    for ld in getattr(project, "line_loads", []):
        pt = getattr(ld, "point", None)
        if pt is not None and math.dist((pt.x, pt.y), (x, y)) <= radius:
            return load_tip(ld, mode)
    for ld in getattr(project, "distributed_loads", []):
        a, b = getattr(ld, "start", None), getattr(ld, "end", None)
        if a is None or b is None:
            continue
        if _near_segment(x, y, a.x, a.y, b.x, b.y) <= radius:
            return load_tip(ld, mode)

    # Supports
    for s in getattr(project, "supports", []):
        h, t = getattr(s, "head", None), getattr(s, "tail", None)
        if h is None or t is None:
            continue
        if _near_segment(x, y, t.x, t.y, h.x, h.y) <= radius:
            return support_tip(s, mode)

    # Material region under the cursor
    try:
        from ogr_core.geometry.regions import build_regions
        ext = next((b for b in project.boundaries
                    if b.btype.name == "EXTERNAL"), None)
        mats = [b for b in project.boundaries
                if b.btype.name == "MATERIAL"]
        if ext is not None:
            for i, region in enumerate(build_regions(ext, mats)):
                if not _region_contains(region, x, y):
                    continue
                material = _material_of(project, region)
                if material is not None:
                    return material_tip(material, mode,
                                        region_name=f"region {i + 1}")
                # A region with no material assigned yet is worth
                # reporting too: "region 2 — no material assigned" tells
                # the user something actionable, whereas silence looks
                # like the tip is broken.
                return (f"region {i + 1}\nno material assigned"
                        if mode != DataTipMode.MINIMUM
                        else f"region {i + 1}")
    except Exception:  # noqa: BLE001
        pass

    # Otherwise, the nearest boundary
    best = None
    for b in getattr(project, "boundaries", []):
        verts = list(b.polyline.vertices)
        for p, q in zip(verts, verts[1:]):
            d = _near_segment(x, y, p.x, p.y, q.x, q.y)
            if d <= radius and (best is None or d < best[0]):
                best = (d, b)
    if best is not None:
        return boundary_tip(best[1], mode)
    return ""


def _near_segment(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-30:
        return math.dist((px, py), (ax, ay))
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.dist((px, py), (ax + t * dx, ay + t * dy))


def _region_contains(region, x: float, y: float) -> bool:
    """Point-in-region test.

    ``MaterialRegion`` exposes no containment test of its own, so Shapely
    does the work when available and a ray-casting fallback keeps the tip
    working without it.
    """
    poly = getattr(region, "polygon", None)
    if poly is None:
        return False
    pts = [(v.x, v.y) for v in poly.vertices]
    if len(pts) < 3:
        return False
    try:
        from shapely.geometry import Point, Polygon
        return Polygon(pts).covers(Point(x, y))
    except Exception:  # noqa: BLE001
        pass
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xint:
                inside = not inside
    return inside


def _material_of(project, region):
    mat_id = getattr(region, "material_id", None)
    if mat_id is None:
        return None
    for m in getattr(project, "materials", []):
        if m.id == mat_id:
            return m
    return None
