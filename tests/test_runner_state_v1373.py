# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.373 — the runner puts back, after every file, what a file leaves in
the process for every file after it, and freezes what survives the
collection it makes between files.

Invariants protected:

1. **``sys.path`` after a file is what it was before it.** 242 files insert
   ``tests/`` at import and nothing took it out: 369 entries at the end of
   the suite. Every ``spawn`` worker of a search pool gets that list and
   walks it with one ``stat`` per entry for each module it imports; a pool
   of 4 cost 0.5–0.7 s with 12 entries and 2.4–3.6 s with 369, measured A/B
   in one process (docs/audits/AUDITORIA_SUITE_v0.1.372.md §4.3). Inside its
   own file the insert is still seen: that is what the file asked for.
2. **The run's two folders** (``OGR_BRIDGE_DIR``, ``OGR_SETTINGS_DIR``) are
   put back too. Two runner self-tests repoint them through a second
   ``main()`` and left every later file in other folders (audit D-d).
3. **What survives the collection between files is frozen**
   (``gc.freeze``), so the next full collection walks only what was made
   since. Each one cost ~320 ns per live object, 3.4 s per file at the end
   of the suite: 13.6 of its 87.6 minutes (audit §3).

How: ``main()`` of a second copy of the runner over two throwaway test
files in a temporary folder. The first inserts a marker into ``sys.path``
at import, keeps 5000 lists alive and repoints ``OGR_SETTINGS_DIR`` in a
test; the second writes down what it sees. ``foreign_packages`` answers
``[]`` on that copy only: the folder is not the tree, and that check is
not what is tested here. Run against the runner of 0.1.372 these three
invariants fail (checked when they were written).

A trap, as in ``test_runner_selection_v180``: the inner ``main()`` runs only
the throwaway folder, never ``tests/``, or this file would run itself.
"""
from __future__ import annotations

import contextlib
import gc
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_FOLDERS = ("OGR_BRIDGE_DIR", "OGR_SETTINGS_DIR")

_FIRST = '''
import gc, json, os, sys
OUT = {out!r}
MARK = {mark!r}
sys.path.insert(0, MARK)
KEEP = [[] for _ in range(5000)]          # alive, tracked: frozen next
with open(OUT + ".a.json", "w") as fh:
    json.dump({{"settings": os.environ.get("OGR_SETTINGS_DIR"),
               "frozen": gc.get_freeze_count()}}, fh)


class TestFirst:
    def test_its_own_insert_is_seen(self):
        assert MARK in sys.path

    def test_repoints_the_settings(self):
        os.environ["OGR_SETTINGS_DIR"] = MARK
'''

_SECOND = '''
import gc, json, os, sys
OUT = {out!r}
MARK = {mark!r}


class TestSecond:
    def test_writes_what_it_sees(self):
        with open(OUT + ".b.json", "w") as fh:
            json.dump({{"mark": MARK in sys.path,
                       "settings": os.environ.get("OGR_SETTINGS_DIR"),
                       "frozen": gc.get_freeze_count()}}, fh)
'''


def _load_runner(path: Path = _TESTS / "_runner.py"):
    """The runner as a module of its own; the fake ``pytest`` it installs
    is put back (rule 5), as in ``test_runner_selection_v180``."""
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_state_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


_SEEN: dict = {}


def _seen(runner_path: Path = _TESTS / "_runner.py") -> dict:
    """Run the two throwaway files once, return what they wrote down."""
    if runner_path in _SEEN:
        return _SEEN[runner_path]
    runner = _load_runner(runner_path)
    runner.foreign_packages = lambda origins, root: []
    folder = Path(tempfile.mkdtemp(prefix="ogr_test_runner_state_"))
    out = str(folder / "seen")
    mark = str(folder / "not-a-folder-on-the-path")
    (folder / "test_a_leaves.py").write_text(
        _FIRST.format(out=out, mark=mark), encoding="utf-8")
    (folder / "test_b_records.py").write_text(
        _SECOND.format(out=out, mark=mark), encoding="utf-8")
    saved_path = list(sys.path)
    saved_env = {v: os.environ.get(v) for v in _FOLDERS}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = runner.main(folder)
        with open(out + ".a.json") as fh:
            a = json.load(fh)
        with open(out + ".b.json") as fh:
            b = json.load(fh)
    finally:
        # Rule 5: the inner main() set the run's folders of its own.
        sys.path[:] = saved_path
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        # the modules the inner run imported by their stems
        for stem in ("test_a_leaves", "test_b_records"):
            sys.modules.pop(stem, None)
        shutil.rmtree(folder, ignore_errors=True)
    _SEEN[runner_path] = {"code": code, "text": buf.getvalue(), "a": a,
                          "b": b, "mark": mark}
    return _SEEN[runner_path]


class TestWhatAFileLeavesIsPutBack:
    def test_the_inner_run_passed(self):
        s = _seen()
        assert s["code"] == 0, s["text"]
        assert "Passed: 3" in s["text"], s["text"]

    def test_its_sys_path_insert_does_not_reach_the_next_file(self):
        assert _seen()["b"]["mark"] is False

    def test_the_settings_folder_is_the_runs_again(self):
        s = _seen()
        assert s["a"]["settings"] is not None
        assert s["b"]["settings"] == s["a"]["settings"]
        assert s["b"]["settings"] != s["mark"]


class TestWhatSurvivesIsFrozen:
    def test_the_lists_kept_by_the_first_file_are_frozen_before_the_second(self):
        s = _seen()
        # 5000 lists made after the freeze that preceded the first file,
        # still alive: the collection before the second file froze them.
        assert s["b"]["frozen"] >= s["a"]["frozen"] + 5000, (s["a"], s["b"])

    def test_the_loop_collects_then_freezes(self):
        src = (_TESTS / "_runner.py").read_text(encoding="utf-8")
        loop = src[src.index("for i_file, f in enumerate(test_files, 1):"):]
        loop = loop[:loop.index('print(f"\\n=== {f.name}')]
        # collected first: the previous file's garbage is still freed
        assert loop.index("gc.collect()") < loop.index("gc.freeze()")
        assert "gc_guard.release()" in loop
