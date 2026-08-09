# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Steady-state saturated seepage solver — Phase 2 of the groundwater plan.

Solves the confined/saturated groundwater flow equation over a T3 mesh:

    div( K grad H ) = 0,        H = y + P/gamma_w

with H the total hydraulic head, K the (possibly anisotropic) hydraulic
conductivity tensor per material, and the boundary conditions of the
reference specification:

    TOTAL_HEAD      Dirichlet on H          (value = H)
    PRESSURE_HEAD   Dirichlet on H = y + hp (value = hp)
    ZERO_PRESSURE   Dirichlet on H = y      (value ignored)
    NODAL_FLOW      Neumann, point flux Q at a node   (value = Q)
    INFILTRATION    Neumann, flux q per unit length of a boundary
                    segment, distributed to its two nodes (value = q)
    UNKNOWN         seepage face: P = 0 or Q = 0, resolved iteratively.
                    In Phase 2 (saturated, linear) it behaves as Q = 0;
                    Phase 3 turns it into the real unilateral condition.

Discretisation
--------------
Standard Galerkin FE. For a linear triangle the shape-function gradients
are constant, so the element conductivity matrix is exact in closed form:

    Ke_ij = A * (grad Ni)^T K (grad Nj)

No numerical quadrature is needed, which makes the assembly both fast
and free of integration error (Bathe & Khoshgoftaar, 1979).

The assembled system K H = Q is solved with a sparse direct solver
(``scipy.sparse.linalg.spsolve``), falling back to a dense solve and
finally to a pure-Python Gaussian elimination so the module never hard
-depends on SciPy.

Dirichlet conditions are applied by elimination (row/column zeroing with
the known value carried to the right-hand side), which preserves the
symmetry of the reduced system.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

try:
    from scipy.sparse import csr_matrix as _csr
    from scipy.sparse.linalg import spsolve as _spsolve
