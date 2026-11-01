# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.405 (D390) — a calculation does not start while the results file of
the last Compute is still being written.

WHAT INVARIANT THIS PROTECTS.

Since 0.1.400 (D385) a Compute's ``.h5`` is written on a thread, and the
window answers at once. The interface test of 0.1.402 (hallazgo 5) then
chained calculations for six minutes after a serial Compute, and its file
never appeared. The writer shares the interpreter with the calculation's
thread, and makes tens of thousands of short calls into HDF5: measured on
the Bishop result of ACADS 1(a) at 25 x 25 x 12, 24.6 s alone and 122.3 s
with a serial Compute running
(``_auditoria/P8_interfaz/h5_escritor_concurrente.py``). Before 0.1.400 the
file was always written before the next calculation; it is again, through
``run_task``, the door of every calculation of the window.

1. **The file first:** with a write held by an event, a calculation asked
   for meanwhile starts only after the file is written, and a dialog says
   what the window is waiting for.
2. **Nothing to wait for, no wait:** with no write running, the calculation
   starts at once and no such dialog appears.

The write is held by an event a short timer releases while the window
waits; what is checked is the order of events, not a time.
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_RESULTS = {}


def _results():
    if not _RESULTS:
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import run_analysis
        p = build_demo_project()
        s = p.settings.search
        s.grid_nx = s.grid_ny = 2
        s.radius_increment = 2
        p.settings.advanced.parallel_search = False
        _RESULTS["run"] = run_analysis(p, ["bishop_simplified"]).results
    return _RESULTS["run"]


def _window():
    from PySide6.QtWidgets import QApplication
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    w.act_load_demo()
    w._tasks_threaded = True
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


@contextlib.contextmanager
def _held_writes(log, gate):
    import ogr_gui.background as bg
    real = bg.write_results_file

    def held(path, result, project_id):
        gate.wait(10)
        out = real(path, result, project_id)
        log.append("file written")
        return out
    bg.write_results_file = held
    try:
        yield
    finally:
        bg.write_results_file = real


@contextlib.contextmanager
def _dialog_titles(titles):
    import ogr_gui.dialogs.misc_dialogs as md
    real = md.TaskProgressDialog

    class Spy(real):
        def __init__(self, parent=None, title="", on_cancel=None):
            titles.append(title)
            super().__init__(parent, title, on_cancel)
    md.TaskProgressDialog = Spy
    try:
        yield
    finally:
        md.TaskProgressDialog = real


class TestTheFileFirst:

    def test_a_calculation_waits_for_the_file(self):
        from ogr_gui.background import run_task
        from ogr_gui.i18n import tr
        w = _window()
        log, titles, gate = [], [], threading.Event()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                w.project.results_path = Path(tmp) / "model.h5"
                with _held_writes(log, gate), _dialog_titles(titles):
                    w._on_compute_done(_results())
                    assert w._results_writer.isRunning()
                    release = threading.Timer(0.2, gate.set)
                    release.start()
                    try:
                        run_task(w, lambda cb: log.append("calculation"),
                                 "Compute")
                    finally:
                        release.cancel()
                assert log == ["file written", "calculation"], log
                assert tr("Saving the results file...") in titles, titles
                assert (Path(tmp) / "model.h5").exists()
        finally:
            gate.set()
            _done(w)

    def test_nothing_to_wait_for(self):
        from ogr_gui.background import run_task
        from ogr_gui.i18n import tr
        w = _window()
        log, titles = [], []
        try:
            with _dialog_titles(titles):
                run_task(w, lambda cb: log.append("calculation"), "Compute")
            assert log == ["calculation"]
            assert tr("Saving the results file...") not in titles, titles
        finally:
            _done(w)
