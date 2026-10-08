# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.275 (D271) — the hydraulic properties dialog edits the user curve and
kr_min, and with the User Defined model Ks IS the first point of the curve.

The defects
-----------
* The User Defined page was one sentence: no table. A curve could only be
  set by a script or the API, so choosing User Defined in the interface gave
  a material without a curve — kr = 1 everywhere, a saturated solve.
* ``kr_min``, the floor of the relative permeability, moves the flow of
  every model with a dry zone and could not be seen or changed here.
* The page said "Ks is taken from the first point of the user curve" and
  disabled the Ks box, but the conductivity came from the ``ks`` field and
  the curve only normalised kr: k = ks * k(psi) / k_first. A curve whose
  first point was not ``ks`` was not the curve typed; the Plot scaled it by
  the disabled box.
* The Ks box had twelve decimals: opening the dialog and pressing OK
  rounded a Ks below 1e-10 and turned 1e-13 into 1e-14.

The invariants (rule 7 and round trips, no snapshot)
-----------------------------------------------------
* entering three points and a kr_min and pressing OK stores them, sorted
  by suction, with Ks equal to the first point;
* each of them MOVES a steady unsaturated solve (the rectangular Gardner
  dam of ``test_unsaturated_v127``): a point of the curve by 0.12 m, kr_min
  by 0.31 m, measured;
* Ks of a User Defined material is its first point, whatever the ``ks``
  field says (``USER_KS_FROM_CURVE``; off, the field again);
* opening the dialog and pressing OK changes nothing: the curve (even an
  unsorted one), a kr_min of 1e-12, a Ks of 1e-13 come back to the bit;
* the Plot is not modal and draws the points of the curve;
* every message ``problems()`` and ``notices()`` can produce has its Spanish;
* the API refuses a Ks that contradicts the first point, and keeps one that
  agrees in step with it.

Module switches and the language are restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402

try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
import ogr_core.hydraulic.hydraulic_properties as hpm  # noqa: E402

UD = PermeabilityModel.USER_DEFINED
CURVE = [(0.0, 1e-5), (10.0, 1e-7), (50.0, 1e-13)]       # kPa, m/s


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_CACHE: dict = {}


def _dam():
    if "dam" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t127_d271", Path(__file__).parent / "test_unsaturated_v127.py")
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        mesh = t._dam_mesh(1.0)
        _CACHE["dam"] = (mesh, t._dam_bcs(mesh))
    return _CACHE["dam"]


def _heads(hp):
    from ogr_fem2d.solvers import UnsaturatedSeepageSolver
    mesh, bcs = _dam()
    r = UnsaturatedSeepageSolver(mesh, {"m": hp}, relaxation=0.4,
                                 max_iterations=400,
                                 tolerance=1e-6).solve_unsaturated(bcs)
    assert r.converged, r.notes
    return r.total_head


def _moved(a, b):
    return max(abs(x - y) for x, y in zip(_heads(a), _heads(b)))


def _project(hydraulic):
    from test_slide_validation_ej1 import _ej1_project
    p = _ej1_project()
    for m in p.materials:
        m.hydraulic = HydraulicProperties.from_dict(hydraulic.to_dict())
    return p


def _dialog(p):
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    from ogr_gui.i18n import set_language
    QApplication.instance() or QApplication([])
    set_language("en")
    return HydraulicPropertiesDialog(p, None)


