# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Groundwater by finite elements, and the drawdown level sweep.

What the Groundwater menu does, through the core functions the interface
itself calls since v0.1.200 (spec 008, F3a):

* ``rules.set_fem_mesh`` — a new mesh drops the boundary conditions and
  the fields of the old one, the transient stages' conditions included,
  because all of them are keyed by node id;
* ``bc_targets`` — the named sides, a reservoir's wetted perimeter,
  infiltration on boundary edges, nodes along a polyline;
* ``GroundwaterSettings.set_transient`` — the stage checks;
* ``parse_grid_csv_text`` — a pressure-grid file read as the interface
  reads it;
* ``solve_project_groundwater`` / ``run_transient_stability`` and
  ``run_configured_drawdown_sweep`` — in a job, like an analysis.

Units. Heads and levels in metres, pore pressure in kPa. Permeabilities,
infiltration rates and nodal flows in one consistent length/time unit
(m/s by convention; the solver needs them consistent, not a particular
one). Each permeability model takes its parameters in the unit of its own
definition (v0.1.200): van Genuchten and Gardner in suction HEAD (alpha in
1/m, a in 1/m^n), Brooks-Corey, Fredlund-Xing, Simple and a user curve in
matric suction (kPa).

The solve analyses a detached copy. When it ends and the model has not
changed meanwhile, its field is WRITTEN BACK into the model as one undo
step — what Compute Groundwater does to the interface's model, and what a
material taking its pore pressure from the field reads. If the model
changed while it ran, nothing is written: a field computed for another
model is not this model's, and the answer says so.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
from typing import Any, Optional

from ..coerce import coerce_enum, coerce_value, points, type_hints
from ..errors import (Conflict, InvalidArgument, NotConfigured, NotFound,
                      did_you_mean, unknown)
from ..results import (json_safe, seepage_field_summary, stage_rows)
from ..snapshot import detached_copy, model_hash
from . import operation
from .analysis import (JOB_FINISHERS, JOB_WORDS, _check_runnable,
                       _job_answer, store_job_result)
from .model import find_material

JOB_WORDS.update(groundwater="groundwater analysis",
                 drawdown_sweep="drawdown sweep")

_ASSIGN_KEYS = ("bc_type", "side", "nodes", "along", "reservoir", "value",
                "seepage_face")
_STAGE_KEYS = ("time", "calculate_sf", "label", "bcs")
_RESULT_VIEWS = ("summary", "point", "section", "free_surface", "stages",
                 "nodes")


def _heavy():
    from ogr_core.project.commands import HEAVY_ATTRS, LIGHT_ATTRS
    return LIGHT_ATTRS + HEAVY_ATTRS


def _need_mesh(project):
    mesh = getattr(project, "fem_mesh", None)
    if mesh is None or mesh.element_count == 0:
        raise NotConfigured("The model has no finite-element mesh.",
                            hint="Generate one with mesh_generate.")
    return mesh


# ----------------------------------------------------------------------
# Hydraulic properties
# ----------------------------------------------------------------------
@operation("hydraulic_set", toolset="groundwater", mutates=True)
def hydraulic_set(ws, material: str, project_id: Optional[str] = None,
                  model: Optional[str] = None,
                  library: Optional[str] = None,
                  properties: Optional[dict] = None,
                  reset: bool = False) -> dict:
    """Set a material's hydraulic properties: permeability, its model for
    the unsaturated zone, water contents and storage."""
    from ogr_core.hydraulic import HydraulicProperties
    from ogr_core.hydraulic.permeability_models import (COMMON_FIELDS,
                                                        MODEL_FIELDS,
                                                        SUCTION_UNIT,
                                                        PermeabilityModel,
                                                        library_for)
    from ogr_core.materials import PorePressureType

    props = {} if properties is None else coerce_value(properties, dict,
                                                       "properties")
    reset = coerce_value(reset, bool, "reset")
    if "model" in props:
        raise InvalidArgument("Pass the permeability model as `model`, not "
                              "inside properties.")
    hints = type_hints(HydraulicProperties)
    known = sorted(k for k in hints if not k.startswith("_"))

    def edit(project):
        m = find_material(project, material)
        notes = []
        if m.hydraulic is None or reset:
            if m.hydraulic is None:
                notes.append(f"{m.name} had no hydraulic properties; "
                             f"started from the defaults.")
            hp = HydraulicProperties()
        else:
            hp = copy.deepcopy(m.hydraulic)
        if model is not None:
            hp.model = coerce_enum(model, PermeabilityModel, "model")
        if library is not None:
            lib = library_for(hp.model)
            if not lib:
                raise Conflict(
                    f"The {hp.model.value} model has no parameter library.",
                    hint="Libraries exist for van_genuchten, brooks_corey, "
                         "gardner and fredlund_xing.")
            name = next((k for k in lib if k.lower()
                         == str(library).strip().lower()), None)
            if name is None:
                raise unknown(f"{hp.model.value} library soil", library,
                              list(lib))
            for key, value in lib[name].items():
                setattr(hp, key, value)
            notes.append(f"{name} from the library: {lib[name]}.")
        read = set(COMMON_FIELDS) | set(MODEL_FIELDS.get(hp.model, ()))
        for key, raw in props.items():
            if key not in known:
                hint = did_you_mean(key, known)
                raise InvalidArgument(
                    f"{key!r} is not a hydraulic property.",
                    hint=(hint + " " if hint else "")
                    + f"Properties: {', '.join(known)}.")
            if key not in read:
                owners = [mm.value for mm, fs in MODEL_FIELDS.items()
                          if key in fs]
                raise Conflict(
                    f"{key} is only read by the {' / '.join(owners)} model, "
                    f"and this material's is {hp.model.value}: it would "
                    f"move nothing.",
                    hint=f"Pass model='{owners[0]}' in the same call to "
                         f"switch.")
            if key == "user_curve":
                value = [tuple(p) for p in points(raw, "user_curve",
                                                  minimum=2)]
            else:
                value = coerce_value(raw, hints[key], key)
            setattr(hp, key, value)
        if "vg_m" in props and not hp.vg_custom_m:
            raise Conflict("vg_m is only read with vg_custom_m=true; "
                           "otherwise m = 1 - 1/n.")
        bad = hp.problems()
        if bad:
            raise InvalidArgument("These hydraulic properties are not "
                                  "usable: " + " ".join(bad),
                                  details={"problems": bad})
        m.hydraulic = hp
        project._notify("material_modified")
        if hp.model != PermeabilityModel.VAN_GENUCHTEN and any(
                k.startswith("vg_") for k in props):
            notes.append("vg_alpha, vg_n and vg_m also define this "
                         "material's water-retention curve, which only the "
                         "transient analysis reads.")
        if not any(mm.pore_pressure == PorePressureType.FEM_SEEPAGE
                   for mm in project.materials):
            notes.append("No material takes its pore pressure from the "
                         "seepage field yet: material_set(pore_pressure="
                         "'fem') couples it to the stability analysis.")
        return {"material": m.name, "hydraulic": json_safe(hp.to_dict()),
                "suction_unit": SUCTION_UNIT.get(hp.model, "m"),
                "read_by_this_model": sorted(read - {"model"}),
                "notes": notes}

    return ws.mutate(project_id, f"Hydraulic properties of {material}",
                     edit)


