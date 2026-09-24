# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The demo slope, built in ONE place.

v0.1.196 (spec 008) — the interface (*File → Load Demo Slope*) and the
command line (``ogr-slip2d-cli new-demo``) each built their own demo, and
they were NOT the same model: the command line pointed the material at the
water table and set its pore-pressure model, the interface drew the water
table and assigned it to nothing, so its water produced no pore pressure at
all and the two demos gave different factors of safety under one name. The
owner chose the command line's as the canonical one (2026-09-24): a demo
with a water table that does nothing teaches the wrong lesson.

Both front ends, and the operations layer an agent drives, now call
:func:`build_demo_project`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def build_demo_project(name: str = "Demo slope"):
    """A homogeneous 1V:1H slope, 10 m high, with an active water table.

    External boundary (0,0)-(50,0)-(50,15)-(35,15)-(25,25)-(0,25), CCW;
    one Mohr-Coulomb material (c' = 10 kPa, phi' = 25 deg, gamma = 19
    kN/m3); a horizontal water table at y = 8 assigned to it.
    """
    from ..geometry import Boundary, BoundaryType, Polyline, Vertex
    from ..materials import Material, PorePressureType
    from ..materials.builtin_models import MohrCoulomb
    from .project import Project

    p = Project(name)
    ext = Polyline(
        vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                  Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
        closed=True,
    )
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(
        name="Silty clay",
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        unit_weight=19.0, sat_unit_weight=20.5,
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    p.add_material(mat)
    wt = Boundary(polyline=Polyline(vertices=[Vertex(0, 8), Vertex(50, 8)]),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    mat.water_surface_id = wt.id
    p.is_dirty = False
    return p
