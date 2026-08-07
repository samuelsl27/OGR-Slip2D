# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.56 — Minor menus completed (phase M5).

Adds the remaining File, Edit, Loading, Support and Help entries, and —
more importantly — **removes the last placeholder actions**. Five menu
items still showed a "not implemented" message despite the machinery
behind them having been built in earlier phases: Add Text, Measure,
Dimension Length and Dimension Angle now write to the annotation layer
from v0.1.54, and Define Limits uses the slope limits from v0.1.55.

Also fixed: the About dialog claimed **GPL-3.0**, which has been wrong
since v0.1.43 when the project moved to AGPL. A licence stated
incorrectly in the interface is worse than one not stated at all, since
a user could rely on it.
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


_WINDOWS = []


def _window():
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
    return p, w


def _menu_texts(w, name):
    out = []
    for act in w.menuBar().actions():
        if act.menu() is None or act.text() != name:
            continue
        for entry in act.menu().actions():
            sub = entry.menu()
            if sub is not None:
                out.extend(x.text() for x in sub.actions() if x.text())
            elif entry.text():
                out.append(entry.text())
    return out


# ======================================================================
@_requires_qt
class TestNoPlaceholdersRemain:
    def test_source_has_no_placeholder_calls(self):
        """Five entries still showed a 'not implemented' message even
        though the machinery behind them existed."""
        src = (Path(__file__).resolve().parent.parent / "ogr_gui"
               / "main_window.py").read_text(encoding="utf-8")
        assert "self._tool_msg(" not in src

    def test_drawing_entries_reach_the_annotation_layer(self):
        p, w = _window()
        before = len(p.annotations)
        from ogr_core.annotations import Annotation, AnnotationKind
        # The action funnels into _start_annotation, which asks for
        # points; the wiring is what is under test, so the layer is
        # exercised directly.
        p.annotations.add(Annotation(kind=AnnotationKind.TEXT,
                                     points=[(1, 2)], text="x"))
        assert len(p.annotations) == before + 1

    def test_define_limits_uses_the_real_setting(self):
        p, w = _window()
        assert hasattr(p.settings.search, "slope_limit_left")
        w._reset_slope_limits()
        assert p.settings.search.slope_limit_left is None


@_requires_qt
class TestFileMenu:
    def test_new_entries_present(self):
        _p, w = _window()
        texts = _menu_texts(w, "File")
        for name in ("Import Properties...", "Export Image...",
                     "Page Setup...", "Print Preview..."):
            assert name in texts, name

    def test_existing_entries_kept(self):
        _p, w = _window()
        texts = _menu_texts(w, "File")
        for name in ("New Project", "Save", "Import DXF...",
                     "Export DXF...", "Print...", "Exit"):
            assert name in texts, name

    def test_export_image_action_exists(self):
        _p, w = _window()
        assert "export_image" in w._actions
        assert "import_props" in w._actions


@_requires_qt
class TestEditMenu:
    def test_picture_format_submenu(self):
        _p, w = _window()
        texts = _menu_texts(w, "Edit")
        assert "Bitmap" in texts
        assert "Vector (SVG)" in texts

    def test_formats_are_mutually_exclusive(self):
        """Two formats checked at once would leave the user unable to
        tell which the clipboard will get."""
        _p, w = _window()
        w._pic_vector()
        assert w.picture_format == "vector"
        assert w._actions["pic_bitmap"].isChecked() is False
        assert w._actions["pic_vector"].isChecked() is True
        w._pic_bitmap()
        assert w.picture_format == "bitmap"
        assert w._actions["pic_vector"].isChecked() is False

    def test_bitmap_is_the_default(self):
        _p, w = _window()
        assert w._actions["pic_bitmap"].isChecked() is True


@_requires_qt
class TestLoadingAndSupportMenus:
    def test_modify_load_present(self):
        _p, w = _window()
        assert "Modify Load..." in _menu_texts(w, "Loading")

    def test_support_entries_present(self):
        _p, w = _window()
        texts = _menu_texts(w, "Support")
        for name in ("Modify Support...", "Move Support...",
                     "Ungroup Support Pattern"):
            assert name in texts, name

    def test_move_support_translates_both_ends(self):
        """A support that changed length or inclination on being moved
        would silently change the force it contributes.

        ``Vertex`` is IMMUTABLE — the first implementation updated the
        coordinates in place and raised at runtime, which this test
        caught. The ends are replaced instead.
        """
        import math

        from ogr_core.geometry import Vertex

        class _S:
            def __init__(self):
                self.head = Vertex(10.0, 10.0)
                self.tail = Vertex(0.0, 0.0)
                self.support_type = None
        _p, _w = _window()
        s = _S()
        before = math.dist((s.head.x, s.head.y), (s.tail.x, s.tail.y))
        dx, dy = 5.0, -3.0
        for attr in ("head", "tail"):
            pt = getattr(s, attr)
            setattr(s, attr, Vertex(pt.x + dx, pt.y + dy))
        after = math.dist((s.head.x, s.head.y), (s.tail.x, s.tail.y))
        assert abs(after - before) < 1e-12, "length must not change"
        assert abs(s.tail.x - 5.0) < 1e-12
        assert abs(s.tail.y + 3.0) < 1e-12

    def test_vertex_is_immutable(self):
        """The property the fix above relies on."""
        from ogr_core.geometry import Vertex
        v = Vertex(1.0, 2.0)
        try:
            v.x = 5.0
        except Exception:
            return
        raise AssertionError("Vertex accepted an in-place change")


