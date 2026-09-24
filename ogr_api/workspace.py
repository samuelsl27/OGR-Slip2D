# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The open models, their locks, their undo history and their results.

A caller never holds a ``Project``: it holds a ``project_id``, a handle this
module mints. That is what the MCP protocol of 2026-07-28 asks of a server
that keeps state between calls — the protocol itself keeps none, so the
state travels as an argument the model can see and pass back (SEP-2567).

Two rules make concurrent callers safe:

* every read and every write of a model happens under that model's lock,
  including reads, because ``resolve_regions`` and ``bounding_box`` WRITE
  their caches;
* every write goes through :meth:`Workspace.mutate`, which wraps it in a
  ``SnapshotCommand``: atomic, and one undo step.

The ``project`` of a handle is read through a provider, not stored. In the
headless server it is the handle's own object; in the live bridge of phase
F4 it will be ``lambda: mainwindow.project``, because the interface swaps
its ``Project`` on New and Open and a stored reference would go on editing
the old one.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Optional

from .errors import Busy, Conflict, InvalidArgument, NotFound, unknown

#: How long an operation waits for a model another operation is using.
LOCK_TIMEOUT_S = 30.0


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class StoredResult:
    """One analysis (or one evaluated surface) kept for later questions.

    ``summary`` is always in memory; the full result — every surface with
    its slices — is loaded only when a question needs it, from ``loader``.
    """

    def __init__(self, result_id: str, kind: str, project_id: str,
                 model_hash: str, summary: dict,
                 loader: Optional[Callable[[], dict]] = None,
                 payload: Optional[dict] = None,
                 on_evict: Optional[Callable[[], None]] = None) -> None:
        self.id = result_id
        self.kind = kind
        self.project_id = project_id
        self.model_hash = model_hash
        self.summary = summary
        self.created = time.time()
        self._loader = loader
        self._payload = payload
        self._on_evict = on_evict

    def payload(self) -> dict:
        """``{"results": {method_id: SearchResult | LEMResult}, ...}``."""
        if self._payload is None and self._loader is not None:
            self._payload = self._loader()
        return self._payload or {}

    def evict(self) -> None:
        self._payload = None
        if self._on_evict is not None:
            try:
                self._on_evict()
            except OSError:
                pass


class ProjectHandle:
    """One open model."""

    def __init__(self, handle_id: str, project=None,
                 provider: Optional[Callable] = None,
                 path: Optional[Path] = None) -> None:
        from ogr_core.project.commands import CommandStack

        self.id = handle_id
        self._project = project
        self._provider = provider
        self.path = path
        self.lock = threading.RLock()
        self.stack = CommandStack()
        self.results: "OrderedDict[str, StoredResult]" = OrderedDict()
        #: Persistent namespace of ``python_exec`` for this model.
        self.exec_ns: dict = {}
        #: Hash of the model as last opened or saved, for "unsaved changes".
        self.saved_hash: Optional[str] = None
        self.busy_with: Optional[str] = None
        self.busy_since: float = 0.0

    @property
    def project(self):
        return self._provider() if self._provider is not None \
            else self._project


