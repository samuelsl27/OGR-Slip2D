# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D446 (v0.1.510) — the PDF report writes an integer coordinate with its
decimals, and a count without them.

The invariant
-------------
Until OGR Core 0.2.14 the report's ``_fmt`` wrote with decimals only a
``float`` and passed everything else through ``str()``: the demo slope,
whose vertices are integers, printed «0» where a real coordinate prints
«0.000», and with one vertex edited to (35.5; 15) the same row of the «List
of Coordinates» mixed «35.500» and «15» (the ficha, measured with 0.1.457).
The core treats every number that is not a ``bool`` as real (the owner's
decision B), and its census of the 52 calls found no count among them: the
counts were already written with ``str()`` at their call site. Here, end to
end through the report this program generates:

* every cell of the «List of Coordinates» of the demo slope has three
  decimals, the integer vertices included;
* with a vertex edited to (35.5; 15), its row reads «35.500» and «15.000»;
* the slice number of «Slice Data» stays a count, «1», «2»…, while the
  integer magnitudes of its row (the c and φ of the demo's clay, 0
  decimals by design) are unchanged.

The reference is the format itself: three decimals, the rule the report
states for coordinates. Cost: one small run (Bishop, a 3×3 grid) and two
reports.
"""
from __future__ import annotations

import os
import re
import tempfile

_THREE = re.compile(r"^-?\d+\.\d{3}$")
_RUN: list = []


def _run():
    if not _RUN:
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import run_analysis
        p = build_demo_project()
        s = p.settings.search
        s.grid_nx = s.grid_ny = 3
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        _RUN.append((p, run_analysis(p).results))
    return _RUN[0]


def _tables(project, results):
    """The cell texts of every table the report draws, in order."""
    import reportlab.platypus as RP

    import ogr_core.report.report_generator as RG
    seen = []
    real = RP.Table

    class Spy(real):
        def __init__(self, data, *a, **k):
            seen.append([[str(c) for c in row] for row in data])
            super().__init__(data, *a, **k)

    RP.Table = Spy
    had = hasattr(RG, "Table")
    if had:
        before, RG.Table = RG.Table, Spy
    try:
        with tempfile.TemporaryDirectory() as d:
            RG.generate_report(project, results, os.path.join(d, "r.pdf"))
    finally:
        RP.Table = real
        if had:
            RG.Table = before
    return seen


def _coordinate_tables(tables):
    return [t for t in tables if t and t[0] == ["X", "Y"]]


class TestTheListOfCoordinates:

    def test_every_cell_of_the_demo_has_three_decimals(self):
        p, results = _run()
        assert all(float(v.x).is_integer() and float(v.y).is_integer()
                   for b in p.boundaries for v in b.polyline.vertices), \
            "the premise: the demo's vertices are integers"
        coords = _coordinate_tables(_tables(p, results))
        assert len(coords) == len(p.boundaries)
        cells = [c for t in coords for row in t[1:] for c in row]
        assert cells and all(_THREE.match(c) for c in cells), cells

    def test_an_edited_vertex_reads_with_its_neighbours(self):
        import copy

        from ogr_core.geometry import Vertex
        p, results = _run()
        q = copy.deepcopy(p)
        ext = q.external_boundary()
        i = next(k for k, v in enumerate(ext.polyline.vertices)
                 if v.x > 0 and v.y > 0)
        ext.polyline.vertices[i] = Vertex(35.5, 15)
        coords = _coordinate_tables(_tables(q, results))
        rows = [row for t in coords for row in t[1:]]
        assert ["35.500", "15.000"] in rows, rows


class TestACountStaysACount:

    def test_the_slice_numbers(self):
        p, results = _run()
        tables = _tables(p, results)
        slices = [t for t in tables if t and t[0] and t[0][0] in ("#", "Slice")]
        assert slices, [t[0] for t in tables if t]
        numbers = [row[0] for row in slices[0][1:]]
        assert numbers[:3] == ["1", "2", "3"], numbers[:5]
