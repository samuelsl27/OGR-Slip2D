# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.376 — what a release needs and what development runs: ``--fast``,
the slow list, each test's time, and the serial run every 100 commits.

Invariants protected:

1. **``--fast`` leaves out exactly the listed files** of the selection, in
   series and in chunks, with the same result in both, and says so before
   and after the totals as any filtered run does. Whole files: their tests
   share what is expensive, and leaving out one test moved its cost to the
   next (the first list went by test, and took 19.3 min instead of 11).
2. **``--fast`` never does nothing** (rule 7): with no list, or with every
   selected file in it, it stops with code 2 instead of running the whole
   selection under a FILTERED banner.
3. **The list is written on purpose, from measured times**: the files of the
   folder that took the threshold or more, in order, with the licence lines,
   read back as written; never a file the folder no longer has; nothing when
   there are no times, nor from a filtered command. The real
   ``tests/_slow.txt`` names only files that exist (a stale entry would leave
   out nothing).
4. **Times are kept for the runner's own folder**: each test's under any
   filter, each file's without ``-k``; a whole run names the slow files the
   list leaves in.
5. **The serial run is remembered only when it is the whole suite and
   green**, by the commit it ran at; a whole run in chunks ends saying how
   many commits ago that was, and ``SERIAL RUN DUE`` from the owner's
   number on, or when it cannot be told.
6. **The owner's number is one number**: ``SERIAL_EVERY`` and AGENTS.md say
   the same.
7. **A test of the runner never writes the machine's own files** (durations,
   times, serial record, slow list).

How: ``main()`` of a copy of the runner over throwaway files, as
``test_runner_jobs_v1375`` does. For invariants 3 to 5 the copy is loaded
from the throwaway folder itself, the ``tests/`` of a throwaway git
repository, so that the folder is the runner's own and it writes what it
writes for the real suite — to files of the test's, pointed at by patching
the copy.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402  (the runner's own)

from test_runner_jobs_v1375 import (  # noqa: E402
    _CLEAN, _OUT, _load_runner, _totals,
)

_TESTS = Path(__file__).resolve().parent
_FOLDERS = ("OGR_BRIDGE_DIR", "OGR_SETTINGS_DIR")
#: The project's two licence lines, as this file opens with them: the licence
#: test reads every identifier quoted in the sources, so they are not quoted.
_LICENCE = Path(__file__).read_text(encoding="utf-8").splitlines()[:2]
_REAL = [Path(tempfile.gettempdir()) / n for n in (
    "ogr-slip2d-test-durations.json", "ogr-slip2d-test-times.json",
    "ogr-slip2d-serial-run.json")] + [_TESTS / "_slow.txt"]

#: Two of the six files of ``_CLEAN`` (seven of its eleven tests), and one
#: file that is not there.
_SLOW = ("test_b_three.py\n"
         "test_e_four.py  # 52 s, 4 tests\n"
         "# a comment line\n"
         "\n"
         "test_zz_gone.py\n")

#: One file that takes a measurable while, for the times and the list.
_TIMED = {
    "test_a_quick.py": "class TestA:\n    def test_a1(self):\n        pass\n\n"
                       "    def test_a2(self):\n        pass\n",
    "test_b_sleeps.py": '''
import time


class TestB:
    def test_b_quick(self):
        pass

    def test_b_sleeps(self):
        time.sleep(0.6)
''',
}


def _bytes(p: Path):
    return p.read_bytes() if p.exists() else None


def _main(runner, folder: Path, files: dict, patch: dict | None = None,
          **kw) -> dict:
    """``runner.main(folder)`` over ``files`` written into ``folder``, with
    ``patch`` set on the runner first: ``{"code", "text", "marks"}``.
    Everything the run sets in this process is put back here."""
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    runner.foreign_packages = lambda origins, root: []
    for attr, value in (patch or {}).items():
        setattr(runner, attr, value)
    out = Path(tempfile.mkdtemp(prefix="ogr_test_fast_marks_"))
    saved_path = list(sys.path)
    saved_env = {v: os.environ.get(v) for v in (*_FOLDERS, _OUT)}
    os.environ[_OUT] = str(out)
    real = [_bytes(p) for p in _REAL]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = runner.main(folder, **kw)
        marks = {p.stem for p in out.glob("*.json")}
    finally:
        sys.path[:] = saved_path
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        for name in files:
            sys.modules.pop(name[:-3], None)
        shutil.rmtree(out, ignore_errors=True)
    text = buf.getvalue()
    for kept in re.findall(r"\(log: (.+?)[\\/]log_\d+\.txt\)", text):
        shutil.rmtree(kept, ignore_errors=True)
    assert [_bytes(p) for p in _REAL] == real, "a machine file was written"
    return {"code": code, "text": text, "marks": marks}


def _throwaway(files: dict, patch: dict | None = None, **kw) -> dict:
    """A run of the runner in ``tests/`` over a fresh folder: not its own."""
    folder = Path(tempfile.mkdtemp(prefix="ogr_test_fast_files_"))
    try:
        return _main(_load_runner(), folder, files, patch, **kw)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _git(cwd: Path, *args) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    try:
        out = subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                             cwd=cwd, env=env, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=60)
    except OSError:
        pytest.skip("no git on this system")
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def _repo(commits: int) -> tuple[Path, list]:
    """A throwaway git repository with ``commits`` empty commits, and their
    hashes, oldest first."""
    root = Path(tempfile.mkdtemp(prefix="ogr_test_fast_repo_")).resolve()
    _git(root, "init", "-q")
    shas = []
    for i in range(commits):
        _git(root, "commit", "-q", "--allow-empty", "-m", f"c{i}")
        shas.append(_git(root, "rev-parse", "HEAD"))
    return root, shas


