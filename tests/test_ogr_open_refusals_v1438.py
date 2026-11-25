# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.438 (D422) -- what the agent receives for a ``.ogr`` it cannot read,
and the files of another shape that opened without a word.

Invariants protected here:

* **Every valid file opens the same.** The shape ``Project.from_dict`` now
  checks (``ogr_core.project.file_shape``) is an identity with what the
  program writes and reads: the table has a shape for every key
  ``to_dict()`` writes (a model with every section) and accepts the shape it
  wrote; its keys are the keys the readers read (``Project.from_dict`` and
  ``ProjectSettings.from_dict``, by AST); a file read back after it was
  saved gives the same ``document_hash``; a null the reader always took
  still opens -- only a null: the ``""``, ``0`` and ``false`` the same
  idioms swallowed are a section of another shape, and refused (the owner's
  decision in the review of 0.1.438); and a file with a BOM reads as the
  same file without one.
  (On the 248 source ``.ogr`` of the bank the readers of 0.1.437 and of this
  version give the same ``document_hash`` for every file: measured with
  ``_auditoria/P10_herramientas/medir0_d422.py``, not here.)
* **No case leaves ``ogr_api.call`` loose.** Each of the files of
  :data:`CASES` -- the bank's ``medir_d422.py``, and twelve more -- either
  opens or raises an ``OgrApiError``: none an ``AttributeError``, an
  ``IndexError``, an ``OverflowError``, a ``RecursionError`` or a
  ``PermissionError``, also when what is broken lies inside an item, where
  the shape is not checked (the owner's decisions in the review of
  0.1.438). ``project_open`` and ``properties_import`` say the
  same (one reader). The texts that do not move are 0.1.437's, from
  ``_V1437``, measured by running :func:`_capture` on a ``git archive`` of
  that tree (``_auditoria/P10_herramientas/capture_d422.py``); the ones that
  move are the sentences decided for this version, written here.
* **The MCP server says one thing with a window and without one**, an
  unexpected exception as ``[E_INTERNAL]`` with its type and its text too.
* **Each code says it in Spanish**, and the window does, by Open.

One main window and one MCP server for the whole file.

v0.1.473 (spec 010) -- the core's sources are read in the tree of the
``ogr_core`` that is imported (``tests/_sources.py``), which fails
rather than find nothing: the core left this repository for OGR-Core.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import json
import os
import string
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import _sources as S  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except Exception:  # pragma: no cover
    _HAS_QT = False


def _requires_qt(obj):
    """A class (or a method) that needs Qt; without it, nothing to run."""
    if _HAS_QT:
        return obj
    return type(obj.__name__, (), {}) if isinstance(obj, type) else None


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI "
                                 "(pip install -e .[mcp])")
        return False
    return True


