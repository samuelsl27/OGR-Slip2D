# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.200 (spec 008, F3a) — groundwater for the agent, and the units.

Invariants protected
--------------------
**Each permeability model gets its suction in the unit of its own
definition** (rule 1, closed forms from the sources). The solver evaluates
k_r at an element's pressure head P (m); van Genuchten (1980) and Gardner
(1958) are written in suction HEAD, h = -P metres, and Brooks & Corey
(1964), Fredlund & Xing (1994), Simple and a user table in matric SUCTION,
s = -P·gamma_w kPa. Until this version every model was handed the metres:
a factor gamma_w too little suction for the four kPa models. Checked
through ``_element_kr``, the solver's own door, against the formulas.

**The van Genuchten library is Carsel & Parrish (1988) in 1/m.** Their
table is in 1/cm (sand 0.145 1/cm); it was stored as printed and read as
1/m — a "sand" a hundred times too retentive.

**The agent's groundwater runs are validated by what they compute**, each
against an external reference and through the operations layer: Darcy's
law in 1-D (heads and discharge exact), the arithmetic and harmonic means
of layered flow, the erfc step response of a confined aquifer and its
convergence to the steady state, Charnyi's discharge through a rectangular
dam, and Morgenstern's (1963) drawdown factors through the sweep.

**The field is written back as one undo step, and only onto the model it
was computed for.** A model edited while the job ran keeps its old field;
the stored result can still be read.

**A new mesh drops everything keyed by node id** — found in this version:
the conditions of each transient stage and of the initial state survived a
remesh, and a stage reservoir on the left face (8 nodes at x = 0) stood on
8 nodes of the crest (y = 25) of the demo slope after going from 300 to 600
elements.

**Every refusal leaves the model as it was**, and a parameter the chosen
model does not read is refused (rule 7).

**The interface's fixes**: Cancel in Set Boundary Conditions cancels, the
initial-state capture waits for OK, deleting a stage keeps the other
stages' conditions on their stages, and the Interpret groundwater window
has a solver after reopening the project.
"""
from __future__ import annotations

import atexit
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 5.0, "friction_angle": 30.0}}
_CACHE: dict = {}


def _ws():
    from ogr_api import Workspace
    ws = Workspace()
    atexit.register(ws.shutdown)
    return ws


def _box(ws, w, h, *, name="Box", boundaries=None, materials=None):
    from ogr_api import call
    pid = call(ws, "project_new", name=name)["project_id"]
    spec = {"external": [[0, 0], [w, 0], [w, h], [0, h]],
            "materials": materials or [{"name": "Soil", "unit_weight": 20,
                                        "strength": _SOIL}]}
    if boundaries:
        spec["material_boundaries"] = boundaries
    call(ws, "model_define", project_id=pid, spec=spec)
    return pid


def _state(ws, pid) -> str:
    return json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                      default=str)


# ======================================================================
# The units, per model
# ======================================================================
def _kr_via_solver(props, P, gamma_w=9.81):
    """k_r the solver uses for an element whose pressure head is P."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.geometry.regions import MaterialRegion
    from ogr_fem2d.mesh import generate_mesh
    from ogr_fem2d.solvers import UnsaturatedSeepageSolver

    poly = Polyline(vertices=[Vertex(0, 0), Vertex(2, 0), Vertex(2, 1),
                              Vertex(0, 1)], closed=True)
    mesh = generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=0.5)
    solver = UnsaturatedSeepageSolver(mesh, {"m": props}, gamma_w=gamma_w)
    kr = solver._element_kr([nd.y + P for nd in mesh.nodes])
    assert max(kr) - min(kr) < 1e-12, kr
    return kr[0]


