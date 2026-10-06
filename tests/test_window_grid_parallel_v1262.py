# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.262, defect D247 — a Grid Search started from the window is split
across processes like any other, and when it cannot be, it says so.

Invariants protected:

1. **The window's project reaches the workers.** A project bound to the
   main window carries two listeners in ``_listeners`` — the canvas's
   lambda and the window's own method — and they were the only part of it
   that did not pickle. ``_parallel_grid_run`` pickles the project into
   every batch, failed on the first, and fell back to one process: so
   *Compute* had run every grid in series since the parallel search
   existed (6.4 s against 3.5 s on the demo, measured in 0.1.235). The
   batches now carry ``copies.shippable_copy``: shallow, without the
   attributes of ``NOT_COPIED``, its region cache warm, the original's
   listeners untouched.
2. **The parallel answer is the sequential one, bit for bit** — the same
   evaluations in the same order, counts, critical surface and notes — on
   the window's own project, through the search and through the window's
   ``_ComputeWorker`` running as a real thread.
3. **A pool that fails says so.** Falling back to one process is still
   right (``test_parallel_search_v197``); doing it in silence was not. The
   search records a note with the reason, and a healthy pool records none.
4. **The program's main module loads no Qt.** On Windows each worker
   starts by re-importing the parent's main module, which for
   ``python -m ogr_gui`` is ``ogr_gui/__main__.py``: its PySide6 and window
   imports cost every worker 1.4 s before it did anything. They are made
   inside the functions now.

ANCHOR. Identity against the sequential run, which the parallel search has
been held to since v0.1.97; the premise is checked on a real window.

COST. Two grids of 7 x 7 centres and 11 radii (539 circles, over the 400
that start a pool) at 12 slices, one of them through a QThread, and a
subprocess import. Some 20-30 s, most of it starting worker processes.
Skipped where the machine would run the grid in a single process.
"""
from __future__ import annotations

GRID_NX = GRID_NY = 6
RADIUS_INCREMENT = 10
NUM_SLICES = 12


def _model():
    """The Ej_2 geometry of ``test_parallel_search_v197``, dry, with its
    grid."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("D247")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=12.0,
                                                 friction_angle=28.0))]
    p.resolve_regions()
    s = p.settings.search
    s.search_method, s.surface_type = "grid", "circular"
    s.grid_x_min, s.grid_x_max = 20.0, 60.0
    s.grid_y_min, s.grid_y_max = 75.0, 115.0
    s.grid_nx, s.grid_ny = GRID_NX, GRID_NY
    s.radius_increment = RADIUS_INCREMENT
    p.settings.methods.num_slices = NUM_SLICES
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.advanced.parallel_cpu_percent = 100
    return p


def _window_project():
    """The model bound to a real main window: it gets the window's and the
    canvas's listeners, which is what a project opened in the program
    carries."""
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    p = _model()
    w._attach_project(p)
    return w, p


def _needs_a_pool(p):
    import pytest
    from ogr_slip2d.search import _worker_count
    n = (GRID_NX + 1) * (GRID_NY + 1) * (RADIUS_INCREMENT + 1)
    if _worker_count(p, n) < 2:
        pytest.skip("this machine runs the grid in a single process")


class _Spy:
    """Records whether ``_parallel_grid_run`` returned a result; restores
    the module attribute however the test ends."""

    def __enter__(self):
        import ogr_slip2d.search as S
        self._S, self._real, self.used = S, S._parallel_grid_run, []

        def spy(*a, **k):
            out = self._real(*a, **k)
            self.used.append(out is not None)
            return out

        S._parallel_grid_run = spy
        return self

    def __exit__(self, *exc):
        self._S._parallel_grid_run = self._real
        return False


def _signature(r):
    return ([repr(e.fos) for e in r.evaluations], r.valid_count,
            r.invalid_count, repr(r.critical.fos), list(r.notes))


def _sequential():
    from ogr_slip2d.analysis_runner import build_search
    p = _model()
    p.settings.advanced.parallel_search = False
    return build_search(p, "bishop_simplified").run(p)


# ======================================================================
class TestTheWindowProjectReachesTheWorkers:
    """Invariants 1 and 2."""

    def test_the_premise_the_window_project_does_not_pickle(self):
        """And the shippable copy does, leaving the window's listeners
        where they were."""
        import pickle
        w, p = _window_project()
        assert len(p._listeners) >= 2
        try:
            pickle.dumps(p)
            raise AssertionError("the window's project pickled")
        except AssertionError:
            raise
        except Exception:  # noqa: BLE001 - the premise is that it fails
            pass
        from ogr_core.project.copies import shippable_copy
        c = shippable_copy(p)
        assert c._listeners == [] and len(p._listeners) >= 2
        assert pickle.loads(pickle.dumps(c)).name == p.name
        assert c.boundaries is p.boundaries  # shallow, on purpose
        w.close()

    def test_the_search_splits_it_and_answers_as_in_series(self):
        """Fails on v0.1.261: the pool could not pickle the project."""
        from ogr_slip2d.analysis_runner import build_search
        w, p = _window_project()
        _needs_a_pool(p)
        with _Spy() as spy:
            par = build_search(p, "bishop_simplified").run(p)
        assert spy.used == [True], spy.used
        assert _signature(par) == _signature(_sequential())
        w.close()

    def test_the_window_compute_worker_splits_it_too(self):
        """Through the door the program uses: the worker as a real
        thread."""
        from ogr_gui.main_window import _ComputeWorker
        w, p = _window_project()
        _needs_a_pool(p)
        with _Spy() as spy:
            worker = _ComputeWorker(p, ["bishop_simplified"])
            worker.start()
            assert worker.wait(240000), "the compute thread did not finish"
        assert spy.used == [True], spy.used
        got = worker.results["bishop_simplified"]
        assert _signature(got) == _signature(_sequential())
        w.close()


# ======================================================================
class TestAFailedPoolSaysSo:
    """Invariant 3."""

    def _run(self, broken):
        import concurrent.futures as cf
        from ogr_slip2d.analysis_runner import build_search

        class _Boom:
            def __init__(self, *a, **kw):
                raise OSError("no process pool on this host")

        p = _model()
        _needs_a_pool(p)
        real = cf.ProcessPoolExecutor
        if broken:
            cf.ProcessPoolExecutor = _Boom
        try:
            return build_search(p, "bishop_simplified").run(p)
        finally:
            cf.ProcessPoolExecutor = real

    def test_a_broken_pool_gives_the_same_answer_and_a_note(self):
        """Fails on v0.1.261: the same answer and not a word."""
        got = self._run(True)
        seq = _sequential()
        assert repr(got.critical.fos) == repr(seq.critical.fos)
        lines = [n for n in got.notes if "ran in one" in n]
        assert len(lines) == 1, got.notes
        assert "OSError: no process pool on this host" in lines[0]

    def test_a_healthy_pool_says_nothing_of_the_kind(self):
        assert not any("ran in one" in n for n in self._run(False).notes)


# ======================================================================
class TestTheMainModuleLoadsNoQt:
    """Invariant 4."""

    def test_importing_it_does_not_import_pyside6(self):
        """In a fresh interpreter, as a worker process would. Fails on
        v0.1.261, whose module imports PySide6 and the window."""
        import subprocess
        import sys
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys, ogr_gui.__main__ as m; "
             "print('PySide6' in sys.modules, callable(m.main), "
             "callable(m.start_window))"],
            capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr
        assert out.stdout.split() == ["False", "True", "True"], out.stdout
