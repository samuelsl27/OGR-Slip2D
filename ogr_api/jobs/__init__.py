# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Analyses in a child process: progress, cancellation, and honest failure.

WHY A PROCESS AND NOT A THREAD. The engine has no cancellation — no loop in
it checks a flag, and the interface's Cancel button sets one nobody reads —
and a thread cannot be killed. A run can take an hour (the verification
bank has models above 70 minutes), so "stop" has to be real: the job's
whole process tree is killed. A process also keeps a native crash from
taking the server down with it, and keeps its standard output — which the
engine does not use, but a pool worker might — off the MCP wire.

The child is NOT a daemon, so the Grid Search can still start its own
process pool inside it (a daemonic process cannot have children, and the
search would fall back to sequential in silence).

The child writes four files into its job folder, each replaced atomically:
``progress.json`` while running; then ``result.pkl`` (the full results),
``summary.json`` (what a caller reads) and ``status.json`` last. A process
that ends without ``status.json`` crashed, and the tail of its
``stderr.log`` says how.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from ..errors import Busy, unknown

#: States a job can be in.
QUEUED, RUNNING, DONE, FAILED, CANCELLED, CRASHED = (
    "queued", "running", "done", "failed", "cancelled", "crashed")
FINAL = (DONE, FAILED, CANCELLED, CRASHED)


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _kill_tree(pid: int) -> None:
    """Kill ``pid`` and everything it started."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, check=False)
    else:  # pragma: no cover - exercised on the POSIX runners
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


class Job:
    """One analysis running (or run) in a child process."""

    def __init__(self, job_id: str, kind: str, project_id: str,
                 folder: Path, proc: subprocess.Popen, model_hash: str,
                 params: dict) -> None:
        self.id = job_id
        self.kind = kind
        self.project_id = project_id
        self.folder = folder
        self.proc = proc
        self.model_hash = model_hash
        self.params = params
        self.started = time.time()
        self.ended: Optional[float] = None
        self.cancelled = False
        #: Set once the result has been stored under a ``result_id``.
        self.result_id: Optional[str] = None
        self._final: Optional[dict] = None

    # ------------------------------------------------------------------
    def status(self) -> dict:
        """Where the job is; final states are cached once reached."""
        if self._final is not None:
            return dict(self._final)
        out = {"job_id": self.id, "kind": self.kind,
               "project_id": self.project_id,
               "elapsed_s": round(time.time() - self.started, 1)}
        status = _read_json(self.folder / "status.json")
        code = self.proc.poll()
        if status is not None and code is not None:
            out.update(status)
            self._finish(out)
        elif self.cancelled and code is not None:
            out["state"] = CANCELLED
            self._finish(out)
        elif code is not None:
            out["state"] = CRASHED
            out["exit_code"] = code
            out["error"] = ("The analysis process ended without reporting "
                            "a result.")
            out["log_tail"] = self.log_tail()
            self._finish(out)
        else:
            out["state"] = RUNNING
            prog = _read_json(self.folder / "progress.json")
            if prog:
                out["progress"] = prog
        return out

    def _finish(self, out: dict) -> None:
        self.ended = self.ended or time.time()
        out["elapsed_s"] = round(self.ended - self.started, 1)
        self._final = dict(out)

    @property
    def done(self) -> bool:
        return self.status()["state"] in FINAL

    def wait(self, timeout: float, poll: float = 0.1) -> dict:
        """Wait up to ``timeout`` seconds for a final state."""
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            st = self.status()
            if st["state"] in FINAL or time.time() >= deadline:
                return st
            time.sleep(poll)

    def log_tail(self, n: int = 2000) -> str:
        try:
            text = (self.folder / "stderr.log").read_text(
                encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return text[-n:]

    def summary(self) -> Optional[dict]:
        return _read_json(self.folder / "summary.json")

    def load_results(self) -> dict:
        """The full results; only ever the file this job's child wrote."""
        with open(self.folder / "result.pkl", "rb") as fh:
            return pickle.load(fh)

    def cancel(self) -> dict:
        if self.proc.poll() is None:
            self.cancelled = True
            _kill_tree(self.proc.pid)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                pass
        return self.status()


class JobManager:
    """Starts, tracks and cancels jobs; at most ``max_concurrent`` at once."""

    def __init__(self, root=None, max_concurrent: int = 1) -> None:
        self._own_root = root is None
        self.root = Path(root) if root else Path(
            tempfile.mkdtemp(prefix="ogr_jobs_"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max(1, int(max_concurrent))
        self.jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def running(self) -> list[Job]:
        return [j for j in self.jobs.values()
                if j.status()["state"] == RUNNING]

    def start(self, kind: str, project, project_id: str, model_hash: str,
              params: dict) -> Job:
        """Pickle ``project`` (a detached copy) and start the worker."""
        with self._lock:
            busy = self.running()
            if len(busy) >= self.max_concurrent:
                raise Busy(
                    f"Job {busy[0].id} is still running.",
                    hint=f"Wait for it with job_get('{busy[0].id}', "
                         f"wait_seconds=...) or stop it with job_cancel.")
            job_id = f"j_{uuid.uuid4().hex[:10]}"
            folder = self.root / job_id
            folder.mkdir()
            with open(folder / "input.pkl", "wb") as fh:
                pickle.dump({"kind": kind, "project": project,
                             "params": params}, fh,
                            protocol=pickle.HIGHEST_PROTOCOL)
            proc = self._spawn(folder)
            job = Job(job_id, kind, project_id, folder, proc, model_hash,
                      params)
            self.jobs[job_id] = job
            return job

    def _spawn(self, folder: Path) -> subprocess.Popen:
        # The worker must import THIS source tree, not whatever else is on
        # the path — the lesson of the test runner's provenance check
        # (v0.1.89): a stale installed copy answers just as confidently.
        root = str(Path(__file__).resolve().parents[2])
        env = dict(os.environ)
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                      cwd=str(folder), env=env)
        if sys.platform == "win32":
            kwargs["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                                       | 0x08000000)  # CREATE_NO_WINDOW
        else:  # pragma: no cover
            kwargs["start_new_session"] = True
        err = open(folder / "stderr.log", "wb")
        try:
            return subprocess.Popen(
                [sys.executable, "-m", "ogr_api.jobs.worker", str(folder)],
                stderr=err, **kwargs)
        finally:
            err.close()

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise unknown("job_id", job_id, list(self.jobs))
        return job

    def cancel(self, job_id: str) -> dict:
        return self.get(job_id).cancel()

    def forget(self, job_id: str) -> None:
        """Drop a finished job and its folder."""
        job = self.jobs.pop(job_id, None)
        if job is not None:
            shutil.rmtree(job.folder, ignore_errors=True)

    def shutdown(self) -> None:
        for job in list(self.jobs.values()):
            if job.proc.poll() is None:
                job.cancel()
        if self._own_root:
            shutil.rmtree(self.root, ignore_errors=True)
