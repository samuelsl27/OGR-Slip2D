# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.500 (D438) — the centre map of Interpret, its legend, Minimum Surfaces
and the agent's ``minimum_per_centre`` view read a Ky or Newmark run by
what the run reports, not by the factor.

Since v0.1.450 (D423) the report's figure draws, at each slip centre, the
surface the run would pick there (``critical_per_centre``: the lowest Ky,
the largest Newmark displacement). The other doors kept the lowest factor
of each centre on a run whose critical surface is the lowest Ky. Measured
with 0.1.485 and 0.1.499 on the demo slope with c = 20 kPa, a 5×5×6 grid
and Bishop, Ky without a standard: the critical surface has Ky 0.2941 at
(40, 45), and Interpret's legend read «Factor of safety» with its mark at
1.6237, its lowest cell «(34, 29) — FoS = 1.529», and the first row of the
API's view fos 1.528675 at (34, 29) (the bench's ``medir_d423.py``).

The owner's decision (option a, in the three doors; the view keeps its
key). The invariants, on a 5×5×3 grid that keeps the separation (the
critical surface at (40, 37) with Ky 0.3117, the lowest factor at (34, 29)):

* the premise, measured and written: the centre of the lowest factor is
  not the critical centre, and at some centre the surface of the lowest Ky
  is not the one of the lowest factor;
* an identity: what each door shows at a centre is the run's number
  (``reported_value``) of the surface ``critical_per_centre`` picks there —
  the map's cells, the surfaces Minimum Surfaces draws, and the API's rows;
  the API's first row is the critical surface, and the legend is titled by
  the run's quantity with its mark at the critical surface's number;
* with Newmark, the same with the displacement, in the project's unit, and
  ``ranked_by`` says so;
* on a run of factors nothing moves: the view is the lowest factor of each
  centre ordered by it, without ``ranked_by``, and the window draws
  ``minimum_per_centre``.

Cost: three runs of a 5×5×3 grid (about 0.35 s each) and three Interpret
windows, offscreen.
"""
from __future__ import annotations

import math
import re

_METHOD = "bishop_simplified"
_RUNS: dict = {}


def _project(mode):
    """The demo slope with c = 20 kPa: "ky", "newmark" or "fos"."""
    from examples.quick_slope import build_demo_slope
    from ogr_core.loads.seismic_record import SeismicRecord
    p = build_demo_slope()
    p.materials[0].strength.params["cohesion"] = 20.0
    s = p.settings.search
    s.grid_nx, s.grid_ny, s.radius_increment = 5, 5, 3
    p.settings.methods.enabled_methods = [_METHOD]
    cfg = p.settings.seismic
    if mode == "ky":
        cfg.compute_ky = True
    if mode == "newmark":
        rec = SeismicRecord(name="sinusoid", dt=0.01, accelerations=[
            0.3 * math.sin(2 * math.pi * 2 * i * 0.01) for i in range(400)])
        p.seismic_records = [rec]
        cfg.newmark, cfg.record_id = True, rec.id
    return p


def _run(mode):
    if mode not in _RUNS:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _project(mode)
        _RUNS[mode] = (p, run_analysis(p))
    return _RUNS[mode]


def _sr(mode):
    return _run(mode)[1].results[_METHOD]


def _centre(r):
    from ogr_slip2d.interpretation import slip_centre
    c = slip_centre(r.surface.to_dict())
    return None if c is None else (round(c[0], 3), round(c[1], 3))


def _view(mode, n=1000):
    """The API's view, through its own function (no job to start)."""
    from ogr_api.ops.statistics import _search_view
    return _search_view(None, _sr(mode), "minimum_per_centre", None, None,
                        None, None, None, None, None, n, None, False)


def _window(mode):
    """What Interpret shows of the run: ``(legend title, legend mark,
    {centre: cell value}, [the surfaces drawn])``."""
    from PySide6.QtWidgets import QApplication, QGraphicsRectItem
    app = QApplication.instance() or QApplication([])
    from ogr_gui.canvas.graphics_items import SlipSurfaceItem
    from ogr_gui.interpret_window import InterpretWindow
    p, out = _run(mode)
    w = InterpretWindow(p, out.results, None, factor_report=out.factor_report)
    try:
        cells = {}
        for it in w.canvas._result_items:
            if isinstance(it, QGraphicsRectItem):
                m = re.search(r"\(([-\d.]+), ([-\d.]+)\).* = ([-\d.]+)$",
                              it.toolTip())
                cells[(float(m.group(1)), float(m.group(2)))] = float(
                    m.group(3))
        # Minimum Surfaces (the Data menu's door): the window opens on the
        # Global Minimum
        w._set_surface_mode("minimum")
        drawn = [it.surface_dict for it in w.canvas._result_items
                 if isinstance(it, SlipSurfaceItem)]
        return w.legend._title, w.legend._mark, cells, drawn
    finally:
        w.close()
        w.deleteLater()
        app.processEvents()


