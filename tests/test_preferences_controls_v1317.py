# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.317 (D299) — every control of *Preferences* is read by somebody.

The dialog had three check boxes that nothing read or saved: "Show Tabs for
Multiple Windows" (there are no tabbed windows), "Mark file as modified after
importing" (importing always marks the project: every import is an undo step
since 0.1.302) and "Default to compressed format when saving" (the .ogr has
no compressed format). A setting that changes nothing is worse than none
(rule 7): the user believes the program honours it. The owner decided to
remove the three, and with them the group they filled.

The invariants:

* every control with a value that the dialog keeps (a check box, a combo, a
  spin box, a line edit, a radio button) is read by ``_accept`` — measured on
  the source with the AST, and on the real dialog, whose value widgets are
  all among the ones ``_accept`` reads;
* none of the three check boxes is there;
* control: the language and the theme are still emitted on Save, as D290
  left them.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_SRC = (Path(__file__).resolve().parent.parent / "ogr_gui" / "dialogs"
        / "preferences_dialog.py")
_VALUE_WIDGETS = ("QCheckBox", "QComboBox", "QSpinBox", "QDoubleSpinBox",
                  "QLineEdit", "QRadioButton", "QSlider")
_GONE = ("Show Tabs for Multiple Windows",
         "Mark file as modified after importing",
         "Default to compressed format when saving")


def _methods():
    tree = ast.parse(_SRC.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == "PreferencesDialog")
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


def _created(fn):
    """``self.<attr>`` assigned a value widget in ``fn``."""
    out = set()
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                and getattr(n.value.func, "id", None) in _VALUE_WIDGETS):
            for t in n.targets:
                if (isinstance(t, ast.Attribute)
                        and isinstance(t.value, ast.Name)
                        and t.value.id == "self"):
                    out.add(t.attr)
    return out


def _read(fn):
    """``self.<attr>`` mentioned anywhere in ``fn``."""
    return {n.attr for n in ast.walk(fn)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "self"}


def _dialog():
    from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
    QApplication.instance() or QApplication([])
    return PreferencesDialog(active_theme="light")


class TestEveryControlHasAReader:
    def test_in_the_source(self):
        methods = _methods()
        created = _created(methods["__init__"])
        assert created, "the scan has to find the language and theme combos"
        unread = created - _read(methods["_accept"])
        assert unread == set(), unread

    def test_in_the_real_dialog(self):
        from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox,
                                       QComboBox, QLineEdit, QRadioButton,
                                       QSlider)
        d = _dialog()
        try:
            read = [getattr(d, a) for a in _read(_methods()["_accept"])
                    if hasattr(d, a)]
            values = [w for cls in (QCheckBox, QComboBox, QAbstractSpinBox,
                                    QLineEdit, QRadioButton, QSlider)
                      for w in d.findChildren(cls)
                      # a combo's own editor is part of the combo
                      if not isinstance(w.parent(), QComboBox)]
            assert values
            for w in values:
                assert any(w is r for r in read), type(w).__name__
        finally:
            d.deleteLater()

    def test_the_three_check_boxes_are_gone(self):
        from PySide6.QtWidgets import QCheckBox
        d = _dialog()
        try:
            texts = [c.text() for c in d.findChildren(QCheckBox)]
            for gone in _GONE:
                assert gone not in texts
        finally:
            d.deleteLater()


class TestWhatItStillDoes:
    def test_save_emits_the_language_and_the_theme(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        d = _dialog()
        got = {}
        try:
            set_language("en")
            d.language_changed.connect(lambda v: got.setdefault("lang", v))
            d.theme_changed.connect(lambda v: got.setdefault("theme", v))
            d.cbo_language.setCurrentIndex(d.cbo_language.findData("es"))
            d.cbo_theme.setCurrentIndex(d.cbo_theme.findData("dark"))
            d._accept()
            assert got == {"lang": "es", "theme": "dark"}
        finally:
            set_language(before)
            d.deleteLater()
