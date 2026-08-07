# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""FE mesh generation for OGR FEM2D (Phase 1 of the groundwater plan)."""
from .generator import (  # noqa: F401
    discretize_edges,
    generate_mesh,
    generate_mesh_for_project,
)
from .mesh import Element, Mesh, Node  # noqa: F401

__all__ = [
    "Node", "Element", "Mesh",
    "generate_mesh", "generate_mesh_for_project", "discretize_edges",
]
