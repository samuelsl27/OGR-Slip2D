# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Finite-element mesh data structures (Phase 1 of the groundwater plan).

Defines the minimal, solver-agnostic mesh representation used by the
OGR FEM2D seepage engine:

    * :class:`Node`    — a mesh vertex (x, y) with a stable integer id
    * :class:`Element` — a linear triangle (T3) referencing three node
      ids, carrying the material and source region it belongs to
    * :class:`Mesh`    — the node/element container plus the queries the
      solver and the GUI need (quality statistics, boundary edges,
      point location, serialisation)

Only T3 elements are produced for now. T3 is sufficient for
groundwater flow: the primary unknown is total head H, and a linear
interpolation of H over a triangle gives a constant flux per element,
which is the classical formulation for seepage (Bathe & Khoshgoftaar,
1979). T6 can be added later by mid-side node insertion without
changing this container.

v0.1.342 (D337) -- moved whole from ``ogr_fem2d/mesh/mesh.py``: the
project stores a mesh and the core rebuilds it on load, so it is the core's.
``ogr_fem2d.mesh`` and ``ogr_fem2d.mesh.mesh`` re-export these names.

v0.1.383 (V5 of the compute audit) -- ``Mesh.locate`` narrows its scan with
a grid index whose boxes carry a certified floating-point margin; it still
returns the scan's element, object for object (see :class:`_Locator`).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Iterator, Optional


#: v0.1.271 (D270) — below this ``shape_ratio`` a triangle is degenerate
#: (flat). The generator repairs such triangles and the solvers report them;
#: the bank's healthy meshes have none below 0.1, the flat ones are at 1e-15.
DEGENERATE_SHAPE_RATIO = 1e-10

#: v0.1.383 (V5) — the tolerance of ``Element.contains`` and the determinant
#: below which ``Element.barycentric`` gives up. The locator's certified
#: margin (``_certified_box``) is derived from both, so each lives here once:
#: changing one where it is used and not in the bound would let the index
#: skip an element the scan returns.
CONTAINS_TOL = 1e-9
DEGENERATE_DET = 1e-15


def triangle_shape_ratio(p1, p2, p3) -> float:
    """2A / L^2max: 0 for collinear vertices, ~0.87 for an equilateral
    triangle, and independent of the triangle's size — a RELATIVE measure,
    unlike the absolute 1e-15 on the determinant that ``shape_gradients``
    still uses (and that a flat triangle metres across passes)."""
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    l2 = max((x2 - x1) ** 2 + (y2 - y1) ** 2,
             (x3 - x2) ** 2 + (y3 - y2) ** 2,
             (x1 - x3) ** 2 + (y1 - y3) ** 2)
    return abs(det) / l2 if l2 > 0.0 else 0.0


