# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Interpolation of a value scattered over (x, y) points.

v0.1.246 (D229). Two readers need it: the water pressure grid
(``ogr_core.hydraulic.water_pressure_grid``), which interpolates a pore
pressure, and the Discrete Function strength model, which interpolates cu,
or c and φ, over a material. The thin plate spline and the inverse distance
weighting were written for the grid and are moved here unchanged, operation
for operation, so the grid gives the doubles it always gave; the field class
below adds what the Discrete Function needs.

The methods, and where each comes from:

* **Inverse distance** — Shepard (1968), *A two-dimensional interpolation
  function for irregularly-spaced data*, Proc. 23rd ACM National
  Conference: F(P) = Σ wᵢ Fᵢ / Σ wᵢ with wᵢ = 1/‖P − Pᵢ‖², exact at the
  data points. The reference's documentation writes it over every point;
  the grid keeps its k nearest, as it always did.
* **Thin plate spline** — the classical surface spline, φ(r) = r²·ln r plus
  a linear polynomial, fitted through every point (Harder & Desmarais 1972;
  Duchon 1976). It reproduces a planar field exactly. The reference uses
  the form with tension of Franke (1985), a different surface that agrees
  closely inside the data cloud; the difference is documented in the grid.
* **TIN** — the Delaunay triangulation of the points (``scipy.spatial``)
  and the plane of the triangle that holds the point.
* **Linear by elevation** — only the elevations: the value is interpolated
  linearly between the nearest data elevation above and the nearest below,
  and is the end value outside them.

**The secondary method**, as the reference's documentation states it: where
the chosen method cannot answer (a point outside the convex hull of a TIN,
a spline system that cannot be solved), the local thin plate spline over the
ten nearest points answers, and where that fails too, inverse distance.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

try:
    import numpy as _np
except ImportError:  # pragma: no cover - numpy is a hard dependency
    _np = None

#: How many of the nearest points the local thin plate spline fits through:
#: the reference's figure.
LOCAL_TPS_POINTS = 10


# ----------------------------------------------------------------------
# The grid's two methods, moved here unchanged (v0.1.246).
# ----------------------------------------------------------------------
def tps_fit(points: Sequence) -> Optional[tuple]:
    """Fit the thin plate spline through ``points`` (x, y, value).

    Returns ``(weights, xy)`` for :func:`tps_value`, or None when the system
    is singular or ill-conditioned (condition number above 1e12).
    """
    pts = _np.asarray(points, dtype=float)
    xy = pts[:, :2]
    v = pts[:, 2]
    n = len(pts)

    d = _np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
    with _np.errstate(divide="ignore", invalid="ignore"):
        A = _np.where(d > 0, d * d * _np.log(d), 0.0)
    P = _np.hstack([_np.ones((n, 1)), xy])           # [1, x, y]
    M = _np.zeros((n + 3, n + 3))
    M[:n, :n] = A
    M[:n, n:] = P
    M[n:, :n] = P.T
    rhs = _np.concatenate([v, _np.zeros(3)])
    try:
        cond = _np.linalg.cond(M)
        if not math.isfinite(cond) or cond > 1e12:
            return None
        w = _np.linalg.solve(M, rhs)
    except _np.linalg.LinAlgError:
        return None
    return w, xy


def tps_value(fit: tuple, x: float, y: float) -> float:
    """The thin plate spline of :func:`tps_fit` at (x, y)."""
    w, xy = fit
    n = len(xy)
    d = _np.linalg.norm(xy - _np.array([x, y]), axis=1)
    with _np.errstate(divide="ignore", invalid="ignore"):
        phi = _np.where(d > 0, d * d * _np.log(d), 0.0)
    return float(phi @ w[:n] + w[n] + w[n + 1] * x + w[n + 2] * y)


def idw_value(points: Sequence, x: float, y: float,
              neighbours: Optional[int] = None) -> float:
    """Shepard inverse-distance weighting (power 2) at (x, y).

    Over the ``neighbours`` nearest points, or over every point when None;
    exact at a data point.
    """
    best: list[tuple[float, float]] = []  # (d2, value)
    for px, py, pv in points:
        d2 = (px - x) ** 2 + (py - y) ** 2
        if d2 < 1e-18:
            return pv
        best.append((d2, pv))
    best.sort(key=lambda t: t[0])
    if neighbours is not None:
        best = best[: max(1, neighbours)]
    wsum = vsum = 0.0
    for d2, pv in best:
        w = 1.0 / d2
        wsum += w
        vsum += w * pv
    return vsum / wsum


