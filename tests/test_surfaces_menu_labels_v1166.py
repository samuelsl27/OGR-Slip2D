# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.166 (D102) - the Surfaces menu labels say what their actions do.

"Add Surface" was the label of an action that adds no surface at all: it
enters ``ToolMode.DRAW_BLOCK_SEARCH`` and draws a Block Search object,
exactly as its own docstring said from the first public version. Three
lines below it in the same menu sits "Add Surface (centre and radius)...",
which really does add one. Two entries starting with the same words, and
the one a user reaches for first was the one that did something else.

The invariants protected here, and why each of them exists:

* the label is tied to the BEHAVIOUR, not to a snapshot of its text: the
  action is triggered and the canvas must end up in the Block Search draw
  mode. A test that only compared strings would go green on a label that
  had drifted away from its handler again;
* inside the Surfaces menu no label repeats another and none is a prefix
  of another. Scoped to that menu deliberately: measured over the 135
  registered actions there are seven legitimate prefix pairs elsewhere
  ("Save"/"Save As...", "Compute"/"Compute Statistics", ...), so a global
  version of this rule would fail for reasons that are not defects;
* no two actions anywhere share their text. That one IS global, and it
  protects a test rather than a user: ``test_menu_reachability_v142``
  identifies actions by TEXT against a set, so two actions with the same
  label are indistinguishable to it and a duplicate could hide an
  unreachable action - which is rule 3 itself;
* the label and the tooltip are translated. ``_mk`` calls ``tr(text)``
  with a VARIABLE, so the AST scanner of ``test_i18n_coverage_v141``
  cannot see a single action label; the census here is what keeps that
  hole from growing, and the budget is measured, not guessed;
* the icon key exists in the catalog. ``icon()`` answers an unknown key
  with a gear and says nothing, so renaming the key without touching
  ``icons.py`` would have shipped a gear on the toolbar in silence.

No assertion here fixes a factor of safety: this version does not touch a
single executable line of calculation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QToolBar
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


# Qt destroys the QMenus when the owning window is collected, and the
# walks below read them after construction.
_WINDOWS: list = []

# The action under test, and the label it used to carry.
_KEY = "block_object"
_OLD_LABEL = "Add Surface"

# Measured on 0.1.166: 27 of the 135 registered action labels have no
# Spanish entry, so they stay in English however the language is set.
# It must never grow. Lower it as they are translated; they are listed
# in the changelog of this version.
_LABELS_WITHOUT_SPANISH = 27


def _window():
    """One window for the whole file: building a MainWindow is expensive
    and every test here reads it rather than rebuilding it."""
    if _WINDOWS:
        return _WINDOWS[0]
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    # set_language BEFORE MainWindow: _mk translates once, at
    # construction, so a window built in Spanish would answer Spanish
    # text to every lookup below.
    set_language("en")
    w = MainWindow()
    _WINDOWS.append(w)
    return w


def _menu_texts(window, name):
    """Every action text under the top-level menu called ``name``,
    submenus included, as a LIST: a set is what hides a duplicate, which
    is the defect being fixed.

    The walk never hands a QMenu back to its caller. Holding a menu
    wrapper past the loop that produced it outlives the C++ object -
    "Internal C++ object (QMenu) already deleted" - which is the failure
    ``test_menu_reachability_v142`` documents at its own module level.
    """
    out = []
    found = False

    def walk(menu):
        for act in menu.actions():
            sub = act.menu()
            if sub is not None:
                walk(sub)
            elif act.text():
                out.append(act.text())

    for act in window.menuBar().actions():
        sub = act.menu()
        if sub is not None and act.text() == name:
            found = True
            walk(sub)
    assert found, "no %s menu" % name
    return out


@_requires_qt
class TestTheLabelSaysWhatItDoes:
    def test_the_label_names_block_search(self):
        assert "Block Search" in _window()._actions[_KEY].text()

    def test_no_action_is_called_add_surface_alone(self):
        """The bare name is free again, which is what P-D101 needs in
        order to give it to an action that really adds a surface."""
        same = [k for k, a in _window()._actions.items()
                if a.text() == _OLD_LABEL]
        assert not same, same

    def test_the_action_enters_the_block_search_draw_mode(self):
        """The identity that matters: the label is checked against what
        the handler DOES, not against another string.

        Block Search is set first on purpose: with any other search
        method this action used to open a modal QMessageBox, which blocks
        for ever without a screen. That modal was P-D103, closed in
        v0.1.167; the method is set here anyway, because what this test
        measures is the draw mode and not the guard.
        """
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        previous_method = w.project.settings.search.search_method
        previous_tool = w.canvas.tool_mode
        try:
            w.project.settings.search.search_method = "block"
            w.refresh_action_availability()
            w._actions[_KEY].trigger()
            assert w.canvas.tool_mode == ToolMode.DRAW_BLOCK_SEARCH
        finally:
            w.project.settings.search.search_method = previous_method
            w._set_tool(previous_tool)
            w.refresh_action_availability()


@_requires_qt
class TestTheSurfacesMenuDoesNotRepeatItself:
    def test_no_two_labels_are_equal(self):
        texts = _menu_texts(_window(), "Surfaces")
        repeated = sorted({t for t in texts if texts.count(t) > 1})
        assert not repeated, repeated

    def test_no_label_is_a_prefix_of_another(self):
        """The exact shape of D102: "Add Surface" and "Add Surface (centre
        and radius)...". Scoped to this menu - see the module docstring."""
        texts = _menu_texts(_window(), "Surfaces")
        pairs = [(a, b) for a in texts for b in texts
                 if a != b and b.startswith(a)]
        assert not pairs, pairs


