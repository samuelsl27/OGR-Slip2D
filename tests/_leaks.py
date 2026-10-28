# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.374 — what a test file leaves in the process, named at the file that
leaves it.

Rule 5 says a test puts back anything global it changes. Until this version
that was checked by luck: a leak showed only when a later test happened to
depend on it, and only in the full run, which is the worst failure there is
to diagnose (the language left in Spanish that failed unrelated menu tests).
The runner now takes a :func:`snapshot` before each file and another after
it, once it has put back ``sys.path`` and its own folders, and :func:`diff`
names what changed. A change is a leak, and the run fails, unless:

- the key did not exist before: a library imported, or the QApplication
  made, for the first time. Not for an environment variable, and not for a
  value that comes from a test file (a function written in one, a mock):
  those are leaks however new;
- it is an attribute of an ``ogr_*`` module imported for the first time
  that still has the literal value its source gives it;
- an entry of :data:`ALLOWED` says why it is not one.

What is looked at: the environment, the working folder, the import
machinery, warnings, logging, the locale, the interpreter's hooks and
knobs, ``builtins``, numpy, ``random``, matplotlib, the QApplication (style,
sheet, palette, font, locale, and the static dialogs tests replace so that
no modal window opens), the saved preferences and the bridge discovery
files of the run, and every attribute of every ``ogr_*`` module and of every
class they define.

