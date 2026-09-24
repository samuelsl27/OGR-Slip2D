# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Running analyses and reading what they found.

Every search runs as a JOB in a child process (``ogr_api.jobs``), even a
three-second one: one path for every run is what keeps a short run and a
long one from ever giving different answers, and it is what makes Cancel
real. ``analysis_run`` waits up to ``wait_seconds`` and either returns the
result or hands back a ``job_id`` to ask about later.

The job analyses a DETACHED COPY of the model taken when it starts, so an
edit made while it runs cannot leak into it; its result records the
model's fingerprint, and a result whose model has changed since is marked
``stale`` wherever it is shown.

``surface_evaluate`` prices one given surface in-process: it is quick, and
it goes through ``analysis_runner.evaluate_surfaces``, the same factored
copy and configured search a run uses.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..coerce import coerce_value, points
from ..errors import InvalidArgument, JobFailed, NotConfigured, unknown
from ..results import factor_report_summary, json_safe, lem_summary
from ..snapshot import detached_copy, model_hash
from . import operation

_VIEWS = ("summary", "critical", "top", "minima", "warnings")


def _check_runnable(project, methods) -> list:
    from ogr_core.project.rules import compute_blockers
    from ogr_slip2d.analysis_runner import check_analysis_settings
    from ogr_slip2d.methods import method_registry

    blockers = [r.message for r in compute_blockers(project)]
    blockers += list(check_analysis_settings(project))
    if blockers:
        raise NotConfigured(
            "The model cannot be analysed as configured: "
            + " ".join(blockers),
            details={"problems": blockers},
            hint="Fix these, or see project_validate.")
    if methods is None:
        return list(project.settings.methods.enabled_methods) or [
            "bishop_simplified"]
    methods = coerce_value(methods, list[str], "methods")
    known = method_registry()
    for mid in methods:
        if mid not in known:
            raise unknown("method", mid, sorted(known))
    if not methods:
        raise InvalidArgument("methods is empty.")
    return methods


def _job_answer(ws, job, *, raise_on_failure: bool) -> dict:
    """What a caller sees of a job, storing its result the first time."""
    st = job.status()
    state = st["state"]
    out = {"job_id": job.id, "state": state,
           "elapsed_s": st.get("elapsed_s")}
    if state == "running":
        out["progress"] = st.get("progress")
        out["hint"] = (f"Still running; call job_get('{job.id}', "
                       f"wait_seconds=30) to wait, or job_cancel to stop.")
        return out
    if state == "done":
        summary = job.summary() or {}
        handle = ws.projects.get(job.project_id)
        if job.result_id is None and handle is not None:
            res = ws.store_result(
                handle, "analysis", summary, model_hash=job.model_hash,
                loader=job.load_results,
                on_evict=lambda j=job: ws.jobs.forget(j.id))
            job.result_id = res.id
        out["result_id"] = job.result_id
        out["summary"] = summary
        if handle is not None:
            out["stale"] = model_hash(handle.project) != job.model_hash
        return out
    out["error"] = st.get("error")
    if st.get("problems"):
        out["problems"] = st["problems"]
    if st.get("log_tail"):
        out["log_tail"] = st["log_tail"]
    if raise_on_failure and state in ("failed", "crashed"):
        raise JobFailed(f"The analysis {state}: {st.get('error')}",
                        details=json_safe(out))
    return out


@operation("analysis_run", toolset="analysis")
def analysis_run(ws, project_id: Optional[str] = None,
                 methods: Optional[list] = None,
                 wait_seconds: float = 30.0) -> dict:
    """Run the configured search for each method, as a background job."""
    wait = coerce_value(wait_seconds, float, "wait_seconds")
    if wait < 0:
        raise InvalidArgument("wait_seconds cannot be negative.")
    handle = ws.get(project_id)
    with ws.reading(handle.id, "analysis_run") as project:
        method_ids = _check_runnable(project, methods)
        copy = detached_copy(project)
        fingerprint = model_hash(project)
    job = ws.jobs.start("analysis", copy, handle.id, fingerprint,
                        {"method_ids": method_ids})
    job.wait(wait)
    return _job_answer(ws, job, raise_on_failure=True)


@operation("job_get", toolset="analysis")
def job_get(ws, job_id: str, wait_seconds: float = 0.0) -> dict:
    """A job's state, waiting up to wait_seconds for it to finish."""
    wait = coerce_value(wait_seconds, float, "wait_seconds")
    job = ws.jobs.get(job_id)
    job.wait(max(0.0, wait))
    return _job_answer(ws, job, raise_on_failure=False)


@operation("job_cancel", toolset="analysis")
def job_cancel(ws, job_id: str) -> dict:
    """Stop a running job and every process it started."""
    job = ws.jobs.get(job_id)
    job.cancel()
    return _job_answer(ws, job, raise_on_failure=False)


