# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.383 (V5 of the compute audit) — ``Mesh.locate`` answers through a grid
index with the SAME element object the linear scan gives, for every query.

Why it matters: the LEM coupling interpolates the finite-element pore
pressure at every slice base through ``Mesh.locate``. On bank 010 the scan
was 87 % of the case, 549 of 1441 elements tested per query. An index that
returned another element for one point in a million would move a factor of
safety, and nothing downstream would notice.

What carries the identity: the index (``ogr_core.fem.mesh._Locator``) only
narrows WHICH elements are tested. Each candidate still goes through
``Element.contains`` with its default tolerance, in list order. An element
can be skipped only through its CERTIFIED box: a floating-point bound (the
standard model of Higham, 2002, §2.2) guarantees that every point
``contains`` accepts lies inside it. An element whose bound cannot be
certified is tested on every query.

The oracle is the scan of 0.1.382, copied literally below. The points are
the ones where a wrong margin or a wrong order would show:
- vertices, edge points and their extensions, one and two ulps to either
  side;
- the corners of the certified boxes;
- points around and outside the mesh;
- overlapping elements, an uncertifiable sliver and a flat triangle;
- the types and meshes the index must leave to the scan.

Every test is well under a second: a mesh of 80 elements, a few thousand
queries.
"""
import copy
import inspect
import math
import pickle
import random
from dataclasses import fields

import numpy as np

from ogr_core.fem import mesh as mesh_module
from ogr_core.fem.mesh import Element, Mesh, Node


def _scan(mesh, x, y):
    """``Mesh.locate`` of 0.1.382, literally: the oracle."""
    for e in mesh.elements:
        if e.contains(mesh, x, y):
            return e
    return None


def _grid_mesh(nx=8, ny=5, h=1.25, x0=512.0, y0=-64.0, jitter=0.3, seed=11):
    """A graded-looking mesh: a grid of squares with jittered inner nodes,
    each square split along alternating diagonals (2 * nx * ny elements)."""
    rng = random.Random(seed)
    nodes = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + i * h, y0 + j * h
            if 0 < i < nx and 0 < j < ny:
                x += rng.uniform(-jitter, jitter) * h
                y += rng.uniform(-jitter, jitter) * h
            nodes.append(Node(len(nodes), x, y))
    elements = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c = a + 1, a + nx + 1
            d = c + 1
            pairs = (((a, b, d), (a, d, c)) if (i + j) % 2
                     else ((a, b, c), (b, d, c)))
            for t in pairs:
                elements.append(Element(len(elements), t))
    return Mesh(nodes=nodes, elements=elements)


def _indexed(mesh):
    """``mesh`` with its index built now, checked to be a real one."""
    mesh._locator = mesh_module._build_locator(mesh)
    loc = mesh._locator
    assert loc.fits(mesh) and loc.fx0 < loc.fx1 and loc.cells != [()]
    return loc


def _ulps(v, k):
    """``v`` moved ``k`` ulps (negative: downwards)."""
    step = math.inf if k > 0 else -math.inf
    for _ in range(abs(k)):
        v = math.nextafter(v, step)
    return v


def _around(x, y, ks=(-2, -1, 0, 1, 2)):
    return [(_ulps(x, a), _ulps(y, b)) for a in ks for b in ks]


def _same_as_the_scan(mesh, points, loc=None):
    """Every point answers with the scan's object; returns how many went
    through the index (``loc.takes``)."""
    taken = 0
    for x, y in points:
        assert mesh.locate(x, y) is _scan(mesh, x, y), (x, y)
        if loc is not None and loc.takes(x, y):
            taken += 1
    return taken


class TestTheIndexAnswersAsTheScan:

    def test_vertices_and_the_ulps_around_them(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        pts = [p for n in mesh.nodes for p in _around(n.x, n.y)]
        assert _same_as_the_scan(mesh, pts, loc) == len(pts)

    def test_edge_points_their_extensions_and_their_ulps(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        edges = {tuple(sorted((u, v))) for e in mesh.elements
                 for u, v in zip(e.nodes, e.nodes[1:] + e.nodes[:1])}
        pts = []
        for u, v in sorted(edges):
            a, b = mesh.nodes[u], mesh.nodes[v]
            for f in (0.25, 0.5, 0.75, -0.25, 1.25):
                x, y = a.x + f * (b.x - a.x), a.y + f * (b.y - a.y)
                pts.extend(_around(x, y, ks=(-1, 0, 1)))
        assert _same_as_the_scan(mesh, pts, loc) == len(pts)

    def test_the_corners_of_every_certified_box(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        pts = []
        for e in mesh.elements:
            (x1, y1), (x2, y2), (x3, y3) = e.coords(mesh)
            box = mesh_module._certified_box(x1, y1, x2, y2, x3, y3,
                                             loc.fx0, loc.fx1, loc.fy0, loc.fy1)
            assert box is not None
            for x in box[:2]:
                for y in box[2:]:
                    pts.extend(_around(x, y, ks=(-1, 0, 1)))
        assert _same_as_the_scan(mesh, pts, loc) == len(pts)

    def test_random_points_on_around_and_beyond_the_mesh(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        rng = random.Random(5)
        inside = [(rng.uniform(loc.fx0, loc.fx1), rng.uniform(loc.fy0, loc.fy1))
                  for _ in range(1500)]
        assert _same_as_the_scan(mesh, inside, loc) == len(inside)
        beyond = [(loc.fx1 + 1.0, loc.fy0), (loc.fx0, loc.fy1 * 2.0 + 1e3),
                  (_ulps(loc.fx1, 1), loc.fy0), (loc.fx0, _ulps(loc.fy0, -1)),
                  (math.nan, loc.fy0), (loc.fx0, math.inf), (-math.inf, 0.0),
                  (1e17, 1e17)]
        assert _same_as_the_scan(mesh, beyond, loc) == 0
        # Why far queries take the scan: that far, every difference to a
        # vertex rounds alike, the numerators come out 0 and contains
        # accepts the first element. The bound only holds inside the far box.
        assert _scan(mesh, 1e17, 1e17) is mesh.elements[0]

    def test_the_tips_of_what_contains_accepts(self):
        # contains accepts the triangle scaled by 1 + 3 tol about its
        # centroid, whose tips stand 2 tol W beyond the vertex box: the
        # farthest an accepted point gets. The certified margin is about
        # 6 tol W; a margin cut below the tips, or a contains widened past
        # its tolerance, shows here first.
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        tol = mesh_module.CONTAINS_TOL
        tips = []
        for e in mesh.elements:
            v = e.coords(mesh)
            box = mesh_module._certified_box(*v[0], *v[1], *v[2], loc.fx0,
                                             loc.fx1, loc.fy0, loc.fy1)
            cx, cy = sum(p[0] for p in v) / 3.0, sum(p[1] for p in v) / 3.0
            for vx, vy in v:
                for lam in (0.5, 0.9, 0.99, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
                    x = vx + 3.0 * tol * lam * (vx - cx)
                    y = vy + 3.0 * tol * lam * (vy - cy)
                    for p in _around(x, y, ks=(-1, 0, 1)):
                        if e.contains(mesh, *p):
                            assert (box[0] <= p[0] <= box[1]
                                    and box[2] <= p[1] <= box[3]), p
                        if lam == 0.99:
                            tips.append(p)
        assert _same_as_the_scan(mesh, tips, loc) == len(tips)

    def test_the_types_the_index_leaves_to_the_scan(self):
        # Only exact Python floats: what every caller of the program passes.
        # numpy's float64 is a float subclass that honours numpy's error
        # state, and another subclass could redefine the arithmetic.
        class Shifted(float):
            def __rsub__(self, other):
                return float(other) - float(self) - 0.25

        mesh = _grid_mesh()
        loc = _indexed(mesh)
        e = mesh.elements[30]
        cx = sum(mesh.nodes[i].x for i in e.nodes) / 3.0
        cy = sum(mesh.nodes[i].y for i in e.nodes) / 3.0
        assert _same_as_the_scan(mesh, [(cx, cy)], loc) == 1
        scanned = [(np.float64(cx), np.float64(cy)), (np.float64(cx), cy),
                   (cx, np.float64(cy)), (np.float32(cx), np.float32(cy)),
                   (int(cx), int(cy)), (True, False),
                   (Shifted(cx), Shifted(cy)), (cx, Shifted(cy))]
        assert _same_as_the_scan(mesh, scanned, loc) == 0


class TestOrderAndUncertifiedElements:

    def test_overlapping_elements_answer_with_the_first_in_list_order(self):
        base = _grid_mesh()
        n = len(base.nodes)
        nodes = list(base.nodes) + [Node(n, 400.0, -200.0),
                                    Node(n + 1, 700.0, -200.0),
                                    Node(n + 2, 550.0, 200.0)]
        cover = Element(0, (n, n + 1, n + 2))     # holds the whole grid
        doubled = [Element(k, e.nodes) for k, e in
                   enumerate(reversed(base.elements), start=1)]
        rng = random.Random(9)
        for first, rest in (([cover], base.elements + doubled),
                            ([], base.elements + doubled + [cover])):
            mesh = Mesh(nodes=nodes, elements=first + list(rest))
            loc = _indexed(mesh)
            pts = [(rng.uniform(511.0, 523.0), rng.uniform(-65.0, -57.0))
                   for _ in range(400)]
            pts += [p for nd in base.nodes[::5] for p in _around(nd.x, nd.y)]
            assert _same_as_the_scan(mesh, pts, loc) == len(pts)

    def test_a_sliver_and_a_flat_triangle_are_tested_on_every_query(self):
        # The sliver lies one ulp of y off the mesh's diagonal: |det| is
        # 5.7e-14, above contains' 1e-15, but its rounding can be as big,
        # so it has no certified box, and contains still accepts points
        # near the chord. First in the list, it must win wherever it does.
        base = _grid_mesh()
        n = len(base.nodes)
        nodes = list(base.nodes) + [
            Node(n, 512.0, -64.0), Node(n + 1, 520.0, -56.0),
            Node(n + 2, 516.0, math.nextafter(-60.0, math.inf)),
            Node(n + 3, 513.0, -60.0), Node(n + 4, 521.0, -60.0),
            Node(n + 5, 517.0, -60.0)]
        sliver = Element(0, (n, n + 1, n + 2))
        flat = Element(1, (n + 3, n + 4, n + 5))          # det exactly 0
        mesh = Mesh(nodes=nodes,
                    elements=[sliver] + list(base.elements) + [flat])
        loc = _indexed(mesh)
        assert loc.always == (0, len(mesh.elements) - 1)
        pts = []
        for f in [i / 20 for i in range(21)]:
            pts.extend(_around(512.0 + 8.0 * f, -64.0 + 8.0 * f,
                               ks=range(-3, 4)))
            pts.extend(_around(513.0 + 8.0 * f, -60.0, ks=(-1, 0, 1)))
        assert _same_as_the_scan(mesh, pts, loc) == len(pts)
        assert any(mesh.locate(x, y) is sliver for x, y in pts)

    def test_the_always_list_keeps_list_order_with_both_kinds(self):
        # Uncertified elements enter the always list first, boxes over
        # too many cells after them: only sorting puts the cover (position
        # 0, moved there) before the sliver (position 1), and the merge
        # needs that order to answer as the scan does.
        base = _grid_mesh()
        n = len(base.nodes)
        nodes = list(base.nodes) + [
            Node(n, 400.0, -200.0), Node(n + 1, 700.0, -200.0),
            Node(n + 2, 550.0, 200.0), Node(n + 3, 512.0, -64.0),
            Node(n + 4, 520.0, -56.0),
            Node(n + 5, 516.0, math.nextafter(-60.0, math.inf))]
        cover = Element(0, (n, n + 1, n + 2))
        sliver = Element(1, (n + 3, n + 4, n + 5))
        mesh = Mesh(nodes=nodes, elements=[cover, sliver] + list(base.elements))
        loc = _indexed(mesh)
        assert loc.always == (0, 1)
        pts = [p for i in range(21)
               for p in _around(512.0 + 0.4 * i, -64.0 + 0.4 * i,
                                ks=range(-3, 4))]
        assert any(sliver.contains(mesh, x, y) for x, y in pts)
        assert _same_as_the_scan(mesh, pts, loc) == len(pts)

    def test_the_lists_cover_every_element_once_and_in_order(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        listed = set()
        for cell in loc.cells:
            assert list(cell) == sorted(set(cell))
            listed.update(cell)
        assert list(loc.always) == sorted(set(loc.always))
        assert not listed & set(loc.always)
        assert listed | set(loc.always) == set(range(len(mesh.elements)))


class TestTheCertifiedBox:
    """The bound itself, on single triangles chosen to strain it: no point
    ``contains`` accepts lies outside its box."""

    TRIANGLES = (
        ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
        ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)),
        ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0)),                 # clockwise
        ((0.0, 0.0), (10.0, 0.0), (5.0, 1e-3)),               # needle
        ((5e5, 4e6), (5e5 + 2.0, 4e6), (5e5 + 0.5, 4e6 + 1.5)),   # UTM-like
        ((1e-6, 2e-6), (3e-6, 2e-6), (2e-6, 4e-6)),           # micrometres
    )

    def test_contains_accepts_nothing_outside_the_box(self):
        rng = random.Random(3)
        for v in self.TRIANGLES:
            nodes = [Node(i, x, y) for i, (x, y) in enumerate(v)]
            mesh = Mesh(nodes=nodes, elements=[Element(0, (0, 1, 2))])
            e = mesh.elements[0]
            xs, ys = [p[0] for p in v], [p[1] for p in v]
            size = max(max(xs) - min(xs), max(ys) - min(ys))
            far = (min(xs) - size, max(xs) + size, min(ys) - size, max(ys) + size)
            box = mesh_module._certified_box(*v[0], *v[1], *v[2], *far)
            assert box is not None, v
            pts = []
            for x in box[:2]:
                for y in box[2:]:
                    pts.extend(_around(x, y, ks=range(-4, 5)))
            for (ax, ay), (bx, by) in zip(v, v[1:] + v[:1]):
                for f in (-1e-9, 0.0, 0.5, 1.0, 1.0 + 1e-9, -0.5, 1.5):
                    x, y = ax + f * (bx - ax), ay + f * (by - ay)
                    pts.extend(_around(x, y, ks=range(-3, 4)))
            pts += [(rng.uniform(box[0] - size * 1e-6, box[1] + size * 1e-6),
                     rng.uniform(box[2] - size * 1e-6, box[3] + size * 1e-6))
                    for _ in range(300)]
            for x, y in pts:
                if e.contains(mesh, x, y):
                    assert box[0] <= x <= box[1] and box[2] <= y <= box[3], (v, x, y)

    def test_what_has_no_box(self):
        # Three points one ulp off a diagonal 16 m long: |det| = 2.8e-14 is
        # above DEGENERATE_DET, so contains can accept, but its rounding can
        # be as big: the determinant is not known to its sign.
        x = math.nextafter(8.0, 16.0)
        det = (16.0 - 0.0) * (8.0 - 0.0) - (x - 0.0) * (16.0 - 0.0)
        assert abs(det) >= mesh_module.DEGENERATE_DET
        assert mesh_module._certified_box(0.0, 0.0, 16.0, 16.0, x, 8.0,
                                          -16.0, 32.0, -16.0, 32.0) is None
        # Below DEGENERATE_DET (contains never accepts) and an overflowing
        # determinant (contains can accept, the bound cannot follow it).
        assert mesh_module._certified_box(0.0, 0.0, 1.0, 0.0, 0.0, 5e-16,
                                          -1.0, 2.0, -1.0, 2.0) is None
        assert mesh_module._certified_box(0.0, 0.0, 2e154, 0.0, 0.0, 1e154,
                                          -2e154, 4e154, -1e154, 2e154) is None


class TestWhatTheIndexAssumes:

    def test_the_bound_reads_the_tolerance_and_threshold_contains_uses(self):
        tol = inspect.signature(Element.contains).parameters["tol"].default
        assert tol == mesh_module.CONTAINS_TOL

        def tri(h):
            return Mesh(nodes=[Node(0, 0.0, 0.0), Node(1, 1.0, 0.0),
                               Node(2, 0.0, h)],
                        elements=[Element(0, (0, 1, 2))])

        above = tri(2.0 * mesh_module.DEGENERATE_DET)
        below = tri(0.5 * mesh_module.DEGENERATE_DET)
        assert above.elements[0].barycentric(above, 0.1, 0.0) is not None
        assert below.elements[0].barycentric(below, 0.1, 0.0) is None

    def test_the_index_is_not_a_field_of_the_mesh(self):
        # A field would enter __init__, __eq__, __repr__ and asdict: two
        # equal meshes would stop being equal once one of them is indexed.
        assert [f.name for f in fields(Mesh)] == [
            "nodes", "elements", "target_size", "notes"]
        a, b = _grid_mesh(), _grid_mesh()
        _indexed(a)
        assert a == b and repr(a) == repr(b)


class TestLifecycle:

    def test_the_index_comes_after_some_scans(self):
        mesh = _grid_mesh()
        n = mesh_module._LOCATOR_AFTER_SCANS
        for k in range(n - 1):
            mesh.locate(512.5 + 0.01 * k, -63.5)
        assert getattr(mesh, "_locator", None) is None
        mesh.locate(512.5, -63.5)
        assert mesh._locator.fits(mesh) and mesh._locator.cells != [()]

    def test_the_index_is_published_whole(self):
        # The build runs while the mesh still has no index, and the finished
        # one arrives in a single assignment: another thread reading
        # _locator meanwhile sees None (and scans) or a complete index.
        mesh = _grid_mesh()
        seen = []
        real = mesh_module._grid_of

        def spy(nodes, elements):
            seen.append(getattr(mesh, "_locator", None))
            return real(nodes, elements)

        mesh_module._grid_of = spy
        try:
            for _ in range(mesh_module._LOCATOR_AFTER_SCANS):
                mesh.locate(515.0, -61.0)
        finally:
            mesh_module._grid_of = real
        assert seen == [None] and mesh._locator.cells != [()]

    def test_it_tests_a_handful_of_elements_where_the_scan_tests_dozens(self):
        mesh = _grid_mesh()
        _indexed(mesh)
        rng = random.Random(2)
        pts = [(rng.uniform(512.2, 521.8), rng.uniform(-63.8, -57.9))
               for _ in range(300)]
        calls = [0]
        real = Element.contains

        def counted(self, *a, **k):
            calls[0] += 1
            return real(self, *a, **k)

        Element.contains = counted
        try:
            for x, y in pts:
                mesh.locate(x, y)
            indexed = calls[0]
            calls[0] = 0
            for x, y in pts:
                _scan(mesh, x, y)
            scanned = calls[0]
        finally:
            Element.contains = real
        assert indexed <= 3 * len(pts)
        assert scanned >= 25 * len(pts)

    def test_the_index_does_not_travel_with_a_copy(self):
        mesh = _grid_mesh()
        loc = _indexed(mesh)
        mesh._locate_scans = 3
        for clone in (pickle.loads(pickle.dumps(mesh)), copy.copy(mesh),
                      copy.deepcopy(mesh)):
            assert "_locator" not in vars(clone)
            assert "_locate_scans" not in vars(clone)
            assert clone == mesh
            _same_as_the_scan(clone, [(515.0, -61.0), (0.0, 0.0)])
        assert mesh._locator is loc and mesh._locate_scans == 3
        assert pickle.dumps(mesh) == pickle.dumps(_grid_mesh())

    def test_replacing_or_resizing_the_lists_drops_the_index(self):
        mesh = _grid_mesh()
        _indexed(mesh)
        mesh.nodes = [Node(n.id, n.x + 100.0, n.y) for n in mesh.nodes]
        _same_as_the_scan(mesh, [(615.0, -61.0), (515.0, -61.0)])
        assert mesh._locator is None
        _indexed(mesh)
        mesh.elements.append(Element(len(mesh.elements), (0, 1, 9)))
        assert mesh.locate(612.6, -63.9) is _scan(mesh, 612.6, -63.9)
        assert mesh._locator is None

    def test_a_mesh_the_bound_does_not_cover_keeps_scanning(self):
        class Everywhere(Element):
            def contains(self, mesh, x, y, tol=mesh_module.CONTAINS_TOL):
                return True

        def square(xy):
            return Mesh(nodes=[Node(i, x, y) for i, (x, y) in enumerate(xy)],
                        elements=[Element(0, (0, 1, 2)), Element(1, (1, 3, 2))])

        ints = square(((0, 0), (4, 0), (0, 4), (4, 4)))
        singles = square(tuple((np.float32(x), np.float32(y)) for x, y in
                               ((0.0, 0.0), (4.0, 0.0), (0.0, 4.0), (4.0, 4.0))))
        huge = square(((0.0, 0.0), (4e100, 0.0), (0.0, 4e100), (4e100, 4e100)))
        sub = _grid_mesh()      # a subclass could redefine contains: it does
        sub.elements[7] = Everywhere(7, sub.elements[7].nodes)
        for mesh, pts in ((ints, [(1.0, 1.0), (3.0, 3.5)]),
                          (singles, [(1.0, 1.0), (3.0, 3.5)]),
                          (huge, [(1.0, 1.0), (3e100, 3.5e100)]),
                          (sub, [(520.0, -58.5), (513.0, -63.0)])):
            loc = mesh_module._build_locator(mesh)
            mesh._locator = loc
            assert loc.fits(mesh)
            assert _same_as_the_scan(mesh, pts, loc) == 0
        assert sub.locate(520.0, -58.5) is sub.elements[7]

    def test_forget_index_after_an_edit_in_place(self):
        # The program replaces a mesh; code that edits one in place calls
        # forget_index, and the next index is of the new geometry.
        mesh = _grid_mesh()
        stale = _indexed(mesh)
        mesh._locate_scans = 5
        moved = mesh.nodes[22]
        mesh.nodes[22] = Node(22, moved.x + 0.6, moved.y)
        rng = random.Random(4)
        pts = [(rng.uniform(512.0, 522.0), rng.uniform(-64.0, -57.75))
               for _ in range(200)]
        pts += [p for n in mesh.nodes[17:28] for p in _around(n.x, n.y)]
        pts += TestScriptsMakeTheIndexStale._beside_node(mesh, 22)
        assert TestScriptsMakeTheIndexStale._stale_somewhere(stale, mesh, pts)
        mesh.forget_index()
        assert "_locator" not in vars(mesh) and "_locate_scans" not in vars(mesh)
        _same_as_the_scan(mesh, pts)
        assert mesh._locator.fits(mesh) and mesh._locator.cells != [()]
        assert _same_as_the_scan(mesh, pts, mesh._locator) == len(pts)

    def test_lists_the_index_cannot_measure_are_scanned_without_failing(self):
        # Out of contract, but the scan answered them: nodes=None with no
        # elements, or the elements as an iterator, which the first scan
        # spends. The build asks for a length; its TypeError must not
        # replace the scan's answer on the call that would have built it.
        n = 3 * mesh_module._LOCATOR_AFTER_SCANS
        no_nodes = Mesh(nodes=None, elements=[])
        assert all(no_nodes.locate(0.2, 0.2) is None for _ in range(n))
        assert getattr(no_nodes, "_locator", None) is None
        nodes = [Node(0, 0.0, 0.0), Node(1, 1.0, 0.0), Node(2, 0.0, 1.0)]
        spent = Mesh(nodes=nodes, elements=iter([Element(0, (0, 1, 2))]))
        assert spent.locate(0.2, 0.2) is not None
        assert all(spent.locate(0.2, 0.2) is None for _ in range(n))

    def test_a_mesh_that_cannot_be_read_is_scanned_and_fails_as_the_scan(self):
        mesh = Mesh(nodes=[Node(0, 0.0, 0.0), Node(1, 1.0, 0.0),
                           Node(2, 0.0, 1.0)],
                    elements=[Element(0, (0, 1, 2)), Element(1, (0, 1, 7))])
        loc = mesh_module._build_locator(mesh)
        assert not loc.takes(0.2, 0.2)
        mesh._locator = loc
        assert mesh.locate(0.2, 0.2) is mesh.elements[0]
        for find in (mesh.locate, lambda x, y: _scan(mesh, x, y)):
            try:
                find(0.9, 0.9)
            except IndexError:
                pass
            else:
                raise AssertionError("the element with node 7 raises here")


class TestScriptsMakeTheIndexStale:
    """A user's script can edit a mesh in place (python_exec, the window's
    terminal), which no index notices: both runners make every index stale
    around it (decided by the owner in v0.1.383). The script moves an inner
    node 0.6 m: points beside it change element, and the old index answers
    some of them with None or another element (checked first, so the test
    cannot pass on a move the old index would have survived)."""

    SCRIPT = "n = m.nodes[22]\nm.nodes[22] = Node(22, n.x + 0.6, n.y)"

    @staticmethod
    def _indexed_by_use():
        mesh = _grid_mesh()
        for _ in range(mesh_module._LOCATOR_AFTER_SCANS):
            mesh.locate(515.0, -61.0)
        assert mesh._locator is not None
        return mesh

    @staticmethod
    def _beside_node(mesh, k):
        n = mesh.nodes[k]
        steps = (-0.45, -0.3, -0.15, -0.05, 0.05, 0.15, 0.3, 0.45)
        return [(n.x + dx, n.y + dy) for dx in steps for dy in steps]

    @staticmethod
    def _stale_somewhere(stale, mesh, pts):
        return any(stale.find(mesh, x, y) is not _scan(mesh, x, y)
                   for x, y in pts)

    def test_invalidate_mesh_indexes_makes_every_index_stale(self):
        saved = mesh_module._INDEX_EPOCH
        try:
            a, b = _grid_mesh(), _grid_mesh(seed=3)
            la, lb = _indexed(a), _indexed(b)
            mesh_module.invalidate_mesh_indexes()
            assert not la.fits(a) and not lb.fits(b)
            _same_as_the_scan(a, [(515.0, -61.0)])
            assert a._locator is None
        finally:
            mesh_module._INDEX_EPOCH = saved

    def test_a_python_exec_script(self):
        from ogr_api.pyexec import run_python
        mesh = self._indexed_by_use()
        stale = mesh._locator
        out = run_python(self.SCRIPT, {"m": mesh, "Node": Node})
        assert out["ok"], out
        pts = self._beside_node(mesh, 22)
        assert self._stale_somewhere(stale, mesh, pts)
        _same_as_the_scan(mesh, pts)

    def test_a_terminal_command(self):
        from PySide6.QtWidgets import QApplication

        from ogr_gui.widgets.terminal import TerminalWidget
        QApplication.instance() or QApplication([])
        mesh = self._indexed_by_use()
        stale = mesh._locator
        term = TerminalWidget(namespace={"m": mesh, "Node": Node})
        try:
            term._execute(self.SCRIPT)
        finally:
            term.deleteLater()
        pts = self._beside_node(mesh, 22)
        assert self._stale_somewhere(stale, mesh, pts)
        _same_as_the_scan(mesh, pts)