@dataclass(frozen=True)
class Node:
    """A mesh vertex."""

    id: int
    x: float
    y: float

    def distance_to(self, other: "Node") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class Element:
    """A linear triangular element (T3), nodes in CCW order."""

    id: int
    nodes: tuple[int, int, int]
    material_id: Optional[str] = None
    region_index: Optional[int] = None

    # ------------------------------------------------------------------
    def coords(self, mesh: "Mesh") -> list[tuple[float, float]]:
        return [(mesh.nodes[i].x, mesh.nodes[i].y) for i in self.nodes]

    def area(self, mesh: "Mesh") -> float:
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        return 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

    def centroid(self, mesh: "Mesh") -> tuple[float, float]:
        pts = self.coords(mesh)
        return (sum(p[0] for p in pts) / 3.0, sum(p[1] for p in pts) / 3.0)

    def angles_deg(self, mesh: "Mesh") -> list[float]:
        """The three interior angles, in degrees."""
        p = self.coords(mesh)
        out = []
        for i in range(3):
            a = p[i]
            b = p[(i + 1) % 3]
            c = p[(i + 2) % 3]
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - a[0], c[1] - a[1])
            n1 = math.hypot(*v1)
            n2 = math.hypot(*v2)
            if n1 < 1e-15 or n2 < 1e-15:
                out.append(0.0)
                continue
            cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
            out.append(math.degrees(math.acos(max(-1.0, min(1.0, cosang)))))
        return out

    def min_angle_deg(self, mesh: "Mesh") -> float:
        return min(self.angles_deg(mesh))

    def shape_ratio(self, mesh: "Mesh") -> float:
        """See :func:`triangle_shape_ratio`."""
        return triangle_shape_ratio(*self.coords(mesh))

    def shape_gradients(self, mesh: "Mesh"):
        """(dN/dx, dN/dy, area) for the three linear shape functions.

        For a T3 the gradients are constant over the element, which is
        what the seepage stiffness matrix assembly needs (Phase 2).
        """
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det) < 1e-15:
            return None
        area = 0.5 * abs(det)
        dNdx = [(y2 - y3) / det, (y3 - y1) / det, (y1 - y2) / det]
        dNdy = [(x3 - x2) / det, (x1 - x3) / det, (x2 - x1) / det]
        return dNdx, dNdy, area

    def contains(self, mesh: "Mesh", x: float, y: float,
                 tol: float = CONTAINS_TOL) -> bool:
        """Barycentric point-in-triangle test (inclusive of edges)."""
        bc = self.barycentric(mesh, x, y)
        if bc is None:
            return False
        return all(w >= -tol for w in bc)

    def barycentric(self, mesh: "Mesh", x: float, y: float):
        """Barycentric coordinates of (x, y), or None if degenerate."""
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det) < DEGENERATE_DET:
            return None
        l1 = ((x2 - x) * (y3 - y) - (x3 - x) * (y2 - y)) / det
        l2 = ((x3 - x) * (y1 - y) - (x1 - x) * (y3 - y)) / det
        return (l1, l2, 1.0 - l1 - l2)


