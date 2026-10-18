# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.321 (D300, the labels; D240) — the rows of Define Materials, the names
of the strength models and the soil textures of Pick read in the interface
language, and no key of the Spanish dictionary is written twice.

The defect (D300, its last family): three lists of the interface came from
the core and skipped ``tr()``, so they read in English whatever the
language:

* each parameter row of Define Materials was labelled with the parameter's
  KEY (``QLabel(f"{name}:")``: «cohesion:», «friction_angle:», «mb:»),
  while the core keeps, for every parameter, a description
  (``PARAMETERS = {key: (default, unit, description)}``) that only the
  tooltip showed. By decision of the owner the row now reads the
  description, translated, and the tooltip carries the key and the unit for
  whoever writes a script against the API. The editors stay keyed by the
  parameter, so nothing that reads or writes them moved;
* the strength combo, and the three other places that name the model of a
  material, showed ``DISPLAY_NAME`` as written in the core;
* Pick in the hydraulic dialog listed the keys of ``MATERIAL_LIBRARY``.
  They are the API's contract (``hydraulic_set(library="Sandy loam")``), so
  the list shows them translated and maps the choice back to the key.

``tr(variable)`` is invisible to the coverage test of v0.1.41, which reads
literal keys, so this file checks the core's lists themselves: every
description, every model name and every texture has its Spanish. A new
model or parameter without it fails here. The model names that are
eponyms (Mohr-Coulomb, Hoek-Brown, Barton-Bandis, SHANSEP) read the same in
Spanish and carry no entry; the list of them is checked to be exact, so it
cannot go stale.

The defect (D240): 20 keys of the Spanish dictionary were written two or
three times, 22 surplus entries. A repeated key in a dict literal is legal
Python and the last one wins without a word, so the file said two things
where one read it: «Add Grid» was «Añadir malla» and then «Añadir
rejilla», «None» was «Ninguno», «Ninguna» and «Ninguno». The surplus
entries are gone, each key keeping the text that already won, so no text
on screen moved. The check reads the SOURCE with the AST because the dict
object has already lost the duplicates.

Controls: in English the rows read the core's descriptions verbatim, and
Pick in English and in Spanish load the same values for the same texture.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

_ROOT = Path(__file__).resolve().parents[1]
_WINDOWS: list = []

#: Model names that are a person's or a method's name and read the same in
#: Spanish: they carry no entry, on purpose.
EPONYMS = {"Mohr-Coulomb", "Hoek-Brown", "Barton-Bandis", "SHANSEP"}


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _spanish():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


def _textures():
    from ogr_core.hydraulic import PermeabilityModel, library_for
    out = set()
    for model in PermeabilityModel:
        out.update(library_for(model) or {})
    return out


class TestEveryLabelOfTheCoreHasSpanish:
    def test_every_parameter_description(self):
        from ogr_core.materials import REGISTRY
        es = _spanish()
        missing = sorted({desc for cls in REGISTRY.all().values()
                          for _d, _u, desc in cls.PARAMETERS.values()
                          if desc not in es})
        assert not missing, missing

    def test_every_model_name_but_the_eponyms(self):
        from ogr_core.materials import REGISTRY
        es = _spanish()
        names = {cls.DISPLAY_NAME for cls in REGISTRY.all().values()}
        assert {n for n in names if n not in es} == EPONYMS

    def test_every_soil_texture_and_no_two_alike(self):
        """Distinct, because Pick maps the shown text back to the key."""
        es = _spanish()
        textures = _textures()
        assert textures and all(t in es for t in textures), \
            sorted(t for t in textures if t not in es)
        assert len({es[t] for t in textures}) == len(textures)


class TestNoKeyOfTheDictionaryIsWrittenTwice:
    def test_the_source_has_each_key_once(self):
        path = _ROOT / "ogr_gui" / "i18n" / "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        repeated = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            seen = set()
            for key in node.keys:
                if isinstance(key, ast.Constant):
                    if key.value in seen:
                        repeated.append((key.lineno, key.value))
                    seen.add(key.value)
        assert not repeated, repeated

    def test_the_two_that_disagreed_keep_the_text_that_won(self):
        es = _spanish()
        assert es["Add Grid"] == "Añadir rejilla"
        assert es["None"] == "Ninguno"