# ----------------------------------------------------------------------
# The mesh
# ----------------------------------------------------------------------
@operation("mesh_generate", toolset="groundwater", mutates=True)
def mesh_generate(ws, project_id: Optional[str] = None,
                  target_elements: Optional[int] = None,
                  target_size: Optional[float] = None,
                  min_angle: float = 25.0,
                  refine_passes: int = 3) -> dict:
    """Generate the finite-element mesh; drops the boundary conditions and
    fields of the previous one."""
    from ogr_core.project.rules import set_fem_mesh
    from ogr_fem2d.mesh import generate_mesh_for_project
    from ogr_fem2d.solvers.bc_targets import boundary_sides

    if target_elements is not None and target_size is not None:
        raise Conflict("Give target_elements or target_size, not both: the "
                       "mesher reads target_size first and would ignore "
                       "the other.")
    kw: dict[str, Any] = {}
    if target_size is not None:
        size = coerce_value(target_size, float, "target_size")
        if size <= 0:
            raise InvalidArgument("target_size must be positive.")
        kw["target_size"] = size
    else:
        n = coerce_value(1000 if target_elements is None else
                         target_elements, int, "target_elements")
        if not 20 <= n <= 200_000:
            raise InvalidArgument("target_elements must be between 20 and "
                                  "200000 (the interface's range).")
        kw["target_elements"] = n
    angle = coerce_value(min_angle, float, "min_angle")
    if not 0 < angle <= 45:
        raise InvalidArgument("min_angle must be in (0, 45] degrees.")
    passes = coerce_value(refine_passes, int, "refine_passes")
    if not 0 <= passes <= 20:
        raise InvalidArgument("refine_passes must be between 0 and 20.")
    kw.update(min_angle=angle, refine_passes=passes)

    def edit(project):
        if project.external_boundary() is None:
            raise NotConfigured("The model has no External boundary to "
                                "mesh.")
        try:
            mesh = generate_mesh_for_project(project, **kw)
        except (ValueError, RuntimeError, ArithmeticError) as exc:
            raise Conflict(f"Mesh generation failed: {exc}") from None
        if mesh.element_count == 0:
            raise Conflict("No mesh was generated from this geometry.")
        dropped = set_fem_mesh(project, mesh)
        notes = []
        if dropped:
            notes.append("Dropped with the previous mesh (they belong to "
                         "its node ids): " + ", ".join(dropped) + ".")
        notes.append("Until seepage_bc_set, the conditions are the "
                     "defaults: unknown (seepage face) on the ground "
                     "surface, no flow elsewhere — no prescribed head, so "
                     "a steady solve has nothing to solve for.")
        return {"mesh": json_safe(mesh.quality_stats()),
                "boundary_nodes_by_side": {
                    k: len(v) for k, v in boundary_sides(mesh).items()},
                "notes": notes}

    return ws.mutate(project_id, "Generate FE mesh", edit, attrs=_heavy())


