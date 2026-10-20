# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer on a matplotlib figure (v0.1.338, D336).

The PNG an agent renders (``render.render_png``, the ``model_render`` tool)
drew the model and its surfaces, and not what the user had drawn on it. This
draws the layer from the primitives of ``ogr_core.annotations.drawing`` —
the geometry the canvas and the DXF export draw from — as matplotlib
artists:

* strokes in data coordinates, with the annotation's colour, width and line
  style, and its fill under a closed one;
* the marks (arrow heads, the ticks of dimensions and axes, the arc of an
  angle, a one-point cross) in PIXELS at their model point, through
  ``IdentityTransform() + ScaledTranslation(x, y, ax.transData)``: they keep
  their size whatever the extent of the figure, as on the canvas;
* the labels with ``annotate`` and an offset in points;
* an image over its rectangle, under the model; one that cannot be read is
  its frame and its name.

Marks and labels are added as artists that do not move the axes' limits: the
picture keeps the model's framing.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.annotations import AnnotationKind
from ogr_core.annotations import drawing as d

#: Above the model's surfaces and labels (render_png draws them up to 9).
Z_ANNOTATION = 12
#: Under the regions (render_png fills them at 1), over the grid (0).
Z_IMAGE = 0.5
#: A screen pixel in points, at the 96 dpi the canvas's sizes assume.
PT_PER_PX = 0.75

_STYLES = {"solid": "-", "dash": "--", "dot": ":", "dashdot": "-."}


def visible(project) -> list:
    layer = getattr(project, "annotations", None)
    if layer is None:
        return []
    return [a for a in layer.ordered() if a.style.visible and a.points]


def draw_annotations(ax, project) -> list:
    """Draw ``project``'s visible annotations on ``ax``; returns the artists
    added, in drawing order."""
    out = []
    for a in visible(project):
        z = (Z_IMAGE if a.kind == AnnotationKind.IMAGE else Z_ANNOTATION) \
            + 1e-3 * a.z_order
        for prim in d.primitives(a):
            out += _DRAW[type(prim)](ax, prim, a, z)
    return out


# ----------------------------------------------------------------------
def _pixels(ax, x, y):
    """A transform for a path drawn in display pixels at the data point
    (x, y)."""
    from matplotlib.transforms import IdentityTransform, ScaledTranslation
    return IdentityTransform() + ScaledTranslation(x, y, ax.transData)


def _px(ax, n: float) -> float:
    """``n`` canvas pixels in display pixels of this figure."""
    return n * ax.figure.dpi / 96.0


def _line_width(a) -> float:
    """The annotation's width, in canvas pixels, as matplotlib points."""
    return max(float(a.style.line_width), 0.1) * PT_PER_PX


def _stroke(ax, s: d.Stroke, a, z) -> list:
    xs = [p[0] for p in s.points]
    ys = [p[1] for p in s.points]
    if s.closed and (xs[0], ys[0]) != (xs[-1], ys[-1]):
        xs, ys = xs + xs[:1], ys + ys[:1]
    out = []
    if s.filled and a.style.fill:
        out += ax.fill(xs, ys, color=a.style.fill, linewidth=0,
                       alpha=max(0.0, min(1.0, float(a.style.fill_opacity))),
                       zorder=z)
    style = "--" if s.dashed else _STYLES.get(a.style.line_style, "-")
    out += ax.plot(xs, ys, color=a.style.colour, linewidth=_line_width(a),
                   linestyle=style, zorder=z)
    return out


def _mark(ax, m: d.Mark, a, z) -> list:
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    ang = math.radians(m.angle)
    ux, uy = math.cos(ang), math.sin(ang)
    filled = False
    if m.kind == "arrow":
        length, half = _px(ax, d.ARROW_PX), _px(ax, d.ARROW_PX / 2.5)
        bx, by = -length * ux, -length * uy
        verts = [(0.0, 0.0), (bx - half * uy, by + half * ux),
                 (bx + half * uy, by - half * ux), (0.0, 0.0)]
        codes = [Path.MOVETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]
        filled = True
    elif m.kind == "tick":
        h = _px(ax, d.TICK_PX)
        verts = [(-h * uy, h * ux), (h * uy, -h * ux)]
        codes = [Path.MOVETO, Path.LINETO]
    elif m.kind == "arc":
        lo, hi = sorted((m.angle, m.angle + m.sweep))
        arc = Path.arc(lo, hi)
        r = _px(ax, d.ARC_PX)
        verts = [(x * r, y * r) for x, y in arc.vertices]
        codes = list(arc.codes)
    elif m.kind == "cross":
        h = _px(ax, d.CROSS_PX)
        verts = [(-h, 0.0), (h, 0.0), (0.0, -h), (0.0, h)]
        codes = [Path.MOVETO, Path.LINETO, Path.MOVETO, Path.LINETO]
    else:
        return []
    patch = PathPatch(Path(verts, codes), transform=_pixels(ax, *m.at),
                      edgecolor=a.style.colour,
                      facecolor=a.style.colour if filled else "none",
                      linewidth=_line_width(a), zorder=z, clip_on=False)
    ax.add_artist(patch)
    return [patch]


_PLACES = {"at": ("left", "top", (0.0, 0.0)),
           "above": ("center", "bottom", (0.0, 0.0)),
           "below": ("center", "top", (0.0, -d.TICK_PX)),
           "left": ("right", "center", (-d.TICK_PX, 0.0)),
           "beside": ("left", "center", (d.TICK_PX, 0.0))}


def _label(ax, lab: d.Label, a, z) -> list:
    ha, va, (dx, dy) = _PLACES.get(lab.place, _PLACES["at"])
    text = ax.annotate(lab.text, xy=lab.at,
                       xytext=(dx * PT_PER_PX, dy * PT_PER_PX),
                       textcoords="offset points", ha=ha, va=va,
                       fontsize=max(float(a.style.font_size), 1.0),
                       color=a.style.colour, zorder=z,
                       annotation_clip=False)
    return [text]


def _picture(ax, pic: d.Picture, a, z) -> list:
    x0, y0, x1, y1 = pic.corners
    try:
        import matplotlib.image as mpimg
        img = mpimg.imread(pic.path)
    except Exception:  # noqa: BLE001 - a missing or unreadable file
        out = []
        for prim in d.picture_fallback(pic):
            out += _DRAW[type(prim)](ax, prim, a, z)
        return out
    # the axes' own aspect: imshow would otherwise impose its own
    return [ax.imshow(img, extent=(x0, x1, y0, y1), zorder=z,
                      aspect=ax.get_aspect(), interpolation="bilinear")]


_DRAW = {d.Stroke: _stroke, d.Mark: _mark, d.Label: _label,
         d.Picture: _picture}
