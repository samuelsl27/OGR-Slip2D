# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The child process of a job: ``python -m ogr_api.jobs.worker <folder>``.

Everything happens under the ``__main__`` guard. On Windows the Grid
Search's process pool starts its workers by re-importing the parent's main
module (here, this file as ``__mp_main__``); a module that did work at
import time would run the whole analysis again in every pool worker.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time
import traceback
from pathlib import Path


#: v0.1.198 — Windows refuses to rename a file over one another process
#: holds open (``PermissionError``, WinError 5), and the parent READS
#: ``progress.json`` and ``status.json`` while a job runs. Measured in a
#: full suite run: a job died with "PermissionError: [WinError 5]" on the
#: progress file, the moment a poll caught it open. A read takes
#: milliseconds, so a rename that waits a little always gets through.
_REPLACE_TRIES = 40
_REPLACE_WAIT_S = 0.025


def _replace(tmp: Path, path: Path, tries: int = _REPLACE_TRIES) -> None:
    for attempt in range(tries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(_REPLACE_WAIT_S)


def _write_json(path: Path, data: dict,
                tries: int = _REPLACE_TRIES) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
    _replace(tmp, path, tries)


def _write_pickle(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)
    _replace(tmp, path)


def _write_progress(folder: Path, done: int, total: int) -> bool:
    """Report progress; False when this update had to be skipped.

    Progress is advisory: an update that cannot be written (the parent
    holding the file open for its poll) is dropped, never retried and never
    raised — it used to propagate out of the progress callback and kill
    the whole analysis (v0.1.198).
    """
    try:
        _write_json(folder / "progress.json",
                    {"done": int(done), "total": int(total),
                     "fraction": (float(done) / total) if total else None},
                    tries=1)
        return True
    except OSError:
        return False


def _provenance() -> dict:
    import ogr_api
    import ogr_slip2d
    return {"ogr_api": str(Path(ogr_api.__file__).resolve().parent),
            "ogr_slip2d_version": ogr_slip2d.__version__,
            "python": sys.version.split()[0]}


def _analysis(project, params, progress):
    from ogr_slip2d.analysis_runner import run_analysis

    from ..results import outcome_summary

    outcome = run_analysis(project, params.get("method_ids"),
                           progress_cb=progress)
    return ({"results": outcome.results,
             "factor_report": outcome.factor_report,
             "warnings": list(outcome.warnings)},
            outcome_summary(outcome.results, outcome.factor_report,
                            outcome.warnings))


def _groundwater(project, params, progress):
    """Compute Groundwater: steady, or the staged transient with the
    factor of safety at each stage flagged Calculate SF (v0.1.200)."""
    from ogr_slip2d.transient_stability import (run_transient_stability,
                                                solve_project_groundwater)

    from ..results import groundwater_summary

    gw = project.settings.groundwater
    warnings = []
    if gw.transient and gw.transient_stages and params.get("stage_factors"):
        outcome = run_transient_stability(project, params.get("method_ids"),
                                          progress_cb=progress)
        warnings = list(outcome.warnings)
    else:
        solve_project_groundwater(project, progress_cb=progress)
    payload = {"seepage_result": project.seepage_result,
               "transient_results": list(project.transient_results or []),
               "mesh": project.fem_mesh, "warnings": warnings}
    return payload, groundwater_summary(project, warnings)


def _drawdown_sweep(project, params, progress):
    """The drawdown level sweep, through the analysis door (v0.1.200)."""
    from ogr_slip2d.analysis_runner import run_configured_drawdown_sweep

    from ..results import drawdown_sweep_summary

    sweep, report, warnings = run_configured_drawdown_sweep(
        project, params.get("method_ids"),
        n_levels=params.get("n_levels", 11),
        include_total=params.get("include_total", True),
        progress_cb=progress)
    return ({"sweep": sweep, "factor_report": report,
             "warnings": list(warnings)},
            drawdown_sweep_summary(sweep, report, warnings))


#: The job kinds a worker runs: ``fn(project, params, progress) ->
#: (payload for result.pkl, summary for summary.json)``.
_KINDS = {"analysis": _analysis, "groundwater": _groundwater,
          "drawdown_sweep": _drawdown_sweep}


def _run(folder: Path) -> None:
    started = time.time()
    with open(folder / "input.pkl", "rb") as fh:
        job = pickle.load(fh)
    kind = job["kind"]
    params = job["params"]
    project = job["project"]

    last = [0.0]

    def progress(done, total):
        now = time.time()
        if now - last[0] < 0.5 and done < total:
            return
        last[0] = now
        _write_progress(folder, done, total)

    runner = _KINDS.get(kind)
    if runner is None:
        raise ValueError(f"unknown job kind {kind!r}")
    payload, summary = runner(project, params, progress)
    _write_pickle(folder / "result.pkl", payload)
    _write_json(folder / "summary.json", summary)
    _write_json(folder / "status.json",
                {"state": "done", "run_s": round(time.time() - started, 2),
                 "provenance": _provenance()})


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0])
    try:
        _run(folder)
        return 0
    except BaseException as exc:  # noqa: BLE001 - reported, not swallowed
        problems = getattr(exc, "problems", None)
        _write_json(folder / "status.json", {
            "state": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "problems": list(problems) if problems else None,
            "traceback": traceback.format_exc()[-4000:],
        })
        return 1


if __name__ == "__main__":
    sys.exit(main())
