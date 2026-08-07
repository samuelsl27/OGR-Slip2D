# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Embedded Python terminal — interactive REPL inside the GUI.

Provides a dockable REPL with access to the live ``project`` object, a
``canvas`` reference, and the full OGR API. Ideal for quick parameter
sweeps, scripted boundary edits, or diagnostics without leaving the
GUI.

Security note: the terminal executes arbitrary Python. That is by
design and matches the spec ("poder interactuar mediante Python
directamente"). The REPL runs in-process, sharing state with the rest
of the GUI.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import code
import io
import sys
import traceback
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QDockWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


# ----------------------------------------------------------------------
class _OutputCapture(io.StringIO):
    """Redirects stdout/stderr into a signal callback."""

    def __init__(self, callback) -> None:
        super().__init__()
        self.callback = callback

    def write(self, s: str) -> int:
        if s:
            self.callback(s)
        return len(s)

    def flush(self) -> None:
        pass


# ----------------------------------------------------------------------
class TerminalWidget(QPlainTextEdit):
    """QPlainTextEdit customised as an interactive REPL.

    - Multi-line input joined with ``\\n``.
    - Shift+Enter to submit (Enter adds a newline).
    - History navigated with Ctrl+↑ / Ctrl+↓.
    - Ctrl+L clears the buffer.
    """

    command_executed = Signal(str)

    PROMPT = ">>> "
    CONTINUATION = "... "

    def __init__(self, namespace: Optional[dict] = None, parent=None) -> None:
        super().__init__(parent)
        font = QFont("Consolas, Menlo, monospace")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        self._ns: dict[str, Any] = namespace if namespace is not None else {}
        self._compiler = code.InteractiveInterpreter(self._ns)
        self._history: list[str] = []
        self._history_idx: int = 0
        self._input_start = 0

        self._write_banner()
        self._write_prompt()

    # ------------------------------------------------------------------
    def update_namespace(self, extra: dict) -> None:
        """Merge ``extra`` into the REPL's live namespace."""
        self._ns.update(extra)

    # ------------------------------------------------------------------
    def _write_banner(self) -> None:
        banner = (
            "OGR Slip2D — embedded Python terminal\n"
            f"Python {sys.version.split()[0]}\n"
            "Available: project, canvas, mainwindow, ogr_*, np\n"
            "Type 'help_ogr()' for tips.\n"
        )
        self._append_styled(banner, color="#707070")

    def _write_prompt(self, cont: bool = False) -> None:
        self._append_styled(self.CONTINUATION if cont else self.PROMPT,
                            color="#1e6fc5", bold=True)
        self._input_start = self._cursor_pos()

    # ------------------------------------------------------------------
    def _append_styled(self, text: str, color: str = "#202020",
                        bold: bool = False) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            f = fmt.font()
            f.setBold(True)
            fmt.setFont(f)
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _cursor_pos(self) -> int:
        return self.textCursor().position()

    # ------------------------------------------------------------------
    def _current_input(self) -> str:
        text = self.toPlainText()
        return text[self._input_start:]

    def _replace_input(self, new: str) -> None:
        cursor = self.textCursor()
        cursor.setPosition(self._input_start)
        cursor.setPosition(len(self.toPlainText()), QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(new)

    # ------------------------------------------------------------------
    def _execute(self, source: str) -> None:
        if not source.strip():
            return
        self._history.append(source)
        self._history_idx = len(self._history)

        out = _OutputCapture(lambda s: self._append_styled(s, color="#202020"))
        err = _OutputCapture(lambda s: self._append_styled(s, color="#c0392b"))

        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            self._compiler.runsource(source, symbol="exec")
        except SystemExit:
            pass
        except Exception:  # noqa: BLE001
            err.write(traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        self.command_executed.emit(source)

    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        cursor = self.textCursor()

        # Block editing above the current prompt
        if cursor.position() < self._input_start:
            # Only allow navigation keys
            if event.key() not in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                cursor.setPosition(self._cursor_pos())
                self.setTextCursor(cursor)
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)

        key = event.key()
        mods = event.modifiers()

        # Ctrl+L clears the buffer
        if key == Qt.Key_L and mods & Qt.ControlModifier:
            self.clear()
            self._write_banner()
            self._write_prompt()
            event.accept()
            return

        # Ctrl+Up / Ctrl+Down history
        if key == Qt.Key_Up and mods & Qt.ControlModifier:
            if self._history_idx > 0:
                self._history_idx -= 1
                self._replace_input(self._history[self._history_idx])
            event.accept()
            return
        if key == Qt.Key_Down and mods & Qt.ControlModifier:
            if self._history_idx < len(self._history) - 1:
                self._history_idx += 1
                self._replace_input(self._history[self._history_idx])
            else:
                self._replace_input("")
                self._history_idx = len(self._history)
            event.accept()
            return

        # Enter (no Shift): submit
        if key in (Qt.Key_Return, Qt.Key_Enter) and not (mods & Qt.ShiftModifier):
            source = self._current_input()
            self._append_styled("\n")
            self._execute(source)
            self._write_prompt()
            event.accept()
            return

        # Shift+Enter: continuation (just insert a newline)
        if key in (Qt.Key_Return, Qt.Key_Enter) and mods & Qt.ShiftModifier:
            self._append_styled("\n")
            self._append_styled(self.CONTINUATION, color="#1e6fc5", bold=True)
            event.accept()
            return

        # Prevent deleting past the prompt
        if key == Qt.Key_Backspace and cursor.position() <= self._input_start:
            event.accept()
            return

        super().keyPressEvent(event)


# ======================================================================
class TerminalDock(QDockWidget):
    """Dockable host around :class:`TerminalWidget`."""

    def __init__(self, parent=None) -> None:
        super().__init__("Terminal", parent)
        self.setObjectName("TerminalDock")
        self.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        self.terminal = TerminalWidget()
        vbox.addWidget(self.terminal)
        self.setWidget(container)

    # ------------------------------------------------------------------
    def attach_context(self, project, canvas, mainwindow) -> None:
        """Inject live references into the REPL namespace."""
        import numpy as np

        try:
            import ogr_core  # noqa: F401
            import ogr_slip2d  # noqa: F401
        except ImportError:
            pass

        ns = {
            "project": project,
            "canvas": canvas,
            "mainwindow": mainwindow,
            "np": np,
            "help_ogr": self._help_ogr,
        }

        # Let users access the domain packages directly
        try:
            import ogr_core
            import ogr_slip2d
            ns["ogr_core"] = ogr_core
            ns["ogr_slip2d"] = ogr_slip2d
        except ImportError:
            pass

        self.terminal.update_namespace(ns)

    # ------------------------------------------------------------------
    @staticmethod
    def _help_ogr() -> None:
        print(
            "OGR Terminal tips\n"
            "-----------------\n"
            "  project                  the current Project instance\n"
            "  canvas                   the CanvasView\n"
            "  mainwindow               the MainWindow\n"
            "  ogr_core / ogr_slip2d    domain packages\n"
            "  np                       NumPy\n"
            "\n"
            "Examples:\n"
            "  len(project.boundaries)\n"
            "  project.bounding_box()\n"
            "  [m.name for m in project.materials]\n"
            "  from ogr_slip2d import BishopSimplified, GridSearch\n"
            "  r = GridSearch(BishopSimplified(), grid_nx=6, grid_ny=6,\n"
            "                 radius_increment=2.0, min_radius=4.0,\n"
            "                 num_slices=25, min_area=5).run(project)\n"
            "  r.critical.fos\n"
            "\n"
            "Shortcuts: Enter = run, Shift+Enter = newline, "
            "Ctrl+Up/Down = history, Ctrl+L = clear."
        )
