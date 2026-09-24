# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.41 — Internationalisation coverage.

The audit reported i18n as "partial", and measuring it showed the real
problem was not missing translations but strings that never reached the
translation layer at all: only 62 strings were wrapped in ``tr()`` (in 8
of some 30 GUI files) while **380 user-visible strings were not**. A user
switching to Spanish would still see those in English, because they never
consult the dictionary.

These tests lock in the coverage so it cannot silently decay:

* every key wrapped in ``tr()`` anywhere in the GUI must have a Spanish
  translation — the check that would have caught the original gap;
* a translation must not be left equal to the English text (a sign of a
  forgotten entry);
* the number of unwrapped user-visible strings must not grow beyond the
  recorded budget, so new dialogs cannot reintroduce the problem;
* switching language actually changes what the widgets show.
"""
from __future__ import annotations

import glob
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_gui.i18n import (  # noqa: E402
    _DICTS,
    available_languages,
    current_language,
    set_language,
    tr,
)

_ROOT = Path(__file__).resolve().parent.parent
_GUI = _ROOT / "ogr_gui"

# Constructors and setters whose literal argument is shown to the user.
_VISIBLE = [
    r'setWindowTitle\(\s*"([^"]+)"',
    r'QLabel\(\s*"([^"]+)"',
    r'QPushButton\(\s*"([^"]+)"',
    r'QCheckBox\(\s*"([^"]+)"',
    r'QGroupBox\(\s*"([^"]+)"',
    r'addRow\(\s*"([^"]+)"',
    r'setText\(\s*"([^"]+)"',
]

# Budget of still-unwrapped strings. Lower it as coverage improves; it
# must never be raised.
_UNWRAPPED_BUDGET = 210

# v0.1.167 (D103) - a SECOND list with a SECOND budget, deliberately not
# seven more entries in _VISIBLE. The patterns above match constructors
# and setters; none of them sees `QMessageBox.*(self, "...")` or
# `showMessage("...")`, which is how the eight strings of the Block
# Search action stayed invisible to this file. Folding them into the
# count above would put 68 message strings under the same ceiling as 20
# dialog strings and make the history of the 210 unreadable.
#
# EVERY PATTERN CAPTURES EXACTLY ONE GROUP, and the alternation uses
# `(?:...)` on purpose: measured, a second capturing group makes
# `re.findall` return TUPLES, and `_unwrapped_count` then calls
# `.startswith("%")` on a tuple -> AttributeError. The D103 ficha
# proposed these patterns with capturing groups.
_VISIBLE_MESSAGES = [
    r'showMessage\(\s*"([^"]+)"',
    r'QMessageBox\.(?:information|warning|critical|question)'
    r'\(\s*self,\s*"([^"]+)"',
]

# Measured the day it landed (v0.1.167): 68. It was 70 before this
# version dropped the modal of the Block Search action and wrapped that
# action's draw prompt. Same rule as _UNWRAPPED_BUDGET - lower it as
# coverage improves, never raise it - but pinned to the REAL count
# instead of a comfortable ceiling, so the next unwrapped message box
# fails this file. The 210 above has run against a real count of 20
# since it was written, which is a control that cannot fail.
# v0.1.198 — 68 -> 67: Change Slope Angle's unwrapped "no external"
# message box went with the rewrite (its message now goes through tr()).
_UNWRAPPED_BUDGET_MESSAGES = 67


def _gui_sources():
    for f in glob.glob(str(_GUI / "**" / "*.py"), recursive=True):
        if os.path.basename(os.path.dirname(f)) == "i18n":
            continue
        yield f, open(f, encoding="utf-8").read()


def _wrapped_keys():
    """Every key passed to ``tr()``, extracted with the AST.

    A regex cannot do this correctly: Python's implicit string
    concatenation means

        tr("Press Preview to check the "
           "geometry before importing.")

    passes ONE joined string at runtime, while a regex sees only the first
    fragment and then reports a perfectly translated key as missing. The
    AST gives the concatenated value, which is what ``tr`` actually
    receives.
    """
    import ast as _ast

    keys = set()
    for _f, src in _gui_sources():
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name != "tr" or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, _ast.Constant) and isinstance(arg.value,
                                                             str):
                keys.add(arg.value)
    return keys


def _unwrapped_count(patterns=None):
    """Visible strings without ``tr()`` that ``patterns`` can see.

    v0.1.167 - the argument exists so the second list is measured with
    the SAME filter as the first: two filters would make the two
    budgets incomparable. Called with no argument the behaviour is
    identical to before, which is what keeps the history of the 210
    meaningful. The default is a sentinel and not ``patterns=_VISIBLE``
    so that the list is read at call time, not frozen at import.
    """
    n = 0
    for _f, src in _gui_sources():
        for pat in (_VISIBLE if patterns is None else patterns):
            for m in re.findall(pat, src):
                if len(m) > 1 and any(c.isalpha() for c in m) \
                        and not m.startswith("%") and "{" not in m:
                    n += 1
    return n


class TestTranslationCompleteness:
    def test_every_wrapped_key_has_spanish(self):
        """The check the project lacked: a string routed through tr()
        with no Spanish entry silently stays in English."""
        es = _DICTS["es"]
        missing = sorted(k for k in _wrapped_keys() if k not in es)
        assert not missing, (
            f"{len(missing)} keys without Spanish: {missing[:15]}")

    def test_spanish_dictionary_is_substantial(self):
        assert len(_DICTS["es"]) > 300

    def test_no_lazy_identity_translations(self):
        """A Spanish value identical to its English key usually means a
        forgotten entry. A short allow-list covers the genuine cases
        (proper nouns, symbols, units)."""
        # Words that are legitimately identical in Spanish: proper nouns
        # (Monte Carlo), cognates (Horizontal, Error, Color), acronyms
        # kept as-is on the status bar so the two languages read the same
        # width, and pure format strings.
        allowed = {"OGR Slip2D", "A:", "B:", "C:", "a:", "n:", "nx:",
                   "ny:", "x:", "y:", "Sx:", "Sy:", "OK", "General",
                   "Material:", "K2 / K1:", "Manual:", "Fill",
                   "X: 0.000   Y: 0.000", "Advanced", "Basic",
                   "k_h (horizontal):", "k_v (vertical):", "Auto",
                   "Tolerance (ε):", "Model:", "Type:", "Units:",
                   "Mark FoS = 1.0", "Hatch pattern", "Color", "Colour",
                   "no", "Monte Carlo", "Horizontal:", "Vertical:",
                   "   |   FS = %s", "%s — %s (%d)", "Error", "Color:",
                   "Zoom", "Snap", "SNAP", "OSNAP", "ORTHO", "GRID",
                   # v0.1.72 — the drawdown envelope summaries. Notation
                   # only: the same symbols name the same quantities in
                   # both languages, so a "translation" that differed
                   # would be wrong rather than more Spanish.
                   "R: Cr = %.4g, φR = %.4g°",
                   "Kc = 1: d = %.4g, ψ = %.4g°",
                   # v0.1.74 — cognate, like Horizontal above: the
                   # interslice force function shape is "Trapezoidal" in
                   # both languages.
                   "Trapezoidal",
                   # v0.1.87 — the slice-data panel names one of its rows
                   # and one of its section headers after the material,
                   # and "material" is the same word in Spanish. The
                   # entries exist because the panel translates its labels
                   # through a variable, so tr() has to find them in the
                   # dictionary; they are identical because translating
                   # them would be inventing a difference.
                   "Material", "─ Material ─",
                   # v0.1.122 — the equivalent-fluid retaining wall's
                   # profile shapes. "Triangular" is the same word in
                   # Spanish, exactly as "Trapezoidal" above already was;
                   # the other two of the four ARE translated ("Uniform" →
                   # "Uniforme", "Custom" → "Personalizado"), which is what
                   # says these two are cognates and not forgotten entries.
                   "Triangular",
                   # v0.1.123 — the pile failure mode of Ito and Matsui
                   # (1975). A proper noun, like "Monte Carlo" above: the
                   # OTHER mode of the same combo IS translated ("Shear" →
                   # "Cortante"), which is what says this one is a name and
                   # not a forgotten entry.
                   "Ito & Matsui",
                   # v0.1.127 - the symbol for the critical seismic
                   # coefficient, in the same class as "Cr:", "d:" and
                   # "mi:" above: notation, not prose. The words around
                   # it ARE translated ("Critical acceleration:" ->
                   # "Aceleracion critica:"), which is what says this one
                   # is a symbol and not a forgotten entry.
                   "Ky:"}
        same = [k for k, v in _DICTS["es"].items()
                if k == v and k not in allowed]
        assert len(same) < 12, same[:15]

    def test_english_is_the_reference(self):
        """English keys pass through unchanged."""
        set_language("en")
        try:
            assert tr("Materials") == "Materials"
            assert tr("Water Table") == "Water Table"
        finally:
            set_language("es")

    def test_unknown_key_returns_itself(self):
        set_language("es")
        assert tr("a key that does not exist") == \
            "a key that does not exist"


class TestCoverageBudget:
    def test_unwrapped_strings_stay_within_budget(self):
        """Coverage must not decay: new dialogs cannot reintroduce
        untranslatable text without lowering this budget deliberately."""
        n = _unwrapped_count()
        assert n <= _UNWRAPPED_BUDGET, (
            f"{n} user-visible strings are not wrapped in tr() "
            f"(budget {_UNWRAPPED_BUDGET}).")

    def test_message_box_strings_stay_within_their_own_budget(self):
        """v0.1.167 (D103). Modal titles and status-bar messages were
        invisible to the seven patterns above, so the budget above never
        counted them: wrapping one of them could not move it by a point,
        which is why the ficha's own closing criterion -'the unwrapped
        budget lowered by six'- was unreachable as written."""
        n = _unwrapped_count(_VISIBLE_MESSAGES)
        assert n <= _UNWRAPPED_BUDGET_MESSAGES, (
            f"{n} message-box titles and status-bar messages are not "
            f"wrapped in tr() (budget {_UNWRAPPED_BUDGET_MESSAGES}).")

    def test_the_message_budget_is_not_a_ghost(self):
        """Kept apart from the test above on purpose, so a failure says
        WHICH of the two broke: that one means coverage decayed, this
        one means the control went slack.

        _UNWRAPPED_BUDGET has stood at 210 against a real count of 20
        since it was written - `n <= 210` cannot fail, so it stopped
        being a measurement. Pinning this one to the measured count is
        what keeps it from ending up the same way.
        """
        n = _unwrapped_count(_VISIBLE_MESSAGES)
        assert n == _UNWRAPPED_BUDGET_MESSAGES, (
            f"the real count is {n}; set _UNWRAPPED_BUDGET_MESSAGES to "
            f"{n} (it is {_UNWRAPPED_BUDGET_MESSAGES}). Lowering it is "
            f"the point; raising it needs a reason in a changelog.")

    def test_every_pattern_captures_exactly_one_group(self):
        """Measured, not assumed: `re.findall` returns tuples for a
        pattern with two groups, and `_unwrapped_count` then calls
        `.startswith` on a tuple. Both lists are checked because the
        crash does not care which list the pattern came from."""
        for pat in _VISIBLE + _VISIBLE_MESSAGES:
            assert re.compile(pat).groups == 1, pat

    def test_the_default_scan_is_unchanged_by_the_parameter(self):
        """The refactor that made room for the second list must not
        have moved the first count."""
        assert _unwrapped_count() == _unwrapped_count(_VISIBLE)
        assert _UNWRAPPED_BUDGET == 210

    def test_a_useful_number_of_strings_are_wrapped(self):
        assert len(_wrapped_keys()) > 250

    def test_key_dialogs_are_covered(self):
        """Spot-check the files the audit flagged as worst."""
        for name in ("dialogs/random_variables_dialog.py",
                     "dialogs/transient_stages_dialog.py",
                     "dialogs/hydraulic_properties_dialog.py",
                     "statistics_window.py"):
            src = open(_GUI / name, encoding="utf-8").read()
            assert 'tr("' in src, name