@operation("job_list", toolset="analysis")
def job_list(ws) -> dict:
    """Every job of this session and its state."""
    if ws._jobs is None:
        return {"jobs": []}
    return {"jobs": [{"job_id": j.id, "project_id": j.project_id,
                      "state": j.status()["state"],
                      "result_id": j.result_id}
                     for j in ws.jobs.jobs.values()]}


# ----------------------------------------------------------------------
@operation("results_get", toolset="analysis")
def results_get(ws, result_id: str, method_id: Optional[str] = None,
                view: str = "summary", n: int = 10) -> dict:
    """Read a stored result: summary, critical (with slices), top, minima,
    warnings."""
    if view not in _VIEWS:
        raise unknown("view", view, _VIEWS)
    n = coerce_value(n, int, "n")
    if not 1 <= n <= 100:
        raise InvalidArgument("n must be between 1 and 100.")
    handle, res = ws.find_result(result_id)
    out = {"result_id": res.id, "kind": res.kind,
           "project_id": handle.id,
           "stale": model_hash(handle.project) != res.model_hash}
    if view == "summary":
        out["summary"] = res.summary
        return out
    if view == "warnings":
        out["warnings"] = res.summary.get("warnings", [])
        return out
    payload = res.payload().get("results", {})
    mids = [method_id] if method_id else list(payload)
    for mid in mids:
        if mid not in payload:
            raise unknown("method in this result", mid, list(payload))
    per = {}
    for mid in mids:
        r = payload[mid]
        is_search = hasattr(r, "evaluations")
        crit = r.critical if is_search else r
        if view == "critical":
            per[mid] = lem_summary(crit, with_slices=True)
        elif view == "top":
            per[mid] = [lem_summary(x) for x in r.top_n(n)] \
                if is_search else [lem_summary(r)]
        elif view == "minima":
            per[mid] = [lem_summary(x) for x in
                        (getattr(r, "minima", None) or [])[:n]]
    out[view] = per
    return out


def surface_from_spec(spec):
    """A ``SlipCircle`` or ``SlipSurface`` from a small JSON spec."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipCircle, SlipSurface

    if not isinstance(spec, dict):
        raise InvalidArgument("surface must be an object with a 'type'.")
    kind = spec.get("type")
    if kind == "circle":
        def g(*names):
            for nm in names:
                if nm in spec:
                    return coerce_value(spec[nm], float, nm)
            raise InvalidArgument(f"A circle needs {names[0]}.")
        r = g("radius", "r")
        if r <= 0:
            raise InvalidArgument("radius must be positive.")
        return SlipCircle(centre_x=g("centre_x", "center_x", "xc"),
                          centre_y=g("centre_y", "center_y", "yc"),
                          radius=r)
    if kind == "three_points":
        pts = points(spec.get("points"), "points", minimum=3)
        if len(pts) != 3:
            raise InvalidArgument("three_points needs exactly 3 points.")
        try:
            return SlipCircle.from_three_points(*(Vertex(x, y)
                                                  for x, y in pts))
        except (ValueError, ZeroDivisionError) as exc:
            raise InvalidArgument(f"No circle through those points: "
                                  f"{exc}") from None
    if kind == "polyline":
        pts = points(spec.get("points"), "points", minimum=2)
        return SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))
    raise unknown("surface type", kind, ["circle", "three_points",
                                         "polyline"])


@operation("surface_evaluate", toolset="analysis")
def surface_evaluate(ws, surface: dict, project_id: Optional[str] = None,
                     methods: Optional[list] = None) -> dict:
    """The factor of safety of ONE given slip surface, per method."""
    from ogr_slip2d.analysis_runner import (AnalysisNotConfigured,
                                            evaluate_surfaces)

    surf = surface_from_spec(surface)
    handle = ws.get(project_id)
    with ws.reading(handle.id, "surface_evaluate") as project:
        method_ids = _check_runnable(project, methods)
        copy = detached_copy(project)
        fingerprint = model_hash(project)
    try:
        outcome = evaluate_surfaces(copy, surf, method_ids)
    except AnalysisNotConfigured as exc:  # pragma: no cover - checked above
        raise NotConfigured(str(exc),
                            details={"problems": exc.problems}) from None
    per = {mid: lem_summary(r) for mid, r in outcome.results.items()}
    summary = {"methods": per,
               "factor_report": factor_report_summary(outcome.factor_report),
               "warnings": list(outcome.warnings)}
    res = ws.store_result(handle, "surface", summary,
                          model_hash=fingerprint,
                          payload={"results": outcome.results,
                                   "factor_report": outcome.factor_report})
    none = [mid for mid, r in outcome.results.items() if r is None]
    if none:
        summary["notes"] = [f"{', '.join(none)}: the surface does not cut "
                            f"the model, so there is nothing to price."]
    return {"result_id": res.id, **summary}
