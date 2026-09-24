# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Random variables, statistics, back analysis, optimisation, and questions
to a stored result.

v0.1.201 (spec 008, F3b). The three runs go through the analysis door
(``analysis_runner.run_configured_statistics``, ``..._back_analysis``,
``..._optimization``) in a job, like an analysis: design factors, the
settings checks and warnings, the project's settings and seed. The
interface calls the same doors.

``results_query`` asks a stored result what the Interpret window asks it
(``ogr_slip2d.interpretation``): error codes and the census of rejected
surfaces, raw data, surfaces through a point, the minimum per centre, the
factor of safety along the slope, the slices with the method's numbers, a
filter; and, of a statistics result, the histogram, the convergence, the
samples paired by their index and the sensitivity.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import csv
import io
from typing import Optional

from ..coerce import coerce_enum, coerce_value, point
from ..errors import Conflict, InvalidArgument, NotConfigured, unknown
from ..results import json_safe, lem_summary
from ..snapshot import detached_copy, model_hash
from . import operation
from .analysis import (JOB_FINISHERS, JOB_WORDS, _check_runnable,
                       _job_answer, store_job_result)

JOB_WORDS.update(statistics="statistics run",
                 back_analysis="back analysis",
                 optimize="optimisation")


def _wait(wait_seconds) -> float:
    wait = coerce_value(wait_seconds, float, "wait_seconds")
    if wait < 0:
        raise InvalidArgument("wait_seconds cannot be negative.")
    return wait


# ----------------------------------------------------------------------
# Random variables
# ----------------------------------------------------------------------
def _rv_info(rv) -> dict:
    d = json_safe(rv.to_dict())
    d["key"] = rv.key
    d["low"] = json_safe(rv.distribution.low)
    d["high"] = json_safe(rv.distribution.high)
    d["is_random"] = rv.distribution.is_random
    return d


@operation("random_variable_list", toolset="statistics")
def random_variable_list(ws, project_id: Optional[str] = None) -> dict:
    """The model inputs that can be random variables, and those that are."""
    from ogr_core.statistics import available_variables

    with ws.reading(project_id, "random_variable_list") as project:
        avail = available_variables(project)
        return {"available": [{"key": rv.key, "label": rv.label,
                               "kind": rv.kind.value,
                               "current_value": json_safe(
                                   rv.distribution.mean)}
                              for rv in avail],
                "defined": [_rv_info(rv)
                            for rv in project.random_variables]}


@operation("random_variable_set", toolset="statistics", mutates=True)
def random_variable_set(ws, key: str, project_id: Optional[str] = None,
                        distribution: Optional[str] = None,
                        std_dev: Optional[float] = None,
                        rel_min: Optional[float] = None,
                        rel_max: Optional[float] = None,
                        correlated_with: Optional[str] = None,
                        correlation: Optional[float] = None,
                        label: Optional[str] = None) -> dict:
    """Make a model input a random variable, or change one."""
    from ogr_core.statistics import (DistributionType, RandomVariable,
                                     available_variables, get_value)
    from ogr_core.statistics.random_variables import (default_dispersion,
                                                      variable_problems)

    def edit(project):
        defined = {rv.key: rv for rv in project.random_variables}
        notes = []
        if key in defined:
            rv = RandomVariable.from_dict(defined[key].to_dict())
        else:
            avail = {rv.key: rv for rv in available_variables(project)}
            if key not in avail:
                raise unknown("random variable", key, list(avail))
            rv = default_dispersion(RandomVariable.from_dict(
                avail[key].to_dict()))
            notes.append("New variable: std_dev 10 % of the mean and a "
                         "range of 30 % either side, unless given.")
        # The mean IS the model's value: the deterministic analysis uses
        # the model, so samples centred elsewhere would not be samples of
        # this model.
        current = get_value(project, rv)
        if current is not None:
            if abs(current - rv.distribution.mean) > 1e-12 * max(
                    1.0, abs(current)):
                notes.append(f"Mean updated from {rv.distribution.mean:g} "
                             f"to the model's value {current:g}.")
            rv.distribution.mean = float(current)
        d = rv.distribution
        if distribution is not None:
            d.dist_type = coerce_enum(distribution, DistributionType,
                                      "distribution")
        for name, raw in (("std_dev", std_dev), ("rel_min", rel_min),
                          ("rel_max", rel_max)):
            if raw is not None:
                setattr(d, name, coerce_value(raw, float, name))
        if correlated_with is not None:
            rv.correlated_with = correlated_with or None
        if correlation is not None:
            rv.correlation = coerce_value(correlation, float, "correlation")
        if label is not None:
            rv.label = str(label)
        others = [k for k in defined if k != key]
        bad = variable_problems(rv, others)
        if bad:
            raise InvalidArgument(" ".join(bad), details={"problems": bad})
        if std_dev is not None and d.dist_type.value in (
                "uniform", "triangular", "exponential", "none"):
            notes.append(f"std_dev is not read by a {d.dist_type.value} "
                         f"distribution.")
        new = [rv if r.key == key else r for r in project.random_variables]
        if key not in defined:
            new.append(rv)
        project.random_variables = new
        st = project.settings.statistics
        if not (st.probabilistic_analysis or st.sensitivity_analysis):
            notes.append("Neither the probabilistic nor the sensitivity "
                         "analysis is on (settings statistics.*): nothing "
                         "reads the variables yet.")
        return {"variable": _rv_info(rv), "defined": len(new),
                "notes": notes}

    return ws.mutate(project_id, f"Random variable {key}", edit)