def _material_dialog(language):
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog,
    )
    from ogr_gui.i18n import set_language
    QApplication.instance() or QApplication([])
    set_language(language)
    m = Material(name="M", strength=MohrCoulomb(cohesion=10,
                                                friction_angle=25))
    d = MaterialPropertiesDialog([m], None)
    _WINDOWS.append(d)
    d.list.setCurrentRow(0)
    return d


def _rows(panel):
    """{key: (label text, tooltip)} of the rows the panel shows."""
    form = panel._form
    return {key: (form.labelForField(ed).text(), ed.toolTip())
            for key, ed in panel._editors.items()}


@_requires_qt
class TestDefineMaterialsSpeaksSpanish:
    def test_every_row_of_every_model_reads_its_description(self):
        from ogr_core.materials import REGISTRY
        from ogr_gui.i18n import current_language, set_language, tr
        before = current_language()
        try:
            d = _material_dialog("es")
            panel = d.param_panel
            checked = 0
            for cls in REGISTRY.all().values():
                if not cls.PARAMETERS:
                    continue
                panel.set_model(cls, {})
                rows = _rows(panel)
                assert set(rows) == set(cls.PARAMETERS), cls.MODEL_ID
                for key, (_d, unit, desc) in cls.PARAMETERS.items():
                    label, tip = rows[key]
                    assert label == tr(desc) + ":", (cls.MODEL_ID, label)
                    assert label != desc + ":", (cls.MODEL_ID, label)
                    assert tip.startswith(key), (cls.MODEL_ID, tip)
                    checked += 1
            assert checked > 40, checked
        finally:
            set_language(before)

    def test_the_strength_combo_names_the_models_in_spanish(self):
        from ogr_core.materials import REGISTRY
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            d = _material_dialog("es")
            es = _spanish()
            combo = d.cbo_strength
            shown = {combo.itemData(i): combo.itemText(i)
                     for i in range(combo.count())}
            for mid, cls in REGISTRY.all().items():
                assert shown[mid] == es.get(cls.DISPLAY_NAME,
                                            cls.DISPLAY_NAME), mid
            assert shown["undrained"] == "Sin drenaje (φ=0)"
        finally:
            set_language(before)

    def test_control_in_english_the_rows_are_the_descriptions(self):
        from ogr_core.materials import MohrCoulomb
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            d = _material_dialog("en")
            d.param_panel.set_model(MohrCoulomb, {})
            rows = _rows(d.param_panel)
            for key, (_d, _u, desc) in MohrCoulomb.PARAMETERS.items():
                assert rows[key][0] == desc + ":", rows[key]
            assert d.cbo_strength.itemText(
                d.cbo_strength.findData("undrained")) == "Undrained (φ=0)"
        finally:
            set_language(before)


@_requires_qt
class TestPickSpeaksSpanish:
    def _pick(self, language, answer):
        """Pick for Brooks-Corey in ``language``, answering ``answer``;
        returns (the items shown, bc_lambda, bc_psi_b after OK)."""
        from PySide6.QtWidgets import QInputDialog
        from test_retention_dialog_v1268 import _dialog, _project
        from ogr_core.hydraulic import PermeabilityModel
        from ogr_gui.i18n import set_language
        set_language(language)
        p = _project(transient=False)
        d = _dialog(p)
        _WINDOWS.append(d)
        seen = []

        def fake(_parent, _title, _label, items, *_a, **_k):
            seen.extend(items)
            return answer, True

        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.BROOKS_COREY))
        raw = QInputDialog.__dict__.get("getItem")
        QInputDialog.getItem = staticmethod(fake)
        try:
            d._pick()
        finally:
            if raw is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw
        d._accept()
        h = p.materials[0].hydraulic
        return seen, h.bc_lambda, h.bc_psi_b

    def test_the_list_is_spanish_and_loads_the_keys_values(self):
        from ogr_core.hydraulic import PermeabilityModel, library_for
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            shown, lam, psi = self._pick("es", "Franco arenoso")
            lib = library_for(PermeabilityModel.BROOKS_COREY)
            es = _spanish()
            assert shown == sorted(es[k] for k in lib), shown
            assert "Sandy loam" not in shown
            want = lib["Sandy loam"]
            assert abs(lam - want["bc_lambda"]) < 1e-12, lam
            assert abs(psi - want["bc_psi_b"]) < 1e-9, psi
            # control: the same texture picked in English
            _en, lam_en, psi_en = self._pick("en", "Sandy loam")
            assert (lam, psi) == (lam_en, psi_en)
        finally:
            set_language(before)


