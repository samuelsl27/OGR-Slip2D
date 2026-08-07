# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.13 P9 fix — Add Grid dialog stays open during canvas
pick (per Samuel's suggestion, the dialog is now floating non-modal
and the pick flow no longer hides it).
"""
from __future__ import annotations
import unittest

try:
    import PySide6  # noqa: F401
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


def _requires_qt(cls):
    if _HAS_QT:
        return cls
    for name in list(vars(cls)):
        if name.startswith("test_"):
            setattr(cls, name, lambda self: None)
    return cls


# ======================================================================
@_requires_qt
class TestAddGridDialogStaysOpen:
    """The dialog must NOT call hide() on pick — it stays visible
    so the user can press OK directly after clicking 2 corners."""

    def test_pick_does_not_hide_dialog(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from ogr_core.project import Project
        from ogr_gui.dialogs.grid_dialogs import AddGridDialog

        p = Project("test")
        dlg = AddGridDialog(p)
        dlg.show()
        assert dlg.isVisible()
        # Simulate Pick on canvas button
        dlg._pick_on_canvas()
        # Dialog must STILL be visible
        assert dlg.isVisible(), \
            "v0.1.13 fix: dialog must stay open during canvas pick"
        dlg.close()

    def test_update_bounds_method_exists(self):
        """The new update_bounds() method should be the API for the
        MainWindow to push picked values into the dialog."""
        from ogr_gui.dialogs.grid_dialogs import AddGridDialog
        assert hasattr(AddGridDialog, "update_bounds")

    def test_update_bounds_pushes_to_spinboxes(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from ogr_core.project import Project
        from ogr_gui.dialogs.grid_dialogs import AddGridDialog
        p = Project("test")
        dlg = AddGridDialog(p)
        dlg.show()
        dlg.update_bounds(5.0, 10.0, 25.0, 30.0)
        assert dlg.sb_xmin.value() == 5.0
        assert dlg.sb_xmax.value() == 25.0
        assert dlg.sb_ymin.value() == 10.0
        assert dlg.sb_ymax.value() == 30.0
        dlg.close()


# ======================================================================
@_requires_qt
class TestPickStartedSignal:
    """The pick_started signal exists for the MainWindow to switch
    canvas tool mode without exec()ing the dialog."""

    def test_signal_class_attribute(self):
        from ogr_gui.dialogs.grid_dialogs import AddGridDialog
        assert hasattr(AddGridDialog, "pick_started")