@operation("mesh_reset", toolset="groundwater", mutates=True)
def mesh_reset(ws, project_id: Optional[str] = None) -> dict:
    """Remove the mesh and everything computed on it."""
    from ogr_core.project.rules import reset_fem_mesh

    def edit(project):
        if project.fem_mesh is None:
            return {"removed": False, "notes": ["There was no mesh."]}
        return {"removed": True, "dropped": reset_fem_mesh(project)}

    return ws.mutate(project_id, "Reset FE mesh", edit, attrs=_heavy())


# ----------------------------------------------------------------------
# Boundary conditions
# ----------------------------------------------------------------------
def bc_summary(bcs, mesh) -> dict:
    """How many nodes carry each condition, per side of the model."""
    from ogr_fem2d.solvers.bc_targets import boundary_sides

    side_of = {nid: side for side, ids in boundary_sides(mesh).items()
               for nid in ids}
    by_side: dict = {}
    for b in bcs.nodes:
        side = side_of.get(b.node_id, "interior")
        cell = by_side.setdefault(side, {})
        cell[b.bc_type.value] = cell.get(b.bc_type.value, 0) + 1
    heads = [b for b in bcs.nodes if b.bc_type.value in (
        "total_head", "pressure_head", "zero_pressure")]
    return {"by_side": by_side,
            "infiltration_segments": len(bcs.segments),
            "prescribes_a_head": bool(heads)}


def _assign(bcs, mesh, spec: dict, where: str) -> tuple[int, list]:
    """Apply one assignment ``spec`` (the arguments of ``seepage_bc_set``)
    to ``bcs``; returns how many nodes or edges it set, and notes."""
    from ogr_fem2d.solvers import BCType
    from ogr_fem2d.solvers.bc_targets import (SIDES, allows_seepage_face,
                                              apply_reservoir,
                                              assign_to_nodes,
                                              boundary_sides, needs_value,
                                              nodes_along)

    if not isinstance(spec, dict):
        raise InvalidArgument(f"{where} must be an object.")
    extra = [k for k in spec if k not in _ASSIGN_KEYS]
    if extra:
        raise InvalidArgument(f"{where}: unknown key(s) {extra}; the keys "
                              f"are {list(_ASSIGN_KEYS)}.")
    targets = [k for k in ("side", "nodes", "along", "reservoir")
               if spec.get(k) is not None]
    if len(targets) != 1:
        raise InvalidArgument(f"{where}: say where with exactly one of "
                              f"side, nodes, along or reservoir.")
    target = targets[0]
    if target == "reservoir":
        r = spec["reservoir"]
        if not isinstance(r, dict) or "level" not in r:
            raise InvalidArgument(f"{where}.reservoir is {{'level': y, "
                                  f"'side': 'left' or 'right', "
                                  f"'unknown_elsewhere': bool}}.")
        bad = [k for k in r if k not in ("level", "side",
                                         "unknown_elsewhere")]
        if bad:
            raise InvalidArgument(f"{where}.reservoir: unknown key(s) "
                                  f"{bad}.")
        if spec.get("bc_type") not in (None, "total_head"):
            raise Conflict("A reservoir is a total head (its level), not "
                           f"{spec['bc_type']!r}.")
        if spec.get("value") is not None:
            raise Conflict("A reservoir's value is its level; drop value.")
        if spec.get("seepage_face"):
            raise Conflict("A reservoir reads no seepage-face flag.")
        level = coerce_value(r["level"], float, f"{where}.reservoir.level")
        side = r.get("side", "left")
        if side not in ("left", "right"):
            raise unknown("reservoir side", side, ["left", "right"])
        elsewhere = coerce_value(r.get("unknown_elsewhere", False), bool,
                                 f"{where}.reservoir.unknown_elsewhere")
        ids = apply_reservoir(bcs, mesh, level, side,
                              unknown_elsewhere=elsewhere)
        if not ids:
            raise Conflict(f"No boundary node is below {level:g} on the "
                           f"{side}: nothing was assigned.")
        return len(ids), [f"Reservoir at {level:g} on the {side}: "
                          f"{len(ids)} node(s) submerged."]

    if spec.get("bc_type") is None:
        raise InvalidArgument(f"{where} needs bc_type.")
    t = coerce_enum(spec["bc_type"], BCType, f"{where}.bc_type")
    value = spec.get("value")
    if needs_value(t):
        if value is None:
            raise InvalidArgument(f"A {t.value} condition needs value.")
        value = coerce_value(value, float, f"{where}.value")
    elif value is not None:
        raise Conflict(f"A {t.value} condition reads no value.")
    face = spec.get("seepage_face")
    if face is not None:
        face = coerce_value(face, bool, f"{where}.seepage_face")
        if face and not allows_seepage_face(t):
            raise Conflict(f"Only nodal_flow and infiltration read the "
                           f"seepage-face flag, not {t.value}.")
    if target == "side":
        if spec["side"] not in SIDES:
            raise unknown("side", spec["side"], SIDES)
        ids = boundary_sides(mesh)[spec["side"]]
    elif target == "nodes":
        ids = coerce_value(spec["nodes"], list[int], f"{where}.nodes")
        outside = [i for i in ids if not 0 <= i < mesh.node_count]
        if outside:
            raise InvalidArgument(f"{where}.nodes: {outside[:5]} are not "
                                  f"nodes of this mesh (0.."
                                  f"{mesh.node_count - 1}).")
    else:
        ids = nodes_along(mesh, points(spec["along"], f"{where}.along",
                                       minimum=2))
    if not ids:
        raise Conflict(f"{where}: no boundary node matched.")
    if t == BCType.INFILTRATION:
        wanted = set(ids)
        if not any(u in wanted and w in wanted
                   for u, w in mesh.boundary_edges()):
            raise Conflict("Infiltration goes on boundary edges, and no "
                           "edge of the boundary has both ends among "
                           "those nodes.")
    n = assign_to_nodes(bcs, mesh, ids, t, value or 0.0, bool(face))
    what = "edge(s)" if t == BCType.INFILTRATION else "node(s)"
    return n, [f"{t.value} on {n} {what}."]