class TestLanguageSwitching:
    """Every test here restores English on exit: leaving the language set
    to Spanish leaked into other suites, where translated menu titles no
    longer matched the names being looked up."""

    def teardown_method(self, _m=None):
        set_language("en")

    def test_switching_changes_the_text(self):
        set_language("es")
        assert tr("Materials") == "Materiales"
        set_language("en")
        assert tr("Materials") == "Materials"
        set_language("es")

    def test_available_languages(self):
        langs = available_languages()
        assert "en" in langs and "es" in langs

    def test_current_language_reported(self):
        set_language("es")
        assert current_language() == "es"
        set_language("en")
        assert current_language() == "en"
        set_language("es")

    def test_geotechnical_terms_are_correct(self):
        """Terminology matters more than literal translation: these are
        the standard Spanish geotechnical terms."""
        set_language("es")
        expected = {
            "Water Table": "Nivel freático",
            "Tension Crack": "Grieta de tracción",
            "Boundary Conditions": "Condiciones de contorno",
            "Standard deviation:": "Desviación típica:",
            "Number of slices:": "Número de dovelas:",
        }
        for k, v in expected.items():
            assert tr(k) == v, (k, tr(k))

    def test_dialog_shows_translated_title(self):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            return
        QApplication.instance() or QApplication([])
        set_language("es")
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog,
        )
        d = RandomVariablesDialog(_ej1_project(), None)
        assert "Estadística" in d.windowTitle()
