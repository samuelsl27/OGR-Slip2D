# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A computation a test file memoizes for its own tests is reached only from
that file, unless the reason it is safe to share is written down here.

WHAT INVARIANT THIS PROTECTS.

Test files share expensive, deterministic computations among their own tests
through module-level memos: a ``_CACHE`` dict (some eighty files) or, since
v0.1.378, ``_shared_*`` helpers reading ``_SHARED``. The runner executes every test file
once and keeps the module in ``sys.modules`` for the rest of the process
(``tests/_runner.py``, where each file is loaded), so a memo that ANOTHER
file reaches hands it whatever the first file computed — and possibly
changed — in the serial run, and a freshly computed object under ``--jobs``,
where the two files may land in different processes. A difference that
depends on the order of the files is the worst kind to diagnose (AGENTS.md,
rule 5), so it is caught statically: a helper that reads or writes a
module-level cache, or is named ``_shared_*``, may not be imported or
reached as an attribute from another test file.

The nine such reaches that existed when this guard was written are listed in
``ALLOWED`` with the reason each one is safe: every one of them hands out an
object its readers only read. One of them keeps a latent hazard, said in
its entry: ``test_probabilistic_all_failed_v1169._det`` keys its memo by the
method set and not by the project.

Importing a file's ordinary builders, which compute afresh on every call
(``_slope``, ``_run``, ``_project``…), is not what this is about and stays
free.

Measured cost: 0.87 s on the development laptop. It reads every test file,
but parses only the ones another test file imports and the ones that import
them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import glob
import os
import re

_TESTS = os.path.dirname(os.path.abspath(__file__))

#: ``from test_x import ...`` or ``import test_x``, at any indentation.
_IMPORT = re.compile(r"^[ \t]*(?:from[ \t]+(test_\w+)[ \t]+import\b|import[ \t]+(test_\w+))",
                     re.M)

#: (reading file, memo file, helper) -> why it is safe to share today.
ALLOWED = {
    ("test_bishop_general_base_forces_v1213", "test_janbu_base_forces_v1107", "_slope"):
        "a dry slope and its slices, only read: the methods never write to a slice",
    ("test_envelope_own_stress_v1213", "test_janbu_base_forces_v1107", "_slope"):
        "a dry slope and its slices, only read: the methods never write to a slice",
    ("test_core_messages_v1333", "test_no_number_v1152", "_symmetric_results"):
        "the nine methods' results on one circle, only read",
    ("test_own_base_stress_v1210", "test_slide_validation_ej2_piezo_v194", "_result"):
        "one method's result on a reference circle, memoised by (method, circle), only read",
    ("test_partial_method_loss_v1170", "test_probabilistic_all_failed_v1169", "_det"):
        "LATENT: the memo is keyed by the method set and not by the project; safe "
        "only because every caller passes the same Ej_1 model, built afresh",
    ("test_mass_switch_note_v1238", "test_statistical_rebuild_v1154", "_notched"):
        "never handed out to be mutated (its docstring); a reader that flips the "
        "option takes a deep copy first",
    ("test_partial_method_loss_v1170", "test_statistical_rebuild_v1154", "_notched"):
        "never handed out to be mutated; _without_the_option takes a deep copy",
    ("test_reevaluation_symmetry_v1239", "test_statistical_rebuild_v1154", "_notched"):
        "never handed out to be mutated (its docstring)",
    ("test_surface_key_endpoints_v1237", "test_statistical_rebuild_v1154", "_notched"):
        "never handed out to be mutated (its docstring)",
}


def _is_cache_name(name: str) -> bool:
    return "CACHE" in name or name == "_SHARED"


def importers(sources: dict) -> dict:
    """``{test module: {the other test files that import it}}``, read from
    the text, so that only those files need parsing."""
    out = {}
    for mod, text in sources.items():
        for a, b in _IMPORT.findall(text):
            target = a or b
            if target != mod and target in sources:
                out.setdefault(target, set()).add(mod)
    return out