@operation("random_variable_delete", toolset="statistics", mutates=True)
def random_variable_delete(ws, key: str,
                           project_id: Optional[str] = None) -> dict:
    """Remove a random variable (or 'all'); correlations to it go too."""
    from ogr_core.statistics.random_variables import forget_variable

    def edit(project):
        keys = [rv.key for rv in project.random_variables]
        if key == "all":
            project.random_variables = []
            return {"removed": keys}
        if key not in keys:
            raise unknown("defined random variable", key, keys)
        project.random_variables = forget_variable(
            list(project.random_variables), key)
        return {"removed": [key]}

    return ws.mutate(project_id, f"Delete random variable {key}", edit)


# ----------------------------------------------------------------------
# The three runs
# ----------------------------------------------------------------------
@operation("statistics_run", toolset="statistics")
def statistics_run(ws, project_id: Optional[str] = None,
                   wait_seconds: float = 30.0) -> dict:
    """Compute Statistics (probabilistic and/or sensitivity) as a job."""
    wait = _wait(wait_seconds)
    handle = ws.get(project_id)
    with ws.reading(handle.id, "statistics_run") as project:
        st = project.settings.statistics
        if not (st.probabilistic_analysis or st.sensitivity_analysis):
            raise NotConfigured(
                "Neither the probabilistic nor the sensitivity analysis is "
                "on.", hint="settings_set statistics.probabilistic_analysis"
                            "=true (or sensitivity_analysis).")
        if not project.random_variables:
            raise NotConfigured("No random variable is defined.",
                                hint="random_variable_list, then "
                                     "random_variable_set.")
        method_ids = _check_runnable(project, None)
        copy_ = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("statistics", copy_, handle.id, fingerprint,
                        {"method_ids": method_ids})
    job.wait(wait)
    return _job_answer(ws, job, raise_on_failure=True)


@operation("back_analysis_run", toolset="statistics")
def back_analysis_run(ws, project_id: Optional[str] = None,
                      target_fos: Optional[float] = None,
                      elevation: Optional[float] = None,
                      method_id: Optional[str] = None,
                      wait_seconds: float = 30.0) -> dict:
    """The horizontal support force needed to reach a target factor of
    safety, over the configured search, as a job."""
    from ogr_slip2d.back_analysis import SUPPORTED_METHODS

    wait = _wait(wait_seconds)
    params = {}
    if target_fos is not None:
        params["target_fos"] = coerce_value(target_fos, float, "target_fos")
        if not params["target_fos"] > 0:
            raise InvalidArgument("target_fos must be positive.")
    if elevation is not None:
        params["elevation"] = coerce_value(elevation, float, "elevation")
    if method_id is not None:
        if method_id not in SUPPORTED_METHODS:
            raise unknown("back-analysis method", method_id,
                          SUPPORTED_METHODS)
        params["method_id"] = method_id
    handle = ws.get(project_id)
    with ws.reading(handle.id, "back_analysis_run") as project:
        _check_runnable(project, None)
        copy_ = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("back_analysis", copy_, handle.id, fingerprint,
                        params)
    job.wait(wait)
    return _job_answer(ws, job, raise_on_failure=True)


