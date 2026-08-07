# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Annotation layer: drawing primitives that take no part in the analysis."""
from .annotation import (  # noqa: F401
    CONVERTIBLE_KINDS,
    Annotation,
    AnnotationKind,
    AnnotationLayer,
    AnnotationStyle,
    to_boundary_points,
)

__all__ = [
    "Annotation", "AnnotationKind", "AnnotationStyle", "AnnotationLayer",
    "to_boundary_points", "CONVERTIBLE_KINDS",
]
