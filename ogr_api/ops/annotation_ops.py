# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer — drawings, text, dimensions — and its one bridge to
the model.

Annotations never reach an analysis (``tech-stack.md``: the solver never
reads ``Project.annotations``), which is also why editing them does not
mark a result as stale (``snapshot.model_hash``). The ONLY way one becomes
geometry is :func:`annotation_to_boundary`, explicit and one-way (AGENTS.md:
"do not convert annotations into geometry automatically").

That bridge goes through the same checks as ``boundary_add`` — one
External, one water table, ``ensure_ccw``, no self-crossing — which the
interface's *Convert Tool to Boundary* skips (reported in v0.1.196). And a
closed shape's outline repeats its first point at the end, which a closed
polyline must not; the repeat is dropped. A closed shape can become the
External or, since v0.1.197, a material LENS (a hole of the region around
it); the open line types refuse it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
from typing import Any, Optional

from ..coerce import coerce_enum, coerce_value, point, points, type_hints
from ..errors import Conflict, InvalidArgument, did_you_mean, unknown
from ..results import json_safe
from . import operation

#: Minimum points per annotation kind, as the interface asks for them.
_MIN_POINTS = {"text": 1, "axes": 1, "dimension_angle": 3, "image": 2}
_LINE_STYLES = ("solid", "dash", "dot", "dashdot")


def annotation_info(a) -> dict:
    d = json_safe(a.to_dict())
    value = a.measured_value()
    if value is not None:
        d["measured_value"] = json_safe(value)
    return d


def _find(project, ref):
    for a in project.annotations.ordered():
        if a.id == ref:
            return a
    raise unknown("annotation", ref,
                  [a.id for a in project.annotations.ordered()][:40])


def _style(base, raw: Optional[dict]):
    from ogr_core.annotations.annotation import AnnotationStyle

    style = dataclasses.replace(base) if base is not None \
        else AnnotationStyle()
    if not raw:
        return style
    if not isinstance(raw, dict):
        raise InvalidArgument("style is an object of style fields.")
    names = [f.name for f in dataclasses.fields(AnnotationStyle)]
    hints = type_hints(AnnotationStyle)
    for key, val in raw.items():
        if key not in names:
            hint = did_you_mean(key, names)
            raise InvalidArgument(f"{key!r} is not a style field.",
                                  hint=(hint + " " if hint else "")
                                  + f"Fields: {names}.")
        v = coerce_value(val, hints[key], f"style.{key}")
        if key == "line_style" and v not in _LINE_STYLES:
            raise InvalidArgument(f"line_style is one of {_LINE_STYLES}.")
        setattr(style, key, v)
    return style


@operation("annotation_set", toolset="annotations", mutates=True)
def annotation_set(ws, project_id: Optional[str] = None,
                   annotation: Optional[str] = None,
                   kind: Optional[str] = None,
                   points_xy: Optional[list] = None,
                   text: Optional[str] = None,
                   style: Optional[dict] = None,
                   visible: Optional[bool] = None,
                   dx: Optional[float] = None, dy: Optional[float] = None,
                   z: Optional[str] = None) -> dict:
    """Add an annotation (line, arrow, text, dimension...) or change one
    (annotation=...); annotation='all' with visible shows or hides all."""
    import uuid

    from ogr_core.annotations.annotation import Annotation, AnnotationKind

    def edit(project):
        layer = project.annotations
        if annotation == "all":
            if visible is None or any(v is not None for v in (
                    kind, points_xy, text, style, dx, dy, z)):
                raise InvalidArgument("annotation='all' only takes "
                                      "visible.")
            layer.set_all_visible(coerce_value(visible, bool, "visible"))
            return {"visible": bool(visible),
                    "count": len(layer.ordered())}
        creating = annotation is None
        if creating:
            k = coerce_enum(kind, AnnotationKind, "kind")
            a = Annotation(kind=k, id=uuid.uuid4().hex[:12])
            if points_xy is None:
                raise InvalidArgument("A new annotation needs points_xy.")
        else:
            a = _find(project, annotation)
            if kind is not None and coerce_enum(
                    kind, AnnotationKind, "kind") != a.kind:
                raise Conflict("An annotation's kind cannot change.")
        if points_xy is not None:
            need = _MIN_POINTS.get(a.kind.value, 2)
            a.points = [tuple(p) for p in points(points_xy, "points_xy",
                                                 minimum=need)]
        if a.kind.value == "image":
            if text is not None or creating:
                if text is None:
                    raise InvalidArgument("An image annotation needs text: "
                                          "the image file's path.")
                a.text = str(ws.resolve_path(text))
        elif text is not None:
            if a.kind.value != "text" and not a.kind.value.startswith(
                    "dimension"):
                raise Conflict(f"text is not shown by a {a.kind.value!r}.")
            a.text = str(text)
        if style is not None or visible is not None:
            a.style = _style(a.style, style)
            if visible is not None:
                a.style.visible = coerce_value(visible, bool, "visible")
        if dx is not None or dy is not None:
            a.translate(coerce_value(dx or 0.0, float, "dx"),
                        coerce_value(dy or 0.0, float, "dy"))
        if creating:
            layer.add(a)
        if z is not None:
            if z == "front":
                layer.bring_to_front(a.id)
            elif z == "back":
                layer.send_to_back(a.id)
            else:
                raise InvalidArgument("z is 'front' or 'back'.")
        return {"annotation": annotation_info(a), "created": creating}

    return ws.mutate(project_id, "Set annotation", edit)


