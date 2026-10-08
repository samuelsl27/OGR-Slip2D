# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.278 (D275) — the water-retention curve of the transient analysis has an
alpha of its own, ``wc_alpha``, read by every permeability model except van
Genuchten.

The defect: ``vg_alpha`` was both the van Genuchten PERMEABILITY parameter
and the retention of every model. Its default since v0.1.200, 3.6 1/m (the
loam of Carsel & Parrish 1988), gave a new material of any model a retention
with a large unsaturated storage: on groundwater verification problem 18
(the dam without drain under a rising reservoir) the head on the toe slope
at 19 656 h is 2.77 m off the published figure with it, and 0.61 m with
0.036, the value the verification bank fixes in its scripts.

What these tests protect:

* **the figure** (the external anchor, rule 1): problem 18 rebuilt here at
  a coarse mesh, against the eleven points of its fig. 18.5 digitized at
  300 dpi (1 px ~ 0.009 m). A NEW material, with no alpha given, is within
  0.8 m everywhere (0.614 measured: the default is the 0.036 the bank
  fixes), and the old default 3.6 is more than 2 m off (2.768 measured).
  The coarse mesh moves both by less than 0.002 m against the bank's 800
  elements and 60 steps (0.613 and 2.769, measured), at a seventh of the
  cost;
* **rule 7**: ``wc_alpha`` moves the transient of a user-curve material and
  not its steady state; it moves nothing at all with van Genuchten, whose
  curve reads ``vg_alpha``; and ``vg_alpha`` moves the steady state of a van
  Genuchten material;
* **a file keeps what it meant**: without ``wc_alpha`` the retention reads
  the ``vg_alpha`` the file carries (0.036 when that is missing too), as
  every version up to 0.1.277 did;
* the interface and the API say which alpha a model reads.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_core.hydraulic import hydraulic_properties as HP  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _app():
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------- problem 18
P_ARR, CORONA, P_ABJ, ALT = 24.0, 4.0, 24.0, 12.0
BASE = P_ARR + CORONA + P_ABJ
#: Fig. 18.1 of the groundwater verification manual: (suction kPa, k m/s).
CURVE_18 = [(0.0, 1.0e-7), (3.0, 1.0e-7), (50.0, 1.0e-9), (200.0, 1.0e-12)]
#: Fig. 18.5, total head along the toe slope at 19 656 h: x [m] -> H [m],
#: the reference curve digitized at 300 dpi (113 px/m on that axis).
FIG_18_5 = {28: 8.34, 30: 8.015, 32: 7.644, 34: 7.233, 36: 6.791, 38: 6.288,
            40: 5.688, 42: 4.970, 44: 4.005, 46: 3.008, 48: 2.014}


def _material_18(**kw):
    """The dam's material as a NEW material: only what the problem gives
    (the curve and mv = 0.003 1/kPa), nothing of the retention."""
    return HydraulicProperties(
        ks=CURVE_18[0][1], model=PermeabilityModel.USER_DEFINED,
        user_curve=list(CURVE_18), specific_storage=9.81 * 0.003, **kw)


