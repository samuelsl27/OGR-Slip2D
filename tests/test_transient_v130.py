# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.30 — Transient seepage tests (Phase 6).

Validation strategy — everything has an exact or independently-computable
target:

* **Analytical diffusion (erfc)** — a confined, fully saturated aquifer
  obeys dH/dt = D d2H/dx2 with D = K/Ss, whose step response is
  H = H0 + (H1-H0) erfc[x / (2 sqrt(D t))]. Compared only where the
  semi-infinite assumption holds (the diffusion length must stay well
  inside the domain), because the analytical solution — not the solver —
  stops applying otherwise.
* **Asymptotic consistency** — the transient solution at large time must
  reproduce the steady-state solution of the same boundary conditions.
  This is the strongest single check: it couples the transient machinery
  to the already-validated Phase-3 solver.
* **Storage physics** — draining lowers the stored water monotonically;
  the elastic storage must NOT vanish in the saturated zone (the bug that
  the generalised storage content fixes); a larger storage coefficient
  must slow the response down.
* **Retention curve** — analytic van Genuchten limits and the derivative
  checked against finite differences.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.regions import MaterialRegion  # noqa: E402
from ogr_core.hydraulic import (  # noqa: E402
    HydraulicProperties,
    PermeabilityModel,
)
from ogr_fem2d.mesh import generate_mesh  # noqa: E402
from ogr_fem2d.solvers import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    TransientSeepageSolver,
    TransientStage,
    UnsaturatedSeepageSolver,
)


def _rect_mesh(w, h, size):
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(w, 0),
                              Vertex(w, h), Vertex(0, h)], closed=True)
    return generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=size)


# ======================================================================
class TestRetentionCurve:
    def test_saturated_and_dry_limits(self):
        p = HydraulicProperties(wc_sat=0.45, wc_res=0.08,
                                vg_alpha=0.05, vg_n=2.0)
        assert abs(p.water_content(0.0) - 0.45) < 1e-12
        assert abs(p.water_content(-5.0) - 0.45) < 1e-12
        assert p.water_content(1e6) < 0.09

    def test_monotone_decreasing(self):
        p = HydraulicProperties(vg_alpha=0.05, vg_n=2.0)
        prev = p.water_content(0.0)
        for psi in (1, 5, 10, 50, 200, 1000):
            th = p.water_content(psi)
            assert th <= prev + 1e-12
            prev = th

    def test_capacity_matches_finite_difference(self):
        """C = d(theta)/d(pressure head) must match a numerical
        derivative of the retention curve."""
        p = HydraulicProperties(wc_sat=0.45, wc_res=0.08,
                                vg_alpha=0.05, vg_n=2.0)
        for psi in (2.0, 10.0, 40.0, 150.0):
            d = 1e-4 * psi
            num = (p.water_content(psi - d)
                   - p.water_content(psi + d)) / (2 * d)
            ana = p.specific_moisture_capacity(psi)
            assert abs(num - ana) / max(abs(ana), 1e-12) < 1e-3, psi

    def test_capacity_zero_when_saturated(self):
        p = HydraulicProperties()
        assert p.specific_moisture_capacity(0.0) == 0.0

    def test_storage_uses_ss_when_saturated(self):
        p = HydraulicProperties(specific_storage=3e-4)
        assert abs(p.storage_at(5.0) - 3e-4) < 1e-15
        # Capillary storage is substantially larger than elastic storage.
        # The exact ratio depends on the retention parameters (with the
        # default loam-like curve it is about 10x, with a sand it is far
        # more), so the assertion stays deliberately modest.
        assert p.storage_at(-10.0) > 5 * 3e-4

    def test_storage_content_is_the_integral_of_storage(self):
        """W(P) must have storage_at as its derivative in BOTH zones —
        this consistency is what keeps the modified Picard scheme valid
        across the water table."""
        p = HydraulicProperties(wc_sat=0.45, wc_res=0.08,
                                vg_alpha=0.05, vg_n=2.0,
                                specific_storage=1e-3)
        for ph in (-40.0, -10.0, -2.0, 3.0, 20.0):
            d = 1e-4
            num = (p.storage_content(ph + d)
                   - p.storage_content(ph - d)) / (2 * d)
            assert abs(num - p.storage_at(ph)) / max(
                p.storage_at(ph), 1e-12) < 1e-2, ph

    def test_storage_content_grows_with_pressure_when_saturated(self):
        """The elastic branch: W = theta_s + Ss*P. If this were flat the
        transient problem would collapse onto the steady state."""
        p = HydraulicProperties(wc_sat=0.4, specific_storage=1e-3)
        w0 = p.storage_content(0.0)
        w1 = p.storage_content(10.0)
        assert w1 > w0
        assert abs((w1 - w0) - 1e-3 * 10.0) < 1e-12

    def test_serialisation_round_trip(self):
        p = HydraulicProperties(specific_storage=7e-4, wc_sat=0.42)
        p2 = HydraulicProperties.from_dict(p.to_dict())
        assert abs(p2.specific_storage - 7e-4) < 1e-15
        assert abs(p2.wc_sat - 0.42) < 1e-12


