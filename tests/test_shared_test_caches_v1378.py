# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A computation a test file memoizes for its own tests is reached only from
that file, unless the reason it is safe to share is written down here.

WHAT INVARIANT THIS PROTECTS.

Test files share expensive, deterministic computations among their own tests
through module-level memos. The runner executes every test file once and
keeps the module in ``sys.modules`` for the rest of the process
(``tests/_runner.py``, where each file is loaded), so a memo that ANOTHER
file reaches hands it whatever the first file computed — and possibly
changed — in the serial run, and a freshly computed object under ``--jobs``,
where the two files may land in different processes. A difference that
depends on the order of the files is the worst kind to diagnose (AGENTS.md,
rule 5), so it is caught statically.

What counts as a memo (a module-level container and the code that reads it):

* a container named like a cache (``*CACHE*``, ``_SHARED``), and every
  function or method that refers to it;
* any other module-level empty container (``{}``, ``[]``, ``dict()``…)
  that a function both tests (``in``, ``not``, ``if X``) and returns
  something taken from (``_RUN``, ``_WINDOWS``); a list a function only
  appends to is a registry, not a memo, and a name (``_shared_*``) proves
  nothing;
* a function or method — judged by itself, as ``Class.method`` — that
  refers to a memo of its own file, or to a memo of another test file it
  reaches: a fixpoint over all the files, so a chain through a second file
  counts.

What counts as reaching one: importing it, or an attribute through an
imported module or class (``T.f``, ``C.m``, ``C().m``, ``T.C().m``), through
a helper of the reading file that returns an imported module
(``_helpers().f``), or through a variable bound to any of those
(``h = _helpers(); h.f``, ``t = C(); t.m``). Names are resolved per
function, so one alias bound to two modules in two functions is read right.

Known limit, on purpose: dynamic access (``getattr(T, "_run")``,
``importlib``) is not followed; it does not occur in ``tests/`` at v0.1.379.

The reaches that existed when this guard was written are listed in
``ALLOWED`` with the reason each one is safe: every one of them hands out an
object its readers only read. Two keep a latent hazard, said in their
entries: ``test_probabilistic_all_failed_v1169._det`` keys its memo by the
method set and not by the project, and ``_run_gm`` reads it.

History: v0.1.378 recognised a memo only by its name and only one call
away. The adversarial review of v0.1.379 found reaches it could not see (two
memos named otherwise, chains through a second file, an alias reused in two
functions) and a reason it gave that was false; the guard was rewritten to
the rules above.

Measured cost: under 1 s on the development laptop. It reads every test
file, but parses only the ones a memo could reach: a file that is imported
and declares a module-level container, and then, only while a memo is
found, the files that import it.

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
#: A module-level empty container, with or without an annotation.
_CONTAINER = re.compile(
    r"^(\w+)[ \t]*(?::[^=\n]*)?=[ \t]*(?:\{\}|\[\]|dict\(\)|list\(\)|set\(\))[ \t]*(?:#.*)?$",
    re.M)

