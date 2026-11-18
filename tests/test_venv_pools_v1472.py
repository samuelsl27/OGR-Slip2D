# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.472 (spec 010) — in a virtual environment on Windows, without a
console, a calculation pool runs, and its workers compute with the same
trees as the process that opened it.

Without a console the workers start with ``pythonw.exe`` (D326, v0.1.329).
In a venv that one is a launcher, and multiprocessing cannot use it: the pool
died (``BrokenProcessPool``) and every search fell back to one process. The
plain fix, the base interpreter's ``pythonw.exe``, is worse: the pool runs,
but its workers are OUTSIDE the venv and can import another tree. The one
that works is the base ``pythonw.exe`` with ``__PYVENV_LAUNCHER__`` naming
the venv's, set only while each worker is created (``pool_context``).

What this file holds:

* the decisions, with fake folders and no process: in a venv the base
  ``pythonw.exe``; outside it, what v0.1.471 gave; nothing global changed;
* a real pool in a real venv (a throwaway one, 0.4 s to make; Windows only,
  so the CI on Linux skips it): a child process started with
  ``CREATE_NO_WINDOW``, as a job of the API is, opens the program's pool,
  and every worker must report the venv's ``sys.prefix`` and the parent's
  ``ogr_slip2d`` and ``ogr_core`` files, and be a ``pythonw.exe``
  (without the pool's context multiprocessing runs them too, inside the
  venv, but with ``python.exe``: a console window per worker, D326 again);
* its teeth, as fixed cases: the same child with the venv's ``pythonw.exe``
  (the pool dies) and with the base one without the launcher (the workers
  are outside the venv) must both be caught by the same judge.

It costs about four seconds (three children, each with a pool of two): a
pool cannot be tested without starting one, and the venv is made once.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_WINDOWS = sys.platform == "win32"


def _fake(folder, names):
    os.makedirs(folder, exist_ok=True)
    for name in names:
        Path(folder, name).write_bytes(b"")
    return folder


# ----------------------------------------------------------------------
class TestTheDecisions:
    def _two_trees(self):
        root = tempfile.mkdtemp(prefix="ogr_test_venv_")
        venv = _fake(os.path.join(root, "venv", "Scripts"),
                     ("python.exe", "pythonw.exe"))
        base = _fake(os.path.join(root, "base"), ("python.exe", "pythonw.exe"))
        return (os.path.join(venv, "python.exe"),
                os.path.join(base, "python.exe"))

    def test_in_a_venv_it_is_the_base_pythonw(self):
        from ogr_slip2d.processes import child_executable
        venv_exe, base_exe = self._two_trees()
        got = child_executable(platform="win32", executable=venv_exe,
                               console=0, frozen=False,
                               base_executable=base_exe, in_venv=True)
        assert got == os.path.join(os.path.dirname(base_exe), "pythonw.exe")

    def test_outside_a_venv_it_is_what_it_was(self):
        from ogr_slip2d.processes import child_executable
        venv_exe, base_exe = self._two_trees()
        got = child_executable(platform="win32", executable=venv_exe,
                               console=0, frozen=False,
                               base_executable=base_exe, in_venv=False)
        assert got == os.path.join(os.path.dirname(venv_exe), "pythonw.exe")

    def test_a_console_another_system_a_frozen_build_change_nothing(self):
        from ogr_slip2d.processes import child_executable, pool_context
        venv_exe, base_exe = self._two_trees()
        for kw in ({"platform": "win32", "console": 1234, "frozen": False},
                   {"platform": "linux", "console": 0, "frozen": False},
                   {"platform": "win32", "console": 0, "frozen": True}):
            assert child_executable(executable=venv_exe, in_venv=True,
                                    base_executable=base_exe, **kw) is None
            assert pool_context(executable=venv_exe, in_venv=True,
                                base_executable=base_exe, **kw) is None

    def test_no_base_pythonw_is_none(self):
        from ogr_slip2d.processes import child_executable
        venv_exe, _ = self._two_trees()
        bare = _fake(tempfile.mkdtemp(prefix="ogr_test_base_"), ("python.exe",))
        assert child_executable(platform="win32", executable=venv_exe,
                                console=0, frozen=False, in_venv=True,
                                base_executable=os.path.join(bare, "python.exe")
                                ) is None

    def test_the_context_only_in_a_venv(self):
        from ogr_slip2d import processes
        venv_exe, base_exe = self._two_trees()
        kw = dict(platform="win32", executable=venv_exe, console=0,
                  frozen=False, base_executable=base_exe)
        assert processes.pool_context(in_venv=False, **kw) is None
        assert isinstance(processes.pool_context(in_venv=True, **kw),
                          processes._VenvContext)

    def test_in_a_venv_nothing_global_is_pointed(self):
        """Pointed for the whole process, every other pool would start with
        the base interpreter and no launcher: outside the venv."""
        import multiprocessing.spawn as spawn
        from ogr_slip2d.processes import windowless_children
        venv_exe, base_exe = self._two_trees()
        before = spawn.get_executable()
        try:
            got = windowless_children(platform="win32", executable=venv_exe,
                                      console=0, frozen=False,
                                      base_executable=base_exe, in_venv=True)
            assert got is not None
            assert spawn.get_executable() == before
        finally:
            spawn.set_executable(before)


