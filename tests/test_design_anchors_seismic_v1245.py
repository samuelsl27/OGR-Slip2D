# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D226d — the last three pieces of a design standard's actions: the
effective stress a support's bond reads, the unit-weight factor γγ and a
factor on the seismic coefficients.

**The invariants.**

* **Anchors.** γG reaches the effective vertical stress of a support's bond
  only when the option asks for it (off by default, as in the reference: a
  heavier column makes a stronger anchor). On, it multiplies the soil and the
  permanent loads above the bond and the pore pressure that reads that soil
  (Ru); the ponded water and the variable loads never take it.
* **γγ divides.** It is a material factor, and EN 1997-1 (2.4.6.2, eq. 2.2)
  writes a design material property as X_d = X_k/γ_M; until v0.1.244 it
  multiplied (a custom γγ = 1.25 gave 0.888742 on the slope below where
  the weight divided gives 1.388659). A custom file from before reads its
  factor inverted, so its number does not move.
* **The seismic factor** multiplies kh and kv (1 in every preset: Frank et
  al. 2004, §11.5, send the seismic situation to EN 1998-5); a run that
  SEEKS the coefficient (Ky, Newmark) does not apply it and says so.

Against what: closed forms (σ′v = γ·z on the crest of the slope; every bond
sample × γG under a linear pullout law with no adhesion), and identities in
the nine methods (γγ = 1.25 is the model with γ/1.25; the seismic factor
1.2 is the model with kh·1.2). Rule 7 for the three settings, the file
migration, the analysis's refusal of a factored kh that is no coefficient,
the dialog, and the switch (``design_factors.UNIT_WEIGHT_DIVIDES``).

The slope is the φ = 0 one of ``test_tension_crack_truncation_v1109``
(c = 40 kPa, γ = 19, crest at y = 40), its circle (55; 58) R 34, 160 slices,
methods to 1e-12. Comparisons are relative, never ``==`` on doubles of
different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_REL = 5e-9


def _slope():
    import test_tension_crack_truncation_v1109 as U
    return U._phi0_slope(crack_y=None)


def _standard(p, preset=None, **kw):
    ds = p.settings.design_standard
    ds.enabled = True
    if preset is not None:
        ds.apply_preset(preset)
    else:
        ds.standard = "custom"
    for k, v in kw.items():
        setattr(ds, k, v)
    return p


def _work(p):
    from ogr_core.project.design_factors import prepare_analysis_project
    return prepare_analysis_project(p)


def _fos(p, method="bishop_simplified"):
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    work, _rep = _work(p)
    c = SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0)
    sl = slice_surface(work, c, num_slices=160)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel)


def _sigma(p, x=70.0, y=32.0):
    from ogr_core.support.bond import sigma_v_effective_at
    work, _rep = _work(p)
    return sigma_v_effective_at(work, x, y)[0]


