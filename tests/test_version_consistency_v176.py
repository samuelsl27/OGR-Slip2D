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
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Every file that states the version, and how to find it in that file.
_SOURCES = {
    "pyproject.toml": r'^version\s*=\s*"([^"]+)"',
    "ogr_core/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_slip2d/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_fem2d/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_gui/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_cli/__init__.py": r'^__version__\s*=\s*"([^"]+)"',
    "ogr_gui/main_window.py": r'^\s*VERSION\s*=\s*"([^"]+)"',
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
