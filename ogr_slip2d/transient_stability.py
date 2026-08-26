# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From a transient seepage history to a history of factors of safety.

This is the coupling, and until v0.1.125 it existed only inside the
interface. ``MainWindow`` meshed, solved, staged and ran the stability
analysis; nothing outside Qt could do any of it, so a script — or the
command line, or a verification bank — could not analyse a drawdown at
all. The only programmatic door, ``solve_project_seepage``, drives the
*saturated linear* solver: no free surface, no seepage face, no k(psi).
What was missing was never the physics.

Two functions, and the interface now calls them:

``solve_project_groundwater``
    what *Compute Groundwater* does — a steady saturated/unsaturated
    solve, or a staged transient one when the project asks for it.

``run_transient_stability``
    the same, plus the factor of safety at every stage flagged
    *Calculate SF*.

**Each stage is analysed with its own water, both halves of it.** The
pore pressures come from that stage's field and the weight of any
standing water comes from that stage's boundary conditions, because that
is where a finite-element model states where its reservoir is
(``ogr_core.hydraulic.ponded_water``). Swapping only the field — which is
what the interface did until this version — analyses a drawdown with the
pressures of the emptied reservoir and the weight of the full one.

``ogr_fem2d`` is imported inside the functions, the same way
``ogr_core.project`` imports it: the dependency is real but it is not
needed to import this module, and the limit-equilibrium engine must not
require a finite-element package to load.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

__all__ = [
    "StageStability",
    "TransientStabilityOutcome",
    "solve_project_groundwater",
    "run_transient_stability",
    "stage_boundary_conditions",
    "with_stage_water",
]


# ======================================================================
@dataclass
class StageStability:
    """What one transient stage produced."""

    index: int
    time: float = 0.0
    label: str = ""
    #: ``ogr_fem2d.solvers.SeepageResult`` for this stage.
    result: object = None
    #: ``method_id -> factor of safety``, empty when the stage was not
    #: flagged *Calculate SF*.
    factors: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def minimum(self) -> Optional[float]:
        return min(self.factors.values()) if self.factors else None


@dataclass
class TransientStabilityOutcome:
    stages: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def results(self) -> list:
        """The per-stage seepage results, in stage order."""
        return [s.result for s in self.stages]

    def series(self, method_id: str) -> list:
        """``[(time, factor of safety)]`` for one method."""
        return [(s.time, s.factors[method_id]) for s in self.stages
                if method_id in s.factors]


# ======================================================================
def _hydraulic_props(project) -> dict:
    from ogr_core.hydraulic import HydraulicProperties
    from ogr_fem2d.solvers import hydraulic_props_of

    props = hydraulic_props_of(project)
    for m in getattr(project, "materials", []):
        props.setdefault(m.id, HydraulicProperties())
    return props


def _mesh_of(project, **mesh_kwargs):
    mesh = getattr(project, "fem_mesh", None)
    if mesh is not None and getattr(mesh, "element_count", 0) > 0:
        return mesh
    from ogr_fem2d.mesh import generate_mesh_for_project

    mesh = generate_mesh_for_project(project, **mesh_kwargs)
    project.fem_mesh = mesh
    return mesh


def _current_bcs(project, mesh):
    """The project's boundary conditions, defaulted the documented way.

    Same rule as the interface's ``_seepage_bcs``: a stored set whose
    node ids do not fit the current mesh is not a set for this mesh, so
    it is replaced rather than half applied.
    """
    from ogr_fem2d.solvers import default_boundary_conditions

    bcs = getattr(project, "seepage_bcs", None)
    ok = bcs is not None and {b.node_id for b in bcs.nodes} <= set(
        range(mesh.node_count))
    if not ok:
        bcs = default_boundary_conditions(mesh)
        project.seepage_bcs = bcs
    return bcs


def stage_boundary_conditions(project, stage: dict, current):
    """The boundary conditions of one stage, falling back to ``current``.

    v0.1.31 — without per-stage conditions the initial state and every
    stage would share one set, the field would already be in equilibrium
    with it and nothing would evolve in time. A drawdown needs the stage
    level to differ from the initial one.
    """
    from ogr_fem2d.solvers import SeepageBoundaryConditions

    raw = stage.get("bcs") if isinstance(stage, dict) else None
    if not raw:
        return current
    return SeepageBoundaryConditions.from_dict(raw)


