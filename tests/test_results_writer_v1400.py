# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.400 (D385) — the results file of a Compute is written off the window's
thread, and the window waits for it before the next one and before closing.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.397 (DUDA 3) saw the window "not responding" for
one to three minutes after a big Compute. ``_on_compute_done`` called
``save_results`` on the window's thread: one HDF5 group and one compressed
dataset per surface. The test's ``.h5`` (207 MB) was written at the very end
of the freeze, and the compute audit had measured 47 s for the Bishop of
K03. The gate of this version
(``_auditoria/P8_interfaz/d385_guardado_h5.py``, the same result): 55 s
inline and 55 s on a thread, a 50 ms heartbeat on the main thread never
more than 0.095 s apart, and the same bytes.

1. **On screen first:** with a display, the result is in the window while
   its file is still being written, and the file that appears is,
   byte for byte, the one ``save_results`` writes.
2. **One file at a time:** a second write starts only after the first has
   finished.
3. **Closing waits for it** (the owner's decision), and leaves neither a
   ``.tmp`` nor a running thread.
4. **A failed write is said** in the status bar, leaves no ``.tmp``, and
   leaves the previous results file as it was (the write goes to the
   ``.tmp`` and only a finished one replaces it).
5. **Without a display nothing changes:** the file is written before
   ``_on_compute_done`` returns, the same bytes as ``save_results``.

The writes are held by an event the test releases, never by a clock. Where
a thread has to release one while the window waits (2 and 3), a short timer
does it, and the assertion is about the order of events, not about time.
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_RESULTS = {}


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _results():
    """A small Compute of the demo model, computed once for the file."""
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


def _window(threaded: bool):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w.act_load_demo()
    w._tasks_threaded = threaded
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


@contextlib.contextmanager
def _held_writes(log, gate=None):
    """``write_results_file`` logged, and held at its start until ``gate``
    is set (restored on exit)."""
    import ogr_gui.background as bg
    real = bg.write_results_file

    def held(path, result, project_id):
        log.append(("start", Path(path).name))
        if gate is not None:
            gate.wait(10)
        out = real(path, result, project_id)
        log.append(("end", Path(path).name))
        return out
    bg.write_results_file = held
    try:
        yield
    finally:
        bg.write_results_file = real


def _reference_bytes(result, folder: Path, project_id: str) -> bytes:
    from ogr_core.project import save_results
    ref = folder / "reference.h5"
    save_results(ref, result, project_id=project_id)
    return ref.read_bytes()


# ======================================================================
class TestTheWindowWritesOffItsThread:
    """Invariants 1 and 2."""

    def test_on_screen_first_then_the_same_file(self):
        results = _results()
        first = next(iter(results.values()))
        w = _window(threaded=True)
        log, gate = [], threading.Event()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "model.h5"
                w.project.results_path = path
                with _held_writes(log, gate):
                    w._on_compute_done(results)
                    assert w.last_search_result is first
                    assert not path.exists(), "the file was written first"
                    writer = w._results_writer
                    assert writer is not None and writer.isRunning()
                    gate.set()
                    w._wait_results_writer()
                assert w._results_writer is None
                assert not writer.isRunning()
                assert path.exists()
                assert not (Path(tmp) / "model.h5.tmp").exists()
                assert path.read_bytes() == _reference_bytes(
                    first, Path(tmp), w.project.id)
        finally:
            gate.set()
            _done(w)

    def test_one_file_at_a_time(self):
        results = _results()
        first = next(iter(results.values()))
        w = _window(threaded=True)
        log, gate = [], threading.Event()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                w.project.results_path = Path(tmp) / "a.h5"
                with _held_writes(log, gate):
                    w._on_compute_done(results)
                    release = threading.Timer(0.2, gate.set)
                    release.start()
                    try:
                        w._write_results(Path(tmp) / "b.h5", first)
                        w._wait_results_writer()
                    finally:
                        release.cancel()
                assert log == [("start", "a.h5"), ("end", "a.h5"),
                               ("start", "b.h5"), ("end", "b.h5")], log
        finally:
            gate.set()
            _done(w)


class TestClosingWaitsForTheFile:
    """Invariant 3."""

    def test_close(self):
        results = _results()
        w = _window(threaded=True)
        log, gate = [], threading.Event()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "model.h5"
                w.project.results_path = path
                with _held_writes(log, gate):
                    w._on_compute_done(results)
                    writer = w._results_writer
                    release = threading.Timer(0.2, gate.set)
                    release.start()
                    try:
                        w.project.is_dirty = False
                        w.close()
                    finally:
                        release.cancel()
                assert path.exists(), "the window closed before the file"
                assert not (Path(tmp) / "model.h5.tmp").exists()
                assert not writer.isRunning()
                assert w._results_writer is None
        finally:
            gate.set()
            w.deleteLater()


class TestAFailedWriteIsSaid:
    """Invariant 4."""

    def test_the_bar_says_it_and_nothing_is_left(self):
        import ogr_core.project as project_pkg
        results = _results()
        w = _window(threaded=False)
        real = project_pkg.save_results

        def failing(path, result, project_id=""):
            Path(path).write_bytes(b"half a file")
            raise OSError("disk full")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "model.h5"
                path.write_bytes(b"the previous results")
                w.project.results_path = path
                project_pkg.save_results = failing
                try:
                    w._on_compute_done(results)
                finally:
                    project_pkg.save_results = real
                assert path.read_bytes() == b"the previous results"
                assert not (Path(tmp) / "model.h5.tmp").exists()
                assert "disk full" in w.ogr_status.currentMessage()
        finally:
            _done(w)


class TestWithoutADisplayNothingChanges:
    """Invariant 5."""

    def test_written_before_it_returns(self):
        results = _results()
        first = next(iter(results.values()))
        w = _window(threaded=False)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "model.h5"
                w.project.results_path = path
                w._on_compute_done(results)
                assert w._results_writer is None
                assert path.read_bytes() == _reference_bytes(
                    first, Path(tmp), w.project.id)
        finally:
            _done(w)
