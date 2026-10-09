# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.290 (D291) — every menu entry and every message of the main window
has its Spanish.

The defect: 26 of the 130 actions of ``MainWindow._mk`` had no Spanish
entry — the whole groundwater workflow among them — and 121 messages of the
main window (status bar, ``_info``, message boxes) were literals or
f-strings that never reached ``tr()``. ``test_i18n_coverage_v141`` could not
see either: it reads ``tr("…")`` calls with the text written in them, and
``_mk`` receives its text as a variable; and it counts only literal
messages, never f-strings. The GUI test of 0.1.284 listed them on screen.

What these tests protect — the rule 2 counterpart of the rule 3 test that
walks the real menu bar:

* every title and every entry of the REAL menu bar (built in English, the
  keys) has a Spanish translation different from the English; the dynamic
  entries of the *Window* menu are not keys;
* no message argument of ``ogr_gui/main_window.py`` is a literal or an
  f-string with letters left outside ``tr()`` (read with the AST);
* two messages through the real code: with Spanish active, computing the
  groundwater without a mesh and resetting a mesh that does not exist speak
  Spanish.

The language is restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMenu, QMessageBox  # noqa: E402

from ogr_gui.i18n import _DICTS, current_language, set_language  # noqa: E402

_WIN = Path(__file__).resolve().parent.parent / "ogr_gui" / "main_window.py"


def _app():
    return QApplication.instance() or QApplication([])


def _english_window():
    from ogr_gui.main_window import MainWindow
    _app()
    prev = current_language()
    set_language("en")
    try:
        return MainWindow(), prev
    except Exception:
        set_language(prev)
        raise


class TestTheMenuBar:
    def test_every_title_and_entry_has_spanish(self):
        w, prev = _english_window()
        try:
            es = _DICTS["es"]
            # written the same in Spanish (as in the allow-list of
            # test_i18n_coverage_v141)
            same = {"Zoom", "Terminal"}

            def untranslated(text):
                return text not in es or (es[text] == text and text not in same)
            # the Window menu lists the open windows: its entries are names
            dynamic = w._window_menu.title()
            menus = w.menuBar().findChildren(QMenu)
            missing = []
            for menu in menus:
                if menu.title() and untranslated(menu.title()):
                    missing.append(("menu", menu.title()))
                if menu.title() == dynamic:
                    continue
                # the entries that open a submenu are checked as menus
                # (not through QAction.menu(), whose wrapper can outlive
                # its menu in a test run)
                subtitles = {m.title() for m in menus if m.parent() is menu}
                for act in menu.actions():
                    text = act.text()
                    if act.isSeparator() or not text or text in subtitles:
                        continue
                    if untranslated(text):
                        missing.append((menu.title(), text))
            assert not missing, missing
        finally:
            w.close()
            set_language(prev)


def _message_arguments(src):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = getattr(f, "attr", None) or getattr(f, "id", None)
        if name == "showMessage" and node.args:
            yield node.args[0]
        elif name == "_info" and node.args:
            yield from node.args[:2]
        elif name in ("information", "warning", "critical", "question") \
                and isinstance(f, ast.Attribute) \
                and getattr(f.value, "id", None) == "QMessageBox" \
                and len(node.args) >= 3:
            yield node.args[1]
            yield node.args[2]


def _letters(text):
    return any(c.isalpha() for c in re.sub(r"[{][^}]*[}]", "", text))


class TestTheMessages:
    def test_no_message_of_the_window_skips_tr(self):
        src = _WIN.read_text(encoding="utf-8")
        loose = []
        for a in _message_arguments(src):
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                if _letters(a.value) and a.value != "OGR Slip2D":
                    loose.append((a.lineno, a.value[:50]))
            elif isinstance(a, ast.JoinedStr):
                text = "".join(v.value if isinstance(v, ast.Constant) else "{}"
                               for v in a.values)
                if _letters(text):
                    loose.append((a.lineno, text[:50]))
            elif isinstance(a, ast.BinOp) and isinstance(a.left, ast.Constant) \
                    and isinstance(a.left.value, str) and _letters(a.left.value):
                loose.append((a.lineno, a.left.value[:50]))
        assert not loose, loose

    def test_two_messages_speak_spanish(self):
        w, prev = _english_window()
        shown = []
        raw = QMessageBox.__dict__.get("information")
        QMessageBox.information = staticmethod(
            lambda _p, title, text, *a, **k: shown.append(text))
        try:
            set_language("es")
            w._compute_groundwater()
            assert shown == ["Genera primero la malla de elementos finitos."]
            w._reset_fem_mesh()
            assert w.statusBar().currentMessage() == \
                "No hay malla de elementos finitos que borrar"
        finally:
            if raw is None:
                del QMessageBox.information
            else:
                QMessageBox.information = raw
            set_language(prev)
            w.close()