def _editable_bcs(project, mesh, *, for_edit: bool):
    """A copy of the model's conditions, or the defaults when it has none."""
    from ogr_fem2d.solvers import default_boundary_conditions
    from ogr_fem2d.solvers.bc_targets import fits_mesh

    bcs = project.seepage_bcs
    if bcs is None:
        return default_boundary_conditions(mesh), (
            ["Started from the default conditions."] if for_edit else [])
    if not fits_mesh(bcs, mesh):
        raise Conflict("The stored boundary conditions name nodes this "
                       "mesh does not have.",
                       hint="seepage_bc_clear restores the defaults.")
    return copy.deepcopy(bcs), []


@operation("seepage_bc_set", toolset="groundwater", mutates=True)
def seepage_bc_set(ws, project_id: Optional[str] = None,
                   bc_type: Optional[str] = None,
                   side: Optional[str] = None,
                   nodes: Optional[list] = None,
                   along: Optional[list] = None,
                   reservoir: Optional[dict] = None,
                   value: Optional[float] = None,
                   seepage_face: Optional[bool] = None) -> dict:
    """Assign a seepage boundary condition to a side, to nodes, along a
    polyline of the boundary, or as a reservoir."""
    spec = {k: v for k, v in dict(
        bc_type=bc_type, side=side, nodes=nodes, along=along,
        reservoir=reservoir, value=value,
        seepage_face=seepage_face).items() if v is not None}

    def edit(project):
        mesh = _need_mesh(project)
        bcs, notes = _editable_bcs(project, mesh, for_edit=True)
        n, more = _assign(bcs, mesh, spec, "condition")
        project.seepage_bcs = bcs
        project._fea_ponding_cache = None
        return {"assigned": n, "conditions": bc_summary(bcs, mesh),
                "notes": notes + more}

    return ws.mutate(project_id, "Set boundary conditions", edit)


@operation("seepage_bc_clear", toolset="groundwater", mutates=True)
def seepage_bc_clear(ws, project_id: Optional[str] = None) -> dict:
    """Restore the default boundary conditions: unknown (seepage face) on
    the ground surface, no flow on the other sides."""
    from ogr_fem2d.solvers import default_boundary_conditions

    def edit(project):
        mesh = _need_mesh(project)
        project.seepage_bcs = default_boundary_conditions(mesh)
        project._fea_ponding_cache = None
        return {"conditions": bc_summary(project.seepage_bcs, mesh),
                "notes": ["The defaults prescribe no head: a steady solve "
                          "needs a total-head, pressure-head or "
                          "zero-pressure condition somewhere."]}

    return ws.mutate(project_id, "Restore default boundary conditions",
                     edit)


def _bcs_from_spec(project, mesh, spec, where: str) -> dict:
    """A condition set, as stored in a stage, from an agent's ``spec``:
    'current', {'base': 'current'|'defaults', 'assign': [...]}, or the
    stored form {'nodes': [...], 'segments': [...]}."""
    from ogr_fem2d.solvers import (SeepageBoundaryConditions,
                                   default_boundary_conditions)
    from ogr_fem2d.solvers.bc_targets import fits_mesh

    if mesh is None:
        raise NotConfigured(f"{where}: conditions need a mesh.",
                            hint="Generate one with mesh_generate.")
    if spec == "current":
        return _editable_bcs(project, mesh, for_edit=False)[0].to_dict()
    if not isinstance(spec, dict):
        raise InvalidArgument(f"{where} is 'current', {{'base', 'assign'}} "
                              f"or {{'nodes', 'segments'}}.")
    if "nodes" in spec or "segments" in spec:
        try:
            bcs = SeepageBoundaryConditions.from_dict(spec)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidArgument(f"{where}: {exc}") from None
        if not fits_mesh(bcs, mesh):
            raise Conflict(f"{where} names nodes this mesh does not have.")
        return bcs.to_dict()
    bad = [k for k in spec if k not in ("base", "assign")]
    if bad:
        raise InvalidArgument(f"{where}: unknown key(s) {bad}.")
    base = spec.get("base", "current")
    if base == "current":
        bcs = _editable_bcs(project, mesh, for_edit=False)[0]
    elif base == "defaults":
        bcs = default_boundary_conditions(mesh)
    else:
        raise unknown(f"{where}.base", base, ["current", "defaults"])
    for i, item in enumerate(spec.get("assign") or []):
        _assign(bcs, mesh, item, f"{where}.assign[{i}]")
    return bcs.to_dict()


