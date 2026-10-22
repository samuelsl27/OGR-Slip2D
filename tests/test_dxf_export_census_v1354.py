# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.354 (D335, eighth part) — what the DXF export says carries stable
codes and the window says it in Spanish; the API's census of rejected
surfaces groups them as the window does; and the critical probabilistic
surface's Spanish names the searches by their names.

The export's summary ("4 entities — OGR_EXTERNAL: 1, …"), its error and what
it skipped (the mesh, a surface the engine cannot draw, an image it cannot
read) were English f-strings, and the status bar showed them inside a
translated frame. Each is a code now (``ogr_core.dxf.messages
.EXPORT_MESSAGES``, apart from the import's table, which the test of
v0.1.334 holds to its 0.1.333 samples).

``interpretation.invalid_summary`` grouped by the whole sentence
(``by_reason``), values and all, so one condition found at several values
was several groups -- what the window did before D314. ``by_group`` keys on
the code with the varying values left out ("…"). The plan called it
``by_code``; that key already holds the reference's error codes (-112,
-101), so it keeps them.

The invariants:

* **the English is v0.1.353's, byte for byte** (``_V1353``: that version's
  expressions and its ``ExportReport``, run on the inputs below);
* every code says itself in Spanish with its fields;
* **no sentence of the export is built without its code** (AST census; the
  label drawn in the file and the programmer's TypeError are not messages);
* **a real export**, said in Spanish: its summary and a surface it skipped;
  the window's status bar reads the codes;
* ``by_group`` is one group for one condition, ``by_reason`` and
  ``by_code`` are as they were;
* the critical probabilistic surface's Spanish names the four searches as
  the Surface Options do.
"""
from __future__ import annotations

import ast
import os
import re
import string
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{cat, code, args, english}``: the sentence v0.1.353 wrote; a nested
#: value is ``{"$code", "$cat", "$args"}``.
_V1353 = [{'cat': 'export',
  'code': 'dxf.export.summary',
  'english': '4 entities — OGR_EXTERNAL: 1, OGR_MATERIAL: 3',
  'args': {'total': 4,
           'layers': [{'$code': 'dxf.export.layer',
                       '$cat': 'export',
                       '$args': {'layer': 'OGR_EXTERNAL', 'n': 1}},
                      {'$code': 'dxf.export.layer',
                       '$cat': 'export',
                       '$args': {'layer': 'OGR_MATERIAL', 'n': 3}}]}},
 {'cat': 'export',
  'code': 'dxf.export.layer',
  'english': 'OGR_EXTERNAL: 1',
  'args': {'layer': 'OGR_EXTERNAL', 'n': 1}},
 {'cat': 'export',
  'code': 'dxf.export.failed',
  'english': 'failed',
  'args': {}},
 {'cat': 'export',
  'code': 'dxf.export.ezdxf_missing',
  'english': "The 'ezdxf' package is required to export DXF files.",
  'args': {}},
 {'cat': 'export',
  'code': 'dxf.export.write_failed',
  'english': 'Could not write the DXF file: disk full',
  'args': {'error': 'disk full'}},
 {'cat': 'export',
  'code': 'dxf.export.skipped_mesh',
  'english': 'mesh (too big)',
  'args': {'error': 'too big'}},
 {'cat': 'export',
  'code': 'dxf.export.skipped_surface',
  'english': 'bishop_simplified critical surface (CompositeSurface)',
  'args': {'method_id': 'bishop_simplified', 'kind': 'CompositeSurface'}},
 {'cat': 'export',
  'code': 'dxf.export.skipped_surface',
  'english': 'spencer critical surface (unknown)',
  'args': {'method_id': 'spencer', 'kind': 'unknown'}},
 {'cat': 'export',
  'code': 'dxf.export.skipped_picture',
  'english': 'image logo.png (file not found or not readable): drawn as its '
             'frame',
  'args': {'path': 'logo.png'}},
 {'cat': 'export',
  'code': 'dxf.export.skipped_picture',
  'english': 'image (none) (file not found or not readable): drawn as its '
             'frame',
  'args': {'path': '(none)'}}]


def _cat(_name="export"):
    from ogr_core.dxf.messages import EXPORT_MESSAGES
    return EXPORT_MESSAGES


def _resolve(v):
    from ogr_core.messages import as_nested, coded
    if isinstance(v, dict) and "$code" in v:
        return as_nested(coded(_cat(), v["$code"], **_resolve(v["$args"])))
    if isinstance(v, list):
        return [_resolve(x) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x) for k, x in v.items()}
    return v


def _message(case):
    from ogr_core.messages import coded
    return coded(_cat(), case["code"], **_resolve(case["args"]))


_F = string.Formatter()


def _fields(t):
    return sorted({f for _t, f, _s, _c in _F.parse(t) if f})


def _wordless(t):
    return not any(ch.isalpha() for lit, _f, _s, _c in _F.parse(t)
                   for ch in lit)


_UNFILLED = re.compile(r"\{[a-z_]+(?:[:!][^}]*)?\}")


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_code_with_its_sample(self):
        for case in _V1353:
            assert _message(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code(self):
        assert {c["code"] for c in _V1353} == set(_cat())

    def test_the_import_table_is_untouched(self):
        from ogr_core.dxf.messages import EXPORT_MESSAGES, MESSAGES
        assert not set(EXPORT_MESSAGES) & set(MESSAGES)
        from ogr_gui.core_messages import _catalogue
        assert set(EXPORT_MESSAGES) <= set(_catalogue())


class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for code, spec in _cat().items():
            if _wordless(spec.english):
                continue
            assert spec.english in es, (code, spec.english[:60])
            assert _fields(es[spec.english]) == _fields(spec.english), code
            assert es[spec.english] != spec.english, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_text
        with _Spanish():
            for case in _V1353:
                said = note_text(_message(case))
                if not _wordless(_cat()[case["code"]].english):
                    assert said != case["english"], case["code"]
                assert not _UNFILLED.search(said), (case["code"], said)


# ======================================================================
_CODED = {
    "ogr_core/dxf/exporter.py": ("ExportReport.summary", "export_dxf"),
    "ogr_core/dxf/annotation_export.py": ("AnnotationWriter._picture",),
}
#: What the export writes INTO the drawing (a label beside each surface) and
#: the TypeError a caller of the old signature gets: not messages to a user.
_NOT_MESSAGES = ("{mid}  FS = {fos:.4f}", "export_dxf takes the critical")


def _function(tree, name):
    if "." in name:
        cls, meth = name.split(".")
        owners = [n for n in tree.body
                  if isinstance(n, ast.ClassDef) and n.name == cls]
        assert len(owners) == 1, name
        found = [n for n in owners[0].body
                 if isinstance(n, ast.FunctionDef) and n.name == meth]
    else:
        found = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(found) == 1, name
    return found[0]


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for name in names:
                fn = _function(tree, name)
                # every docstring in it, a nested function's too
                docs = {d.body[0].value for d in ast.walk(fn)
                        if isinstance(d, (ast.FunctionDef, ast.ClassDef))
                        and d.body and isinstance(d.body[0], ast.Expr)
                        and isinstance(d.body[0].value, ast.Constant)}
                # a format spec (".4f") is an f-string of its own in the
                # tree: it belongs to the f-string it formats
                specs = {v.format_spec for v in ast.walk(fn)
                         if isinstance(v, ast.FormattedValue)
                         and v.format_spec is not None}
                for n in ast.walk(fn):
                    if n in docs or n in specs:
                        continue
                    seg = ast.get_source_segment(src, n) or ""
                    if any(k in seg for k in _NOT_MESSAGES):
                        continue
                    if isinstance(n, ast.JoinedStr):
                        found.append((rel, name, n.lineno, "f-string"))
                    elif (isinstance(n, ast.BinOp)
                          and isinstance(n.op, ast.Mod)
                          and isinstance(n.left, ast.Constant)
                          and isinstance(n.left.value, str)):
                        found.append((rel, name, n.lineno, "% format"))
                    elif (isinstance(n, ast.Constant)
                          and isinstance(n.value, str)
                          and len(n.value) > 40 and " " in n.value):
                        found.append((rel, name, n.lineno, "sentence"))
        assert not found, found

    def test_the_window_reads_the_codes(self):
        src = (_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8")
        flat = " ".join(src.split())
        assert 'tr("Exported to %s | %s") % (path, note_text(rep.summary()))' \
            in flat
        assert "note_text(s) for s in sorted(set(rep.skipped))" in flat


# ======================================================================
def _model():
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Export")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 3.0,
                                                   "friction_angle": 19.6}}}]})
        return ws.get(pid).project
    finally:
        ws.shutdown()


class TestARealExportInSpanish:

    def test_its_summary_and_a_skipped_surface(self):
        from ogr_core.dxf.exporter import export_dxf
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        p = _model()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.dxf")
            rep = export_dxf(p, path, None,
                             [("spencer", None, 1.2, "CompositeSurface")])
        assert rep.ok, rep.error
        assert rep.summary().code == "dxf.export.summary"
        with _Spanish():
            summary = note_text(rep.summary())
            skipped = [note_text(s) for s in rep.skipped]
            name = method_name("spencer")
        assert re.match(r"\d+ entidades — ", summary), summary
        assert skipped == ["superficie crítica de %s (CompositeSurface)"
                           % name], skipped


# ======================================================================
def _rejected(value, at):
    from types import SimpleNamespace as NS

    from ogr_core.messages import coded
    from ogr_slip2d.messages import M_ALPHA_COLLAPSED, MESSAGES
    msg = coded(MESSAGES, M_ALPHA_COLLAPSED, value=value, slice=at)
    return NS(is_valid=False, admissible=True, error_message=msg,
              message_code=msg.code, message_args=msg.args,
              admissibility_reason="", admissibility_note="",
              converged=False)


class TestTheCensusGroupsLikeTheWindow:

    def test_one_condition_is_one_group(self):
        from types import SimpleNamespace as NS

        from ogr_slip2d.interpretation import invalid_summary
        sr = NS(evaluations=[_rejected(0.0123, 3), _rejected(0.0456, 7),
                             _rejected(0.0123, 3)],
                total_count=3, analysed_count=0)
        census = invalid_summary(sr)
        assert census["by_reason"] == {
            "mα collapsed to 0.0123 at slice 3": 2,
            "mα collapsed to 0.0456 at slice 7": 1}, census["by_reason"]
        assert census["by_group"] == {"mα collapsed to … at slice …": 3}
        assert sum(census["by_code"].values()) == 3

    def test_a_count_without_an_evaluation_is_its_own_group(self):
        from types import SimpleNamespace as NS

        from ogr_slip2d.interpretation import invalid_summary
        sr = NS(evaluations=[], total_count=2, analysed_count=0,
                misses_ground=2)
        census = invalid_summary(sr)
        why = "the circle does not cut the ground surface twice"
        assert census["by_group"] == {why: 2} == census["by_reason"]


class TestTheSearchesByTheirNames:

    def test_the_critical_probabilistic_surface(self):
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.probabilistic import _CPS_STEERED
        es = _DICTS["es"]
        said = es[_CPS_STEERED]
        for search in ("Grid Search", "Slope Search", "Path Search",
                       "Block Search"):
            name = es[search].replace("Búsqueda ", "")
            assert name in said, (name, said)
        assert "Grid" not in said, said
