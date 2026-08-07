# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.47 — DXF import problem report (Phase D3).

An import that says "3 problems found" and closes has told the user
almost nothing: a gap of a few millimetres in a hundred-metre model
cannot be found by panning. This phase makes each problem *actionable* —
located, explained, and reachable in one click.

What the tests pin down:

* selecting a problem **centres the canvas on it**, and the closer zoom
  gets closer still;
* the canvas keeps its **vertical flip** (the model has y upwards; a
  naive ``fitInView`` would turn the drawing upside down);
* problems are grouped by kind, ordered with **errors first**, and each
  kind carries advice that names the setting to change;
* the **area mismatch** — which the sanitiser cannot know, because it only
  emerges once regions are built — is injected as the top problem, since
  it is the single most important thing to report;
* a clean import says so instead of showing an empty list.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

from ogr_core.dxf import (  # noqa: E402
    ImportOptions,
    apply_to_project,
    preview,
)
from ogr_core.project import Project  # noqa: E402


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


_MESSY = Path("/tmp/ogr_problems.dxf")
_CLEAN = Path("/tmp/ogr_clean.dxf")


def _make_messy(path=_MESSY):
    """Open external boundary, a second stray external, and a material
    line dangling in mid-air."""
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for name in ("OGR_EXTERNAL", "OGR_MATERIAL"):
        if name not in doc.layers:
            doc.layers.add(name)
    msp.add_lwpolyline(
        [(0, 0), (120, 0), (120, 25), (75, 25), (50, 50), (0, 50)],
        dxfattribs={"layer": "OGR_EXTERNAL"})
    msp.add_lwpolyline([(200, 0), (210, 0), (210, 10), (200, 10),
                        (200, 0)], dxfattribs={"layer": "OGR_EXTERNAL"})
    msp.add_line((30, 25), (70, 22), dxfattribs={"layer": "OGR_MATERIAL"})
    doc.saveas(str(path))
    return path


def _make_clean(path=_CLEAN):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for name in ("OGR_EXTERNAL", "OGR_MATERIAL"):
        if name not in doc.layers:
            doc.layers.add(name)
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)],
                       dxfattribs={"layer": "OGR_EXTERNAL"},
                       close=True)
    msp.add_line((0, 25), (100, 25), dxfattribs={"layer": "OGR_MATERIAL"})
    doc.saveas(str(path))
    return path