class _Language:
    """The interface in ``code`` for the block, and back after it (rule 5)."""

    def __init__(self, code):
        self.code = code

    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language(self.code)

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
# 0.1.437's answers, measured on its tree (see the module docstring)
# ======================================================================
_V1437 = {'project_open anidado': ['RecursionError',
                          'Stack overflow (used 2912 kB) while decoding a '
                          'JSON array from a unicode string'],
 'project_open boundaries_str': ['InvalidArgument',
                                 '[E_INVALID_ARGUMENT] '
                                 '<tmp>/boundaries_str.ogr is not a readable '
                                 '.ogr file: TypeError: string indices must '
                                 "be integers, not 'str'"],
 'project_open busqueda_lista': ['OPENS', 'Demo slope'],
 'project_open carpeta': ['PermissionError',
                          "[Errno 13] Permission denied: '<tmp>/carpeta.ogr'"],
 'project_open con_bom': ['InvalidArgument',
                          '[E_INVALID_ARGUMENT] <tmp>/con_bom.ogr is not a '
                          'readable .ogr file: JSONDecodeError: Unexpected '
                          'UTF-8 BOM (decode using utf-8-sig): line 1 column '
                          '1 (char 0)'],
 'project_open contorno_tipo': ['InvalidArgument',
                                '[E_INVALID_ARGUMENT] <tmp>/contorno_tipo.ogr '
                                'is not a readable .ogr file: KeyError: '
                                "'FUTURE'"],
 'project_open distribucion_null': ['AttributeError',
                                    "'NoneType' object has no attribute "
                                    "'get'"],
 'project_open foco_elemento': ['AttributeError',
                                "'list' object has no attribute 'get'"],
 'project_open foco_falso': ['OPENS', 'Demo slope'],
 'project_open geojson': ['OPENS', 'Untitled'],
 'project_open huella_corta': ['IndexError', 'list index out of range'],
 'project_open json_roto': ['InvalidArgument',
                            '[E_INVALID_ARGUMENT] <tmp>/json_roto.ogr is not '
                            'a readable .ogr file: JSONDecodeError: '
                            'Unterminated string starting at: line 1 column '
                            '30 (char 29)'],
 'project_open material_null': ['InvalidArgument',
                                '[E_INVALID_ARGUMENT] <tmp>/material_null.ogr '
                                'is not a readable .ogr file: TypeError: '
                                "'NoneType' object is not subscriptable"],
 'project_open material_null_2': ['InvalidArgument',
                                  '[E_INVALID_ARGUMENT] '
                                  '<tmp>/material_null_2.ogr is not a '
                                  "readable .ogr file: TypeError: 'NoneType' "
                                  'object is not subscriptable'],
 'project_open material_sin_nombre': ['InvalidArgument',
                                      '[E_INVALID_ARGUMENT] '
                                      '<tmp>/material_sin_nombre.ogr is not a '
                                      "readable .ogr file: KeyError: 'name'"],
 'project_open materials_obj': ['OPENS', 'Demo slope'],
 'project_open materials_texto': ['OPENS', 'Demo slope'],
 'project_open metodos_lista': ['InvalidArgument',
                                '[E_INVALID_ARGUMENT] <tmp>/metodos_lista.ogr '
                                'is not a readable .ogr file: TypeError: '
                                'ogr_core.project.settings.MethodsSettings() '
                                'argument after ** must be a mapping, not '
                                'list'],
 'project_open no_utf8': ['InvalidArgument',
                          '[E_INVALID_ARGUMENT] <tmp>/no_utf8.ogr is not a '
                          "readable .ogr file: UnicodeDecodeError: 'utf-8' "
                          "codec can't decode byte 0xf1 in position 12: "
                          'invalid continuation byte'],
 'project_open peso_cadena': ['OPENS', 'Demo slope'],
 'project_open raiz_bool': ['AttributeError',
                            "'bool' object has no attribute 'get'"],
 'project_open raiz_cadena': ['AttributeError',
                              "'str' object has no attribute 'get'"],
 'project_open raiz_lista': ['AttributeError',
                             "'list' object has no attribute 'get'"],
 'project_open raiz_null': ['AttributeError',
                            "'NoneType' object has no attribute 'get'"],
 'project_open raiz_numero': ['AttributeError',
                              "'int' object has no attribute 'get'"],
 'project_open rejilla_cero': ['OPENS', 'Demo slope'],
 'project_open seismic_lista': ['AttributeError',
                                "'list' object has no attribute 'get'"],
 'project_open settings_lista': ['AttributeError',
                                 "'list' object has no attribute 'get'"],
 'project_open vacio': ['OPENS', 'Untitled'],
 'project_open variable_elemento': ['AttributeError',
                                    "'str' object has no attribute 'get'"],
 'project_open vertice_str': ['InvalidArgument',
                              '[E_INVALID_ARGUMENT] <tmp>/vertice_str.ogr is '
                              'not a readable .ogr file: ValueError: too many '
                              'values to unpack (expected 2)'],
 'project_open z_orden_infinito': ['OverflowError',
                                   'cannot convert float infinity to integer'],
 'properties_import anidado': ['RecursionError',
                               'Stack overflow (used 2912 kB) while decoding '
                               'a JSON array from a unicode string'],
 'properties_import boundaries_str': ['InvalidArgument',
                                      '[E_INVALID_ARGUMENT] '
                                      '<tmp>/boundaries_str.ogr is not a '
                                      'readable .ogr file: string indices '
                                      "must be integers, not 'str'"],
 'properties_import busqueda_lista': ['OPENS', '[["Silty clay (2)"], []]'],
 'properties_import carpeta': ['PermissionError',
                               '[Errno 13] Permission denied: '
                               "'<tmp>/carpeta.ogr'"],
 'properties_import con_bom': ['InvalidArgument',
                               '[E_INVALID_ARGUMENT] <tmp>/con_bom.ogr is not '
                               'a readable .ogr file: Unexpected UTF-8 BOM '
                               '(decode using utf-8-sig): line 1 column 1 '
                               '(char 0)'],
 'properties_import contorno_tipo': ['InvalidArgument',
                                     '[E_INVALID_ARGUMENT] '
                                     '<tmp>/contorno_tipo.ogr is not a '
                                     "readable .ogr file: 'FUTURE'"],
 'properties_import distribucion_null': ['AttributeError',
                                         "'NoneType' object has no attribute "
                                         "'get'"],
 'properties_import foco_elemento': ['AttributeError',
                                     "'list' object has no attribute 'get'"],
 'properties_import foco_falso': ['OPENS', '[["Silty clay (2)"], []]'],
 'properties_import geojson': ['OPENS', '[[], []]'],
 'properties_import huella_corta': ['IndexError', 'list index out of range'],
 'properties_import json_roto': ['InvalidArgument',
                                 '[E_INVALID_ARGUMENT] <tmp>/json_roto.ogr is '
                                 'not a readable .ogr file: Unterminated '
                                 'string starting at: line 1 column 30 (char '
                                 '29)'],
 'properties_import material_null': ['InvalidArgument',
                                     '[E_INVALID_ARGUMENT] '
                                     '<tmp>/material_null.ogr is not a '
                                     "readable .ogr file: 'NoneType' object "
                                     'is not subscriptable'],
 'properties_import material_null_2': ['InvalidArgument',
                                       '[E_INVALID_ARGUMENT] '
                                       '<tmp>/material_null_2.ogr is not a '
                                       "readable .ogr file: 'NoneType' object "
                                       'is not subscriptable'],
 'properties_import material_sin_nombre': ['InvalidArgument',
                                           '[E_INVALID_ARGUMENT] '
                                           '<tmp>/material_sin_nombre.ogr is '
                                           "not a readable .ogr file: 'name'"],
 'properties_import materials_obj': ['OPENS', '[[], []]'],
 'properties_import materials_texto': ['OPENS', '[[], []]'],
 'properties_import metodos_lista': ['InvalidArgument',
                                     '[E_INVALID_ARGUMENT] '
                                     '<tmp>/metodos_lista.ogr is not a '
                                     'readable .ogr file: '
                                     'ogr_core.project.settings.MethodsSettings() '
                                     'argument after ** must be a mapping, '
                                     'not list'],
 'properties_import no_utf8': ['InvalidArgument',
                               '[E_INVALID_ARGUMENT] <tmp>/no_utf8.ogr is not '
                               "a readable .ogr file: 'utf-8' codec can't "
                               'decode byte 0xf1 in position 12: invalid '
                               'continuation byte'],
 'properties_import peso_cadena': ['OPENS', '[["Silty clay (2)"], []]'],
 'properties_import raiz_bool': ['AttributeError',
                                 "'bool' object has no attribute 'get'"],
 'properties_import raiz_cadena': ['AttributeError',
                                   "'str' object has no attribute 'get'"],
 'properties_import raiz_lista': ['AttributeError',
                                  "'list' object has no attribute 'get'"],
 'properties_import raiz_null': ['AttributeError',
                                 "'NoneType' object has no attribute 'get'"],
 'properties_import raiz_numero': ['AttributeError',
                                   "'int' object has no attribute 'get'"],
 'properties_import rejilla_cero': ['OPENS', '[["Silty clay (2)"], []]'],
 'properties_import seismic_lista': ['AttributeError',
                                     "'list' object has no attribute 'get'"],
 'properties_import settings_lista': ['AttributeError',
                                      "'list' object has no attribute 'get'"],
 'properties_import vacio': ['OPENS', '[[], []]'],
 'properties_import variable_elemento': ['AttributeError',
                                         "'str' object has no attribute "
                                         "'get'"],
 'properties_import vertice_str': ['InvalidArgument',
                                   '[E_INVALID_ARGUMENT] '
                                   '<tmp>/vertice_str.ogr is not a readable '
                                   '.ogr file: too many values to unpack '
                                   '(expected 2)'],
 'properties_import z_orden_infinito': ['OverflowError',
                                        'cannot convert float infinity to '
                                        'integer']}

