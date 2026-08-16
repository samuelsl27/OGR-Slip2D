# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.80 — running part of the suite selects a part, and says so.

Invariant protected: ``tests/_runner.py`` accepts a selection, and

1. **with no selection it runs exactly what it ran before** — the file
   list is ``sorted(glob("test_*.py"))``, unchanged and unreordered,
   because that is the command in ``.github/workflows/tests.yml``; and
2. **a selection that matches nothing exits non-zero.**

Why this file exists. Until v0.1.80 the runner took no arguments at all:
``main(root)`` ran all 99 files, always. Measuring the suite showed why
that hurt — the four slowest files are 42 % of the seven minutes, while
the 58 fastest hold nearly half of the tests and cost under ten seconds
between them. Checking a change to one subsystem cost the whole suite.

The danger the selection introduces is not slowness, it is a false green.
``python tests/_runner.py transiant`` — one letter wrong — would find no
file, print ``Total: 0  Passed: 0  Failed: 0`` and exit 0, which reads
exactly like a suite that passed. Rule 7 asks that a new control be shown
to move the number; here the number that must move includes the **exit
code**, so that is tested too.

A trap for whoever edits this file: ``main()`` must only ever be called
here on paths that return *before* the run loop — an empty selection or
``--list``. Any call that reaches the loop while this file is selected
would run this file inside itself, for ever.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_SELF = Path(__file__).resolve()


def _quiet_main(**kwargs) -> tuple[int, str]:
    """``main()`` with its output captured, as ``(exit code, text)``.

    Captured rather than printed for two reasons: the runner's own log
    stays readable, and the *message* can be asserted on. An exit code of
    2 with a blank screen would be almost as unhelpful as exit 0.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _R.main(_TESTS, **kwargs)
    return code, buf.getvalue()


def _load_runner():
    """Import ``tests/_runner.py`` as a module, however we were launched.

    The runner is normally ``__main__``, so it cannot be imported by
    name. Loading it by path re-executes its body, which reinstalls the
    fake ``pytest`` module — an equivalent object, but a global mutation
    all the same. Rule 5: put back exactly what was there.
    """
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_under_test", _TESTS / "_runner.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


_R = _load_runner()


class TestTheCiPathIsUntouched:
    def test_no_patterns_selects_every_file(self):
        """The command CI runs must see the same list as before."""
        expected = sorted(_TESTS.glob("test_*.py"))
        assert _R.select_files(_TESTS, ()) == expected
        assert _R.select_files(_TESTS, []) == expected
        assert _R.select_files(_TESTS, None) == expected

    def test_no_patterns_counts_every_test(self):
        every = _R.select_files(_TESTS, ())
        # The suite is far past a thousand tests; a count that collapses
        # to a handful means the AST walk stopped seeing classes.
        assert _R._count_tests(every) > 1000

    def test_selection_never_reorders(self):
        """Reproducing a run in the same order is what makes a state leak
        findable at all — the failure rule 5 exists for."""
        picked = _R.select_files(_TESTS, ["test_"])
        assert picked == sorted(picked)
        assert picked == _R.select_files(_TESTS, ())


class TestFileSelection:
    def test_a_pattern_selects_strictly_fewer_files(self):
        """Rule 7: the control has to move the number."""
        every = _R.select_files(_TESTS, ())
        picked = _R.select_files(_TESTS, ["runner_selection"])
        assert 0 < len(picked) < len(every)
        assert all("runner_selection" in p.stem for p in picked)

    def test_several_patterns_are_a_union(self):
        a = set(_R.select_files(_TESTS, ["runner_selection"]))
        b = set(_R.select_files(_TESTS, ["geometry"]))
        both = set(_R.select_files(_TESTS, ["runner_selection", "geometry"]))
        assert a and b
        assert both == a | b

    def test_a_file_name_and_a_path_select_the_same_file(self):
        """All three shapes a pattern arrives in must agree, and none of
        them may depend on the current directory."""
        by_fragment = _R.select_files(_TESTS, ["runner_selection"])
        assert by_fragment == _R.select_files(_TESTS, [_SELF.name])
        assert by_fragment == _R.select_files(_TESTS, ["tests/" + _SELF.name])
        assert by_fragment == _R.select_files(_TESTS, [str(_SELF)])

    def test_matching_ignores_case(self):
        assert (_R.select_files(_TESTS, ["RUNNER_SELECTION"])
                == _R.select_files(_TESTS, ["runner_selection"]))

    def test_an_empty_pattern_selects_nothing_rather_than_everything(self):
        """An empty substring is inside every name, so the naive rule
        would silently select the whole suite while looking like a
        filter. It has to reach the empty-selection guard instead."""
        assert _R.select_files(_TESTS, [""]) == []
        assert _R.select_files(_TESTS, ["/"]) == []
        assert _R.select_files(_TESTS, [".py"]) == []


class TestNameFilter:
    def test_k_selects_only_matching_methods(self):
        everything = _R._declared_tests([_SELF])
        picked = _R._declared_tests([_SELF], "ignores_case")
        assert 0 < len(picked) < len(everything)
        assert all("ignores_case" in m for _, _, m in picked)

    def test_k_matches_the_class_name_too(self):
        picked = _R._declared_tests([_SELF], "TestNameFilter")
        assert picked
        assert all(cls == "TestNameFilter" for _, cls, _ in picked)

    def test_k_ignores_case(self):
        assert _R.match_test("TestX", "test_foo", "TEST_FOO")
        assert _R.match_test("TestX", "test_foo", "testx.TEST_")
        assert not _R.match_test("TestX", "test_foo", "test_bar")

    def test_no_k_keeps_everything(self):
        assert _R.match_test("TestX", "test_foo", None)
        assert _R.match_test("TestX", "test_foo", "")


class TestAnEmptySelectionIsAnError:
    """The whole point of the guard: a filter that finds nothing must not
    be reported the same way as a suite that passed.

    Both calls below return before the runner imports or executes
    anything — see the trap noted in the module docstring.
    """

    def test_a_file_pattern_matching_nothing_exits_non_zero(self):
        code, out = _quiet_main(patterns=["no-such-file-anywhere"])
        assert code == 2
        assert "no-such-file-anywhere" in out

    def test_a_k_matching_nothing_exits_non_zero(self):
        code, out = _quiet_main(patterns=[_SELF.name],
                                k="no-such-test-name-anywhere")
        assert code == 2
        assert "no-such-test-name-anywhere" in out

    def test_a_typo_is_told_what_it_probably_meant(self):
        """The suggestion is the difference between an exit code and an
        explanation: ``runner_selektion`` shares its first characters
        with the file that was meant."""
        code, out = _quiet_main(patterns=["runner_selektion"])
        assert code == 2
        assert "test_runner_selection_v180" in out


class TestListOnly:
    def test_list_only_reports_success_without_running_anything(self):
        """If this ever started running the selection it would run this
        very file inside itself, so a hang here is the symptom."""
        code, out = _quiet_main(patterns=[_SELF.name], list_only=True)
        assert code == 0
        assert "Nothing was run." in out
        # The listing names this very test, and naming it is all it did.
        assert "test_list_only_reports_success_without_running_anything" in out


class TestArgumentParsing:
    def test_no_arguments_means_no_filter(self):
        ns = _R._parse_args([])
        assert ns.patterns == [] and ns.k is None and ns.list_only is False

    def test_patterns_and_k_and_list_are_read(self):
        ns = _R._parse_args(["transient", "seepage", "-k", "erfc", "--list"])
        assert ns.patterns == ["transient", "seepage"]
        assert ns.k == "erfc"
        assert ns.list_only is True
