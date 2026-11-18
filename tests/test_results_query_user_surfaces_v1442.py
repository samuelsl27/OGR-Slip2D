# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.442 (D400) — the API's listings include the surfaces the user drew, and
say which they are; the census stays the search's.

The invariant: a view that LISTS surfaces lists every surface the run
analysed, the ones the user drew by hand included, and marks those with
``surface.user_defined``; the CENSUS of rejected surfaces describes what the
search generated, the population the counters count, and a surface of the
user never enters it. Until this version ``results_query`` with ``filter``
and ``raw_data`` read the search's population alone: with a hand-drawn
polyline critical (demo slope, Janbu, F = 1.123199), ``filter fos_max=1.2``
answered nothing and the raw data had no row for the surface the run
reported; and no listing, the ``critical`` of ``analysis_run`` among them,
said whose a surface was.

What is anchored here:

* the definition, re-derived here from the run itself: ``filter`` by factor
  is the admissible surfaces of ``evaluations`` AND ``user_evaluations``
  within the bounds, and the raw data is one row for each of both lists, the
  search's first and untouched;
* the identity of the census, which is what keeps the two rules apart: for
  every error code, ``filter(code).count == by_code.get(code, 0)``, less at
  -101 the rejections that leave no evaluation and the census counts there.
  On a grid whose census is NOT empty (two -112, four -111 and eleven -101
  under Bishop, the eleven refused by the Slope Limits without leaving an
  evaluation, so the -101 clause is exercised), with a user circle the
  m-alpha screen rejects: it is in the raw data, marked, and the census
  does not move;
* without surfaces of the user nothing changes. ``_V1441`` is MEASURED on
  the tree of 0.1.441 (a16295f) by running this file's ``_capture()`` there
  (``_auditoria/P10_herramientas/capture_d400.py`` of the bench); it is not
  what this code prints. The factors in it were rounded on one machine and
  the suite also runs on another, so a number is compared to 2e-6 and
  everything else (keys, order, strings, counts, booleans) exactly. In the
  same process the comparison is exact: a row is ``lem_summary`` of always,
  to the last key.

