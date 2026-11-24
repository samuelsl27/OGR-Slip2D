# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.468 (D357, D453) — the report and the exports with Sarma's wedges.

WHAT THIS VERSION CHANGES

Until v0.1.467 what leaves the program showed a result of Sarma's method as
vertical slices, or left its faces out: the PDF report had no table of the
faces, no setting of ``settings.sarma`` and no number of the method (Kc,
the least |q|); the CSV of Interpret, the API and the HDF5 file gave no
angle, strength or force of a face (the API gave E, E′ and X alone, the
HDF5 the geometry and PW alone), and the API no polygon of a wedge.

And D453, older than Sarma: the report's slice table headed «Base σ [kPa]»
and «Shear str. [kPa]» and printed ``base_normal_force`` and
``base_shear_strength``, which the contract of ``LEMResult`` declares
FORCES in kN/m (v0.1.107), in every method. The panel of Interpret divided
them by the base length; the report did not. The rule now lives in ONE
place, ``ogr_core.result_rows``, which the report, the panel, the CSV, the
API and the HDF5 file ask.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **D453, the slice table prints stresses**: on the reference's own Slice
   Data table of Ej_2 (the ordinary method's critical circle, row 1:
   σn = 8.80223 kPa, τ_f = 31.082 kPa; the fixture and the row of
   ``test_interpret_slice_data_v187``), the report prints 8.80 and 31.08
   (v0.1.467 printed 9.31 and 32.87, the forces); and on every slice of a
   Bishop and of a Sarma result the cell is N/l and S/l, divided here by
   hand, at the cell's rounding. Graph Query of Interpret plots the same
   numbers, and a gap (NaN) where there is none, not a 0.
2. **The faces of problem 4** (Hoek 1987; the published geometry, with
   its interface from the kink to the ground at x = 82.85, D122),
   saturated, 2 wedges: the interface ends where the figure has it, at the
   angle and length of that segment in closed form; its water thrust is
   the hydrostatic triangle ½·γw·(y_wt − y_kink)·L (the water table is the
   slope, so u is linear along the face and zero at its top); its c̄ and φ̄
   are the spoil's (100 kPa, 42°); E′ = E − PW; E, E′ and X are the
   method's. The faces count from 0, as the wedges. A spilled population
   gives the same rows. A filled tension crack at the head (the review of
   0.1.468): its water, ½·γw·h², is the PW of the head face, whose E′ is
   then 0, on both senses of sliding.