# ======================================================================
def solve_project_groundwater(project, *, progress_cb: Optional[Callable]
                              = None, **mesh_kwargs):
    """Solve the project's groundwater analysis as configured.

    Returns a single ``SeepageResult`` for a steady analysis, or the list
    of per-stage results for a transient one. The transient results are
    also stored on ``project.transient_results`` and the governing field
    on ``project.seepage_result``, which is where every consumer looks
    for them — the pore-pressure coupling, the Interpret windows and the
    saved file.

    Unlike ``solve_project_seepage`` this uses the **unsaturated** solver,
    with its free surface and its seepage faces. That other function is
    the saturated linear door and stays as it is; confined cases are
    validated against it.
    """
    from ogr_fem2d.solvers import UnsaturatedSeepageSolver

    gw = project.settings.groundwater
    mesh = _mesh_of(project, **mesh_kwargs)
    props = _hydraulic_props(project)
    gamma_w = getattr(gw, "pore_fluid_unit_weight", 9.81)

    if gw.transient and gw.transient_stages:
        return _solve_transient(project, mesh, props, gamma_w,
                                progress_cb=progress_cb)

    solver = UnsaturatedSeepageSolver(mesh, props, gamma_w=gamma_w,
                                      relaxation=0.4, max_iterations=200,
                                      tolerance=1e-5)
    result = solver.solve_unsaturated(_current_bcs(project, mesh))
    project.seepage_result = result
    project.transient_results = []
    project._fea_ponding_cache = None
    # Kept so the Interpret groundwater view can trace the free surface
    # without rebuilding a solver that might differ from the one that
    # produced the field it is drawing.
    project._gw_solver = solver
    return result


def _solve_transient(project, mesh, props, gamma_w, *, progress_cb=None):
    from ogr_fem2d.solvers import TransientSeepageSolver, TransientStage

    gw = project.settings.groundwater
    solver = TransientSeepageSolver(
        mesh, props, gamma_w=gamma_w, relaxation=0.5,
        tolerance=gw.transient_tolerance,
        max_picard=gw.transient_max_iterations,
        time_steps=gw.transient_time_steps,
    )
    current = _current_bcs(project, mesh)
    initial = current
    if gw.transient_initial_bcs:
        from ogr_fem2d.solvers import SeepageBoundaryConditions
        initial = SeepageBoundaryConditions.from_dict(
            gw.transient_initial_bcs)

    stages = []
    for st in gw.transient_stages:
        stages.append(TransientStage(
            time=float(st.get("time", 0.0)),
            calculate_sf=bool(st.get("calculate_sf")),
            label=str(st.get("label", "")),
            bcs=stage_boundary_conditions(project, st, current),
        ))
    results = solver.solve_transient(stages, initial_bcs=initial)
    project.transient_results = results
    if results:
        project.seepage_result = results[-1]
    project._fea_ponding_cache = None
    project._gw_solver = solver
    if progress_cb is not None:
        progress_cb(len(results), len(results) or 1)
    return results


# ======================================================================
class with_stage_water:
    """Context manager: the project speaks for one stage while inside.

    Installs the stage's **field and boundary conditions** together and
    puts back whatever was there on the way out, whether or not the body
    raised. Both halves matter and only one of them used to be swapped:
    the pore pressures come from the field, and the weight of standing
    water comes from the conditions, so a stage analysed with the wrong
    conditions carries the weight of a reservoir it has already emptied.
    """

    def __init__(self, project, result, bcs=None):
        self.project = project
        self.result = result
        self.bcs = bcs

    def __enter__(self):
        p = self.project
        self._saved = (getattr(p, "seepage_result", None),
                       getattr(p, "seepage_bcs", None),
                       getattr(p, "_fea_ponding_cache", None))
        p.seepage_result = self.result
        if self.bcs is not None:
            p.seepage_bcs = self.bcs
        p._fea_ponding_cache = None
        return p

    def __exit__(self, *exc):
        p = self.project
        p.seepage_result, p.seepage_bcs, p._fea_ponding_cache = self._saved
        return False


