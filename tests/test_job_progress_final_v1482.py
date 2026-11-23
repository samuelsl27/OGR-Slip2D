# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.482 (D371) — a job's ``progress.json`` ends with its final update.

The defect: ``_write_progress`` renamed its temporary file over
``progress.json`` with a single try (v0.1.198, so that progress could never
kill an analysis). The parent reads that file at every poll, and Windows
refuses to rename over a file another process holds open (WinError 5): when
the last update met a poll, it was dropped and the folder of a finished job
said it was half way. ``test_api_jobs_v1194`` caught it now and then in a
loaded ``--jobs 4`` run; holding the file open on purpose reproduces it
every time.

What these tests protect:

* the final update (``done >= total``) waits for a reader that lets go
  within the retries, and lands;
* an intermediate update with the file held is still dropped at the first
  try, without waiting — the guarantee of v0.1.198;
* a final update whose reader never lets go returns ``False`` and does not
  raise.

On Linux renaming over an open file does not fail, so these cases only
discriminate on Windows; there they assert what is true on that platform
(the write lands at once, nothing waits).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path

_WINDOWS = os.name == "nt"


def _folder_at_one_of_five():
    from ogr_api.jobs.worker import _write_progress
    folder = Path(tempfile.mkdtemp(prefix="ogr_progress_"))
    assert _write_progress(folder, 1, 5) is True
    return folder


def _read(folder):
    return json.loads((folder / "progress.json").read_text(encoding="utf-8"))


class _CountingSleep:
    """Stands in for the worker's ``time.sleep``: counts, never sleeps."""

    def __init__(self):
        self.calls = 0

    def __call__(self, _seconds):
        self.calls += 1


def _with_sleep(counter, fn):
    from ogr_api.jobs import worker
    real = worker.time.sleep
    # the worker's module object ``time`` is the global one: patch the
    # attribute it looks up and put it back whatever happens (rule 5)
    worker.time.sleep = counter
    try:
        return fn()
    finally:
        worker.time.sleep = real


class TestTheFinalProgressUpdate:
    def test_it_waits_for_a_reader_that_lets_go(self):
        from ogr_api.jobs.worker import _write_progress
        folder = _folder_at_one_of_five()
        opened, release = threading.Event(), threading.Event()

        def reader():
            with open(folder / "progress.json", "r", encoding="utf-8"):
                opened.set()
                release.wait(0.1)    # the poll, holding the file ~100 ms

        t = threading.Thread(target=reader, daemon=True)
        try:
            t.start()
            assert opened.wait(5.0)
            assert _write_progress(folder, 5, 5) is True
            assert _read(folder) == {"done": 5, "total": 5, "fraction": 1.0}
        finally:
            release.set()
            t.join(5.0)
            shutil.rmtree(folder, ignore_errors=True)

    def test_it_gives_up_without_raising(self):
        from ogr_api.jobs.worker import _REPLACE_TRIES, _write_progress
        folder = _folder_at_one_of_five()
        sleeps = _CountingSleep()
        try:
            with open(folder / "progress.json", "r", encoding="utf-8"):
                wrote = _with_sleep(sleeps,
                                    lambda: _write_progress(folder, 5, 5))
            if _WINDOWS:
                assert wrote is False
                assert sleeps.calls == _REPLACE_TRIES - 1
                assert _read(folder)["done"] == 1
            else:
                assert wrote is True and sleeps.calls == 0
        finally:
            shutil.rmtree(folder, ignore_errors=True)


class TestAnIntermediateProgressUpdate:
    def test_it_is_dropped_without_waiting(self):
        from ogr_api.jobs.worker import _write_progress
        folder = _folder_at_one_of_five()
        sleeps = _CountingSleep()
        try:
            with open(folder / "progress.json", "r", encoding="utf-8"):
                wrote = _with_sleep(sleeps,
                                    lambda: _write_progress(folder, 3, 5))
            assert sleeps.calls == 0
            if _WINDOWS:
                assert wrote is False
                assert _read(folder)["done"] == 1
            else:
                assert wrote is True and _read(folder)["done"] == 3
        finally:
            shutil.rmtree(folder, ignore_errors=True)
