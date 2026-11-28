# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D455 (v0.1.514) — a force per metre of slope is written in kN/m.

The invariant
-------------
``LEMResult`` gives the slice forces per metre of slope, in kN/m
(``ogr_slip2d/methods/base.py``: «ALL THREE ARE FORCES, in kN/m per
unit…»), and Sarma's face table in the PDF report already writes ``PW``,
``E``, ``E′`` and ``X`` in ``[kN/m]``. The slice-data panel of Interpret
wrote its nine forces in «(kN)» (the weight, the base normal, the driving
shear and the E, X, E′ to either side), so the same number read as a force
in one place and a force per metre in the next. The owner's decision
(2026-11-28): one unit, kN/m, which is what the number is. No number
moves; only the unit written.

Checked here, on the panel's own table (``_SliceDataDock.FIELDS``):

* no row writes «(kN)»;
* the nine force rows write «(kN/m)», in English and in Spanish;
* the units that were right stay: kN/m³ for the unit weight, kPa for the
  stresses.

And the report's slice table, which is OGR Core's: since 0.2.15 (pinned in
v0.1.521) it heads the weight «Weight [kN/m]», as its face table heads PW,
E, E′ and X; until 0.2.14 it wrote [kN].

Cost: reads a table and a dictionary, and slices one circle of the demo
slope for the report's table; no window.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_FORCES = ("Weight W", "Base normal force N", "Driving shear W·sinα",
           "E left", "E right", "X left", "X right", "E′ left", "E′ right")


def _labels():
    from ogr_gui.interpret_window import _SliceDataDock
    return [label for label, _fn in _SliceDataDock.FIELDS]


class TestForceUnits:
    def test_no_row_writes_kn_alone(self):
        assert [lb for lb in _labels() if "(kN)" in lb] == []

    def test_the_nine_forces_are_per_metre(self):
        labels = _labels()
        for name in _FORCES:
            assert f"{name} (kN/m)" in labels, name

    def test_and_in_spanish(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for name in _FORCES:
            text = es.get(f"{name} (kN/m)")
            assert text is not None and text.endswith("(kN/m)"), (name, text)

    def test_the_right_units_stay(self):
        labels = _labels()
        assert "Unit weight γ (kN/m³)" in labels
        assert "Pore pressure u (kPa)" in labels
        assert "Base normal stress σₙ (kPa)" in labels

    def test_the_report_slice_table_heads_the_weight_per_metre(self):
        """v0.1.521 -- OGR Core 0.2.15 (D455)."""
        import ogr_core.report.report_generator as RG
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.surface import SlipCircle
        p = build_demo_project()
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        ev = build_search(p, "bishop_simplified").evaluate_circle(
            p, SlipCircle(centre_x=34.0, centre_y=30.0, radius=130 ** 0.5))
        header = [str(c) for c in RG._slice_table(ev, p)._cellvalues[0]]
        weight = [c for c in header if c.startswith("Weight")]
        assert weight and all(c.endswith("[kN/m]") for c in weight), header
        assert not any(c.endswith("[kN]") for c in header), header