_TMP = tempfile.mkdtemp(prefix="ogr_d422_")


def _scrub(text):
    """The temporary folder as ``<tmp>/``, also inside a repr (an
    ``OSError``'s), whatever the system's separator."""
    text = str(text)
    esc = _TMP.replace("\\", "\\\\")
    for form, sep in ((esc, os.sep.replace("\\", "\\\\")), (_TMP, os.sep)):
        text = text.replace(form + sep, "<tmp>/").replace(form, "<tmp>")
    return text


_BASE: dict = {}


def _base():
    """The demo, as its file holds it."""
    if not _BASE:
        from ogr_core.project.demo import build_demo_project
        _BASE.update(json.loads(json.dumps(build_demo_project().to_dict())))
    return copy.deepcopy(_BASE)


def _put(path, value):
    def edit(d):
        t = d
        for k in path[:-1]:
            t = t[k]
        t[path[-1]] = value
        return d
    return edit


def _drop(path):
    def edit(d):
        t = d
        for k in path[:-1]:
            t = t[k]
        t.pop(path[-1])
        return d
    return edit


def _root(value):
    return lambda d: value


def _vertex_as_text(d):
    d["boundaries"][0]["polyline"]["vertices"][0] = "0,0"
    return d


def _variable_without_distribution(d):
    """A random variable of the demo whose distribution is null: inside an
    item, where the shape is not checked (an ``AttributeError``)."""
    from ogr_core.project.demo import build_demo_project
    from ogr_core.statistics import available_variables
    rv = next(v for v in available_variables(build_demo_project())
              if v.param == "cohesion").to_dict()
    rv["distribution"] = None
    d["random_variables"] = [rv]
    return d


def _short_footprint(d):
    """A region assignment whose footprint has a vertex of one coordinate
    (an ``IndexError``)."""
    d["region_assignments"] = [{"footprint": [[0.0]],
                                "material_id": d["materials"][0]["id"]}]
    return d


def _second_material_null(d):
    """A bad item that is not the first one."""
    d["materials"] = [d["materials"][0], None]
    return d


def _infinite_z_order(d):
    """An annotation whose ``z_order`` is ``1e999``: ``int(inf)`` is an
    ``OverflowError`` (json writes and reads it as ``Infinity``)."""
    from ogr_core.annotations.annotation import Annotation, AnnotationKind
    a = Annotation(kind=AnnotationKind.LINE,
                   points=[(0.0, 0.0), (5.0, 5.0)]).to_dict()
    a["z_order"] = float("inf")
    d["annotations"] = [a]
    return d


#: (key, how): a function of the demo's dict, or how the bytes are written.
#: The bank's ``medir_d422.py`` and twelve more: a root ``true``, two
#: subsections of the settings (``search`` opened with its defaults), two
#: things broken inside an item, which the census of D414 still found loose
#: on this version, and, from the review of 0.1.438, what the reader
#: swallowed as empty (``""``, ``false``, ``0``), an object with none of the
#: keys of a project, a bad item that is not the first, and two errors of
#: Python's own (an ``OverflowError`` and a ``RecursionError``).
CASES = (
    ("raiz_lista", _root([])),
    ("raiz_numero", _root(42)),
    ("raiz_cadena", _root("x")),
    ("raiz_null", _root(None)),
    ("raiz_bool", _root(True)),
    ("materials_obj", _put(["materials"], {})),
    ("boundaries_str", _put(["boundaries"], "x")),
    ("vertice_str", _vertex_as_text),
    ("json_roto", "json_roto"),
    ("no_utf8", "no_utf8"),
    ("settings_lista", _put(["settings"], [])),
    ("seismic_lista", _put(["seismic"], [])),
    ("metodos_lista", _put(["settings", "methods"], [])),
    ("busqueda_lista", _put(["settings", "search"], [])),
    ("material_sin_nombre", _drop(["materials", 0, "name"])),
    ("contorno_tipo", _put(["boundaries", 0, "type"], "FUTURE")),
    ("material_null", _put(["materials"], [None])),
    ("foco_elemento", _put(["focus_objects"], [[1]])),
    ("variable_elemento", _put(["random_variables"], ["x"])),
    ("peso_cadena", _put(["materials", 0, "unit_weight"], "x")),
    ("con_bom", "con_bom"),
    ("vacio", _root({})),
    ("carpeta", "carpeta"),
    # the review of 0.1.438: what is broken inside an item
    ("distribucion_null", _variable_without_distribution),
    ("huella_corta", _short_footprint),
    # the review of 0.1.438
    ("materials_texto", _put(["materials"], "")),
    ("foco_falso", _put(["focus_objects"], False)),
    ("rejilla_cero", _put(["water_pressure_grid"], 0)),
    ("geojson", _root({"type": "FeatureCollection", "features": []})),
    ("material_null_2", _second_material_null),
    ("z_orden_infinito", _infinite_z_order),
    ("anidado", "anidado"),
)

