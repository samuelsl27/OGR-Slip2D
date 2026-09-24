# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A picture of the model, with a result's surfaces on it.

Returns the PNG bytes under ``png`` — the MCP server turns them into an
image block — and, with ``save_path``, also writes them to disk, for the
clients that cannot show an image (the OpenAPI proxy, a model without
vision).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..coerce import coerce_value
from ..errors import Conflict, InvalidArgument, unknown
from . import operation


@operation("model_render", toolset="view")
def model_render(ws, project_id: Optional[str] = None,
                 result_id: Optional[str] = None,
                 method_id: Optional[str] = None,
                 width: int = 900, height: int = 600,
                 labels: bool = True,
                 save_path: Optional[str] = None,
                 overwrite: bool = False,
                 field: Optional[str] = None,
                 stage: Optional[int] = None,
                 source: str = "model") -> dict:
    """A PNG of the model, optionally with a result's critical surface
    or the groundwater field (contours and free surface); or, attached to
    a window, a capture of its canvas (``source="window"``)."""
    from ..render import render_png

    if source not in ("model", "window"):
        raise unknown("source", source, ["model", "window"])
    if source == "window":
        return _window_capture(ws, project_id, result_id, method_id,
                               field, stage, width, height, save_path,
                               overwrite)

    width = coerce_value(width, int, "width")
    height = coerce_value(height, int, "height")
    if not (200 <= width <= 4000 and 150 <= height <= 4000):
        raise InvalidArgument("width must be 200..4000 and height "
                              "150..4000 pixels.")
    if result_id is not None:
        handle, res = ws.find_result(result_id)
        if project_id is not None and project_id != handle.id:
            raise InvalidArgument(f"{result_id} belongs to {handle.id}, "
                                  f"not {project_id}.")
    else:
        handle, res = ws.get(project_id), None

    surfaces = []
    title = handle.project.name
    if res is not None:
        payload = res.payload().get("results", {})
        mids = [method_id] if method_id else list(payload)
        for mid in mids:
            if mid not in payload:
                raise unknown("method in this result", mid, list(payload))
            r = payload[mid]
            crit = r.critical if hasattr(r, "evaluations") else r
            if crit is not None:
                fos = crit.fos
                label = f"{mid}: {fos:.3f}" if fos is not None else mid
                surfaces.append((label, crit))
        if res.kind == "analysis":
            title += " — critical surface" + ("s" if len(surfaces) > 1
                                                else "")
    target = None
    if save_path is not None:
        target = ws.resolve_path(save_path, for_write=True,
                                 overwrite=overwrite, suffix=".png")
    with ws.reading(handle.id, "model_render") as project:
        overlay, fs = _field_overlay(project, field, stage)
        if overlay is not None:
            title += f" — {overlay[0]}"
        png = render_png(project, surfaces=surfaces, width=width,
                         height=height, labels=bool(labels), title=title,
                         field=overlay, free_surface=fs)
    if target is not None:
        target.write_bytes(png)
    return {"project_id": handle.id, "png": png,
            "saved_to": str(target) if target else None,
            "surfaces": [label for label, _ in surfaces]}


#: The groundwater quantities a picture can show, with their units.
_FIELDS = {"total_head": "total head H (m)",
           "pressure_head": "pressure head P (m)",
           "pore_pressure": "pore pressure u (kPa)"}


def _field_overlay(project, field, stage):
    """``(label, values, mesh)`` and the free surface of the model's
    groundwater field, or ``(None, None)`` when no field was asked for.
    v0.1.200 (spec 008, F3a)."""
    if field is None:
        if stage is not None:
            raise Conflict("stage is only read together with field.")
        return None, None
    if field not in _FIELDS:
        raise unknown("field", field, list(_FIELDS))
    from .groundwater import field_of
    result, mesh, label = field_of(project, stage)
    from ogr_slip2d.transient_stability import groundwater_query_solver
    solver = groundwater_query_solver(project)
    fs = solver.free_surface_points(result) if solver is not None else []
    return (f"{_FIELDS[field]}{label}", getattr(result, field), mesh), fs


def _window_capture(ws, project_id, result_id, method_id, field, stage,
                    width, height, save_path, overwrite) -> dict:
    """The live window's canvas as it is (spec 008, F4, v0.1.203): what
    the plan of F4 asked for instead of the Agg drawing."""
    host = getattr(ws, "host", None)
    if host is None:
        raise Conflict("source='window' needs the live bridge (the MCP "
                       "server started with --attach).")
    stray = [n for n, v in (("result_id", result_id),
                            ("method_id", method_id), ("field", field),
                            ("stage", stage)) if v is not None]
    if stray:
        raise Conflict(f"{', '.join(stray)} are not read with "
                       f"source='window': the capture shows what the "
                       f"window shows.")
    handle = ws.get(project_id)
    if handle.id != host.handle_id:
        raise Conflict("Only the window's model has a window to capture.")
    width = coerce_value(width, int, "width")
    height = coerce_value(height, int, "height")
    target = None
    if save_path is not None:
        target = ws.resolve_path(save_path, for_write=True,
                                 overwrite=overwrite, suffix=".png")
    png = host.capture(width, height)
    if target is not None:
        target.write_bytes(png)
    return {"project_id": handle.id, "png": png, "source": "window",
            "saved_to": str(target) if target else None, "surfaces": []}

