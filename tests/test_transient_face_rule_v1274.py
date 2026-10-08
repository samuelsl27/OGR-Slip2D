# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.274 (D269) — the seepage face of a transient step follows the steady
solver's rule, which is relative to the flow, and not an absolute flux.

The defect
----------
``TransientSeepageSolver.step`` carried its own copy of the switching loop
and released a node held at P = 0 when its reaction exceeded 1e-12, an
ABSOLUTE flux; the steady solver uses q_tol = 1e-3 times the largest nodal
flux. With permeabilities from 1e-13 to 1e-4 m/s on the verification bank,
an absolute threshold is round-off for one model and the whole flow of
another — the answer depended on the UNITS of the permeability.

The invariants
--------------
* **Dimensional invariance, to the bit.** Scaling every permeability by
  lambda and every time by 1/lambda multiplies each step's system by lambda
  and leaves the heads unchanged. With lambda = 2**-20 the scaling is exact
  in floating point, so the heads must be EQUAL. They are with the relative
  rule; with the absolute one (switch off) the face of a drawdown takes
  another node and the heads move by centimetres — measured 2.5 cm on this
  dam, which is what the test pins as "they differ".
* **No seepage face, no change.** A transient without UNKNOWN nodes computes
  nothing new: the switch on and off give the same heads to the bit.
* **The step asks its final state.** A transient step with a seepage face
  records ``unsettled_nodes``, as the steady solver does.

On the bank the unified rule moves nothing measurable (05-015 to 021 equal
to the bit, the drawdown of problem 102 by 3e-7 m: ``_auditoria/P6_0274``).
The switch is restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    TransientSeepageSolver,
    TransientStage,
)

LAMBDA = 2.0 ** -20
_CACHE: dict = {}


def _t127():
    if "t" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t127_d269", Path(__file__).parent / "test_unsaturated_v127.py")
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        _CACHE["t"] = t
        _CACHE["mesh"] = t._dam_mesh(1.0)
    return _CACHE["t"], _CACHE["mesh"]


def _bcs(h1, face=True):
    """The rectangular dam with the upstream head at ``h1``; above it, and
    on the downstream face above H2 and on the crest, a potential seepage
    face (``face``) or an impervious boundary."""
    t, mesh = _t127()
    b = SeepageBoundaryConditions()
    for nid in sorted(mesh.boundary_node_ids()):
        nd = mesh.nodes[nid]
        if abs(nd.x) < 1e-9 and nd.y <= h1 + 1e-9:
            b.add_node(nid, BCType.TOTAL_HEAD, h1)
        elif abs(nd.x - t.L_DAM) < 1e-9 and nd.y <= t.H2 + 1e-9:
            b.add_node(nid, BCType.TOTAL_HEAD, t.H2)
        elif face and (abs(nd.x) < 1e-9 or abs(nd.x - t.L_DAM) < 1e-9
                       or abs(nd.y - t.H_DAM) < 1e-9):
            b.add_node(nid, BCType.UNKNOWN)
        else:
            b.add_node(nid, BCType.NODAL_FLOW, 0.0)
    return b


def _drawdown(scale, rule, face=True):
    """From the steady state with the reservoir at 10 m, the reservoir
    drops to 4 m: one hour and ten hours (times divided by ``scale``)."""
    t, mesh = _t127()
    props = {"m": HydraulicProperties(
        ks=t.K_DAM * scale, model=PermeabilityModel.GARDNER, gardner_a=1.0,
        gardner_n=3.0)}
    old = seepage.TRANSIENT_FACE_RULE
    try:
        seepage.TRANSIENT_FACE_RULE = rule
        s = TransientSeepageSolver(mesh, props, relaxation=0.5,
                                   tolerance=1e-6, time_steps=8,
                                   max_picard=80)
        down = _bcs(4.0, face)
        return s.solve_transient(
            [TransientStage(time=3600.0 / scale, bcs=down),
             TransientStage(time=36000.0 / scale, bcs=down)],
            initial_bcs=_bcs(10.0, face))
    finally:
        seepage.TRANSIENT_FACE_RULE = old


def _run(scale, rule, face=True):
    key = (scale, rule, face)
    if key not in _CACHE:
        _CACHE[key] = _drawdown(scale, rule, face)
    return _CACHE[key]


class TestDimensionalInvariance:
    def test_the_relative_rule_gives_the_same_heads_to_the_bit(self):
        a, b = _run(1.0, True), _run(LAMBDA, True)
        for x, y in zip(a, b):
            assert x.converged and y.converged
            assert x.total_head == y.total_head
            assert sorted(x.seepage_nodes) == sorted(y.seepage_nodes)

    def test_the_absolute_rule_did_not(self):
        a, b = _run(1.0, False), _run(LAMBDA, False)
        worst = max(max(abs(p - q) for p, q in zip(x.total_head, y.total_head))
                    for x, y in zip(a, b))
        assert worst > 1e-3, worst          # measured 2.5 cm


class TestWithoutASeepageFace:
    def test_nothing_changes(self):
        a, b = _run(1.0, False, face=False), _run(1.0, True, face=False)
        for x, y in zip(a, b):
            assert x.total_head == y.total_head
            assert x.iterations == y.iterations
            assert "unsettled_nodes" not in y.notes


class TestTheStepAsksItsFinalState:
    def test_a_stage_with_a_face_reports_its_unsettled_nodes(self):
        res = _run(1.0, True)
        for r in res:
            assert r.notes["unsettled_nodes"] == 0, r.notes
            assert r.converged
