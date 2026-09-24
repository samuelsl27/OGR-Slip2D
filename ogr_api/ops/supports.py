# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Support types (the property sets) and the supports placed in the model.

Two levels, as in the interface: a SUPPORT TYPE is a named set of
properties of one class (a grouted tieback with this capacity...), and a
SUPPORT is a placement of one set, head at the slope face and tail inside.

What this checks that the interface's editor only checked with widgets:

* a parameter is a real field of the class (``dataclasses.fields``, which
  also covers the table field ``points`` that ``PARAMETERS`` omits);
* a string parameter is one of its tokens
  (``ogr_core.support.PARAMETER_CHOICES``, moved out of the editor in
  v0.1.196): the engine does not check them — a pile treats anything that is
  not ``"ito_matsui"`` as shear;
* ``user_angle_deg`` only with the ``user_defined`` orientation, which is
  the only one that reads it.

A support's type is always set by BOTH ``type_ref`` (the set's id) and
``type_id`` (its class), which is what ``resolve_support_type`` reads first.
Defaults for a new support come from its set, and otherwise from the class
— not ``ACTIVE`` blindly, which is what the interface falls back to for a
set without stored defaults, although three classes default to PASSIVE.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
import math
from typing import Any, Optional
from uuid import uuid4

from ..coerce import coerce_enum, coerce_value, point, type_hints
from ..errors import Conflict, InvalidArgument, did_you_mean, unknown
from ..results import json_safe
from . import operation


def _registry():
    from ogr_core.support.support import support_registry
    return support_registry()


def _label(st) -> str:
    return getattr(st, "_display_name", None) or st.DISPLAY_NAME


def type_info(st) -> dict:
    params = {f.name: json_safe(getattr(st, f.name))
              for f in dataclasses.fields(st) if f.name != "id"}
    fa = getattr(st, "_force_application", None)
    fo = getattr(st, "_orientation", None)
    return {"id": st.id, "name": _label(st), "class": st.TYPE_ID,
            "params": params,
            "force_application": fa.value if fa is not None else None,
            "orientation": fo.value if fo is not None else None,
            "user_angle_deg": getattr(st, "_user_angle_deg", 0.0),
            "color": getattr(st, "_color", None),
            "allows_pattern": bool(getattr(type(st), "ALLOWS_PATTERN",
                                           True))}


def support_info(s) -> dict:
    return {"id": s.id, "name": s.name, "class": s.type_id,
            "support_type": s.type_ref,
            "head": [s.head.x, s.head.y], "tail": [s.tail.x, s.tail.y],
            "length": round(s.length(), 6),
            "force_application": s.force_application.value,
            "orientation": s.orientation.value,
            "user_angle_deg": s.user_angle_deg,
            "pattern_id": getattr(s, "pattern_id", None)}


def find_type(project, ref):
    sets = list(project.support_types)
    if ref is None:
        if len(sets) == 1:
            return sets[0]
        raise InvalidArgument(
            "Say which support type (support_type=...)." if sets else
            "The model has no support types yet.",
            hint=("Types: " + ", ".join(f"{st.id} ({_label(st)})"
                                         for st in sets)) if sets else
            "Define one with support_type_set.")
    for st in sets:
        if st.id == ref:
            return st
    named = [st for st in sets
             if _label(st).strip().lower() == str(ref).strip().lower()]
    if len(named) == 1:
        return named[0]
    raise unknown("support type", ref,
                  [f"{st.id} ({_label(st)})" for st in sets])


def find_support(project, ref):
    for s in project.supports:
        if s.id == ref:
            return s
    named = [s for s in project.supports
             if (s.name or "").strip().lower() == str(ref).strip().lower()]
    if len(named) == 1:
        return named[0]
    raise unknown("support", ref, [f"{s.id} ({s.name})"
                                   for s in project.supports][:40])


def _params(cls, raw: dict, base: Optional[dict] = None) -> dict:
    """``raw`` validated against the class's fields, merged over ``base``."""
    from ogr_core.support.support import PARAMETER_CHOICES

    fields = [f.name for f in dataclasses.fields(cls) if f.name != "id"]
    hints = type_hints(cls)
    out = dict(base or {})
    for key, val in (raw or {}).items():
        if key not in fields:
            hint = did_you_mean(key, fields)
            raise InvalidArgument(
                f"{cls.TYPE_ID}: {key!r} is not a parameter.",
                hint=(hint + " " if hint else "")
                + f"Parameters of {cls.TYPE_ID}: {fields}.")
        if key == "points":
            pts = coerce_value(val, list, "points")
            out[key] = [list(point(p, f"points[{i}]"))
                        for i, p in enumerate(pts)]
            continue
        v = coerce_value(val, hints.get(key, Any), key)
        choices = PARAMETER_CHOICES.get(key)
        if choices is not None and v not in choices:
            raise InvalidArgument(
                f"{key}: {v!r} is not one of {list(choices)}.",
                hint=did_you_mean(str(v), choices) or None)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and \
                not math.isfinite(v):
            raise InvalidArgument(f"{key} must be finite.")
        out[key] = v
    return out


