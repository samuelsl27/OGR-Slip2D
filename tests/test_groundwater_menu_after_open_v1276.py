# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.276 (D281, D282) — what the manual test of D191/D271 found in the
interface around groundwater.

D281 — the Groundwater menu after Open
--------------------------------------
Define Hydraulic Properties, Boundary Conditions, Transient, Compute and
Interpret Groundwater are enabled by ``_update_groundwater_actions``, and
nothing that Open, New or the demo goes through (``_attach_project`` ->
``refresh_action_availability``) called it. Opening a .ogr with an FEA
method and a mesh left them disabled, as they were for the empty project
the window started with: a saved groundwater model could not be computed
without going through Project Settings first. The invariant: after
attaching a project, and after any project event, the groundwater actions
answer for THAT project.

D282 — the hydraulic properties dialog on a screen
--------------------------------------------------
* its parameters scroll: the column had grown to 842 px (974 with a user
  curve), taller than a 1536 x 816 screen, and the title bar went off the
  top; the problems and OK / Cancel stay outside the scroll, always seen;
* the first column of the curve table is as wide as its header (it showed
  "latric suction (kP");
* the Plot's line starts at the first point (suction 0, drawn at 1e-2), not
  at 0.1 kPa;
* the window frees the dialog when it closes (each opening left one more
  alive).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402

GW = ("gw_hydraulic", "gw_transient", "gw_bcs", "gw_compute")
CURVE = [(0.0, 1e-5), (10.0, 1e-7), (50.0, 1e-13)]


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _fea_project(mesh=True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.settings import GroundwaterMethod
    from ogr_fem2d.mesh import generate_mesh_for_project
    p = Project("gw")
    p.boundaries.append(Boundary(btype=BoundaryType.EXTERNAL, polyline=Polyline(
        [Vertex(0, 0), Vertex(20, 0), Vertex(20, 12), Vertex(0, 12)],
        closed=True)))
    m = Material(name="Presa", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(ks=1e-5, model=PermeabilityModel.USER_DEFINED,
                                      user_curve=list(CURVE))
    p.materials.append(m)
    p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
    if mesh:
        p.fem_mesh = generate_mesh_for_project(p, target_elements=150)
    return p


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    return MainWindow()


@_requires_qt
class TestTheGroundwaterMenuAfterOpen:
    def test_attaching_an_fea_project_with_a_mesh_enables_it(self):
        w = _window()
        # the empty project of start-up has no mesh to compute on
        assert not w._actions["gw_compute"].isEnabled()
        w._attach_project(_fea_project())
        for key in GW:
            assert w._actions[key].isEnabled(), key
        assert not w._actions["gw_interpret"].isEnabled()   # no result yet

    def test_attaching_one_without_a_mesh_disables_compute(self):
        w = _window()
        w._attach_project(_fea_project())
        w._attach_project(_fea_project(mesh=False))
        assert w._actions["gw_hydraulic"].isEnabled()
        assert not w._actions["gw_compute"].isEnabled()
        assert not w._actions["gw_bcs"].isEnabled()

    def test_a_project_event_refreshes_it(self):
        """A change made elsewhere (the API, the agent bridge) reaches the
        menu through the project's listener."""
        from ogr_fem2d.mesh import generate_mesh_for_project
        w = _window()
        p = _fea_project(mesh=False)
        w._attach_project(p)
        assert not w._actions["gw_compute"].isEnabled()
        p.fem_mesh = generate_mesh_for_project(p, target_elements=150)
        p._notify("mesh_changed")
        assert w._actions["gw_compute"].isEnabled()


def _dialog(p):
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    return HydraulicPropertiesDialog(p, None)


@_requires_qt
class TestTheHydraulicDialogOnAScreen:
    def test_its_parameters_scroll_and_its_buttons_do_not(self):
        from PySide6.QtWidgets import QDialogButtonBox, QScrollArea
        _window()
        d = _dialog(_fea_project())
        assert isinstance(d.scroll, QScrollArea)
        assert d.scroll.widget().isAncestorOf(d.tbl_curve)
        assert d.scroll.widget().isAncestorOf(d.gb_wc)
        bb = d.findChild(QDialogButtonBox)
        assert not d.scroll.widget().isAncestorOf(bb)
        assert not d.scroll.widget().isAncestorOf(d.lbl_problems)

    def test_it_fits_a_laptop_screen(self):
        _window()
        p = _fea_project()
        p.materials[0].hydraulic.user_curve = [(float(10 * i), 1e-5 / 10 ** i)
                                               for i in range(12)]
        d = _dialog(p)
        assert d.minimumSizeHint().height() < 600, d.minimumSizeHint()

    def test_the_first_column_fits_its_header(self):
        from PySide6.QtWidgets import QHeaderView
        _window()
        d = _dialog(_fea_project())
        h = d.tbl_curve.horizontalHeader()
        assert h.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents

    def test_the_plot_line_starts_at_the_first_point(self):
        _window()
        d = _dialog(_fea_project())
        dlg = d._plot()
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        line, points = dlg.findChild(FigureCanvasQTAgg).figure.axes[0].get_lines()
        assert line.get_xdata()[0] == points.get_xdata()[0] == 1e-2
        assert line.get_ydata()[0] == points.get_ydata()[0] == 1e-5
        dlg.close()

    def test_the_window_frees_it(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from ogr_gui.dialogs.hydraulic_properties_dialog import (
            HydraulicPropertiesDialog)
        w = _window()
        w._attach_project(_fea_project())
        real = HydraulicPropertiesDialog.exec
        HydraulicPropertiesDialog.exec = lambda self: 0        # Cancel
        try:
            w._define_hydraulic_properties()
            w._define_hydraulic_properties()
        finally:
            HydraulicPropertiesDialog.exec = real
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert w.findChildren(HydraulicPropertiesDialog) == []
