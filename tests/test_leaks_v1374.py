# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.374 — the runner names what a test file leaves in the process, at the
file that leaves it, and the run fails (``tests/_leaks.py``).

Invariants protected:

1. **The four leaks injected in the suite audit fail the file that leaves
   them**, each under its own key: the language left in Spanish, an
   environment variable, a constant of the engine and a method of one of
   its classes. A file that changes the same things and puts them back is
   not named. The run exits 1 and its totals say ``Leaks: 4`` while
   ``Failed`` stays 0: the tests passed, the files did not.
2. **What the rules allow, and only that**, on synthetic snapshots: a
   library may move what its first import moves, in the file that imports
   it and no other; a value from a test file is a leak even on a key never
   seen; a builtin static member of Qt put back by attribute access is the
   same member, while a Python function put back bare where its
   staticmethod was is not (qtpy's wrappers of ``QFileDialog`` are Python
   functions, so for those the difference is real); an object installed
   once may be installed again, not removed.
3. **The saved preferences are compared by their keys**: an INI file whose
   keys were all removed again is the same as none (how D-c is put back).
4. **A module attribute's value at import** is known only when the source
   assigns it once, to a literal (``VERSION`` of the About box is assigned
   four times, and comparing its first literal named a false leak).
5. **Every entry of ``ALLOWED`` says why.**

How: ``main()`` of a second copy of the runner over throwaway files, as
``test_runner_state_v1373`` does. The inner run shares this process, so its
leaks are this file's too: each is put back before this file ends — or the
outer runner names THIS file, which is the check working.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import _leaks  # noqa: E402

_TESTS = Path(__file__).resolve().parent
_FOLDERS = ("OGR_BRIDGE_DIR", "OGR_SETTINGS_DIR")
_VAR = "OGR_TEST_INJECTED_LEAK_V1374"

_FILES = {
    "test_a_language.py": '''
class TestA:
    def test_leaves_spanish(self):
        from ogr_gui.i18n import set_language
        set_language("es")
''',
    "test_b_environment.py": f'''
import os


class TestB:
    def test_leaves_a_variable(self):
        os.environ[{_VAR!r}] = "1"
''',
    "test_c_constant.py": '''
class TestC:
    def test_leaves_a_constant(self):
        import ogr_slip2d.search as s
        s._PARALLEL_MIN_CIRCLES = 1
''',
    "test_d_method.py": '''
class TestD:
    def test_leaves_a_method(self):
        from ogr_slip2d.search import GridSearch
        GridSearch._centres = lambda self, project: []
''',
    "test_e_puts_back.py": f'''
import os


class TestE:
    def test_changes_all_and_puts_back(self):
        import ogr_slip2d.search as s
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from ogr_gui.i18n import current_language, set_language
        from ogr_slip2d.search import GridSearch
        language, constant = current_language(), s._PARALLEL_MIN_CIRCLES
        method, warning = GridSearch._centres, QMessageBox.warning
        dialog = QFileDialog.__dict__["getOpenFileName"]
        try:
            set_language("en" if language != "en" else "es")
            os.environ[{_VAR!r} + "_E"] = "1"
            s._PARALLEL_MIN_CIRCLES = 2
            GridSearch._centres = lambda self, project: []
            QMessageBox.warning = staticmethod(lambda *a, **k: 0)
            QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
        finally:
            set_language(language)
            os.environ.pop({_VAR!r} + "_E", None)
            s._PARALLEL_MIN_CIRCLES = constant
            GridSearch._centres = method
            # read off the class and put back, as files of the suite do: a
            # builtin, bare where it had a staticmethod, the same thing
            QMessageBox.warning = warning
            # qtpy's wrapper is a Python function: back from __dict__
            QFileDialog.getOpenFileName = dialog
''',
}


def _load_runner():
    """The runner as a module of its own; the fake ``pytest`` it installs
    is put back (rule 5), as in ``test_runner_selection_v180``."""
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_leaks_under_test", _TESTS / "_runner.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


_SEEN: dict = {}


