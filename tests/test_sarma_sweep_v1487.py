# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.487 (D457) — the factor of Sarma's method with non-vertical slices is
the LARGEST root of Kc(F) = kh (``ogr_slip2d/sarma/solver.py``, «THE
ROOT»), and no longer a smaller one when two roots lie close.

THE DEFECT
    ``solve`` looked for the first change of sign of H, down from F = ∞, by
    a sweep of ratio 1.05: two roots inside one step leave none, and the
    sweep went on down. On the circle of D452 (vertical faces, φ 30°, c 1,
    Ru 0.7) the roots come every 1 + 1.3/n: with 75 wedges the method gave
    0.7632 and with 100 0.5965, where the largest root is 0.8175 and
    0.8191; on problem 5 of the manual with γw = 9.81, the bisector and no
    faces of the table, 0.5957 with 2, 10 and 25 wedges, where it is
    0.6096. No fixed ratio is enough: 1.02 still misses with 150 and 200
    wedges (the bench's ``_auditoria/P9_D457/medir_barridos_d457.py``).

THE INVARIANT
    The factor is the largest root by a judge that shares nothing with the
    solver: ``_kc_direct`` of ``test_sarma_solver_v1461`` (the equilibrium
    of the wedges written out and solved as one linear system) changes
    sign across the factor, and has no root above it (rule 1: an identity
    of the equilibrium, not what the program prints). With the sweep of
    v0.1.486 (``solver.ROOT_ENUMERATOR = "sweep"``, restored) the same
    judge finds a root above the factor (rule 7: the enumerator moves the
    number). The identity the enumerator rests on, that H·∏√(1 + tan²φ g²)
    is a polynomial in g = 1/F of degree 2(n − pairs), is checked on its
    own: its Chebyshev coefficients past that degree vanish.

COST
    About 6 s (the judge on 100 wedges is a 200 × 200 linear system per
    point of a 1500-point scan, twice); worth it because it is the
    reference (rule 1).
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import test_sarma_wedges_v1463 as W63  # noqa: E402
from test_sarma_near_pair_v1470 import _Judge  # noqa: E402
from test_sarma_optimize_angles_v1471 import _roots_above  # noqa: E402

_CACHE: dict = {}


def _circle_wedges(n):
    """The wedges of D452's circle with ``n`` vertical faces."""
    key = ("circle", n)
    if key not in _CACHE:
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.sarma.wedges import to_solver
        from ogr_slip2d.surface import SlipCircle
        p = Project("v1487 circle")
        W63._external(p, ((0, 0), (80, 0), (80, 20), (40, 20), (20, 10),
                          (0, 10)))
        soil = Material(name="soil", unit_weight=18.0, sat_unit_weight=20.0,
                        use_sat_unit_weight=True,
                        strength=MohrCoulomb(cohesion=1.0,
                                             friction_angle=30.0))
        soil.pore_pressure = PorePressureType.RU_COEFFICIENT
        soil.ru = 0.7
        p.materials = [soil]
        p.settings.sarma.tolerance = 1e-12
        p.settings.sarma.slice_angles = "vertical"
        p.settings.sarma.num_slices = n
        r = evaluate_surfaces(p, SlipCircle(centre_x=30, centre_y=35,
                                            radius=26),
                              ["sarma"]).results["sarma"]
        _CACHE[key] = to_solver(r.slices, 0.0, 0.0)
    return _CACHE[key]


def _p5_wedges(n):
    """Problem 5 with γw = 9.81, the bisector, no faces of the table."""
    key = ("p5", n)
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.sarma.wedges import to_solver
        p, s, _a, _t = W63._problem5(9.81)
        p.settings.sarma.tolerance = 1e-12
        p.settings.sarma.num_slices = n
        p.settings.sarma.slice_angles = "bisector"
        r = evaluate_surfaces(p, s, ["sarma"]).results["sarma"]
        _CACHE[key] = to_solver(r.slices, 0.0, 0.0)
    return _CACHE[key]


def _solve(si, enumerator=None):
    from ogr_slip2d.sarma import solver as SV
    kept = SV.ROOT_ENUMERATOR
    if enumerator is not None:
        SV.ROOT_ENUMERATOR = enumerator
    try:
        return SV.solve(si.bases, si.faces, slide_sign=si.slide_sign,
                        head_thrust=si.head_thrust, tolerance=1e-12)
    finally:
        SV.ROOT_ENUMERATOR = kept


def _judge(si, sol):
    return _Judge(si.bases, si.faces, sol.slide_sign, sol.senses,
                  head=si.head_thrust)


def _is_the_largest_root(si, sol):
    judge = _judge(si, sol)
    F = sol.fos
    lo, hi = judge.h(F * (1 - 1e-7)), judge.h(F * (1 + 1e-7))
    assert lo is not None and hi is not None and (lo > 0.0) != (hi > 0.0), \
        (F, lo, hi)
    assert _roots_above(judge, F, 50.0) == [], F


class TestTheLargestRoot:

    def test_the_circle_with_many_wedges(self):
        for n, want in ((75, 0.817510), (100, 0.819129)):
            si = _circle_wedges(n)
            sol = _solve(si)
            assert abs(sol.fos - want) < 1e-5, (n, sol.fos)
            _is_the_largest_root(si, sol)

    def test_problem_5_without_its_table(self):
        for n in (2, 10, 25):
            si = _p5_wedges(n)
            sol = _solve(si)
            assert abs(sol.fos - 0.609567) < 1e-5, (n, sol.fos)
        _is_the_largest_root(si, sol)

    def test_where_the_sweep_already_found_it_nothing_moves(self):
        """40, 50 and 60 wedges: the sweep of 1.05 found the largest root
        there, and the enumerator gives the same to Brent's tolerance."""
        for n in (40, 50, 60):
            si = _circle_wedges(n)
            new, old = _solve(si).fos, _solve(si, "sweep").fos
            assert abs(new - old) < 1e-9, (n, new, old)


class TestTheSweepOfBeforeMissedIt:
    """Rule 7: the enumerator moves the number. With the sweep of v0.1.486
    the judge finds a root above the factor."""

    def test_circle_100_and_problem_5(self):
        for si, want in ((_circle_wedges(100), 0.596451),
                         (_p5_wedges(10), 0.595702)):
            sol = _solve(si, "sweep")
            assert abs(sol.fos - want) < 1e-5, sol.fos
            above = _roots_above(_judge(si, sol), sol.fos, 50.0)
            assert above, sol.fos


class TestTheNextRootOfTheNote:
    """``near_pair`` (the note of D452) finds the next root down with the
    same enumerator: on the 40-wedge circle 0.7857, where the sweep gave
    0.7372 and stepped over 0.7857 and 0.7609."""

    def test_circle_40(self):
        from ogr_slip2d.sarma import solver as SV
        si = _circle_wedges(40)
        sol = _solve(si)
        d, nxt = SV.near_pair(si.bases, si.faces, sol.fos,
                              slide_sign=si.slide_sign, tolerance=1e-12)
        assert abs(nxt - 0.785682) < 1e-5, nxt
        judge = _judge(si, sol)
        assert judge.is_root(nxt)
        roots = _roots_above(judge, nxt, sol.fos * (1 - 1e-6), n=600)
        assert roots == [], roots


class TestThePolynomial:
    """H·∏√(1 + tan²φᵢ g²) (one factor per wedge, one of each cancelled
    pair left out) is a polynomial in g of degree 2(n − pairs): interpolated
    at a few more Chebyshev points than that, the coefficients past the
    degree are rounding."""

    def test_its_degree(self):
        import numpy as np
        from numpy.polynomial import chebyshev
        from ogr_slip2d.sarma import solver as SV
        for si in (_p5_wedges(10), _circle_wedges(40)):
            fr = SV._frame(si.bases, si.faces, si.slide_sign, si.head_thrust)
            deg = 2 * (len(fr.alpha) - len(fr.pairs))
            a, b = 0.5, 2.0

            def f(x):
                g = a + (b - a) * (x + 1.0) / 2.0
                return (np.asarray(SV._H(fr, g, 0.0, SV._ARRAY), dtype=float)
                        * SV._root_weights(fr, g))
            c = chebyshev.chebinterpolate(f, deg + 8)
            tail = np.max(np.abs(c[deg + 1:])) / np.max(np.abs(c))
            assert tail < 1e-11, (len(fr.alpha), len(fr.pairs), tail)
