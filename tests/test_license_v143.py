# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.43 — Licence consistency.

The project moved from GPL-3.0-or-later to **AGPL-3.0-or-later** so that a
modified version offered as a network service must publish its source,
while ordinary use — including paid engineering work — stays completely
free and unencumbered.

Licence metadata is the kind of thing that drifts silently: a new file
without a header, or a stale identifier left behind in packaging
metadata, and the project ships inconsistent terms. These tests make that
a build failure.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SPDX = "SPDX-License-Identifier: AGPL-3.0-or-later"


def _sources():
    for f in glob.glob(str(_ROOT / "**" / "*.py"), recursive=True):
        if "__pycache__" in f:
            continue
        yield Path(f)


class TestSpdxHeaders:
    def test_every_source_file_declares_the_licence(self):
        """A file without an SPDX header is invisible to licence tooling
        and ambiguous to a reader."""
        missing = [str(p.relative_to(_ROOT)) for p in _sources()
                   if _SPDX not in p.read_text(encoding="utf-8")]
        assert not missing, (
            f"{len(missing)} files without an SPDX header: {missing[:10]}")

    def test_header_is_near_the_top(self):
        """It must be in the first few lines, where tooling looks."""
        for p in _sources():
            head = p.read_text(encoding="utf-8").split("\n")[:6]
            assert any(_SPDX in ln for ln in head), p.name

    def test_no_stale_gpl_identifiers(self):
        """The plain GPL identifier must not survive anywhere: an
        AGPL project carrying GPL headers states two different things."""
        stale = []
        for p in _sources():
            # This file quotes the identifier as data, so scanning it
            # would match its own source.
            if p.name == Path(__file__).name:
                continue
            txt = p.read_text(encoding="utf-8")
            for m in re.finditer(r"SPDX-License-Identifier:\s*(\S+)", txt):
                if m.group(1) != "AGPL-3.0-or-later":
                    stale.append((p.name, m.group(1)))
        assert not stale, stale

    def test_copyright_line_present(self):
        missing = [p.name for p in _sources()
                   if "Copyright (C) 2026 Samuel Sáez López"
                   not in p.read_text(encoding="utf-8")]
        assert not missing, missing[:10]


class TestPackagingMetadata:
    def test_pyproject_declares_agpl(self):
        txt = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'license = {text = "AGPL-3.0-or-later"}' in txt
        assert "GNU Affero General Public License" in txt

    def test_pyproject_has_no_plain_gpl_left(self):
        txt = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "GPL-3.0-or-later" not in txt.replace(
            "AGPL-3.0-or-later", "")
        assert "(GPLv3+)" not in txt


class TestLicenceFiles:
    def test_license_file_is_agpl(self):
        txt = (_ROOT / "LICENSE").read_text(encoding="utf-8")
        assert "GNU AFFERO GENERAL PUBLIC LICENSE" in txt
        assert "Affero" in txt

    def test_license_contains_the_verbatim_text(self):
        """v0.1.45 — the full licence text is now shipped, replacing the
        earlier stub. Conveying an AGPL work without the verbatim licence
        fails its own section 4, so this is a distribution requirement and
        not a nicety."""
        txt = (_ROOT / "LICENSE").read_text(encoding="utf-8")
        assert "GNU AFFERO GENERAL PUBLIC LICENSE" in txt
        assert "Version 3, 19 November 2007" in txt
        # Section 13 is the whole reason for choosing AGPL over GPL
        assert "13. Remote Network Interaction" in txt
        assert "END OF TERMS AND CONDITIONS" in txt
        assert "Copyright (C) 2007 Free Software Foundation" in txt
        # All seventeen numbered sections present
        for n in range(18):
            assert f"\n{n}. " in txt or f"\n  {n}. " in txt, n
        assert len(txt) > 30000, len(txt)

    def test_license_carries_the_project_notice(self):
        txt = (_ROOT / "LICENSE").read_text(encoding="utf-8")
        assert "Copyright (C) 2026 Samuel Sáez López" in txt
        assert "commercial engineering work" in txt

    def test_cla_exists_and_explains_the_grant(self):
        p = _ROOT / "CLA.md"
        assert p.exists()
        txt = p.read_text(encoding="utf-8")
        # The essential points a contributor must be able to find
        assert "You keep your copyright" in txt
        assert "other than the AGPL" in txt
        assert "not an assignment" in txt

    def test_contributors_file_references_the_cla(self):
        txt = (_ROOT / "CONTRIBUTORS.md").read_text(encoding="utf-8")
        assert "CLA.md" in txt

    def test_readme_explains_the_practical_effect(self):
        # Two READMEs since the first public release: README.md in English
        # (what a visitor arriving from GitHub or opengeorock.org reads) and
        # README.es.md in Spanish. Both are checked, and the phrases checked
        # are the ones actually shipped in each language — a reader who only
        # opens the Spanish one must still find the warranty notice, so
        # testing a single file would leave half the audience unguarded.
        expected = {
            "README.md": (
                "professional engineering work",
                "remotely over a network",
                "There is no warranty of any kind",
                "checked against independent calculations",
            ),
            "README.es.md": (
                "trabajo profesional de ingeniería",
                "en remoto a través de una red",
                "No hay garantía",
                "contrastarse con cálculos independientes",
            ),
        }
        for name, phrases in expected.items():
            raw = (_ROOT / name).read_text(encoding="utf-8")
            # Collapse whitespace: the wording is wrapped across lines, so a
            # plain substring search would miss it.
            txt = " ".join(raw.split())
            assert "AGPL-3.0-or-later" in txt, name
            for phrase in phrases:
                assert phrase in txt, (name, phrase)

    def test_the_two_readmes_link_to_each_other(self):
        """A translation nobody can find from the other one is not a
        translation; it is a file that silently goes stale."""
        assert "README.es.md" in (_ROOT / "README.md").read_text(encoding="utf-8")
        assert "README.md" in (_ROOT / "README.es.md").read_text(encoding="utf-8")
