# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.377 — off Windows, the runner's exit code is the tests' verdict,
whatever the interpreter's own shutdown would do after it; on Windows the
shutdown runs as it always did, and a crash in it still shows.

Why. From v0.1.276 every CI run on Linux ended with exit 139: all tests
passed, the totals were printed, and then the interpreter, tearing down
what the suite left alive, segfaulted inside Qt ("QObject: shared QObject
was deleted directly", <no Python frame>). A red CI with every test green
hides the next real red. Off Windows the runner now ends the process
itself after the totals (``os._exit``, which is ``_exit(2)`` there: no
library destructor runs), so that shutdown never runs; the crash is D370,
open, and is no longer seen — the price the owner chose.

Not on Windows, measured: there ``os._exit`` goes through ``ExitProcess``,
which still unloads every DLL with what the suite left alive. Two chunks of
``--jobs 4`` died with 0xC0000005 after their last file, and the same chunk
alone died with ``os._exit`` and exited 0 with the old ending (A/B).

Invariants protected:

1. **Off Windows, a green run exits 0 even when the shutdown would
   crash**; on Windows the shutdown still runs, and its crash is seen.
2. **Either way the totals are written out in full**: the streams are
   emptied before the end, which the old ending did not do — under the same
   crash it lost them.
3. **The injected crash is real**: the same injection without the runner
   ends the process with 139 and loses what was still buffered, so what the
   runner does above is its own doing.
4. **Off Windows any other verdict passes through unchanged**: a selection
   that matches nothing exits 2, not 139.

How: the real runner as ``__main__`` (``runpy``), in a process of its own
with a crash registered with ``atexit`` before it starts: only a process
of its own can show how a process ends. Each platform checks its own branch:
Linux in the CI, Windows here. Its temporary folder is one of the test's
own, so that it writes none of the machine's files (durations, times,
serial record). Two runs of a few seconds each, the cost of starting the
runner with Qt.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_RUNNER = _TESTS / "_runner.py"
#: Whether the runner ends the process itself (see its ``__main__``).
_ENDS_ITSELF = sys.platform != "win32"

#: What the interpreter's shutdown does in the CI since v0.1.276, as far as
#: the exit code goes: atexit handlers run at shutdown, so this one ends the
#: process with 139 there and only there.
_CRASH_AT_SHUTDOWN = "import atexit, os; atexit.register(os._exit, 139); "


def _run(code: str) -> subprocess.CompletedProcess:
    tmp = tempfile.mkdtemp(prefix="ogr_test_shutdown_")
    env = dict(os.environ, TEMP=tmp, TMP=tmp, TMPDIR=tmp,
               QT_QPA_PLATFORM="offscreen")
    # Buffered, as a redirected stdout is by default: unbuffered (the CI
    # sets PYTHONUNBUFFERED) nothing would be left to lose, and the flush
    # before the end would go untested.
    env.pop("PYTHONUNBUFFERED", None)
    try:
        return subprocess.run([sys.executable, "-c", code], env=env,
                              cwd=str(_TESTS.parent), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _runner_with_crash(*args: str) -> subprocess.CompletedProcess:
    return _run(_CRASH_AT_SHUTDOWN
                + "import runpy, sys; "
                + f"sys.argv = [{str(_RUNNER)!r}, *{list(args)!r}]; "
                + f"runpy.run_path({str(_RUNNER)!r}, run_name='__main__')")


_RUNS: dict = {}


def _once(key, make):
    if key not in _RUNS:
        _RUNS[key] = make()
    return _RUNS[key]


def _green():
    # One real test, cheap and with no window: it only reads the sources.
    return _once("green", lambda: _runner_with_crash(
        "test_license_v143", "-k", "test_copyright_line_present"))


class TestTheVerdictIsTheTests:
    def test_a_green_run_exits_with_its_verdict_or_the_crash_shows(self):
        run = _green()
        expected = 0 if _ENDS_ITSELF else 139
        assert run.returncode == expected, (run.returncode,
                                            run.stdout[-2000:],
                                            run.stderr[-2000:])

    def test_with_its_totals_written_out(self):
        out = _green().stdout
        assert "Total: 1    Passed: 1    Failed: 0" in out
        # the banner after the totals is the last thing main() prints
        assert out.rstrip().splitlines()[-1].startswith("FILTERED RUN")

    def test_the_crash_is_real_without_the_runner(self):
        run = _run(_CRASH_AT_SHUTDOWN + "print('done')")
        assert run.returncode == 139
        # And what was still in the buffer is lost with it: why the runner
        # flushes before its own end, and why its totals are there above.
        assert run.stdout == ""

    def test_another_verdict_passes_through(self):
        run = _once("nothing", lambda: _runner_with_crash(
            "test_license_v143", "-k", "no_test_is_called_this_v1377"))
        expected = 2 if _ENDS_ITSELF else 139
        assert run.returncode == expected, (run.returncode,
                                            run.stdout[-2000:])
        assert "No test name matches" in run.stdout
