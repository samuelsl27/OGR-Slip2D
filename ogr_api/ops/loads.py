# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Distributed and line loads, the pseudo-static seismic load, and records.

Every setting a load carries is checked against what the ENGINE reads, not
only against its type — the rule 7 of AGENTS.md, applied at the door:

* ``magnitude_end`` is only read by a triangular or trapezoidal load, and a
  non-constant load WITHOUT one is silently constant (``pressure_at``), so
  the pair is enforced both ways;
* ``angle_deg`` is only read by the two angle orientations;
* a LINE load with ``normal_to_boundary`` or ``angle_to_boundary`` is
  REFUSED: ``LineLoad.direction_vector`` has no branch for either and acts
  vertically, while the interface offers both. Reported in v0.1.196; the
  owner decided (2026-09-24) to implement them in a batch of their own,
  with an external validation, and until then an agent cannot ask for a
  direction the engine will not apply;
* the seismic coefficients are only read with ``enabled``.

Magnitudes are pressures (kPa) for a distributed load and forces per metre
(kN/m) for a line load, positive: the DIRECTION is the orientation's. With
``normal_to_boundary`` the direction is the segment start→end turned 90°
clockwise, so a load pressing INTO the ground is given left to right along
its surface — the answer says when the given order makes it pull upward.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Any, Optional

from ..coerce import coerce_enum, coerce_value, point
from ..errors import Conflict, InvalidArgument, unknown
from ..results import json_safe
from . import operation

_KINDS = ("distributed", "line")
_ANGLED = ("angle_from_horizontal", "angle_to_boundary")
_BOUNDARY_RELATIVE = ("normal_to_boundary", "angle_to_boundary")


def load_info(load) -> dict:
    d = json_safe(load.to_dict())
    d.pop("type", None)
    d["kind"] = "line" if hasattr(load, "point") else "distributed"
    return d


def _find_load(project, ref):
    loads = list(project.distributed_loads) + list(project.line_loads)
    for ld in loads:
        if ld.id == ref:
            return ld
    named = [ld for ld in loads
             if (ld.name or "").strip().lower() == str(ref).strip().lower()]
    if len(named) == 1:
        return named[0]
    raise unknown("load", ref, [f"{ld.id} ({ld.name})" for ld in loads])


def _ground_note(project, pts) -> list[str]:
    """A load acts where it is: warn when it is off the ground surface."""
    from ogr_core.geometry.ground import distance_to_profile, ground_surface
    from ogr_core.geometry.cleanup import model_tolerance

    ext = project.external_boundary()
    if ext is None:
        return []
    profile = ground_surface(ext)
    tol = 1000 * model_tolerance(project.boundaries)  # 0.1 % of the model
    far = [p for p in pts if distance_to_profile(profile, p[0], p[1]) > tol]
    if far:
        return [f"{len(far)} point(s) of this load are not on the ground "
                f"surface; the engine places a load by its x-range, so check "
                f"it is where you mean."]
    return []


def _check_fields(kind, orientation, distribution, magnitude_end, angle_deg
                  ) -> None:
    ov = orientation.value
    if kind == "line" and ov in _BOUNDARY_RELATIVE:
        raise Conflict(
            f"orientation {ov!r} is not implemented for a line load: the "
            f"engine would apply it vertically.",
            hint="Use 'vertical', 'horizontal' or 'angle_from_horizontal' "
                 "(with angle_deg). Boundary-relative line loads are "
                 "scheduled as a separate, validated change.")
    if angle_deg is not None and ov not in _ANGLED:
        raise Conflict(f"angle_deg is only read with an angle orientation "
                       f"({list(_ANGLED)}), not {ov!r}.")
    if kind == "distributed":
        const = distribution.value == "constant"
        if const and magnitude_end is not None:
            raise Conflict("magnitude_end is only read by a triangular or "
                           "trapezoidal load.",
                           hint="Set distribution, or drop magnitude_end.")
        if not const and magnitude_end is None:
            raise Conflict(
                f"A {distribution.value} load needs magnitude_end; without "
                f"it the engine applies a constant pressure.")


