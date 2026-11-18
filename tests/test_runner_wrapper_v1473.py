# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.473 (spec 010) — what this repository says of itself to the shared
runner, and that it says it right.

Until v0.1.471 the runner lived in ``tests/_runner.py``, whole, and its tests
loaded it by path and used what it had inside. OGR Core 0.2.0 took it
(``ogr_core.testing.runner`` and ``ogr_core.testing.leaks``), and
``tests/_runner.py`` is now a wrapper that passes it this repository's
configuration. The invariants of the runner itself are tested in OGR-Core;
the ones that are this repository's are here. Where each one of the old files
went (``censo.md`` §4 of spec 010):

==============================  ===========================  =====================
Old file                        In OGR-Core                  Here
==============================  ===========================  =====================
test_runner_exit_v1203          test_runner_exit_v10         —
test_runner_selection_v180      test_runner_selection_v10    the real suite counts
test_runner_provenance_v189     test_runner_provenance_v10,  the five own and the
                                test_runner_shared_v10       shared one, the pin
test_runner_state_v1373         test_runner_state_v020       the run's two folders
test_runner_jobs_v1375          test_runner_jobs_v020        the three clock files
test_runner_fast_v1376          test_runner_fast_v020        the real slow list,
                                                             the 100, release.md,
                                                             the machine files
test_runner_shutdown_v1377      test_runner_shutdown_v020    —
test_leaks_v1374                test_leaks_v020              the ten entries and
                                                             their rules, the
                                                             language of ogr_gui
test_gc_guard_v1302 (1 case)    test_runner_shared_v10       the two Qt hooks
test_rules_moved_v1194 (1)      (none)                       an async test fails
==============================  ===========================  =====================

The last one has no test in OGR-Core, although its code is there
(``_run_method``): it stays here, against the shared runner, until OGR-Core
has its own (to be asked for its 0.2.1).
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent
sys.path.insert(0, str(_TESTS))

import _runner as W  # noqa: E402  (the wrapper)
from ogr_core.testing import leaks, runner  # noqa: E402


def _inside(path, root) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


# ----------------------------------------------------------------------
class TestThePackages:
    def test_the_five_own_resolve_in_this_repository(self):
        assert W.OWN == ("ogr_slip2d", "ogr_gui", "ogr_cli", "ogr_api",
                         "ogr_mcp")
        for name in W.OWN:
            spec = importlib.util.find_spec(name)
            assert spec is not None, name
            assert _inside(spec.origin, _ROOT), (name, spec.origin)

    def test_the_core_is_shared_and_lives_elsewhere(self):
        import ogr_core
        assert W.SHARED == ("ogr_core",)
        assert not _inside(ogr_core.__file__, _ROOT), ogr_core.__file__

    def test_the_two_copies_are_gone(self):
        """Its code is changed only in OGR-Core (AGENTS.md): a folder of
        either name here would be a second core, and an ``ogr_fem2d`` would
        take the name of the third program."""
        assert not (_ROOT / "ogr_core").exists()
        assert not (_ROOT / "ogr_fem2d").exists()

    def test_the_pin_is_the_core_that_is_imported(self):
        import ogr_core
        assert W.pinned() == {"ogr_core": ogr_core.__version__}


class TestWithoutAPinNothingRuns:
    def test_it_exits_with_two(self):
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_wrapper_"))
        try:
            (folder / "tests").mkdir()
            shutil.copyfile(_TESTS / "_runner.py", folder / "tests" / "_runner.py")
            text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
            unpinned = re.sub(r'^\s*"ogr-core @[^"]*",\n', "", text, flags=re.M)
            assert unpinned != text
            (folder / "pyproject.toml").write_text(unpinned, encoding="utf-8")
            done = subprocess.run(
                [sys.executable, str(folder / "tests" / "_runner.py"), "--list"],
                capture_output=True, text=True, timeout=120)
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        assert done.returncode == 2, done.stdout + done.stderr
        assert "does not pin ogr-core" in done.stdout


