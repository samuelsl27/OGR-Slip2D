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
from ogr_core.messages import as_nested
from ogr_core.progress import checkpoint

from .. import messages as M
# v0.1.342 (D337) -- the stored data and the identities that rebuild it are
# the core's (``ogr_core.fem.seepage_data``); every name is re-exported here.
from ogr_core.fem.seepage_data import (  # noqa: F401
    BCType,
    NodeBC,
    SeepageBoundaryConditions,
    SeepageResult,
    SegmentBC,
    _change_series,
    _finite_or_none,
    element_fluxes,
    hydraulic_props_of,
    restore_derived,
)

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

try:
    from scipy.sparse import csr_matrix as _csr
    from scipy.sparse.linalg import splu as _splu
    from scipy.sparse.linalg import spsolve as _spsolve
except ImportError:  # pragma: no cover
    _csr = None
    _splu = None
    _spsolve = None


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
        self._degenerate: Optional[int] = None
        self._unmapped: Optional[int] = None

    # ------------------------------------------------------------------
    def _note_degenerate(self, res: SeepageResult) -> None:
        """v0.1.271 (D270) — say so when the mesh has flat elements.

        The generator repairs them since this version, but a mesh saved by
        an earlier one travels in the .ogr. They are reported and NOT
        skipped: removing one can leave a node with no element in its
        region, and the fix is to regenerate the mesh, which is what the
        warning says. A mesh without them gets no note at all."""
        if self._degenerate is None:
            self._degenerate = (len(self.mesh.degenerate_elements())
                                if hasattr(self.mesh, "degenerate_elements")
                                else 0)
        if self._degenerate:
            res.notes["degenerate_elements"] = self._degenerate
            res.notes["mesh_warning"] = M.seepage_note(
                M.MESH_FLAT, n=self._degenerate)

    def _note_default_props(self, res: SeepageResult) -> None:
        """v0.1.280 (D284) — say how many elements are solved with
        ``default_props`` because their material is not in the mapping the
        solver was given. The project's doors refuse a mesh whose materials
        no longer exist (``rules.mesh_mismatch``); this is for whoever builds
        the solver directly — a script, a measurement — where a mesh of one
        project with the properties of another was computed in silence (a
        D274 measurement came out all saturated that way). A mesh whose
        elements are all mapped gets no note."""
        if self._unmapped is None:
            self._unmapped = sum(1 for e in self.mesh.elements
                                 if e.material_id not in self.materials)
        if self._unmapped:
            res.notes["default_props_elements"] = self._unmapped

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
            res.notes["error"] = M.seepage_note(M.EMPTY_MESH)
            return res
        # before any early return: a node that only flat elements touch
        # makes the system singular, and that failure needs this reason
        self._note_degenerate(res)
        self._note_default_props(res)

        fixed = self._dirichlet_values(bcs)
        if extra_dirichlet:
            fixed.update(extra_dirichlet)
        if not fixed:
            # Pure Neumann problem → head is defined only up to a
            # constant; the system is singular. Report instead of
            # returning a meaningless field.
            res.notes["error"] = M.seepage_note(M.NO_DIRICHLET)
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
            res.notes["error"] = M.seepage_note(M.LINEAR_FAILED)
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
        # Nodal reactions at Dirichlet nodes: Q = K.H - q_applied, the
        # flow the prescribed head has to SUPPLY there. Positive is water
        # entering the domain at that node, which a seepage face cannot
        # do; negative is water leaving. v0.1.266 — this said the
        # opposite, and the switching below always read it this way: a
        # column draining through a head-fixed base gives -I x width.
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
        """Darcy velocity v = -K grad H and |grad H| per element.

        v0.1.342 (D337) -- the loop is :func:`element_fluxes` in the core,
        which the project's loader calls without the solver."""
        return element_fluxes(self.mesh, self.props_for, H, kr)

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


#: v0.1.266 (D124) -- when the Picard loop of ``solve_unsaturated`` ends
#: without converging, two other roads to the SAME fixed point are tried
#: before the run is reported unconverged (``_rescue``): Anderson
#: acceleration of the very Picard map, then continuation in the steepness
#: of the permeability functions solved by Newton's method.
#:
#: Why: a permeability function that drops many decades over a fraction of
#: a metre makes the Picard map of a fine mesh cycle for ever. Measured on
#: dam 2 of the groundwater verification problem 9 (Bowles 1984), whose
#: toe-drain curve falls six decades between 8 and 12 kPa: the 946-element
#: mesh converges in 68 passes, the 3883-element one runs into a period-4
#: cycle of five to seven drain elements (successive increments at cosine
#: -1.000, unrelaxed change 2.6-3.0 m) and no relaxation breaks it; a 1-D
#: column under the same kind of curve fails for every relaxation from 0.2
#: to 0.6. Anderson converges on the dam and not on the column; Newton with
#: continuation converges on both; all of them land on one fixed point
#: (3.76148e-6 m3/(min m) through the dam, 1.0 % from Bowles' flow net).
#:
#: The rescue runs ONLY after the loop has failed, so every model that
#: converges today goes through exactly the arithmetic it went through
#: before. Off, the v0.1.265 behaviour. Since v0.1.358 (D356) "failed"
#: includes a loop that stops with the seepage face unsettled
#: (``LOOP_SETTLED_FACE``).
PICARD_RESCUE = True

#: v0.1.283 (D279) — the seepage face's switch budget, when not given,
#: scales with the relaxation: max(25, ceil(10/w))
#: (``UnsaturatedSeepageSolver.max_node_switches``). With w >= 0.4 it is the
#: 25 it always was; a slower relaxation no longer freezes a node of the
#: face before the iterate has settled. Switch off to rebuild 0.1.282.
SWITCH_BUDGET_SCALES_WITH_OMEGA = True

#: v0.1.284 (D280) — the hysteresis bands of the seepage-face switching are
#: ten times narrower: a free node is held at P = 0 when its pressure exceeds
#: 0.002 h (was 0.02 h) and a held node is released when its inflow exceeds
#: 1e-4 of the largest nodal flux of the first solve (was 1e-3), in the steady
#: solver and in every transient step (one rule since D269). With the old
#: bands more than one face set was admissible, and w or the path (loop or
#: rescue) picked a different one: 4 of the 53 steady rows of the bank landed
#: 1 to 24 mm apart. Measured with the narrow bands (_auditoria/P6_0284 of the
#: bank): three of those rows give one face for w from 0.2 to 0.8 (heads
#: within 4e-5 m), the fourth two sets 2 mm apart; Charnyi's discharge is
#: unchanged (1.772 %); the 58 rows of the bank converge as before, with the
#: same rescues and passes within four, and the door's answer moves within
#: its old band (05-001 1 cm, 02-038 up to 2 mm, the transient 05-018 1.9 cm). The bands exist
#: against chatter (v0.1.125); the rescue stays behind them. Switch off to
#: rebuild 0.1.283.
FACE_BANDS_TIGHT = True

#: Anderson depths tried in turn, and the map evaluations allowed to each.
#: Neither depth wins everywhere: on that dam, started after 200 Picard
#: passes, depth 20 needs 36 evaluations and depth 5 166; started after
#: 30, depth 5 needs 52 and depth 20 does not converge in 150.
RESCUE_ANDERSON_DEPTHS = (5, 20)
RESCUE_ANDERSON_EVALUATIONS = 150
#: Newton iterations allowed to the whole continuation (the dam above
#: needs 436 over 22 steps of t) and to one step of it.
RESCUE_NEWTON_BUDGET = 1000
RESCUE_NEWTON_PER_STEP = 30
#: Smallest continuation step before the continuation gives up.
RESCUE_MIN_STEP = 1e-3

#: v0.1.356 (D285) -- a road of the rescue is accepted only when its answer
#: also settles the seepage face (``_unsettled_nodes``); a road that reaches
#: the tolerance with the face unsettled is set aside and the next road is
#: tried (``_rescue``). Each road starts a switch budget of its own and may
#: freeze a node of the face in the wrong state; until 0.1.355 that road was
#: accepted, the final check of ``solve_unsaturated`` reported the face
#: unsettled, and the roads after it were never tried. Measured on problem 4
#: of the groundwater verification bank (the toe-drain dam of Harr 1990)
#: with permeability curves of six decades over 0.5 kPa: in the four cases
#: where a road was accepted with one to four nodes taking water in or free
#: under pressure, the continuation settles the face. In three of them
#: another road reaches the same fixed point (the loop alone, within 2e-6 m;
#: the second Anderson depth at w = 0.25, within 6e-7 m); in all four the
#: face ends 0.18-0.19 m from the toe (Casagrande's correction gives 0.172)
#: where the accepted road had it up to 0.49 m. Over the 53 unsaturated
#: steady rows of the bank, with w from 0.2 to 0.8, no road is set aside.
#: When no road settles the face, the state published is the first one set
#: aside -- the one 0.1.355 published -- and the face is reported unsettled
#: (after a loop that stopped with the face unsettled, the loop's own state:
#: ``LOOP_SETTLED_FACE``). Switch off to rebuild 0.1.355.
RESCUE_SETTLED_FACE = True

#: v0.1.358 (D356) -- a Picard loop that stops with the seepage face
#: unsettled has not converged, and the rescue runs.
#:
#: The loop stops when the relaxed change is below the tolerance and the
#: face set has stopped changing. A node frozen by the switch budget cannot
#: change the set, so the loop could stop with a frozen node held at P = 0
#: and water going in; the final check of ``solve_unsaturated`` reported the
#: face unsettled, and the rescue, which ran only after a loop that failed,
#: was never tried. Switched on, the loop's final state is asked before the
#: loop is believed (the very solve the end publishes, computed once). When
#: its face is unsettled the rescue runs with Anderson started from the
#: loop's face WITHOUT its frozen nodes, the ones the loop could not revise;
#: a road that settles the face is published, and if none does the loop's
#: own state is, as 0.1.357 published it, with the rescue reported "failed".
#:
#: Measured in the groundwater verification bank (_auditoria/P6_0358):
#: dam 2 of problem 9 (Bowles 1984, the toe-drain dam of Chapuis et al.
#: 2001) on the generator's 1000-element mesh, solved with the groundwater
#: door's settings (w = 0.4, 200 passes, tolerance 1e-5), stopped with a
#: node of the downstream face, in the drain, held while water went in at
#: 35 times the flow through the dam, and came out unconverged, with no
#: discharge and the free surface 3 to 4 m high; rescued, its discharge is
#: 4.2105e-6 m3/(min m), 0.46 % below the 4.23e-6 published. Of the 255 steady
#: unsaturated runs of the bank (51 rows, w from 0.2 to 0.8) only that dam
#: at w = 0.4, 0.6 and 0.8 moves; the other 252 are identical to the bit.
#: In 14 cases forced with a starved budget the rescue reaches the
#: reference fixed point in 10 and falls back to the loop's state in 4;
#: started from the loop's face as it was, it published as converged once
#: another face admissible within the bands, 4.2 cm off at a node held in
#: dry ground. Switch off to rebuild 0.1.357.
LOOP_SETTLED_FACE = True

