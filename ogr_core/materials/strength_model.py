# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Abstract constitutive-model (strength) interface.

Every failure criterion in OGR Slip2D is implemented as a subclass of
:class:`StrengthModel`. Adding a new criterion = creating a new subclass
in its own file and registering it with the global ``REGISTRY``. The
core solver and GUI discover it automatically.

Design pattern: Strategy + Plugin Registry.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class StrengthModel(ABC):
    """Base class for all shear-strength constitutive laws.

    Subclasses must declare:
        - ``MODEL_ID``: unique string identifier for serialization
        - ``DISPLAY_NAME``: human-readable name (translatable)
        - ``PARAMETERS``: dict of {name: (default, unit, description)}

    and implement ``shear_strength(sigma_n_eff)``.
    """

    MODEL_ID: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    PARAMETERS: ClassVar[dict[str, tuple[float, str, str]]] = {}

    def __init__(self, **params: float) -> None:
        # Populate with defaults, then override with user-supplied values
        self.params: dict[str, float] = {
            name: default for name, (default, _, _) in self.PARAMETERS.items()
        }
        for key, value in params.items():
            if key not in self.PARAMETERS:
                raise ValueError(
                    f"{self.MODEL_ID}: unknown parameter '{key}'. "
                    f"Valid: {list(self.PARAMETERS)}"
                )
            self.params[key] = float(value)

    # ------------------------------------------------------------------
    @abstractmethod
    def shear_strength(self, sigma_n_eff: float) -> float:
        """Return shear strength τ for a given effective normal stress σ'n.

        Args:
            sigma_n_eff: effective normal stress on the slip surface [kPa].

        Returns:
            Shear strength [kPa].
        """

    # ------------------------------------------------------------------
    def shear_strength_ctx(
        self, sigma_n_eff: float, ctx: "SliceContext | None" = None,
    ) -> float:
        """Context-aware shear strength.

        v0.1.15 — most models depend only on σ'ₙ and ignore ``ctx``.
        Anisotropic and stress-history models (SHANSEP, Anisotropic
        Linear, Generalized Anisotropic, Barton-Bandis with depth, …)
        override this to use the slice base angle, vertical effective
        stress, depth, etc., provided in the SliceContext.

        The default implementation simply delegates to
        :meth:`shear_strength`, so existing models work unchanged.
        """
        return self.shear_strength(sigma_n_eff)

    @property
    def needs_context(self) -> bool:
        """True if this model's strength depends on more than σ'ₙ
        (e.g. base angle or vertical stress). The solver uses this to
        decide whether to call shear_strength_ctx with a populated
        SliceContext. Default False."""
        return False

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"model_id": self.MODEL_ID, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, data: dict) -> "StrengthModel":
        from .registry import REGISTRY

        model_cls = REGISTRY.get(data["model_id"])
        return model_cls(**data.get("params", {}))

    def __repr__(self) -> str:
        kv = ", ".join(f"{k}={v:g}" for k, v in self.params.items())
        return f"{self.__class__.__name__}({kv})"


# ----------------------------------------------------------------------
from dataclasses import dataclass as _dataclass


@_dataclass
class SliceContext:
    """Per-slice context passed to ``shear_strength_ctx`` for models
    whose strength depends on more than the effective normal stress.

    v0.1.15. All fields optional; populated by the LEM solver.

    Attributes:
        base_angle_rad: inclination of the slice base from horizontal
            (α). Used by anisotropic models (the angle between the slip
            direction and the bedding orientation).
        sigma_v_eff: vertical effective stress at the base centre [kPa]
            (overburden minus pore pressure). Used by SHANSEP and
            Vertical-Stress-Ratio models.
        depth: vertical depth below the ground surface at the slice
            base [m]. Used by Barton-Bandis (JCS scaling) and others.
        pore_pressure: pore water pressure at the base [kPa].
        y_base: elevation of the slice base [m].
    """
    base_angle_rad: float = 0.0
    sigma_v_eff: float = 0.0
    depth: float = 0.0
    pore_pressure: float = 0.0
    y_base: float = 0.0
