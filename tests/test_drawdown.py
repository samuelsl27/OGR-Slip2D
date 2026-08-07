# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for the v0.1.8 Rapid Drawdown B-bar pore-pressure model.

Verifies:
    - When Rapid Drawdown is OFF, pore pressure ignores the Drawdown Line
    - When ON with B̄=1, Δu = γw · (y_drawdown - y_wt) (full transfer)
    - When ON with B̄=0.5, half transfer
    - When the drawdown line is below the water table, no extra pressure
"""
from __future__ import annotations

import math


def _make_project(b_bar=None, drawdown_y=None, rapid=True):
    from ogr_core.geometry import (
        Boundary,
        BoundaryType,
        Polyline,
        Vertex,
    )
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    p = Project("dd")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0),
        Vertex(50, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    # Final water table at y=15
    p.add_boundary(Boundary(
        polyline=Polyline(
            vertices=[Vertex(0, 15), Vertex(50, 15)], closed=False),
        btype=BoundaryType.WATER_TABLE,
    ))
    if drawdown_y is not None:
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, drawdown_y), Vertex(50, drawdown_y)],
                closed=False),
            btype=BoundaryType.DRAWDOWN,
        ))
    p.settings.groundwater.rapid_drawdown = rapid
    p.settings.groundwater.rapid_drawdown_method = "b_bar"

    mat = Material(
        name="Soil",
        strength=MohrCoulomb(cohesion=10, friction_angle=25),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    if b_bar is not None:
        mat.b_bar = b_bar
    p.materials = [mat]
    return p, mat


# ======================================================================
class TestBBarDrawdown:
    def test_no_drawdown_line_no_excess(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p, mat = _make_project(b_bar=1.0, drawdown_y=None)
        # h_wt = 15 - 5 = 10 → u = γw · 10 = 98.1 kPa
        u = pore_pressure_at(p, Vertex(25, 5), mat)
        assert math.isclose(u, 9.81 * 10, rel_tol=0.01)

    def test_rapid_off_ignores_drawdown(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p, mat = _make_project(b_bar=1.0, drawdown_y=25.0, rapid=False)
        u = pore_pressure_at(p, Vertex(25, 5), mat)
        # No excess applied — same as steady-state
        assert math.isclose(u, 9.81 * 10, rel_tol=0.01)

    def test_b_bar_one_full_transfer(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p, mat = _make_project(b_bar=1.0, drawdown_y=25.0, rapid=True)
        # u_steady = γw · 10
        # Δu = 1.0 · γw · (25 - 15) = γw · 10
        # total = γw · 20
        u = pore_pressure_at(p, Vertex(25, 5), mat)
        assert math.isclose(u, 9.81 * 20, rel_tol=0.01)

    def test_b_bar_half_transfer(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p, mat = _make_project(b_bar=0.5, drawdown_y=25.0, rapid=True)
        # Δu = 0.5 · γw · 10 = γw · 5
        # total = γw · 15
        u = pore_pressure_at(p, Vertex(25, 5), mat)
        assert math.isclose(u, 9.81 * 15, rel_tol=0.01)

    def test_drawdown_below_wt_no_excess(self):
        """If the drawdown line is BELOW the WT, this isn't a 'drawdown'
        situation — no excess pore pressure should be added."""
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p, mat = _make_project(b_bar=1.0, drawdown_y=10.0, rapid=True)
        u = pore_pressure_at(p, Vertex(25, 5), mat)
        assert math.isclose(u, 9.81 * 10, rel_tol=0.01)
