# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What steers or complements the search: the tension crack's water, focus
objects, and slip surfaces the user draws by hand.

The interface's own conditions are kept, because each is a control that
would otherwise move nothing (rule 7):

* tension crack properties only mean something with a Tension Crack
  boundary (the interface refuses the same way), and each water level is
  read only by its own mode — a ``depth`` with mode ``filled`` is refused,
  not stored;
* a focus tolerance is read only by POINT and TANGENT focus objects;
* user surfaces are circles, analysed only when the surface type is
  circular — the interface greys the actions otherwise, and the engine
  skips them with a note.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Any, Optional

from ..coerce import coerce_enum, coerce_value, points
from ..errors import Conflict, InvalidArgument, unknown
from ..results import json_safe, surface_summary
from . import operation

#: Point counts per focus kind: the interface asks for exactly these (a
#: window may also be a triangle, which ``FocusObject.valid`` accepts).
_FOCUS_POINTS = {"window": (3, 4), "line": (2, 2), "point": (1, 1),
                 "tangent": (2, 2)}
_TOLERANCE_KINDS = ("point", "tangent")

#: Which extra value each tension-crack water mode reads.
_TC_FIELD = {"percent_filled": "percent_filled",
             "filled_below_elevation": "elevation",
             "filled_to_depth": "depth"}


@operation("tension_crack_set", toolset="search", mutates=True)
def tension_crack_set(ws, mode: str, project_id: Optional[str] = None,
                      percent_filled: Optional[float] = None,
                      elevation: Optional[float] = None,
                      depth: Optional[float] = None,
                      piezometric_line: Optional[str] = None) -> dict:
    """How much water stands in the tension crack."""
    from ogr_core.geometry import BoundaryType
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)

    m = coerce_enum(mode, WaterLevelMode, "mode")
    given = {"percent_filled": percent_filled, "elevation": elevation,
             "depth": depth}
    wanted = _TC_FIELD.get(m.value)
    for key, val in given.items():
        if val is not None and key != wanted:
            raise Conflict(f"{key} is not read with mode {m.value!r}" + (
                f" (it reads {wanted})." if wanted else "."))
    if wanted and given[wanted] is None:
        raise InvalidArgument(f"mode {m.value!r} needs {wanted}.")
    if piezometric_line is not None and m.value != "use_piezometric":
        raise Conflict("piezometric_line is only read with mode "
                       "'use_piezometric'.")

    def edit(project):
        if not project.boundaries_of(BoundaryType.TENSION_CRACK):
            raise Conflict("The model has no Tension Crack boundary.",
                           hint="Add one with boundary_add(type="
                                "'tension_crack', ...) first.")
        props = TensionCrackProperties(mode=m)
        if wanted == "percent_filled":
            v = coerce_value(percent_filled, float, "percent_filled")
            if not 0 <= v <= 100:
                raise InvalidArgument("percent_filled is 0..100.")
            props.percent_filled = v
        elif wanted == "elevation":
            props.elevation = coerce_value(elevation, float, "elevation")
        elif wanted == "depth":
            v = coerce_value(depth, float, "depth")
            if v < 0:
                raise InvalidArgument("depth must be ≥ 0.")
            props.depth = v
        if m.value == "use_water_table" and not project.boundaries_of(
                BoundaryType.WATER_TABLE):
            raise Conflict("Mode 'use_water_table' needs a water table.")
        if m.value == "use_piezometric":
            lines = project.boundaries_of(BoundaryType.PIEZOMETRIC)
            if not lines:
                raise Conflict("Mode 'use_piezometric' needs a "
                               "piezometric line.")
            if piezometric_line is None:
                if len(lines) > 1:
                    raise InvalidArgument(
                        "Several piezometric lines: say which one.",
                        hint=", ".join(f"{b.id} ({b.name})" for b in lines))
                props.piezo_id = lines[0].id
            else:
                hit = [b for b in lines if b.id == piezometric_line or
                       (b.name or "").lower()
                       == str(piezometric_line).lower()]
                if len(hit) != 1:
                    raise unknown("piezometric line", piezometric_line,
                                  [b.id for b in lines])
                props.piezo_id = hit[0].id
        project.tension_crack_properties = props
        project._notify("tension_crack_changed")
        return {"tension_crack": json_safe(props.to_dict()
                                           if hasattr(props, "to_dict")
                                           else vars(props))}

    return ws.mutate(project_id, "Set tension crack", edit)


def focus_info(f) -> dict:
    return {"id": f.id, "kind": f.kind.value,
            "points": [list(p) for p in f.points],
            "tolerance": f.tolerance, "enabled": f.enabled,
            "valid": bool(f.valid)}


