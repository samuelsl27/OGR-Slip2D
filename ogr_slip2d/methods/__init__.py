# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Limit Equilibrium Methods — plugin collection.
"""
from .base import LEMMethod, LEMResult, get_method, method_registry, register_method
from .bishop import BishopSimplified
from .gle import GLEMorgensternPrice, constant, half_sine, trapezoidal
from .janbu import JanbuCorrected, JanbuSimplified
from .lowe_karafiath import LoweKarafiath
from .modified_swedish import (
    CorpsOfEngineers1,
    CorpsOfEngineers2,
    PrescribedInclinationMethod,
)
from .ordinary import OrdinaryFellenius
from .spencer import Spencer

__all__ = [
    "LEMMethod",
    "LEMResult",
    "BishopSimplified",
    "JanbuSimplified",
    "JanbuCorrected",
    "OrdinaryFellenius",
    "Spencer",
    "GLEMorgensternPrice",
    "LoweKarafiath",
    "CorpsOfEngineers1",
    "CorpsOfEngineers2",
    "PrescribedInclinationMethod",
    "half_sine",
    "constant",
    "trapezoidal",
    "register_method",
    "method_registry",
    "get_method",
]
