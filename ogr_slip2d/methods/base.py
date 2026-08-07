# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Abstract base class & plugin registry for Limit Equilibrium Methods.

Each LEM method is a subclass of :class:`LEMMethod` registered with the
``@register_method`` decorator. The GUI dropdown and the CLI ``--method``
flag both enumerate the registry, so adding a new method requires
**only** creating a new file in this package.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional

from ogr_core.materials import Material
from ogr_core.project import Project

from ..slicer import Slices
from ..surface import SurfaceProtocol


# ======================================================================
@dataclass
class LEMResult:
    """Result of a single FoS calculation on a specific slip surface."""

    fos: float
    converged: bool
    iterations: int
    method_id: str
    surface: SurfaceProtocol
    slices: Slices
    error_message: str = ""

    # Per-slice arrays (useful for post-processing plots)
    base_normal: list[float] = field(default_factory=list)
    base_shear_force: list[float] = field(default_factory=list)
    base_shear_strength: list[float] = field(default_factory=list)

    # v0.1.22 — method-specific extras. Recognised keys:
    #   "boundary_ratios": list[float] of X/E at each of the n+1 slice
    #       boundaries (used by the line-of-thrust post-processor).
    #       Methods that assume X = 0 (Bishop, Janbu, Ordinary) may omit
    #       it; zeros are assumed.
    #   "lambda": converged interslice scaling (Spencer: tanθ; GLE: λ).
    details: dict = field(default_factory=dict)

    # v0.1.32 — post-analysis admissibility (anomaly A3). Surfaces that
    # fail the Tensile Stress or m-alpha checks stay in the evaluation
    # list (so search algorithms that need feedback, such as Simulated
    # Annealing, keep working) but are excluded when the CRITICAL
    # surface is selected.
    admissible: bool = True
    # Why the surface was judged inadmissible. Deliberately NOT stored in
    # ``error_message``: that field marks a FAILED calculation and feeds
    # ``is_valid``, whereas an inadmissible surface has a perfectly
    # converged (but physically unreliable) factor of safety.
    admissibility_note: str = ""

    @property
    def is_valid(self) -> bool:
        return (
            self.converged
            and math.isfinite(self.fos)
            and self.fos > 0
            and not self.error_message
        )

    def to_dict(self) -> dict:
        return {
            "fos": self.fos,
            "converged": self.converged,
            "iterations": self.iterations,
            "method": self.method_id,
            "surface": self.surface.to_dict(),
            "slices": self.slices.to_list(),
            "base_normal": list(self.base_normal),
            "base_shear_force": list(self.base_shear_force),
            "base_shear_strength": list(self.base_shear_strength),
            "error": self.error_message,
        }


# ======================================================================
class LEMMethod(ABC):
    """Abstract Limit Equilibrium Method.

    Concrete subclasses must implement :meth:`compute_fos` for a single
    pre-sliced failure surface.
    """

    METHOD_ID: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    SATISFIES_FORCE: ClassVar[bool] = False
    SATISFIES_MOMENT: ClassVar[bool] = False

    def __init__(
        self,
        tolerance: float = 1e-3,
        max_iterations: int = 75,
        initial_fos: float = 1.0,
    ) -> None:
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.initial_fos = initial_fos

    # ------------------------------------------------------------------
    @abstractmethod
    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        """Compute the Factor of Safety for one failure surface."""

    # ------------------------------------------------------------------
    @staticmethod
    def _shear_strength(material: Optional[Material], sigma_n_eff: float) -> float:
        if material is None:
            return 0.0
        return material.strength.shear_strength(sigma_n_eff)


# ======================================================================
_METHOD_REGISTRY: dict[str, type[LEMMethod]] = {}


def register_method(cls: type[LEMMethod]) -> type[LEMMethod]:
    if not cls.METHOD_ID:
        raise ValueError(f"{cls.__name__} has no METHOD_ID")
    if cls.METHOD_ID in _METHOD_REGISTRY:
        raise ValueError(f"Duplicate METHOD_ID: {cls.METHOD_ID}")
    _METHOD_REGISTRY[cls.METHOD_ID] = cls
    return cls


def method_registry() -> dict[str, type[LEMMethod]]:
    return dict(_METHOD_REGISTRY)


def get_method(method_id: str) -> type[LEMMethod]:
    if method_id not in _METHOD_REGISTRY:
        raise KeyError(
            f"Unknown method '{method_id}'. Available: {list(_METHOD_REGISTRY)}"
        )
    return _METHOD_REGISTRY[method_id]