Where it comes from: the census of the suite audit, which ran this same
comparison over the whole suite from outside it
(docs/audits/AUDITORIA_SUITE_v0.1.372.md §8–9).
"""
from __future__ import annotations

import ast
import builtins
import configparser
import contextlib
import fnmatch
import gc
import os
import sys
import threading
import types
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SCALARS = (type(None), bool, int, float, complex, str, bytes)
_CONTAINERS = ("list", "dict", "set", "bytearray", "deque", "OrderedDict",
               "defaultdict", "Counter")

#: Marks a value that comes from a test file: such a value inside the
#: program is a leak even on a key seen for the first time.
FROM_A_TEST = "!test"

#: Stands for a key that is not there.
ABSENT = "(absent)"

_UNKNOWN = object()


def _from_a_test(v) -> bool:
    code = getattr(getattr(v, "__func__", v), "__code__", None)
    if code is not None:
        return Path(code.co_filename).name.startswith("test_")
    return type(v).__module__ == "unittest.mock"


def _content(v) -> str:
    """A hash of a small container of plain values, so that a table changed
    in place (same length) is still a change. Empty for anything else: a
    repr of arbitrary objects can be slow, and their identity is enough."""
    try:
        if len(v) > 64:
            return ""
        if isinstance(v, dict):
            items = tuple(v.items())
            if all(isinstance(a, _SCALARS) and isinstance(b, _SCALARS)
                   for a, b in items):
                return f"#{hash(items)}"
        elif isinstance(v, (list, set)):
            if all(isinstance(a, _SCALARS) for a in v):
                return f"#{hash(frozenset(v) if isinstance(v, set) else tuple(v))}"
    except Exception:  # noqa: BLE001
        pass
    return ""


def value_of(v) -> str:
    """A comparable stand-in for ``v``: the value itself when it is a plain
    one; otherwise its type and identity, with the length of a container
    and the fill of an ``lru_cache`` (a cache that grows is a change)."""
    try:
        if isinstance(v, _SCALARS):
            r = repr(v)
            return r if len(r) <= 160 else f"{r[:120]}…#{hash(r)}"
        if isinstance(v, (tuple, frozenset)):
            r = repr(v)
            return r if len(r) <= 160 else f"{type(v).__name__}#{hash(r)}"
        if isinstance(v, (staticmethod, classmethod)):
            inner = v.__func__
            # A builtin binds to nothing either way, so Qt's staticmethod(f)
            # and the f a test reads off the class and puts back are the
            # same thing (files of the suite do exactly that). A Python
            # function does bind: wrapped and bare are two behaviours, and
            # qtpy's wrappers of QFileDialog are Python functions.
            if not isinstance(inner, types.FunctionType):
                return value_of(inner)
            return f"{type(v).__name__}({value_of(inner)})"
        tn = type(v).__name__
        mark = FROM_A_TEST if _from_a_test(v) else ""
        if tn in _CONTAINERS:
            return f"{tn}@{id(v)}:len={len(v)}{_content(v)}"
        if getattr(v, "cache_info", None) is not None and callable(v):
            return f"lru@{id(v)}:size={v.cache_info().currsize}"
        return f"{tn}@{id(v)}{mark}"
    except Exception as e:  # noqa: BLE001
        return f"<{type(e).__name__}>"


# --------------------------------------------------------- import defaults
_DEFAULTS: dict = {}


def import_default(module: str, name: str):
    """The value ``name`` has when ``module`` is first imported, when its
    source says so plainly: ONE assignment of a plain literal at module
    level, counting those inside ``if``/``try``/``with``/``for`` blocks.
    Assigned twice or more (``VERSION = "unknown"``, then the real one) or
    to something computed, it is unknown and not compared."""
    table = _DEFAULTS.get(module)
    if table is None:
        table = _DEFAULTS[module] = _literal_table(sys.modules.get(module))
    return table.get(name)


def _targets(node):
    if isinstance(node, ast.Name):
        yield node.id
    elif isinstance(node, (ast.Tuple, ast.List)):
        for e in node.elts:
            yield from _targets(e)
    elif isinstance(node, ast.Starred):
        yield from _targets(node.value)


def _literal_table(mod) -> dict:
    path = getattr(mod, "__file__", None)
    if not path or not str(path).endswith(".py"):
        return {}
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return {}
    count: dict = {}
    value: dict = {}

    def bind(name, node=None):
        count[name] = count.get(name, 0) + 1
        try:
            value[name] = _UNKNOWN if node is None else ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError, MemoryError,
                RecursionError):
            value[name] = _UNKNOWN

    def walk(body):
        for node in body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    plain = isinstance(t, ast.Name)
                    for n in _targets(t):
                        bind(n, node.value if plain else None)
            elif isinstance(node, ast.AnnAssign):
                if node.value is not None and isinstance(node.target,
                                                         ast.Name):
                    bind(node.target.id, node.value)
            elif isinstance(node, ast.AugAssign):
                for n in _targets(node.target):
                    bind(n)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                bind(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    bind((a.asname or a.name).split(".")[0])
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                for n in _targets(node.target):
                    bind(n)
                walk(node.body)
                walk(node.orelse)
            elif isinstance(node, (ast.If, ast.While)):
                walk(node.body)
                walk(node.orelse)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                walk(node.body)
            elif isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                walk(node.body)
                for h in node.handlers:
                    walk(h.body)
                walk(node.orelse)
                walk(node.finalbody)
            elif isinstance(node, ast.Match):
                for case in node.cases:
                    walk(case.body)

    walk(tree.body)
    return {n: value_of(value[n]) for n, c in count.items()
            if c == 1 and value[n] is not _UNKNOWN
            and isinstance(value[n], _SCALARS)}


# ---------------------------------------------------------------- snapshot
#: Static members tests replace so that no modal window opens. Kept by
#: what the class returns, not by the object in its __dict__ (see value_of).
_DIALOGS = {
    "QMessageBox": ("exec", "question", "warning", "information",
                    "critical", "about"),
    "QFileDialog": ("exec", "getOpenFileName", "getOpenFileNames",
                    "getSaveFileName", "getExistingDirectory"),
    "QInputDialog": ("exec", "getText", "getMultiLineText", "getDouble",
                     "getInt", "getItem"),
    "QColorDialog": ("exec", "getColor"),
    "QFontDialog": ("exec", "getFont"),
    "QDialog": ("exec", "open"),
    "QMenu": ("exec", "popup"),
}


def _qt(s: dict) -> None:
    qtw = sys.modules.get("PySide6.QtWidgets")
    if qtw is None:
        return
    app = qtw.QApplication.instance()
    if app is None:
        return
    try:
        qtg = sys.modules["PySide6.QtGui"]
        qtc = sys.modules["PySide6.QtCore"]
        style = app.style()
        s["qt.style"] = style.objectName() if style is not None else None
        s["qt.styleSheet"] = f"#{hash(app.styleSheet())}"
        pal = app.palette()
        s["qt.palette"] = f"#{hash(tuple(pal.color(r).name() for r in qtg.QPalette.ColorRole if r.name != 'NColorRoles'))}"
        s["qt.font"] = app.font().toString()
        s["qt.layoutDirection"] = repr(app.layoutDirection())
        s["qt.applicationName"] = app.applicationName()
        s["qt.organizationName"] = app.organizationName()
        s["qt.quitOnLastWindowClosed"] = app.quitOnLastWindowClosed()
        s["qt.locale"] = qtc.QLocale().name()
    except Exception as e:  # noqa: BLE001
        s["qt.error"] = repr(e)[:120]
    for cname, attrs in _DIALOGS.items():
        c = getattr(qtw, cname, None)
        if c is None:
            continue
        for a in attrs:
            if a in c.__dict__:
                s[f"qt.{cname}.{a}"] = value_of(c.__dict__[a])


def _folder_files(folder) -> tuple:
    """The run's preferences or bridges: each INI file by its keys and
    values, any other file by its name. An INI file with no keys left is
    the same as none, so a test that saves a preference and removes it
    again leaves nothing."""
    if not folder or not os.path.isdir(folder):
        return ()
    out = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not name.lower().endswith(".ini"):
            out.append(name)
            continue
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        try:
            parser.read(path, encoding="utf-8")
        except (configparser.Error, OSError, UnicodeDecodeError):
            out.append(f"{name}: unreadable")
            continue
        for section in parser.sections():
            for k, v in parser.items(section, raw=True):
                out.append(f"{name}: [{section}] {k}={v}")
    return tuple(out)


def snapshot() -> dict:
    """The state a test file could leave behind; see the module docstring."""
    s: dict = {}
    for k, v in os.environ.items():
        s[f"env:{k}"] = v
    s["cwd"] = os.getcwd()
    s["sys.meta_path"] = repr([type(x).__name__ for x in sys.meta_path])
    s["warnings.filters"] = tuple(repr(f) for f in warnings.filters)
    lg = sys.modules.get("logging")
    if lg is not None:
        s["logging.root.level"] = lg.root.level
        s["logging.root.handlers"] = repr([type(h).__name__
                                           for h in lg.root.handlers])
        s["logging.disable"] = lg.root.manager.disable
    loc = sys.modules.get("locale")
    if loc is not None:
        try:
            s["locale"] = loc.setlocale(loc.LC_ALL)
        except Exception:  # noqa: BLE001
            pass
    sock = sys.modules.get("socket")
    if sock is not None:
        s["socket.defaulttimeout"] = repr(sock.getdefaulttimeout())
    s["sys.excepthook"] = value_of(sys.excepthook)
    s["sys.unraisablehook"] = value_of(sys.unraisablehook)
    s["threading.excepthook"] = value_of(threading.excepthook)
    s["sys.recursionlimit"] = sys.getrecursionlimit()
    s["sys.switchinterval"] = sys.getswitchinterval()
    s["sys.stdout"] = value_of(sys.stdout)
    s["sys.stderr"] = value_of(sys.stderr)
    s["gc.threshold"] = repr(gc.get_threshold())
    s["gc.debug"] = gc.get_debug()
    s["gc.enabled"] = gc.isenabled()
    s["gc.callbacks"] = len(gc.callbacks)
    s["pytest"] = value_of(sys.modules.get("pytest"))
    for name in dir(builtins):
        if not name.startswith("_"):
            s[f"builtins.{name}"] = value_of(getattr(builtins, name))
    tf = sys.modules.get("tempfile")
    if tf is not None:
        s["tempfile.tempdir"] = repr(tf.tempdir)
    tm = sys.modules["time"]
    for a in ("time", "sleep", "perf_counter", "monotonic"):
        s[f"time.{a}"] = value_of(getattr(tm, a))
    s["os.cpu_count"] = value_of(os.cpu_count)
    mps = sys.modules.get("multiprocessing.spawn")
    if mps is not None:
        s["mp.executable"] = repr(mps.get_executable())
    mp = sys.modules.get("multiprocessing")
    if mp is not None:
        try:
            s["mp.start_method"] = repr(mp.get_start_method(allow_none=True))
        except Exception:  # noqa: BLE001
            pass
    np = sys.modules.get("numpy")
    if np is not None:
        try:
            s["np.geterr"] = repr(sorted(np.geterr().items()))
            s["np.printoptions"] = repr(sorted(
                (k, repr(v)) for k, v in np.get_printoptions().items()))
        except Exception:  # noqa: BLE001
            pass
    if "numpy.random" in sys.modules:
        try:
            st = sys.modules["numpy.random"].get_state()
            s["np.random.state"] = f"#{hash(st[1].tobytes())}:{st[2]}"
        except Exception:  # noqa: BLE001
            pass
    rnd = sys.modules.get("random")
    if rnd is not None:
        s["random.state"] = f"#{hash(rnd.getstate())}"
    mpl = sys.modules.get("matplotlib")
    if mpl is not None:
        try:
            rc, orig = mpl.rcParams, mpl.rcParamsOrig
            s["mpl.rcParams"] = repr(sorted(
                k for k in dict.keys(rc) if k != "backend"
                and repr(dict.__getitem__(rc, k))
                != repr(dict.__getitem__(orig, k))))
            backend = dict.__getitem__(rc, "backend")
            sentinel = getattr(sys.modules.get("matplotlib.rcsetup"),
                               "_auto_backend_sentinel", None)
            s["mpl.backend"] = "auto" if backend is sentinel else repr(backend)
        except Exception as e:  # noqa: BLE001
            s["mpl.error"] = repr(e)[:100]
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is not None:
        try:
            s["plt.open_figures"] = len(plt.get_fignums())
        except Exception:  # noqa: BLE001
            pass
    _qt(s)
    s["settings"] = _folder_files(os.environ.get("OGR_SETTINGS_DIR"))
    s["bridges"] = _folder_files(os.environ.get("OGR_BRIDGE_DIR"))
    # Every attribute of every ogr_* module, and of every class it defines:
    # a monkeypatch left in place, a constant changed, a registry that grew.
    for name, m in list(sys.modules.items()):
        if m is None or not name.split(".")[0].startswith("ogr_"):
            continue
        s[f"module:{name}"] = f"@{id(m)}"
        try:
            items = list(vars(m).items())
        except Exception:  # noqa: BLE001
            continue
        for a, v in items:
            if a.startswith("__") or isinstance(v, types.ModuleType):
                continue
            s[f"mod:{name}.{a}"] = value_of(v)
            if isinstance(v, type) and getattr(v, "__module__", None) == name:
                try:
                    citems = list(vars(v).items())
                except Exception:  # noqa: BLE001
                    continue
                for ca, cv in citems:
                    if not ca.startswith("__"):
                        s[f"cls:{name}.{a}.{ca}"] = value_of(cv)
    # Not compared: tells diff() what was imported for the first time.
    s["__modules__"] = frozenset(sys.modules)
    return s


# ---------------------------------------------------------- what is allowed
def _type_of(v) -> str:
    return str(v).split("@", 1)[0]


def ANY(was, now, new) -> bool:  # noqa: N802
    return True


def INSTALLED(was, now, new) -> bool:  # noqa: N802
    """Installed once in the application (None → an object), or installed
    again (an object → another of its type). Removed is a leak."""
    if now in ("None", ABSENT):
        return False
    return was in ("None", ABSENT) or _type_of(was) == _type_of(now)


def first_import(*packages) -> Callable:
    """Allowed in the file where one of ``packages`` was first imported."""
    def rule(was, now, new) -> bool:
        return any(m == p or m.startswith(p + ".")
                   for m in new for p in packages)
    rule.__qualname__ = f"first_import{packages!r}"
    return rule


def added_on_first_import(*packages) -> Callable:
    """Entries only added, never removed, where one of ``packages`` was
    first imported."""
    first = first_import(*packages)

    def rule(was, now, new) -> bool:
        if not (isinstance(was, tuple) and isinstance(now, tuple)):
            return False
        return set(was) <= set(now) and first(was, now, new)
    rule.__qualname__ = f"added_on_first_import{packages!r}"
    return rule


def from_value(value, to=None) -> Callable:
    """Allowed only away from this value, the one before first use, and
    only to ``to`` when given."""
    def rule(was, now, new) -> bool:
        return was == value and (to is None or now == to)
    rule.__qualname__ = f"from_value({value!r}, to={to!r})"
    return rule


def to_windowless(was, now, new) -> bool:
    return "pythonw" in str(now).lower()


@dataclass(frozen=True)
class Allow:
    key: str
    rule: Callable
    why: str


#: A change that matches an entry is not a leak. Every entry says why; a
#: change nobody can explain this way is fixed in the test, not added here.
ALLOWED = (
    # Caches and registries the program keeps on purpose.
    Allow("mod:ogr_core.geometry.ground._envelope", ANY,
          "lru_cache(maxsize=64) of the ground envelope: bounded, and a "
          "function of its arguments only"),
    Allow("mod:ogr_core.geometry.ground._lower_envelope", ANY,
          "the same cache for the lower envelope"),
    Allow("mod:*.icon", ANY,
          "ogr_gui.resources.icons.icon, an lru_cache of icons, under every "
          "module that imports it; a change of theme empties it on purpose"),
    Allow("mod:ogr_api.coerce._HINTS", ANY,
          "the type hints of each operation, read once and kept"),
    Allow("cls:ogr_gui.main_window.MainWindow._sessions", ANY,
          "the windows open in the process. They stay alive between files "
          "on purpose since 0.1.302 (ogr_gui/gc_guard.py; audit D-b)"),
    Allow("mod:ogr_gui.gc_guard._kept", ANY,
          "garbage the collector found on another thread, waiting to be "
          "freed on the main one: the runner frees it before every file"),
    # Installed once in the application.
    Allow("mod:ogr_gui.wheel_guard._guard", INSTALLED,
          "the wheel guard, installed in the application by the first "
          "window; test_wheel_guard_v1285 installs it again"),
    Allow("mod:ogr_gui.button_floor._floor", INSTALLED,
          "the button floor, installed in the application by the first "
          "window"),
    Allow("mod:ogr_gui.themes._ORIGINAL_PALETTE", INSTALLED,
          "the application's palette, captured the first time a theme is "
          "applied, to go back to"),
    # What a library does to the process the first time it is imported.
    Allow("env:PATH", first_import("PySide6"),
          "PySide6 puts its folder first on PATH when imported, for its "
          "DLLs (PySide6/__init__.py)"),
    Allow("env:PYSIDE6_OPTION_PYTHON_ENUM", first_import("PySide6"),
          "set by PySide6 when imported"),
    Allow("env:QT_API", first_import("qtpy"),
          "qtpy records the binding it picked (qtpy/__init__.py)"),
    Allow("qt.QFileDialog.*", first_import("qtpy"),
          "qtpy, which QtAwesome brings, wraps QFileDialog's four static "
          "dialogs in Python functions when imported (qtpy/QtWidgets.py)"),
    Allow("sys.meta_path", first_import("six"),
          "six registers its importer for six.moves"),
    Allow("warnings.filters", added_on_first_import("numpy", "scipy"),
          "numpy ignores its 'size changed' warnings (numpy/__init__.py); "
          "scipy.special always shows SpecialFunctionWarning "
          "(scipy/special/_sf_error.py)"),
    Allow("random.state", first_import("rich"),
          "rich draws 24 bits from the module's generator when imported "
          "(rich/style.py). The program never uses that generator: each "
          "search has its own since 0.1.119"),
    # What the first use settles, once.
    Allow("mpl.backend", from_value("auto"),
          "matplotlib resolves its automatic backend the first time it "
          "needs one"),
    Allow("mpl.rcParams", from_value("[]", to="['backend_fallback']"),
          "matplotlib.use(), which the program calls before its first chart "
          "(ogr_gui/xy_chart.py and six more), always sets backend_fallback "
          "to False (matplotlib/__init__.py). Only that key, and only from "
          "a clean rcParams: any other one changed is still a leak"),
    Allow("mp.start_method", from_value("None"),
          "the first process pool fixes the default start method"),
    Allow("mp.executable", to_windowless,
          "ogr_slip2d.processes.windowless_children points multiprocessing "
          "at pythonw.exe before every pool when there is no console: the "
          "program's choice, the same every time"),
)


def _allowed(key, was, now, new) -> bool:
    return any(fnmatch.fnmatchcase(key, a.key) and a.rule(was, now, new)
               for a in ALLOWED)


# -------------------------------------------------------------------- diff
def _first_seen(key, now):
    """The value to hold a key seen for the first time against, or None
    when its being new is no change (see the module docstring)."""
    if FROM_A_TEST in str(now):
        return ABSENT
    if key.startswith("env:"):
        return ABSENT
    if key.startswith("mod:"):
        module, _, name = key[4:].rpartition(".")
        default = import_default(module, name)
        if default is not None and default != now:
            return default
    return None


def diff(before: dict, after: dict) -> list:
    """``(key, before, after)`` for every change that is a leak."""
    new = (after.get("__modules__", frozenset())
           - before.get("__modules__", frozenset()))
    out = []
    for key, now in after.items():
        if key.startswith("__"):
            continue
        if key in before:
            was = before[key]
            if was == now:
                continue
        else:
            was = _first_seen(key, now)
            if was is None:
                continue
        if not _allowed(key, was, now, new):
            out.append((key, was, now))
    for key, was in before.items():
        if key.startswith("__") or key in after:
            continue
        if not _allowed(key, was, ABSENT, new):
            out.append((key, was, ABSENT))
    return out


def _short(v, n: int = 100) -> str:
    s = v if isinstance(v, str) else repr(v)
    return s if len(s) <= n else s[:n - 1] + "…"


def describe(key, was, now) -> str:
    """One line for a leak: ``key: before → after``."""
    if isinstance(was, tuple) or isinstance(now, tuple):
        a = set(was) if isinstance(was, tuple) else set()
        b = set(now) if isinstance(now, tuple) else set()
        bits = ([f"-{_short(x, 80)}" for x in sorted(a - b)[:4]]
                + [f"+{_short(x, 80)}" for x in sorted(b - a)[:4]])
        return f"{key}: " + "; ".join(bits)
    return f"{key}: {_short(was)} → {_short(now)}"


# ------------------------------------------------------- helpers for tests
@contextlib.contextmanager
def root_logging_kept():
    """The root logger as it was, whatever the block configures.

    Two callers configure it, both rightly in a process of their own and
    both called in the test process: ``mcp``'s ``MCPServer`` when it is
    built (``basicConfig(level=INFO, handlers=[RichHandler])``,
    mcp/server/mcpserver/utilities/logging.py) and ``ogr_mcp.cli.main``.
    ``basicConfig`` does nothing once the root has a handler, so the first
    file to call either configured logging for every file after it, and
    hid the others (audit D-f).
    """
    import logging
    root = logging.getLogger()
    level, handlers = root.level, list(root.handlers)
    try:
        yield
    finally:
        for h in list(root.handlers):
            if h not in handlers:
                root.removeHandler(h)
                h.close()
        for h in handlers:
            if h not in root.handlers:
                root.addHandler(h)
        root.setLevel(level)