3. **The report**, laid out by reportlab (the texts its Paragraphs and
   Tables are built with, the pattern of ``test_report_global_minimums_
   v1447``), on problem 4 with the 25 wedges of the settings, of which the
   surface keeps fewer: with Sarma it writes the face table (one row per
   face, at the rows' rounding), the block of Sarma's settings (each
   setting changed moves its row: rule 7; the number of wedges asked for,
   apart from the wedges the surface has; its English row is OGR-Core's,
   «Least Number of Wedges» until a new core renames it, and its Spanish
   «Número de cuñas pedido» since v0.1.488, D454) and
   Kc, the least |q|, the force ratio, the wedges and the faces made
   vertical of the critical (one, on the fixture of
   ``test_sarma_method_v1464`` whose bisectors cross); without Sarma, none
   of it.
4. **The exports**: Interpret's CSV writes ``<name>_faces.csv`` beside the
   chosen file with the face rows, and none without Sarma; the API's
   ``sarma_faces`` carries the new keys and the three of v0.1.464, and
   ``slice_table`` the polygon and the area of each wedge (the toe wedge's
   area is the triangle's in closed form), and of no vertical slice; the
   HDF5 ``faces`` has its twelve columns, named as the rows' keys, with
   their values (NaN where a row has None), and a file without Sarma has
   no ``faces``.
5. **The Spanish** of every new label.

The two cases are solved once per module (about 0.2 s each); the two
reports and the two windows are most of this file's time.
"""
from __future__ import annotations

import csv
import math
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_interpret_v1467 as T67  # noqa: E402
import test_sarma_pole_v1466 as T66  # noqa: E402
import test_sarma_wedges_v1463 as W63  # noqa: E402

_CACHE: dict = {}

#: Problem 4's interface (``W63._THETA4``): from the kink (108, 6.4) to the
#: ground at x = 82.85, on the slope y = 76.5·x / 111.4.
_TOP4 = (82.85, 76.5 * 82.85 / 111.4)
_GAMMA_W = 9.81


def _case(n):
    """Problem 4 saturated with ``n`` wedges and the published interface,
    solved here (``test_shared_test_caches_v1378``: another file's memo is
    its object in the serial run and a fresh one under --jobs)."""
    key = ("sarma", n)
    if key not in _CACHE:
        p, s = T67._p4(True, n)
        _CACHE[key] = (p, T66._door(p, s)[0])
    return _CACHE[key]


def _sarma():
    """Problem 4 saturated, 2 wedges, the published interface."""
    return _case(2)


def _sarma25():
    """Problem 4 saturated with 25 wedges asked for: the surface keeps
    fewer, the divisions whose bisectors cross taken away."""
    return _case(25)


def _bishop():
    """Bishop on problem 4's published surface, saturated."""
    if "bishop" not in _CACHE:
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p, s, _angles = W63._problem4(True)
        r = evaluate_surfaces(p, s, ["bishop_simplified"]).results[
            "bishop_simplified"]
        _CACHE["bishop"] = (p, r)
    return _CACHE["bishop"]


def _ej2():
    if "ej2" not in _CACHE:
        import test_interpret_slice_data_v187 as T187
        _CACHE["ej2"] = T187._ej2_reference_result()
    return _CACHE["ej2"]


def _search(result):
    from ogr_slip2d.search import SearchResult
    sr = SearchResult(method_id=result.method_id)
    sr.evaluations = [result]           # the critical is derived from it
    return sr


def _cells(table) -> list:
    return [list(row) for row in table._cellvalues]


def _column(header, start) -> int:
    return next(i for i, h in enumerate(header) if h.startswith(start))


@contextmanager
def _swapped(owner, name, value):
    kept = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, kept)


def _report(project, results):
    """What the report writes, in order: ``("p", text)`` for a paragraph
    (its bold taken off) and ``("t", rows)`` for a table of plain text."""
    import ogr_core.report.report_generator as RG
    said = []
    real_p, real_t = RG.Paragraph, RG.Table

    class Par(real_p):
        def __init__(self, text, *a, **k):
            said.append(("p", re.sub(r"</?b>", "", str(text))))
            super().__init__(text, *a, **k)

    class Tab(real_t):
        def __init__(self, data, *a, **k):
            if all(isinstance(c, str) for row in data for c in row):
                said.append(("t", [list(row) for row in data]))
            super().__init__(data, *a, **k)

    with _swapped(RG, "Paragraph", Par), _swapped(RG, "Table", Tab):
        with tempfile.TemporaryDirectory() as d:
            RG.generate_report(project, results, os.path.join(d, "r.pdf"))
    return said


def _sarma_report():
    if "report" not in _CACHE:
        p, r = _sarma25()
        pb, rb = _bishop()
        _CACHE["report"] = _report(p, {"bishop_simplified": _search(rb),
                                       "sarma": _search(r)})
    return _CACHE["report"]


def _values_after(said, key) -> list:
    """The paragraph after each paragraph ``key``: a row of a kv table."""
    texts = [v for k, v in said if k == "p"]
    return [texts[i + 1] for i, t in enumerate(texts) if t == key]


# ======================================================================
class TestD453TheSliceTablePrintsStresses:

    def test_the_references_row_1(self):
        from ogr_core.report.report_generator import _slice_table
        p, res = _ej2()
        rows = _cells(_slice_table(res, p))
        sigma = _column(rows[0], "Base σ")
        tau = _column(rows[0], "Shear str.")
        # the reference's Slice Data table, row 1 (T187.REFERENCE_ROW_1)
        assert abs(float(rows[1][sigma]) - 8.80223) <= 0.005 + 1e-9, rows[1]
        assert abs(float(rows[1][tau]) - 31.082) <= 0.005 + 1e-9, rows[1]

    def test_every_cell_is_the_force_over_the_base_length(self):
        from ogr_core.report.report_generator import _slice_table
        for label, (p, res) in (("bishop", _bishop()), ("sarma", _sarma())):
            rows = _cells(_slice_table(res, p))
            sigma = _column(rows[0], "Base σ")
            tau = _column(rows[0], "Shear str.")
            slices = list(res.slices)
            assert len(rows) == len(slices) + 1
            apart = 0
            for row, s in zip(rows[1:], slices):
                i = s.index
                n = res.base_normal_force[i] / s.base_length
                t = res.base_shear_strength[i] / s.base_length
                assert abs(float(row[sigma]) - n) <= 0.005 + 1e-9 * abs(n), (
                    label, i, row[sigma], n)
                assert abs(float(row[tau]) - t) <= 0.005 + 1e-9 * abs(t), (
                    label, i, row[tau], t)
                # what v0.1.467 printed, the force, is another number here
                apart += abs(res.base_normal_force[i] - n) > 0.01
            assert apart, label

    def test_graph_query_plots_the_same_rule(self):
        """Interpret's Graph Query kept a copy of the rule (the review of
        0.1.468): a base of no length was divided by 1e-12 and a slice
        without a number plotted at 0."""
        import dataclasses

        from ogr_gui.interpret_window import InterpretWindow
        value = InterpretWindow._slice_value
        _p, res = _bishop()
        for i, s in enumerate(res.slices):
            n = res.base_normal_force[s.index] / s.base_length
            t = res.base_shear_strength[s.index] / s.base_length
            assert abs(value(res, s, i, "base_normal_force") - n) <= (
                1e-12 * abs(n))
            assert abs(value(res, s, i, "shear_strength") - t) <= (
                1e-12 * abs(t))
        flat = dataclasses.replace(next(iter(res.slices)), base_length=0.0)
        assert math.isnan(value(res, flat, 0, "base_normal_force"))
        assert math.isnan(value(res, flat, 0, "shear_stress"))


# ======================================================================
class TestTheFacesOfProblem4:

    def test_the_interface_is_the_figures(self):
        from ogr_core.result_rows import face_rows
        _p, r = _sarma()
        rows = face_rows(r)
        # from 0, as the wedges (``Slice.index``)
        assert [f["index"] for f in rows] == [0, 1, 2]
        assert [s.index for s in r.slices] == [0, 1]
        f = rows[1]
        assert (f["x_base"], f["y_base"]) == (108.0, 6.4)
        assert abs(f["x_top"] - _TOP4[0]) <= 1e-6, f
        assert abs(f["y_top"] - _TOP4[1]) <= 1e-6, f
        dx, dy = _TOP4[0] - 108.0, _TOP4[1] - 6.4
        assert abs(f["angle_deg"] - math.degrees(math.atan2(dy, dx))) <= 1e-6
        assert abs(f["angle_deg"] - 116.48) <= 0.005, f["angle_deg"]
        assert abs(f["length"] - math.hypot(dx, dy)) <= 1e-6, f
        assert f["angle_source"] == "vertex"
        # the spoil's strength (Hoek 1987), from the materials
        assert f["strength_source"] == "materials"
        assert abs(f["cohesion"] - 100.0) <= 1e-12
        assert abs(f["friction_angle"] - 42.0) <= 1e-9
        # the hydrostatic triangle: u = 0 at the top (on the water table),
        # γw·(y_wt − y) at the kink, linear between
        pw = 0.5 * _GAMMA_W * (76.5 * 108.0 / 111.4 - 6.4) * math.hypot(dx, dy)
        assert abs(f["water_force"] / pw - 1.0) <= 1e-6, (f["water_force"], pw)
        # the two ends are points on the ground
        for end in (rows[0], rows[2]):
            assert end["angle_source"] == "end" and end["length"] == 0.0

    def test_the_forces_are_the_methods(self):
        from ogr_core.result_rows import face_rows
        _p, r = _sarma()
        rows = face_rows(r)
        d = r.details
        assert [f["E"] for f in rows] == list(d["sarma_face_thrusts"])
        assert [f["E_effective"] for f in rows] == list(
            d["sarma_face_effective"])
        assert [f["X"] for f in rows] == list(d["sarma_face_shears"])
        f = rows[1]
        assert f["E"] > 0 and f["X"] > 0, f
        assert abs(f["E_effective"] - (f["E"] - f["water_force"])) <= (
            1e-9 * f["E"]), f

    def test_a_tension_crack_is_the_head_faces_water(self):
        """A filled crack 4 m deep at the head: its water, ½·9.81·4², acts
        on the head face, which is the last in x when the slope slides
        toward −x and the first when it is mirrored. E there is that water
        alone, so E′ = 0 (it was E′ = E = 78.5 with PW = 0)."""
        from ogr_api.results import lem_summary
        from ogr_core.result_rows import face_rows
        water = 0.5 * _GAMMA_W * 4.0 ** 2
        factors = []
        for mirror in (False, True):
            p, s = W63._slope(crack=True, mirror=mirror)
            p.settings.sarma.num_slices = 4
            r, _out = T66._door(p, s)
            factors.append(r.fos)
            assert abs(r.slices.tension_crack_force - water) <= 1e-9
            rows = face_rows(r)
            head = rows[0] if mirror else rows[-1]
            toe = rows[-1] if mirror else rows[0]
            assert head["angle_source"] == "end" and abs(
                head["length"] - 4.0) <= 1e-9, head
            assert abs(head["water_force"] - water) <= 1e-9, head
            assert abs(head["E"] - water) <= 1e-9 and abs(
                head["E_effective"]) <= 1e-9, head
            assert toe["water_force"] == 0.0 and toe["E"] == 0.0
            # an interior face keeps its own water: E′ = E − PW
            for f in rows[1:-1]:
                assert abs(f["E_effective"] - (f["E"] - f["water_force"])) \
                    <= 1e-9 * abs(f["E"]), f
            api = lem_summary(r)["details"]["sarma_faces"]
            assert abs(api[rows.index(head)]["water_force"] - water) <= 1e-6
        assert abs(factors[0] - factors[1]) <= 1e-12 * factors[0], factors

    def test_another_method_has_no_faces(self):
        from ogr_core.result_rows import face_rows
        assert face_rows(_bishop()[1]) == []
        assert face_rows(None) == []

    def test_a_spilled_population_gives_the_same_rows(self):
        from ogr_core.result_rows import face_rows
        from ogr_slip2d.slice_store import SliceStore
        p, s = T67._p4(True, 2)
        res, _out = T66._door(p, s)
        before = face_rows(res)
        store = SliceStore()
        store.spill(res)
        assert type(res.slices).__name__ == "SpilledSlices"
        assert face_rows(res) == before and len(before) == 3


# ======================================================================
class TestTheReport:

    def test_the_face_table(self):
        from ogr_core.report.report_generator import _fmt
        from ogr_core.result_rows import face_rows
        said = _sarma_report()
        tables = [v for k, v in said if k == "t" and v[0][0] == "#"
                  and "θ\n[°]" in v[0]]
        assert len(tables) == 1, len(tables)        # Sarma's alone
        rows = tables[0]
        head = rows[0]
        faces = face_rows(_sarma25()[1])
        assert len(rows) == len(faces) + 1
        for cells, f in zip(rows[1:], faces):
            # from 1, as the wedges of the slice table above it
            assert cells[0] == str(f["index"] + 1)
            for col, key, nd in (("x\n", "x_base", 2), ("y\n", "y_base", 2),
                                 ("θ", "angle_deg", 1),
                                 ("Length", "length", 2),
                                 ("PW", "water_force", 1),
                                 ("c̄", "cohesion", 1),
                                 ("φ̄", "friction_angle", 1),
                                 ("E\n", "E", 1), ("E′", "E_effective", 1),
                                 ("X\n", "X", 1)):
                assert cells[_column(head, col)] == _fmt(f[key], nd), (
                    col, cells, f)
        # its heading names the method, after Sarma's slice table
        texts = [v for k, v in said if k == "p"]
        assert any(t.startswith("Faces of the Wedges — ") for t in texts)

    def test_the_settings_block(self):
        said = _sarma_report()
        p, _r = _sarma25()
        sa = p.settings.sarma
        for key, value in (("Least Number of Wedges", str(sa.num_slices)),
                           ("Face Angles", "Bisector"),
                           ("Face Strength", "From the materials"),
                           ("Boundaries at Material Contacts",
                            "At every contact"),
                           ("Sense of the Face Shear",
                            "Fixed: the upper wedge moves down"),
                           ("Tolerance", str(sa.tolerance))):
            assert value in _values_after(said, key), (key, value)

    def test_a_setting_moves_its_row(self):
        """Rule 7: the block reads ``settings.sarma``, not a default."""
        from ogr_core.project import Project
        from ogr_core.report.report_generator import _sarma_settings_rows
        p = Project("v1468 settings")
        sa = p.settings.sarma
        before = dict(_sarma_settings_rows(p))
        assert "Face Cohesion [kPa]" not in before
        # its own tolerance and iterations, not the methods' ones
        p.settings.methods.tolerance = 0.0123
        p.settings.methods.max_iterations = 321
        sa.tolerance, sa.max_iterations = 1e-7, 77
        sa.num_slices, sa.slice_angles = 7, "mean_normal"
        sa.interslice_strength = "given"
        sa.interslice_cohesion, sa.interslice_phi = 12.5, 31.0
        sa.boundaries_at_materials = not sa.boundaries_at_materials
        sa.shear_sense = "kinematic"
        after = dict(_sarma_settings_rows(p))
        assert after["Least Number of Wedges"] == 7
        assert after["Tolerance"] == 1e-7 and after["Maximum Iterations"] == 77
        assert after["Face Angles"] == "Mean normal"
        assert after["Face Strength"] == "Given c and φ"
        assert after["Face Cohesion [kPa]"] == "12.500"
        assert after["Face Friction Angle [°]"] == "31.000"
        assert after["Boundaries at Material Contacts"] != before[
            "Boundaries at Material Contacts"]
        assert after["Sense of the Face Shear"] == (
            "Kinematic: the rigid wedges' own")

    def test_the_critical_surfaces_numbers(self):
        from ogr_core.report.report_generator import _fmt
        said = _sarma_report()
        _p, r = _sarma25()
        d = r.details
        for key, value in (("Kc at F = 1", _fmt(d["sarma_kc"], 4)),
                           ("Least |q| of the Faces",
                            _fmt(d["sarma_min_abs_q"], 3)),
                           ("Largest Force / Vertical Load",
                            _fmt(d["sarma_max_force_ratio"], 3)),
                           ("Faces Made Vertical",
                            str(int(d.get("sarma_verticalized") or 0)))):
            assert value in _values_after(said, key), (key, value)
        # the setting by its own name, apart from the wedges the critical
        # has (``len(slices)``, not its faces), which are fewer here
        n = _p.settings.sarma.num_slices
        assert len(r.slices) < n, (len(r.slices), n)
        assert _values_after(said, "Least Number of Wedges") == [str(n)]
        assert _values_after(said, "Number of Wedges") == [str(len(r.slices))]
        # Kc at F = 1 is a number here, not a dash
        assert re.fullmatch(r"-?\d+\.\d{4}", _fmt(d["sarma_kc"], 4))

    def test_a_face_made_vertical_is_counted(self):
        """The fixture of ``test_sarma_method_v1464`` whose bisectors cross
        near a concave bend: one face of the policy made vertical."""
        from ogr_core.report.report_generator import _sarma_result_rows
        from ogr_core.result_rows import face_rows
        close = ((10, 10), (20, 5), (24, 4.5), (38, 4.0625), (40, 4),
                 (60, 12), (70, 20))
        p, s = W63._slope(load=False, surface=close)
        p.settings.sarma.num_slices = 1
        r, _out = T66._door(p, s)
        made = [f for f in face_rows(r) if f["angle_source"] == "verticalized"]
        assert len(made) == 1 and abs(made[0]["angle_deg"] - 90.0) <= 1e-9
        assert dict(_sarma_result_rows(r))["Faces Made Vertical"] == 1

    def test_without_sarma_none_of_it(self):
        if "bishop_report" not in _CACHE:
            p, r = _bishop()
            _CACHE["bishop_report"] = _report(
                p, {"bishop_simplified": _search(r)})
        said = _CACHE["bishop_report"]
        texts = {v for k, v in said if k == "p"}
        for key in ("Kc at F = 1", "Least |q| of the Faces",
                    "Number of Wedges", "Least Number of Wedges",
                    "Face Angles"):
            assert key not in texts, key
        assert not any(t.startswith("Faces of the Wedges") for t in texts)
        assert not [v for k, v in said if k == "t" and "θ\n[°]" in v[0]]


# ======================================================================
def _export(result, project):
    """Interpret's Export Slice Data (CSV): ``(files, said)``, every file
    the export wrote, read back as rows, and what the status bar said."""
    import ogr_gui.interpret_window as IW
    from PySide6.QtWidgets import QMessageBox
    w = T67._window(result, project)

    def refuse(*_a, **_k):
        raise AssertionError("a modal box was about to open")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "slices.csv")
        with _swapped(IW, "get_save_file_name",
                      lambda *a, **k: (path, "")), \
                _swapped(QMessageBox, "critical", staticmethod(refuse)):
            w._export_slice_data_csv()
        files = {}
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), encoding="utf-8",
                      newline="") as fh:
                files[name] = list(csv.reader(fh))
    return files, w.statusBar().currentMessage()