# ======================================================================
class TestAnalyticDiffusion:
    """Confined, fully saturated aquifer: exact erfc step response."""

    L, H, K, SS = 50.0, 5.0, 1.0e-4, 1.0e-3
    H0, H1 = 100.0, 110.0     # high enough to stay saturated everywhere

    def _setup(self):
        mesh = _rect_mesh(self.L, self.H, 1.0)
        props = {"m": HydraulicProperties(
            ks=self.K, model=PermeabilityModel.CONSTANT,
            specific_storage=self.SS)}
        s = TransientSeepageSolver(mesh, props, relaxation=1.0,
                                   tolerance=1e-9, max_picard=12,
                                   time_steps=150)
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H1)
            elif abs(nd.x - self.L) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H0)
            else:
                b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        h_ini = [self.H0] * mesh.node_count
        for nid in mesh.boundary_node_ids():
            if abs(mesh.nodes[nid].x) < 1e-9:
                h_ini[nid] = self.H1
        return mesh, s, b, h_ini

    def test_matches_erfc_solution(self):
        mesh, s, b, h_ini = self._setup()
        D = self.K / self.SS
        for T in (200.0, 1000.0):
            r = s.solve_transient([TransientStage(time=T, bcs=b)],
                                  initial_head=h_ini, initial_bcs=b)[0]
            assert r.converged, r.notes
            # Only where the semi-infinite assumption still holds
            limit = min(2.0 * math.sqrt(D * T),
                        self.L - 3.0 * math.sqrt(D * T))
            errs = []
            for i, nd in enumerate(mesh.nodes):
                if abs(nd.y - self.H / 2) < 0.6 and 0.5 < nd.x < limit:
                    exact = self.H0 + (self.H1 - self.H0) * math.erfc(
                        nd.x / (2.0 * math.sqrt(D * T)))
                    errs.append(abs(r.total_head[i] - exact))
            assert errs, T
            assert max(errs) / (self.H1 - self.H0) < 0.01, (T, max(errs))

    def test_front_advances_with_time(self):
        mesh, s, b, h_ini = self._setup()
        heads = []
        probe = min(range(mesh.node_count),
                    key=lambda i: (mesh.nodes[i].x - 12.0) ** 2
                    + (mesh.nodes[i].y - self.H / 2) ** 2)
        for T in (100.0, 500.0, 2000.0):
            r = s.solve_transient([TransientStage(time=T, bcs=b)],
                                  initial_head=h_ini, initial_bcs=b)[0]
            heads.append(r.total_head[probe])
        for a, c in zip(heads[:-1], heads[1:]):
            assert c > a, heads

    def test_larger_storage_slows_the_response(self):
        """Doubling Ss must delay the pressure front: with Ss ten times
        larger the head at a fixed point and time must be lower."""
        mesh, _s, b, h_ini = self._setup()
        probe = min(range(mesh.node_count),
                    key=lambda i: (mesh.nodes[i].x - 10.0) ** 2
                    + (mesh.nodes[i].y - self.H / 2) ** 2)
        out = []
        for ss in (self.SS, 10.0 * self.SS):
            props = {"m": HydraulicProperties(
                ks=self.K, model=PermeabilityModel.CONSTANT,
                specific_storage=ss)}
            s = TransientSeepageSolver(mesh, props, relaxation=1.0,
                                       tolerance=1e-9, max_picard=12,
                                       time_steps=120)
            r = s.solve_transient([TransientStage(time=500.0, bcs=b)],
                                  initial_head=h_ini, initial_bcs=b)[0]
            out.append(r.total_head[probe])
        assert out[1] < out[0], out