# ----------------------------------------------------------------------
# Transient stages
# ----------------------------------------------------------------------
@operation("transient_set", toolset="groundwater", mutates=True)
def transient_set(ws, project_id: Optional[str] = None,
                  enabled: bool = True,
                  stages: Optional[list] = None,
                  initial: Any = None,
                  tolerance: Optional[float] = None,
                  max_iterations: Optional[int] = None,
                  time_steps: Optional[int] = None) -> dict:
    """Configure the staged transient groundwater analysis: stages with
    their times, conditions and Calculate SF, and the initial state."""
    from ogr_core.materials import PorePressureType

    enabled = coerce_value(enabled, bool, "enabled")

    def edit(project):
        gw = project.settings.groundwater
        others = [name for name, on in (
            ("excess pore pressure", gw.excess_pore_pressure),
            ("rapid drawdown", gw.rapid_drawdown)) if on]
        mesh = project.fem_mesh
        if stages is None:
            raw = [dict(st) for st in gw.transient_stages]
        else:
            if not isinstance(stages, (list, tuple)):
                raise InvalidArgument("stages must be a list of objects.")
            raw = []
            for i, st in enumerate(stages):
                if not isinstance(st, dict) or "time" not in st:
                    raise InvalidArgument(f"stages[{i}] is an object with "
                                          f"a 'time'.")
                bad = [k for k in st if k not in _STAGE_KEYS]
                if bad:
                    raise InvalidArgument(f"stages[{i}]: unknown key(s) "
                                          f"{bad}; the keys are "
                                          f"{list(_STAGE_KEYS)}.")
                entry = {"time": coerce_value(st["time"], float,
                                              f"stages[{i}].time"),
                         "calculate_sf": coerce_value(
                             st.get("calculate_sf", False), bool,
                             f"stages[{i}].calculate_sf"),
                         "label": str(st.get("label", ""))}
                if st.get("bcs") is not None:
                    entry["bcs"] = _bcs_from_spec(project, mesh, st["bcs"],
                                                  f"stages[{i}].bcs")
                raw.append(entry)
        try:
            gw.set_transient(
                enabled, raw,
                tolerance=(None if tolerance is None else coerce_value(
                    tolerance, float, "tolerance")),
                max_iterations=(None if max_iterations is None else
                                coerce_value(max_iterations, int,
                                             "max_iterations")),
                time_steps=(None if time_steps is None else coerce_value(
                    time_steps, int, "time_steps")))
        except ValueError as exc:
            raise InvalidArgument(str(exc)) from None
        if initial is not None:
            if isinstance(initial, str) and initial.strip().lower() in (
                    "none", "clear"):
                gw.transient_initial_bcs = None
            else:
                gw.transient_initial_bcs = _bcs_from_spec(
                    project, mesh, initial, "initial")
        notes = []
        if enabled and others:
            notes.append("Switched off (one advanced groundwater option at "
                         "a time): " + ", ".join(others) + ".")
        if enabled and any(st.get("calculate_sf")
                           for st in gw.transient_stages) and not any(
                m.pore_pressure == PorePressureType.FEM_SEEPAGE
                for m in project.materials):
            notes.append("No material takes its pore pressure from the "
                         "seepage field, so the stage factors of safety "
                         "would ignore the computed water pressures.")
        return {"transient": gw.transient,
                "stages": [{"time": st["time"], "label": st["label"],
                            "calculate_sf": st["calculate_sf"],
                            "own_conditions": bool(st.get("bcs"))}
                           for st in gw.transient_stages],
                "initial": ("own conditions" if gw.transient_initial_bcs
                            else "the current conditions"),
                "tolerance": gw.transient_tolerance,
                "max_iterations": gw.transient_max_iterations,
                "time_steps": gw.transient_time_steps,
                "notes": notes}

    return ws.mutate(project_id, "Transient groundwater", edit)


# ----------------------------------------------------------------------
# The water pressure grid
# ----------------------------------------------------------------------
def _grid_rows(raw) -> list:
    if not isinstance(raw, (list, tuple)):
        raise InvalidArgument("points must be a list of [x, y, value].")
    out = []
    for i, row in enumerate(raw):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise InvalidArgument(f"points[{i}] must be [x, y, value], got "
                                  f"{row!r}.")
        out.append(tuple(coerce_value(v, float, f"points[{i}]")
                         for v in row))
    return out


