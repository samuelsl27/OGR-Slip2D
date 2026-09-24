# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.198 — a poll of a job's progress cannot kill the job.

Found by a full suite run: an analysis job died with
``PermissionError: [WinError 5]`` renaming ``progress.json.tmp`` over
``progress.json``. On Windows a file cannot be renamed over one another
process holds open, and the parent reads that file while the job runs; the
exception left the progress callback and ended the whole analysis. It is a
race — the same test passed three times in a row afterwards — so nothing
short of holding the file open on purpose reproduces it.

Invariants protected:

* a progress update that cannot be written is SKIPPED (progress is
  advisory), with the destination held open for good;
* a final write (status, summary, result) waits for a reader to let go:
  with the destination held open and released 0.2 s later, it lands;
* a job whose ``progress.json`` a reader keeps open for its whole run
  still finishes, with its result.

On a platform where the rename does not fail the same cases hold
trivially; they cannot pass by accident on Windows, where the hold is real.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}


def _tmp():
    return Path(tempfile.mkdtemp(prefix="ogr_race_"))


class TestTheWorkerWrites:
    def test_a_progress_update_that_cannot_land_is_skipped(self):
        from ogr_api.jobs.worker import _write_progress
        folder = _tmp()
        try:
            dest = folder / "progress.json"
            dest.write_text("{}", encoding="utf-8")
            with open(dest, "r", encoding="utf-8"):
                wrote = _write_progress(folder, 3, 10)     # must not raise
            assert wrote in (True, False)
            assert _write_progress(folder, 4, 10) is True  # once released
            assert json.loads(dest.read_text())["done"] == 4
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_final_write_waits_for_the_reader(self):
        from ogr_api.jobs.worker import _write_json
        folder = _tmp()
        try:
            dest = folder / "status.json"
            dest.write_text("{}", encoding="utf-8")
            fh = open(dest, "r", encoding="utf-8")
            threading.Timer(0.2, fh.close).start()
            t0 = time.time()
            _write_json(dest, {"state": "done"})
            assert json.loads(dest.read_text()) == {"state": "done"}
            assert time.time() - t0 < 5.0
        finally:
            shutil.rmtree(folder, ignore_errors=True)


class TestAJobWithAReaderHoldingItsProgress:
    def test_it_finishes(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        stop = threading.Event()
        try:
            pid = call(ws, "project_new", name="Race")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[20, 20], [70, 20], [70, 35], [50, 35],
                             [30, 25], [20, 25]],
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": _SOIL}],
                "settings": {"methods.enabled_methods":
                             ["bishop_simplified"],
                             "search.grid_x_min": 22.8,
                             "search.grid_x_max": 43.7,
                             "search.grid_y_min": 42.3,
                             "search.grid_y_max": 62.6,
                             "search.grid_nx": 6, "search.grid_ny": 6,
                             "search.radius_increment": 4}})
            started = call(ws, "analysis_run", project_id=pid,
                           wait_seconds=0)
            job = ws.jobs.get(started["job_id"])
            progress = job.folder / "progress.json"

            def hold():
                # Keep the file open whenever it exists, re-opening as the
                # worker replaces it: the worst a polling client can do.
                while not stop.is_set():
                    try:
                        with open(progress, "r", encoding="utf-8"):
                            time.sleep(0.05)
                    except OSError:
                        time.sleep(0.005)
            reader = threading.Thread(target=hold, daemon=True)
            reader.start()
            out = call(ws, "job_get", job_id=started["job_id"],
                       wait_seconds=240)
            assert out["state"] == "done", out
            assert out["summary"]["methods"][0]["counts"]["valid"] > 0
        finally:
            stop.set()
            ws.shutdown()
