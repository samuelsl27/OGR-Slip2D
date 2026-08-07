# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Unit system configuration.

All internal computations use SI base (m, kN, kPa, kN/m³, seconds).
Display and input units are converted at the GUI boundary. This keeps
the solver simple and avoids the nightmare of mixed-unit intermediate
calculations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UnitSystem(Enum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class TimeUnit(Enum):
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    MONTHS = "mo"
    YEARS = "yr"


class PermeabilityUnit(Enum):
    M_S = "m/s"
    M_DAY = "m/day"
    M_YEAR = "m/year"
    CM_S = "cm/s"
    MM_HOUR = "mm/hour"


class FailureDirection(Enum):
    RIGHT_TO_LEFT = "R2L"
    LEFT_TO_RIGHT = "L2R"


@dataclass
class Units:
    """Active display-unit configuration for a project.

    v0.1.13 — extended with ``system_id`` to select one of the 6
    detailed unit systems defined in :mod:`ogr_core.units`.

    Pattern A (stored-as-SI):
        - The CORE always stores values in SI (m, kN, kPa, kN/m³).
        - ``system_id`` only affects how values are presented in the
          UI and how they are entered by the user.
        - Changing ``system_id`` does NOT mutate the values in memory;
          dialogs re-render with new units and apply conversions on
          submit.

    The legacy ``system`` (METRIC / IMPERIAL) is retained for backward
    compatibility with v0.1.12 project files. The detailed system_id
    takes precedence when present.
    """
    system: UnitSystem = UnitSystem.METRIC
    time: TimeUnit = TimeUnit.DAYS
    permeability: PermeabilityUnit = PermeabilityUnit.M_S
    failure_direction: FailureDirection = FailureDirection.RIGHT_TO_LEFT
    # v0.1.13 — full Slide-style unit system identifier.
    # One of: metric_kpa | metric_mpa | metric_tonnes |
    #         imperial_tons | imperial_ksf | imperial_psf
    # Defaults to metric_kpa (the internal SI system).
    system_id: str = "metric_kpa"

    def to_dict(self) -> dict:
        return {
            "system": self.system.value,
            "time": self.time.value,
            "permeability": self.permeability.value,
            "failure_direction": self.failure_direction.value,
            "system_id": self.system_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Units":
        # Back-compat: derive system_id from legacy ``system`` if missing.
        sid = data.get("system_id")
        if sid is None:
            legacy = data.get("system", "metric")
            sid = "metric_kpa" if legacy == "metric" else "imperial_psf"
        return cls(
            system=UnitSystem(data.get("system", "metric")),
            time=TimeUnit(data.get("time", "d")),
            permeability=PermeabilityUnit(data.get("permeability", "m/s")),
            failure_direction=FailureDirection(
                data.get("failure_direction", "R2L")
            ),
            system_id=sid,
        )

    def get_system(self):
        """Return the detailed :class:`ogr_core.units.UnitSystem` object
        for the active ``system_id``."""
        # Lazy import to avoid circular imports
        from ogr_core.units import get_system
        return get_system(self.system_id)
