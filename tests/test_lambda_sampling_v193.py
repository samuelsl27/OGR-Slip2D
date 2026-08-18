# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Spencer and GLE stop sampling λ once the root is bracketed.

WHAT INVARIANT THIS PROTECTS. Both methods find λ by sampling a calibrated
shape of 14 values, looking for a sign change in ``g(λ) = F_f − F_m``, and
then refining inside that bracket. Until v0.1.93 they evaluated all 14
first and looked afterwards. Each sample is a full inner solve, and on the
Ej_2 reference grid **82 % of Spencer's inner solves were that sampling** —
14 per surface against the 3 the bisection actually needed. Spencer and GLE
cost 15× Bishop per circle, so that sampling was most of the wait.

WHY STOPPING EARLY CANNOT MOVE A NUMBER, which is the thing to keep true:
``_first_bracket`` scans CONSECUTIVE samples in ascending λ and returns the
FIRST sign change, and samples are appended in that same ascending order.
Truncating the list right after that sign change therefore leaves the very
bracket it would have returned — so the same bracket, the same bisection,
the same root. This file pins the control flow that makes the argument
hold; the factors of safety themselves are pinned against the published
reference in ``test_slide_validation_ej1`` and ``..._ej2_v184``.

The two paths that still need the whole shape are the reason the cut is
conditional, and both are checked below:

* no sign change anywhere → the fallback picks ``min(samples, key=|g|)``
  over EVERY sample, so it must still see all of them;
* no sign change anywhere → the v0.1.90 λ-extension (2.0 … 6.0) must still
  be reached, or a root at λ ≈ 3 becomes unreachable again.

``g(λ)`` is supplied by a stub inner solve rather than by geometry, so the
root sits exactly where each case needs it and the test states one thing.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def _project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 12), Vertex(30, 12),
        Vertex(20, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("lambda")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=19, sat_unit_weight=20,
                            strength=MohrCoulomb(cohesion=10,
                                                 friction_angle=28))]
    return p


def _circle_and_slices(project):
    from ogr_core.geometry import ground_surface
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle

    circle = SlipCircle(centre_x=28.0, centre_y=30.0, radius=24.0)
    ground = ground_surface(project.external_boundary())
    assert circle.intersect_with_ground(ground) is not None
    slices = slice_surface(project, circle, num_slices=15)
    assert slices is not None and len(slices) >= 3
    return circle, slices


class _Stub:
    """A ``g(λ)`` with the root exactly where the case needs it.

    ``F_f`` and ``F_m`` are returned so that ``F_f − F_m = λ − root``, which
    is monotone and therefore has exactly one sign change — the shape the
    real surfaces show, and the one v0.1.90 measured when it found the root
    sitting at λ = 2.994.
    """

    def __init__(self, root):
        self.root = root
        self.lams = []

    def __call__(self, *args, **kwargs):
        # (slices, lam, ...) for Spencer and GLE alike.
        lam = args[1]
        self.lams.append(lam)
        g = lam - self.root
        return 1.20 + 0.5 * g, 1.20 - 0.5 * g


def _run_with_stub(method, project, circle, slices, root):
    stub = _Stub(root)
    cls = type(method)
    real = cls._inner_solve
    cls._inner_solve = lambda self, *a, **k: stub(*a, **k)
    try:
        result = method.compute_fos(project, circle, slices)
    finally:
        cls._inner_solve = real
    return stub, result


def _cases():
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.spencer import Spencer
    return [("spencer", Spencer()),
            ("gle", GLEMorgensternPrice())]


class TestLambdaSamplingStopsEarly:
    def test_stops_at_the_first_sign_change(self):
        p = _project()
        circle, slices = _circle_and_slices(p)
        for name, method in _cases():
            shape = method.lambda_grid()
            root = 0.3                      # between 0.2 and 0.4 of the shape
            stub, res = _run_with_stub(method, p, circle, slices, root)
            sampled = [v for v in stub.lams if v in shape]
            # The shape is ascending; the first sign change is the first
            # value above the root, so everything past it is never touched.
            expected = shape.index(min(v for v in shape if v > root)) + 1
            assert len(sampled) == expected, (
                "%s sampled %d of the shape, expected %d"
                % (name, len(sampled), expected))
            assert len(sampled) < len(shape), (
                "%s gained nothing: it still swept the whole shape" % name)
            assert abs(res.fos - 1.20) < 1e-6, name

    def test_without_a_bracket_the_whole_shape_is_swept(self):
        """The ``min(|g|)`` fallback compares over every sample."""
        p = _project()
        circle, slices = _circle_and_slices(p)
        for name, method in _cases():
            shape = method.lambda_grid()
            # Root beyond the configured range: no sign change anywhere.
            stub, _res = _run_with_stub(method, p, circle, slices, 99.0)
            sampled = [v for v in stub.lams if v in shape]
            assert len(sampled) == len(shape), (
                "%s cut the sweep short with no bracket to justify it"
                % name)

    def test_the_v0190_extension_is_still_reached(self):
        """A root at λ ≈ 3 must stay reachable — the v0.1.90 finding."""
        p = _project()
        circle, slices = _circle_and_slices(p)
        for name, method in _cases():
            shape = method.lambda_grid()
            stub, res = _run_with_stub(method, p, circle, slices, 2.994)
            beyond = [v for v in stub.lams if v > max(shape)]
            assert beyond, (
                "%s never sampled past the shape, so a root at lambda=3 "
                "is unreachable again" % name)
            assert abs(res.fos - 1.20) < 1e-6, name

    def test_a_root_at_the_top_of_the_shape_still_converges(self):
        """The Ej_1 circle converges at λ = 1.4919 — the last shape value.

        The edge case the cut must not break: the sign change appears only
        between the last two samples, so the sweep runs to the end and the
        bracket is still found.
        """
        p = _project()
        circle, slices = _circle_and_slices(p)
        for name, method in _cases():
            shape = method.lambda_grid()
            stub, res = _run_with_stub(method, p, circle, slices, 1.4919)
            sampled = [v for v in stub.lams if v in shape]
            assert len(sampled) == len(shape), name
            assert abs(res.fos - 1.20) < 1e-6, name
            assert not [v for v in stub.lams if v > max(shape)], (
                "%s reached the extension although the shape bracketed"
                % name)