def _picked(mode):
    """``{centre: surface}`` of ``critical_per_centre``."""
    from ogr_slip2d.interpretation import critical_per_centre
    return {_centre(r): r for r in critical_per_centre(_sr(mode))
            if _centre(r) is not None}


class TestThePremise:

    def test_the_lowest_factor_is_not_at_the_critical_centre(self):
        from ogr_slip2d.interpretation import minimum_per_centre
        sr = _sr("ky")
        lowest = min(minimum_per_centre(sr), key=lambda r: r.fos)
        assert _centre(lowest) != _centre(sr.critical)

    def test_some_centre_picks_another_surface_by_ky(self):
        from ogr_slip2d.interpretation import minimum_per_centre
        by_fos = {_centre(r): r for r in minimum_per_centre(_sr("ky"))}
        picked = _picked("ky")
        assert any(by_fos[c] is not picked[c] for c in picked)


class TestTheAgentsView:

    def test_the_first_row_is_the_critical_surface(self):
        sr = _sr("ky")
        out = _view("ky")
        first = out["surfaces"][0]
        assert out["ranked_by"] == "ky"
        assert (first["surface"]["centre_x"], first["surface"]["centre_y"]) \
            == tuple(sr.critical.surface.to_dict()[k]
                     for k in ("centre_x", "centre_y"))
        assert abs(first["details"]["ky"] - sr.critical.details["ky"])             <= 5e-7

    def test_each_row_is_the_surface_of_its_centre(self):
        picked = _picked("ky")
        out = _view("ky")
        assert out["count"] == len(picked)
        for row in out["surfaces"]:
            c = (round(row["surface"]["centre_x"], 3),
                 round(row["surface"]["centre_y"], 3))
            # the view's numbers are rounded to 6 decimals
            assert abs(row["details"]["ky"] - picked[c].details["ky"])                 <= 5e-7

    def test_newmark_ranks_by_the_displacement(self):
        sr = _sr("newmark")
        out = _view("newmark")
        assert out["ranked_by"] == "newmark_displacement"
        moved = [row["details"]["newmark_displacement"]
                 for row in out["surfaces"]]
        assert abs(moved[0] - sr.critical.details["newmark_displacement"])             <= 5e-7
        assert moved[0] == max(moved)

    def test_a_run_of_factors_is_what_it_was(self):
        from ogr_api.ops.statistics import _row
        from ogr_slip2d.interpretation import minimum_per_centre
        sr = _sr("fos")
        out = _view("fos")
        assert "ranked_by" not in out
        rows = sorted(minimum_per_centre(sr), key=lambda r: r.fos)
        assert out["surfaces"] == [_row(sr, r) for r in rows]


class TestTheWindow:

    def test_ky_cells_legend_and_minimum_surfaces(self):
        from ogr_slip2d.interpretation import reported_value
        sr = _sr("ky")
        title, mark, cells, drawn = _window("ky")
        assert title == "Critical seismic coefficient"
        assert mark == sr.critical.details["ky"]
        picked = _picked("ky")
        assert set(cells) == {(round(c[0], 2), round(c[1], 2))
                              for c in picked}
        for c, r in picked.items():
            cell = cells[(round(c[0], 2), round(c[1], 2))]
            assert abs(cell - reported_value(sr, r)) <= 5e-5, (c, cell)
        lowest = min(cells, key=cells.get)
        crit = _centre(sr.critical)
        assert lowest == (round(crit[0], 2), round(crit[1], 2))
        ids = {d.get("id") for d in drawn}
        assert {r.surface.to_dict().get("id")
                for r in picked.values()} <= ids

    def test_newmark_legend_is_the_displacement_in_its_unit(self):
        from ogr_slip2d.reported import displacement_in_units
        p, _out = _run("newmark")
        sr = _sr("newmark")
        title, mark, cells, _drawn = _window("newmark")
        value, unit = displacement_in_units(
            p, sr.critical.details["newmark_displacement"])
        assert title == "Newmark displacement [%s]" % unit
        assert mark == value
        assert abs(max(cells.values()) - value) <= 5e-4

    def test_a_run_of_factors_draws_the_lowest_factor(self):
        from ogr_slip2d.interpretation import minimum_per_centre
        sr = _sr("fos")
        title, mark, cells, drawn = _window("fos")
        assert title == "Factor of safety" and mark == sr.critical.fos
        by_fos = minimum_per_centre(sr)
        for r in by_fos:
            c = _centre(r)
            assert abs(cells[(round(c[0], 2), round(c[1], 2))] - r.fos) \
                <= 5e-4
        ids = {d.get("id") for d in drawn}
        assert {r.surface.to_dict().get("id") for r in by_fos} <= ids