#: (reading file, memo file, name) -> why it is safe to share today.
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
    ("test_partial_method_loss_v1170", "test_probabilistic_all_failed_v1169", "_run_gm"):
        "LATENT, the same hazard one call away: _run_gm reads _det; its one caller "
        "here passes the same Ej_1 model, built afresh",
    ("test_mass_switch_note_v1238", "test_statistical_rebuild_v1154", "_notched"):
        "the two-mass model, only read: the engine clones it per sample, and the "
        "one reader here that changes it deep-copies it first",
    ("test_partial_method_loss_v1170", "test_statistical_rebuild_v1154", "_notched"):
        "the two-mass model, only read; _without_the_option deep-copies before it "
        "flips the option",
    ("test_reevaluation_symmetry_v1239", "test_statistical_rebuild_v1154", "_notched"):
        "the two-mass model, only read; the reader deep-copies before it changes it",
    ("test_surface_key_endpoints_v1237", "test_statistical_rebuild_v1154", "_notched"):
        "the two-mass model, only read by the surface-key cases",
    ("test_statistics_surface_line_v1255", "test_mass_switch_note_v1238", "_model"):
        "the same two-mass model one file further: shown in a StatisticsWindow, which "
        "never writes to its project, and passed to run_sensitivity, which clones",
    ("test_statistics_surface_line_v1255", "test_mass_switch_note_v1238", "_global_minimum"):
        "a Global Minimum run on that model; the engine clones per sample",
    ("test_statistics_surface_line_v1255", "test_mass_switch_note_v1238", "_deterministic"):
        "one circle of that model evaluated on it; an evaluation does not write to "
        "the model",
    ("test_statistics_surface_line_v1255", "test_mass_switch_note_v1238", "_narrow"):
        "a random variable on that model's material, built afresh on every call; "
        "the model is only read",
    ("test_statistics_surface_line_v1255", "test_mass_switch_note_v1238", "_wide"):
        "a random variable on that model's material, built afresh on every call; "
        "the model is only read",
    ("test_stat_notes_v1353", "test_partial_method_loss_v1170", "_real_partial"):
        "a run on the two-mass model one file further; only its notes are read",
    ("test_texts_spanish_v1370", "test_report_spanish_v1355", "_capture"):
        "the report model, its results and factor report, only read to write a PDF: "
        "the report generator and its figures do not write to them",
    ("test_add_surface_centre_radius_v1335", "test_add_surface_three_points_v1168", "_window"):
        "a MainWindow; the reader sorts before the owner and is its only importer, "
        "and the runner then loads the owner as a fresh module, so each file has its own",
    ("test_add_surface_centre_radius_v1335", "test_add_surface_three_points_v1168",
     "_canvas_ready"):
        "the same window, through the canvas helper; the same reason",
}


def _is_cache_name(name: str) -> bool:
    return "CACHE" in name or name == "_SHARED"


def _target_of(node, aliases):
    """The test module and name an expression stands for, or None.

    ``aliases``: name -> ("mod", T) | ("name", T, n) | ("modfn", T) | ("inst", T, C)."""
    if isinstance(node, ast.Name):
        a = aliases.get(node.id)
        if a and a[0] == "name":
            return a[1], a[2]
    if not isinstance(node, ast.Attribute):
        return None
    base, attr = node.value, node.attr
    if isinstance(base, ast.Call):
        f = base.func
        if isinstance(f, ast.Name):
            a = aliases.get(f.id)
            if a and a[0] == "modfn":
                return a[1], attr
            if a and a[0] == "name":
                return a[1], f"{a[2]}.{attr}"
            return None
        base = f
    if isinstance(base, ast.Name):
        a = aliases.get(base.id)
        if not a:
            return None
        if a[0] == "mod":
            return a[1], attr
        if a[0] in ("name", "inst"):
            return a[1], f"{a[2]}.{attr}"
        return None
    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
        a = aliases.get(base.value.id)
        if a and a[0] == "mod":
            return a[1], f"{base.attr}.{attr}"
    return None


def _add_imports(node, amap, tests, own) -> None:
    if isinstance(node, ast.Import):
        for a in node.names:
            if a.name in tests and a.name != own:
                amap[a.asname or a.name] = ("mod", a.name)
    elif isinstance(node, ast.ImportFrom) and node.module in tests and node.module != own:
        for a in node.names:
            amap[a.asname or a.name] = ("name", node.module, a.name)


def _binding(value, amap):
    """What ``x = value`` binds ``x`` to, when it is a module or an instance."""
    if isinstance(value, ast.Name):
        a = amap.get(value.id)
        if a and a[0] in ("mod", "inst"):
            return a
    if isinstance(value, ast.Call):
        f = value.func
        if isinstance(f, ast.Name):
            a = amap.get(f.id)
            if a and a[0] == "modfn":
                return ("mod", a[1])
            if a and a[0] == "name":
                return ("inst", a[1], a[2])
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            a = amap.get(f.value.id)
            if a and a[0] == "mod":
                return ("inst", a[1], f.attr)
    return None


