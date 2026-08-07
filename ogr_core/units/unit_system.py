# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Unit systems for OGR Suite.

The 6 unit systems supported (as in the Project Settings → General
dropdown):

    1. metric_mpa     — m, MN, MN/m, MPa, MN/m³
    2. metric_kpa     — m, kN, kN/m, kPa, kN/m³           ← INTERNAL SI
    3. metric_tonnes  — m, tonnes, tonnes/m, tonnes/m², tonnes/m³
    4. imperial_tons  — ft, short tons, tons/ft, tons/ft², tons/ft³
    5. imperial_ksf   — ft, kips, kips/ft, ksf, kips/ft³
    6. imperial_psf   — ft, lbs, lbs/ft, psf, lbs/ft³

PATTERN A — STORED-AS-SI:
    The CORE always stores values in metric_kpa (m, kN, kPa, kN/m³).
    All formulas are written in those units.
    Only the I/O layer (dialogs, displays, file export labels) uses
    other systems via :meth:`UnitSystem.to_user` / :meth:`from_user`.

To change the active system in a project, the values in memory do NOT
change; only the labels and the values shown in dialogs are converted
on display, and on form-submit converted back to SI before storing.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .quantities import Quantity


# ----------------------------------------------------------------------
# SI base — all factors below are ``user_value = SI_value × factor``,
# i.e. multiply an SI internal value by ``factor`` to get the user-system
# value, and divide by ``factor`` to go from user → SI.
# ----------------------------------------------------------------------

# Conversion factors. Length expressed in metres internally.
_FT_PER_M: float = 3.280839895013123              # 1 m = 3.2808 ft
_LB_PER_KN: float = 224.808943099711              # 1 kN ≈ 224.81 lbf
_KIP_PER_KN: float = 0.224808943099711            # 1 kN = 0.2248 kips
_TON_PER_KN: float = 0.112404471549856            # 1 kN = 0.1124 short tons
_TONNE_PER_KN: float = 0.10197162129779284        # 1 kN ≈ 0.1020 tonnes-force
_PSF_PER_KPA: float = 20.88543423315013           # 1 kPa = 20.885 psf
_KSF_PER_KPA: float = 0.020885434233150126        # 1 kPa = 0.02089 ksf
_TONS_PER_FT2_PER_KPA: float = 0.010442717116575064  # 1 kPa = 0.01044 tons/ft²
_TONNES_PER_M2_PER_KPA: float = 0.10197162129779284  # 1 kPa ≈ 0.10197 tonnes/m²
_MPA_PER_KPA: float = 0.001                       # 1 kPa = 0.001 MPa
_MN_PER_KN: float = 0.001                         # 1 kN = 0.001 MN
_CM_PER_M: float = 100.0                          # 1 m = 100 cm
_MM_PER_M: float = 1000.0                         # 1 m = 1000 mm
_IN_PER_FT: float = 12.0                          # 1 ft = 12 in
_IN_PER_M: float = 39.37007874015748              # 1 m = 39.37 in


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class UnitSystem:
    """A complete unit system (one of 6 supported configurations).

    Attributes
    ----------
    id
        Stable identifier ("metric_kpa", "imperial_psf", ...). Used in
        project files and in code; never translated.
    label
        Short human-readable description shown in the Project Settings
        dropdown ("Metric, stress as kPa", ...).
    summary
        One-line summary shown next to the dropdown
        ("m, kN, kN/m, kPa, kN/m³").
    factors
        Map ``{Quantity → multiplier_from_SI}``.
        ``user_value = SI_value × factor``
        ``SI_value   = user_value / factor``
    labels
        Map ``{Quantity → unit_label}`` shown in dialogs ("kPa", "psf", ...).
    """

    id: str
    label: str
    summary: str
    factors: Dict[str, float]
    labels: Dict[str, str]

    # --------------------------------------------------------------
    def to_user(self, si_value: float, q: Quantity) -> float:
        """Convert an SI internal value to user units.

        Parameters
        ----------
        si_value
            The value as stored internally (always SI: m, kN, kPa, kN/m³).
        q
            The :class:`Quantity` of the value.
        """
        f = self.factors.get(q.value, 1.0)
        return si_value * f

    def from_user(self, user_value: float, q: Quantity) -> float:
        """Convert a user-system value to SI internal."""
        f = self.factors.get(q.value, 1.0)
        if f == 0:
            return user_value
        return user_value / f

    def label_for(self, q: Quantity) -> str:
        """Get the unit string for a quantity, e.g. 'kPa', 'psf'."""
        return self.labels.get(q.value, "")


