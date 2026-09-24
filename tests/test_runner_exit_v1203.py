# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.203 — a test that calls ``sys.exit`` fails; it does not end the suite.

Invariant protected: ``tests/_runner.py::run_test`` turns a ``SystemExit``
raised by a test into that test's failure, with its reason, just like any
other exception. An assertion keeps its message; a pass is a pass.

Why this file exists. On 2026-09-24 the full suite for v0.1.202 stopped at
44 % with no totals. The test file of the next version was already in
``tests/``, and one of its tests called ``ogr_mcp.cli.main(["--attach"])``
on code that did not know the option yet. argparse answered with
``sys.exit(2)``, which is a ``BaseException``. The loop caught
``Exception`` only, so the exit went through it and ended the process
there: every file after that one went unrun. The exit code was 2, so it
was not a false green, but a whole run was lost to one test.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent


def _load_runner():
    """``tests/_runner.py`` by path; it is ``__main__`` when it runs.
    Loading it reinstalls the fake ``pytest`` — rule 5: put it back."""
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_exit_under_test", _TESTS / "_runner.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


_R = _load_runner()


class _Cases:
    def test_exits(self):
        sys.exit(2)

    def test_asserts(self):
        assert 1 == 2, "one is not two"

    def test_raises(self):
        raise ValueError("bad value")

    def test_passes(self):
        assert True


class TestATestThatExitsFails:
    def test_system_exit_is_that_tests_failure(self):
        why, tb = _R.run_test(_Cases, _Cases.test_exits)
        assert why == "SystemExit: 2", why
        assert "sys.exit(2)" in tb

    def test_the_other_outcomes_are_unchanged(self):
        assert _R.run_test(_Cases, _Cases.test_passes) == (None, None)
        why, _ = _R.run_test(_Cases, _Cases.test_asserts)
        assert why == "one is not two", why
        why, _ = _R.run_test(_Cases, _Cases.test_raises)
        assert why == "ValueError: bad value", why

    def test_the_loop_uses_it(self):
        """The run loop goes through ``run_test``: a helper the loop did
        not call would protect nothing."""
        src = (_TESTS / "_runner.py").read_text(encoding="utf-8")
        loop = src[src.index("for m_name, m in methods:"):]
        assert "run_test(cls, m)" in loop[:400]
        assert "except Exception" not in loop[:600]
