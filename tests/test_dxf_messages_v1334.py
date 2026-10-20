# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.334 (D314, second part) — the DXF import's problems carry a stable code.

What the sanitiser finds wrong with a drawing, and why a preview fails,
reached the import dialog and the problems panel in English: sentences with
their numbers baked in, under a raw ``[kind]`` prefix, and the panel's group
titles were the kind with spaces ("External gap"), passed through ``tr()``
with no entry. They now carry a code and its values beside the English
(``ogr_core.dxf.messages``), and the interface says them by code
(``ogr_gui.core_messages``).

The invariants, as in ``test_core_messages_v1333``:

* **the English does not move.** Each template, filled with a sample, equals
  the 0.1.333 expression that wrote it, copied here literally (rule 1);
* **every code has its Spanish** with the same fields, and every kind of
  problem the panel knows has a code and a title in Spanish;
* **the importer writes its codes**, on real drawings: an open external
  boundary, a second external, a dangling material line, a file that is not
  there, a drawing with no layer assigned, and the regions not tiling the
  external boundary;
* **no site writes a problem without its code**: an AST census of
  ``ogr_core`` refuses a call to ``add_problem`` (the sentence-only door,
  kept for scripts) and an ``error =`` on a preview without ``error_code``;
* **in Spanish, the dialog and the panel speak Spanish.** And the screen
  test of 0.1.321 loses its exception for "Could not read the DXF file: ",
  whose no-ghost rule would fail if the English came back.