def _apply_behaviour(st, cls, force_application, orientation,
                     user_angle_deg, *, reset: bool) -> None:
    from ogr_core.support.support import ForceApplication, ForceOrientation

    if reset or getattr(st, "_force_application", None) is None:
        st._force_application = cls.DEFAULT_APPLICATION
    if reset or getattr(st, "_orientation", None) is None:
        st._orientation = cls.DEFAULT_ORIENTATION
    if force_application is not None:
        st._force_application = coerce_enum(force_application,
                                            ForceApplication,
                                            "force_application")
    if orientation is not None:
        st._orientation = coerce_enum(orientation, ForceOrientation,
                                      "orientation")
    if user_angle_deg is not None:
        if st._orientation.value != "user_defined":
            raise Conflict("user_angle_deg is only read with orientation "
                           "'user_defined'.")
        st._user_angle_deg = coerce_value(user_angle_deg, float,
                                          "user_angle_deg")
    elif not hasattr(st, "_user_angle_deg"):
        st._user_angle_deg = 0.0


@operation("support_type_set", toolset="supports", mutates=True)
def support_type_set(ws, project_id: Optional[str] = None,
                     support_type: Optional[str] = None,
                     type_class: Optional[str] = None,
                     name: Optional[str] = None,
                     params: Optional[dict] = None,
                     force_application: Optional[str] = None,
                     orientation: Optional[str] = None,
                     user_angle_deg: Optional[float] = None,
                     color: Optional[str] = None) -> dict:
    """Define a support type (a property set of one class), or change one."""
    reg = _registry()

    def edit(project):
        from ogr_core.support.support import reconcile_support_refs
        creating = support_type is None
        if creating:
            if type_class not in reg:
                raise unknown("support class", type_class, list(reg))
            cls = reg[type_class]
            values = _params(cls, params)
            st = cls(**values)
            st.id = str(uuid4())
            taken = {_label(x).strip().lower()
                     for x in project.support_types}
            base = name or cls.DISPLAY_NAME
            label, i = base, 2
            while label.strip().lower() in taken:
                label, i = f"{base} ({i})", i + 1
            if name and label != name:
                raise Conflict(f"A support type named {name!r} exists.",
                               hint=f"Pass support_type={name!r} to change "
                                    f"it.")
            st._display_name = label
            st._color = color or "#4b0082"
            _apply_behaviour(st, cls, force_application, orientation,
                             user_angle_deg, reset=True)
            project.support_types.append(st)
        else:
            old = find_type(project, support_type)
            cls = reg[type_class] if type_class is not None else type(old)
            if type_class is not None and type_class not in reg:
                raise unknown("support class", type_class, list(reg))
            same = cls is type(old)
            base = ({f.name: getattr(old, f.name)
                     for f in dataclasses.fields(old) if f.name != "id"}
                    if same else {})
            st = cls(**_params(cls, params, base))
            st.id = old.id
            st._display_name = name or _label(old)
            st._color = color or getattr(old, "_color", "#4b0082")
            if same:
                for attr in ("_force_application", "_orientation",
                             "_user_angle_deg"):
                    if hasattr(old, attr):
                        setattr(st, attr, getattr(old, attr))
            # Changing the class resets the behaviour to the new class's
            # defaults, as the editor does.
            _apply_behaviour(st, cls, force_application, orientation,
                             user_angle_deg, reset=not same)
            project.support_types[project.support_types.index(old)] = st
        rec = reconcile_support_refs(project)
        project._notify("support_types_changed")
        return {"support_type": type_info(st), "created": creating,
                "supports_retyped": rec["retyped"]}

    return ws.mutate(project_id, "Set support type", edit)


