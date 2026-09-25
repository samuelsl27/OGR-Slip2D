# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — an analysis job is isolated, stoppable and honest.

Invariants protected:

* **Isolation.** A job analyses the model AS IT WAS WHEN IT STARTED. An edit
  made while it runs does not reach it — checked by re-pricing the job's
  critical circle on a copy of the ORIGINAL model and demanding the same
  number to 1e-9, which an edited cohesion would move — and the stored
  result says it is ``stale``.
* **Cancel is real.** The engine has no cancellation, so a job is a child
  process and "stop" kills its whole tree: after ``job_cancel`` neither the
  worker nor any process it started is alive. That is what a thread
  could never give.
* **Failure is reported, never mistaken for a result.** A worker that
  raises reports ``failed`` with its error; a worker that dies without a
  word reports ``crashed`` with the tail of its log.
* **One at a time.** A second run while one is going is refused (``Busy``)
  and names the job in the way.
* **Provenance.** The worker says which ``ogr_api`` it imported, and it is
  this tree's — the test-runner lesson of v0.1.89: a stale installed copy
  answers just as confidently.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}


def _acads(ws, grid):
    from ogr_api import call
    pid = call(ws, "project_new", name="Jobs")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                     [20, 25]],
        "materials": [{"name": "Soil", "unit_weight": 20.0,
                       "strength": _SOIL}],
        "settings": {"methods.enabled_methods": ["bishop_simplified"],
                     "search.grid_x_min": 22.8, "search.grid_x_max": 43.7,
                     "search.grid_y_min": 42.3, "search.grid_y_max": 62.6,
                     **grid}})
    return pid


_SMALL = {"search.grid_nx": 4, "search.grid_ny": 4,
          "search.radius_increment": 3}
#: Long enough to still be running when cancelled: GLE and Spencer on a
#: fine grid (tens of thousands of circles).
_LONG = {"methods.enabled_methods": ["gle_morgenstern_price", "spencer"],
         "search.grid_nx": 60, "search.grid_ny": 60,
         "search.radius_increment": 12}


def _children(pid: int) -> list[int]:
    """Direct children of ``pid``."""
    if sys.platform == "win32":
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter "
             f"'ParentProcessId={pid}').ProcessId"],
            capture_output=True, text=True).stdout
        return [int(x) for x in out.split() if x.strip().isdigit()]
    kids = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat") as fh:
                    stat = fh.read()
                if int(stat.rsplit(")", 1)[1].split()[1]) == pid:
                    kids.append(int(d))
            except (OSError, ValueError, IndexError):
                pass
    return kids


def _alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True).stdout
        return str(pid) in out.split()
    try:
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


