# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.315 (D293) — in Spanish, with either theme, no button is narrower than
its text and every dialog fits a 1366 × 768 screen.

What was measured (offscreen, Spanish, light theme), before this version:

* the theme gave every ``QPushButton`` a ``min-width: 70px``. In Qt a
  style-sheet minimum REPLACES the one the text asks for, so a layout short
  of room squeezed buttons under their text: the transient dialog opened at
  520 px and cut its four buttons ("Capturar condiciones actuales" got 144
  of its 279 px). Without the theme the same dialog asked for 805 px and cut
  nothing. Moving the rule to the buttons of a ``QDialogButtonBox`` was the
  first plan, and the census below refuted it: with Qt's Spanish catalog
  "Restaurar los valores predeterminados" got 220 of its 339 px in Display
  Options, already on opening. The sheets now set no minimum at all, and
  ``ogr_gui.button_floor`` gives a box button max(100 px, its text);
* the hydraulic dialog put its parameters in a plain ``QScrollArea``, which
  got some 190 px for 530 px of content and scrolled sideways over cut notes
  and buttons; and its minimum width was set by a 486 px rich-text note in
  the left column, whose line break is only a space in HTML;
* a census of the dialogs found two more: *Define Support* kept its list
  column at 220 px, under its row of three Spanish buttons, and *Add Grid*
  had an unwrapped 1616 px introduction, so its minimum was wider than the
  screen.

The invariants, offscreen, with the language and the theme restored:

* every dialog of the census, at its MINIMUM size (the layout keeps it from
  being smaller), shows each visible button at least as wide as its text,
  and that minimum fits 1366 × 728 (768 less a taskbar);
* the transient and hydraulic dialogs also open without a cut button, and
  the hydraulic one without a sideways scroll bar;
* control: OK and Cancel keep the 100 px the theme gave them;
* the floor does nothing while no theme is the application's style sheet,
  so a test that puts the sheet back leaves it inert (rule 5).