@operation("support_type_delete", toolset="supports", mutates=True)
def support_type_delete(ws, support_type: str,
                        project_id: Optional[str] = None,
                        reassign_to: Optional[str] = None) -> dict:
    """Delete a support type; refuses while placed supports use it."""
    def edit(project):
        from ogr_core.support.support import reconcile_support_refs
        st = find_type(project, support_type)
        users = [s for s in project.supports if s.type_ref == st.id]
        target = find_type(project, reassign_to) \
            if reassign_to is not None else None
        if target is st:
            raise InvalidArgument("reassign_to is the type being deleted.")
        if users and target is None:
            raise Conflict(f"{len(users)} placed support(s) use "
                           f"{_label(st)!r}.",
                           hint="Pass reassign_to='<type>', or delete those "
                                "supports first.")
        for s in users:
            s.type_ref, s.type_id = target.id, target.TYPE_ID
        project.support_types = [x for x in project.support_types
                                 if x is not st]
        reconcile_support_refs(project)
        project._notify("support_types_changed")
        return {"deleted": _label(st), "reassigned": len(users)}

    return ws.mutate(project_id, "Delete support type", edit)


def _placement_notes(project, head, tail) -> list[str]:
    from ogr_core.geometry.cleanup import model_tolerance
    from ogr_core.geometry.ground import distance_to_profile, ground_surface
    from ogr_core.project.project import _point_in_polygon_verts

    ext = project.external_boundary()
    if ext is None:
        return []
    notes = []
    tol = 1000 * model_tolerance(project.boundaries)
    if distance_to_profile(ground_surface(ext), head[0], head[1]) > tol:
        notes.append("The head is not on the ground surface; the head is "
                     "the end at the slope face (where the plate is).")
    if not _point_in_polygon_verts(tail[0], tail[1],
                                   ext.polyline.vertices):
        notes.append("The tail is outside the model.")
    return notes


@operation("support_set", toolset="supports", mutates=True)
def support_set(ws, project_id: Optional[str] = None,
                support: Optional[str] = None,
                support_type: Optional[str] = None,
                head: Optional[list] = None, tail: Optional[list] = None,
                dx: Optional[float] = None, dy: Optional[float] = None,
                force_application: Optional[str] = None,
                orientation: Optional[str] = None,
                user_angle_deg: Optional[float] = None,
                name: Optional[str] = None,
                color: Optional[str] = None) -> dict:
    """Place a support (head at the slope face, tail inside), or move,
    stretch, retype or edit one (support=...)."""
    from ogr_core.geometry import Vertex
    from ogr_core.support.support import (ForceApplication,
                                          ForceOrientation, SupportInstance)

    def edit(project):
        creating = support is None
        if creating:
            st = find_type(project, support_type)
            if head is None or tail is None:
                raise InvalidArgument("A new support needs head and tail "
                                      "[x, y].")
            h, t = point(head, "head"), point(tail, "tail")
            if math.hypot(t[0] - h[0], t[1] - h[1]) <= 0:
                raise InvalidArgument("head and tail coincide.")
            s = SupportInstance(
                type_id=st.TYPE_ID, type_ref=st.id,
                head=Vertex(*h), tail=Vertex(*t),
                force_application=getattr(st, "_force_application", None),
                orientation=getattr(st, "_orientation", None),
                user_angle_deg=getattr(st, "_user_angle_deg", 0.0),
                name=name or _label(st),
                color=color or getattr(st, "_color", "#4b0082"))
            project.add_support(s)
        else:
            s = find_support(project, support)
            if support_type is not None:
                st = find_type(project, support_type)
                s.type_ref, s.type_id = st.id, st.TYPE_ID
            if head is not None:
                s.head = Vertex(*point(head, "head"))
            if tail is not None:
                s.tail = Vertex(*point(tail, "tail"))
            if dx is not None or dy is not None:
                ddx = coerce_value(dx or 0.0, float, "dx")
                ddy = coerce_value(dy or 0.0, float, "dy")
                s.head = Vertex(s.head.x + ddx, s.head.y + ddy)
                s.tail = Vertex(s.tail.x + ddx, s.tail.y + ddy)
            if name is not None:
                s.name = str(name)
            if color is not None:
                s.color = str(color)
            if s.length() <= 0:
                raise InvalidArgument("head and tail coincide.")
        if creating and (dx is not None or dy is not None):
            raise InvalidArgument("dx/dy move an existing support; give "
                                  "head and tail for a new one.")
        if force_application is not None:
            s.force_application = coerce_enum(
                force_application, ForceApplication, "force_application")
        if orientation is not None:
            s.orientation = coerce_enum(orientation, ForceOrientation,
                                        "orientation")
        if user_angle_deg is not None:
            if s.orientation.value != "user_defined":
                raise Conflict("user_angle_deg is only read with "
                               "orientation 'user_defined'.")
            s.user_angle_deg = coerce_value(user_angle_deg, float,
                                            "user_angle_deg")
        project._notify("supports_changed")
        return {"support": support_info(s), "created": creating,
                "notes": _placement_notes(project, (s.head.x, s.head.y),
                                          (s.tail.x, s.tail.y))}

    return ws.mutate(project_id, "Set support", edit)