class TestEachModelGetsItsOwnUnit:
    def test_brooks_corey_reads_kpa(self):
        """Brooks & Corey (1964): k_r = (psi_b / s)^(2 + 3 lambda) for
        s > psi_b, with s = -P gamma_w in kPa."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        p = HydraulicProperties(model=PermeabilityModel.BROOKS_COREY,
                                bc_lambda=0.6, bc_psi_b=30.0)
        s = 10.0 * 9.81
        exact = (30.0 / s) ** (2.0 + 3.0 * 0.6)
        assert abs(_kr_via_solver(p, -10.0) - exact) < 1e-12 * exact
        # Metres (the old path) would sit below the bubbling pressure.
        assert p.relative_permeability(10.0) == 1.0

    def test_van_genuchten_reads_metres(self):
        """van Genuchten (1980), Mualem form, with h = -P in metres."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        a, n = 3.6, 1.56
        m = 1.0 - 1.0 / n
        p = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                vg_alpha=a, vg_n=n, kr_min=1e-12)
        se = (1.0 + (a * 2.0) ** n) ** (-m)
        exact = math.sqrt(se) * (1.0 - (1.0 - se ** (1.0 / m)) ** m) ** 2
        assert abs(_kr_via_solver(p, -2.0) - exact) < 1e-12

    def test_gardner_reads_metres(self):
        """Gardner (1958): k_r = 1 / (1 + a h^n), h in metres."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        p = HydraulicProperties(model=PermeabilityModel.GARDNER,
                                gardner_a=0.01, gardner_n=2.0)
        assert abs(_kr_via_solver(p, -10.0) - 0.5) < 1e-12

    def test_a_user_curve_reads_kpa(self):
        """A table point at s = 9.81 kPa is P = -1 m of water; half way,
        P = -0.5 m, is the log-linear mid-point, 10^-0.5. With metres it
        would have been 10^(-0.5/9.81) = 0.889."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        p = HydraulicProperties(model=PermeabilityModel.USER_DEFINED,
                                user_curve=[(0.0, 1e-5), (9.81, 1e-6)],
                                kr_min=1e-9)
        assert abs(_kr_via_solver(p, -1.0) - 0.1) < 1e-12
        assert abs(_kr_via_solver(p, -0.5) - 10 ** -0.5) < 1e-12

    def test_fredlund_xing_and_simple_read_kpa(self):
        """The unit identity: k_r(P) = k_r(s = -P gamma_w), and not
        k_r(-P). (The functional form of these two is not what this
        checks.)"""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        for p in (HydraulicProperties(
                model=PermeabilityModel.FREDLUND_XING),
                  HydraulicProperties(model=PermeabilityModel.SIMPLE)):
            got = _kr_via_solver(p, -3.0)
            assert abs(got - p.relative_permeability(3.0 * 9.81)) < 1e-15
            assert abs(got - p.relative_permeability(3.0)) > 1e-3, p.model

    def test_gamma_w_is_the_solvers(self):
        """The conversion uses the fluid the solver was given (a project
        in imperial units has 62.4)."""
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        p = HydraulicProperties(model=PermeabilityModel.BROOKS_COREY,
                                bc_lambda=1.0, bc_psi_b=1.0, kr_min=1e-15)
        a = _kr_via_solver(p, -1.0, gamma_w=9.81)
        b = _kr_via_solver(p, -1.0, gamma_w=62.4)
        assert abs(a / 9.81 ** -5 - 1.0) < 1e-12
        assert abs(b / 62.4 ** -5 - 1.0) < 1e-12

    def test_each_model_declares_its_unit(self):
        from ogr_core.hydraulic import PermeabilityModel
        from ogr_core.hydraulic.permeability_models import SUCTION_UNIT
        assert set(SUCTION_UNIT) == set(PermeabilityModel)
        heads = {m.value for m, u in SUCTION_UNIT.items() if u == "m"}
        assert heads == {"constant", "van_genuchten", "gardner"}


class TestTheLibraryIsInItsUnit:
    #: Carsel & Parrish (1988), Table 3: alpha in 1/cm, n.
    CARSEL_PARRISH = {"Sand": (0.145, 2.68), "Loamy sand": (0.124, 2.28),
                      "Sandy loam": (0.075, 1.89), "Loam": (0.036, 1.56),
                      "Silt": (0.016, 1.37), "Silt loam": (0.020, 1.41),
                      "Clay": (0.008, 1.09), "Silty clay": (0.005, 1.09)}

    def test_the_van_genuchten_alphas_are_per_metre(self):
        from ogr_core.hydraulic import PermeabilityModel, library_for
        lib = library_for(PermeabilityModel.VAN_GENUCHTEN)
        assert set(lib) == set(self.CARSEL_PARRISH)
        for soil, (a_cm, n) in self.CARSEL_PARRISH.items():
            assert abs(lib[soil]["vg_alpha"] - 100.0 * a_cm) < 1e-9, soil
            assert lib[soil]["vg_n"] == n

    def test_the_default_is_their_loam(self):
        from ogr_core.hydraulic import HydraulicProperties
        p = HydraulicProperties()
        assert (p.vg_alpha, p.vg_n) == (3.6, 1.56)

    def test_a_file_without_the_key_keeps_what_it_meant(self):
        """The loader's default stays 0.036: a file without vg_alpha was
        written when that was the default, evaluated as 1/m."""
        from ogr_core.hydraulic import HydraulicProperties
        assert HydraulicProperties.from_dict({}).vg_alpha == 0.036

    def test_the_retention_curve_is_in_metres(self):
        """theta(h) = theta_r + (theta_s - theta_r)[1 + (alpha h)^n]^-m,
        h in metres (van Genuchten 1980), what the transient storage
        reads for every model."""
        from ogr_core.hydraulic import HydraulicProperties
        p = HydraulicProperties()
        m = 1.0 - 1.0 / p.vg_n
        se = (1.0 + (p.vg_alpha * 1.5) ** p.vg_n) ** (-m)
        exact = p.wc_res + (p.wc_sat - p.wc_res) * se
        assert abs(p.storage_content(-1.5) - exact) < 1e-15


class TestUnusableProperties:
    def test_each_check_names_its_field(self):
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        assert HydraulicProperties().problems() == []
        for kw, word in ((dict(ks=0.0), "ks"), (dict(vg_n=1.0), "vg_n"),
                         (dict(kr_min=0.0), "kr_min"),
                         (dict(wc_res=0.5, wc_sat=0.4), "wc_res"),
                         (dict(model=PermeabilityModel.USER_DEFINED,
                               user_curve=[(0.0, 0.0), (10.0, 1e-6)]),
                          "user_curve")):
            probs = HydraulicProperties(**kw).problems()
            assert any(word in p for p in probs), (kw, probs)