# ----------------------------------------------------------------------
class ScatteredField:
    """A value given at scattered (x, y) points, read anywhere.

    ``method`` is one of :attr:`METHODS`. The fits are built once, on first
    use, and kept: a slope search reads the field at every slice base of
    every trial surface.
    """

    METHODS = ("inverse_distance", "tin", "thin_plate_spline",
               "linear_by_elevation")

    def __init__(self, points: Sequence, method: str = "inverse_distance"):
        if method not in self.METHODS:
            raise ValueError(f"unknown interpolation method {method!r}; "
                             f"one of {self.METHODS}")
        self.points = [(float(x), float(y), float(v)) for x, y, v in points]
        self.method = method
        self._tps = None          # (fit or None) once tried
        self._tps_tried = False
        self._tin = None
        self._tin_tried = False
        self._local: dict = {}
        self._levels = None

    # ------------------------------------------------------------------
    def value_at(self, x: float, y: float) -> float:
        """The field at (x, y). NaN with no points at all."""
        n = len(self.points)
        if n == 0:
            return math.nan
        if n == 1:
            return self.points[0][2]
        if self.method == "inverse_distance":
            return idw_value(self.points, x, y)
        if self.method == "linear_by_elevation":
            return self._by_elevation(y)
        if self.method == "tin":
            v = self._tin_value(x, y)
        else:
            v = self._global_tps(x, y)
        return v if v is not None else self._secondary(x, y)

    # ------------------------------------------------------------------
    def _secondary(self, x: float, y: float) -> float:
        """The local thin plate spline over the nearest points, and inverse
        distance where that cannot be solved either."""
        v = self._local_tps(x, y)
        return v if v is not None else idw_value(self.points, x, y)

    def _global_tps(self, x: float, y: float) -> Optional[float]:
        if not self._tps_tried:
            self._tps_tried = True
            self._tps = tps_fit(self.points) if len(self.points) >= 3 \
                else None
        return None if self._tps is None else tps_value(self._tps, x, y)

    def _local_tps(self, x: float, y: float) -> Optional[float]:
        if len(self.points) <= LOCAL_TPS_POINTS:
            return self._global_tps(x, y)
        order = sorted(range(len(self.points)),
                       key=lambda i: (self.points[i][0] - x) ** 2
                       + (self.points[i][1] - y) ** 2)
        key = tuple(sorted(order[:LOCAL_TPS_POINTS]))
        if key not in self._local:
            self._local[key] = tps_fit([self.points[i] for i in key])
        fit = self._local[key]
        return None if fit is None else tps_value(fit, x, y)

    def _tin_value(self, x: float, y: float) -> Optional[float]:
        if not self._tin_tried:
            self._tin_tried = True
            try:
                from scipy.spatial import Delaunay
                self._tin = Delaunay(_np.asarray(
                    [(px, py) for px, py, _v in self.points], dtype=float))
            except Exception:  # noqa: BLE001 - collinear or too few: no TIN
                self._tin = None
        tri = self._tin
        if tri is None:
            return None
        s = int(tri.find_simplex(_np.array([x, y])))
        if s < 0:
            return None   # outside the convex hull
        t = tri.transform[s]
        b = t[:2].dot(_np.array([x, y]) - t[2])
        bary = (b[0], b[1], 1.0 - b[0] - b[1])
        verts = tri.simplices[s]
        return float(sum(w * self.points[i][2] for w, i in zip(bary, verts)))

    def _by_elevation(self, y: float) -> float:
        """Linear between the nearest data elevations above and below; the
        end value outside them. Points at one elevation count as their
        mean (the reference's documentation does not say)."""
        if self._levels is None:
            by_y: dict = {}
            for _x, py, v in self.points:
                by_y.setdefault(py, []).append(v)
            self._levels = sorted((py, sum(vs) / len(vs))
                                  for py, vs in by_y.items())
        lv = self._levels
        if y <= lv[0][0]:
            return lv[0][1]
        if y >= lv[-1][0]:
            return lv[-1][1]
        for (y0, v0), (y1, v1) in zip(lv, lv[1:]):
            if y0 <= y <= y1:
                return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
        return lv[-1][1]  # pragma: no cover - the loop always brackets