def _bind_all(assigns, amap) -> None:
    for _ in range(2):
        for target, value in assigns:
            bound = _binding(value, amap)
            if bound:
                amap[target] = bound


class _Body:
    """One function or method, walked once."""

    def __init__(self, fn, cls) -> None:
        self.cls = cls
        self.imports, self.assigns, self.returns, self.nodes = [], [], [], []
        for x in ast.walk(fn):
            if isinstance(x, (ast.Import, ast.ImportFrom)):
                self.imports.append(x)
            elif isinstance(x, ast.Assign) and len(x.targets) == 1 \
                    and isinstance(x.targets[0], ast.Name):
                self.assigns.append((x.targets[0].id, x.value))
            elif isinstance(x, ast.Return) and isinstance(x.value, ast.Name):
                self.returns.append(x.value.id)
            if isinstance(x, (ast.Name, ast.Attribute, ast.Compare, ast.If, ast.IfExp,
                              ast.While, ast.Return)):
                self.nodes.append(x)


class _File:
    """One test file: its memos, what each function refers to, and how it
    names the other test files (per function: a name imported or bound in
    one function means nothing in another)."""

    def __init__(self, name: str, text: str, tests) -> None:
        self.name = name
        tree = ast.parse(text)
        self.containers = set()
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        top, top_assigns, top_nodes, bodies = {}, [], [], {}
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for tg in targets:
                    if isinstance(tg, ast.Name) and (_is_cache_name(tg.id) or _empty(node.value)):
                        self.containers.add(tg.id)
            if isinstance(node, ast.FunctionDef):
                bodies[node.name] = _Body(node, None)
            elif isinstance(node, ast.ClassDef):
                for m in node.body:
                    if isinstance(m, ast.FunctionDef):
                        bodies[f"{node.name}.{m.name}"] = _Body(m, node.name)
            else:
                for x in ast.walk(node):
                    if isinstance(x, (ast.Import, ast.ImportFrom)):
                        _add_imports(x, top, tests, name)
                    elif isinstance(x, ast.Assign) and len(x.targets) == 1 \
                            and isinstance(x.targets[0], ast.Name):
                        top_assigns.append((x.targets[0].id, x.value))
                    if isinstance(x, (ast.Name, ast.Attribute)):
                        top_nodes.append(x)
        _bind_all(top_assigns, top)
        maps = {}
        for key, b in bodies.items():
            amap = dict(top)
            for x in b.imports:
                _add_imports(x, amap, tests, name)
            _bind_all(b.assigns, amap)
            maps[key] = amap
            if "." not in key:
                for r in b.returns:
                    a = amap.get(r)
                    if a and a[0] == "mod":
                        top[key] = ("modfn", a[1])
        for key, b in bodies.items():
            amap = maps[key]
            for k, v in top.items():
                if v[0] == "modfn":
                    amap.setdefault(k, v)
            _bind_all(b.assigns, amap)
        self.imported_names = set()
        for amap in [top, *maps.values()]:
            for a in amap.values():
                if a[0] == "name":
                    self.imported_names.add((a[1], a[2]))
        self.bodies, self.local_refs, self.ext_refs = list(bodies), {}, {}
        memo = {c for c in self.containers if _is_cache_name(c)}
        for key, b in bodies.items():
            local, ext = set(), set()
            amap = maps[key]
            for x in b.nodes:
                if isinstance(x, ast.Name):
                    local.add(x.id)
                    if x.id in amap:
                        t = _target_of(x, amap)
                        if t:
                            ext.add(t)
                elif isinstance(x, ast.Attribute):
                    base = x.value.func if isinstance(x.value, ast.Call) else x.value
                    if isinstance(base, ast.Name):
                        # only a method of this file can be a local memo:
                        # ``self.m``, ``C.m``, ``C().m`` with C a class here
                        if base.id == "self" and b.cls:
                            local.add(f"{b.cls}.{x.attr}")
                        elif base.id in classes:
                            local.add(f"{base.id}.{x.attr}")
                        elif base.id in amap:
                            t = _target_of(x, amap)
                            if t:
                                ext.add(t)
                    elif isinstance(base, ast.Attribute):
                        t = _target_of(x, amap)
                        if t:
                            ext.add(t)
            self.local_refs[key], self.ext_refs[key] = local, ext
            memo |= _memo_shape(b.nodes, self.containers)
        self.top_ext = {t for t in (_target_of(x, top) for x in top_nodes) if t}
        self.memo = memo
        self.close()

    def close(self) -> None:
        changed = True
        while changed:
            changed = False
            for key in self.bodies:
                if key not in self.memo and self.local_refs[key] & self.memo:
                    self.memo.add(key)
                    changed = True