Without Qt. Five small runs through ``analysis_run`` (about 0.7 s each: they
are the cost of the file), computed once and shared.
"""
from __future__ import annotations

import atexit
import copy
import json
import os
import re
import tempfile
from types import SimpleNamespace

_J, _B = "janbu_simplified", "bishop_simplified"
#: The polyline of ``tests/test_back_analysis_user_surfaces_v1428.py``: added
#: to the demo slope's Path search of 5 it is the critical surface of the run
#: (F = 1.123199; the search alone finds 1.309425).
_WINNER = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
#: The one of ``tests/test_user_polylines_v1427.py`` that the m-alpha screen
#: rejects under Bishop (F = 0.223, code -112).
_STEEP = [(19.0, 25.0), (31.0, 8.0), (34.0, 16.0)]
#: Two circles of the user on the low grid, both inside its Slope Limits: one
#: valid, which is the critical surface of that run (F = 1.185; the grid alone
#: finds 1.3007), and one the m-alpha screen rejects (F = 3.0019, -112).
_FREE, _BARRED = (36.0, 28.0, 12.0), (32.0, 16.0, 5.0)
_SIX = ["centre_x", "centre_y", "radius", "x_left", "x_right",
        "fos_or_error_code"]


def _path_project(method, polylines):
    from examples.quick_slope import build_demo_slope
    from ogr_slip2d.surface import UserPolylineSurface
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "non_circular", "path"
    s.path_num_surfaces = 5
    s.optimize_enabled = False
    p.settings.methods.enabled_methods = [method]
    p.user_polylines = [UserPolylineSurface.from_points(q)
                        for q in polylines]
    return p


def _grid_project(circles):
    """A low grid on the demo slope whose census is not empty under Bishop,
    with a left Slope Limit that refuses some circles before they are
    sliced: 64 circles, two -112, four -111 and eleven -101, the eleven
    without an evaluation (measured in the review of 0.1.442)."""
    from examples.quick_slope import build_demo_slope
    from ogr_slip2d.surface import SlipCircle
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "circular", "grid"
    s.grid_x_min, s.grid_x_max = 30.0, 38.0
    s.grid_y_min, s.grid_y_max = 17.0, 23.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    s.slope_limit_left, s.slope_limit_right = 24.0, 50.0
    p.settings.methods.enabled_methods = [_B]
    p.user_surfaces = [SlipCircle(centre_x=x, centre_y=y, radius=r)
                       for x, y, r in circles]
    return p


_CASES = {
    "path": lambda: _path_project(_J, []),
    "path+user": lambda: _path_project(_J, [_WINNER]),
    "steep": lambda: _path_project(_B, [_WINNER, _STEEP]),
    "grid": lambda: _grid_project([]),
    "grid+user": lambda: _grid_project([_FREE, _BARRED]),
}
_WS: list = []
_RUNS: dict = {}


def _ws():
    if not _WS:
        from ogr_api import Workspace
        ws = Workspace()
        atexit.register(ws.shutdown)
        _WS.append(ws)
    return _WS[0]


def _run(name):
    """The run of a case, once: its id, its method, what ``analysis_run``
    answered for the method, and the ``SearchResult`` behind it."""
    if name not in _RUNS:
        from ogr_api import call
        ws = _ws()
        p = _CASES[name]()
        mid = p.settings.methods.enabled_methods[0]
        run = call(ws, "analysis_run", project_id=ws.add(p).id,
                   wait_seconds=300)
        _h, res = ws.find_result(run["result_id"])
        _RUNS[name] = SimpleNamespace(
            rid=run["result_id"], mid=mid,
            summary=run["summary"]["methods"][0],
            sr=res.payload()["results"][mid])
    return _RUNS[name]


def _q(name, **kw):
    from ogr_api import call
    return call(_ws(), "results_query", result_id=_run(name).rid, **kw)


def _get(name, view, **kw):
    from ogr_api import call
    r = _run(name)
    return call(_ws(), "results_get", result_id=r.rid, view=view,
                **kw)[view][r.mid]


def _is_users(row) -> bool:
    return (row.get("surface") or {}).get("user_defined") is True


def _mentions(obj) -> int:
    """How many times ``user_defined`` is a key or a word anywhere in a
    JSON answer."""
    if isinstance(obj, dict):
        return sum((k == "user_defined") + _mentions(v)
                   for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return sum(_mentions(v) for v in obj)
    return int(isinstance(obj, str) and "user_defined" in obj)


def _unmarked(row) -> dict:
    """A listed row without its mark, to compare it with ``lem_summary``."""
    out = dict(row)
    out["surface"] = {k: v for k, v in (row.get("surface") or {}).items()
                      if k != "user_defined"}
    return out


def _cells(csv_text) -> list:
    return [line.split(",") for line in csv_text.splitlines()]


def _admissible(evaluations) -> list:
    """The surfaces a listing by factor may show: no error code. The mapping
    of the codes is the program's (``error_code``, anchored by
    ``tests/test_tensile_export_code_v1192.py``); what is re-derived here is
    WHICH LISTS are read, the rule of this version."""
    from ogr_slip2d.interpretation import error_code
    return [r for r in evaluations if error_code(r) is None]


def _no_evaluation(sr, code: int = -101) -> int:
    """The rejections the census files under ``code`` that left no
    evaluation (``invalid_summary``), which a filter over evaluations cannot
    count.

    v0.1.445 (D420) -- changed on purpose: -103 too, the circles that leave
    the External Boundary, counted on the result since that version."""
    attrs = {-101: ("ends_below_ground", "ends_above_ground",
                    "bases_above_ground", "outside_slope_limits",
                    "misses_ground"),
             -103: ("leaves_external",)}.get(code, ())
    return sum(int(getattr(sr, a, 0) or 0) for a in attrs)


# ----------------------------------------------------------------------
# The reference of "nothing changes"
# ----------------------------------------------------------------------
def _capture():
    """What the tree it runs on answers for the two runs WITHOUT surfaces of
    the user, through the API alone, as JSON text (so the order of the keys
    is part of it). Run on the tree of 0.1.441 for ``_V1441`` (see the
    header)."""
    out = {}
    for name, point in (("path", [25.0, 18.0]), ("grid", [33.0, 15.5])):
        r = _run(name)
        crit = _get(name, "critical")
        sl = _q(name, view="slices")
        raw = _q(name, view="raw_data")
        answers = {
            "summary": r.summary,
            "get.critical": {"keys": list(crit),
                             "slices": len(crit["slices"])},
            "get.top": _get(name, "top", n=2)[1],
            "raw_data": {k: v for k, v in raw.items() if k != "csv_head"},
            "raw_data.cells": _cells(raw["csv_head"])[:3],
            "filter": _q(name, view="filter", fos_max=2.0, n=1),
            "filter.code": _q(name, view="filter", code=-112, n=1),
            "minimum_per_centre": _q(name, view="minimum_per_centre", n=1),
            "slices": {"surface": sl["surface"], "n": len(sl["slices"]),
                       "keys": list(sl["slices"][0])},
            "through": _q(name, view="surfaces_through_point",
                          point_xy=point, tolerance=1.0, n=1),
            "error_codes": _q(name, view="error_codes")["by_code"],
            "invalid_summary": _q(name, view="invalid_summary")["census"],
        }
        out[name] = {view: json.dumps(_masked(answer), ensure_ascii=False)
                     for view, answer in answers.items()}
    return out


def _masked(obj):
    """The same JSON with the ids of the run, random each time, hidden."""
    if isinstance(obj, dict):
        return {k: ("<id>" if k in ("result_id", "project_id") else
                    _masked(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_masked(v) for v in obj]
    return obj


def _number(text):
    """A number written with decimals, and how many: ``(value, decimals)``,
    or None for any other text."""
    if not re.fullmatch(r"-?\d+\.\d+", text):
        return None
    return float(text), len(text.split(".")[1])


def _differences(got, want, where="") -> list:
    """Where two JSON answers differ: everything exactly, except a number
    with decimals (also one written as text, a cell of the CSV), to 2e-6."""
    if isinstance(want, bool) or isinstance(got, bool) or want is None:
        return [] if got is want else [f"{where}: {got!r} != {want!r}"]
    if isinstance(want, dict):
        if not isinstance(got, dict) or list(got) != list(want):
            return [f"{where}: keys {list(got) if isinstance(got, dict) else got!r}"
                    f" != {list(want)}"]
        return [d for k in want
                for d in _differences(got[k], want[k], f"{where}.{k}")]
    if isinstance(want, list):
        if not isinstance(got, list) or len(got) != len(want):
            return [f"{where}: {got!r} != {want!r}"]
        return [d for i, (g, w) in enumerate(zip(got, want))
                for d in _differences(g, w, f"{where}[{i}]")]
    if isinstance(want, float):
        return [] if (isinstance(got, float)
                      and abs(got - want) <= 2e-6) else [
            f"{where}: {got!r} != {want!r}"]
    if isinstance(want, str) and isinstance(got, str) and got != want:
        g, w = _number(got), _number(want)
        if (g is not None and w is not None and g[1] == w[1]
                and abs(g[0] - w[0]) <= 2e-6):
            return []
    return [] if got == want and type(got) is type(want) else [
        f"{where}: {got!r} != {want!r}"]


#: MEASURED on 0.1.441 (a16295f) with ``_capture()``; see the header.
_V1441 = {
    "path": {
        "summary": (
            '{"method_id": "janbu_simplified", "caption": "fos", "value":'
            ' 1.309425, "unit": "-", "critical": {"fos": 1.309425, "conve'
            'rged": true, "iterations": 4, "valid": true, "admissible": t'
            'rue, "surface": {"type": "polyline", "vertices": [[18.704396'
            ', 25.0], [18.750842, 24.943035], [20.64659, 22.617925], [22.'
            '542339, 20.292815], [24.438087, 17.967705], [26.333836, 15.6'
            '42595], [28.861639, 14.02698], [31.468373, 12.542077], [34.4'
            '59135, 12.306824], [37.421644, 12.779628], [40.328913, 13.51'
            '9752], [43.236183, 14.259876], [46.143452, 15.0]]}, "n_slice'
            's": 25}, "counts": {"attempted": 6, "total": 6, "valid": 5, '
            '"invalid": 1, "inadmissible": 0, "focus_rejected": 0, "user_'
            'surfaces": 0}, "optimized": false}'),
        "get.critical": (
            '{"keys": ["fos", "converged", "iterations", "valid", "admiss'
            'ible", "surface", "n_slices", "slices"], "slices": 25}'),
        "get.top": (
            '{"fos": 1.336519, "converged": true, "iterations": 4, "valid'
            '": true, "admissible": true, "surface": {"type": "polyline",'
            ' "vertices": [[21.075834, 25.0], [22.056419, 22.949307], [23'
            '.350591, 20.242812], [24.644763, 17.536316], [26.285098, 15.'
            '024484], [28.727448, 13.282379], [31.43776, 11.996219], [34.'
            '353744, 11.291209], [37.284086, 11.933935], [40.065809, 13.0'
            '57329], [42.35186, 15.0]]}, "n_slices": 25}'),
        "raw_data": (
            '{"result_id": "<id>", "view": "raw_data", "stale": false, "m'
            'ethod_id": "janbu_simplified", "rows": 5, "notes": []}'),
        "raw_data.cells": (
            '[["centre_x", "centre_y", "radius", "x_left", "x_right", "fo'
            's_or_error_code"], ["", "", "", "", "", "1.394317"], ["", ""'
            ', "", "", "", "1.405207"]]'),
        "filter": (
            '{"result_id": "<id>", "view": "filter", "stale": false, "met'
            'hod_id": "janbu_simplified", "count": 5, "surfaces": [{"fos"'
            ': 1.309425, "converged": true, "iterations": 4, "valid": tru'
            'e, "admissible": true, "surface": {"type": "polyline", "vert'
            'ices": [[18.704396, 25.0], [18.750842, 24.943035], [20.64659'
            ', 22.617925], [22.542339, 20.292815], [24.438087, 17.967705]'
            ', [26.333836, 15.642595], [28.861639, 14.02698], [31.468373,'
            ' 12.542077], [34.459135, 12.306824], [37.421644, 12.779628],'
            ' [40.328913, 13.519752], [43.236183, 14.259876], [46.143452,'
            ' 15.0]]}, "n_slices": 25, "error_code": null, "x_left": 18.7'
            '04396019339924, "x_right": 46.143452281083505}]}'),
        "filter.code": (
            '{"result_id": "<id>", "view": "filter", "stale": false, "met'
            'hod_id": "janbu_simplified", "count": 0, "surfaces": []}'),
        "minimum_per_centre": (
            '{"result_id": "<id>", "view": "minimum_per_centre", "stale":'
            ' false, "method_id": "janbu_simplified", "count": 5, "surfac'
            'es": [{"fos": 1.309425, "converged": true, "iterations": 4, '
            '"valid": true, "admissible": true, "surface": {"type": "poly'
            'line", "vertices": [[18.704396, 25.0], [18.750842, 24.943035'
            '], [20.64659, 22.617925], [22.542339, 20.292815], [24.438087'
            ', 17.967705], [26.333836, 15.642595], [28.861639, 14.02698],'
            ' [31.468373, 12.542077], [34.459135, 12.306824], [37.421644,'
            ' 12.779628], [40.328913, 13.519752], [43.236183, 14.259876],'
            ' [46.143452, 15.0]]}, "n_slices": 25, "error_code": null, "x'
            '_left": 18.704396019339924, "x_right": 46.143452281083505}]}'),
        "slices": (
            '{"surface": {"fos": 1.309425, "converged": true, "iterations'
            '": 4, "valid": true, "admissible": true, "surface": {"type":'
            ' "polyline", "vertices": [[18.704396, 25.0], [18.750842, 24.'
            '943035], [20.64659, 22.617925], [22.542339, 20.292815], [24.'
            '438087, 17.967705], [26.333836, 15.642595], [28.861639, 14.0'
            '2698], [31.468373, 12.542077], [34.459135, 12.306824], [37.4'
            '21644, 12.779628], [40.328913, 13.519752], [43.236183, 14.25'
            '9876], [46.143452, 15.0]]}, "n_slices": 25, "error_code": nu'
            'll, "x_left": 18.704396019339924, "x_right": 46.143452281083'
            '505}, "n": 25, "keys": ["index", "x_centre", "width", "base_'
            'length", "base_angle_deg", "height", "weight", "weight_facto'
            'r", "pore_pressure", "surface_pressure", "base_normal_force"'
            ', "driving_shear", "sigma_n", "sigma_n_eff", "tau_f", "tau_m'
            '", "material", "cohesion", "friction_angle"]}'),
        "through": (
            '{"result_id": "<id>", "view": "surfaces_through_point", "sta'
            'le": false, "method_id": "janbu_simplified", "count": 2, "su'
            'rfaces": [{"fos": 1.309425, "converged": true, "iterations":'
            ' 4, "valid": true, "admissible": true, "surface": {"type": "'
            'polyline", "vertices": [[18.704396, 25.0], [18.750842, 24.94'
            '3035], [20.64659, 22.617925], [22.542339, 20.292815], [24.43'
            '8087, 17.967705], [26.333836, 15.642595], [28.861639, 14.026'
            '98], [31.468373, 12.542077], [34.459135, 12.306824], [37.421'
            '644, 12.779628], [40.328913, 13.519752], [43.236183, 14.2598'
            '76], [46.143452, 15.0]]}, "n_slices": 25, "error_code": null'
            ', "x_left": 18.704396019339924, "x_right": 46.14345228108350'
            '5, "distance": 0.455911}]}'),
        "error_codes": '{}',
        "invalid_summary": (
            '{"generated": 6, "analysed": 5, "rejected": 1, "by_code": {}'
            ', "by_reason": {}, "by_group": {}, "not_sliced": 1, "focus_r'
            'emoved": 0}'),
    },
    "grid": {
        "summary": (
            '{"method_id": "bishop_simplified", "caption": "fos", "value"'
            ': 1.300715, "unit": "-", "critical": {"fos": 1.300715, "conv'
            'erged": true, "iterations": 4, "valid": true, "admissible": '
            'true, "surface": {"type": "circle", "centre_x": 32.666667, "'
            'centre_y": 23.0, "radius": 7.183816, "x_left": 25.48285, "x_'
            'right": 34.049473, "tension_cracks": [[25.482850456191933, 2'
            '3.0, 24.517149543808067]]}, "n_slices": 25}, "counts": {"att'
            'empted": 64, "total": 64, "valid": 41, "invalid": 23, "inadm'
            'issible": 2, "focus_rejected": 0, "user_surfaces": 0}, "opti'
            'mized": false}'),
        "get.critical": (
            '{"keys": ["fos", "converged", "iterations", "valid", "admiss'
            'ible", "surface", "n_slices", "slices"], "slices": 25}'),
        "get.top": (
            '{"fos": 1.317209, "converged": true, "iterations": 4, "valid'
            '": true, "admissible": true, "surface": {"type": "circle", "'
            'centre_x": 32.666667, "centre_y": 23.0, "radius": 8.650067, '
            '"x_left": 24.016599, "x_right": 35.956601, "tension_cracks":'
            ' [[24.0165991713838, 23.0, 25.0]]}, "n_slices": 25}'),
        "raw_data": (
            '{"result_id": "<id>", "view": "raw_data", "stale": false, "m'
            'ethod_id": "bishop_simplified", "rows": 45, "notes": ["The f'
            'irst 20 rows; pass save_path for all."]}'),
        "raw_data.cells": (
            '[["centre_x", "centre_y", "radius", "x_left", "x_right", "fo'
            's_or_error_code"], ["30.0", "17.0", "2.5152543263816605", "2'
            '7.484745673618338", "32.51525432638166", "-112"], ["30.0", "'
            '17.0", "4.878858223313768", "25.121141776686233", "34.606707'
            '06401459", "2.969934"]]'),
        "filter": (
            '{"result_id": "<id>", "view": "filter", "stale": false, "met'
            'hod_id": "bishop_simplified", "count": 13, "surfaces": [{"fo'
            's": 1.300715, "converged": true, "iterations": 4, "valid": t'
            'rue, "admissible": true, "surface": {"type": "circle", "cent'
            're_x": 32.666667, "centre_y": 23.0, "radius": 7.183816, "x_l'
            'eft": 25.48285, "x_right": 34.049473, "tension_cracks": [[25'
            '.482850456191933, 23.0, 24.517149543808067]]}, "n_slices": 2'
            '5, "error_code": null, "x_left": 25.482850456191933, "x_righ'
            't": 34.04947255010049}]}'),
        "filter.code": (
            '{"result_id": "<id>", "view": "filter", "stale": false, "met'
            'hod_id": "bishop_simplified", "count": 2, "surfaces": [{"fos'
            '": 4.910382, "converged": true, "iterations": 4, "valid": tr'
            'ue, "admissible": false, "surface": {"type": "circle", "cent'
            're_x": 30.0, "centre_y": 17.0, "radius": 2.515254, "x_left":'
            ' 27.484746, "x_right": 32.515254, "tension_cracks": [[27.484'
            '745673618338, 17.0, 22.515254326381662], [32.51525432638166,'
            ' 17.0, 17.48474567361834]]}, "n_slices": 25, "admissibility_'
            'note": "m_alpha < 0.2 on 1 slice(s)", "note_code": "screen.m'
            '_alpha", "note_args": {"limit": 0.2, "count": 1}, "error_cod'
            'e": -112, "x_left": 27.484745673618338, "x_right": 32.515254'
            '32638166}]}'),
        "minimum_per_centre": (
            '{"result_id": "<id>", "view": "minimum_per_centre", "stale":'
            ' false, "method_id": "bishop_simplified", "count": 16, "surf'
            'aces": [{"fos": 1.300715, "converged": true, "iterations": 4'
            ', "valid": true, "admissible": true, "surface": {"type": "ci'
            'rcle", "centre_x": 32.666667, "centre_y": 23.0, "radius": 7.'
            '183816, "x_left": 25.48285, "x_right": 34.049473, "tension_c'
            'racks": [[25.482850456191933, 23.0, 24.517149543808067]]}, "'
            'n_slices": 25, "error_code": null, "x_left": 25.482850456191'
            '933, "x_right": 34.04947255010049}]}'),
        "slices": (
            '{"surface": {"fos": 1.300715, "converged": true, "iterations'
            '": 4, "valid": true, "admissible": true, "surface": {"type":'
            ' "circle", "centre_x": 32.666667, "centre_y": 23.0, "radius"'
            ': 7.183816, "x_left": 25.48285, "x_right": 34.049473, "tensi'
            'on_cracks": [[25.482850456191933, 23.0, 24.517149543808067]]'
            '}, "n_slices": 25, "error_code": null, "x_left": 25.48285045'
            '6191933, "x_right": 34.04947255010049}, "n": 25, "keys": ["i'
            'ndex", "x_centre", "width", "base_length", "base_angle_deg",'
            ' "height", "weight", "weight_factor", "pore_pressure", "surf'
            'ace_pressure", "base_normal_force", "driving_shear", "sigma_'
            'n", "sigma_n_eff", "tau_f", "tau_m", "material", "cohesion",'
            ' "friction_angle"]}'),
        "through": (
            '{"result_id": "<id>", "view": "surfaces_through_point", "sta'
            'le": false, "method_id": "bishop_simplified", "count": 11, "'
            'surfaces": [{"fos": 1.300715, "converged": true, "iterations'
            '": 4, "valid": true, "admissible": true, "surface": {"type":'
            ' "circle", "centre_x": 32.666667, "centre_y": 23.0, "radius"'
            ': 7.183816, "x_left": 25.48285, "x_right": 34.049473, "tensi'
            'on_cracks": [[25.482850456191933, 23.0, 24.517149543808067]]'
            '}, "n_slices": 25, "error_code": null, "x_left": 25.48285045'
            '6191933, "x_right": 34.04947255010049, "distance": 0.324296}'
            ']}'),
        "error_codes": '{"-112": 2, "-111": 4, "-101": 11}',
        "invalid_summary": (
            '{"generated": 64, "analysed": 39, "rejected": 25, "by_code":'
            ' {"-112": 2, "-111": 4, "-101": 11}, "by_reason": {"an end d'
            'aylights outside the Slope Limits": 11, "Zero driving moment'
            ' — surface does not slide": 3, "m_alpha < 0.2 on 1 slice(s)"'
            ': 2, "Non-physical factor of safety -197 in iteration": 1}, '
            '"by_group": {"an end daylights outside the Slope Limits": 11'
            ', "Zero driving moment — surface does not slide": 3, "m_alph'
            'a < 0.2 on … slice(s)": 2, "Non-physical factor of safety … '
            'in iteration": 1}, "not_sliced": 8, "focus_removed": 0}'),
    },
}


# ======================================================================
class TestTheListingsShowTheUsersSurface:
    """Janbu, Path of 5, and the polyline that is the critical surface."""

    def test_the_run_under_test_is_the_one_of_the_ficha(self):
        r = _run("path+user")
        assert len(r.sr.evaluations) == 5 and len(r.sr.user_evaluations) == 1
        assert r.sr.critical is r.sr.user_evaluations[0]
        assert abs(r.sr.critical.fos - 1.123199) < 2e-6

    def test_the_critical_surface_of_the_run_says_whose_it_is(self):
        r = _run("path+user")
        assert _is_users(r.summary["critical"])
        assert abs(r.summary["critical"]["fos"] - r.sr.critical.fos) < 1e-6
        assert _is_users(_get("path+user", "critical"))
        top = _get("path+user", "top", n=10)
        assert [_is_users(x) for x in top] == [True] + [False] * 5

    def test_the_summary_says_it_in_this_process_too(self):
        """``analysis_run`` writes its summary in the worker's process; the
        same function here, and its ``top``, which no operation asks for
        today."""
        from ogr_api.results import search_summary
        r = _run("path+user")
        got = search_summary(r.mid, r.sr, top=10)
        assert _is_users(got["critical"])
        assert [_is_users(x) for x in got["top"]] == [True] + [False] * 5
        assert _mentions(got) == 2
        alone = _run("path")
        assert _mentions(search_summary(alone.mid, alone.sr, top=10)) == 0

    def test_the_filter_by_factor_finds_it(self):
        """``fos_max=1.2`` answered nothing: the only surface under 1.2 is
        the user's. Against the definition, re-derived from both lists."""
        r = _run("path+user")
        got = _q("path+user", view="filter", fos_max=1.2)
        want = [e for e in _admissible(r.sr.evaluations
                                       + r.sr.user_evaluations)
                if e.fos <= 1.2]
        assert len(want) == 1 and want[0] is r.sr.user_evaluations[0]
        assert got["count"] == 1
        assert _is_users(got["surfaces"][0])
        assert abs(got["surfaces"][0]["fos"] - want[0].fos) < 1e-6

    def test_the_filter_without_bounds_is_both_lists(self):
        r = _run("path+user")
        got = _q("path+user", view="filter", n=1000)
        both = _admissible(r.sr.evaluations + r.sr.user_evaluations)
        assert got["count"] == len(both) == 6
        assert sorted(s["fos"] for s in got["surfaces"]) == sorted(
            round(e.fos, 6) for e in both)
        assert sum(map(_is_users, got["surfaces"])) == 1
        # and the bounds apply to the user's as to any other
        assert _q("path+user", view="filter", fos_min=1.2)["count"] == 5

    def test_the_raw_data_has_its_row_and_a_seventh_column(self):
        r = _run("path+user")
        got = _q("path+user", view="raw_data")
        head, *rows = _cells(got["csv_head"])
        assert head == _SIX + ["user_defined"]
        assert got["rows"] == len(rows) == 6
        assert [row[6] for row in rows] == ["0"] * 5 + ["1"]
        assert abs(float(rows[-1][5]) - r.sr.critical.fos) < 1e-6
        assert all(len(row) == 7 for row in rows)

    def test_the_searchs_rows_are_the_ones_of_the_run_without_it(self):
        """The same search with and without the polyline, in this process:
        its rows first, in their order, cell for cell."""
        _head, *with_it = _cells(_q("path+user", view="raw_data")["csv_head"])
        _head, *alone = _cells(_q("path", view="raw_data")["csv_head"])
        assert [row[:6] for row in with_it[:5]] == alone
        assert all(len(row) == 6 for row in alone)

    def test_the_csv_that_is_saved_has_them_too(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "raw.csv")
            got = _q("path+user", view="raw_data", save_path=path)
            assert got["rows"] == 6
            with open(path, encoding="utf-8") as fh:
                head, *rows = _cells(fh.read())
        assert head == _SIX + ["user_defined"]
        assert [row[6] for row in rows] == ["0"] * 5 + ["1"]

    def test_every_listing_marks_it_and_only_it(self):
        r = _run("path+user")
        per_centre = _q("path+user", view="minimum_per_centre", n=1000)
        assert sum(map(_is_users, per_centre["surfaces"])) == 1
        assert _is_users(per_centre["surfaces"][0])
        assert _is_users(_q("path+user", view="slices")["surface"])
        assert _is_users(_q("path+user", view="slices", rank=1)["surface"])
        assert not _is_users(_q("path+user", view="slices",
                                rank=2)["surface"])
        # a vertex of the polyline: the user's surface passes through it
        hits = _q("path+user", view="surfaces_through_point",
                  point_xy=list(_WINNER[1]), tolerance=0.01)
        assert hits["count"] >= 1
        assert [s for s in hits["surfaces"] if s["distance"] < 1e-9
                and _is_users(s)], hits
        # the mark is true or it is not there: never false, never elsewhere
        for answer in (per_centre, hits, r.summary,
                       _q("path+user", view="filter", n=1000),
                       _get("path+user", "top", n=10)):
            rows = (answer.get("surfaces", [answer.get("critical")])
                    if isinstance(answer, dict) else answer)
            assert _mentions(answer) == sum(map(_is_users, rows)), answer

    def test_a_marked_row_is_otherwise_the_row_of_always(self):
        from ogr_api.results import json_safe, lem_summary
        r = _run("path+user")
        assert _unmarked(r.summary["critical"]) == json_safe(
            lem_summary(r.sr.critical))