@operation("load_set", toolset="loads", mutates=True)
def load_set(ws, project_id: Optional[str] = None,
             load: Optional[str] = None, kind: Optional[str] = None,
             start: Optional[list] = None, end: Optional[list] = None,
             point_xy: Optional[list] = None,
             magnitude: Optional[float] = None,
             magnitude_end: Optional[float] = None,
             distribution: Optional[str] = None,
             orientation: Optional[str] = None,
             angle_deg: Optional[float] = None,
             creates_excess_pore_pressure: Optional[bool] = None,
             name: Optional[str] = None) -> dict:
    """Add a distributed or line load, or change one (load=...)."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import (DistributedLoad, LineLoad, LoadDistribution,
                                LoadOrientation)

    def num(v, where, lo=0.0):
        v = coerce_value(v, float, where)
        if lo is not None and v < lo:
            raise InvalidArgument(
                f"{where} must be ≥ {lo:g}; the direction is set by "
                f"orientation, not by the sign.")
        return v

    def edit(project):
        creating = load is None
        if creating:
            if kind not in _KINDS:
                raise unknown("load kind", kind, _KINDS)
            k = kind
            if magnitude is None:
                raise InvalidArgument("A new load needs magnitude.")
        else:
            obj = _find_load(project, load)
            k = "line" if hasattr(obj, "point") else "distributed"
            if kind is not None and kind != k:
                raise Conflict(f"Load {load!r} is a {k} load; its kind "
                               f"cannot change. Delete it and add another.")
        default_or = ("vertical" if k == "line" else "normal_to_boundary")
        orient = coerce_enum(orientation, LoadOrientation, "orientation") \
            if orientation is not None else (
                None if not creating else LoadOrientation(default_or))
        distr = coerce_enum(distribution, LoadDistribution,
                            "distribution") if distribution is not None \
            else None
        if k == "line" and (distribution is not None
                            or magnitude_end is not None or start
                            or end):
            raise InvalidArgument("A line load has a point_xy and one "
                                  "magnitude; start, end, distribution and "
                                  "magnitude_end belong to distributed "
                                  "loads.")
        if k == "distributed" and point_xy is not None:
            raise InvalidArgument("A distributed load runs from start to "
                                  "end; point_xy belongs to line loads.")
        notes = []
        if creating:
            if k == "distributed":
                if start is None or end is None:
                    raise InvalidArgument("A distributed load needs start "
                                          "and end [x, y].")
                (sx, sy), (ex, ey) = point(start, "start"), point(end, "end")
                if math.hypot(ex - sx, ey - sy) <= 0:
                    raise InvalidArgument("start and end coincide.")
                distr = distr or LoadDistribution.CONSTANT
                _check_fields(k, orient, distr, magnitude_end, angle_deg)
                m1 = num(magnitude, "magnitude")
                obj = DistributedLoad(
                    start=Vertex(sx, sy), end=Vertex(ex, ey), magnitude_1=m1,
                    magnitude_2=(num(magnitude_end, "magnitude_end")
                                 if magnitude_end is not None else None),
                    orientation=orient,
                    angle_deg=(coerce_value(angle_deg, float, "angle_deg")
                               if angle_deg is not None else 0.0),
                    distribution=distr,
                    creates_excess_pore_pressure=bool(
                        creates_excess_pore_pressure),
                    name=name or f"Dist {m1:.1f} kN/m²")
                project.add_distributed_load(obj)
                notes += _ground_note(project, [(sx, sy), (ex, ey)])
            else:
                if point_xy is None:
                    raise InvalidArgument("A line load needs point_xy "
                                          "[x, y].")
                px, py = point(point_xy, "point_xy")
                _check_fields(k, orient, None, None, angle_deg)
                m = num(magnitude, "magnitude")
                obj = LineLoad(
                    point=Vertex(px, py), magnitude=m, orientation=orient,
                    angle_deg=(coerce_value(angle_deg, float, "angle_deg")
                               if angle_deg is not None else 0.0),
                    creates_excess_pore_pressure=bool(
                        creates_excess_pore_pressure),
                    name=name or f"Line {m:.1f} kN/m")
                project.add_line_load(obj)
                notes += _ground_note(project, [(px, py)])
        else:
            if k == "distributed":
                if start is not None:
                    obj.start = Vertex(*point(start, "start"))
                if end is not None:
                    obj.end = Vertex(*point(end, "end"))
                if magnitude is not None:
                    obj.magnitude_1 = num(magnitude, "magnitude")
                if magnitude_end is not None:
                    obj.magnitude_2 = num(magnitude_end, "magnitude_end")
                if distr is not None:
                    obj.distribution = distr
                    if distr == LoadDistribution.CONSTANT and \
                            magnitude_end is None:
                        obj.magnitude_2 = None
            else:
                if point_xy is not None:
                    obj.point = Vertex(*point(point_xy, "point_xy"))
                if magnitude is not None:
                    obj.magnitude = num(magnitude, "magnitude")
            if orient is not None:
                obj.orientation = orient
            if angle_deg is not None:
                obj.angle_deg = coerce_value(angle_deg, float, "angle_deg")
            elif orient is not None and orient.value not in _ANGLED:
                obj.angle_deg = 0.0
            if creates_excess_pore_pressure is not None:
                obj.creates_excess_pore_pressure = bool(
                    creates_excess_pore_pressure)
            if name is not None:
                obj.name = str(name)
            _check_fields(k, obj.orientation,
                          getattr(obj, "distribution", None),
                          getattr(obj, "magnitude_2", None),
                          obj.angle_deg if obj.orientation.value in _ANGLED
                          else None)
            project._notify("loads_changed")
        if k == "distributed" and obj.orientation.value == \
                "normal_to_boundary":
            dx, dy = obj.direction_vector()
            if dy > 1e-9:
                notes.append("With this start→end order the load points "
                             "UPWARD (it pulls the ground). Give the points "
                             "left to right along the surface for a load "
                             "that presses into it.")
        if obj.creates_excess_pore_pressure and \
                project.settings.groundwater.advanced_option() != \
                "excess_pore_pressure":
            notes.append("creates_excess_pore_pressure is only read with "
                         "the groundwater advanced option "
                         "'excess_pore_pressure'.")
        return {"load": load_info(obj), "created": creating, "notes": notes}

    return ws.mutate(project_id, "Set load", edit)


@operation("load_delete", toolset="loads", mutates=True)
def load_delete(ws, loads: Any, project_id: Optional[str] = None) -> dict:
    """Delete loads by id or name, or 'all'."""
    def edit(project):
        if loads == "all":
            n = len(project.distributed_loads) + len(project.line_loads)
            project.distributed_loads, project.line_loads = [], []
        else:
            refs = [loads] if isinstance(loads, str) else list(loads or [])
            if not refs:
                raise InvalidArgument("loads is a list of ids/names, or "
                                      "'all'.")
            gone = {_find_load(project, r).id for r in refs}
            n = len(gone)
            project.distributed_loads = [ld for ld in
                                         project.distributed_loads
                                         if ld.id not in gone]
            project.line_loads = [ld for ld in project.line_loads
                                  if ld.id not in gone]
        project._notify("loads_changed")
        return {"deleted": n}

    return ws.mutate(project_id, "Delete loads", edit)


@operation("seismic_set", toolset="loads", mutates=True)
def seismic_set(ws, project_id: Optional[str] = None,
                enabled: Optional[bool] = None, kh: Optional[float] = None,
                kv: Optional[float] = None,
                creates_excess_pore_pressure: Optional[bool] = None) -> dict:
    """The pseudo-static seismic load: kh, kv and whether it applies."""
    def edit(project):
        s = project.seismic
        if enabled is not None:
            s.enabled = coerce_value(enabled, bool, "enabled")
        for key, val in (("kh", kh), ("kv", kv)):
            if val is not None:
                v = coerce_value(val, float, key)
                if abs(v) >= 1.0:
                    raise InvalidArgument(f"|{key}| must be below 1 (a "
                                          f"fraction of g), got {v}.")
                setattr(s, key, v)
        if creates_excess_pore_pressure is not None:
            s.creates_excess_pore_pressure = coerce_value(
                creates_excess_pore_pressure, bool,
                "creates_excess_pore_pressure")
        notes = []
        if not s.enabled and (s.kh or s.kv):
            notes.append("kh and kv are only read with enabled=true.")
        project._notify("loads_changed")
        return {"seismic": json_safe(s.to_dict() if hasattr(s, "to_dict")
                                     else vars(s)), "notes": notes}

    return ws.mutate(project_id, "Set seismic load", edit)


def _find_record(project, ref):
    for r in project.seismic_records:
        if r.id == ref or r.name.strip().lower() == str(ref).strip().lower():
            return r
    raise unknown("seismic record", ref,
                  [f"{r.id} ({r.name})" for r in project.seismic_records])


def record_info(r) -> dict:
    return {"id": r.id, "name": r.name, "dt": r.dt,
            "samples": len(r.accelerations),
            "pga_g": json_safe(max((abs(a) for a in r.accelerations),
                                   default=0.0)),
            "usable": bool(r.is_usable())}


@operation("seismic_record_set", toolset="loads", mutates=True)
def seismic_record_set(ws, project_id: Optional[str] = None,
                       record: Optional[str] = None,
                       name: Optional[str] = None,
                       path: Optional[str] = None,
                       text: Optional[str] = None,
                       accelerations: Optional[list] = None,
                       dt: Optional[float] = None,
                       unit: str = "g") -> dict:
    """Add a strong-motion record (from a file, text or values), or rename /
    re-time one (record=...)."""
    from ogr_core.loads.seismic_record import (AccelerationUnit,
                                               SeismicRecord,
                                               parse_record_text)

    acc_unit = coerce_enum(unit, AccelerationUnit, "unit")
    sources = [x is not None for x in (path, text, accelerations)]
    body = None
    src_name = ""
    if sum(sources) > 1:
        raise InvalidArgument("Give only one of path, text or "
                              "accelerations.")
    if path is not None:
        p = ws.resolve_path(path)
        body = p.read_text(encoding="utf-8", errors="replace")
        src_name = p.name
        default_name = p.stem
    elif text is not None:
        body = str(text)
        default_name = "Record"
    elif accelerations is not None:
        vals = coerce_value(accelerations, list[float], "accelerations")
        if dt is None:
            raise InvalidArgument("accelerations need dt (seconds).")
        body = "\n".join(repr(v) for v in vals)
        default_name = "Record"

    def edit(project):
        from ogr_core.project.rules import set_seismic_records
        notes = []
        if record is None:
            if body is None:
                raise InvalidArgument("A new record needs path, text or "
                                      "accelerations.")
            step = coerce_value(dt, float, "dt") if dt is not None else None
            if step is not None and step <= 0:
                raise InvalidArgument("dt must be positive.")
            acc, step_out, note = parse_record_text(body, acc_unit, dt=step)
            if not acc:
                raise InvalidArgument(f"Nothing was read: {note}")
            if note:
                notes.append(note)
            rec = SeismicRecord(name=name or default_name, dt=step_out,
                                accelerations=acc, source_unit=acc_unit,
                                source_file=src_name)
            set_seismic_records(project, list(project.seismic_records)
                                + [rec])
        else:
            if body is not None:
                raise InvalidArgument("To replace the samples, delete the "
                                      "record and add a new one.")
            rec = _find_record(project, record)
            if name is not None:
                rec.name = str(name)
            if dt is not None:
                step = coerce_value(dt, float, "dt")
                if step <= 0:
                    raise InvalidArgument("dt must be positive.")
                rec.dt = step
        project._notify("seismic_records_changed")
        return {"record": record_info(rec), "notes": notes}

    return ws.mutate(project_id, "Set seismic record", edit)


@operation("seismic_record_delete", toolset="loads", mutates=True)
def seismic_record_delete(ws, record: str,
                          project_id: Optional[str] = None) -> dict:
    """Delete a strong-motion record."""
    def edit(project):
        from ogr_core.project.rules import set_seismic_records
        rec = _find_record(project, record)
        cleared = set_seismic_records(
            project, [r for r in project.seismic_records if r is not rec])
        project._notify("seismic_records_changed")
        notes = (["It was the record the Newmark analysis used; that "
                  "selection is now empty."] if cleared else [])
        return {"deleted": rec.name, "notes": notes}

    return ws.mutate(project_id, "Delete seismic record", edit)