def _empty(value) -> bool:
    if isinstance(value, (ast.Dict, ast.List, ast.Set)):
        return not (getattr(value, "keys", None) or getattr(value, "elts", None))
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id in ("dict", "list", "set") and not value.args
            and not value.keywords)


def _memo_shape(nodes, containers) -> set:
    """The containers a function uses as a memo: it tests one (``in``,
    ``not``, ``if X``) and returns something taken from it."""
    tested, returned = set(), set()
    for x in nodes:
        if isinstance(x, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in x.ops):
            for c in x.comparators:
                if isinstance(c, ast.Name) and c.id in containers:
                    tested.add(c.id)
        elif isinstance(x, (ast.If, ast.IfExp, ast.While)):
            t = x.test.operand if isinstance(x.test, ast.UnaryOp) else x.test
            if isinstance(t, ast.Name) and t.id in containers:
                tested.add(t.id)
        elif isinstance(x, ast.Return) and x.value is not None:
            for y in ast.walk(x.value):
                if isinstance(y, ast.Name) and y.id in containers:
                    returned.add(y.id)
    return tested & returned


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


def _may_hold_a_memo(text: str) -> bool:
    """A cache by name, or a module-level container the text both tests and
    returns: the cheap reading that decides whether a file is parsed. A
    container only appended to (a registry) does not pass."""
    if "CACHE" in text or "_SHARED" in text:
        return True
    for c in _CONTAINER.findall(text):
        name = re.escape(c)
        if (re.search(rf"\b(?:in|not|if)\s+{name}\b", text)
                and re.search(rf"return[^\n]*\b{name}\b", text)):
            return True
    return False


