# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.160 — No commercial product name anywhere in the source.

WHAT INVARIANT THIS PROTECTS. ``AGENTS.md`` allows reading the commercial
documentation in ``docs/reference/`` to learn WHAT a function does and how the
interface should behave, but forbids the code from carrying any reference to
those products or their trademarks, or from copying their text; formulas are
cited by their original scientific source. Nothing measured that rule, and it
had been broken since the first public commit: on 2026-09-11, with v0.1.159,
the tree named the reference product **159 times in 55 files** (ogr_core 40,
ogr_slip2d 28, ogr_gui 50, tests 41), and nine passages reproduced sentences
of its documentation between quotation marks.

The rule is not cosmetic. This project is published under AGPL, and the
provenance of a formula is the difference between a citation a reader can
check — Bishop (1955), Spencer (1967), Greco (1996), Su (2009) — and a name
that only says which program happened to be on the author's screen.

WHY THE NAMES ARE ASSEMBLED FROM FRAGMENTS BELOW. Spelled out, this file would
be the only place in the tree still carrying them: the grep in D126's closing
criterion would return these very lines, and this test would have to exempt
ITSELF — the one exemption a guard like this cannot afford, because it is the
file most likely to grow the next one. ``test_license_v143`` skips itself when
it hunts for stale GPL identifiers, for want of an alternative; here there is
one, so the exception list is empty and nothing at all is skipped.

WHY THE PATTERN IS WIDER THAN THE DEFECT REPORT'S. That report used an
expression anchored with a word boundary after an optional single digit, and
it does NOT match the third-product spelling (there is no word boundary
between a letter and the digit that follows it) — which is exactly what
``ogr_core/support/support.py:6`` carried. It also cannot see the file names
of the product's help system, which are a reference to its documentation just
as much as the trademark is: 10 such lines, 6 of them with no trademark on the
same line to give them away.

WHAT IS DELIBERATELY NOT FORBIDDEN. The validation tests name the reference
model files they read their numbers from. Those are file names on disk in
``referencias/``, the verification bank, which MAY name the program whose
manual it reproduces; they are the provenance of a measured number, and
deleting them would leave a validated factor of safety with nothing to check
it against, which is rule 1 turned off to satisfy this one.
``test_the_pattern_leaves_the_bank_provenance_alone`` and
``test_the_provenance_is_still_written_in_the_validation_tests`` pin that
boundary from both sides, so it cannot drift in either direction.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TREES = ("ogr_core", "ogr_slip2d", "ogr_fem2d", "ogr_gui", "ogr_cli", "tests")

# Split on purpose — see the docstring. The halves are meaningless apart, so
# this file does not match its own pattern and needs no exemption.
_NAME = "Sli" + "de"
_BRANDS = ("Rocs" + "cience", "GeoSt" + "udio", "SLO" + "PE/W", "SE" + "EP/W")
_HELP_FILES = ("Water_" + "Parameters", "Add_Material_" + "Boundary",
               "Define_Tension_" + "Crack", "Strenght_" + "Type",
               "Surface_" + "Options")

# ``\b<name>[0-9]?\b`` catches the bare name and both numbered products, and
# still leaves the bank's ``<name>2d_Ej_1_General`` alone: the optional digit
# is followed by a letter there, so no word boundary closes the match.
_FORBIDDEN = re.compile("|".join(
    [r"\b" + _NAME + r"[0-9]?\b"]
    + [re.escape(s) for s in _BRANDS + _HELP_FILES]))

# EMPTY ON PURPOSE, and nothing is skipped either. Adding a path here has to be
# a written decision, visible in a diff, and not a quiet habit — which is how
# the 159 occurrences accumulated in the first place.
_EXCEPTIONS: frozenset = frozenset()


def _sources():
    for tree in _TREES:
        for f in glob.glob(str(_ROOT / tree / "**" / "*.py"), recursive=True):
            if "__pycache__" in f:
                continue
            p = Path(f)
            if str(p.relative_to(_ROOT)).replace("\\", "/") in _EXCEPTIONS:
                continue
            yield p


class TestNoVendorNames:
    def test_no_source_file_names_the_reference_product(self):
        hits = []
        for p in _sources():
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if _FORBIDDEN.search(line):
                    hits.append("%s:%d: %s" % (
                        p.relative_to(_ROOT), n, line.strip()[:90]))
        assert not hits, (
            "%d line(s) name the reference product or its help files. Cite the "
            "original scientific source, or say \"the reference\":\n%s"
            % (len(hits), "\n".join(hits[:20])))

    def test_this_file_is_scanned_like_every_other(self):
        """The guard has to be inside what it guards. If a later edit spells a
        name out here, the test above must catch it like any other file."""
        assert Path(__file__).resolve() in {p.resolve() for p in _sources()}

    def test_the_exception_list_stays_empty(self):
        """An exception must cost a decision. If this ever needs to hold a
        path, the reason belongs in the changelog next to it."""
        assert _EXCEPTIONS == frozenset()


class TestThePatternItself:
    def test_it_catches_every_spelling_the_tree_actually_had(self):
        """Taken from the v0.1.159 inventory, not invented: each of these was a
        real line somewhere in the five packages or in tests."""
        muestras = ["(%s convention)" % _NAME, "per %s2 rules" % _NAME,
                    "the %s2/%s3 documentation" % (_NAME, _NAME),
                    "%s's rule" % _NAME, "%s-style default" % _NAME,
                    "per %s's %s.htm" % (_NAME, _HELP_FILES[0])]
        muestras += list(_BRANDS)
        muestras += ["%s.htm" % _HELP_FILES[1], "%s.pdf" % _HELP_FILES[3],
                     "%s.pdf" % _HELP_FILES[4], "%s.htm" % _HELP_FILES[2]]
        for m in muestras:
            assert _FORBIDDEN.search(m), m

    def test_the_pattern_leaves_the_bank_provenance_alone(self):
        """The bank's own file names are data provenance, not a brand in the
        code: a validated number has to say which file it was read from."""
        for m in ("%s2d_Ej_1_General.s01" % _NAME,
                  "%s2d_Ej_2_General.htm" % _NAME,
                  "02_%s2_Problema079/modelo_1_path.ogr" % _NAME):
            assert not _FORBIDDEN.search(m), m

    def test_the_provenance_is_still_written_in_the_validation_tests(self):
        """The other half of the same decision: if a later cleanup deletes the
        file names, the numbers stop being checkable and rule 1 is what
        breaks, not this one."""
        for archivo, n in (("test_slide_validation_ej1.py", 1),
                           ("test_slide_validation_ej2_v184.py", 2)):
            txt = (_ROOT / "tests" / archivo).read_text(encoding="utf-8")
            assert "%s2d_Ej_%d_General" % (_NAME, n) in txt, archivo
