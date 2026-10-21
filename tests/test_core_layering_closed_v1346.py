# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.346 (D337, closed) — the core imports none of the layers above it,
read from the source and measured at run time.

The last entries of the census were the statistical runners,
``ogr_core/statistics/probabilistic.py`` and ``sensitivity.py``: they run
the engine (a search per sample, the method's re-evaluation, the engine's
surfaces), so they moved up, whole, to ``ogr_slip2d``. Whole, because tests
patch their module globals, and a patch in one half of a split module would
not reach the other — the trap of the switch of v0.1.344 again.

The invariants:

* **the old paths fail loudly, with the new one**: importing
  ``ogr_core.statistics.probabilistic`` or ``.sensitivity``, or one of their
  names from ``ogr_core.statistics``, raises an ``ImportError`` that says
  where it went — never a re-export, which would be the core importing the
  engine;
* what is pure stays where it was: the distributions, the random variables
  and the drawdown sweep;
* **at run time**: in a fresh interpreter, importing every module of the
  core, loading a model with a mesh, a seepage field, focus objects and user
  circles, and computing what the core computes for the engine (the
  effective stress and the equivalent strength along a support, the stress
  of the loads, a DXF with a critical surface) leaves no module of
  ``ogr_slip2d``, ``ogr_fem2d``, ``ogr_api``, ``ogr_gui``, ``ogr_cli``,
  ``ogr_mcp``, ``PySide6`` or ``mcp`` in ``sys.modules``;
* the census of ``test_core_layering_v1340`` is empty (it asserts so itself).
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_BANNED = ("ogr_slip2d", "ogr_fem2d", "ogr_api", "ogr_gui", "ogr_cli",
           "ogr_mcp", "PySide6", "mcp")
_STUBS = ("ogr_core.statistics.probabilistic",
          "ogr_core.statistics.sensitivity")


# ======================================================================
class TestTheOldPathsFailLoudly:

    def test_the_two_modules(self):
        for name, new in zip(_STUBS, ("ogr_slip2d.probabilistic",
                                      "ogr_slip2d.sensitivity")):
            sys.modules.pop(name, None)
            try:
                importlib.import_module(name)
            except ImportError as exc:
                assert new in str(exc), exc
            else:
                raise AssertionError(name + " imported")

    def test_a_moved_name_from_the_package(self):
        for name, new in (("run_global_minimum", "ogr_slip2d.probabilistic"),
                          ("run_sensitivity", "ogr_slip2d.sensitivity"),
                          ("ProbabilisticType", "ogr_slip2d.probabilistic")):
            try:
                exec("from ogr_core.statistics import " + name, {})
            except ImportError as exc:
                assert new in str(exc), exc
            else:
                raise AssertionError(name + " imported from the core")

    def test_the_new_paths_and_what_stays(self):
        from ogr_core.statistics import (RandomVariable, SamplingMethod,
                                         run_drawdown_sweep)
        from ogr_slip2d.probabilistic import (ProbabilisticType,
                                              run_global_minimum,
                                              run_overall_slope,
                                              sample_pairs)
        from ogr_slip2d.sensitivity import run_sensitivity
        assert callable(run_global_minimum) and callable(run_sensitivity)
        assert run_overall_slope.__module__ == "ogr_slip2d.probabilistic"
        assert RandomVariable and SamplingMethod and run_drawdown_sweep
        assert ProbabilisticType and sample_pairs


# ======================================================================
_SCRIPT = r'''
import json, pkgutil, sys, tempfile, pathlib, importlib
import ogr_core
stubs = set(json.loads(sys.argv[2]))
names = []
for info in pkgutil.walk_packages(ogr_core.__path__, "ogr_core."):
    if info.name in stubs:
        continue
    importlib.import_module(info.name)
    names.append(info.name)
from ogr_core.project import Project
from ogr_core.dxf.exporter import ExportOptions, export_dxf
from ogr_core.hydraulic.excess_pore_pressure import load_delta_sigma_v
from ogr_core.support.bond import equivalent_c_phi_at, sigma_v_effective_at
p = Project.load(sys.argv[1])
xmin, ymin, xmax, ymax = p.bounding_box()
x, y = 0.5 * (xmin + xmax), ymin + 0.3 * (ymax - ymin)
sigma_v_effective_at(p, x, y)
equivalent_c_phi_at(p, x, y, 50.0)
load_delta_sigma_v(p, x)
out = pathlib.Path(tempfile.mkdtemp()) / "x.dxf"
rep = export_dxf(p, out, ExportOptions(unit="m"),
                 [("m", [(xmin, ymax), (x, y), (xmax, ymax)], 1.2)])
loaded = sorted(m for m in sys.modules
                if m.split(".")[0] in json.loads(sys.argv[3]))
print(json.dumps({"modules": len(names), "loaded": loaded,
                  "mesh": p.fem_mesh is not None,
                  "focus": len(p.focus_objects),
                  "circles": len(p.user_surfaces),
                  "dxf": rep.ok}))
'''


class TestAtRunTime:

    def test_the_whole_core_without_the_layers_above(self):
        import test_focus_circle_in_core_v1343 as F
        p = F._project()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_core_"))
        path = tmp / "model.ogr"
        try:
            p.save(path)
            env = dict(os.environ, PYTHONPATH=str(_ROOT),
                       QT_QPA_PLATFORM="offscreen")
            out = subprocess.run(
                [sys.executable, "-c", _SCRIPT, str(path),
                 json.dumps(list(_STUBS)), json.dumps(list(_BANNED))],
                cwd=str(_ROOT), env=env, capture_output=True, text=True,
                timeout=600)
        finally:
            path.unlink(missing_ok=True)
            tmp.rmdir()
        assert out.returncode == 0, out.stderr
        got = json.loads(out.stdout.strip().splitlines()[-1])
        assert got["loaded"] == [], got["loaded"]
        assert got["modules"] > 80, got["modules"]
        assert got["mesh"] and got["focus"] == 2 and got["circles"] == 1
        assert got["dxf"]