@operation("water_grid_set", toolset="groundwater", mutates=True)
def water_grid_set(ws, project_id: Optional[str] = None,
                   points: Optional[list] = None,
                   csv_path: Optional[str] = None,
                   value_type: Optional[str] = None,
                   interpolation: Optional[str] = None,
                   idw_neighbours: Optional[int] = None,
                   allow_suction: Optional[bool] = None) -> dict:
    """Define the water pressure grid (points or a CSV file) or change its
    options; ``value_type`` sets the groundwater method that reads it."""
    from ogr_core.hydraulic.water_pressure_grid import (
        GridValueType, WaterPressureGrid, method_for_value_type,
        parse_grid_csv_text, value_type_for_method)

    if points is not None and csv_path is not None:
        raise Conflict("Give points or csv_path, not both.")
    rows = None
    if points is not None:
        rows = _grid_rows(points)
    elif csv_path is not None:
        path = ws.resolve_path(csv_path)
        rows = parse_grid_csv_text(path.read_text(encoding="utf-8",
                                                  errors="replace"))
        if not rows:
            raise InvalidArgument(f"No (x, y, value) row could be read from "
                                  f"{path.name}.")
    vt = None if value_type is None else coerce_enum(
        value_type, GridValueType, "value_type")
    if interpolation is not None and interpolation not in ("tps", "idw"):
        raise unknown("interpolation", interpolation, ["tps", "idw"])
    nb = None
    if idw_neighbours is not None:
        nb = coerce_value(idw_neighbours, int, "idw_neighbours")
        if not 1 <= nb <= 100:
            raise InvalidArgument("idw_neighbours must be 1..100.")
    suction = None if allow_suction is None else coerce_value(
        allow_suction, bool, "allow_suction")

    def edit(project):
        old = project.water_pressure_grid
        if rows is None and old is None:
            raise InvalidArgument("There is no grid yet: give points or "
                                  "csv_path.")
        grid = WaterPressureGrid(
            points=list(rows if rows is not None else old.points),
            interpolation=interpolation or (old.interpolation if old
                                            else "tps"),
            idw_neighbours=nb or (old.idw_neighbours if old else 8),
            allow_suction=(suction if suction is not None else
                           (old.allow_suction if old else False)))
        project.water_pressure_grid = grid
        notes = []
        n = len(grid.points)
        gw = project.settings.groundwater
        # v0.1.202 — the type of the values is the groundwater METHOD's, as
        # in the reference; ``value_type`` here sets that method, in the
        # same undo step.
        if vt is not None and gw.method != method_for_value_type(vt):
            notes.append(f"Groundwater method set to "
                         f"{method_for_value_type(vt)} (was {gw.method}).")
            gw.method = method_for_value_type(vt)
            project._notify("settings_changed")
        current = value_type_for_method(gw.method)
        if current is None:
            notes.append(f"The groundwater method is {gw.method!r}: the "
                         f"grid is only read with a grid method; pass "
                         f"value_type (or settings_set groundwater.method).")
        if grid.interpolation == "tps":
            if n > 300:
                notes.append(f"{n} points: above 300 the grid is "
                             f"interpolated by IDW, not TPS.")
            elif n > 1 and not grid._ensure_tps():
                notes.append("The TPS fit is ill-conditioned (repeated or "
                             "collinear points?): IDW is used instead.")
            if nb is not None and n <= 300:
                notes.append("idw_neighbours is only read when the TPS "
                             "falls back to IDW.")
        return {"points": n,
                "value_type": current.value if current else None,
                "method": gw.method,
                "interpolation": grid.interpolation,
                "idw_neighbours": grid.idw_neighbours,
                "allow_suction": grid.allow_suction, "notes": notes}

    return ws.mutate(project_id, "Water pressure grid", edit)


@operation("water_grid_delete", toolset="groundwater", mutates=True)
def water_grid_delete(ws, project_id: Optional[str] = None) -> dict:
    """Remove the water pressure grid."""
    def edit(project):
        had = project.water_pressure_grid is not None
        project.water_pressure_grid = None
        return {"deleted": had}

    return ws.mutate(project_id, "Delete water pressure grid", edit)


# ----------------------------------------------------------------------
# Running
# ----------------------------------------------------------------------
# ``mutates``: its field is written back into the model, one undo step.
@operation("groundwater_run", toolset="groundwater", mutates=True)
def groundwater_run(ws, project_id: Optional[str] = None,
                    stage_factors: bool = True,
                    methods: Optional[list] = None,
                    wait_seconds: float = 30.0) -> dict:
    """Solve the groundwater (steady, or the transient stages with their
    factors of safety) as a background job; the field is written back."""
    from ogr_fem2d.solvers.bc_targets import fits_mesh
    from ogr_fem2d.solvers import SeepageBoundaryConditions

    wait = coerce_value(wait_seconds, float, "wait_seconds")
    if wait < 0:
        raise InvalidArgument("wait_seconds cannot be negative.")
    stage_factors = coerce_value(stage_factors, bool, "stage_factors")
    handle = ws.get(project_id)
    with ws.reading(handle.id, "groundwater_run") as project:
        mesh = _need_mesh(project)
        if project.seepage_bcs is None:
            raise NotConfigured(
                "No boundary conditions have been set.",
                hint="Set them with seepage_bc_set. The defaults prescribe "
                     "no head, so a steady solve would be singular.")
        gw = project.settings.groundwater
        sets = [("the current conditions", project.seepage_bcs)]
        if gw.transient_initial_bcs:
            sets.append(("the initial conditions",
                         SeepageBoundaryConditions.from_dict(
                             gw.transient_initial_bcs)))
        for i, st in enumerate(gw.transient_stages):
            if st.get("bcs"):
                sets.append((f"the conditions of stage {i}",
                             SeepageBoundaryConditions.from_dict(st["bcs"])))
        for what, bcs in sets:
            if not fits_mesh(bcs, mesh):
                raise Conflict(f"{what} name nodes this mesh does not "
                               f"have.", hint="Set them again.")
        transient = bool(gw.transient and gw.transient_stages)
        sf = transient and stage_factors and any(
            st.get("calculate_sf") for st in gw.transient_stages)
        if methods is not None and not sf:
            raise Conflict("methods is only read when a transient stage is "
                           "flagged calculate_sf and stage_factors is on.")
        method_ids = _check_runnable(project, methods) if sf else None
        copy_ = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("groundwater", copy_, handle.id, fingerprint,
                        {"method_ids": method_ids,
                         "stage_factors": bool(sf)})
    job.wait(wait)
    return _job_answer(ws, job, raise_on_failure=True)


