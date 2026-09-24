# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — a model built by an agent gives the published number.

Invariant protected: a model built FROM SCRATCH through the operations
layer (``ogr_api``) — the path an AI agent drives — reproduces published
reference results, through the same configured analysis a user gets.

Why this is the risk and not the arithmetic. The operations layer adds no
formula; what it adds is a SECOND WAY TO REACH THE ENGINE: a declarative
model spec, settings set by dotted path, the analysis in a child process,
the result read back as JSON. Any of those can land on a different model
or a different configuration from the one validated, and the number would
still look plausible. So the check is rule 1 with the new door: an external
reference, not a snapshot of what the layer prints.

References, imported from the files that validate the engine directly,
never re-typed:

* ACADS 1(a), Giam & Donald (1989): mean of 33 programs 0.991, ±2 %
  (``test_acads_validation_v178._MEAN_33`` / ``_TOL``).
* Ej_1 reference run: the six methods on their published critical circles,
  0.5 % (``test_slide_validation_ej1.TestAllMethodsValidationEj1._REF``),
  and the published grid (``_GRID``, ``_EXPECTED_TOTAL``) finding the
  published critical centre and radius. The radii are quoted from that
  file's docstring, where they are literals too.

THE TOLERANCE IS SET EXPLICITLY, AND THAT IS A FINDING (v0.1.194, reported
and not changed). ``test_slide_validation_ej1`` builds ``Spencer()`` and
``GLEMorgensternPrice()`` with the CLASS default tolerance, 0.001. A
project carries ``methods.tolerance = 0.005``, and through the configured
path Spencer on its published circle comes out +0.556 % — outside the
0.5 % the direct test holds it to (0.001 gives +0.343 %, 1e-4 +0.306 %;
GLE 0.389 / 0.158 / 0.109 %). So the Ej_1 validation measures a
configuration no user gets by default. This file sets 0.001 through
``settings_set`` to compare like with like, and says so here rather than
hiding it in a helper.

If a case here fails, NOTHING is tuned: it means the operations layer and
the validated path have diverged, and that is the report.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_acads_validation_v178 as acads  # noqa: E402
import test_slide_validation_ej1 as ej1  # noqa: E402

_CACHE: dict = {}

# Published critical radii (test_slide_validation_ej1.py, docstring lines
# 12-13: "R = 47.2124436" and "R = 41.5014358").
_BISHOP = (88.0, 70.5, 47.2124436, 0.882889)
_JANBU = (84.0, 66.0, 41.5014358, 0.842548)


def _ws():
    from ogr_api import Workspace
    return Workspace()


def _acads_spec() -> dict:
    """ACADS 1(a) exactly as ``acads._acads_1a`` builds it, as a spec."""
    return {
        "name": "ACADS 1(a)",
        "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                     [20, 25]],
        "materials": [{"name": "Soil", "unit_weight": 20.0, "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": 3.0, "friction_angle": 19.6}}}],
    }


def _ej1_spec(extra_settings=None) -> dict:
    """Ej_1 as ``ej1._ej1_project`` builds it: three layers, painted at
    one interior point each."""
    settings = {"units.failure_direction": "L2R",
                "methods.tolerance": 0.001}
    settings.update(extra_settings or {})

    def mc(c, phi):
        return {"model": "mohr_coulomb",
                "params": {"cohesion": c, "friction_angle": phi}}

    return {
        "name": "Ej_1",
        "external": [[120, 0], [120, 25], [75, 25], [50, 50], [0, 50],
                     [0, 30], [0, 20], [0, 0]],
        "material_boundaries": [[[0, 30], [75, 25]], [[0, 20], [120, 10]]],
        "materials": [
            {"name": "Mat1", "unit_weight": 20, "strength": mc(15, 25),
             "at": [30, 40]},
            {"name": "Mat2", "unit_weight": 20, "strength": mc(10, 25),
             "at": [30, 22]},
            {"name": "Mat3", "unit_weight": 20, "strength": mc(19, 30),
             "at": [30, 5]},
        ],
        "settings": settings,
    }