# ======================================================================
class TestTheCensusStaysTheSearchs:
    """Bishop on the low grid, whose census is not empty, with two circles
    of the user: one valid, the critical surface, and one m-alpha rejects."""

    def test_the_run_under_test_has_a_census(self):
        from ogr_slip2d.interpretation import error_code
        r = _run("grid+user")
        census = _q("grid+user", view="error_codes")["by_code"]
        assert census == {"-112": 2, "-111": 4, "-101": 11}, census
        # the eleven left no evaluation: the Slope Limits refused them
        assert _no_evaluation(r.sr) == 11
        assert r.sr.outside_slope_limits == 11
        free, barred = r.sr.user_evaluations
        assert r.sr.critical is free
        assert error_code(free) is None and error_code(barred) == -112

    def test_the_census_is_the_same_with_and_without_them(self):
        for view in ("error_codes", "invalid_summary"):
            with_them = _masked(_q("grid+user", view=view))
            alone = _masked(_q("grid", view=view))
            assert with_them == alone, view
        mine, theirs = (dict(_run(n).summary["counts"])
                        for n in ("grid+user", "grid"))
        assert mine.pop("user_surfaces") == 2
        assert theirs.pop("user_surfaces") == 0
        assert mine == theirs

    def test_the_filter_by_code_is_the_census(self):
        """For every code, also with a rejected surface of the user: it has
        the code -112 and is not one of the two. At -101 the census counts
        eleven circles that left no evaluation, which no filter can list."""
        from ogr_slip2d.interpretation import ERROR_CODES
        for name in ("grid+user", "grid", "steep", "path+user"):
            r = _run(name)
            census = _q(name, view="error_codes")["by_code"]
            for code in ERROR_CODES:
                want = census.get(str(code), 0) - _no_evaluation(r.sr, code)
                got = _q(name, view="filter", code=code, n=1000)
                assert got["count"] == want, (name, code, got["count"], want)
                assert not any(map(_is_users, got["surfaces"])), (name, code)
        assert _q("grid+user", view="filter", code=-101)["count"] == 0
        assert _q("grid+user", view="filter", code=-112)["count"] == 2

    def test_a_code_with_a_bound_is_still_the_census(self):
        """``code`` and a factor bound together: the user's rejected circle
        (-112, F = 3.0019) is inside any such bound and is not listed."""
        from ogr_slip2d.interpretation import error_code
        r = _run("grid+user")
        barred = r.sr.user_evaluations[1]
        coded = [e for e in r.sr.evaluations if error_code(e) == -112]
        assert len(coded) == 2
        hi = max(e.fos for e in coded + [barred]) + 1.0
        got = _q("grid+user", view="filter", code=-112, fos_min=0.0,
                 fos_max=hi, n=1000)
        assert got["count"] == 2
        assert not any(map(_is_users, got["surfaces"]))
        low = min(e.fos for e in coded)
        assert _q("grid+user", view="filter", code=-112,
                  fos_max=low + 1e-9)["count"] == 1

    def test_a_rejected_surface_of_the_user_is_listed_and_not_counted(self):
        from ogr_slip2d.interpretation import error_code
        r = _run("grid+user")
        head, *rows = _cells(_save_all("grid+user"))
        assert head == _SIX + ["user_defined"]
        assert len(rows) == len(r.sr.evaluations) + 2
        assert [row[6] for row in rows] == (
            ["0"] * len(r.sr.evaluations) + ["1", "1"])
        free, barred = rows[-2:]
        assert [float(c) for c in barred[:3]] == list(_BARRED)
        assert barred[5] == "-112"
        assert [float(c) for c in free[:3]] == list(_FREE)
        assert abs(float(free[5]) - r.sr.critical.fos) < 1e-6
        # and the grid's rows are the ones of the run without them, whole:
        # here every cell of the geometry has something in it
        _head, *alone = _cells(_save_all("grid"))
        assert [row[:6] for row in rows[:-2]] == alone
        assert all(all(row[:5]) and len(row) == 6 for row in alone)
        # by factor: the valid one is listed, the rejected one is not
        by_factor = _q("grid+user", view="filter", n=1000)
        search_only = _admissible(r.sr.evaluations)
        assert by_factor["count"] == len(search_only) + 1
        assert sum(map(_is_users, by_factor["surfaces"])) == 1
        assert error_code(r.sr.user_evaluations[1]) == -112

    def test_the_steep_polyline_of_the_user_under_bishop(self):
        """The ficha's own case: m-alpha rejects it, the counters and the
        census do not move, and the listings show it with its code."""
        r = _run("steep")
        counts = r.summary["counts"]
        assert (counts["total"], counts["valid"], counts["inadmissible"],
                counts["user_surfaces"]) == (6, 5, 0, 2), counts
        assert _q("steep", view="error_codes")["by_code"] == {}
        head, *rows = _cells(_q("steep", view="raw_data")["csv_head"])
        assert [row[5:] for row in rows[-2:]] == [
            [f"{r.sr.critical.fos:.6f}", "1"], ["-112", "1"]]
        per_centre = _q("steep", view="minimum_per_centre", n=1000)
        marked = [s for s in per_centre["surfaces"] if _is_users(s)]
        assert sorted((s["error_code"], s["admissible"]) == (-112, False)
                      for s in marked) == [False, True]
        assert sorted((s["error_code"], s["admissible"]) == (None, True)
                      for s in marked) == [False, True]

    def test_only_a_rejected_surface_of_the_user_is_enough(self):
        """The seventh column is there when the run analysed a surface of
        the user, valid or not: with the rejected circle alone too."""
        from ogr_slip2d.interpretation import raw_data_rows
        from ogr_slip2d import interpretation as it
        raw_data_columns = getattr(it, "raw_data_columns",
                                   lambda _sr: list(_SIX))
        sr = _run("grid+user").sr
        barred = sr.user_evaluations[1]
        only = SimpleNamespace(evaluations=sr.evaluations,
                               user_evaluations=[barred])
        assert raw_data_columns(only) == _SIX + ["user_defined"]
        rows = raw_data_rows(only)
        assert [row[6] for row in rows] == ["0"] * len(sr.evaluations) + ["1"]
        assert rows[-1][5] == "-112"

    def test_whose_a_surface_is_goes_by_identity(self):
        """A surface of the user that repeats one of the search is still the
        user's, and the search's twin is not: the same geometry, the same
        factor, another object."""
        from ogr_api import results
        from ogr_slip2d.interpretation import raw_data_rows
        summary_in_search = getattr(
            results, "summary_in_search",
            lambda _sr, r, **kw: results.lem_summary(r, **kw))
        sr = _run("grid").sr
        twin = copy.copy(sr.evaluations[0])
        double = SimpleNamespace(evaluations=list(sr.evaluations[:2]),
                                 user_evaluations=[twin])
        rows = raw_data_rows(double)
        assert rows[0][:6] == rows[2][:6]
        assert [row[6] for row in rows] == ["0", "0", "1"]
        assert _is_users(summary_in_search(double, twin))
        assert not _is_users(summary_in_search(double, sr.evaluations[0]))

    def test_the_head_says_where_the_users_rows_are(self):
        """``csv_head`` stops at 20 rows and the user's are the last ones:
        the seventh column would read all zeros."""
        got = _q("grid+user", view="raw_data")
        assert got["rows"] > 20
        assert all(row[6] == "0" for row in _cells(got["csv_head"])[1:])
        assert len(got["notes"]) == 2
        assert "last 2 row(s) of the %d" % got["rows"] in got["notes"][1]
        # nothing to say when they are in sight, when everything was saved,
        # or when there are none
        assert _q("path+user", view="raw_data")["notes"] == []
        assert len(_q("grid", view="raw_data")["notes"]) == 1
        with tempfile.TemporaryDirectory() as folder:
            saved = _q("grid+user", view="raw_data",
                       save_path=os.path.join(folder, "raw.csv"))
        assert "notes" not in saved