# ======================================================================
# hydraulic_set
# ======================================================================
class TestHydraulicSet:
    def test_it_sets_and_refuses_what_the_model_would_not_read(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        out = call(ws, "hydraulic_set", project_id=pid, material="Soil",
                   model="brooks_corey", properties={"ks": 2e-6,
                                                     "bc_psi_b": 12.0})
        assert out["suction_unit"] == "kPa"
        hyd = ws.get(pid).project.materials[0].hydraulic
        assert (hyd.ks, hyd.bc_psi_b, hyd.model.value) == (
            2e-6, 12.0, "brooks_corey")
        before = _state(ws, pid)
        with pytest.raises(Conflict):
            call(ws, "hydraulic_set", project_id=pid, material="Soil",
                 properties={"gardner_a": 0.1})
        with pytest.raises(InvalidArgument):
            call(ws, "hydraulic_set", project_id=pid, material="Soil",
                 properties={"ks": -1.0})
        with pytest.raises(Conflict):
            call(ws, "hydraulic_set", project_id=pid, material="Soil",
                 model="van_genuchten", properties={"vg_m": 0.3})
        assert _state(ws, pid) == before

    def test_switching_model_and_library_in_one_call(self):
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10)
        out = call(ws, "hydraulic_set", project_id=pid, material="Soil",
                   model="van_genuchten", library="sand")
        hyd = ws.get(pid).project.materials[0].hydraulic
        assert (hyd.vg_alpha, hyd.vg_n) == (14.5, 2.68), out
        assert out["suction_unit"] == "m"

    def test_material_set_sends_hydraulics_to_its_operation(self):
        from ogr_api import InvalidArgument, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        try:
            call(ws, "material_set", project_id=pid, material="Soil",
                 properties={"hydraulic": {"ks": 1e-6}})
        except InvalidArgument as exc:
            assert "hydraulic_set" in str(exc)
        else:
            raise AssertionError("hydraulic accepted by material_set")

    def test_a_drawdown_envelope_is_set_and_said_to_be_unread(self):
        from ogr_api import call
        from ogr_core.materials.drawdown_envelopes import REnvelope
        ws = _ws()
        pid = _box(ws, 20, 10)
        out = call(ws, "material_set", project_id=pid, material="Soil",
                   properties={"drawdown_envelope": {
                       "kind": "r", "c_r": 10.0, "phi_r_deg": 15.0}})
        env = ws.get(pid).project.materials[0].drawdown_envelope
        assert isinstance(env, REnvelope) and env.c_r == 10.0
        assert any("multi-stage" in n for n in out["notes"]), out


# ======================================================================
# Darcy through the operations
# ======================================================================
K = 1e-5


def _confined(ws, pid, hl=15.0, hr=12.0):
    from ogr_api import call
    call(ws, "mesh_generate", project_id=pid, target_elements=400)
    call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
         side="left", value=hl)
    call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
         side="right", value=hr)
    call(ws, "seepage_bc_set", project_id=pid, bc_type="nodal_flow",
         side="ground", value=0.0)


def _darcy():
    if "darcy" not in _CACHE:
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10, name="Darcy")
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": K})
        _confined(ws, pid)
        steps = len(ws.get(pid).stack.history()[0])
        before = _state(ws, pid)
        run = call(ws, "groundwater_run", project_id=pid, wait_seconds=120)
        _CACHE["darcy"] = (ws, pid, run, steps, before)
    return _CACHE["darcy"]


def _layered(split):
    """Two materials split horizontally ('parallel') or vertically
    ('series'), k 1e-5 and 4e-5."""
    key = "layers_" + split
    if key not in _CACHE:
        from ogr_api import call
        ws = _ws()
        line = [[0, 5], [20, 5]] if split == "parallel" else [[10, 0],
                                                              [10, 10]]
        at = ([[10, 7.5], [10, 2.5]] if split == "parallel"
              else [[5, 5], [15, 5]])
        pid = _box(ws, 20, 10, name=key, boundaries=[line], materials=[
            {"name": "A", "unit_weight": 20, "strength": _SOIL,
             "at": at[0]},
            {"name": "B", "unit_weight": 20, "strength": _SOIL,
             "at": at[1]}])
        call(ws, "hydraulic_set", project_id=pid, material="A",
             properties={"ks": 1e-5})
        call(ws, "hydraulic_set", project_id=pid, material="B",
             properties={"ks": 4e-5})
        _confined(ws, pid)
        call(ws, "groundwater_run", project_id=pid, wait_seconds=120)
        _CACHE[key] = (ws, pid)
    return _CACHE[key]


def _flow(ws, pid, x):
    from ogr_api import call
    return call(ws, "groundwater_results", project_id=pid, view="section",
                section=[[x, 0], [x, 10]])["section"]["flow"]