class TestThePoolIsMadeAsBefore:
    """Outside a venv ``stoppable_pool`` makes its pool with exactly the
    call of v0.1.471, without ``mp_context``: passing ``mp_context=None``
    broke two test doubles written with the old signature (the first full
    suite of this version). In a venv it passes the context."""

    def _kwargs(self, context):
        import concurrent.futures as cf
        from ogr_slip2d import processes
        seen = {}

        class Recorder:
            def __init__(self, **kw):
                seen.update(kw)

        raw_pool, raw_context = cf.ProcessPoolExecutor, processes.pool_context
        cf.ProcessPoolExecutor = Recorder
        processes.pool_context = lambda **k: context
        try:
            processes.stoppable_pool(2)
        finally:
            cf.ProcessPoolExecutor, processes.pool_context = raw_pool, raw_context
        return seen

    def test_outside_a_venv_no_context_is_passed(self):
        assert "mp_context" not in self._kwargs(None)

    def test_in_a_venv_its_context_is(self):
        from ogr_slip2d import processes
        context = processes._VenvContext()
        assert self._kwargs(context)["mp_context"] is context


class TestAWorkerIsStartedWithBothAndThenNeither:
    """``_start_in_venv`` with a stand-in for multiprocessing's Popen: what
    it sees while it starts the worker, and what is left after."""

    def _start(self, popen):
        import multiprocessing.spawn as spawn
        from ogr_slip2d import processes
        raw = processes.child_executable, processes.venv_launcher
        processes.child_executable = lambda **k: "BASE_PYTHONW"
        processes.venv_launcher = lambda executable=None: "VENV_PYTHONW"
        exe_before = spawn.get_executable()
        env_before = os.environ.get("__PYVENV_LAUNCHER__")
        try:
            try:
                processes._start_in_venv(object(), popen=popen)
            except RuntimeError:
                pass
            return (os.fsdecode(spawn.get_executable()),
                    os.environ.get("__PYVENV_LAUNCHER__"),
                    os.fsdecode(exe_before), env_before)
        finally:
            processes.child_executable, processes.venv_launcher = raw
            spawn.set_executable(exe_before)
            if env_before is None:
                os.environ.pop("__PYVENV_LAUNCHER__", None)
            else:
                os.environ["__PYVENV_LAUNCHER__"] = env_before

    def test_while_it_starts(self):
        import multiprocessing.spawn as spawn
        seen = []
        self._start(lambda p: seen.append(
            (os.fsdecode(spawn.get_executable()),
             os.environ.get("__PYVENV_LAUNCHER__"))))
        assert seen == [("BASE_PYTHONW", "VENV_PYTHONW")]

    def test_put_back_after(self):
        exe, env, exe_before, env_before = self._start(lambda p: None)
        assert (exe, env) == (exe_before, env_before)

    def test_put_back_when_it_fails(self):
        def fails(p):
            raise RuntimeError("CreateProcess failed")
        exe, env, exe_before, env_before = self._start(fails)
        assert (exe, env) == (exe_before, env_before)


# ----------------------------------------------------------------------
# The real pool, in a real venv
_CHILD = r'''
import json, os, sys
variant, root = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)
from ogr_slip2d import processes
if variant == "venv_pythonw":
    # the launcher itself, as v0.1.471 gave
    processes.child_executable = lambda **k: processes.venv_launcher()
elif variant == "base_without_launcher":
    processes.venv_launcher = lambda executable=None: None

# what the pool's context used for each worker it started
started = []
_raw_start = processes._start_in_venv


def _recorded(process_obj, popen=None):
    started.append([processes.child_executable(), processes.venv_launcher()])
    return _raw_start(process_obj, popen)


processes._start_in_venv = _recorded


def work(_):
    import ogr_core, ogr_slip2d
    return [sys.prefix, ogr_slip2d.__file__, ogr_core.__file__,
            os.path.basename(sys.executable)]


if __name__ == "__main__":
    out = {"context": processes.pool_context() is not None,
           "base_pythonw": os.path.join(os.path.dirname(sys._base_executable),
                                        "pythonw.exe"),
           # the venv's own launcher, from sys.executable: one variant
           # replaces venv_launcher
           "venv_pythonw": os.path.join(os.path.dirname(sys.executable),
                                        "pythonw.exe")}
    try:
        pool, stop = processes.stoppable_pool(2)
        with pool:
            out["children"] = list(pool.map(work, range(4)))
    except Exception as exc:
        out["error"] = type(exc).__name__
    out["started"] = started
    print(json.dumps(out))
'''

