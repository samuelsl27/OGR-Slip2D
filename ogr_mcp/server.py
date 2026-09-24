# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The MCP tools: one per operation of ``ogr_api``, written by hand.

By hand, and not generated from the registry, because what a tool is FOR
is its description and its parameter types — that is the whole interface a
language model sees — and a generated one would describe Python, not the
task. ``tests/test_mcp_server_v1195.py`` keeps the two from drifting: every
operation has a tool, every tool calls an operation, and every tool
parameter is a parameter of its operation.

Errors. The SDK (2.x) sends a generic "Error executing tool" for any
exception that is not a ``ToolError``, and logs the rest. A model cannot
recover from "an error happened", so every tool body runs inside
:func:`_errors`, which turns an ``OgrApiError`` into its coded message
(``[E_INVALID_ARGUMENT] ... Did you mean ...? Hint: ...``) and anything
else into its type and message.

This module imports the SDK; ``ogr_mcp/__init__.py`` does not, so the
package stays importable without it.

Author: Samuel Sáez López (UPCT)
"""
import contextlib
import json
import logging
import time
from typing import Annotated, Any, Literal, Optional

import anyio
from mcp.server.mcpserver import Context, Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from ogr_api import OgrApiError, call
from ogr_api.inventory import coverage

from . import __version__
from .guide import GUIDE, INSTRUCTIONS, SOURCE_URL
from .profiles import TOOLSETS, select

log = logging.getLogger("ogr_mcp")

#: Longest a tool call waits for a job before handing back its job_id.
#: Many clients cut a request at about 60 s whatever the protocol allows.
DEFAULT_MAX_WAIT_S = 50.0

# ----------------------------------------------------------------------
# Shared parameter types
# ----------------------------------------------------------------------
ProjectId = Annotated[Optional[str], Field(
    description="Model handle from project_new/project_open. May be "
                "omitted while only one model is open.")]
Points = Annotated[list[list[float]], Field(
    description="Vertices [[x, y], ...] in metres.")]
Methods = Annotated[Optional[list[str]], Field(
    description="Method ids, e.g. ['bishop_simplified', 'spencer']; "
                "default: the model's enabled methods. See "
                "catalog('methods').")]

_READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True)
_EDIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
_DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)


@contextlib.contextmanager
def _errors():
    """Every failure as a message a model can act on."""
    try:
        yield
    except ToolError:
        raise
    except OgrApiError as exc:
        raise ToolError(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 - reported, with its type
        log.exception("tool failed")
        raise ToolError(f"{type(exc).__name__}: {exc}") from None


def _strip(kwargs: dict) -> dict:
    """Drop the arguments the caller did not give, so each operation's own
    default applies (one default per parameter, in ``ogr_api``)."""
    return {k: v for k, v in kwargs.items() if v is not None}


def build_server(ws, *, profile: str = "full", toolsets=None,
                 max_wait: float = DEFAULT_MAX_WAIT_S) -> MCPServer:
    """An ``MCPServer`` publishing the tools of ``profile`` over ``ws``."""
    from ogr_api import __version__ as api_version

    selected = select(profile, toolsets)
    srv = MCPServer("ogr-slip2d", title="OGR Slip2D",
                    description="Slope stability by limit equilibrium: "
                                "build, analyse and read models.",
                    instructions=INSTRUCTIONS, version=__version__,
                    website_url=SOURCE_URL)
    registered: list[str] = []

    def tool(name: str, annotations: ToolAnnotations,
             structured: Optional[bool] = None):
        def deco(fn):
            if name in selected:
                srv.tool(name=name, annotations=annotations,
                         structured_output=structured)(fn)
                registered.append(name)
            return fn
        return deco

    def run(op_name: str, /, **kwargs) -> dict:
        # Positional-only, like ``ogr_api.call``: ``boundary_edit`` has a
        # parameter called ``op``, and a keyword of the same name here made
        # its every call a TypeError raised OUTSIDE ``_errors`` — which the
        # SDK then reported as a bare "Error executing tool". Found by the
        # forwarding test, not by a user.
        with _errors():
            return call(ws, op_name, **_strip(kwargs))

    async def wait_for_job(ctx: Context, answer: dict,
                           wait_seconds: float) -> dict:
        """Wait for a job, reporting its progress, up to the cap."""
        if answer.get("state") != "running":
            return answer
        job_id = answer["job_id"]
        deadline = time.monotonic() + max(0.0, min(wait_seconds, max_wait))
        last = None
        while time.monotonic() < deadline:
            await anyio.sleep(0.5)
            with _errors():
                st = ws.jobs.get(job_id).status()
            prog = st.get("progress") or {}
            if prog and prog.get("done") != last:
                last = prog.get("done")
                with contextlib.suppress(Exception):
                    await ctx.report_progress(prog.get("done", 0),
                                              prog.get("total"),
                                              message="surfaces evaluated")
            if st["state"] != "running":
                break
        return await anyio.to_thread.run_sync(
            lambda: run("job_get", job_id=job_id, wait_seconds=0))

    # ------------------------------------------------------------------
    # core
    # ------------------------------------------------------------------
    @tool("server_info", _READ)
    def server_info() -> dict[str, Any]:
        """What this server is, its units and rules, and the open models.
        Call it first."""
        return {
            "server": "ogr-slip2d", "version": __version__,
            "ogr_api": api_version,
            "units": "SI: m, kN, kPa, kN/m3, degrees",
            "profile": profile, "tools": list(registered),
            "workdir": str(ws.workdir) if ws.workdir else None,
            "open_models": [{"project_id": h.id, "name": h.project.name}
                            for h in ws.projects.values()],
            "guide": INSTRUCTIONS,
            # How much of the desktop program's menu an agent can reach
            # today (ogr_api/inventory.py); 'pending' shrinks each phase.
            "program_coverage": coverage(),
            "source_code": SOURCE_URL,
            "licence": "AGPL-3.0-or-later",
        }

    @tool("catalog", _READ)
    def catalog(kind: Annotated[Literal[
            "strength_models", "methods", "search_methods",
            "surface_types", "boundary_types", "pore_pressure_types",
            "groundwater_methods", "interslice_functions",
            "failure_directions", "unit_systems", "design_standards",
            "settings"], Field(description="What to list.")]
                ) -> dict[str, Any]:
        """What the program offers: material models with their parameters,
        methods, searches, boundary types, settings with their choices..."""
        return run("catalog", kind=kind)

    @tool("project_new", _EDIT)
    def project_new(name: Annotated[str, Field(
            description="Name of the new model.")] = "Untitled"
                    ) -> dict[str, Any]:
        """Create an empty model; returns its project_id."""
        return run("project_new", name=name)

    @tool("project_open", _EDIT)
    def project_open(path: Annotated[str, Field(
            description="Path of a .ogr file, absolute or relative to the "
                        "server's working folder.")]) -> dict[str, Any]:
        """Open a .ogr model file; returns its project_id and a summary."""
        return run("project_open", path=path)

    @tool("project_save", _EDIT)
    def project_save(project_id: ProjectId = None,
                     path: Annotated[Optional[str], Field(
                         description="Where to save (.ogr added if "
                                     "missing); default: its own file."
                     )] = None,
                     overwrite: Annotated[bool, Field(
                         description="Replace an existing other file."
                     )] = False) -> dict[str, Any]:
        """Save the model as a .ogr file the desktop program opens."""
        return run("project_save", project_id=project_id, path=path,
                   overwrite=overwrite)

    @tool("project_close", _DESTRUCTIVE)
    def project_close(project_id: ProjectId = None,
                      discard_changes: Annotated[bool, Field(
                          description="Close even with unsaved changes."
                      )] = False) -> dict[str, Any]:
        """Close a model (refuses to lose unsaved changes unless told)."""
        return run("project_close", project_id=project_id,
                   discard_changes=discard_changes)

    @tool("project_list", _READ)
    def project_list() -> dict[str, Any]:
        """Every open model with its project_id."""
        return run("project_list")

    @tool("project_summary", _READ)
    def project_summary(project_id: ProjectId = None,
                        detail: Annotated[Literal["normal", "full"], Field(
                            description="'full' adds every vertex."
                        )] = "normal") -> dict[str, Any]:
        """The model: boundaries, materials, the material each region
        resolves to (and how), loads, settings, whether it can run, undo
        history and results."""
        return run("project_summary", project_id=project_id, detail=detail)

    @tool("project_validate", _READ)
    def project_validate(project_id: ProjectId = None) -> dict[str, Any]:
        """The checks an analysis would make, without running: blockers,
        warnings and model notes (unassigned water, unused materials...)."""
        return run("project_validate", project_id=project_id)

    @tool("project_get", _READ)
    def project_get(project_id: ProjectId = None,
                    section: Annotated[str, Field(
                        description="A key of the .ogr file: materials, "
                                    "boundaries, settings, supports, "
                                    "distributed_loads, ...")] = "materials"
                    ) -> dict[str, Any]:
        """One section of the model exactly as the .ogr file stores it."""
        return run("project_get", project_id=project_id, section=section)

    # ------------------------------------------------------------------
    # model
    # ------------------------------------------------------------------
    @tool("model_define", _EDIT)
    def model_define(spec: Annotated[dict[str, Any], Field(description=(
            "The whole model. Keys: 'name'; 'external' [[x,y],...] closed "
            "outline (required); 'material_boundaries' [[[x,y],...],...] "
            "open polylines edge to edge; 'materials' [{'name', 'strength': "
            "{'model': 'mohr_coulomb', 'params': {'cohesion': 10, "
            "'friction_angle': 30}}, 'unit_weight': 20, 'at': [x, y] (a "
            "point inside its region), other properties...}]; "
            "'water_table' {'points': [[x,y],...], 'materials': 'all' or "
            "[names]}; 'piezometric_lines' [same]; 'tension_crack' "
            "[[x,y],...]; 'settings' {'section.field': value}; 'replace' "
            "(default true: replaces geometry and materials)."))],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Build or rebuild the whole model in one step: geometry,
        materials, their regions and water. Unassigned regions take the
        FIRST material."""
        return run("model_define", spec=spec, project_id=project_id)

    @tool("boundary_add", _EDIT)
    def boundary_add(type: Annotated[Literal[
            "external", "material", "water_table", "piezometric",
            "drawdown", "tension_crack", "block_search_object",
            "weak_layer", "anisotropic_surface"], Field(
                description="Boundary type.")],
            points: Points,
            project_id: ProjectId = None,
            name: Annotated[Optional[str], Field(
                description="Optional label.")] = None,
            closed: Annotated[Optional[bool], Field(
                description="Only for a block search window.")] = None,
            material: Annotated[Optional[str], Field(
                description="Weak layer only: its material.")] = None,
            assign_to: Annotated[Any, Field(
                description="Water table / piezometric line only: 'all' "
                            "or a list of material names that use it.")
            ] = None,
            replace: Annotated[bool, Field(
                description="External only: replace the existing one.")
            ] = False) -> dict[str, Any]:
        """Add one boundary. One external, one water table and one tension
        crack at most; a water surface does nothing until assigned."""
        return run("boundary_add", type=type, points=points,
                   project_id=project_id, name=name, closed=closed,
                   material=material, assign_to=assign_to,
                   replace=replace)

    @tool("boundary_edit", _DESTRUCTIVE)
    def boundary_edit(boundary: Annotated[str, Field(
            description="Boundary id (see project_summary) or name.")],
            op: Annotated[Literal[
                "set_vertices", "translate", "move_vertex",
                "insert_vertex", "delete_vertex", "rename", "change_type",
                "delete"], Field(description="What to do.")],
            project_id: ProjectId = None,
            points: Annotated[Optional[list[list[float]]], Field(
                description="set_vertices: the new vertices.")] = None,
            dx: Annotated[float, Field(description="translate: dx (m).")
                          ] = 0.0,
            dy: Annotated[float, Field(description="translate: dy (m).")
                          ] = 0.0,
            index: Annotated[Optional[int], Field(
                description="*_vertex: vertex index (insert goes before "
                            "it).")] = None,
            point_xy: Annotated[Optional[list[float]], Field(
                description="move/insert_vertex: [x, y].")] = None,
            name: Annotated[Optional[str], Field(
                description="rename: new name.")] = None,
            new_type: Annotated[Optional[str], Field(
                description="change_type: new boundary type.")] = None
            ) -> dict[str, Any]:
        """Edit or delete a boundary."""
        return run("boundary_edit", boundary=boundary, op=op,
                   project_id=project_id, points=points, dx=dx, dy=dy,
                   index=index, point_xy=point_xy, name=name,
                   new_type=new_type)

    @tool("material_set", _EDIT)
    def material_set(project_id: ProjectId = None,
                     material: Annotated[Optional[str], Field(
                         description="Name or id of the material to "
                                     "UPDATE; omit to create a new one."
                     )] = None,
                     name: Annotated[Optional[str], Field(
                         description="Name (required when creating).")
                     ] = None,
                     strength: Annotated[Optional[dict[str, Any]], Field(
                         description="{'model': id, 'params': {...}} — "
                                     "see catalog('strength_models').")
                     ] = None,
                     properties: Annotated[Optional[dict[str, Any]], Field(
                         description="Other properties: unit_weight, "
                                     "sat_unit_weight, use_sat_unit_weight,"
                                     " pore_pressure, ru, constant_u, "
                                     "water_surface_id, color, hu, phi_b, "
                                     "...")] = None) -> dict[str, Any]:
        """Create a material, or update one."""
        return run("material_set", project_id=project_id, material=material,
                   name=name, strength=strength, properties=properties)

    @tool("material_delete", _DESTRUCTIVE)
    def material_delete(material: Annotated[str, Field(
            description="Name or id.")],
            project_id: ProjectId = None,
            reassign_to: Annotated[Optional[str], Field(
                description="Material that takes over its regions.")
            ] = None,
            force: Annotated[bool, Field(
                description="Delete even if used, dropping its region "
                            "assignments.")] = False) -> dict[str, Any]:
        """Delete a material (refuses while regions use it)."""
        return run("material_delete", material=material,
                   project_id=project_id, reassign_to=reassign_to,
                   force=force)

    @tool("material_assign", _EDIT)
    def material_assign(material: Annotated[str, Field(
            description="Name or id.")],
            x: Annotated[float, Field(description="x of a point inside "
                                                  "the region (m).")],
            y: Annotated[float, Field(description="y of that point (m).")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Assign a material to the region containing (x, y)."""
        return run("material_assign", material=material, x=x, y=y,
                   project_id=project_id)

    # ------------------------------------------------------------------
    # settings
    # ------------------------------------------------------------------
    @tool("settings_get", _READ)
    def settings_get(project_id: ProjectId = None,
                     section: Annotated[Optional[str], Field(
                         description="One section (methods, search, "
                                     "groundwater, units, advanced, "
                                     "design_standard, seismic, ...); "
                                     "default all.")] = None
                     ) -> dict[str, Any]:
        """Every setting with its value, type and allowed choices."""
        return run("settings_get", project_id=project_id, section=section)

    @tool("settings_set", _EDIT)
    def settings_set(changes: Annotated[dict[str, Any], Field(
            description="{'section.field': value}, e.g. "
                        "{'methods.num_slices': 30, "
                        "'search.search_method': 'slope'}. All or "
                        "nothing.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Change any settings by dotted path; unknown names and values
        are refused with a suggestion."""
        return run("settings_set", changes=changes, project_id=project_id)

    @tool("analysis_configure", _EDIT)
    def analysis_configure(project_id: ProjectId = None,
                           methods: Methods = None,
                           surface_type: Annotated[Optional[Literal[
                               "circular", "non_circular"]], Field(
                               description="Slip surface shape.")] = None,
                           search_method: Annotated[Optional[str], Field(
                               description="grid, slope, auto_refine, "
                                           "particle_swarm (circular); "
                                           "block, path, "
                                           "simulated_annealing, "
                                           "auto_refine, particle_swarm "
                                           "(non-circular).")] = None,
                           num_slices: Annotated[Optional[int], Field(
                               description="Slices per surface.")] = None,
                           grid: Annotated[Any, Field(
                               description="Grid search centres: 'auto' or"
                                           " {'x_min','x_max','y_min',"
                                           "'y_max','nx','ny'}; nx, ny are"
                                           " intervals.")] = None,
                           radius_increment: Annotated[Optional[int], Field(
                               description="Grid search: radii per centre"
                                           " minus one.")] = None,
                           failure_direction: Annotated[Optional[Literal[
                               "left_to_right", "right_to_left"]], Field(
                               description="left_to_right when the slope "
                                           "goes down to the right.")
                           ] = None,
                           tolerance: Annotated[Optional[float], Field(
                               description="Convergence tolerance.")
                           ] = None,
                           design_standard: Annotated[Optional[str], Field(
                               description="'off', eurocode7_da1c1, "
                                           "eurocode7_da1c2, eurocode7_da2,"
                                           " eurocode7_da3 or custom.")
                           ] = None) -> dict[str, Any]:
        """The common analysis settings in one call."""
        return run("analysis_configure", project_id=project_id,
                   methods=methods, surface_type=surface_type,
                   search_method=search_method, num_slices=num_slices,
                   grid=grid, radius_increment=radius_increment,
                   failure_direction=failure_direction, tolerance=tolerance,
                   design_standard=design_standard)

    # ------------------------------------------------------------------
    # analysis
    # ------------------------------------------------------------------
    WaitSeconds = Annotated[float, Field(
        description=f"How long to wait for the result before returning a "
                    f"job_id (capped at {max_wait:g} s).")]

    @tool("analysis_run", _EDIT)
    async def analysis_run(ctx: Context, project_id: ProjectId = None,
                           methods: Methods = None,
                           wait_seconds: WaitSeconds = 30.0
                           ) -> dict[str, Any]:
        """Run the configured search for each method as a background job.
        Returns the result, or state 'running' and a job_id to poll with
        job_get."""
        started = await anyio.to_thread.run_sync(lambda: run(
            "analysis_run", project_id=project_id, methods=methods,
            wait_seconds=0))
        out = await wait_for_job(ctx, started, wait_seconds)
        if out.get("state") in ("failed", "crashed"):
            raise ToolError(f"[E_JOB_FAILED] The analysis {out['state']}: "
                            f"{out.get('error')} "
                            f"{json.dumps(out.get('problems') or '')}")
        return out

    @tool("job_get", _READ)
    async def job_get(ctx: Context, job_id: Annotated[str, Field(
            description="From analysis_run.")],
            wait_seconds: WaitSeconds = 0.0) -> dict[str, Any]:
        """A job's state and progress; its result once done."""
        answer = await anyio.to_thread.run_sync(
            lambda: run("job_get", job_id=job_id, wait_seconds=0))
        return await wait_for_job(ctx, answer, wait_seconds)

    @tool("job_cancel", _DESTRUCTIVE)
    def job_cancel(job_id: Annotated[str, Field(
            description="The job to stop.")]) -> dict[str, Any]:
        """Stop a running analysis and every process it started."""
        return run("job_cancel", job_id=job_id)

    @tool("job_list", _READ)
    def job_list() -> dict[str, Any]:
        """Every job of this session and its state."""
        return run("job_list")

    @tool("results_get", _READ)
    def results_get(result_id: Annotated[str, Field(
            description="From analysis_run, job_get or surface_evaluate.")],
            view: Annotated[Literal["summary", "critical", "top", "minima",
                                    "warnings"], Field(
                description="summary; critical (surface with its slice "
                            "table); top (n best surfaces); minima; "
                            "warnings.")] = "summary",
            method_id: Annotated[Optional[str], Field(
                description="One method only.")] = None,
            n: Annotated[int, Field(description="How many for 'top'/"
                                                "'minima'.")] = 10
            ) -> dict[str, Any]:
        """Read a result: factors, critical surfaces, slices, counts."""
        return run("results_get", result_id=result_id, view=view,
                   method_id=method_id, n=n)

    @tool("surface_evaluate", _READ)
    def surface_evaluate(surface: Annotated[dict[str, Any], Field(
            description="{'type': 'circle', 'centre_x', 'centre_y', "
                        "'radius'} or {'type': 'three_points', 'points': "
                        "[[x,y]x3]} or {'type': 'polyline', 'points': "
                        "[[x,y],...]}.")],
            project_id: ProjectId = None,
            methods: Methods = None) -> dict[str, Any]:
        """The factor of safety of ONE given slip surface, per method,
        with the model's settings (no search)."""
        return run("surface_evaluate", surface=surface,
                   project_id=project_id, methods=methods)

    # ------------------------------------------------------------------
    # view, history, python
    # ------------------------------------------------------------------
    @tool("model_render", _READ, structured=False)
    def model_render(project_id: ProjectId = None,
                     result_id: Annotated[Optional[str], Field(
                         description="Draw this result's critical "
                                     "surfaces.")] = None,
                     method_id: Annotated[Optional[str], Field(
                         description="Only this method's surface.")
                     ] = None,
                     width: Annotated[int, Field(
                         description="Pixels, 200-4000.")] = 900,
                     height: Annotated[int, Field(
                         description="Pixels, 150-4000.")] = 600,
                     save_path: Annotated[Optional[str], Field(
                         description="Also save the PNG here (for clients "
                                     "that cannot show images).")] = None,
                     overwrite: Annotated[bool, Field(
                         description="Replace an existing file.")] = False
                     ) -> list:
        """A picture (PNG) of the model, with a result's critical surface."""
        out = run("model_render", project_id=project_id,
                  result_id=result_id, method_id=method_id, width=width,
                  height=height, save_path=save_path, overwrite=overwrite)
        note = {k: v for k, v in out.items() if k != "png"}
        return [Image(data=out["png"], format="png"), json.dumps(note)]

    @tool("project_history", _EDIT)
    def project_history(project_id: ProjectId = None,
                        action: Annotated[Literal["list", "undo", "redo"],
                                          Field(description="What to do.")
                                          ] = "list",
                        steps: Annotated[int, Field(
                            description="How many steps.")] = 1
                        ) -> dict[str, Any]:
        """Undo or redo edits, or list them. Every edit is one step."""
        return run("project_history", project_id=project_id, action=action,
                   steps=steps)

    @tool("python_exec", _DESTRUCTIVE)
    def python_exec(code: Annotated[str, Field(
            description="Python source. Available: project (the live "
                        "model), api (every tool as api.<name>(...)), np, "
                        "ogr_core, ogr_slip2d, result(result_id). The "
                        "value of the last expression is returned.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Run Python against the model, for anything no tool covers. One
        undo step; rolled back if it raises. Full access to the machine."""
        return run("python_exec", code=code, project_id=project_id)

    # ------------------------------------------------------------------
    # resources
    # ------------------------------------------------------------------
    @srv.resource("ogr://guide", name="modelling_guide",
                  mime_type="text/markdown",
                  description="How to build a slope model correctly.")
    def guide() -> str:
        return GUIDE

    @srv.resource("ogr://catalog/{kind}", name="catalog",
                  mime_type="application/json",
                  description="catalog(kind) as a resource.")
    def catalog_resource(kind: str) -> str:
        return json.dumps(run("catalog", kind=kind))

    missing = [t for t in selected if t not in registered]
    if missing:  # pragma: no cover - a profile naming a tool never written
        raise RuntimeError(f"profile names tools that do not exist: "
                           f"{missing}")
    srv._ogr_tools = tuple(registered)  # for tests and server_info
    return srv


def all_tools() -> tuple[str, ...]:
    return tuple(t for tools in TOOLSETS.values() for t in tools)