_PATHS: dict = {}


def _path(key):
    """The file of case ``key``, written once. A broken JSON and a latin-1
    one from fixed bytes, so their texts do not hang on the demo."""
    if key in _PATHS:
        return _PATHS[key]
    how = dict(CASES)[key]
    p = os.path.join(_TMP, key + ".ogr")
    if how == "json_roto":
        with open(p, "wb") as fh:
            fh.write(b'{"name": "x", "materials": [{"na')
    elif how == "no_utf8":
        with open(p, "wb") as fh:
            fh.write('{"name": "Peñarroya"}'.encode("latin-1"))
    elif how == "con_bom":
        with open(p, "wb") as fh:
            fh.write(b"\xef\xbb\xbf" + json.dumps(_base()).encode("utf-8"))
    elif how == "carpeta":
        os.mkdir(p)
    elif how == "anidado":
        # deeper than any decoder takes: a RecursionError of json itself
        with open(p, "wb") as fh:
            fh.write(b'{"name": "x", "settings": ' + b"[" * 100000
                     + b"]" * 100000 + b"}")
    else:
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(how(_base()), fh)
    _PATHS[key] = p
    return p


_CAPTURED: dict = {}


def _capture() -> dict:
    """What :data:`_V1437` recorded, measured on this tree: for each case,
    what ``project_open`` and ``properties_import`` give through
    ``ogr_api.call`` -- the exception's type and text, or what opened."""
    if _CAPTURED:
        return _CAPTURED
    from ogr_api import Workspace, call
    out = {}
    ws = Workspace()
    try:
        for key, _how in CASES:
            p = _path(key)
            # a destination of its own: what one case imports does not number
            # the names of the next
            target = call(ws, "project_new", template="demo")["project_id"]
            for op, kw in (("project_open", {"path": p}),
                           ("properties_import", {"project_id": target,
                                                  "path": p})):
                name = "%s %s" % (op, key)
                try:
                    got = call(ws, op, **kw)
                except Exception as exc:  # noqa: BLE001
                    out[name] = [type(exc).__name__, _scrub(exc)]
                    continue
                if op == "project_open":
                    out[name] = ["OPENS", got["summary"]["name"]]
                    call(ws, "project_close", project_id=got["project_id"],
                         discard_changes=True)
                else:
                    out[name] = ["OPENS", json.dumps(
                        [got["materials"], got["support_types"]])]
    finally:
        ws.shutdown()
    _CAPTURED.update(out)
    return _CAPTURED


# ======================================================================
#: The cases whose answer does not move, and the ones that do, with the
#: sentence each says now (the owner's decision: a section of another type
#: gets the new sentence also where 0.1.437 already wrapped Python's).
_UNCHANGED = ("vertice_str", "json_roto", "no_utf8", "material_sin_nombre",
              "contorno_tipo")
#: v0.1.492 (D429, ogr-core 0.2.11): a unit weight "x" is refused at
#: opening, with this sentence; up to 0.2.10 it opened, and failed when
#: computed
_PESO_CADENA = ("The field 'unit_weight' of item 1 of the section "
                "'materials' of the file must be a number, not a string.")
_ROOT_IS = "The file does not hold a project: it is %s, not an object."
_SECTION = "The section '%s' of the file must be %s, not %s."
_ITEM = "Item 1 of the section '%s' of the file must be an object, not %s."
_NOW = {
    "raiz_lista": _ROOT_IS % "a list",
    "raiz_numero": _ROOT_IS % "a number",
    "raiz_cadena": _ROOT_IS % "a string",
    "raiz_null": _ROOT_IS % "null",
    "raiz_bool": _ROOT_IS % "a boolean",
    "vacio": "The file does not hold a project: it has none of the keys of "
             "one.",
    "materials_obj": _SECTION % ("materials", "a list", "an object"),
    "boundaries_str": _SECTION % ("boundaries", "a list", "a string"),
    "settings_lista": _SECTION % ("settings", "an object", "a list"),
    "seismic_lista": _SECTION % ("seismic", "an object", "a list"),
    "metodos_lista": _SECTION % ("settings.methods", "an object", "a list"),
    "busqueda_lista": _SECTION % ("settings.search", "an object or null",
                                  "a list"),
    "material_null": _ITEM % ("materials", "null"),
    "foco_elemento": _ITEM % ("focus_objects", "a list"),
    "variable_elemento": _ITEM % ("random_variables", "a string"),
    # the review of 0.1.438: what the reader swallowed as empty is a section
    # of another shape too, and an object with none of the keys is no
    # project (the owner's decision)
    "materials_texto": _SECTION % ("materials", "a list", "a string"),
    "foco_falso": _SECTION % ("focus_objects", "a list or null",
                              "a boolean"),
    "rejilla_cero": _SECTION % ("water_pressure_grid", "an object or null",
                                "a number"),
    "geojson": "The file does not hold a project: it has none of the keys "
               "of one.",
    "material_null_2": "Item 2 of the section 'materials' of the file must "
                       "be an object, not null.",
}
#: what the window says of each, in Spanish
_NOW_ES = {
    "raiz_lista": "El archivo no contiene un proyecto: es una lista, no un "
                  "objeto.",
    "raiz_null": "El archivo no contiene un proyecto: es null, no un objeto.",
    "raiz_bool": "El archivo no contiene un proyecto: es un valor lógico, no "
                 "un objeto.",
    "vacio": "El archivo no contiene un proyecto: no tiene ninguna de las "
             "claves de un proyecto.",
    "foco_falso": "La sección «focus_objects» del archivo tiene que ser una "
                  "lista o null, no un valor lógico.",
    "material_null_2": "El elemento 2 de la sección «materials» del archivo "
                       "tiene que ser un objeto, no null.",
    "materials_obj": "La sección «materials» del archivo tiene que ser una "
                     "lista, no un objeto.",
    "busqueda_lista": "La sección «settings.search» del archivo tiene que "
                      "ser un objeto o null, no una lista.",
    "material_null": "El elemento 1 de la sección «materials» del archivo "
                     "tiene que ser un objeto, no null.",
    "variable_elemento": "El elemento 1 de la sección «random_variables» del "
                         "archivo tiene que ser un objeto, no un texto.",
    "foco_elemento": "El elemento 1 de la sección «focus_objects» del "
                     "archivo tiene que ser un objeto, no una lista.",
}


