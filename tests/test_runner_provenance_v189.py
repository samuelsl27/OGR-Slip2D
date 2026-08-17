# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.89 — the runner says which tree it is measuring, and refuses a foreign one.

WHAT INVARIANT THIS PROTECTS: that a run cannot silently measure a different
tree than the one being edited. Every other test in the suite assumes the
answer to "which code is this?" is obvious. It is not.

Why this file exists. Diagnosing the v0.1.84 fall of
``test_support_increases_fos``, a stand-alone script that replicated the test
line by line reported the SAME result for the working tree and for HEAD, while
instrumenting inside the runner showed 10 valid surfaces and a critical 2.1279
against 0 valid. The script would have led to the opposite conclusion, and for
three versions nobody could say why. It was not wrong about what it measured;
it was measuring the wrong tree, and nothing said so.

The mechanism, verified on this machine and fully deterministic:

1. ``python C:\\somewhere\\else\\script.py`` puts the SCRIPT's directory in
   ``sys.path[0]`` — not the working directory. This is the step that
   surprises: cd-ing into a tree does not put that tree on the path.
2. No ``ogr_*`` lives there, so ``PathFinder`` (position 2 of
   ``sys.meta_path``) finds nothing.
3. ``_EditableFinder`` (position 3), installed by ``pip install -e .``,
   answers instead — and resolves every ``ogr_*`` to one hard-coded absolute
   path, whichever tree was installed.

So a diagnostic kept outside the repository imports the main working tree no
matter which tree you cd into or which commit you check out. The decoy
experiment that settled it: with the cwd set to a directory containing its own
``ogr_slip2d`` package, the import still came from the installed path and the
decoy's ``MARKER`` never appeared.

The runner cannot fix other people's scripts. What it can do is name the tree
it is about to measure on every run, and refuse to run when that tree is not
its own — which is the case it CAN detect and the one that would poison an
entire suite rather than one diagnosis.

A trap for whoever edits this file: ``main()`` may only be called on paths
that return BEFORE the run loop, or this file runs itself for ever.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_ROOT = _TESTS.parent


