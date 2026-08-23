# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Water Pressure Grid — pore pressure defined by a grid of data points.

Groundwater conditions can be modelled by a set of (x, y, value) data
points, from which the pore pressure at any location is interpolated.
The data may come from field measurements (piezometers) or from an
external seepage analysis. Three grid value types are supported:

    * TOTAL_HEAD      — value = total hydraulic head H  →  u = γw·(H − y)
    * PRESSURE_HEAD   — value = pressure head hp        →  u = γw·hp
    * PORE_PRESSURE   — value = pore pressure u directly

Two spatial interpolation methods are provided:

    * ``tps`` — Thin Plate Spline: the radial-basis surface
      φ(r) = r²·ln r plus a linear polynomial, fitted through every data
      point. Smooth, exact at the data points, and it reproduces planar
      fields exactly (the polynomial part), which is the analytically
      correct behaviour for hydrostatic conditions.

      **Source**: Harder & Desmarais (1972), *Interpolation using
      surface splines*, J. Aircraft 9(2), and Duchon (1976), *Splines
      minimizing rotation-invariant semi-norms in Sobolev spaces*. This
      docstring cited **Franke (1985)** until v0.1.109, and that was
      wrong in a way worth recording: Franke (1985), *Thin plate splines
      with tension*, CAGD 2, is a DIFFERENT surface. Its basis is
      ln(φr/2) + K₀(φr) + γₑ — a modified Bessel function of the second
      kind with a tension parameter φ — and it degenerates to the
      classical spline only as φ → 0. The two agree closely inside the
      data cloud and diverge most where the interpolation EXTRAPOLATES,
      which is exactly where a slip surface near the crest of a slope
      tends to fall: on verification problem 12 six of thirty slice
      bases lie outside the convex hull of the 22 published pressure
      points. The misattribution mattered because it hid the fact that
      the reference this benchmark suite is compared against says it
      uses the tension form; see ``docs/PENDIENTES.md``.
    * ``idw`` — Shepard inverse-distance weighting (power 2) over the
      k nearest points. Robust for very large clouds; used as the
      automatic fallback when the TPS system is ill-conditioned or the
      point count is large (> 300).

This module is self-contained (numpy only) and is consumed by
``ogr_core.hydraulic.pore_pressure`` when the project's groundwater
method is one of the three grid types. It also defines the consumption
interface that the future OGR FEM2D seepage engine will reuse
(Phase 4 of the groundwater plan: the FEM result will simply feed one
of these grids).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None


class GridValueType(Enum):
    TOTAL_HEAD = "total_head"
    PRESSURE_HEAD = "pressure_head"
    PORE_PRESSURE = "pore_pressure"


@dataclass
class WaterPressureGrid:
    """Grid of water-pressure data points with lazy interpolation."""

    points: list[tuple[float, float, float]] = field(default_factory=list)
    value_type: GridValueType = GridValueType.PORE_PRESSURE
    interpolation: str = "tps"          # "tps" | "idw"
    idw_neighbours: int = 8
    allow_suction: bool = False         # keep u < 0 (unsaturated) or clamp

    # -- lazy TPS cache ------------------------------------------------
    _tps_weights: Optional["_np.ndarray"] = field(
        default=None, repr=False, compare=False)
    _tps_pts: Optional["_np.ndarray"] = field(
        default=None, repr=False, compare=False)

    # ==================================================================
    # Serialisation
    # ==================================================================
    def to_dict(self) -> dict:
        return {
            "points": [list(p) for p in self.points],
            "value_type": self.value_type.value,
            "interpolation": self.interpolation,
            "idw_neighbours": self.idw_neighbours,
            "allow_suction": self.allow_suction,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WaterPressureGrid":
        return cls(
            points=[tuple(p) for p in d.get("points", [])],
            value_type=GridValueType(d.get("value_type", "pore_pressure")),
            interpolation=d.get("interpolation", "tps"),
            idw_neighbours=int(d.get("idw_neighbours", 8)),
            allow_suction=bool(d.get("allow_suction", False)),
        )

    # ==================================================================
    # Interpolation of the raw grid VALUE at (x, y)
    # ==================================================================
    def value_at(self, x: float, y: float) -> Optional[float]:
        n = len(self.points)
        if n == 0:
            return None
        if n == 1:
            return self.points[0][2]
        method = self.interpolation
        if method == "tps" and (_np is None or n > 300):
            method = "idw"
        if method == "tps":
            v = self._tps_value(x, y)
            if v is not None:
                return v
            method = "idw"  # ill-conditioned system → fallback
        return self._idw_value(x, y)

    # ------------------------------------------------------------------
    def _ensure_tps(self) -> bool:
        """Fit the TPS once and cache the weights. Returns False if the
        system is singular/ill-conditioned."""
        if self._tps_weights is not None:
            return True
        pts = _np.asarray(self.points, dtype=float)
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
                return False
            w = _np.linalg.solve(M, rhs)
        except _np.linalg.LinAlgError:
            return False
        self._tps_weights = w
        self._tps_pts = xy
        return True

    def _tps_value(self, x: float, y: float) -> Optional[float]:
        if not self._ensure_tps():
            return None
        xy = self._tps_pts
        w = self._tps_weights
        n = len(xy)
        d = _np.linalg.norm(xy - _np.array([x, y]), axis=1)
        with _np.errstate(divide="ignore", invalid="ignore"):
            phi = _np.where(d > 0, d * d * _np.log(d), 0.0)
        return float(phi @ w[:n] + w[n] + w[n + 1] * x + w[n + 2] * y)

    # ------------------------------------------------------------------
    def _idw_value(self, x: float, y: float) -> float:
        """Shepard IDW (power 2) over the k nearest points; exact at
        the data points."""
        best: list[tuple[float, float]] = []  # (d2, value)
        for px, py, pv in self.points:
            d2 = (px - x) ** 2 + (py - y) ** 2
            if d2 < 1e-18:
                return pv
            best.append((d2, pv))
        best.sort(key=lambda t: t[0])
        best = best[: max(1, self.idw_neighbours)]
        wsum = vsum = 0.0
        for d2, pv in best:
            w = 1.0 / d2
            wsum += w
            vsum += w * pv
        return vsum / wsum

    # ==================================================================
    # Pore pressure at (x, y)
    # ==================================================================
    def pore_pressure_at(self, x: float, y: float,
                         gamma_w: float) -> Optional[float]:
        """u [kPa] at (x, y), converting the grid value according to the
        grid type. Suction (u < 0) is clamped to zero unless
        ``allow_suction`` is set."""
        v = self.value_at(x, y)
        if v is None:
            return None
        if self.value_type == GridValueType.TOTAL_HEAD:
            u = gamma_w * (v - y)
        elif self.value_type == GridValueType.PRESSURE_HEAD:
            u = gamma_w * v
        else:  # PORE_PRESSURE
            u = v
        if not self.allow_suction:
            u = max(0.0, u)
        return u