v0.1.326 (D319, D320, D321) widens the census past the buttons, because
the third test of the interface found what it did not look at: Project
Settings cut its page names («Agua sub», «Transitori») and Surface Options,
with an explicit window minimum that REPLACES the layout's, opened with the
Block Search boxes 2–3 px tall. At the size each dialog opens at AND at its
minimum, ``_squeezed`` also reports a label that does not wrap and is
narrower than its text, a check box or radio button narrower than its text,
a combo or spin box lower than its own minimum, and a list whose items do
not fit across.
"""
from __future__ import annotations

import contextlib
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()
_SCREEN = (1366, 728)


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
def _spanish_with(theme):
    """Spanish and ``theme``, and everything put back afterwards."""
    from PySide6.QtCore import QLibraryInfo, QTranslator
    from PySide6.QtGui import QPalette
    from ogr_gui.i18n import current_language, set_language
    from ogr_gui.themes import apply_theme
    app = QApplication.instance() or QApplication([])
    sheet, palette = app.styleSheet(), QPalette(app.palette())
    language = current_language()
    # Qt's own Spanish catalog, for the standard buttons of the boxes:
    # "Restore Defaults" is twice as long in Spanish
    qt_es = QTranslator()
    loaded = qt_es.load("qtbase_es",
                        QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    try:
        if loaded:
            app.installTranslator(qt_es)
        apply_theme(app, theme)
        set_language("es")
        yield app
    finally:
        set_language(language)
        if loaded:
            app.removeTranslator(qt_es)
        app.setStyleSheet(sheet)
        app.setPalette(palette)


def _window():
    from ogr_core.support import EndAnchored
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.support_types = [
        EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)]
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


def _cut(dialog):
    """The buttons showing less than their text. A button with no text (a
    colour swatch of fixed width) has none to cut."""
    from PySide6.QtWidgets import QPushButton
    return [(b.text(), b.width(), b.sizeHint().width())
            for b in dialog.findChildren(QPushButton)
            if b.isVisible() and b.text()
            and b.width() < b.sizeHint().width()]


def _squeezed(dialog):
    """v0.1.326 — what ``dialog`` shows cut or squashed besides its buttons,
    as ``(kind, text, has, needs)``. Text that wraps (a word-wrapped label,
    a ``WrappingCheckBox``) is cut when it gets fewer lines than it needs at
    its width, so it is measured in height; a list counts when its widest
    item is wider than what it shows across."""
    from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox,
                                   QLabel, QListWidget, QRadioButton)

    def text_cut(kind, w):
        if w.hasHeightForWidth():
            need = w.heightForWidth(w.width())
            if w.height() < need:
                out.append((kind + " lines", w.text()[:60], w.height(), need))
        elif w.width() < w.sizeHint().width():
            out.append((kind, w.text()[:60], w.width(), w.sizeHint().width()))

    out = []
    for w in dialog.findChildren(QLabel):
        if w.isVisible() and w.text():
            text_cut("label", w)
    for cls in (QCheckBox, QRadioButton):
        for w in dialog.findChildren(cls):
            if w.isVisible() and w.text():
                text_cut("check", w)
    for cls in (QAbstractSpinBox, QComboBox):
        for w in dialog.findChildren(cls):
            if (w.isVisible()
                    and w.height() < w.minimumSizeHint().height()):
                out.append(("box", type(w).__name__, w.height(),
                            w.minimumSizeHint().height()))
    for w in dialog.findChildren(QListWidget):
        if (w.isVisible() and w.count()
                and w.sizeHintForColumn(0) > w.viewport().width()):
            out.append(("list", w.item(0).text()[:60], w.viewport().width(),
                        w.sizeHintForColumn(0)))
    return out


def _named(w):
    """The dialogs of the ticket, built as the window builds them."""
    from ogr_core.project.settings import GroundwaterSettings
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    from ogr_gui.dialogs.transient_stages_dialog import TransientStagesDialog
    return {
        "hydraulic": lambda: HydraulicPropertiesDialog(w.project, None),
        "transient": lambda: TransientStagesDialog(GroundwaterSettings()),
    }


def _explicit(w):
    """Dialogs whose constructor needs more than the project."""
    from ogr_core.geometry import Vertex
    from ogr_core.project.settings import GroundwaterSettings
    from ogr_core.support import SupportInstance
    from ogr_gui.dialogs import (annotations_dialog, load_dialogs,
                                 material_properties_dialog, snap_dialog,
                                 support_properties_dialog,
                                 transient_stages_dialog)
    from ogr_gui.dialogs.boundary_dialogs import AssignMaterialDialog
    from ogr_gui.dialogs.project_settings_dialog import ProjectSettingsDialog
    # found by name, wherever they live: one import line per module
    # would be a second list of where each dialog is defined
    wanted = ("DisplayOptionsDialog", "SeismicLoadDialog",
              "SelectionFilterDialog", "EditCoordinatesDialog",
              "ChangeSlopeAngleDialog", "GeometryCleanupDialog")
    found = {}
    for m in pkgutil.iter_modules(
            importlib.import_module("ogr_gui.dialogs").__path__):
        mod = importlib.import_module("ogr_gui.dialogs." + m.name)
        for name in wanted:
            cls = getattr(mod, name, None)
            if cls is not None and cls.__module__ == mod.__name__:
                found[name] = cls
    DisplayOptionsDialog = found["DisplayOptionsDialog"]
    SeismicLoadDialog = found["SeismicLoadDialog"]
    SelectionFilterDialog = found["SelectionFilterDialog"]
    EditCoordinatesDialog = found["EditCoordinatesDialog"]
    ChangeSlopeAngleDialog = found["ChangeSlopeAngleDialog"]
    GeometryCleanupDialog = found["GeometryCleanupDialog"]
    p = w.project
    st = p.support_types[0]
    support = SupportInstance(type_id=st.TYPE_ID, type_ref=st.id,
                              head=Vertex(30.0, 20.0), tail=Vertex(36.0, 17.0))
    return {
        "TransientStagesDialog":
            lambda: transient_stages_dialog.TransientStagesDialog(
                GroundwaterSettings()),
        "MaterialPropertiesDialog":
            lambda: material_properties_dialog.MaterialPropertiesDialog(
                p.materials, w),
        "SupportInstancePropertiesDialog":
            lambda: support_properties_dialog.SupportInstancePropertiesDialog(
                support, p, w),
        "AnnotationsDialog":
            lambda: annotations_dialog.AnnotationsDialog(p.annotations, w),
        "AssignMaterialDialog":
            lambda: AssignMaterialDialog(p.materials, None, w),
        "SnapDialog": lambda: snap_dialog.SnapDialog(w.canvas.snap_settings,
                                                     parent=w),
        "DistributedLoadDialog":
            lambda: load_dialogs.DistributedLoadDialog(parent=w),
        "LineLoadDialog": lambda: load_dialogs.LineLoadDialog(parent=w),
        "ProjectSettingsDialog":
            lambda: ProjectSettingsDialog(p.settings, w, project=p),
        "DisplayOptionsDialog":
            lambda: DisplayOptionsDialog(w.canvas.display_options, w),
        "SeismicLoadDialog": lambda: SeismicLoadDialog(p.seismic, w),
        "SelectionFilterDialog":
            lambda: SelectionFilterDialog(w.selection_filter, w),
        "EditCoordinatesDialog":
            lambda: EditCoordinatesDialog(p.boundaries[0], w),
        "ChangeSlopeAngleDialog": lambda: ChangeSlopeAngleDialog(45.0, w),
        "GeometryCleanupDialog":
            lambda: GeometryCleanupDialog("Geometry cleanup report", w),
    }


def _census(w):
    """Every QDialog of ``ogr_gui.dialogs`` that opens on the project alone,
    plus the explicit ones above, by name."""
    import ogr_gui.dialogs as pkg
    from PySide6.QtWidgets import QDialog
    p = w.project
    found = {}
    for m in pkgutil.iter_modules(pkg.__path__):
        mod = importlib.import_module("ogr_gui.dialogs." + m.name)
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if issubclass(cls, QDialog) and cls.__module__ == mod.__name__:
                found[name] = cls

    def generic(cls):
        def build():
            for args in ((p, w), (p,), (p.settings, w), (w,), ()):
                try:
                    return cls(*args)
                except Exception:  # noqa: BLE001 - another signature
                    continue
            return None
        return build

    builders = {name: generic(cls) for name, cls in found.items()
                if not name.startswith("_")}
    builders.update(_explicit(w))
    return builders


def _measure(app, build):
    """``(minimum, cut at the minimum, squeezed where it opens or at the
    minimum)`` of the dialog ``build`` returns, or None when it does not
    open on this model."""
    try:
        d = build()
    except Exception:  # noqa: BLE001 - the census skips what needs more
        return None
    if d is None:
        return None
    try:
        d.show()
        app.processEvents()
        squeezed = _squeezed(d)
        ms = d.minimumSizeHint()
        d.resize(ms)
        app.processEvents()
        return (ms.width(), ms.height()), _cut(d), squeezed + _squeezed(d)
    finally:
        d.hide()
        d.deleteLater()
        app.processEvents()


# ----------------------------------------------------------------------
class TestTheNamedDialogs:
    def test_they_open_with_no_cut_button(self):
        w = _window()
        try:
            for theme in ("light", "dark"):
                with _spanish_with(theme) as app, _no_modals():
                    for name, build in _named(w).items():
                        d = build()
                        d.show()
                        app.processEvents()
                        assert _cut(d) == [], (theme, name, _cut(d))
                        d.hide()
                        d.deleteLater()
        finally:
            _done(w)

    def test_the_hydraulic_one_does_not_scroll_sideways(self):
        w = _window()
        try:
            for theme in ("light", "dark"):
                with _spanish_with(theme) as app, _no_modals():
                    d = _named(w)["hydraulic"]()
                    d.show()
                    app.processEvents()
                    for size in (d.size(), d.minimumSizeHint()):
                        d.resize(size)
                        app.processEvents()
                        bar = d.scroll.horizontalScrollBar()
                        assert not bar.isVisible(), (theme, size)
                    d.hide()
                    d.deleteLater()
        finally:
            _done(w)

    def test_ok_and_cancel_keep_the_width_of_the_theme(self):
        from PySide6.QtWidgets import QDialogButtonBox
        w = _window()
        try:
            with _spanish_with("light") as app, _no_modals():
                d = _named(w)["transient"]()
                d.show()
                app.processEvents()
                box = d.findChildren(QDialogButtonBox)[0]
                for b in box.buttons():
                    # min-width 70 plus the 14 px padding on each side
                    assert b.width() >= 98, (b.text(), b.width())
                d.hide()
                d.deleteLater()
        finally:
            _done(w)


class TestTheCensus:
    def test_no_dialog_cuts_a_button_or_outgrows_the_screen(self):
        w = _window()
        try:
            for theme in ("light", "dark"):
                with _spanish_with(theme) as app, _no_modals():
                    measured, bad = 0, []
                    for name, build in sorted(_census(w).items()):
                        got = _measure(app, build)
                        if got is None:
                            continue
                        measured += 1
                        (mw, mh), cut, squeezed = got
                        if (cut or squeezed or mw > _SCREEN[0]
                                or mh > _SCREEN[1]):
                            bad.append((name, (mw, mh), cut, squeezed))
                    # the census has to see something to mean anything
                    assert measured >= 35, measured
                    assert bad == [], (theme, bad)
        finally:
            _done(w)


class TestTheFloor:
    def test_it_is_inert_without_a_theme(self):
        """Installed by ``apply_theme`` and never removed: with the style
        sheet put back, a box button gets no floor from it."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
        from ogr_gui import button_floor
        app = QApplication.instance() or QApplication([])
        button_floor.install(app)
        sheet = app.styleSheet()
        try:
            app.setStyleSheet("")
            d = QDialog()
            QVBoxLayout(d).addWidget(QDialogButtonBox(QDialogButtonBox.Ok))
            d.show()
            app.processEvents()
            ok = d.findChildren(QDialogButtonBox)[0].buttons()[0]
            assert ok.minimumWidth() == 0
            d.hide()
            d.deleteLater()
        finally:
            app.setStyleSheet(sheet)
