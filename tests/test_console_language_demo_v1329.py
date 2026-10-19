# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.329 (D326, D327, D328) — the calculation processes open no window, the
language switches Qt's own texts at once, and the demo slope declares the
direction of its own geometry.

The defects, seen in the third test of the interface:

* **D326 (H11).** Started without a console (a detached start, a shortcut),
  Compute put three or four terminal windows in front of the program, one
  of them maximised in the statistics: on Windows, a process with no
  console that starts ``python.exe`` children gives each one a console of
  its own; the jobs of the API start their worker without one too
  (``CREATE_NO_WINDOW``). By decision of the owner the search points
  multiprocessing at ``pythonw.exe`` in that case only, just before it
  creates its pool (``ogr_slip2d.processes``), whoever started it. The
  numbers cannot move: the split of a search reproduces the sequential one
  bit for bit (``test_parallel_search_v197``), and that identity is checked
  again here with the windowless interpreter.
* **D327 (H10).** Qt's catalogue (D302) was installed once, at start, so
  after choosing English the notice «Language changed…» had «Aceptar». By
  decision of the owner the catalogue is switched when the language is
  saved, before the notice.
* **D328 (H5).** The demo declared «Right to Left» while its ground is
  higher on the left (y = 25 against 15), and every run said so. By
  decision of the owner it declares «Left to Right». Its factor of safety
  cannot depend on it: the declaration is read by the water thrust of a
  tension crack, the direction of a support and the starting face of Path
  Search, and the demo has none of the three. That is an identity, checked
  here by computing both declarations in one process.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


# ----------------------------------------------------------------------
class TestTheChildInterpreter:
    def _folder(self, with_pythonw):
        folder = tempfile.mkdtemp(prefix="ogr_test_exe_")
        for name in ("python.exe",) + (("pythonw.exe",) if with_pythonw
                                       else ()):
            Path(folder, name).write_bytes(b"")
        return os.path.join(folder, "python.exe")

    def test_without_a_console_on_windows_it_is_pythonw(self):
        from ogr_slip2d.processes import child_executable
        exe = self._folder(with_pythonw=True)
        got = child_executable(platform="win32", executable=exe, console=0,
                               frozen=False)
        assert got == os.path.join(os.path.dirname(exe), "pythonw.exe")

    def test_otherwise_nothing_changes(self):
        from ogr_slip2d.processes import child_executable
        exe = self._folder(with_pythonw=True)
        # a console to share, another system, a frozen build
        assert child_executable(platform="win32", executable=exe,
                                console=1234, frozen=False) is None
        assert child_executable(platform="linux", executable=exe,
                                console=0, frozen=False) is None
        assert child_executable(platform="win32", executable=exe,
                                console=0, frozen=True) is None
        # and no pythonw next to the interpreter
        bare = self._folder(with_pythonw=False)
        assert child_executable(platform="win32", executable=bare,
                                console=0, frozen=False) is None

    def test_it_is_what_multiprocessing_starts(self):
        import multiprocessing.spawn as spawn
        from ogr_slip2d.processes import windowless_children
        exe = self._folder(with_pythonw=True)
        before = spawn.get_executable()
        try:
            got = windowless_children(platform="win32", executable=exe,
                                      console=0, frozen=False)
            assert got is not None
            assert spawn.get_executable() == got
        finally:
            spawn.set_executable(before)
        assert spawn.get_executable() == before

    def test_a_split_search_under_it_is_bit_identical(self):
        """The real pythonw.exe, the real pool: the same evaluations, in
        the same order, to the last bit, and no fallback to one process."""
        import multiprocessing.spawn as spawn
        from ogr_slip2d.processes import child_executable
        import test_parallel_search_v197 as par
        exe = child_executable(platform=sys.platform, console=0,
                               frozen=False)
        if exe is None:
            pytest.skip("no pythonw.exe on this system")
        before = spawn.get_executable()
        try:
            spawn.set_executable(exe)
            p = par._project()
            split = par._search(p, 2).run(p)
        finally:
            spawn.set_executable(before)
        assert not any("ran in one" in n for n in split.notes), split.notes
        p = par._project()
        alone = par._search(p, 1).run(p)
        assert par._fingerprint(split) == par._fingerprint(alone)


    def test_the_search_asks_before_every_pool(self):
        """Where it is applied: the pool of the search, whoever runs it
        (the window, the MCP server, the worker of a job, a script)."""
        import ogr_slip2d.processes as processes
        import test_parallel_search_v197 as par
        calls = []
        raw = processes.windowless_children
        processes.windowless_children = lambda **k: calls.append(k)
        try:
            p = par._project()
            par._search(p, 2).run(p)
        finally:
            processes.windowless_children = raw
        assert len(calls) == 1, calls


# ----------------------------------------------------------------------
def _yes():
    box = QMessageBox(QMessageBox.Question, "t", "x",
                      QMessageBox.Yes | QMessageBox.No)
    return box.button(QMessageBox.Yes).text()


class TestTheLanguageSwitchesQtsTextsAtOnce:
    def test_the_notice_and_the_boxes_after_it(self):
        import test_language_saved_v1289 as saved
        from ogr_gui.main_window import MainWindow
        seen = []
        raw = QMessageBox.__dict__.get("information")
        with saved._Fresh():
            w = MainWindow()
            QMessageBox.information = staticmethod(
                lambda *a, **k: seen.append(_yes()))
            try:
                w._apply_language("es")
                assert _yes() == "&Sí"
                w._apply_language("en")
                assert _yes() == "&Yes"
                # what the notice itself was shown with, each time
                assert seen == ["&Sí", "&Yes"], seen
            finally:
                if raw is None:
                    del QMessageBox.information
                else:
                    QMessageBox.information = raw
                w.close()
        # rule 5: nothing of it is left installed
        assert _yes() == "&Yes"

    def test_a_switch_replaces_and_does_not_pile_up(self):
        from ogr_gui.qt_catalog import reset_qt_translator, switch_qt_translator
        app = _app()
        try:
            first = switch_qt_translator(app, "es")
            second = switch_qt_translator(app, "es")
            assert first is not None and second is not None
            assert first is not second
            reset_qt_translator(app)
            # had the first one stayed, the Spanish would still be there
            assert _yes() == "&Yes"
        finally:
            reset_qt_translator(app)


# ----------------------------------------------------------------------
class TestTheDemoDeclaresItsGeometry:
    def test_left_to_right_and_no_contradiction(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.analysis_runner import _failure_direction_note
        from ogr_slip2d.failure_direction import (is_left_to_right,
                                                  model_crest_is_on_the_right)
        p = build_demo_project()
        assert p.settings.units.failure_direction == \
            FailureDirection.LEFT_TO_RIGHT
        assert is_left_to_right(p)
        assert not model_crest_is_on_the_right(p)
        assert _failure_direction_note(p) == []

    def test_its_factor_does_not_depend_on_it(self):
        """The identity of the docstring: both declarations, one process."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.analysis_runner import run_analysis
        fos = {}
        for direction in (FailureDirection.LEFT_TO_RIGHT,
                          FailureDirection.RIGHT_TO_LEFT):
            p = build_demo_project()
            p.settings.units.failure_direction = direction
            results = run_analysis(p).results
            fos[direction] = {mid: repr(r.critical.fos)
                              for mid, r in results.items()
                              if r is not None and r.critical is not None}
        assert fos[FailureDirection.LEFT_TO_RIGHT]
        assert fos[FailureDirection.LEFT_TO_RIGHT] == \
            fos[FailureDirection.RIGHT_TO_LEFT], fos