# ---------------------------------------------------------------------------
# What is ON SCREEN, measured: the guard the two AST censuses cannot be.
#
# A label table handed to Qt by subscript (``addItem(labels[m], m)``), a
# core list (``cls.DISPLAY_NAME``) or an enum's ``.value`` reaches the
# screen through a variable, and neither the census of test_gui_spanish_v1318
# (literals and f-strings) nor test_i18n_coverage_v141 (literal tr keys)
# can see it. At 0.1.320 the main window and the 44 dialogs of the D293
# census, opened in Spanish, still showed 95 texts that read English.
#
# "Reads English" is a heuristic, written down so it is the same every run:
# the text holds one of the English words below, holds no Spanish letter
# (á, ñ…) and no Spanish function word, and is not the Spanish of any entry.
# The names the model itself carries (the project's, its materials',
# boundaries' and support types') are data and are removed first.

#: v0.1.322 — without the words that are also Spanish (horizontal,
#: vertical, material, global, local, no, factor): «Horizontal» as a support
#: orientation read as English and was a false alarm.
_ENGLISH = set("""the of to and or for with from by in on at is are this that
search options method methods surface surfaces grid slope block path auto
refine simulated annealing swarm particle analysis materials
boundary boundaries load loads support supports water pressure line point
points add delete edit define apply cancel close none all show hide display
settings project type name value values default model models number count
min max minimum maximum left right top bottom start end table function
functions strength unit weight angle force forces safety stress
stresses region regions vertex vertices crack tension seismic coefficient
stage stages time step steps mesh element elements node
nodes file open save new import export report results result critical
enabled disabled yes""".split())
_SPANISH_WORDS = set("""de del la las el los con por para sin una uno un al
y o en se""".split())

#: Texts that read English on purpose, by pattern, each with its reason.
#: Every pattern must still match something on screen (no ghosts).
#:
#: Not here because this test never sees it: the navigation bar matplotlib
#: puts on a chart ("Back to previous view", "Save the figure"…), which
#: stays English by decision of the owner — it is the library's text.
SHOWN_EXCEPTIONS = {
    r"^Could not read the DXF file: ":
        "a message of ogr_core, which speaks English like the whole API "
        "(the census opens the DXF dialog on no file at all)",
    r"^Corps of Engineers #[12]$":
        "the proper name of the method, like Spencer or Janbu",
    r"^[a-z][a-z0-9_]* \[[^\]]+\]$":
        "the tooltip of a parameter row of Define Materials: its key and "
        "unit, for whoever writes a script against the API",
    r"^(in|min)$":
        "a unit symbol (inch, minute), the same in Spanish",
    # v0.1.322 — the supports' exceptions of 0.1.321 are gone: the family
    # is translated (test_supports_spanish_v1322).
}


