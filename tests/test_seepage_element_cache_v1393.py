# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The seepage assembly keeps each element's geometry and saturated matrix.

WHAT INVARIANT THIS PROTECTS.

V14 of the compute audit (v0.1.393). ``SeepageSolver.assemble`` recomputed,
at every call, the shape gradients and area of every element, looked up its
material's conductivity tensor and formed its nine entries: bank 05/015
assembled 1600 times, 13.7 s of 46.4, with every element at kr = 1. Now the
geometry and the triplet positions are kept per solver, and so is the
matrix at the saturated conductivity (``K0``) once one is formed; each call
reads the conductivity once per material and takes ``K0`` as it stands
where ``kr`` is absent or exactly the float 1.0 (``x * 1.0`` is ``x``) and
the tensor has the bits ``K0`` was formed with, forming any other element
again with the same expression. The relative permeability's two imports
moved to module level too (2.46 million calls each in that run). 05/015
went from 46.0-46.9 s to 32.1-33.2 s and 05/004 from 7.3-7.5 s to 5.8-5.9 s
(one fresh process per run, ABBA), every published field identical.
Class B: the same expression on the same floats.

1. **The assembly is v0.1.392's, to the bit:** that version's method is
   written out below, and the triplets and the right-hand side are compared
   at a first call and at later ones, with ``kr`` absent, all ones,
   fractional and mixed, with an anisotropic tensor, a flat element and
   loads; with a ``kr`` of numpy numbers, the types of the entries too.
2. **What the cache keeps cannot go stale:** a conductivity edited in place,
   an element given another material, a new mesh, a mesh a script edited
   (the index epoch moved), a mesh code edited and declared with
   ``forget_index``, and a ``kxy`` that goes from 0.0 to -0.0 (``==``
   holds, the entries differ) all assemble as v0.1.392 does.
3. **The lists it returns are the caller's:** changing them does not reach
   the next call.
4. **The work is counted:** the geometry once per element per solver, the
   tensor once per material per call, and the matrices formed — none with
   kr = 1 once kept, one per element with a fractional kr.
5. **A bad mesh or a short ``kr`` raise what they raised.**

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math


def _old_assemble(self, bcs, kr=None):
    """``SeepageSolver.assemble`` of v0.1.392, copied."""
    from ogr_fem2d.solvers.seepage import BCType
    n = self.mesh.node_count
    rows, cols, vals = [], [], []
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
                kij = area * (
                    dNdx[i] * (kxx * dNdx[j] + kxy * dNdy[j])
                    + dNdy[i] * (kxy * dNdx[j] + kyy * dNdy[j])
                )
                rows.append(e.nodes[i])
                cols.append(e.nodes[j])
                vals.append(kij)
    for b in bcs.nodes:
        if b.bc_type == BCType.NODAL_FLOW:
            q[b.node_id] += b.value
    for s in bcs.segments:
        na, nb = self.mesh.nodes[s.node_a], self.mesh.nodes[s.node_b]
        L = math.hypot(nb.x - na.x, nb.y - na.y)
        half = 0.5 * s.q * L
        q[s.node_a] += half
        q[s.node_b] += half
    return rows, cols, vals, q


def _mesh(flat=False):
    """A 3 x 2 strip of triangles over two materials; ``flat`` adds an
    element of no area (its three nodes on a line)."""
    from ogr_fem2d.mesh.mesh import Element, Mesh, Node
    nodes = [Node(3 * j + k, 1.3 * k, 0.9 * j)
             for j in range(3) for k in range(3)]
    elements = []
    for j in range(2):
        for k in range(2):
            a, b = 3 * j + k, 3 * j + k + 1
            c, d = 3 * (j + 1) + k + 1, 3 * (j + 1) + k
            mat = "a" if k == 0 else "b"
            elements.append(Element(len(elements), (a, b, c), mat))
            elements.append(Element(len(elements), (a, c, d), mat))
    if flat:
        elements.append(Element(len(elements), (0, 1, 2), "a"))
    return Mesh(nodes=nodes, elements=elements, target_size=1.0)


def _solver(flat=False):
    from ogr_core.hydraulic import HydraulicProperties
    from ogr_fem2d.solvers.seepage import (BCType, SeepageBoundaryConditions,
                                           SeepageSolver)
    mesh = _mesh(flat)
    props = {"a": HydraulicProperties(ks=2e-5),
             "b": HydraulicProperties(ks=7e-6, k2_k1=0.3, k1_angle_deg=27.0)}
    bcs = SeepageBoundaryConditions()
    bcs.add_node(0, BCType.TOTAL_HEAD, 2.0)
    bcs.add_node(8, BCType.NODAL_FLOW, -1e-6)
    return SeepageSolver(mesh, props, gamma_w=9.81), bcs


