# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.492 (D429) -- a ``.ogr`` value this build does not know is refused,
not replaced by another one.

Invariant protected: the eight cases of D429, each one value of the JSON
changed, are refused with a code -- at opening the six of the core
(ogr-core 0.2.11), by ``check_analysis_settings`` the two of the engine
(v0.1.491) -- and never read as the value that used to stand in for them;
the agent receives the refusal of a unit weight ``"x"`` as an
``InvalidArgument`` of ``project_open``; and what is MISSING still migrates
as before (absence is not "unknown").

Why (rule 7). The permeability became constant, an envelope vanished, a
grid of an unknown interpolation was read by IDW (1.5745 at (3, 3) where TPS
gives 1.9), an unknown acceleration unit became g, an unknown search ran as
a Grid Search and an unknown sampling as Monte Carlo -- another number,
said nowhere. A weight ``"x"`` opened and failed only when computed. The
references are the enumerations of each value, not a capture. The bank
holds none of these (census of 2026-11-24: 0 of 30 800 ``.ogr``).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

_BASE: dict = {}


def _base() -> dict:
    """The demo with every section the eight cases change, as its JSON."""
    if not _BASE:
        from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties
        from ogr_core.hydraulic.water_pressure_grid import WaterPressureGrid
        from ogr_core.loads.seismic_record import SeismicRecord
        from ogr_core.materials.drawdown_envelopes import REnvelope
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        p.materials[0].hydraulic = HydraulicProperties()
        p.materials[0].drawdown_envelope = REnvelope(c_r=1.0, phi_r_deg=20.0)
        p.water_pressure_grid = WaterPressureGrid(
            points=[(0.0, 0.0, 1.0), (10.0, 0.0, 2.0), (0.0, 10.0, 3.0)])
        p.seismic_records = [SeismicRecord(name="r", dt=0.01,
                                           accelerations=[0.0, 0.1, 0.0])]
        _BASE.update(json.loads(json.dumps(p.to_dict())))
    return _BASE


def _changed(where, key, value, *, delete=False) -> dict:
    d = copy.deepcopy(_base())
    t = d
    for k in where:
        t = t[k]
    if delete:
        t.pop(key, None)
    else:
        t[key] = value
    return d


def _refusal(d):
    """The exception ``Project.from_dict`` refuses ``d`` with."""
    from ogr_core.project import Project
    try:
        Project.from_dict(d)
    except ValueError as exc:
        return exc
    raise AssertionError("it opened")


def _code(exc):
    return getattr(exc, "code", None) or getattr(
        exc.args[0] if exc.args else None, "code", None)


#: (where, key, value, code): the six the core refuses at opening
_AT_OPENING = (
    (["materials", 0, "hydraulic"], "model", "future_model",
     "file.enum_unknown"),
    (["materials", 0, "drawdown_envelope"], "kind", "future",
     "file.value_unknown"),
    (["water_pressure_grid"], "interpolation", "kriging",
     "file.value_unknown"),
    (["seismic_records", 0], "source_unit", "furlongs", "file.enum_unknown"),
    (["materials", 0], "unit_weight", "x", "file.field_type"),
    (["materials", 0], "name", 5, "file.field_type"),
)


class TestRefusedAtOpening:
    def test_each_unknown_value_is_refused_with_its_code(self):
        for where, key, value, code in _AT_OPENING:
            exc = _refusal(_changed(where, key, value))
            assert _code(exc) == code, (key, value, _code(exc), exc)

    def test_a_null_name_is_refused(self):
        exc = _refusal(_changed(["materials", 0], "name", None))
        assert _code(exc) == "file.field_type", exc

    def test_the_refusals_name_what_is_known(self):
        """The reference: the values of each enumeration, all of them."""
        from ogr_core.hydraulic.hydraulic_properties import PermeabilityModel
        from ogr_core.loads.seismic_record import AccelerationUnit
        texts = {key: str(_refusal(_changed(where, key, value)))
                 for where, key, value, _c in _AT_OPENING}
        assert "'future_model'" in texts["model"]
        assert PermeabilityModel.__name__ in texts["model"]
        assert "'furlongs'" in texts["source_unit"]
        assert AccelerationUnit.__name__ in texts["source_unit"]
        assert texts["kind"].endswith("Known: r, kc1"), texts["kind"]
        assert texts["interpolation"].endswith("Known: tps, idw")

    def test_what_is_missing_still_migrates(self):
        from ogr_core.hydraulic.hydraulic_properties import PermeabilityModel
        from ogr_core.loads.seismic_record import AccelerationUnit
        from ogr_core.project import Project
        p = Project.from_dict(_changed(["materials", 0, "hydraulic"],
                                       "model", None, delete=True))
        assert p.materials[0].hydraulic.model is PermeabilityModel.CONSTANT
        p = Project.from_dict(_changed(["water_pressure_grid"],
                                       "interpolation", None, delete=True))
        assert p.water_pressure_grid.interpolation == "tps"
        p = Project.from_dict(_changed(["seismic_records", 0],
                                       "source_unit", None, delete=True))
        assert p.seismic_records[0].source_unit is AccelerationUnit.G
        p = Project.from_dict(_changed(["materials", 0],
                                       "drawdown_envelope", None, delete=True))
        assert p.materials[0].drawdown_envelope is None

    def test_every_known_value_opens(self):
        from ogr_core.hydraulic.hydraulic_properties import PermeabilityModel
        from ogr_core.loads.seismic_record import AccelerationUnit
        from ogr_core.project import Project
        for m in PermeabilityModel:
            Project.from_dict(_changed(["materials", 0, "hydraulic"],
                                       "model", m.value))
        for u in AccelerationUnit:
            Project.from_dict(_changed(["seismic_records", 0],
                                       "source_unit", u.value))
        for i in ("tps", "idw"):
            Project.from_dict(_changed(["water_pressure_grid"],
                                       "interpolation", i))
        for w in (20, 20.0):
            Project.from_dict(_changed(["materials", 0], "unit_weight", w))


class TestRefusedBeforeComputing:
    """The two of the engine (v0.1.491): they open, and do not run."""

    def test_search_and_sampling(self):
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = Project.from_dict(_changed(["settings", "search"],
                                       "search_method", "future_search"))
        codes = [getattr(x, "code", None) for x in check_analysis_settings(p)]
        assert "setting.search_unknown" in codes, codes
        d = _changed(["settings", "statistics"], "sampling_method",
                     "future_sampling")
        d["settings"]["statistics"]["probabilistic_analysis"] = True
        codes = [getattr(x, "code", None)
                 for x in check_analysis_settings(Project.from_dict(d))]
        assert "setting.sampling_unknown" in codes, codes


class TestTheAgent:
    def test_a_weight_that_is_not_a_number_is_an_invalid_argument(
            self, tmp_path):
        from ogr_api import InvalidArgument, Workspace, call
        path = Path(tmp_path) / "peso.ogr"
        path.write_text(json.dumps(_changed(["materials", 0], "unit_weight",
                                            "x")), encoding="utf-8")
        ws = Workspace()
        try:
            call(ws, "project_open", path=str(path))
        except InvalidArgument as exc:
            assert "must be a number, not a string" in str(exc), exc
        else:
            raise AssertionError("project_open opened it")
        finally:
            ws.shutdown()