#: v0.1.359 (D364) -- the flux band of the seepage face scales with a flow
#: that exists.
#:
#: The band is 1e-4 of the largest nodal flux of the first, saturated,
#: solve (``_face_q_tol``). When every prescribed head is one level and no
#: flux is applied -- a dam that drains only through its seepage face --
#: that solve is the level itself and carries no flow, and the band was
#: round-off: 5e-24 on the dam of problem 102 without its tailwater, whose
#: face carries 1.3e-6. Any positive round-off reaction then released a
#: held node or counted it unsettled. Switched on, such a model takes the
#: scale from the first solve of the loop with the face held, before the
#: switching that reads it (the band is read only for held nodes), as each
#: transient step does since D269 (``TRANSIENT_FACE_RULE``).
#:
#: Measured on the groundwater verification bank (_auditoria/P6_0359): 60
#: of the 255 steady unsaturated runs (12 rows, w from 0.2 to 0.8) are of
#: this kind. In them the new scale is 0.9 to 65 times the largest nodal
#: flux of the answer (65 on the toe-drain dam 2 of problem 9, whose drain
#: carries the whole face in the second pass), and none of their 6854
#: decisions that read the band had a flux below 1e-4 of that of the
#: answer. 254 runs are identical to the bit; one (problem 11 on the
#: coarse mesh, w = 0.3) keeps held a node the old band released at 1.9e-4
#: of the final flux, and lands on the same face 2.3e-8 m off. The rescue
#: failing on dam 2 of problem 9 on a fine mesh (D365) is not this (see
#: ``_rescue``). Switch off to rebuild 0.1.358.
FACE_FLUX_SCALE_FROM_FLOW = True

#: v0.1.362 (D367) -- when the continuation of the rescue stops on its
#: smallest step, the rescue follows the path of solutions on from the last
#: state it accepted, piece by piece across the kinks of the permeability
#: curves (``_piecewise_path``; Allgower & Georg 1990). With User Defined
#: curves the continuation can stop at a fold of the path that sits on a
#: kink, where no one-sided Jacobian turns singular and continuation in t
#: cannot pass (D366). The path is followed with no Newton budget of its
#: own, by the owner's decision: it ends at t = 1, or as a piecewise-linear
#: algorithm ends (its smallest step, a tangent that does not enter the next
#: piece, t below 0). With other permeability models it does not run, and
#: the rescue says so (``seepage.picard_rescue_piecewise_na``).
#:
#: Measured on dam 2 of problem 9 of the groundwater verification bank,
#: whose two finest meshes failed with the door's settings
#: (_auditoria/P6_0362): from where the continuation stops, from the state
#: before it and from t = 0 the path is one, a Z with three folds on the
#: drain's kink at 9.8 kPa and one smooth fold, and it reaches the answer
#: already known: 7.8e-7 m from the bank's on 3886 elements and 3.1e-7 m
#: from the one Anderson finds on 3691, the discharge -1.44 % and -1.39 %
#: of the published one. It costs 1242 to 1433 Newton iterations (some 720
#: kinks crossed, most of them three times along the Z), about 30 s; the
#: continuation's budget leaves 734 to 749. It runs only where the
#: continuation stopped on its smallest step: over the 255 steady
#: unsaturated runs of the bank (w from 0.2 to 0.8), on the three runs of
#: that dam's x4 mesh that failed, which now converge; the other 252 are
#: identical to the bit, as are the three meshes of that dam that converged
#: with the door. Switch off to rebuild 0.1.361.
RESCUE_PIECEWISE_PATH = True

#: v0.1.274 (D269) — the seepage face of a transient time step follows the
#: steady solver's rule (``_switch_seepage_face``) instead of its own copy.
#:
#: ``TransientSeepageSolver.step`` carried an inline copy of the switching
#: loop that released a node held at P = 0 when its reaction exceeded an
#: ABSOLUTE 1e-12, while the steady solver uses q_tol = 1e-3 times the
#: largest nodal flux. Permeabilities on the verification bank run from
#: 1e-13 to 1e-4: an absolute flux threshold is inside the round-off of one
#: model and of the order of the whole flow of another. Switched on, each
#: step takes q_tol from the reactions of its FIRST linear solve (which
#: carry the storage flux and scale with the time step; a saturated solve
#: of the stage's conditions does not — its flux is zero in a drawdown to a
#: uniform level, exactly when the transient flow is largest) and checks the
#: face of its final state (``_unsettled_nodes``): a step that leaves nodes
#: violating the face condition is not converged, and the stage says how
#: many (``notes["unsettled_nodes"]``). Without a seepage face nothing is
#: computed, so saturated transients do the same arithmetic as before.
#: Switch off to rebuild the transient of 0.1.273.
TRANSIENT_FACE_RULE = True

#: v0.1.282 (D276) — a converged transient step carries, to the next step
#: and to the stored water, the last linear solve it publishes, and not the
#: relaxed iterate (``TransientSeepageSolver.step``, "What is carried and
#: what is published"). With w = 1 the two are the same to the bit (the
#: erfc, Terzaghi, Ferris and Celia runs do not move); with w < 1 the
#: carried state moves by about tolerance·(1 - w)/w. Switch off to rebuild
#: 0.1.281.
TRANSIENT_CARRY_LAST_SOLVE = True


class _NewtonSystem:
    """The steady unsaturated equations as a residual for Newton's method
    (v0.1.266, D124).

        R(H) = sum_e kr_e(H)^t K0_e H_e - q

    with K0_e the element conductivity matrix at kr = 1 (the assembly of
    ``SeepageSolver.assemble``), q the applied fluxes and kr_e taken, as in
    ``_element_kr``, at the element's mean pressure head. Its Jacobian,

        J = sum_e [ kr_e^t K0_e + (K0_e H_e) d(kr_e^t)/dp (1/3) 1^T ],

    is not symmetric; d(kr^t)/dp is a central difference of the material's
    own function, so every permeability model is differentiated the same
    way, kinks included. Elements the assembly skips (degenerate) are
    skipped here too.
    """

    def __init__(self, solver, bcs) -> None:
        mesh = solver.mesh
        nodes, k0, ys, props = [], [], [], []
        for e in mesh.elements:
            g = e.shape_gradients(mesh)
            if g is None:
                continue
            dNdx, dNdy, area = g
            kxx, kyy, kxy = solver.props_for(e).conductivity_tensor()
            ke = [[area * (dNdx[i] * (kxx * dNdx[j] + kxy * dNdy[j])
                           + dNdy[i] * (kxy * dNdx[j] + kyy * dNdy[j]))
                   for j in range(3)] for i in range(3)]
            nodes.append(e.nodes)
            k0.append(ke)
            ys.append([mesh.nodes[i].y for i in e.nodes])
            props.append(solver.props_for(e))
        self.n = mesh.node_count
        self.gamma_w = solver.gamma_w
        self.EN = _np.asarray(nodes, dtype=int).reshape(-1, 3)
        self.K0 = _np.asarray(k0, dtype=float).reshape(-1, 3, 3)
        self.Y = _np.asarray(ys, dtype=float).reshape(-1, 3)
        self.props = props
        self.rows = _np.repeat(self.EN, 3, axis=1).ravel()
        self.cols = _np.tile(self.EN, (1, 3)).ravel()
        self.q = _np.asarray(solver.assemble(bcs)[3], dtype=float)
        self.fixed = solver._dirichlet_values(bcs)
        self.node_y = [nd.y for nd in mesh.nodes]

    def _kr(self, p, t):
        k = _np.array([pr.kr_at_pressure_head(float(pp), self.gamma_w)
                       for pr, pp in zip(self.props, p)])
        return k if t == 1.0 else k ** t

    def residual(self, H, t, jacobian: bool = False):
        He = H[self.EN]
        p = _np.mean(He - self.Y, axis=1)
        kr = self._kr(p, t)
        KH = _np.einsum("eij,ej->ei", self.K0, He)
        R = -self.q.copy()
        _np.add.at(R, self.EN.ravel(), (kr[:, None] * KH).ravel())
        if not jacobian:
            return R
        h = 1e-7 * _np.maximum(1.0, _np.abs(p))
        dk = (self._kr(p + h, t) - self._kr(p - h, t)) / (2.0 * h)
        Je = (kr[:, None, None] * self.K0
              + KH[:, :, None] * (dk / 3.0)[:, None, None])
        J = _csr((Je.ravel(), (self.rows, self.cols)),
                 shape=(self.n, self.n))
        return R, J

    def newton(self, H0, active, t, tol, max_iterations):
        """Newton's method with the seepage-face set ``active`` held at
        P = 0 and a backtracking (Armijo) line search on |R| over the free
        nodes. Converged when the full Newton correction is below ``tol``
        (m); a line search that cannot reduce |R| is a failure, never a
        convergence. Returns (H, converged, iterations)."""
        fixed = dict(self.fixed)
        fixed.update({nid: self.node_y[nid] for nid in active})
        H = _np.array(H0, dtype=float)
        for nid, v in fixed.items():
            H[nid] = v
        free = _np.array([i for i in range(self.n) if i not in fixed],
                         dtype=int)
        if free.size == 0:
            return H, True, 0
        for k in range(1, max_iterations + 1):
            R, J = self.residual(H, t, jacobian=True)
            Rf = R[free]
            norm = float(_np.linalg.norm(Rf))
            try:
                d = _spsolve(J[free][:, free].tocsc(), -Rf)
            except Exception:  # noqa: BLE001 — a singular step ends Newton
                return H, False, k
            d = _np.atleast_1d(_np.asarray(d, dtype=float))
            if not _np.all(_np.isfinite(d)):
                return H, False, k
            if float(_np.max(_np.abs(d))) < tol:
                H[free] += d
                return H, True, k
            lam = 1.0
            while True:
                Hn = H.copy()
                Hn[free] += lam * d
                trial = float(_np.linalg.norm(self.residual(Hn, t)[free]))
                if trial <= (1.0 - 1e-4 * lam) * norm:
                    break
                lam *= 0.5
                if lam < 1e-4:
                    return H, False, k
            H = Hn
        return H, False, max_iterations


#: kPa: an element this close to a kink of its curve is ON the kink (the
#: round-off of a converged state, far below the solver's tolerance)
_KINK_ROUNDING = 1e-9