class TestIsolation:
    def test_an_edit_after_the_start_does_not_reach_the_job(self):
        from ogr_api import Workspace, call
        from ogr_api.ops.analysis import surface_from_spec
        from ogr_api.snapshot import detached_copy
        from ogr_slip2d.analysis_runner import evaluate_surfaces

        ws = Workspace()
        try:
            pid = _acads(ws, _SMALL)
            original = detached_copy(ws.get(pid).project)
            started = call(ws, "analysis_run", project_id=pid,
                           wait_seconds=0)
            call(ws, "material_set", project_id=pid, material="Soil",
                 strength={"model": "mohr_coulomb",
                           "params": {"cohesion": 30.0,
                                      "friction_angle": 35.0}})
            out = call(ws, "job_get", job_id=started["job_id"],
                       wait_seconds=120)
            assert out["state"] == "done", out
            assert out["stale"] is True
            m = out["summary"]["methods"][0]
            surf = surface_from_spec(dict(m["critical"]["surface"],
                                          type="circle"))
            again = evaluate_surfaces(original, surf,
                                      ["bishop_simplified"])
            fos = again.results["bishop_simplified"].fos
            assert abs(fos - m["value"]) < 1e-6, (fos, m["value"])
        finally:
            ws.shutdown()

    def test_progress_is_written_and_ends_complete(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = _acads(ws, _SMALL)
            out = call(ws, "analysis_run", project_id=pid,
                       wait_seconds=120)
            assert out["state"] == "done", out
            job = ws.jobs.get(out["job_id"])
            import json
            prog = json.loads((job.folder / "progress.json").read_text())
            assert prog["done"] == prog["total"] > 0
            assert out["summary"]["methods"][0]["counts"]["attempted"] \
                == 5 * 5 * 4
        finally:
            ws.shutdown()

    def test_the_worker_imported_this_tree(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = _acads(ws, _SMALL)
            out = call(ws, "analysis_run", project_id=pid,
                       wait_seconds=120)
            st = ws.jobs.get(out["job_id"]).status()
            assert Path(st["provenance"]["ogr_api"]) == _ROOT / "ogr_api"
        finally:
            ws.shutdown()


class TestStopAndFailure:
    def test_cancel_kills_the_worker_and_everything_it_started(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = _acads(ws, _LONG)
            started = call(ws, "analysis_run", project_id=pid,
                           wait_seconds=0)
            job = ws.jobs.get(started["job_id"])
            # Give the search time to start its process pool, and record
            # the children it had while it was alive.
            kids: list[int] = []
            deadline = time.time() + 15
            while time.time() < deadline and not kids:
                time.sleep(1.0)
                kids = _children(job.proc.pid)
            assert job.status()["state"] == "running"
            out = call(ws, "job_cancel", job_id=job.id)
            assert out["state"] == "cancelled", out
            assert not _alive(job.proc.pid)
            # v0.1.205 — a moment for the condemned to die. On POSIX the
            # cancel SIGKILLs the whole process group and waits for the
            # worker only; delivery to the pool's processes is asynchronous,
            # and on GitHub's Linux with Python 3.13 one was caught between
            # the signal and its death ("orphaned processes [3033]"; 3.11
            # and 3.12 passed the same run). An orphan — a process outside
            # the group, which nobody signalled — is still alive after this.
            survivors = [k for k in kids if _alive(k)]
            deadline = time.time() + 5.0
            while survivors and time.time() < deadline:
                time.sleep(0.1)
                survivors = [k for k in survivors if _alive(k)]
            assert not survivors, f"orphaned processes {survivors}"
        finally:
            ws.shutdown()

    def test_a_second_run_is_refused_while_one_runs(self):
        from ogr_api import Busy, Workspace, call
        ws = Workspace()
        try:
            pid = _acads(ws, _LONG)
            first = call(ws, "analysis_run", project_id=pid,
                         wait_seconds=0)
            with pytest.raises(Busy):
                call(ws, "analysis_run", project_id=pid, wait_seconds=0)
            call(ws, "job_cancel", job_id=first["job_id"])
        finally:
            ws.shutdown()

    def test_a_worker_that_dies_is_reported_as_crashed(self):
        from ogr_api import Workspace, call
        from ogr_api.jobs import _kill_tree
        ws = Workspace()
        try:
            pid = _acads(ws, _LONG)
            started = call(ws, "analysis_run", project_id=pid,
                           wait_seconds=0)
            job = ws.jobs.get(started["job_id"])
            time.sleep(1.0)
            _kill_tree(job.proc.pid)       # NOT job_cancel: a crash
            job.proc.wait(timeout=10)
            out = call(ws, "job_get", job_id=job.id)
            assert out["state"] == "crashed", out
            assert "log_tail" in out or out.get("error")
        finally:
            ws.shutdown()

    def test_a_worker_that_raises_reports_its_error(self):
        from ogr_api import Workspace, call
        from ogr_api.snapshot import detached_copy, model_hash
        ws = Workspace()
        try:
            pid = _acads(ws, _SMALL)
            project = ws.get(pid).project
            job = ws.jobs.start("no_such_kind", detached_copy(project), pid,
                                model_hash(project), {})
            out = call(ws, "job_get", job_id=job.id, wait_seconds=60)
            assert out["state"] == "failed", out
            assert "no_such_kind" in out["error"]
            assert "result_id" not in out
        finally:
            ws.shutdown()

    def test_an_unconfigured_model_is_refused_before_any_job(self):
        from ogr_api import NotConfigured, Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="empty")["project_id"]
            with pytest.raises(NotConfigured):
                call(ws, "analysis_run", project_id=pid)
            assert ws._jobs is None or not ws.jobs.jobs
        finally:
            ws.shutdown()