def _hex(asm):
    rows, cols, vals, q = asm
    return (list(rows), list(cols), [v.hex() for v in vals],
            [v.hex() for v in q])


def _kr_cases(n):
    return (None, [1.0] * n, [0.37 + 0.05 * i for i in range(n)],
            [1.0 if i % 3 else 0.25 for i in range(n)])


# ======================================================================
class TestTheAssemblyIsV0_1_392s:
    """Invariant 1."""

    def test_first_and_later_calls(self):
        s, bcs = _solver(flat=True)
        n = len(s.mesh.elements)
        for kr in _kr_cases(n) + _kr_cases(n):
            assert _hex(s.assemble(bcs, kr)) == _hex(_old_assemble(s, bcs, kr))

    def test_a_first_call_with_kr(self):
        """The first call builds the cache in its own pass, with kr."""
        for kr_index in range(4):
            s, bcs = _solver()
            kr = _kr_cases(len(s.mesh.elements))[kr_index]
            assert _hex(s.assemble(bcs, kr)) == _hex(_old_assemble(s, bcs, kr))
            assert _hex(s.assemble(bcs, None)) == _hex(_old_assemble(s, bcs))

    def test_a_kr_of_numpy_numbers(self):
        """``kxx * numpy.float64(1.0)`` is a numpy number: the entries were
        numpy numbers, and still are — the shortcut takes a Python float."""
        import numpy as np
        s, bcs = _solver()
        n = len(s.mesh.elements)
        s.assemble(bcs)
        for kr in ([np.float64(1.0)] * n, [np.float64(0.5)] * n):
            new, old = s.assemble(bcs, kr), _old_assemble(s, bcs, kr)
            assert _hex(new) == _hex(old)
            assert [type(v) for v in new[2]] == [type(v) for v in old[2]]
            assert type(new[2][0]) is np.float64


# ======================================================================
class TestTheCacheCannotGoStale:
    """Invariant 2."""

    def _same(self, s, bcs):
        n = len(s.mesh.elements)
        for kr in _kr_cases(n):
            assert _hex(s.assemble(bcs, kr)) == _hex(_old_assemble(s, bcs, kr))

    def test_a_conductivity_edited_in_place(self):
        s, bcs = _solver()
        s.assemble(bcs)
        s.materials["b"].ks = 3e-4
        s.materials["b"].k1_angle_deg = -15.0
        self._same(s, bcs)

    def test_an_element_given_another_material(self):
        s, bcs = _solver()
        s.assemble(bcs)
        s.mesh.elements[0].material_id = "b"
        self._same(s, bcs)

    def test_a_new_mesh(self):
        s, bcs = _solver()
        s.assemble(bcs)
        s.mesh = _mesh(flat=True)
        self._same(s, bcs)

    def test_a_mesh_a_script_edited(self):
        """A node replaced in the same list: what a python_exec script can
        do, and why its run moves the index epoch (v0.1.383)."""
        from ogr_core.fem.mesh import invalidate_mesh_indexes
        from ogr_fem2d.mesh.mesh import Node
        s, bcs = _solver()
        s.assemble(bcs)
        old = s.mesh.nodes[4]
        s.mesh.nodes[4] = Node(old.id, old.x + 0.4, old.y)
        invalidate_mesh_indexes()
        self._same(s, bcs)

    def test_a_mesh_code_edited_and_declared(self):
        """Code that edits a mesh in place calls forget_index (the contract
        of v0.1.383, and what the python_exec guide asks of a script that
        edits a mesh and uses it again): the solver builds again. Without
        it the kept geometry stands — the control that this case can
        fail."""
        from ogr_fem2d.mesh.mesh import Node
        s, bcs = _solver()
        s.assemble(bcs)
        old = s.mesh.nodes[4]
        s.mesh.nodes[4] = Node(old.id, old.x + 0.4, old.y)
        assert _hex(s.assemble(bcs)) != _hex(_old_assemble(s, bcs))
        s.mesh.forget_index()
        self._same(s, bcs)

    def test_the_count_of_forget_index_stays_behind(self):
        """Like the index (v0.1.383): a pool's payload, a statistics sample
        or an undo snapshot pickles the bytes it pickled before."""
        import copy
        import pickle
        mesh = _mesh()
        mesh.forget_index()
        mesh.forget_index()
        assert mesh._forgets == 2
        assert pickle.dumps(mesh) == pickle.dumps(_mesh())
        for clone in (copy.copy(mesh), copy.deepcopy(mesh)):
            assert "_forgets" not in vars(clone)
        assert mesh._forgets == 2

    def test_a_zero_that_changes_sign(self):
        """An isotropic material's angle edited from 0.0 to -0.0: ``kxy``
        goes from 0.0 to -0.0, the tensors compare equal and some entries
        do not (in these two elements, wound the other way). The matrix
        kept at 0.0 must not stand for it."""
        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.mesh.mesh import Element, Mesh, Node
        from ogr_fem2d.solvers.seepage import (SeepageBoundaryConditions,
                                               SeepageSolver)
        pts = [(0.0, 0.0), (1.3, 0.0), (0.0, 0.9), (1.3, 0.9)]
        mesh = Mesh(nodes=[Node(i, x, y) for i, (x, y) in enumerate(pts)],
                    elements=[Element(0, (0, 2, 1), "a"),
                              Element(1, (0, 2, 3), "a")], target_size=1.0)
        hp = HydraulicProperties(ks=2e-5, k1_angle_deg=0.0)
        s = SeepageSolver(mesh, {"a": hp}, gamma_w=9.81)
        bcs = SeepageBoundaryConditions()
        before = _hex(s.assemble(bcs))
        hp.k1_angle_deg = -0.0
        assert hp.conductivity_tensor() == (2e-5, 2e-5, 0.0)
        for kr in (None, [1.0, 1.0], None):
            new = _hex(s.assemble(bcs, kr))
            assert new == _hex(_old_assemble(s, bcs, kr))
            assert new != before


