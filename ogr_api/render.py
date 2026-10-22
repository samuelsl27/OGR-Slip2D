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


def _hold_limits(ax, xlim, ylim) -> None:
    """Set the axes' limits and leave autoscaling on.

    v0.1.339 -- ``set_xlim`` turns autoscaling off, and the equal aspect
    then widens one side at draw time with a warning ("Ignoring fixed x
    limits to fulfill fixed data aspect..."), printed on every PNG since
    v0.1.338: 26 times in its suite, none in v0.1.337's. Autoscaling back
    on keeps the limits -- ``set_xlim`` marks them up to date, and nothing
    added after this asks for a new autoscale -- and the aspect widens the
    same side by the same amount, without the warning."""
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_autoscale_on(True)


def _draw_grid(fig, ax, grid) -> None:
    """The minimum factor of safety at each slip centre, as filled contours
    with their colour scale (low red, high blue), the centres as dots and
    the critical centre as a star (v0.1.339, D336)."""
    xs, ys, fos = grid["x"], grid["y"], grid["fos"]
    try:
        from matplotlib.tri import Triangulation
        tri = Triangulation(xs, ys)
        cs = ax.tricontourf(tri, fos, levels=12, cmap="RdYlBu", alpha=0.85,
                            zorder=3)
        fig.colorbar(cs, ax=ax, shrink=0.8,
                     label=grid.get("label", "minimum factor of safety"))
    except Exception:  # noqa: BLE001 - collinear centres: dots only
        pass
    ax.plot(xs, ys, ".", color="#333333", markersize=2, zorder=4)
    crit = grid.get("critical")
    if crit is not None:
        ax.plot([crit[0]], [crit[1]], "*", color="#000000", markersize=11,
                zorder=10, label=grid.get("critical_label",
                                          "critical centre"))


def render_png(project, *, surfaces: Iterable = (), width: int = 900,
               height: int = 600, dpi: int = 100, labels: bool = True,
               title: Optional[str] = None,
               slice_lines: bool = True, field=None,
               free_surface=None, annotations: bool = True,
               extent=None, grid=None) -> bytes:
    """PNG bytes of ``project`` with ``surfaces`` drawn on it.

    ``surfaces`` is a sequence of ``(label, LEMResult)``; each is drawn as
    the base of its slices, which is the surface the engine priced —
    including a tension-crack truncation or a composite segment, which a
    circle drawn from its centre and radius would not show.

    ``field`` (v0.1.200) is ``(label, nodal values, mesh)``: filled
    contours over the finite-element mesh, as the Interpret groundwater
    window draws them; ``free_surface`` a list of (x, y), drawn dashed.

    ``annotations`` (v0.1.338, D336) draws the model's annotation layer
    over it (``render_annotations``), inside the model's framing.

    v0.1.339 (D336) -- for the report's figures: ``extent`` is the frame
    ``(xmin, xmax, ymin, ymax)`` instead of the model's own, and ``grid`` the
    minimum factor of safety at each slip centre (``report_figures
    .grid_data``), drawn as filled contours with their scale, the centres as
    dots and the critical one marked.
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

    if field is not None:
        from matplotlib.tri import Triangulation

        label, values, mesh = field
        tri = Triangulation([n.x for n in mesh.nodes],
                            [n.y for n in mesh.nodes],
                            [list(e.nodes) for e in mesh.elements])
        cs = ax.tricontourf(tri, list(values), levels=16, cmap="viridis",
                            alpha=0.9, zorder=2)
        fig.colorbar(cs, ax=ax, label=label, shrink=0.8)
    if free_surface:
        ax.plot([p[0] for p in free_surface], [p[1] for p in free_surface],
                color="#0b3d91", lw=2.0, ls="--", zorder=5,
                label="free surface (P = 0)")

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
    if grid is not None:
        _draw_grid(fig, ax, grid)
    if surfaces or free_surface:
        ax.legend(loc="best", fontsize=8)

    ax.margins(0.05)
    ax.autoscale_view()
    if annotations:
        # v0.1.338 (D336) — the layer the user drew, over the model and in
        # its framing: an annotation far away does not shrink the slope
        from .render_annotations import draw_annotations
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        model_data = ax.dataLim.frozen()
        draw_annotations(ax, project)
        # the equal aspect with adjustable data limits re-frames the axes
        # from their DATA limits when drawn, and an annotation far away is
        # in them: measured, a line to (1000, 1000) re-framed the whole
        # picture (43714 pixels moved). The model's data limits go back.
        ax.dataLim.set(model_data)
        _hold_limits(ax, xlim, ylim)
    if extent is not None:
        # v0.1.339 — the frame asked for is also the data the equal aspect
        # keeps: with the data inside the view, matplotlib may SHRINK one
        # side down to the data, about the view's centre, and cut off the
        # centres at the edge of a search area; with the frame as the data
        # it can only widen it.
        from matplotlib.transforms import Bbox
        ax.dataLim.set(Bbox.from_extents(extent[0], extent[2], extent[1],
                                         extent[3]))
        _hold_limits(ax, extent[:2], extent[2:])
    if title:
        ax.set_title(title, fontsize=10)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    return buf.getvalue()