class _Own:
    """The runner copied into ``tests/`` of a throwaway repository and run
    from there, its machine files pointed at the test's own."""

    def __init__(self):
        self.root, self.shas = _repo(1)
        self.tests = self.root / "tests"
        self.tests.mkdir()
        for name in ("_runner.py", "_leaks.py"):
            shutil.copy(_TESTS / name, self.tests / name)
        self.files = {"DURATIONS": self.root / "durations.json",
                      "TEST_TIMES": self.root / "times.json",
                      "SERIAL_RECORD": self.root / "serial.json"}

    def run(self, files: dict, **kw) -> dict:
        saved = sys.modules.get("pytest")
        try:
            spec = importlib.util.spec_from_file_location(
                "_ogr_runner_fast_under_test", self.tests / "_runner.py")
            runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runner)
        finally:
            if saved is not None:
                sys.modules["pytest"] = saved
            else:
                sys.modules.pop("pytest", None)
        assert runner.SLOW_LIST == self.tests / "_slow.txt"
        # A whole run names the files of twice this: 0.3 s, which the file
        # that sleeps 0.6 s passes and a file of two empty tests does not.
        return _main(runner, self.tests, files,
                     {**self.files, "SLOW_SECONDS": 0.15}, **kw)

    def read(self, key: str):
        return _load_runner().load_durations(self.files[key])


_RUNS: dict = {}


def _once(key, make):
    if key not in _RUNS:
        _RUNS[key] = make()
    return _RUNS[key]


def _chain() -> dict:
    """In one repository: a whole serial run, the list written from its
    times, then a --fast run with that list."""
    def make():
        own = _Own()
        out = {"own": own, "whole": own.run(_TIMED)}
        out["write"] = own.run({}, write_slow=0.3)
        out["list"] = (own.tests / "_slow.txt").read_text(encoding="utf-8")
        out["after_whole"] = {k: _bytes(p) for k, p in own.files.items()}
        out["times_whole"] = own.read("TEST_TIMES")
        out["durations_whole"] = own.read("DURATIONS")
        # Gone before the --fast run, to see what it writes back: an empty
        # test can time 0.000 s twice, and equal bytes would prove nothing.
        own.files["TEST_TIMES"].unlink()
        own.files["DURATIONS"].unlink()
        out["fast"] = own.run({}, fast=True)
        out["after_fast"] = {k: _bytes(p) for k, p in own.files.items()}
        return out
    return _once("chain", make)


def _slow_list_file() -> Path:
    def make():
        p = Path(tempfile.mkdtemp(prefix="ogr_test_fast_list_")) / "_slow.txt"
        p.write_text(_SLOW, encoding="utf-8")
        return p
    return _once("list", make)