class TestDarcyThroughTheApi:
    def test_the_heads_are_linear(self):
        from ogr_api import call
        ws, pid, run, _s, _b = _darcy()
        assert run["state"] == "done" and run["written_back"], run
        for x, y in ((0.0, 5.0), (5.0, 2.0), (10.0, 5.0), (17.3, 8.0)):
            at = call(ws, "groundwater_results", project_id=pid,
                      view="point", point_xy=[x, y])["at"]
            assert abs(at["total_head_m"] - (15.0 - 3.0 * x / 20.0)) < 1e-6
            assert abs(at["pore_pressure_kpa"]
                       - 9.81 * (at["total_head_m"] - y)) < 1e-5

    def test_the_discharge_is_darcys(self):
        """Q = k i A = 1e-5 x 3/20 x 10, and ks is what sets it: this is
        the test that hydraulic_set's number is read."""
        ws, pid, *_ = _darcy()
        exact = K * 3.0 / 20.0 * 10.0
        for x in (4.0, 10.0, 16.0):
            q = _flow(ws, pid, x)
            assert abs(abs(q) - exact) < 1e-6 * exact, (x, q)

    def test_the_sign_follows_the_section(self):
        """Positive towards the section's left-hand normal: upward
        section, flow to the right, so negative; reversed, positive."""
        from ogr_api import call
        ws, pid, *_ = _darcy()
        up = _flow(ws, pid, 10.0)
        down = call(ws, "groundwater_results", project_id=pid,
                    view="section",
                    section=[[10, 10], [10, 0]])["section"]["flow"]
        assert up < 0 < down and abs(up + down) < 1e-12

    def test_parallel_layers_add_arithmetically(self):
        ws, pid = _layered("parallel")
        exact = (1e-5 * 5.0 + 4e-5 * 5.0) * 3.0 / 20.0
        q = abs(_flow(ws, pid, 10.0))
        assert abs(q - exact) < 1e-6 * exact, (q, exact)

    def test_layers_in_series_add_harmonically(self):
        from ogr_api import call
        ws, pid = _layered("series")
        k_eq = 20.0 / (10.0 / 1e-5 + 10.0 / 4e-5)
        exact = k_eq * 3.0 / 20.0 * 10.0
        q = abs(_flow(ws, pid, 5.0))
        assert abs(q - exact) < 1e-6 * exact, (q, exact)
        # The head at the interface divides the drop by resistance.
        h = call(ws, "groundwater_results", project_id=pid, view="point",
                 point_xy=[10.0, 5.0])["at"]["total_head_m"]
        r1, r2 = 10.0 / 1e-5, 10.0 / 4e-5
        assert abs(h - (15.0 - 3.0 * r1 / (r1 + r2))) < 1e-6


# ======================================================================
# Write-back
# ======================================================================
class TestTheFieldIsWrittenBack:
    def test_one_undo_step_that_restores_the_model(self):
        from ogr_api import call
        ws, pid, run, steps, before = _darcy()
        handle = ws.get(pid)
        undo = handle.stack.history()[0]
        assert len(undo) == steps + 1 and undo[-1] == "Compute groundwater"
        after = _state(ws, pid)
        assert handle.project.seepage_result is not None
        call(ws, "project_history", project_id=pid, action="undo")
        try:
            assert _state(ws, pid) == before
            assert handle.project.seepage_result is None
        finally:
            call(ws, "project_history", project_id=pid, action="redo")
        assert _state(ws, pid) == after

    def test_asking_again_writes_nothing_again(self):
        from ogr_api import call
        ws, pid, run, *_ = _darcy()
        n = len(ws.get(pid).stack.history()[0])
        again = call(ws, "job_get", job_id=run["job_id"])
        assert again["written_back"] and not again["stale"]
        assert len(ws.get(pid).stack.history()[0]) == n

    def test_a_model_edited_meanwhile_keeps_its_field(self):
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": K})
        _confined(ws, pid)
        started = call(ws, "groundwater_run", project_id=pid,
                       wait_seconds=0)
        # The write-back happens when the job is ASKED about, so this
        # edit always lands first, however fast the job is.
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": 2 * K})
        done = call(ws, "job_get", job_id=started["job_id"],
                    wait_seconds=120)
        assert done["state"] == "done" and not done["written_back"], done
        assert ws.get(pid).project.seepage_result is None
        # The stored field is still there to read.
        q = call(ws, "groundwater_results", result_id=done["result_id"],
                 view="section", section=[[10, 0], [10, 10]])
        assert q["stale"]
        exact = K * 3.0 / 20.0 * 10.0
        assert abs(abs(q["section"]["flow"]) - exact) < 1e-6 * exact

    def test_results_get_points_a_field_to_its_reader(self):
        from ogr_api import Conflict, call
        ws, pid, run, *_ = _darcy()
        s = call(ws, "results_get", result_id=run["result_id"])
        assert s["kind"] == "groundwater"
        with pytest.raises(Conflict):
            call(ws, "results_get", result_id=run["result_id"],
                 view="critical")


# ======================================================================
# Transient: erfc and the steady limit
# ======================================================================
L_AQ, H_AQ, K_AQ, SS_AQ = 50.0, 5.0, 1.0e-4, 1.0e-3
H0, H1 = 100.0, 110.0
TIMES = (200.0, 1000.0, 1.0e6)


def _aquifer():
    if "aquifer" not in _CACHE:
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, L_AQ, H_AQ, name="Aquifer")
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": K_AQ, "specific_storage": SS_AQ})
        call(ws, "mesh_generate", project_id=pid, target_size=1.0)
        _set = dict(project_id=pid, bc_type="total_head")
        call(ws, "seepage_bc_set", side="left", value=H1, **_set)
        call(ws, "seepage_bc_set", side="right", value=H0, **_set)
        call(ws, "seepage_bc_set", project_id=pid, bc_type="nodal_flow",
             side="ground", value=0.0)
        out = call(ws, "transient_set", project_id=pid, stages=[
            {"time": t, "label": f"t{i}"} for i, t in enumerate(TIMES)],
            initial={"base": "current", "assign": [
                {"bc_type": "total_head", "side": "left", "value": H0}]},
            time_steps=150)
        run = call(ws, "groundwater_run", project_id=pid, wait_seconds=300)
        _CACHE["aquifer"] = (ws, pid, out, run)
    return _CACHE["aquifer"]


