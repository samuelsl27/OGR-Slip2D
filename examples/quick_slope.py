# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
examples/quick_slope.py
-----------------------
End-to-end demo of OGR Slip2D:

    1. Take the demo slope (homogeneous, one Mohr-Coulomb material, a water
       table), no GUI.
    2. Run a grid search with Bishop Simplified.
    3. Print the critical Factor of Safety.

Run from repository root:

    python -m examples.quick_slope

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

from ogr_core.project import Project, save_results
from ogr_core.project.demo import build_demo_project
from ogr_slip2d import BishopSimplified, GridSearch


def build_demo_slope() -> Project:
    """The demo slope of ``ogr_core.project.demo``, under this example's
    name: a homogeneous slope 10 m high with a 1V:1H face and a horizontal
    water table at y = 8.

        (0, 25) ────────── (25, 25)  crest
           │                    \\
           │                     \\  face 1V:1H
           │                      \\
           │              toe (35, 15) ────── (50, 15)
           │                                      │
        (0, 0) ──────────────────────────────── (50, 0)

    External boundary (0,0)-(50,0)-(50,15)-(35,15)-(25,25)-(0,25), CCW; one
    Mohr-Coulomb material, c' = 10 kPa, phi' = 25 deg, gamma = 19 kN/m3.

    v0.1.457 (D426) -- until this version the example built a second copy of
    the same slope by hand (since v0.1.59), with the default failure
    direction, Right to Left, while its ground is higher on the left: every
    run through ``run_analysis``, and ``project_validate``, warned that the
    declaration contradicted the geometry. It is now ``build_demo_project``,
    which declares Left to Right since v0.1.329 (D328): one demo slope. No
    number moves, measured in one process: the declaration (the 18 critical
    surfaces of nine searches with Bishop and Janbu, the same bit for bit
    under both), and the new copy against the old one, whose vertices were
    floats where the demo's are integers (every population the same bit for
    bit). What changes is the material's colour, the demo's now; the project
    starts with no unsaved changes; and the coordinates are integers, so
    ``main()`` prints ``bbox = (0, 0, 50, 25)`` and the PDF report lists
    ``0`` where it listed ``0.000``.
    """
    return build_demo_project(name="Demo homogeneous slope")


def surface_counts(result) -> str:
    """The line ``main`` prints about the population: every surface the
    search generated (``total_count``), the valid ones (``analysed_count``,
    converged and through the post-checks: the ones that can be critical)
    and the rest, invalid, as the reference's report counts them.

    v0.1.457 -- it said «Evaluated 118 surfaces (valid: 90, invalid: 57)»,
    and the parts did not add up to the whole: 118 was ``len(evaluations)``,
    the surfaces sliced, while the invalid count includes the 29 rejected
    before slicing, which leave no evaluation. Of the 147 generated, 90 are
    valid and 57 invalid.
    """
    generated = result.total_count
    valid = result.analysed_count
    return (f"Generated {generated} surfaces "
            f"(valid: {valid}, invalid: {generated - valid})")


def main():
    """Run the example and print what it found; return the search result."""
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
    print(surface_counts(result))

    critical = result.critical
    if critical is None:
        print("No valid failure surface found.")
        return result

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
    return result


if __name__ == "__main__":
    main()