def _shown_texts(widget):
    from PySide6.QtWidgets import (QAbstractButton, QComboBox,
                                   QDialogButtonBox, QDockWidget, QGroupBox,
                                   QLabel, QTableWidget, QTabWidget, QWidget)
    out = [widget.windowTitle()]
    for w in [widget] + widget.findChildren(QWidget):
        if w.toolTip():
            out.append(w.toolTip())
        if isinstance(w, QDockWidget):
            # v0.1.324 (D315) — five dock titles were English
            out.append(w.windowTitle())
        if isinstance(w, QLabel):
            out.append(w.text())
        elif isinstance(w, QAbstractButton) and not isinstance(
                w.parent(), QDialogButtonBox):
            out.append(w.text())
        elif isinstance(w, QGroupBox):
            out.append(w.title())
        elif isinstance(w, QComboBox):
            out += [w.itemText(i) for i in range(w.count())]
        elif isinstance(w, QTabWidget):
            out += [w.tabText(i) for i in range(w.count())]
        elif isinstance(w, QTableWidget):
            for i in range(w.columnCount()):
                h = w.horizontalHeaderItem(i)
                if h is not None:
                    out.append(h.text())
            # v0.1.324 (D315) — and the cells: the Method column showed the
            # method's identifier
            for r in range(min(w.rowCount(), 20)):
                for c in range(w.columnCount()):
                    item = w.item(r, c)
                    if item is not None:
                        out.append(item.text())
    return [t for t in out if t]


def _stored_identifiers():
    """The identifiers the .ogr keeps that have a label in ogr_gui.labels:
    one on screen means a label was not used (D315)."""
    from ogr_gui import labels as L
    ids = set(L.METHOD_NAMES)
    for table in (L.PORE_PRESSURE, L.GROUNDWATER_METHOD, L.LOAD_ORIENTATION,
                  L.FORCE_ORIENTATION):
        ids |= {getattr(k, "value", k) for k in table}
    return {i for i in ids if "_" in i}


def _reads_english(text, spanish, data_names, identifiers=()):
    import re
    if text in spanish:
        return False
    plain = re.sub(r"<[^>]+>", " ", text)
    for name in data_names:
        plain = plain.replace(name, " ")
    # v0.1.324 (D315) — a stored identifier reads English whatever Spanish
    # surrounds it («Método: bishop_simplified  Válidas: …»)
    if any(re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(i), plain) for i in identifiers):
        return True
    if re.search(r"[áéíóúüñÁÉÍÓÚÑ¿¡]", plain):
        return False
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", plain)]
    if any(w in _SPANISH_WORDS for w in words):
        return False
    return any(w in _ENGLISH for w in words)


@_requires_qt
class TestNothingOnScreenReadsEnglish:
    def test_the_window_and_every_dialog_of_the_census(self):
        import re
        import test_dialogs_fit_v1315 as fit
        from ogr_core.support import EndAnchored
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.main_window import MainWindow
        before = current_language()
        es = _spanish()
        spanish = set(es.values())
        found = {}
        QApplication.instance() or QApplication([])
        set_language("es")
        # the census's own window, built in Spanish instead of English
        w = MainWindow()
        try:
            w.act_load_demo()
            w.project.support_types = [
                EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)]
            w.project.is_dirty = False
            # v0.1.324 (D315) — computed, so that the results panel, its
            # table and the status bar have something to say
            from test_design_factor_report_gui_v1165 import _compute_all
            _compute_all(w)
            w.project.is_dirty = False
            ids = _stored_identifiers()
            p = w.project
            data_names = sorted(
                {n for n in [p.name] + [m.name for m in p.materials]
                 + [getattr(b, "name", "") for b in p.boundaries]
                 + [getattr(s, "_display_name", "")
                    for s in p.support_types] if n},
                key=len, reverse=True)
            for t in _shown_texts(w) + [w.ogr_status.currentMessage()]:
                if t and _reads_english(t, spanish, data_names, ids):
                    found.setdefault(t, set()).add("MainWindow")
            opened = 0
            with fit._no_modals():
                for name, build in sorted(fit._census(w).items()):
                    try:
                        d = build()
                    except Exception:  # noqa: BLE001 - the census skips
                        continue
                    if d is None:
                        continue
                    _WINDOWS.append(d)
                    opened += 1
                    for t in _shown_texts(d):
                        if _reads_english(t, spanish, data_names, ids):
                            found.setdefault(t, set()).add(name)
            assert opened > 40, opened
            # and Interpret, on the reference slope
            from test_gui_spanish_v1318 import _interpret_window
            ip, iw = _interpret_window("es")
            names = sorted({n for n in [ip.name] + [m.name for m in
                                                    ip.materials] if n},
                           key=len, reverse=True)
            for t in _shown_texts(iw):
                if _reads_english(t, spanish, names, ids):
                    found.setdefault(t, set()).add("InterpretWindow")
        finally:
            set_language(before)
            fit._done(w)
        left = {t: sorted(v) for t, v in found.items()
                if not any(re.search(p, t) for p in SHOWN_EXCEPTIONS)}
        assert not left, left
        ghosts = [p for p in SHOWN_EXCEPTIONS
                  if not any(re.search(p, t) for t in found)]
        assert not ghosts, ghosts


