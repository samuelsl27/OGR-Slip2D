# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The finite-element data the project stores (v0.1.342, D337).

``Project.from_dict`` rebuilds a mesh, the seepage boundary conditions and
the seepage results from a ``.ogr``, and until this version it imported them
from ``ogr_fem2d``: the core reached up into an engine. They are data and
the closed-form identities that rebuild their derived fields, so they live
here; the solvers stay in ``ogr_fem2d``, which re-exports these names at
their old paths so every import of them keeps working and ``isinstance``
sees one class.

There is no registry the engine would fill at import: loading a model
before importing the engine would then leave ``fem_mesh = None``, and the
next save would write the mesh away without a word.

Author: Samuel Sáez López (UPCT)
"""
from .mesh import (  # noqa: F401
    DEGENERATE_SHAPE_RATIO,
    Element,
    Mesh,
    Node,
    triangle_shape_ratio,
)
from .seepage_data import (  # noqa: F401
    BCType,
    NodeBC,
    SeepageBoundaryConditions,
    SeepageResult,
    SegmentBC,
    element_fluxes,
    hydraulic_props_of,
    restore_derived,
)

__all__ = [
    "DEGENERATE_SHAPE_RATIO", "Element", "Mesh", "Node",
    "triangle_shape_ratio", "BCType", "NodeBC", "SegmentBC",
    "SeepageBoundaryConditions", "SeepageResult", "element_fluxes",
    "hydraulic_props_of", "restore_derived",
]