_RUNS: dict = {}


def _same(a, b) -> bool:
    return (os.path.normcase(os.path.realpath(a))
            == os.path.normcase(os.path.realpath(b)))


def _venv() -> Path:
    """A throwaway venv whose site sees what this interpreter sees: its
    site-packages through a .pth (``site.addsitedir``, so that their own
    .pth files, the editable installs among them, are read too)."""
    if "venv" not in _RUNS:
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_venvpool_")) / "venv"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip",
                        str(folder)], check=True, timeout=120)
        import site
        dirs = [d for d in site.getsitepackages() if os.path.isdir(d)]
        lines = [f"import site; site.addsitedir({d!r})" for d in dirs]
        target = folder / "Lib" / "site-packages" / "ogr_test_parent.pth"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (folder.parent / "child.py").write_text(_CHILD, encoding="utf-8")
        _RUNS["venv"] = folder
    return _RUNS["venv"]


def _run(variant: str) -> dict:
    if variant not in _RUNS:
        venv = _venv()
        done = subprocess.run(
            [str(venv / "Scripts" / "python.exe"),
             str(venv.parent / "child.py"), variant, str(_ROOT)],
            capture_output=True, text=True, timeout=300,
            creationflags=0x08000000)  # CREATE_NO_WINDOW: no console
        assert done.returncode == 0, done.stderr[-2000:]
        _RUNS[variant] = json.loads(done.stdout.strip().splitlines()[-1])
    return _RUNS[variant]


def _judge(out: dict) -> list:
    """What is wrong with a child's run: nothing, for the program's."""
    import ogr_core
    import ogr_slip2d
    venv = _venv()
    if not out.get("context"):
        return ["no venv context"]
    if "error" in out:
        return [f"the pool died: {out['error']}"]
    problems = []
    for prefix, slip2d, core, exe in out["children"]:
        if exe.lower() != "pythonw.exe":
            # multiprocessing's own venv path (bpo-35797) runs too, but
            # with python.exe: a console window per worker, D326 again
            problems.append(f"a worker has a console: {exe}")
        if not _same(prefix, venv):
            problems.append(f"a worker is outside the venv: {prefix}")
        if not _same(slip2d, ogr_slip2d.__file__):
            problems.append(f"another ogr_slip2d: {slip2d}")
        if not _same(core, ogr_core.__file__):
            problems.append(f"another ogr_core: {core}")
    return problems


def _windows_only():
    if not _WINDOWS:
        pytest.skip("Windows only: pythonw.exe and its venv launcher")


class TestARealPoolInAVenv:
    def test_it_runs_with_the_parents_trees(self):
        _windows_only()
        out = _run("program")
        assert _judge(out) == [], out
        assert len(out["children"]) == 4

    def test_the_program_starts_the_base_one_with_the_launcher(self):
        _windows_only()
        out = _run("program")
        assert out["started"], out
        for exe, launcher in out["started"]:
            assert _same(exe, out["base_pythonw"]), (exe, out)
            assert _same(launcher, out["venv_pythonw"]), (launcher, out)

    def test_the_venvs_pythonw_is_caught(self):
        _windows_only()
        out = _run("venv_pythonw")
        assert out["started"] and all(_same(e, out["venv_pythonw"])
                                      for e, _ in out["started"]), out
        problems = _judge(out)
        assert any(p.startswith("the pool died") for p in problems), problems

    def test_the_base_one_without_the_launcher_is_caught(self):
        """Caught either way it shows. Outside the venv the worker either
        runs with the base interpreter's ``sys.prefix`` (measured in
        v0.1.472, from a system Python that had this tree installed), or
        cannot even load the program and the pool dies (measured in
        v0.1.473, in the ``.venv``: the core is only there)."""
        _windows_only()
        out = _run("base_without_launcher")
        assert out["started"] and all(
            _same(e, out["base_pythonw"]) and l is None
            for e, l in out["started"]), out
        problems = _judge(out)
        assert any(p.startswith(("a worker is outside the venv",
                                 "the pool died")) for p in problems), problems