class _PiecewiseSystem:
    """The residual of ``_NewtonSystem`` piece by piece (v0.1.362, D367).

    Every element sits on one piece of its permeability curve
    (``HydraulicProperties.log_kr_pieces``): between two points of a User
    Defined table, or on its floor ``kr_min``. Held on its piece, ln kr =
    a + b s is linear in the element's mean suction s (kPa), so

        kr^t = exp(t (a + b s))

    is smooth: the residual of the CELL, the problem's own while every
    element stays on its piece. These are the pieces of smoothness of
    Allgower & Georg (1990, §11.7), and the kinks of the curves are the
    facets between them. ``applicable`` is False when an element has a
    curve that is not piecewise log-linear (every model but User Defined).
    The seepage-face nodes ``active`` are held at P = 0."""

    def __init__(self, system, active, gamma_w):
        self.sy = system
        self.gw = float(gamma_w)
        fixed = dict(system.fixed)
        fixed.update({nid: system.node_y[nid] for nid in active})
        self.free = _np.array([i for i in range(system.n) if i not in fixed],
                              dtype=int)
        self.fix_i = _np.array(sorted(fixed), dtype=int)
        self.fix_v = _np.array([fixed[i] for i in self.fix_i], dtype=float)
        self.pos = -_np.ones(system.n, dtype=int)
        self.pos[self.free] = _np.arange(self.free.size)
        index, curves, mat = {}, [], []
        for pr in system.props:
            if id(pr) not in index:
                index[id(pr)] = len(curves)
                curves.append(pr.log_kr_pieces()
                              if pr.suction_unit() == "kPa" else None)
            mat.append(index[id(pr)])
        self.applicable = all(c is not None for c in curves)
        if not self.applicable:
            return
        self.curves = [tuple(_np.asarray(v, dtype=float) for v in c)
                       for c in curves]
        self.mat = _np.asarray(mat, dtype=int)
        n_el = self.mat.size
        self.j = _np.zeros(n_el, dtype=int)
        self.a, self.b = _np.zeros(n_el), _np.zeros(n_el)
        self.lo, self.hi = _np.zeros(n_el), _np.zeros(n_el)

    def complete(self, Hf):
        """The whole head vector from the free nodes."""
        H = _np.empty(self.sy.n)
        H[self.free] = Hf
        H[self.fix_i] = self.fix_v
        return H

    def suction(self, H):
        """Mean suction of every element, kPa."""
        return -self.gw * _np.mean(H[self.sy.EN] - self.sy.Y, axis=1)

    def _set(self, e):
        kinks, a, b = self.curves[self.mat[e]]
        j = self.j[e]
        self.a[e], self.b[e] = a[j], b[j]
        self.lo[e] = kinks[j - 1] if j > 0 else -math.inf
        self.hi[e] = kinks[j] if j < kinks.size else math.inf

    def assign(self, H):
        """Every element to the piece its suction is on."""
        s = self.suction(H)
        for m, (kinks, _a, _b) in enumerate(self.curves):
            sel = self.mat == m
            self.j[sel] = _np.searchsorted(kinks, s[sel])
        for e in range(self.j.size):
            self._set(e)

    def cross(self, e, side):
        """Element ``e`` to the next piece up ("hi") or down ("lo")."""
        self.j[e] += 1 if side == "hi" else -1
        self._set(e)

    def outside(self, s, skip=None):
        """Elements whose suction has left their piece."""
        out = (s < self.lo - _KINK_ROUNDING) | (s > self.hi + _KINK_ROUNDING)
        if skip is not None:
            out[skip] = False
        return _np.flatnonzero(out)

    def residual(self, H, t):
        """(R, J, R_t) of the cell over the free nodes: the residual, its
        Jacobian and its derivative in t. d(kr^t)/dp = kr^t t b (-gamma_w),
        and d(kr^t)/dt = kr^t ln kr."""
        sy = self.sy
        He = H[sy.EN]
        ln_kr = self.a + self.b * (-self.gw * _np.mean(He - sy.Y, axis=1))
        krt = _np.exp(t * ln_kr)
        KH = _np.einsum("eij,ej->ei", sy.K0, He)
        R = -sy.q.copy()
        _np.add.at(R, sy.EN.ravel(), (krt[:, None] * KH).ravel())
        dk = krt * t * self.b * (-self.gw)
        Je = (krt[:, None, None] * sy.K0
              + KH[:, :, None] * (dk / 3.0)[:, None, None])
        J = _csr((Je.ravel(), (sy.rows, sy.cols)), shape=(sy.n, sy.n))
        Rt = _np.zeros(sy.n)
        _np.add.at(Rt, sy.EN.ravel(), ((ln_kr * krt)[:, None] * KH).ravel())
        free = self.free
        return R[free], J[free][:, free].tocsc(), Rt[free]

    def suction_gradient(self, e):
        """d s_e / dH over the free nodes."""
        g = _np.zeros(self.free.size)
        for nid in self.sy.EN[e]:
            if self.pos[nid] >= 0:
                g[self.pos[nid]] += -self.gw / 3.0
        return g

    def suction_rate(self, tau_h):
        """d s / d(arc) of every element along the tangent's head part."""
        T = _np.zeros(self.sy.n)
        T[self.free] = tau_h
        return -self.gw * _np.mean(T[self.sy.EN], axis=1)


def _det_sign(lu) -> int:
    """sign(det A) from ``splu`` (Pr A Pc = L U, L with a unit diagonal):
    that of diag(U) times the parities of the two permutations."""
    d = lu.U.diagonal()
    if _np.any(d == 0):
        return 0
    sign = -1 if _np.count_nonzero(d < 0) % 2 else 1
    return sign * _parity(lu.perm_r) * _parity(lu.perm_c)


