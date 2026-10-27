# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.372 — a test imports only what CI installs.

Invariant protected: every module a test imports is in the standard
library, in this repository, in a requirement of ``pyproject.toml`` (the
base list and the ``[mcp]`` extra, which is what CI installs), or in a
short list below that says why it is there anyway.

Why. ``test_cancel_v1366.py`` (0.1.366, D362) imported ``psutil`` to see
that no pool worker was left after a cancel. psutil is not a requirement of
the project; it happened to be installed on the machine the suite ran on,
so the whole suite passed there five versions in a row, and CI failed on
the import in the three Pythons when the tanda was pushed. The standard
library answers the same question (``multiprocessing.active_children``).
A module that is "just there" on one machine is invisible to every local
run, so this reads the imports instead of trying them.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TESTS = _ROOT / "tests"

#: The extras CI installs (``pip install -e ".[mcp]"`` in the workflow).
_CI_EXTRAS = ("mcp",)

#: Imported by tests although no requirement names them, each with why
#: CI has it or why the test does not need it.
_ALLOWED = {
    "pytest": "the runner supplies a stand-in (tests/_runner.py)",
    "examples": "the repository's own examples/ folder",
    "ogr_snap_engine_test": "test_snap_engine.py registers it in "
                            "sys.modules itself",
    "httpx2": "a requirement of mcp, installed by the [mcp] extra; used "
              "only when mcp is importable",
    "starlette": "a requirement of mcp, installed by the [mcp] extra",
    "cryptography": "optional: the test returns on ImportError",
}


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared() -> set[str]:
    """Import names (lower case) of the requirements CI installs."""
    import tomllib
    from importlib.metadata import packages_distributions

    meta = tomllib.loads((_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"))["project"]
    reqs = list(meta["dependencies"])
    for extra in _CI_EXTRAS:
        reqs += meta["optional-dependencies"][extra]
    dists = {_norm(re.split(r"[\s<>=!~;\[]", r, maxsplit=1)[0])
             for r in reqs}
    # a requirement not installed here still counts under its own name
    names = {d.replace("-", "_") for d in dists}
    for module, owners in packages_distributions().items():
        if any(_norm(o) in dists for o in owners):
            names.add(module.lower())
    return names


def _imports(source: str) -> set[str]:
    """Top-level names of the absolute imports in ``source``, wherever they
    are (inside functions too: most tests import there)."""
    out = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif (isinstance(node, ast.ImportFrom) and node.level == 0
              and node.module):
            out.add(node.module.split(".")[0])
    return out


def _local() -> set[str]:
    """This repository's packages and the tests' own modules."""
    packages = {p.name for p in _ROOT.iterdir()
                if p.is_dir() and (p / "__init__.py").exists()}
    tests = {p.stem for p in _TESTS.rglob("*.py")}
    return packages | tests | {p.name for p in _TESTS.iterdir() if p.is_dir()}


def _unexplained(source: str, declared: set[str], local: set[str]) -> set[str]:
    return {m for m in _imports(source)
            if m not in sys.stdlib_module_names and m not in local
            and m not in _ALLOWED and m.lower() not in declared}


def _every_test_file():
    return sorted(_TESTS.rglob("*.py"))


class TestTheTestsImportOnlyWhatCIInstalls:

    def test_every_import_is_declared_or_explained(self):
        declared, local = _declared(), _local()
        bad = {}
        for path in _every_test_file():
            found = _unexplained(path.read_text(encoding="utf-8"),
                                 declared, local)
            if found:
                bad[path.name] = sorted(found)
        assert not bad, bad

    def test_the_census_sees_the_import_that_failed_in_ci(self):
        """The case that opened this: an import inside a test method of a
        module that is not a requirement. A census that read only the
        module's top would have missed it."""
        source = ("class T:\n"
                  "    def test(self):\n"
                  "        import psutil\n"
                  "        import numpy\n")
        assert _unexplained(source, _declared(), _local()) == {"psutil"}

    def test_every_explained_name_is_still_imported(self):
        """An entry nobody imports any more would let that module back in
        unexplained."""
        used = set()
        for path in _every_test_file():
            used |= _imports(path.read_text(encoding="utf-8"))
        stale = sorted(set(_ALLOWED) - used)
        assert not stale, stale
