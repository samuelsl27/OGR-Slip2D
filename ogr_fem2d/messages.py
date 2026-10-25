# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the seepage solvers say about a field, with stable codes
(v0.1.352, D335).

``notes["error"]``, ``notes["warning"]``, ``notes["mesh_warning"]`` and the
initial-state notes of a transient: why a field could not be solved, why it
did not converge, what a flat element does to the system. They were English
sentences with their values in them; each is a code here with that English
and its format specs, so the sentence is the one the solver wrote -- the
tests, the API and the bank read it -- and the interface translates it. A
reason that follows another sentence (an initial state that failed BECAUSE
of something) is nested with its own code.

Codes are ``seepage.*``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, coded

EMPTY_MESH = "seepage.empty_mesh"
NO_DIRICHLET = "seepage.no_dirichlet"
LINEAR_FAILED = "seepage.linear_failed"
PICARD_LINEAR_FAILED = "seepage.picard_linear_failed"
FINAL_FAILED = "seepage.final_failed"
FACE_UNSETTLED = "seepage.face_unsettled"
PICARD_NO_RESCUE = "seepage.picard_no_rescue"
PICARD_RESCUE_FAILED = "seepage.picard_rescue_failed"
PICARD_RESCUE_PIECEWISE_NA = "seepage.picard_rescue_piecewise_na"
INITIAL_FAILED = "seepage.initial_failed"
INITIAL_FAILED_WHY = "seepage.initial_failed_why"
NO_TIME_STEP = "seepage.no_time_step"
STAGE_STEPS = "seepage.stage_steps"
INITIAL_NOT_CONVERGED = "seepage.initial_not_converged"
INITIAL_NOT_CONVERGED_WHY = "seepage.initial_not_converged_why"
MESH_FLAT = "seepage.mesh_flat"

_PICARD = ("Picard iteration did not converge in {steps} steps (last change "
           "{change:.3e} m), and ")

SEEPAGE_NOTES = {s.code: s for s in (
    MessageSpec(EMPTY_MESH, "empty mesh"),
    MessageSpec(NO_DIRICHLET,
                "no Dirichlet (head) boundary condition: the problem is "
                "singular. Prescribe Total Head, Pressure Head or Zero "
                "Pressure somewhere on the boundary."),
    MessageSpec(LINEAR_FAILED, "linear solve failed"),
    MessageSpec(PICARD_LINEAR_FAILED,
                "linear solve failed at Picard iteration {it}"),
    MessageSpec(FINAL_FAILED, "final solve failed"),
    MessageSpec(FACE_UNSETTLED,
                "the seepage face never settled: {unsettled} boundary "
                "node(s) still want to switch between 'P = 0' and 'no flow' "
                "({frozen} were frozen by the switch budget of {budget}). The "
                "free surface this reports is not the converged one."),
    MessageSpec(PICARD_NO_RESCUE, _PICARD + "the rescue is switched off."),
    MessageSpec(PICARD_RESCUE_FAILED,
                _PICARD + "neither did the rescue (Anderson acceleration, then "
                "continuation with Newton's method; last change "
                "{rescue_change:.3e} m). A permeability function that drops "
                "many decades over a short suction range is the usual cause: "
                "check the curves of the materials near the water table."),
    # v0.1.362 (D367): the continuation stopped where its path turns back,
    # and the road that follows such turns works only with User Defined
    # curves
    MessageSpec(PICARD_RESCUE_PIECEWISE_NA,
                _PICARD + "neither did the rescue (Anderson acceleration, then "
                "continuation with Newton's method; last change "
                "{rescue_change:.3e} m). The continuation stopped where its "
                "path of solutions turns back; the road that follows the "
                "path across such turns works only when every material has "
                "a User Defined permeability curve, and this model has "
                "others."),
    MessageSpec(INITIAL_FAILED, "initial steady state failed"),
    MessageSpec(INITIAL_FAILED_WHY, "initial steady state failed: {why}"),
    MessageSpec(NO_TIME_STEP, "no time step computed"),
    MessageSpec(STAGE_STEPS,
                "stage {k}: some time steps did not converge; try more time "
                "steps or more Picard iterations per step"),
    MessageSpec(INITIAL_NOT_CONVERGED,
                "the initial steady state did not converge"),
    MessageSpec(INITIAL_NOT_CONVERGED_WHY,
                "the initial steady state did not converge: {why}"),
    MessageSpec(MESH_FLAT,
                "the mesh has {n} flat element(s) (three collinear nodes): "
                "nodes under them do not count as boundary and the "
                "conductivity matrix is badly conditioned. Regenerate the "
                "mesh."),
)}


def seepage_note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(SEEPAGE_NOTES, code, **args)