def _parity(perm) -> int:
    perm = _np.asarray(perm)
    seen = _np.zeros(perm.size, dtype=bool)
    cycles = 0
    for i in range(perm.size):
        if not seen[i]:
            cycles += 1
            j = i
            while not seen[j]:
                seen[j] = True
                j = perm[j]
    return -1 if (perm.size - cycles) % 2 else 1


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
       plain fixed-point iteration oscillates — up to a point: when the
       function is steep enough for the mesh, no relaxation stops the
       oscillation, and ``_rescue`` takes over (v0.1.266, see
       ``PICARD_RESCUE``).

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

    #: How many times one boundary node may flip between "free" and
    #: "held at P = 0" before it is frozen in its current state.
    #:
    #: v0.1.125 — this was **3**, and three is not a backstop, it is a
    #: cap that fires during ordinary convergence. On the verification
    #: dam of problem 102 it froze 47 of the 77 nodes of the exit face,
    #: left the free surface 4.5 m too high, and the run still reported
    #: ``converged = True`` — because a frozen node cannot change the
    #: active set, and "the active set stopped changing" was the
    #: convergence test. The factor of safety came out 9.4 % low, in the
    #: unsafe direction and in silence.
    #:
    #: The chatter the budget exists for is actually stopped by the two
    #: hysteresis bands below; the budget is only there for the case they
    #: do not. Measured on that dam: the answer is identical for every
    #: budget from 10 upwards (1.7174 at 10, at 40 and at 200), so the
    #: cure cost nothing and the cap was pure damage.
    DEFAULT_MAX_NODE_SWITCHES = 25

    def __init__(self, *args, relaxation: float = 0.5,
                 max_iterations: int = 200, tolerance: float = 1e-4,
                 max_node_switches: Optional[int] = None,
                 switch_pressure_tol: float = 0.0,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.relaxation = min(max(relaxation, 0.05), 1.0)
        self.max_iterations = max(1, max_iterations)
        self.tolerance = tolerance
        # Anti-chatter budget for the seepage-face switching; None → the
        # default, scaled with the relaxation (see ``max_node_switches``)
        self.max_node_switches = max_node_switches
        # Hysteresis band on the pressure-head decision; 0 → derived
        # from the mesh size in solve_unsaturated()
        self.switch_pressure_tol = switch_pressure_tol

    @property
    def max_node_switches(self) -> int:
        """How many times a node of the seepage face may switch before it
        freezes: the one given to the constructor, or else
        ``DEFAULT_MAX_NODE_SWITCHES`` scaled with the relaxation,
        max(25, ceil(10/w)) (v0.1.283, D279;
        ``SWITCH_BUDGET_SCALES_WITH_OMEGA``).

        With a slow relaxation the face set changes at almost every pass
        while the relaxed iterate creeps towards the fixed point, so a node
        spends switches in proportion to 1/w. Measured on the rectangular
        Gardner dam of ``test_unsaturated_v127`` with w = 0.1: a node at
        the foot of the face spent the 25 and froze held at P = 0 with
        water going in, the run came out unconverged 0.129 m from the fixed
        point, and the rescue could not step in (the frozen set no longer
        changes, so the loop "ends"; it can since v0.1.358, D356); with 50
        or more it converges within 1.3 tolerance. 10/w is 25 at w = 0.4,
        the groundwater door's, so the door and every w >= 0.4 keep exactly
        the budget they had. It is read when used, so the initial steady
        state of a transient, solved with the door's w (D277), gets the
        budget of that w."""
        if self._max_node_switches is not None:
            return self._max_node_switches
        if SWITCH_BUDGET_SCALES_WITH_OMEGA:
            return max(self.DEFAULT_MAX_NODE_SWITCHES,
                       math.ceil(10.0 / self.relaxation - 1e-9))
        return self.DEFAULT_MAX_NODE_SWITCHES

    @max_node_switches.setter
    def max_node_switches(self, value) -> None:
        self._max_node_switches = None if value is None else max(1, int(value))

    def _face_p_tol(self) -> float:
        """The pressure band of the seepage-face switching: a free node is
        held at P = 0 only when its pressure exceeds it. ``switch_pressure_tol``
        when given; otherwise a fraction of the element size, 0.002 h
        (``FACE_BANDS_TIGHT``; 0.02 h until v0.1.283, D280)."""
        if self.switch_pressure_tol:
            return self.switch_pressure_tol
        f = 0.002 if FACE_BANDS_TIGHT else 0.02
        return f * max(self.mesh.target_size, 1e-9)

    @staticmethod
    def _face_q_tol(q_scale: float) -> float:
        """The flux band: a held node is released only when its inflow
        exceeds this fraction of ``q_scale``, 1e-4 (``FACE_BANDS_TIGHT``;
        1e-3 until v0.1.283, D280).

        ``q_scale`` is the largest nodal flux of the first solve; when that
        solve carries no flow (``_saturated_carries_no_flow``), of the first
        solve with the face held (v0.1.359, D364,
        ``FACE_FLUX_SCALE_FROM_FLOW``). Until then such a model got a band
        of round-off, which the 1e-14 below did not catch: round-off is
        not zero."""
        f = 1e-4 if FACE_BANDS_TIGHT else 1e-3
        return f * q_scale if q_scale > 0 else 1e-14

    def _saturated_carries_no_flow(self, bcs) -> bool:
        """True when the saturated solve of ``bcs`` has no flow at all:
        every prescribed head is one level and no flux is applied (v0.1.359,
        D364). The level then satisfies the equations and the conditions
        (the rows of a conductivity matrix sum to zero) and the solution is
        unique, so every nodal flux of that solve is round-off.

        Decided from the conditions and not from the solved field: its
        round-off grows with the conductivity contrast (a relative head
        range from 3e-14 to 7e-12 on the verification bank, against 0.19
        and up where there is flow), and a threshold of 1e-12 missed a dam
        with a drain. Two levels one ulp apart count as two: the doubtful
        case keeps the band of the saturated solve, as before."""
        fixed = self._dirichlet_values(bcs)
        if not fixed or max(fixed.values()) != min(fixed.values()):
            return False
        if any(b.bc_type == BCType.NODAL_FLOW and b.value for b in bcs.nodes):
            return False
        return not any(s.q for s in bcs.segments)

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
            # v0.1.200 — through ``kr_at_pressure_head``, which gives each
            # model its suction in the unit it is written in (m of water
            # or kPa). This passed -p_mean, metres, to all of them.
            kr.append(self.props_for(e).kr_at_pressure_head(
                p_mean, self.gamma_w))
        return kr

    # ------------------------------------------------------------------
    def solve_unsaturated(self, bcs: SeepageBoundaryConditions
                          ) -> SeepageResult:
        """Picard iteration with seepage-face nodal switching.

        The convergence history (v0.1.269, D265) is published in the
        notes, for the Interpret charts and for anyone asking how a run
        got where it did:

        ``history``
            One entry per Picard pass: the UNRELAXED change of the heads,
            max|H_new - H| in metres, where H_new is the linear solve with
            the conductivities of H. It is the change the map itself asks
            for, independent of the relaxation factor w; the loop stops on
            the RELAXED one, w times it (see ``picard_delta``), so a run
            that converged ends with an entry below ``tolerance / w``.
            When the rescue ran, its entries follow, with the same
            measure max|G(H) - H|: one per Anderson evaluation of the map,
            and the final one of the continuation (its intermediate steps
            solve other problems, with kr raised to t < 1, and are left
            out; a continuation that fails before t = 1 leaves none). Every
            road tried is there, those set aside because their answer left
            the seepage face unsettled too (v0.1.356, D285); ``rescue``
            names the road whose state is published, or says "failed" when
            it is the loop's (v0.1.358, D356; see below). Four significant
            figures; None where there is no number.
        ``history_segments``
            ``[name, first index]`` of each part of the series:
            ``"picard"``, ``"anderson <depth>"``, ``"continuation"``.
        ``tolerance``
            The tolerance the run was judged against.
        ``picard_delta``
            The last RELAXED change of the loop, the quantity the stop test
            reads (see below).

        What the tolerance measures (v0.1.272, D267)
        --------------------------------------------
        The loop stops when the RELAXED change w·max|H_new - H| falls below
        ``tolerance`` and the seepage-face set has stopped changing. The
        unrelaxed change at that point is below tolerance / w, so a small w
        loosens the test by 1/w. Measured on the rectangular Gardner dam of
        ``test_unsaturated_v127`` against the fixed point solved to 1e-12,
        the converged result lies within 0.06 tolerance (w = 0.8), 0.25
        (0.4, the groundwater door's), 0.56 (0.3), 0.76 (0.2) and 1.3 (0.1)
        of it; and that fixed point is unique: w = 0.4 and 0.5 and three
        different starting fields agree to 3e-13. Judging the unrelaxed
        change instead would tighten the test by 1/w and move the digits of
        every model that converges today, for nothing measurable, so it was
        not done.

        What a very small w does instead: with w = 0.1 the relaxation is so
        slow that the face set changes at every pass for the first thirty,
        and with a budget of 25 (``DEFAULT_MAX_NODE_SWITCHES``) a node at the
        foot of the face spends it and freezes held at P = 0 with water
        going in. The loop then stops 0.13 m from the fixed point. Until
        v0.1.357 the run was reported unconverged there, the face never
        settled; since v0.1.358 the rescue takes over and lands 6e-7 m from
        the fixed point (D356, below). With a budget of 50 or more the loop
        converges by itself within 1.3 tolerance, and since D279 the
        default budget scales with 1/w; the groundwater door uses w = 0.4.

        How precisely the seepage face is resolved (v0.1.273, D266)
        -----------------------------------------------------------
        On that dam the converged state is unique. Not everywhere: the
        switching accepts a released node whose pressure is up to ``p_tol``
        and a held node whose inflow is up to ``q_tol``, and more than one
        face set can satisfy both. With the bands of 0.1.283 (0.02 times
        the element size and 1e-3 of the largest nodal flux), over the 53
        unsaturated steady rows of the verification bank run with w from
        0.2 to 0.8, 4 rows landed on another face set at another w (or
        after the rescue instead of the loop): one to five face nodes, 0.2
        to 2.4 cm of head, always below ``p_tol`` (1.4 and 4.2 cm in those
        meshes). With the bands ten times narrower (v0.1.284, D280,
        ``FACE_BANDS_TIGHT``) three of those rows give one face for every
        w (heads within 4e-5 m) and the fourth (02-038 h = 61 with a dry
        Gardner curve) two sets 2.1 mm apart. The exit point is resolved
        to a node and the face pressures to ``p_tol``; that is the
        precision of this algorithm, not a convergence error.

        A loop that stops with the face unsettled (v0.1.358, D356)
        ----------------------------------------------------------
        The stop test reads the face set, and a node frozen by the switch
        budget no longer changes it: the loop can stop with a frozen node
        held at P = 0 while water goes in. The loop's final state is asked
        (``_unsettled_nodes``) before the loop is believed, and when its
        face is unsettled the run goes to the rescue like a loop that
        failed, with Anderson started from the loop's face without its
        frozen nodes (``LOOP_SETTLED_FACE``). A road that settles the face
        is published. If none does, the loop's own state is, as before:
        unconverged, with ``rescue`` "failed", and a history that holds the
        loop, ending below ``tolerance / w``, and every road tried.

        A model that drains only through its face (v0.1.359, D364)
        -----------------------------------------------------------
        The flux band is 1e-4 of the largest nodal flux of the saturated
        solve (``_face_q_tol``). With one prescribed level and no applied
        flux that solve carries no flow (``_saturated_carries_no_flow``)
        and its fluxes are round-off; the band is then taken from the first
        pass solved with the face held, the first whose switching reads it
        (``FACE_FLUX_SCALE_FROM_FLOW``). The rescue and the final check use
        that band too.
        """
        n = self.mesh.node_count
        if n == 0 or not self.mesh.elements:
            res = SeepageResult()
            res.notes["error"] = M.seepage_note(M.EMPTY_MESH)
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
        # flux band scales with the largest nodal flux of the saturated
        # solve (v0.1.274: this said "the total Dirichlet throughput",
        # which is not what is computed), so it is dimensionally
        # consistent across permeabilities. A saturated solve with no flow
        # has only round-off to give: the scale then waits for the first
        # solve with the face held (v0.1.359, D364).
        p_tol = self._face_p_tol()
        q_scale = max((abs(r) for r in first.reactions), default=0.0)
        q_tol = self._face_q_tol(q_scale)
        scale_from_flow = (FACE_FLUX_SCALE_FROM_FLOW
                           and self._saturated_carries_no_flow(bcs))
        history: list[float] = []
        # v0.1.269 (D265): the unrelaxed change of every pass, published
        # (``history`` above stays the relaxed one the stop test reads)
        changes: list[float] = []
        converged = False
        it = 0
        H_prev = H

        for it in range(1, self.max_iterations + 1):
            # v0.1.366 (D362) -- where a watcher may stop the solve
            checkpoint()
            kr = self._element_kr(H)
            extra = {nid: self.mesh.nodes[nid].y for nid in active}
            step = super().solve(bcs, kr=kr, extra_dirichlet=extra)
            if not step.converged:
                res = SeepageResult()
                res.notes["error"] = M.seepage_note(
                    M.PICARD_LINEAR_FAILED, it=it)
                res.iterations = it
                return res

            H_new = step.total_head
            w = self.relaxation
            H_relaxed = [(1.0 - w) * H[i] + w * H_new[i] for i in range(n)]
            delta = max(abs(H_relaxed[i] - H[i]) for i in range(n))
            changes.append(max(abs(H_new[i] - H[i]) for i in range(n)))
            H_prev = H
            H = H_relaxed
            history.append(delta)

            if scale_from_flow and active:
                # D364: the first solve with the face held, before the
                # first switching that reads the band
                q_tol = self._face_q_tol(
                    max((abs(r) for r in step.reactions), default=0.0))
                scale_from_flow = False
            new_active = self._switch_seepage_face(
                active, switches, unknown, H, step.reactions, p_tol, q_tol)
            set_changed = (new_active != active)
            active = new_active

            if delta < self.tolerance and not set_changed:
                converged = True
                break

        # ---- the rescue (v0.1.266, D124) ----------------------------
        # Only after the loop has failed: whatever converged above with
        # its face settled goes through exactly the arithmetic it went
        # through before.
        rescue = None
        final = None
        unsettled_loop = False
        if converged and PICARD_RESCUE and LOOP_SETTLED_FACE:
            # v0.1.358 (D356): a loop that stopped with the face unsettled
            # has failed too. Its final state is the solve the end makes,
            # computed here once, so a settled loop publishes the same bits.
            kr = self._element_kr(H)
            extra = {nid: self.mesh.nodes[nid].y for nid in active}
            final = super().solve(bcs, kr=kr, extra_dirichlet=extra)
            if final.converged and self._unsettled_nodes(
                    final, unknown, active, p_tol, q_tol):
                converged = False
                unsettled_loop = True
        if not converged and PICARD_RESCUE:
            start_face = active
            if unsettled_loop:
                # the frozen nodes are the ones the loop could not revise;
                # started with them, Anderson kept a node held in dry
                # ground whose inflow stayed below the band (D356)
                start_face = {nid for nid in active
                              if switches.get(nid, 0) < self.max_node_switches}
            rescue = self._rescue(bcs, H, H_prev, start_face, unknown, p_tol,
                                  q_tol, first.total_head,
                                  fallback=not unsettled_loop)
            if rescue["converged"]:
                H = rescue["head"]
                active = rescue["active"]
                switches = rescue["switches"]
                converged = True
                final = None

        # ---- final consistent state ---------------------------------
        if final is None:
            kr = self._element_kr(H)
            extra = {nid: self.mesh.nodes[nid].y for nid in active}
            final = super().solve(bcs, kr=kr, extra_dirichlet=extra)
        if not final.converged:
            final.notes["error"] = M.seepage_note(M.FINAL_FAILED)
            return final
        final.converged = converged
        final.iterations = it + (rescue["iterations"] if rescue else 0)
        final.seepage_nodes = sorted(active)
        final.notes["picard_delta"] = history[-1] if history else float("nan")
        final.notes["relaxation"] = self.relaxation
        final.notes["kr_min"] = min(kr) if kr else 1.0
        final.notes["kr_max"] = max(kr) if kr else 1.0
        if rescue is not None:
            final.notes["rescue"] = rescue["method"]
            final.notes["rescue_iterations"] = rescue["iterations"]
            final.notes["rescue_residual"] = rescue["residual"]
            if rescue.get("piecewise"):
                # v0.1.362 (D367): the piecewise path could not run
                final.notes["rescue_piecewise"] = rescue["piecewise"]
        segments = [["picard", 0]]
        if rescue is not None:
            segments += [[name, len(changes) + i]
                         for name, i in rescue["segments"]]
            changes += rescue["history"]
        final.notes["history"] = _change_series(changes)
        final.notes["history_segments"] = segments
        final.notes["tolerance"] = self.tolerance
        # v0.1.125 — a frozen node is an unresolved boundary condition,
        # and until this version nothing said so: freezing made the
        # active set stop changing, which was read as convergence. The
        # count is recorded even when zero so a run can be asked the
        # question, and the check below asks it of the FINAL state
        # rather than trusting that the loop ended for the right reason.
        frozen = sorted(nid for nid, k in switches.items()
                        if k >= self.max_node_switches)
        final.notes["frozen_nodes"] = len(frozen)
        unsettled = self._unsettled_nodes(final, unknown, active, p_tol,
                                          q_tol)
        final.notes["unsettled_nodes"] = len(unsettled)
        if unsettled:
            final.converged = False
            final.notes["warning"] = M.seepage_note(
                M.FACE_UNSETTLED, unsettled=len(unsettled),
                frozen=len(frozen), budget=self.max_node_switches)
        elif not converged and rescue is None:
            # v0.1.273 (D266) — this told the user to try "a smaller
            # relaxation factor or a finer mesh". Neither is advice: the
            # relaxation is not a setting anywhere a user can reach (see
            # ``solve_project_groundwater``), and a finer mesh is what brings
            # on the cycle the rescue exists for (D124). This branch is only
            # reached with the rescue switched off.
            final.notes["warning"] = M.seepage_note(
                M.PICARD_NO_RESCUE, steps=self.max_iterations,
                change=history[-1])
        elif not converged:
            # v0.1.266 — the old advice is wrong on both counts when the
            # rescue has run: no relaxation breaks the cycle it exists
            # for, and refining is what brings the cycle on (D124). Since
            # v0.1.362 (D367) it says when the continuation stopped at a
            # turn of its path that the piecewise path could not follow.
            final.notes["warning"] = M.seepage_note(
                M.PICARD_RESCUE_PIECEWISE_NA if rescue.get("piecewise")
                else M.PICARD_RESCUE_FAILED, steps=self.max_iterations,
                change=history[-1], rescue_change=rescue["residual"])
        return final

    # ------------------------------------------------------------------
    def _switch_seepage_face(self, active, switches, unknown, H,
                             reactions, p_tol, q_tol) -> set:
        """The active set after one seepage-face switching decision.

        Reaction sign convention (verified empirically against a 1D case):
        POSITIVE reaction = water entering the domain at that node. A
        seepage face cannot admit water, so a node held at P = 0 whose
        reaction turns positive must be released back to Q = 0.

        Plain switching chatters (the active set flips 2->1->0->2
        indefinitely and the heads never settle), which is the classical
        difficulty of the nodal-switching algorithm. Two standard cures
        are applied: a hysteresis band on both decisions, and a per-node
        switch budget after which the node is frozen in its current state
        so the active set is guaranteed to settle. ``switches`` is updated
        in place.

        v0.1.266 — moved out of the Picard loop, unchanged, so that the
        rescue applies the very same rule.
        """
        new_active = set(active)
        for nid in unknown:
            if switches.get(nid, 0) >= self.max_node_switches:
                continue                      # frozen
            y = self.mesh.nodes[nid].y
            if nid in active:
                q_node = (reactions[nid]
                          if reactions else 0.0)
                if q_node > q_tol:            # inflow → release
                    new_active.discard(nid)
                    switches[nid] = switches.get(nid, 0) + 1
            else:
                if H[nid] - y > p_tol:        # positive P → hold at 0
                    new_active.add(nid)
                    switches[nid] = switches.get(nid, 0) + 1
        return new_active

    # ------------------------------------------------------------------
    def _picard_map(self, bcs, H, active, power: float = 1.0):
        """One unrelaxed Picard step, G(H): the linear solve with the
        conductivities of ``H`` and the seepage-face nodes of ``active``
        held at P = 0. ``power`` raises every relative permeability to
        that power, the continuation parameter of ``_continuation_newton``
        (1 is the problem itself)."""
        kr = self._element_kr(list(H))
        if power != 1.0:
            kr = [k ** power for k in kr]
        extra = {nid: self.mesh.nodes[nid].y for nid in active}
        return SeepageSolver.solve(self, bcs, kr=kr, extra_dirichlet=extra)

    # ------------------------------------------------------------------
    def _rescue(self, bcs, H, H_prev, active, unknown, p_tol, q_tol,
                H_saturated, fallback: bool = True) -> dict:
        """Look for the fixed point the Picard loop failed to reach
        (v0.1.266, D124; see ``PICARD_RESCUE``).

        The fixed point is the loop's own: heads H such that the linear
        solve with the conductivities k(H) returns H, with the seepage-face
        nodes obeying the loop's switching rule. Two roads, in order:

        1. **Anderson acceleration** of the unrelaxed Picard map
           G(H) (Anderson 1965; the "type II" form of Walker & Ni 2011,
           which Lott, Walker, Woodward & Yang 2012 apply to the Picard
           iteration of variably saturated flow), started from the centre
           of the loop's last step — the centre of the cycle it was in.
           Each depth of ``RESCUE_ANDERSON_DEPTHS`` in turn.
        2. **Continuation with Newton's method** (``_continuation_newton``):
           the steepness of every permeability function is brought from
           zero to its own, each step solved by Newton from the previous
           one. Where it stops on its smallest step, since v0.1.362 (D367)
           its path of solutions is followed on from there, piece by piece
           across the kinks of the curves (``_piecewise_path``,
           ``RESCUE_PIECEWISE_PATH``).

        Convergence is judged on the UNRELAXED change, max|G(H) - H| below
        the tolerance, which is stricter than the loop's relaxed test.
        Each road starts a switch budget of its own: it is a new attempt,
        and the loop may have spent its budget on the cycle.

        What a road must settle (v0.1.356, D285)
        ----------------------------------------
        A road is accepted only when its answer also obeys the seepage-face
        condition (``_unsettled_nodes``; ``RESCUE_SETTLED_FACE``). Where a
        road accepts, its switching rule has just run on the same linear
        solve with the same bands, so a node can still break the face there
        only if the road's own budget froze it. Such a road is set aside and
        the next one is tried. If none settles the face, the first road set
        aside is returned, marked converged as before, and the face check
        of ``solve_unsaturated`` reports it: the state 0.1.355 published,
        with ``iterations``, ``history`` and ``segments`` covering every
        road tried. Until 0.1.355 the first road to reach the tolerance was
        taken whatever its face, and the roads after it never ran.

        Measured on problem 4 of the groundwater verification bank (see the
        switch): the continuation settled all four cases Anderson had
        accepted with the face unsettled. The second Anderson depth settled
        none of them -- it froze the same nodes as the first -- and is tried
        all the same, in the written order: it is the road that settles
        other cases once the first depth fails on the tolerance.

        A loop that stopped with the face unsettled (v0.1.358, D356) has a
        state of its own to fall back on, the one 0.1.357 published: with
        ``fallback`` False a road set aside is not returned, and the rescue
        reports "failed", so that ``solve_unsaturated`` publishes the
        loop's state. ``active`` is then the loop's face without its frozen
        nodes (``LOOP_SETTLED_FACE``).

        Where every road fails on a fine mesh (D365, closed as documented)
        -------------------------------------------------------------------
        Dam 2 of problem 9 of the groundwater verification bank (the
        toe-drain dam of Chapuis et al. 2001, whose drain loses six decades
        of permeability over 2.9 kPa of suction), on the generator's
        4000-element mesh with the groundwater door's settings (w = 0.4,
        200 passes, tolerance 1e-5): the loop cycles and the three roads
        fail, and the run comes out unconverged. Measured
        (_auditoria/P6_0359), it is none of the things a setting reaches:
        * not the flux band (D364): with any band, from round-off to 1e-3
          of the real flow, the three roads are identical. None of them
          changes the face (one node held throughout), and the band is read
          only to release a held node;
        * not a missing answer: started from the field the bank converges
          to with w = 0.3, Anderson accepts it in 5 evaluations with the
          door's tolerance and bands;
        * Anderson's outcome hangs on where the loop's cycle leaves it and
          on round-off. From four other starts neither depth reaches the
          tolerance, and the same iteration written in the mixing form of
          Walker & Ni (2011) with parameter 1, equal to this one but for
          rounding, ends 3.1 m off instead of 2.0;
        * the continuation stops at t = 0.62 with its step halved to the
          minimum: Newton's line search cannot reduce |R|, frozen to eight
          figures. It is not the budget (266 of 1000 iterations), the
          per-step budget or the face. The Jacobian is not turning singular
          there (its smallest singular value falls smoothly along t), which
          was read as a kink of the piecewise curves rather than a fold; it
          is both, a fold that sits on a kink (D366, below).
        Of five meshes from 1921 to 4095 elements, two fail (3691 and
        3886); the other three converge, by three different roads, with the
        discharge between -2.5 % and +0.8 % of the published one. The owner
        decided to leave the rescue as it is and to look for a road robust
        to near-step curves under its own entry (D366).

        Why the continuation stops: a fold on a kink (D366, documented)
        ----------------------------------------------------------------
        Measured on the same two meshes (_auditoria/P6_0360): Newton stops
        because one element of the drain sits on the kink at 9.8 kPa where
        the drain's curve meets its floor ``kr_min``. From the wet side the
        step sends it dry, from the dry side wet, and the step the line
        search accepts shrinks with its distance to the kink. The Jacobian
        is exact on either side; what changes across the kink is the sign
        of its determinant, +1 with the dry slope and -1 with the wet one.
        Below t* two solutions exist, the element dry and the element wet,
        and they meet on the kink (between t = 0.6172 and 0.6177 on 3886
        elements, 0.6489 and 0.6504 on 3691): past it neither is a solution.
        The path of solutions turns back at a non-smooth fold, which no
        one-sided singular value shows, and continuation in the natural
        parameter cannot cross it however its steps are searched.

        Roads measured from the continuation's last state, each written two
        algebraically equal ways:
        * a non-monotone line search (Grippo, Lampariello & Lucidi 1986):
          fails on both meshes, there being no root nearby;
        * pseudo-arclength continuation (Keller 1977; Allgower & Georg
          1990): fails on both, its tangent turning vertical at the fold;
        * Anderson with systematic restarts (Henderson & Varadhan 2019):
          converges on 3886 and fails on 3691;
        * pseudo-transient continuation (Kelley & Keyes 1998; Fowler &
          Kelley 2005 for non-smooth equations): converges on 3886 only
          for one decade of its initial step, and fails on 3691;
        * Newton with one-sided derivatives (Qi & Sun 1993) was not tried:
          the derivative is not what fails.
        The solution exists on both meshes (discharge -1.44 % and -1.39 %
        of the published one), but which start, Anderson variant and depth
        reaches it depends on the mesh: of 24 combinations, 2 converge on
        3886, 4 on 3691 and none on both. A road chosen because it covers
        these two meshes would be fitted to them. The owner closed D366 as
        documented and opened D367 for a road that follows the path of
        solutions across such folds.

        The path followed across the folds (D367, v0.1.362)
        ----------------------------------------------------
        The continuation stops at the fold because it moves in t; the path
        goes on. Followed by its arc length, piece by piece
        (``_piecewise_path``, after Allgower & Georg 1990), on both meshes
        it is a Z. There are three folds on the drain's kink at 9.8 kPa and
        one smooth fold: the path runs forward to t = 0.93-0.97, back to
        0.66-0.67 and forward to 1, so between those two values the
        intermediate problem has three solutions. Started where the
        continuation stops, at the state before it, or at t = 0, it is one
        path and it ends at one point, the answer already known. On 3886
        elements that is 7.8e-7 m from the bank's; on 3691, 3.1e-7 m from
        Anderson's. The discharge is -1.44 % and -1.39 % of the published
        one, and both meshes now converge with the door's settings
        (_auditoria/P6_0362).

        The pseudo-transient continuation was measured again, with the
        storage scale of the transient (the lumped capacity of Celia et al.
        1990) in place of diag|J|. It converges for no initial step over
        eleven decades, on either mesh.

        The path costs 1242 to 1433 Newton iterations, more than the
        continuation's budget leaves (734 and 749). By the owner's decision
        it has no budget of its own, and it runs only when every material
        has a User Defined curve.

        Returns a dict: ``converged``, ``method``, ``iterations`` (map
        evaluations plus Newton iterations), ``residual`` (the last
        max|G(H) - H|, m; that of the road returned), ``head``, ``active``
        and ``switches``; and ``history`` and ``segments``, its part of the
        published series (see ``solve_unsaturated``), indexed from the
        rescue's start. A road set aside also carries ``unsettled``, the
        number of face nodes it left unsettled. ``piecewise`` is "not
        applicable" when the continuation stopped on its smallest step and
        the piecewise path could not run.
        """
        out = {"converged": False, "method": "failed", "iterations": 0,
               "residual": float("nan"), "head": H, "active": set(active),
               "switches": {}, "history": [], "segments": []}
        if _np is None:
            out["method"] = "not available (needs NumPy)"
            return out

        def _done(r, method):
            r["method"] = method
            r["iterations"] = out["iterations"]
            r["history"], r["segments"] = out["history"], out["segments"]
            return r

        # v0.1.356 (D285): the first road that reached the tolerance with
        # the face unsettled, kept in case no road settles it
        aside = None
        start = 0.5 * (_np.asarray(H, dtype=float)
                       + _np.asarray(H_prev, dtype=float))
        for depth in RESCUE_ANDERSON_DEPTHS:
            r = self._anderson(bcs, start, set(active), unknown, p_tol,
                               q_tol, depth)
            out["iterations"] += r["iterations"]
            out["residual"] = r["residual"]
            if r["history"]:
                out["segments"].append([f"anderson {depth}",
                                        len(out["history"])])
                out["history"] += r["history"]
            if r["converged"]:
                return _done(r, f"anderson (depth {depth})")
            if aside is None and r.get("unsettled"):
                aside = (r, f"anderson (depth {depth})")
        if _csr is not None and _spsolve is not None:
            r = self._continuation_newton(bcs, H_saturated, unknown, p_tol,
                                          q_tol)
            out["iterations"] += r["iterations"]
            out["residual"] = r["residual"]
            if math.isfinite(r["residual"]):
                out["segments"].append(["continuation",
                                        len(out["history"])])
                out["history"].append(r["residual"])
            if r["converged"]:
                return _done(r, "continuation-newton")
            if aside is None and r.get("unsettled"):
                aside = (r, "continuation-newton")
            if RESCUE_PIECEWISE_PATH and r.get("stopped") == "min_step":
                # v0.1.362 (D367): on from where the continuation stopped
                r = self._piecewise_path(bcs, r["last"], unknown, p_tol,
                                         q_tol)
                if r.get("applicable") is False:
                    out["piecewise"] = "not applicable"
                else:
                    out["iterations"] += r["iterations"]
                    out["residual"] = r["residual"]
                    if math.isfinite(r["residual"]):
                        out["segments"].append(["continuation-piecewise",
                                                len(out["history"])])
                        out["history"].append(r["residual"])
                    if r["converged"]:
                        return _done(r, "continuation-piecewise")
                    if aside is None and r.get("unsettled"):
                        aside = (r, "continuation-piecewise")
        if aside is not None and fallback:
            # No road settled the face: hand over what 0.1.355 published,
            # and let the final check of solve_unsaturated report the face
            r, method = aside
            r["converged"] = True
            return _done(r, method)
        return out

    # ------------------------------------------------------------------
    def _anderson(self, bcs, x0, active, unknown, p_tol, q_tol,
                  depth: int) -> dict:
        """Anderson acceleration of G (Walker & Ni 2011, Alg. AA with
        mixing parameter 1): x_{k+1} = G(x_k) - dG gamma, where gamma
        minimises |F(x_k) - dF gamma| over the last ``depth`` differences
        of the residual F = G(x) - x and of G. The history is emptied
        whenever the seepage-face set changes, since G changes with it.

        A state that reaches the tolerance with the seepage face unsettled
        ends the road unaccepted, marked ``unsettled`` (v0.1.356, D285; see
        ``_rescue``): only a node this road froze can be the cause, and
        iterating on cannot unfreeze it."""
        x = _np.asarray(x0, dtype=float)
        switches: dict[int, int] = {}
        dF: list = []
        dG: list = []
        F_prev = G_prev = None
        residual = float("nan")
        residuals: list[float] = []          # v0.1.269 (D265)
        k = 0
        for k in range(1, RESCUE_ANDERSON_EVALUATIONS + 1):
            checkpoint()                     # v0.1.366 (D362)
            step = self._picard_map(bcs, x, active)
            if not step.converged:
                break
            g = _np.asarray(step.total_head, dtype=float)
            f = g - x
            residual = float(_np.max(_np.abs(f)))
            residuals.append(residual)
            new_active = self._switch_seepage_face(
                active, switches, unknown, g, step.reactions, p_tol, q_tol)
            if new_active != active:
                active = new_active
                dF, dG = [], []
                F_prev = G_prev = None
                x = g
                continue
            if residual < self.tolerance:
                result = {"converged": True, "iterations": k,
                          "residual": residual, "head": x.tolist(),
                          "active": active, "switches": switches,
                          "history": residuals}
                if RESCUE_SETTLED_FACE:
                    # v0.1.356 (D285): the switching just ran on this very
                    # solve, so a node can only break the face if frozen
                    bad = self._unsettled_nodes(step, unknown, active, p_tol,
                                                q_tol)
                    if bad:
                        result["converged"] = False
                        result["unsettled"] = len(bad)
                return result
            if F_prev is not None:
                dF.append(f - F_prev)
                dG.append(g - G_prev)
                if len(dF) > depth:
                    dF.pop(0)
                    dG.pop(0)
            F_prev, G_prev = f, g
            if dF:
                gamma = _np.linalg.lstsq(_np.array(dF).T, f, rcond=None)[0]
                x = g - _np.array(dG).T @ gamma
            else:
                x = g
        return {"converged": False, "iterations": k, "residual": residual,
                "head": x.tolist(), "active": active, "switches": switches,
                "history": residuals}

    # ------------------------------------------------------------------
    def _continuation_newton(self, bcs, H0, unknown, p_tol, q_tol) -> dict:
        """Continuation in the steepness of the permeability functions,
        each step solved by Newton's method.

        Every relative permeability is raised to a power t, from 0 (kr = 1
        everywhere: the linear problem, whose solution ``H0`` is) to 1 (the
        problem itself). Raising kr to t scales log kr, and so the slope of
        every curve, by t, so a short step in t is a small change of the
        problem and each Newton solve starts close to its solution (the
        embedding is the classical natural-parameter continuation of
        Allgower & Georg 1990). A step that fails is halved; one that
        converges doubles the next. Within a step the seepage-face set is
        held fixed for Newton and switched with the loop's rule afterwards,
        repeating the step until the set stops changing. Newton's method
        on this equation is compared with Picard's by Paniconi & Putti
        (1994). Continuation in the natural parameter cannot cross a
        turning point of the path, and with piecewise curves one can sit on
        a kink, where no one-sided Jacobian turns singular (D366, see
        ``_rescue``). Stopped on its smallest step, it returns, since
        v0.1.362 (D367), ``stopped`` = "min_step" and ``last``, its last
        accepted state and the one before it, for ``_piecewise_path`` to
        follow the path on from there.

        The answer must be a fixed point of the Picard map itself and, since
        v0.1.356 (D285, see ``_rescue``), settle the seepage face: one that
        does not is returned unaccepted, marked ``unsettled``.
        """
        system = _NewtonSystem(self, bcs)
        H = _np.asarray(H0, dtype=float)
        active: set = set()
        switches: dict[int, int] = {}
        t, dt = 0.0, 0.25
        t_prev, H_prev = t, H
        newton = 0
        fail = {"converged": False, "iterations": 0,
                "residual": float("nan"), "head": list(H0),
                "active": set(), "switches": {}}
        while True:
            tn = min(1.0, t + dt)
            Hn, act_n, sw_n = H, set(active), dict(switches)
            ok_step = False
            for _ in range(len(unknown) + 2):
                Hn, ok, k = system.newton(Hn, act_n, tn, self.tolerance,
                                          RESCUE_NEWTON_PER_STEP)
                newton += k
                if not ok:
                    break
                step = self._picard_map(bcs, Hn, act_n, power=tn)
                if not step.converged:
                    break
                new_active = self._switch_seepage_face(
                    act_n, sw_n, unknown, step.total_head, step.reactions,
                    p_tol, q_tol)
                if new_active == act_n:
                    ok_step = True
                    break
                act_n = new_active
            if newton > RESCUE_NEWTON_BUDGET:
                fail["iterations"] = newton
                return fail
            if ok_step:
                t_prev, H_prev = t, H
                H, active, switches, t = Hn, act_n, sw_n, tn
                if t >= 1.0:
                    break
                dt = min(2.0 * dt, 1.0)
            else:
                dt *= 0.5
                if dt < RESCUE_MIN_STEP:
                    fail["iterations"] = newton
                    # v0.1.362 (D367): where it stopped, for the piecewise
                    # path to go on from (``_piecewise_path``)
                    fail["stopped"] = "min_step"
                    fail["last"] = (t, H, set(active), dict(switches),
                                    t_prev, H_prev)
                    return fail
        # The answer must be a fixed point of the Picard map itself.
        step = self._picard_map(bcs, H, active)
        residual = (float(_np.max(_np.abs(
            _np.asarray(step.total_head, dtype=float) - H)))
            if step.converged else float("inf"))
        result = {"converged": residual < self.tolerance,
                  "iterations": newton, "residual": residual,
                  "head": H.tolist(), "active": active, "switches": switches}
        if result["converged"] and RESCUE_SETTLED_FACE:
            # v0.1.356 (D285): and settle the face, which only a node frozen
            # by this road's budget can break here
            bad = self._unsettled_nodes(step, unknown, active, p_tol, q_tol)
            if bad:
                result["converged"] = False
                result["unsettled"] = len(bad)
        return result

    # ------------------------------------------------------------------
    def _piecewise_path(self, bcs, last, unknown, p_tol, q_tol) -> dict:
        """Follow the continuation's path of solutions on from where it
        stopped, piece by piece across the kinks of the permeability curves
        (v0.1.362, D367; ``RESCUE_PIECEWISE_PATH``, see ``_rescue``).

        The continuation solves R(H, t) = 0 with every kr raised to t, from
        0 to 1. Its solutions form a path in (H, t) that can turn back in
        t. Continuation in t cannot follow a turn, and with piecewise
        curves a turn can sit on a kink (D366). Here the path is followed
        by its arc length, after Allgower & Georg (1990):

        * the orientation (their 2.1.7): the sign of det [A; tau*], with
          A = [J R_t], is constant along the path. By Cramer's rule, with
          tau = c (v, 1) and v = -J^-1 R_t, det [A; tau*] = c det J
          (1 + |v|^2), so tau_t has the sign of det J. At t = 0, J is K0 on
          the free nodes, positive definite, and the path leaves towards
          t > 0; where det J < 0 it goes on with t decreasing;
        * the pieces of smoothness (their §11.7): with every element held
          on a piece of its curve the residual is smooth
          (``_PiecewiseSystem``). Each step is a tangent predictor and
          Keller's (1977) bordered Newton corrector on that residual;
        * the facets (their ch. 14): the step is cut short at the first
          kink an element would reach along the tangent, a minimum-ratio
          test (their 14.1.2). There the corrector holds that element's
          suction on the kink instead of the arc length. The element
          passes to the next piece, the tangent is taken again with that
          piece's Jacobian, and it must enter the piece: the path crosses a
          facet transversally (their 14.1.11-17). Where det J changed sign,
          t turns back: the fold on a kink.

        A corrected point is accepted when every element is still on its
        piece, where the residual of the cell is the problem's; otherwise
        the step is halved. A corrector fails when it does not converge in
        ``RESCUE_NEWTON_PER_STEP`` iterations or stops contracting. The
        seepage face is held along the path, as Newton holds it within a
        step of the continuation. At t = 1 the continuation's own closing
        follows: the face rule, with Newton at t = 1 whenever it changes
        the face, then a fixed point of the Picard map and a settled face.

        There is no Newton budget of its own (the owner's decision, D367):
        the path that leaves the regular linear problem at t = 0 cannot
        come back to t = 0 and, bounded, reaches t = 1 (their ch. 1 and
        14.2). It also ends, failing, as a piecewise-linear algorithm ends:
        an arc step below the smallest, a tangent that does not enter the
        next piece, or t below 0. The smallest arc step is the
        continuation's ratio of its smallest step to its first (1e-3 to
        0.25) times the arc of its last accepted step.

        ``last`` is the continuation's last accepted state (t, H, face,
        switches) and the one before it (t, H). Returns the continuation's
        dict. ``applicable`` is False, with nothing computed, when a
        material's curve is not piecewise log-linear.
        """
        t, H, active, switches, t_prev, H_prev = last
        active, switches = set(active), dict(switches)
        out = {"converged": False, "iterations": 0, "residual": float("nan"),
               "head": list(H), "active": set(active),
               "switches": dict(switches)}
        system = _NewtonSystem(self, bcs)
        cells = _PiecewiseSystem(system, active, self.gamma_w)
        if _splu is None or not cells.applicable:
            out["applicable"] = False
            return out
        free = cells.free
        H = _np.asarray(H, dtype=float).copy()
        length = float(_np.linalg.norm(
            _np.append(H[free], t)
            - _np.append(_np.asarray(H_prev, dtype=float)[free], t_prev)))
        smallest = length * RESCUE_MIN_STEP / 0.25
        H[cells.fix_i] = cells.fix_v
        cells.assign(H)
        tau = self._path_tangent(cells, H, t)
        newton = 0
        while True:
            # the first kink an element reaches along the tangent
            s = cells.suction(H)
            rate = cells.suction_rate(tau[:-1])
            with _np.errstate(divide="ignore", invalid="ignore"):
                up = _np.where(rate > 0, (cells.hi - s) / rate, _np.inf)
                down = _np.where(rate < 0, (s - cells.lo) / (-rate), _np.inf)
            to_kink = _np.minimum(_np.maximum(up, 0.0), _np.maximum(down, 0.0))
            e = int(_np.argmin(to_kink))
            at_kink = float(to_kink[e])
            side = "hi" if up[e] <= down[e] else "lo"
            at_end = (1.0 - t) / tau[-1] if tau[-1] > 0 else math.inf
            arc = min(length, at_kink, at_end)
            if arc == at_kink and at_kink <= length:
                kind = "kink"
            elif arc == at_end and at_end <= length:
                kind = "end"
            else:
                kind = "arc"
            u0 = _np.append(H[free], t)
            guess = u0 + arc * tau
            if kind == "arc":
                held = ("arc", tau, u0, arc)
            elif kind == "kink":
                held = ("kink", e, cells.hi[e] if side == "hi" else cells.lo[e])
            else:
                held = ("end",)
                guess[-1] = 1.0
            Hf, tc, ok, k = self._path_corrector(cells, guess[:-1],
                                                 float(guess[-1]), held)
            newton += k
            if ok:
                Hc = cells.complete(Hf)
                ok = cells.outside(cells.suction(Hc),
                                   skip=e if kind == "kink" else None).size == 0
            if not ok:
                length = 0.5 * arc
                # only a failed arc step measures the step: one cut short at
                # a kink or at t = 1 can be any length
                if kind == "arc" and length < smallest:
                    out["iterations"] = newton
                    return out
                continue
            H, t = Hc, tc
            if kind == "kink":
                cells.cross(e, side)
            tau = self._path_tangent(cells, H, t)
            if kind == "kink":
                enters = cells.suction_rate(tau[:-1])[e]
                if not (enters > 0 if side == "hi" else enters < 0):
                    out["iterations"] = newton
                    return out
            elif kind == "arc":
                length = 2.0 * length
            if kind == "end":
                break
            if t < 0.0:
                out["iterations"] = newton
                return out
        # at t = 1, the continuation's own closing
        for _ in range(len(unknown) + 2):
            step = self._picard_map(bcs, H, active)
            if not step.converged:
                break
            new_active = self._switch_seepage_face(
                active, switches, unknown, step.total_head, step.reactions,
                p_tol, q_tol)
            if new_active == active:
                residual = float(_np.max(_np.abs(
                    _np.asarray(step.total_head, dtype=float) - H)))
                out.update(converged=residual < self.tolerance,
                           residual=residual, head=H.tolist(),
                           active=active, switches=switches)
                if out["converged"] and RESCUE_SETTLED_FACE:
                    bad = self._unsettled_nodes(step, unknown, active, p_tol,
                                                q_tol)
                    if bad:
                        out["converged"] = False
                        out["unsettled"] = len(bad)
                break
            active = new_active
            H, ok, k = system.newton(H, active, 1.0, self.tolerance,
                                     RESCUE_NEWTON_PER_STEP)
            newton += k
            if not ok:
                break
        out["iterations"] = newton
        return out

    @staticmethod
    def _path_tangent(cells, H, t):
        """The unit tangent of positive orientation: tau_t has the sign of
        det J (``_piecewise_path``)."""
        _R, J, Rt = cells.residual(H, t)
        lu = _splu(J)
        tau = _np.append(lu.solve(-Rt), 1.0)
        tau /= _np.linalg.norm(tau)
        return -tau if _det_sign(lu) < 0 else tau

    def _path_corrector(self, cells, Hf, t, held):
        """Bordered Newton (Keller 1977) on [R(H, t); g(H, t)] = 0 from
        (Hf, t), the residual of the cell, with g by ``held``:
        ("arc", tau, u0, arc): tau . (u - u0) - arc; ("kink", e, s_b):
        s_e(H) - s_b; ("end",): t - 1. The bordered system is solved by
        blocks with one LU of J. Full steps; converged when the step is
        below the tolerance (the rule of ``_NewtonSystem.newton``), failed
        when it does not converge in ``RESCUE_NEWTON_PER_STEP`` iterations,
        a step is not finite or a step is longer than the one before.
        Returns (Hf, t, ok, iterations)."""
        Hf = _np.array(Hf, dtype=float)
        before = math.inf
        if held[0] == "kink":
            grad = cells.suction_gradient(held[1])
        for k in range(1, RESCUE_NEWTON_PER_STEP + 1):
            checkpoint()                     # v0.1.366 (D362)
            H = cells.complete(Hf)
            R, J, Rt = cells.residual(H, t)
            if held[0] == "arc":
                tau, u0, arc = held[1], held[2], held[3]
                g = float(tau[:-1] @ (Hf - u0[:-1]) + tau[-1] * (t - u0[-1])
                          - arc)
                c, ct = tau[:-1], tau[-1]
            elif held[0] == "kink":
                g = float(cells.suction(H)[held[1]] - held[2])
                c, ct = grad, 0.0
            else:
                g = t - 1.0
                c, ct = _np.zeros(Hf.size), 1.0
            try:
                lu = _splu(J)
                a = lu.solve(R)
                b = lu.solve(Rt)
                dt = (-g + float(c @ a)) / (ct - float(c @ b))
                dh = -a - b * dt
            except Exception:  # noqa: BLE001 — a singular cell ends it
                return Hf, t, False, k
            if not (_np.all(_np.isfinite(dh)) and math.isfinite(dt)):
                return Hf, t, False, k
            size = max(float(_np.max(_np.abs(dh))) if dh.size else 0.0,
                       abs(dt))
            Hf = Hf + dh
            t = t + dt
            if size < self.tolerance:
                return Hf, t, True, k
            if size > before:
                return Hf, t, False, k
            before = size
        return Hf, t, False, RESCUE_NEWTON_PER_STEP

    # ------------------------------------------------------------------
    def _unsettled_nodes(self, result, unknown, active, p_tol, q_tol
                         ) -> list:
        """Seepage-face nodes whose condition the final state violates.

        The unilateral condition is "P = 0 **or** Q = 0, and never water
        entering". A node left free whose pressure came out positive, or
        held at zero pressure while water is being pushed in, breaks it —
        whatever the iteration did on the way there. Asking the answer
        instead of the loop is what makes the budget unable to hide.
        """
        out = []
        for nid in unknown:
            y = self.mesh.nodes[nid].y
            if nid in active:
                q_node = (result.reactions[nid] if result.reactions
                          else 0.0)
                if q_node > q_tol:
                    out.append(nid)
            elif result.total_head and result.total_head[nid] - y > p_tol:
                out.append(nid)
        return out

    # ------------------------------------------------------------------
    def free_surface_points(self, result: SeepageResult,
                            samples: int = 120) -> list:
        """Trace the free surface as the P = 0 iso-line, returned as
        (x, y) samples ordered by x (:func:`free_surface_points`)."""
        return free_surface_points(self.mesh, result, samples)


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
                 max_picard: int = 30,
                 steady_relaxation: Optional[float] = None,
                 steady_tolerance: Optional[float] = None,
                 steady_max_iterations: Optional[int] = None,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # 0 → automatic number of time steps per stage
        self.time_steps = max(0, int(time_steps))
        self.max_picard = max(1, int(max_picard))
        # v0.1.281 (D277): the settings of the initial steady state, when
        # it is computed here (no ``initial_head``); None → this solver's
        # own, as before. See ``_initial_steady``.
        self.steady_relaxation = steady_relaxation
        self.steady_tolerance = steady_tolerance
        self.steady_max_iterations = steady_max_iterations
        #: v0.1.307 (D295) — the steady field the last ``solve_transient``
        #: started from, or None (an ``initial_head`` was given, or the
        #: steady run produced no field). It was a local and was lost.
        self.initial_result = None

    def _initial_steady(self, bcs) -> SeepageResult:
        """The steady state a transient starts from, solved with the
        ``steady_*`` settings where they were given (v0.1.281, D277).

        The project's door solves its steady analysis with w = 0.4, 200
        passes and tolerance 1e-5 (``solve_project_groundwater``); the
        transient solver it builds runs with w = 0.5 and the transient
        tolerance, and its initial steady state used to inherit them. The
        field at t = 0 then differed from the steady analysis of the same
        model and conditions at the level of the tolerance (where the loop
        stops depends on w, D267), and a user comparing the two saw two
        "equal" fields that were not. The door now passes its own settings
        here; a script that passes none gets what it always got."""
        saved = (self.relaxation, self.tolerance, self.max_iterations)
        try:
            if self.steady_relaxation is not None:
                self.relaxation = min(max(self.steady_relaxation, 0.05), 1.0)
            if self.steady_tolerance is not None:
                self.tolerance = self.steady_tolerance
            if self.steady_max_iterations is not None:
                self.max_iterations = max(1, int(self.steady_max_iterations))
            return super().solve_unsaturated(bcs)
        finally:
            self.relaxation, self.tolerance, self.max_iterations = saved

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

        v0.1.269 (D265) — ``result.notes`` carries this step's convergence
        history, ``history`` / ``history_segments`` / ``tolerance`` /
        ``relaxation`` as ``solve_unsaturated`` defines them, so a stage
        (the result of its last step) shows how its last step converged.
        The tuple is unchanged: tests and scripts unpack it.

        What is carried and what is published (v0.1.282, D276)
        ------------------------------------------------------
        A step that converges returns, as the state the next step and the
        stored water start from, the last linear solve — the one ``result``
        publishes (``TRANSIENT_CARRY_LAST_SOLVE``). Until v0.1.281 it carried
        the RELAXED iterate and published the unrelaxed solve, which differ
        by about tolerance·(1 - w)/w: measured on the transients of the
        groundwater verification bank (w = 0.3), 1.6-2.2e-4 m at tolerance
        1e-4 (05-017 to 019) and 1.7-2.1e-6 m at 1e-6 (05-020), exactly that
        bound. The relaxation is a device of the iterations, not of the
        state: carrying the solve keeps the published heads, their
        reactions and the stored water those of one solved system. A step
        that does not converge still carries the relaxed iterate (its
        unrelaxed solve can be far off) and says so. Over a stage the
        change is larger than that per-step bound: carrying another state
        changes the Picard trajectory, and each step stops elsewhere within
        the precision of the relaxed test (next section). Measured: the
        published heads of 05-017 to 019 moved by 4 to 8 mm, 05-020 by
        3e-5 m and the drawdown of problem 102 by 2e-7 m (none of them a
        published figure).

        What the tolerance measures (v0.1.282, D276)
        --------------------------------------------
        The loop stops when the RELAXED change w·max|H_new - H| falls below
        ``tolerance`` and the face has settled, as in the steady solver
        (D267). Judging the unrelaxed change instead (the same as running
        with tolerance·w) was measured and not adopted: on 05-017 to 019 it
        moves the heads by 2 to 10 mm (20 to 100 tolerances: that is how far
        from the stricter answer the relaxed test stops) for 20 % more
        passes, and on 05-020 by 1-4e-5 m; nothing in the bank's published
        figures is that precise, and the steady solver keeps the same test.
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
        p_tol = self._face_p_tol()
        converged = False
        it = 0
        step_result = None
        changes: list[float] = []
        q_tol: Optional[float] = None

        for it in range(1, self.max_picard + 1):
            checkpoint()                     # v0.1.366 (D362)
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
            changes.append(max(abs(H_new[i] - H[i]) for i in range(n)))
            H = H_rel

            # Seepage-face switching (same convention as Phase 3:
            # POSITIVE reaction = water entering the domain)
            if TRANSIENT_FACE_RULE:
                # v0.1.274 (D269): the steady solver's rule, with q_tol
                # from this step's first linear solve (see the switch)
                if unknown and q_tol is None:
                    q_scale = max((abs(r) for r in step_result.reactions),
                                  default=0.0)
                    q_tol = self._face_q_tol(q_scale)
                new_active = (self._switch_seepage_face(
                    active, switches, unknown, H, step_result.reactions,
                    p_tol, q_tol) if unknown else set(active))
            else:
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

        if TRANSIENT_FACE_RULE and unknown and q_tol is not None:
            # v0.1.274 (D269): ask the final state, as the steady solver
            # does, instead of trusting that the loop ended for the right
            # reason (a frozen node stops the set changing too)
            unsettled = self._unsettled_nodes(step_result, unknown, active,
                                              p_tol, q_tol)
            step_result.notes["unsettled_nodes"] = len(unsettled)
            if unsettled:
                converged = False

        step_result.notes.update({
            "history": _change_series(changes),
            "history_segments": [["picard", 0]],
            "tolerance": self.tolerance, "relaxation": self.relaxation})
        if converged and TRANSIENT_CARRY_LAST_SOLVE:
            # v0.1.282 (D276): carry what is published (see the docstring)
            H = list(step_result.total_head)
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
        self._note_degenerate(res)
        self._note_default_props(res)
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

        v0.1.270 (D268) — when the initial field comes from the steady
        run, every stage says whether that run converged:
        ``notes["initial_state_converged"]``, and, when it did not,
        ``notes["initial_state_warning"]`` with the steady run's own
        reason. A separate key: ``warning`` is the stage's own, and a stage
        whose time steps fail writes it. The stages' ``converged`` is NOT
        lowered (the owner's decision): they converged from where they
        started, and lowering it would also take away their free surface
        and flux (``ok``). The one exception is a zero-span stage before
        the first time step: it IS the steady field, unevolved, so it gets
        that field's ``converged`` and its notes — reporting True there
        was simply false. A given ``initial_head`` is the user's, and is
        not judged.

        v0.1.307 (D295) — the steady field itself is kept on
        ``self.initial_result`` (the return value is unchanged), so the
        project can keep the state at t = 0 that every stage started from.
        """
        self.initial_result = None
        if not stages:
            return []
        base_bcs = initial_bcs or (stages[0].bcs
                                   or SeepageBoundaryConditions())

        steady = None
        initial_notes: dict = {}
        if initial_head is not None:
            H = list(initial_head)
        else:
            steady = self._initial_steady(base_bcs)
            if not steady.total_head:
                out = SeepageResult()
                # v0.1.125 — carry the reason through. It used to be
                # replaced by this summary, and the summary is the one
                # thing the caller already knew: the steady solver names
                # the cause precisely — most often "no Dirichlet (head)
                # boundary condition", which is a mistake the user can
                # fix the moment somebody tells them.
                why = (steady.notes.get("error")
                       or steady.notes.get("warning") or "")
                out.notes["error"] = (
                    M.seepage_note(M.INITIAL_FAILED_WHY, why=as_nested(why))
                    if why else M.seepage_note(M.INITIAL_FAILED))
                return [out]
            H = list(steady.total_head)
            self.initial_result = steady
            initial_notes["initial_state_converged"] = bool(steady.converged)
            if not steady.converged:
                why = (steady.notes.get("warning")
                       or steady.notes.get("error") or "")
                initial_notes["initial_state_warning"] = (
                    M.seepage_note(M.INITIAL_NOT_CONVERGED_WHY,
                                   why=as_nested(why))
                    if why else M.seepage_note(M.INITIAL_NOT_CONVERGED))

        results: list = []
        active: set = set()
        t_prev = 0.0
        advanced = False
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
                if steady is not None and not advanced:
                    # v0.1.270 (D268): this stage is the steady field
                    res.converged = bool(steady.converged)
                    res.notes.update(steady.notes)
                # v0.1.125 — ``calculate_sf`` travels with a zero-span
                # stage too. Without it the INITIAL instant of a
                # transient — the one stage that always has zero span —
                # could be ticked *Calculate SF* and quietly produce no
                # factor at all, because the consumer looks for this key
                # and only the stages that actually advanced had it.
                res.notes.update({"stage": k, "time": stage.time,
                                  "time_steps": 0,
                                  "calculate_sf": stage.calculate_sf,
                                  "label": stage.label})
                res.notes.update(initial_notes)
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
                advanced = True
            if last is None:
                last = SeepageResult()
                last.notes["error"] = M.seepage_note(M.NO_TIME_STEP)
                last.notes.update(initial_notes)
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
                # v0.1.200 — the Interpret groundwater window and the
                # agent read the label here, and it was never written: a
                # stage's name reached nobody.
                "label": stage.label,
            })
            last.notes.update(initial_notes)
            if not all_ok:
                # v0.1.273 (D266) — both are settings of the project (the
                # transient's time steps and Picard iterations per step); the
                # relaxation factor this used to suggest is not
                last.notes["warning"] = M.seepage_note(M.STAGE_STEPS, k=k)
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
            # v0.1.275 (D271): the Ks the material is computed with
            k_max = max(k_max, p.saturated_k())
            c_min = min(c_min, max(p.storage_at(-1.0), 1e-9))
        # characteristic diffusion time over one element
        t_elem = c_min * h * h / max(k_max, 1e-30)
        if t_elem <= 0 or not math.isfinite(t_elem):
            return 10
        return int(min(200, max(4, math.ceil(span / t_elem))))


def free_surface_points(mesh, result: SeepageResult,
                        samples: int = 120) -> list:
    """Trace the free surface as the P = 0 iso-line, returned as
    (x, y) samples ordered by x.

    For each of ``samples`` vertical scan lines the highest point
    where the pressure head changes sign is located by linear
    interpolation along mesh element edges.

    v0.1.332 (D329b) — a function of the mesh and the result, so that a
    window holding the project's mesh and result (Interpret) can draw it
    without a solver; ``UnsaturatedSeepageSolver.free_surface_points``
    calls it with its own mesh.
    """
    if not result.ok:
        return []
    P = result.pressure_head
    xs = [nd.x for nd in mesh.nodes]
    x_min, x_max = min(xs), max(xs)
    out: list[tuple[float, float]] = []
    # Collect sign-changing edges once
    seg: list[tuple[float, float]] = []
    for key in mesh.edge_map():
        a, b = key
        pa, pb = P[a], P[b]
        if (pa > 0.0) == (pb > 0.0):
            continue
        na, nb = mesh.nodes[a], mesh.nodes[b]
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
