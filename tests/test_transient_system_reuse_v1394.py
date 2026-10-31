# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A transient step keeps the eliminated system while it repeats.

WHAT INVARIANT THIS PROTECTS.

V15 of the compute audit (v0.1.394). Every linear solve of a transient step
assembled its triplets, eliminated the Dirichlet heads in two passes over
them and built the sparse matrix again — building it took longer than
``spsolve`` — although in bank 05/015 (1-D consolidation, a saturated
column) 1590 of the 1600 systems were the one before: only the right-hand
side moves. Now the elimination and the matrix are kept per solver and
built again when the assembled triplets (storage diagonal included) differ
in a bit or a type, or the fixed nodes or their order do; the right-hand
side, ``spsolve`` and the reactions are computed at every call with the
same operations in the same order. The lumped mass is kept too, with the
element cache's validity (v0.1.393). Class B: the same function on the same
inputs.

1. **Each solve is v0.1.393's, to the bit:** that version's
   ``_solve_linear_step``, ``_linear_solve`` and ``_lumped_mass`` are
   written out below, and heads, pressures, reactions (and their types) are
   compared along sequences that repeat the system, change only the
   right-hand side or the fixed heads, change the diagonal, ``kr``, the
   fixed nodes or their order, a conductivity, a zero's sign, or bring
   numpy numbers; and along whole transients.
2. **The key is strict, and a failed construction is not a hit:** counted
   on ``_csr``, a system is built once while it repeats and again at each
   of those changes; a ``_csr`` that raises is tried at every solve, as
   before, and a ``_csr`` replaced between solves is the one used.
3. **A redefined ``_linear_solve`` is called at every solve,** with lists
   of its own, on the class or on the instance.
4. **``spsolve`` leaves the matrix as it took it,** which is what makes a
   kept matrix the one a fresh build would give (checked on the SciPy
   installed, which the CI varies).
5. **The lumped mass is v0.1.393's,** summed once per mesh and handed out
   as a new list, and stale with the geometry.
6. **A fixed node outside the mesh raises what it raised.**

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib


# ----------------------------------------------------------------------
# v0.1.393, copied
def _old_lumped_mass(self):
    m = [0.0] * self.mesh.node_count
    for e in self.mesh.elements:
        a3 = e.area(self.mesh) / 3.0
        for nid in e.nodes:
            m[nid] += a3
    return m


def _old_linear_solve(self, rows, cols, vals, rhs, n):
    import ogr_fem2d.solvers.seepage as SP
    _csr, _spsolve, _np = SP._csr, SP._spsolve, SP._np
    if _csr is not None and _spsolve is not None and _np is not None:
        try:
            A = _csr((vals, (rows, cols)), shape=(n, n))
            x = _spsolve(A.tocsc(), _np.asarray(rhs, dtype=float))
            if x is not None and _np.all(_np.isfinite(x)):
                return [float(v) for v in x]
        except Exception:  # noqa: BLE001
            pass
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


def _old_solve_linear_step(self, bcs, kr, extra_dirichlet, diag, extra_q,
                           fluxes=True):
    from ogr_fem2d.solvers.seepage import SeepageResult
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
    H = _old_linear_solve(self, kr_, kc_, kv_, q, n)
    if H is None:
        return None
    res = SeepageResult()
    res.total_head = list(H)
    res.pressure_head = [H[i] - self.mesh.nodes[i].y for i in range(n)]
    res.pore_pressure = [self.gamma_w * p for p in res.pressure_head]
    if fluxes:
        res.velocity, res.gradient = self._element_fluxes(H, kr)
    res.gamma_w = self.gamma_w
    res.kr = list(kr) if kr is not None else None
    KH = [0.0] * n
    for r, c, v in zip(rows0, cols0, vals0):
        KH[r] += v * H[c]
    res.reactions = [KH[i] - q0[i] for i in range(n)]
    res.converged = True
    self._note_degenerate(res)
    self._note_default_props(res)
    return res


@contextlib.contextmanager
def _as_v0_1_393():
    """The step, the solve and the mass of v0.1.393; given back on exit."""
    import ogr_fem2d.solvers.seepage as SP
    T, S = SP.TransientSeepageSolver, SP.SeepageSolver
    saved = (T.__dict__["_solve_linear_step"], T.__dict__["_lumped_mass"],
             S.__dict__["_linear_solve"])
    T._solve_linear_step = _old_solve_linear_step
    T._lumped_mass = _old_lumped_mass
    S._linear_solve = _old_linear_solve
    try:
        yield
    finally:
        (T._solve_linear_step, T._lumped_mass, S._linear_solve) = saved


