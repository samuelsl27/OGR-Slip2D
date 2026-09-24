# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A PNG of the model, and of a slip surface on it, without Qt.

The interface draws the model on a ``QGraphicsScene``, which needs a
``QGuiApplication`` on the main thread; the MCP server runs each call on a
worker thread and must not depend on a display. So this is a second,
deliberately plain drawing with matplotlib's Agg backend, through the
object-oriented API (``Figure`` + ``FigureCanvasAgg``): no ``pyplot``, so
no global figure state and no interference with the interface's own QtAgg
charts in the same process.

It is a view for a reader — a person or a model with vision — and not a
second canvas: colours come from the model (``Material.color``,
``BoundaryType.default_color``), and anything it cannot draw faithfully it
leaves out rather than approximates. The live bridge of phase F4 returns a
capture of the real canvas instead.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import io
import math
from typing import Iterable, Optional

_STYLE = {
    "EXTERNAL": dict(lw=1.8, ls="-"),
    "MATERIAL": dict(lw=1.0, ls="-"),
    "WATER_TABLE": dict(lw=1.6, ls="-"),
    "PIEZOMETRIC": dict(lw=1.4, ls="--"),
    "DRAWDOWN": dict(lw=1.4, ls="-."),
    "TENSION_CRACK": dict(lw=1.4, ls=":"),
    "BLOCK_SEARCH_OBJECT": dict(lw=1.2, ls="--"),
    "WEAK_LAYER": dict(lw=2.4, ls="-"),
    "ANISOTROPIC_SURFACE": dict(lw=1.0, ls=":"),
}

_SURFACE_COLOURS = ("#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e",
                    "#8c564b", "#e377c2", "#17becf", "#7f7f7f")


def _xy(vertices) -> tuple[list, list]:
    return [v.x for v in vertices], [v.y for v in vertices]


