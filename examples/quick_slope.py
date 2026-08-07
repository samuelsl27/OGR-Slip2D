# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
examples/quick_slope.py
-----------------------
End-to-end demo of OGR Slip2D:

    1. Build a small homogeneous slope model (no GUI).
    2. Add a Mohr-Coulomb material and a water table.
    3. Run a grid search with Bishop Simplified.
    4. Print the critical Factor of Safety.

Run from repository root:

    python -m examples.quick_slope

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, MohrCoulomb, PorePressureType
from ogr_core.project import Project, save_results
from ogr_slip2d import BishopSimplified, GridSearch


def build_demo_slope() -> Project:
    """A simple 2D slope:

           crest (25, 25) ─── (50, 25)
                        \\
                         \\  slope 1:2
                          \\
                           toe (35, 15)
                                 |
                                 └─── (50, 15)   ground in front
        origin (0, 0)  ───  (25, 15)            ground behind

    External boundary is a closed CCW polygon.
    """
    project = Project(name="Demo homogeneous slope")

    # External boundary (closed polygon, CCW)
    ext_poly = Polyline(
        vertices=[
            Vertex(0.0, 0.0),     # BL corner
            Vertex(50.0, 0.0),    # BR corner
            Vertex(50.0, 15.0),   # front ground
            Vertex(35.0, 15.0),   # toe
            Vertex(25.0, 25.0),   # crest
            Vertex(0.0, 25.0),    # back crest
        ],
        closed=True,
    )
    ext_poly.ensure_ccw()
    project.add_boundary(Boundary(polyline=ext_poly, btype=BoundaryType.EXTERNAL))

    # Material
    mat = Material(
        name="Silty clay",
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        unit_weight=19.0,
        sat_unit_weight=20.5,
        pore_pressure=PorePressureType.WATER_TABLE,
        color="#a0522d",
    )
    project.add_material(mat)

    # Water table (a low, horizontal line for pore pressure generation)
    wt_poly = Polyline(
        vertices=[Vertex(0.0, 8.0), Vertex(50.0, 8.0)],
        closed=False,
    )
    wt = Boundary(polyline=wt_poly, btype=BoundaryType.WATER_TABLE)
    project.add_boundary(wt)
    mat.water_surface_id = wt.id

    return project


def main() -> None:
    project = build_demo_slope()
    print(f"Project '{project.name}' — bbox = {project.bounding_box()}")
    print(f"Materials: {len(project.materials)}, boundaries: {len(project.boundaries)}")

    method = BishopSimplified(tolerance=1e-3, max_iterations=60)
    search = GridSearch(
        method=method,
        grid_nx=6,
        grid_ny=6,
        radius_increment=1.5,
        min_radius=4.0,
        num_slices=25,
        min_area=2.0,
    )
    print("\nRunning Bishop Simplified grid search...")
    result = search.run(project)
    print(f"Evaluated {len(result.evaluations)} surfaces "
          f"(valid: {result.valid_count}, invalid: {result.invalid_count})")

    critical = result.critical
    if critical is None:
        print("No valid failure surface found.")
        return

    s = critical.surface.to_dict()
    print("\n── Critical surface ──")
    print(f"  FoS          = {critical.fos:.4f}")
    print(f"  converged    = {critical.converged}")
    print(f"  iterations   = {critical.iterations}")
    print(f"  centre       = ({s['centre_x']:.2f}, {s['centre_y']:.2f})")
    print(f"  radius       = {s['radius']:.2f} m")
    print(f"  x_left, x_right = {s.get('x_left'):.2f}, {s.get('x_right'):.2f}")
    print(f"  n slices     = {len(critical.slices)}")

    out_path = Path("quick_slope_results.h5")
    save_results(out_path, result, project_id=project.id)
    print(f"\nResults saved to {out_path.resolve()}")


if __name__ == "__main__":
    main()
