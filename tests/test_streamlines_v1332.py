# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.332 (D329b) — the streamlines of a seepage field, validated against
external identities (rule 1).

The tracer (``ogr_fem2d.solvers.streamlines``) follows the Darcy velocity,
constant inside each linear triangle, from edge to edge: exact by segment,
with the field's own approximation as the only error. What these tests
check, none of it against what the code prints today:

* **a closed-form flow.** The stagnation-point flow of the potential
  phi = x^2 - y^2 has the velocity (-2x, 2y) and the stream function
  psi = 2xy (its harmonic conjugate, Cauchy-Riemann; phi + i psi = z^2),
  so its streamlines are the hyperbolas x*y = constant. On a mesh whose
  element velocities are the exact ones at their centroids, x*y along every
  traced line stays within a small fraction of its value, and the error
  falls when the mesh is refined;
* **exact by segment.** Every segment lies in one element and runs along
  that element's velocity, to rounding;
* **a uniform field** gives straight lines from boundary to boundary;
* the lines go through mesh nodes and vertices (a line started on a node,
  or crossing at a vertex, used to stop there while this was written);
* on a real field — the seepage of the first worked example that
  ``test_interpret_i3_v153`` solves, 107 elements — most of them run from
  boundary to boundary. Measured while this was written: 1 of the 22 ends
  of its streamlines reached the boundary with the first tracer, which
  probed for the next element and took a ray leaving almost along an edge
  for one that had not left; 17 with the element across the edge and the
  slide along an edge where the two elements' flows meet head-on. The five
  inside end at nodes most of whose elements' velocities point at them, on
  material contacts: the discrete field's own convergence, not the
  tracer's.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _grid(nx, ny, x0, x1, y0, y1):
    """A structured mesh of linear triangles, the diagonals alternating so
    that no direction is favoured."""
    from ogr_fem2d.mesh.mesh import Element, Mesh, Node
    nodes = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            nodes.append(Node(len(nodes), x0 + (x1 - x0) * i / nx,
                              y0 + (y1 - y0) * j / ny))
    elements = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c = a + 1, a + nx + 1
            d = c + 1
            tris = ((a, b, d), (a, d, c)) if (i + j) % 2 == 0 \
                else ((a, b, c), (b, d, c))
            for t in tris:
                elements.append(Element(len(elements), t))
    return Mesh(nodes=nodes, elements=elements)


def _stagnation(mesh):
    """The exact velocity -grad(x^2 - y^2) at each element's centroid."""
    out = []
    for e in mesh.elements:
        cx, cy = e.centroid(mesh)
        out.append((-2.0 * cx, 2.0 * cy))
    return out


_STARTS = ((2.5, 1.0), (2.0, 1.5), (1.2, 1.2), (2.9, 0.7))


def _worst_xy_error(n):
    from ogr_fem2d.solvers.streamlines import trace_streamline
    mesh = _grid(n, n, 0.5, 3.0, 0.5, 3.0)
    velocity = _stagnation(mesh)
    worst = 0.0
    for start in _STARTS:
        line = trace_streamline(mesh, velocity, start)
        assert len(line) > 10, (n, start, len(line))
        c = start[0] * start[1]
        worst = max(worst, max(abs(x * y - c) / c for x, y in line))
    return worst


class TestTheClosedFormFlow:
    def test_x_times_y_is_kept_along_every_line(self):
        assert _worst_xy_error(40) < 3e-3

    def test_the_error_falls_with_the_mesh(self):
        coarse, fine = _worst_xy_error(20), _worst_xy_error(40)
        assert fine < 0.6 * coarse, (coarse, fine)

    def test_a_line_runs_from_boundary_to_boundary(self):
        """From (2.5, 1): x*y = 2.5, upstream to x = 3 at y = 5/6 and
        downstream to y = 3 at x = 5/6."""
        from ogr_fem2d.solvers.streamlines import trace_streamline
        mesh = _grid(40, 40, 0.5, 3.0, 0.5, 3.0)
        line = trace_streamline(mesh, _stagnation(mesh), (2.5, 1.0))
        (x_up, y_up), (x_down, y_down) = line[0], line[-1]
        assert abs(x_up - 3.0) < 1e-9 and abs(y_up - 2.5 / 3.0) < 1e-2
        assert abs(y_down - 3.0) < 1e-9 and abs(x_down - 2.5 / 3.0) < 1e-2


