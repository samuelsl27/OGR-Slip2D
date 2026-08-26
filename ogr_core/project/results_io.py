# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
HDF5 results I/O.

As per the project specification, OGR Slip2D uses a *hybrid* project
format:

    - ``project.ogr``   → JSON file with the geotechnical model
    - ``project.h5``    → HDF5 file with the numerical results

The two live side-by-side (same stem); the JSON model file is the
"source of truth" and is human-readable / version-controllable, while
the HDF5 binary file holds the potentially-large numerical output
(thousands of surfaces × tens of slices × multiple scalars each).

Top-level HDF5 layout:

    /
    ├── meta (group attrs: format_version, method, project_id, ...)
    ├── surfaces/
    │   ├── surface_0000
    │   │   ├── attrs: fos, converged, method, centre_x, centre_y, radius
    │   │   └── slices (dataset, structured array)
    │   ├── surface_0001
    │   └── ...
    └── summary/
        ├── fos_array      (1D)
        ├── centres        (Nx2)
        └── radii          (1D)

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from ogr_slip2d.search import SearchResult

RESULTS_FORMAT_VERSION = "0.1"


# ----------------------------------------------------------------------
def _slice_dtype() -> np.dtype:
    return np.dtype(
        [
            ("index", "i4"),
            ("x_centre", "f8"),
            ("width", "f8"),
            ("base_y_left", "f8"),
            ("base_y_right", "f8"),
            ("base_angle_deg", "f8"),
            ("base_length", "f8"),
            ("height", "f8"),
            ("weight", "f8"),
            ("pore_pressure", "f8"),
            ("surface_pressure", "f8"),
        ]
    )


# ----------------------------------------------------------------------
def save_results(
    path: Path | str,
    search_result: "SearchResult",
    project_id: str = "",
    extra_meta: Optional[dict] = None,
) -> Path:
    """Write a full SearchResult to an HDF5 file. Returns the path."""
    try:
        import h5py
    except ImportError as e:
        raise ImportError(
            "h5py is required to save HDF5 results. "
            "Install with `pip install h5py`."
        ) from e

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    dtype = _slice_dtype()

    with h5py.File(path, "w") as f:
        # Metadata
        f.attrs["format_version"] = RESULTS_FORMAT_VERSION
        f.attrs["project_id"] = project_id
        f.attrs["method"] = search_result.method_id
        f.attrs["n_surfaces"] = len(search_result.evaluations)
        f.attrs["n_valid"] = search_result.valid_count
        f.attrs["n_invalid"] = search_result.invalid_count
        # v0.1.127 — which quantity the run minimised. A results file
        # that records only the factor of safety cannot say which surface
        # was the answer when the answer was a critical seismic
        # coefficient, and "the one with the lowest fos" would be the
        # wrong one.
        f.attrs["objective"] = getattr(search_result, "objective", "fos")
        if extra_meta:
            for k, v in extra_meta.items():
                try:
                    f.attrs[k] = v
                except Exception:  # noqa: BLE001
                    pass

        # Surfaces
        group = f.create_group("surfaces")
        for i, res in enumerate(search_result.evaluations):
            sg = group.create_group(f"surface_{i:05d}")
            sg.attrs["fos"] = float(res.fos) if np.isfinite(res.fos) else np.nan
            sg.attrs["converged"] = res.converged
            sg.attrs["iterations"] = res.iterations
            sg.attrs["method"] = res.method_id
            sg.attrs["is_valid"] = res.is_valid
            sg.attrs["error"] = res.error_message or ""
            # v0.1.127 — the seismic extras, written only when the run
            # produced them, so a file from an ordinary run is byte for
            # byte the file it always was.
            for key in ("ky", "ky_fos", "newmark_displacement"):
                value = (res.details or {}).get(key)
                if value is not None:
                    sg.attrs[key] = (float(value) if np.isfinite(value)
                                     else np.nan)

            sd = res.surface.to_dict()
            sg.attrs["surface_type"] = sd["type"]
            # v0.1.111 — "composite" as well: the type string says which of
            # the two it is, and the centre and radius are what the surface
            # is identified by in either case.
            if sd["type"] in ("circle", "composite"):
                sg.attrs["centre_x"] = sd["centre_x"]
                sg.attrs["centre_y"] = sd["centre_y"]
                sg.attrs["radius"] = sd["radius"]
                if sd.get("x_left") is not None:
                    sg.attrs["x_left"] = sd["x_left"]
                    sg.attrs["x_right"] = sd["x_right"]

            # Slice table
            rows = np.empty(len(res.slices), dtype=dtype)
            for j, s in enumerate(res.slices):
                d = s.to_dict()
                rows[j] = (
                    d["index"],
                    d["x_centre"],
                    d["width"],
                    d["base_y_left"],
                    d["base_y_right"],
                    d["base_angle_deg"],
                    d["base_length"],
                    d["height"],
                    d["weight"],
                    d["pore_pressure"],
                    d["surface_pressure"],
                )
            sg.create_dataset("slices", data=rows, compression="gzip")

        # Summary
        summary = f.create_group("summary")
        fos_arr = np.array(
            [r.fos if r.is_valid else np.nan for r in search_result.evaluations],
            dtype="f8",
        )
        summary.create_dataset("fos_array", data=fos_arr, compression="gzip")

        centres = np.array(
            [
                (r.surface.to_dict().get("centre_x", np.nan),
                 r.surface.to_dict().get("centre_y", np.nan))
                for r in search_result.evaluations
            ],
            dtype="f8",
        )
        summary.create_dataset("centres", data=centres, compression="gzip")

        radii = np.array(
            [r.surface.to_dict().get("radius", np.nan)
             for r in search_result.evaluations],
            dtype="f8",
        )
        summary.create_dataset("radii", data=radii, compression="gzip")

    return path


# ----------------------------------------------------------------------
def load_summary(path: Path | str) -> dict:
    """Lightweight read: metadata + summary arrays only (no per-slice data)."""
    try:
        import h5py
    except ImportError as e:
        raise ImportError("h5py required to read HDF5 results") from e

    path = Path(path)
    with h5py.File(path, "r") as f:
        meta = {k: f.attrs[k] for k in f.attrs.keys()}
        out = {"meta": meta}
        if "summary" in f:
            s = f["summary"]
            out["fos_array"] = s["fos_array"][:]
            out["centres"] = s["centres"][:]
            out["radii"] = s["radii"][:]
        return out