def _fast(jobs: int) -> dict:
    return _once(f"fast{jobs}", lambda: _throwaway(
        _CLEAN, {"SLOW_LIST": _slow_list_file()}, fast=True, jobs=jobs))


class TestFastLeavesOutTheListedFiles:
    def test_in_series(self):
        run = _fast(1)
        assert run["code"] == 0, run["text"]
        assert _totals(run["text"]) == "Total: 4    Passed: 4    Failed: 0"
        assert run["marks"] == {"a1", "c1", "d1", "f1"}

    def test_in_chunks_as_in_series(self):
        run = _fast(3)
        assert run["code"] == 0, run["text"]
        assert "[CHUNK]" not in run["text"]
        assert _totals(run["text"]) == "Total: 4    Passed: 4    Failed: 0"
        assert run["marks"] == _fast(1)["marks"]

    def test_only_the_files_left_run(self):
        for jobs in (1, 3):
            heads = re.findall(r"=== (\S+) ===", _fast(jobs)["text"])
            assert sorted(heads) == ["test_a_one.py", "test_c_clock.py",
                                     "test_d_one.py", "test_f_one.py"]

    def test_said_before_and_after_the_totals(self):
        for jobs in (1, 3):
            text = _fast(jobs)["text"]
            lines = [x for x in text.splitlines()
                     if x.startswith("FILTERED RUN")]
            assert len(lines) == 2, text
            # two of the selection: the entry of a file not there is not one
            assert lines[0].startswith("FILTERED RUN — 4 of 6 files, --fast: "
                                       "2 slow file(s) left out "
                                       "(tests/_slow.txt)"), lines[0]
            total_at = text.index("\nTotal:")
            assert text.index(lines[0]) < total_at < text.rindex(lines[1])

    def test_listed_without_them(self):
        run = _throwaway(_CLEAN, {"SLOW_LIST": _slow_list_file()},
                         fast=True, list_only=True)
        assert run["code"] == 0
        listed = re.findall(r"^(test_[^:\s]+)::", run["text"], flags=re.M)
        assert sorted(set(listed)) == ["test_a_one.py", "test_c_clock.py",
                                       "test_d_one.py", "test_f_one.py"]


class TestFastNeverDoesNothing:
    def test_without_a_list(self):
        absent = Path(tempfile.gettempdir()) / "ogr_test_fast_no_such_list.txt"
        run = _throwaway(_CLEAN, {"SLOW_LIST": absent}, fast=True)
        assert run["code"] == 2
        assert "--fast has nothing to leave out" in run["text"]
        assert "Total:" not in run["text"]

    def test_with_every_selected_file_in_it(self):
        run = _throwaway(_CLEAN, {"SLOW_LIST": _slow_list_file()},
                         patterns=["test_b_three", "test_d_one"], fast=True)
        assert run["code"] == 0, run["text"]
        assert _totals(run["text"]) == "Total: 1    Passed: 1    Failed: 0"
        run = _throwaway(_CLEAN, {"SLOW_LIST": _slow_list_file()},
                         patterns=["test_b_three", "test_e_four"], fast=True)
        assert run["code"] == 2
        assert "--fast leaves nothing to run" in run["text"]
        assert "Total:" not in run["text"]