# ----------------------------------------------------------------------
# System 2 — Metric, stress as kPa  (THE INTERNAL SI SYSTEM)
# ----------------------------------------------------------------------
METRIC_KPA = UnitSystem(
    id="metric_kpa",
    label="Metric, stress as kPa",
    summary="m, kN, kN/m, kPa, kN/m³",
    factors={
        Quantity.LENGTH.value:            1.0,           # m
        Quantity.SMALL_LENGTH.value:      _CM_PER_M,     # cm
        Quantity.VERY_SMALL_LENGTH.value: _MM_PER_M,     # mm
        Quantity.AREA.value:              1.0,           # m²
        Quantity.VERY_SMALL_AREA.value:   _MM_PER_M ** 2,  # mm²
        Quantity.VOLUME.value:            1.0,           # m³
        Quantity.ONE_OVER_LENGTH.value:   1.0,           # 1/m
        Quantity.FORCE.value:             1.0,           # kN
        Quantity.WEIGHT.value:            1.0,           # kN
        Quantity.UNIT_WEIGHT.value:       1.0,           # kN/m³
        Quantity.PRESSURE.value:          1.0,           # kPa
        Quantity.SHEAR_STRENGTH.value:    1.0,           # kPa
        Quantity.BOND_STRENGTH.value:     1.0,           # kN/m
        Quantity.JOINT_STIFFNESS.value:   1.0,           # kPa/m
        Quantity.STIFFNESS.value:         1.0,           # kN/m
        Quantity.MOMENT.value:            1.0,           # kNm
        Quantity.HOOP_MOMENT.value:       1.0,           # kNm/m
        Quantity.FLUX.value:              1.0,           # m/s
        Quantity.FLOW_RATE.value:         1.0,           # m³/s
        Quantity.TIME.value:              1.0,           # s
        Quantity.ANGLE.value:             1.0,           # degrees
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "m",
        Quantity.SMALL_LENGTH.value:      "cm",
        Quantity.VERY_SMALL_LENGTH.value: "mm",
        Quantity.AREA.value:              "m²",
        Quantity.VERY_SMALL_AREA.value:   "mm²",
        Quantity.VOLUME.value:            "m³",
        Quantity.ONE_OVER_LENGTH.value:   "1/m",
        Quantity.FORCE.value:             "kN",
        Quantity.WEIGHT.value:            "kN",
        Quantity.UNIT_WEIGHT.value:       "kN/m³",
        Quantity.PRESSURE.value:          "kPa",
        Quantity.SHEAR_STRENGTH.value:    "kPa",
        Quantity.BOND_STRENGTH.value:     "kN/m",
        Quantity.JOINT_STIFFNESS.value:   "kPa/m",
        Quantity.STIFFNESS.value:         "kN/m",
        Quantity.MOMENT.value:            "kNm",
        Quantity.HOOP_MOMENT.value:       "kNm/m",
        Quantity.FLUX.value:              "m/s",
        Quantity.FLOW_RATE.value:         "m³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)

# ----------------------------------------------------------------------
# System 1 — Metric, stress as MPa
# ----------------------------------------------------------------------
METRIC_MPA = UnitSystem(
    id="metric_mpa",
    label="Metric, stress as MPa",
    summary="m, MN, MN/m, MPa, MN/m³",
    factors={
        Quantity.LENGTH.value:            1.0,
        Quantity.SMALL_LENGTH.value:      _CM_PER_M,
        Quantity.VERY_SMALL_LENGTH.value: _MM_PER_M,
        Quantity.AREA.value:              1.0,
        Quantity.VERY_SMALL_AREA.value:   _MM_PER_M ** 2,
        Quantity.VOLUME.value:            1.0,
        Quantity.ONE_OVER_LENGTH.value:   1.0,
        Quantity.FORCE.value:             _MN_PER_KN,    # 0.001
        Quantity.WEIGHT.value:            _MN_PER_KN,
        Quantity.UNIT_WEIGHT.value:       _MN_PER_KN,    # MN/m³
        Quantity.PRESSURE.value:          _MPA_PER_KPA,  # 0.001
        Quantity.SHEAR_STRENGTH.value:    _MPA_PER_KPA,
        Quantity.BOND_STRENGTH.value:     _MN_PER_KN,    # MN/m
        Quantity.JOINT_STIFFNESS.value:   _MPA_PER_KPA,  # MPa/m
        Quantity.STIFFNESS.value:         _MN_PER_KN,    # MN/m
        Quantity.MOMENT.value:            _MN_PER_KN,    # MNm
        Quantity.HOOP_MOMENT.value:       _MN_PER_KN,    # MNm/m
        Quantity.FLUX.value:              1.0,
        Quantity.FLOW_RATE.value:         1.0,
        Quantity.TIME.value:              1.0,
        Quantity.ANGLE.value:             1.0,
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "m",
        Quantity.SMALL_LENGTH.value:      "cm",
        Quantity.VERY_SMALL_LENGTH.value: "mm",
        Quantity.AREA.value:              "m²",
        Quantity.VERY_SMALL_AREA.value:   "mm²",
        Quantity.VOLUME.value:            "m³",
        Quantity.ONE_OVER_LENGTH.value:   "1/m",
        Quantity.FORCE.value:             "MN",
        Quantity.WEIGHT.value:            "MN",
        Quantity.UNIT_WEIGHT.value:       "MN/m³",
        Quantity.PRESSURE.value:          "MPa",
        Quantity.SHEAR_STRENGTH.value:    "MPa",
        Quantity.BOND_STRENGTH.value:     "MN/m",
        Quantity.JOINT_STIFFNESS.value:   "MPa/m",
        Quantity.STIFFNESS.value:         "MN/m",
        Quantity.MOMENT.value:            "MNm",
        Quantity.HOOP_MOMENT.value:       "MNm/m",
        Quantity.FLUX.value:              "m/s",
        Quantity.FLOW_RATE.value:         "m³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)

# ----------------------------------------------------------------------
# System 3 — Metric, stress as tonnes/m²
# ----------------------------------------------------------------------
METRIC_TONNES = UnitSystem(
    id="metric_tonnes",
    label="Metric, stress as tonnes/m²",
    summary="m, tonnes, tonnes/m, tonnes/m², tonnes/m³",
    factors={
        Quantity.LENGTH.value:            1.0,
        Quantity.SMALL_LENGTH.value:      _CM_PER_M,
        Quantity.VERY_SMALL_LENGTH.value: _MM_PER_M,
        Quantity.AREA.value:              1.0,
        Quantity.VERY_SMALL_AREA.value:   _MM_PER_M ** 2,
        Quantity.VOLUME.value:            1.0,
        Quantity.ONE_OVER_LENGTH.value:   1.0,
        Quantity.FORCE.value:             _TONNE_PER_KN,
        Quantity.WEIGHT.value:            _TONNE_PER_KN,
        Quantity.UNIT_WEIGHT.value:       _TONNE_PER_KN,
        Quantity.PRESSURE.value:          _TONNES_PER_M2_PER_KPA,
        Quantity.SHEAR_STRENGTH.value:    _TONNES_PER_M2_PER_KPA,
        Quantity.BOND_STRENGTH.value:     _TONNE_PER_KN,
        Quantity.JOINT_STIFFNESS.value:   _TONNES_PER_M2_PER_KPA,
        Quantity.STIFFNESS.value:         _TONNE_PER_KN,
        Quantity.MOMENT.value:            _TONNE_PER_KN,
        Quantity.HOOP_MOMENT.value:       _TONNE_PER_KN,
        Quantity.FLUX.value:              1.0,
        Quantity.FLOW_RATE.value:         1.0,
        Quantity.TIME.value:              1.0,
        Quantity.ANGLE.value:             1.0,
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "m",
        Quantity.SMALL_LENGTH.value:      "cm",
        Quantity.VERY_SMALL_LENGTH.value: "mm",
        Quantity.AREA.value:              "m²",
        Quantity.VERY_SMALL_AREA.value:   "mm²",
        Quantity.VOLUME.value:            "m³",
        Quantity.ONE_OVER_LENGTH.value:   "1/m",
        Quantity.FORCE.value:             "tonnes",
        Quantity.WEIGHT.value:            "tonnes",
        Quantity.UNIT_WEIGHT.value:       "tonnes/m³",
        Quantity.PRESSURE.value:          "tonnes/m²",
        Quantity.SHEAR_STRENGTH.value:    "tonnes/m²",
        Quantity.BOND_STRENGTH.value:     "tonnes/m",
        Quantity.JOINT_STIFFNESS.value:   "tonnes/m²/m",
        Quantity.STIFFNESS.value:         "tonnes/m",
        Quantity.MOMENT.value:            "tonnesm",
        Quantity.HOOP_MOMENT.value:       "tonnesm/m",
        Quantity.FLUX.value:              "m/s",
        Quantity.FLOW_RATE.value:         "m³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)

# ----------------------------------------------------------------------
# System 4 — Imperial, stress as tons/ft² (short tons = 2000 lb)
# ----------------------------------------------------------------------
IMPERIAL_TONS = UnitSystem(
    id="imperial_tons",
    label="Imperial, stress as tons/ft²",
    summary="ft, short tons (2000 lbs), tons/ft, tons/ft², tons/ft³",
    factors={
        Quantity.LENGTH.value:            _FT_PER_M,
        Quantity.SMALL_LENGTH.value:      _IN_PER_M,     # in
        Quantity.VERY_SMALL_LENGTH.value: _IN_PER_M,
        Quantity.AREA.value:              _FT_PER_M ** 2,
        Quantity.VERY_SMALL_AREA.value:   _IN_PER_M ** 2,
        Quantity.VOLUME.value:            _FT_PER_M ** 3,
        Quantity.ONE_OVER_LENGTH.value:   1.0 / _FT_PER_M,
        Quantity.FORCE.value:             _TON_PER_KN,
        Quantity.WEIGHT.value:            _TON_PER_KN,
        Quantity.UNIT_WEIGHT.value:       _TON_PER_KN / (_FT_PER_M ** 3),
        Quantity.PRESSURE.value:          _TONS_PER_FT2_PER_KPA,
        Quantity.SHEAR_STRENGTH.value:    _TONS_PER_FT2_PER_KPA,
        Quantity.BOND_STRENGTH.value:     _TON_PER_KN / _FT_PER_M,
        Quantity.JOINT_STIFFNESS.value:   _TONS_PER_FT2_PER_KPA / _FT_PER_M,
        Quantity.STIFFNESS.value:         _TON_PER_KN / _FT_PER_M,
        Quantity.MOMENT.value:            _TON_PER_KN * _FT_PER_M,
        Quantity.HOOP_MOMENT.value:       _TON_PER_KN,  # tonsft/ft = tons
        Quantity.FLUX.value:              _FT_PER_M,    # ft/s
        Quantity.FLOW_RATE.value:         _FT_PER_M ** 3,
        Quantity.TIME.value:              1.0,
        Quantity.ANGLE.value:             1.0,
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "ft",
        Quantity.SMALL_LENGTH.value:      "in",
        Quantity.VERY_SMALL_LENGTH.value: "in",
        Quantity.AREA.value:              "ft²",
        Quantity.VERY_SMALL_AREA.value:   "in²",
        Quantity.VOLUME.value:            "ft³",
        Quantity.ONE_OVER_LENGTH.value:   "1/ft",
        Quantity.FORCE.value:             "tons",
        Quantity.WEIGHT.value:            "tons",
        Quantity.UNIT_WEIGHT.value:       "tons/ft³",
        Quantity.PRESSURE.value:          "tons/ft²",
        Quantity.SHEAR_STRENGTH.value:    "tons/ft²",
        Quantity.BOND_STRENGTH.value:     "tons/ft",
        Quantity.JOINT_STIFFNESS.value:   "tons/ft²/ft",
        Quantity.STIFFNESS.value:         "tons/ft",
        Quantity.MOMENT.value:            "tonsft",
        Quantity.HOOP_MOMENT.value:       "tonsft/ft",
        Quantity.FLUX.value:              "ft/s",
        Quantity.FLOW_RATE.value:         "ft³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)

# ----------------------------------------------------------------------
# System 5 — Imperial, stress as ksf  (1 kip = 1000 lbf)
# ----------------------------------------------------------------------
IMPERIAL_KSF = UnitSystem(
    id="imperial_ksf",
    label="Imperial, stress as ksf",
    summary="ft, kips, kips/ft, ksf, kips/ft³",
    factors={
        Quantity.LENGTH.value:            _FT_PER_M,
        Quantity.SMALL_LENGTH.value:      _IN_PER_M,
        Quantity.VERY_SMALL_LENGTH.value: _IN_PER_M,
        Quantity.AREA.value:              _FT_PER_M ** 2,
        Quantity.VERY_SMALL_AREA.value:   _IN_PER_M ** 2,
        Quantity.VOLUME.value:            _FT_PER_M ** 3,
        Quantity.ONE_OVER_LENGTH.value:   1.0 / _FT_PER_M,
        Quantity.FORCE.value:             _KIP_PER_KN,
        Quantity.WEIGHT.value:            _KIP_PER_KN,
        Quantity.UNIT_WEIGHT.value:       _KIP_PER_KN / (_FT_PER_M ** 3),
        Quantity.PRESSURE.value:          _KSF_PER_KPA,
        Quantity.SHEAR_STRENGTH.value:    _KSF_PER_KPA,
        Quantity.BOND_STRENGTH.value:     _KIP_PER_KN / _FT_PER_M,
        Quantity.JOINT_STIFFNESS.value:   _KSF_PER_KPA / _FT_PER_M,
        Quantity.STIFFNESS.value:         _KIP_PER_KN / _FT_PER_M,
        Quantity.MOMENT.value:            _KIP_PER_KN * _FT_PER_M,
        Quantity.HOOP_MOMENT.value:       _KIP_PER_KN,
        Quantity.FLUX.value:              _FT_PER_M,
        Quantity.FLOW_RATE.value:         _FT_PER_M ** 3,
        Quantity.TIME.value:              1.0,
        Quantity.ANGLE.value:             1.0,
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "ft",
        Quantity.SMALL_LENGTH.value:      "in",
        Quantity.VERY_SMALL_LENGTH.value: "in",
        Quantity.AREA.value:              "ft²",
        Quantity.VERY_SMALL_AREA.value:   "in²",
        Quantity.VOLUME.value:            "ft³",
        Quantity.ONE_OVER_LENGTH.value:   "1/ft",
        Quantity.FORCE.value:             "kips",
        Quantity.WEIGHT.value:            "kips",
        Quantity.UNIT_WEIGHT.value:       "kips/ft³",
        Quantity.PRESSURE.value:          "ksf",
        Quantity.SHEAR_STRENGTH.value:    "ksf",
        Quantity.BOND_STRENGTH.value:     "kips/ft",
        Quantity.JOINT_STIFFNESS.value:   "ksf/ft",
        Quantity.STIFFNESS.value:         "kips/ft",
        Quantity.MOMENT.value:            "kipsft",
        Quantity.HOOP_MOMENT.value:       "kipsft/ft",
        Quantity.FLUX.value:              "ft/s",
        Quantity.FLOW_RATE.value:         "ft³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)

# ----------------------------------------------------------------------
# System 6 — Imperial, stress as psf
# ----------------------------------------------------------------------
IMPERIAL_PSF = UnitSystem(
    id="imperial_psf",
    label="Imperial, stress as psf",
    summary="ft, lbs, lbs/ft, psf, lbs/ft³",
    factors={
        Quantity.LENGTH.value:            _FT_PER_M,
        Quantity.SMALL_LENGTH.value:      _IN_PER_M,
        Quantity.VERY_SMALL_LENGTH.value: _IN_PER_M,
        Quantity.AREA.value:              _FT_PER_M ** 2,
        Quantity.VERY_SMALL_AREA.value:   _IN_PER_M ** 2,
        Quantity.VOLUME.value:            _FT_PER_M ** 3,
        Quantity.ONE_OVER_LENGTH.value:   1.0 / _FT_PER_M,
        Quantity.FORCE.value:             _LB_PER_KN,
        Quantity.WEIGHT.value:            _LB_PER_KN,
        Quantity.UNIT_WEIGHT.value:       _LB_PER_KN / (_FT_PER_M ** 3),
        Quantity.PRESSURE.value:          _PSF_PER_KPA,
        Quantity.SHEAR_STRENGTH.value:    _PSF_PER_KPA,
        Quantity.BOND_STRENGTH.value:     _LB_PER_KN / _FT_PER_M,
        Quantity.JOINT_STIFFNESS.value:   _PSF_PER_KPA / _FT_PER_M,
        Quantity.STIFFNESS.value:         _LB_PER_KN / _FT_PER_M,
        Quantity.MOMENT.value:            _LB_PER_KN * _FT_PER_M,
        Quantity.HOOP_MOMENT.value:       _LB_PER_KN,
        Quantity.FLUX.value:              _FT_PER_M,
        Quantity.FLOW_RATE.value:         _FT_PER_M ** 3,
        Quantity.TIME.value:              1.0,
        Quantity.ANGLE.value:             1.0,
        Quantity.DIMENSIONLESS.value:     1.0,
    },
    labels={
        Quantity.LENGTH.value:            "ft",
        Quantity.SMALL_LENGTH.value:      "in",
        Quantity.VERY_SMALL_LENGTH.value: "in",
        Quantity.AREA.value:              "ft²",
        Quantity.VERY_SMALL_AREA.value:   "in²",
        Quantity.VOLUME.value:            "ft³",
        Quantity.ONE_OVER_LENGTH.value:   "1/ft",
        Quantity.FORCE.value:             "lbs",
        Quantity.WEIGHT.value:            "lbs",
        Quantity.UNIT_WEIGHT.value:       "lbs/ft³",
        Quantity.PRESSURE.value:          "psf",
        Quantity.SHEAR_STRENGTH.value:    "psf",
        Quantity.BOND_STRENGTH.value:     "lbs/ft",
        Quantity.JOINT_STIFFNESS.value:   "psf/ft",
        Quantity.STIFFNESS.value:         "lbs/ft",
        Quantity.MOMENT.value:            "lbsft",
        Quantity.HOOP_MOMENT.value:       "lbsft/ft",
        Quantity.FLUX.value:              "ft/s",
        Quantity.FLOW_RATE.value:         "ft³/s",
        Quantity.TIME.value:              "s",
        Quantity.ANGLE.value:             "°",
        Quantity.DIMENSIONLESS.value:     "",
    },
)


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------
SYSTEMS: Dict[str, UnitSystem] = {
    METRIC_KPA.id:    METRIC_KPA,
    METRIC_MPA.id:    METRIC_MPA,
    METRIC_TONNES.id: METRIC_TONNES,
    IMPERIAL_TONS.id: IMPERIAL_TONS,
    IMPERIAL_KSF.id:  IMPERIAL_KSF,
    IMPERIAL_PSF.id:  IMPERIAL_PSF,
}

DEFAULT_SYSTEM_ID: str = METRIC_KPA.id
"""Default unit system used internally and on first project creation."""


def get_system(system_id: str) -> UnitSystem:
    """Look up a unit system by id; falls back to METRIC_KPA if unknown."""
    return SYSTEMS.get(system_id, METRIC_KPA)