#: what is broken inside an item: Python's own words, now wrapped with the
#: exception's type (the owner's decision in the review of 0.1.438)
_INSIDE = {
    "distribucion_null": "AttributeError: 'NoneType' object has no "
                         "attribute 'get'",
    "huella_corta": "IndexError: list index out of range",
    "z_orden_infinito": "OverflowError: cannot convert float infinity to "
                        "integer",
    # its text is the decoder's and changes with Python's version: the
    # type is what is checked
    "anidado": "RecursionError: ",
}


def _agent_text(key):
    """The refusal ``project_open`` and ``properties_import`` give now."""
    p = "<tmp>/%s.ogr" % key
    if key == "carpeta":
        return "[E_INVALID_ARGUMENT] %s is not a file." % p
    if key in _INSIDE:
        return ("[E_INVALID_ARGUMENT] %s is not a readable .ogr file: %s"
                % (p, _INSIDE[key]))
    return ("[E_INVALID_ARGUMENT] %s is not a readable .ogr file: "
            "ValueError: %s" % (p, _NOW[key]))


class TestTheAgentReadsARefusal:

    def test_no_case_leaves_call_loose(self):
        now = _capture()
        loose = {k: v for k, v in now.items()
                 if v[0] not in ("InvalidArgument", "OPENS")}
        assert loose == {}, loose
        opens = sorted(k.split(" ", 1)[1] for k, v in now.items()
                       if v[0] == "OPENS" and k.startswith("project_open"))
        # a BOM is read; a value of another type inside an item is refused
        # since D429 (ogr-core 0.2.11)
        assert opens == ["con_bom"], opens
        for op in ("project_open", "properties_import"):
            kind, text = now[op + " peso_cadena"]
            assert kind == "InvalidArgument", (op, kind)
            assert text.endswith("ValueError: " + _PESO_CADENA), text
        # every case the test names is one of the CASES
        named = {*_NOW, *_INSIDE, "carpeta", *_UNCHANGED, "peso_cadena",
                 "con_bom"}
        assert named == {k for k, _h in CASES}, named ^ {k for k, _h in CASES}

    def test_the_two_operations_say_the_same(self):
        now = _capture()
        for key, _how in CASES:
            a, b = now["project_open " + key], now["properties_import " + key]
            if a[0] == "OPENS":
                assert b[0] == "OPENS", (key, b)
            else:
                assert a == b, (key, a, b)

    def test_what_does_not_move_is_0437(self):
        now = _capture()
        assert sorted(_V1437) == sorted(now), sorted(set(_V1437) ^ set(now))
        assert len(_V1437) == 2 * len(CASES) == 64
        for key in _UNCHANGED:
            name = "project_open " + key
            assert now[name] == _V1437[name], (name, now[name], _V1437[name])
            name = "properties_import " + key
            if _V1437[name][0] == "OPENS":
                assert now[name] == _V1437[name], name
        # what 0.1.437 let out loose or opened, and what it wrapped and
        # this version says by the new sentence
        was = {k.split(" ", 1)[1]: v[0] for k, v in _V1437.items()
               if k.startswith("project_open")}
        assert sorted(k for k, t in was.items()
                      if t not in ("InvalidArgument", "OPENS")) == sorted(
            ["raiz_lista", "raiz_numero", "raiz_cadena", "raiz_null",
             "raiz_bool", "settings_lista", "seismic_lista", "foco_elemento",
             "variable_elemento", "carpeta", "distribucion_null",
             "huella_corta", "z_orden_infinito", "anidado"]), was
        assert sorted(k for k, t in was.items() if t == "OPENS") == [
            "busqueda_lista", "foco_falso", "geojson", "materials_obj",
            "materials_texto", "peso_cadena", "rejilla_cero", "vacio"], was

    def test_what_moves_says_the_sentence_of_its_shape(self):
        now = _capture()
        for key in [*_NOW, "carpeta", *_INSIDE]:
            kind, text = now["project_open " + key]
            assert kind == "InvalidArgument", (key, kind, text)
            if key == "anidado":
                assert text.startswith(_agent_text(key)), (key, text)
            else:
                assert text == _agent_text(key), (key, text)

    def test_a_file_the_system_will_not_hand_over(self):
        """A file that exists and cannot be read (locked, no permission) is
        said as such, by both operations; ``Project.load`` is made to fail
        as the system would, and put back."""
        from ogr_api import InvalidArgument, Workspace, call
        from ogr_core.project import Project

        def refused(*_a, **_k):
            raise PermissionError(13, "Permission denied")
        ws = Workspace()
        saved = Project.__dict__["load"]
        said = []
        try:
            target = call(ws, "project_new", template="demo")["project_id"]
            Project.load = classmethod(lambda cls, path: refused())
            for op, kw in (("project_open", {}),
                           ("properties_import", {"project_id": target})):
                try:
                    call(ws, op, path=_path("peso_cadena"), **kw)
                except InvalidArgument as exc:
                    said.append(_scrub(exc))
        finally:
            Project.load = saved
            ws.shutdown()
        assert said == ["[E_INVALID_ARGUMENT] <tmp>/peso_cadena.ogr cannot "
                        "be read: PermissionError: [Errno 13] Permission "
                        "denied"] * 2, said

    def test_the_exceptions_carry_the_codes(self):
        """``Project.load`` raises the ``ValueError`` of a coded refusal, and
        its text is the sentence."""
        from ogr_core.file_messages import (ITEM_SHAPE, NO_PROJECT_KEY,
                                            NOT_A_PROJECT, SECTION_SHAPE)
        from ogr_core.project import Project
        codes = {k: SECTION_SHAPE for k in _NOW}
        codes.update({k: NOT_A_PROJECT for k in _NOW if k.startswith("raiz")})
        codes.update({k: NO_PROJECT_KEY for k in ("vacio", "geojson")})
        codes.update({k: ITEM_SHAPE for k in (
            "material_null", "material_null_2", "foco_elemento",
            "variable_elemento")})
        for key, sentence in _NOW.items():
            try:
                Project.load(_path(key))
            except ValueError as exc:
                coded = exc.args[0]
                assert str(exc) == sentence == str(coded), key
                assert coded.code == codes[key], (key, coded.code)
            else:
                raise AssertionError("%s was read" % key)


