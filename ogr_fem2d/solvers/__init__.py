# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Finite-element solvers for OGR FEM2D."""
from .seepage import (  # noqa: F401
    BCType,
    NodeBC,
    SeepageBoundaryConditions,
    SeepageResult,
    SeepageSolver,
    SegmentBC,
    default_boundary_conditions,
    solve_project_seepage,
    UnsaturatedSeepageSolver,
    TransientSeepageSolver,
    TransientStage,
)

__all__ = [
    "BCType", "NodeBC", "SegmentBC", "SeepageBoundaryConditions",
    "SeepageSolver", "SeepageResult", "default_boundary_conditions",
    "solve_project_seepage", "UnsaturatedSeepageSolver", "TransientSeepageSolver", "TransientStage",
]
