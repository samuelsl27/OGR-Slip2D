# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.340 (D337, first part) — the core does not import the layers above it.

AGENTS.md fixes the layers in one direction, ``ogr_core → ogr_slip2d /
ogr_fem2d → ogr_api → {ogr_gui, ogr_cli, ogr_mcp}``, and until this version
nothing enforced it for the core: ``test_api_layering_pyexec_v1194`` only
banned ``ogr_api`` from it. Ticket D337 named one place where the core
reached up into the engine — the DXF exporter — and the census this file
makes found twenty statements in seven files, all of them imports inside a
function, which is why nothing failed at import time.

The invariants:

* **the census is exact.** Every import in ``ogr_core`` of ``ogr_slip2d``,
  ``ogr_fem2d``, ``ogr_api``, ``ogr_gui``, ``ogr_cli``, ``ogr_mcp``,
  ``PySide6``, ``mcp`` or ``importlib``, and every ``__import__`` call —
  inside functions, classes and ``TYPE_CHECKING`` blocks too — is a
  ``(file, enclosing function, module)`` entry of :data:`ALLOWED`, as many
  times as it is written. A new one fails, and so does an entry that no
  longer matches anything: each version of the D337 batch deletes the
  entries it removes, so the list only shrinks, and it is empty when D337
  closes (v0.1.346);
* **the census sees what it must**: a module written here with one import
  of each kind is found whole, so an empty census means no import and not
  a blind scanner;
* this version removes two: ``results_io`` names ``SearchResult`` as a
  string annotation only, and building an ``OptimizeSettings`` from the
  project's settings is the engine's (``ogr_slip2d.optimize.
  settings_from_project`` and ``optimize_kwargs``), no longer a method of
  ``ProjectSettings``.
"""
from __future__ import annotations

import ast
import tempfile
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

#: The layers above the core, and the two ways around an import statement.
BANNED = frozenset({"ogr_slip2d", "ogr_fem2d", "ogr_api", "ogr_gui",
                    "ogr_cli", "ogr_mcp", "PySide6", "mcp", "importlib"})
DYNAMIC = "__import__"

#: ``(file, enclosing function, module)``: how many times it is written.
#: Only shrinks. Each version of the D337 batch removes its own entries.
ALLOWED = Counter({
    # the stored data classes (v0.1.342, v0.1.343)
    ("ogr_core/project/project.py", "Project.from_dict", "ogr_fem2d"): 3,
    ("ogr_core/project/project.py", "Project.from_dict", "ogr_slip2d"): 2,
    # the soil columns and their switch (v0.1.344)
    ("ogr_core/hydraulic/excess_pore_pressure.py", "_loading_bands",
     "ogr_slip2d"): 1,
    ("ogr_core/hydraulic/excess_pore_pressure.py", "load_delta_sigma_v",
     "ogr_slip2d"): 2,
    ("ogr_core/support/bond.py", "sigma_v_effective_at", "ogr_slip2d"): 2,
    ("ogr_core/support/bond.py", "_layer_top_at", "ogr_slip2d"): 1,
    # the local strength of an envelope (v0.1.345)
    ("ogr_core/support/bond.py", "equivalent_c_phi_at", "ogr_slip2d"): 1,
    # the statistical runners (v0.1.346)
    ("ogr_core/statistics/probabilistic.py",
     "_critical_probabilistic_excluded", "ogr_slip2d"): 1,
    ("ogr_core/statistics/probabilistic.py",
     "_does_not_reevaluate_to_itself", "ogr_slip2d"): 1,
    ("ogr_core/statistics/probabilistic.py", "_evaluate_on",
     "ogr_slip2d"): 1,
    ("ogr_core/statistics/probabilistic.py", "_rebuild_surface",
     "ogr_slip2d"): 1,
    ("ogr_core/statistics/probabilistic.py", "_sample_failure",
     "ogr_slip2d"): 1,
    ("ogr_core/statistics/probabilistic.py", "run_global_minimum",
     "ogr_slip2d"): 1,
    ("ogr_core/statistics/sensitivity.py", "run_sensitivity",
     "ogr_slip2d"): 1,
})


def census_of(path: Path, root: Path) -> Counter:
    """The banned imports of one file, by enclosing function."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rel = path.relative_to(root).as_posix()
    found: Counter = Counter()

    def visit(node, where):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                visit(child, where + [child.name])
                continue
            modules = []
            if isinstance(child, ast.Import):
                modules = [a.name.split(".")[0] for a in child.names]
            elif (isinstance(child, ast.ImportFrom) and child.level == 0
                  and child.module):
                modules = [child.module.split(".")[0]]
            elif (isinstance(child, ast.Call)
                  and isinstance(child.func, ast.Name)
                  and child.func.id == DYNAMIC):
                modules = [DYNAMIC]
            for module in modules:
                if module in BANNED or module == DYNAMIC:
                    found[(rel, ".".join(where) or "<module>", module)] += 1
            visit(child, where)

    visit(tree, [])
    return found


