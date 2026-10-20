# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Finite-element mesh data structures: moved to :mod:`ogr_core.fem.mesh`.

v0.1.342 (D337) -- the project stores the mesh and the core rebuilds it on
load, so the data structures are the core's. This module re-exports them,
the same objects, so every import of ``ogr_fem2d.mesh.mesh`` keeps working.

Author: Samuel Sáez López (UPCT)
"""
from ogr_core.fem.mesh import (  # noqa: F401
    DEGENERATE_SHAPE_RATIO,
    Element,
    Mesh,
    Node,
    triangle_shape_ratio,
)

__all__ = ["DEGENERATE_SHAPE_RATIO", "triangle_shape_ratio", "Node",
           "Element", "Mesh"]
