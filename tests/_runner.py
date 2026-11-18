# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The test runner of OGR Slip2D: the suite's runner
(``ogr_core.testing.runner``), pointed at this repository.

    QT_QPA_PLATFORM=offscreen python tests/_runner.py --jobs 4   # a release
    QT_QPA_PLATFORM=offscreen python tests/_runner.py            # in series (CI)
    python tests/_runner.py --fast --jobs 4                      # development
    python tests/_runner.py transient -k erfc --list             # a part

DRAFT of phase 1 of OGR Core 0.2.0, written to check that the shared runner
carries everything this program's own runner did (v0.1.471). What used to
be constants and imports of that runner is here what this repository says
of itself: its own packages, the core it shares and pins, its hooks for Qt,
the two folders every run gets, its part of the leak check's allow-list,
the name of its machine files and the owner's rule about the serial run.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
# This tree first, before any editable install can answer for it (see
# foreign_packages in the runner).
sys.path.insert(0, str(_ROOT))

from ogr_core.testing import leaks, runner  # noqa: E402

#: The packages this repository contains, and the one it takes from the core.
OWN = ("ogr_slip2d", "ogr_gui", "ogr_cli", "ogr_api", "ogr_mcp")
SHARED = ("ogr_core",)
#: The name this repository's durations are kept under on the machine.
LABEL = "ogr-slip2d"
#: A release runs the whole suite in chunks (``--jobs 4``), and in series
#: once every this many commits: the owner's decision (v0.1.376), in
#: AGENTS.md with the same number.
SERIAL_EVERY = 100
#: The folders every run gets, empty and of its own (v0.1.207, v0.1.289):
#: the discovery folder of an open window, and the saved preferences.
RUN_FOLDERS = {"OGR_BRIDGE_DIR": "bridges", "OGR_SETTINGS_DIR": "settings"}


def to_windowless(was, now, new) -> bool:
    return "pythonw" in str(now).lower()


#: This program's part of the leak check's allow-list; the suite's own
#: (the core's caches, what a library does on import) is in
#: ``ogr_core.testing.leaks.ALLOWED``. Every entry says why.
ALLOWED = (
    # Caches and registries the program keeps on purpose.
    leaks.Allow("mod:*.icon", leaks.ANY,
                "ogr_gui.resources.icons.icon, an lru_cache of icons, under "
                "every module that imports it; a change of theme empties it "
                "on purpose"),
    leaks.Allow("mod:ogr_api.coerce._HINTS", leaks.ANY,
                "the type hints of each operation, read once and kept"),
    leaks.Allow("cls:ogr_gui.main_window.MainWindow._sessions", leaks.ANY,
                "the windows open in the process. They stay alive between "
                "files on purpose since 0.1.302 (ogr_gui/gc_guard.py; audit "
                "D-b)"),
    leaks.Allow("mod:ogr_gui.gc_guard._kept", leaks.ANY,
                "garbage the collector found on another thread, waiting to "
                "be freed on the main one: the runner frees it before every "
                "file"),
    leaks.Allow("mod:ogr_gui.core_messages._CATALOGUE", leaks.FILLED_ONCE,
                "the table of every message code, filled from constant "
                "tables the first time a message is shown. In the serial run "
                "that is in the file that imports the module, and a new key "
                "is no change; a chunk of --jobs can import it in one file "
                "and fill it in another (v0.1.375)"),
    # Installed once in the application.
    leaks.Allow("mod:ogr_gui.wheel_guard._guard", leaks.INSTALLED,
                "the wheel guard, installed in the application by the first "
                "window; test_wheel_guard_v1285 installs it again"),
    leaks.Allow("mod:ogr_gui.button_floor._floor", leaks.INSTALLED,
                "the button floor, installed in the application by the "
                "first window"),
    leaks.Allow("mod:ogr_gui.themes._ORIGINAL_PALETTE", leaks.INSTALLED,
                "the application's palette, captured the first time a theme "
                "is applied, to go back to"),
    # What the program's first use settles, once.
    leaks.Allow("mpl.rcParams",
                leaks.from_value("[]", to="['backend_fallback']"),
                "matplotlib.use(), which the program calls before its first "
                "chart (ogr_gui/xy_chart.py and six more), always sets "
                "backend_fallback to False (matplotlib/__init__.py). Only "
                "that key, and only from a clean rcParams: any other one "
                "changed is still a leak"),
    leaks.Allow("mp.executable", to_windowless,
                "ogr_slip2d.processes.windowless_children points "
                "multiprocessing at pythonw.exe before every pool when there "
                "is no console: the program's choice, the same every time"),
)


def _install_gc_guard() -> None:
    # v0.1.302 (D310) — cyclic garbage found on a worker thread (a process
    # pool's, a compute thread's) is held for the main thread instead of
    # handed to shiboken's deferred deletion, which aborted the suite about
    # one run in two (see ogr_gui/gc_guard.py). Called once the trees are
    # checked: it imports from the tree just checked.
    from ogr_gui import gc_guard
    gc_guard.install()


def _release_garbage() -> None:
    from ogr_gui import gc_guard
    gc_guard.release()


def _release_windows() -> int:
    """Delete the windows with no parent the tests left alive, with Python
    alive, before the interpreter's shutdown; returns how many (v0.1.422,
    D370).

    At shutdown PySide's atexit hook deletes every wrapped object one by
    one, in no order a window's children can rely on. On Linux, a dialog a
    test kept alive through a cycle of its own (a lambda connected to it)
    ended there next to an object held by a QSharedPointer of Qt's: «shared
    QObject was deleted directly», then a segfault. Deleted here, each one
    takes its children with it in Qt's own order. Only windows without a
    parent: a popup menu is a top-level widget too, but its window owns it.
    Nothing to do in a run that never imported Qt."""
    if "PySide6.QtWidgets" not in sys.modules:
        return 0
    import shiboken6
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return 0
    released = 0
    for window in [w for w in app.topLevelWidgets() if w.parent() is None]:
        if shiboken6.isValid(window):
            shiboken6.delete(window)
            released += 1
    return released


HOOKS = runner.Hooks(before_run=_install_gc_guard,
                     before_file=_release_garbage,
                     after_run=_release_windows)


def pinned() -> dict:
    """``{"ogr_core": version}`` as ``pyproject.toml`` pins it."""
    version = runner.pinned_from_pyproject(_ROOT / "pyproject.toml", "ogr-core")
    return {"ogr_core": version} if version else {}


def config() -> dict:
    return {"own": OWN, "shared": SHARED, "pinned": pinned(), "hooks": HOOKS,
            "allowed": ALLOWED, "run_folders": RUN_FOLDERS, "label": LABEL,
            "serial_every": SERIAL_EVERY}


def main(patterns=(), k=None, list_only=False, **options) -> int:
    """This repository's run, for a test that wants to drive it."""
    return runner.main(_TESTS, patterns, k, list_only, **config(), **options)


if __name__ == "__main__":
    if not pinned():
        print("pyproject.toml does not pin ogr-core to a tag or an exact "
              "version: nothing to check the shared core against.")
        sys.exit(2)
    sys.exit(runner.cli(_TESTS, **config()))