class TestTheTransientThroughTheApi:
    def test_the_step_response_is_erfc(self):
        """H = H0 + (H1 - H0) erfc(x / 2 sqrt(D t)), D = k/Ss, where the
        semi-infinite assumption still holds (as test_transient_v130)."""
        ws, pid, _out, run = _aquifer()
        assert run["written_back"], run
        stages = ws.get(pid).project.transient_results
        mesh = ws.get(pid).project.fem_mesh
        assert len(stages) == len(TIMES)
        D = K_AQ / SS_AQ
        for r, T in zip(stages[:2], TIMES[:2]):
            assert r.converged, r.notes
            limit = min(2.0 * math.sqrt(D * T),
                        L_AQ - 3.0 * math.sqrt(D * T))
            errs = [abs(r.total_head[i] - (H0 + (H1 - H0) * math.erfc(
                        nd.x / (2.0 * math.sqrt(D * T)))))
                    for i, nd in enumerate(mesh.nodes)
                    if abs(nd.y - H_AQ / 2) < 0.6 and 0.5 < nd.x < limit]
            assert errs and max(errs) / (H1 - H0) < 0.01, (T, max(errs))

    def test_a_long_time_is_the_steady_state(self):
        ws, pid, *_ = _aquifer()
        r = ws.get(pid).project.transient_results[-1]
        mesh = ws.get(pid).project.fem_mesh
        worst = max(abs(h - (H1 - (H1 - H0) * nd.x / L_AQ))
                    for h, nd in zip(r.total_head, mesh.nodes))
        assert worst < 1e-3 * (H1 - H0), worst

    def test_the_stages_are_readable(self):
        from ogr_api import call
        ws, pid, out, _run = _aquifer()
        assert out["initial"] == "own conditions"
        rows = call(ws, "groundwater_results", project_id=pid,
                    view="stages")["stages"]
        assert [r["time"] for r in rows] == list(TIMES)
        assert [r["label"] for r in rows] == ["t0", "t1", "t2"]
        mid = call(ws, "groundwater_results", project_id=pid, stage=0,
                   view="point", point_xy=[5.0, 2.5])["at"]
        late = call(ws, "groundwater_results", project_id=pid, stage=2,
                    view="point", point_xy=[5.0, 2.5])["at"]
        assert mid["total_head_m"] < late["total_head_m"]


# ======================================================================
# Charnyi, the free surface, and reopening
# ======================================================================
L_DAM, H_DAM, K_DAM, HU, HD = 20.0, 12.0, 1.0e-5, 10.0, 2.0


def _dam():
    if "dam" not in _CACHE:
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, L_DAM, H_DAM, name="Dam")
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             model="gardner", properties={"ks": K_DAM, "kr_min": 1e-8,
                                          "gardner_a": 1.0e4,
                                          "gardner_n": 5.0})
        call(ws, "mesh_generate", project_id=pid, target_size=0.6)
        for pts in ([[0, HU], [0, H_DAM]], [[L_DAM, 0], [L_DAM, H_DAM]]):
            call(ws, "seepage_bc_set", project_id=pid, bc_type="unknown",
                 along=pts)
        for side, level in (("left", HU), ("right", HD)):
            call(ws, "seepage_bc_set", project_id=pid,
                 reservoir={"level": level, "side": side})
        run = call(ws, "groundwater_run", project_id=pid, wait_seconds=300)
        _CACHE["dam"] = (ws, pid, run)
    return _CACHE["dam"]


class TestCharnyiThroughTheApi:
    def test_the_discharge_is_charnyis(self):
        """q = k (H1^2 - H2^2) / 2L for a rectangular dam on an
        impervious base (Charnyi); with k(psi) this sharp the unsaturated
        zone barely conducts, so within 5 % as in test_unsaturated_v127."""
        ws, pid, run = _dam()
        assert run["summary"]["field"]["converged"], run
        exact = K_DAM * (HU ** 2 - HD ** 2) / (2.0 * L_DAM)
        q = abs(_flow_dam(ws, pid))
        assert abs(q - exact) / exact < 0.05, (q, exact)

    def test_the_free_surface_survives_reopening(self):
        import tempfile

        from ogr_api import call
        ws, pid, _run = _dam()
        fs = call(ws, "groundwater_results", project_id=pid,
                  view="free_surface")["free_surface"]
        assert len(fs) > 10 and abs(fs[0][1] - HU) < 1.0, fs[:3]
        folder = Path(tempfile.mkdtemp(prefix="ogr_gw_"))
        path = str(folder / "dam.ogr")
        call(ws, "project_save", project_id=pid, path=path)
        other = call(ws, "project_open", path=path)["project_id"]
        assert getattr(ws.get(other).project, "_gw_solver", None) is None
        again = call(ws, "groundwater_results", project_id=other,
                     view="free_surface")["free_surface"]
        assert again == fs
        # The file keeps nine significant digits of each head.
        q1, q2 = _flow_dam(ws, pid), _flow_dam(ws, other)
        assert abs(q1 - q2) <= 1e-6 * abs(q1), (q1, q2)

    def test_the_picture_has_the_field(self):
        from ogr_api import Conflict, call
        ws, pid, _run = _dam()
        out = call(ws, "model_render", project_id=pid, field="pressure_head")
        assert out["png"][:8] == b"\x89PNG\r\n\x1a\n"
        with pytest.raises(Conflict):
            call(ws, "model_render", project_id=pid, stage=0)