# ======================================================================
def _rich():
    """A model with every section ``to_dict`` writes when it has one."""
    from ogr_core.annotations.annotation import Annotation, AnnotationKind
    from ogr_core.fem.seepage_data import BCType, SeepageBoundaryConditions
    from ogr_core.geometry import Vertex
    from ogr_core.geometry.focus import FocusObject
    from ogr_core.geometry.slip_circle import SlipCircle
    from ogr_core.geometry.user_polyline import UserPolylineSurface
    from ogr_core.hydraulic.water_pressure_grid import WaterPressureGrid
    from ogr_core.loads.loads import DistributedLoad, LineLoad
    from ogr_core.loads.seismic_record import SeismicRecord
    from ogr_core.project.demo import build_demo_project
    from ogr_core.statistics import available_variables
    from ogr_core.support import GroutedTieback, SupportInstance
    p = build_demo_project()
    # v0.1.464 (D357): with Sarma, so its section is written too
    p.settings.methods.enabled_methods.append("sarma")
    g = GroutedTieback()
    p.support_types = [g]
    p.supports = [SupportInstance(type_id="grouted_tieback", type_ref=g.id,
                                  name="S1", head=Vertex(30, 20),
                                  tail=Vertex(20, 15))]
    p.add_distributed_load(DistributedLoad(start=Vertex(5, 25),
                                           end=Vertex(20, 25),
                                           magnitude_1=20.0))
    p.add_line_load(LineLoad(point=Vertex(10, 25), magnitude=50.0))
    p.seismic_records = [SeismicRecord(name="Rec", dt=0.01,
                                       accelerations=[0.0, 0.1, 0.0])]
    p.focus_objects = [FocusObject(points=[(20.0, 20.0)])]
    p.random_variables = [next(v for v in available_variables(p)
                               if v.param == "cohesion")]
    p.seepage_bcs = SeepageBoundaryConditions()
    p.seepage_bcs.add_node(0, BCType.TOTAL_HEAD, 10.0)
    p.water_pressure_grid = WaterPressureGrid(points=[(10.0, 10.0, 5.0)])
    p.annotations.add(Annotation(kind=AnnotationKind.LINE,
                                 points=[(0.0, 0.0), (5.0, 5.0)]))
    assert p.assign_material_at(10.0, 5.0, p.materials[0].id)
    p.user_surfaces = [SlipCircle(centre_x=30.0, centre_y=40.0, radius=25.0)]
    p.user_polylines = [UserPolylineSurface(points=[
        (5.0, 25.0), (25.0, 12.0), (45.0, 20.0)])]
    # a mesh of one triangle and its fields, without a solve: what to_dict
    # writes of each is an object (the review of 0.1.438: without them, a
    # table that refused every saved finite-element model passed)
    from ogr_core.fem.mesh import Element, Mesh, Node
    from ogr_core.fem.seepage_data import SeepageResult
    p.fem_mesh = Mesh(nodes=[Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
                             Node(2, 0.0, 10.0)],
                      elements=[Element(0, (0, 1, 2),
                                        material_id=p.materials[0].id)],
                      target_size=10.0)
    p.seepage_result = SeepageResult(total_head=[5.0, 5.0, 5.0])
    p.transient_results = [SeepageResult(total_head=[5.0, 5.0, 5.0])]
    p.transient_initial_result = SeepageResult(total_head=[5.0, 5.0, 5.0])
    return p


#: the sections the reader has always taken as null, measured one by one on
#: the demo with 0.1.437: written here, not read off the table it checks
_NULLABLE = {"water_pressure_grid", "fem_mesh", "seepage_bcs",
             "seepage_result", "transient_initial_result",
             "transient_results", "random_variables", "annotations",
             "focus_objects", "user_surfaces", "user_polylines"}
_NULLABLE_SETTINGS = {"search", "advanced", "design_standard",
                      # v0.1.464 (D357): ``or {}`` reads the defaults
                      "sarma"}