# ---------------------------------------------------------------------------
# ogr_gui.labels: one name per stored identifier.

#: Labels that read the same in Spanish and so carry no entry: proper names
#: of methods and unit symbols. Checked exact, so it cannot go stale.
SAME_IN_SPANISH = {"Spencer", "GLE / Morgenstern-Price",
                   "Corps of Engineers #1", "Corps of Engineers #2",
                   "Lowe-Karafiath", "s", "min", "h", "d", "m/s", "cm/s",
                   # v0.1.322 — a support's force orientation
                   "Horizontal"}


def _label_tables():
    from ogr_core.loads.loads import LoadDistribution, LoadOrientation
    from ogr_core.materials.material import PorePressureType
    from ogr_core.project.settings import GroundwaterMethod
    from ogr_core.project.units import PermeabilityUnit, TimeUnit
    from ogr_core.support import ForceApplication, ForceOrientation
    from ogr_gui import labels as L
    return ((L.FORCE_APPLICATION, ForceApplication),
            (L.FORCE_ORIENTATION, ForceOrientation),
            (L.PORE_PRESSURE, PorePressureType),
            (L.GROUNDWATER_METHOD, GroundwaterMethod),
            (L.LOAD_ORIENTATION, LoadOrientation),
            (L.LOAD_DISTRIBUTION, LoadDistribution),
            (L.TIME_UNIT, TimeUnit),
            (L.PERMEABILITY_UNIT, PermeabilityUnit))


class TestEveryIdentifierHasItsLabel:
    def test_every_member_of_every_enum(self):
        from ogr_core.project.settings import LEMMethod
        from ogr_gui.labels import METHOD_NAMES
        for table, enum in _label_tables():
            assert set(table) == set(enum), enum
        assert set(METHOD_NAMES) == {m.value for m in LEMMethod}

    def test_every_label_has_spanish_or_reads_the_same(self):
        from ogr_gui.labels import METHOD_NAMES
        es = _spanish()
        labels = set(METHOD_NAMES.values())
        for table, _enum in _label_tables():
            labels |= set(table.values())
        assert {t for t in labels if t not in es} == SAME_IN_SPANISH

    def test_the_method_names_are_the_engines(self):
        """The table lives here so that ogr_gui does not import the engine
        for a settings dialog; it must say what the engine says."""
        from ogr_gui.labels import METHOD_NAMES
        from ogr_slip2d.methods import method_registry
        reg = method_registry()
        assert {k: reg[k].DISPLAY_NAME for k in METHOD_NAMES} == METHOD_NAMES


