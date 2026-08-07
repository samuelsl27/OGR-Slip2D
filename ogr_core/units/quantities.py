# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Physical quantities used throughout OGR Suite.

Each Quantity is a category of measurement (length, force, pressure, ...).
Unit conversion functions in :mod:`conversions` map values between SI
(internal) and any user unit system.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from enum import Enum


class Quantity(str, Enum):
    """Enumeration of physical quantities the program reasons about.

    The string value is used as the dict key in :class:`UnitSystem`.
    """

    LENGTH = "length"
    """Generic length: m / ft. Used for coordinates, slope dimensions,
    radii, slice widths, etc."""

    SMALL_LENGTH = "small_length"
    """Small length (cm / inches). For settlement, displacement, joint
    aperture, snap distance, etc."""

    VERY_SMALL_LENGTH = "very_small_length"
    """Very small length (mm / inches). For grid pixel size, particle
    size, etc."""

    AREA = "area"
    """Cross-sectional area (m² / ft²)."""

    VERY_SMALL_AREA = "very_small_area"
    """Very small area (mm² / in²) for joint contact, etc."""

    VOLUME = "volume"
    """Volume (m³ / ft³)."""

    ONE_OVER_LENGTH = "one_over_length"
    """Inverse length (1/m / 1/ft)."""

    FORCE = "force"
    """Force (kN / MN / tonnes / kips / lbs / short tons)."""

    WEIGHT = "weight"
    """Synonym of FORCE — same units, used for slice weight reporting."""

    UNIT_WEIGHT = "unit_weight"
    """Unit weight γ (kN/m³ / MN/m³ / tonnes/m³ / kips/ft³ / lbs/ft³ / 
    tons/ft³)."""

    PRESSURE = "pressure"
    """Pressure / stress (kPa / MPa / tonnes/m² / ksf / psf / tons/ft²)."""

    SHEAR_STRENGTH = "shear_strength"
    """Shear strength / cohesion. Same units as PRESSURE."""

    BOND_STRENGTH = "bond_strength"
    """Force per unit length, used for grouted bolts (kN/m / MN/m / 
    tonnes/m / kips/ft / lbs/ft / tons/ft)."""

    JOINT_STIFFNESS = "joint_stiffness"
    """Stress per displacement (kPa/m / MPa/m / tonnes/m²/m / ksf/ft / 
    psf/ft / tons/ft²/ft)."""

    STIFFNESS = "stiffness"
    """Force per displacement (kN/m / MN/m / tonnes/m / kips/ft / lbs/ft / 
    tons/ft)."""

    MOMENT = "moment"
    """Bending moment (kNm / MNm / tonnesm / kipsft / lbsft / tonsft)."""

    HOOP_MOMENT = "hoop_moment"
    """Hoop moment per unit length (kNm/m / MNm/m / tonnesm/m / kipsft/ft / 
    lbsft/ft / tonsft/ft)."""

    FLUX = "flux"
    """Velocity / Darcy flux (m/s / ft/s)."""

    FLOW_RATE = "flow_rate"
    """Volumetric flow (m³/s / ft³/s)."""

    TIME = "time"
    """Time (s in all systems)."""

    ANGLE = "angle"
    """Angle (degrees in all systems for I/O; converted to radians
    internally for trig)."""

    DIMENSIONLESS = "dimensionless"
    """Pure number (factor of safety, ratios, GSI, mb, s, a, etc.)."""