@_requires_qt
class TestNoTwoActionsShareTheirText:
    def test_every_registered_action_has_its_own_text(self):
        """Protects ``test_menu_reachability_v142``, which identifies
        actions by text against a set."""
        w = _window()
        texts = [a.text() for a in w._actions.values() if a.text()]
        repeated = sorted({t for t in texts if texts.count(t) > 1})
        assert not repeated, repeated


@_requires_qt
class TestTheTextIsTranslated:
    def test_the_new_label_has_spanish(self):
        from ogr_gui.i18n import _DICTS
        assert _window()._actions[_KEY].text() in _DICTS["es"]

    def test_the_spanish_uses_the_projects_own_term(self):
        """Terminology, not a snapshot: the dictionary already renders
        "Block Search" this way, both in this action's own enabled
        tooltip and in "Block Search Options"."""
        from ogr_gui.i18n import _DICTS
        spanish = _DICTS["es"][_window()._actions[_KEY].text()]
        assert u"búsqueda por bloques" in spanish, spanish

    def test_the_disabled_tooltip_no_longer_says_add_surface(self):
        """The branch almost every user sees: Block Search is not the
        default method, so the action is normally greyed out."""
        w = _window()
        previous = w.project.settings.search.search_method
        try:
            w.project.settings.search.search_method = "grid"
            w.refresh_action_availability()
            tip = w._actions[_KEY].toolTip()
            assert not w._actions[_KEY].isEnabled()
            assert "Block Search" in tip
            assert not tip.startswith(_OLD_LABEL), tip
        finally:
            w.project.settings.search.search_method = previous
            w.refresh_action_availability()

    def test_the_disabled_tooltip_is_translated(self):
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.main_window import MainWindow
        previous = current_language()
        try:
            set_language("es")
            w = MainWindow()
            _WINDOWS.append(w)
            w.project.settings.search.search_method = "grid"
            w.refresh_action_availability()
            tip = w._actions[_KEY].toolTip()
            assert u"búsqueda por bloques" in tip, tip
        finally:
            # Rule 5: a test that leaves the language set breaks menu
            # tests it never heard of, and only in the full suite.
            set_language(previous)


@_requires_qt
class TestEveryActionLabelIsTranslatable:
    def test_labels_without_spanish_stay_within_budget(self):
        """The hole no test could see. It must not grow."""
        from ogr_gui.i18n import _DICTS
        w = _window()
        missing = sorted(a.text() for a in w._actions.values()
                         if a.text() and a.text() not in _DICTS["es"])
        assert len(missing) <= _LABELS_WITHOUT_SPANISH, \
            "%d action labels have no Spanish (budget %d): %s" % (
                len(missing), _LABELS_WITHOUT_SPANISH, missing[:10])

    def test_the_coverage_scanner_cannot_see_action_labels(self):
        """WHY the budget above has to exist, measured against the real
        scanner instead of asserted in a comment.

        ``_mk`` calls ``tr(text)`` with a variable, and the AST scanner
        only records literal constants passed to ``tr``. So an action
        label is invisible to it, while the very same words written
        inside a ``tr("...")`` call are not. Both halves are checked: an
        absence on its own would also pass if the scanner were broken.
        """
        from test_i18n_coverage_v141 import _wrapped_keys
        keys = _wrapped_keys()
        label = _window()._actions[_KEY].text()
        assert label not in keys, \
            "the scanner sees action labels now - lower the budget"
        assert ("Add a Block Search object (search window) on the model"
                in keys), "the scanner stopped seeing literal tr() keys"


@_requires_qt
class TestTheIconKey:
    def test_the_action_icon_key_is_in_the_catalog(self):
        """``icon()`` answers an unknown key with a gear and says
        nothing, and nothing else guards the catalog."""
        from ogr_gui.resources.icons import has
        assert has("block_object")

    def test_the_old_icon_key_is_gone(self):
        """A circle-dot for an action that draws a quadrilateral. The
        name goes back to being free for P-D101, whose three-point
        surface is what it described."""
        from ogr_gui.resources.icons import has
        assert not has("surface_3pts")


@_requires_qt
class TestWhatMustNotChange:
    def test_it_is_enabled_only_with_block_search(self):
        w = _window()
        previous = w.project.settings.search.search_method
        try:
            for method, expected in (("block", True), ("grid", False)):
                w.project.settings.search.search_method = method
                w.refresh_action_availability()
                assert w._actions[_KEY].isEnabled() is expected, method
        finally:
            w.project.settings.search.search_method = previous
            w.refresh_action_availability()

    def test_it_is_reachable_from_the_menu_bar(self):
        """Rule 3, on the renamed key."""
        w = _window()
        assert w._actions[_KEY].text() in _menu_texts(w, "Surfaces")

    def test_it_is_still_on_the_toolbar(self):
        """``_build_toolbar`` skips a key it does not recognise without a
        word, so a typo there removes the button in silence."""
        w = _window()
        action = w._actions[_KEY]
        assert any(action is a for tb in w.findChildren(QToolBar)
                   for a in tb.actions())

    def test_the_old_key_stays_in_the_dictionary(self):
        """"Add Surface" is NOT orphaned, which is what the prompt
        assumed: ``_add_surface_centre_radius`` uses it as the title of
        both its dialogs. Retiring it would have broken
        ``test_every_wrapped_key_has_spanish``."""
        from ogr_gui.i18n import _DICTS
        from test_i18n_coverage_v141 import _wrapped_keys
        assert _OLD_LABEL in _wrapped_keys()
        assert _OLD_LABEL in _DICTS["es"]