class TestTheCSV:

    def test_the_faces_go_to_a_second_file(self):
        from ogr_core.result_rows import face_rows
        p, r = _sarma()
        files, said = _export(r, p)
        assert sorted(files) == ["slices.csv", "slices_faces.csv"], files
        assert len(files["slices.csv"]) == len(r.slices) + 1
        table = files["slices_faces.csv"]
        faces = face_rows(r)
        assert table[0] == list(faces[0])
        assert len(table) == len(faces) + 1
        for cells, f in zip(table[1:], faces):
            for key, cell in zip(table[0], cells):
                value = f[key]
                if isinstance(value, str):
                    assert cell == value, (key, cell)
                else:
                    assert float(cell) == value, (key, cell, value)
        assert "slices.csv" in said and "slices_faces.csv" in said, said

    def test_without_sarma_one_file(self):
        p, r = _bishop()
        files, said = _export(r, p)
        assert sorted(files) == ["slices.csv"], files
        assert "faces" not in said, said


# ======================================================================
class TestTheAPIAndTheHDF5:

    def test_sarma_faces(self):
        from ogr_api.results import lem_summary
        from ogr_core.result_rows import face_rows
        _p, r = _sarma()
        got = lem_summary(r)["details"]["sarma_faces"]
        faces = face_rows(r)
        assert len(got) == len(faces)
        for g, f in zip(got, faces):
            assert set(g) == set(f)
            # the three keys of v0.1.464
            assert {"E", "E_effective", "X"} <= set(g)
            assert g["angle_source"] == f["angle_source"]
            assert g["index"] == f["index"]
            for key in ("x_top", "angle_deg", "water_force", "E", "X"):
                assert abs(g[key] - f[key]) <= 1e-6 * (1 + abs(f[key])), key

    def test_the_wedges_polygon_and_area(self):
        from ogr_api.results import slice_table
        _p, r = _sarma()
        rows = slice_table(r)
        assert all("polygon" in row and "area" in row for row in rows)
        # the toe wedge is the triangle toe, kink, top of the interface
        (x1, y1), (x2, y2) = (108.0, 6.4), _TOP4
        triangle = 0.5 * abs(x1 * y2 - x2 * y1)
        assert abs(rows[0]["area"] / triangle - 1.0) <= 1e-6, (
            rows[0]["area"], triangle)
        assert rows[0]["polygon"][0] == [0.0, 0.0]
        # and no vertical slice carries them
        assert not any("polygon" in row or "area" in row
                       for row in slice_table(_bishop()[1]))

    def test_the_hdf5_faces(self):
        import h5py
        import numpy as np

        from ogr_core.project.results_io import save_results
        from ogr_core.result_rows import face_rows
        _p, r = _sarma()
        faces = face_rows(r)
        with tempfile.TemporaryDirectory() as folder:
            path = save_results(os.path.join(folder, "s.h5"), _search(r))
            plain = save_results(os.path.join(folder, "b.h5"),
                                 _search(_bishop()[1]))
            found = []
            with h5py.File(path, "r") as fh:
                fh.visititems(lambda name, obj: found.append(
                    (obj.attrs["columns"], np.array(obj)))
                    if name.endswith("/faces") else None)
            plain_faces = []
            with h5py.File(plain, "r") as fh:
                fh.visititems(lambda name, obj: plain_faces.append(name)
                              if name.endswith("/faces") else None)
        assert len(found) == 1 and not plain_faces
        columns, data = found[0]
        names = columns.split(",")
        # the rows' own names, as the API and the CSV give them
        assert names == ["x_base", "y_base", "x_top", "y_top", "length",
                         "water_force", "angle_deg", "cohesion",
                         "friction_angle", "E", "E_effective", "X"]
        assert set(names) <= set(faces[0])
        assert data.shape == (len(faces), 12)
        for row, f in zip(data, faces):
            got = dict(zip(names, row))
            for key in names:
                assert got[key] == f[key], key

    def test_a_force_the_method_did_not_give_is_nan_in_the_hdf5(self):
        """A surface without a factor keeps its faces and has no forces
        (E, E′, X None): a gap in the f8 columns, not a 0. The result is
        problem 4's with its forces taken away, which is what such a
        result carries."""
        import dataclasses

        import h5py
        import numpy as np

        from ogr_core.project.results_io import save_results
        _p, r = _sarma()
        gone = {k: [None] * 3 for k in ("sarma_face_thrusts",
                                        "sarma_face_effective",
                                        "sarma_face_shears")}
        bare = dataclasses.replace(r, details={**r.details, **gone})
        with tempfile.TemporaryDirectory() as folder:
            path = save_results(os.path.join(folder, "n.h5"), _search(bare))
            found = []
            with h5py.File(path, "r") as fh:
                fh.visititems(lambda name, obj: found.append(np.array(obj))
                              if name.endswith("/faces") else None)
        data = found[0]
        assert np.isnan(data[:, 9:]).all()
        assert np.isfinite(data[:, :9]).all()


