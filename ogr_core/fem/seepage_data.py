# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The seepage data the project stores: boundary conditions and results, and
the closed-form identities that rebuild a result's derived fields.

v0.1.342 (D337) -- moved word for word from ``ogr_fem2d/solvers/seepage.py``
(the classes, ``restore_derived`` and ``hydraulic_props_of``) together with
the solver's element-flux loop (:func:`element_fluxes`). The core's loader
rebuilt these from a ``.ogr`` by importing the solver module; they are data,
so they are the core's. ``ogr_fem2d.solvers.seepage`` re-exports every name.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties


# ======================================================================
class BCType(Enum):
    TOTAL_HEAD = "total_head"
    PRESSURE_HEAD = "pressure_head"
    ZERO_PRESSURE = "zero_pressure"
    NODAL_FLOW = "nodal_flow"
    INFILTRATION = "infiltration"
    UNKNOWN = "unknown"          # seepage face (P = 0 or Q = 0)


@dataclass
class NodeBC:
    """Boundary condition applied at a single mesh node."""

    node_id: int
    bc_type: BCType
    value: float = 0.0
    seepage_face: bool = False

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "bc_type": self.bc_type.value,
                "value": self.value, "seepage_face": self.seepage_face}

    @classmethod
    def from_dict(cls, d: dict) -> "NodeBC":
        return cls(int(d["node_id"]), BCType(d["bc_type"]),
                   float(d.get("value", 0.0)),
                   bool(d.get("seepage_face", False)))


@dataclass
class SegmentBC:
    """Infiltration applied over a boundary segment (flux per unit
    length). Distributed to the two end nodes as q*L/2 each, which is the
    exact consistent load vector for a linear element."""

    node_a: int
    node_b: int
    q: float = 0.0
    seepage_face: bool = False

    def to_dict(self) -> dict:
        return {"node_a": self.node_a, "node_b": self.node_b, "q": self.q,
                "seepage_face": self.seepage_face}

    @classmethod
    def from_dict(cls, d: dict) -> "SegmentBC":
        return cls(int(d["node_a"]), int(d["node_b"]),
                   float(d.get("q", 0.0)),
                   bool(d.get("seepage_face", False)))


@dataclass
class SeepageBoundaryConditions:
    """The full BC set for a mesh."""

    nodes: list[NodeBC] = field(default_factory=list)
    segments: list[SegmentBC] = field(default_factory=list)

    def add_node(self, node_id: int, bc_type: BCType, value: float = 0.0,
                 seepage_face: bool = False) -> None:
        self.nodes = [b for b in self.nodes if b.node_id != node_id]
        self.nodes.append(NodeBC(node_id, bc_type, value, seepage_face))

    def add_segment(self, a: int, b: int, q: float,
                    seepage_face: bool = False) -> None:
        self.segments.append(SegmentBC(a, b, q, seepage_face))

    def of_type(self, bc_type: BCType) -> list[NodeBC]:
        return [b for b in self.nodes if b.bc_type == bc_type]

    def to_dict(self) -> dict:
        return {"nodes": [n.to_dict() for n in self.nodes],
                "segments": [s.to_dict() for s in self.segments]}

    @classmethod
    def from_dict(cls, d: dict) -> "SeepageBoundaryConditions":
        return cls(
            nodes=[NodeBC.from_dict(n) for n in d.get("nodes", [])],
            segments=[SegmentBC.from_dict(s) for s in d.get("segments", [])],
        )