def _find_focus(project, ref):
    for f in project.focus_objects:
        if f.id == ref:
            return f
    raise unknown("focus object", ref, [f.id for f in
                                        project.focus_objects])


@operation("focus_set", toolset="search", mutates=True)
def focus_set(ws, project_id: Optional[str] = None,
              focus: Optional[str] = None, kind: Optional[str] = None,
              points_xy: Optional[list] = None,
              tolerance: Optional[float] = None,
              enabled: Optional[bool] = None) -> dict:
    """Add a focus object (window, line, point, tangent) that narrows the
    search, or change one (focus=...)."""
    import uuid

    from ogr_slip2d.focus import FocusKind, FocusObject

    def edit(project):
        creating = focus is None
        if creating:
            k = coerce_enum(kind, FocusKind, "kind")
            f = FocusObject(kind=k, id=uuid.uuid4().hex[:12])
            if points_xy is None:
                raise InvalidArgument("A focus object needs points_xy.")
        else:
            f = _find_focus(project, focus)
            if kind is not None and coerce_enum(kind, FocusKind,
                                                "kind") != f.kind:
                raise Conflict("A focus object's kind cannot change; "
                               "delete it and add another.")
        if points_xy is not None:
            lo, hi = _FOCUS_POINTS[f.kind.value]
            pts = points(points_xy, "points_xy", minimum=lo)
            if len(pts) > hi:
                raise InvalidArgument(f"A {f.kind.value} focus takes "
                                      f"{hi} point(s), got {len(pts)}.")
            f.points = [tuple(p) for p in pts]
        if tolerance is not None:
            if f.kind.value not in _TOLERANCE_KINDS:
                raise Conflict(f"tolerance is only read by point and "
                               f"tangent focus objects, not "
                               f"{f.kind.value!r}.")
            tol = coerce_value(tolerance, float, "tolerance")
            if tol <= 0:
                raise InvalidArgument("tolerance must be positive.")
            f.tolerance = tol
        if enabled is not None:
            f.enabled = coerce_value(enabled, bool, "enabled")
        if not f.valid:
            raise InvalidArgument("That focus object is not valid (check "
                                  "its points).")
        if creating:
            project.focus_objects.append(f)
        project._notify("focus_changed")
        return {"focus": focus_info(f), "created": creating}

    return ws.mutate(project_id, "Set focus object", edit)


@operation("focus_delete", toolset="search", mutates=True)
def focus_delete(ws, focus: Any, project_id: Optional[str] = None) -> dict:
    """Delete a focus object, or 'all'."""
    def edit(project):
        if focus == "all":
            n = len(project.focus_objects)
            project.focus_objects = []
        else:
            f = _find_focus(project, focus)
            project.focus_objects = [x for x in project.focus_objects
                                     if x is not f]
            n = 1
        project._notify("focus_changed")
        return {"deleted": n}

    return ws.mutate(project_id, "Delete focus objects", edit)


@operation("user_surface_add", toolset="search", mutates=True)
def user_surface_add(ws, surface: dict,
                     project_id: Optional[str] = None) -> dict:
    """Add a slip circle of your own, analysed alongside the search."""
    from .analysis import surface_from_spec

    if not isinstance(surface, dict) or surface.get("type") not in (
            "circle", "three_points"):
        raise InvalidArgument("A user surface is a circle: {'type': "
                              "'circle', ...} or {'type': 'three_points', "
                              "...}.")
    circ = surface_from_spec(surface)

    def edit(project):
        if project.settings.search.surface_type != "circular":
            raise Conflict("User surfaces are circles and are only "
                           "analysed with surface_type='circular'.",
                           hint="Or evaluate it once with "
                                "surface_evaluate.")
        project.user_surfaces.append(circ)
        project._notify("user_surfaces_changed")
        return {"surface": {"id": circ.id, **surface_summary(circ)},
                "count": len(project.user_surfaces)}

    return ws.mutate(project_id, "Add user surface", edit)


@operation("user_surface_delete", toolset="search", mutates=True)
def user_surface_delete(ws, surface: Any,
                        project_id: Optional[str] = None) -> dict:
    """Delete a user surface (by id), or 'all'."""
    def edit(project):
        if surface == "all":
            n = len(project.user_surfaces)
            project.user_surfaces = []
        else:
            keep = [s for s in project.user_surfaces if s.id != surface]
            if len(keep) == len(project.user_surfaces):
                raise unknown("user surface", surface,
                              [s.id for s in project.user_surfaces])
            n = len(project.user_surfaces) - len(keep)
            project.user_surfaces = keep
        project._notify("user_surfaces_changed")
        return {"deleted": n}

    return ws.mutate(project_id, "Delete user surfaces", edit)