# ======================================================================
class TestAsymptoticConsistency:
    """The transient solution at large time must reproduce the steady
    state — this ties Phase 6 to the validated Phase-3 solver."""

    W, HT = 20.0, 12.0

    def _bcs(self, mesh, left, right):
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                if nd.y <= left + 1e-9:
                    b.add_node(nid, BCType.TOTAL_HEAD, left)
                else:
                    b.add_node(nid, BCType.UNKNOWN)
            elif abs(nd.x - self.W) < 1e-9:
                if nd.y <= right + 1e-9:
                    b.add_node(nid, BCType.TOTAL_HEAD, right)
                else:
                    b.add_node(nid, BCType.UNKNOWN)
            else:
                b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        return b

    def _props(self):
        return {"m": HydraulicProperties(
            ks=1e-5, model=PermeabilityModel.GARDNER,
            gardner_a=1.0, gardner_n=3.0, vg_alpha=0.1, vg_n=2.0,
            wc_sat=0.4, wc_res=0.05, specific_storage=1e-4)}

    def test_long_time_matches_steady_state(self):
        mesh = _rect_mesh(self.W, self.HT, 0.9)
        props = self._props()
        final = self._bcs(mesh, 10.0, 3.0)
        steady = UnsaturatedSeepageSolver(
            mesh, props, relaxation=0.4, max_iterations=200,
            tolerance=1e-6).solve_unsaturated(final)
        assert steady.ok
        tr = TransientSeepageSolver(mesh, props, relaxation=0.5,
                                    tolerance=1e-6, max_picard=40)
        rt = tr.solve_transient([TransientStage(time=1e9, bcs=final)],
                                initial_bcs=self._bcs(mesh, 10.0, 10.0))[-1]
        diff = max(abs(a - c) for a, c in zip(steady.total_head,
                                              rt.total_head))
        assert diff < 0.05, diff

    def test_drainage_reduces_stored_water(self):
        mesh = _rect_mesh(self.W, self.HT, 1.8)
        props = self._props()
        tr = TransientSeepageSolver(mesh, props, relaxation=0.5,
                                    tolerance=1e-4, max_picard=20,
                                    time_steps=8)
        stages = [TransientStage(time=t, bcs=self._bcs(mesh, 4.0, 4.0))
                  for t in (1e4, 1e5, 1e6)]
        res = tr.solve_transient(stages,
                                 initial_bcs=self._bcs(mesh, 10.0, 10.0))
        stored = [r.notes.get("stored_water") for r in res]
        assert all(v is not None for v in stored), stored
        for a, c in zip(stored[:-1], stored[1:]):
            assert c <= a + 1e-9, stored


# ======================================================================
class TestStagesAndSettings:
    def test_stage_serialisation(self):
        b = SeepageBoundaryConditions()
        b.add_node(0, BCType.TOTAL_HEAD, 5.0)
        st = TransientStage(time=250.0, calculate_sf=True, label="drawdown",
                            bcs=b)
        st2 = TransientStage.from_dict(st.to_dict())
        assert abs(st2.time - 250.0) < 1e-12
        assert st2.calculate_sf is True
        assert st2.label == "drawdown"
        assert st2.bcs is not None and len(st2.bcs.nodes) == 1

    def test_stage_without_bcs(self):
        st2 = TransientStage.from_dict(TransientStage(time=1.0).to_dict())
        assert st2.bcs is None

    def test_advanced_options_are_exclusive(self):
        """The reference allows only ONE advanced groundwater option."""
        from ogr_core.project.settings import GroundwaterSettings
        g = GroundwaterSettings()
        g.set_advanced_option("transient")
        assert (g.transient, g.excess_pore_pressure, g.rapid_drawdown) == \
            (True, False, False)
        g.set_advanced_option("rapid_drawdown")
        assert (g.transient, g.excess_pore_pressure, g.rapid_drawdown) == \
            (False, False, True)
        g.set_advanced_option(None)
        assert g.advanced_option() is None

    def test_sf_stage_selection(self):
        from ogr_core.project.settings import GroundwaterSettings
        g = GroundwaterSettings()
        g.transient_stages = [
            {"time": 10.0, "calculate_sf": False},
            {"time": 20.0, "calculate_sf": True},
            {"time": 30.0, "calculate_sf": True},
        ]
        assert g.stage_times() == [10.0, 20.0, 30.0]
        assert g.sf_stages() == [1, 2]

    def test_results_carry_stage_metadata(self):
        mesh = _rect_mesh(10.0, 8.0, 1.2)
        props = {"m": HydraulicProperties(
            ks=1e-5, model=PermeabilityModel.CONSTANT,
            specific_storage=1e-4)}
        tr = TransientSeepageSolver(mesh, props, relaxation=1.0,
                                    tolerance=1e-7, time_steps=6)
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 6.0)
            elif abs(nd.x - 10.0) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 3.0)
            else:
                b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        stages = [TransientStage(time=100.0, bcs=b),
                  TransientStage(time=300.0, calculate_sf=True, bcs=b)]
        res = tr.solve_transient(stages, initial_bcs=b)
        assert len(res) == 2
        assert res[0].notes["stage"] == 0
        assert abs(res[1].notes["time"] - 300.0) < 1e-9
        assert res[1].notes["calculate_sf"] is True
        assert res[0].notes["time_steps"] == 6

    def test_empty_stage_list(self):
        mesh = _rect_mesh(6.0, 4.0, 1.5)
        tr = TransientSeepageSolver(
            mesh, {"m": HydraulicProperties(ks=1e-5)})
        assert tr.solve_transient([]) == []

    def test_auto_time_steps_is_positive(self):
        mesh = _rect_mesh(10.0, 8.0, 1.2)
        tr = TransientSeepageSolver(
            mesh, {"m": HydraulicProperties(ks=1e-5,
                                            specific_storage=1e-4)})
        n = tr._auto_time_steps(1e5)
        assert 4 <= n <= 200


