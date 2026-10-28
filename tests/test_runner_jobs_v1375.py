# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.375 — ``python tests/_runner.py --jobs N``: the selection in N
processes at once, without losing what the serial run catches.

Invariants protected:

1. **The same files, the same tests, the same verdict** as the serial run
   of the same folder, printed in the same order, each file once, with the
   progress counted over the whole run.
2. **Contiguous chunks**: each process runs a piece of the alphabetical
   order (a file keeps its serial neighbours except at the borders), and
   :func:`partition` makes the heaviest piece as light as it can be.
3. **The leaks injected in the suite audit fail the file that leaves
   them**, inside a chunk as in a serial run (``Leaks: 4``, code 1; the file
   that puts everything back is not named).
4. **A chunk that dies is a failure, never a shorter green run**: a file
   that calls ``os._exit(3)`` in its second test fails the run, named with
   its exit code, the file it died in, the file before it and how many of
   its chunk's files did not finish; the other chunks still report.
5. **The run is the run declared**: tests run that the source does not
   declare (a method inherited from a class that is not a ``Test`` class)
   fail it, with the two numbers.
6. **The serial lane**: a file with ``SERIAL_LANE = True`` runs alone,
   after every chunk has ended, in a process of its own; the marker is read
   from the source without running it.
7. **Durations**: kept for the runner's own folder only, merged, never for
   throwaway files.

How: ``main()`` of a second copy of the runner over throwaway files, as
``test_runner_state_v1373`` does. The chunks are real processes running the
real runner; what their files leave stays in them.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import itertools
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_leaks_v1374 import _FILES as _LEAKY  # noqa: E402

_TESTS = Path(__file__).resolve().parent
_FOLDERS = ("OGR_BRIDGE_DIR", "OGR_SETTINGS_DIR")
_OUT = "OGR_TEST_JOBS_OUT_V1375"

_MARK = '''
import json
import os
import time


def _mark(name):
    out = os.environ[{out!r}]
    with open(os.path.join(out, name + ".json"), "w") as fh:
        json.dump({{"pid": os.getpid(), "t": time.time()}}, fh)
'''.format(out=_OUT)

#: Six files, one in the serial lane; "b" has three tests and "e" four, so
#: that the chunks are uneven by file and even by test.
_CLEAN = {
    "test_a_one.py": _MARK + '''

class TestA:
    def test_a1(self):
        _mark("a1")
''',
    "test_b_three.py": _MARK + '''

class TestB:
    def test_b1(self):
        _mark("b1")

    def test_b2(self):
        _mark("b2")

    def test_b3(self):
        _mark("b3")
''',
    "test_c_clock.py": _MARK + '''
SERIAL_LANE = True


class TestC:
    def test_c1(self):
        _mark("c1")
''',
    "test_d_one.py": _MARK + '''

class TestD:
    def test_d1(self):
        _mark("d1")
''',
    "test_e_four.py": _MARK + '''

class TestE:
    def test_e1(self):
        _mark("e1")

    def test_e2(self):
        _mark("e2")

    def test_e3(self):
        _mark("e3")

    def test_e4(self):
        _mark("e4")
''',
    "test_f_one.py": _MARK + '''

class TestF:
    def test_f1(self):
        _mark("f1")
''',
}

#: Weights 1, 2, 1, 1, 5 by test count: two chunks, [a b c d] and [e], and
#: b dies in its second test with c and d still to run in its chunk.
_DYING = {
    "test_a_ok.py": "class TestA:\n    def test_a(self):\n        pass\n",
    "test_b_dies.py": '''
import os


class TestB:
    def test_b1_passes(self):
        pass

    def test_b2_exits(self):
        os._exit(3)
''',
    "test_c_after.py": "class TestC:\n    def test_c(self):\n        pass\n",
    "test_d_after.py": "class TestD:\n    def test_d(self):\n        pass\n",
    "test_e_other.py": "class TestE:\n" + "".join(
        f"    def test_e{i}(self):\n        pass\n\n" for i in range(5)),
}