"""
from __future__ import annotations

import ast
import re
import string
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[1]

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


def _samples() -> dict:
    """``{code: (args, sentence the 0.1.333 code wrote)}``, each right-hand
    side the old expression with the sample in place of its variables."""
    import ogr_core.dxf.messages as m
    gap, n, exc = 12.3456, 2, "boom"
    region_area, external_area = 800.0, 1000.0
    return {
        m.EMPTY: ({}, "No geometry was assigned to any "
                      "layer."),
        m.EXTERNAL: ({}, "The external boundary has fewer than "
                         "three vertices."),
        m.EXTERNAL_GAP: ({"gap": gap},
                         f"The external boundary was open by {gap:.3f} "
                         f"units and has been closed with a straight "
                         f"segment; check the result."),
        m.EXTERNAL_MISSING: ({}, "No layer was assigned to the external "
                                 "boundary; the model cannot define regions "
                                 "without one."),
        m.EXTERNAL_MULTIPLE: ({"count": n},
                              f"{n} external boundaries were found; the "
                              f"largest will be used and the rest ignored."),
        m.DANGLING_END: ({}, "A material boundary end does not reach any "
                             "other boundary, so the region will not "
                             "close."),
        m.REGIONS: ({"error": exc}, f"Regions could not be built: {exc}"),
        m.AREA_MISMATCH: (
            {"regions": region_area, "external": external_area},
            "The region areas (%.2f) do not add up to the "
            "external boundary (%.2f): at least one region did "
            "not close." % (region_area, external_area)),
        m.UNREADABLE: ({"error": exc}, f"Could not read the DXF file: {exc}"),
        m.EZDXF_MISSING: ({}, "The 'ezdxf' package is required to import "
                              "DXF files."),
        m.NO_LAYER_ASSIGNED: ({}, "No layer has been assigned a geometry "
                                  "type. Use the table to say what each "
                                  "layer represents."),
        "join": (
            {"first": {"code": "", "args": {}, "text": "a"},
             "second": {"code": "", "args": {}, "text": "b"}}, "a; b"),
    }


def _fields(template):
    return sorted(f for _t, f, _s, _c in string.Formatter().parse(template)
                  if f)


# ======================================================================
class TestTheCatalogue:

    def test_every_code_has_a_sample(self):
        from ogr_core.dxf.messages import MESSAGES
        assert sorted(set(MESSAGES) - set(_samples())) == []

    def test_the_english_is_the_sentence_written_before(self):
        from ogr_core.dxf.messages import text
        wrong = [(c, text(c, **a), old) for c, (a, old) in _samples().items()
                 if text(c, **a) != old]
        assert wrong == [], wrong

    def test_every_code_has_its_spanish_with_the_same_fields(self):
        from ogr_core.dxf.messages import MESSAGES
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        bad = []
        for code, spec in MESSAGES.items():
            words = "".join(t for t, _f, _s, _c
                            in string.Formatter().parse(spec.english))
            if not any(ch.isalpha() for ch in words):
                continue                 # "{first}; {second}"
            if spec.english not in es:
                bad.append(("no Spanish", code))
            elif _fields(es[spec.english]) != _fields(spec.english):
                bad.append(("fields", code))
        assert bad == [], bad

    def test_every_kind_the_panel_knows_has_a_code_and_a_title(self):
        from ogr_core.dxf.messages import MESSAGES, problem_code
        from ogr_gui.dialogs import dxf_problems_panel as panel
        from ogr_gui.i18n import _DICTS
        kinds = set(panel._PROBLEM_INFO) | {"area_mismatch"}
        assert kinds <= set(panel._TITLES), kinds - set(panel._TITLES)
        assert all(problem_code(k) in MESSAGES for k in kinds)
        missing = [t for t in panel._TITLES.values()
                   if t not in _DICTS["es"]]
        assert missing == [], missing


# ======================================================================
def _messy(folder: Path) -> Path:
    """An open external boundary, a second stray external, and a material
    line dangling in mid-air (``test_dxf_problems_v147``'s drawing)."""
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
    path = folder / "messy.dxf"
    doc.saveas(str(path))
    return path


def _unassigned(folder: Path) -> Path:
    doc = ezdxf.new("R2010", setup=True)
    doc.layers.add("SOMETHING_ELSE")
    doc.modelspace().add_line((0, 0), (10, 0),
                              dxfattribs={"layer": "SOMETHING_ELSE"})
    path = folder / "unassigned.dxf"
    doc.saveas(str(path))
    return path


def _preview(path):
    from ogr_core.dxf import ImportOptions, preview
    return preview(path, ImportOptions(unit="m", weld_pct=0.05))


def _coded(problem):
    from ogr_core.dxf.messages import MESSAGES, text
    assert problem["code"] in MESSAGES, problem
    assert text(problem["code"], **problem["args"]) == problem["message"]


@_requires(_HAS_EZDXF)
class TestTheImporterWritesItsCodes:

    def test_a_messy_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pv = _preview(_messy(Path(tmp)))
        kinds = {p["kind"] for p in pv.report.problems}
        assert {"external_gap", "external_multiple",
                "dangling_end"} <= kinds, kinds
        for p in pv.report.problems:
            _coded(p)
        multiple = next(p for p in pv.report.problems
                        if p["kind"] == "external_multiple")
        assert multiple["args"] == {"count": 2}

    def test_a_file_that_is_not_there(self):
        from ogr_core.dxf.messages import UNREADABLE, text
        with tempfile.TemporaryDirectory() as tmp:
            pv = _preview(Path(tmp) / "missing.dxf")
        assert pv.error_code == UNREADABLE
        assert pv.error == text(UNREADABLE, **pv.error_args)
        assert pv.error.startswith("Could not read the DXF file: ")

    def test_no_layer_assigned(self):
        from ogr_core.dxf.messages import NO_LAYER_ASSIGNED, text
        with tempfile.TemporaryDirectory() as tmp:
            pv = _preview(_unassigned(Path(tmp)))
        assert pv.error_code == NO_LAYER_ASSIGNED
        assert pv.error == text(NO_LAYER_ASSIGNED)

    def test_the_area_mismatch_is_written_by_the_core(self):
        from ogr_core.dxf.importer import area_mismatch_problem
        from ogr_core.dxf.messages import AREA_MISMATCH
        with tempfile.TemporaryDirectory() as tmp:
            pv = _preview(_messy(Path(tmp)))
        pv.external_area, pv.region_area = 1000.0, 800.0
        p = area_mismatch_problem(pv)
        assert p["code"] == AREA_MISMATCH and p["kind"] == "area_mismatch"
        _coded(p)
        pv.region_area = 1000.0
        assert area_mismatch_problem(pv) is None


# ======================================================================
def _core_trees():
    for path in sorted((ROOT / "ogr_core").rglob("*.py")):
        yield path.relative_to(ROOT).as_posix(), ast.parse(
            path.read_text(encoding="utf-8"))


class TestNoSiteWritesAProblemWithoutItsCode:

    def test_the_core_calls_only_the_coded_door(self):
        bad, coded = [], 0
        for rel, tree in _core_trees():
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)):
                    if node.func.attr == "add_problem":
                        bad.append((rel, node.lineno))
                    elif node.func.attr == "add_coded_problem":
                        coded += 1
        assert bad == [], bad
        assert coded >= 7, coded          # the census sees the sites

    def test_every_preview_error_has_its_code(self):
        """In ``preview``, each block that writes ``pv.error`` also writes
        ``pv.error_code``."""
        tree = ast.parse((ROOT / "ogr_core/dxf/importer.py").read_text(
            encoding="utf-8"))
        blocks = 0
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            names = [t.attr for st in body if isinstance(st, ast.Assign)
                     for t in st.targets if isinstance(t, ast.Attribute)]
            if "error" in names:
                blocks += 1
                assert "error_code" in names, (node.lineno, names)
        assert blocks >= 2, blocks