def _flow_dam(ws, pid):
    from ogr_api import call
    return call(ws, "groundwater_results", project_id=pid, view="section",
                section=[[L_DAM / 2, H_DAM], [L_DAM / 2, 0]])["section"][
        "flow"]


# ======================================================================
# The drawdown sweep through the operations
# ======================================================================
def _morgenstern():
    if "morgenstern" not in _CACHE:
        import test_drawdown_sweep_v170 as dd
        from ogr_api import call
        ws = _ws()
        pid = ws.add(dd._homogeneous()).id
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], surface_type="circular",
             search_method="grid", num_slices=18,
             grid={"x_min": 60, "x_max": 240, "y_min": 160, "y_max": 420,
                   "nx": 3, "ny": 4},
             radius_increment=6, failure_direction="right_to_left")
        run = call(ws, "drawdown_sweep_run", project_id=pid, n_levels=4,
                   wait_seconds=300)
        _CACHE["morgenstern"] = (ws, pid, run)
    return _CACHE["morgenstern"]


class TestMorgensternThroughTheSweep:
    def test_the_worst_is_the_total_drawdown_near_120(self):
        """Morgenstern (1963): 1.20 emptied, 1.41 at half; the band is
        test_drawdown_sweep_v170's (6 %)."""
        _ws_, _pid, run = _morgenstern()
        m = run["summary"]["methods"][0]
        assert abs(m["critical"]["fos"] - 1.20) / 1.20 < 0.06, m
        by_level = dict(zip(m["levels"], m["fos"]))
        half = min((lv for lv in by_level if lv != "total drawdown"),
                   key=lambda lv: abs(lv - 50.0))
        assert by_level[half] > m["total_drawdown_fos"]

    def test_it_is_the_door_the_interface_uses(self):
        """Same numbers as ``run_configured_drawdown_sweep`` in process."""
        from ogr_slip2d.analysis_runner import run_configured_drawdown_sweep
        ws, pid, run = _morgenstern()
        sweep, _rep, _w = run_configured_drawdown_sweep(
            ws.get(pid).project, n_levels=4)
        ms = sweep.by_method["bishop_simplified"]
        got = run["summary"]["methods"][0]["fos"]
        assert [round(f, 6) for f in ms.fos] == got

    def test_a_design_standard_reaches_the_sweep(self):
        """Rule 7 for the one door (owner's decision, 2026-09-24): with
        the standard off the sweep is exactly the old path on the raw
        project; with EC7 DA1-C2 on it answers the FACTORED model, which
        the old path ignored (measured: 1.2245 -> 0.9803 at total
        drawdown, a pass that was a fail)."""
        import test_drawdown_sweep_v170 as dd
        from ogr_api import call
        from ogr_core.statistics import run_drawdown_sweep
        from ogr_slip2d.analysis_runner import (build_search,
                                                run_configured_drawdown_sweep)
        ws = _ws()
        out = {}
        for standard in ("off", "eurocode7_da1c2"):
            pid = ws.add(dd._homogeneous()).id
            call(ws, "analysis_configure", project_id=pid,
                 methods=["bishop_simplified"], surface_type="circular",
                 search_method="grid", num_slices=18,
                 grid={"x_min": 60, "x_max": 240, "y_min": 160,
                       "y_max": 420, "nx": 3, "ny": 4},
                 radius_increment=6, failure_direction="right_to_left",
                 design_standard=standard)
            p = ws.get(pid).project
            raw = run_drawdown_sweep(
                p, lambda mid: build_search(p, mid), ["bishop_simplified"],
                n_levels=2).by_method["bishop_simplified"].fos
            door, rep, _w = run_configured_drawdown_sweep(p, n_levels=2)
            out[standard] = (raw, door.by_method["bishop_simplified"].fos,
                             rep.applied)
        raw, door, applied = out["off"]
        assert door == raw and not applied
        raw, door, applied = out["eurocode7_da1c2"]
        assert applied and all(d < r for d, r in zip(door, raw))
        assert raw == out["off"][0]

    def test_without_rapid_drawdown_it_refuses(self):
        from ogr_api import NotConfigured, call
        from ogr_slip2d.analysis_runner import (AnalysisNotConfigured,
                                                run_configured_drawdown_sweep)
        ws = _ws()
        pid = _box(ws, 20, 10)
        with pytest.raises(NotConfigured):
            call(ws, "drawdown_sweep_run", project_id=pid)
        with pytest.raises(AnalysisNotConfigured):
            run_configured_drawdown_sweep(ws.get(pid).project)