# ======================================================================
class TestTheSpanish:

    def test_every_new_label(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        from ogr_core.report.report_generator import (_face_table,
                                                      _sarma_result_rows,
                                                      _sarma_settings_rows)
        p, r = _sarma()
        before = current_language()
        set_language("es")
        try:
            keys = [k for k, _v in _sarma_settings_rows(p, note_text)]
            keys += [k for k, _v in _sarma_result_rows(r, note_text)]
            values = [v for _k, v in _sarma_settings_rows(p, note_text)
                      if isinstance(v, str)]
            head = _cells(_face_table(r, p, note_text))[0]
            heading = note_text("Faces of the Wedges")
            message = note_text("Wedge and face data exported to %s and %s")
        finally:
            set_language(before)
        assert keys[:3] == ["Número de cuñas pedido", "Ángulo de las caras",
                            "Resistencia de las caras"], keys
        assert "Número de cuñas" in keys[3:], keys
        for k in ("Fronteras en los contactos de material",
                  "Sentido del cortante en las caras", "Kc con F = 1",
                  "Menor |q| de las caras", "Mayor fuerza / carga vertical",
                  "Caras puestas verticales"):
            assert k in keys, (k, keys)
        assert "En cada contacto" in values, values
        assert "Longitud\n[m]" in head, head
        assert heading == "Caras de las cuñas"
        assert message == ("Datos de las cuñas y de sus caras exportados a "
                           "%s y %s")