@_requires_qt
class TestTheDialogEditsTheCurveAndTheFloor:
    def _entered(self):
        """A material switched to User Defined with no curve; three points
        and a kr_min entered from the dialog; OK."""
        p = _project(HydraulicProperties(ks=3e-5))
        d = _dialog(p)
        d.cbo_model.setCurrentIndex(d.cbo_model.findData(UD))
        assert "two" in d.lbl_problems.text()      # no curve yet: said
        # typed out of order: stored sorted by suction
        d.import_curve_text("suction,k\n10,1e-7\n0,1e-5\n50,1e-13\n")
        d.sp_kr_min.setValue(1e-9)
        d._accept()
        return p.materials[0].hydraulic, d

    def test_the_points_and_the_floor_are_stored(self):
        h, _d = self._entered()
        assert h.model == UD
        assert h.user_curve == CURVE
        assert h.kr_min == 1e-9
        assert h.ks == 1e-5 and h.saturated_k() == 1e-5

    def test_the_ks_box_shows_the_first_point_and_is_read_only(self):
        _h, d = self._entered()
        assert not d.sp_ks.isEnabled()
        assert d.sp_ks.value() == 1e-5

    def test_a_point_of_the_curve_moves_the_steady_solve(self):
        h, _d = self._entered()
        p = _project(h)
        d = _dialog(p)
        d.tbl_curve.item(1, 1).setText("1e-8")       # the 10 kPa point
        d._accept()
        h2 = p.materials[0].hydraulic
        assert h2.user_curve[1] == (10.0, 1e-8)
        base = HydraulicProperties.from_dict(h.to_dict())
        base.kr_min = 1e-6
        moved = HydraulicProperties.from_dict(h2.to_dict())
        moved.kr_min = 1e-6
        assert _moved(base, moved) > 0.05            # measured 0.12 m

    def test_kr_min_moves_the_steady_solve(self):
        h, _d = self._entered()
        floor_default = HydraulicProperties.from_dict(h.to_dict())
        floor_default.kr_min = 1e-6
        assert _moved(floor_default, h) > 0.1        # measured 0.31 m

    def test_the_floor_that_clamps_points_is_said(self):
        p = _project(HydraulicProperties(ks=1e-5, model=UD,
                                         user_curve=list(CURVE)))
        d = _dialog(p)
        assert "below kr_min" in d.lbl_problems.text()
        d.sp_kr_min.setValue(1e-9)
        assert "below kr_min" not in d.lbl_problems.text()

    def test_a_row_that_is_not_two_numbers_is_said(self):
        p = _project(HydraulicProperties(ks=1e-5, model=UD,
                                         user_curve=list(CURVE)))
        d = _dialog(p)
        d.tbl_curve.item(2, 0).setText("fifty")
        assert "not two numbers: 3" in d.lbl_problems.text()

    def test_a_file_without_pairs_leaves_the_curve(self):
        p = _project(HydraulicProperties(ks=1e-5, model=UD,
                                         user_curve=list(CURVE)))
        d = _dialog(p)
        assert d.import_curve_text("no numbers here\n") == 0
        d._accept()
        assert p.materials[0].hydraulic.user_curve == CURVE


@_requires_qt
class TestOpeningAndPressingOkChangesNothing:
    def test_a_user_curve_and_a_tiny_floor(self):
        curve = [(0.0, 1.234567e-9), (10.0, 3.3e-12), (100.0, 1e-13)]
        h = HydraulicProperties(ks=1.234567e-9, model=UD, user_curve=curve,
                                kr_min=1e-12)
        p = _project(h)
        _dialog(p)._accept()
        after = p.materials[0].hydraulic
        assert after.user_curve == curve
        assert after.kr_min == 1e-12
        assert after.ks == 1.234567e-9

    def test_an_unsorted_curve_is_left_as_it_was(self):
        curve = [(10.0, 1e-7), (0.0, 1e-5), (50.0, 1e-13)]
        p = _project(HydraulicProperties(ks=1e-5, model=UD,
                                         user_curve=list(curve)))
        _dialog(p)._accept()
        assert p.materials[0].hydraulic.user_curve == curve

    def test_a_tiny_saturated_permeability(self):
        # the Ks box had twelve decimals: 1e-13 came back as 1e-14
        p = _project(HydraulicProperties(ks=1e-13))
        _dialog(p)._accept()
        assert p.materials[0].hydraulic.ks == 1e-13