def _function_keys(src, cls, fn):
    """The string keys ``fn`` of class ``cls`` reads off its ``data``:
    ``data.get("k")``, ``data["k"]`` and ``"k" in data``."""
    tree = ast.parse(src)
    keys = set()
    for c in ast.walk(tree):
        if not (isinstance(c, ast.ClassDef) and c.name == cls):
            continue
        for f in c.body:
            if not (isinstance(f, ast.FunctionDef) and f.name == fn):
                continue
            for n in ast.walk(f):
                if (isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "get"
                        and getattr(n.func.value, "id", "") == "data"
                        and n.args and isinstance(n.args[0], ast.Constant)):
                    keys.add(n.args[0].value)
                elif (isinstance(n, ast.Subscript)
                      and getattr(n.value, "id", "") == "data"
                      and isinstance(n.slice, ast.Constant)):
                    keys.add(n.slice.value)
                elif (isinstance(n, ast.Compare)
                      and isinstance(n.left, ast.Constant)
                      and any(isinstance(o, ast.In) for o in n.ops)
                      and any(getattr(c2, "id", "") == "data"
                              for c2 in n.comparators)):
                    keys.add(n.left.value)
    return keys


class TestEveryValidFileOpensTheSame:

    def test_the_table_is_what_to_dict_writes(self):
        from ogr_core.file_messages import json_shape
        from ogr_core.project.file_shape import (_ACCEPTS, SCALARS,
                                                 SECTIONS,
                                                 SETTINGS_SECTIONS)
        d = json.loads(json.dumps(_rich().to_dict()))
        sections = set(d) - set(SCALARS)
        assert sections == set(SECTIONS), sections ^ set(SECTIONS)
        for key in sections:
            # the model has one of each: no section is checked by its null
            assert d[key] not in (None, [], {}), key
            assert json_shape(d[key]) in _ACCEPTS[SECTIONS[key]], key
            if isinstance(d[key], list):
                assert all(json_shape(i) == "object" for i in d[key]), key
        settings = {k for k, v in d["settings"].items()
                    if isinstance(v, dict)}
        assert settings == set(SETTINGS_SECTIONS), (
            settings ^ set(SETTINGS_SECTIONS))

    def test_the_table_is_what_the_readers_read(self):
        """Every key ``Project.from_dict`` reads is in the table, and the
        table has nothing it does not read but ``format_version`` (written
        since 0.1.59, read by nothing); the settings likewise."""
        from ogr_core.project.file_shape import (SCALARS, SECTIONS,
                                                 SETTINGS_SECTIONS)
        src = S.source("ogr_core/project/project.py").read_text(
            encoding="utf-8")
        read = _function_keys(src, "Project", "from_dict")
        assert read == set(SECTIONS) | set(SCALARS) - {"format_version"}, (
            read ^ (set(SECTIONS) | set(SCALARS)))
        src = S.source("ogr_core/project/settings.py").read_text(
            encoding="utf-8")
        read = _function_keys(src, "ProjectSettings", "from_dict")
        assert read == set(SETTINGS_SECTIONS) | {"max_materials",
                                                 "max_supports"}, read

    def test_a_file_reads_back_as_it_was(self):
        from ogr_api.snapshot import document_hash
        from ogr_core.project import Project
        from ogr_core.project.demo import build_demo_project
        for name, p in (("demo", build_demo_project()), ("rich", _rich())):
            f = os.path.join(_TMP, "back %s.ogr" % name)
            p.save(f)
            once = Project.load(f)
            once.save(f)
            twice = Project.load(f)
            assert document_hash(once) == document_hash(twice), name

    def test_a_null_the_reader_always_took_still_opens(self):
        from ogr_core.project import Project
        for key in _NULLABLE:
            Project.from_dict(_put([key], None)(_base()))
        for key in _NULLABLE_SETTINGS:
            Project.from_dict(_put(["settings", key], None)(_base()))

    def test_only_a_null(self):
        """The idioms that took a null (``if section:``, ``or {}``) also
        swallowed ``""``, ``0`` and ``false``; those are a section of another
        shape, and refused (the owner's decision in the review of 0.1.438).
        Every other section refuses a null too."""
        from ogr_core.file_messages import SECTION_SHAPE
        from ogr_core.project import Project
        from ogr_core.project.file_shape import SECTIONS, SETTINGS_SECTIONS
        cases = [([k], v) for k in _NULLABLE for v in ("", 0, False)]
        cases += [(["settings", k], v) for k in _NULLABLE_SETTINGS
                  for v in ("", 0, False)]
        cases += [([k], None) for k in set(SECTIONS) - _NULLABLE]
        cases += [(["settings", k], None)
                  for k in set(SETTINGS_SECTIONS) - _NULLABLE_SETTINGS]
        # v0.1.464 (D357): + 3, the three falsy values of «sarma»
        assert len(cases) == 42 + 11 + 8 + 3, len(cases)
        for path, value in cases:
            try:
                Project.from_dict(_put(path, value)(_base()))
            except ValueError as exc:
                assert exc.args[0].code == SECTION_SHAPE, (path, value)
            else:
                raise AssertionError("%r with %r was read" % (path, value))

    def test_a_bom_is_read_as_the_same_file(self):
        from ogr_api.snapshot import document_hash
        from ogr_core.project import Project
        plain = os.path.join(_TMP, "plain.ogr")
        with open(plain, "w", encoding="utf-8") as fh:
            json.dump(_base(), fh)
        assert document_hash(Project.load(_path("con_bom"))) == (
            document_hash(Project.load(plain)))


# ======================================================================
_SERVER: list = []


def _server():
    if not _SERVER:
        from _leaks import root_logging_kept
        from ogr_api import Workspace
        from ogr_mcp.server import build_server
        ws = Workspace()
        # building the server configures the root logger (audit D-f)
        with root_logging_kept():
            _SERVER.append((ws, build_server(ws, profile="full")))
    return _SERVER[0]


