# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.203 — a test that calls ``sys.exit`` fails; it does not end the suite.

Invariant protected: ``tests/_runner.py::run_test`` turns a ``SystemExit``
raised by a test into that test's failure, with its reason, just like any
other exception. An assertion keeps its message; a pass is a pass.

v0.1.205 — and ``pytest.skip`` is a third outcome, "skipped", with its
reason: the shim had no ``skip``, so the one test that needs the
verification bank failed on GitHub (where the bank does not exist) with an
AttributeError. A skip is not a pass either: it is counted apart.

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

    # The skip of the runner UNDER TEST, not ``import pytest``: that is the
    # shim of the runner running this file, whose Skipped is another class
    # and would escape to it (both of these cases came out skipped that way).
    def test_skips(self):
        _R._FakePytest.skip("the bank is not on this machine")

    def test_skips_with_another_copys_pytest(self):
        # The pytest installed in sys.modules is the one of the runner that
        # runs THIS file: another copy, another Skipped class. That is what
        # a test doing ``import _runner`` produced on GitHub.
        import pytest
        pytest.skip("raised by another copy of the runner")

    def test_swallows_everything(self):
        try:
            _R._FakePytest.skip("still a skip")
        except Exception:                   # noqa: BLE001 - the point
            raise AssertionError("a test's except Exception caught the skip")

    def test_asserts(self):
        assert 1 == 2, "one is not two"

    def test_raises(self):
        raise ValueError("bad value")

    def test_passes(self):
        assert True


class TestATestThatExitsFails:
    def test_system_exit_is_that_tests_failure(self):
        outcome, why, tb = _R.run_test(_Cases, _Cases.test_exits)
        assert (outcome, why) == ("failed", "SystemExit: 2"), (outcome, why)
        assert "sys.exit(2)" in tb

    def test_the_other_outcomes_are_unchanged(self):
        assert _R.run_test(_Cases, _Cases.test_passes) == ("passed", None,
                                                          None)
        outcome, why, _ = _R.run_test(_Cases, _Cases.test_asserts)
        assert (outcome, why) == ("failed", "one is not two"), why
        outcome, why, _ = _R.run_test(_Cases, _Cases.test_raises)
        assert (outcome, why) == ("failed", "ValueError: bad value"), why


class TestASkipIsNeitherAPassNorAFailure:
    def test_it_is_skipped_with_its_reason(self):
        outcome, why, tb = _R.run_test(_Cases, _Cases.test_skips)
        assert (outcome, why, tb) == (
            "skipped", "the bank is not on this machine", None)

    def test_a_tests_except_exception_cannot_swallow_it(self):
        outcome, why, _ = _R.run_test(_Cases, _Cases.test_swallows_everything)
        assert (outcome, why) == ("skipped", "still a skip"), (outcome, why)

    def test_another_copys_skip_is_still_a_skip(self):
        """The first run of v0.1.205 on GitHub: a copy of the runner made
        by ``import _runner`` raised ITS Skipped, the running runner caught
        only its own class, and the suite ended at 83 % with no totals."""
        try:
            outcome, why, _ = _R.run_test(
                _Cases, _Cases.test_skips_with_another_copys_pytest)
        except BaseException as exc:        # noqa: BLE001 - the defect
            # Uncaught, it would reach the runner running THIS file and be
            # counted as this case's skip: a defect hidden as a skip.
            raise AssertionError(
                "the copy under test let another copy's skip through: %r"
                % (exc,)) from None
        assert (outcome, why) == ("skipped",
                                  "raised by another copy of the runner"), (
            outcome, why)

    def test_loading_the_runner_again_keeps_the_installed_shim(self):
        """Looked at WHILE loading, not after: ``_load_runner`` puts the
        shim back in its ``finally``, so asking after it proves nothing."""
        before = sys.modules.get("pytest")
        assert getattr(before, "ogr_shim", False), "no shim installed here"
        try:
            spec = importlib.util.spec_from_file_location(
                "_ogr_runner_loaded_again", _TESTS / "_runner.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            assert sys.modules.get("pytest") is before, (
                "loading the runner again replaced the installed pytest")
        finally:
            sys.modules["pytest"] = before

    def test_the_totals_name_it(self):
        src = (_TESTS / "_runner.py").read_text(encoding="utf-8")
        assert 'Skipped: {skipped}' in src

    def test_the_loop_uses_it(self):
        """The run loop goes through ``run_test``: a helper the loop did
        not call would protect nothing."""
        src = (_TESTS / "_runner.py").read_text(encoding="utf-8")
        loop = src[src.index("for m_name, m in methods:"):]
        assert "run_test(cls, m)" in loop[:400]
        assert "except Exception" not in loop[:800]
