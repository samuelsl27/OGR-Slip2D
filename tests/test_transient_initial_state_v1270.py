# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.270 (D268) — a transient says whether the steady field it started
from converged.

The defect
----------
With no ``initial_head``, ``TransientSeepageSolver.solve_transient`` takes
its initial state from a steady run and only checked that the run produced
heads, not that it converged. A steady state that did not converge (or
whose seepage face never settled) was evolved in silence: every stage came
out "converged" with no note and no warning.

The decision and the invariants
-------------------------------
The owner chose to ANNOTATE, not to lower ``converged``: the stages
converged from where they started, and lowering the flag would also take
their free surface, their flux and the API's point queries away
(``SeepageResult.ok``). So:

* **every stage carries** ``initial_state_converged`` and, when it is
  False, ``initial_state_warning`` with the steady run's own reason;
* **the one exception is a zero-span stage before the first time step**:
  it IS the steady field, unevolved, so it reports that field's
  ``converged`` and notes — reporting True there was false;
* **annotating moves nothing**: a transient started from the steady run
  gives, to the bit, the heads of the same transient given that run's
  heads as ``initial_head`` (the identity this file checks);
* **a given initial_head is the user's** and is not judged: no note;
* **the warning reaches the caller**: ``run_transient_stability``'s
  warnings, the API's stage rows and the status bar of the main window
  (which replaces the driver's warnings with its own summary, so it has to
  carry it there).

