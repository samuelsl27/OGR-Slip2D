# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — the layers stay in their order, and scripts are
contained.

Invariants protected:

* **Layering**, read from the source with the AST, not from what happens
  to be importable: ``ogr_api`` imports neither PySide6, nor ``ogr_gui``,
  nor ``mcp``/``ogr_mcp`` (it must run headless and without the MCP SDK);
  the engine (``ogr_core``, ``ogr_slip2d``, ``ogr_fem2d``) never imports
  ``ogr_api``; and ``ogr_core/project/rules.py`` imports neither Qt nor
  the solver. A layer that reached upwards would make the headless server
  need a display, or the engine need its own front end.
* **python_exec captures per thread.** Two scripts running at once each
  get their own output; ``redirect_stdout`` would have swapped one
  process-wide stream and mixed them.
* **python_exec leaves ``sys.stdout``/``sys.stderr`` exactly as it found
  them** (rule 5), also when the script raises.
* **REPL behaviour**: the last expression's value comes back; an exception
  comes back as data with its traceback.
"""
from __future__ import annotations

import ast
import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 \
                and node.module:
            out.add(node.module.split(".")[0])
    return out


def _package_imports(pkg: str) -> dict[str, set[str]]:
    return {str(p.relative_to(_ROOT)): _imports(p)
            for p in sorted((_ROOT / pkg).rglob("*.py"))}


class TestLayering:
    def test_the_operations_layer_needs_no_display_and_no_sdk(self):
        banned = {"PySide6", "ogr_gui", "mcp", "ogr_mcp"}
        found = {f: sorted(i & banned)
                 for f, i in _package_imports("ogr_api").items()
                 if i & banned}
        assert not found, found

    def test_the_engine_never_imports_the_operations_layer(self):
        for pkg in ("ogr_core", "ogr_slip2d", "ogr_fem2d"):
            found = [f for f, i in _package_imports(pkg).items()
                     if "ogr_api" in i]
            assert not found, (pkg, found)

    def test_the_rules_module_is_core_only(self):
        imports = _imports(_ROOT / "ogr_core" / "project" / "rules.py")
        assert not imports & {"PySide6", "ogr_gui", "ogr_slip2d",
                              "ogr_fem2d", "ogr_api"}, imports

    def test_the_layer_is_one_of_the_measured_packages(self):
        """The runner's provenance check covers it."""
        runner = (_ROOT / "tests" / "_runner.py").read_text(
            encoding="utf-8")
        assert '"ogr_api"' in runner


class TestPythonExec:
    def test_repl_value_output_and_error(self):
        from ogr_api.pyexec import run_python
        ns: dict = {}
        out = run_python("x = 6\nprint('hello')\nx * 7", ns)
        assert out["ok"] and out["stdout"] == "hello\n"
        assert out["value"] == "42"
        bad = run_python("1/0", ns)
        assert bad["ok"] is False and "ZeroDivisionError" in bad["error"]
        syn = run_python("def (", ns)
        assert syn["ok"] is False and "SyntaxError" in syn["error"]

    def test_the_streams_are_put_back(self):
        from ogr_api.pyexec import run_python
        out0, err0 = sys.stdout, sys.stderr
        run_python("print('a')", {})
        run_python("import sys; sys.stderr.write('b'); raise KeyError", {})
        assert sys.stdout is out0 and sys.stderr is err0

    def test_two_scripts_at_once_keep_their_own_output(self):
        from ogr_api.pyexec import run_python
        barrier = threading.Barrier(2)
        results = {}

        def work(tag):
            ns = {"barrier": barrier}
            code = ("for i in range(200):\n"
                    f"    print('{tag}', i)\n"
                    "    if i == 100:\n"
                    "        barrier.wait(timeout=10)\n")
            results[tag] = run_python(code, ns)

        threads = [threading.Thread(target=work, args=(t,))
                   for t in ("A", "B")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        for tag, other in (("A", "B"), ("B", "A")):
            lines = results[tag]["stdout"].splitlines()
            assert len(lines) == 200, (tag, len(lines))
            assert all(line.startswith(tag + " ") for line in lines), tag
            assert not any(line.startswith(other + " ") for line in lines)

    def test_a_script_sees_the_model_and_the_operations(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="Script")["project_id"]
            out = call(ws, "python_exec", project_id=pid, code=(
                "print(project.name)\n"
                "sorted(api.operations())[:2]"))
            assert out["ok"], out
            assert out["stdout"] == "Script\n"
            assert out["value"].startswith("['analysis_configure'")
        finally:
            ws.shutdown()
