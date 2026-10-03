# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Help Topics opens the online documentation, in the language of the interface.

WHAT INVARIANT THIS PROTECTS. Until v0.1.250 *Help Topics* (F1) opened a MODAL
box with a repository address and one line about the terminal, and the
interpretation window had a box of its own with a different line: no help,
said two different ways. The documentation lives on the project's site, in the
two languages of this interface, so:

* F1 opens the page in the language the user is reading -- Spanish interface,
  Spanish page; English interface, English page -- and a language the site has
  no page for falls back to the English one, which the site itself declares as
  its ``x-default``;
* the two addresses live in ONE table and both windows go through ONE door,
  so they cannot drift apart again;
* nothing is modal: a dialog blocks a test run for good (AGENTS.md), and a
  machine without a browser still gets the address on its status bar.

WHY THESE ANCHORS. The addresses are the site's own: the ``hreflang`` links of
its documentation index, read in the site's source on 2026-10-03. No test here
opens a browser: the module-level opener is replaced, and it is restored in
``finally`` together with the interface language (rule 5; the runner does not
call ``teardown_method``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_ES = "https://opengeorock.org/es/docs/index.html"
_EN = "https://opengeorock.org/docs/index.html"
_WINDOWS = []      # keep references: Qt destroys child widgets otherwise


class _Opener:
    """Stands in for the browser and records what it was asked to open."""

    def __init__(self, answer=True):
        self.answer = answer
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def _with_opener(opener, language, action):
    """``action()`` with ``opener`` as the browser and ``language`` as the
    interface language, both restored whatever happens.

    The documentation module is imported FIRST, on purpose: on a tree
    without it this fails before ``action`` can open the modal box the old
    handler opened, which would block the run instead of failing it.
    """
    import ogr_gui.documentation as D
    from ogr_gui.i18n import current_language, set_language

    saved_opener, saved_language = D._open_url, current_language()
    D._open_url = opener
    try:
        set_language(language)
        return action()
    finally:
        D._open_url = saved_opener
        set_language(saved_language)


def _main_window():
    from test_slide_validation_ej1 import _ej1_project

    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow

    QApplication.instance() or QApplication([])
    set_language("en")
    p = _ej1_project()
    w = MainWindow()
    w.canvas.set_project(p)
    w.project = p
    _WINDOWS.append(w)
    return w


def _interpret_window():
    from test_slide_validation_ej1 import _ej1_project

    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch

    QApplication.instance() or QApplication([])
    set_language("en")
    p = _ej1_project()
    res = {"bishop_simplified": GridSearch(
        method=BishopSimplified(), grid_x=(70, 100), grid_y=(60, 85),
        grid_nx=2, grid_ny=2, radius_increment=4, min_radius=15,
        num_slices=16, min_area=0.5).run(p)}
    w = InterpretWindow(p, res, None)
    _WINDOWS.append(w)
    return w


def _menu_holding(window, action):
    """The title of the top-level menu that holds ``action``, or None."""
    for top in window.menuBar().actions():
        menu = top.menu()
        if menu is not None and action in menu.actions():
            return menu.title()
    return None


# ======================================================================
class TestTheAddresses:

    def test_one_table_holds_the_two_pages_of_the_site(self):
        from ogr_gui.documentation import DOCS_URLS
        assert DOCS_URLS == {"es": _ES, "en": _EN}

    def test_every_interface_language_has_its_page(self):
        from ogr_gui.documentation import DOCS_URLS
        from ogr_gui.i18n import available_languages
        assert set(available_languages()) <= set(DOCS_URLS)

    def test_a_language_without_a_page_falls_back_to_english(self):
        from ogr_gui.documentation import documentation_url
        assert documentation_url("es") == _ES
        assert documentation_url("en") == _EN
        assert documentation_url("fr") == _EN


# ======================================================================
@_requires_qt
class TestF1InTheMainWindow:

    def test_help_topics_is_in_the_help_menu_on_f1(self):
        w = _main_window()
        act = w._actions["help"]
        assert act.shortcut().toString() == "F1"
        assert _menu_holding(w, act) == "Help"

    def test_a_spanish_interface_opens_the_spanish_page(self):
        w = _main_window()
        opener = _Opener(True)
        _with_opener(opener, "es", w._actions["help"].trigger)
        assert opener.urls == [_ES]
        assert _ES in w.statusBar().currentMessage()

    def test_an_english_interface_opens_the_english_page(self):
        w = _main_window()
        opener = _Opener(True)
        _with_opener(opener, "en", w._actions["help"].trigger)
        assert opener.urls == [_EN]
        assert _EN in w.statusBar().currentMessage()

    def test_without_a_browser_the_status_bar_gives_the_address(self):
        w = _main_window()
        opener = _Opener(False)
        _with_opener(opener, "en", w._actions["help"].trigger)
        said = w.statusBar().currentMessage()
        assert opener.urls == [_EN]
        assert _EN in said and "No browser" in said, said

    def test_a_browser_that_raises_does_not_take_the_window_down(self):
        from ogr_gui.documentation import open_documentation
        w = _main_window()
        opener = _Opener(RuntimeError("no handler for https"))
        opened = _with_opener(opener, "es",
                              lambda: open_documentation(w))
        assert opened is False
        assert _ES in w.statusBar().currentMessage()

    def test_the_handler_opens_nothing_modal(self):
        import inspect

        from ogr_gui.main_window import MainWindow
        src = inspect.getsource(MainWindow.act_help)
        assert "QMessageBox" not in src and ".exec(" not in src


# ======================================================================
@_requires_qt
class TestTheInterpretWindowGoesThroughTheSameDoor:

    def test_its_help_topics_is_in_its_help_menu(self):
        w = _interpret_window()
        assert _menu_holding(w, w._act_help_topics) == "Help"

    def test_its_help_topics_opens_the_same_page(self):
        w = _interpret_window()
        opener = _Opener(True)
        _with_opener(opener, "es", w._act_help_topics.trigger)
        assert opener.urls == [_ES]
        assert _ES in w.statusBar().currentMessage()