# ======================================================================
class TestTheListsAreTheCallers:
    """Invariant 3."""

    def test_changing_them_does_not_reach_the_next_call(self):
        """The first call's lists and a later one's: they come from two
        paths (the pass that keeps, and the kept triplets)."""
        s, bcs = _solver()
        for _ in range(3):
            rows, cols, vals, q = s.assemble(bcs)
            rows.append(0)
            cols.append(0)
            vals.append(1.0)
            rows[0] = cols[1] = 99
            assert _hex(s.assemble(bcs)) == _hex(_old_assemble(s, bcs))


# ======================================================================
class TestTheWorkIsCounted:
    """Invariant 4."""

    def test_geometry_once_and_tensors_per_call(self):
        from ogr_core.fem.mesh import Element
        from ogr_core.hydraulic.hydraulic_properties import (
            HydraulicProperties)
        s, bcs = _solver(flat=True)
        counts = {"geom": 0, "tensor": 0}
        real_g = Element.__dict__["shape_gradients"]
        real_t = HydraulicProperties.__dict__["conductivity_tensor"]

        def geom(self, mesh):
            counts["geom"] += 1
            return real_g(self, mesh)

        def tensor(self):
            counts["tensor"] += 1
            return real_t(self)

        Element.shape_gradients = geom
        HydraulicProperties.conductivity_tensor = tensor
        try:
            s.assemble(bcs)
            assert counts == {"geom": len(s.mesh.elements),
                              "tensor": len(s.mesh.elements) - 1}
            counts.update(geom=0, tensor=0)
            for _ in range(3):
                s.assemble(bcs, [1.0] * len(s.mesh.elements))
            assert counts == {"geom": 0, "tensor": 3 * 2}
        finally:
            Element.shape_gradients = real_g
            HydraulicProperties.conductivity_tensor = real_t

    def test_matrices_formed(self):
        """kr = 1 forms none after the first call; a fractional kr forms
        every element; a first call with a fractional kr leaves K0 to the
        first call that needs it; a conductivity edited between calls is
        formed once more and then kept."""
        import ogr_fem2d.solvers.seepage as SP
        s, bcs = _solver()
        n = len(s.mesh.elements)
        formed = [0]
        real = SP._element_matrix

        def counting(*args):
            formed[0] += 1
            return real(*args)

        def calls(kr):
            formed[0] = 0
            s.assemble(bcs, kr)
            return formed[0]

        SP._element_matrix = counting
        try:
            assert calls([0.5] * n) == n
            assert [calls(None), calls(None), calls([1.0] * n)] == [n, 0, 0]
            assert calls([0.5] * n) == n
            s.materials["b"].ks = 3e-4
            assert [calls(None), calls(None)] == [n // 2, 0]
        finally:
            SP._element_matrix = real


# ======================================================================
class TestWhatABadInputRaises:
    """Invariant 5."""

    def _raised(self, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - compared, not swallowed
            return type(exc).__name__, str(exc)
        return None

    def test_an_element_on_a_missing_node(self):
        from ogr_fem2d.mesh.mesh import Element
        s, bcs = _solver()
        s.mesh.elements.append(Element(len(s.mesh.elements), (0, 1, 40), "a"))
        new = self._raised(lambda: s.assemble(bcs))
        old = self._raised(lambda: _old_assemble(s, bcs))
        assert new is not None and new == old

    def test_a_short_kr(self):
        s, bcs = _solver()
        short = [1.0] * 3
        new = self._raised(lambda: s.assemble(bcs, short))
        old = self._raised(lambda: _old_assemble(s, bcs, short))
        assert new is not None and new == old
        s.assemble(bcs)                       # and on the cached path
        new = self._raised(lambda: s.assemble(bcs, short))
        assert new == old
