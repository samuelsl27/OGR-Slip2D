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

#: What a job's progress counts, by kind.
_STEPS = {"analysis": "surfaces evaluated", "groundwater": "stages solved",
          "drawdown_sweep": "searches done",
          "statistics": "evaluations done",
          "back_analysis": "surfaces analysed", "optimize": "steps"}

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
                 max_wait: float = DEFAULT_MAX_WAIT_S,
                 backend=None, oauth=None,
                 public_url: Optional[str] = None) -> MCPServer:
    """An ``MCPServer`` publishing the tools of ``profile`` over ``ws``.

    With ``backend`` (an ``ogr_api.bridge.BridgeClient``, spec 008 F4)
    every tool is forwarded to a running window instead: the same
    operations, run on the window's own model; ``ws`` is then unused.
    """
    from ogr_api import __version__ as api_version

    selected = select(profile, toolsets)
    auth_kwargs = {}
    if oauth is not None:
        # F4b (v0.1.204): the server is its own authorization server; see
        # ``oauth.py``. Tokens are bound to the MCP endpoint's public URL.
        from mcp.server.auth.settings import (AuthSettings,
                                              ClientRegistrationOptions,
                                              RevocationOptions)
        base = public_url.rstrip("/")
        auth_kwargs = dict(
            auth_server_provider=oauth,
            auth=AuthSettings(
                issuer_url=base, resource_server_url=f"{base}/mcp",
                validate_token_resource=True,
                client_registration_options=ClientRegistrationOptions(
                    enabled=True),
                revocation_options=RevocationOptions(enabled=True)))
    srv = MCPServer("ogr-slip2d", title="OGR Slip2D",
                    description="Slope stability by limit equilibrium: "
                                "build, analyse and read models.",
                    instructions=INSTRUCTIONS, version=__version__,
                    website_url=SOURCE_URL, **auth_kwargs)
    if oauth is not None:
        from .oauth import install_approval_route
        install_approval_route(srv, oauth)
    registered: list[str] = []
    pending: dict = {}

    def tool(name: str, annotations: ToolAnnotations,
             structured: Optional[bool] = None):
        # Collected here and registered at the end IN THE PROFILE'S ORDER,
        # so tools/list is deterministic by construction and not by the
        # order this file happens to define them in (the 2026-07-28
        # specification asks for a stable list, which clients cache).
        def deco(fn):
            if name in selected:
                pending[name] = (fn, annotations, structured)
            return fn
        return deco

    def run(op_name: str, /, **kwargs) -> dict:
        # Positional-only, like ``ogr_api.call``: ``boundary_edit`` has a
        # parameter called ``op``, and a keyword of the same name here made
        # its every call a TypeError raised OUTSIDE ``_errors`` — which the
        # SDK then reported as a bare "Error executing tool". Found by the
        # forwarding test, not by a user.
        with _errors():
            if backend is not None:
                return backend.call(op_name, **_strip(kwargs))
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
            # Through the operation, so that attached to a window (F4) the
            # job is asked where it runs.
            st = await anyio.to_thread.run_sync(
                lambda: run("job_get", job_id=job_id, wait_seconds=0))
            prog = st.get("progress") or {}
            if prog and prog.get("done") != last:
                last = prog.get("done")
                with contextlib.suppress(Exception):
                    await ctx.report_progress(prog.get("done", 0),
                                              prog.get("total"),
                                              message=_STEPS.get(
                                                  st.get("kind"), "steps"))
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
        if backend is not None:
            models = [{"project_id": m["project_id"], "name": m["name"]}
                      for m in run("project_list")["projects"]]
        else:
            models = [{"project_id": h.id, "name": h.project.name}
                      for h in ws.projects.values()]
        return {
            "server": "ogr-slip2d", "version": __version__,
            "ogr_api": api_version,
            "units": "SI: m, kN, kPa, kN/m3, degrees",
            "profile": profile, "tools": list(registered),
            "workdir": (str(ws.workdir) if ws is not None and ws.workdir
                        else None),
            "open_models": models,
            # F4: attached to a running window, the model IS the window's.
            "attached_to_window": ({"pid": backend.pid,
                                    "window": backend.window}
                                   if backend is not None else None),
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
    def project_new(name: Annotated[Optional[str], Field(
            description="Name of the new model.")] = None,
            template: Annotated[Literal["empty", "demo"], Field(
                description="'demo' starts from the demo slope (with a "
                            "water table).")] = "empty"
                    ) -> dict[str, Any]:
        """Create a model (empty or the demo slope); returns its
        project_id."""
        return run("project_new", name=name, template=template)

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
            "open polylines edge to edge, or {'points': [...], 'closed': "
            "true} for a lens; 'materials' [{'name', 'strength': "
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
                description="Material: true for a lens (a closed boundary "
                            "inside the mass). Block search window.")
            ] = None,
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
                "delete", "copy", "scale", "rotate", "simplify"], Field(
                    description="What to do.")],
            project_id: ProjectId = None,
            points: Annotated[Optional[list[list[float]]], Field(
                description="set_vertices: the new vertices.")] = None,
            dx: Annotated[float, Field(description="translate/copy: dx "
                                                   "(m).")] = 0.0,
            dy: Annotated[float, Field(description="translate/copy: dy "
                                                   "(m).")] = 0.0,
            index: Annotated[Optional[int], Field(
                description="*_vertex: vertex index (insert goes before "
                            "it).")] = None,
            point_xy: Annotated[Optional[list[float]], Field(
                description="move/insert_vertex: [x, y].")] = None,
            name: Annotated[Optional[str], Field(
                description="rename: new name.")] = None,
            new_type: Annotated[Optional[str], Field(
                description="change_type: new boundary type.")] = None,
            sx: Annotated[Optional[float], Field(
                description="scale: x factor.")] = None,
            sy: Annotated[Optional[float], Field(
                description="scale: y factor (default sx).")] = None,
            angle: Annotated[Optional[float], Field(
                description="rotate: degrees, counter-clockwise.")] = None,
            pivot: Annotated[Any, Field(
                description="scale/rotate: [x, y] or 'centroid' "
                            "(default).")] = None,
            tolerance: Annotated[Optional[float], Field(
                description="simplify: max deviation (m).")] = None
            ) -> dict[str, Any]:
        """Edit, transform, copy or delete a boundary."""
        return run("boundary_edit", boundary=boundary, op=op,
                   project_id=project_id, points=points, dx=dx, dy=dy,
                   index=index, point_xy=point_xy, name=name,
                   new_type=new_type, sx=sx, sy=sy, angle=angle,
                   pivot=pivot, tolerance=tolerance)

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
                                     "drawdown_envelope ({'kind': 'r', "
                                     "'c_r', 'phi_r_deg'} or {'kind': "
                                     "'kc1', 'd', 'psi_deg'}), ... "
                                     "Permeability: hydraulic_set.")
                     ] = None) -> dict[str, Any]:
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
                         description="Replace an existing file.")] = False,
                     field: Annotated[Optional[Literal[
                         "total_head", "pressure_head", "pore_pressure"]],
                         Field(description="Contour the groundwater field "
                                           "(and its free surface).")
                     ] = None,
                     stage: Annotated[Optional[int], Field(
                         description="With field: a transient stage.")
                     ] = None,
                     source: Annotated[Literal["model", "window"], Field(
                         description="'window': the real canvas (only "
                                     "attached to a window).")
                     ] = "model") -> list:
        """A picture (PNG) of the model, with a result's critical surface
        or the groundwater field."""
        out = run("model_render", project_id=project_id,
                  result_id=result_id, method_id=method_id, width=width,
                  height=height, save_path=save_path, overwrite=overwrite,
                  field=field, stage=stage, source=source)
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
    # model (F2): the External as a whole, geometry health
    # ------------------------------------------------------------------
    @tool("external_reshape", _EDIT)
    def external_reshape(project_id: ProjectId = None,
                         offset: Annotated[Optional[float], Field(
                             description="Parallel offset of every edge "
                                         "(m): + expands, - shrinks.")
                         ] = None,
                         points_xy: Annotated[Optional[list[list[float]]],
                                              Field(
                             description="Or a polyline whose two ends lie "
                                         "on the External: outside = fill,"
                                         " inside = excavation.")] = None,
                         keep_removed_as_material: Annotated[bool, Field(
                             description="Keep the cut-out old ground as a "
                                         "material boundary.")] = False,
                         snap_tolerance: Annotated[float, Field(
                             description="How far an end may be from the "
                                         "External, as a fraction of the "
                                         "model size.")] = 1e-3
                         ) -> dict[str, Any]:
        """Expand or shrink the External boundary (offset, or a fill/cut
        polyline)."""
        return run("external_reshape", project_id=project_id, offset=offset,
                   points_xy=points_xy,
                   keep_removed_as_material=keep_removed_as_material,
                   snap_tolerance=snap_tolerance)

    @tool("slope_angle_change", _EDIT)
    def slope_angle_change(toe: Annotated[Any, Field(
            description="The toe: an External vertex index or its [x, y].")],
            crest: Annotated[Any, Field(
                description="The crest: an External vertex index or its "
                            "[x, y] (higher than the toe).")],
            project_id: ProjectId = None,
            change_deg: Annotated[Optional[float], Field(
                description="Change of the overall angle, degrees: + "
                            "steeper, - flatter.")] = None,
            target_deg: Annotated[Optional[float], Field(
                description="Or the new overall angle, degrees.")] = None,
            mode: Annotated[Literal["horizontal", "vertical", "rotate"],
                            Field(description=(
                                "How the face vertices move: keep their "
                                "elevation (horizontal), their x (vertical)"
                                ", or turn about the toe."))] = "horizontal",
            keep_benches: Annotated[Optional[bool], Field(
                description="Projections only (default true): move each "
                            "vertex relative to the crest, keeping bench "
                            "widths.")] = None) -> dict[str, Any]:
        """Change the overall angle of the slope face between the toe and
        the crest; only the face moves (layers ending on it follow)."""
        return run("slope_angle_change", toe=toe, crest=crest,
                   project_id=project_id, change_deg=change_deg,
                   target_deg=target_deg, mode=mode,
                   keep_benches=keep_benches)

    @tool("geometry_cleanup", _EDIT)
    def geometry_cleanup(project_id: ProjectId = None,
                         apply: Annotated[bool, Field(
                             description="Remove duplicate vertices (else "
                                         "only report).")] = False,
                         simplify_tolerance: Annotated[float, Field(
                             description="With apply: also simplify every "
                                         "boundary by this deviation (m)."
                         )] = 0.0) -> dict[str, Any]:
        """Report duplicate vertices, self-crossings and crossings between
        boundaries; optionally fix duplicates."""
        return run("geometry_cleanup", project_id=project_id, apply=apply,
                   simplify_tolerance=simplify_tolerance)

    # ------------------------------------------------------------------
    # loads
    # ------------------------------------------------------------------
    @tool("load_set", _EDIT)
    def load_set(project_id: ProjectId = None,
                 load: Annotated[Optional[str], Field(
                     description="Id or name of a load to CHANGE; omit to "
                                 "add one.")] = None,
                 kind: Annotated[Optional[Literal["distributed", "line"]],
                                 Field(description="New load: distributed "
                                                   "(kPa along start-end) "
                                                   "or line (kN/m at a "
                                                   "point).")] = None,
                 start: Annotated[Optional[list[float]], Field(
                     description="Distributed: [x, y]; give start and end "
                                 "left to right along the ground so a "
                                 "normal load presses into it.")] = None,
                 end: Annotated[Optional[list[float]], Field(
                     description="Distributed: [x, y].")] = None,
                 point_xy: Annotated[Optional[list[float]], Field(
                     description="Line load: [x, y].")] = None,
                 magnitude: Annotated[Optional[float], Field(
                     description="kPa (distributed) or kN/m (line), >= 0; "
                                 "direction comes from orientation.")
                 ] = None,
                 magnitude_end: Annotated[Optional[float], Field(
                     description="Distributed triangular/trapezoidal: the "
                                 "value at end.")] = None,
                 distribution: Annotated[Optional[Literal[
                     "constant", "triangular", "trapezoidal"]], Field(
                     description="Distributed only.")] = None,
                 orientation: Annotated[Optional[Literal[
                     "normal_to_boundary", "vertical", "horizontal",
                     "angle_from_horizontal", "angle_to_boundary"]], Field(
                     description="Direction. For a line load, "
                                 "normal/angle_to_boundary follow the ground"
                                 " surface at the point (normal into the "
                                 "ground; angle CCW from the left-to-right "
                                 "tangent, -90 = normal).")
                 ] = None,
                 angle_deg: Annotated[Optional[float], Field(
                     description="Only with an angle orientation.")] = None,
                 creates_excess_pore_pressure: Annotated[Optional[bool],
                                                         Field(
                     description="Loads undrained layers (needs the "
                                 "excess pore pressure option).")] = None,
                 name: Annotated[Optional[str], Field(
                     description="Label.")] = None) -> dict[str, Any]:
        """Add a distributed or line load, or change one."""
        return run("load_set", project_id=project_id, load=load, kind=kind,
                   start=start, end=end, point_xy=point_xy,
                   magnitude=magnitude, magnitude_end=magnitude_end,
                   distribution=distribution, orientation=orientation,
                   angle_deg=angle_deg,
                   creates_excess_pore_pressure=creates_excess_pore_pressure,
                   name=name)

    @tool("load_delete", _DESTRUCTIVE)
    def load_delete(loads: Annotated[Any, Field(
            description="List of load ids/names, or 'all'.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete loads (distributed or line) by id or name, or all."""
        return run("load_delete", loads=loads, project_id=project_id)

    @tool("seismic_set", _EDIT)
    def seismic_set(project_id: ProjectId = None,
                    enabled: Annotated[Optional[bool], Field(
                        description="Apply the pseudo-static load.")] = None,
                    kh: Annotated[Optional[float], Field(
                        description="Horizontal coefficient (fraction of "
                                    "g).")] = None,
                    kv: Annotated[Optional[float], Field(
                        description="Vertical coefficient (fraction of g)."
                    )] = None,
                    creates_excess_pore_pressure: Annotated[
                        Optional[bool], Field(
                            description="Seismic excess pore pressure.")
                    ] = None) -> dict[str, Any]:
        """The pseudo-static seismic load (kh, kv)."""
        return run("seismic_set", project_id=project_id, enabled=enabled,
                   kh=kh, kv=kv,
                   creates_excess_pore_pressure=creates_excess_pore_pressure)

    @tool("seismic_record_set", _EDIT)
    def seismic_record_set(project_id: ProjectId = None,
                           record: Annotated[Optional[str], Field(
                               description="Id or name of a record to "
                                           "rename/re-time; omit to add.")
                           ] = None,
                           name: Annotated[Optional[str], Field(
                               description="Record name.")] = None,
                           path: Annotated[Optional[str], Field(
                               description="Text file: time-acceleration "
                                           "pairs or one value per line.")
                           ] = None,
                           text: Annotated[Optional[str], Field(
                               description="The same, inline.")] = None,
                           accelerations: Annotated[
                               Optional[list[float]], Field(
                                   description="Or the samples directly.")
                           ] = None,
                           dt: Annotated[Optional[float], Field(
                               description="Time step (s).")] = None,
                           unit: Annotated[Literal["g", "cm/s2", "m/s2"],
                                           Field(description="Unit of the "
                                                             "samples.")
                                           ] = "g") -> dict[str, Any]:
        """Add a strong-motion record for a Newmark analysis, or edit one."""
        return run("seismic_record_set", project_id=project_id,
                   record=record, name=name, path=path, text=text,
                   accelerations=accelerations, dt=dt, unit=unit)

    @tool("seismic_record_delete", _DESTRUCTIVE)
    def seismic_record_delete(record: Annotated[str, Field(
            description="Id or name.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete a strong-motion record by id or name."""
        return run("seismic_record_delete", record=record,
                   project_id=project_id)

    # ------------------------------------------------------------------
    # supports
    # ------------------------------------------------------------------
    @tool("support_type_set", _EDIT)
    def support_type_set(project_id: ProjectId = None,
                         support_type: Annotated[Optional[str], Field(
                             description="Id or name of a type to CHANGE; "
                                         "omit to define one.")] = None,
                         type_class: Annotated[Optional[Literal[
                             "end_anchored", "grouted_tieback",
                             "grouted_tieback_friction", "soil_nail",
                             "pile_micropile", "geosynthetic",
                             "user_defined", "retaining_wall_efp",
                             "helical_anchor"]], Field(
                             description="The support class.")] = None,
                         name: Annotated[Optional[str], Field(
                             description="Name of the type.")] = None,
                         params: Annotated[Optional[dict[str, Any]], Field(
                             description="Class parameters (kN, kN/m, kPa,"
                                         " m, %); unknown names are "
                                         "refused with the valid ones.")
                         ] = None,
                         force_application: Annotated[Optional[Literal[
                             "active", "passive"]], Field(
                             description="Default: the class's.")] = None,
                         orientation: Annotated[Optional[Literal[
                             "tangent_to_slip", "parallel_to_support",
                             "bisector", "horizontal",
                             "perpendicular_to_pile", "user_defined"]],
                             Field(description="Force direction; default "
                                               "the class's.")] = None,
                         user_angle_deg: Annotated[Optional[float], Field(
                             description="Only with user_defined.")] = None,
                         color: Annotated[Optional[str], Field(
                             description="Hex colour.")] = None
                         ) -> dict[str, Any]:
        """Define a support type (property set), or change one."""
        return run("support_type_set", project_id=project_id,
                   support_type=support_type, type_class=type_class,
                   name=name, params=params,
                   force_application=force_application,
                   orientation=orientation, user_angle_deg=user_angle_deg,
                   color=color)

    @tool("support_type_delete", _DESTRUCTIVE)
    def support_type_delete(support_type: Annotated[str, Field(
            description="Id or name.")],
            project_id: ProjectId = None,
            reassign_to: Annotated[Optional[str], Field(
                description="Type that takes over its placed supports.")
            ] = None) -> dict[str, Any]:
        """Delete a support type (refuses while supports use it)."""
        return run("support_type_delete", support_type=support_type,
                   project_id=project_id, reassign_to=reassign_to)

    @tool("support_set", _EDIT)
    def support_set(project_id: ProjectId = None,
                    support: Annotated[Optional[str], Field(
                        description="Id or name of a support to CHANGE; "
                                    "omit to place one.")] = None,
                    support_type: Annotated[Optional[str], Field(
                        description="Its type (id or name); may be omitted"
                                    " when only one exists.")] = None,
                    head: Annotated[Optional[list[float]], Field(
                        description="[x, y] at the slope face.")] = None,
                    tail: Annotated[Optional[list[float]], Field(
                        description="[x, y] inside the slope.")] = None,
                    dx: Annotated[Optional[float], Field(
                        description="Move an existing support by dx (m).")
                    ] = None,
                    dy: Annotated[Optional[float], Field(
                        description="...and dy (m).")] = None,
                    force_application: Annotated[Optional[Literal[
                        "active", "passive"]], Field(
                        description="Default: its type's.")] = None,
                    orientation: Annotated[Optional[Literal[
                        "tangent_to_slip", "parallel_to_support",
                        "bisector", "horizontal", "perpendicular_to_pile",
                        "user_defined"]], Field(
                        description="Default: its type's.")] = None,
                    user_angle_deg: Annotated[Optional[float], Field(
                        description="Only with user_defined.")] = None,
                    name: Annotated[Optional[str], Field(
                        description="Label.")] = None,
                    color: Annotated[Optional[str], Field(
                        description="Hex colour.")] = None
                    ) -> dict[str, Any]:
        """Place a support, or move, stretch or edit one."""
        return run("support_set", project_id=project_id, support=support,
                   support_type=support_type, head=head, tail=tail, dx=dx,
                   dy=dy, force_application=force_application,
                   orientation=orientation, user_angle_deg=user_angle_deg,
                   name=name, color=color)

    @tool("support_pattern_add", _EDIT)
    def support_pattern_add(start: Annotated[list[float], Field(
            description="[x, y]: first head.")],
            end: Annotated[list[float], Field(
                description="[x, y]: the row runs start to end.")],
            length: Annotated[float, Field(
                description="Support length (m).")],
            spacing: Annotated[float, Field(
                description="Distance between heads (m).")],
            project_id: ProjectId = None,
            support_type: Annotated[Optional[str], Field(
                description="Type id or name.")] = None,
            orientation_mode: Annotated[Literal["angle", "normal", "depth"],
                                        Field(
                description="angle: angle_deg from horizontal; normal: "
                            "perpendicular to the row; depth: vertical.")
            ] = "angle",
            angle_deg: Annotated[float, Field(
                description="For orientation_mode='angle'.")] = -15.0,
            flip_180: Annotated[bool, Field(
                description="Reverse every support.")] = False,
            force_application: Annotated[Optional[Literal[
                "active", "passive"]], Field(
                description="Default: the type's.")] = None,
            orientation: Annotated[Optional[str], Field(
                description="Force direction; default the type's.")] = None
            ) -> dict[str, Any]:
        """A row of supports along a segment (a pattern, ungroupable)."""
        return run("support_pattern_add", start=start, end=end,
                   length=length, spacing=spacing, project_id=project_id,
                   support_type=support_type,
                   orientation_mode=orientation_mode, angle_deg=angle_deg,
                   flip_180=flip_180, force_application=force_application,
                   orientation=orientation)

    @tool("support_delete", _DESTRUCTIVE)
    def support_delete(supports: Annotated[Any, Field(
            description="List of ids/names, or 'all'.")] = None,
            pattern: Annotated[Optional[str], Field(
                description="Or a whole pattern by pattern_id.")] = None,
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete placed supports by id or name, a pattern, or all."""
        return run("support_delete", supports=supports, pattern=pattern,
                   project_id=project_id)

    @tool("support_ungroup", _EDIT)
    def support_ungroup(pattern: Annotated[Optional[str], Field(
            description="pattern_id; default all patterns.")] = None,
            project_id: ProjectId = None) -> dict[str, Any]:
        """Break a pattern into independent supports."""
        return run("support_ungroup", pattern=pattern,
                   project_id=project_id)

    # ------------------------------------------------------------------
    # search objects
    # ------------------------------------------------------------------
    @tool("tension_crack_set", _EDIT)
    def tension_crack_set(mode: Annotated[Literal[
            "dry", "filled", "percent_filled", "filled_below_elevation",
            "filled_to_depth", "use_water_table", "use_piezometric"], Field(
                description="Water in the tension crack.")],
            project_id: ProjectId = None,
            percent_filled: Annotated[Optional[float], Field(
                description="percent_filled: 0-100.")] = None,
            elevation: Annotated[Optional[float], Field(
                description="filled_below_elevation: y (m).")] = None,
            depth: Annotated[Optional[float], Field(
                description="filled_to_depth: m.")] = None,
            piezometric_line: Annotated[Optional[str], Field(
                description="use_piezometric: which line.")] = None
            ) -> dict[str, Any]:
        """How much water stands in the tension crack (needs a
        tension_crack boundary)."""
        return run("tension_crack_set", mode=mode, project_id=project_id,
                   percent_filled=percent_filled, elevation=elevation,
                   depth=depth, piezometric_line=piezometric_line)

    @tool("focus_set", _EDIT)
    def focus_set(project_id: ProjectId = None,
                  focus: Annotated[Optional[str], Field(
                      description="Id of a focus object to CHANGE; omit to"
                                  " add.")] = None,
                  kind: Annotated[Optional[Literal[
                      "window", "line", "point", "tangent"]], Field(
                      description="window: surfaces through it; line: "
                                  "crossing it; point: through it; "
                                  "tangent: touching it.")] = None,
                  points_xy: Annotated[Optional[list[list[float]]], Field(
                      description="window 4 (or 3), line 2, point 1, "
                                  "tangent 2.")] = None,
                  tolerance: Annotated[Optional[float], Field(
                      description="point/tangent only (m).")] = None,
                  enabled: Annotated[Optional[bool], Field(
                      description="Switch it on or off.")] = None
                  ) -> dict[str, Any]:
        """Add a focus object that narrows the search, or change one."""
        return run("focus_set", project_id=project_id, focus=focus,
                   kind=kind, points_xy=points_xy, tolerance=tolerance,
                   enabled=enabled)

    @tool("focus_delete", _DESTRUCTIVE)
    def focus_delete(focus: Annotated[str, Field(
            description="Id, or 'all'.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete a focus object by id, or all of them."""
        return run("focus_delete", focus=focus, project_id=project_id)

    @tool("user_surface_add", _EDIT)
    def user_surface_add(surface: Annotated[dict[str, Any], Field(
            description="{'type': 'circle', 'centre_x', 'centre_y', "
                        "'radius'} or {'type': 'three_points', 'points': "
                        "[[x,y]x3]}.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Add a slip circle analysed alongside every search (circular
        surface type only)."""
        return run("user_surface_add", surface=surface,
                   project_id=project_id)

    @tool("user_surface_delete", _DESTRUCTIVE)
    def user_surface_delete(surface: Annotated[str, Field(
            description="Id, or 'all'.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete a user slip surface by id, or all of them."""
        return run("user_surface_delete", surface=surface,
                   project_id=project_id)

    # ------------------------------------------------------------------
    # annotations
    # ------------------------------------------------------------------
    @tool("annotation_set", _EDIT)
    def annotation_set(project_id: ProjectId = None,
                       annotation: Annotated[Optional[str], Field(
                           description="Id to CHANGE; 'all' with visible; "
                                       "omit to add.")] = None,
                       kind: Annotated[Optional[Literal[
                           "line", "arrow", "polyline", "polygon",
                           "rectangle", "circle", "text",
                           "dimension_length", "dimension_angle",
                           "dimension_x", "dimension_y", "axes", "image"]],
                           Field(description="What to draw.")] = None,
                       points_xy: Annotated[Optional[list[list[float]]],
                                            Field(
                           description="text/axes 1 point, "
                                       "dimension_angle 3, others 2+; "
                                       "image: its box corners.")] = None,
                       text: Annotated[Optional[str], Field(
                           description="Text; for an image, its file path."
                       )] = None,
                       style: Annotated[Optional[dict[str, Any]], Field(
                           description="colour, line_width, line_style, "
                                       "fill, fill_opacity, font_size.")
                       ] = None,
                       visible: Annotated[Optional[bool], Field(
                           description="Show or hide.")] = None,
                       dx: Annotated[Optional[float], Field(
                           description="Move by dx (m).")] = None,
                       dy: Annotated[Optional[float], Field(
                           description="...and dy (m).")] = None,
                       z: Annotated[Optional[Literal["front", "back"]],
                                    Field(description="Drawing order.")
                                    ] = None) -> dict[str, Any]:
        """Draw an annotation (never read by the analysis), or change one."""
        return run("annotation_set", project_id=project_id,
                   annotation=annotation, kind=kind, points_xy=points_xy,
                   text=text, style=style, visible=visible, dx=dx, dy=dy,
                   z=z)

    @tool("annotation_delete", _DESTRUCTIVE)
    def annotation_delete(annotations: Annotated[Any, Field(
            description="List of ids, or 'all'.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Delete annotations by id, or all of them."""
        return run("annotation_delete", annotations=annotations,
                   project_id=project_id)

    @tool("annotation_to_boundary", _EDIT)
    def annotation_to_boundary(annotation: Annotated[str, Field(
            description="Id of a line, polyline or closed shape.")],
            type: Annotated[Literal["external", "material", "water_table",
                                    "piezometric", "tension_crack"], Field(
                description="Boundary it becomes (closed shapes: external, "
                            "or material as a lens).")],
            project_id: ProjectId = None,
            assign_to: Annotated[Any, Field(
                description="Water surfaces: 'all' or material names.")
            ] = None,
            replace: Annotated[bool, Field(
                description="External: replace the existing one.")] = False
            ) -> dict[str, Any]:
        """Turn a drawn shape into a model boundary (explicit, one-way)."""
        return run("annotation_to_boundary", annotation=annotation,
                   type=type, project_id=project_id, assign_to=assign_to,
                   replace=replace)

    @tool("properties_table", _READ)
    def properties_table(what: Annotated[Literal[
            "materials", "supports", "hydraulic"], Field(
                description="Which table.")] = "materials",
            project_id: ProjectId = None) -> dict[str, Any]:
        """Materials, support types or hydraulic properties as a table."""
        return run("properties_table", what=what, project_id=project_id)

    # ------------------------------------------------------------------
    # files
    # ------------------------------------------------------------------
    @tool("dxf_inspect", _READ)
    def dxf_inspect(path: Annotated[str, Field(
            description="The .dxf file.")],
            unit: Annotated[str, Field(
                description="Drawing unit: m, cm, mm, ft...")] = "m",
            layer_kinds: Annotated[Optional[dict[str, str]], Field(
                description="Try a mapping layer -> external, material, "
                            "water_table, piezo, drawdown, tension_crack, "
                            "weak_layer, anisotropic_surface, ignore.")
            ] = None) -> dict[str, Any]:
        """Read a DXF without importing it: layers, proposed types, unit,
        problems."""
        return run("dxf_inspect", path=path, unit=unit,
                   layer_kinds=layer_kinds)

    @tool("dxf_import", _EDIT)
    def dxf_import(path: Annotated[str, Field(
            description="The .dxf file.")],
            project_id: ProjectId = None,
            unit: Annotated[str, Field(
                description="Drawing unit.")] = "m",
            layer_kinds: Annotated[Optional[dict[str, str]], Field(
                description="layer -> boundary type (see dxf_inspect).")
            ] = None,
            weld_pct: Annotated[float, Field(
                description="Weld distance, % of the drawing size.")
            ] = 0.05,
            simplify: Annotated[bool, Field(
                description="Simplify dense polylines.")] = True,
            simplify_pct: Annotated[float, Field(
                description="Simplification, % of the drawing size.")
            ] = 0.02,
            replace_model: Annotated[bool, Field(
                description="Replace boundaries of the imported types.")
            ] = True) -> dict[str, Any]:
        """Import DXF geometry into the model (one undo step)."""
        return run("dxf_import", path=path, project_id=project_id, unit=unit,
                   layer_kinds=layer_kinds, weld_pct=weld_pct,
                   simplify=simplify, simplify_pct=simplify_pct,
                   replace_model=replace_model)

    @tool("dxf_export", _EDIT)
    def dxf_export(path: Annotated[str, Field(
            description="Where to write the .dxf.")],
            project_id: ProjectId = None,
            result_id: Annotated[Optional[str], Field(
                description="Also draw this analysis's critical "
                            "surfaces.")] = None,
            overwrite: Annotated[bool, Field(
                description="Replace an existing file.")] = False,
            unit: Annotated[str, Field(description="Drawing unit.")] = "m",
            boundaries: Annotated[bool, Field(
                description="Include boundaries.")] = True,
            supports: Annotated[bool, Field(
                description="Include supports.")] = True,
            loads: Annotated[bool, Field(
                description="Include loads.")] = True,
            slip_surface: Annotated[bool, Field(
                description="Include the result's surfaces.")] = True,
            annotations: Annotated[bool, Field(
                description="Include labels.")] = True) -> dict[str, Any]:
        """Export the model (and a result) to DXF."""
        return run("dxf_export", path=path, project_id=project_id,
                   result_id=result_id, overwrite=overwrite, unit=unit,
                   boundaries=boundaries, supports=supports, loads=loads,
                   slip_surface=slip_surface, annotations=annotations)

    @tool("report_generate", _EDIT)
    def report_generate(path: Annotated[str, Field(
            description="Where to write the .pdf.")],
            result_id: Annotated[str, Field(
                description="An analysis result (analysis_run).")],
            overwrite: Annotated[bool, Field(
                description="Replace an existing file.")] = False,
            author: Annotated[Optional[str], Field(
                description="Author on the cover.")] = None,
            company: Annotated[Optional[str], Field(
                description="Company on the cover.")] = None,
            title: Annotated[Optional[str], Field(
                description="Report title.")] = None) -> dict[str, Any]:
        """A PDF report of an analysis."""
        return run("report_generate", path=path, result_id=result_id,
                   overwrite=overwrite, author=author, company=company,
                   title=title)

    @tool("properties_import", _EDIT)
    def properties_import(path: Annotated[str, Field(
            description="Another .ogr file.")],
            project_id: ProjectId = None,
            what: Annotated[Literal["materials", "support_types", "both"],
                            Field(description="What to copy.")] = "both",
            names: Annotated[Optional[list[str]], Field(
                description="Only these names.")] = None
            ) -> dict[str, Any]:
        """Copy materials and/or support types from another model (fresh
        ids; its water surfaces are not carried over)."""
        return run("properties_import", path=path, project_id=project_id,
                   what=what, names=names)


    # ------------------------------------------------------------------
    # groundwater (F3a): finite-element seepage and the drawdown sweep
    # ------------------------------------------------------------------
    async def run_job(ctx: Context, op_name: str, what: str,
                      wait_seconds: float, **kwargs) -> dict:
        started = await anyio.to_thread.run_sync(lambda: run(
            op_name, wait_seconds=0, **kwargs))
        out = await wait_for_job(ctx, started, wait_seconds)
        if out.get("state") in ("failed", "crashed"):
            raise ToolError(f"[E_JOB_FAILED] The {what} {out['state']}: "
                            f"{out.get('error')} "
                            f"{json.dumps(out.get('problems') or '')}")
        return out

    BcSide = Annotated[Optional[Literal["left", "right", "bottom",
                                        "ground"]], Field(
        description="A whole side of the model: 'ground' is the top "
                    "surface including the slope face.")]

    @tool("hydraulic_set", _EDIT)
    def hydraulic_set(material: Annotated[str, Field(
            description="Material name or id.")],
            project_id: ProjectId = None,
            model: Annotated[Optional[Literal[
                "constant", "simple", "brooks_corey", "fredlund_xing",
                "gardner", "van_genuchten", "user_defined"]], Field(
                description="Permeability model of the unsaturated zone. "
                            "van_genuchten/gardner take suction HEAD (m): "
                            "vg_alpha in 1/m, gardner_a in 1/m^n; the "
                            "others matric suction (kPa): bc_psi_b, fx_a, "
                            "user_curve suctions.")] = None,
            library: Annotated[Optional[str], Field(
                description="Typical soil of the model's library, e.g. "
                            "'Sand', 'Loam', 'Clay'.")] = None,
            properties: Annotated[Optional[dict[str, Any]], Field(
                description="Fields: ks (saturated permeability), k2_k1, "
                            "k1_angle_deg, kr_min, simple_soil_type, "
                            "bc_lambda, bc_psi_b, fx_a, fx_b, fx_c, "
                            "gardner_a, gardner_n, vg_alpha, vg_n, vg_m, "
                            "vg_custom_m, user_curve [[suction_kPa, k], "
                            "...], wc_sat, wc_res, specific_storage. A "
                            "parameter of another model is refused.")
            ] = None,
            reset: Annotated[bool, Field(
                description="Start from the defaults instead of the "
                            "material's current values.")] = False
            ) -> dict[str, Any]:
        """Set a material's hydraulic properties for the finite-element
        groundwater analysis (permeability, unsaturated model, water
        contents)."""
        return run("hydraulic_set", material=material,
                   project_id=project_id, model=model, library=library,
                   properties=properties, reset=reset)

    @tool("mesh_generate", _DESTRUCTIVE)
    def mesh_generate(project_id: ProjectId = None,
                      target_elements: Annotated[Optional[int], Field(
                          description="Approximate number of triangles "
                                      "(default 1000).")] = None,
                      target_size: Annotated[Optional[float], Field(
                          description="Element edge length (m), instead "
                                      "of target_elements.")] = None,
                      min_angle: Annotated[float, Field(
                          description="Quality floor, degrees.")] = 25.0,
                      refine_passes: Annotated[int, Field(
                          description="Maximum refinement passes.")] = 3
                      ) -> dict[str, Any]:
        """Generate the finite-element mesh. Replaces the old one and
        drops its boundary conditions and fields (keyed by node)."""
        return run("mesh_generate", project_id=project_id,
                   target_elements=target_elements, target_size=target_size,
                   min_angle=min_angle, refine_passes=refine_passes)

    @tool("mesh_reset", _DESTRUCTIVE)
    def mesh_reset(project_id: ProjectId = None) -> dict[str, Any]:
        """Remove the mesh and everything computed on it."""
        return run("mesh_reset", project_id=project_id)

    @tool("seepage_bc_set", _EDIT)
    def seepage_bc_set(project_id: ProjectId = None,
                       bc_type: Annotated[Optional[Literal[
                           "total_head", "pressure_head", "zero_pressure",
                           "nodal_flow", "infiltration", "unknown"]], Field(
                           description="total_head/pressure_head (m), "
                                       "nodal_flow (per node), infiltration"
                                       " (rate per length of boundary), "
                                       "zero_pressure, unknown (seepage "
                                       "face: P=0 or Q=0).")] = None,
                       side: BcSide = None,
                       nodes: Annotated[Optional[list[int]], Field(
                           description="Node ids instead of a side.")
                       ] = None,
                       along: Annotated[Optional[list[list[float]]], Field(
                           description="A polyline [[x,y],...]: the "
                                       "boundary nodes on it.")] = None,
                       reservoir: Annotated[Optional[dict[str, Any]], Field(
                           description="{'level': y, 'side': 'left' or "
                                       "'right', 'unknown_elsewhere': "
                                       "bool}: total head = level on the "
                                       "wetted perimeter.")] = None,
                       value: Annotated[Optional[float], Field(
                           description="The head, flow or rate; refused "
                                       "for types that read none.")] = None,
                       seepage_face: Annotated[Optional[bool], Field(
                           description="nodal_flow/infiltration only: may "
                                       "switch to a seepage face.")] = None
                       ) -> dict[str, Any]:
        """Assign a seepage boundary condition to a side, nodes, a polyline
        of the boundary, or a reservoir. Needs a mesh."""
        return run("seepage_bc_set", project_id=project_id, bc_type=bc_type,
                   side=side, nodes=nodes, along=along, reservoir=reservoir,
                   value=value, seepage_face=seepage_face)

    @tool("seepage_bc_clear", _DESTRUCTIVE)
    def seepage_bc_clear(project_id: ProjectId = None) -> dict[str, Any]:
        """Restore the default conditions: unknown (seepage face) on the
        ground surface, no flow on the other sides."""
        return run("seepage_bc_clear", project_id=project_id)

    @tool("transient_set", _EDIT)
    def transient_set(project_id: ProjectId = None,
                      enabled: Annotated[bool, Field(
                          description="Turn the transient analysis on or "
                                      "off.")] = True,
                      stages: Annotated[Optional[list[dict[str, Any]]], Field(
                          description="[{'time', 'calculate_sf', 'label', "
                                      "'bcs'}]; bcs is 'current', or {'base':"
                                      " 'current'|'defaults', 'assign': "
                                      "[seepage_bc_set arguments...]}; "
                                      "without bcs a stage uses the current "
                                      "conditions. Omit to keep the stages.")
                      ] = None,
                      initial: Annotated[Any, Field(
                          description="Conditions of the initial state: "
                                      "same forms as a stage's bcs, or "
                                      "'none' for the current ones.")] = None,
                      tolerance: Annotated[Optional[float], Field(
                          description="Convergence tolerance.")] = None,
                      max_iterations: Annotated[Optional[int], Field(
                          description="Picard iterations per step.")
                      ] = None,
                      time_steps: Annotated[Optional[int], Field(
                          description="Steps per stage; 0 = automatic.")
                      ] = None) -> dict[str, Any]:
        """Configure the staged transient groundwater analysis (times,
        per-stage conditions, Calculate SF, initial state)."""
        return run("transient_set", project_id=project_id, enabled=enabled,
                   stages=stages, initial=initial, tolerance=tolerance,
                   max_iterations=max_iterations, time_steps=time_steps)

    @tool("water_grid_set", _EDIT)
    def water_grid_set(project_id: ProjectId = None,
                       points: Annotated[Optional[list[list[float]]], Field(
                           description="[[x, y, value], ...].")] = None,
                       csv_path: Annotated[Optional[str], Field(
                           description="A text file of x, y, value rows "
                                       "instead of points.")] = None,
                       value_type: Annotated[Optional[Literal[
                           "total_head", "pressure_head", "pore_pressure"]],
                           Field(description="What the values are (m, m, "
                                             "kPa); sets the groundwater "
                                             "method grid_<type>, where "
                                             "the type lives.")] = None,
                       interpolation: Annotated[Optional[Literal[
                           "tps", "idw"]], Field(
                           description="Thin-plate spline or inverse "
                                       "distance.")] = None,
                       idw_neighbours: Annotated[Optional[int], Field(
                           description="Points IDW averages.")] = None,
                       allow_suction: Annotated[Optional[bool], Field(
                           description="Keep negative pore pressure.")
                       ] = None) -> dict[str, Any]:
        """Define the water pressure grid, or change its options. It is read
        with a grid_* groundwater method (settings_set)."""
        return run("water_grid_set", project_id=project_id, points=points,
                   csv_path=csv_path, value_type=value_type,
                   interpolation=interpolation,
                   idw_neighbours=idw_neighbours,
                   allow_suction=allow_suction)

    @tool("water_grid_delete", _DESTRUCTIVE)
    def water_grid_delete(project_id: ProjectId = None) -> dict[str, Any]:
        """Remove the water pressure grid."""
        return run("water_grid_delete", project_id=project_id)

    @tool("groundwater_run", _EDIT)
    async def groundwater_run(ctx: Context, project_id: ProjectId = None,
                              stage_factors: Annotated[bool, Field(
                                  description="Transient: also the factor "
                                              "of safety at the stages "
                                              "flagged calculate_sf.")
                              ] = True,
                              methods: Methods = None,
                              wait_seconds: WaitSeconds = 30.0
                              ) -> dict[str, Any]:
        """Solve the groundwater by finite elements (steady, or the
        transient stages) as a background job. The field is written back
        into the model; materials read it with pore_pressure='fem'."""
        return await run_job(ctx, "groundwater_run", "groundwater analysis",
                             wait_seconds, project_id=project_id,
                             stage_factors=stage_factors, methods=methods)

    @tool("groundwater_results", _EDIT)
    def groundwater_results(project_id: ProjectId = None,
                            result_id: Annotated[Optional[str], Field(
                                description="A stored groundwater result "
                                            "instead of the model's own "
                                            "field.")] = None,
                            view: Annotated[Literal[
                                "summary", "point", "section",
                                "free_surface", "stages", "nodes"], Field(
                                description="What to read.")] = "summary",
                            stage: Annotated[Optional[int], Field(
                                description="Transient stage (0-based); "
                                            "default the last.")] = None,
                            point_xy: Annotated[Optional[list[float]], Field(
                                description="view 'point': [x, y].")] = None,
                            section: Annotated[Optional[list[list[float]]],
                                               Field(
                                description="view 'section': [[x0, y0], "
                                            "[x1, y1]].")] = None,
                            save_path: Annotated[Optional[str], Field(
                                description="view 'nodes': write the CSV "
                                            "here.")] = None,
                            overwrite: Annotated[bool, Field(
                                description="Replace an existing file.")
                            ] = False) -> dict[str, Any]:
        """Read the groundwater field: head, pressure and flow at a point,
        the flow through a section, the free surface, the stages with their
        factors, or every node as CSV."""
        return run("groundwater_results", project_id=project_id,
                   result_id=result_id, view=view, stage=stage,
                   point_xy=point_xy, section=section, save_path=save_path,
                   overwrite=overwrite)

    @tool("drawdown_sweep_run", _EDIT)
    async def drawdown_sweep_run(ctx: Context, project_id: ProjectId = None,
                                 methods: Methods = None,
                                 n_levels: Annotated[int, Field(
                                     description="Reservoir levels from the "
                                                 "initial one to the lowest "
                                                 "ground (2-101); each is a "
                                                 "full search.")] = 11,
                                 include_total: Annotated[bool, Field(
                                     description="Also the total drawdown."
                                 )] = True,
                                 wait_seconds: WaitSeconds = 30.0
                                 ) -> dict[str, Any]:
        """Rapid drawdown: search at a range of reservoir levels and report
        the worst (the total drawdown is not always it)."""
        return await run_job(ctx, "drawdown_sweep_run", "drawdown sweep",
                             wait_seconds, project_id=project_id,
                             methods=methods, n_levels=n_levels,
                             include_total=include_total)

    # ------------------------------------------------------------------
    # statistics (F3b): random variables, statistics, back analysis,
    # optimisation, and questions to a stored result
    # ------------------------------------------------------------------
    @tool("random_variable_list", _READ)
    def random_variable_list(project_id: ProjectId = None
                             ) -> dict[str, Any]:
        """The model inputs that can be random variables (with their keys
        and current values), and the ones defined."""
        return run("random_variable_list", project_id=project_id)

    @tool("random_variable_set", _EDIT)
    def random_variable_set(key: Annotated[str, Field(
            description="The variable's key, from random_variable_list.")],
            project_id: ProjectId = None,
            distribution: Annotated[Optional[Literal[
                "none", "normal", "uniform", "triangular", "beta",
                "exponential", "lognormal", "gamma"]], Field(
                description="Distribution; its mean is always the "
                            "model's value.")] = None,
            std_dev: Annotated[Optional[float], Field(
                description="Standard deviation (normal, lognormal, beta, "
                            "gamma).")] = None,
            rel_min: Annotated[Optional[float], Field(
                description="How far below the mean it may go.")] = None,
            rel_max: Annotated[Optional[float], Field(
                description="How far above the mean it may go.")] = None,
            correlated_with: Annotated[Optional[str], Field(
                description="Key of another defined variable ('' to "
                            "clear).")] = None,
            correlation: Annotated[Optional[float], Field(
                description="Correlation coefficient, -1..1.")] = None,
            label: Annotated[Optional[str], Field(
                description="Display name.")] = None) -> dict[str, Any]:
        """Make a model input a random variable, or change one. New ones
        start at std 10 % of the mean and a 30 % range either side."""
        return run("random_variable_set", key=key, project_id=project_id,
                   distribution=distribution, std_dev=std_dev,
                   rel_min=rel_min, rel_max=rel_max,
                   correlated_with=correlated_with, correlation=correlation,
                   label=label)

    @tool("random_variable_delete", _DESTRUCTIVE)
    def random_variable_delete(key: Annotated[str, Field(
            description="A defined variable's key, or 'all'.")],
            project_id: ProjectId = None) -> dict[str, Any]:
        """Remove a random variable; correlations that pointed at it go."""
        return run("random_variable_delete", key=key, project_id=project_id)

    @tool("statistics_run", _EDIT)
    async def statistics_run(ctx: Context, project_id: ProjectId = None,
                             wait_seconds: WaitSeconds = 30.0
                             ) -> dict[str, Any]:
        """Compute Statistics as a background job: the deterministic run,
        then the probabilistic (PF, reliability index) and/or sensitivity
        analysis set in settings statistics.*, with the design factors
        and seed of the model."""
        return await run_job(ctx, "statistics_run", "statistics run",
                             wait_seconds, project_id=project_id)

    @tool("back_analysis_run", _EDIT)
    async def back_analysis_run(ctx: Context, project_id: ProjectId = None,
                                target_fos: Annotated[Optional[float], Field(
                                    description="Target factor of safety "
                                                "(default: settings).")
                                ] = None,
                                elevation: Annotated[Optional[float], Field(
                                    description="y of the horizontal force "
                                                "(m).")] = None,
                                method_id: Annotated[Optional[Literal[
                                    "bishop_simplified", "janbu_simplified",
                                    "janbu_corrected"]], Field(
                                    description="Method.")] = None,
                                wait_seconds: WaitSeconds = 30.0
                                ) -> dict[str, Any]:
        """The horizontal support force needed to reach a target factor of
        safety, over every surface of the configured search (a job)."""
        return await run_job(ctx, "back_analysis_run", "back analysis",
                             wait_seconds, project_id=project_id,
                             target_fos=target_fos, elevation=elevation,
                             method_id=method_id)

    @tool("optimize_run", _EDIT)
    async def optimize_run(ctx: Context, result_id: Annotated[str, Field(
            description="An analysis_run result with a non-circular "
                        "critical surface.")],
            method_id: Annotated[Optional[str], Field(
                description="Which method's critical surface.")] = None,
            max_iterations: Annotated[Optional[int], Field(
                description="Default: settings search.optimize_max_"
                            "iterations.")] = None,
            wait_seconds: WaitSeconds = 30.0) -> dict[str, Any]:
        """Optimise a non-circular critical surface with the model's
        optimisation settings and seed; the result is a NEW result_id."""
        return await run_job(ctx, "optimize_run", "optimisation",
                             wait_seconds, result_id=result_id,
                             method_id=method_id,
                             max_iterations=max_iterations)

    @tool("results_query", _EDIT)
    def results_query(result_id: Annotated[str, Field(
            description="A stored result.")],
            view: Annotated[Literal[
                "error_codes", "invalid_summary", "raw_data",
                "surfaces_through_point", "minimum_per_centre",
                "sf_along_slope", "slices", "filter", "histogram",
                "convergence", "samples", "sensitivity"], Field(
                description="Analysis results: error_codes (-120 tensile, "
                            "-112 m-alpha, -111 not converged, -101 "
                            "other), invalid_summary, raw_data, "
                            "surfaces_through_point, minimum_per_centre, "
                            "sf_along_slope, slices (method's numbers), "
                            "filter. Statistics results: histogram, "
                            "convergence, samples, sensitivity.")],
            method_id: Annotated[Optional[str], Field(
                description="Which method.")] = None,
            point_xy: Annotated[Optional[list[float]], Field(
                description="surfaces_through_point: [x, y].")] = None,
            tolerance: Annotated[Optional[float], Field(
                description="surfaces_through_point: metres (0.5).")
            ] = None,
            bins: Annotated[Optional[int], Field(
                description="sf_along_slope / histogram: bins.")] = None,
            rank: Annotated[Optional[int], Field(
                description="slices: the n-th lowest surface (default "
                            "the critical).")] = None,
            fos_min: Annotated[Optional[float], Field(
                description="filter: lowest factor.")] = None,
            fos_max: Annotated[Optional[float], Field(
                description="filter: highest factor.")] = None,
            code: Annotated[Optional[int], Field(
                description="filter: only surfaces with this error code.")
            ] = None,
            n: Annotated[int, Field(
                description="How many rows at most.")] = 20,
            save_path: Annotated[Optional[str], Field(
                description="raw_data / slices / samples: write a CSV.")
            ] = None,
            overwrite: Annotated[bool, Field(
                description="Replace an existing file.")] = False
            ) -> dict[str, Any]:
        """Ask a stored result what the Interpret window asks it."""
        return run("results_query", result_id=result_id, view=view,
                   method_id=method_id, point_xy=point_xy,
                   tolerance=tolerance, bins=bins, rank=rank,
                   fos_min=fos_min, fos_max=fos_max, code=code, n=n,
                   save_path=save_path, overwrite=overwrite)

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

    for name in selected:
        if name in pending:
            fn, ann, structured = pending[name]
            srv.tool(name=name, annotations=ann,
                     structured_output=structured)(fn)
            registered.append(name)
    missing = [t for t in selected if t not in registered]
    if missing:  # pragma: no cover - a profile naming a tool never written
        raise RuntimeError(f"profile names tools that do not exist: "
                           f"{missing}")
    srv._ogr_tools = tuple(registered)  # for tests and server_info
    return srv


def all_tools() -> tuple[str, ...]:
    return tuple(t for tools in TOOLSETS.values() for t in tools)