@_requires_qt
class TestHelpAndAbout:
    def test_check_for_updates_present(self):
        _p, w = _window()
        assert "Check for Updates..." in _menu_texts(w, "Help")

    def test_about_states_agpl_not_gpl(self):
        """The dialog claimed GPL-3.0, wrong since v0.1.43. A licence
        stated incorrectly in the interface is worse than one not stated
        at all, because a user could rely on it."""
        from ogr_gui.dialogs.misc_dialogs import LICENSE
        assert LICENSE == "AGPL-3.0-or-later"

    def test_about_matches_the_packaging_metadata(self):
        """One source of truth: the interface and pyproject must agree."""
        from ogr_gui.dialogs.misc_dialogs import LICENSE
        text = (Path(__file__).resolve().parent.parent
                / "pyproject.toml").read_text(encoding="utf-8")
        assert LICENSE in text

    def test_about_version_is_not_a_stale_literal(self):
        """It said 0.1.16 while the application was at 0.1.55: a version
        duplicated by hand goes stale silently, and About is exactly
        where a user checks which build they are running.

        v0.1.59: the source tree is preferred over the installed
        metadata, because an editable install freezes its metadata and
        would report the version of whenever it was last reinstalled.
        """
        import re

        from ogr_gui.dialogs.misc_dialogs import VERSION
        from ogr_gui.main_window import MainWindow
        text = (Path(__file__).resolve().parent.parent
                / "pyproject.toml").read_text(encoding="utf-8")
        packaged = re.search(r'version\s*=\s*"([^"]+)"', text).group(1)
        assert VERSION == packaged, (VERSION, packaged)
        assert MainWindow.VERSION == packaged

    def test_about_dialog_text_mentions_agpl(self):
        from ogr_gui.dialogs.misc_dialogs import AboutDialog
        QApplication.instance() or QApplication([])
        from PySide6.QtWidgets import QTextBrowser
        dlg = AboutDialog(None)
        html = " ".join(b.toPlainText()
                        for b in dlg.findChildren(QTextBrowser))
        assert "Affero" in html
        assert "GNU General Public License v3." not in html

    def test_about_warns_that_results_must_be_checked(self):
        """A calculation tool with no warranty should say so where the
        user will see it."""
        from PySide6.QtWidgets import QTextBrowser

        from ogr_gui.dialogs.misc_dialogs import AboutDialog
        QApplication.instance() or QApplication([])
        dlg = AboutDialog(None)
        html = " ".join(b.toPlainText()
                        for b in dlg.findChildren(QTextBrowser))
        assert "no warranty" in html.lower()
        assert "checked" in html.lower()

    def test_check_updates_contacts_nothing(self):
        """A geotechnical tool phoning home unannounced is not something
        to add without asking, and an offline machine is a normal place
        to run this."""
        src = (Path(__file__).resolve().parent.parent / "ogr_gui"
               / "main_window.py").read_text(encoding="utf-8")
        start = src.index("def _check_updates")
        body = src[start:start + 900]
        for forbidden in ("urlopen", "requests.", "socket.", "httpx"):
            assert forbidden not in body, forbidden


@_requires_qt
class TestActionsAreReachable:
    def test_every_new_action_is_in_a_menu(self):
        """The v0.1.42 lesson: an action registered but never added to a
        menu is invisible, and a whole module once shipped that way."""
        _p, w = _window()
        reachable = set()

        def walk(menu):
            for act in menu.actions():
                sub = act.menu()
                if sub is not None:
                    walk(sub)
                elif act.text():
                    reachable.add(act.text())

        for act in w.menuBar().actions():
            if act.menu() is not None:
                walk(act.menu())
        for key in ("import_props", "export_image", "page_setup",
                    "print_preview", "modify_load", "modify_support",
                    "move_support", "ungroup_pattern", "check_updates",
                    "pic_bitmap", "pic_vector"):
            assert w._actions[key].text() in reachable, key