def _acads_run():
    """The problem's grid: 20 x 20 intervals and 11 circles per point."""
    if "acads" not in _CACHE:
        from ogr_api import call
        ws = _ws()
        try:
            pid = call(ws, "project_new", name="ACADS")["project_id"]
            call(ws, "model_define", project_id=pid, spec=_acads_spec())
            (x0, x1), (y0, y1) = acads._GRID["grid_x"], acads._GRID["grid_y"]
            call(ws, "settings_set", project_id=pid, changes={
                "methods.enabled_methods": ["bishop_simplified"],
                "search.grid_x_min": x0, "search.grid_x_max": x1,
                "search.grid_y_min": y0, "search.grid_y_max": y1,
                "search.grid_nx": 20, "search.grid_ny": 20,
                "search.radius_increment": 10,
                "search.min_area": acads._GRID["min_area"]})
            _CACHE["acads"] = call(ws, "analysis_run", project_id=pid,
                                   wait_seconds=600)
        finally:
            ws.shutdown()
    return _CACHE["acads"]


def _ej1_grid_run():
    if "ej1" not in _CACHE:
        from ogr_api import call
        g = ej1._GRID
        ws = _ws()
        try:
            pid = call(ws, "project_new", name="Ej_1")["project_id"]
            call(ws, "model_define", project_id=pid, spec=_ej1_spec({
                "methods.enabled_methods": ["bishop_simplified",
                                            "janbu_simplified"],
                "search.grid_x_min": g["grid_x"][0],
                "search.grid_x_max": g["grid_x"][1],
                "search.grid_y_min": g["grid_y"][0],
                "search.grid_y_max": g["grid_y"][1],
                "search.grid_nx": g["grid_nx"],
                "search.grid_ny": g["grid_ny"],
                "search.radius_increment": g["radius_increment"],
                "search.min_area": g["min_area"]}))
            _CACHE["ej1"] = call(ws, "analysis_run", project_id=pid,
                                 wait_seconds=600)
        finally:
            ws.shutdown()
    return _CACHE["ej1"]


def _method(run, mid):
    return next(m for m in run["summary"]["methods"]
                if m["method_id"] == mid)


# ======================================================================
class TestAcadsBuiltByOperations:
    def test_the_run_finishes(self):
        assert _acads_run()["state"] == "done", _acads_run()

    def test_bishop_is_within_the_published_band(self):
        m = _method(_acads_run(), "bishop_simplified")
        err = abs(m["value"] - acads._MEAN_33) / acads._MEAN_33
        assert err < acads._TOL, f"FoS={m['value']} err={err * 100:.2f}%"

    def test_it_is_a_factor_of_safety_and_not_something_else(self):
        m = _method(_acads_run(), "bishop_simplified")
        assert m["caption"] == "fos"
        assert m["unit"] == "-"

    def test_the_population_is_the_one_asked_for(self):
        """(nx+1)(ny+1)(r+1) = 21 x 21 x 11, the identity every grid
        search satisfies — an identity, not a count copied from a run."""
        c = _method(_acads_run(), "bishop_simplified")["counts"]
        assert c["attempted"] == (20 + 1) * (20 + 1) * (10 + 1) == 4851
        assert c["total"] == c["valid"] + c["invalid"]


class TestEj1BuiltByOperations:
    def test_every_method_on_its_published_circle(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = call(ws, "project_new", name="Ej_1")["project_id"]
            call(ws, "model_define", project_id=pid, spec=_ej1_spec())
            for mid, cx, cy, r, ref, tol in \
                    ej1.TestAllMethodsValidationEj1._REF:
                out = call(ws, "surface_evaluate", project_id=pid,
                           methods=[mid],
                           surface={"type": "circle", "centre_x": cx,
                                    "centre_y": cy, "radius": r})
                fos = out["methods"][mid]["fos"]
                err = abs(fos - ref) / ref * 100
                assert err < tol, f"{mid}: FS={fos:.5f} err={err:.3f}%"
        finally:
            ws.shutdown()

    def test_the_grid_is_the_published_population(self):
        run = _ej1_grid_run()
        assert run["state"] == "done", run
        for mid in ("bishop_simplified", "janbu_simplified"):
            assert _method(run, mid)["counts"]["total"] == \
                ej1._EXPECTED_TOTAL

    def test_the_grid_finds_the_published_critical_circles(self):
        run = _ej1_grid_run()
        for mid, (cx, cy, r, ref) in (("bishop_simplified", _BISHOP),
                                      ("janbu_simplified", _JANBU)):
            m = _method(run, mid)
            s = m["critical"]["surface"]
            assert abs(s["centre_x"] - cx) < 1e-6, (mid, s)
            assert abs(s["centre_y"] - cy) < 1e-6, (mid, s)
            assert abs(s["radius"] - r) < 1e-3, (mid, s)
            err = abs(m["value"] - ref) / ref * 100
            assert err < 0.5, f"{mid}: FS={m['value']} err={err:.3f}%"
