# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.268 (D191) — the water content function of the transient analysis is
editable in the hydraulic-properties dialog, with every permeability model,
and every field of it moves a number (rule 7).

The defect: the transient reads a van Genuchten retention curve (theta_s,
theta_r, alpha, n, m) and the specific storage Ss with ANY permeability
model, but the dialog showed alpha and n on the van Genuchten page only and
theta_s, theta_r and Ss on none. A material with a user-defined curve had
five parameters moving its transient that nobody could see or change.

What these tests protect:

* through the DIALOG (the widgets a user touches, then OK), with a
  user-defined permeability curve, changing each of theta_s, theta_r,
  alpha, n, the custom m and Ss moves the heads of a small transient: a
  column with the water table inside and the head at its base raised. The
  movement asked for is 1 cm, against 1.3-24 cm measured;
* theta_s, theta_r and Ss are greyed out when no transient analysis reads
  them (``rules.transient_storage_is_read``) and alpha/n/m are not (they are
  also the van Genuchten permeability, which a steady analysis reads);
  since v0.1.278 (D275) the group's alpha is ``wc_alpha``, and alpha, n and
  m are greyed out where they move nothing for the model shown
  (``rules.retention_field_is_read``, its own test in
  ``test_retention_alpha_v1278.py``);
* Ss keeps ten decimals: 1e-7 survives opening the dialog and pressing OK;
* a User Defined material without a curve says so inside the dialog.

The external anchor for the transient itself is in
``test_transient_celia_v1268.py`` (Celia, Bouloutas & Zarba 1990).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _app():
    return QApplication.instance() or QApplication([])


CURVE_KPA = [(0.0, 1e-5), (10.0, 1e-6), (100.0, 1e-8)]


def _project(transient=True):
    from test_slide_validation_ej1 import _ej1_project
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.project.settings import GroundwaterMethod
    p = _ej1_project()
    p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
    p.settings.groundwater.transient = transient
    for m in p.materials:
        m.hydraulic = HydraulicProperties(
            ks=1e-5, model=PermeabilityModel.USER_DEFINED,
            user_curve=list(CURVE_KPA), wc_alpha=1.0, vg_n=1.5,
            wc_sat=0.4, wc_res=0.05, specific_storage=1e-3)
    return p


def _dialog(p):
    _app()
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog,
    )
    return HydraulicPropertiesDialog(p, None)


def _heads(hp):
    """A 2 m column, water table at 0.5 m, the base raised to 1.5 m at
    t = 0: the heads after 60 s (the saturated zone, Ss) and after 2 h
    (the unsaturated zone, the retention curve)."""
    from ogr_fem2d.mesh.mesh import Element, Mesh, Node
    from ogr_fem2d.solvers.seepage import (BCType, SeepageBoundaryConditions,
                                           TransientSeepageSolver)
    dz, rows = 0.1, 20
    nodes = [Node(2 * j + k, k * dz, j * dz)
             for j in range(rows + 1) for k in (0, 1)]
    elements = []
    for j in range(rows):
        a, b, c, d = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
        elements.append(Element(len(elements), (a, b, c), "m"))
        elements.append(Element(len(elements), (a, c, d), "m"))
    mesh = Mesh(nodes=nodes, elements=elements, target_size=dz)
    bcs = SeepageBoundaryConditions()
    for nid in (0, 1):
        bcs.add_node(nid, BCType.TOTAL_HEAD, 1.5)
    s = TransientSeepageSolver(mesh, {"m": hp}, gamma_w=9.81,
                               relaxation=1.0, tolerance=1e-9,
                               max_picard=200)
    H = [0.5] * mesh.node_count
    early = None
    for k, dt in enumerate([20.0] * 3 + [900.0] * 8):
        H, _act, ok, _it, _r = s.step(bcs, H, dt, set())
        assert ok, k
        if k == 2:
            early = list(H)
    return early, list(H)


def _moved(hp_a, hp_b):
    ea, la = _heads(hp_a)
    eb, lb = _heads(hp_b)
    return max(max(abs(x - y) for x, y in zip(ea, eb)),
               max(abs(x - y) for x, y in zip(la, lb)))


@_requires_qt
class TestEveryFieldMovesTheTransient:
    """Rule 7, through the dialog."""

    def _edit(self, edit):
        p = _project()
        before = p.materials[0].hydraulic
        d = _dialog(p)
        edit(d)
        d._accept()
        after = p.materials[0].hydraulic
        return before, after

    def _check(self, edit, field):
        before, after = self._edit(edit)
        assert getattr(after, field) != getattr(before, field), field
        assert _moved(before, after) > 0.01, field

    def test_saturated_water_content(self):
        self._check(lambda d: d.sp_wc_sat.setValue(0.35), "wc_sat")

    def test_residual_water_content(self):
        self._check(lambda d: d.sp_wc_res.setValue(0.10), "wc_res")

    def test_alpha(self):
        # v0.1.278 (D275): the group's alpha is wc_alpha; the material is a
        # user curve, whose retention does not read vg_alpha
        self._check(lambda d: d.sp_wc_alpha.setValue(2.0), "wc_alpha")

    def test_n(self):
        self._check(lambda d: d.sp_vg_n.setValue(2.0), "vg_n")

    def test_custom_m(self):
        def edit(d):
            d.chk_custom_m.setChecked(True)
            d.sp_vg_m.setValue(0.45)
        self._check(edit, "vg_m")

    def test_specific_storage(self):
        self._check(lambda d: d.sp_ss.setValue(1e-2), "specific_storage")


@_requires_qt
class TestTheGroupFollowsTheRule:
    def test_greyed_out_without_a_transient(self):
        d = _dialog(_project(transient=False))
        for w in (d.sp_wc_sat, d.sp_wc_res, d.sp_ss):
            assert w.isEnabled() is False
        # v0.1.278 (D275): with this user curve and no transient, the
        # curve's alpha and n move nothing either; with van Genuchten its
        # page's alpha and the n are its permeability
        assert d.sp_wc_alpha.isEnabled() is False
        assert d.sp_vg_n.isEnabled() is False
        from ogr_core.hydraulic import PermeabilityModel
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.VAN_GENUCHTEN))
        assert d.sp_vg_alpha.isEnabled() is True
        assert d.sp_vg_n.isEnabled() is True

    def test_enabled_with_a_transient(self):
        d = _dialog(_project(transient=True))
        for w in (d.sp_wc_sat, d.sp_wc_res, d.sp_ss):
            assert w.isEnabled() is True

    def test_the_rule_lives_in_the_engine(self):
        from ogr_core.project.rules import transient_storage_is_read
        assert transient_storage_is_read(_project(transient=True)) is True
        assert transient_storage_is_read(_project(transient=False)) is False

    def test_a_small_storage_survives_ok(self):
        p = _project()
        for m in p.materials:
            m.hydraulic.specific_storage = 1e-7
        d = _dialog(p)
        d._accept()
        assert p.materials[0].hydraulic.specific_storage == 1e-7

    def test_shown_with_every_model(self):
        from ogr_core.hydraulic import PermeabilityModel
        d = _dialog(_project())
        for mdl in PermeabilityModel:
            d.cbo_model.setCurrentIndex(d.cbo_model.findData(mdl))
            assert d.gb_wc.isHidden() is False, mdl

    def test_an_empty_user_curve_is_reported(self):
        p = _project()
        for m in p.materials:
            m.hydraulic.user_curve = []
        d = _dialog(p)
        assert "two" in d.lbl_problems.text() or "dos" in d.lbl_problems.text()