@contextlib.contextmanager
def _counting_csr(raises=False):
    """``_csr`` counted (and, with ``raises``, failing); given back."""
    import ogr_fem2d.solvers.seepage as SP
    real = SP._csr
    calls = [0]

    def csr(*args, **kw):
        calls[0] += 1
        if raises:
            raise ValueError("no sparse matrix today")
        return real(*args, **kw)

    SP._csr = csr
    try:
        yield calls
    finally:
        SP._csr = real


# ----------------------------------------------------------------------
def _mesh():
    """A 3 x 4 strip of triangles over two materials, one anisotropic."""
    from ogr_fem2d.mesh.mesh import Element, Mesh, Node
    nodes = [Node(3 * j + k, 1.1 * k, 0.8 * j)
             for j in range(4) for k in range(3)]
    elements = []
    for j in range(3):
        for k in range(2):
            a, b = 3 * j + k, 3 * j + k + 1
            c, d = 3 * (j + 1) + k + 1, 3 * (j + 1) + k
            mat = "a" if k == 0 else "b"
            elements.append(Element(len(elements), (a, b, c), mat))
            elements.append(Element(len(elements), (a, c, d), mat))
    return Mesh(nodes=nodes, elements=elements, target_size=1.0)


def _solver(cls=None):
    from ogr_core.hydraulic import HydraulicProperties
    from ogr_fem2d.solvers.seepage import (BCType, SeepageBoundaryConditions,
                                           TransientSeepageSolver)
    props = {"a": HydraulicProperties(ks=2e-5, specific_storage=1e-3),
             "b": HydraulicProperties(ks=7e-6, k2_k1=0.3, k1_angle_deg=27.0,
                                      specific_storage=2e-3)}
    bcs = SeepageBoundaryConditions()
    for nid in (0, 1, 2):
        bcs.add_node(nid, BCType.TOTAL_HEAD, 2.5)
    bcs.add_node(10, BCType.NODAL_FLOW, -1e-6)
    s = (cls or TransientSeepageSolver)(_mesh(), props, gamma_w=9.81)
    return s, bcs


def _fields(res):
    return ([v.hex() for v in res.total_head],
            [v.hex() for v in res.pressure_head],
            [v.hex() for v in res.pore_pressure],
            [float(v).hex() for v in res.reactions],
            [type(v).__name__ for v in res.reactions],
            repr(res.velocity), repr(res.gradient), res.kr, res.converged,
            sorted(res.notes.items()))


N = 12
ELEMENTS = 12
KR1 = [1.0] * ELEMENTS
KR2 = [0.4 + 0.05 * i for i in range(ELEMENTS)]
D1 = [0.0, 0.0, 0.0] + [1e-4 * (1 + i) for i in range(N - 3)]
D2 = [2.0 * d for d in D1]


def _q(k):
    return [1e-6 * ((i * 7 + k) % 5 - 2) for i in range(N)]


def _step(s, bcs, kr, diag, q, extra):
    """The new solve and v0.1.393's on the same solver, compared."""
    new = s._solve_linear_step(bcs, kr, dict(extra), list(diag), list(q))
    old = _old_solve_linear_step(s, bcs, kr, dict(extra), list(diag),
                                 list(q))
    assert _fields(new) == _fields(old)
    return new


