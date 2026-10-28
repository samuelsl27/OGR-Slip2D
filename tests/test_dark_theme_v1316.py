# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.316 (D301) — the dark theme can be read, and the light one did not
change.

``apply_theme`` set only a style sheet. The dark sheet names no ``QLabel``,
``QCheckBox`` or plain panel, so those kept the light palette's dark text
on the dark window. Measured offscreen on the main window, *Preferences*,
the hydraulic dialog and a ``QMessageBox``, as the contrast ratio (WCAG)
between each text's background and its ink, cut from a grab of the WHOLE
window (a widget grabbed alone is painted on its own palette, not on the
window's background, and hides exactly this):

* 0.1.315, dark: minimum 1.28 (the coordinates of the status bar), 1.48 for
  "No results yet.", the message box, the hydraulic labels and every check
  box of *Preferences*;
* 0.1.315, light: minimum 4.08; 0.1.316, light: the same 4.08, widget by
  widget; 0.1.316, dark: 4.04.

The fix: a palette with the theme (the dark one from the colours its sheet
already used; the light one is the palette the application had before any
theme), the colours the widgets wrote as literals asked by role
(``theme_color``: the light value of each role IS the old literal), the
icons built again under the new palette, and the paper of the canvas.

The invariants:

* every enabled text with letters in the sample reads at a ratio of at least
  4.0 in BOTH themes — the light theme's minimum before this version;
* the light theme is the platform palette and the old literals;
* an icon with no colour of its own reads on the dark menu, and the window
  builds its icons again when the theme changes;
* the canvas paper follows the theme and a material keeps its colour;
* the sheet, the palette, the language and the icon caches are put back,
  and so is the saved theme (v0.1.374): ``_apply_theme`` saves it, and
  from this file on every window of the run opened dark (audit D-c,
  docs/audits/AUDITORIA_SUITE_v0.1.372.md §9).
"""
from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()
_THRESHOLD = 4.0


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


@contextlib.contextmanager
def _no_modals():
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


@contextlib.contextmanager
def _themed():
    """Put back the sheet, the palette, the language and the icons; and
    the saved theme, by saving into a folder of the block's own, as
    test_qt_translations_v1292 does."""
    from PySide6.QtGui import QPalette
    from ogr_gui.i18n import current_language, set_language
    from ogr_gui.resources import icons
    app = QApplication.instance() or QApplication([])
    sheet, palette = app.styleSheet(), QPalette(app.palette())
    language = current_language()
    settings = os.environ.get("OGR_SETTINGS_DIR")
    os.environ["OGR_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="ogr_test_theme_")
    try:
        set_language("en")
        yield app
    finally:
        if settings is None:
            os.environ.pop("OGR_SETTINGS_DIR", None)
        else:
            os.environ["OGR_SETTINGS_DIR"] = settings
        set_language(language)
        app.setStyleSheet(sheet)
        app.setPalette(palette)
        # absent before this version: the cleanup must not hide the failure
        getattr(icons, "reset_cache", lambda: None)()


def _window():
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.act_load_demo()
    w.resize(1200, 800)
    w.project.is_dirty = False
    return w


def _lum(c):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _ratio(a, b):
    """The WCAG contrast ratio of two colours."""
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _contrast(widget, shot, top):
    """Background (the commonest colour) against the ink (the colour
    farthest from it) in the widget's area of a grab of its window."""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import (QCheckBox, QRadioButton, QStyle,
                                   QStyleOptionButton)
    rect = widget.rect()
    if isinstance(widget, (QCheckBox, QRadioButton)):
        # the text, not the box drawn beside it
        opt = QStyleOptionButton()
        widget.initStyleOption(opt)
        el = (QStyle.SE_CheckBoxContents if isinstance(widget, QCheckBox)
              else QStyle.SE_RadioButtonContents)
        rect = widget.style().subElementRect(el, opt, widget)
    rect = QRect(rect.topLeft() + widget.mapTo(top, QPoint(0, 0)),
                 rect.size())
    pixels = []
    for y in range(max(0, rect.top()), min(shot.height(), rect.bottom() + 1)):
        for x in range(max(0, rect.left()),
                       min(shot.width(), rect.right() + 1)):
            c = shot.pixelColor(x, y)
            pixels.append((c.red(), c.green(), c.blue()))
    if not pixels:
        return None
    bg = Counter(pixels).most_common(1)[0][0]
    ink = max(pixels, key=lambda p: abs(_lum(p) - _lum(bg)))
    return _ratio(bg, ink)


def _texts(top, name):
    """``(ratio, where, text)`` of every enabled, visible text with letters
    (a disabled one is pale on purpose; a separator is not text)."""
    from PySide6.QtWidgets import QCheckBox, QLabel, QRadioButton
    shot = top.grab().toImage()
    out = []
    for cls in (QLabel, QCheckBox, QRadioButton):
        for wd in top.findChildren(cls):
            if not wd.isVisible() or not wd.isEnabled():
                continue
            if not any(ch.isalnum() for ch in wd.text()):
                continue
            if wd.width() < 4 or wd.height() < 4:
                continue
            r = _contrast(wd, shot, top)
            if r is not None:
                out.append((round(r, 2), name, wd.text()[:40]))
    return out


