# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.76 — every package agrees on which version this is.

Invariant protected: the version in ``pyproject.toml``, the one the About
box shows, and the ``__version__`` of all five packages are the same
string.

Why. AGENTS.md lists four places to bump per release, and there are
seven. The three it omits had been frozen at **0.1.59 since v0.1.59**:
``ogr_core``, ``ogr_gui`` and ``ogr_cli``. Nothing broke, which is the
problem — ``ogr_cli.__version__`` reported 0.1.59 while the CLI shipped
inside a 0.1.75 distribution, so a bug report quoting it would have sent
the reader sixteen releases into the past.

A checklist in a document is only as good as the reader's attention; this
makes the omission fail the build instead.

v0.1.473 (spec 010) -- seven sites, not nine: ``ogr_core`` and ``ogr_fem2d``
left this repository for OGR-Core, whose own series of versions the core
keeps (0.2.0 for that one, 0.2.1 since v0.1.474, 0.2.2 since v0.1.475).
What this program says of the core is the version it pins in
``pyproject.toml``, and the ``ogr_core`` that is imported
must be that one: the runner refuses another before a single test runs, and
this file says it too, for whoever imports the program outside the runner.

v0.1.475 (OGR Core 0.2.2) -- **the run measures the core the runner held it
to.** OGR-Core runs this suite against the core of each of its PRs, with
``--dev-core``: the imported core is then a ``X.Y.Z.devN`` of a release
later than the pin, and "imported == pinned" failed by construction (one of
the three red tests of the first such run, on 302a97c). In an ordinary run
the core held to is the pinned one, exactly; in a development run, the one
``--dev-core`` accepts and nothing else. The runner gives that check whole
(``shared_problems`` with ``dev_core_run()``), and both tests of the pin
(this one and ``test_runner_wrapper_v1473``) ask :func:`core_problems`, so
that the cases below can prove what it accepts and refuses. Outside the
runner the variable is not set, and the check is the strict one.
"""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from ogr_core.testing import runner

_ROOT = Path(__file__).resolve().parent.parent


def core_problems(origins=None, pinned=None, dev=None) -> list:
    """Why the core this process imports is not the one the run was held
    to; empty when it is. By default: the real ``ogr_core``, the version
    ``pyproject.toml`` pins, and whether this run accepted a development
    version (``runner.dev_core_run()``)."""
    if origins is None:
        origins = runner.package_origins(("ogr_core",))
    if pinned is None:
        version = runner.pinned_from_pyproject(_ROOT / "pyproject.toml",
                                               "ogr-core")
        pinned = {"ogr_core": version} if version else {}
    if dev is None:
        dev = runner.dev_core_run()
    return runner.shared_problems(origins, pinned, dev_core=dev)

# Every file that states the version, and how to find it in that file.
_SOURCES = {
    "pyproject.toml": r'^version\s*=\s*"([^"]+)"',
    "ogr_slip2d/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_gui/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_cli/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_gui/main_window.py": r'^\s*VERSION\s*=\s*"([^"]+)"',
    # v0.1.194 (spec 008) — the operations layer is a sixth package, and
    # it enters this list the version it is born, not sixteen later.
    "ogr_api/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    # v0.1.195 — and the MCP server package, the ninth site.
    "ogr_mcp/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
}


def _declared() -> dict[str, str]:
    found = {}
    for rel, pattern in _SOURCES.items():
        text = (_ROOT / rel).read_text(encoding="utf-8")
        m = re.search(pattern, text, re.MULTILINE)
        assert m is not None, f"no version declaration found in {rel}"
        found[rel] = m.group(1)
    return found


class TestVersionConsistency:
    def test_all_packages_declare_the_same_version(self):
        """One release, one number.

        A package left behind does not fail at runtime — it just reports
        a version that was true a year ago, which is worse than none.
        """
        found = _declared()
        distinct = sorted(set(found.values()))
        assert len(distinct) == 1, (
            "the release version disagrees across files: "
            + ", ".join(f"{k} = {v}" for k, v in sorted(found.items())))

    def test_the_version_is_a_release_number(self):
        """Guards against a placeholder surviving into a release."""
        for rel, v in _declared().items():
            assert re.fullmatch(r"\d+\.\d+\.\d+([abrc.\-+].*)?", v), (rel, v)

    def test_the_changelog_for_this_version_exists(self):
        """A release without a changelog loses the half that matters.

        AGENTS.md asks each version to record what was *found*, not only
        what was written; the file has to be there for that to happen.
        """
        version = _declared()["pyproject.toml"]
        path = _ROOT / "docs" / "changelog" / f"CHANGELOG_v{version}.md"
        assert path.exists(), f"missing {path.relative_to(_ROOT)}"


class TestTheCoreIsThePinnedOne:
    def test_the_imported_core_is_the_version_pyproject_pins(self):
        import ogr_core
        pinned = runner.pinned_from_pyproject(_ROOT / "pyproject.toml",
                                              "ogr-core")
        assert pinned is not None, "pyproject.toml does not pin ogr-core"
        assert core_problems() == [], core_problems()
        if not runner.dev_core_run():
            assert ogr_core.__version__ == pinned, (ogr_core.__version__,
                                                    pinned)

    def test_the_two_old_sites_are_gone(self):
        assert not (_ROOT / "ogr_core").exists()
        assert not (_ROOT / "ogr_fem2d").exists()
        assert len(_SOURCES) == 7, sorted(_SOURCES)


# ----------------------------------------------------------------------
#: The pin of the cases below: invented, so that they say the same whatever
#: this repository pins.
_PIN = {"ogr_core": "0.2.2"}


def _verdicts(versions, dev):
    """``{version: passes}`` for an invented ``ogr_core`` declaring each
    version (``declared_version`` reads its ``__init__.py`` without running
    it), held to :data:`_PIN`."""
    root = Path(tempfile.mkdtemp(prefix="ogr_test_pin_"))
    try:
        out = {}
        for i, version in enumerate(versions):
            package = root / str(i) / "ogr_core"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text(
                f'__version__ = "{version}"\n', encoding="utf-8")
            out[version] = core_problems({"ogr_core": package}, _PIN,
                                         dev) == []
        return out
    finally:
        shutil.rmtree(root, ignore_errors=True)


class TestWhatTheCheckOfThePinAccepts:
    """v0.1.475 -- the teeth of :func:`core_problems`: what an ordinary run
    and a development run each let through."""

    def test_an_ordinary_run_takes_the_pinned_core_only(self):
        assert _verdicts(["0.2.2", "0.2.3.dev0", "0.2.2.dev0", "0.2.3",
                          "0.2.1"], dev=False) == {
            "0.2.2": True, "0.2.3.dev0": False, "0.2.2.dev0": False,
            "0.2.3": False, "0.2.1": False}

    def test_a_development_run_takes_a_dev_of_a_later_release_only(self):
        # 0.2.2.dev0 came BEFORE the pinned 0.2.2: an older core; an rc is
        # a core somebody called a release, not the core being changed
        assert _verdicts(["0.2.2", "0.2.3.dev0", "0.2.2.dev0", "0.2.1.dev0",
                          "0.2.3rc1", "0.2.3", "0.2.1"], dev=True) == {
            "0.2.2": True, "0.2.3.dev0": True, "0.2.2.dev0": False,
            "0.2.1.dev0": False, "0.2.3rc1": False, "0.2.3": False,
            "0.2.1": False}

    def test_by_default_it_follows_the_run(self):
        """What the two tests of the pin call: a development core passes
        exactly when this run is one that accepted it."""
        assert (_verdicts(["0.2.3.dev0"], dev=None)["0.2.3.dev0"]
                is runner.dev_core_run())

    def test_a_core_that_does_not_resolve_never_passes(self):
        for dev in (False, True):
            assert core_problems({"ogr_core": None}, _PIN, dev) != []
