# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.422 (D370, D394) — the suite ends through the interpreter's own
shutdown on every platform, and nothing a test leaves takes the run down.

D370. From v0.1.276 the Linux CI died after the totals («QObject: shared
QObject was deleted directly», 139). gdb placed it in PySide's atexit hook
(``destroyQCoreApplication`` → ``BindingManager::visitAllPyObjects`` →
``QObject::~QObject``): at shutdown every wrapped object is deleted one by
one, and a dialog with no parent that a test kept alive through a cycle of
its own (a lambda connected to it) met one held by a QSharedPointer of
Qt's. Bisected on the CI to five tests of ``test_assign_water_surface_v195``
and ``test_transient_no_stages_v1306``, not deterministically. Deleting the
parentless windows with Python alive before the end removes it, so the
runner does that (``_release_windows``) and, by the owner's decision
(2026-11-04), ends with ``sys.exit`` on every platform again.

D394. ``TestAKilledJobLeavesNoFolder`` (v0.1.409) started its process in
the suite's own process group, and ``Job.cancel`` kills the GROUP on POSIX
(``os.killpg``): on Linux it took the whole suite with it, and the CI step
and its log, from v0.1.409 on. The program is not affected: JobManager
starts its workers in a session of their own.

The invariants:

* ``_release_windows`` deletes a parentless dialog a cycle keeps alive, and
  a window's popup menu goes with its window, not on its own;
* the runner, run on one of the files that left such a dialog, ends with 0
  through the normal shutdown (the case that died on Linux);
* the killed-job test starts its process in a session of its own, read
  from its source; and on POSIX, ``Job``'s kill of such a process leaves the
  caller alive.
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent


def _python(code: str, **env) -> subprocess.CompletedProcess:
    tmp = tempfile.mkdtemp(prefix="ogr_test_release_")
    full = dict(os.environ, TEMP=tmp, TMP=tmp, TMPDIR=tmp,
                QT_QPA_PLATFORM="offscreen", **env)
    try:
        return subprocess.run([sys.executable, "-c", code], env=full,
                              cwd=str(_TESTS.parent), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_RELEASE = r'''
import sys
sys.path.insert(0, "tests")
import shiboken6
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMenu
import _runner
app = QApplication([])
dialog = QDialog()                        # no parent, kept by a cycle
dialog.finished.connect(lambda *_: dialog.close())
window = QMainWindow()
menu = QMenu(window)                      # a popup: top-level, but owned
window.show()
menu.addAction("x")
print("released", _runner._release_windows())
print("dialog", shiboken6.isValid(dialog))
print("window", shiboken6.isValid(window))
print("menu", shiboken6.isValid(menu))
'''


class TestTheRunnerReleasesTheWindows:

    def test_the_parentless_ones_and_their_children(self):
        run = _python(_RELEASE)
        assert run.returncode == 0, (run.returncode, run.stderr[-2000:])
        lines = run.stdout.splitlines()
        assert "released 2" in lines, lines
        assert "dialog False" in lines and "window False" in lines, lines
        # the menu went with its window: deleted by it, not on its own
        assert "menu False" in lines, lines

    def test_a_file_that_left_a_dialog_ends_with_zero(self):
        """One of the tests that died with 135 on Linux, run alone by the
        real runner, through the interpreter's own shutdown."""
        run = _python(
            "import runpy, sys; "
            f"sys.argv = [{str(_TESTS / '_runner.py')!r}, "
            "'test_assign_water_surface_v195', '-k', "
            "'test_select_all_and_clear_all']; "
            f"runpy.run_path({str(_TESTS / '_runner.py')!r}, "
            "run_name='__main__')")
        assert "Passed: 1    Failed: 0" in run.stdout, run.stdout[-1500:]
        assert run.returncode == 0, (run.returncode, run.stderr[-2000:])
        assert "shared QObject" not in run.stderr


class TestAKilledJobKillsOnlyItsSession:

    def test_the_test_starts_its_process_in_a_session_of_its_own(self):
        tree = ast.parse((_TESTS / "test_slice_store_parallel_v1409.py")
                         .read_text(encoding="utf-8"))
        popens = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", None) == "Popen"]
        assert popens
        assert all("start_new_session" in {k.arg for k in n.keywords}
                   for n in popens), [ast.unparse(n) for n in popens]

    def test_on_posix_the_caller_survives(self):
        if sys.platform == "win32":
            pytest.skip("os.killpg is POSIX: Windows kills a tree, not a group")
        code = (
            "import subprocess, sys, tempfile\n"
            "from pathlib import Path\n"
            "from ogr_api.jobs import Job\n"
            "p = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)'], start_new_session=True)\n"
            "with tempfile.TemporaryDirectory() as d:\n"
            "    Job('j', 'analysis', 'p', Path(d), p, 'h', {}).cancel()\n"
            "print('alive', p.poll() is not None)\n")
        run = _python(code)
        assert run.returncode == 0, (run.returncode, run.stderr[-1500:])
        assert "alive True" in run.stdout, run.stdout
