# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer in a DXF drawing, as native entities (v0.1.337).

Until this version the export never read ``project.annotations``: what the
user drew on the drawing stayed out of the drawing. Each visible annotation
is now written from the primitives of ``ogr_core.annotations.drawing``, the
same geometry the canvas draws, as the entity a CAD program has for it:

* lines, polylines, polygons, rectangles and circles: ``LWPOLYLINE`` (closed
  when the shape is), with a solid ``HATCH`` under it for a fill, its
  transparency the annotation's opacity;
* an arrow: its line and a ``SOLID`` head;
* text: ``TEXT``;
* a length, horizontal or vertical dimension: a real ``DIMENSION``
  (aligned, or linear at 0° or 90°), and an angle: an angular one — so the
  CAD program measures them itself. By decision of the owner they measure
  in DRAWING units: a 10 m dimension exported in millimetres reads 10000,
  as any dimension drawn in that file would. The decimals keep the
  millimetre;
* the axes: their two lines, the ticks and the coordinates as ``TEXT``;
* an image: an ``IMAGE`` linked to its file, written before the model so it
  lies under it. One whose file is missing, or whose size cannot be read,
  is the frame the canvas draws for it, and the report says so.

What has a size on screen on the canvas (an arrow head, a tick, a text) gets
a size in the drawing at ``model_per_px``: a thousandth of the model's
diagonal per pixel, so it keeps its proportion to the model whatever the
model's size and the drawing's unit.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.annotations import AnnotationKind
from ogr_core.annotations import drawing as d

#: Pixels of the canvas per thousandth of the model's diagonal.
PX_PER_DIAGONAL = 1000.0

_LINETYPES = {"solid": "Continuous", "dash": "DASHED", "dot": "DOT",
              "dashdot": "DASHDOT"}
_LINEWEIGHTS = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80,
                90, 100, 106, 120, 140, 158, 200, 211)


def visible_annotations(project) -> list:
    """The annotations the export writes: the visible ones, in their order."""
    layer = getattr(project, "annotations", None)
    if layer is None:
        return []
    return [a for a in layer.ordered() if a.style.visible and a.points]


def _rgb(colour: Optional[str]) -> Optional[tuple]:
    text = (colour or "").lstrip("#")
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _lineweight(px: float) -> int:
    """The DXF lineweight (hundredths of a millimetre) nearest a canvas
    width: a quarter of a millimetre per pixel."""
    want = max(0.0, float(px)) * 25.0
    return min(_LINEWEIGHTS, key=lambda w: abs(w - want))


def dimension_decimals(factor: float) -> int:
    """Decimals that keep the millimetre in a drawing whose unit is
    ``factor`` metres."""
    if not factor or factor <= 0:
        return 3
    return max(0, math.ceil(-math.log10(0.001 / factor) - 1e-9))


