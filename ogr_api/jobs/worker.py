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


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def _write_pickle(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def _provenance() -> dict:
    import ogr_api
    import ogr_slip2d
    return {"ogr_api": str(Path(ogr_api.__file__).resolve().parent),
            "ogr_slip2d_version": ogr_slip2d.__version__,
            "python": sys.version.split()[0]}


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
        _write_json(folder / "progress.json",
                    {"done": int(done), "total": int(total),
                     "fraction": (float(done) / total) if total else None})

    if kind != "analysis":
        raise ValueError(f"unknown job kind {kind!r}")

    from ogr_slip2d.analysis_runner import run_analysis

    from ..results import outcome_summary

    outcome = run_analysis(project, params.get("method_ids"),
                           progress_cb=progress)
    results = outcome.results
    _write_pickle(folder / "result.pkl",
                  {"results": results,
                   "factor_report": outcome.factor_report,
                   "warnings": list(outcome.warnings)})
    _write_json(folder / "summary.json",
                outcome_summary(results, outcome.factor_report,
                                outcome.warnings))
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
