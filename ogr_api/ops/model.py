# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Geometry, materials, and which material fills which region.

Every operation here is one undo step and all-or-nothing
(``Workspace.mutate``). Every rule the interface enforces is enforced here
by ASKING ``ogr_core.project.rules`` — one water table, one tension crack,
one drawdown line and only with rapid drawdown on, a Block Search object
only with the Block Search — never by re-deciding it.

Two conventions a caller has to know, both the program's own and both
repeated in the answers where they bite:

* a region nobody assigned takes the FIRST material of the list (the
  reference's convention, ``Project.resolve_regions``), so deleting or
  reordering materials can silently change regions;
* a water table or piezometric line does nothing until a material points
  at it, and pointing at it also sets that material's pore-pressure model
  (``rules.assign_water_surface``).

Materials and boundaries can be named by id or by name, because a
language model remembers names far better than ids.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
from typing import Any, Optional

from ..coerce import coerce_enum, coerce_value, point, points, type_hints
from ..errors import Conflict, InvalidArgument, NotFound, unknown
from . import operation
from .project import boundary_info, material_info, regions_info

#: Minimum vertices per boundary type.
_MIN_VERTICES = {"EXTERNAL": 3, "BLOCK_SEARCH_OBJECT": 1}

#: Material fields this layer edits as plain values. ``hydraulic`` and
#: ``drawdown_envelope`` are structures, edited by the groundwater
#: operations of phase F3; ``id`` and ``strength`` have their own handling.
_MATERIAL_FIELDS = ("name", "unit_weight", "sat_unit_weight",
                    "use_sat_unit_weight", "pore_pressure", "ru",
                    "constant_u", "water_surface_id", "color", "hatch",
                    "phi_b", "air_entry_value", "hu", "auto_hu",
                    "undrained_behaviour", "b_bar", "weight_creates_excess",
                    "use_grid", "anisotropic_surface_id")
_MATERIAL_LATER = {"hydraulic": "F3 (groundwater)",
                   "drawdown_envelope": "F3 (rapid drawdown)"}


# ----------------------------------------------------------------------
# Lookups
# ----------------------------------------------------------------------
def find_material(project, ref):
    """A material by id, or by name (case-insensitive)."""
    if ref is None:
        raise InvalidArgument("A material id or name is required.")
    for m in project.materials:
        if m.id == ref:
            return m
    key = str(ref).strip().lower()
    for m in project.materials:
        if m.name.strip().lower() == key:
            return m
    raise unknown("material", ref, [m.name for m in project.materials]
                  + [m.id for m in project.materials])


def find_boundary(project, ref):
    for b in project.boundaries:
        if b.id == ref:
            return b
    key = str(ref).strip().lower()
    named = [b for b in project.boundaries if (b.name or "").lower() == key]
    if len(named) == 1:
        return named[0]
    raise unknown("boundary", ref,
                  [f"{b.id} ({b.btype.name.lower()})"
                   for b in project.boundaries])


def boundary_type(raw):
    from ogr_core.geometry import BoundaryType

    aliases = {"piezometric_line": "PIEZOMETRIC", "piezo": "PIEZOMETRIC",
               "block": "BLOCK_SEARCH_OBJECT",
               "block_search": "BLOCK_SEARCH_OBJECT",
               "drawdown_line": "DRAWDOWN"}
    if isinstance(raw, str) and raw.strip().lower() in aliases:
        raw = aliases[raw.strip().lower()]
    return coerce_enum(raw, BoundaryType, "type")


# ----------------------------------------------------------------------
# Boundaries
# ----------------------------------------------------------------------
def _make_boundary(btype, pts, *, name=None, closed=None,
                   material_id=None):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    from ogr_core.geometry.cleanup import has_self_intersections

    need = _MIN_VERTICES.get(btype.name, 2)
    verts = points(pts, "points", minimum=need)
    if btype.name == "EXTERNAL":
        closed = True
    elif closed is None:
        closed = False
    elif closed and btype.name != "BLOCK_SEARCH_OBJECT":
        raise InvalidArgument(
            f"A {btype.display_name} is an open polyline; only the External "
            f"boundary and a Block Search window are closed.")
    poly = Polyline(vertices=[Vertex(x, y) for x, y in verts],
                    closed=bool(closed))
    if btype.name == "EXTERNAL":
        poly.ensure_ccw()
    if len(poly.vertices) >= 4 and has_self_intersections(poly):
        raise InvalidArgument(f"The {btype.display_name} crosses itself.",
                              hint="Check the order of the points.")
    return Boundary(polyline=poly, btype=btype, name=name or "",
                    material_id=material_id)


def _check_allowed(project, btype, *, replacing=None) -> None:
    from ogr_core.project.rules import boundary_refusal

    refusal = boundary_refusal(project, btype)
    if refusal is None:
        return
    if refusal.code == "single_instance" and replacing is not None:
        return
    raise Conflict(refusal.message)


def _monotonic_note(b) -> Optional[str]:
    xs = [v.x for v in b.polyline.vertices]
    if len(xs) >= 2 and not (all(a < c for a, c in zip(xs, xs[1:]))
                             or all(a > c for a, c in zip(xs, xs[1:]))):
        return (f"The {b.btype.display_name} doubles back in x; a water "
                f"surface is read as a function of x.")
    return None


def _assign_water(project, surface, assign_to) -> list[str]:
    """Point materials at a water surface; returns their names."""
    from ogr_core.project.rules import assign_water_surface

    if assign_to is None:
        return []
    if assign_to == "all":
        mats = list(project.materials)
    elif isinstance(assign_to, (list, tuple)):
        mats = [find_material(project, r) for r in assign_to]
    else:
        mats = [find_material(project, assign_to)]
    assign_water_surface(project, surface.id, [m.id for m in mats])
    return [m.name for m in mats]


@operation("boundary_add", toolset="model", mutates=True)
def boundary_add(ws, type: str, points: list,
                 project_id: Optional[str] = None,
                 name: Optional[str] = None, closed: Optional[bool] = None,
                 material: Optional[str] = None,
                 assign_to: Any = None, replace: bool = False) -> dict:
    """Add a boundary (external, material, water_table, piezometric, ...)."""
    btype = boundary_type(type)
    WATER = ("WATER_TABLE", "PIEZOMETRIC")

    def edit(project):
        existing = None
        if btype.name == "EXTERNAL":
            existing = project.external_boundary()
            if existing is not None and not replace:
                raise Conflict(
                    "The model already has an External boundary.",
                    hint="Pass replace=true to replace it, or edit it with "
                         "boundary_edit.")
        _check_allowed(project, btype,
                       replacing=existing if replace else None)
        mat_id = None
        if btype.name == "WEAK_LAYER":
            if material is None:
                raise InvalidArgument(
                    "A weak layer needs the material it is made of.",
                    hint="Pass material='<name or id>'.")
            mat_id = find_material(project, material).id
        elif material is not None:
            raise InvalidArgument(
                f"material is only read for a weak layer, not a "
                f"{btype.display_name}.")
        b = _make_boundary(btype, points, name=name, closed=closed,
                           material_id=mat_id)
        if existing is not None:
            b.id = existing.id
            idx = project.boundaries.index(existing)
            project.boundaries[idx] = b
            project._notify("boundary_modified")
        else:
            project.add_boundary(b)
        notes = []
        assigned = []
        if btype.name in WATER:
            assigned = _assign_water(project, b, assign_to)
            note = _monotonic_note(b)
            if note:
                notes.append(note)
            if not assigned and not any(m.water_surface_id == b.id
                                        for m in project.materials):
                notes.append(
                    f"This {btype.display_name} is assigned to no material "
                    f"and produces no pore pressure until one points at "
                    f"it (assign_to, or material_set water_surface_id).")
        elif assign_to is not None:
            raise InvalidArgument(
                "assign_to is only read for a water table or a "
                "piezometric line.")
        return {"boundary": boundary_info(b, with_vertices=True),
                "replaced": existing is not None,
                "assigned_to": assigned,
                "regions": len(project.resolve_regions()),
                "notes": notes}

    return ws.mutate(project_id, f"Add {btype.display_name}", edit)


_EDIT_OPS = ("set_vertices", "translate", "move_vertex", "insert_vertex",
             "delete_vertex", "rename", "change_type", "delete")


@operation("boundary_edit", toolset="model", mutates=True)
def boundary_edit(ws, boundary: str, op: str,
                  project_id: Optional[str] = None,
                  points: Optional[list] = None, dx: float = 0.0,
                  dy: float = 0.0, index: Optional[int] = None,
                  point_xy: Optional[list] = None,
                  name: Optional[str] = None,
                  new_type: Optional[str] = None) -> dict:
    """Edit or delete a boundary: set_vertices, translate, move/insert/
    delete_vertex, rename, change_type, delete."""
    from ogr_core.geometry import Vertex

    if op not in _EDIT_OPS:
        raise unknown("boundary_edit op", op, _EDIT_OPS)

    def edit(project):
        b = find_boundary(project, boundary)
        idx = project.boundaries.index(b)
        notes = []
        if op == "delete":
            project.boundaries.pop(idx)
            cleared = [m for m in project.materials
                       if m.water_surface_id == b.id]
            if cleared:
                from ogr_core.project.rules import assign_water_surface
                assign_water_surface(project, b.id, [],
                                     [m.id for m in cleared])
                notes.append("Materials that used it now have no water "
                             "surface: " + ", ".join(m.name for m in cleared))
            for m in project.materials:
                if m.anisotropic_surface_id == b.id:
                    m.anisotropic_surface_id = None
                    notes.append(f"{m.name!r} lost its anisotropic surface.")
            project._notify("boundary_removed")
            return {"deleted": b.id, "notes": notes,
                    "regions": len(project.resolve_regions())}

        new = dataclasses.replace(
            b, polyline=dataclasses.replace(
                b.polyline, vertices=list(b.polyline.vertices)))
        verts = new.polyline.vertices
        if op == "set_vertices":
            if points is None:
                raise InvalidArgument("set_vertices needs points.")
            fresh = _make_boundary(b.btype, points,
                                   closed=b.polyline.closed
                                   if b.btype.name != "EXTERNAL" else None,
                                   material_id=b.material_id)
            new.polyline = dataclasses.replace(
                fresh.polyline, id=b.polyline.id)
        elif op == "translate":
            ddx = coerce_value(dx, float, "dx")
            ddy = coerce_value(dy, float, "dy")
            new.polyline.vertices = [Vertex(v.x + ddx, v.y + ddy)
                                     for v in verts]
        elif op in ("move_vertex", "insert_vertex", "delete_vertex"):
            i = coerce_value(index, int, "index")
            limit = len(verts) + (1 if op == "insert_vertex" else 0)
            if not 0 <= i < limit:
                raise InvalidArgument(
                    f"index {i} is outside 0..{limit - 1}.")
            if op == "delete_vertex":
                need = _MIN_VERTICES.get(b.btype.name, 2)
                if len(verts) - 1 < need:
                    raise Conflict(f"A {b.btype.display_name} needs at "
                                   f"least {need} vertices.")
                verts.pop(i)
            else:
                x, y = point(point_xy, "point_xy")
                if op == "move_vertex":
                    verts[i] = Vertex(x, y)
                else:
                    verts.insert(i, Vertex(x, y))
            if b.btype.name == "EXTERNAL":
                new.polyline.ensure_ccw()
        elif op == "rename":
            if name is None:
                raise InvalidArgument("rename needs name.")
            new.name = str(name)
        elif op == "change_type":
            from ogr_core.geometry.transforms import convert_boundary
            target = boundary_type(new_type)
            project.boundaries.pop(idx)
            try:
                _check_allowed(project, target)
            finally:
                project.boundaries.insert(idx, b)
            if target.name == "EXTERNAL" and not b.polyline.closed:
                raise Conflict("Only a closed polyline can become the "
                               "External boundary.")
            new = convert_boundary(b, target)
        from ogr_core.geometry.cleanup import has_self_intersections
        if len(new.polyline.vertices) >= 4 and has_self_intersections(
                new.polyline):
            raise InvalidArgument("The edit makes the boundary cross "
                                  "itself.")
        project.boundaries[idx] = new
        project._notify("boundary_modified")
        return {"boundary": boundary_info(new, with_vertices=True),
                "regions": len(project.resolve_regions()), "notes": notes}

    return ws.mutate(project_id, f"Edit boundary ({op})", edit)


# ----------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------
def _apply_material_fields(project, m, fields: dict, *, creating: bool
                           ) -> list[str]:
    """Write validated ``fields`` onto material ``m``; returns notes."""
    from ogr_core.geometry import BoundaryType
    from ogr_core.project.rules import water_surface_model

    hints = type_hints(type(m))
    notes = []
    for key, raw in fields.items():
        if key in _MATERIAL_LATER:
            raise InvalidArgument(
                f"{key} is edited by the operations of phase "
                f"{_MATERIAL_LATER[key]}.",
                hint="Use python_exec meanwhile.")
        if key not in _MATERIAL_FIELDS:
            from ..errors import did_you_mean
            hint = did_you_mean(key, _MATERIAL_FIELDS)
            raise InvalidArgument(
                f"{key!r} is not a material property.",
                hint=(hint + " " if hint else "")
                + f"Properties: {', '.join(_MATERIAL_FIELDS)}.")
        value = coerce_value(raw, hints[key], key)
        if key == "name" and not str(value).strip():
            raise InvalidArgument("name cannot be empty.")
        setattr(m, key, value)

    # A water surface only means something to the two surface models, and
    # pointing at one picks the model (the interface's rule, moved).
    pp = m.pore_pressure.value
    if "water_surface_id" in fields and m.water_surface_id:
        surf = next((b for b in project.boundaries
                     if b.id == m.water_surface_id), None)
        if surf is None or surf.btype not in (BoundaryType.WATER_TABLE,
                                              BoundaryType.PIEZOMETRIC):
            raise InvalidArgument(
                f"water_surface_id {m.water_surface_id!r} is not a water "
                f"table or piezometric line of this model.")
        model = water_surface_model(project, m.water_surface_id)
        if "pore_pressure" in fields and m.pore_pressure != model:
            raise Conflict(
                f"pore_pressure {pp!r} contradicts the water surface, which "
                f"is a {surf.btype.display_name} ({model.value!r}).",
                hint="Leave pore_pressure out; it follows the surface.")
        m.pore_pressure = model
    elif ("water_surface_id" in fields and not m.water_surface_id
          and "pore_pressure" not in fields
          and m.pore_pressure.value in ("water_table", "piezometric")):
        # Clearing the surface clears the model it set — the same thing
        # unticking a material in the Assign dialog does.
        from ogr_core.materials import PorePressureType
        m.pore_pressure = PorePressureType.NONE
    elif m.pore_pressure.value in ("water_table", "piezometric") and \
            not m.water_surface_id:
        notes.append(f"{m.name!r} uses {m.pore_pressure.value!r} pore "
                     f"pressure but points at no water surface, so u = 0.")
    pp = m.pore_pressure.value
    if m.water_surface_id and m.pore_pressure.value not in (
            "water_table", "piezometric"):
        raise Conflict(
            f"water_surface_id is only read with pore_pressure "
            f"'water_table' or 'piezometric' (it is {pp!r}).")
    if "ru" in fields and pp != "ru":
        raise Conflict("ru is only read with pore_pressure='ru'.")
    if "constant_u" in fields and pp != "constant":
        raise Conflict("constant_u is only read with "
                       "pore_pressure='constant'.")
    if "sat_unit_weight" in fields and not m.use_sat_unit_weight:
        notes.append("sat_unit_weight is only used below the water surface "
                     "when use_sat_unit_weight is true, which it is not.")
    if "b_bar" in fields and not m.undrained_behaviour:
        notes.append("b_bar only applies with undrained_behaviour=true.")
    if m.anisotropic_surface_id and not any(
            b.id == m.anisotropic_surface_id
            and b.btype == BoundaryType.ANISOTROPIC_SURFACE
            for b in project.boundaries):
        raise InvalidArgument("anisotropic_surface_id is not an "
                              "anisotropic surface of this model.")
    return notes


def _new_material(project, name, strength, fields):
    from ogr_core.materials import Material

    from ..catalog import strength_from_spec

    if not isinstance(name, str) or not name.strip():
        raise InvalidArgument("A new material needs a name.")
    if strength is None:
        raise InvalidArgument(
            "A new material needs a strength model.",
            hint="e.g. strength={'model': 'mohr_coulomb', 'params': "
                 "{'cohesion': 10, 'friction_angle': 30}}; see "
                 "catalog('strength_models').")
    if any(m.name.strip().lower() == name.strip().lower()
           for m in project.materials):
        raise Conflict(f"A material named {name!r} exists.",
                       hint=f"Pass material={name!r} to update it.")
    if len(project.materials) >= project.settings.max_materials:
        raise Conflict(f"The model already has the maximum of "
                       f"{project.settings.max_materials} materials.")
    m = Material(name=name.strip(), strength=strength_from_spec(strength))
    notes = _apply_material_fields(project, m, fields, creating=True)
    project.add_material(m)
    return m, notes


@operation("material_set", toolset="model", mutates=True)
def material_set(ws, project_id: Optional[str] = None,
                 material: Optional[str] = None,
                 name: Optional[str] = None,
                 strength: Optional[dict] = None,
                 properties: Optional[dict] = None) -> dict:
    """Create a material (name + strength) or update one (material=...)."""
    from ..catalog import strength_from_spec

    fields = dict(properties or {})

    def edit(project):
        if material is None:
            m, notes = _new_material(project, name, strength, fields)
            created = True
        else:
            m = find_material(project, material)
            created = False
            if name is not None:
                if any(o is not m and o.name.strip().lower()
                       == name.strip().lower() for o in project.materials):
                    raise Conflict(f"Another material is named {name!r}.")
                fields["name"] = name
            if strength is not None:
                m.strength = strength_from_spec(strength)
            notes = _apply_material_fields(project, m, fields,
                                           creating=False)
            project._notify("material_modified")
        return {"material": material_info(m), "created": created,
                "notes": notes}

    return ws.mutate(project_id, "Set material", edit)


@operation("material_delete", toolset="model", mutates=True)
def material_delete(ws, material: str, project_id: Optional[str] = None,
                    reassign_to: Optional[str] = None,
                    force: bool = False) -> dict:
    """Delete a material; refuses while regions or layers use it."""
    def edit(project):
        m = find_material(project, material)
        target = find_material(project, reassign_to) \
            if reassign_to is not None else None
        if target is m:
            raise InvalidArgument("reassign_to is the material being "
                                  "deleted.")
        refs_assign = [a for a in project.region_assignments
                       if a.get("material_id") == m.id]
        refs_layers = [b for b in project.boundaries
                       if b.material_id == m.id]
        is_default = project.materials and project.materials[0] is m
        if (refs_assign or refs_layers) and target is None and not force:
            raise Conflict(
                f"{m.name!r} is used by {len(refs_assign)} region "
                f"assignment(s) and {len(refs_layers)} weak layer(s).",
                hint="Pass reassign_to='<material>' to move them, or "
                     "force=true to drop them.")
        for a in refs_assign:
            if target is not None:
                a["material_id"] = target.id
        if target is None:
            project.region_assignments = [
                a for a in project.region_assignments
                if a.get("material_id") != m.id]
        for b in refs_layers:
            b.material_id = target.id if target is not None else None
        project.materials = [x for x in project.materials if x is not m]
        project._notify("material_removed")
        notes = []
        if is_default and project.materials:
            notes.append(
                f"{m.name!r} was the FIRST material, which every unassigned "
                f"region takes; they now take "
                f"{project.materials[0].name!r}.")
        return {"deleted": m.name, "reassigned_to":
                target.name if target else None,
                "notes": notes, "regions": regions_info(project)}

    return ws.mutate(project_id, "Delete material", edit)


@operation("material_assign", toolset="model", mutates=True)
def material_assign(ws, material: str, x: float, y: float,
                    project_id: Optional[str] = None) -> dict:
    """Paint a material onto the region containing (x, y)."""
    px = coerce_value(x, float, "x")
    py = coerce_value(y, float, "y")

    def edit(project):
        m = find_material(project, material)
        if not project.assign_material_at(px, py, m.id):
            regions = regions_info(project)
            raise InvalidArgument(
                f"({px}, {py}) is not inside any region of the model.",
                hint="Region centroids: " + "; ".join(
                    f"#{r['index']} {r['centroid']} ({r['material']})"
                    for r in regions) if regions else
                "The model has no regions yet: add an External boundary.")
        return {"material": m.name, "regions": regions_info(project)}

    return ws.mutate(project_id, "Assign material", edit)


# ----------------------------------------------------------------------
# The whole model in one call
# ----------------------------------------------------------------------
_SPEC_KEYS = ("name", "replace", "external", "material_boundaries",
              "materials", "water_table", "piezometric_lines",
              "tension_crack", "settings")


def _water_spec(raw, where):
    if isinstance(raw, dict):
        if "points" not in raw:
            raise InvalidArgument(f"{where} needs 'points'.")
        return raw["points"], raw.get("materials", "all")
    return raw, "all"


@operation("model_define", toolset="model", mutates=True)
def model_define(ws, spec: dict, project_id: Optional[str] = None) -> dict:
    """Build (or rebuild) a whole model from one declarative spec."""
    from ogr_core.geometry import BoundaryType

    if not isinstance(spec, dict):
        raise InvalidArgument("spec must be an object.")
    stray = [k for k in spec if k not in _SPEC_KEYS]
    if stray:
        from ..errors import did_you_mean
        hint = did_you_mean(stray[0], _SPEC_KEYS)
        raise InvalidArgument(
            f"{stray[0]!r} is not a key of the model spec.",
            hint=(hint + " " if hint else "") + f"Keys: {list(_SPEC_KEYS)}.")
    replace = spec.get("replace", True)

    def edit(project):
        notes = []
        if "name" in spec:
            project.name = str(spec["name"])
        if replace:
            project.boundaries = []
            project.materials = []
            project.region_assignments = []
            project.invalidate_regions_cache()
        if "external" in spec:
            ext = project.external_boundary()
            b = _make_boundary(BoundaryType.EXTERNAL, spec["external"])
            if ext is not None:
                project.boundaries[project.boundaries.index(ext)] = b
            else:
                project.add_boundary(b)
        for i, pts in enumerate(spec.get("material_boundaries", []) or []):
            project.add_boundary(_make_boundary(BoundaryType.MATERIAL, pts))
        if project.external_boundary() is None:
            raise InvalidArgument("The model needs an 'external' boundary.")
        if not project.resolve_regions():
            raise InvalidArgument(
                "The External boundary encloses no valid region.",
                hint="Give at least three non-collinear points in order.")

        mats = spec.get("materials", []) or []
        if not isinstance(mats, list):
            raise InvalidArgument("materials must be a list.")
        placements = []
        for j, entry in enumerate(mats):
            if not isinstance(entry, dict):
                raise InvalidArgument(f"materials[{j}] must be an object.")
            entry = dict(entry)
            at = entry.pop("at", None)
            nm = entry.pop("name", None)
            st = entry.pop("strength", None)
            m, mnotes = _new_material(project, nm, st, entry)
            notes.extend(mnotes)
            if at is not None:
                pts_at = [at] if (isinstance(at, (list, tuple)) and at
                                  and not isinstance(at[0], (list, tuple,
                                                             dict))) else at
                for k, pt in enumerate(pts_at):
                    placements.append((m, point(pt, f"materials[{j}].at"
                                                    f"[{k}]")))
        for m, (x, y) in placements:
            if not project.assign_material_at(x, y, m.id):
                raise InvalidArgument(
                    f"materials: the point ({x}, {y}) for {m.name!r} is not "
                    f"inside any region.",
                    hint="Region centroids: " + "; ".join(
                        f"{r['centroid']}" for r in regions_info(project)))

        if "water_table" in spec and spec["water_table"] is not None:
            pts, to = _water_spec(spec["water_table"], "water_table")
            wt = _make_boundary(BoundaryType.WATER_TABLE, pts)
            _check_allowed(project, BoundaryType.WATER_TABLE)
            project.add_boundary(wt)
            _assign_water(project, wt, to)
        for i, raw in enumerate(spec.get("piezometric_lines", []) or []):
            pts, to = _water_spec(raw, f"piezometric_lines[{i}]")
            pl = _make_boundary(BoundaryType.PIEZOMETRIC, pts)
            project.add_boundary(pl)
            _assign_water(project, pl, to)
        if spec.get("tension_crack"):
            _check_allowed(project, BoundaryType.TENSION_CRACK)
            project.add_boundary(_make_boundary(
                BoundaryType.TENSION_CRACK, spec["tension_crack"]))

        if spec.get("settings"):
            from ..settings_schema import apply_changes
            apply_changes(project, spec["settings"])

        regions = regions_info(project)
        placed = {m.id for m, _ in placements}
        for idx, m in enumerate(project.materials):
            if idx > 0 and m.id not in placed:
                notes.append(f"{m.name!r} has no 'at' point and is used by "
                             f"no region.")
        defaulted = [r for r in regions if r["how"] ==
                     "default_first_material"]
        if defaulted and len(project.materials) > 1:
            notes.append(
                f"{len(defaulted)} region(s) were not assigned and take the "
                f"first material, {project.materials[0].name!r}.")
        return {"boundaries": [boundary_info(b, with_vertices=False)
                               for b in project.boundaries],
                "materials": [material_info(m) for m in project.materials],
                "regions": regions, "notes": notes}

    return ws.mutate(project_id, "Define model", edit)
