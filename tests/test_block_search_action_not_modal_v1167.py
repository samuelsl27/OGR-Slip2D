# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.167 (D103) - the Block Search action states its precondition on the
status bar, never in a modal, and every string it shows is translatable.

``act_add_block_search_object`` opened a ``QMessageBox.information`` when
the search method was not Block Search. Without a screen a modal never
comes back, so any automated run that reached it hung for ever - the rule
AGENTS.md states outright, and the one v0.1.125 already answered this way
for the groundwater diagnostic. Its six literals and the two of the draw
prompt never went through ``tr()``.

The invariants protected here, and why each of them exists:

* the guard answers WITHOUT a modal, and the check is a real one: the
  four static constructors of ``QMessageBox`` are rebound to raise, so a
  box that came back would fail this file instead of hanging the suite.
  Rebinding the NAME in ``main_window`` and not the attribute on the Qt
  class is deliberate - ``main_window.QMessageBox is QMessageBox``, so
  patching the class would reach the whole of PySide6 and an escape
  before the ``finally`` would leave it patched for every later file,
  which is rule 5 in its most expensive form;
* the method is called DIRECTLY, never through ``trigger()``. The action
  is disabled outside Block Search and a disabled ``QAction`` ignores
  ``trigger()``, so a test written that way would have gone green
  against the defect. That is measured here rather than commented;
* the advice on the status bar is the SAME STRING as the disabled
  tooltip. One precondition, one text: a second sentence for the same
  rule is how a tooltip ends up contradicting what it describes, which
  is the defect D102 had just repaired one step above;
* what the fix must CONSERVE: with Block Search set, the action still
  enters ``ToolMode.DRAW_BLOCK_SEARCH``, and the guard still refuses to
  enter it otherwise;
* the two budgets of ``test_i18n_coverage_v141`` stay apart, and the
  patterns of the new one capture exactly one group.

On the ficha's own premises, measured against this tree and refuted:
its code quotations are from 0.1.159 and the action has been called
``act_add_block_search_object`` since D102; and its claim that only a
headless test can reach the box is false in the worse direction - the
embedded terminal hands ``mainwindow`` to the user, so the hang was
reachable in the running application.

No assertion here fixes a factor of safety: this version does not touch a
single executable line of calculation. What is checked are identities and
names.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


# Qt destroys the child widgets when the owning window is collected, and
# the reads below happen after construction.
_WINDOWS: list = []

_KEY = "block_object"

# The advice and the disabled tooltip are the SAME key on purpose. The
# three fragments are copied verbatim from the tooltip in
# ``main_window.refresh_action_availability``; Python joins them at parse
# time, which is what makes this one dictionary key.
_PRECONDITION = ("Add Block Search Object is only available with the "
                 "Block Search method. Set Surface Options -> Surface "
                 "Type = Non-Circular, Search Method = Block Search.")

_DRAW = ("Draw a Block Search window: click the corners, "
         "right-click or Enter to close.")

_METHOD = "act_add_block_search_object"

_ROOT = Path(__file__).resolve().parent.parent
_MAIN_WINDOW = _ROOT / "ogr_gui" / "main_window.py"


def _window():
    """One window for the whole file: building a MainWindow is expensive
    and every test here reads it rather than rebuilding it."""
    if _WINDOWS:
        return _WINDOWS[0]
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    _WINDOWS.append(w)
    return w


@contextlib.contextmanager
def _a_modal_is_a_failure():
    """Turn a hang into a failure.

    No other test in this project patches ``QMessageBox``; the convention
    is to AVOID the modal branch, which is exactly what left this defect
    unmeasured for so long. All four static constructors are rebound,
    not just ``information``: swapping the box for a ``warning`` is not
    fixing it.
    """
    import ogr_gui.main_window as mw
    reached: list = []

    class _Fake:
        @staticmethod
        def _boom(*_a, **_k):
            reached.append(True)
            raise AssertionError("a modal was opened")

        information = _boom
        warning = _boom
        critical = _boom
        question = _boom

    previous = mw.QMessageBox
    mw.QMessageBox = _Fake
    try:
        yield reached
    finally:
        mw.QMessageBox = previous