def _load_runner():
    """Import ``tests/_runner.py`` by path; it is normally ``__main__``.

    Executing its body reinstalls the fake ``pytest`` module — an equivalent
    object, but a global mutation all the same. Rule 5: put back exactly what
    was there.
    """
    saved = sys.modules.get("pytest")
    try:
        spec = importlib.util.spec_from_file_location(
            "_ogr_runner_provenance_under_test", _TESTS / "_runner.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved is not None:
            sys.modules["pytest"] = saved
        else:
            sys.modules.pop("pytest", None)


_R = _load_runner()


class TestThisTreeIsTheOneMeasured:
    def test_every_package_resolves_inside_the_repository(self):
        origins = _R.package_origins()
        assert set(origins) == set(_R.PACKAGES), origins
        for name, where in origins.items():
            assert where is not None, f"{name} is not importable at all"
            # Raises ValueError if it is not under the root, which is
            # exactly the condition the guard tests for.
            where.relative_to(_ROOT)

    def test_no_strangers_here(self):
        assert _R.foreign_packages(_R.package_origins(), _ROOT) == []

    def test_each_package_is_its_own_directory_under_the_root(self):
        """Guards the banner: it collapses five paths into one by taking
        their common PARENT, which is only right if each package really is
        a directory directly under the tree."""
        for name, where in _R.package_origins().items():
            assert where.name == name, (name, where)
            assert where.parent == _ROOT, (name, where.parent)


class TestAForeignPackageIsRefused:
    """The synthetic cases. Real ones cannot be built without breaking the
    interpreter this suite is running in, so the check is a pure function of
    (origins, root) precisely so it can be tested with data."""

    def test_a_package_outside_the_root_is_flagged(self):
        origins = {"ogr_core": _ROOT / "ogr_core",
                   "ogr_slip2d": Path("C:/some/other/tree/ogr_slip2d")
                   if sys.platform == "win32"
                   else Path("/some/other/tree/ogr_slip2d")}
        bad = _R.foreign_packages(origins, _ROOT)
        assert [n for n, _ in bad] == ["ogr_slip2d"], bad

    def test_a_package_that_does_not_resolve_is_flagged(self):
        """None means find_spec found nothing. Not an absence of evidence:
        the tests are about to import it and fail one by one instead."""
        bad = _R.foreign_packages({"ogr_fem2d": None}, _ROOT)
        assert [n for n, _ in bad] == ["ogr_fem2d"], bad

    def test_a_sibling_tree_is_not_mistaken_for_this_one(self):
        """``OGR-Slip2D-copy`` starts with the same characters as
        ``OGR-Slip2D``. A prefix comparison on strings would accept it;
        relative_to on paths does not."""
        sibling = _ROOT.parent / (_ROOT.name + "-copy") / "ogr_gui"
        bad = _R.foreign_packages({"ogr_gui": sibling}, _ROOT)
        assert [n for n, _ in bad] == ["ogr_gui"], bad

    def test_the_message_names_the_offender_and_this_tree(self):
        """An exit code with a blank screen would be nearly as unhelpful as
        exit 0. The reader has to be told WHERE it looked."""
        buf = io.StringIO()
        saved = _R.package_origins
        try:
            _R.package_origins = lambda: {
                "ogr_core": Path("/elsewhere/ogr_core")}
            with contextlib.redirect_stdout(buf):
                code = _R.main(_TESTS)
        finally:
            _R.package_origins = saved
        text = buf.getvalue()
        assert code == 2, code
        assert "WRONG TREE" in text, text
        assert "ogr_core" in text, text
        assert str(_ROOT) in text, text
        # And it must not have run anything.
        assert "Total:" not in text, text


class TestResolutionExecutesNothing:
    """The guard runs BEFORE the first test, so it must not execute any
    module-level code. Importing the five packages to read their ``__file__``
    would run half the project's module bodies before anything is measured —
    the state leak rule 5 exists for. ``find_spec`` resolves through the same
    finders without executing, which is the whole reason it is used."""

    def test_find_spec_does_not_execute_the_module(self):
        # A stdlib module this suite has no reason to have imported. If a
        # future dependency imports it, pick another rather than deleting it
        # from sys.modules: that would create a second copy with its own
        # globals, which is the very failure being guarded against.
        victim = next((n for n in ("colorsys", "wave", "cgitb", "mailbox")
                       if n not in sys.modules), None)
        if victim is None:
            return          # nothing left to prove it with; not a failure
        spec = importlib.util.find_spec(victim)
        assert spec is not None and spec.origin, victim
        assert victim not in sys.modules, \
            f"find_spec executed {victim}; the guard would leak state"

    def test_package_origins_is_written_that_way(self):
        """Source-level, because the property above is only preserved as long
        as nobody 'simplifies' this into an import."""
        src = (_TESTS / "_runner.py").read_text(encoding="utf-8")
        body = src.split("def package_origins")[1].split("\ndef ")[0]
        assert "find_spec" in body, body
        for forbidden in ("import_module", "__import__"):
            assert forbidden not in body, forbidden


class TestTheBannerSaysSomethingUseful:
    def test_it_is_one_line_naming_the_tree(self):
        line = _R.provenance(_ROOT, _R.package_origins())
        assert "\n" not in line, line
        assert str(_ROOT) in line, line
        assert line.startswith("tree: "), line

    def test_it_falls_back_to_listing_when_the_tree_is_not_single(self):
        """A split resolution is exactly the situation worth seeing in full,
        so the collapsed form must not hide it."""
        origins = {"ogr_core": _ROOT / "ogr_core",
                   "ogr_gui": Path("/elsewhere/ogr_gui")}
        line = _R.provenance(_ROOT, origins)
        assert "ogr_core=" in line and "ogr_gui=" in line, line

    def test_head_sha_never_raises_and_looks_like_a_sha(self):
        sha = _R.head_sha(_ROOT)
        assert sha == "?" or (len(sha) == 7
                              and all(c in "0123456789abcdef" for c in sha)), \
            sha

    def test_head_sha_on_a_directory_without_git(self):
        """The banner must not be able to fail. A missing .git is a '?',
        not a traceback that stops the suite before it starts."""
        assert _R.head_sha(_TESTS) == "?"


class TestTheGuardDidNotBreakTheSelection:
    """v0.1.80's two rules still hold with a banner printed first."""

    def test_a_pattern_matching_nothing_still_exits_two(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _R.main(_TESTS, patterns=["definitivamente-no-existe"])
        assert code == 2, code
        assert "tree: " in buf.getvalue()

    def test_list_only_still_reports_success(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = _R.main(_TESTS, patterns=["runner_provenance"],
                           list_only=True)
        assert code == 0, code
        assert "Nothing was run." in buf.getvalue()
