# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.285 (D286) — the mouse wheel changes a number box or a drop-down only
when it has the focus.

The defect: Qt gives every spin box and combo box the focus policy
``WheelFocus``, so scrolling a long dialog with the wheel stepped whichever
box passed under the pointer. The GUI test of 0.1.284 saw the Gardner ``a``
of the hydraulic dialog go from 0.01 to 0 that way; with OK, the material
would have been stored with a = 0 that nobody typed.

What these tests protect, on the REAL hydraulic dialog:

* a box and a drop-down without the focus do not change under the wheel;
* the same box with the focus does (the wheel still works where the user
  is typing);
* boxes and drop-downs lose ``WheelFocus`` when polished;
* the main window installs the guard;
* switched off, the wheel steps an unfocused box again (rule 7).

A wheel event sent by hand is not spontaneous: Qt delivers it to its
receiver only and neither moves the focus nor passes it to the parent, so
the scrolling of the panel is checked by hand. The guard and the switch are
restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_gui import wheel_guard  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _wheel(widget, notches=3):
    app = _app()
    for _ in range(notches):
        ev = QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))),
                         QPoint(0, 0), QPoint(0, -120), Qt.NoButton,
                         Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(widget, ev)
        app.processEvents()


def _dialog():
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    p = Project("d286")
    m = Material(name="Soil", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(ks=1e-6, model=PermeabilityModel.GARDNER,
                                      gardner_a=0.01, gardner_n=2.0)
    p.materials = [m]
    dlg = HydraulicPropertiesDialog(p)
    dlg.show()
    dlg.activateWindow()
    _app().processEvents()
    return dlg


class _Guarded:
    """Install the guard for the test and leave the application as found."""

    def __enter__(self):
        self.was = wheel_guard.installed()
        self.switch = wheel_guard.WHEEL_NEEDS_FOCUS
        wheel_guard.install(_app())
        return self

    def __exit__(self, *exc):
        wheel_guard.WHEEL_NEEDS_FOCUS = self.switch
        if not self.was:
            wheel_guard.uninstall(_app())
        return False


class TestTheWheel:
    def test_an_unfocused_box_does_not_change(self):
        with _Guarded():
            dlg = _dialog()
            try:
                dlg.sp_ks.setFocus()
                _app().processEvents()
                a = dlg.sp_g_a
                assert not a.hasFocus()
                before = a.value()
                _wheel(a)
                assert a.value() == before
            finally:
                dlg.reject()

    def test_an_unfocused_drop_down_does_not_change(self):
        with _Guarded():
            dlg = _dialog()
            try:
                dlg.sp_ks.setFocus()
                _app().processEvents()
                before = dlg.cbo_model.currentIndex()
                _wheel(dlg.cbo_model)
                assert dlg.cbo_model.currentIndex() == before
            finally:
                dlg.reject()

    def test_a_focused_box_still_changes(self):
        with _Guarded():
            dlg = _dialog()
            try:
                a = dlg.sp_g_a
                a.setFocus()
                _app().processEvents()
                assert a.hasFocus()
                before = a.value()
                _wheel(a)
                assert a.value() < before
            finally:
                dlg.reject()

    def test_boxes_lose_wheel_focus(self):
        with _Guarded():
            dlg = _dialog()
            try:
                for w in (dlg.sp_g_a, dlg.sp_ks, dlg.cbo_model):
                    assert w.focusPolicy() == Qt.FocusPolicy.StrongFocus, w
            finally:
                dlg.reject()

    def test_switched_off_the_wheel_steps_an_unfocused_box(self):
        with _Guarded():
            wheel_guard.WHEEL_NEEDS_FOCUS = False
            dlg = _dialog()
            try:
                dlg.sp_ks.setFocus()
                _app().processEvents()
                a = dlg.sp_g_a
                before = a.value()
                _wheel(a)
                assert a.value() < before
            finally:
                dlg.reject()


class TestTheWindow:
    def test_the_main_window_installs_the_guard(self):
        from ogr_gui.main_window import MainWindow
        was = wheel_guard.installed()
        try:
            wheel_guard.uninstall(_app())
            w = MainWindow()
            try:
                assert wheel_guard.installed()
            finally:
                w.close()
                w.deleteLater()
        finally:
            if not was:
                wheel_guard.uninstall(_app())
            else:
                wheel_guard.install(_app())