def memo_helpers(sources: dict, only=None) -> dict:
    """``{module: {helper names}}``: the module-level functions (and the
    methods of module-level classes, by class name) that use a module-level
    cache, plus every function named ``_shared_*`` and the caches
    themselves. ``only`` limits the modules looked at."""
    out = {}
    for mod, text in sources.items():
        if only is not None and mod not in only:
            continue
        if "CACHE" not in text and "_SHARED" not in text and "_shared_" not in text:
            continue
        tree = ast.parse(text)
        caches = set()
        for node in tree.body:
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target] if isinstance(node, ast.AnnAssign) else [])
            for tg in targets:
                if isinstance(tg, ast.Name) and _is_cache_name(tg.id):
                    caches.add(tg.id)
        names = set(caches)
        for node in tree.body:
            funcs = [(node.name, node)] if isinstance(node, ast.FunctionDef) else []
            if isinstance(node, ast.ClassDef):
                funcs = [(node.name, m) for m in node.body if isinstance(m, ast.FunctionDef)]
            for name, fn in funcs:
                used = {x.id for x in ast.walk(fn) if isinstance(x, ast.Name)}
                if used & caches or fn.name.startswith("_shared_"):
                    names.add(name)
        if names:
            out[mod] = names
    return out


def cross_file_uses(sources: dict, helpers: dict, readers=None) -> set:
    """``{(reading module, memo module, name)}`` for every import of a memo
    helper, or attribute access to one through an imported module, made by a
    file other than the helper's own. ``readers`` limits the files parsed."""
    found = set()
    for mod, text in sources.items():
        if readers is not None and mod not in readers:
            continue
        if not any(other in text for other in helpers if other != mod):
            continue
        tree = ast.parse(text)
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in helpers and node.module != mod:
                for a in node.names:
                    if a.name in helpers[node.module]:
                        found.add((mod, node.module, a.name))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in helpers and a.name != mod:
                        aliases[a.asname or a.name] = a.name
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in aliases
                    and node.attr in helpers[aliases[node.value.id]]):
                found.add((mod, aliases[node.value.id], node.attr))
    return found


def _sources() -> dict:
    out = {}
    for path in sorted(glob.glob(os.path.join(_TESTS, "test_*.py"))):
        with open(path, encoding="utf-8") as f:
            out[os.path.splitext(os.path.basename(path))[0]] = f.read()
    return out


_STATE: dict = {}


def _actual() -> set:
    """Computed once for the file: both tests below read it."""
    if "uses" not in _STATE:
        src = _sources()
        imported = importers(src)
        helpers = memo_helpers(src, only=set(imported))
        readers = set().union(*(imported[m] for m in helpers)) if helpers else set()
        _STATE["uses"] = cross_file_uses(src, helpers, readers)
    return _STATE["uses"]


class TestTheSuite:
    def test_no_file_reaches_another_files_memo(self):
        new = sorted(_actual() - set(ALLOWED))
        assert not new, (
            "a test file reaches another file's memo; in the serial run it gets "
            "the object that file computed, under --jobs a fresh one. Give it its "
            "own computation, or add it to ALLOWED with the reason it is safe: "
            f"{new}")

    def test_every_allowed_reach_still_exists(self):
        """An entry whose reach is gone is a reason nobody can check any
        more; it is removed with the code that needed it."""
        stale = sorted(set(ALLOWED) - _actual())
        assert not stale, stale


class TestTheChecker:
    """The guard has to be able to fail, or it guards nothing."""

    MEMO = (
        "_CACHE = {}\n"
        "def _expensive():\n"
        "    if 'x' not in _CACHE:\n"
        "        _CACHE['x'] = object()\n"
        "    return _CACHE['x']\n"
        "def _shared_run():\n"
        "    return 1\n"
        "def _fresh():\n"
        "    return object()\n")

    def test_it_sees_an_import_of_a_memo(self):
        src = {"test_a": self.MEMO,
               "test_b": "from test_a import _expensive, _fresh\n"}
        assert cross_file_uses(src, memo_helpers(src)) == {
            ("test_b", "test_a", "_expensive")}

    def test_it_sees_an_attribute_through_a_module(self):
        src = {"test_a": self.MEMO,
               "test_b": "import test_a as T\nT._shared_run()\nT._fresh()\n"}
        assert cross_file_uses(src, memo_helpers(src)) == {
            ("test_b", "test_a", "_shared_run")}

    def test_a_file_may_use_its_own_memo(self):
        src = {"test_a": self.MEMO + "_expensive()\n_shared_run()\n"}
        assert cross_file_uses(src, memo_helpers(src)) == set()

    def test_the_text_finds_every_importer(self):
        """The shortcut that keeps this file fast may not miss an import:
        indented, aliased and parenthesised forms all count."""
        src = {"test_a": self.MEMO,
               "test_b": "def f():\n    from test_a import (\n        _expensive)\n",
               "test_c": "import test_a as T\n",
               "test_d": "x = 'test_a'\n"}
        assert importers(src) == {"test_a": {"test_b", "test_c"}}
