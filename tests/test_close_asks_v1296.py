# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.296 (D283) — closing the window with unsaved changes asks first:
Save / Discard / Cancel, the question New Project already asked.

The defect: ``MainWindow.closeEvent`` only deregistered the session and
stopped the agent bridge, so the X, *File → Exit* and Ctrl+Q closed the
program without a word and the work was lost (the manual test of D191, and
three times in the second GUI test). The owner's decision: ask as New does,
only when there are unsaved changes.

What these tests protect (the question replaced, never opened):

* a clean project closes without asking;
* with changes: Cancel keeps the window (the event is ignored, the session
  stays registered); Discard closes; Save with a file saves and closes;
  Save whose Save As is cancelled keeps the window;
* *File → Exit* goes through that question;
* without a screen — the ``offscreen`` platform of the suite — the question
  answers Discard by itself, so a test closing a changed window never
  blocks.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402


def _window(dirty=True):
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    w.project.is_dirty = dirty
    return w


def _answering(w, answer):
    """Replace the question on this window; returns the list of titles it
    was asked with."""
    asked = []

    def ask(title, text):
        asked.append(title)
        return answer
    w._ask_unsaved = ask
    return asked


def _close(w):
    ev = QCloseEvent()
    w.closeEvent(ev)
    return ev.isAccepted()


def _done(w):
    w.project.is_dirty = False
    w.__dict__.pop("_ask_unsaved", None)
    w.close()


class TestTheQuestion:
    def test_a_clean_project_closes_without_asking(self):
        w = _window(dirty=False)
        asked = _answering(w, "cancel")
        try:
            assert _close(w) is True
            assert asked == []
        finally:
            _done(w)

    def test_cancel_keeps_the_window(self):
        w = _window()
        asked = _answering(w, "cancel")
        gone = []
        w.unregister_session = lambda: gone.append(True)
        try:
            assert _close(w) is False
            assert asked == ["Exit"]
            assert gone == []
        finally:
            del w.unregister_session
            _done(w)

    def test_discard_closes(self):
        w = _window()
        _answering(w, "discard")
        try:
            assert _close(w) is True
        finally:
            _done(w)

    def test_save_with_a_file_saves_and_closes(self):
        w = _window()
        _answering(w, "save")
        path = Path(tempfile.mkdtemp(prefix="ogr_test_close_")) / "m.ogr"
        try:
            w.project.file_path = path
            assert _close(w) is True
            assert path.exists()
            assert w.project.is_dirty is False
        finally:
            _done(w)

    def test_save_whose_save_as_is_cancelled_keeps_the_window(self):
        w = _window()
        _answering(w, "save")
        raw = QFileDialog.__dict__.get("getSaveFileName")
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
        try:
            w.project.file_path = None
            assert _close(w) is False
        finally:
            if raw is None:
                del QFileDialog.getSaveFileName
            else:
                QFileDialog.getSaveFileName = raw
            _done(w)

    def test_file_exit_asks(self):
        w = _window()
        asked = _answering(w, "cancel")
        w.show()
        QApplication.processEvents()
        try:
            w._actions["exit"].trigger()
            QApplication.processEvents()
            assert asked == ["Exit"]
            assert w.isVisible()
        finally:
            _done(w)


class TestWithoutAScreen:
    def test_the_question_answers_discard_by_itself(self):
        assert QApplication.platformName() == "offscreen" or \
            os.environ.get("QT_QPA_PLATFORM") == "offscreen"
        w = _window()
        try:
            assert w._ask_unsaved("Exit", "?") == "discard"
            assert _close(w) is True
        finally:
            _done(w)