@contextlib.contextmanager
def _search_method(value):
    """Set the search method and put everything back (rule 5)."""
    w = _window()
    previous_method = w.project.settings.search.search_method
    previous_tool = w.canvas.tool_mode
    try:
        w.project.settings.search.search_method = value
        w.refresh_action_availability()
        yield w
    finally:
        w.project.settings.search.search_method = previous_method
        w._set_tool(previous_tool)
        w.refresh_action_availability()


def _function_node():
    """The AST of the action, located by NAME and not by line range.

    Every code quotation in the D103 ficha had gone stale by the time it
    was read; a range of lines is a citation that expires.
    """
    tree = ast.parse(io.open(_MAIN_WINDOW, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == _METHOD:
            return node
    raise AssertionError("%s no longer exists in main_window.py" % _METHOD)


@_requires_qt
class TestTheAdviceIsNotModal:
    def test_the_grid_branch_does_not_open_a_modal(self):
        """The measurement the whole ficha is about."""
        with _a_modal_is_a_failure() as reached, _search_method("grid") as w:
            w.act_add_block_search_object()
            assert reached == [], "the guard opened a message box"

    def test_the_grid_branch_says_why_in_the_status_bar(self):
        """A guard that returns in silence is a guard that leaves the
        user with an action that did nothing."""
        from ogr_gui.i18n import tr
        with _a_modal_is_a_failure(), _search_method("grid") as w:
            w.act_add_block_search_object()
            assert w.ogr_status.currentMessage() == tr(_PRECONDITION)

    def test_the_grid_branch_does_not_enter_the_draw_mode(self):
        """What the fix must CONSERVE: the guard is still a guard. Losing
        this while removing the modal would be the worse defect."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _a_modal_is_a_failure(), _search_method("grid") as w:
            w.act_add_block_search_object()
            assert w.canvas.tool_mode != ToolMode.DRAW_BLOCK_SEARCH

    def test_the_advice_is_the_disabled_tooltip_string(self):
        """One precondition, one text - and two code paths that cannot
        drift apart, because they read the same key."""
        with _a_modal_is_a_failure(), _search_method("grid") as w:
            w.act_add_block_search_object()
            assert w.ogr_status.currentMessage() == w._actions[_KEY].toolTip()

    def test_no_modal_survives_in_the_function_body(self):
        """Read from the syntax tree, so a box hidden behind a branch the
        run above never takes is caught too."""
        boxes = [n for n in ast.walk(_function_node())
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)
                 and getattr(n.func.value, "id", None) == "QMessageBox"]
        assert boxes == [], "%d QMessageBox call(s) left" % len(boxes)

    def test_every_string_the_function_shows_goes_through_tr(self):
        """Rule 2 measured where it happens: no bare literal reaches
        ``showMessage`` or a message box from this function."""
        bare = []
        for node in ast.walk(_function_node()):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None)
            if name not in ("showMessage", "information", "warning",
                            "critical", "question"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    bare.append(arg.value)
        assert bare == [], "strings shown without tr(): %r" % (bare[:4],)


@_requires_qt
class TestTheDrawPromptIsTranslated:
    def test_the_block_branch_still_enters_the_draw_mode(self):
        """The identity the fix CONSERVES, and the one thing the ficha
        marks as immovable."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _a_modal_is_a_failure(), _search_method("block") as w:
            w.act_add_block_search_object()
            assert w.canvas.tool_mode == ToolMode.DRAW_BLOCK_SEARCH

    def test_the_draw_prompt_has_a_spanish_entry(self):
        """Rule 2. The identical-translation check of
        ``test_i18n_coverage_v141`` sits at 10 of a ceiling of 12, so a
        lazy copy here would cost more than this one string."""
        from ogr_gui.i18n import _DICTS
        assert _DRAW in _DICTS["es"]
        assert _DICTS["es"][_DRAW] != _DRAW

    def test_the_draw_prompt_reaches_the_status_bar_translated(self):
        """``tr()`` inside the method runs on every call, so unlike the
        action labels of ``_mk`` this needs no second window."""
        from ogr_gui.i18n import _DICTS, current_language, set_language
        previous = current_language()
        try:
            set_language("es")
            with _a_modal_is_a_failure(), _search_method("block") as w:
                w.act_add_block_search_object()
                assert w.ogr_status.currentMessage() == _DICTS["es"][_DRAW]
        finally:
            # Rule 5: a test that leaves the language set breaks menu
            # tests it never heard of, and only in the full suite.
            set_language(previous)


@_requires_qt
class TestWhyThisFileCallsTheMethodDirectly:
    def test_the_action_is_disabled_outside_block_search(self):
        """Measured premise, true before and after the fix."""
        with _search_method("grid") as w:
            assert not w._actions[_KEY].isEnabled()

    def test_triggering_a_disabled_action_is_not_a_probe(self):
        """Why every test above calls the method instead.

        A disabled QAction ignores ``trigger()``, so a file written that
        way would have reported green against the modal. This is the
        ficha's premise measured, not argued.
        """
        with _a_modal_is_a_failure() as reached, _search_method("grid") as w:
            w._actions[_KEY].trigger()
            assert reached == [], "a disabled action reached its slot"

    def test_the_terminal_hands_the_user_the_window(self):
        """The ficha's premise refuted in the worse direction.

        It says only a headless test can reach the box. But View >
        Terminal (Ctrl+`) puts ``mainwindow`` in the namespace of the
        embedded interpreter, so ``mainwindow.act_add_block_search_object()``
        opened the modal in the running application. The hang was a
        user-reachable defect, not test hygiene.
        """
        w = _window()
        assert w.terminal_dock.terminal._ns.get("mainwindow") is w
        assert "terminal" in w._actions

    def test_the_status_bar_is_the_status_bar(self):
        """``self.ogr_status`` and ``self.statusBar()`` are one object,
        so the v0.1.125 precedent applies to this call unchanged and the
        choice between the two spellings is not a change of behaviour."""
        w = _window()
        assert w.ogr_status is w.statusBar()


@_requires_qt
class TestTheScannerAndItsTwoBudgets:
    def test_the_old_budget_is_untouched(self):
        """The ficha forbids moving it, and it could not have moved:
        none of its seven patterns sees these strings."""
        from test_i18n_coverage_v141 import _UNWRAPPED_BUDGET
        assert _UNWRAPPED_BUDGET == 210

    def test_the_seven_old_patterns_never_saw_these_two_strings(self):
        """The refuted premise of the ficha's closing criterion.

        It asks for 'the unwrapped budget lowered by six'. Wrapping these
        strings cannot move it by a point, which is why this version
        declares a second budget instead of lowering the first.
        """
        from test_i18n_coverage_v141 import _VISIBLE
        src = io.open(_MAIN_WINDOW, encoding="utf-8").read()
        for pat in _VISIBLE:
            for hit in re.findall(pat, src):
                assert _PRECONDITION not in hit
                assert _DRAW not in hit

    def test_the_new_patterns_capture_exactly_one_group(self):
        """Measured: with two groups ``re.findall`` returns tuples and
        the scanner raises ``AttributeError`` on ``.startswith``. The
        ficha proposed them with capturing groups, so this is the guard
        against copying it back."""
        from test_i18n_coverage_v141 import _VISIBLE_MESSAGES
        for pat in _VISIBLE_MESSAGES:
            assert re.compile(pat).groups == 1, pat
        two_groups = r'QMessageBox\.(information|warning)\(\s*self,\s*"([^"]+)"'
        found = re.findall(two_groups, 'QMessageBox.information(self, "T")')
        assert isinstance(found[0], tuple), "the trap no longer reproduces"

    def test_the_message_budget_is_declared_and_pinned(self):
        """A second budget as loose as the first would be a second
        ghost: 210 against a real count of 20 cannot fail."""
        from test_i18n_coverage_v141 import (
            _UNWRAPPED_BUDGET_MESSAGES, _VISIBLE_MESSAGES, _unwrapped_count,
        )
        assert isinstance(_UNWRAPPED_BUDGET_MESSAGES, int)
        assert _unwrapped_count(_VISIBLE_MESSAGES) == _UNWRAPPED_BUDGET_MESSAGES