class Workspace:
    """Every model a caller has open, plus the job manager.

    ``workdir`` anchors relative paths; without one a relative path is an
    error, because a client such as a desktop chat application starts the
    server in a directory the user never chose.
    """

    def __init__(self, *, workdir: Optional[str | Path] = None,
                 jobs_root: Optional[str | Path] = None,
                 max_concurrent_jobs: int = 1,
                 max_results_per_project: int = 5) -> None:
        self.workdir = Path(workdir).expanduser().resolve() if workdir \
            else None
        self.projects: "OrderedDict[str, ProjectHandle]" = OrderedDict()
        self.max_results_per_project = int(max_results_per_project)
        self._jobs_root = jobs_root
        self._max_jobs = int(max_concurrent_jobs)
        self._jobs = None
        self._registry_lock = threading.Lock()
        # Per thread, the handles currently inside a mutation: a nested
        # mutation of the same model (an operation called from a
        # ``python_exec`` script) is part of the outer undo step.
        self._local = threading.local()

    # ------------------------------------------------------------------
    @property
    def jobs(self):
        if self._jobs is None:
            from .jobs import JobManager
            self._jobs = JobManager(root=self._jobs_root,
                                    max_concurrent=self._max_jobs)
        return self._jobs

    def shutdown(self) -> None:
        """Kill running jobs and remove their files."""
        if self._jobs is not None:
            self._jobs.shutdown()

    # ------------------------------------------------------------------
    def add(self, project=None, *, provider=None,
            path: Optional[Path] = None) -> ProjectHandle:
        from .snapshot import document_hash

        handle = ProjectHandle(_new_id("p"), project=project,
                               provider=provider, path=path)
        with self._registry_lock:
            self.projects[handle.id] = handle
        handle.saved_hash = document_hash(handle.project) if path else None
        return handle

    def get(self, project_id: Optional[str] = None) -> ProjectHandle:
        """The handle for ``project_id``; with None, the only open model."""
        if project_id is None or project_id == "":
            if len(self.projects) == 1:
                return next(iter(self.projects.values()))
            if not self.projects:
                raise NotFound("No model is open.",
                               hint="Call project_new or project_open "
                                    "first.")
            raise InvalidArgument(
                "Several models are open; say which one with project_id.",
                hint="Open: " + ", ".join(
                    f"{h.id} ({h.project.name})"
                    for h in self.projects.values()))
        handle = self.projects.get(project_id)
        if handle is None:
            raise unknown("project_id", project_id, list(self.projects))
        return handle

    def close(self, project_id: str) -> ProjectHandle:
        handle = self.get(project_id)
        with self._registry_lock:
            self.projects.pop(handle.id, None)
        for res in handle.results.values():
            res.evict()
        return handle

    # ------------------------------------------------------------------
    @contextlib.contextmanager
    def _locked(self, handle: ProjectHandle, what: str):
        if not handle.lock.acquire(timeout=LOCK_TIMEOUT_S):
            since = time.time() - handle.busy_since
            raise Busy(f"Model {handle.id} is busy with "
                       f"{handle.busy_with or 'another operation'} "
                       f"({since:.0f} s).",
                       hint="Retry when it finishes.")
        outer = handle.busy_with is None
        if outer:
            handle.busy_with, handle.busy_since = what, time.time()
        try:
            yield handle.project
        finally:
            if outer:
                handle.busy_with = None
            handle.lock.release()

    @contextlib.contextmanager
    def reading(self, project_id: Optional[str], what: str = "a read"):
        """The model, under its lock, for the duration of the block."""
        handle = self.get(project_id)
        with self._locked(handle, what) as project:
            yield project

    def mutate(self, project_id: Optional[str], description: str,
               fn: Callable, attrs=None):
        """Run ``fn(project)`` as ONE undoable, all-or-nothing edit.

        Returns what ``fn`` returned. An edit that changes nothing leaves no
        undo step. Called from inside another mutation of the same model
        (a script calling an operation), it simply runs: the outer edit is
        the undo step.
        """
        from ogr_core.project.commands import LIGHT_ATTRS, SnapshotCommand

        handle = self.get(project_id)
        active = getattr(self._local, "active", None)
        if active is None:
            active = self._local.active = set()
        with self._locked(handle, description) as project:
            if handle.id in active:
                return fn(project)
            active.add(handle.id)
            try:
                cmd = SnapshotCommand(description, fn,
                                      attrs=attrs or LIGHT_ATTRS)
                cmd.execute(project)
                if cmd.changed:
                    handle.stack.record(cmd)
                return cmd.result
            finally:
                active.discard(handle.id)

    # ------------------------------------------------------------------
    def resolve_path(self, path: str, *, for_write: bool = False,
                     overwrite: bool = False,
                     suffix: Optional[str] = None,
                     own_file: Optional[Path] = None) -> Path:
        """An absolute path, checked for what the caller is about to do.

        Relative paths need a ``workdir``. Writing never replaces an
        existing file unless ``overwrite`` is true — except the model's
        own file, which is what "save" means.
        """
        if not isinstance(path, str) or not path.strip():
            raise InvalidArgument("A path must be a non-empty string.")
        p = Path(path.strip()).expanduser()
        if suffix and p.suffix.lower() != suffix:
            if p.suffix:
                raise InvalidArgument(
                    f"{p.name!r} does not end in {suffix}.")
            p = p.with_suffix(suffix)
        if not p.is_absolute():
            if self.workdir is None:
                raise InvalidArgument(
                    f"{path!r} is a relative path and no working directory "
                    f"was configured.",
                    hint="Pass an absolute path, or start the server with "
                         "--workdir.")
            p = self.workdir / p
        p = p.resolve()
        if for_write:
            if not p.parent.is_dir():
                raise InvalidArgument(f"The folder {p.parent} does not "
                                      f"exist.")
            same = own_file is not None and Path(own_file).resolve() == p
            if p.exists() and not overwrite and not same:
                raise Conflict(f"{p} already exists.",
                               hint="Pass overwrite=true to replace it.")
        elif not p.exists():
            raise NotFound(f"{p} does not exist.")
        return p

    # ------------------------------------------------------------------
    def store_result(self, handle: ProjectHandle, kind: str, summary: dict,
                     *, model_hash: str, loader=None, payload=None,
                     on_evict=None) -> StoredResult:
        """Keep a result under a new ``result_id``, evicting the oldest."""
        res = StoredResult(_new_id("r"), kind, handle.id, model_hash,
                           summary, loader=loader, payload=payload,
                           on_evict=on_evict)
        handle.results[res.id] = res
        while len(handle.results) > self.max_results_per_project:
            _, old = handle.results.popitem(last=False)
            old.evict()
        return res

    def find_result(self, result_id: str) -> tuple[ProjectHandle,
                                                   StoredResult]:
        known = []
        for handle in self.projects.values():
            if result_id in handle.results:
                return handle, handle.results[result_id]
            known.extend(handle.results)
        raise unknown("result_id", result_id, known)