def _bridged(real):
    """What a call does through the bridge to a window, without the socket:
    the handler sends ``error_to_dict`` of what it raised, and the client
    raises ``error_from_dict`` of that (``ogr_api/bridge.py``)."""
    from ogr_api.bridge import error_from_dict, error_to_dict

    def call(ws, op, **kw):
        try:
            return real(ws, op, **kw)
        except Exception as exc:  # noqa: BLE001
            raise error_from_dict(error_to_dict(exc)) from None
    return call


def _mcp_texts(bridged=False):
    """For each case, what the MCP server answers to ``project_open`` and
    ``properties_import``: whether it is an error, and its text."""
    import ogr_mcp.server as S
    from mcp import Client
    ws, srv = _server()

    async def scenario():
        out = {}
        async with Client(srv) as c:
            r = await c.call_tool("project_new", {"name": "dest"})
            dest = json.loads(r.content[0].text)["project_id"]
            for key, _how in CASES:
                for tool, args in (("project_open", {"path": _path(key)}),
                                   ("properties_import",
                                    {"path": _path(key),
                                     "project_id": dest})):
                    r = await c.call_tool(tool, args)
                    text = " ".join(getattr(x, "text", "")
                                    for x in r.content)
                    if not r.is_error and tool == "project_open":
                        pid = json.loads(text)["project_id"]
                        await c.call_tool("project_close", {
                            "project_id": pid, "discard_changes": True})
                        text = "opens"
                    elif not r.is_error:
                        text = "imports"
                    out["%s %s" % (tool, key)] = (r.is_error, _scrub(text))
            await c.call_tool("project_close", {"project_id": dest,
                                                "discard_changes": True})
        return out

    saved = S.call
    if bridged:
        S.call = _bridged(saved)
    try:
        return asyncio.run(scenario())
    finally:
        S.call = saved


class TestTheMcpSaysItOnce:

    def test_with_a_window_and_without(self):
        if not _have_mcp():
            return
        alone, bridged = _mcp_texts(), _mcp_texts(bridged=True)
        assert alone == bridged, {k: (alone[k], bridged[k]) for k in alone
                                  if alone[k] != bridged[k]}
        for key in [*_NOW, *_INSIDE]:
            is_error, text = alone["project_open " + key]
            assert is_error and _agent_text(key) in text, (key, text)

    def test_an_unexpected_exception_is_internal_both_ways(self):
        if not _have_mcp():
            return
        import logging
        import ogr_mcp.server as S
        from mcp import Client
        ws, srv = _server()

        def boom(*_a, **_k):
            raise ValueError("boom detail")

        async def scenario():
            async with Client(srv) as c:
                return await c.call_tool("project_list", {})
        saved = S.call
        log = logging.getLogger("ogr_mcp")
        level = log.level
        said = []
        try:
            # the trace it logs is not what is checked here
            log.setLevel(logging.CRITICAL)
            for fn in (boom, _bridged(boom)):
                S.call = fn
                r = asyncio.run(scenario())
                said.append((r.is_error, r.content[0].text))
        finally:
            S.call = saved
            log.setLevel(level)
        assert said[0] == said[1], said
        assert said[0][0] and "[E_INTERNAL] ValueError: boom detail" in (
            said[0][1]), said


# ======================================================================
def _fields(template):
    return sorted({f for _t, f, _s, _c in string.Formatter().parse(template)
                   if f})


class TestEachCodeSaysItInSpanish:

    def test_the_catalogue_and_the_words(self):
        from ogr_core.file_messages import (FILE_MESSAGES, ITEM_SHAPE,
                                            NO_PROJECT_KEY, NOT_A_PROJECT,
                                            SECTION_SHAPE, SHAPE_WORDS)
        from ogr_gui.core_messages import _catalogue
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for code in (NOT_A_PROJECT, NO_PROJECT_KEY, SECTION_SHAPE,
                     ITEM_SHAPE):
            spec = FILE_MESSAGES[code]
            assert code in _catalogue(), code
            assert es.get(spec.english, spec.english) != spec.english, code
            assert _fields(es[spec.english]) == _fields(spec.english), code
        for key, words in SHAPE_WORDS.items():
            if key != "null":
                assert es.get(words, words) != words, words

    def test_the_sentences(self):
        from ogr_core.project import Project
        from ogr_gui.core_messages import error_text
        said = {}
        for key in _NOW_ES:
            try:
                Project.load(_path(key))
            except ValueError as exc:
                with _Language("es"):
                    said[key] = error_text(exc)
                with _Language("en"):
                    # the window's English is the agent's sentence
                    assert error_text(exc) == _NOW[key], key
        assert said == _NOW_ES, said


# ======================================================================
_WINDOW: list = []


def _window():
    if not _WINDOW:
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w.project.is_dirty = False
        _WINDOW.append(w)
    return _WINDOW[0]


@_requires_qt
class TestTheWindowSaysIt:

    def test_open_says_the_shape(self):
        """Open, by its real handler, with the file dialog and the message
        box replaced and put back; the window keeps its project."""
        import ogr_gui.main_window as MW
        w = _window()
        before = w.project
        boxes = []
        saved = (MW.get_open_file_name, MW.QMessageBox.critical)
        MW.QMessageBox.critical = staticmethod(
            lambda *a, **k: boxes.append(a[2] if len(a) > 2 else ""))
        try:
            for key in ("raiz_lista", "materials_obj", "foco_elemento",
                        "vacio"):
                MW.get_open_file_name = (
                    lambda *a, _p=_path(key), **k: (_p, ""))
                w.project.is_dirty = False
                with _Language("es"):
                    w.act_open()
                assert boxes[-1] == ("No se pudo abrir el proyecto:\n"
                                     + _NOW_ES[key]), boxes[-1]
                assert w.project is before
        finally:
            MW.get_open_file_name, MW.QMessageBox.critical = saved
            w.project.is_dirty = False
        assert len(boxes) == 4, boxes