The non-converged case is the reproduction of the defect's prompt: the
rectangular Gardner dam of ``test_unsaturated_v127`` with two Picard
passes and the rescue switched off (restored in ``finally``, rule 5).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    TransientSeepageSolver,
    TransientStage,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _dam():
    spec = importlib.util.spec_from_file_location(
        "t127_d268", Path(__file__).parent / "test_unsaturated_v127.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    mesh = t._dam_mesh(0.7)
    props = {"m": HydraulicProperties(
        ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
        gardner_n=3.0,
        # the retention these numbers were measured with (the
        # default alpha up to 0.1.277; v0.1.278, D275)
        wc_alpha=3.6)}
    return mesh, props, t._dam_bcs(mesh)


_CACHE: dict = {}


def _stages(bcs):
    return [TransientStage(time=0.0, bcs=bcs, label="t = 0"),
            TransientStage(time=3600.0, bcs=bcs, label="1 h")]


def _starved():
    """Two Picard passes for the initial steady state, rescue off."""
    if "starved" not in _CACHE:
        mesh, props, bcs = _dam()
        old = seepage.PICARD_RESCUE
        try:
            seepage.PICARD_RESCUE = False
            s = TransientSeepageSolver(mesh, props, relaxation=0.4,
                                       max_iterations=2, tolerance=1e-5,
                                       time_steps=4, max_picard=50)
            steady = seepage.UnsaturatedSeepageSolver.solve_unsaturated(
                s, bcs)
            _CACHE["starved"] = (steady, s.solve_transient(
                _stages(bcs), initial_bcs=bcs))
        finally:
            seepage.PICARD_RESCUE = old
        _CACHE["dam"] = (mesh, props, bcs)
    return _CACHE["starved"]


def _settled():
    """The same transient with a budget the steady state converges in,
    and again with that steady state's heads given as initial_head."""
    if "settled" not in _CACHE:
        _starved()
        mesh, props, bcs = _CACHE["dam"]

        def solver():
            return TransientSeepageSolver(mesh, props, relaxation=0.4,
                                          max_iterations=250,
                                          tolerance=1e-5, time_steps=4,
                                          max_picard=50)
        steady = seepage.UnsaturatedSeepageSolver.solve_unsaturated(
            solver(), bcs)
        from_steady = solver().solve_transient(_stages(bcs),
                                               initial_bcs=bcs)
        given = solver().solve_transient(
            _stages(bcs), initial_head=list(steady.total_head))
        _CACHE["settled"] = (steady, from_steady, given)
    return _CACHE["settled"]


class TestAnUnconvergedStart:
    def test_the_case_is_the_defect(self):
        steady, _stages_ = _starved()
        assert not steady.converged and steady.total_head

    def test_every_stage_says_so(self):
        _steady, res = _starved()
        assert len(res) == 2
        for r in res:
            assert r.notes["initial_state_converged"] is False, r.notes
            assert "did not converge" in r.notes["initial_state_warning"]

    def test_the_stage_that_advanced_keeps_its_own_flag(self):
        _steady, res = _starved()
        later = res[1]
        assert later.notes["time_steps"] == 4
        assert later.converged is True     # the owner's decision: not lowered
        assert later.ok

    def test_the_initial_instant_is_the_steady_field(self):
        steady, res = _starved()
        first = res[0]
        assert first.notes["time_steps"] == 0
        assert first.converged is False
        assert first.total_head == steady.total_head
        # and it carries that field's own diagnostics
        assert first.notes["unsettled_nodes"] == \
            steady.notes["unsettled_nodes"]
        assert first.notes["history"] == steady.notes["history"]


class TestAConvergedStart:
    def test_every_stage_says_so(self):
        steady, res, _given = _settled()
        assert steady.converged
        for r in res:
            assert r.notes["initial_state_converged"] is True
            assert "initial_state_warning" not in r.notes
        assert res[0].converged is True

    def test_annotating_moves_nothing(self):
        """The heads of a transient started from the steady run equal,
        to the bit, those of the same transient given that run's heads."""
        _steady, res, given = _settled()
        for a, b in zip(res, given):
            assert a.total_head == b.total_head
            assert a.converged == b.converged
            assert a.iterations == b.iterations

    def test_a_given_initial_head_is_not_judged(self):
        _steady, _res, given = _settled()
        for r in given:
            assert "initial_state_converged" not in r.notes
            assert "initial_state_warning" not in r.notes


class TestTheWarningReachesTheCaller:
    def _project(self, results):
        from ogr_core.project import Project
        _starved()
        mesh, _props, bcs = _CACHE["dam"]
        p = Project()
        # v0.1.280 (D284): the mesh's elements are of material "m", and a
        # project without that material is now refused by the doors as a
        # mesh of another model; the project has to own it
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        mat = Material(name="m", strength=MohrCoulomb(cohesion=10.0,
                                                      friction_angle=30.0))
        mat.id = "m"
        p.materials = [mat]
        p.fem_mesh = mesh
        p.seepage_bcs = bcs
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_stages = [{"time": 0.0, "label": "t = 0"},
                               {"time": 3600.0, "label": "1 h"}]

        def fake(project, *a, **k):
            project.transient_results = list(results)
            project.seepage_result = results[-1]
            return list(results)
        return p, fake

    def _with_fake(self, fake, body):
        import ogr_slip2d.transient_stability as ts
        real = ts.solve_project_groundwater
        ts.solve_project_groundwater = fake
        try:
            return body()
        finally:
            ts.solve_project_groundwater = real

    def test_run_transient_stability(self):
        from ogr_slip2d.transient_stability import (
            INITIAL_STATE_NOT_CONVERGED, run_transient_stability)
        _steady, res = _starved()
        p, fake = self._project(res)
        out = self._with_fake(fake, lambda: run_transient_stability(p))
        assert INITIAL_STATE_NOT_CONVERGED in out.warnings, out.warnings

    def test_not_when_it_converged(self):
        from ogr_slip2d.transient_stability import (
            INITIAL_STATE_NOT_CONVERGED, run_transient_stability)
        _steady, res, _given = _settled()
        p, fake = self._project(res)
        out = self._with_fake(fake, lambda: run_transient_stability(p))
        assert INITIAL_STATE_NOT_CONVERGED not in out.warnings

    def test_the_api_stage_rows(self):
        from ogr_api.results import seepage_field_summary, stage_rows
        _steady, res = _starved()
        rows = stage_rows(res)
        assert [r["initial_state_converged"] for r in rows] == [False, False]
        assert all("did not converge" in r["initial_state_warning"]
                   for r in rows)
        assert "warning" in rows[0]
        notes = seepage_field_summary(res[-1])["notes"]
        assert notes["initial_state_converged"] is False

    def test_it_is_translated(self):
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.transient_stability import (
            INITIAL_STATE_NOT_CONVERGED)
        assert INITIAL_STATE_NOT_CONVERGED in _DICTS["es"]


@_requires_qt
class TestTheStatusBar:
    def test_the_transient_summary_carries_it(self):
        """The main window replaces the driver's warnings with its own
        summary of the stages; the summary has to carry this one."""
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        _steady, res = _starved()
        helper = TestTheWarningReachesTheCaller()
        p, fake = helper._project(res)
        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        helper._with_fake(fake, w._compute_groundwater)
        msg = w.statusBar().currentMessage()
        assert "initial steady state" in msg, msg