def core_census() -> Counter:
    found: Counter = Counter()
    for path in sorted((_ROOT / "ogr_core").rglob("*.py")):
        found.update(census_of(path, _ROOT))
    return found


# ======================================================================
class TestTheCoreImportsNoLayerAbove:

    def test_the_census_is_the_allowed_list_exactly(self):
        found = core_census()
        new = found - ALLOWED
        gone = ALLOWED - found
        assert not new, ("imports of an upper layer not in the list", new)
        assert not gone, ("entries that match nothing any more: delete "
                          "them", gone)

    def test_the_census_sees_every_kind_of_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "ogr_core" / "x"
            pkg.mkdir(parents=True)
            (pkg / "m.py").write_text(
                "from __future__ import annotations\n"
                "from typing import TYPE_CHECKING\n"
                "import os\n"
                "from . import sibling\n"
                "if TYPE_CHECKING:\n"
                "    from ogr_slip2d.search import SearchResult\n"
                "class K:\n"
                "    def f(self):\n"
                "        import ogr_fem2d.mesh as m\n"
                "        return __import__('ogr_api')\n"
                "def g():\n"
                "    import importlib\n"
                "    from PySide6.QtWidgets import QWidget\n",
                encoding="utf-8")
            found = census_of(pkg / "m.py", root)
        assert found == Counter({
            ("ogr_core/x/m.py", "<module>", "ogr_slip2d"): 1,
            ("ogr_core/x/m.py", "K.f", "ogr_fem2d"): 1,
            ("ogr_core/x/m.py", "K.f", DYNAMIC): 1,
            ("ogr_core/x/m.py", "g", "importlib"): 1,
            ("ogr_core/x/m.py", "g", "PySide6"): 1,
        }), found


# ======================================================================
class TestWhatThisVersionMoved:

    def test_results_io_names_the_type_without_importing_it(self):
        found = census_of(_ROOT / "ogr_core" / "project" / "results_io.py",
                          _ROOT)
        assert found == Counter()

    def test_the_optimisation_settings_are_built_by_the_engine(self):
        from ogr_core.project.settings import ProjectSettings
        from ogr_slip2d.optimize import (OptimizeSettings, optimize_kwargs,
                                         settings_from_project)
        assert not hasattr(ProjectSettings, "optimize_settings")
        assert not hasattr(ProjectSettings, "optimize_kwargs")
        s = ProjectSettings()
        s.search.optimize_max_iterations = 77
        s.search.optimize_max_concave_angle_enabled = False
        s.search.optimize_snap_shallow_to_slope = True
        s.search.optimize_snap_specify_distance = True
        s.search.optimize_snap_distance = 2.5
        o = settings_from_project(s)
        assert isinstance(o, OptimizeSettings) and o.enabled
        assert o.max_iterations == 77
        # unticked: concave angles are not allowed, a limit of zero
        assert o.max_concave_angle_deg == 0.0
        assert o.snap_distance == 2.5
        s.search.optimize_enabled = False
        assert optimize_kwargs(s) == {"optimize": None}
        s.search.optimize_enabled = True
        assert optimize_kwargs(s) == {"optimize": settings_from_project(s)}