@_requires_qt
class TestThePlot:
    def test_is_not_modal_and_draws_the_points(self):
        p = _project(HydraulicProperties(ks=1e-5, model=UD,
                                         user_curve=list(CURVE)))
        d = _dialog(p)
        dlg = d._plot()
        assert dlg is not None and not dlg.isModal() and dlg.isVisible()
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        canvas = dlg.findChild(FigureCanvasQTAgg)
        lines = canvas.figure.axes[0].get_lines()
        assert len(lines) == 2                       # the function, the points
        assert list(lines[1].get_ydata()) == [k for _s, k in CURVE]
        dlg.close()


class TestKsIsTheFirstPoint:
    def test_the_conductivity_reads_the_first_point(self):
        h = HydraulicProperties(ks=2e-5, model=UD, user_curve=list(CURVE))
        assert h.saturated_k() == 1e-5
        assert h.principal()[0] == 1e-5
        assert h.conductivity_tensor()[0] == 1e-5
        assert h.k_at_suction(0.0) == 1e-5

    def test_other_models_keep_their_ks(self):
        h = HydraulicProperties(ks=2e-5, model=PermeabilityModel.GARDNER,
                                user_curve=list(CURVE))
        assert h.saturated_k() == 2e-5

    def test_switched_off_the_field_is_read_again(self):
        h = HydraulicProperties(ks=2e-5, model=UD, user_curve=list(CURVE))
        old = hpm.USER_KS_FROM_CURVE
        try:
            hpm.USER_KS_FROM_CURVE = False
            assert h.principal()[0] == 2e-5
        finally:
            hpm.USER_KS_FROM_CURVE = old


class TestEveryMessageIsTranslated:
    CASES = [dict(ks=0.0), dict(k2_k1=-1.0), dict(kr_min=0.0),
             dict(bc_lambda=0.0), dict(bc_psi_b=-1.0), dict(fx_a=0.0),
             dict(gardner_a=-1.0), dict(gardner_n=0.0), dict(vg_alpha=0.0),
             dict(vg_n=1.0), dict(vg_m=0.0), dict(wc_res=0.5, wc_sat=0.4),
             dict(specific_storage=-1.0), dict(model=UD, user_curve=[]),
             dict(model=UD, user_curve=[(-1.0, 1e-5), (1.0, 1e-6)]),
             dict(model=UD, user_curve=[(0.0, 1e-5), (0.0, 1e-6)]),
             dict(model=UD, user_curve=[(0.0, 0.0), (1.0, 1e-6)])]

    def test_problems_and_notices(self):
        from ogr_gui.i18n import _DICTS
        msgs = []
        for kw in self.CASES:
            msgs += HydraulicProperties(**kw).problems()
        msgs += HydraulicProperties(model=UD,
                                    user_curve=list(CURVE)).notices()
        assert len(set(msgs)) >= 17
        missing = [m for m in set(msgs) if m not in _DICTS["es"]]
        assert not missing, missing


class TestTheApi:
    def _pid(self):
        import atexit
        from ogr_api import Workspace, call
        ws = Workspace()
        atexit.register(ws.shutdown)
        pid = call(ws, "project_new", name="Box")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
            "materials": [{"name": "Soil", "unit_weight": 20,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 5.0,
                                                   "friction_angle": 30.0}}}]})
        return ws, pid

    def test_a_contradicting_ks_is_refused(self):
        from ogr_api import Conflict, call
        ws, pid = self._pid()
        with pytest.raises(Conflict):
            call(ws, "hydraulic_set", project_id=pid, material="Soil",
                 model="user_defined",
                 properties={"ks": 3e-5,
                             "user_curve": [[0, 1e-5], [10, 1e-7]]})

    def test_no_ks_is_kept_in_step_and_the_floor_is_noticed(self):
        from ogr_api import call
        ws, pid = self._pid()
        out = call(ws, "hydraulic_set", project_id=pid, material="Soil",
                   model="user_defined",
                   properties={"user_curve": [[0, 1e-5], [10, 1e-7],
                                              [50, 1e-13]]})
        hyd = ws.get(pid).project.materials[0].hydraulic
        assert hyd.ks == 1e-5
        assert any("below kr_min" in n for n in out["notes"]), out["notes"]