#: One test the source declares, two that run: ``_Base.test_inherited`` is
#: not in the body of a ``Test`` class, and runs in ``TestA``.
_UNDECLARED = {
    "test_a_inherits.py": '''
class _Base:
    def test_inherited(self):
        pass


class TestA(_Base):
    def test_own(self):
        pass
''',
    "test_b_plain.py": "class TestB:\n    def test_b(self):\n        pass\n",
}


def _load_runner():
    """The runner as a module of its own; the fake ``pytest`` it installs
    is put back (rule 5), as in ``test_runner_selection_v180``."""
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_jobs_under_test", _TESTS / "_runner.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


def _run(files: dict, **kw) -> dict:
    """``main()`` of a copy of the runner over ``files`` written to a fresh
    folder: ``{"code", "text", "by_file", "marks"}``. Everything the run
    sets in this process is put back here."""
    runner = _load_runner()
    runner.foreign_packages = lambda origins, root: []
    folder = Path(tempfile.mkdtemp(prefix="ogr_test_jobs_files_"))
    out = Path(tempfile.mkdtemp(prefix="ogr_test_jobs_marks_"))
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    saved_path = list(sys.path)
    saved_env = {v: os.environ.get(v) for v in (*_FOLDERS, _OUT)}
    os.environ[_OUT] = str(out)
    durations = (runner.DURATIONS.read_bytes()
                 if runner.DURATIONS.exists() else None)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = runner.main(folder, **kw)
        marks = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                 for p in out.glob("*.json")}
    finally:
        sys.path[:] = saved_path
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        for name in files:
            sys.modules.pop(name[:-3], None)
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)
    text = buf.getvalue()
    # A chunk that died keeps its logs for whoever reads the message.
    for kept in re.findall(r"\(log: (.+?)[\\/]log_\d+\.txt\)", text):
        shutil.rmtree(kept, ignore_errors=True)
    by_file = dict(re.findall(r"=== (\S+) ===[^\n]*\n(.*?)(?=\n=== |\n=+\n)",
                              text, flags=re.S))
    after = (runner.DURATIONS.read_bytes()
             if runner.DURATIONS.exists() else None)
    return {"code": code, "text": text, "by_file": by_file, "marks": marks,
            "durations_untouched": after == durations}


_RUNS: dict = {}


def _once(key: str, files: dict, **kw) -> dict:
    if key not in _RUNS:
        _RUNS[key] = _run(files, **kw)
    return _RUNS[key]


def _serial():
    return _once("serial", _CLEAN)


def _jobs():
    return _once("jobs", _CLEAN, jobs=3)


def _totals(text: str) -> str:
    return next(line for line in text.splitlines()
                if line.startswith("Total:"))


class TestTheSameRunAsTheSerialOne:
    def test_both_pass(self):
        assert _serial()["code"] == 0, _serial()["text"]
        assert _jobs()["code"] == 0, _jobs()["text"]

    def test_the_same_totals(self):
        assert _totals(_jobs()["text"]) == _totals(_serial()["text"]) == \
            "Total: 11    Passed: 11    Failed: 0"

    def test_every_file_once_in_order_and_the_lane_last(self):
        heads = re.findall(r"=== (\S+) ===", _jobs()["text"])
        assert heads == ["test_a_one.py", "test_b_three.py", "test_d_one.py",
                         "test_e_four.py", "test_f_one.py", "test_c_clock.py"]

    def test_the_progress_is_counted_over_the_whole_run(self):
        tags = re.findall(r"\[\s*(\d+)/(\d+)\s+\d+%\]", _jobs()["text"])
        assert [int(a) for a, _ in tags] == list(range(1, 12))
        assert {b for _, b in tags} == {"11"}

    def test_it_ends_saying_when_the_serial_run_is_due(self):
        # v0.1.376 — the owner adopted the run in chunks for releases, with
        # the serial run once every SERIAL_EVERY commits: the line that said
        # a release still needed the serial run is now that count
        # (test_runner_fast_v1376).
        text = _jobs()["text"]
        assert "a release still needs the serial run" not in text
        assert re.search(r"^(SERIAL RUN DUE — |last full serial run: )",
                         text, flags=re.M)


