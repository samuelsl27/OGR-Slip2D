# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The per-slice and per-face numbers a result is shown and exported with,
in ONE place for every reader: the PDF report (``ogr_core.report``),
Interpret's panel and CSV (``ogr_slip2d.interpretation``, which delegates
here), the API (``ogr_api.results``) and the HDF5 file
(``ogr_core.project.results_io``).

In the core, below the engine (AGENTS.md: the layers run one way), so the
results are read by their attributes and nothing of ``ogr_slip2d`` is
imported. Not inside ``ogr_core.report``, whose package imports reportlab:
the API and the engine would load the report to read a row.

v0.1.468 (D357, D453): moved here from ``ogr_slip2d.interpretation`` so the
report can ask the same rule. The report printed the method's base FORCES
under «Base σ [kPa]» and «Shear str. [kPa]» (D453), because it read the
arrays and did not divide them, while the panel did.
"""
from __future__ import annotations

import math
from typing import Optional


def per_slice(result, name: str, index) -> Optional[float]:
    """One entry of a result's per-slice array (``base_normal_force``,
    ``base_shear_force``, ``base_shear_strength``), or None.

    Those are computed by the METHOD and live on the result, not on the
    slice: a reader handed only the slice cannot show them."""
    if result is None:
        return None
    arr = getattr(result, name, None)
    if not arr or index is None or not (0 <= index < len(arr)):
        return None
    v = arr[index]
    return v if isinstance(v, (int, float)) and math.isfinite(v) else None


def slice_stress(result, name: str, slice_) -> Optional[float]:
    """A per-slice force of the method divided by the base length: the
    stress the reference reports [kPa]. ``base_normal_force`` gives σn,
    ``base_shear_strength`` gives τ_f."""
    f = per_slice(result, name, getattr(slice_, "index", None))
    length = getattr(slice_, "base_length", 0.0) or 0.0
    if f is None or length <= 0:
        return None
    return f / length


def face_rows(result) -> list:
    """One dict per face of a result of Sarma's method on wedges, in
    increasing x, or ``[]`` for any other result (v0.1.468, D357).

    ``index`` counts from 0, as the wedges do (``Slice.index``): wedge k
    lies between faces k and k + 1. The first face is the toe's when the
    mass slides toward −x and the head's when it slides toward +x.

    The geometry and the strength of each face (``WedgeFace``: base and top
    points, θ in degrees counter-clockwise from +x, length, the water thrust
    PW, c̄ and φ̄ before the reduction by F, and where the angle and the
    strength came from) and the forces the method solved on it
    (``details["sarma_face_thrusts"]``, ``"sarma_face_effective"``,
    ``"sarma_face_shears"``: E, E′ = E − PW and X in the method's frame, so
    the mirror image of a slope gives the same values; None where the
    result has no factor or a q vanished at it). PW is the method's
    (``"sarma_face_water"``): on the head face, the water of a tension
    crack, which the face itself gives as 0. A spilled population answers
    ``faces`` from the fields its stub keeps (``wedge_fields``)."""
    faces = getattr(getattr(result, "slices", None), "faces", None)
    if not faces:
        return []
    d = getattr(result, "details", None) or {}

    def column(key):
        v = d.get(key)
        return list(v) if v else []
    E = column("sarma_face_thrusts")
    Ee = column("sarma_face_effective")
    X = column("sarma_face_shears")
    W = column("sarma_face_water")

    def at(values, j):
        return values[j] if j < len(values) else None
    rows = []
    for j, f in enumerate(faces):
        rows.append({
            "index": j,
            "x_base": f.x_base, "y_base": f.y_base,
            "x_top": f.x_top, "y_top": f.y_top,
            "angle_deg": math.degrees(f.theta),
            "length": f.length,
            "water_force": (W[j] if j < len(W) and W[j] is not None
                            else f.water_force),
            "cohesion": f.cohesion,
            "friction_angle": math.degrees(math.atan(f.tan_phi)),
            "angle_source": f.angle_source,
            "strength_source": f.strength_source,
            "E": at(E, j), "E_effective": at(Ee, j), "X": at(X, j),
        })
    return rows
