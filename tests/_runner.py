# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Minimal test runner for environments without pytest.

Discovers classes starting with 'Test' in tests/*.py, instantiates them,
and runs methods starting with 'test_'. Supports the small subset of
pytest features used in the OGR test suite:

    - pytest.approx()
    - pytest.raises(...)
    - tmp_path fixture (emulated with tempfile)

Not a replacement for pytest in production — only a smoke-test tool
that allows verifying the suite in air-gapped CI environments.

Running a part of it
--------------------

    python tests/_runner.py                          # everything
    python tests/_runner.py transient                # by file fragment
    python tests/_runner.py transient seepage        # union of both
    python tests/_runner.py tests/test_mesh_v125.py  # by path
    python tests/_runner.py -k erfc                  # by test name
    python tests/_runner.py --list transient         # show, run nothing

Selection exists because the whole suite is 1706 tests in 99 files and
about seven minutes, while the distribution is extremely uneven: the four
slowest files are 42 % of the time, and the 58 fastest — nearly half of
all the tests — add up to under ten seconds. Checking a change to one
subsystem used to cost the full seven minutes regardless.

Two rules keep the shortcut from becoming a liar, and both are tested:

1. **No arguments behaves exactly as before.** That is what CI runs.
2. **A selection that matches nothing exits non-zero.** Otherwise a typo
   prints ``Total: 0  Passed: 0  Failed: 0`` and reads as success.

Which tree is being measured
----------------------------

Every run opens with a ``tree:`` line naming the directory the ``ogr_*``
packages resolve to, and refuses to run if any of them resolves outside this
repository. That is not defensive tidiness — it is the fix for a wrong
diagnosis that nearly reversed a correct conclusion in v0.1.84, because
``pip install -e .`` registers a finder that resolves every ``ogr_*`` to one
hard-coded absolute path. A diagnostic script kept outside the repository
therefore imports the main working tree no matter which tree you cd into or
which commit you check out. The full mechanism is in
:func:`foreign_packages`.

The practical rule that follows: **run diagnostics from inside the tree you
mean to measure**, and check the ``tree:`` line rather than assuming.

Running in chunks
-----------------

    python tests/_runner.py --jobs 4                 # four processes
    python tests/_runner.py --jobs 4 --list          # the plan, run nothing

v0.1.375 — the selection is cut into contiguous pieces of the alphabetical
order, balanced by how long each file took last time, and each piece runs
in a process of its own with this same loop: the same leak check, the same
progress lines. The output is printed in order, as a serial run would print
it. Files with a module-level ``SERIAL_LANE = True`` (they compare with the
clock) run after the chunks, alone. A chunk that dies cannot leave a green
run behind: the run passes only if every chunk ends with its code, every
selected file reports its end, and the tests run are the tests declared
(see :func:`partition` and ``_run_jobs``). Without ``--jobs`` nothing
changes, and that serial run is what CI executes.
"""
from __future__ import annotations

import argparse
import ast
import codecs
import gc
import importlib.util
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager, suppress
from pathlib import Path


# --- pytest compatibility shim ----------------------------------------
class _Approx:
    def __init__(self, expected, rel=None, abs_=None):
        self.expected = expected
        self.rel = rel
        self.abs = abs_

    def __eq__(self, other):
        if self.abs is not None:
            return math.isclose(other, self.expected, abs_tol=self.abs)
        tol = self.rel if self.rel is not None else 1e-6
        return math.isclose(other, self.expected, rel_tol=tol, abs_tol=1e-9)

    def __repr__(self):
        return f"approx({self.expected})"


def _approx(expected, rel=None, abs=None):  # noqa: A002
    return _Approx(expected, rel=rel, abs_=abs)


@contextmanager
def _raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, got {type(e).__name__}")
    raise AssertionError(f"Expected {exc_type.__name__}, no exception raised")


class Skipped(BaseException):
    """``pytest.skip`` in this runner: the test cannot be measured HERE.

    v0.1.205 — the shim had no ``skip``, so a test that called it failed with
    an AttributeError instead: on GitHub, where the verification bank does
    not exist, ``test_the_fifteen_sheets_give_what_they_gave`` turned the CI
    red for a reason that was not a defect. A ``BaseException``, as pytest's
    own, so that a test's ``except Exception`` cannot swallow it.

    Recognised by the ``ogr_skip`` mark and NOT by its class, on purpose: a
    test that ``import _runner`` (to borrow a helper) executes this file a
    second time and makes a second ``Skipped`` class. On GitHub that copy's
    skip escaped the running runner's ``except Skipped`` and ended the suite
    at 83 % with no totals (the first run of v0.1.205). Any copy's mark is
    the same mark.
    """
    ogr_skip = True


def _skip(reason: str = ""):
    raise Skipped(reason)


class _FakePytest:
    approx = staticmethod(_approx)
    raises = staticmethod(_raises)
    skip = staticmethod(_skip)
    #: This shim, as opposed to a real pytest (v0.1.205, see below).
    ogr_shim = True


# v0.1.205 — install once. A test that ``import _runner`` re-executes this
# file, and replacing the shim then left a different one installed for every
# file after it (rule 5); keeping the first makes a second import harmless.
if not getattr(sys.modules.get("pytest"), "ogr_shim", False):
    sys.modules["pytest"] = _FakePytest()  # type: ignore


# --- Selection --------------------------------------------------------
PACKAGES = ("ogr_core", "ogr_slip2d", "ogr_fem2d", "ogr_gui", "ogr_cli",
            "ogr_api", "ogr_mcp")


def package_origins() -> dict:
    """Where each ``ogr_*`` package WOULD be imported from.

    ``find_spec`` resolves through the same finders a real import would, so
    this sees exactly what the tests will see — but it executes no
    module-level code, which is the property that lets it run before the
    first test. Importing the five packages here to ask them their
    ``__file__`` would run the module-level code of half the project before
    anything is measured, which is what rule 5 exists to prevent.

    Returns ``{name: directory or None}``.
    """
    out = {}
    for name in PACKAGES:
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError, AttributeError):
            spec = None
        origin = getattr(spec, "origin", None) if spec else None
        out[name] = Path(origin).resolve().parent if origin else None
    return out


def foreign_packages(origins: dict, repo_root: Path) -> list:
    """The packages that resolve OUTSIDE ``repo_root``.

    v0.1.89 — this exists because of a wrong diagnosis that cost two days
    and nearly reversed a correct conclusion. Diagnosing the v0.1.84 fall of
    ``test_support_increases_fos``, a stand-alone script replicating the test
    line by line reported the SAME result for the working tree and for HEAD,
    when instrumenting inside the runner showed 10 valid surfaces and a
    critical 2.1279 against 0 valid. The script was not wrong about what it
    measured; it was measuring the wrong tree, and said nothing about it.

    The mechanism, and it is fully deterministic:

    1. ``python C:\\somewhere\\else\\script.py`` puts the SCRIPT's directory
       in ``sys.path[0]`` — not the working directory.
    2. There is no ``ogr_*`` there, so ``PathFinder`` (position 2 of
       ``sys.meta_path``) finds nothing.
    3. ``_EditableFinder`` (position 3), installed by ``pip install -e .``,
       answers instead — and it resolves every ``ogr_*`` to one hard-coded
       absolute path, the tree that was installed.

    So a script stored outside the repository imports the MAIN working tree
    whatever tree you cd into or commit you check out. Verified: with the cwd
    set to a directory containing its own ``ogr_slip2d``, the import still
    came from the installed path and the decoy's marker never appeared.

    This runner does not have the problem — it inserts its own parent in
    ``sys.path`` — but it cannot detect the problem for others either, so
    what it can do is refuse to run when it is itself pointed at another
    tree, and print where it is looking either way. A suite that silently
    tests a different tree than the one being edited is the worst failure
    available: every result is real and every conclusion is wrong.
    """
    bad = []
    for name, where in sorted(origins.items()):
        if where is None:
            bad.append((name, None))
            continue
        try:
            where.relative_to(repo_root)
        except ValueError:
            bad.append((name, where))
    return bad


def head_sha(repo_root: Path) -> str:
    """The short commit of ``repo_root``, read from ``.git`` directly.

    No subprocess: the banner must not be able to fail. This says which
    commit, not whether the tree is clean — ``git status`` is the reader's
    job, and the PATH above is the part that actually caused the bug.
    """
    try:
        head = (repo_root / ".git" / "HEAD").read_text(
            encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:].strip()
            sha = (repo_root / ".git" / ref).read_text(
                encoding="utf-8").strip()
        else:
            sha = head
        return sha[:7] if sha else "?"
    except OSError:
        return "?"


def provenance(repo_root: Path, origins: dict) -> str:
    """One line saying which tree is about to be measured.

    Each package sits in its OWN directory under the tree, so the thing to
    collapse is their common parent, not the directories themselves. Getting
    that wrong prints five absolute paths on one line, which is the sort of
    banner people learn to skip — and a banner nobody reads protects nothing.
    """
    parents = {v.parent for v in origins.values() if v is not None}
    if len(parents) == 1:
        return (f"tree: {parents.pop()}  @ {head_sha(repo_root)}  "
                f"({len(PACKAGES)} ogr packages)")
    return "tree: " + ", ".join(
        f"{k}={v}" for k, v in sorted(origins.items()))


def _normalise(pattern: str) -> str:
    """Reduce a file pattern to the fragment that is compared against a stem.

    A pattern may arrive in three shapes and all three must work:
    ``transient``, ``test_transient_v130.py`` (shell completion) and
    ``tests/test_transient_v130.py`` (copied from a traceback). Dropping
    the directory part and the extension makes them one case.

    Resolving the pattern as a path instead would tie the result to the
    current directory, so ``tests/test_x.py`` would select from the repo
    root and silently select nothing from anywhere else. A pattern must
    mean the same thing wherever it is typed.
    """
    p = pattern.replace("\\", "/").rstrip("/")
    p = p.rsplit("/", 1)[-1]
    if p.endswith(".py"):
        p = p[:-3]
    return p.lower()


def select_files(tests_dir: Path, patterns) -> list[Path]:
    """The test files to run, in the order the runner has always used.

    With no patterns this is ``sorted(glob("test_*.py"))`` — byte for byte
    what CI executes. With patterns, a file is kept when any normalised
    pattern is a substring of its stem. The order never changes: a run
    that cannot be reproduced in the same order cannot be used to chase a
    state leak, which is the failure rule 5 exists for.
    """
    every = sorted(tests_dir.glob("test_*.py"))
    if not patterns:
        return every
    wanted = [n for n in (_normalise(p) for p in patterns) if n]
    return [f for f in every
            if any(n in f.stem.lower() for n in wanted)]


def match_test(class_name: str, method_name: str, expr: str | None) -> bool:
    """Whether ``Class.method`` is kept by a ``-k`` expression.

    Plain case-insensitive substring against ``"Class.method"``. The
    ``and``/``or``/``not`` grammar of pytest's own ``-k`` is deliberately
    NOT implemented: a boolean parser that mis-reads a ``not`` selects a
    different set than the one the reader believes it selected, and says
    nothing. A documented substring cannot be misread that way.
    """
    if not expr:
        return True
    return expr.lower() in f"{class_name}.{method_name}".lower()


def _declared_tests(files, expr: str | None = None):
    """Every ``(file, class, method)`` the selection declares, WITHOUT
    importing anything.

    The runner discovers tests as it goes, so it cannot know the total
    until the end. Importing every module up front to count them would
    execute the module-level code of the whole suite before the first
    test runs — exactly the kind of state leak rule 5 exists to prevent.
    Parsing the source answers the question with no execution at all:
    81 files in about 230 ms, 0.06 % of a run, and nothing during it.

    Applying ``expr`` here rather than after the fact is what keeps the
    progress denominator honest under ``-k``.

    Returns ``None`` if anything cannot be parsed, in which case the
    caller falls back to a plain counter. A progress display must never
    be the reason a test run fails.
    """
    found: list[tuple[Path, str, str]] = []
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            return None
        for node in tree.body:
            if not (isinstance(node, ast.ClassDef)
                    and node.name.startswith("Test")):
                continue
            for m in node.body:
                if (isinstance(m, ast.FunctionDef)
                        and m.name.startswith("test_")
                        and match_test(node.name, m.name, expr)):
                    found.append((f, node.name, m.name))
    return found


def _count_tests(files, expr: str | None = None) -> int:
    """Total number of selected test methods, or 0 if the source cannot
    be parsed."""
    declared = _declared_tests(files, expr)
    return len(declared) if declared is not None else 0


def _suggest(every, patterns) -> list[str]:
    """File names close to what was asked, so a typo is visible.

    ``transiant`` shares its first four characters with
    ``test_transient_v130``; printing that beside the error turns a blank
    result into an obvious misspelling.
    """
    out: list[str] = []
    for p in patterns:
        head = _normalise(p)[:4]
        if head:
            out += [f.stem for f in every if head in f.stem.lower()]
    return sorted(set(out))[:8]


# --- Discovery & runner -----------------------------------------------
def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_method(instance, method):
    # Bind the unbound function to the instance so `self` is provided
    bound = method.__get__(instance, type(instance))
    sig = inspect.signature(bound)
    kwargs = {}
    if "tmp_path" in sig.parameters:
        tmpdir = tempfile.mkdtemp()
        kwargs["tmp_path"] = Path(tmpdir)
    result = bound(**kwargs)
    # v0.1.194 — an ``async def`` test returns a coroutine WITHOUT RUNNING
    # A LINE OF ITS BODY, and until now that return value was ignored, so
    # it counted as a pass: a green test that tested nothing. The MCP
    # server tests are the first in this suite with async code to drive,
    # which is exactly when a slip like that stops being hypothetical.
    if inspect.iscoroutine(result):
        result.close()
        raise TypeError(
            f"{method.__name__} is `async def`, and this runner does not "
            f"await coroutines, so its body never ran. Make it a plain "
            f"method and drive the async part with asyncio.run(...).")


def run_test(cls, method):
    """Run one test: ``(outcome, why, traceback)``, with ``outcome`` one of
    ``"passed"``, ``"failed"`` and ``"skipped"``.

    v0.1.203 — ``SystemExit`` is a failure of that test, like any other
    exception. Code under test that calls ``sys.exit`` (argparse does, on an
    option it does not know) used to escape the run loop and end the WHOLE
    suite there, with no totals: one test's failure cost every file after
    it. ``KeyboardInterrupt`` still stops the run, as it should.

    v0.1.205 — ``pytest.skip`` is a third outcome, counted apart: neither a
    pass (it measured nothing) nor a failure (nothing was wrong).
    """
    try:
        _run_method(cls(), method)
        return "passed", None, None
    except AssertionError as e:
        return "failed", f"{e}", traceback.format_exc()
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return "failed", f"{type(e).__name__}: {e}", traceback.format_exc()
    except BaseException as e:
        # By its mark, from whichever copy of this file raised it (see
        # ``Skipped``); anything else — KeyboardInterrupt — goes on up.
        if getattr(e, "ogr_skip", False):
            return "skipped", f"{e}", None
        raise


#: The folders a run gives itself (see ``main``), put back after every file.
_RUN_FOLDERS = ("OGR_BRIDGE_DIR", "OGR_SETTINGS_DIR")


# --- Running in chunks (v0.1.375) ---------------------------------------
#: The last measured seconds of each file, by name, to balance the chunks of
#: ``--jobs``. In the temporary folder and not in the repository: it
#: describes this machine, not the code, and a missing or stale entry only
#: makes the chunks less even, never the run less complete.
DURATIONS = Path(tempfile.gettempdir()) / "ogr-slip2d-test-durations.json"


def serial_lane(path: Path) -> bool:
    """Whether a test file asks to run alone, after the chunks: a
    module-level ``SERIAL_LANE = True``, read from the source without
    importing it (nothing of a file runs before its turn). For the files
    that compare with the clock, which a process sharing the cores could
    fail for a reason that is not a defect."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return False
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "SERIAL_LANE"
                        for t in node.targets)):
            return (isinstance(node.value, ast.Constant)
                    and node.value.value is True)
    return False


def load_durations(path: Path = DURATIONS) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: float(v) for k, v in data.items()
            if isinstance(v, (int, float)) and v >= 0}


def save_durations(times: dict, path: Path = DURATIONS) -> None:
    """Merge ``times`` into the file: a filtered run updates its own files
    and keeps the rest. Written aside and moved, so that a run reading it
    never sees half a file; a failure to write costs balance, not a run."""
    if not times:
        return
    data = load_durations(path)
    data.update({k: round(v, 3) for k, v in times.items()})
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=0, sort_keys=True),
                       encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        with suppress(OSError):
            tmp.unlink()


def file_weights(files, counts: dict, durations: dict) -> list:
    """What each file is expected to cost: its last duration; for a file
    never timed, its tests at the median seconds per test of the files that
    were (one second per test when none was)."""
    rates = sorted(durations[f.name] / counts[f.name] for f in files
                   if f.name in durations and counts.get(f.name))
    rate = rates[len(rates) // 2] if rates else 1.0
    return [max(durations.get(f.name, rate * max(counts.get(f.name, 0), 1)),
                1e-3)
            for f in files]


def partition(weights, n: int) -> list:
    """``[(start, end), ...]``: at most ``n`` contiguous slices that cover
    ``weights`` in order, with the heaviest slice as light as it can be.

    Contiguous on purpose. Each chunk is a piece of the alphabetical order,
    so a file keeps the neighbours it has in the serial run except at the
    n - 1 borders, and a run can be repeated as it was. A queue that hands
    out files as processes come free would end sooner, and would give files
    different neighbours in every run: a leak a neighbour depends on would
    show or hide by chance.

    The heaviest slice is minimised exactly (the linear partition problem):
    the smallest capacity that a greedy fill packs into ``n`` slices, found
    by bisection, and the greedy fill at that capacity. That fill can use
    fewer slices than ``n``; the heaviest slice of two files or more is then
    split where its halves are most even, which never raises the heaviest,
    until there are ``n``: whoever asks for four processes gets four.
    """
    weights = list(weights)
    if not weights:
        return []
    n = max(1, min(n, len(weights)))

    def fill(cap):
        out, start, acc = [], 0, 0.0
        for i, w in enumerate(weights):
            if i > start and acc + w > cap:
                out.append((start, i))
                start, acc = i, 0.0
            acc += w
        out.append((start, len(weights)))
        return out

    lo, hi = max(weights), sum(weights)
    for _ in range(200):
        if hi - lo <= 1e-9 * hi:
            break
        mid = (lo + hi) / 2
        if len(fill(mid)) <= n:
            hi = mid
        else:
            lo = mid
    parts = fill(hi)
    while len(parts) < n:
        a, b = max((p for p in parts if p[1] - p[0] > 1),
                   key=lambda p: sum(weights[p[0]:p[1]]))
        cut = min(range(a + 1, b), key=lambda c: max(sum(weights[a:c]),
                                                     sum(weights[c:b])))
        i = parts.index((a, b))
        parts[i:i + 1] = [(a, cut), (cut, b)]
    return parts


class _Tally:
    """What a run has counted, and the progress tag of its next test. A
    chunk counts from its place in the whole run, so that its lines read
    as the same lines of a serial run."""

    def __init__(self, total: int, offset: int = 0):
        self.passed = self.failed = self.skipped = 0
        self.leaked = 0     # files, not tests: see _run_files
        self.fail_details: list[tuple[str, str]] = []
        self.total, self.offset = total, offset
        # Fixed width, so the pass/fail marks stay in one column and the
        # output is still readable when it scrolls.
        self.w = len(str(total)) if total else 4

    def tag(self) -> str:
        done = self.offset + self.passed + self.failed + self.skipped
        if not self.total:
            return f"[{done:>{self.w}}]"
        return (f"[{done:>{self.w}}/{self.total} "
                f"{100.0 * done / self.total:3.0f}%]")


def _totals_line(passed, failed, skipped, leaked, died=0) -> str:
    # A skip is counted apart and named: it is neither a pass (it measured
    # nothing) nor a failure (nothing was wrong). Absent when there is none,
    # so a run without skips prints exactly what it always printed. So are
    # the files that leaked (v0.1.374): their tests passed, the file did not;
    # and the chunks of --jobs that died (v0.1.375).
    return (f"Total: {passed + failed + skipped}    Passed: {passed}    "
            f"Failed: {failed}" + (f"    Skipped: {skipped}" if skipped else "")
            + (f"    Leaks: {leaked}" if leaked else "")
            + (f"    Chunks died: {died}" if died else ""))


def _leak_detector():
    """``tests/_leaks.py``, by its path next to this file: tests load this
    runner by path too, with no promise that ``tests/`` is on sys.path. Kept
    as ``_leaks`` in sys.modules, the module tests import its helpers from."""
    mod = sys.modules.get("_leaks")
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            "_leaks", Path(__file__).resolve().with_name("_leaks.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_leaks"] = mod
        spec.loader.exec_module(mod)
    return mod


def _run_files(test_files, k, tally: _Tally, leaks, gc_guard, *,
               file_offset: int = 0, n_files: int | None = None,
               on_file=None) -> None:
    """Run ``test_files`` in order, counting into ``tally``.

    ``on_file(f, record)`` is called for every file that reached its end
    (not for one an interrupt cut short) with what it counted, its leaks,
    its failure details and its seconds: what a chunk reports to the run
    that started it, and what a serial run keeps as its durations.
    """
    n_files = n_files or len(test_files)
    for i_file, f in enumerate(test_files, 1):
        # v0.1.302 (D310) — what the previous file left as cyclic garbage is
        # freed here, on the main thread, and not later by whichever thread
        # trips the collector (where Qt objects go to a deferred deletion).
        gc_guard.release()
        gc.collect()
        # v0.1.373 — and what survives is frozen, so the next collections
        # (this one, and the automatic ones on any thread) walk only what was
        # made since. Each full collection cost ~320 ns per live object: 0.4 s
        # per file at the start of the suite, 3.4 s at the end, 13.6 of 87.6
        # minutes (docs/audits/AUDITORIA_SUITE_v0.1.372.md §3). Collected
        # first, frozen after: the previous file's garbage is still freed.
        gc.freeze()
        print(f"\n=== {f.name} ===  ({file_offset + i_file}/{n_files})")
        # v0.1.373 — sys.path and the run's own folders are put back after
        # each file. 242 files insert tests/, which is already sys.path[0],
        # and nothing took it out: 369 entries at the end, walked with one
        # stat each by every import of every spawn worker (a pool of 4 went
        # from 0.5 s to 2.4-3.6 s, audit §4.3). Two runner self-tests repoint
        # the folders through a second main() (audit D-d).
        saved_path = list(sys.path)
        saved_folders = {v: os.environ.get(v) for v in _RUN_FOLDERS}
        start = (tally.passed, tally.failed, tally.skipped,
                 len(tally.fail_details))
        before = leaks.snapshot()
        t0 = time.perf_counter()
        finished = False
        try:
            try:
                mod = _load_module(f)
            except Exception as e:  # noqa: BLE001
                print(f"  [LOAD ERROR] {e}")
                tally.fail_details.append((f.name, traceback.format_exc()))
                tally.failed += 1
                finished = True
                continue

            for name, cls in inspect.getmembers(mod, inspect.isclass):
                if not name.startswith("Test"):
                    continue
                if cls.__module__ != mod.__name__:
                    continue
                methods = [(m_name, m)
                           for m_name, m in inspect.getmembers(cls, inspect.isfunction)
                           if m_name.startswith("test_")
                           and match_test(name, m_name, k)]
                if not methods:
                    continue
                print(f"  {name}:")
                for m_name, m in methods:
                    outcome, why, tb = run_test(cls, m)
                    if outcome == "passed":
                        tally.passed += 1
                        print(f"    {tally.tag()} ✓ {m_name}")
                    elif outcome == "skipped":
                        tally.skipped += 1
                        print(f"    {tally.tag()} ○ {m_name} — skipped: {why}")
                    else:
                        tally.failed += 1
                        print(f"    {tally.tag()} ✗ {m_name}: {why}")
                        tally.fail_details.append((f"{name}.{m_name}", tb))
            finished = True
        finally:
            seconds = time.perf_counter() - t0
            # In place: whoever holds the sys.path list keeps the same one.
            sys.path[:] = saved_path
            for var, value in saved_folders.items():
                if value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = value
            # v0.1.374 — anything else the file left in the process is
            # named here, at the file that left it, and fails the run (rule
            # 5). Before, a leak showed only if a later test happened to
            # depend on it, and only in the full run. What is looked at and
            # what is allowed: tests/_leaks.py.
            found = leaks.diff(before, leaks.snapshot())
            lines = [leaks.describe(*leak) for leak in found]
            if found:
                tally.leaked += 1
                for line in lines:
                    print(f"  ✗ [LEAK] {line}")
                tally.fail_details.append((f"{f.name} [LEAK]", "\n".join(lines)))
            if finished and on_file is not None:
                on_file(f, {"file": f.name,
                            "passed": tally.passed - start[0],
                            "failed": tally.failed - start[1],
                            "skipped": tally.skipped - start[2],
                            "leaks": lines,
                            "details": tally.fail_details[start[3]:],
                            "seconds": round(seconds, 3)})


def _run_chunk(spec_path: Path, leaks, gc_guard) -> int:
    """One chunk of ``--jobs`` (``--child SPEC``): the files of the spec, in
    its order, each written to the report as it ends. A chunk that dies
    leaves behind the files it finished, so the run that started it can say
    where it died; a chunk that ends writes ``{"end": true}`` last."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    tally = _Tally(spec["total"], spec["test_offset"])
    with open(spec["report"], "a", encoding="utf-8") as report:
        def on_file(_f, record):
            report.write(json.dumps(record) + "\n")
            report.flush()

        _run_files([Path(p) for p in spec["files"]], spec.get("k"), tally,
                   leaks, gc_guard, file_offset=spec["file_offset"],
                   n_files=spec["n_files"], on_file=on_file)
        report.write(json.dumps({"end": True}) + "\n")
    return 0 if tally.failed == 0 and tally.leaked == 0 else 1


def _follow(log: Path, proc) -> None:
    """Copy a chunk's output here as it is written, until the chunk ends.
    Bytes, decoded incrementally: a read can stop inside a character."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    with open(log, "rb") as fh:
        while True:
            data = fh.read(1 << 16)
            if data:
                sys.stdout.write(decoder.decode(data))
                sys.stdout.flush()
                continue
            if proc.poll() is not None:
                sys.stdout.write(decoder.decode(fh.read(), final=True))
                sys.stdout.flush()
                return
            time.sleep(0.2)


def _exit_code(code) -> str:
    # Windows gives an NTSTATUS as a large unsigned number: 3221226505 is
    # 0xC0000409, what abort() leaves (AGENTS.md, «Coste de los tests»).
    if code is None:
        return "none"
    if code < 0 or code > 255:
        return f"{code} (0x{code & 0xFFFFFFFF:08X})"
    return str(code)


def _jobs_plan(test_files, declared, jobs: int):
    """``(chunks, lane, weights, timed, counts)``: the contiguous chunks of
    the files not in the serial lane, the lane, each file's expected seconds
    by name, whether those come from measured durations, and each file's
    declared tests by name."""
    counts: dict = {}
    for f, _cls, _m in (declared or ()):
        counts[f.name] = counts.get(f.name, 0) + 1
    lane = [f for f in test_files if serial_lane(f)]
    rest = [f for f in test_files if f not in lane]
    durations = load_durations()
    weights = file_weights(rest, counts, durations)
    chunks = [rest[a:b] for a, b in partition(weights, jobs)]
    timed = any(f.name in durations for f in rest)
    return chunks, lane, dict(zip((f.name for f in rest), weights)), timed, counts


def _print_plan(chunks, lane, weights, timed, counts) -> None:
    n = len(chunks)
    print(f"PARALLEL RUN — {n} chunk(s) at once"
          + (f", then {len(lane)} file(s) alone (SERIAL_LANE)" if lane else ""))
    for i, chunk in enumerate(chunks, 1):
        tests = sum(counts.get(f.name, 0) for f in chunk)
        # Minutes only when they were measured; balanced by test count
        # otherwise, and a count is not a duration.
        cost = (f", ~{sum(weights[f.name] for f in chunk) / 60:.1f} min by "
                f"the last durations" if timed else ", balanced by test count")
        span = (chunk[0].stem if len(chunk) == 1
                else f"{chunk[0].stem} … {chunk[-1].stem}")
        print(f"  chunk {i}/{n}: {span}  ({len(chunk)} file(s), "
              f"{tests} tests{cost})")
    if lane:
        print("  alone:     " + ", ".join(f.stem for f in lane))


def _run_jobs(tests_dir: Path, test_files, k, jobs: int, declared,
              banner) -> int:
    """The selection in ``jobs`` processes at once, then the serial lane.

    The verdict is 0 only when every test passed, no file leaked, and the
    run is complete: every chunk wrote the end of every one of its files
    and its own end, exited with the code its results call for, and the
    tests run add up to the tests the source declares. A chunk that dies —
    an ``os._exit``, an abort, a crash in Qt — is a failure named with its
    exit code and the file it died in, never a shorter green run.
    """
    chunks, lane, weights, timed, counts = _jobs_plan(test_files, declared,
                                                      jobs)
    total = len(declared) if declared is not None else 0
    plan = [(f"{i}/{len(chunks)}", c) for i, c in enumerate(chunks, 1)]
    if lane:
        plan.append(("serial lane", lane))
    if banner:
        print(banner)
    _print_plan(chunks, lane, weights, timed, counts)

    work = Path(tempfile.mkdtemp(prefix="ogr_test_jobs_"))
    runner = str(Path(__file__).resolve())
    procs: list = []
    test_offset = file_offset = 0
    for i, (label, files) in enumerate(plan):
        spec = {"files": [str(f.resolve()) for f in files], "k": k,
                "total": total, "test_offset": test_offset,
                "file_offset": file_offset, "n_files": len(test_files),
                "report": str(work / f"report_{i}.jsonl")}
        (work / f"spec_{i}.json").write_text(json.dumps(spec), encoding="utf-8")
        test_offset += sum(counts.get(f.name, 0) for f in files)
        file_offset += len(files)

    def start(i):
        # The console is inherited on purpose: without one the program
        # sends its own pools to pythonw.exe (ogr_slip2d.processes), and a
        # chunk would test something the serial run does not.
        with open(work / f"log_{i}.txt", "wb") as out:
            return subprocess.Popen(
                [sys.executable, "-u", runner, "--child",
                 str(work / f"spec_{i}.json")],
                stdout=out, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL)

    n_parallel = len(chunks)
    try:
        procs = [start(i) for i in range(n_parallel)]
        for i in range(len(plan)):
            if i == n_parallel:
                # The lane starts once every chunk has ended: following them
                # in order, the last one followed was the last to matter.
                procs.append(start(i))
            _follow(work / f"log_{i}.txt", procs[i])
    except BaseException:
        for p in procs:
            if p.poll() is None:
                p.kill()
        raise

    passed = failed = skipped = leaked = 0
    details: list = []
    died: list = []
    times: dict = {}
    for i, ((label, files), proc) in enumerate(zip(plan, procs)):
        try:
            records = [json.loads(line) for line in
                       (work / f"report_{i}.jsonl").read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError):
            records = []
        done = [r for r in records if "file" in r]
        for r in done:
            passed += r["passed"]
            failed += r["failed"]
            skipped += r["skipped"]
            leaked += bool(r["leaks"])
            details += [tuple(d) for d in r["details"]]
            times[r["file"]] = r["seconds"]
        names = [f.name for f in files]
        names_done = [r["file"] for r in done]
        ended = any(r.get("end") for r in records)
        bad = any(r["failed"] or r["leaks"] for r in done)
        if not ended or names_done != names:
            where = (names[len(names_done)] if len(names_done) < len(names)
                     else "its end")
            after = names_done[-1] if names_done else "no file"
            died.append(f"chunk {label} died: exit {_exit_code(proc.returncode)}"
                        f" in {where}, after {after}; "
                        f"{len(names) - len(names_done)} of its {len(names)}"
                        f" file(s) did not finish (log: {work / f'log_{i}.txt'})")
        elif proc.returncode != (1 if bad else 0):
            died.append(f"chunk {label} ran its {len(names)} file(s) but "
                        f"exited {_exit_code(proc.returncode)} "
                        f"(log: {work / f'log_{i}.txt'})")
    ran = passed + failed + skipped
    if total and not died and ran != total:
        died.append(f"the source declares {total} test(s) and the chunks "
                    f"ran {ran}")

    print("\n" + "=" * 60)
    for line in died:
        print(f"✗ [CHUNK] {line}")
    print(_totals_line(passed, failed, skipped, leaked, len(died)))
    # Until the owner decides otherwise (plan of the suite audit, stage 4),
    # the release check is the serial run: said with the numbers, so that
    # they cannot be pasted as one.
    print(f"PARALLEL RUN — {len(chunks)} chunk(s)"
          + (" + serial lane" if lane else "")
          + "; a release still needs the serial run (AGENTS.md)")
    if banner:
        print(banner)
    if details or died:
        print("\n--- FAILURE DETAILS ---")
        for line in died:
            print(f"\n[CHUNK]\n{line}")
        for name, tb in details[:10]:
            print(f"\n[{name}]\n{tb}")

    if not k and tests_dir.resolve() == Path(__file__).resolve().parent:
        save_durations(times)
    if not died:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if failed == 0 and leaked == 0 and not died else 1


def main(tests_dir: Path, patterns=(), k: str | None = None,
         list_only: bool = False, jobs: int = 1,
         child: str | None = None) -> int:
    # The ✓/✗ marks below are not printable in the console codepage Windows
    # picks when stdout is redirected (cp1252), and the UnicodeEncodeError
    # lands *inside* the except branch that reports a failure — so a single
    # unprintable character turns a full run into a traceback. Widening the
    # encoding here keeps `python tests/_runner.py > log.txt` usable.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # non-reconfigurable stream
        pass

    # v0.1.207 — the MCP server now works on an OPEN WINDOW by default, and
    # finds it through a discovery folder in the user's home. A test that
    # starts a server (in process or as a child) must never find the
    # user's real window and edit their model: the whole run, children
    # included, gets an empty folder of its own. A test that wants a window
    # makes one and points this variable at it, as before.
    os.environ["OGR_BRIDGE_DIR"] = tempfile.mkdtemp(prefix="ogr_test_bridges_")
    # v0.1.289 (D290) — and the saved preferences (language, theme) live in
    # a folder of the run's own, never in the user's registry.
    os.environ["OGR_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="ogr_test_settings_")

    # Before anything else: which tree is this about to measure? See
    # foreign_packages() for why a run that answers this wrongly is worse
    # than a run that fails.
    repo_root = tests_dir.parent
    origins = package_origins()
    strangers = foreign_packages(origins, repo_root)
    if strangers:
        print("WRONG TREE — this suite would not test the code you are "
              "editing.")
        for name, where in strangers:
            print(f"  {name} resolves to "
                  f"{where if where else '(not importable)'}")
        print(f"  this runner lives in {repo_root}")
        print("An ogr_* package resolving outside the runner's own "
              "repository usually means an editable install is answering "
              "the import. Put the tree first on sys.path, or reinstall, "
              "then run again.")
        return 2
    if child is None:
        # A chunk of --jobs says nothing of its own: the run that started it
        # printed this line, and prints the totals.
        print(provenance(repo_root, origins))
    # v0.1.302 (D310) — cyclic garbage found on a worker thread (a process
    # pool's, a compute thread's) is held for the main thread instead of
    # handed to shiboken's deferred deletion, which aborted the suite about
    # one run in two (see ogr_gui/gc_guard.py). After the provenance check:
    # it imports from the tree just checked.
    from ogr_gui import gc_guard
    gc_guard.install()
    leaks = _leak_detector()
    if child is not None:
        return _run_chunk(Path(child), leaks, gc_guard)
    if jobs < 1:
        print(f"--jobs takes a number of processes, 1 or more; got {jobs}.")
        return 2

    patterns = list(patterns)
    every = sorted(tests_dir.glob("test_*.py"))
    test_files = select_files(tests_dir, patterns)
    filtered = bool(patterns) or bool(k)

    def _banner() -> str:
        bits = []
        if patterns:
            bits.append(f"patterns: {patterns}")
        if k:
            bits.append(f"-k {k!r}")
        return (f"FILTERED RUN — {len(test_files)} of {len(every)} files"
                f", {', '.join(bits)} — NOT the full suite")

    if not test_files:
        print(f"No test file matches {patterns}.")
        near = _suggest(every, patterns)
        if near:
            print("Did you mean: " + ", ".join(near))
        print(f"{len(every)} files available — "
              f"`python tests/_runner.py --list` shows them all.")
        return 2

    declared = _declared_tests(test_files, k)
    if k and declared is not None and not declared:
        print(f"No test name matches -k {k!r} "
              f"in the {len(test_files)} selected file(s):")
        for f in test_files:
            print(f"  {f.name}")
        print("`--list` without -k shows the test names available.")
        return 2

    if list_only:
        if declared is None:
            # Silence here would read as "this selection has no tests",
            # when what happened is that the source could not be parsed.
            print(f"Cannot list: one of the {len(test_files)} selected "
                  f"file(s) does not parse. Run them to see the error.")
            return 2
        for f, cls, m_name in declared:
            print(f"{f.name}::{cls}::{m_name}")
        print(f"\n{len(declared)} test(s) in {len(test_files)} file(s)"
              f" of {len(every)}. Nothing was run.")
        if jobs > 1:
            print()
            _print_plan(*_jobs_plan(test_files, declared, jobs))
        return 0

    if jobs > 1:
        return _run_jobs(tests_dir, test_files, k, jobs, declared,
                         _banner() if filtered else None)

    tally = _Tally(len(declared) if declared is not None else 0)
    if filtered:
        print(_banner())
    times: dict = {}
    _run_files(test_files, k, tally, leaks, gc_guard,
               on_file=lambda f, record: times.update(
                   {f.name: record["seconds"]}))

    print("\n" + "=" * 60)
    print(_totals_line(tally.passed, tally.failed, tally.skipped,
                       tally.leaked))
    # Repeated after the totals on purpose: a green partial run pasted
    # into a changelog or a release check is indistinguishable from a
    # green full suite unless the line travels with the numbers.
    if filtered:
        print(_banner())

    if tally.fail_details:
        print("\n--- FAILURE DETAILS ---")
        for name, tb in tally.fail_details[:10]:
            print(f"\n[{name}]\n{tb}")

    # v0.1.375 — what each file took, for the chunks of a later --jobs; not
    # under -k (part of a file), nor for a copy of this runner pointed at
    # another folder (the self-tests' throwaway files).
    if not k and tests_dir.resolve() == Path(__file__).resolve().parent:
        save_durations(times)
    return 0 if tally.failed == 0 and tally.leaked == 0 else 1


def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="python tests/_runner.py",
        description="Run the OGR test suite, or a selected part of it.",
        epilog="With no arguments it runs everything, which is what CI does.")
    p.add_argument(
        "patterns", nargs="*", metavar="PATTERN",
        help="run only files whose name contains this (case-insensitive). "
             "A path or a file name works too: `transient`, "
             "`test_transient_v130.py` and `tests/test_transient_v130.py` "
             "all select the same file.")
    p.add_argument(
        "-k", metavar="SUBSTRING", default=None,
        help="run only tests whose 'Class.method' contains this "
             "(case-insensitive substring; no and/or/not grammar).")
    p.add_argument(
        "--list", dest="list_only", action="store_true",
        help="print the selected tests and exit without running them "
             "(with --jobs, also the chunks it would run).")
    p.add_argument(
        "--jobs", "-j", type=int, default=1, metavar="N",
        help="run in N processes at once: contiguous chunks of the "
             "alphabetical order, balanced by the last durations, then the "
             "files marked SERIAL_LANE alone. A chunk that dies fails the "
             "run. Without it the run is serial, as in CI.")
    # How a run with --jobs starts each chunk; not for typing.
    p.add_argument("--child", metavar="SPEC", default=None,
                   help=argparse.SUPPRESS)
    return p.parse_args(argv)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root.parent))
    ns = _parse_args(sys.argv[1:])
    sys.exit(main(root, patterns=ns.patterns, k=ns.k, list_only=ns.list_only,
                  jobs=ns.jobs, child=ns.child))
