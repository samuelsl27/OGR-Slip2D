# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Strength-model plugin registry.

This is the dynamic discovery mechanism. Register new models with the
``@register`` decorator; the GUI's dropdown and the solver's dispatcher
will pick them up without any further wiring.

Usage:

    from ogr_core.materials.registry import register
    from ogr_core.materials.strength_model import StrengthModel

    @register
    class MyNewCriterion(StrengthModel):
        MODEL_ID = "my_criterion"
        ...

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Type

from .strength_model import StrengthModel


class _Registry:
    """Thread-safe-enough registry of StrengthModel subclasses."""

    def __init__(self) -> None:
        self._models: dict[str, Type[StrengthModel]] = {}

    def register(self, model_cls: Type[StrengthModel]) -> Type[StrengthModel]:
        if not issubclass(model_cls, StrengthModel):
            raise TypeError(f"{model_cls} is not a StrengthModel subclass")
        if not model_cls.MODEL_ID:
            raise ValueError(f"{model_cls.__name__} has no MODEL_ID")
        if model_cls.MODEL_ID in self._models:
            raise ValueError(
                f"Duplicate MODEL_ID '{model_cls.MODEL_ID}' "
                f"({model_cls.__name__} vs {self._models[model_cls.MODEL_ID].__name__})"
            )
        self._models[model_cls.MODEL_ID] = model_cls
        return model_cls

    def get(self, model_id: str) -> Type[StrengthModel]:
        if model_id not in self._models:
            # v0.1.437 (D414) -- with its code; the KeyError and its text
            # are what the agent and test_strength_refusals_v1351 read
            from ..file_messages import STRENGTH_MODEL_UNKNOWN, file_refusal
            raise KeyError(file_refusal(
                STRENGTH_MODEL_UNKNOWN,
                f"Unknown strength model: '{model_id}'. "
                f"Available: {list(self._models)}",
                model_id=model_id, available=list(self._models)))
        return self._models[model_id]

    def all(self) -> dict[str, Type[StrengthModel]]:
        return dict(self._models)

    def ids(self) -> list[str]:
        return list(self._models)


REGISTRY = _Registry()


def register(cls: Type[StrengthModel]) -> Type[StrengthModel]:
    """Decorator for registering a strength model."""
    return REGISTRY.register(cls)
