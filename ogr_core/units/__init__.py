# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Unit-system management for OGR Suite — Pattern A (stored as SI).

Quick reference:

    from ogr_core.units import (
        Quantity, UnitSystem, SYSTEMS, get_system, DEFAULT_SYSTEM_ID,
    )

    sys_ = get_system("imperial_psf")
    psf  = sys_.to_user(10.0, Quantity.PRESSURE)         # 10 kPa → 208.85 psf
    kpa  = sys_.from_user(208.85, Quantity.PRESSURE)     # 208.85 psf → 10 kPa
    label = sys_.label_for(Quantity.PRESSURE)            # "psf"

The CORE always stores values in SI (m, kN, kPa, kN/m³). Only the I/O
layer (dialogs, displays, file export/import) uses the active system.
"""
from .quantities import Quantity
from .unit_system import (
    DEFAULT_SYSTEM_ID,
    IMPERIAL_KSF,
    IMPERIAL_PSF,
    IMPERIAL_TONS,
    METRIC_KPA,
    METRIC_MPA,
    METRIC_TONNES,
    SYSTEMS,
    UnitSystem,
    get_system,
)

__all__ = [
    "Quantity",
    "UnitSystem",
    "SYSTEMS",
    "DEFAULT_SYSTEM_ID",
    "get_system",
    "METRIC_KPA",
    "METRIC_MPA",
    "METRIC_TONNES",
    "IMPERIAL_TONS",
    "IMPERIAL_KSF",
    "IMPERIAL_PSF",
]