def _ring_path(outer, holes):
    """A matplotlib ``Path`` of a ring with holes: each ring a closed
    subpath, so the even-odd fill leaves the holes unpainted."""
    from matplotlib.path import Path

    verts, codes = [], []
    for ring in [outer] + [[(v.x, v.y) for v in h.vertices] for h in holes]:
        if len(ring) < 3:
            continue
        verts += list(ring) + [ring[0]]
        codes += ([Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
                  + [Path.CLOSEPOLY])
    return Path(verts, codes)


def _surface_path(res) -> Optional[tuple[list, list]]:
    """The base of the slices, left to right: what was actually analysed."""
    slices = getattr(res, "slices", None)
    if not slices or len(slices) == 0:
        return None
    xs = [slices[0].base_x_left]
    ys = [slices[0].base_y_left]
    for s in slices:
        xs.append(s.base_x_right)
        ys.append(s.base_y_right)
    return xs, ys


def render_png(project, *, surfaces: Iterable = (), width: int = 900,
               height: int = 600, dpi: int = 100, labels: bool = True,
               title: Optional[str] = None,
               slice_lines: bool = True) -> bytes:
    """PNG bytes of ``project`` with ``surfaces`` drawn on it.

    ``surfaces`` is a sequence of ``(label, LEMResult)``; each is drawn as
    the base of its slices, which is the surface the engine priced —
    including a tension-crack truncation or a composite segment, which a
    circle drawn from its centre and radius would not show.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import PathPatch
    from matplotlib.patches import Polygon as MplPolygon

    surfaces = list(surfaces)
    width = int(max(200, min(4000, width)))
    height = int(max(150, min(4000, height)))
    fig = Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, color="#e6e6e6", linewidth=0.6, zorder=0)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")

    xmin, ymin, xmax, ymax = project.bounding_box()
    size = max(xmax - xmin, ymax - ymin, 1e-9)

    # Regions, coloured by the material the model resolves for them.
    default = project.materials[0] if project.materials else None
    for region in project.resolve_regions():
        mat = project.material_by_id(getattr(region, "material_id", None)) \
            or default
        colour = getattr(mat, "color", "#dddddd") if mat else "#dddddd"
        pts = [(v.x, v.y) for v in region.polygon.vertices]
        holes = getattr(region, "holes", None) or []
        if len(pts) >= 3 and not holes:
            ax.add_patch(MplPolygon(pts, closed=True, facecolor=colour,
                                    edgecolor="none", alpha=0.85, zorder=1))
        elif len(pts) >= 3:
            # v0.1.197 — a region with a lens: one path, the outer ring and
            # each hole as its own closed subpath, so the lens is not
            # painted over with this region's colour.
            ax.add_patch(PathPatch(_ring_path(pts, holes), facecolor=colour,
                                   edgecolor="none", alpha=0.85, zorder=1))
        if labels and mat is not None:
            cx, cy = (region.inside_point
                      if holes and getattr(region, "inside_point", None)
                      else region.centroid())
            ax.text(cx, cy, mat.name, ha="center", va="center", fontsize=8,
                    zorder=6, bbox=dict(boxstyle="round,pad=0.2",
                                        fc="white", ec="none", alpha=0.7))

    for b in project.boundaries:
        if not getattr(b, "visible", True):
            continue
        xs, ys = _xy(b.polyline.vertices)
        if b.polyline.closed and xs:
            xs, ys = xs + xs[:1], ys + ys[:1]
        style = _STYLE.get(b.btype.name, dict(lw=1.0, ls="-"))
        colour = b.color or b.btype.default_color
        if len(xs) == 1:
            ax.plot(xs, ys, "o", color=colour, zorder=4)
        else:
            ax.plot(xs, ys, color=colour, linewidth=style["lw"],
                    linestyle=style["ls"], zorder=4)
        if b.btype.name == "WATER_TABLE" and len(xs) >= 2:
            # The conventional inverted triangle over the phreatic line.
            mid = len(xs) // 2
            mx = (xs[mid - 1] + xs[mid]) / 2
            my = (ys[mid - 1] + ys[mid]) / 2
            ax.plot([mx], [my + 0.015 * size], marker="v", color=colour,
                    markersize=8, zorder=5)

    arrow = 0.05 * size
    for load in getattr(project, "distributed_loads", []):
        dx, dy = load.direction_vector()
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            px = load.start.x + t * (load.end.x - load.start.x)
            py = load.start.y + t * (load.end.y - load.start.y)
            ax.annotate("", xy=(px, py),
                        xytext=(px - dx * arrow, py - dy * arrow),
                        arrowprops=dict(arrowstyle="->", color="#c0392b",
                                        lw=1.0), zorder=7)
    from ogr_core.loads.loads import line_load_direction
    for load in getattr(project, "line_loads", []):
        try:
            dx, dy = line_load_direction(project, load)
        except ValueError:      # boundary-relative, off the ground: the
            dx, dy = 0.0, -1.0  # analysis refuses it; draw it plainly
        px, py = load.point.x, load.point.y
        ax.annotate("", xy=(px, py),
                    xytext=(px - dx * 1.6 * arrow, py - dy * 1.6 * arrow),
                    arrowprops=dict(arrowstyle="-|>", color="#c0392b",
                                    lw=1.6), zorder=7)
    for s in getattr(project, "supports", []):
        ax.plot([s.head.x, s.tail.x], [s.head.y, s.tail.y],
                color="#1b7f3b", linewidth=1.4, zorder=6)

    for i, (label, res) in enumerate(surfaces):
        path = _surface_path(res)
        if path is None:
            continue
        colour = _SURFACE_COLOURS[i % len(_SURFACE_COLOURS)]
        xs, ys = path
        if slice_lines and i == 0:
            for s in res.slices:
                top = getattr(s, "top_y_left", None)
                if top is not None and math.isfinite(top):
                    ax.plot([s.base_x_left, s.base_x_left],
                            [s.base_y_left, top], color=colour,
                            linewidth=0.5, alpha=0.5, zorder=8)
        ax.plot(xs, ys, color=colour, linewidth=2.2, zorder=9, label=label)
    if surfaces:
        ax.legend(loc="best", fontsize=8)

    ax.margins(0.05)
    ax.autoscale_view()
    if title:
        ax.set_title(title, fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    return buf.getvalue()