@operation("optimize_run", toolset="statistics")
def optimize_run(ws, result_id: str, method_id: Optional[str] = None,
                 max_iterations: Optional[int] = None,
                 wait_seconds: float = 30.0) -> dict:
    """Optimise the critical NON-CIRCULAR surface of an analysis result;
    the optimised surface is stored as a new result."""
    wait = _wait(wait_seconds)
    handle, res = ws.find_result(result_id)
    if res.kind != "analysis":
        raise Conflict(f"{result_id} is a {res.kind} result; optimisation "
                       f"starts from an analysis_run result.")
    payload = res.payload().get("results", {})
    mid = method_id or next(iter(payload), None)
    if mid not in payload:
        raise unknown("method in this result", mid, list(payload))
    crit = getattr(payload[mid], "critical", None)
    if crit is None:
        raise Conflict(f"{mid} found no critical surface to optimise.")
    if not hasattr(crit.surface, "polyline"):
        raise Conflict("Optimisation refines a NON-CIRCULAR surface; the "
                       "critical surface of this method is a circle.",
                       hint="Run a non-circular search (block, path, "
                            "cuckoo...) first.")
    params = {"method_id": mid, "surface": crit.surface,
              "start_fos": crit.fos}
    if max_iterations is not None:
        n = coerce_value(max_iterations, int, "max_iterations")
        if not 10 <= n <= 100_000:
            raise InvalidArgument("max_iterations must be 10..100000.")
        params["max_iterations"] = n
    with ws.reading(handle.id, "optimize_run") as project:
        copy_ = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("optimize", copy_, handle.id, fingerprint, params)
    job.wait(wait)
    out = _job_answer(ws, job, raise_on_failure=True)
    if model_hash(handle.project) != res.model_hash:
        out.setdefault("notes", []).append(
            f"{result_id} was computed on an earlier state of the model; "
            f"its surface was optimised on the model as it is now.")
    return out


def _finish(kind):
    def finisher(ws, job, handle, summary) -> dict:
        store_job_result(ws, job, handle, summary, kind)
        return {}
    return finisher


for _kind in ("statistics", "back_analysis", "optimize"):
    JOB_FINISHERS[_kind] = _finish("optimized" if _kind == "optimize"
                                   else _kind)


# ----------------------------------------------------------------------
# Questions to a stored result
# ----------------------------------------------------------------------
_SEARCH_VIEWS = ("error_codes", "invalid_summary", "raw_data",
                 "surfaces_through_point", "minimum_per_centre",
                 "sf_along_slope", "slices", "filter")
_STAT_VIEWS = ("histogram", "convergence", "samples", "sensitivity")
#: Which parameters each view reads (rule 7: the others are refused).
_READS = {
    "raw_data": {"save_path", "overwrite"},
    "surfaces_through_point": {"point_xy", "tolerance", "n"},
    "minimum_per_centre": {"n"},
    "sf_along_slope": {"bins"},
    "slices": {"rank", "save_path", "overwrite"},
    "filter": {"fos_min", "fos_max", "code", "n"},
    "histogram": {"bins"},
    "convergence": {"n"},
    "samples": {"save_path", "overwrite"},
    "sensitivity": set(),
    "error_codes": set(),
    "invalid_summary": set(),
}


def _csv(rows, header) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _write_or_head(ws, text: str, rows: int, save_path, overwrite) -> dict:
    if save_path is None:
        head = "\n".join(text.splitlines()[:21])
        return {"rows": rows, "csv_head": head,
                "notes": ["The first 20 rows; pass save_path for all."]
                if rows > 20 else []}
    target = ws.resolve_path(save_path, for_write=True, overwrite=overwrite,
                             suffix=".csv")
    target.write_text(text, encoding="utf-8")
    return {"rows": rows, "saved_to": str(target)}