# ======================================================================
class TestTheBondOfASupport:
    """σ′v on the crest at (70; 32) is γ·8 = 152 kPa, in closed form."""

    def test_off_by_default_the_bond_reads_the_characteristic_column(self):
        p = _standard(_slope(), "eurocode7_da1c1")
        assert p.settings.design_standard.anchor_permanent_factor is False
        assert _close(_sigma(p), 19.0 * 8.0, 1e-12)

    def test_on_the_soil_takes_gamma_g(self):
        p = _standard(_slope(), "eurocode7_da1c1",
                      anchor_permanent_factor=True)
        assert _close(_sigma(p), 1.35 * 19.0 * 8.0, 1e-12)

    def test_the_permanent_loads_take_it_the_variable_ones_never(self):
        from test_load_actions_v1243 import _crest
        for action, want in (("permanent", 1.35 * (19.0 * 8.0 + 20.0)),
                             ("variable", 1.35 * 19.0 * 8.0 + 20.0)):
            p = _standard(_slope(), "eurocode7_da1c1",
                          anchor_permanent_factor=True)
            p.distributed_loads = [_crest(20.0, action)]
            assert _close(_sigma(p), want, 1e-12), action

    def test_the_pore_pressure_that_reads_the_soil_follows_it(self):
        """With Ru the effective stress is γG·γ·z·(1 − ru): the soil and
        what reads it, one weight."""
        from ogr_core.materials import PorePressureType
        p = _standard(_slope(), "eurocode7_da1c1",
                      anchor_permanent_factor=True)
        p.materials[0].pore_pressure = PorePressureType.RU_COEFFICIENT
        p.materials[0].ru = 0.25
        assert _close(_sigma(p), 1.35 * 19.0 * 8.0 * 0.75, 1e-12)

    def test_every_sample_of_the_bond_takes_gamma_g(self):
        """A linear pullout law with no adhesion is proportional to σ′v:
        each sample of the profile is 1.35 times the one without."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import (Geosynthetic, SupportInstance,
                                      build_bond_profile)
        sheet = SupportInstance(type_id="geosynthetic",
                                head=Vertex(64.0, 32.0),
                                tail=Vertex(76.0, 30.0))
        g = Geosynthetic(pullout_mode="mohr_coulomb", adhesion=0.0,
                         friction_angle_interface=30.0,
                         tensile_capacity=1.0e9, connection_strength=1.0e9)
        off, _ = _work(_standard(_slope(), "eurocode7_da1c1"))
        on, _ = _work(_standard(_slope(), "eurocode7_da1c1",
                                anchor_permanent_factor=True))
        a = build_bond_profile(off, sheet, g).tau
        b = build_bond_profile(on, sheet, g).tau
        assert len(a) == len(b) > 10 and min(a) > 0.0
        for x, y in zip(a, b):
            assert _close(y, 1.35 * x, 1e-12), (x, y)


class TestTheUnitWeightFactorDivides:

    def test_in_the_nine_methods(self):
        for m in _nine():
            q = _slope()
            q.materials[0].unit_weight = 19.0 / 1.25
            a = _fos(_standard(_slope(), factor_unit_weight=1.25), m)
            b = _fos(q, m)
            assert _close(a, b), (m, a, b)

    def test_a_custom_file_from_before_keeps_its_number(self):
        """It multiplied: its 1.25 is read as 0.8, which divides to the
        same weight (measured with v0.1.244: 0.888742)."""
        from ogr_core.project.settings import DesignStandardSettings as D
        p = _slope()
        p.settings.design_standard = D.from_dict(
            {"enabled": True, "standard": "custom",
             "factor_unit_weight": 1.25, "factor_permanent": 1.0,
             "single_source_weight": True})
        assert _close(p.settings.design_standard.factor_unit_weight, 0.8,
                      1e-15)
        assert abs(_fos(p) - 0.888742) < 1e-6

    def test_off_it_multiplies_again(self):
        import ogr_core.project.design_factors as DF
        saved = DF.UNIT_WEIGHT_DIVIDES
        try:
            DF.UNIT_WEIGHT_DIVIDES = False
            off = _fos(_standard(_slope(), factor_unit_weight=1.25))
        finally:
            DF.UNIT_WEIGHT_DIVIDES = saved
        assert abs(off - 0.888742) < 1e-6, off
        assert abs(_fos(_standard(_slope(), factor_unit_weight=1.25))
                   - 1.388659) < 1e-6


class TestTheSeismicFactor:

    def _seismic(self, p, kh):
        p.seismic.enabled = True
        p.seismic.kh = kh
        return p

    def test_it_multiplies_kh_in_the_nine_methods(self):
        for m in _nine():
            a = _fos(_standard(self._seismic(_slope(), 0.1),
                               factor_seismic=1.2), m)
            b = _fos(self._seismic(_slope(), 0.1 * 1.2), m)
            assert _close(a, b), (m, a, b)

    def test_a_run_that_seeks_the_coefficient_says_it_and_leaves_it(self):
        p = _standard(self._seismic(_slope(), 0.1), factor_seismic=1.2)
        p.settings.seismic.compute_ky = True
        work, rep = _work(p)
        assert work.seismic.kh == 0.1
        assert any("not applied" in n for n in rep.notes), rep.notes

    def test_a_factored_coefficient_must_still_be_one(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _standard(self._seismic(_slope(), 0.6), factor_seismic=1.8)
        assert any("seismic factor" in m for m in check_analysis_settings(p))
        p.settings.design_standard.factor_seismic = 1.5
        assert not any("seismic factor" in m
                       for m in check_analysis_settings(p))

    def test_every_preset_carries_one(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        for name in D.PRESETS:
            s = D()
            s.apply_preset(name)
            assert s.factor_seismic == 1.0, name


# ======================================================================
class TestEverySettingMovesTheNumber:
    """Rule 7, and the dialog."""

    def test_the_three_settings(self):
        assert _sigma(_standard(_slope(), "eurocode7_da1c1",
                                anchor_permanent_factor=True)) > _sigma(
            _standard(_slope(), "eurocode7_da1c1")) + 10.0
        assert _fos(_standard(_slope(), factor_unit_weight=1.25)) > \
            _fos(_slope()) + 0.1
        a = _fos(_standard(TestTheSeismicFactor()._seismic(_slope(), 0.1),
                           factor_seismic=1.2))
        b = _fos(TestTheSeismicFactor()._seismic(_slope(), 0.1))
        assert a < b - 0.01

    def test_the_dialog(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            _DesignStandardPage)
        QApplication.instance() or QApplication([])
        s = ProjectSettings()
        s.design_standard.enabled = True
        s.design_standard.standard = "custom"
        page = _DesignStandardPage(s)
        assert not page.chk_anchor.isChecked() and page.chk_anchor.isEnabled()
        page.chk_anchor.setChecked(True)
        page.factors["factor_seismic"].setValue(1.2)
        page.apply()
        assert s.design_standard.anchor_permanent_factor is True
        assert s.design_standard.factor_seismic == 1.2