def _sample(app, w):
    """The texts of the main window, Preferences, the hydraulic dialog and
    a message box, under the active theme."""
    from PySide6.QtWidgets import QMessageBox
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
    w.show()
    app.processEvents()
    rows = _texts(w, "main")
    shown = []
    for name, d in (("preferences", PreferencesDialog(w)),
                    ("hydraulic", HydraulicPropertiesDialog(w.project, w)),
                    ("message", QMessageBox(QMessageBox.Information, "Title",
                                            "Some message text.", parent=w))):
        d.setModal(False)
        d.show()
        app.processEvents()
        rows += _texts(d, name)
        shown.append(d)
    for d in shown:
        d.hide()
        d.deleteLater()
    app.processEvents()
    return rows


# ----------------------------------------------------------------------
class TestEveryTextReads:
    def test_in_both_themes(self):
        with _themed() as app, _no_modals():
            w = _window()
            try:
                for theme in ("light", "dark"):
                    w._apply_theme(theme)
                    rows = _sample(app, w)
                    # the sample has to see something to mean anything
                    assert len(rows) >= 20, (theme, len(rows))
                    low = [r for r in rows if r[0] < _THRESHOLD]
                    assert low == [], (theme, low)
            finally:
                w.project.is_dirty = False
                w.close()


class TestTheLightThemeDidNotChange:
    def test_its_palette_is_the_one_before_any_theme(self):
        from PySide6.QtGui import QPalette
        from ogr_gui.themes import apply_theme
        with _themed() as app:
            from ogr_gui import themes
            before = QPalette(themes._ORIGINAL_PALETTE
                              if themes._ORIGINAL_PALETTE is not None
                              else app.palette())
            apply_theme(app, "dark")
            apply_theme(app, "light")
            assert app.palette() == before

    def test_its_colours_are_the_old_literals(self):
        from ogr_gui.themes import ROLE_COLORS
        light = ROLE_COLORS["light"]
        # what the widgets wrote before this version, role by role
        for role, literal in (("muted", "#555555"), ("muted_strong", "#444444"),
                              ("muted_soft", "#666666"),
                              ("disabled", "#909090"), ("error", "#b00020"),
                              ("warning", "#a05a00"), ("caution", "#8a5a00"),
                              ("accent", "#c0392b"), ("ink", "#202020"),
                              ("note_bg", "#f4f4f8"), ("info_bg", "#eeeeff"),
                              ("status_text", "#4a4a4a"),
                              ("toggle_off", "#707070"),
                              ("separator", "#c0c0c0"),
                              ("canvas_bg", "#fafafa"),
                              ("canvas_bg_gray", "#e8e8e8"),
                              ("grid_minor", "#dcdcdc"),
                              ("grid_major", "#b4b4b4"),
                              ("ruler_text", "#646464")):
            assert light[role] == literal, role
        assert set(ROLE_COLORS["dark"]) == set(light)

    def test_the_active_theme_is_read_from_the_sheet(self):
        """Not from a variable: a test that puts the sheet back must not
        leave the colours of the dark theme behind."""
        from ogr_gui.themes import apply_theme, current_theme, theme_color
        with _themed() as app:
            apply_theme(app, "dark")
            assert current_theme() == "dark"
            app.setStyleSheet("")
            assert current_theme() == "light"
            assert theme_color("ink") == "#202020"


class TestIconsAndCanvas:
    def _icon_ink(self, qicon):
        """The colour of the opaque pixels of an icon."""
        img = qicon.pixmap(24, 24).toImage()
        px = [img.pixelColor(x, y) for y in range(img.height())
              for x in range(img.width())]
        solid = [(c.red(), c.green(), c.blue()) for c in px if c.alpha() > 200]
        assert solid
        return Counter(solid).most_common(1)[0][0]

    def test_an_icon_with_no_colour_of_its_own_reads_on_the_dark_menu(self):
        from ogr_gui.resources.icons import icon
        from ogr_gui.themes import apply_theme
        with _themed() as app:
            apply_theme(app, "dark")
            ink = self._icon_ink(icon("open_project"))
            menu_bg = (0x35, 0x35, 0x35)
            assert _ratio(ink, menu_bg) >= 3.0, ink
            # and the dark grey of the External boundary is lifted
            ink = self._icon_ink(icon("ext_boundary"))
            assert _ratio(ink, menu_bg) >= 3.0, ink

    def test_the_window_builds_its_icons_again(self):
        with _themed():
            w = _window()
            try:
                act = next(a for a in w._actions.values()
                           if a.property("ogr_icon_key") == "open_project")
                w._apply_theme("light")
                light = self._icon_ink(act.icon())
                w._apply_theme("dark")
                dark = self._icon_ink(act.icon())
                assert light != dark
                assert _lum(dark) > _lum(light)
            finally:
                w.project.is_dirty = False
                w.close()

    def test_the_canvas_paper_follows_and_the_model_does_not(self):
        from ogr_gui.canvas.graphics_items import BoundaryItem
        with _themed():
            w = _window()
            try:
                colours = {}
                for theme in ("light", "dark"):
                    w._apply_theme(theme)
                    w.canvas.refresh_scene()
                    paper = w.canvas.backgroundBrush().color().name()
                    lines = sorted(it.pen().color().name()
                                   for it in w.canvas.scene().items()
                                   if isinstance(it, BoundaryItem))
                    colours[theme] = (paper, lines)
                assert colours["light"][0] == "#fafafa"
                assert colours["dark"][0] != colours["light"][0]
                assert colours["dark"][1] == colours["light"][1]
            finally:
                w.project.is_dirty = False
                w.close()