# ======================================================================
def run_transient_stability(project, method_ids=None, *,
                            progress_cb: Optional[Callable] = None,
                            **mesh_kwargs) -> TransientStabilityOutcome:
    """Solve the transient seepage and the stability at the flagged
    stages.

    This is the point of the per-stage *Calculate SF* checkbox: it turns
    a transient pore-pressure history into a factor-of-safety history,
    which is what an engineer needs from a drawdown or a prolonged
    rainfall. Every flagged stage runs the project's own configured
    search, through the same ``run_analysis`` a plain Compute uses, so
    the stage factors honour exactly the settings the project declares.
    """
    from ogr_core.materials import PorePressureType
    from .analysis_runner import run_analysis

    gw = project.settings.groundwater
    out = TransientStabilityOutcome()
    if not (gw.transient and gw.transient_stages):
        out.warnings.append(
            "This project has no transient groundwater stages, so there "
            "is no factor-of-safety history to compute. Turn on "
            "Transient Groundwater and define the stages first.")
        return out

    mesh = _mesh_of(project, **mesh_kwargs)
    current = _current_bcs(project, mesh)
    # The conditions the transient STARTS from. A stage that spans no
    # time did not evolve under its own conditions — it reports the state
    # it inherited — so its water is the water that was in force before
    # it. For the initial instant, the one stage that always has zero
    # span, that is this set and not the currently defined one. Getting
    # it wrong is the same defect this version closes, reappearing one
    # level in: the field of the full reservoir with the weight of the
    # emptied one, or the other way round.
    in_force = current
    if gw.transient_initial_bcs:
        from ogr_fem2d.solvers import SeepageBoundaryConditions
        in_force = SeepageBoundaryConditions.from_dict(
            gw.transient_initial_bcs)
    results = solve_project_groundwater(project, progress_cb=progress_cb,
                                        **mesh_kwargs)
    if not isinstance(results, list):
        results = [results]

    # A field that failed is not a field. Say so: without this the caller
    # gets a list of stages with no factors and no reason, and the most
    # common cause — boundary conditions with no prescribed head at all,
    # which makes the steady problem singular — is one the solver already
    # names precisely.
    for r in results:
        why = r.notes.get("error")
        if why:
            out.warnings.append(
                f"The groundwater analysis produced no field: {why}")
            break

    # The stage pressures only reach the limit-equilibrium engine through
    # materials set to FEM_SEEPAGE. Saying so beats reporting a dry slope.
    couples = any(m.pore_pressure == PorePressureType.FEM_SEEPAGE
                  for m in project.materials)
    _NO_COUPLING = (
        "No material takes its pore pressure from the finite-element "
        "seepage field, so the stage factors of safety would ignore "
        "the computed water pressures entirely.")
    if not couples:
        out.warnings.append(_NO_COUPLING)

    method_ids = (list(method_ids) if method_ids
                  else list(project.settings.methods.enabled_methods)
                  or ["bishop_simplified"])

    for i, r in enumerate(results):
        st = (gw.transient_stages[i]
              if i < len(gw.transient_stages) else {})
        stage = StageStability(
            index=i,
            time=float(r.notes.get("time", st.get("time", 0.0))),
            label=str(st.get("label", "")),
            result=r,
        )
        out.stages.append(stage)
        if not r.notes.get("calculate_sf"):
            continue
        if not couples:
            # The warning also lives on the STAGE, because that is where
            # the Interpret groundwater window reads it and where it
            # survives a save. Returning it only to the caller would have
            # taken it off the screen it was written for.
            r.notes["fos_warning"] = _NO_COUPLING
            stage.warnings.append(_NO_COUPLING)
            continue
        if not r.total_head:
            continue
        own = stage_boundary_conditions(project, st, None)
        if own is not None:
            in_force = own
        elif r.notes.get("time_steps"):
            # It advanced under the currently defined conditions, which
            # is the fallback v0.1.31 established.
            in_force = current
        with with_stage_water(project, r, in_force):
            outcome = run_analysis(project, method_ids)
        for mid, sr in (outcome.results or {}).items():
            crit = sr.critical if sr else None
            if crit is not None:
                stage.factors[mid] = crit.fos
        stage.warnings = list(outcome.warnings)
        # Kept on the result too: that is where the Interpret chart and
        # the saved project have read them since v0.1.31.
        r.notes["fos"] = dict(stage.factors)
        if stage.factors:
            r.notes["fos_min"] = min(stage.factors.values())
    return out