# ======================================================================
# A new mesh drops what was keyed by node
# ======================================================================
class TestANewMeshDropsWhatWasKeyedByNode:
    def test_stage_and_initial_conditions_go_with_the_mesh(self):
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "mesh_generate", project_id=pid, target_elements=200)
        call(ws, "seepage_bc_set", project_id=pid,
             reservoir={"level": 8.0, "side": "left"})
        call(ws, "transient_set", project_id=pid,
             stages=[{"time": 10.0, "label": "a", "bcs": "current"},
                     {"time": 20.0, "calculate_sf": True}],
             initial="current")
        gw = ws.get(pid).project.settings.groundwater
        assert gw.transient_initial_bcs and gw.transient_stages[0]["bcs"]
        out = call(ws, "mesh_generate", project_id=pid,
                   target_elements=500)
        note = " ".join(out["notes"])
        assert "transient stages" in note and "initial" in note, note
        assert gw.transient_initial_bcs is None
        assert [s.get("bcs") for s in gw.transient_stages] == [None, None]
        assert [s["time"] for s in gw.transient_stages] == [10.0, 20.0]
        assert gw.transient_stages[1]["calculate_sf"]

    def test_undo_brings_them_back_with_the_old_mesh(self):
        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "mesh_generate", project_id=pid, target_elements=200)
        call(ws, "seepage_bc_set", project_id=pid,
             reservoir={"level": 8.0, "side": "left"})
        call(ws, "transient_set", project_id=pid,
             stages=[{"time": 10.0, "bcs": "current"}])
        before = _state(ws, pid)
        call(ws, "mesh_generate", project_id=pid, target_elements=500)
        call(ws, "project_history", project_id=pid, action="undo")
        assert _state(ws, pid) == before


# ======================================================================
# Refusals change nothing
# ======================================================================
class TestRefusalsChangeNothing:
    def test_running_needs_a_mesh_and_conditions(self):
        from ogr_api import Conflict, NotConfigured, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": K})
        with pytest.raises(NotConfigured):
            call(ws, "groundwater_run", project_id=pid)
        call(ws, "mesh_generate", project_id=pid, target_elements=100)
        with pytest.raises(NotConfigured):
            call(ws, "groundwater_run", project_id=pid)
        call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
             side="left", value=12.0)
        with pytest.raises(Conflict):
            call(ws, "groundwater_run", project_id=pid,
                 methods=["spencer"])

    def test_conditions_are_checked_against_what_is_read(self):
        from ogr_api import Conflict, InvalidArgument, NotFound, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "mesh_generate", project_id=pid, target_elements=100)
        before = _state(ws, pid)
        for kw, exc in (
                (dict(bc_type="total_head", side="left", nodes=[0],
                      value=1.0), InvalidArgument),
                (dict(bc_type="total_head", side="left"), InvalidArgument),
                (dict(bc_type="unknown", side="left", value=1.0),
                 Conflict),
                (dict(bc_type="total_head", side="left", value=1.0,
                      seepage_face=True), Conflict),
                (dict(reservoir={"level": -5.0}), Conflict),
                (dict(bc_type="nodal_flow", value=0.0,
                      along=[[5, 5], [6, 5]]), Conflict),
                (dict(bc_type="total_head", side="top", value=1.0),
                 NotFound)):
            with pytest.raises(exc):
                call(ws, "seepage_bc_set", project_id=pid, **kw)
            assert _state(ws, pid) == before, kw

    def test_infiltration_needs_a_boundary_edge(self):
        from ogr_api import Conflict, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        call(ws, "mesh_generate", project_id=pid, target_elements=100)
        mesh = ws.get(pid).project.fem_mesh
        lone = sorted(mesh.boundary_node_ids())[:1]
        with pytest.raises(Conflict):
            call(ws, "seepage_bc_set", project_id=pid,
                 bc_type="infiltration", nodes=lone, value=1e-7)
        out = call(ws, "seepage_bc_set", project_id=pid,
                   bc_type="infiltration", side="ground", value=1e-7)
        n = out["conditions"]["infiltration_segments"]
        # Twice does not double it (v0.1.200: an edge is replaced).
        again = call(ws, "seepage_bc_set", project_id=pid,
                     bc_type="infiltration", side="ground", value=1e-7)
        assert again["conditions"]["infiltration_segments"] == n > 0

    def test_transient_checks_are_the_cores(self):
        from ogr_api import InvalidArgument, call
        ws = _ws()
        pid = _box(ws, 20, 10)
        before = _state(ws, pid)
        for stages in ([{"time": 5.0}, {"time": 5.0}], [{"time": -1.0}],
                       []):
            with pytest.raises(InvalidArgument):
                call(ws, "transient_set", project_id=pid, stages=stages)
            assert _state(ws, pid) == before

    def test_reading_needs_a_field_and_the_right_view(self):
        from ogr_api import Conflict, NotFound, call
        ws, pid, *_ = _darcy()
        with pytest.raises(Conflict):
            call(ws, "groundwater_results", project_id=pid,
                 view="point", point_xy=[50.0, 5.0])
        with pytest.raises(Conflict):
            call(ws, "groundwater_results", project_id=pid,
                 section=[[1, 1], [2, 2]])
        with pytest.raises(Conflict):
            call(ws, "groundwater_results", project_id=pid, stage=0,
                 view="summary")
        ws2 = _ws()
        pid2 = _box(ws2, 20, 10)
        with pytest.raises(NotFound):
            call(ws2, "groundwater_results", project_id=pid2)