# ======================================================================
class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")
        return self

    def __exit__(self, *exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)
        return False


#: English words of these messages, matched as WORDS: "region" is a
#: substring of «región» and «regiones».
_ENGLISH = re.compile(r"\b(boundary|boundaries|external|layer|region|regions|"
                      r"could not|dangling|gap|were found|check the result)\b",
                      re.I)


def _english_in(texts):
    return [t for t in texts if _ENGLISH.search(t)]


@_requires(_HAS_EZDXF and _QT)
class TestTheInterfaceSaysThemInSpanish:

    def test_the_dialog_lists_them_in_spanish(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.dxf_import_dialog import DxfImportDialog
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp, _Spanish():
            d = DxfImportDialog(_messy(Path(tmp)))
            try:
                d._preview()
                items = [d.list_problems.item(i).text()
                         for i in range(d.list_problems.count())]
            finally:
                d.deleteLater()
        assert items and not any(t.startswith("[") for t in items), items
        assert _english_in(items) == [], items
        assert any(t.startswith("Varios contornos exteriores: Se han "
                                "encontrado 2 contornos exteriores")
                   for t in items), items

    def test_the_panel_shows_them_in_spanish(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.dxf_problems_panel import DxfProblemsPanel
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            pv = _preview(_messy(Path(tmp)))
        pv.external_area, pv.region_area = 1000.0, 800.0
        with _Spanish():
            panel = DxfProblemsPanel(pv, None, None)
            try:
                texts = []
                for i in range(panel.tree.topLevelItemCount()):
                    top = panel.tree.topLevelItem(i)
                    texts.append(top.text(0))
                    texts += [top.child(j).text(0)
                              for j in range(top.childCount())]
            finally:
                panel.deleteLater()
        assert texts and _english_in(texts) == [], texts
        assert texts[0].startswith("Error — Las áreas no cuadran"), texts[0]
        assert ("Las áreas de las regiones (800.00) no suman la del contorno "
                "exterior (1000.00): al menos una región no se cerró."
                in texts), texts

    def test_a_file_that_cannot_be_read(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.dxf_import_dialog import DxfImportDialog
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp, _Spanish():
            d = DxfImportDialog(Path(tmp) / "missing.dxf")
            try:
                # what the dialog says as it opens (it reads the layers), and
                # after Preview: two doors, the first of which the screen
                # census of 0.1.321 is what sees
                on_open = d.lbl_preview.text()
                d._preview()
                said = d.lbl_preview.text()
            finally:
                d.deleteLater()
        for text in (on_open, said):
            assert text.startswith("No se pudo leer el archivo DXF: "), text

    def test_the_screen_test_has_no_exception_for_it(self):
        import test_labels_spanish_v1321 as screen
        assert not any("DXF" in pattern
                       for pattern in screen.SHOWN_EXCEPTIONS)