# ======================================================================
try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


@_requires_qt
class TestTransientGui:
    def _setup(self):
        from test_slide_validation_ej1 import _ej1_project
        from ogr_core.project.settings import GroundwaterMethod
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        p = _ej1_project()
        p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
        for m in p.materials:
            m.hydraulic = HydraulicProperties(
                ks=1e-5, model=PermeabilityModel.GARDNER,
                gardner_a=1.0, gardner_n=3.0, specific_storage=1e-4)
        p.fem_mesh = generate_mesh_for_project(p, target_elements=140)
        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        w._update_groundwater_actions()
        return p, w

    def test_action_enabled_with_fea(self):
        p, w = self._setup()
        assert w._actions["gw_transient"].isEnabled() is True

    def test_dialog_saves_stages_and_enforces_exclusivity(self):
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog,
        )
        p, w = self._setup()
        gw = p.settings.groundwater
        gw.set_advanced_option("rapid_drawdown")
        d = TransientStagesDialog(gw, None)
        d.chk_enabled.setChecked(True)
        d._add_row(1e4, False, "a")
        d._add_row(1e5, True, "b")
        d._accept()
        assert gw.transient is True
        assert gw.rapid_drawdown is False        # exclusive
        assert len(gw.transient_stages) == 2
        assert gw.sf_stages() == [1]

    def test_dialog_sorts_and_validates(self):
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog,
        )
        p, _w = self._setup()
        d = TransientStagesDialog(p.settings.groundwater, None)
        d._add_row(500.0, False, "later")
        d._add_row(100.0, False, "earlier")
        stages = d.stages()
        assert [s["time"] for s in stages] == [100.0, 500.0]

    def test_compute_routes_to_transient(self):
        from ogr_fem2d.solvers import BCType
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            boundary_sides,
        )
        p, w = self._setup()
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_stages = [{"time": 1e4, "calculate_sf": False},
                               {"time": 1e5, "calculate_sf": True}]
        gw.transient_time_steps = 3
        bcs = w._seepage_bcs()
        sides = boundary_sides(p.fem_mesh)
        for nid in sides["Left edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 40.0)
        for nid in sides["Right edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        p.seepage_bcs = bcs
        w._compute_groundwater()
        assert len(p.transient_results) == 2
        assert p.seepage_result is p.transient_results[-1]
        assert p.transient_results[1].notes["calculate_sf"] is True

    def test_steady_path_untouched_when_transient_off(self):
        from ogr_fem2d.solvers import BCType
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            boundary_sides,
        )
        p, w = self._setup()
        assert p.settings.groundwater.transient is False
        bcs = w._seepage_bcs()
        sides = boundary_sides(p.fem_mesh)
        for nid in sides["Left edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 40.0)
        for nid in sides["Right edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        p.seepage_bcs = bcs
        w._compute_groundwater()
        assert p.seepage_result is not None
        assert p.transient_results == []


# ======================================================================
@_requires_qt
class TestStageFactorsOfSafety:
    """v0.1.31 — the per-stage 'Calculate SF' checkbox must actually
    produce a factor of safety per flagged stage, turning a pore-pressure
    history into a stability history."""

    def _drawdown(self, times=(1e4, 1e6), calc_sf=True):
        from test_slide_validation_ej1 import _ej1_project
        from ogr_core.materials import PorePressureType
        from ogr_core.project.settings import GroundwaterMethod
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_fem2d.solvers import BCType, default_boundary_conditions
        from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        p = _ej1_project()
        gw = p.settings.groundwater
        gw.method = GroundwaterMethod.FEA_STEADY.value
        gw.set_advanced_option("transient")
        gw.transient_time_steps = 3
        for m in p.materials:
            m.hydraulic = HydraulicProperties(
                ks=1e-5, model=PermeabilityModel.GARDNER,
                gardner_a=1.0, gardner_n=3.0, specific_storage=1e-4)
            m.pore_pressure = PorePressureType.FEM_SEEPAGE
        p.fem_mesh = generate_mesh_for_project(p, target_elements=150)
        p.settings.search.grid_nx = 4
        p.settings.search.grid_ny = 4
        mesh = p.fem_mesh
        sides = boundary_sides(mesh)

        def mk(hl, hr):
            b = default_boundary_conditions(mesh)
            for n in sides["Left edge"]:
                b.add_node(n, BCType.TOTAL_HEAD, hl)
            for n in sides["Right edge"]:
                b.add_node(n, BCType.TOTAL_HEAD, hr)
            return b

        gw.transient_initial_bcs = mk(45.0, 30.0).to_dict()
        low = mk(28.0, 26.0).to_dict()
        gw.transient_stages = [{"time": t, "calculate_sf": calc_sf,
                                "bcs": low} for t in times]
        p.seepage_bcs = mk(28.0, 26.0)
        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        w._compute_groundwater()
        return p, w

    def test_fos_computed_for_flagged_stages(self):
        p, _w = self._drawdown()
        for r in p.transient_results:
            assert r.notes.get("fos"), r.notes
            assert "fos_min" in r.notes

    def test_no_fos_when_not_flagged(self):
        p, _w = self._drawdown(calc_sf=False)
        for r in p.transient_results:
            assert not r.notes.get("fos")

    def test_per_stage_bcs_make_the_field_evolve(self):
        """Without per-stage boundary conditions the initial state and
        every stage would share the same conditions and NOTHING would
        change in time — the bug this test pins down."""
        p, _w = self._drawdown(times=(1e4, 1e6))
        u_early = max(p.transient_results[0].pore_pressure)
        u_late = max(p.transient_results[-1].pore_pressure)
        assert u_late < u_early, (u_early, u_late)

    def test_drawdown_recovers_safety_with_time(self):
        """Classic rapid-drawdown behaviour: the factor of safety is
        lowest right after the level drops (pressures not yet dissipated)
        and recovers as they do."""
        p, _w = self._drawdown(times=(1e4, 1e6))
        f0 = p.transient_results[0].notes["fos_min"]
        f1 = p.transient_results[-1].notes["fos_min"]
        assert f1 > f0, (f0, f1)

    def test_warning_when_materials_ignore_seepage(self):
        from ogr_core.materials import PorePressureType
        p, w = self._drawdown()
        for m in p.materials:
            m.pore_pressure = PorePressureType.NONE
        w._compute_groundwater()
        assert any(r.notes.get("fos_warning")
                   for r in p.transient_results)

    def test_active_seepage_result_restored(self):
        """Computing per-stage factors must not leave the project
        pointing at an intermediate stage."""
        p, _w = self._drawdown()
        assert p.seepage_result is p.transient_results[-1]


@_requires_qt
class TestInterpretStageNavigation:
    def _window(self):
        p, w = TestStageFactorsOfSafety()._drawdown(times=(1e4, 1e6))
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow,
        )
        import matplotlib
        matplotlib.use("Agg")
        return p, InterpretGroundwaterWindow(p, p.seepage_result,
                                             w._gw_solver, None)

    def test_stage_selector_lists_every_stage(self):
        p, iw = self._window()
        assert iw.cbo_stage is not None
        assert iw.cbo_stage.count() == len(p.transient_results)

    def test_switching_stage_changes_the_field(self):
        p, iw = self._window()
        iw._on_stage(0)
        first = list(iw.result.total_head)
        iw._on_stage(1)
        assert iw.result.total_head != first

    def test_summary_reports_time_and_fos(self):
        _p, iw = self._window()
        iw._on_stage(0)
        assert "t =" in iw.status.text()
        assert "FoS" in iw.status.text()

    def test_no_selector_for_steady_runs(self):
        from test_slide_validation_ej1 import _ej1_project
        from ogr_fem2d.solvers import SeepageResult
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow,
        )
        QApplication.instance() or QApplication([])
        p = _ej1_project()
        r = SeepageResult()
        r.total_head = [1.0]
        r.pressure_head = [0.0]
        r.pore_pressure = [0.0]
        r.converged = True
        iw = InterpretGroundwaterWindow(p, r, None, None)
        assert iw.cbo_stage is None