class TestTheList:
    def test_written_from_the_times(self):
        c = _chain()
        assert c["write"]["code"] == 0, c["write"]["text"]
        listed = [line.split("#", 1)[0].strip()
                  for line in c["list"].splitlines()
                  if line.split("#", 1)[0].strip()]
        assert listed == ["test_b_sleeps.py"]
        assert re.search(r"^test_b_sleeps\.py  # \d+ s, 2 tests$",
                         c["list"], flags=re.M)
        assert "1 file(s) of 0.3 s or more written to" in c["write"]["text"]

    def test_with_its_licence_and_what_it_is(self):
        head = _chain()["list"].splitlines()
        assert head[:2] == _LICENCE
        assert any("--write-slow-list 0.3" in x for x in head)

    def test_read_back_as_written(self):
        runner = _load_runner()
        own = _chain()["own"]
        assert runner.load_slow_list(own.tests / "_slow.txt") == {
            "test_b_sleeps.py"}
        assert runner.load_slow_list(_slow_list_file()) == {
            "test_b_three.py", "test_e_four.py", "test_zz_gone.py"}

    def test_never_a_file_the_folder_does_not_have(self):
        runner = _load_runner()
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_fast_write_"))
        try:
            (folder / "test_x.py").write_text(
                "class TestX:\n    def test_kept(self):\n        pass\n",
                encoding="utf-8")
            (folder / "test_y.py").write_text(
                "class TestY:\n    def test_y(self):\n        pass\n",
                encoding="utf-8")
            durations = folder / "durations.json"
            runner.save_durations({"test_x.py": 50.0, "test_y.py": 44.9,
                                   "test_gone.py": 90.0}, durations)
            out = folder / "_slow.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                assert runner.write_slow_list(folder, 45.0, durations,
                                              out) == 0
            assert runner.load_slow_list(out) == {"test_x.py"}
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_nothing_without_times(self):
        runner = _load_runner()
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_fast_write_"))
        try:
            (folder / "test_x.py").write_text(
                "class TestX:\n    def test_x(self):\n        pass\n",
                encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = runner.write_slow_list(folder, 45.0,
                                              folder / "none.json",
                                              folder / "_slow.txt")
            assert code == 2
            assert "run the whole suite first" in buf.getvalue()
            assert not (folder / "_slow.txt").exists()
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_written_for_the_whole_folder_only(self):
        run = _throwaway(_CLEAN, None, patterns=["test_a"], write_slow=45.0)
        assert run["code"] == 2
        assert "takes no patterns" in run["text"]

    def test_the_real_list_names_only_files_that_exist(self):
        runner = _load_runner()
        listed = runner.load_slow_list()
        assert listed, "tests/_slow.txt is missing or empty"
        present = {p.name for p in _TESTS.glob("test_*.py")}
        assert sorted(listed - present) == []
        assert runner.SLOW_LIST.read_text(
            encoding="utf-8").splitlines()[:2] == _LICENCE


class TestTheTimes:
    def test_each_test_of_a_whole_run(self):
        c = _chain()
        assert c["whole"]["code"] == 0, c["whole"]["text"]
        times = c["times_whole"]
        assert set(times) == {"test_a_quick.py::TestA::test_a1",
                              "test_a_quick.py::TestA::test_a2",
                              "test_b_sleeps.py::TestB::test_b_quick",
                              "test_b_sleeps.py::TestB::test_b_sleeps"}
        assert times["test_b_sleeps.py::TestB::test_b_sleeps"] >= 0.59

    def test_and_each_file(self):
        assert set(_chain()["durations_whole"]) == {
            "test_a_quick.py", "test_b_sleeps.py"}

    def test_a_fast_run_writes_both_for_what_it_ran(self):
        c = _chain()
        assert c["fast"]["code"] == 0, c["fast"]["text"]
        assert _totals(c["fast"]["text"]) == \
            "Total: 2    Passed: 2    Failed: 0"
        assert set(c["own"].read("TEST_TIMES")) == {
            "test_a_quick.py::TestA::test_a1",
            "test_a_quick.py::TestA::test_a2"}
        assert set(c["own"].read("DURATIONS")) == {"test_a_quick.py"}

    def test_a_whole_run_names_the_slow_files_the_list_leaves_in(self):
        text = _chain()["whole"]["text"]
        assert ("SLOW, NOT IN tests/_slow.txt — 1 file(s) took 0.3 s or more "
                "and --fast still runs them:") in text
        assert re.search(r"^  test_b_sleeps\.py  \d+\.\d s$", text,
                         flags=re.M)

    def test_slowest_first_and_only_the_unlisted(self):
        runner = _load_runner()
        times = {"a": 120.0, "b": 30.0, "c": 200.0, "d": 150.0}
        assert runner.slow_unlisted(times, {"c"}, 90.0) == [("d", 150.0),
                                                           ("a", 120.0)]


class TestTheSerialRecord:
    def test_a_whole_green_serial_run_records_its_commit(self):
        c = _chain()
        rec = _load_runner()._read_json(c["own"].files["SERIAL_RECORD"])
        assert rec["commit"] == c["own"].shas[-1]
        assert rec["tests"] == 4
        assert (f"full serial run recorded: {c['own'].shas[-1][:7]}; the next "
                f"is due in 100 commits") in c["whole"]["text"]

    def test_a_filtered_run_does_not(self):
        c = _chain()
        assert c["after_fast"]["SERIAL_RECORD"] == \
            c["after_whole"]["SERIAL_RECORD"]
        assert "recorded" not in c["fast"]["text"]

    def test_a_red_run_does_not(self):
        def make():
            own = _Own()
            run = own.run({"test_a_fails.py": "class TestA:\n    def test_a(self)"
                           ":\n        assert False\n"})
            return own, run
        own, run = _once("red", make)
        assert run["code"] == 1
        assert not own.files["SERIAL_RECORD"].exists()
        assert "recorded" not in run["text"]


class TestTheSerialNotice:
    def _repo(self):
        return _once("repo3", lambda: _repo(3))

    def _notice(self, record, every=None) -> str:
        runner = _load_runner()
        root, _shas = self._repo()
        path = root / "record.json"
        if record is None:
            path.unlink(missing_ok=True)
        else:
            runner._write_json(path, record)
        return runner.serial_notice(root, path, every)

    def test_none_recorded_is_due(self):
        assert self._notice(None).startswith(
            "SERIAL RUN DUE — no full serial run recorded on this machine; "
            "run `python tests/_runner.py` with no arguments")

    def test_counted_from_the_commit_it_ran_at(self):
        _root, shas = self._repo()
        text = self._notice({"commit": shas[-1], "date": "2026-10-28 12:00"})
        assert text == (f"last full serial run: {shas[-1][:7]}, 2026-10-28 "
                        f"12:00, 0 commit(s) ago (the next is due at 100)")
        text = self._notice({"commit": shas[0], "date": "d"})
        assert ", 2 commit(s) ago" in text

    def test_due_from_the_number_on(self):
        _root, shas = self._repo()
        assert self._notice({"commit": shas[0], "date": "d"}, every=2) \
            .startswith(f"SERIAL RUN DUE — 2 commits since the last full "
                        f"serial run ({shas[0][:7]}, d)")
        assert not self._notice({"commit": shas[1], "date": "d"}, every=2) \
            .startswith("SERIAL RUN DUE")

    def test_due_when_the_commit_is_not_in_this_history(self):
        assert "is not in this history" in self._notice(
            {"commit": "0" * 40, "date": "d"})
        assert self._notice({"date": "d"}).startswith(
            "SERIAL RUN DUE — no full serial run recorded")

    def test_a_whole_run_in_chunks_ends_with_it(self):
        absent = Path(tempfile.gettempdir()) / "ogr_test_fast_no_record.json"
        run = _once("jobs", lambda: _throwaway(
            _CLEAN, {"SERIAL_RECORD": absent}, jobs=2))
        assert run["code"] == 0, run["text"]
        lines = run["text"].splitlines()
        at = next(i for i, x in enumerate(lines) if x.startswith("Total:"))
        assert lines[at + 1] == "PARALLEL RUN — 2 chunk(s) + serial lane"
        assert lines[at + 2].startswith(
            "SERIAL RUN DUE — no full serial run recorded on this machine")
        assert "a release still needs" not in run["text"]

    def test_a_filtered_run_in_chunks_does_not_say_it(self):
        assert "SERIAL RUN" not in _fast(3)["text"]


class TestTheOwnersNumber:
    def test_one_hundred_commits_here_and_in_agents_md(self):
        runner = _load_runner()
        assert runner.SERIAL_EVERY == 100
        agents = (_TESTS.parent / "AGENTS.md").read_text(encoding="utf-8")
        assert re.search(rf"\b{runner.SERIAL_EVERY} commits\b", agents)
        assert "--jobs 4" in agents

    def test_the_release_command_reads_the_notice(self):
        text = (_TESTS.parent / ".claude" / "commands" / "release.md") \
            .read_text(encoding="utf-8")
        assert "--jobs 4" in text and "SERIAL RUN DUE" in text