def _save_all(name) -> str:
    """The whole raw data (``csv_head`` stops at 20 rows)."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "raw.csv")
        _q(name, view="raw_data", save_path=path)
        with open(path, encoding="utf-8") as fh:
            return fh.read()


# ======================================================================
class TestWithoutUserSurfacesNothingChanges:
    def test_the_answers_are_the_ones_of_0_1_441(self):
        got = _capture()
        assert list(got) == list(_V1441)
        bad = []
        for name, views in _V1441.items():
            assert list(got[name]) == list(views), name
            for view, text in views.items():
                bad += _differences(json.loads(got[name][view]),
                                    json.loads(text), f"{name}.{view}")
        assert not bad, bad[:6]

    def test_the_reference_was_measured_on_runs_that_say_something(self):
        """A reference of empty answers would pin nothing. This one reads
        the literal alone: it is about the reference, not the program."""
        for name in ("path", "grid"):
            v = {view: json.loads(text)
                 for view, text in _V1441[name].items()}
            assert v["raw_data.cells"][0] == _SIX
            assert v["filter"]["count"] >= 2 and v["through"]["count"] >= 1
            assert v["get.critical"]["slices"] > 0
            assert v["get.top"]["fos"] > v["summary"]["critical"]["fos"]
        assert json.loads(_V1441["grid"]["error_codes"]) == {
            "-112": 2, "-111": 4, "-101": 11}
        assert json.loads(_V1441["grid"]["filter.code"])["count"] == 2

    def test_nothing_says_user_defined(self):
        for name in ("path", "grid"):
            assert _mentions(_capture()[name]) == 0, name
            assert _mentions(_q(name, view="filter", n=1000)) == 0
            assert _mentions(_get(name, "top", n=100)) == 0
            head = _cells(_q(name, view="raw_data")["csv_head"])[0]
            assert head == _SIX

    def test_a_row_is_the_summary_of_always_to_the_last_key(self):
        """In this process the comparison is exact."""
        from ogr_api import results
        from ogr_api.results import lem_summary
        # a tree without the function summarised every surface so
        summary_in_search = getattr(
            results, "summary_in_search",
            lambda _sr, r, **kw: lem_summary(r, **kw))
        for name in ("path", "grid", "path+user", "grid+user"):
            sr = _run(name).sr
            for r in sr.evaluations:
                assert summary_in_search(sr, r) == lem_summary(r)
        sr = _run("path").sr
        assert summary_in_search(sr, None) is None
        assert summary_in_search(sr, sr.critical, with_slices=True) == (
            lem_summary(sr.critical, with_slices=True))

    def test_the_doubles_with_only_evaluations_keep_six_columns(self):
        """The bench's ``d177`` and
        ``tests/test_tensile_export_code_v1192.py`` build a result with
        nothing but ``evaluations``."""
        from ogr_slip2d import interpretation as it
        from ogr_slip2d.interpretation import raw_data_rows
        # a tree without the function wrote the six names by hand
        raw_data_columns = getattr(it, "raw_data_columns",
                                   lambda _sr: list(_SIX))
        sr = _run("grid").sr
        double = SimpleNamespace(evaluations=list(sr.evaluations[:3]))
        assert raw_data_columns(double) == _SIX
        rows = raw_data_rows(double)
        assert len(rows) == 3 and all(len(row) == 6 for row in rows)
        assert rows == raw_data_rows(sr)[:3]
        assert raw_data_rows(SimpleNamespace(evaluations=None)) == []
        # and a double that does have surfaces of the user is read like a
        # result: seven columns, its rows last
        double.user_evaluations = [sr.evaluations[3]]
        assert raw_data_columns(double) == _SIX + ["user_defined"]
        assert [row[6] for row in raw_data_rows(double)] == [
            "0", "0", "0", "1"]

    def test_the_header_is_written_in_one_place(self):
        """The API and the interpretation window each spelled the six names
        out by hand; a seventh in one of them alone would be a CSV whose
        header does not match its rows."""
        import ogr_slip2d.interpretation as it
        root = os.path.dirname(os.path.dirname(os.path.abspath(it.__file__)))
        # v0.1.473 -- the core in the tree that is imported (tests/_sources.py)
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _sources as S
        found = []
        for package in ("ogr_core", "ogr_slip2d", "ogr_api", "ogr_gui",
                        "ogr_cli", "ogr_mcp"):
            for path in S.package_files(package):
                if '"fos_or_error_code"' in path.read_text(encoding="utf-8"):
                    found.append(S.relative(path))
        assert found == ["ogr_slip2d/interpretation.py"], found
        with open(os.path.join(root, "ogr_gui", "interpret_window.py"),
                  encoding="utf-8") as fh:
            assert ("        header = raw_data_columns(self.search_result)\n"
                    in fh.read())
