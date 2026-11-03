# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.413 (D350) — an annotation with the default colour reads on the dark
canvas, and nothing that is stored or exported changes.

The finding (the fifth interface test, 0.1.355, H12): in the dark theme a
text and an arrow with the default colour all but vanished — only "eba"
could be read, where the text crossed the grey cells of the grid. The
default colour is ``#202020``, stored with the annotation, and the canvas
drew it as stored whatever the theme: about 1.1:1 on the dark paper. The
decision (the owner, 2026-11-02): the dark canvas draws the DEFAULT colour,
and only that one, with the theme's ink; the light theme's ink is exactly
``#202020``, so the light canvas does not change. What goes on white paper
— Export Image, Print — draws the stored colour, as the DXF and the PNG of
the API do.

What these tests protect:

* the contrast of a default-coloured text, arrow and line against the
  canvas, in both themes, read from the items and from a capture of the
  canvas: 4.0:1 or more (the floor of D301);
* a colour chosen by hand is drawn as chosen in both themes;
* a change of theme with the window open recolours the annotations;
* Export Image in the dark theme gives the image the light theme gives;
* the annotation's stored colour and its DXF colour do not change.
"""
from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent))

_DEFAULT = "#202020"
_FLOOR = 4.0


@contextlib.contextmanager
def _themed():
    """Put back the sheet, the palette, the language and the icons, and
    save the theme into a folder of the block's own (as
    test_dark_theme_v1316 does)."""
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
        getattr(icons, "reset_cache", lambda: None)()


def _lum(c):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _ratio(a, b):
    """The WCAG contrast ratio of two colours."""
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _rgb(qcolor):
    return (qcolor.red(), qcolor.green(), qcolor.blue())


_WINDOW: list = []


def _window(theme, colour=None):
    """The one window of the file — the demo, shown, with a text, an arrow
    and a line — in ``theme``, set the way Preferences sets it (the
    window's ``_apply_theme``), its annotations in ``colour`` (the default
    when None). Shared: each MainWindow lives to the end of the process."""
    from ogr_core.annotations import Annotation, AnnotationKind
    if not _WINDOW:
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w.act_load_demo()
        w.resize(1200, 800)
        w.show()
        QApplication.processEvents()
        for kind, pts, text in ((AnnotationKind.TEXT, [(5.0, 28.0)],
                                 "Annotation in the dark"),
                                (AnnotationKind.ARROW, [(-10.0, 30.0),
                                                        (5.0, 27.0)], ""),
                                (AnnotationKind.LINE, [(-10.0, 5.0),
                                                       (-2.0, 5.0)], "")):
            w.project.annotations.add(Annotation(kind=kind, points=pts,
                                                 text=text))
        w.canvas.refresh_scene()
        w.canvas.zoom_all()
        _WINDOW.append(w)
    w = _WINDOW[0]
    for ann in w.project.annotations:
        ann.style.colour = colour or _DEFAULT
    w.canvas.refresh_scene()
    w._apply_theme(theme)
    w.project.is_dirty = False
    QApplication.processEvents()
    return w


def _annotation_colours(canvas):
    """What the annotation items are drawn with: the text brushes and the
    pens of the strokes and marks."""
    from PySide6.QtWidgets import (QGraphicsPathItem,
                                   QGraphicsSimpleTextItem)
    from ogr_gui.canvas.annotation_items import Z_ANNOTATION
    texts, pens = [], []
    for item in canvas.scene().items():
        if not (Z_ANNOTATION <= item.zValue() < Z_ANNOTATION + 1.0):
            continue
        if isinstance(item, QGraphicsSimpleTextItem):
            texts.append(item)
        elif isinstance(item, QGraphicsPathItem):
            pens.append(_rgb(item.pen().color()))
    return texts, pens


def _paper(canvas):
    return _rgb(canvas.backgroundBrush().color())


def _best_contrast_in(canvas, item):
    """The highest contrast against the paper among the pixels of a
    capture of the canvas under ``item`` (a text, which ignores the view's
    transformation)."""
    img = canvas.viewport().grab().toImage()
    # The item ignores the view's transformation: its pixels are where its
    # DEVICE transform puts them (``sceneTransform`` would read its pixel
    # sizes as model units)
    rect = item.deviceTransform(canvas.viewportTransform()).mapRect(
        item.boundingRect()).toAlignedRect()
    rect = rect.intersected(img.rect())
    assert rect.width() > 3 and rect.height() > 3, rect
    paper = _paper(canvas)
    best = 1.0
    for x in range(rect.left(), rect.right()):
        for y in range(rect.top(), rect.bottom()):
            c = img.pixelColor(x, y)
            best = max(best, _ratio(_rgb(c), paper))
    return best


# ======================================================================
class TestTheDefaultColourReads:

    def test_in_both_themes_from_the_items(self):
        with _themed():
            seen = {}
            for theme in ("light", "dark"):
                w = _window(theme)
                texts, pens = _annotation_colours(w.canvas)
                assert texts and pens, (texts, pens)
                paper = _paper(w.canvas)
                for t in texts:
                    r = _ratio(_rgb(t.brush().color()), paper)
                    assert r >= _FLOOR, (theme, r)
                for pen in pens:
                    assert _ratio(pen, paper) >= _FLOOR, (theme, pen, paper)
                seen[theme] = _rgb(texts[0].brush().color())
            # the light canvas draws the stored colour itself
            assert seen["light"] == (0x20, 0x20, 0x20), seen

    def test_in_both_themes_from_a_capture(self):
        """What reaches the screen, not what the item says it has: the
        best-contrasted pixel under the text, against the paper."""
        with _themed():
            for theme in ("light", "dark"):
                w = _window(theme)
                texts, _pens = _annotation_colours(w.canvas)
                best = _best_contrast_in(w.canvas, texts[0])
                assert best >= _FLOOR, (theme, best)

    def test_a_change_of_theme_recolours_them(self):
        """Drawn in the light theme, then the theme changed through the
        window and NOTHING redrawn by hand: the annotations follow, as the
        paper does (D301)."""
        with _themed():
            w = _window("light")
            w._apply_theme("dark")
            QApplication.processEvents()
            texts, pens = _annotation_colours(w.canvas)
            paper = _paper(w.canvas)
            assert all(_ratio(_rgb(t.brush().color()), paper) >= _FLOOR
                       for t in texts)
            assert all(_ratio(pen, paper) >= _FLOOR for pen in pens)


class TestWhatIsNotTheDefaultOrNotTheScreen:

    def test_a_chosen_colour_is_drawn_as_chosen_in_both_themes(self):
        with _themed():
            for theme in ("light", "dark"):
                w = _window(theme, "#12ab34")
                texts, pens = _annotation_colours(w.canvas)
                assert {_rgb(t.brush().color()) for t in texts} == {
                    (0x12, 0xab, 0x34)}, theme
                assert set(pens) == {(0x12, 0xab, 0x34)}, (theme, pens)

    def test_the_stored_colour_does_not_change(self):
        with _themed():
            w = _window("dark")
            colours = {a.to_dict()["style"]["colour"]
                       for a in w.project.annotations}
            assert colours == {_DEFAULT}, colours

    def test_the_dxf_colour_does_not_change(self):
        """The DXF is written from the model, whatever the theme of the
        window that asks for it."""
        import ezdxf
        from ogr_core.dxf.exporter import ExportOptions, export_dxf
        with _themed():
            w = _window("dark")
            path = Path(tempfile.mkdtemp(prefix="ogr_test_d350_")) / "a.dxf"
            rep = export_dxf(w.project, path, ExportOptions(unit="m"))
            assert rep.ok, rep.error
            doc = ezdxf.readfile(str(path))
            colours = {e.rgb for e in doc.modelspace().query(
                '*[layer=="OGR_X_DRAWING"]') if e.dxf.hasattr("true_color")}
            assert colours == {(0x20, 0x20, 0x20)}, colours

    def test_export_image_in_the_dark_theme_is_the_light_one(self):
        """Export Image paints on white paper: the dark theme must not hand
        it the screen's light ink; and afterwards the screen has it back."""
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        out = {}
        tmp = tempfile.mkdtemp(prefix="ogr_test_d350_")
        raw_save = QFileDialog.__dict__.get("getSaveFileName")
        raw_int = QInputDialog.__dict__.get("getInt")
        try:
            QInputDialog.getInt = staticmethod(lambda *a, **k: (800, True))
            with _themed():
                for theme in ("light", "dark"):
                    path = os.path.join(tmp, theme + ".png")
                    QFileDialog.getSaveFileName = staticmethod(
                        lambda *a, _p=path, **k: (_p, ""))
                    w = _window(theme)
                    w._export_image()
                    out[theme] = QImage(path)
                texts, _pens = _annotation_colours(w.canvas)
                screen = _ratio(_rgb(texts[0].brush().color()),
                                _paper(w.canvas))
        finally:
            for cls, name, raw in ((QFileDialog, "getSaveFileName", raw_save),
                                   (QInputDialog, "getInt", raw_int)):
                if raw is None:
                    delattr(cls, name)
                else:
                    setattr(cls, name, raw)
        light, dark = out["light"], out["dark"]
        assert not light.isNull() and light.size() == dark.size()
        assert light == dark
        assert screen >= _FLOOR, screen