class TestTheRealSuite:
    def test_it_counts_past_a_thousand(self):
        # a count that collapses to a handful means the AST walk stopped
        # seeing classes (v0.1.80)
        assert runner._count_tests(runner.select_files(_TESTS, ())) > 1000

    def test_the_three_clock_files_are_marked(self):
        marked = sorted(p.name for p in _TESTS.glob("test_*.py")
                        if runner.serial_lane(p))
        assert marked == ["test_jobs_file_race_v1198.py",
                          "test_optimizations_v111.py",
                          "test_remote_oauth_v1204.py"]

    def test_the_slow_list_names_only_files_that_exist(self):
        path = _TESTS / runner.SLOW_LIST_NAME
        listed = runner.load_slow_list(path)
        assert listed, "tests/_slow.txt is missing or empty"
        present = {p.name for p in _TESTS.glob("test_*.py")}
        assert sorted(listed - present) == []
        licence = Path(__file__).read_text(encoding="utf-8").splitlines()[:2]
        assert path.read_text(encoding="utf-8").splitlines()[:2] == licence


class TestTheOwnersRules:
    def test_one_hundred_commits_here_and_in_agents_md(self):
        assert W.SERIAL_EVERY == 100
        assert W.config()["serial_every"] == 100
        agents = (_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        assert re.search(rf"\b{W.SERIAL_EVERY} commits\b", agents)
        assert "--jobs 4" in agents

    def test_the_release_command_reads_the_notice(self):
        text = (_ROOT / ".claude" / "commands" / "release.md").read_text(
            encoding="utf-8")
        assert "--jobs 4" in text and "SERIAL RUN DUE" in text

    def test_the_machine_files_keep_their_names(self):
        """The durations measured before the move are not lost: the shared
        runner names its files after the label (``records_for``)."""
        r = runner.records_for(W.config()["label"])
        assert [p.name for p in (r.durations, r.test_times, r.serial)] == [
            "ogr-slip2d-test-durations.json", "ogr-slip2d-test-times.json",
            "ogr-slip2d-serial-run.json"]


class TestTheRunsFolders:
    def test_the_two_folders(self):
        assert W.RUN_FOLDERS == {"OGR_BRIDGE_DIR": "bridges",
                                 "OGR_SETTINGS_DIR": "settings"}

    def test_this_run_has_them_and_they_are_not_the_users(self):
        """The window's discovery folder and the saved preferences are the
        run's, never the person's (v0.1.207, v0.1.289)."""
        for var in W.RUN_FOLDERS:
            folder = os.environ.get(var)
            assert folder, var
            assert _inside(folder, tempfile.gettempdir()), (var, folder)


# ----------------------------------------------------------------------
def _snap(**values):
    s = dict(values)
    s["__modules__"] = frozenset()
    return s


def _diff(before, after):
    return leaks.diff(before, after, tuple(leaks.ALLOWED) + tuple(W.ALLOWED))


class TestTheTenEntries:
    def test_they_are_ten_and_none_is_the_suites(self):
        keys = [a.key for a in W.ALLOWED]
        assert len(keys) == 10, keys
        assert not set(keys) & {a.key for a in leaks.ALLOWED}

    def test_every_entry_says_why(self):
        for a in W.ALLOWED:
            assert len(a.why) >= 20, a

    def test_every_entry_names_a_kind_of_key_the_snapshot_takes(self):
        kinds = ("mod:", "cls:", "env:", "qt.", "sys.", "warnings.",
                 "random.", "mpl.", "mp.", "builtins.")
        for a in W.ALLOWED:
            assert a.key.startswith(kinds), a.key

    def test_installed_once_or_again_but_never_removed(self):
        key = "mod:ogr_gui.wheel_guard._guard"
        assert _diff(_snap(**{key: "None"}), _snap(**{key: "WheelGuard@1"})) == []
        assert _diff(_snap(**{key: "WheelGuard@1"}),
                     _snap(**{key: "WheelGuard@2"})) == []
        assert _diff(_snap(**{key: "WheelGuard@1"}), _snap(**{key: "None"})) != []

    def test_a_table_filled_once_from_empty(self):
        key = "mod:ogr_gui.core_messages._CATALOGUE"
        assert _diff(_snap(**{key: "dict@7:len=0#1"}),
                     _snap(**{key: "dict@7:len=482"})) == []
        assert _diff(_snap(**{key: "dict@7:len=482"}),
                     _snap(**{key: "dict@7:len=483"})) != []
        assert _diff(_snap(**{key: "dict@7:len=0#1"}),
                     _snap(**{key: "dict@8:len=482"})) != []

    def test_choosing_the_backend_may_turn_off_its_fallback_only(self):
        key = "mpl.rcParams"
        assert _diff(_snap(**{key: "[]"}),
                     _snap(**{key: "['backend_fallback']"})) == []
        assert _diff(_snap(**{key: "[]"}), _snap(
            **{key: "['backend_fallback', 'lines.linewidth']"})) != []
        assert _diff(_snap(**{key: "[]"}),
                     _snap(**{key: "['lines.linewidth']"})) != []

    def test_the_children_may_go_windowless_only(self):
        key = "mp.executable"
        assert _diff(_snap(**{key: "'C:\\\\py\\\\python.exe'"}),
                     _snap(**{key: "'C:\\\\py\\\\pythonw.exe'"})) == []
        assert _diff(_snap(**{key: "'C:\\\\py\\\\python.exe'"}),
                     _snap(**{key: "'C:\\\\other\\\\python.exe'"})) != []

    def test_without_them_the_programs_changes_are_leaks(self):
        """The suite's list alone does not hide them: they are this
        repository's to declare."""
        key = "mod:ogr_gui.wheel_guard._guard"
        assert leaks.diff(_snap(**{key: "None"}),
                          _snap(**{key: "WheelGuard@1"})) != []


class TestTheLanguageOfTheWindowIsALeak:
    def test_left_in_spanish(self):
        import ogr_gui.i18n  # noqa: F401
        from ogr_gui.i18n import current_language, set_language
        language = current_language()
        before = leaks.snapshot()
        try:
            set_language("es" if language != "es" else "en")
            after = leaks.snapshot()
        finally:
            set_language(language)
        keys = [k for k, _, _ in _diff(before, after)]
        assert "mod:ogr_gui.i18n._LANG" in keys, keys

    def test_its_value_at_import(self):
        import ogr_gui.i18n  # noqa: F401
        assert leaks.import_default("ogr_gui.i18n", "_LANG") == "'en'"


# ----------------------------------------------------------------------
class TestTheQtHooks:
    def test_before_the_run_the_guard_is_installed(self):
        from ogr_gui import gc_guard
        W.HOOKS.before_run()
        assert gc_guard.installed()

    def test_before_each_file_its_garbage_is_freed(self):
        from ogr_gui import gc_guard
        gc_guard._kept.append([object()])
        W.HOOKS.before_file()
        assert gc_guard._kept == []


class TestAnAsyncTestFails:
    """v0.1.194 -- an ``async def`` test returns a coroutine without running
    a line of its body: counted as a pass, it tested nothing. The shared
    runner keeps the rule (``_run_method``); OGR-Core has no test of it
    yet."""

    def test_it_fails_instead_of_passing_empty(self):
        ran = []

        class Case:
            async def test_async(self):
                ran.append(True)

            def test_plain(self):
                ran.append("plain")

        with pytest.raises(TypeError):
            runner._run_method(Case(), Case.test_async)
        assert ran == []
        runner._run_method(Case(), Case.test_plain)
        assert ran == ["plain"]