class AnnotationWriter:
    """Writes annotations into one drawing's model space."""

    def __init__(self, doc, msp, layer: str, factor: float, diagonal: float,
                 report) -> None:
        self.doc, self.msp, self.layer = doc, msp, layer
        self.factor = factor or 1.0
        #: model metres per canvas pixel
        self.mpp = max(diagonal, 1e-9) / PX_PER_DIAGONAL
        self.report = report

    # -- coordinates --------------------------------------------------
    def _p(self, pt) -> tuple:
        return (pt[0] / self.factor, pt[1] / self.factor)

    def _len(self, metres: float) -> float:
        return metres / self.factor

    def _attribs(self, a, dashed: bool = False) -> dict:
        out = {"layer": self.layer,
               "linetype": "DASHED" if dashed
               else _LINETYPES.get(a.style.line_style, "Continuous"),
               "lineweight": _lineweight(a.style.line_width)}
        rgb = _rgb(a.style.colour)
        if rgb is not None:
            from ezdxf.colors import rgb2int
            out["true_color"] = rgb2int(rgb)
        return out

    def _count(self, n: int = 1) -> None:
        self.report.count(self.layer, n)

    # -- the layer ----------------------------------------------------
    def pictures(self, annotations) -> None:
        """The images, written FIRST: in a DXF the entities drawn later lie
        on top, and an image is a backdrop."""
        for a in annotations:
            if a.kind == AnnotationKind.IMAGE:
                for prim in d.primitives(a):
                    self._primitive(prim, a)

    def others(self, annotations) -> None:
        for a in annotations:
            if a.kind == AnnotationKind.IMAGE:
                continue
            dim = d.dimension(a)
            if dim is not None:
                self._dimension(dim, a)
                continue
            for prim in d.primitives(a):
                self._primitive(prim, a)

    # -- primitives ---------------------------------------------------
    def _primitive(self, prim, a) -> None:
        if isinstance(prim, d.Stroke):
            self._stroke(prim, a)
        elif isinstance(prim, d.Mark):
            self._mark(prim, a)
        elif isinstance(prim, d.Label):
            self._label(prim, a)
        elif isinstance(prim, d.Picture):
            self._picture(prim, a)

    def _stroke(self, s: d.Stroke, a) -> None:
        pts = list(s.points)
        closed = s.closed
        if closed and len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-12:
            pts = pts[:-1]
        if s.filled and a.style.fill and len(pts) >= 3:
            self._hatch(pts, a)
        self.msp.add_lwpolyline([self._p(p) for p in pts], close=closed,
                                dxfattribs=self._attribs(a, s.dashed))
        self._count()

    def _hatch(self, pts, a) -> None:
        hatch = self.msp.add_hatch(dxfattribs={"layer": self.layer})
        rgb = _rgb(a.style.fill)
        if rgb is not None:
            hatch.rgb = rgb
        hatch.transparency = 1.0 - max(0.0, min(1.0,
                                                float(a.style.fill_opacity)))
        hatch.paths.add_polyline_path([self._p(p) for p in pts],
                                      is_closed=True)
        self._count()

    def _mark(self, m: d.Mark, a) -> None:
        x, y = m.at
        ang = math.radians(m.angle)
        ux, uy = math.cos(ang), math.sin(ang)
        attribs = self._attribs(a)
        attribs["linetype"] = "Continuous"
        if m.kind == "arrow":
            length = d.ARROW_PX * self.mpp
            half = d.ARROW_PX / 2.5 * self.mpp
            bx, by = x - length * ux, y - length * uy
            tri = [(x, y), (bx - half * uy, by + half * ux),
                   (bx + half * uy, by - half * ux)]
            self.msp.add_solid([self._p(p) for p in tri], dxfattribs=attribs)
            self._count()
        elif m.kind == "tick":
            h = d.TICK_PX * self.mpp
            self.msp.add_line(self._p((x - h * uy, y + h * ux)),
                              self._p((x + h * uy, y - h * ux)),
                              dxfattribs=attribs)
            self._count()
        elif m.kind == "arc":
            start, end = m.angle, m.angle + m.sweep
            if m.sweep < 0:
                start, end = end, start
            self.msp.add_arc(self._p(m.at), self._len(d.ARC_PX * self.mpp),
                             start, end, dxfattribs=attribs)
            self._count()
        elif m.kind == "cross":
            h = d.CROSS_PX * self.mpp
            self.msp.add_line(self._p((x - h, y)), self._p((x + h, y)),
                              dxfattribs=attribs)
            self.msp.add_line(self._p((x, y - h)), self._p((x, y + h)),
                              dxfattribs=attribs)
            self._count(2)

    def text_height(self, a) -> float:
        """A text's height in model metres: its points as pixels at 96 dpi
        (4/3 of a point), at ``mpp``."""
        return max(float(a.style.font_size), 1.0) * 4.0 / 3.0 * self.mpp

    def _label(self, lab: d.Label, a) -> None:
        from ezdxf.enums import TextEntityAlignment as T
        gap = d.TICK_PX * self.mpp
        x, y = lab.at
        place = {"at": (T.TOP_LEFT, (x, y)),
                 "above": (T.BOTTOM_CENTER, (x, y)),
                 "below": (T.TOP_CENTER, (x, y - gap)),
                 "left": (T.MIDDLE_RIGHT, (x - gap, y)),
                 "beside": (T.MIDDLE_LEFT, (x + gap, y))}
        align, at = place.get(lab.place, place["at"])
        attribs = self._attribs(a)
        attribs["height"] = self._len(self.text_height(a))
        text = self.msp.add_text(lab.text, dxfattribs=attribs)
        text.set_placement(self._p(at), align=align)
        self._count()

    def _picture(self, pic: d.Picture, a) -> None:
        from ogr_core.annotations.image_size import pixel_size
        size = pixel_size(pic.path) if pic.path else None
        if size is None:
            from .messages import EXPORT_SKIPPED_PICTURE, export_note
            self.report.skipped.append(export_note(
                EXPORT_SKIPPED_PICTURE, path=pic.path or "(none)"))
            for prim in d.picture_fallback(pic):
                self._primitive(prim, a)
            return
        x0, y0, x1, y1 = pic.corners
        image_def = self.doc.add_image_def(filename=pic.path,
                                           size_in_pixel=size)
        self.msp.add_image(image_def, insert=self._p((x0, y0)),
                           size_in_units=(self._len(x1 - x0),
                                          self._len(y1 - y0)),
                           dxfattribs={"layer": self.layer})
        self._count()

    # -- dimensions -----------------------------------------------------
    def _dimension(self, dim: d.Dimension, a) -> None:
        """A native DIMENSION: the CAD program measures it, in drawing
        units, from the geometry given."""
        attribs = self._attribs(a)
        attribs["linetype"] = "Continuous"
        text = dim.text or "<>"
        override = {
            "dimtxt": self._len(self.text_height(a)),
            "dimasz": self._len(d.ARROW_PX * self.mpp),
            "dimexo": 0.0,
            "dimdec": dimension_decimals(self.factor),
            "dimadec": 1,
        }
        if dim.kind == "aligned":
            p, q = dim.points
            dimension = self.msp.add_aligned_dim(
                p1=self._p(p), p2=self._p(q), distance=0.0, text=text,
                override=override, dxfattribs=attribs)
        elif dim.kind in ("horizontal", "vertical"):
            p, q = dim.points
            dimension = self.msp.add_linear_dim(
                base=self._p(p), p1=self._p(p), p2=self._p(q),
                angle=0.0 if dim.kind == "horizontal" else 90.0, text=text,
                override=override, dxfattribs=attribs)
        else:
            p, v, q = dim.points
            # ezdxf measures from p1 to p2 COUNTER-CLOCKWISE: the interior
            # angle (the one ``measured_value`` gives) needs the pair in
            # that sense, or it reports the reflex one (measured: (2, 0) to
            # (0, 2) about the origin gives 90, the same pair swapped 270)
            cross = ((p[0] - v[0]) * (q[1] - v[1])
                     - (p[1] - v[1]) * (q[0] - v[0]))
            p1, p2 = (p, q) if cross >= 0 else (q, p)
            a1 = math.atan2(p1[1] - v[1], p1[0] - v[0])
            a2 = math.atan2(p2[1] - v[1], p2[0] - v[0])
            mid = a1 + ((a2 - a1) % (2 * math.pi)) / 2.0
            r = d.ARC_PX * self.mpp
            base = (v[0] + r * math.cos(mid), v[1] + r * math.sin(mid))
            dimension = self.msp.add_angular_dim_3p(
                base=self._p(base), center=self._p(v), p1=self._p(p1),
                p2=self._p(p2), text=text, override=override,
                dxfattribs=attribs)
        dimension.render()
        self._count()