def _pv(path, weld=0.05):
    return preview(path, ImportOptions(unit="m", weld_pct=weld))


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestPanelContents:
    def _panel(self, pv=None, canvas=None):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        return DxfProblemsPanel(pv or _pv(_make_messy()), canvas, None)

    def test_lists_every_problem(self):
        pv = _pv(_make_messy())
        p = self._panel(pv)
        assert p.problem_count() == len(pv.report.problems)
        assert p.problem_count() >= 3

    def test_grouped_by_kind(self):
        p = self._panel()
        kinds = set()
        for i in range(p.tree.topLevelItemCount()):
            data = p.tree.topLevelItem(i).data(0, Qt.UserRole)
            assert data[0] == "kind"
            kinds.add(data[1])
        assert "dangling_end" in kinds
        assert len(kinds) >= 2

    def test_dangling_ends_are_grouped_together(self):
        """Two dangling ends must be one group with two children, not two
        groups: the user fixes them as one kind of problem."""
        p = self._panel()
        for i in range(p.tree.topLevelItemCount()):
            top = p.tree.topLevelItem(i)
            if top.data(0, Qt.UserRole)[1] == "dangling_end":
                assert top.childCount() == 2
                return
        raise AssertionError("no dangling_end group")

    def test_errors_come_first(self):
        """Ordering by severity: an error must never be listed below a
        warning."""
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        pv = _pv(_make_messy())
        pv.report.add_problem("external_missing", "synthetic error")
        p = self._panel(pv)
        sev = []
        for i in range(p.tree.topLevelItemCount()):
            kind = p.tree.topLevelItem(i).data(0, Qt.UserRole)[1]
            sev.append(DxfProblemsPanel._severity(kind))
        assert sev[0] == "error", sev
        assert sev == sorted(sev, key=lambda s: 0 if s == "error" else 1)

    def test_coordinates_shown_when_known(self):
        p = self._panel()
        found = False
        for i in range(p.tree.topLevelItemCount()):
            top = p.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).text(1):
                    found = True
        assert found, "no problem showed coordinates"

    def test_header_counts_errors_separately(self):
        pv = _pv(_make_messy())
        pv.report.add_problem("external_missing", "synthetic error")
        p = self._panel(pv)
        assert p.error_count() == 1
        assert "error" in p.lbl_head.text().lower()

    def test_clean_import_says_so(self):
        p = self._panel(_pv(_make_clean(), weld=0.2))
        assert p.problem_count() == 0
        assert "No problems" in p.lbl_head.text()
        assert p.btn_zoom.isEnabled() is False


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestAdvice:
    def _panel(self):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        return DxfProblemsPanel(_pv(_make_messy()), None, None)

    def test_every_known_kind_has_advice(self):
        from ogr_gui.dialogs.dxf_problems_panel import (
            _PROBLEM_INFO, DxfProblemsPanel,
        )
        for kind in _PROBLEM_INFO:
            advice = DxfProblemsPanel._advice(kind)
            assert advice and len(advice) > 30, kind

    def test_advice_names_the_setting_to_change(self):
        """Advice is only useful if it says what to do: the welding
        tolerance is the lever for most of these."""
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        for kind in ("dangling_end", "regions", "area_mismatch"):
            assert "welding tolerance" in DxfProblemsPanel._advice(kind)

    def test_advice_shown_on_selection(self):
        p = self._panel()
        p.tree.setCurrentItem(p.tree.topLevelItem(0))
        assert len(p.lbl_advice.text()) > 30

    def test_unknown_kind_does_not_crash(self):
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        assert DxfProblemsPanel._severity("nonsense") == "warning"
        assert isinstance(DxfProblemsPanel._advice("nonsense"), str)


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestNavigation:
    def _setup(self):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        from ogr_gui.main_window import MainWindow
        opts = ImportOptions(unit="m", weld_pct=0.05)
        pv = preview(_make_messy(), opts)
        proj = Project(name="dxf")
        apply_to_project(proj, pv, opts)
        w = MainWindow()
        w.canvas.set_project(proj)
        w.project = proj
        w.canvas.zoom_all()
        return w, DxfProblemsPanel(pv, w.canvas, w)

    def _centre(self, w):
        c = w.canvas.mapToScene(w.canvas.viewport().rect().center())
        return c.x(), c.y()

    def _first_located(self, panel):
        for i in range(panel.tree.topLevelItemCount()):
            top = panel.tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                data = child.data(0, Qt.UserRole)
                if data[1] is not None:
                    return child, (data[1], data[2])
        raise AssertionError("no located problem")

    def test_selecting_centres_the_canvas(self):
        w, panel = self._setup()
        before = self._centre(w)
        child, (x, y) = self._first_located(panel)
        panel.tree.setCurrentItem(child)
        after = self._centre(w)
        assert after != before
        assert abs(after[0] - x) < 2.0, (after, x)
        assert abs(after[1] - y) < 2.0, (after, y)

    def test_go_to_problem_zooms_closer(self):
        w, panel = self._setup()
        child, (x, y) = self._first_located(panel)
        panel.tree.setCurrentItem(child)
        wide = w.canvas.transform().m11()
        panel._go_to_current()
        close = w.canvas.transform().m11()
        assert close > wide, (wide, close)

    def test_vertical_flip_is_preserved(self):
        """The model has y upwards; a naive fitInView would flip it."""
        w, panel = self._setup()
        child, _pt = self._first_located(panel)
        panel.tree.setCurrentItem(child)
        panel._go_to_current()
        assert w.canvas.transform().m22() < 0

    def test_zoom_all_restores_the_overview(self):
        w, panel = self._setup()
        child, _pt = self._first_located(panel)
        panel.tree.setCurrentItem(child)
        panel._go_to_current()
        zoomed = self._centre(w)
        panel._zoom_all()
        assert self._centre(w) != zoomed

    def test_group_row_has_no_location(self):
        _w, panel = self._setup()
        panel.tree.setCurrentItem(panel.tree.topLevelItem(0))
        assert panel._current_point() is None
        assert panel.btn_zoom.isEnabled() is False

    def test_panel_without_canvas_is_safe(self):
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        QApplication.instance() or QApplication([])
        panel = DxfProblemsPanel(_pv(_make_messy()), None, None)
        child, _pt = self._first_located(panel)
        panel.tree.setCurrentItem(child)
        panel._go_to_current()      # must not raise


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestAreaMismatchInjection:
    def test_area_mismatch_is_reported_first(self):
        """The sanitiser cannot know about it — it only emerges once
        regions are built — so the panel injects it, and it must lead."""
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        pv = _pv(_make_messy())
        # Force a mismatch
        pv.external_area = 1000.0
        pv.region_area = 800.0
        panel = DxfProblemsPanel(pv, None, None)
        first_kind = panel.tree.topLevelItem(0).data(0, Qt.UserRole)[1]
        assert first_kind == "area_mismatch"
        assert DxfProblemsPanel._severity("area_mismatch") == "error"

    def test_matching_areas_add_nothing(self):
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        QApplication.instance() or QApplication([])
        pv = _pv(_make_clean(), weld=0.2)
        panel = DxfProblemsPanel(pv, None, None)
        kinds = [panel.tree.topLevelItem(i).data(0, Qt.UserRole)[1]
                 for i in range(panel.tree.topLevelItemCount())]
        assert "area_mismatch" not in kinds


# ======================================================================
@_requires(_QT)
class TestCanvasZoomToPoint:
    def test_centres_and_keeps_orientation(self):
        QApplication.instance() or QApplication([])
        from test_slide_validation_ej1 import _ej1_project
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        p = _ej1_project()
        w.canvas.set_project(p)
        w.project = p
        w.canvas.zoom_all()
        w.canvas.zoom_to_point(75.0, 25.0)
        c = w.canvas.mapToScene(w.canvas.viewport().rect().center())
        assert abs(c.x() - 75.0) < 3.0
        assert abs(c.y() - 25.0) < 3.0
        assert w.canvas.transform().m22() < 0

    def test_half_width_controls_the_zoom(self):
        QApplication.instance() or QApplication([])
        from test_slide_validation_ej1 import _ej1_project
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        p = _ej1_project()
        w.canvas.set_project(p)
        w.project = p
        w.canvas.zoom_to_point(75.0, 25.0, half_width=20.0)
        wide = w.canvas.transform().m11()
        w.canvas.zoom_to_point(75.0, 25.0, half_width=2.0)
        close = w.canvas.transform().m11()
        assert close > wide