@dataclass
class Mesh:
    """A 2D finite-element mesh of linear triangles."""

    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    # Diagnostics filled in by the generator
    target_size: float = 0.0
    notes: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> Iterator[Element]:
        return iter(self.elements)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def element_count(self) -> int:
        return len(self.elements)

    def total_area(self) -> float:
        return sum(e.area(self) for e in self.elements)

    # ------------------------------------------------------------------
    def quality_stats(self) -> dict:
        """Mesh quality summary. ``min_angle`` is the usual single-number
        indicator: a Delaunay mesh refined to a 25-30 deg floor is
        considered good for FE analysis."""
        if not self.elements:
            return {"elements": 0, "nodes": len(self.nodes)}
        angles = [e.min_angle_deg(self) for e in self.elements]
        areas = [e.area(self) for e in self.elements]
        angles_sorted = sorted(angles)
        n = len(angles_sorted)
        return {
            "elements": len(self.elements),
            "nodes": len(self.nodes),
            "min_angle": angles_sorted[0],
            "mean_min_angle": sum(angles) / n,
            "median_min_angle": angles_sorted[n // 2],
            "pct_below_20deg": 100.0 * sum(
                1 for a in angles if a < 20.0) / n,
            "pct_below_30deg": 100.0 * sum(
                1 for a in angles if a < 30.0) / n,
            "min_area": min(areas),
            "max_area": max(areas),
            "total_area": sum(areas),
        }

    # ------------------------------------------------------------------
    def edge_map(self) -> dict[tuple[int, int], list[int]]:
        """Map each undirected edge (sorted node ids) to the element ids
        sharing it."""
        out: dict[tuple[int, int], list[int]] = {}
        for e in self.elements:
            a, b, c = e.nodes
            for u, v in ((a, b), (b, c), (c, a)):
                key = (u, v) if u < v else (v, u)
                out.setdefault(key, []).append(e.id)
        return out

    def boundary_edges(self) -> list[tuple[int, int]]:
        """Edges belonging to exactly one element — the mesh boundary.
        These are where the seepage boundary conditions get applied
        (Phase 2/3)."""
        return [k for k, v in self.edge_map().items() if len(v) == 1]

    def boundary_node_ids(self) -> set[int]:
        ids: set[int] = set()
        for u, v in self.boundary_edges():
            ids.add(u)
            ids.add(v)
        return ids

    def degenerate_elements(self) -> list[int]:
        """Ids of the flat elements (``shape_ratio`` below
        ``DEGENERATE_SHAPE_RATIO``). v0.1.271 (D270): the generator no
        longer makes them, but a mesh saved before it did travels in the
        .ogr; the solvers report these instead of skipping them, because
        removing one can leave a node with no element in its region."""
        return [e.id for e in self.elements
                if e.shape_ratio(self) < DEGENERATE_SHAPE_RATIO]

    def is_conforming(self) -> bool:
        """True when no edge is shared by more than two elements (a
        basic conformity check: hanging nodes would show up as edges
        with 3+ owners or as boundary edges in the interior)."""
        return all(len(v) <= 2 for v in self.edge_map().values())

    # ------------------------------------------------------------------
    def locate(self, x: float, y: float) -> Optional[Element]:
        """The FIRST element of ``elements`` whose :meth:`Element.contains`
        accepts (x, y), or None. The LEM coupling interpolates pore
        pressure at slice base midpoints through it.

        v0.1.383 (V5): after ``_LOCATOR_AFTER_SCANS`` linear scans of the
        same mesh, a grid index (:class:`_Locator`) chooses WHICH elements
        are tested; each is still tested with the same ``contains`` call and
        in list order, so the answer is the scan's, object for object. The
        queries the index's bound does not cover (not Python floats, not
        finite, far outside the mesh) are scanned, and so is a mesh whose
        ``nodes`` or ``elements`` list was replaced or resized. A mesh's
        geometry is replaced, never edited in place: nothing in the program
        assigns into those lists or into ``Element.nodes`` once a mesh is
        built, and the index would not notice it. A user's script can: the
        code runners make every index stale around one
        (``invalidate_mesh_indexes``), and other code that edits a mesh in
        place calls :meth:`forget_index`."""
        loc = getattr(self, "_locator", None)
        if loc is not None:
            if loc.fits(self):
                if loc.takes(x, y):
                    return loc.find(self, x, y)
            else:
                # The lists were replaced or resized, or a script has run
                # since: the index may be of another geometry. Scan, and
                # count again before building a new one.
                self._locator = loc = None
                self._locate_scans = 0
        found = None
        for e in self.elements:
            if e.contains(self, x, y):
                found = e
                break
        if loc is None:
            self._after_scan()
        return found

    def _after_scan(self) -> None:
        """Counts a scan and, at ``_LOCATOR_AFTER_SCANS``, builds the index.
        It is built whole and then published with ONE assignment: another
        thread that reads ``_locator`` meanwhile (the window's calculation
        and an agent's query share the live mesh) sees None and scans, or
        sees the finished index — never a half-filled one."""
        n = getattr(self, "_locate_scans", 0) + 1
        if n < _LOCATOR_AFTER_SCANS:
            self._locate_scans = n
            return
        self._locate_scans = 0
        try:
            loc = _build_locator(self)
        except Exception:  # noqa: BLE001 — lists the index cannot even measure
            # (no len: a script's iterator, None) are scanned, as before, and
            # the scan's answer must not be lost to the build.
            return
        self._locator = loc

    def forget_index(self) -> None:
        """Drops the locator (v0.1.383, V5) and makes stale what a seepage
        solver keeps of this mesh's elements (``_forgets``, which the
        solver compares; v0.1.393, V14). The program replaces a mesh and
        never edits one in place; code that edits ``nodes``, ``elements`` or
        an ``Element.nodes`` in place calls this, or the index keeps
        answering for the old geometry, and a solver keeps assembling it."""
        self.__dict__.pop("_locator", None)
        self.__dict__.pop("_locate_scans", None)
        self.__dict__["_forgets"] = self.__dict__.get("_forgets", 0) + 1

    def __getstate__(self) -> dict:
        """v0.1.383 (V5) — the index and its scan count stay behind: they
        are of THIS object's lists, and rebuilt where a copy is used, so a
        pool's payload, a statistics sample or an undo snapshot pickles the
        same bytes as before the index existed. A copy, not ``__dict__``
        itself: popping from the live dict would drop the original's index
        while another thread reads it."""
        state = self.__dict__.copy()
        state.pop("_locator", None)
        state.pop("_locate_scans", None)
        # v0.1.393 (V14): the count of forget_index calls is of these lists
        # too; a copy's solver keys on the copy's lists.
        state.pop("_forgets", None)
        return state

    def interpolate(self, values: list[float], x: float,
                    y: float) -> Optional[float]:
        """Interpolate a nodal field at (x, y) with the T3 shape
        functions. ``values`` is indexed by node id."""
        e = self.locate(x, y)
        if e is None:
            return None
        bc = e.barycentric(self, x, y)
        if bc is None:
            return None
        return sum(w * values[nid] for w, nid in zip(bc, e.nodes))

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "nodes": [[n.id, n.x, n.y] for n in self.nodes],
            "elements": [
                [e.id, list(e.nodes), e.material_id, e.region_index]
                for e in self.elements
            ],
            "target_size": self.target_size,
            "notes": dict(self.notes),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Mesh":
        m = cls(target_size=float(d.get("target_size", 0.0)),
                notes=dict(d.get("notes", {})))
        m.nodes = [Node(int(i), float(x), float(y))
                   for i, x, y in d.get("nodes", [])]
        m.elements = [
            Element(int(eid), (int(nn[0]), int(nn[1]), int(nn[2])),
                    mat, rgn)
            for eid, nn, mat, rgn in d.get("elements", [])
        ]
        return m


# ----------------------------------------------------------------------
# v0.1.383 (V5 of the compute audit) — the index behind Mesh.locate.
#
# The linear scan was 87 % of a search with finite-element pore pressures
# (bank 010: 549 of 1441 elements tested per slice base). The index only
# chooses WHICH elements a query tests; each candidate still goes through
# the same ``Element.contains`` call, in list order, so the answer is the
# scan's, object for object. What lets it skip an element is a box that
# provably holds every point ``contains`` accepts (_certified_box).

#: Scans of one mesh before ``Mesh.locate`` builds its index: a build costs
#: about as much (bank 010, 1441 elements: 11 ms, against 0.7 ms per scan),
#: so a mesh asked a handful of times never pays for one.
_LOCATOR_AFTER_SCANS = 16
#: A box over more cells than this goes to the list tested on every query:
#: a tiny element far inside a huge far box would otherwise fill the grid.
_MAX_CELLS_PER_BOX = 64
#: Beyond this the far box is not indexed: with every coordinate below it,
#: no product or quotient of ``contains`` can overflow, so the standard
#: model holds wherever it accepts. The bound's own margin can still reach
#: infinity (a needle near the limit); the element then has no box.
_MAX_COORD = 1e100

#: Moved by ``invalidate_mesh_indexes`` around every user script. An index
#: records the value it was built under and is stale once it moves. A
#: count, never a result: tests/_leaks.py allows it to change.
_INDEX_EPOCH = 0


def invalidate_mesh_indexes() -> None:
    """Makes every mesh index built so far stale, and what every seepage
    solver keeps of a mesh's elements (v0.1.393, V14). The code runners
    (``ogr_api.pyexec.run_python`` for python_exec, and the window's
    terminal) call it before and after a user's script, which can edit a
    mesh in place — through the project, a stored result or a solver —
    where no index would notice (decided by the owner in v0.1.383). An
    edit the script makes after an index it rebuilt itself still needs
    ``Mesh.forget_index``."""
    global _INDEX_EPOCH
    _INDEX_EPOCH += 1


_U = 2.0 ** -53                       # unit roundoff of binary64
_GAMMA2 = 2.0 * _U / (1.0 - 2.0 * _U)
_GAMMA4 = 4.0 * _U / (1.0 - 4.0 * _U)
# Underflow: a subnormal product or quotient is off by at most 2**-1075 (a
# subnormal sum or difference is exact). 2**-1075 itself rounds to 0.0, so
# the slacks use 2**-1074 and above.
_DET_SLACK = 2.0 ** -1070
_NUM_SLACK = 2.0 ** -1073
_QUOT_SLACK = 2.0 ** -1074


def _certified_box(x1, y1, x2, y2, x3, y3, fx0, fx1, fy0, fy1):
    """(x0, x1, y0, y1): a box holding every point of the far box
    [fx0, fx1] x [fy0, fy1] that ``Element.contains`` accepts for the
    triangle (x1, y1), (x2, y2), (x3, y3) — or None when that cannot be
    certified (a determinant not known to its sign, below DEGENERATE_DET,
    or not finite), and the element is then tested on every query.

    The bound follows ``Element.barycentric`` operation by operation under
    the standard model of floating-point arithmetic, fl(a op b) =
    (a op b)(1 + d) with |d| <= u, and gamma_n = n u / (1 - n u) for a
    product of n such factors (Higham, 2002, Accuracy and Stability of
    Numerical Algorithms, 2nd ed., §2.2 and Lemma 3.1):

    - with d the exact determinant, |dhat - d| <= eps_d, so |d| >= d_min;
    - over the far box each numerator n_i and its error are bounded by P_i
      and gamma_4 P_i, so each computed coordinate is within E_i of the
      exact one (E3 adds the two roundings of ``1.0 - l1 - l2``);
    - a point that passes has every exact coordinate >= -tol - E_i, so its
      negative weights add up to at most s = 3 tol + E1 + E2 + E3; and as
      p = sum(l_i v_i) with sum(l_i) = 1, it lies within s * width of the
      vertex extremes in x (s * height in y).

    The box doubles that margin, to absorb the rounding of evaluating it,
    and steps one ulp outward. The derivation, inequality by inequality, is
    in docs/changelog/CHANGELOG_v0.1.383.md.
    """
    # The same operations, in the same order, as Element.barycentric.
    dx21 = x2 - x1
    dy31 = y3 - y1
    dx31 = x3 - x1
    dy21 = y2 - y1
    det = dx21 * dy31 - dx31 * dy21
    big_d = abs(det)
    if not (big_d >= DEGENERATE_DET and math.isfinite(big_d)):
        return None
    # |dhat - d| <= gamma_4 (|Ad| + |Cd|) <= 8u * pd: pd is computed from
    # the rounded differences, which can under-read the exact sum.
    pd = abs(dx21) * abs(dy31) + abs(dx31) * abs(dy21)
    eps_d = 8.0 * _U * pd + _DET_SLACK
    if not eps_d <= 0.25 * big_d:
        return None
    d_min = big_d - eps_d               # a lower bound of |d|
    rho = eps_d / d_min                 # <= 1/3
    # |x_k - x| <= ax_k and |y_k - y| <= ay_k for every query in the far box
    ax1 = max(x1 - fx0, fx1 - x1)
    ax2 = max(x2 - fx0, fx1 - x2)
    ax3 = max(x3 - fx0, fx1 - x3)
    ay1 = max(y1 - fy0, fy1 - y1)
    ay2 = max(y2 - fy0, fy1 - y2)
    ay3 = max(y3 - fy0, fy1 - y3)
    lam1 = (ax2 * ay3 + ax3 * ay2) / d_min    # P1 / d_min, bounds |l1|
    lam2 = (ax3 * ay1 + ax1 * ay3) / d_min    # P2 / d_min, bounds |l2|
    f = (_U + rho + _GAMMA4 * (1.0 + _U)) / (1.0 - rho)
    slack = _NUM_SLACK / d_min + _QUOT_SLACK
    e1 = lam1 * f + slack
    e2 = lam2 * f + slack
    e3 = e1 + e2 + _GAMMA2 * (1.0 + lam1 + e1) + _U * (lam2 + e2)
    s = 3.0 * CONTAINS_TOL + e1 + e2 + e3
    xmin, xmax = min(x1, x2, x3), max(x1, x2, x3)
    ymin, ymax = min(y1, y2, y3), max(y1, y2, y3)
    mx = 2.0 * s * (xmax - xmin)
    my = 2.0 * s * (ymax - ymin)
    lo_x = math.nextafter(xmin - mx, -math.inf)
    hi_x = math.nextafter(xmax + mx, math.inf)
    lo_y = math.nextafter(ymin - my, -math.inf)
    hi_y = math.nextafter(ymax + my, math.inf)
    if not (math.isfinite(lo_x) and math.isfinite(hi_x)
            and math.isfinite(lo_y) and math.isfinite(hi_y)):
        return None
    # A query outside the far box never reaches the grid, so the box may
    # stop at its edge.
    return (max(lo_x, fx0), min(hi_x, fx1), max(lo_y, fy0), min(hi_y, fy1))


class _Locator:
    """A uniform grid over the certified boxes of one mesh's elements.

    ``cells[j * nx + i]`` lists, by increasing position in ``elements``,
    the elements whose box overlaps that cell; ``always`` lists the ones
    without a certified box. The cell of a coordinate is
    ``int((v - g0) * inverse width)``, clamped: the same monotone formula
    for a box's corners and for a query, so a query inside a box falls in
    one of the box's cells. Built once (``_build_locator``) and never
    changed afterwards."""

    __slots__ = ("epoch", "nodes", "elements", "n_nodes", "n_elements",
                 "fx0", "fx1", "fy0", "fy1", "gx0", "gx1", "gy0", "gy1",
                 "nx", "ny", "ix", "iy", "cells", "always")

    def fits(self, mesh: Mesh) -> bool:
        """Still the index of these lists: no script has run since it was
        built, and they are the same objects (``is``, not ``id``, which a
        new list can reuse) with the same lengths."""
        return (self.epoch == _INDEX_EPOCH
                and mesh.elements is self.elements and mesh.nodes is self.nodes
                and len(mesh.elements) == self.n_elements
                and len(mesh.nodes) == self.n_nodes)

    def takes(self, x, y) -> bool:
        """The queries the bound covers: exactly Python floats (a subclass
        could redefine the arithmetic, and numpy's float64 honours numpy's
        error state, which the scan of a skipped element could trip) inside
        the far box. NaN fails the comparisons and the far box is finite,
        so non-finite queries take the scan."""
        return (type(x) is float and type(y) is float
                and self.fx0 <= x <= self.fx1 and self.fy0 <= y <= self.fy1)

    def find(self, mesh: Mesh, x: float, y: float) -> Optional[Element]:
        """The first candidate, in list order, that ``contains`` accepts:
        every element that accepts (x, y) is a candidate, so this is the
        first element of the scan that accepts it."""
        if self.gx0 <= x <= self.gx1 and self.gy0 <= y <= self.gy1:
            i = int((x - self.gx0) * self.ix)
            j = int((y - self.gy0) * self.iy)
            if i >= self.nx:
                i = self.nx - 1
            if j >= self.ny:
                j = self.ny - 1
            cell = self.cells[j * self.nx + i]
        else:
            cell = ()
        order = heapq.merge(cell, self.always) if self.always else cell
        els = self.elements             # the list fits() checked
        for k in order:
            e = els[k]
            if e.contains(mesh, x, y):
                return e
        return None


def _build_locator(mesh: Mesh) -> _Locator:
    """The index of ``mesh`` as it is now. A mesh it cannot cover gets a
    locator that takes no query, so ``locate`` keeps scanning it without
    trying again until its lists change: an element that is not exactly an
    ``Element`` (which could redefine ``contains``), a coordinate that is
    not exactly a float, an element that cannot be read (the scan raises
    there, if it gets that far), coordinates beyond _MAX_COORD, or more
    than half the elements without a certified box."""
    loc = _Locator()
    # Read before the lists: a script that starts during the build leaves
    # this index stale at once.
    loc.epoch = _INDEX_EPOCH
    loc.nodes, loc.elements = mesh.nodes, mesh.elements
    loc.n_nodes, loc.n_elements = len(mesh.nodes), len(mesh.elements)
    loc.fx0 = loc.fy0 = loc.gx0 = loc.gy0 = math.inf
    loc.fx1 = loc.fy1 = loc.gx1 = loc.gy1 = -math.inf
    loc.nx = loc.ny = 1
    loc.ix = loc.iy = 0.0
    loc.cells = [()]
    loc.always = ()
    try:
        grid = _grid_of(loc.nodes, loc.elements)
    except Exception:  # noqa: BLE001 — a mesh the index cannot read is scanned
        return loc
    if grid is None:
        return loc
    (loc.fx0, loc.fx1, loc.fy0, loc.fy1, loc.gx0, loc.gx1, loc.gy0, loc.gy1,
     loc.nx, loc.ny, loc.ix, loc.iy, loc.cells, loc.always) = grid
    return loc


def _grid_of(nodes, elements):
    """The far box, the grid and its lists for ``_build_locator``, or None:
    of the lists the locator keeps, read once, whatever another thread
    assigns to the mesh meanwhile."""
    coords = []
    for e in elements:
        if type(e) is not Element:
            return None
        a, b, c = e.nodes
        p, q, r = nodes[a], nodes[b], nodes[c]
        t = (p.x, p.y, q.x, q.y, r.x, r.y)
        if not all(type(v) is float for v in t):
            return None
        # A vertex at NaN or infinity: tested on every query, as the scan.
        coords.append(t if all(math.isfinite(v) for v in t) else None)
    finite = [t for t in coords if t is not None]
    if not finite:
        return None
    bx0 = min(min(t[0], t[2], t[4]) for t in finite)
    bx1 = max(max(t[0], t[2], t[4]) for t in finite)
    by0 = min(min(t[1], t[3], t[5]) for t in finite)
    by1 = max(max(t[1], t[3], t[5]) for t in finite)
    size = max(bx1 - bx0, by1 - by0)
    if not (0.0 < size and max(abs(bx0), abs(bx1), abs(by0), abs(by1))
            + 2.0 * size <= _MAX_COORD):
        return None
    # The far box: the mesh's box widened all round by its larger side. The
    # bound grows with it, and it holds every query of the program (slice
    # bases, flux sections, the window's and the API's points).
    fx0, fx1, fy0, fy1 = bx0 - size, bx1 + size, by0 - size, by1 + size
    boxes = []
    always = []
    for k, t in enumerate(coords):
        box = None if t is None else _certified_box(*t, fx0, fx1, fy0, fy1)
        if box is None:
            always.append(k)
        else:
            boxes.append((k, box))
    if not boxes or 2 * len(always) > len(coords):
        return None
    gx0 = min(b[0] for _, b in boxes)
    gx1 = max(b[1] for _, b in boxes)
    gy0 = min(b[2] for _, b in boxes)
    gy1 = max(b[3] for _, b in boxes)
    gw, gh = gx1 - gx0, gy1 - gy0
    if not (gw > 0.0 and gh > 0.0):
        return None
    # About one cell per element: each then holds a few boxes.
    side = math.sqrt(gw * gh / len(boxes))
    nx = max(1, min(math.ceil(gw / side), 4 * len(boxes)))
    ny = max(1, min(math.ceil(gh / side), 4 * len(boxes)))
    ix, iy = nx / gw, ny / gh
    if not (math.isfinite(ix) and math.isfinite(iy) and ix > 0.0 and iy > 0.0):
        return None
    cells = [[] for _ in range(nx * ny)]
    for k, (x0, x1, y0, y1) in boxes:
        i0 = min(int((x0 - gx0) * ix), nx - 1)
        i1 = min(int((x1 - gx0) * ix), nx - 1)
        j0 = min(int((y0 - gy0) * iy), ny - 1)
        j1 = min(int((y1 - gy0) * iy), ny - 1)
        if (i1 - i0 + 1) * (j1 - j0 + 1) > _MAX_CELLS_PER_BOX:
            always.append(k)
            continue
        for j in range(j0, j1 + 1):
            row = j * nx
            for i in range(i0, i1 + 1):
                cells[row + i].append(k)
    if 2 * len(always) > len(coords):
        return None
    return (fx0, fx1, fy0, fy1, gx0, gx1, gy0, gy1, nx, ny, ix, iy,
            [tuple(c) for c in cells], tuple(sorted(always)))