class TestTheChunks:
    def test_three_processes_each_a_contiguous_piece(self):
        m = _jobs()["marks"]
        order = ["a1", "b1", "b2", "b3", "d1", "e1", "e2", "e3", "e4", "f1"]
        pids = [m[k]["pid"] for k in order]
        runs = [p for p, _ in itertools.groupby(pids)]
        assert len(runs) == len(set(runs)) == 3, pids
        assert os.getpid() not in pids

    def test_the_lane_runs_alone_after_every_chunk(self):
        m = _jobs()["marks"]
        lane = m["c1"]
        others = [v for k, v in m.items() if k != "c1"]
        assert lane["pid"] not in {v["pid"] for v in others}
        assert lane["t"] > max(v["t"] for v in others)

    def test_the_serial_run_is_one_process_this_one(self):
        assert {v["pid"] for v in _serial()["marks"].values()} == {os.getpid()}


class TestPartition:
    def _best(self, weights, n):
        """The lightest heaviest slice, by trying every set of borders."""
        best = None
        for cuts in itertools.combinations(range(1, len(weights)), n - 1):
            edges = (0, *cuts, len(weights))
            heaviest = max(sum(weights[a:b]) for a, b in zip(edges, edges[1:]))
            best = heaviest if best is None else min(best, heaviest)
        return best

    def test_contiguous_covering_and_optimal(self):
        runner = _load_runner()
        cases = [([5, 1, 1, 1, 1, 1], 2), ([1, 2, 3, 4, 5, 6, 7], 3),
                 ([3, 3, 3, 3], 4), ([9, 1, 9, 1, 9], 3),
                 ([0.4, 7.1, 0.2, 0.2, 3.3, 2.9, 1.0, 5.5], 3)]
        for weights, n in cases:
            parts = runner.partition(weights, n)
            assert parts[0][0] == 0 and parts[-1][1] == len(weights)
            assert all(a < b for a, b in parts)
            assert all(p[1] == q[0] for p, q in zip(parts, parts[1:]))
            heaviest = max(sum(weights[a:b]) for a, b in parts)
            assert abs(heaviest - self._best(weights, n)) < 1e-6, (weights, n)

    def test_as_many_chunks_as_asked_without_a_heavier_one(self):
        runner = _load_runner()
        # the greedy fill at the best capacity (5) packs these into two
        weights = [1, 3, 1, 4, 1]
        parts = runner.partition(weights, 3)
        assert len(parts) == 3
        assert max(sum(weights[a:b]) for a, b in parts) == 5

    def test_more_processes_than_files(self):
        runner = _load_runner()
        assert runner.partition([2, 1], 8) == [(0, 1), (1, 2)]
        assert runner.partition([], 4) == []

    def test_a_file_never_timed_costs_its_tests_at_the_median_rate(self):
        runner = _load_runner()
        files = [Path("test_x.py"), Path("test_y.py"), Path("test_z.py")]
        counts = {"test_x.py": 10, "test_y.py": 4, "test_z.py": 2}
        w = runner.file_weights(files, counts, {"test_x.py": 20.0,
                                                "test_y.py": 4.0})
        # rates 2.0 and 1.0: the median of two is the upper one
        assert w == [20.0, 4.0, 4.0]