@operation("results_query", toolset="analysis")
def results_query(ws, result_id: str, view: str,
                  method_id: Optional[str] = None,
                  point_xy: Optional[list] = None,
                  tolerance: Optional[float] = None,
                  bins: Optional[int] = None,
                  rank: Optional[int] = None,
                  fos_min: Optional[float] = None,
                  fos_max: Optional[float] = None,
                  code: Optional[int] = None,
                  n: int = 20,
                  save_path: Optional[str] = None,
                  overwrite: bool = False) -> dict:
    """Ask a stored result what the Interpret window asks: error codes,
    rejected surfaces, raw data, surfaces through a point, minima per
    centre, factor along the slope, slices, filters; or a statistics
    result's histogram, convergence, samples and sensitivity."""
    views = _SEARCH_VIEWS + _STAT_VIEWS
    if view not in views:
        raise unknown("view", view, views)
    given = {k for k, v in dict(point_xy=point_xy, tolerance=tolerance,
                                bins=bins, rank=rank, fos_min=fos_min,
                                fos_max=fos_max, code=code,
                                save_path=save_path).items()
             if v is not None}
    if overwrite:
        given.add("overwrite")
    stray = sorted(given - _READS[view])
    if stray:
        raise Conflict(f"{', '.join(stray)} {'is' if len(stray) == 1 else 'are'}"
                       f" not read by view={view!r}.")
    n = coerce_value(n, int, "n")
    if not 1 <= n <= 1000:
        raise InvalidArgument("n must be between 1 and 1000.")
    handle, res = ws.find_result(result_id)
    out = {"result_id": res.id, "view": view,
           "stale": model_hash(handle.project) != res.model_hash}
    if view in _STAT_VIEWS:
        if res.kind != "statistics":
            raise Conflict(f"view {view!r} reads a statistics result; "
                           f"{result_id} is a {res.kind} result.")
        return {**out, **_stat_view(ws, res.payload(), view, method_id,
                                    bins, n, save_path, overwrite)}
    if res.kind != "analysis":
        raise Conflict(f"view {view!r} reads an analysis result; "
                       f"{result_id} is a {res.kind} result.")
    payload = res.payload().get("results", {})
    mid = method_id or next(iter(payload), None)
    if mid not in payload:
        raise unknown("method in this result", mid, list(payload))
    out["method_id"] = mid
    return {**out, **_search_view(ws, payload[mid], view, point_xy,
                                  tolerance, bins, rank, fos_min, fos_max,
                                  code, n, save_path, overwrite)}


def _row(r) -> dict:
    from ogr_slip2d.interpretation import error_code, slope_intercepts

    d = lem_summary(r) or {}
    d["error_code"] = error_code(r)
    d["admissible"] = bool(getattr(r, "admissible", True))
    try:
        xl, xr = slope_intercepts(r)
        d["x_left"], d["x_right"] = json_safe(xl), json_safe(xr)
    except Exception:  # noqa: BLE001 - a surface without a range
        pass
    return d


