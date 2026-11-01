# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.406 (D391) — File → Open asks about unsaved changes, as New and closing
the window ask.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.402 (hallazgo 4) opened another ``.ogr`` over a
project with unsaved changes three times, and nothing asked; File → Exit
did ask. ``act_new`` and ``closeEvent`` have asked with ``_ask_unsaved``
since v0.1.296 (D283), and ``act_open`` never looked at ``is_dirty``: the
work was replaced without a word.

1. **A clean project opens without asking.**
2. **Cancel opens nothing:** no file dialog, the project stays.
3. **Discard opens the file.**
4. **Save saves, then opens.**
5. **A Save that does not save opens nothing:** Save As cancelled leaves
   the changes unsaved and the project where it was.
6. **A file dialog cancelled after Discard** leaves the project as it was.

The question and the file dialogs are replaced on the window, and put
back: nothing modal opens.
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
def _file_dialogs(open_path="", save_path=""):
    """``getOpenFileName`` and ``getSaveFileName`` answering with these
    paths ('' is Cancel); yields the list of dialogs shown."""
    from PySide6.QtWidgets import QFileDialog
    shown = []
    raw = {n: QFileDialog.__dict__.get(n)
           for n in ("getOpenFileName", "getSaveFileName")}

    def opening(*a, **k):
        shown.append("open")
        return (str(open_path), "")

    def saving(*a, **k):
        shown.append("save")
        return (str(save_path), "")
    QFileDialog.getOpenFileName = staticmethod(opening)
    QFileDialog.getSaveFileName = staticmethod(saving)
    try:
        yield shown
    finally:
        for n, v in raw.items():
            if v is None:
                delattr(QFileDialog, n)
            else:
                setattr(QFileDialog, n, v)


def _other_file(folder: Path) -> Path:
    from ogr_core.project import Project
    path = folder / "other.ogr"
    Project("other").save(path)
    return path


def _done(w):
    w.project.is_dirty = False
    w.__dict__.pop("_ask_unsaved", None)
    w.close()
    w.deleteLater()


class TestOpenAsks:

    def test_a_clean_project_opens_without_asking(self):
        w = _window(dirty=False)
        asked = _answering(w, "cancel")
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                    _file_dialogs(open_path=_other_file(Path(tmp))):
                w.act_open()
            assert asked == []
            assert w.project.name == "other"
        finally:
            _done(w)

    def test_cancel_opens_nothing(self):
        w = _window()
        asked = _answering(w, "cancel")
        mine = w.project
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                    _file_dialogs(open_path=_other_file(Path(tmp))) as shown:
                w.act_open()
            assert asked == ["Open Project..."]
            assert shown == [], "the file dialog opened"
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)

    def test_discard_opens(self):
        w = _window()
        _answering(w, "discard")
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                    _file_dialogs(open_path=_other_file(Path(tmp))):
                w.act_open()
            assert w.project.name == "other"
        finally:
            _done(w)

    def test_save_saves_then_opens(self):
        w = _window()
        _answering(w, "save")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mine = Path(tmp) / "mine.ogr"
                w.project.file_path = mine
                with _file_dialogs(open_path=_other_file(Path(tmp))):
                    w.act_open()
                assert mine.exists(), "the changes were not saved"
                assert w.project.name == "other"
        finally:
            _done(w)

    def test_a_save_that_does_not_save_opens_nothing(self):
        w = _window()
        _answering(w, "save")
        mine = w.project
        try:
            w.project.file_path = None
            with tempfile.TemporaryDirectory() as tmp, \
                    _file_dialogs(open_path=_other_file(Path(tmp)),
                                  save_path="") as shown:
                w.act_open()
            assert shown == ["save"], shown
            assert w.project is mine and mine.is_dirty
        finally:
            _done(w)

    def test_a_file_dialog_cancelled_after_discard(self):
        w = _window()
        _answering(w, "discard")
        mine = w.project
        try:
            with _file_dialogs(open_path="") as shown:
                w.act_open()
            assert shown == ["open"]
            assert w.project is mine
        finally:
            _done(w)
