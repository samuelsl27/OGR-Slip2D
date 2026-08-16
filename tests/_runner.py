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
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import math
import sys
import tempfile
import traceback
from contextlib import contextmanager
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


class _FakePytest:
    approx = staticmethod(_approx)
    raises = staticmethod(_raises)


sys.modules["pytest"] = _FakePytest()  # type: ignore


# --- Selection --------------------------------------------------------
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
    bound(**kwargs)


def main(tests_dir: Path, patterns=(), k: str | None = None,
         list_only: bool = False) -> int:
    # The ✓/✗ marks below are not printable in the console codepage Windows
    # picks when stdout is redirected (cp1252), and the UnicodeEncodeError
    # lands *inside* the except branch that reports a failure — so a single
    # unprintable character turns a full run into a traceback. Widening the
    # encoding here keeps `python tests/_runner.py > log.txt` usable.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # non-reconfigurable stream
        pass

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
        return 0

    passed = 0
    failed = 0
    fail_details: list[tuple[str, str]] = []

    total_tests = len(declared) if declared is not None else 0
    n_files = len(test_files)
    # Fixed width, so the pass/fail marks stay in one column and the
    # output is still readable when it scrolls.
    w = len(str(total_tests)) if total_tests else 4

    def _tag() -> str:
        done = passed + failed
        if not total_tests:
            return f"[{done:>{w}}]"
        return f"[{done:>{w}}/{total_tests} {100.0 * done / total_tests:3.0f}%]"

    if filtered:
        print(_banner())

    for i_file, f in enumerate(test_files, 1):
        print(f"\n=== {f.name} ===  ({i_file}/{n_files})")
        try:
            mod = _load_module(f)
        except Exception as e:  # noqa: BLE001
            print(f"  [LOAD ERROR] {e}")
            fail_details.append((f.name, traceback.format_exc()))
            failed += 1
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
                try:
                    instance = cls()
                    _run_method(instance, m)
                    passed += 1
                    print(f"    {_tag()} ✓ {m_name}")
                except AssertionError as e:
                    failed += 1
                    print(f"    {_tag()} ✗ {m_name}: {e}")
                    fail_details.append((f"{name}.{m_name}", traceback.format_exc()))
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    print(f"    {_tag()} ✗ {m_name}: {type(e).__name__}: {e}")
                    fail_details.append((f"{name}.{m_name}", traceback.format_exc()))

    print("\n" + "=" * 60)
    print(f"Total: {passed + failed}    Passed: {passed}    Failed: {failed}")
    # Repeated after the totals on purpose: a green partial run pasted
    # into a changelog or a release check is indistinguishable from a
    # green full suite unless the line travels with the numbers.
    if filtered:
        print(_banner())

    if fail_details:
        print("\n--- FAILURE DETAILS ---")
        for name, tb in fail_details[:10]:
            print(f"\n[{name}]\n{tb}")

    return 0 if failed == 0 else 1


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
        help="print the selected tests and exit without running them.")
    return p.parse_args(argv)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root.parent))
    ns = _parse_args(sys.argv[1:])
    sys.exit(main(root, patterns=ns.patterns, k=ns.k, list_only=ns.list_only))
