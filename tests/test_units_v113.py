# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.13 unit system module.

Verifies:
    - All 6 systems registered correctly
    - SI ↔ user-system roundtrip preserves values
    - Specific conversions match published factors
    - Pattern A: core values stay in SI when system_id changes
"""
from __future__ import annotations

import math


# ======================================================================
class TestUnitSystemBasics:
    def test_six_systems_registered(self):
        from ogr_core.units import SYSTEMS
        for sid in (
            "metric_kpa", "metric_mpa", "metric_tonnes",
            "imperial_tons", "imperial_ksf", "imperial_psf",
        ):
            assert sid in SYSTEMS, f"Missing system: {sid}"

    def test_default_is_metric_kpa(self):
        from ogr_core.units import DEFAULT_SYSTEM_ID
        assert DEFAULT_SYSTEM_ID == "metric_kpa"

    def test_metric_kpa_is_identity(self):
        """The internal SI system uses factor=1 for the CORE SI quantities
        (length in m, force in kN, pressure in kPa, unit weight in kN/m³).
        Sub-units like cm/mm have factor != 1 even in metric_kpa, so we
        only check the canonical SI list here."""
        from ogr_core.units import METRIC_KPA, Quantity
        SI_QS = [
            Quantity.LENGTH, Quantity.FORCE, Quantity.WEIGHT,
            Quantity.UNIT_WEIGHT, Quantity.PRESSURE,
            Quantity.SHEAR_STRENGTH, Quantity.BOND_STRENGTH,
            Quantity.STIFFNESS, Quantity.JOINT_STIFFNESS,
            Quantity.MOMENT, Quantity.HOOP_MOMENT,
            Quantity.AREA, Quantity.VOLUME, Quantity.ONE_OVER_LENGTH,
            Quantity.FLUX, Quantity.FLOW_RATE, Quantity.TIME,
            Quantity.ANGLE, Quantity.DIMENSIONLESS,
        ]
        for q in SI_QS:
            v = METRIC_KPA.factors.get(q.value, 1.0)
            assert v == 1.0, f"{q.value} factor != 1 in metric_kpa: {v}"


# ======================================================================
class TestKnownConversions:
    """Compare against well-known engineering conversion factors."""

    def test_kPa_to_psf(self):
        from ogr_core.units import IMPERIAL_PSF, Quantity
        # 1 kPa = 20.885 psf (NIST)
        assert abs(IMPERIAL_PSF.to_user(1.0, Quantity.PRESSURE) - 20.8854) < 0.01

    def test_kPa_to_ksf(self):
        from ogr_core.units import IMPERIAL_KSF, Quantity
        # 1 kPa = 0.020885 ksf
        assert abs(IMPERIAL_KSF.to_user(1.0, Quantity.PRESSURE) - 0.02089) < 0.0001

    def test_kPa_to_MPa(self):
        from ogr_core.units import METRIC_MPA, Quantity
        assert abs(METRIC_MPA.to_user(1000.0, Quantity.PRESSURE) - 1.0) < 1e-9

    def test_kPa_to_tonnes_per_m2(self):
        from ogr_core.units import METRIC_TONNES, Quantity
        # 1 kPa = 1/9.81 tonnes/m² ≈ 0.10197
        v = METRIC_TONNES.to_user(1.0, Quantity.PRESSURE)
        assert abs(v - 0.10197) < 0.001

    def test_kN_to_lbs(self):
        from ogr_core.units import IMPERIAL_PSF, Quantity
        # 1 kN ≈ 224.81 lbf
        assert abs(IMPERIAL_PSF.to_user(1.0, Quantity.FORCE) - 224.809) < 0.05

    def test_kN_to_kips(self):
        from ogr_core.units import IMPERIAL_KSF, Quantity
        # 1 kN ≈ 0.22481 kips
        assert abs(IMPERIAL_KSF.to_user(1.0, Quantity.FORCE) - 0.22481) < 0.001

    def test_m_to_ft(self):
        from ogr_core.units import IMPERIAL_PSF, Quantity
        # 1 m = 3.2808 ft
        assert abs(IMPERIAL_PSF.to_user(1.0, Quantity.LENGTH) - 3.28084) < 0.001


# ======================================================================
class TestRoundtrip:
    """SI → user → SI must preserve the value."""

    def test_pressure_roundtrip_all_systems(self):
        from ogr_core.units import SYSTEMS, Quantity
        for sid, sys_obj in SYSTEMS.items():
            for v_si in [1e-3, 1.0, 50.0, 1000.0, 1e5]:
                user = sys_obj.to_user(v_si, Quantity.PRESSURE)
                back = sys_obj.from_user(user, Quantity.PRESSURE)
                assert abs(back - v_si) < 1e-6 * max(abs(v_si), 1.0), (
                    f"Roundtrip failed for {sid} pressure {v_si}: "
                    f"got back {back}"
                )

    def test_unit_weight_roundtrip_imperial_psf(self):
        from ogr_core.units import IMPERIAL_PSF, Quantity
        gamma_si = 18.5  # kN/m³ (typical soil)
        user = IMPERIAL_PSF.to_user(gamma_si, Quantity.UNIT_WEIGHT)
        # Should be roughly 18.5 × 6.366 = ~117.8 lbs/ft³ (typical soil γ)
        assert 110 < user < 130
        back = IMPERIAL_PSF.from_user(user, Quantity.UNIT_WEIGHT)
        assert abs(back - gamma_si) < 1e-6

    def test_force_roundtrip_all_systems(self):
        from ogr_core.units import SYSTEMS, Quantity
        for sid, sys_obj in SYSTEMS.items():
            for v_si in [1.0, 100.0, 5000.0]:
                user = sys_obj.to_user(v_si, Quantity.FORCE)
                back = sys_obj.from_user(user, Quantity.FORCE)
                assert abs(back - v_si) < 1e-6 * max(abs(v_si), 1.0)


# ======================================================================
class TestLabels:
    def test_kPa_label(self):
        from ogr_core.units import METRIC_KPA, Quantity
        assert METRIC_KPA.label_for(Quantity.PRESSURE) == "kPa"
        assert METRIC_KPA.label_for(Quantity.UNIT_WEIGHT) == "kN/m³"

    def test_imperial_psf_labels(self):
        from ogr_core.units import IMPERIAL_PSF, Quantity
        assert IMPERIAL_PSF.label_for(Quantity.PRESSURE) == "psf"
        assert IMPERIAL_PSF.label_for(Quantity.UNIT_WEIGHT) == "lbs/ft³"
        assert IMPERIAL_PSF.label_for(Quantity.FORCE) == "lbs"
        assert IMPERIAL_PSF.label_for(Quantity.LENGTH) == "ft"

    def test_dimensionless_has_empty_label(self):
        from ogr_core.units import METRIC_KPA, Quantity
        assert METRIC_KPA.label_for(Quantity.DIMENSIONLESS) == ""


# ======================================================================
class TestProjectIntegration:
    """v0.1.13 — Project.units now has a system_id field."""

    def test_default_units_uses_metric_kpa(self):
        from ogr_core.project.units import Units
        u = Units()
        assert u.system_id == "metric_kpa"

    def test_units_get_system_returns_correct_obj(self):
        from ogr_core.project.units import Units
        u = Units()
        u.system_id = "imperial_psf"
        sys_obj = u.get_system()
        assert sys_obj.id == "imperial_psf"

    def test_legacy_units_back_compat(self):
        """Old project files without system_id should still load."""
        from ogr_core.project.units import Units
        u = Units.from_dict({"system": "metric", "time": "d",
                             "permeability": "m/s", "failure_direction": "R2L"})
        # No system_id in input → should default to metric_kpa
        assert u.system_id == "metric_kpa"

    def test_legacy_imperial_maps_to_psf(self):
        from ogr_core.project.units import Units
        u = Units.from_dict({"system": "imperial", "time": "d",
                             "permeability": "m/s", "failure_direction": "R2L"})
        assert u.system_id == "imperial_psf"


# ======================================================================
class TestPatternA:
    """Verify the 'stored as SI' invariant: changing system_id does NOT
    mutate any stored value; only how it's displayed."""

    def test_changing_system_id_preserves_si_storage(self):
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project

        p = Project("test")
        # Cohesion stored as 10 kPa internally
        p.add_material(Material(
            name="Soil", unit_weight=18,
            strength=MohrCoulomb(cohesion=10, friction_angle=20),
        ))

        # Switch to imperial_psf — values in memory MUST NOT change
        p.settings.units.system_id = "imperial_psf"
        assert p.materials[0].unit_weight == 18
        assert p.materials[0].strength.params["cohesion"] == 10
        assert p.materials[0].strength.params["friction_angle"] == 20

        # When the GUI displays this material, it would convert
        # 10 kPa → 208.85 psf for showing, but the storage is unchanged.

        # Switch back to metric_kpa — same values
        p.settings.units.system_id = "metric_kpa"
        assert p.materials[0].strength.params["cohesion"] == 10
