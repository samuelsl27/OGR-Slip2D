# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.404 (D389) — a closed Interpret window lets go of its result, and a
canvas does not stay on the listeners of a project it no longer shows.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.402 (hallazgos 2 and 8) saw the window's memory
climb from 3 to 8 GB over a session, and stay up after opening another
project; ``topLevelWidgets()`` still listed closed Interpret windows. Three
things kept a closed Interpret window's result alive, all measured on the
real window (``_auditoria/P8_interfaz/d389_recalcular.py``: Compute,
Interpret opened and closed twice, Compute again, on the demo model):

* the window, a Qt child of the main window, was only hidden: 168 surface
  results alive where the current Compute has 56;
* deleting it on close was not enough (still 168): its canvas had put
  ``lambda evt: self.refresh_scene()`` on the project's listeners, which
  nothing ever took off (``Project`` had no ``remove_listener``), so the
  project held the canvas and the result it drew.

Deleted on close and off the listeners: 56. (A measurement that left 112
with both was the probe's own: a variable of it still held the last
listener.) A window closed WITHOUT being deleted — as a script or a test
makes one — is not deleted by Qt; it drops its results on close, so that
an object that outlives its closing holds nothing heavy.

1. **The project's listeners:** ``remove_listener`` removes, and is quiet
   about a callable that is not there.
2. **A canvas listens to the project it shows, once:** given a project
   twice, or another project, it is on the current one's listeners once
   and off the previous one's.
3. **In the window:** after Interpret is opened and closed twice and the
   model computed again, only the current results are alive, with the
   automatic collector off (an idle window runs no full collection); no
   Interpret window is left, and the project has the listeners it had.
4. **A closed Interpret window is off the project:** an edit of the model
   afterwards redraws only the main canvas, and another Interpret window
   opens as before.
5. **A window closed but not deleted holds nothing of its result.**
"""
from __future__ import annotations

import gc
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _collector_off():
    was = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        if was:
            gc.enable()


def _alive() -> int:
    from ogr_slip2d.methods.base import LEMResult
    return sum(1 for o in gc.get_objects() if type(o) is LEMResult)


def _deferred_deletes(app):
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _computed_window():
    from ogr_core.project.demo import build_demo_project
    from ogr_gui.main_window import MainWindow
    from ogr_slip2d.analysis_runner import run_analysis
    app = _app()
    w = MainWindow()
    p = build_demo_project()
    p.settings.search.grid_nx = p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 3
    w._attach_project(p)
    w._on_compute_done(run_analysis(p, ["bishop_simplified"]).results)
    return app, w, p


def _done(w):
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


class TestTheListeners:
    """Invariants 1 and 2."""

    def test_remove_listener(self):
        from ogr_core.project import Project
        p = Project()
        calls = []

        def cb(evt):
            calls.append(evt)
        p.add_listener(cb)
        p.remove_listener(cb)
        p.remove_listener(cb)                   # not there: quiet
        p._notify("geometry_changed")
        assert calls == []

    def test_a_canvas_listens_once_to_the_project_it_shows(self):
        from ogr_core.project import Project
        from ogr_gui.canvas.canvas_view import CanvasView
        _app()
        a, b = Project(), Project()
        c = CanvasView(a)
        try:
            n = len(a._listeners)
            c.set_project(a)
            assert len(a._listeners) == n, "the same project, listened twice"
            c.set_project(b)
            assert len(a._listeners) == n - 1, "still on the previous project"
            assert len(b._listeners) == 1
            c.detach_project()
            assert b._listeners == []
        finally:
            c.deleteLater()


class TestAClosedInterpretWindow:
    """Invariants 3 and 4."""

    def test_lets_go_of_its_result(self):
        import weakref

        from ogr_slip2d.analysis_runner import run_analysis
        app, w, p = _computed_window()
        try:
            gc.collect()
            one = _alive()
            listeners = len(p._listeners)
            assert one > 0
            opened = []                 # weak: a strong one would hold them
            with _collector_off():
                for _k in range(2):
                    w.act_interpret()
                    opened.append(weakref.ref(w.interpret_windows[-1]))
                    w.interpret_windows[-1].close()
                    _deferred_deletes(app)
                    w._on_compute_done(
                        run_analysis(p, ["bishop_simplified"]).results)
                    app.processEvents()
                left = _alive()
            assert left == one, (
                "%d surface results alive, %d of them of earlier Computes"
                % (left, left - one))
            # a deleted window is no longer a top-level widget (compared by
            # id: a deleted wrapper must not be asked anything of Qt)
            top = {id(x) for x in app.topLevelWidgets()}
            assert all(r() is None or id(r()) not in top
                       for r in opened), "a closed Interpret window lives on"
            assert w.interpret_windows == []
            assert len(p._listeners) == listeners
        finally:
            _done(w)

    def test_is_off_the_project(self):
        app, w, p = _computed_window()
        try:
            w.act_interpret()
            win = w.interpret_windows[-1]
            canvas = win.canvas
            redrawn = []
            real = type(canvas).refresh_scene

            def spy(self):
                redrawn.append(self is canvas)
                return real(self)
            type(canvas).refresh_scene = spy
            try:
                win.close()
                del win
                _deferred_deletes(app)
                p._notify("geometry_changed")
            finally:
                type(canvas).refresh_scene = real
            assert redrawn and not any(redrawn), (
                "a closed Interpret canvas was redrawn")
            w.act_interpret()
            assert len(w.interpret_windows) == 1
            w.interpret_windows[-1].close()
            _deferred_deletes(app)
        finally:
            _done(w)

    def test_closed_but_not_deleted_holds_nothing(self):
        """Invariant 5: built directly, as a script does, with no
        ``WA_DeleteOnClose``; the object outlives its closing."""
        from ogr_gui.interpret_window import InterpretWindow
        app, w, p = _computed_window()
        win = InterpretWindow(p, dict(w.last_search_results), None)
        try:
            win.close()
            with _collector_off():
                w._attach_project(type(p)())        # the main window lets go
                app.processEvents()
                left = _alive()
            assert win.results_by_method == {} and win.search_result is None
            assert win.canvas._shown_result is None
            assert left == 0, "%d surface results held by a closed window" % left
        finally:
            win.deleteLater()
            _done(w)