def _menu_texts(open_menu):
    """The texts of the popup menu ``open_menu()`` shows.

    ``QMenu.exec`` cannot be replaced on the class — measured on this
    PySide6, the assignment is ignored and ``exec`` blocks for ever without
    a screen. So a timer runs inside the menu's own loop, reads the visible
    menu and closes it, which returns from ``exec``. The retry cap keeps a
    menu that never appears from hanging the suite."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMenu
    seen = []
    tries = [0]

    def grab():
        tries[0] += 1
        menus = [m for m in QApplication.topLevelWidgets()
                 if isinstance(m, QMenu) and m.isVisible()]
        if not menus and tries[0] < 200:
            QTimer.singleShot(10, grab)
            return
        for m in menus:
            seen.extend(a.text() for a in m.actions() if a.text())
            m.close()

    QTimer.singleShot(0, grab)
    open_menu()
    return seen


def _demo_window(language):
    from ogr_core.geometry import Vertex
    from ogr_core.support import EndAnchored, SupportInstance
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language(language)
    w = MainWindow()
    _WINDOWS.append(w)
    w.act_load_demo()
    st = EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)
    w.project.support_types = [st]
    w.project.supports.append(SupportInstance(
        type_id=st.TYPE_ID, type_ref=st.id,
        head=Vertex(30.0, 20.0), tail=Vertex(36.0, 17.0)))
    w.project.is_dirty = False
    return w


@_requires_qt
class TestTheCanvasMenusSpeakSpanish:
    def _menus(self, language):
        from PySide6.QtCore import QPoint
        w = _demo_window(language)
        c = w.canvas
        try:
            return (_menu_texts(lambda: c._show_vertex_context_menu(
                        QPoint(0, 0), (0, 0)))
                    + _menu_texts(lambda: c._show_boundary_context_menu(
                        QPoint(0, 0), 0))
                    + _menu_texts(lambda: c._show_support_context_menu(
                        QPoint(0, 0), 0))
                    + _menu_texts(lambda: c._show_drawing_context_menu(
                        QPoint(0, 0))))
        finally:
            w.project.is_dirty = False
            w.close()

    def test_the_vertex_boundary_support_and_drawing_menus(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            es = self._menus("es")
            for t in ("Insertar vértice (después)", "Editar coordenadas…",
                      "Convertir contorno…", "Expandir / contraer…",
                      "Cambiar ángulo del talud…", "Propiedades…",
                      "Estirar", "Modificar patrón…", "Orto",
                      # v0.1.323 — as the legend writes it (OSNAP), the
                      # same in both languages
                      "OSnap"):
                assert t in es, (t, es)
            # control: the English is what it was
            en = self._menus("en")
            for t in ("Insert Vertex (after)", "Expand / Shrink…",
                      "Stretch", "Ortho", "OSnap"):
                assert t in en, (t, en)
        finally:
            set_language(before)


def _page(dialog, cls_name):
    return next(p for p in dialog.pages if type(p).__name__ == cls_name)


@_requires_qt
class TestProjectSettingsSpeaksSpanish:
    def _dialog(self, language):
        from ogr_core.project.project import Project
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language(language)
        p = Project(name="D300")
        d = ProjectSettingsDialog(p.settings, None, project=p)
        _WINDOWS.append(d)
        return d

    @staticmethod
    def _items(combo):
        return [(combo.itemText(i), combo.itemData(i))
                for i in range(combo.count())]

    def test_pages_units_methods_and_groundwater(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            d = self._dialog("es")
            pages = [d.nav.item(i).text() for i in range(d.nav.count())]
            for t in ("Métodos", "Sismo", "Resumen del proyecto"):
                assert t in pages, pages
            general = _page(d, "_GeneralPage")
            units = [t for t, _ in self._items(general.cbo_unit_system)]
            assert "Métrico, tensiones en kPa" in units, units
            times = [t for t, _ in self._items(general.cbo_time)]
            assert "mes" in times and "año" in times, times
            methods = _page(d, "_MethodsPage").checkboxes
            assert methods["bishop_simplified"].text() == \
                "Bishop simplificado"
            gw = self._items(_page(d, "_GroundwaterPage").cbo_method)
            assert ("Elementos finitos: régimen permanente",
                    "fea_steady") in gw, gw
            # no identifier on screen, in either language
            assert all(t != data for t, data in gw), gw
            d_en = self._dialog("en")
            gw_en = self._items(_page(d_en, "_GroundwaterPage").cbo_method)
            assert ("Finite Element: Steady State", "fea_steady") in gw_en
            assert all(t != data for t, data in gw_en), gw_en
            # control: the page names are what they were
            assert "Methods" in [d_en.nav.item(i).text()
                                 for i in range(d_en.nav.count())]
        finally:
            set_language(before)


@_requires_qt
class TestThePorePressureComboNamesItsChoice:
    def test_in_spanish_and_in_english(self):
        from ogr_core.materials.material import PorePressureType
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            for language, want in (("es", "Nivel freático"),
                                   ("en", "Water Table")):
                d = _material_dialog(language)
                combo = d.cbo_pp
                i = combo.findData(PorePressureType.WATER_TABLE)
                assert combo.itemText(i) == want, combo.itemText(i)
                assert all(combo.itemText(k) != combo.itemData(k).value
                           for k in range(combo.count()))
        finally:
            set_language(before)


@_requires_qt
class TestTheStatisticsWindowNamesTheMethod:
    def test_the_method_combo(self):
        from test_statistics_gui_v138 import (_define_vars, _project,
                                              _window)
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.statistics_window import StatisticsWindow
        before = current_language()
        QApplication.instance() or QApplication([])
        try:
            set_language("es")
            p = _project(n=6)
            _define_vars(p)
            w = _window(p)
            _WINDOWS.append(w)
            w._compute_statistics()
            sw = StatisticsWindow(w.project, w._prob_result,
                                  w._sens_result, None)
            _WINDOWS.append(sw)
            combo = sw.cbo_method
            shown = {combo.itemData(i): combo.itemText(i)
                     for i in range(combo.count())}
            assert shown.get("bishop_simplified") == "Bishop simplificado", \
                shown
            assert all(t != mid for mid, t in shown.items()), shown
            w.project.is_dirty = False
            w.close()
        finally:
            set_language(before)


class TestRandomVariablesAreShownTranslated:
    def _rv(self, kind, param, label):
        from ogr_core.statistics import Distribution, DistributionType
        from ogr_core.statistics.random_variables import (RandomVariable,
                                                          VariableKind)
        return RandomVariable(kind=VariableKind(kind), target_id="t",
                              param=param, label=label,
                              distribution=Distribution(
                                  DistributionType.NORMAL, mean=1.0))

    def test_the_shown_label_and_the_stored_one(self):
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.labels import random_variable_label
        before = current_language()
        cases = [
            (("material_strength", "friction_angle", "Clay — friction_angle"),
             "Clay — ángulo de rozamiento"),
            (("material", "unit_weight", "Clay — unit_weight"),
             "Clay — peso específico"),
            (("hydraulic", "ks", "Clay — hydraulic ks"),
             "Clay — ks (hidráulico)"),
            # v0.1.325 (D318) — the parameter by its symbol
            (("seismic", "kh", "seismic kh"), "coeficiente sísmico k_h"),
            (("water_table", "offset", "Water table — vertical offset"),
             "Nivel freático — desplazamiento vertical"),
            (("distributed_load", "magnitude_1", " — magnitude_1"),
             "Carga distribuida — magnitud 1"),
            # a label edited in a file is shown as it is
            (("material_strength", "cohesion", "my own label"),
             "my own label"),
        ]
        try:
            set_language("es")
            for args, want in cases:
                rv = self._rv(*args)
                assert random_variable_label(rv) == want, (args, want)
                assert rv.label == args[2]
            # control: in English the stored label reads as before
            set_language("en")
            rv = self._rv("material_strength", "friction_angle",
                          "Clay — friction_angle")
            assert random_variable_label(rv) == "Clay — friction angle"
        finally:
            set_language(before)


class TestTheDataTipsSpeakSpanish:
    def test_material_boundary_and_load(self):
        from test_slide_validation_ej1 import _ej1_project
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad
        from ogr_gui.data_tips import (DataTipMode, boundary_tip, load_tip,
                                       material_tip)
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        p = _ej1_project()
        ext = next(b for b in p.boundaries if b.btype.name == "EXTERNAL")
        load = DistributedLoad(start=Vertex(0, 0), end=Vertex(5, 0),
                               magnitude_1=10.0)
        try:
            set_language("es")
            assert "peso específico" in material_tip(p.materials[0])
            assert boundary_tip(ext).startswith("EXTERNO")
            tip = load_tip(load, DataTipMode.MAXIMUM)
            assert tip.splitlines()[0] == "Carga distribuida", tip
            assert "orientación: Normal al contorno" in tip, tip
            # control: the English the tips have always shown
            set_language("en")
            assert "unit weight" in material_tip(p.materials[0])
            assert boundary_tip(ext).startswith("EXTERNAL")
            assert "orientation: Normal to Boundary" in load_tip(load)
        finally:
            set_language(before)