class TestTheLaneMarker:
    def test_read_from_the_source_without_running_it(self):
        runner = _load_runner()
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_jobs_lane_"))
        try:
            cases = {"yes": "SERIAL_LANE = True\nraise SystemExit(9)\n",
                     "no": "SERIAL_LANE = False\n",
                     "computed": "SERIAL_LANE = bool(1)\n",
                     "absent": "X = 1\n",
                     "broken": "SERIAL_LANE = True\ndef (:\n"}
            seen = {}
            for name, text in cases.items():
                p = folder / f"test_{name}.py"
                p.write_text(text, encoding="utf-8")
                seen[name] = runner.serial_lane(p)
            assert seen == {"yes": True, "no": False, "computed": False,
                            "absent": False, "broken": False}
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_the_three_clock_files_are_marked(self):
        runner = _load_runner()
        marked = sorted(p.name for p in _TESTS.glob("test_*.py")
                        if runner.serial_lane(p))
        assert marked == ["test_jobs_file_race_v1198.py",
                          "test_optimizations_v111.py",
                          "test_remote_oauth_v1204.py"]


class TestTheInjectedLeaksFailTheirFileInAChunk:
    def _leaks_of(self, name):
        run = _once("leaks", _LEAKY, jobs=2)
        return [line.split("[LEAK] ", 1)[1]
                for line in run["by_file"][name].splitlines()
                if "✗ [LEAK]" in line]

    def test_each_leak_under_its_own_file(self):
        assert any(x.startswith("env:OGR_TEST_INJECTED_LEAK_V1374:")
                   for x in self._leaks_of("test_b_environment.py"))
        assert any("_PARALLEL_MIN_CIRCLES: 400 → 1" in x
                   for x in self._leaks_of("test_c_constant.py"))
        assert any(x.startswith("cls:ogr_slip2d.search.GridSearch._centres")
                   for x in self._leaks_of("test_d_method.py"))
        assert self._leaks_of("test_a_language.py")
        assert self._leaks_of("test_e_puts_back.py") == []

    def test_the_run_fails_as_the_serial_one_does(self):
        run = _once("leaks", _LEAKY, jobs=2)
        assert run["code"] == 1
        assert _totals(run["text"]) == \
            "Total: 5    Passed: 5    Failed: 0    Leaks: 4"


class TestAChunkThatDiesFailsTheRun:
    def _run(self):
        return _once("dying", _DYING, jobs=2)

    def test_named_with_its_code_its_file_and_what_did_not_finish(self):
        run = self._run()
        assert run["code"] == 1
        line = next(x for x in run["text"].splitlines()
                    if x.startswith("✗ [CHUNK]"))
        assert "chunk 1/2 died: exit 3 in test_b_dies.py, after " \
               "test_a_ok.py; 3 of its 4 file(s) did not finish" in line

    def test_the_other_chunk_still_reports(self):
        run = self._run()
        assert "test_e_other.py" in run["by_file"]
        assert _totals(run["text"]) == \
            "Total: 6    Passed: 6    Failed: 0    Chunks died: 1"

    def test_the_files_after_it_never_ran(self):
        heads = re.findall(r"=== (\S+) ===", self._run()["text"])
        assert "test_c_after.py" not in heads
        assert "test_d_after.py" not in heads


class TestTheRunIsTheRunDeclared:
    def test_a_test_the_source_does_not_declare_fails_it(self):
        run = _once("undeclared", _UNDECLARED, jobs=2)
        assert run["code"] == 1
        assert "the source declares 2 test(s) and the chunks ran 3" \
            in run["text"]


class TestDurations:
    def test_a_throwaway_folder_writes_none(self):
        assert _jobs()["durations_untouched"]
        assert _serial()["durations_untouched"]

    def test_merged_into_what_was_there(self):
        runner = _load_runner()
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_jobs_durations_"))
        try:
            path = folder / "d.json"
            runner.save_durations({"test_a.py": 1.23456}, path)
            runner.save_durations({"test_b.py": 2.0}, path)
            runner.save_durations({"test_a.py": 3.0}, path)
            assert runner.load_durations(path) == {"test_a.py": 3.0,
                                                   "test_b.py": 2.0}
            assert runner.load_durations(folder / "absent.json") == {}
        finally:
            shutil.rmtree(folder, ignore_errors=True)