def _finish_groundwater(ws, job, handle, summary) -> dict:
    """Store the field, and write it back into the model when the model is
    still the one it was computed for."""
    res = store_job_result(ws, job, handle, summary, "groundwater")
    data = job.load_results()
    fields = [data.get("seepage_result")] + list(
        data.get("transient_results") or [])
    if not any(r is not None and r.total_head for r in fields):
        return {"written_back": False,
                "why_not_written": "The solve produced no field; see "
                                   "summary.field.notes."}

    def write(project):
        if model_hash(project) != job.model_hash:
            return None
        project.seepage_result = copy.deepcopy(data["seepage_result"])
        project.transient_results = copy.deepcopy(
            list(data.get("transient_results") or []))
        project._fea_ponding_cache = None
        project._gw_solver = None
        return model_hash(project)

    new_hash = ws.mutate(handle.id, "Compute groundwater", write,
                         attrs=_heavy())
    if new_hash is None:
        return {"written_back": False,
                "why_not_written": "The model changed while the "
                                   "groundwater ran, so this field belongs "
                                   "to a model that no longer exists. Read "
                                   "it with groundwater_results(result_id="
                                   "...) or run again."}
    res.model_hash = new_hash
    return {"written_back": True}


JOB_FINISHERS["groundwater"] = _finish_groundwater


@operation("drawdown_sweep_run", toolset="groundwater")
def drawdown_sweep_run(ws, project_id: Optional[str] = None,
                       methods: Optional[list] = None,
                       n_levels: int = 11, include_total: bool = True,
                       wait_seconds: float = 30.0) -> dict:
    """Search at a range of reservoir levels during a rapid drawdown and
    report the worst, as a background job."""
    wait = coerce_value(wait_seconds, float, "wait_seconds")
    if wait < 0:
        raise InvalidArgument("wait_seconds cannot be negative.")
    n = coerce_value(n_levels, int, "n_levels")
    if not 2 <= n <= 101:
        raise InvalidArgument("n_levels must be between 2 and 101 (each "
                              "level is a full search).")
    include_total = coerce_value(include_total, bool, "include_total")
    handle = ws.get(project_id)
    with ws.reading(handle.id, "drawdown_sweep_run") as project:
        if not project.settings.groundwater.rapid_drawdown:
            raise NotConfigured(
                "The rapid drawdown analysis is off, so there are no two "
                "reservoir levels to sweep between.",
                hint="settings_set groundwater.rapid_drawdown=true, with a "
                     "drawdown line (boundary_add type='drawdown').")
        method_ids = _check_runnable(project, methods)
        copy_ = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("drawdown_sweep", copy_, handle.id, fingerprint,
                        {"method_ids": method_ids, "n_levels": n,
                         "include_total": include_total})
    job.wait(wait)
    return _job_answer(ws, job, raise_on_failure=True)


def _finish_sweep(ws, job, handle, summary) -> dict:
    store_job_result(ws, job, handle, summary, "drawdown_sweep")
    return {}


JOB_FINISHERS["drawdown_sweep"] = _finish_sweep


# ----------------------------------------------------------------------
# Reading the field
# ----------------------------------------------------------------------
def field_of(project, stage=None):
    """``(SeepageResult, mesh, label)`` of the model's field: the governing
    one, or transient stage ``stage``."""
    result = getattr(project, "seepage_result", None)
    mesh = getattr(project, "fem_mesh", None)
    if result is None or mesh is None:
        raise NotFound("This model has no groundwater field.",
                       hint="Run groundwater_run.")
    return _pick_stage(result, list(project.transient_results or []), mesh,
                       stage)


def _pick_stage(result, stages, mesh, stage):
    if stage is None:
        return result, mesh, ""
    i = coerce_value(stage, int, "stage")
    if not stages:
        raise Conflict("stage is only read with a transient field; this "
                       "one is steady.")
    if not 0 <= i < len(stages):
        raise InvalidArgument(f"stage must be 0..{len(stages) - 1}.")
    t = (stages[i].notes or {}).get("time")
    return stages[i], mesh, f", stage {i}" + (f" (t = {t:g})"
                                              if t is not None else "")