# ======================================================================
class TestEachSolveIsV0_1_393s:
    """Invariants 1 and 2."""

    SEQUENCE = [
        # (kr, diag, right-hand side, extra fixed heads, built?)
        (KR1, D1, 0, {11: 2.4}, True),
        (KR1, D1, 1, {11: 2.4}, False),          # only the right side
        (KR1, D1, 2, {11: 2.31}, False),         # only a fixed value
        (KR1, D2, 2, {11: 2.31}, True),          # another dt
        (KR2, D2, 2, {11: 2.31}, True),          # another kr
        (KR2, D2, 3, {11: 2.31, 9: 2.2}, True),  # the face grew
        (KR2, D2, 3, {9: 2.2, 11: 2.31}, True),  # same nodes, other order
        (KR2, D2, 4, {9: 2.2, 11: 2.31}, False),
        (None, D2, 4, {9: 2.2, 11: 2.31}, True),
        (None, D2, 0, {9: 2.2, 11: 2.31}, False),
    ]

    def test_a_sequence_of_solves(self):
        s, bcs = _solver()
        with _counting_csr() as calls:
            for kr, diag, k, extra, built in self.SEQUENCE:
                before = calls[0]
                new = s._solve_linear_step(bcs, kr, dict(extra), list(diag),
                                           _q(k))
                assert calls[0] - before == (1 if built else 0)
                old = _old_solve_linear_step(s, bcs, kr, dict(extra),
                                             list(diag), _q(k))
                assert _fields(new) == _fields(old)

    def test_the_same_diagonal_values_on_other_nodes(self):
        """The storage values appended in the same order on other nodes:
        ``vals`` repeats and ``rows``/``cols`` do not."""
        s, bcs = _solver()
        da = [0.0] * N
        db = [0.0] * N
        da[4], da[7] = 1e-4, 3e-4
        db[5], db[8] = 1e-4, 3e-4
        with _counting_csr() as calls:
            for diag in (da, db, da):
                s._solve_linear_step(bcs, KR1, {}, list(diag), _q(1))
            assert calls[0] == 3
        for diag in (da, db):
            _step(s, bcs, KR1, diag, _q(2), {})

    def test_a_conductivity_edited_between_solves(self):
        s, bcs = _solver()
        _step(s, bcs, KR1, D1, _q(0), {})
        kept = s._step_system
        s.materials["b"].ks = 3e-6
        _step(s, bcs, KR1, D1, _q(0), {})
        assert s._step_system is not kept

    def test_a_zero_that_changes_sign(self):
        """An isotropic material's angle edited from 0.0 to -0.0: the
        triplets compare equal and two differ in the sign of a zero (the
        mesh of test_seepage_element_cache_v1393). The kept system must
        not stand for them."""
        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.mesh.mesh import Element, Mesh, Node
        from ogr_fem2d.solvers.seepage import (BCType,
                                               SeepageBoundaryConditions,
                                               TransientSeepageSolver)
        pts = [(0.0, 0.0), (1.3, 0.0), (0.0, 0.9), (1.3, 0.9)]
        mesh = Mesh(nodes=[Node(i, x, y) for i, (x, y) in enumerate(pts)],
                    elements=[Element(0, (0, 2, 1), "a"),
                              Element(1, (0, 2, 3), "a")], target_size=1.0)
        hp = HydraulicProperties(ks=2e-5, k1_angle_deg=0.0,
                                 specific_storage=1e-3)
        s = TransientSeepageSolver(mesh, {"a": hp}, gamma_w=9.81)
        bcs = SeepageBoundaryConditions()
        bcs.add_node(0, BCType.TOTAL_HEAD, 1.0)
        diag = [0.0, 1e-4, 2e-4, 3e-4]
        q = [0.0, 1e-6, -1e-6, 2e-6]
        _step(s, bcs, None, diag, q, {})
        kept = s._step_system
        rows, cols, vals, _q0 = s.assemble(bcs)
        hp.k1_angle_deg = -0.0
        rows2, cols2, vals2, _q1 = s.assemble(bcs)
        assert vals2 == vals
        assert [v.hex() for v in vals2] != [v.hex() for v in vals]
        _step(s, bcs, None, diag, q, {})
        assert s._step_system is not kept

    def test_numpy_numbers_on_the_diagonal(self):
        """A diagonal of numpy numbers puts them among the triplets, and
        the reactions come out as numpy numbers: such a system is not kept,
        and each solve is v0.1.393's, types included."""
        import numpy as np
        s, bcs = _solver()
        _step(s, bcs, KR1, D1, _q(0), {})
        kept = s._step_system
        nd = [np.float64(d) for d in D1]
        with _counting_csr() as calls:
            new = [s._solve_linear_step(bcs, KR1, {}, list(nd), _q(k))
                   for k in (1, 2)]
            assert calls[0] == 2, "built at each solve, as before"
        assert s._step_system is kept
        for k, res in zip((1, 2), new):
            old = _old_solve_linear_step(s, bcs, KR1, {}, list(nd), _q(k))
            assert _fields(res) == _fields(old)
        assert any(type(v) is np.float64 for v in new[0].reactions)

    def test_a_csr_that_raises_is_tried_at_every_solve(self):
        s, bcs = _solver()
        with _counting_csr(raises=True) as calls:
            for k in range(3):
                _step(s, bcs, KR1, D1, _q(k), {11: 2.4})
            assert calls[0] == 3 * 2, "the new solve and the old, each time"

    def test_down_to_the_last_fallback(self):
        """No sparse matrix and no dense solve either: Gaussian elimination
        solves, and the next solve tries the sparse matrix again. ``_np``
        is replaced in the module with one whose dense solve fails."""
        import types
        import numpy as np
        import ogr_fem2d.solvers.seepage as SP

        def no_dense(*_a, **_k):
            raise np.linalg.LinAlgError("no dense solve today")

        stub = types.SimpleNamespace(
            asarray=np.asarray, all=np.all, isfinite=np.isfinite,
            zeros=np.zeros, linalg=types.SimpleNamespace(solve=no_dense))
        s, bcs = _solver()
        real = SP._np
        SP._np = stub
        try:
            with _counting_csr(raises=True) as calls:
                for k in range(3):
                    _step(s, bcs, KR1, D1, _q(k), {11: 2.4})
                assert calls[0] == 3 * 2, "the new solve and the old"
        finally:
            SP._np = real

    def test_a_csr_replaced_between_solves_is_the_one_used(self):
        s, bcs = _solver()
        _step(s, bcs, KR1, D1, _q(0), {})
        with _counting_csr() as calls:
            s._solve_linear_step(bcs, KR1, {}, list(D1), _q(1))
            assert calls[0] == 1
            s._solve_linear_step(bcs, KR1, {}, list(D1), _q(2))
            assert calls[0] == 1

    def test_whole_transients(self):
        """A saturated column, whose steps repeat their system, and one
        with an unsaturated zone (the model of test_published_fluxes_v1392),
        whose kr moves: every stage as v0.1.393 publishes it."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        from ogr_fem2d.mesh.mesh import Element, Mesh, Node
        from ogr_fem2d.solvers.seepage import (BCType,
                                               SeepageBoundaryConditions,
                                               TransientSeepageSolver,
                                               TransientStage)

        def column(unsaturated):
            dz, rows = 0.1, 20
            nodes = [Node(2 * j + k, k * dz, j * dz)
                     for j in range(rows + 1) for k in (0, 1)]
            els = []
            for j in range(rows):
                a, b, c, d = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
                els.append(Element(len(els), (a, b, c), "m"))
                els.append(Element(len(els), (a, c, d), "m"))
            mesh = Mesh(nodes=nodes, elements=els, target_size=dz)
            if unsaturated:
                hp = HydraulicProperties(
                    ks=1e-5, model=PermeabilityModel.USER_DEFINED,
                    user_curve=[(0.0, 1e-5), (10.0, 1e-6), (100.0, 1e-8)],
                    wc_alpha=1.0, vg_n=1.5, wc_sat=0.4, wc_res=0.05,
                    specific_storage=1e-3)
            else:
                hp = HydraulicProperties(ks=1e-5, specific_storage=1e-3)
            bcs = SeepageBoundaryConditions()
            for nid in (0, 1):
                bcs.add_node(nid, BCType.TOTAL_HEAD, 1.5)
            for nid in (2 * rows, 2 * rows + 1):
                bcs.add_node(nid, BCType.TOTAL_HEAD, 2.5 if not unsaturated
                             else 1.0)
            return mesh, {"m": hp}, bcs

        def run(unsaturated):
            mesh, props, bcs = column(unsaturated)
            s = TransientSeepageSolver(mesh, props, gamma_w=9.81,
                                       relaxation=0.5, tolerance=1e-6,
                                       max_picard=300, time_steps=3)
            stages = [TransientStage(time=0.0, label="t0", bcs=bcs),
                      TransientStage(time=900.0, label="a", bcs=bcs),
                      TransientStage(time=3600.0, label="b", bcs=bcs)]
            out = s.solve_transient(stages,
                                    initial_head=[0.5] * mesh.node_count)
            return [_fields(r) + (r.iterations,) for r in out]

        for unsaturated in (False, True):
            with _counting_csr() as calls:
                new = run(unsaturated)
                built = calls[0]
            with _as_v0_1_393(), _counting_csr() as calls:
                old = run(unsaturated)
                solves = calls[0]
            assert new == old
            if not unsaturated:
                assert built < solves / 3, (built, solves)


# ======================================================================
class TestARedefinedLinearSolve:
    """Invariant 3."""

    def _check(self, s, bcs, seen):
        for k in range(3):
            _step(s, bcs, KR1, D1, _q(k), {11: 2.4})
        assert len(seen) == 3
        assert len({id(rows) for rows in seen}) == 3, "lists of its own"

    def test_on_the_instance(self):
        from ogr_fem2d.solvers.seepage import SeepageSolver
        s, bcs = _solver()
        seen = []

        def solve(rows, cols, vals, rhs, n):
            seen.append(rows)
            return SeepageSolver._linear_solve(s, rows, cols, vals, rhs, n)

        s._linear_solve = solve
        self._check(s, bcs, seen)
        assert getattr(s, "_step_system", None) is None

    def test_on_a_subclass(self):
        from ogr_fem2d.solvers.seepage import TransientSeepageSolver
        seen = []

        class Mine(TransientSeepageSolver):
            def _linear_solve(self, rows, cols, vals, rhs, n):
                seen.append(rows)
                return super()._linear_solve(rows, cols, vals, rhs, n)

        s, bcs = _solver(Mine)
        self._check(s, bcs, seen)


# ======================================================================
class TestSpsolveLeavesTheMatrix:
    """Invariant 4."""

    def test_the_kept_matrix_solves_as_a_fresh_one(self):
        import numpy as np
        import ogr_fem2d.solvers.seepage as SP
        s, bcs = _solver()
        rows, cols, vals, _q0 = s.assemble(bcs)
        n = s.mesh.node_count
        for i in range(n):
            rows.append(i)
            cols.append(i)
            vals.append(1e-3)
        kept = SP._csr((vals, (rows, cols)), shape=(n, n)).tocsc()
        arrays = (kept.data.copy(), kept.indices.copy(), kept.indptr.copy())
        for k in range(3):
            b = np.asarray(_q(k), dtype=float)
            x = SP._spsolve(kept, b)
            fresh = SP._spsolve(
                SP._csr((vals, (rows, cols)), shape=(n, n)).tocsc(), b)
            assert [v.hex() for v in x] == [v.hex() for v in fresh]
            assert all(np.array_equal(a, b2) and a.dtype == b2.dtype
                       for a, b2 in zip(arrays, (kept.data, kept.indices,
                                                 kept.indptr)))


# ======================================================================
class TestTheLumpedMass:
    """Invariant 5."""

    def test_v0_1_393s_once_per_mesh(self):
        from ogr_core.fem.mesh import Element
        s, _bcs = _solver()
        real = Element.__dict__["area"]
        calls = [0]

        def area(self, mesh):
            calls[0] += 1
            return real(self, mesh)

        Element.area = area
        try:
            first = s._lumped_mass()
            assert calls[0] == ELEMENTS
            first[0] = 99.0
            for _ in range(3):
                mass = s._lumped_mass()
                assert ([v.hex() for v in mass]
                        == [v.hex() for v in _old_lumped_mass(s)])
                mass[1] = 99.0
            assert calls[0] == ELEMENTS + 3 * ELEMENTS, "the old ones only"
        finally:
            Element.area = real

    def test_stale_with_the_geometry(self):
        from ogr_core.fem.mesh import invalidate_mesh_indexes
        from ogr_fem2d.mesh.mesh import Node
        s, _bcs = _solver()
        s._lumped_mass()

        def moved():
            old = s.mesh.nodes[4]
            s.mesh.nodes[4] = Node(old.id, old.x + 0.3, old.y)

        moved()
        assert s._lumped_mass() != _old_lumped_mass(s), "the control"
        s.mesh.forget_index()
        assert s._lumped_mass() == _old_lumped_mass(s)
        moved()
        invalidate_mesh_indexes()
        assert s._lumped_mass() == _old_lumped_mass(s)
        s.mesh = _mesh()
        assert s._lumped_mass() == _old_lumped_mass(s)


# ======================================================================
class TestWhatABadInputRaises:
    """Invariant 6."""

    def _raised(self, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - compared, not swallowed
            return type(exc).__name__, str(exc)
        return None

    def test_a_fixed_node_outside_the_mesh(self):
        s, bcs = _solver()
        bad = {40: 1.0}
        new = self._raised(lambda: s._solve_linear_step(
            bcs, KR1, dict(bad), list(D1), _q(0)))
        old = self._raised(lambda: _old_solve_linear_step(
            s, bcs, KR1, dict(bad), list(D1), _q(0)))
        assert new is not None and new == old
        s._solve_linear_step(bcs, KR1, {}, list(D1), _q(0))
        new = self._raised(lambda: s._solve_linear_step(
            bcs, KR1, dict(bad), list(D1), _q(0)))
        assert new == old