def _seen() -> dict:
    """Run the throwaway files once; their output, cut by file."""
    if _SEEN:
        return _SEEN
    from PySide6.QtWidgets import QApplication

    import ogr_slip2d.search as search
    from ogr_gui.i18n import current_language, set_language
    QApplication.instance() or QApplication([])
    runner = _load_runner()
    runner.foreign_packages = lambda origins, root: []
    folder = Path(tempfile.mkdtemp(prefix="ogr_test_leaks_"))
    for name, text in _FILES.items():
        (folder / name).write_text(text, encoding="utf-8")
    saved_path = list(sys.path)
    saved_env = {v: os.environ.get(v) for v in _FOLDERS}
    language = current_language()
    constant = search._PARALLEL_MIN_CIRCLES
    method = search.GridSearch.__dict__["_centres"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = runner.main(folder)
    finally:
        # What the throwaway files left, put back here (see the docstring).
        set_language(language)
        os.environ.pop(_VAR, None)
        search._PARALLEL_MIN_CIRCLES = constant
        search.GridSearch._centres = method
        sys.path[:] = saved_path
        for var, value in saved_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        for name in _FILES:
            sys.modules.pop(name[:-3], None)
        shutil.rmtree(folder, ignore_errors=True)
    text = buf.getvalue()
    by_file = dict(re.findall(r"=== (\S+) ===[^\n]*\n(.*?)(?=\n=== |\n=+\n)",
                              text, flags=re.S))
    _SEEN.update(code=code, text=text, by_file=by_file)
    return _SEEN


def _leaks_of(name: str) -> list:
    return [line.split("[LEAK] ", 1)[1]
            for line in _seen()["by_file"][name].splitlines()
            if "✗ [LEAK]" in line]


class TestTheInjectedLeaksFailTheirFile:
    def test_the_language_left_in_spanish(self):
        got = _leaks_of("test_a_language.py")
        assert [g for g in got if g.startswith("mod:ogr_gui.i18n._LANG:")], got
        assert got[0].endswith("→ 'es'"), got

    def test_an_environment_variable(self):
        got = _leaks_of("test_b_environment.py")
        assert got == [f"env:{_VAR}: (absent) → 1"], got

    def test_a_constant_of_the_engine(self):
        got = _leaks_of("test_c_constant.py")
        assert got == ["mod:ogr_slip2d.search._PARALLEL_MIN_CIRCLES: 400 → 1"], got

    def test_a_method_of_one_of_its_classes(self):
        got = _leaks_of("test_d_method.py")
        assert len(got) == 1, got
        assert got[0].startswith("cls:ogr_slip2d.search.GridSearch._centres:")
        # named as coming from a test file
        assert got[0].endswith(_leaks.FROM_A_TEST), got

    def test_a_file_that_puts_everything_back_is_not_named(self):
        assert _leaks_of("test_e_puts_back.py") == []

    def test_the_run_fails_and_says_how_many_files_leaked(self):
        s = _seen()
        assert s["code"] == 1, s["text"]
        assert "Total: 5    Passed: 5    Failed: 0    Leaks: 4" in s["text"], s["text"]


def _snap(modules=(), **values):
    s = dict(values)
    s["__modules__"] = frozenset(modules)
    return s


class TestTheRules:
    def test_a_first_import_moves_what_it_moves_in_its_own_file_only(self):
        before = _snap(["random"], **{"random.state": "#1"})
        assert _leaks.diff(before, _snap(["random", "rich", "rich.style"],
                                         **{"random.state": "#2"})) == []
        assert _leaks.diff(before, _snap(["random"],
                                         **{"random.state": "#2"})) != []

    def test_warning_filters_may_only_be_added_by_a_first_import(self):
        before = _snap(["warnings"], **{"warnings.filters": ("a",)})
        added = _snap(["warnings", "numpy"], **{"warnings.filters": ("a", "b")})
        removed = _snap(["warnings", "numpy"], **{"warnings.filters": ("b",)})
        assert _leaks.diff(before, added) == []
        assert _leaks.diff(before, removed) != []

    def test_a_value_from_a_test_file_is_a_leak_on_a_new_key(self):
        key = "qt.QFileDialog.getOpenFileName"
        assert _leaks.diff(_snap(), _snap(**{key: "function@1!test"})) != []
        assert _leaks.diff(_snap(), _snap(**{key: "builtin@1"})) == []

    def test_a_new_environment_variable_is_a_leak(self):
        assert _leaks.diff(_snap(), _snap(**{"env:X": "1"})) != []

    def test_a_key_that_disappears_is_a_leak(self):
        assert _leaks.diff(_snap(**{"env:X": "1"}), _snap()) != []

    def test_a_builtin_put_back_by_attribute_access_is_the_same(self):
        assert _leaks.value_of(staticmethod(len)) == _leaks.value_of(len)

    def test_a_python_function_put_back_bare_is_not(self):
        def f():
            pass
        assert _leaks.value_of(staticmethod(f)) == _leaks.value_of(staticmethod(f))
        assert _leaks.value_of(staticmethod(f)) != _leaks.value_of(f)

    def test_installed_once_or_again_but_never_removed(self):
        key = "mod:ogr_gui.wheel_guard._guard"
        assert _leaks.diff(_snap(**{key: "None"}),
                           _snap(**{key: "WheelGuard@1"})) == []
        assert _leaks.diff(_snap(**{key: "WheelGuard@1"}),
                           _snap(**{key: "WheelGuard@2"})) == []
        assert _leaks.diff(_snap(**{key: "WheelGuard@1"}),
                           _snap(**{key: "None"})) != []

    def test_the_automatic_backend_is_settled_once(self):
        assert _leaks.diff(_snap(**{"mpl.backend": "auto"}),
                           _snap(**{"mpl.backend": "'QtAgg'"})) == []
        assert _leaks.diff(_snap(**{"mpl.backend": "'QtAgg'"}),
                           _snap(**{"mpl.backend": "'Agg'"})) != []

    def test_a_table_filled_once_from_empty(self):
        # v0.1.375 — what a chunk of --jobs can fill in another file than
        # the one that imported it
        key = "mod:ogr_gui.core_messages._CATALOGUE"
        assert _leaks.diff(_snap(**{key: "dict@7:len=0#1"}),
                           _snap(**{key: "dict@7:len=482"})) == []
        assert _leaks.diff(_snap(**{key: "dict@7:len=482"}),
                           _snap(**{key: "dict@7:len=483"})) != []
        assert _leaks.diff(_snap(**{key: "dict@7:len=0#1"}),
                           _snap(**{key: "dict@8:len=482"})) != []

    def test_the_application_is_made_once_and_never_unmade(self):
        key = "builtins.qApp"
        assert _leaks.diff(_snap(**{key: "None"}),
                           _snap(**{key: "QApplication@1"})) == []
        assert _leaks.diff(_snap(**{key: "QApplication@1"}),
                           _snap(**{key: "None"})) != []

    def test_choosing_the_backend_may_turn_off_its_fallback_only(self):
        key = "mpl.rcParams"
        assert _leaks.diff(_snap(**{key: "[]"}),
                           _snap(**{key: "['backend_fallback']"})) == []
        assert _leaks.diff(_snap(**{key: "[]"}), _snap(
            **{key: "['backend_fallback', 'lines.linewidth']"})) != []
        assert _leaks.diff(_snap(**{key: "[]"}),
                           _snap(**{key: "['lines.linewidth']"})) != []


class TestTheSavedPreferences:
    def test_an_ini_with_its_keys_removed_is_the_same_as_none(self):
        folder = Path(tempfile.mkdtemp(prefix="ogr_test_leaks_ini_"))
        try:
            assert _leaks._folder_files(str(folder)) == ()
            ini = folder / "ogr-slip2d.ini"
            ini.write_text("[General]\ntheme=dark\n", encoding="utf-8")
            assert _leaks._folder_files(str(folder)) == (
                "ogr-slip2d.ini: [General] theme=dark",)
            ini.write_text("[General]\n", encoding="utf-8")
            assert _leaks._folder_files(str(folder)) == ()
        finally:
            shutil.rmtree(folder, ignore_errors=True)


class TestTheValueAtImport:
    def test_assigned_once_to_a_literal(self):
        import ogr_gui.i18n  # noqa: F401
        assert _leaks.import_default("ogr_gui.i18n", "_LANG") == "'en'"

    def test_assigned_four_times_is_unknown(self):
        import ogr_gui.dialogs.misc_dialogs  # noqa: F401
        assert _leaks.import_default("ogr_gui.dialogs.misc_dialogs",
                                     "VERSION") is None


class TestTheAllowList:
    def test_every_entry_says_why(self):
        for a in _leaks.ALLOWED:
            assert len(a.why) >= 20, a

    def test_every_entry_names_a_kind_of_key_the_snapshot_takes(self):
        kinds = ("mod:", "cls:", "env:", "qt.", "sys.", "warnings.",
                 "random.", "mpl.", "mp.", "builtins.")
        for a in _leaks.ALLOWED:
            assert a.key.startswith(kinds), a.key