def _error_18(hp):
    """max |H - fig. 18.5| [m] on the toe slope at 19 656 h: the 4 m
    reservoir steady state, then 10 m from t = 0 (stages at 0.6 h and
    19 656 h), the toe slope a seepage face. 300 elements and 20 steps."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_fem2d.mesh import generate_mesh_for_project
    from ogr_fem2d.solvers.seepage import (BCType, SeepageBoundaryConditions,
                                           TransientSeepageSolver,
                                           TransientStage)
    p = Project("18")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in
                             [(0.0, 0.0), (BASE, 0.0), (P_ARR + CORONA, ALT),
                              (P_ARR, ALT)]], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="Dam", unit_weight=20.0, sat_unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = hp
    p.materials = [m]
    mesh = generate_mesh_for_project(p, target_elements=300)

    def bcs(reservoir):
        b = SeepageBoundaryConditions()
        for i in mesh.boundary_node_ids():
            x, y = mesh.nodes[i].x, mesh.nodes[i].y
            if x <= P_ARR + 1e-6 and abs(y - ALT * x / P_ARR) < 1e-3 \
                    and y <= reservoir + 1e-6:
                b.add_node(i, BCType.TOTAL_HEAD, reservoir)
            elif x >= P_ARR + CORONA - 1e-6 \
                    and abs(y - ALT * (BASE - x) / P_ABJ) < 1e-3:
                b.add_node(i, BCType.UNKNOWN)
        return b

    s = TransientSeepageSolver(mesh, {m.id: hp}, gamma_w=9.81,
                               relaxation=0.3, max_iterations=600,
                               tolerance=1e-4, time_steps=20, max_picard=100)
    final = bcs(10.0)
    res = s.solve_transient(
        [TransientStage(time=h * 3600.0, label="%g h" % h, bcs=final)
         for h in (0.6, 19656.0)], initial_bcs=bcs(4.0))
    assert res[-1].converged
    return max(abs(mesh.interpolate(res[-1].total_head, x - 1e-3,
                                    ALT * (BASE - x) / P_ABJ - 1e-3) - h)
               for x, h in FIG_18_5.items())


class TestProblem18AgainstItsFigure:
    def test_a_new_material_reproduces_the_figure(self):
        assert _error_18(_material_18()) < 0.8

    def test_the_old_default_alpha_did_not(self):
        assert _error_18(_material_18(wc_alpha=3.6)) > 2.0


# ---------------------------------------------------------------- the alpha
def _theta(alpha, n, psi, ts=0.4, tr=0.05):
    """van Genuchten (1980), m = 1 - 1/n."""
    m = 1.0 - 1.0 / n
    return tr + (ts - tr) * (1.0 + (alpha * psi) ** n) ** (-m)


class TestEachModelReadsItsAlpha:
    def test_a_new_material(self):
        p = HydraulicProperties()
        assert (p.vg_alpha, p.wc_alpha) == (3.6, 0.036)
        assert p.retention_alpha() == 0.036

    def test_every_model_but_van_genuchten_reads_wc_alpha(self):
        for mdl in PermeabilityModel:
            if mdl == PermeabilityModel.VAN_GENUCHTEN:
                continue
            p = HydraulicProperties(model=mdl, vg_alpha=2.0, wc_alpha=0.5)
            for psi in (0.5, 2.0, 10.0):
                assert abs(p.water_content(psi)
                           - _theta(0.5, p.vg_n, psi)) < 1e-12, mdl

    def test_van_genuchten_keeps_one_alpha(self):
        p = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                vg_alpha=2.0, wc_alpha=0.5)
        assert p.retention_alpha() == 2.0
        for psi in (0.5, 2.0, 10.0):
            assert abs(p.water_content(psi) - _theta(2.0, p.vg_n, psi)) \
                < 1e-12

    def test_the_capacity_is_the_derivative_of_that_curve(self):
        p = HydraulicProperties(model=PermeabilityModel.USER_DEFINED,
                                vg_alpha=2.0, wc_alpha=0.5)
        for psi in (0.5, 2.0, 10.0):
            d = 1e-6 * psi
            num = (p.water_content(psi - d) - p.water_content(psi + d)) \
                / (2 * d)
            assert abs(p.specific_moisture_capacity(psi) - num) \
                < 1e-6 * abs(num)

    def test_the_switch_rebuilds_0_1_277(self):
        p = HydraulicProperties(model=PermeabilityModel.USER_DEFINED,
                                vg_alpha=2.0, wc_alpha=0.5)
        old = HP.RETENTION_OWN_ALPHA
        HP.RETENTION_OWN_ALPHA = False
        try:
            assert p.retention_alpha() == 2.0
        finally:
            HP.RETENTION_OWN_ALPHA = old
        assert p.retention_alpha() == 0.5


class TestAFileKeepsWhatItMeant:
    def test_without_either_alpha(self):
        p = HydraulicProperties.from_dict({"model": "user_defined"})
        assert p.wc_alpha == 0.036 == p.vg_alpha

    def test_without_wc_alpha_it_reads_the_files_vg_alpha(self):
        d = {"model": "gardner", "vg_alpha": 2.5, "vg_n": 1.8}
        new = HydraulicProperties.from_dict(d)
        assert new.wc_alpha == 2.5
        old = HP.RETENTION_OWN_ALPHA
        HP.RETENTION_OWN_ALPHA = False
        try:
            before = [new.water_content(psi) for psi in (0.5, 2.0, 10.0)]
        finally:
            HP.RETENTION_OWN_ALPHA = old
        assert [new.water_content(psi) for psi in (0.5, 2.0, 10.0)] == before

    def test_the_round_trip(self):
        p = HydraulicProperties(wc_alpha=0.123)
        assert HydraulicProperties.from_dict(p.to_dict()).wc_alpha == 0.123

    def test_a_non_positive_alpha_is_a_problem(self):
        probs = HydraulicProperties(wc_alpha=0.0).problems()
        assert any("wc_alpha" in t for t in probs), probs


# ---------------------------------------------------------------- rule 7
def _column_heads(hp):
    from test_retention_dialog_v1268 import _heads
    return _heads(hp)


def _moved(a, b):
    ea, la = _column_heads(a)
    eb, lb = _column_heads(b)
    return max(max(abs(x - y) for x, y in zip(ea, eb)),
               max(abs(x - y) for x, y in zip(la, lb)))


def _dam():
    spec = importlib.util.spec_from_file_location(
        "t127_d275", Path(__file__).parent / "test_unsaturated_v127.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    mesh = t._dam_mesh(0.7)
    return t, mesh, t._dam_bcs(mesh)


def _steady(hp):
    from ogr_fem2d.solvers.seepage import UnsaturatedSeepageSolver
    t, mesh, bcs = _dam()
    hp.ks = t.K_DAM
    r = UnsaturatedSeepageSolver(mesh, {"m": hp}, gamma_w=9.81,
                                 relaxation=0.4, max_iterations=300,
                                 tolerance=1e-8).solve_unsaturated(bcs)
    assert r.converged
    return r.total_head


CURVE = [(0.0, 1e-5), (10.0, 1e-6), (100.0, 1e-8)]


def _user(**kw):
    return HydraulicProperties(ks=1e-5, model=PermeabilityModel.USER_DEFINED,
                               user_curve=list(CURVE), vg_n=1.5, wc_sat=0.4,
                               wc_res=0.05, specific_storage=1e-3, **kw)


class TestEachAlphaMovesWhatItReads:
    def test_wc_alpha_moves_the_transient_of_a_user_curve(self):
        assert _moved(_user(wc_alpha=1.0), _user(wc_alpha=2.0)) > 0.01

    def test_wc_alpha_does_not_move_a_steady_state(self):
        a = _steady(_user(wc_alpha=1.0))
        b = _steady(_user(wc_alpha=2.0))
        assert a == b

    def test_wc_alpha_moves_nothing_with_van_genuchten(self):
        def vg(w):
            return HydraulicProperties(
                ks=1e-5, model=PermeabilityModel.VAN_GENUCHTEN, vg_alpha=1.0,
                vg_n=1.5, wc_alpha=w, specific_storage=1e-3)
        assert _moved(vg(0.5), vg(2.0)) == 0.0

    def test_vg_alpha_moves_the_steady_state_of_van_genuchten(self):
        def vg(a):
            return HydraulicProperties(
                model=PermeabilityModel.VAN_GENUCHTEN, vg_alpha=a, vg_n=2.0,
                kr_min=1e-9)
        a, b = _steady(vg(1.0)), _steady(vg(2.0))
        assert max(abs(x - y) for x, y in zip(a, b)) > 1e-3

    def test_vg_alpha_moves_nothing_with_a_user_curve(self):
        assert _moved(_user(vg_alpha=1.0), _user(vg_alpha=2.0)) == 0.0


class TestTheRuleLivesInTheEngine:
    def test_which_field_each_model_reads(self):
        from ogr_core.project.rules import retention_field_is_read
        from test_retention_dialog_v1268 import _project
        steady, transient = _project(transient=False), _project(transient=True)
        vg, ud = PermeabilityModel.VAN_GENUCHTEN, PermeabilityModel.USER_DEFINED
        table = {  # field: (VG steady, VG transient, UD steady, UD transient)
            "wc_alpha": (False, False, False, True),
            "vg_alpha": (True, True, False, False),
            "vg_n": (True, True, False, True),
            "wc_sat": (False, True, False, True),
        }
        for field, want in table.items():
            got = (retention_field_is_read(steady, vg, field),
                   retention_field_is_read(transient, vg, field),
                   retention_field_is_read(steady, ud, field),
                   retention_field_is_read(transient, ud, field))
            assert got == want, field


class TestTheApi:
    def _ws(self):
        import atexit
        from ogr_api import Workspace, call
        ws = Workspace()
        atexit.register(ws.shutdown)
        pid = call(ws, "project_new", name="D275")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [10, 0], [10, 5], [0, 5]],
            "materials": [{"name": "Soil", "unit_weight": 20, "strength": {
                "model": "mohr_coulomb",
                "params": {"cohesion": 5.0, "friction_angle": 30.0}}}]})
        return ws, pid, call

    def test_wc_alpha_is_set_on_a_user_curve(self):
        ws, pid, call = self._ws()
        out = call(ws, "hydraulic_set", project_id=pid, material="Soil",
                   model="user_defined",
                   properties={"user_curve": CURVE, "wc_alpha": 0.2})
        assert out["hydraulic"]["wc_alpha"] == 0.2
        assert "wc_alpha" in out["read_by_this_model"]
        assert "vg_alpha" not in out["read_by_this_model"]

    def test_each_alpha_refused_where_it_moves_nothing(self):
        from ogr_api.errors import Conflict
        ws, pid, call = self._ws()
        for model, key, word in (("van_genuchten", "wc_alpha", "vg_alpha"),
                                 ("gardner", "vg_alpha", "wc_alpha")):
            try:
                call(ws, "hydraulic_set", project_id=pid, material="Soil",
                     model=model, properties={key: 0.5})
            except Conflict as e:
                assert word in str(e), (model, str(e))
            else:
                raise AssertionError((model, key))


@_requires_qt
class TestTheDialog:
    def _dialog(self, transient=True):
        _app()
        from test_retention_dialog_v1268 import _dialog, _project
        p = _project(transient=transient)
        return p, _dialog(p)

    def test_the_groups_alpha_is_wc_alpha(self):
        p, d = self._dialog()
        before = p.materials[0].hydraulic
        d.sp_wc_alpha.setValue(0.25)
        d._accept()
        after = p.materials[0].hydraulic
        assert after.wc_alpha == 0.25 and after.wc_alpha != before.wc_alpha
        assert _moved(before, after) > 0.01

    def test_greyed_out_where_it_moves_nothing(self):
        p, d = self._dialog(transient=False)
        assert d.sp_wc_alpha.isEnabled() is False
        assert d.sp_vg_n.isEnabled() is False
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.VAN_GENUCHTEN))
        assert d.sp_wc_alpha.isEnabled() is False
        assert d.sp_vg_alpha.isEnabled() is True
        assert d.sp_vg_n.isEnabled() is True

    def test_enabled_where_it_is_read(self):
        p, d = self._dialog(transient=True)
        assert d.sp_wc_alpha.isEnabled() is True
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.VAN_GENUCHTEN))
        assert d.sp_wc_alpha.isEnabled() is False

    def test_a_new_material_shows_0_036(self):
        _app()
        from test_retention_dialog_v1268 import _dialog, _project
        p = _project()
        for m in p.materials:
            m.hydraulic = None
        d = _dialog(p)
        assert abs(d.sp_wc_alpha.value() - 0.036) < 1e-12
        assert abs(d.sp_vg_alpha.value() - 3.6) < 1e-12