def reaches(sources: dict) -> set:
    """``{(reading file, memo file, name)}``: every reach of a memo of one
    test file from another, chains through a second file included.

    Lazy: a file is parsed only when it is imported and may hold a memo,
    or when it imports a file that does."""
    imported = importers(sources)
    tests = set(sources)
    files = {}

    def get(m):
        if m not in files:
            files[m] = _File(m, sources[m], tests)
        return files[m]

    memo_mods = {m for m in imported if _may_hold_a_memo(sources[m]) and get(m).memo}
    expanded, found = set(), set()
    while True:
        for m in sorted(memo_mods - expanded):
            expanded.add(m)
            for r in imported.get(m, ()):
                get(r)
        grew = False
        for f in list(files.values()):
            for key in f.bodies:
                for (t, n) in f.ext_refs[key]:
                    if t in files and n in files[t].memo:
                        found.add((f.name, t, n))
                        if key not in f.memo:
                            f.memo.add(key)
                            f.close()
                            grew = True
            for (t, n) in f.top_ext | f.imported_names:
                if t in files and n in files[t].memo:
                    found.add((f.name, t, n))
            if f.memo and f.name in imported and f.name not in memo_mods:
                memo_mods.add(f.name)
                grew = True
        if not grew and not (memo_mods - expanded):
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
        _STATE["uses"] = reaches(_sources())
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
        "_SHARED: dict = {}\n"
        "_RUN = {}\n"
        "_WINDOWS: list = []\n"
        "def _expensive():\n"
        "    if 'x' not in _CACHE:\n"
        "        _CACHE['x'] = object()\n"
        "    return _CACHE['x']\n"
        "def _shared_run():\n"
        "    return _SHARED.setdefault('r', object())\n"
        "def _run():\n"
        "    if 'k' not in _RUN:\n"
        "        _RUN['k'] = object()\n"
        "    return _RUN['k']\n"
        "def _registry():\n"
        "    w = object()\n"
        "    _WINDOWS.append(w)\n"
        "    return w\n"
        "def _shared_meshes():\n"
        "    return object()\n"
        "def _wrap():\n"
        "    return _expensive()\n"
        "def _fresh():\n"
        "    return object()\n"
        "class C:\n"
        "    def reads(self):\n"
        "        return _shared_run()\n"
        "    def through(self):\n"
        "        return self.reads()\n"
        "    def fresh(self):\n"
        "        return object()\n")

    def _check(self, readers: dict) -> set:
        return reaches(dict({"test_a": self.MEMO}, **readers))

    def test_it_sees_an_import_of_a_memo(self):
        assert self._check({"test_b": "from test_a import _expensive, _fresh\n"}) == {
            ("test_b", "test_a", "_expensive")}

    def test_it_sees_an_attribute_through_a_module(self):
        assert self._check({"test_b": "import test_a as T\nT._shared_run()\nT._fresh()\n"}) == {
            ("test_b", "test_a", "_shared_run")}

    def test_it_knows_a_memo_by_its_shape_not_its_name(self):
        """``_RUN`` is a memo; ``_WINDOWS``, only appended to, is a registry;
        ``_shared_meshes`` builds afresh whatever its name says."""
        assert self._check({"test_b": "from test_a import _run, _registry, _shared_meshes\n"}) == {
            ("test_b", "test_a", "_run")}

    def test_it_follows_a_helper_that_calls_a_memo(self):
        assert self._check({"test_b": "from test_a import _wrap\n"}) == {("test_b", "test_a", "_wrap")}

    def test_it_judges_each_method_by_itself(self):
        """A class may be imported for its ordinary builder; only the
        methods that reach a memo, directly or through ``self``, count."""
        assert self._check({
            "test_b": "from test_a import C\nC().fresh()\nC().through()\n",
            "test_c": "import test_a as T\nT.C().reads()\nT.C().fresh()\n",
        }) == {("test_b", "test_a", "C.through"), ("test_c", "test_a", "C.reads")}

    def test_it_follows_helpers_and_variables(self):
        """A helper that returns the module, and variables bound to a module
        or to an instance."""
        assert self._check({"test_b": (
            "def _helpers():\n    import test_a as h\n    return h\n"
            "def f():\n    _helpers()._run()\n"
            "def g():\n    m = _helpers()\n    m._expensive()\n"
            "def k():\n    from test_a import C\n    t = C()\n    t.reads()\n")}) == {
            ("test_b", "test_a", "_run"), ("test_b", "test_a", "_expensive"),
            ("test_b", "test_a", "C.reads")}

    def test_one_alias_in_two_functions_is_read_per_function(self):
        """``T`` is test_a in one function and test_d in the other: each
        reach goes to the module its own function imported."""
        assert self._check({
            "test_d": "def _fresh():\n    return object()\n",
            "test_b": ("def f():\n    import test_a as T\n    T._run()\n"
                       "def g():\n    import test_d as T\n    T._fresh()\n")}) == {
            ("test_b", "test_a", "_run")}

    def test_it_follows_a_chain_through_a_second_file(self):
        assert self._check({
            "test_b": "import test_a as A\ndef _model():\n    return A._run()\n",
            "test_c": "import test_b as B\nB._model()\n",
        }) == {("test_b", "test_a", "_run"), ("test_c", "test_b", "_model")}

    def test_a_file_may_use_its_own_memo(self):
        assert reaches({"test_a": self.MEMO + "_expensive()\n_run()\nC().reads()\n"}) == set()

    def test_the_text_finds_every_importer(self):
        """The shortcut that keeps this file fast may not miss an import:
        indented, aliased and parenthesised forms all count."""
        src = {"test_a": self.MEMO,
               "test_b": "def f():\n    from test_a import (\n        _expensive)\n",
               "test_c": "import test_a as T\n",
               "test_d": "x = 'test_a'\n"}
        assert importers(src) == {"test_a": {"test_b", "test_c"}}