except ImportError:  # pragma: no cover
    _csr = None
    _spsolve = None


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
        """
        out = {}
        for k, v in (notes or {}).items():
            try:
                json.dumps(v)
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
class SeepageSolver:
    """Steady-state saturated FE seepage solver over a T3 mesh."""

    def __init__(self, mesh, materials: Optional[dict] = None,
                 gamma_w: float = 9.81,
                 default_props: Optional[HydraulicProperties] = None) -> None:
        """
        Args:
            mesh: an ``ogr_fem2d.mesh.Mesh``.
            materials: mapping ``material_id -> HydraulicProperties``.
                Elements with an unmapped material use ``default_props``.
            gamma_w: unit weight of water (for pore pressure output).
            default_props: fallback properties.
        """
        self.mesh = mesh
        self.materials = materials or {}
        self.gamma_w = gamma_w
        self.default_props = default_props or HydraulicProperties()

    # ------------------------------------------------------------------
    def props_for(self, element) -> HydraulicProperties:
        return self.materials.get(element.material_id, self.default_props)

    # ------------------------------------------------------------------
    def assemble(self, bcs: SeepageBoundaryConditions,
                 kr: Optional[list] = None):
        """Assemble the global conductivity matrix and flux vector.

        Returns ``(rows, cols, vals, q)`` in COO triplet form plus the
        right-hand side, before Dirichlet elimination.
        """
        n = self.mesh.node_count
        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        q = [0.0] * n

        for e in self.mesh.elements:
            g = e.shape_gradients(self.mesh)
            if g is None:
                continue
            dNdx, dNdy, area = g
            kxx, kyy, kxy = self.props_for(e).conductivity_tensor()
            if kr is not None:
                f = kr[e.id]
                kxx, kyy, kxy = kxx * f, kyy * f, kxy * f
            for i in range(3):
                for j in range(3):
                    # (grad Ni)^T K (grad Nj)
                    kij = area * (
                        dNdx[i] * (kxx * dNdx[j] + kxy * dNdy[j])
                        + dNdy[i] * (kxy * dNdx[j] + kyy * dNdy[j])
                    )
                    rows.append(e.nodes[i])
                    cols.append(e.nodes[j])
                    vals.append(kij)

        # Neumann: point fluxes
        for b in bcs.nodes:
            if b.bc_type == BCType.NODAL_FLOW:
                q[b.node_id] += b.value

        # Neumann: infiltration over segments → consistent load q*L/2
        for s in bcs.segments:
            na, nb = self.mesh.nodes[s.node_a], self.mesh.nodes[s.node_b]
            L = math.hypot(nb.x - na.x, nb.y - na.y)
            half = 0.5 * s.q * L
            q[s.node_a] += half
            q[s.node_b] += half

        return rows, cols, vals, q

    # ------------------------------------------------------------------
    def _dirichlet_values(self, bcs: SeepageBoundaryConditions
                          ) -> dict[int, float]:
        """Prescribed total head per node, resolving PRESSURE_HEAD and
        ZERO_PRESSURE into H = y + hp."""
        fixed: dict[int, float] = {}
        for b in bcs.nodes:
            nd = self.mesh.nodes[b.node_id]
            if b.bc_type == BCType.TOTAL_HEAD:
                fixed[b.node_id] = b.value
            elif b.bc_type == BCType.PRESSURE_HEAD:
                fixed[b.node_id] = nd.y + b.value
            elif b.bc_type == BCType.ZERO_PRESSURE:
                fixed[b.node_id] = nd.y
        return fixed

    # ------------------------------------------------------------------
    def solve(self, bcs: SeepageBoundaryConditions,
              kr: Optional[list] = None,
              extra_dirichlet: Optional[dict] = None) -> SeepageResult:
        """Solve one linear steady-state problem.

        ``kr`` optionally scales each element's conductivity (used by the
        unsaturated Picard iteration); ``extra_dirichlet`` adds prescribed
        heads on top of the boundary conditions (used by the seepage-face
        switching, which converts Unknown nodes into P = 0 nodes).
        """
        res = SeepageResult()
        n = self.mesh.node_count
        if n == 0 or not self.mesh.elements:
            res.notes["error"] = "empty mesh"
            return res

        fixed = self._dirichlet_values(bcs)
        if extra_dirichlet:
            fixed.update(extra_dirichlet)
        if not fixed:
            # Pure Neumann problem → head is defined only up to a
            # constant; the system is singular. Report instead of
            # returning a meaningless field.
            res.notes["error"] = (
                "no Dirichlet (head) boundary condition: the problem is "
                "singular. Prescribe Total Head, Pressure Head or Zero "
                "Pressure somewhere on the boundary."
            )
            return res

        rows, cols, vals, q = self.assemble(bcs, kr)
        rows0, cols0, vals0 = list(rows), list(cols), list(vals)
        q0 = list(q)

        # ---- Dirichlet elimination (preserves symmetry) --------------
        # Carry known values to the RHS, then zero the row/column and put
        # 1 on the diagonal.
        for r, c, v in zip(rows, cols, vals):
            if c in fixed and r not in fixed:
                q[r] -= v * fixed[c]
        keep_rows: list[int] = []
        keep_cols: list[int] = []
        keep_vals: list[float] = []
        for r, c, v in zip(rows, cols, vals):
            if r in fixed or c in fixed:
                continue
            keep_rows.append(r)
            keep_cols.append(c)
            keep_vals.append(v)
        for nid, hv in fixed.items():
            keep_rows.append(nid)
            keep_cols.append(nid)
            keep_vals.append(1.0)
            q[nid] = hv

        H = self._linear_solve(keep_rows, keep_cols, keep_vals, q, n)
        if H is None:
            res.notes["error"] = "linear solve failed"
            return res

        res.total_head = list(H)
        res.pressure_head = [H[i] - self.mesh.nodes[i].y for i in range(n)]
        res.pore_pressure = [self.gamma_w * ph for ph in res.pressure_head]
        res.velocity, res.gradient = self._element_fluxes(H, kr)
        # Recorded so the derived fields can be rebuilt after a save.
        # Every result that gets velocities passes through here, saturated
        # or not, so this is the one place that needs to remember.
        res.gamma_w = self.gamma_w
        res.kr = list(kr) if kr is not None else None
        # Nodal reactions at Dirichlet nodes: Q = K.H - q_applied.
        # A negative reaction means water is being forced INTO the
        # domain at that node, which a seepage face cannot do.
        KH = [0.0] * n
        for r, c, v in zip(rows0, cols0, vals0):
            KH[r] += v * H[c]
        res.reactions = [KH[i] - q0[i] for i in range(n)]
        res.converged = True
        res.iterations = 1
        res.notes["dirichlet_nodes"] = len(fixed)
        return res

    # ------------------------------------------------------------------
    def _linear_solve(self, rows, cols, vals, rhs, n):
        """Sparse solve with graceful degradation."""
        if _csr is not None and _spsolve is not None and _np is not None:
            try:
                A = _csr((vals, (rows, cols)), shape=(n, n))
                x = _spsolve(A.tocsc(), _np.asarray(rhs, dtype=float))
                if x is not None and _np.all(_np.isfinite(x)):
                    return [float(v) for v in x]
            except Exception:  # noqa: BLE001
                pass
        # Dense fallback
        if _np is not None:
            try:
                A = _np.zeros((n, n))
                for r, c, v in zip(rows, cols, vals):
                    A[r, c] += v
                x = _np.linalg.solve(A, _np.asarray(rhs, dtype=float))
                return [float(v) for v in x]
            except Exception:  # noqa: BLE001
                pass
        return self._gauss(rows, cols, vals, rhs, n)

    @staticmethod
    def _gauss(rows, cols, vals, rhs, n):
        """Pure-Python Gaussian elimination with partial pivoting."""
        A = [[0.0] * (n + 1) for _ in range(n)]
        for r, c, v in zip(rows, cols, vals):
            A[r][c] += v
        for i in range(n):
            A[i][n] = rhs[i]
        for col in range(n):
            piv = max(range(col, n), key=lambda r: abs(A[r][col]))
            if abs(A[piv][col]) < 1e-300:
                return None
            A[col], A[piv] = A[piv], A[col]
            pv = A[col][col]
            for r in range(col + 1, n):
                f = A[r][col] / pv
                if f == 0.0:
                    continue
                for c in range(col, n + 1):
                    A[r][c] -= f * A[col][c]
        x = [0.0] * n
        for r in range(n - 1, -1, -1):
            s = A[r][n] - sum(A[r][c] * x[c] for c in range(r + 1, n))
            x[r] = s / A[r][r]
        return x

    # ------------------------------------------------------------------
    def _element_fluxes(self, H, kr: Optional[list] = None):
        """Darcy velocity v = -K grad H and |grad H| per element."""
        vel: list[tuple[float, float]] = []
        grad: list[float] = []
        for e in self.mesh.elements:
            g = e.shape_gradients(self.mesh)
            if g is None:
                vel.append((0.0, 0.0))
                grad.append(0.0)
                continue
            dNdx, dNdy, _a = g
            gx = sum(dNdx[k] * H[e.nodes[k]] for k in range(3))
            gy = sum(dNdy[k] * H[e.nodes[k]] for k in range(3))
            kxx, kyy, kxy = self.props_for(e).conductivity_tensor()
            if kr is not None:
                f = kr[e.id]
                kxx, kyy, kxy = kxx * f, kyy * f, kxy * f
            vx = -(kxx * gx + kxy * gy)
            vy = -(kxy * gx + kyy * gy)
            vel.append((vx, vy))
            grad.append(math.hypot(gx, gy))
        return vel, grad

    # ==================================================================
    def flux_through_segment(self, result: SeepageResult,
                             x0: float, y0: float,
                             x1: float, y1: float,
                             samples: int = 200) -> float:
        """Integrate the normal Darcy flux across a straight section —
        the "discharge section" of the reference Interpret view.

        Uses mid-point sampling of the element velocity field along the
        section, which is exact for the piecewise-constant T3 velocity as
        long as the sampling resolves the elements crossed.
        """
        if not result.ok:
            return float("nan")
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-12:
            return 0.0
        # Unit normal (rotate the tangent by +90 deg)
        nx, ny = -dy / L, dx / L
        ds = L / samples
        total = 0.0
        for k in range(samples):
            t = (k + 0.5) / samples
            px, py = x0 + t * dx, y0 + t * dy
            el = self.mesh.locate(px, py)
            if el is None:
                continue
            vx, vy = result.velocity[el.id]
            total += (vx * nx + vy * ny) * ds
        return total


# ======================================================================
def default_boundary_conditions(mesh, project=None
                                ) -> SeepageBoundaryConditions:
    """Default BCs applied when a mesh is generated, mirroring the
    reference behaviour: *Unknown (P = 0 or Q = 0)* on the slope
    (the upper contour) and **zero nodal flow** along the left, right and
    bottom edges of the external boundary.

    Classification is geometric: boundary nodes sitting on the extreme
    left, right or bottom of the mesh bounding box get zero flow; the
    remaining boundary nodes (the ground surface, including the slope
    face) get ``UNKNOWN``.
    """
    bcs = SeepageBoundaryConditions()
    bnd = sorted(mesh.boundary_node_ids())
    if not bnd:
        return bcs
    xs = [mesh.nodes[i].x for i in bnd]
    ys = [mesh.nodes[i].y for i in bnd]
    x_min, x_max = min(xs), max(xs)
    y_min = min(ys)
    tol = max(1e-6, 1e-4 * max(x_max - x_min, 1.0))
    for nid in bnd:
        nd = mesh.nodes[nid]
        on_side = (abs(nd.x - x_min) <= tol or abs(nd.x - x_max) <= tol
                   or abs(nd.y - y_min) <= tol)
        if on_side:
            bcs.add_node(nid, BCType.NODAL_FLOW, 0.0)
        else:
            bcs.add_node(nid, BCType.UNKNOWN, 0.0)
    return bcs


# ======================================================================
def solve_project_seepage(project, bcs: Optional[
        SeepageBoundaryConditions] = None, **mesh_kwargs) -> SeepageResult:
    """Convenience driver: mesh the project (if needed), collect the
    per-material hydraulic properties and solve.

    When ``bcs`` is None the default boundary conditions are used
    (Unknown on the ground surface, zero nodal flow on the sides and
    bottom), which on its own is a singular problem — a head condition
    must be prescribed somewhere, and the solver says so explicitly
    rather than returning a meaningless field.
    """
    mesh = getattr(project, "fem_mesh", None)
    if mesh is None or mesh.element_count == 0:
        from ogr_fem2d.mesh import generate_mesh_for_project
        mesh = generate_mesh_for_project(project, **mesh_kwargs)
        project.fem_mesh = mesh
    props: dict = {}
    for m in getattr(project, "materials", []):
        hyd = getattr(m, "hydraulic", None)
        if hyd is not None:
            props[m.id] = hyd
    gamma_w = 9.81
    try:
        gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    except Exception:  # noqa: BLE001
        pass
    solver = SeepageSolver(mesh, props, gamma_w=gamma_w)
    if bcs is None:
        bcs = default_boundary_conditions(mesh, project)
    return solver.solve(bcs)


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
    too — ``_element_fluxes`` is a deterministic function of the heads,
    the conductivities and kr, and all three survive the save.

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
    solver = SeepageSolver(mesh, props, gamma_w=result.gamma_w)
    result.velocity, result.gradient = solver._element_fluxes(H, result.kr)
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


# ======================================================================
class UnsaturatedSeepageSolver(SeepageSolver):
    """Steady-state **saturated/unsaturated** seepage with a free surface
    and seepage faces — Phase 3 of the groundwater plan.

    Two coupled non-linearities are resolved simultaneously:

    1. **k(psi)** — the conductivity of every element depends on the
       matric suction, which depends on the solution. Handled by **Picard
       iteration** with under-relaxation: at each step the element
       suction is evaluated from the current heads, the relative
       permeabilities are updated, the linear system is re-solved, and the
       new heads are blended with the old ones,

           H <- (1 - w) H_old + w H_new,

       with ``w = relaxation``. Under-relaxation is what makes the scheme
       robust when the permeability function is steep (sands), where a
       plain fixed-point iteration oscillates.

    2. **Seepage face** — ``UNKNOWN`` boundary nodes obey the unilateral
       (Signorini) condition "P = 0 **or** Q = 0": water may leave the
       domain but not enter, and where it leaves the pressure must be
       atmospheric. Resolved by the classical **nodal switching**
       algorithm (Neuman, 1973; Bathe & Khoshgoftaar, 1979):

           * a free (Q = 0) node whose computed pressure head becomes
             positive is switched to Dirichlet P = 0 (H = y);
           * a switched node whose nodal reaction indicates inflow
             (water being pushed *into* the domain, which is
             unphysical) is released back to Q = 0.

       The active set is updated once per Picard step; convergence
       requires both the head change and the active set to settle.

    The free surface itself is not tracked as a moving mesh boundary:
    with this formulation it is simply the P = 0 iso-line of the
    converged solution, which is the standard fixed-mesh approach and
    avoids re-meshing altogether.
    """

    def __init__(self, *args, relaxation: float = 0.5,
                 max_iterations: int = 200, tolerance: float = 1e-4,
                 max_node_switches: int = 3,
                 switch_pressure_tol: float = 0.0,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.relaxation = min(max(relaxation, 0.05), 1.0)
        self.max_iterations = max(1, max_iterations)
        self.tolerance = tolerance
        # Anti-chatter budget for the seepage-face switching
        self.max_node_switches = max(1, max_node_switches)
        # Hysteresis band on the pressure-head decision; 0 → derived
        # from the mesh size in solve_unsaturated()
        self.switch_pressure_tol = switch_pressure_tol

    # ------------------------------------------------------------------
    def _element_kr(self, H: list) -> list:
        """Relative permeability per element from the current heads.

        The element suction is taken from the mean nodal pressure head,
        which for a T3 (linear P) is the value at the centroid — the
        natural single point for a constant-conductivity element.
        """
        kr = []
        for e in self.mesh.elements:
            p_mean = 0.0
            for nid in e.nodes:
                p_mean += H[nid] - self.mesh.nodes[nid].y
            p_mean /= 3.0
            suction = -p_mean          # positive where P < 0
            kr.append(self.props_for(e).relative_permeability(suction))
        return kr

    # ------------------------------------------------------------------
    def solve_unsaturated(self, bcs: SeepageBoundaryConditions
                          ) -> SeepageResult:
        """Picard iteration with seepage-face nodal switching."""
        n = self.mesh.node_count
        if n == 0 or not self.mesh.elements:
            res = SeepageResult()
            res.notes["error"] = "empty mesh"
            return res

        unknown = [b.node_id for b in bcs.nodes
                   if b.bc_type == BCType.UNKNOWN]
        unknown += [b.node_id for b in bcs.nodes if b.seepage_face]
        unknown = sorted(set(unknown))

        # ---- initial guess: linear (saturated) solve -----------------
        first = super().solve(bcs)
        if not first.converged:
            return first
        H = list(first.total_head)
        active: set[int] = set()      # Unknown nodes switched to P = 0
        switches: dict[int, int] = {}
        # Hysteresis bands. The pressure band scales with the element
        # size (a sub-element pressure change is not a real switch); the
        # flux band scales with the total Dirichlet throughput so it is
        # dimensionally consistent across permeabilities.
        p_tol = (self.switch_pressure_tol
                 or 0.02 * max(self.mesh.target_size, 1e-9))
        q_scale = max((abs(r) for r in first.reactions), default=0.0)
        q_tol = 1e-3 * q_scale if q_scale > 0 else 1e-14
        history: list[float] = []
        converged = False
        it = 0

        for it in range(1, self.max_iterations + 1):
            kr = self._element_kr(H)
            extra = {nid: self.mesh.nodes[nid].y for nid in active}
            step = super().solve(bcs, kr=kr, extra_dirichlet=extra)
            if not step.converged:
                res = SeepageResult()
                res.notes["error"] = (
                    f"linear solve failed at Picard iteration {it}")
                res.iterations = it
                return res

            H_new = step.total_head
            w = self.relaxation
            H_relaxed = [(1.0 - w) * H[i] + w * H_new[i] for i in range(n)]
            delta = max(abs(H_relaxed[i] - H[i]) for i in range(n))
            H = H_relaxed
            history.append(delta)

            # ---- seepage-face switching -----------------------------
            # Reaction sign convention (verified empirically against a
            # 1D case): POSITIVE reaction = water entering the domain at
            # that node. A seepage face cannot admit water, so a node
            # held at P = 0 whose reaction turns positive must be
            # released back to Q = 0.
            #
            # Plain switching chatters (the active set flips 2->1->0->2
            # indefinitely and the heads never settle), which is the
            # classical difficulty of the nodal-switching algorithm. Two
            # standard cures are applied: a hysteresis band on both
            # decisions, and a per-node switch budget after which the
            # node is frozen in its current state so the active set is
            # guaranteed to settle.
            new_active = set(active)
            for nid in unknown:
                if switches.get(nid, 0) >= self.max_node_switches:
                    continue                      # frozen
                y = self.mesh.nodes[nid].y
                if nid in active:
                    q_node = (step.reactions[nid]
                              if step.reactions else 0.0)
                    if q_node > q_tol:            # inflow → release
                        new_active.discard(nid)
                        switches[nid] = switches.get(nid, 0) + 1
                else:
                    if H[nid] - y > p_tol:        # positive P → hold at 0
                        new_active.add(nid)
                        switches[nid] = switches.get(nid, 0) + 1
            set_changed = (new_active != active)
            active = new_active

            if delta < self.tolerance and not set_changed:
                converged = True
                break

        # ---- final consistent state ---------------------------------
        kr = self._element_kr(H)
        extra = {nid: self.mesh.nodes[nid].y for nid in active}
        final = super().solve(bcs, kr=kr, extra_dirichlet=extra)
        if not final.converged:
            final.notes["error"] = "final solve failed"
            return final
        final.converged = converged
        final.iterations = it
        final.seepage_nodes = sorted(active)
        final.notes["picard_delta"] = history[-1] if history else float("nan")
        final.notes["relaxation"] = self.relaxation
        final.notes["kr_min"] = min(kr) if kr else 1.0
        final.notes["kr_max"] = max(kr) if kr else 1.0
        if not converged:
            final.notes["warning"] = (
                f"Picard iteration did not converge in "
                f"{self.max_iterations} steps (last change "
                f"{history[-1]:.3e} m). Try a smaller relaxation factor "
                f"or a finer mesh.")
        return final

    # ------------------------------------------------------------------
    def free_surface_points(self, result: SeepageResult,
                            samples: int = 120) -> list:
        """Trace the free surface as the P = 0 iso-line, returned as
        (x, y) samples ordered by x.

        For each of ``samples`` vertical scan lines the highest point
        where the pressure head changes sign is located by linear
        interpolation along mesh element edges.
        """
        if not result.ok:
            return []
        P = result.pressure_head
        xs = [nd.x for nd in self.mesh.nodes]
        x_min, x_max = min(xs), max(xs)
        out: list[tuple[float, float]] = []
        # Collect sign-changing edges once
        seg: list[tuple[float, float]] = []
        for key in self.mesh.edge_map():
            a, b = key
            pa, pb = P[a], P[b]
            if (pa > 0.0) == (pb > 0.0):
                continue
            na, nb = self.mesh.nodes[a], self.mesh.nodes[b]
            t = pa / (pa - pb) if abs(pa - pb) > 1e-30 else 0.5
            seg.append((na.x + t * (nb.x - na.x),
                        na.y + t * (nb.y - na.y)))
        if not seg:
            return []
        # Keep the highest crossing per scan column
        width = max(x_max - x_min, 1e-9)
        buckets: dict[int, tuple[float, float]] = {}
        for (px, py) in seg:
            k = int(samples * (px - x_min) / width)
            cur = buckets.get(k)
            if cur is None or py > cur[1]:
                buckets[k] = (px, py)
        for k in sorted(buckets):
            out.append(buckets[k])
        return out


# ======================================================================
@dataclass
class TransientStage:
    """One stage of a transient groundwater analysis."""

    time: float = 0.0
    calculate_sf: bool = False
    label: str = ""
    bcs: Optional[SeepageBoundaryConditions] = None

    def to_dict(self) -> dict:
        return {"time": self.time, "calculate_sf": self.calculate_sf,
                "label": self.label,
                "bcs": self.bcs.to_dict() if self.bcs else None}

    @classmethod
    def from_dict(cls, d: dict) -> "TransientStage":
        bcs = d.get("bcs")
        return cls(time=float(d.get("time", 0.0)),
                   calculate_sf=bool(d.get("calculate_sf", False)),
                   label=str(d.get("label", "")),
                   bcs=SeepageBoundaryConditions.from_dict(bcs)
                   if bcs else None)


class TransientSeepageSolver(UnsaturatedSeepageSolver):
    """Transient saturated/unsaturated seepage — Phase 6.

    Solves the time-dependent Richards equation in **mixed form**

        d(theta)/dt = div( K(psi) grad H ),        H = y + P

    discretised in space by Galerkin FE (as in Phases 2-3) and in time by
    **backward Euler** (fully implicit, unconditionally stable), with two
    measures the literature identifies as essential for this equation:

    **Modified Picard iteration** (Celia, Bouloutas & Zarba, 1990). The
    naive pressure-head form of Richards' equation suffers large mass
    balance errors. Writing the storage term in mixed form and iterating

        [ M C^m / dt + K^m ] H^(m+1)
              = Q + M C^m / dt H^m - M (theta^m - theta^n) / dt

    keeps the accumulated water mass consistent with the fluxes, because
    the theta difference is carried explicitly rather than being replaced
    by C dH.

    **Mass lumping** of the storage matrix M (row-summed to a diagonal).
    A consistent mass matrix produces oscillatory pressure profiles near
    sharp wetting fronts; lumping suppresses them and improves both
    convergence and the mass balance.

    Storage coefficient per node: the specific moisture capacity
    C = d(theta)/dh in the unsaturated zone, and the elastic specific
    storage Ss below the water table (where d(theta)/dh = 0 and the
    system would otherwise be singular in time).

    Seepage faces keep working exactly as in Phase 3: the nodal switching
    is applied inside every time step.

    Author: Samuel Sáez López (UPCT)
    """

    def __init__(self, *args, time_steps: int = 0,
                 max_picard: int = 30, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # 0 → automatic number of time steps per stage
        self.time_steps = max(0, int(time_steps))
        self.max_picard = max(1, int(max_picard))

    # ------------------------------------------------------------------
    def _lumped_mass(self) -> list:
        """Row-summed (lumped) mass matrix: for a T3 each node receives
        one third of every element area it belongs to."""
        m = [0.0] * self.mesh.node_count
        for e in self.mesh.elements:
            a3 = e.area(self.mesh) / 3.0
            for nid in e.nodes:
                m[nid] += a3
        return m

    def _node_props(self):
        """Hydraulic properties per node, averaged over the elements
        sharing it (properties are defined per material/element)."""
        out: list = [None] * self.mesh.node_count
        for e in self.mesh.elements:
            p = self.props_for(e)
            for nid in e.nodes:
                if out[nid] is None:
                    out[nid] = p
        return out

    # ------------------------------------------------------------------
    def step(self, bcs: SeepageBoundaryConditions, H_old: list,
             dt: float, active: Optional[set] = None):
        """Advance one time step of size ``dt`` from ``H_old``.

        Returns ``(H_new, active_set, converged, iterations, result)``.
        """
        n = self.mesh.node_count
        mass = self._lumped_mass()
        nprops = self._node_props()
        ys = [nd.y for nd in self.mesh.nodes]

        # Generalised stored-water content at the previous time level.
        # Using storage_content (not water_content) is what keeps the
        # ELASTIC storage alive in the saturated zone, where theta is
        # constant and the plain mixed form would degenerate to the
        # steady-state equation.
        theta_old = []
        for i in range(n):
            p = nprops[i]
            theta_old.append(p.storage_content(H_old[i] - ys[i])
                             if p else 0.0)

        active = set(active or ())
        unknown = sorted({b.node_id for b in bcs.nodes
                          if b.bc_type == BCType.UNKNOWN}
                         | {b.node_id for b in bcs.nodes if b.seepage_face})
        H = list(H_old)
        switches: dict[int, int] = {}
        p_tol = (self.switch_pressure_tol
                 or 0.02 * max(self.mesh.target_size, 1e-9))
        converged = False
        it = 0
        step_result = None

        for it in range(1, self.max_picard + 1):
            kr = self._element_kr(H)
            # Storage and mixed-form correction, both lumped
            extra_q = [0.0] * n
            diag = [0.0] * n
            for i in range(n):
                p = nprops[i]
                if p is None:
                    continue
                ph = H[i] - ys[i]
                cap = p.storage_at(ph)
                coef = mass[i] * cap / dt
                diag[i] = coef
                theta_m = p.storage_content(ph)
                extra_q[i] = (coef * H[i]
                              - mass[i] * (theta_m - theta_old[i]) / dt)

            extra_dirichlet = {nid: ys[nid] for nid in active}
            step_result = self._solve_linear_step(
                bcs, kr, extra_dirichlet, diag, extra_q)
            if step_result is None or not step_result.converged:
                return H, active, False, it, step_result

            H_new = step_result.total_head
            w = self.relaxation
            H_rel = [(1.0 - w) * H[i] + w * H_new[i] for i in range(n)]
            delta = max(abs(H_rel[i] - H[i]) for i in range(n))
            H = H_rel

            # Seepage-face switching (same convention as Phase 3:
            # POSITIVE reaction = water entering the domain)
            new_active = set(active)
            for nid in unknown:
                if switches.get(nid, 0) >= self.max_node_switches:
                    continue
                if nid in active:
                    q_node = (step_result.reactions[nid]
                              if step_result.reactions else 0.0)
                    if q_node > 1e-12:
                        new_active.discard(nid)
                        switches[nid] = switches.get(nid, 0) + 1
                elif H[nid] - ys[nid] > p_tol:
                    new_active.add(nid)
                    switches[nid] = switches.get(nid, 0) + 1
            changed = new_active != active
            active = new_active

            if delta < self.tolerance and not changed:
                converged = True
                break

        return H, active, converged, it, step_result

    # ------------------------------------------------------------------
    def _solve_linear_step(self, bcs, kr, extra_dirichlet, diag, extra_q):
        """One linear solve with the storage terms added to the diagonal
        and to the right-hand side."""
        n = self.mesh.node_count
        rows, cols, vals, q = self.assemble(bcs, kr)
        for i in range(n):
            if diag[i] != 0.0:
                rows.append(i)
                cols.append(i)
                vals.append(diag[i])
            q[i] += extra_q[i]

        fixed = self._dirichlet_values(bcs)
        if extra_dirichlet:
            fixed.update(extra_dirichlet)
        if not fixed:
            # Transient problems are well posed without Dirichlet data
            # (storage regularises them), so this is allowed here.
            fixed = {}

        rows0, cols0, vals0 = list(rows), list(cols), list(vals)
        q0 = list(q)
        for r, c, v in zip(rows, cols, vals):
            if c in fixed and r not in fixed:
                q[r] -= v * fixed[c]
        kr_, kc_, kv_ = [], [], []
        for r, c, v in zip(rows, cols, vals):
            if r in fixed or c in fixed:
                continue
            kr_.append(r)
            kc_.append(c)
            kv_.append(v)
        for nid, hv in fixed.items():
            kr_.append(nid)
            kc_.append(nid)
            kv_.append(1.0)
            q[nid] = hv

        H = self._linear_solve(kr_, kc_, kv_, q, n)
        if H is None:
            return None
        res = SeepageResult()
        res.total_head = list(H)
        res.pressure_head = [H[i] - self.mesh.nodes[i].y for i in range(n)]
        res.pore_pressure = [self.gamma_w * p for p in res.pressure_head]
        res.velocity, res.gradient = self._element_fluxes(H, kr)
        res.gamma_w = self.gamma_w          # see SeepageResult.to_dict
        res.kr = list(kr) if kr is not None else None
        KH = [0.0] * n
        for r, c, v in zip(rows0, cols0, vals0):
            KH[r] += v * H[c]
        res.reactions = [KH[i] - q0[i] for i in range(n)]
        res.converged = True
        return res

    # ------------------------------------------------------------------
    def stored_water(self, H: list) -> float:
        """Total water volume stored in the domain for a head field —
        used to verify the global mass balance."""
        nprops = self._node_props()
        mass = self._lumped_mass()
        total = 0.0
        for i, nd in enumerate(self.mesh.nodes):
            p = nprops[i]
            if p is None:
                continue
            total += mass[i] * p.storage_content(H[i] - nd.y)
        return total

    # ------------------------------------------------------------------
    def solve_transient(self, stages: list, initial_head: Optional[list] = None,
                        initial_bcs: Optional[SeepageBoundaryConditions] = None,
                        ) -> list:
        """Run a staged transient analysis.

        ``stages`` is a list of :class:`TransientStage` with increasing
        times; each stage may carry its own boundary conditions (falling
        back to ``initial_bcs``). The initial head field may be given
        directly, or is otherwise obtained from a steady-state run with
        ``initial_bcs`` — matching the reference, which allows ANY
        groundwater method to define the initial conditions.

        Returns one :class:`SeepageResult` per stage, each annotated with
        the stage time, the number of time steps used and the mass
        balance error.
        """
        if not stages:
            return []
        base_bcs = initial_bcs or (stages[0].bcs
                                   or SeepageBoundaryConditions())

        if initial_head is not None:
            H = list(initial_head)
        else:
            steady = super().solve_unsaturated(base_bcs)
            if not steady.total_head:
                out = SeepageResult()
                out.notes["error"] = "initial steady state failed"
                return [out]
            H = list(steady.total_head)

        results: list = []
        active: set = set()
        t_prev = 0.0
        for k, stage in enumerate(stages):
            bcs = stage.bcs or base_bcs
            span = max(stage.time - t_prev, 0.0)
            if span <= 0.0:
                res = SeepageResult()
                res.total_head = list(H)
                res.pressure_head = [H[i] - self.mesh.nodes[i].y
                                     for i in range(len(H))]
                res.pore_pressure = [self.gamma_w * p
                                     for p in res.pressure_head]
                res.gamma_w = self.gamma_w   # a zero-span stage still has
                res.converged = True         # to survive a save
                res.notes.update({"stage": k, "time": stage.time,
                                  "time_steps": 0})
                results.append(res)
                continue

            nsteps = self.time_steps or self._auto_time_steps(span)
            dt = span / nsteps
            w0 = self.stored_water(H)
            all_ok = True
            iters = 0
            last = None
            for _ in range(nsteps):
                H, active, ok, it, last = self.step(bcs, H, dt, active)
                iters += it
                all_ok = all_ok and ok
            if last is None:
                last = SeepageResult()
                last.notes["error"] = "no time step computed"
                results.append(last)
                t_prev = stage.time
                continue
            last.converged = all_ok
            last.iterations = iters
            last.seepage_nodes = sorted(active)
            w1 = self.stored_water(H)
            last.notes.update({
                "stage": k, "time": stage.time, "dt": dt,
                "time_steps": nsteps,
                "stored_water": w1,
                "storage_change": w1 - w0,
                "calculate_sf": stage.calculate_sf,
            })
            if not all_ok:
                last.notes["warning"] = (
                    f"stage {k}: some time steps did not converge; try "
                    f"more time steps or a smaller relaxation factor")
            results.append(last)
            t_prev = stage.time
        return results

    # ------------------------------------------------------------------
    def _auto_time_steps(self, span: float) -> int:
        """Automatic number of time steps for a stage.

        Uses a diffusion-style criterion: the step is limited so that the
        water front cannot cross more than about one element per step,
        which is what keeps the non-linear iteration well conditioned.
        The result is clamped to a practical range.
        """
        h = max(self.mesh.target_size, 1e-9)
        k_max = 1e-12
        c_min = 1.0
        for e in self.mesh.elements:
            p = self.props_for(e)
            k_max = max(k_max, p.ks)
            c_min = min(c_min, max(p.storage_at(-1.0), 1e-9))
        # characteristic diffusion time over one element
        t_elem = c_min * h * h / max(k_max, 1e-30)
        if t_elem <= 0 or not math.isfinite(t_elem):
            return 10
        return int(min(200, max(4, math.ceil(span / t_elem))))