@operation("groundwater_results", toolset="groundwater")
def groundwater_results(ws, project_id: Optional[str] = None,
                        result_id: Optional[str] = None,
                        view: str = "summary",
                        stage: Optional[int] = None,
                        point_xy: Optional[list] = None,
                        section: Optional[list] = None,
                        save_path: Optional[str] = None,
                        overwrite: bool = False) -> dict:
    """Read the groundwater field: summary, the values at a point, the
    flow through a section, the free surface, the stages, or every node."""
    from ogr_fem2d.solvers import UnsaturatedSeepageSolver
    from ogr_slip2d.transient_stability import groundwater_query_solver

    if view not in _RESULT_VIEWS:
        raise unknown("view", view, _RESULT_VIEWS)
    for name, given, owner in (("point_xy", point_xy, "point"),
                               ("section", section, "section"),
                               ("save_path", save_path, "nodes")):
        if given is not None and view != owner:
            raise Conflict(f"{name} is only read by view={owner!r}.")
    if overwrite and view != "nodes":
        raise Conflict("overwrite is only read by view='nodes'.")

    if result_id is not None:
        handle, res = ws.find_result(result_id)
        if project_id is not None and project_id != handle.id:
            raise InvalidArgument(f"{result_id} belongs to {handle.id}.")
        if res.kind != "groundwater":
            raise Conflict(f"{result_id} is a {res.kind} result, not a "
                           f"groundwater field.")
        data = res.payload()
        stages = list(data.get("transient_results") or [])
        field, mesh, label = _pick_stage(data.get("seepage_result"), stages,
                                         data.get("mesh"), stage)
        if field is None or mesh is None:
            raise NotFound(f"{result_id} holds no field.")
        solver = UnsaturatedSeepageSolver(mesh, {})
        source = {"result_id": res.id,
                  "stale": model_hash(handle.project) != res.model_hash}
        out = _read_field(ws, view, field, stages, mesh, solver, label,
                          point_xy, section, save_path, overwrite)
        return {**source, **out}
    handle = ws.get(project_id)
    with ws.reading(handle.id, "groundwater_results") as project:
        field, mesh, label = field_of(project, stage)
        stages = list(project.transient_results or [])
        solver = groundwater_query_solver(project)
        out = _read_field(ws, view, field, stages, mesh, solver, label,
                          point_xy, section, save_path, overwrite)
    return {"project_id": handle.id, **out}


def _read_field(ws, view, field, stages, mesh, solver, label, point_xy,
                section, save_path, overwrite) -> dict:
    from ..coerce import point

    out: dict = {"view": view, "field": ("governing" if not label
                                         else label.lstrip(", "))}
    if view == "summary":
        out["summary"] = seepage_field_summary(field)
        out["mesh"] = {"elements": mesh.element_count,
                       "nodes": mesh.node_count}
        out["stages"] = len(stages)
        return out
    if view == "stages":
        if not stages:
            raise Conflict("This field is steady; it has no stages.")
        out["stages"] = stage_rows(stages)
        return out
    if not field.ok:
        raise Conflict("This field did not converge or is empty: there is "
                       "nothing to read from it.",
                       details={"notes": json_safe(field.notes)})
    if view == "point":
        if point_xy is None:
            raise InvalidArgument("view='point' needs point_xy [x, y].")
        x, y = point(point_xy, "point_xy")
        e = mesh.locate(x, y)
        if e is None:
            raise Conflict(f"({x:g}, {y:g}) is outside the mesh.")
        vx, vy = field.velocity[e.id] if field.velocity else (None, None)
        out["at"] = json_safe({
            "x": x, "y": y,
            "total_head_m": mesh.interpolate(field.total_head, x, y),
            "pressure_head_m": mesh.interpolate(field.pressure_head, x, y),
            "pore_pressure_kpa": mesh.interpolate(field.pore_pressure, x,
                                                  y),
            "element": e.id, "material_id": e.material_id,
            "velocity": [vx, vy],
            "gradient": (field.gradient[e.id] if field.gradient
                         else None),
            "kr": field.kr[e.id] if field.kr else None})
        return out
    if view == "section":
        pts = points(section, "section", minimum=2)
        if len(pts) != 2:
            raise InvalidArgument("section is two points [[x0, y0], "
                                  "[x1, y1]].")
        (x0, y0), (x1, y1) = pts
        q = solver.flux_through_segment(field, x0, y0, x1, y1, samples=500)
        out["section"] = json_safe({
            "from": [x0, y0], "to": [x1, y1],
            "length_m": math.hypot(x1 - x0, y1 - y0), "flow": q,
            "sign": "positive when the flow crosses towards the section's "
                    "left-hand normal (the direction from->to turned +90 "
                    "degrees); reversing the section reverses the sign",
            "unit": "the permeability's unit times metres (per metre of "
                    "width)"})
        return out
    if view == "free_surface":
        fs = solver.free_surface_points(field)
        out["free_surface"] = [[round(x, 4), round(y, 4)] for x, y in fs]
        if not fs:
            out["notes"] = ["No P = 0 crossing: the mesh is entirely "
                            "saturated or entirely dry."]
        return out
    # nodes
    lines = ["node,x,y,total_head_m,pressure_head_m,pore_pressure_kpa"]
    for nd in mesh.nodes:
        i = nd.id
        lines.append(f"{i},{nd.x:.6g},{nd.y:.6g},"
                     f"{field.total_head[i]:.6g},"
                     f"{field.pressure_head[i]:.6g},"
                     f"{field.pore_pressure[i]:.6g}")
    out["rows"] = len(lines) - 1
    if save_path is None:
        out["csv_head"] = "\n".join(lines[:21])
        out["notes"] = ["The first 20 rows; pass save_path for them all."]
        return out
    target = ws.resolve_path(save_path, for_write=True, overwrite=overwrite,
                             suffix=".csv")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out["saved_to"] = str(target)
    return out