@operation("annotation_delete", toolset="annotations", mutates=True)
def annotation_delete(ws, annotations: Any,
                      project_id: Optional[str] = None) -> dict:
    """Delete annotations by id, or 'all'."""
    def edit(project):
        layer = project.annotations
        if annotations == "all":
            n = len(layer.ordered())
            layer.clear()
        else:
            refs = [annotations] if isinstance(annotations, str) else \
                list(annotations or [])
            if not refs:
                raise InvalidArgument("annotations is a list of ids, or "
                                      "'all'.")
            for r in refs:
                layer.remove(_find(project, r).id)
            n = len(refs)
        return {"deleted": n}

    return ws.mutate(project_id, "Delete annotations", edit)


@operation("annotation_to_boundary", toolset="annotations", mutates=True)
def annotation_to_boundary(ws, annotation: str, type: str,
                           project_id: Optional[str] = None,
                           assign_to: Any = None,
                           replace: bool = False) -> dict:
    """Turn a drawn shape into a model boundary (the one explicit bridge);
    the annotation stays."""
    from ogr_core.annotations.annotation import to_boundary_points

    from .model import boundary_add

    allowed = ("external", "material", "water_table", "piezometric",
               "tension_crack")
    if type not in allowed:
        raise unknown("boundary type for a converted shape", type, allowed)
    with ws.reading(project_id, "annotation_to_boundary") as project:
        a = _find(project, annotation)
        pts = to_boundary_points(a)
        if pts is None:
            raise Conflict(f"A {a.kind.value!r} annotation cannot become "
                           f"geometry.",
                           hint="Lines, polylines, polygons, rectangles "
                                "and circles can.")
        pts = [list(p) for p in pts]
        closed = None
        if type == "external":
            if not a.closed:
                raise Conflict("Only a closed shape can become the External "
                               "boundary.")
        elif a.closed and type == "material":
            # v0.1.197 — a closed shape as a material boundary is a LENS,
            # a hole of the region around it now that regions have holes.
            closed = True
        elif a.closed:
            # A water table, a piezometric line or a crack is an OPEN
            # polyline; a closed shape as one of them means nothing.
            raise Conflict(f"A closed {a.kind.value!r} cannot become a "
                           f"{type}; draw it as a line or polyline.")
        if a.closed and len(pts) > 2 and pts[0] == pts[-1]:
            # The outline repeats its first point; a closed polyline's
            # closing edge is implicit.
            pts = pts[:-1]
    return boundary_add(ws, type=type, points=pts, project_id=project_id,
                        assign_to=assign_to, replace=replace,
                        closed=closed)


@operation("properties_table", toolset="annotations")
def properties_table(ws, what: str = "materials",
                     project_id: Optional[str] = None) -> dict:
    """The materials, support types or hydraulic properties as a table."""
    from .project import material_info
    from .supports import type_info

    kinds = ("materials", "supports", "hydraulic")
    if what not in kinds:
        raise unknown("table", what, kinds)
    with ws.reading(project_id, "properties_table") as project:
        if what == "materials":
            rows = [material_info(m) for m in project.materials]
        elif what == "supports":
            rows = [type_info(st) for st in project.support_types]
        else:
            rows = [{"material": m.name,
                     "hydraulic": json_safe(m.hydraulic.to_dict())
                     if m.hydraulic is not None else None}
                    for m in project.materials]
    return {"table": what, "rows": rows}