# ======================================================================
def _finite_or_none(v):
    """``v`` with every non-finite float, at any depth of lists and
    dicts, replaced by None (see ``SeepageResult._json_safe``)."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, (list, tuple)):
        return [_finite_or_none(x) for x in v]
    if isinstance(v, dict):
        return {k: _finite_or_none(x) for k, x in v.items()}
    return v


def _change_series(values) -> list:
    """A convergence series as it is published in ``notes["history"]``:
    four significant figures, which is all a chart of it can show, and
    None where there is no number (v0.1.269, D265)."""
    return [float("%.4g" % v) if math.isfinite(v) else None
            for v in values]


# ======================================================================
@dataclass
class SeepageResult:
    """Nodal heads plus the derived fields the Interpret view needs.

    Only three of these are *data*: ``total_head`` (what the solve
    produced), ``kr`` (what conductivity scaling it produced it with) and
    ``gamma_w``. Everything else is a function of those plus the mesh and
    the material properties — which is why ``to_dict`` writes the three
    and ``restore_derived`` recomputes the rest. See ``to_dict``.
    """

    total_head: list[float] = field(default_factory=list)
    pressure_head: list[float] = field(default_factory=list)
    pore_pressure: list[float] = field(default_factory=list)
    # per-element Darcy velocity (vx, vy) and gradient magnitude
    velocity: list[tuple[float, float]] = field(default_factory=list)
    reactions: list[float] = field(default_factory=list)
    seepage_nodes: list[int] = field(default_factory=list)
    gradient: list[float] = field(default_factory=list)
    converged: bool = False
    iterations: int = 1
    notes: dict = field(default_factory=dict)
    # Unit weight of the pore fluid the heads were converted with. Kept on
    # the result because u = gamma_w * (H - y) cannot be rebuilt without
    # it, and the project setting may have changed since the solve.
    gamma_w: float = 9.81
    # Per-element relative permeability actually used, or None for a
    # saturated solve. Stored rather than recomputed from the final heads:
    # the Picard loop scales conductivity with kr(H_k) and then solves for
    # H_(k+1), so kr(H_final) is *close to* but not equal to the kr the
    # velocities were computed with. Recomputing would make a reopened
    # project draw slightly different flow vectors than the one that was
    # saved, which is exactly the kind of silent discrepancy that is
    # worse than the file being a little larger.
    kr: Optional[list[float]] = None

    @property
    def ok(self) -> bool:
        return self.converged and bool(self.total_head)

    # ------------------------------------------------------------------
    # Serialisation
    #
    # v0.1.78. Until this version the field was not written to the .ogr at
    # all: `fem_mesh` was saved and `seepage_result` was not, so reopening
    # a project whose materials take u from a finite-element field and
    # pressing Compute reported u = 0 everywhere — a dry slope, in
    # silence. v0.1.77 detected that and refused to compute; this is the
    # other half, which is to stop losing the field in the first place.
    #
    # What is written is only what cannot be derived:
    #
    #   pressure_head = H[i] - node[i].y        (exact, closed form)
    #   pore_pressure = gamma_w * pressure_head (exact, closed form)
    #   velocity, gradient = _element_fluxes(H, kr)  (deterministic)
    #   reactions -> not written at all: its only consumers are the
    #       solver's own seepage-face iteration and the transient step,
    #       both of which recompute it. Nothing on the reload path reads
    #       it, and it never survived a save before either.
    #
    # That is ~3N floats instead of ~10N. The alternative — writing every
    # field verbatim — costs nothing in code but stores the same numbers
    # up to four times over, and the .ogr is a text format a user is
    # expected to be able to open.
    # ------------------------------------------------------------------
    SCHEMA = 1

    @staticmethod
    def _round(values, sig: int = 9):
        """Trim the digits that carry no information.

        Heads are metres and pressures kilopascals; nine significant
        figures is already far below any physical meaning, and it is kept
        that generous on purpose so the round-trip test can demand 1e-9
        rather than negotiating with the tolerance.
        """
        return [float(f"%.{sig}g" % v) for v in values]

    @staticmethod
    def _json_safe(notes: dict) -> dict:
        """Drop note entries JSON cannot represent.

        Notes are diagnostics, not results — a key that cannot be written
        is worth losing, but it must never make ``save()`` raise on a
        project the user just spent minutes computing.

        v0.1.269 — a non-finite number is written as null. ``json.dumps``
        accepts NaN and inf by default and writes ``NaN``, which is not
        JSON: the .ogr is declared pure JSON, and a ``picard_delta`` of a
        loop that never ran, or the residual of a rescue whose last solve
        failed (inf), put one in it.
        """
        out = {}
        for k, v in (notes or {}).items():
            v = _finite_or_none(v)
            try:
                json.dumps(v, allow_nan=False)
            except (TypeError, ValueError):
                continue
            out[str(k)] = v
        return out

    def to_dict(self) -> dict:
        d = {
            "schema": self.SCHEMA,
            "total_head": self._round(self.total_head),
            "gamma_w": float(self.gamma_w),
            "seepage_nodes": [int(i) for i in self.seepage_nodes],
            "converged": bool(self.converged),
            "iterations": int(self.iterations),
            "notes": self._json_safe(self.notes),
        }
        if self.kr is not None:
            d["kr"] = self._round(self.kr)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SeepageResult":
        """Restore the stored fields only.

        The derived fields stay empty until :func:`restore_derived` is
        given the mesh they refer to. A result whose ``pore_pressure`` is
        empty already reads as "no field" everywhere it is consumed
        (``pore_pressure.py`` returns 0.0, the Interpret overlay skips),
        so a half-restored result degrades the way the old missing-field
        case did rather than inventing numbers.
        """
        r = cls()
        r.total_head = [float(v) for v in d.get("total_head", [])]
        kr = d.get("kr")
        r.kr = [float(v) for v in kr] if kr is not None else None
        r.gamma_w = float(d.get("gamma_w", 9.81))
        r.seepage_nodes = [int(i) for i in d.get("seepage_nodes", [])]
        r.converged = bool(d.get("converged", False))
        r.iterations = int(d.get("iterations", 1))
        r.notes = dict(d.get("notes") or {})
        return r


# ======================================================================
def element_fluxes(mesh, props_for, H, kr: Optional[list] = None):
    """Darcy velocity v = -K grad H and |grad H| per element.

    ``props_for(element)`` gives the element's ``HydraulicProperties``,
    ``H`` the nodal total heads and ``kr`` the relative conductivity per
    element (None: saturated). Over a linear triangle the head gradient is
    constant, so the velocity is one vector per element (Darcy 1856; the T3
    formulation of Bathe & Khoshgoftaar 1979).

    v0.1.342 (D337) -- ``SeepageSolver._element_fluxes`` word for word, so
    the core can rebuild a stored field's velocities without the solver.
    The solver calls this.
    """
    vel: list[tuple[float, float]] = []
    grad: list[float] = []
    for e in mesh.elements:
        g = e.shape_gradients(mesh)
        if g is None:
            vel.append((0.0, 0.0))
            grad.append(0.0)
            continue
        dNdx, dNdy, _a = g
        gx = sum(dNdx[k] * H[e.nodes[k]] for k in range(3))
        gy = sum(dNdy[k] * H[e.nodes[k]] for k in range(3))
        kxx, kyy, kxy = props_for(e).conductivity_tensor()
        if kr is not None:
            f = kr[e.id]
            kxx, kyy, kxy = kxx * f, kyy * f, kxy * f
        vx = -(kxx * gx + kxy * gy)
        vy = -(kxy * gx + kyy * gy)
        vel.append((vx, vy))
        grad.append(math.hypot(gx, gy))
    return vel, grad


# ----------------------------------------------------------------------
def restore_derived(result: SeepageResult, mesh, props: Optional[dict]
                    = None) -> SeepageResult:
    """Rebuild the fields ``to_dict`` deliberately did not store.

    Called after loading a project (see ``Project.from_dict``). Mutates
    and returns ``result``.

    ``pressure_head`` and ``pore_pressure`` are closed-form identities:

        P_i = H_i - y_i          u_i = gamma_w * P_i

    so they come back **exactly**, to the last digit written. The element
    fluxes are recomputed with the stored ``kr``, which makes them exact
    too — :func:`element_fluxes` is a deterministic function of the heads,
    the conductivities and kr, and all three survive the save.

    v0.1.342 (D337) -- it built a ``SeepageSolver`` to reach that function,
    which made the core's loader import the solver. The function is here
    now, and the solver calls it.

    Args:
        result: a result restored by :meth:`SeepageResult.from_dict`.
        mesh: the ``Mesh`` the heads were computed on. Node ordering must
            match; it does, because the mesh is stored in the same file
            and is not regenerated on load.
        props: ``material_id -> HydraulicProperties``. Without it the
            velocities cannot be rebuilt, so they are left empty rather
            than computed with a default conductivity that was never
            used — a plausible-looking wrong flow field is worse than no
            flow field. Heads and pore pressures are unaffected.
    """
    n = len(result.total_head)
    if n == 0 or mesh is None:
        return result
    if len(mesh.nodes) != n:
        # A mesh that does not match the field is not a field for this
        # mesh. Say nothing and restore nothing: the analysis guard
        # (`check_analysis_settings`) then reports it the same way it
        # reports a project that was never solved.
        result.notes["restore_error"] = (
            f"mesh has {len(mesh.nodes)} nodes, field has {n}")
        result.total_head = []
        return result
    H = result.total_head
    result.pressure_head = [H[i] - mesh.nodes[i].y for i in range(n)]
    result.pore_pressure = [result.gamma_w * p for p in result.pressure_head]
    if props is None:
        return result
    # the solver's mapping and its fallback, exactly: an unmapped material
    # takes the default properties, as ``SeepageSolver.props_for`` does
    default = HydraulicProperties()
    result.velocity, result.gradient = element_fluxes(
        mesh, lambda e: props.get(e.material_id, default), H, result.kr)
    return result


def hydraulic_props_of(project) -> dict:
    """``material_id -> HydraulicProperties`` for a project.

    One helper because three call sites built the same mapping by hand
    (the driver above, the interface's Compute Groundwater, and now the
    project loader), and a mapping built three ways drifts three ways.
    """
    props: dict = {}
    for m in getattr(project, "materials", []):
        hyd = getattr(m, "hydraulic", None)
        if hyd is not None:
            props[m.id] = hyd
    return props