class TestExactBySegment:
    def test_each_segment_runs_along_its_elements_velocity(self):
        from ogr_fem2d.solvers.streamlines import _inside, trace_streamline
        mesh = _grid(20, 20, 0.5, 3.0, 0.5, 3.0)
        velocity = _stagnation(mesh)
        line = trace_streamline(mesh, velocity, (2.2, 0.9))
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            mid = ((ax + bx) / 2.0, (ay + by) / 2.0)
            owners = [e for e in mesh.elements
                      if _inside(e.coords(mesh), mid, tol=1e-9)]
            assert owners, mid
            vx, vy = velocity[owners[0].id]
            dx, dy = bx - ax, by - ay
            sine = abs(dx * vy - dy * vx) / (math.hypot(dx, dy)
                                             * math.hypot(vx, vy))
            assert sine < 1e-9, sine
            # and downstream, not against the flow
            assert dx * vx + dy * vy > 0.0


class TestAUniformField:
    def test_straight_lines_from_boundary_to_boundary(self):
        from ogr_fem2d.solvers.streamlines import streamlines
        mesh = _grid(20, 10, 0.0, 10.0, 0.0, 5.0)
        v = (1.0, 0.5)
        lines = streamlines(mesh, [v] * len(mesh.elements), count=6)
        assert lines
        for line in lines:
            for (ax, ay), (bx, by) in zip(line, line[1:]):
                dx, dy = bx - ax, by - ay
                sine = abs(dx * v[1] - dy * v[0]) / (math.hypot(dx, dy)
                                                     * math.hypot(*v))
                assert sine < 1e-9
            for x, y in (line[0], line[-1]):
                on_edge = min(abs(x), abs(x - 10.0), abs(y), abs(y - 5.0))
                assert on_edge < 1e-9, (x, y)

    def test_a_line_through_a_vertex_goes_on(self):
        """(6, 0.5) is a node of this mesh, and the line from (5, 0) passes
        through it on its way to (10, 2.5)."""
        from ogr_fem2d.solvers.streamlines import trace_streamline
        mesh = _grid(20, 10, 0.0, 10.0, 0.0, 5.0)
        line = trace_streamline(mesh, [(1.0, 0.5)] * len(mesh.elements),
                                (5.0, 0.0))
        assert abs(line[-1][0] - 10.0) < 1e-9
        assert abs(line[-1][1] - 2.5) < 1e-9

    def test_control_no_flow_no_lines(self):
        from ogr_fem2d.solvers.streamlines import seed_points, streamlines
        mesh = _grid(4, 4, 0.0, 1.0, 0.0, 1.0)
        still = [(0.0, 0.0)] * len(mesh.elements)
        assert seed_points(mesh, still) == []
        assert streamlines(mesh, still) == []


class TestARealField:
    def test_most_ends_reach_the_boundary(self):
        import test_interpret_i3_v153 as i3
        from ogr_fem2d.solvers.streamlines import streamlines
        p = i3.TestGroundwaterEntries()._with_seepage()
        mesh, velocity = p.fem_mesh, p.seepage_result.velocity
        boundary = mesh.boundary_edges()

        def on_boundary(pt):
            for a, b in boundary:
                ax, ay = mesh.nodes[a].x, mesh.nodes[a].y
                ex, ey = mesh.nodes[b].x - ax, mesh.nodes[b].y - ay
                length = math.hypot(ex, ey)
                t = ((pt[0] - ax) * ex + (pt[1] - ay) * ey) / length ** 2
                off = abs((pt[0] - ax) * ey - (pt[1] - ay) * ex) / length
                if off < 1e-6 * length and -1e-6 <= t <= 1 + 1e-6:
                    return True
            return False

        lines = streamlines(mesh, velocity, count=12)
        assert len(lines) >= 8, len(lines)
        ends = [end for line in lines for end in (line[0], line[-1])]
        reached = sum(on_boundary(end) for end in ends)
        assert reached >= 0.75 * len(ends), (reached, len(ends))