def _search_view(ws, sr, view, point_xy, tolerance, bins, rank, fos_min,
                 fos_max, code, n, save_path, overwrite) -> dict:
    from ogr_slip2d import interpretation as it

    if not hasattr(sr, "evaluations"):
        raise Conflict("This result holds one evaluated surface, not a "
                       "search; there is nothing to census.")
    if view == "error_codes":
        census = it.invalid_summary(sr)
        return {"codes": {str(k): v for k, v in it.ERROR_CODES.items()},
                "by_code": {str(k): v for k, v in census["by_code"].items()},
                "not_sliced": census["not_sliced"]}
    if view == "invalid_summary":
        census = it.invalid_summary(sr)
        census["by_code"] = {str(k): v for k, v in census["by_code"].items()}
        return {"census": census}
    if view == "raw_data":
        rows = it.raw_data_rows(sr)
        text = _csv(rows, ["centre_x", "centre_y", "radius", "x_left",
                           "x_right", "fos_or_error_code"])
        return _write_or_head(ws, text, len(rows), save_path, overwrite)
    if view == "surfaces_through_point":
        if point_xy is None:
            raise InvalidArgument("surfaces_through_point needs point_xy.")
        x, y = point(point_xy, "point_xy")
        tol = coerce_value(0.5 if tolerance is None else tolerance, float,
                           "tolerance")
        if tol <= 0:
            raise InvalidArgument("tolerance must be positive.")
        hits = it.surfaces_through_point(sr, x, y, tol)
        return {"count": len(hits),
                "surfaces": [{**_row(r), "distance": round(d, 6)}
                             for d, r in hits[:n]]}
    if view == "minimum_per_centre":
        rows = sorted(it.minimum_per_centre(sr), key=lambda r: r.fos)
        return {"count": len(rows), "surfaces": [_row(r) for r in rows[:n]]}
    if view == "sf_along_slope":
        b = None if bins is None else coerce_value(bins, int, "bins")
        xs, fs = it.sf_along_slope(sr, bins=b)
        return {"points": [[round(x, 4), round(f, 6)]
                           for x, f in zip(xs, fs)]}
    if view == "slices":
        if rank is None:
            target = sr.critical
        else:
            k = coerce_value(rank, int, "rank")
            ordered = sr.top_n(max(k, 1))
            if not 1 <= k <= len(ordered):
                raise InvalidArgument(f"rank must be 1..{len(ordered)}.")
            target = ordered[k - 1]
        if target is None:
            raise Conflict("No surface to read slices from.")
        rows = it.slice_rows(target)
        out = {"surface": _row(target)}
        keys = list(rows[0]) if rows else []
        text = _csv([["" if r[k] is None else r[k] for k in keys]
                     for r in rows], keys)
        if save_path is not None:
            out.update(_write_or_head(ws, text, len(rows), save_path,
                                      overwrite))
        else:
            out["slices"] = json_safe(rows)
        return out
    # filter
    lo = None if fos_min is None else coerce_value(fos_min, float,
                                                   "fos_min")
    hi = None if fos_max is None else coerce_value(fos_max, float,
                                                   "fos_max")
    want = None if code is None else coerce_value(code, int, "code")
    if want is not None and want not in it.ERROR_CODES:
        raise unknown("error code", want, [str(c) for c in it.ERROR_CODES])
    picked = []
    for r in sr.evaluations:
        c = it.error_code(r)
        if want is not None:
            if c != want:
                continue
        elif c is not None:
            continue
        if lo is not None and (r.fos is None or r.fos < lo):
            continue
        if hi is not None and (r.fos is None or r.fos > hi):
            continue
        picked.append(r)
    picked.sort(key=lambda r: (r.fos is None, r.fos or 0.0))
    return {"count": len(picked), "surfaces": [_row(r) for r in picked[:n]]}


def _stat_view(ws, payload, view, method_id, bins, n, save_path,
               overwrite) -> dict:
    from ogr_core.statistics import sample_pairs

    if view == "sensitivity":
        sens = payload.get("sensitivity")
        if sens is None:
            raise Conflict("This run had no sensitivity analysis.")
        mid = method_id or next(iter(sens.by_method), None)
        if mid not in sens.by_method:
            raise unknown("method", mid, list(sens.by_method))
        return {"method_id": mid, "ranking": json_safe(sens.ranking(mid)),
                "variables": {k: json_safe({
                    "label": vs.label, "values": vs.values, "fos": vs.fos,
                    "range": vs.fos_range,
                    "crossing_1": vs.crossing(1.0)})
                    for k, vs in sens.by_method[mid].items()}}
    prob = payload.get("probabilistic")
    if prob is None or not prob.ok:
        raise Conflict("This run had no probabilistic result.")
    mid = method_id or getattr(prob.reported, "method_id", None)
    if mid not in prob.by_method:
        raise unknown("method", mid, list(prob.by_method))
    st = prob.by_method[mid].statistics
    if view == "histogram":
        b = 20 if bins is None else coerce_value(bins, int, "bins")
        if not 2 <= b <= 200:
            raise InvalidArgument("bins must be 2..200.")
        return {"method_id": mid, "bins": json_safe(st.histogram(bins=b))}
    if view == "convergence":
        return {"method_id": mid,
                "running": json_safe(st.convergence(steps=n))}
    # samples, each with its own index
    keys = list(prob.samples)
    pairs = {k: {i: v for i, v, _f in sample_pairs(prob, mid, k)}
             for k in keys}
    idx = list(getattr(prob.by_method[mid], "sample_index", []) or [])
    rows = [[i + 1] + [pairs[k].get(i, "") for k in keys] + [f]
            for i, f in zip(idx, st.values)]
    text = _csv(rows, ["sample"] + keys + ["fos"])
    return {"method_id": mid,
            **_write_or_head(ws, text, len(rows), save_path, overwrite)}