@operation("support_pattern_add", toolset="supports", mutates=True)
def support_pattern_add(ws, start: list, end: list, length: float,
                        spacing: float, project_id: Optional[str] = None,
                        support_type: Optional[str] = None,
                        orientation_mode: str = "angle",
                        angle_deg: float = -15.0, flip_180: bool = False,
                        force_application: Optional[str] = None,
                        orientation: Optional[str] = None) -> dict:
    """A row of supports along the segment start→end (heads on it)."""
    from ogr_core.support.support import (ForceApplication,
                                          ForceOrientation, SupportPattern)

    modes = ("angle", "normal", "depth")
    if orientation_mode not in modes:
        raise unknown("orientation_mode", orientation_mode, modes)

    def edit(project):
        st = find_type(project, support_type)
        if not getattr(type(st), "ALLOWS_PATTERN", True):
            raise Conflict(f"{st.TYPE_ID} cannot be placed as a pattern.")
        L = coerce_value(length, float, "length")
        sp = coerce_value(spacing, float, "spacing")
        if L <= 0 or sp <= 0:
            raise InvalidArgument("length and spacing must be positive.")
        pat = SupportPattern(
            type_id=st.TYPE_ID, type_ref=st.id, length=L, spacing=sp,
            orientation_mode=orientation_mode,
            angle_deg=coerce_value(angle_deg, float, "angle_deg"),
            flip_180=coerce_value(flip_180, bool, "flip_180"),
            force_application=(coerce_enum(force_application,
                                           ForceApplication,
                                           "force_application")
                               if force_application is not None else
                               getattr(st, "_force_application", None)),
            orientation=(coerce_enum(orientation, ForceOrientation,
                                     "orientation")
                         if orientation is not None else
                         getattr(st, "_orientation", None)),
            user_angle_deg=getattr(st, "_user_angle_deg", 0.0))
        made = pat.generate_along_segment(point(start, "start"),
                                          point(end, "end"))
        if not made:
            raise InvalidArgument("No support fits: the segment is shorter "
                                  "than the spacing allows.")
        for s in made:
            s.name = _label(st)
            s.color = getattr(st, "_color", "#4b0082")
        project.supports.extend(made)
        project._notify("supports_changed")
        return {"added": len(made), "pattern_id": made[0].pattern_id,
                "supports": [support_info(s) for s in made[:20]]}

    return ws.mutate(project_id, "Add support pattern", edit)


@operation("support_delete", toolset="supports", mutates=True)
def support_delete(ws, supports: Any = None, pattern: Optional[str] = None,
                   project_id: Optional[str] = None) -> dict:
    """Delete supports by id/name, a whole pattern, or 'all'."""
    def edit(project):
        if pattern is not None:
            gone = {s.id for s in project.supports
                    if getattr(s, "pattern_id", None) == pattern}
            if not gone:
                raise unknown("pattern", pattern, sorted(
                    {s.pattern_id for s in project.supports
                     if getattr(s, "pattern_id", None)}))
        elif supports == "all":
            gone = {s.id for s in project.supports}
        else:
            refs = [supports] if isinstance(supports, str) else \
                list(supports or [])
            if not refs:
                raise InvalidArgument("Give supports (ids/names or 'all') "
                                      "or pattern.")
            gone = {find_support(project, r).id for r in refs}
        project.supports = [s for s in project.supports if s.id not in gone]
        project._notify("supports_changed")
        return {"deleted": len(gone)}

    return ws.mutate(project_id, "Delete supports", edit)


@operation("support_ungroup", toolset="supports", mutates=True)
def support_ungroup(ws, pattern: Optional[str] = None,
                    project_id: Optional[str] = None) -> dict:
    """Break a pattern (or all of them) into independent supports."""
    def edit(project):
        hit = [s for s in project.supports
               if getattr(s, "pattern_id", None)
               and (pattern is None or s.pattern_id == pattern)]
        if not hit:
            raise Conflict("No support belongs to that pattern."
                           if pattern else
                           "No support belongs to a pattern.")
        for s in hit:
            s.pattern_id = None
        project._notify("supports_changed")
        return {"ungrouped": len(hit)}

    return ws.mutate(project_id, "Ungroup support pattern", edit)
