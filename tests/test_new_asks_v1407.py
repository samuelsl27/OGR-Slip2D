# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.407 (D392) — File → New, and Load Demo Slope, replace the project only
when its changes are saved or discarded, as Open (D391) and closing the
window (D283) do.

WHAT INVARIANT THIS PROTECTS.

``act_new`` asked with ``_ask_unsaved`` and, to Save, called ``act_save``
and went on to the new project whether or not it had saved: on a project
never saved, Save As cancelled (or a write that failed) lost the changes the
user had just asked to keep. ``act_load_demo`` asked its own Yes/No, which
offered no Save and had no offscreen guard. Both now go through
``_may_replace_project``, the rule of Open.

New:

1. **A clean project is replaced without asking.**
2. **Cancel creates nothing:** the same project, still with its changes.
3. **Discard creates the empty project.**
4. **Save saves, then creates the empty project.**
5. **A Save that does not save creates nothing:** Save As cancelled leaves
   the project where it was, with its changes.

Load Demo Slope: Cancel loads nothing, Discard loads the demo, and a Save
that does not save leaves the project.

The question and the save dialog are replaced on the window, and put back:
nothing modal opens.
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _window(dirty=True):
    from PySide6.QtWidgets import QApplication
    from ogr_core.project import Project
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w._attach_project(Project("mine"))
    w.project.is_dirty = dirty
    return w


def _answering(w, answer):
    asked = []

    def ask(title, text):
        asked.append(title)
        return answer
    w._ask_unsaved = ask
    return asked


@contextlib.contextmanager
def _save_dialog(path=""):
    """``getSaveFileName`` answering with this path ('' is Cancel); yields
    the list of dialogs shown."""
    from PySide6.QtWidgets import QFileDialog
    shown = []
    raw = QFileDialog.__dict__.get("getSaveFileName")

    def saving(*a, **k):
        shown.append("save")
        return (str(path), "")
    QFileDialog.getSaveFileName = staticmethod(saving)
    try:
        yield shown
    finally:
        if raw is None:
            delattr(QFileDialog, "getSaveFileName")
        else:
            QFileDialog.getSaveFileName = raw


def _done(w):
    w.project.is_dirty = False
    w.__dict__.pop("_ask_unsaved", None)
    w.close()
    w.deleteLater()


class TestNewAsks:

    def test_a_clean_project_is_replaced_without_asking(self):
        w = _window(dirty=False)
        asked = _answering(w, "cancel")
        mine = w.project
        try:
            w.act_new()
            assert asked == []
            assert w.project is not mine and w.project.name == "Untitled"
        finally:
            _done(w)

    def test_cancel_creates_nothing(self):
        w = _window()
        asked = _answering(w, "cancel")
        mine = w.project
        try:
            w.act_new()
            assert asked == ["New Project"]
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)

    def test_discard_creates_the_empty_project(self):
        w = _window()
        _answering(w, "discard")
        mine = w.project
        try:
            w.act_new()
            assert w.project is not mine and w.project.name == "Untitled"
        finally:
            _done(w)

    def test_save_saves_then_creates(self):
        w = _window()
        _answering(w, "save")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mine = Path(tmp) / "mine.ogr"
                w.project.file_path = mine
                w.act_new()
                assert mine.exists(), "the changes were not saved"
                assert w.project.name == "Untitled"
        finally:
            _done(w)

    def test_a_save_that_does_not_save_creates_nothing(self):
        w = _window()
        _answering(w, "save")
        mine = w.project
        try:
            w.project.file_path = None
            with _save_dialog(path="") as shown:
                w.act_new()
            assert shown == ["save"], shown
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)


class TestLoadDemoAsks:

    def test_cancel_loads_nothing(self):
        w = _window()
        asked = _answering(w, "cancel")
        mine = w.project
        try:
            w.act_load_demo()
            assert asked == ["Load Demo Slope"]
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)

    def test_discard_loads_the_demo(self):
        w = _window()
        _answering(w, "discard")
        try:
            w.act_load_demo()
            assert w.project.name == "Demo slope"
        finally:
            _done(w)

    def test_a_save_that_does_not_save_loads_nothing(self):
        w = _window()
        _answering(w, "save")
        mine = w.project
        try:
            w.project.file_path = None
            with _save_dialog(path="") as shown:
                w.act_load_demo()
            assert shown == ["save"], shown
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)
