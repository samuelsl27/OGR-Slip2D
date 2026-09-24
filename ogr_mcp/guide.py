# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a language model has to know to build a slope model correctly.

English on purpose: its reader is a model, not the interface's user (the
spec 008 decision, stated so it is not read as a breach of rule 2).

Two texts. ``INSTRUCTIONS`` is short and travels with every connection as
the server's ``instructions``; ``GUIDE`` is the full version, served as the
resource ``ogr://guide``. Many clients never read resources, so every rule
that changes a NUMBER is in the short one too, and repeated in the tool
descriptions where it bites.

Author: Samuel Sáez López (UPCT)
"""

SOURCE_URL = "https://github.com/samuelsl27/OGR-Slip2D"

INSTRUCTIONS = """\
OGR Slip2D: 2-D slope stability by limit equilibrium (9 methods, 7 searches).
Units are SI everywhere: m, kN, kPa, kN/m3, degrees. x to the right, y up.
Workflow: project_new -> model_define (geometry + materials + water in one
call) -> project_validate -> analysis_configure -> analysis_run ->
results_get / model_render. Pass the project_id you get back; it may be
omitted while only one model is open.
Rules that change the number:
- A region nobody assigned takes the FIRST material of the list.
- A water table or piezometric line does nothing until materials point at it
  (model_define water_table.materials, or boundary_add assign_to).
- search grid nx, ny are INTERVALS: points = nx + 1; radius_increment 10
  means 11 radii per centre.
- analysis_run may return state 'running' with a job_id: poll job_get.
- A result marked stale was computed on a model that has changed since.
- A finite-element groundwater field (groundwater_run) reaches only the
  materials with pore_pressure 'fem'.
catalog('strength_models') lists every material model and its parameters.
Full guide: resource ogr://guide.
"""

GUIDE = """\
# OGR Slip2D — modelling guide for agents

## Units and axes
SI everywhere: lengths in m, forces in kN (per metre out of plane),
stresses in kPa, unit weights in kN/m3, angles in degrees. x grows to the
right, y grows upwards. The unit system in settings only changes what the
interface DISPLAYS; every value you send or receive here is SI.

## Geometry
* The External boundary is one closed polygon: the whole soil/rock mass.
  Give its vertices in order; orientation is fixed for you.
* Material boundaries are open polylines that split the mass into regions.
  Run them from edge to edge of the External boundary. A CLOSED material
  boundary inside the mass is a lens: a region of its own, and a hole of
  the region around it (closed=true; each point once).
* Regions are computed, not drawn. Assign a material to a region by giving
  ONE POINT INSIDE IT (materials[].at in model_define, or material_assign).
* A region nobody assigned takes the FIRST material of the list. This is
  the program's convention and it is silent: check project_summary, whose
  regions[].how says 'assigned', 'inherited' or 'default_first_material'.
* At most one water table, one tension crack and one external boundary;
  a drawdown line only with the rapid drawdown option on; a Block Search
  object only with the Block Search.

## Water
* A water table (phreatic surface) or a piezometric line produces pore
  pressure ONLY in the materials that point at it. model_define's
  water_table {"points": [...], "materials": "all" | [names]} does both.
* Pointing a material at a water table sets its pore-pressure model to
  'water_table'; at a piezometric line, to 'piezometric'.
* Give water surfaces left to right, as functions of x.

## Groundwater by finite elements
hydraulic_set (each material's permeability) -> mesh_generate ->
seepage_bc_set (a side, nodes, a polyline of the boundary, or a
reservoir) -> groundwater_run -> groundwater_results / model_render(field=
'pore_pressure'). Then material_set(pore_pressure='fem') makes the
stability analysis read the field.
* A new mesh drops the conditions and fields of the old one: they are
  keyed by node, so set the conditions after meshing.
* The default conditions prescribe no head (unknown on the ground, no flow
  elsewhere); a steady solve needs a total head, a pressure head or a zero
  pressure somewhere. groundwater_run refuses a model with none set.
* Units: heads in m, pore pressure in kPa; permeability, infiltration and
  nodal flow in ONE consistent unit (m/s). van Genuchten and Gardner take
  suction head (alpha in 1/m); Brooks-Corey, Fredlund-Xing, Simple and a
  user curve take matric suction in kPa.
* Transient: transient_set with stages (time, calculate_sf, their own
  conditions); groundwater_run then gives a factor of safety per flagged
  stage.
* Rapid drawdown: turn it on in settings (groundwater.rapid_drawdown) with
  a drawdown line; drawdown_sweep_run searches at several reservoir levels,
  because the total drawdown is not always the worst.
* A water pressure grid (water_grid_set) is another source of pore
  pressure, read with a grid_* groundwater method.

## Materials
catalog('strength_models') lists the 21 strength models with their
parameters, units and defaults. The common ones:
* mohr_coulomb: cohesion (kPa), friction_angle (deg)
* undrained: cohesion (kPa) — phi = 0
* hoek_brown: sigci (kPa), mb, s, a
unit_weight is the bulk unit weight; sat_unit_weight is only used below the
water surface when use_sat_unit_weight is true.

## Search and methods
* surface_type 'circular' or 'non_circular'; each search method works with
  one or both (catalog('search_methods')).
* Grid search: grid bounds are the CENTRES of the trial circles, usually
  above and in front of the slope; 'auto' lets the program place them.
  nx, ny are INTERVALS (points = nx + 1); radius_increment 10 gives 11
  radii per centre. Total circles = (nx+1)(ny+1)(radius_increment+1).
* failure_direction: 'left_to_right' when the slope goes down to the right
  (crest on the left), 'right_to_left' otherwise. A wrong value produces a
  warning in project_validate.
* methods: bishop_simplified, janbu_simplified, janbu_corrected, spencer,
  gle_morgenstern_price, ordinary_fellenius, lowe_karafiath,
  corps_engineers_1, corps_engineers_2.
* With a design standard on, the number is an OVER-DESIGN factor (must be
  above 1), not a factor of safety; results say which in 'caption'.

## Running and reading results
* analysis_run runs every enabled method as a background job and waits up
  to wait_seconds. If it answers state 'running', call job_get with the
  job_id (and a wait) until 'done'; job_cancel stops it for real.
* The answer carries a result_id: results_get(result_id, view=...) with
  'summary', 'critical' (with slices), 'top', 'minima' or 'warnings';
  model_render(result_id=...) draws the critical surfaces.
* surface_evaluate prices ONE surface you give (circle by centre and
  radius, three points, or a polyline) without a search.
* Warnings are the program speaking: read them. A result is 'stale' when
  the model changed after it was computed.

## Undo and scripts
* Every edit is one undo step: project_history(action='undo').
* python_exec runs Python with `project` (the live model), `api` (every
  operation: api.material_set(...)), `np`, `ogr_core`, `ogr_slip2d` and
  `result(result_id)`. The whole script is one undo step, rolled back if it
  raises. Use it for what no tool covers yet.

## Files
Paths are absolute, or relative to the folder the server was started with
(--workdir). Nothing is overwritten unless overwrite=true.
"""