# ======================================================================
# The pressure grid
# ======================================================================
class TestTheWaterGrid:
    def test_points_a_file_and_what_would_not_be_read(self):
        import tempfile

        from ogr_api import call
        ws = _ws()
        pid = _box(ws, 20, 10)
        out = call(ws, "water_grid_set", project_id=pid,
                   points=[[0, 0, 50.0], [20, 0, 40.0], [10, 10, 0.0]])
        assert out["points"] == 3
        assert any("grid_*" in n for n in out["notes"]), out
        folder = Path(tempfile.mkdtemp(prefix="ogr_grid_"))
        f = folder / "grid.csv"
        f.write_text("x;y;u\n0;0;50\n20;0;40\n10;10;0\n5;5;20\n",
                     encoding="utf-8")
        out = call(ws, "water_grid_set", project_id=pid, csv_path=str(f),
                   idw_neighbours=4)
        assert out["points"] == 4 and out["idw_neighbours"] == 4
        assert any("only read when the TPS falls back" in n
                   for n in out["notes"]), out
        call(ws, "water_grid_delete", project_id=pid)
        assert ws.get(pid).project.water_pressure_grid is None


# ======================================================================
# The model notes ask the engine which water surface a material uses
# ======================================================================
class TestTheWaterNoteAsksTheEngine:
    def test_a_material_without_a_surface_of_its_own_uses_the_first(self):
        """The engine's ``resolve_water_surface`` falls back to the first
        water table; the note said such a table "produces no pore
        pressure" while the analysis gave it pore pressure."""
        import test_drawdown_sweep_v170 as dd
        from ogr_api import call
        from ogr_core.hydraulic.water_surfaces import materials_using_surface
        ws = _ws()
        p = dd._homogeneous()
        pid = ws.add(p).id
        wt = next(b for b in p.boundaries if b.btype.name == "WATER_TABLE")
        assert p.materials[0].water_surface_id is None
        assert materials_using_surface(p, wt) == [p.materials[0]]
        notes = call(ws, "project_validate", project_id=pid)["model_notes"]
        assert not any("assigned to no material" in n for n in notes), notes


# ======================================================================
# The interface
# ======================================================================
def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


class TestTheInterface:
    def test_the_bc_dialog_edits_a_copy(self):
        if _qt() is None:
            return
        from ogr_core.project import Project
        from ogr_gui.main_window import MainWindow
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = _box(ws, 20, 10)
            project = ws.get(pid).project
        finally:
            ws.shutdown()
        project.fem_mesh = generate_mesh_for_project(project,
                                                     target_elements=100)
        w = MainWindow()
        try:
            w._attach_project(project)
            first = w._seepage_bcs()
            # Asking wrote nothing: the defaults are not stored.
            assert project.seepage_bcs is None
            project.seepage_bcs = first
            copy = w._seepage_bcs()
            assert copy is not project.seepage_bcs
            assert copy.to_dict() == project.seepage_bcs.to_dict()
            assert isinstance(project, Project)
        finally:
            w.close()
            w.deleteLater()

    def test_the_initial_capture_waits_for_ok(self):
        if _qt() is None:
            return
        from PySide6.QtWidgets import QMessageBox

        from ogr_core.project.settings import GroundwaterSettings
        from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        bcs = SeepageBoundaryConditions()
        bcs.add_node(0, BCType.TOTAL_HEAD, 3.0)
        gw = GroundwaterSettings()
        raw = QMessageBox.information
        QMessageBox.information = staticmethod(lambda *a, **k: None)
        try:
            dlg = TransientStagesDialog(gw, current_bcs=bcs)
            dlg._capture_initial()
            assert gw.transient_initial_bcs is None
            dlg.reject()
            assert gw.transient_initial_bcs is None
            dlg = TransientStagesDialog(gw, current_bcs=bcs)
            dlg._add_row(5.0, False, "")
            dlg.chk_enabled.setChecked(True)
            dlg._capture_initial()
            dlg._accept()
            assert gw.transient_initial_bcs == bcs.to_dict()
        finally:
            QMessageBox.information = raw

    def test_deleting_a_stage_keeps_the_others_conditions(self):
        if _qt() is None:
            return
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        gw = GroundwaterSettings()
        gw.set_transient(True, [{"time": 1.0, "bcs": {"nodes": [1]}},
                                {"time": 2.0, "bcs": {"nodes": [2]}},
                                {"time": 3.0, "bcs": {"nodes": [3]}}])
        dlg = TransientStagesDialog(gw)
        dlg.table.selectRow(1)
        dlg._delete()
        got = [(s["time"], s.get("bcs")) for s in dlg.stages()]
        assert got == [(1.0, {"nodes": [1]}), (3.0, {"nodes": [3]})], got

    def test_the_interpret_window_has_a_solver_after_reopening(self):
        from ogr_core.project import Project
        from ogr_slip2d.transient_stability import groundwater_query_solver
        ws, pid, _run = _dam()
        project = ws.get(pid).project
        reopened = Project.from_dict(json.loads(json.dumps(
            project.to_dict())))
        solver = groundwater_query_solver(reopened)
        assert solver is not None
        fs = solver.free_surface_points(reopened.seepage_result)
        ref = groundwater_query_solver(project).free_surface_points(
            project.seepage_result)
        # Nine significant digits per head in the file: equal to 1e-6 m.
        assert fs and len(fs) == len(ref)
        assert max(abs(a - c) for p, q in zip(fs, ref)
                   for a, c in zip(p, q)) < 1e-6
