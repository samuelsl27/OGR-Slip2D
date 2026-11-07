# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.433 (D411) — the English on screen that no census read: the interface's
half (the core's messages and the undo names are D412, v0.1.434).

The invariant: with the interface in Spanish, each place listed below reads
Spanish where the user reads it, by the rules ``ogr_gui/labels.py`` holds;
the agent, the command line and the ``.ogr`` keep their English and their
data unchanged; and the censuses see the paths these texts came by.

What was found (the review of v0.1.432, three read-only explorers measuring
it on 2f498f6, and the owner's decisions of 2026-11-07):

* identifiers on screen: the search method («Búsqueda: grid»), the boundary
  conditions' summary («nodal_flow: 21»), the cleanup report («[0] EXTERNAL
  «External Boundary»»), the DXF import's counts («EXTERNAL: 1»), the
  property tables («water_table», «cohesion», «shear»), the method in Export
  Raw Data, the stored label of a random variable («friction_angle»), and
  32 fields of coded notes measured down to 11 that held one with no kind;
* English beside a translated text: the startup message (``tr("Ready") +
  " — File → …"``), the Selection Filter's fields and «nothing selectable»,
  «no conditions», the random variable's plot, «ΔFoS», the DXF preview's
  error, a coded refusal shown raw (the drawdown sweep), « deg»;
* default names the program gives, in English: «Untitled» and «Demo slope»
  (translated by the owner's decision), «Original ground (from
  Expand/Shrink)», a support set an agent creates without a name, the
  report's «Untitled Project»;
* «[BC]» written into a stage's label, which the ``.ogr`` keeps: no longer
  written (the owner's decision); a stage with its own conditions is marked
  in a column of its own and as «[CC]» in Interpret Groundwater;
* two dialogs no menu opened: the sensitivity tornado is connected, and
  Graph SF Along Slope draws with SFAlongSlopeDialog (the owner's
  decisions).

What is checked here: each place through the real window or dialog, in
Spanish and in English (control), every replaced static put back exactly;
the two identities of the charts (the tornado's bars are the ranking's
numbers; the factor along the slope is the series the engine computes, and
its minimum is the population's); the agent's English and the data
unchanged; the new census rules on sources of their own.

One main window for the file, apart from the dialogs the tests keep alive.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

_WINDOW: list = []
_KEPT: list = []


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced for the block and put back exactly."""
    raw = owner.__dict__.get(name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is None:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


_STARTUP: list = []


def _window():
    """The main window, built in Spanish once, with the demo loaded."""
    if not _WINDOW:
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        with _language("es"):
            w = MainWindow()
            # what the constructor put on the status bar, before the demo
            _STARTUP.append(w.ogr_status.currentMessage())
            w.project.is_dirty = False
            w.act_load_demo()
            w.project.is_dirty = False
        _WINDOW.append(w)
    return _WINDOW[0]


def _texts_of_figure(widget):
    """The texts of every matplotlib figure inside ``widget``."""
    from PySide6.QtWidgets import QWidget
    out = []
    for w in [widget] + widget.findChildren(QWidget):
        for ax in getattr(getattr(w, "figure", None), "axes", None) or []:
            out += [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
            out += [t.get_text() for t in ax.texts]
            legend = ax.get_legend()
            if legend is not None:
                out += [t.get_text() for t in legend.get_texts()]
    return [t for t in out if t]


# ---------------------------------------------------------------------------
class TestTheLabelTablesMatchWhatTheyName:
    """Each table of ogr_gui.labels against the identifiers it names."""

    def test_support_choices_are_the_cores(self):
        from ogr_core.support.support import PARAMETER_CHOICES
        from ogr_gui.labels import SUPPORT_CHOICES
        for param, choices in SUPPORT_CHOICES.items():
            if param in PARAMETER_CHOICES:
                assert {d for _l, d in choices} == \
                    set(PARAMETER_CHOICES[param]), param

    def test_drawdown_procedures_and_techniques_are_the_engines(self):
        from ogr_gui.labels import DRAWDOWN_PROCEDURE, OPTIMIZE_TECHNIQUE
        from ogr_slip2d.optimize import TECHNIQUES
        from ogr_slip2d.rapid_drawdown import B_BAR, MULTISTAGE_METHODS
        assert set(DRAWDOWN_PROCEDURE) == set(MULTISTAGE_METHODS) | {B_BAR}
        assert set(OPTIMIZE_TECHNIQUE) == set(TECHNIQUES)

    def test_surface_types_and_kinds(self):
        from ogr_core.project.settings import SurfaceType
        from ogr_gui.labels import SURFACE_KIND, SURFACE_TYPE
        assert set(SURFACE_TYPE) == {t.value for t in SurfaceType}
        assert {"circle", "polyline", "composite", "weak_layer"} <= \
            set(SURFACE_KIND)

    def test_default_names_and_given_ones(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.geometry.expand_shrink import REMOVED_ARC_NAME
        from ogr_gui.labels import (boundary_name, default_support_name,
                                    project_label, support_type_label)
        from test_spanish_texts_v1432 import _line
        with _language("es"):
            assert project_label("Untitled") == "Sin título"
            assert project_label("Demo slope") == "Talud de ejemplo"
            assert project_label("Presa norte") == "Presa norte"
            arc = _line(BoundaryType.MATERIAL, name=REMOVED_ARC_NAME)
            assert boundary_name(arc) == \
                "Terreno original (de Expandir / contraer)"
            assert boundary_name(_line(BoundaryType.MATERIAL,
                                       name="Arcilla")) == "Arcilla"

            class Set:
                DISPLAY_NAME = "End Anchored"
            s = Set()
            for given, shown in (("End Anchored", "Anclado en el extremo"),
                                 ("End Anchored (2)",
                                  "Anclado en el extremo (2)"),
                                 ("Norte", "Norte")):
                s._display_name = given
                assert support_type_label(s) == shown, given
            assert default_support_name("Norte") is None
        with _language("en"):
            assert project_label("Untitled") == "Untitled"
            assert boundary_name(arc) == REMOVED_ARC_NAME


@_requires_qt
class TestTheWindowSaysItInSpanish:
    def test_the_startup_message(self):
        from ogr_gui.main_window import MainWindow
        _window()
        # the window's own, as the constructor shows it (review of 0.1.433)
        assert _STARTUP[0] == (
            "Listo — Archivo → Cargar talud de ejemplo para empezar con "
            "un modelo de muestra."), _STARTUP
        with _language("es"):
            assert MainWindow._startup_message() == (
                "Listo — Archivo → Cargar talud de ejemplo para empezar con "
                "un modelo de muestra.")
        with _language("en"):
            assert MainWindow._startup_message() == (
                "Ready — File → Load Demo Slope to start with a sample "
                "model.")

    def test_the_selection_filter(self):
        from dataclasses import replace
        import ogr_gui.main_window as mw
        w = _window()
        kept = w.selection_filter
        seen = {}
        try:
            with _swapped(mw.SelectionFilterDialog, "exec", lambda _s: 1):
                for language in ("es", "en"):
                    with _language(language):
                        w.selection_filter = kept
                        w.act_selection_filter()
                        seen[language] = w.ogr_status.currentMessage()
                with _language("es"):
                    w.selection_filter = replace(kept, **{
                        f: False for f in kept.__dataclass_fields__})
                    w.act_selection_filter()
                    seen["none"] = w.ogr_status.currentMessage()
        finally:
            w.selection_filter = kept
            w.canvas.selection_filter = kept
        assert seen["es"] == ("Filtro de selección: contornos, vértices, "
                              "materiales, soportes, cargas, superficies de "
                              "rotura"), seen
        assert seen["en"] == ("Selection filter: boundaries, vertices, "
                              "materials, supports, loads, slip surfaces")
        assert seen["none"] == "Filtro de selección: nada seleccionable"

    def test_the_selectable_fields_are_the_dialogs(self):
        from dataclasses import fields
        from ogr_gui.dialogs.boundary_dialogs import SelectionFilterState
        from ogr_gui.labels import SELECTABLE
        assert list(SELECTABLE) == [f.name for f in
                                    fields(SelectionFilterState)]

    def test_the_search_method_and_the_information_viewer(self):
        from PySide6.QtWidgets import QMessageBox
        import ogr_gui.main_window as mw
        w = _window()
        shown = []
        with _swapped(mw.SurfaceOptionsDialog, "exec", lambda _s: 1), \
                _swapped(QMessageBox, "information", staticmethod(
                    lambda _p, _t, text, *a, **k: shown.append(text))), \
                _language("es"):
            w.act_surface_options()
            status = w.ogr_status.currentMessage()
            w.act_info_viewer()
        w.project.is_dirty = False
        assert status == ("Búsqueda de superficies configurada: Búsqueda por "
                          "rejilla"), status
        assert "<b>Búsqueda:</b> Búsqueda por rejilla" in shown[-1], shown
        assert "<b>Proyecto:</b> Talud de ejemplo" in shown[-1], shown

    def test_the_dxf_counts_and_the_previews_error(self):
        from types import SimpleNamespace
        from ogr_core.dxf.messages import NO_LAYER_ASSIGNED
        from ogr_gui.core_messages import preview_error_text
        from ogr_gui.main_window import MainWindow
        created = {"WATER_TABLE": 1, "EXTERNAL": 1, "MATERIAL": 2}
        pv = SimpleNamespace(error_code=NO_LAYER_ASSIGNED, error_args={},
                             error="No layer has been assigned a geometry "
                                   "type. Use the table to say what each "
                                   "layer represents.")
        with _language("es"):
            assert MainWindow._dxf_counts(created) == (
                "Contorno exterior: 1, Contorno de material: 2, Nivel "
                "freático: 1")
            assert preview_error_text(pv).startswith(
                "Ninguna capa tiene asignado un tipo de geometría")
        with _language("en"):
            assert MainWindow._dxf_counts(created) == (
                "External Boundary: 1, Material Boundary: 2, Water Table: 1")
        # the agent's keys are the stored ones, unchanged
        assert set(created) == {"WATER_TABLE", "EXTERNAL", "MATERIAL"}

    def test_import_dxf_says_it_through_the_handler(self):
        """Through ``act_import_dxf``, its file dialog and its import dialog
        swapped: the preview's error and the counts as the user reads them.
        ``preview_error_text`` already said it in 0.1.432; the handler did
        not ask it (review of 0.1.433)."""
        from types import SimpleNamespace
        import ogr_core.dxf as dxf
        import ogr_gui.dialogs.dxf_import_dialog as DI
        import ogr_gui.main_window as MW
        from ogr_core.dxf.messages import NO_LAYER_ASSIGNED
        w = _window()
        said = []
        bad = SimpleNamespace(ok=False, error_code=NO_LAYER_ASSIGNED,
                              error_args={},
                              error="No layer has been assigned a geometry "
                                    "type.")
        good = SimpleNamespace(ok=True, report=None, external_area=0.0,
                               area_matches=True)

        def dialog(pv):
            class _Dialog:
                result_preview, options = pv, None

                def __init__(self, *a, **k):
                    pass

                def exec(self):
                    return 1
            return _Dialog
        with _language("es"), \
                _swapped(MW, "get_open_file_name",
                         lambda *a, **k: ("x.dxf", "")), \
                _swapped(w, "_info", lambda m, *a, **k: said.append(m)):
            with _swapped(DI, "DxfImportDialog", dialog(bad)):
                w.act_import_dxf()
            kept = w.project
            with _swapped(DI, "DxfImportDialog", dialog(good)), \
                    _swapped(dxf, "apply_to_project",
                             lambda *a: {"EXTERNAL": 1, "MATERIAL": 2}):
                w.act_import_dxf()
                status = w.statusBar().currentMessage()
        assert w.project is kept
        assert said and said[0].startswith(
            "Ninguna capa tiene asignado un tipo de geometría"), said
        assert "Contorno exterior: 1, Contorno de material: 2" in status, \
            status

    def test_the_drawdown_sweeps_refusal(self):
        from PySide6.QtWidgets import QMessageBox
        from ogr_gui.core_messages import note_text
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings
        w = _window()
        gw = w.project.settings.groundwater
        kept = gw.rapid_drawdown
        shown = []
        try:
            gw.rapid_drawdown = True
            why = check_drawdown_settings(w.project)
            assert why, "the demo should be refused"
            with _swapped(QMessageBox, "warning", staticmethod(
                    lambda _p, _t, text, *a, **k: shown.append(text))), \
                    _language("es"):
                w._drawdown_sweep()
                spanish = note_text(why)
        finally:
            gw.rapid_drawdown = kept
        assert shown == [spanish] and spanish != str(why), (shown, str(why))

    def test_a_new_projects_title_and_the_window_menu(self):
        # the file's one window: a new project, then the demo again for the
        # tests after this one
        w = _window()
        with _language("es"):
            w.act_new()
            title = w.windowTitle()
            session = w.session_label()
            name = w.project.name
            w.project.is_dirty = False
            w.act_load_demo()
        w.project.is_dirty = False
        assert title.endswith(" — Sin título"), title
        assert "Sin título" in session and "Untitled" not in session
        assert name == "Untitled"                    # the data is the same

    def test_the_cleanup_report(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.cleanup import inspect_boundaries
        from ogr_core.geometry.expand_shrink import REMOVED_ARC_NAME
        from ogr_gui.main_window import MainWindow
        from test_spanish_texts_v1432 import _line
        boundaries = [
            _line(BoundaryType.MATERIAL),
            _line(BoundaryType.MATERIAL, name="Arcilla", y=8.0),
            _line(BoundaryType.MATERIAL, name=REMOVED_ARC_NAME, y=9.0),
            Boundary(btype=BoundaryType.BLOCK_SEARCH_OBJECT,
                     polyline=Polyline(vertices=[Vertex(20.0, 10.0)],
                                       closed=False))]
        rep = inspect_boundaries(boundaries)
        with _language("es"):
            lines = MainWindow._geometry_cleanup_lines(rep, boundaries)
        assert lines[4:] == [
            "  [0] Contorno de material: 2 vértices — sin problemas",
            "  [1] Contorno de material «Arcilla»: 2 vértices — sin problemas",
            "  [2] Contorno de material «Terreno original (de Expandir / "
            "contraer)»: 2 vértices — sin problemas",
            "  [3] Objeto de búsqueda por bloques: 1 vértice — sin problemas",
        ], lines
        with _language("en"):
            lines = MainWindow._geometry_cleanup_lines(rep, boundaries)
        assert lines[4] == "  [0] Material Boundary: 2 vertices — no problems"


@_requires_qt
class TestTheDialogsSayItInSpanish:
    def test_the_boundary_conditions_summary(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            BoundaryConditionsDialog)
        QApplication.instance() or QApplication([])
        mesh = generate_mesh_for_project(build_demo_project(),
                                         target_elements=40)
        bcs = SeepageBoundaryConditions()
        for n in range(4):
            bcs.add_node(n, BCType.NODAL_FLOW, 0.0)
        bcs.add_node(4, BCType.UNKNOWN, 0.0)
        seen = {}
        for language in ("es", "en"):
            with _language(language):
                d = BoundaryConditionsDialog(mesh, bcs)
                _KEPT.append(d)
                seen[language] = d.lbl_summary.text()
        with _language("es"):
            d = BoundaryConditionsDialog(mesh, SeepageBoundaryConditions())
            _KEPT.append(d)
            seen["none"] = d.lbl_summary.text()
        assert seen["es"] == ("Caudal nodal: 4  |  Desconocida (P=0 o Q=0): "
                              "1"), seen
        assert seen["en"] == "Nodal Flow Rate: 4  |  Unknown (P=0 or Q=0): 1"
        assert seen["none"] == "sin condiciones"

    def test_the_property_tables(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support import SupportInstance
        from ogr_core.support.support import support_registry
        from ogr_gui.dialogs.properties_table_dialog import (
            PropertiesTableDialog)
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        p.materials[0].hydraulic = HydraulicProperties(
            ks=1e-6, model=PermeabilityModel.VAN_GENUCHTEN)
        pile = support_registry()["pile_micropile"]()
        pile._display_name = "Pilote norte"
        p.support_types = [pile]
        p.supports = [SupportInstance(type_id=pile.TYPE_ID,
                                      head=Vertex(30.0, 18.0),
                                      tail=Vertex(24.0, 12.0),
                                      type_ref=getattr(pile, "id", None))]

        def cells(d):
            t = d.table
            return ([t.horizontalHeaderItem(c).text()
                     for c in range(t.columnCount())],
                    [t.item(r, c).text() for r in range(t.rowCount())
                     for c in range(t.columnCount()) if t.item(r, c)])
        with _language("es"):
            mats = cells(PropertiesTableDialog(p, "materials"))
            sups = cells(PropertiesTableDialog(p, "supports"))
            hyd = cells(PropertiesTableDialog(p, "hydraulic"))
        assert "ángulo de rozamiento" in mats[0], mats[0]
        assert "Nivel freático" in mats[1] and "water_table" not in mats[1]
        assert "Cortante" in sups[1] and "shear" not in sups[1], sups
        assert "van Genuchten" in hyd[1] and "van_genuchten" not in hyd[1]
        with _language("en"):
            mats = cells(PropertiesTableDialog(p, "materials"))
        assert "friction angle" in mats[0]                   # control

    def test_define_support_names_a_default_set(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support import EndAnchored
        from ogr_core.support.support import support_registry
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        a, b, c = (EndAnchored(), EndAnchored(),
                   support_registry()["grouted_tieback_friction"]())
        a._display_name, b._display_name = "End Anchored", "End Anchored (2)"
        c._display_name = "Norte"
        p.support_types = [a, b, c]
        with _language("es"):
            d = DefineSupportDialog(p)
            _KEPT.append(d)
            rows = [d.list_widget.item(i).text()
                    for i in range(d.list_widget.count())]
            d.list_widget.setCurrentRow(2)
            from PySide6.QtWidgets import QDoubleSpinBox
            suffixes = {s.suffix() for s in d.findChildren(QDoubleSpinBox)}
        assert rows == ["Anclado en el extremo",
                        "Anclado en el extremo (2)",
                        "Norte  [Anclaje inyectado con rozamiento]"], rows
        assert " °" in suffixes and " deg" not in suffixes, suffixes
        assert a._display_name == "End Anchored"      # the data is the same

    def test_the_other_places_that_name_a_support(self):
        """Sites the review of 0.1.433 found with the rules this version has,
        put in by the owner's decision: Modify and Move Support
        (``MainWindow._support_label``) and the force diagram's selector read
        a default name in English («1: End Anchored», «End Anchored  [Anclado
        en el extremo]»), and the data tip a choice by its value («modo de
        rotura: shear»)."""
        from types import SimpleNamespace as NS
        from ogr_core.geometry import Vertex
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support import SupportInstance
        from ogr_core.support.support import support_registry
        from ogr_gui.data_tips import support_tip
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        pile = support_registry()["pile_micropile"]()
        pile._display_name = "Pile / Micropile"          # as an agent names it
        p.support_types = [pile]
        sup = SupportInstance(head=Vertex(30.0, 18.0), tail=Vertex(24.0, 12.0),
                              type_id=pile.TYPE_ID, name="Pile / Micropile",
                              type_ref=getattr(pile, "id", None))
        p.supports = [sup]
        host = NS(project=p, _type_label=MainWindow._type_label)
        with _language("es"):
            listed = MainWindow._support_label(host, sup)
            d = SupportForceDiagramWindow(p)
            _KEPT.append(d)
            picked = [d.cbo.itemText(i) for i in range(d.cbo.count())]
            tip = support_tip(sup, project=p)
        assert listed == "Pilote / micropilote", listed
        assert picked == ["Pilote / micropilote"], picked
        assert "Cortante" in tip and "shear" not in tip, tip
        with _language("en"):                                  # control
            assert MainWindow._support_label(host, sup) == "Pile / Micropile"
            assert "Shear" in support_tip(sup, project=p)

    def test_a_default_name_is_shown_by_the_current_class(self):
        """A set keeps its name when its class changes (the type combo,
        ``support_type_set`` without a name): a default name is shown by the
        class the set HAS, as a boundary's by its current type. And «User
        Defined» is masculine wherever it names the support class. Both
        found by the review of 0.1.433."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support.support import support_registry
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        from ogr_gui.labels import support_name, support_type_label
        from types import SimpleNamespace as NS
        QApplication.instance() or QApplication([])
        reg = support_registry()
        moved = reg["grouted_tieback"]()
        moved._display_name = "End Anchored (2)"         # born End Anchored
        ud = reg["user_defined"]()
        ud._display_name = "User Defined"
        p = build_demo_project()
        p.support_types = [moved, ud]
        with _language("es"):
            assert support_type_label(moved) == "Anclaje inyectado (2)"
            assert support_name(NS(name="End Anchored (2)"), moved) == \
                "Anclaje inyectado (2)"
            d = DefineSupportDialog(p)
            _KEPT.append(d)
            rows = [d.list_widget.item(i).text()
                    for i in range(d.list_widget.count())]
            combo = [d.cbo_type.itemText(i) for i in range(d.cbo_type.count())]
        assert rows == ["Anclaje inyectado (2)", "Definido por el usuario"], \
            rows
        assert "Definido por el usuario" in combo and \
            "Definida por el usuario" not in combo, combo
        with _language("en"):                                  # control
            assert support_type_label(moved) == "Grouted Tieback (2)"

    def test_the_random_variables_plot(self):
        from PySide6.QtWidgets import QDialog
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics import available_variables
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog)
        QApplication.instance() or QApplication([])
        from ogr_core.statistics.distributions import DistributionType
        p = build_demo_project()
        rv = available_variables(p)[0]
        dist = rv.distribution
        dist.dist_type = DistributionType.NORMAL
        dist.std_dev = max(abs(dist.mean) * 0.1, 0.1)
        dist.rel_min, dist.rel_max = 2.0 * dist.std_dev, 2.0 * dist.std_dev
        assert dist.is_random, dist          # or _plot opens a modal box
        p.random_variables = [rv]
        seen = []
        with _language("es"):
            d = RandomVariablesDialog(p)
            _KEPT.append(d)
            d._current_key = rv.key
            d.defined[rv.key] = rv
            with _swapped(QDialog, "exec",
                          lambda dlg: seen.extend(_texts_of_figure(dlg))):
                d._plot()
        assert {"media", "Valor", "Densidad de probabilidad"} <= set(seen), \
            seen

    def test_the_transient_stages(self):
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog, stage_label)
        from ogr_gui.interpret_groundwater_window import stage_entry
        QApplication.instance() or QApplication([])
        bcs = SeepageBoundaryConditions()
        bcs.add_node(0, BCType.TOTAL_HEAD, 3.0)
        gw = GroundwaterSettings()
        gw.transient_stages = [
            {"time": 10.0, "calculate_sf": False, "label": "Etapa 1 [BC]",
             "bcs": bcs.to_dict()},
            {"time": 20.0, "calculate_sf": True, "label": "Etapa 2"}]
        with _language("es"):
            d = TransientStagesDialog(gw, current_bcs=bcs)
            _KEPT.append(d)
            labels = [d.table.item(r, 2).text() for r in range(2)]
            marks = [d.table.item(r, 3).text() for r in range(2)]
            d.table.setCurrentCell(1, 0)
            d._capture()
            marks_after = [d.table.item(r, 3).text() for r in range(2)]
            stages = d.stages()
            entry = stage_entry(0, {"time": 86400, "label": "Etapa 1 [BC]",
                                    "calculate_sf": True})
        assert labels == ["Etapa 1", "Etapa 2"], labels
        assert marks == ["capturadas", ""] and \
            marks_after == ["capturadas", "capturadas"], (marks, marks_after)
        assert [s["label"] for s in stages] == ["Etapa 1", "Etapa 2"]
        assert entry == "1: t = 86400 Etapa 1  [CC]  [FS]", entry
        assert stage_label("Etapa [BC]", own_bcs=False) == "Etapa [BC]"
        # as the dialog: on a stage without its conditions it is not the
        # program's flag, and the selector keeps it too
        assert stage_entry(0, {"time": 1, "label": "Etapa [BC]",
                               "own_bcs": False}) == "1: t = 1 Etapa [BC]"
        with _language("en"):
            assert stage_entry(1, {"time": 5, "own_bcs": True}) == \
                "2: t = 5  [BC]"

    def test_the_solvers_flag_is_the_stages_own(self):
        """The flag through the project's door, the one the window and the
        agent use: it fills a stage without conditions of its own with the
        current ones, so «has some» is not «has its own». The review of
        0.1.433 found every stage marked."""
        import test_seepage_run_notes_v1352 as srn
        from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
        from ogr_gui.interpret_groundwater_window import stage_entry
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = srn._seepage_project(transient=True)
        mesh = p.fem_mesh
        p.settings.groundwater.transient_initial_bcs = p.seepage_bcs.to_dict()
        low = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                low.add_node(nid, BCType.TOTAL_HEAD, 4.0)
            elif abs(nd.x - srn._W) < 1e-9:
                low.add_node(nid, BCType.TOTAL_HEAD, 3.0)
        p.settings.groundwater.transient_stages = [
            {"time": 3600.0, "label": "sin"},
            {"time": 7200.0, "label": "con", "bcs": low.to_dict()}]
        p.settings.groundwater.transient_time_steps = 1
        solve_project_groundwater(p)
        notes = [r.notes for r in p.transient_results]
        assert [n.get("own_bcs") for n in notes] == [False, True], notes
        with _language("es"):
            entries = [stage_entry(i, n) for i, n in enumerate(notes)]
        assert entries == ["1: t = 3600 sin", "2: t = 7200 con  [CC]"], \
            entries


@_requires_qt
class TestInterpretSaysItInSpanish:
    _built: list = []

    def _interpret(self):
        """Interpret on the reference slope, built in Spanish once for the
        class (the search and the window are the dear part); the helper
        leaves the language set, so it is put back here."""
        from test_gui_spanish_v1318 import _interpret_window
        if not self._built:
            with _language("es"):
                self._built.append(_interpret_window("es"))
        return self._built[0]

    def test_export_raw_data_names_the_method(self):
        from PySide6.QtWidgets import QDialog, QLabel
        _p, iw = self._interpret()
        seen = []
        with _language("es"), _swapped(QDialog, "exec", lambda dlg: seen.extend(
                lab.text() for lab in dlg.findChildren(QLabel))):
            iw._export_raw_data()
        assert any("para el método Bishop simplificado" in t
                   for t in seen), seen
        assert not any("bishop_simplified" in t for t in seen), seen

    def test_the_factor_along_the_slope_is_the_engines_series(self):
        """The identity: the chart plots exactly the series
        ``interpretation.sf_along_slope`` computes, and its minimum is the
        lowest factor of the valid surfaces, the critical one's here."""
        from PySide6.QtWidgets import QDialog
        _p, iw = self._interpret()
        with _language("es"), _swapped(QDialog, "exec",
                                       lambda dlg: QDialog.Accepted):
            dlg = iw._graph_sf_along_slope()
        _KEPT.append(dlg)
        xs, ys = iw.sf_along_slope_series(True, True, 50)
        line = dlg.ax().get_lines()[0]
        assert list(line.get_xdata()) == list(xs)
        assert list(line.get_ydata()) == list(ys)
        valid = [r.fos for r in iw.search_result.valid()]
        assert min(ys) == min(valid) == iw.search_result.critical.fos
        texts = _texts_of_figure(dlg)
        assert "Coordenada X" in texts and "Factor de seguridad" in texts

    def test_the_tornado_is_the_rankings(self):
        """The identity: each bar is ITS variable's ``fos_range``, with the
        sign of ``is_increasing`` -- the ranking's numbers -- read bar by bar
        against its tick label. Two of the variables are shown alike (two
        loads of one magnitude): each keeps its bar. The two of the model
        are named as Define Random Variables names them (``variable_label``),
        not by their stored labels. Review of 0.1.433."""
        from ogr_core.statistics import available_variables
        from ogr_slip2d.sensitivity import (SensitivityResult,
                                            VariableSensitivity)
        p, iw = self._interpret()
        strength = [v for v in available_variables(p)
                    if v.param in ("cohesion", "friction_angle")]
        coh = next(v for v in strength if v.param == "cohesion")
        phi = next(v for v in strength if v.param == "friction_angle"
                   and v.label.split(" — ")[0] == coh.label.split(" — ")[0])
        mat = coh.label.split(" — ")[0]
        VS = VariableSensitivity
        sens = SensitivityResult(by_method={"bishop_simplified": {
            coh.key: VS(key=coh.key, label=coh.label, values=[1.0, 2.0, 3.0],
                        fos=[1.1, 1.2, 1.4]),
            phi.key: VS(key=phi.key, label=phi.label, values=[20.0, 30.0],
                        fos=[1.5, 1.0]),
            "x1": VS(key="x1", label="Carga", values=[1.0, 2.0],
                     fos=[1.0, 1.05]),
            "x2": VS(key="x2", label="Carga", values=[1.0, 2.0],
                     fos=[1.0, 0.8])}})
        ranking = {k: s for k, _l, s in sens.ranking()}
        kept = p.random_variables
        p.random_variables = [coh, phi]
        try:
            with _language("es"), _swapped(iw, "_stat_results",
                                           lambda: (None, sens)):
                iw._sensitivity_tornado()
        finally:
            p.random_variables = kept
        dlg = iw._chart_windows[-1]
        ax = dlg.ax()
        bars = sorted(ax.patches, key=lambda b: b.get_y())
        ticks = [t.get_text() for t in ax.get_yticklabels()]
        got = sorted(zip(ticks, [round(b.get_width(), 12) for b in bars]))
        want = sorted([(mat + " — cohesión", round(ranking[coh.key], 12)),
                       (mat + " — ángulo de rozamiento",
                        round(-ranking[phi.key], 12)),
                       ("Carga", round(ranking["x1"], 12)),
                       ("Carga", round(-ranking["x2"], 12))])
        assert got == want, (got, want)
        texts = _texts_of_figure(dlg)
        assert "Sensibilidad — tornado" in texts, texts

    def test_the_result_table_and_the_values_fallback(self):
        """Two more the review found, put in by the owner's decision: the
        Result Table's «Tipo» column read the serialised type («circle»), and
        the fallback of Show Values Along Surface began with an English
        heading out of tr()."""
        from PySide6.QtWidgets import QDialog, QTableWidget
        import ogr_gui.dialogs.chart_dialogs as CD
        _p, iw = self._interpret()
        cells, said = [], []

        def read(dlg):
            for t in dlg.findChildren(QTableWidget):
                cells.extend(t.item(r, 2).text()
                             for r in range(min(t.rowCount(), 5)))
            return 0

        def broken(*a, **k):
            raise RuntimeError("the chart cannot be drawn")
        with _language("es"), _swapped(QDialog, "exec", read):
            iw._add_result_table()
        with _language("es"), _swapped(CD, "MultiLineDialog", broken), \
                _swapped(iw, "_info", lambda m, *a, **k: said.append(m)):
            iw._show_values_along()
        assert cells and set(cells) == {"círculo"}, cells
        assert said and said[0].startswith(
            "<b>Valores a lo largo de la superficie crítica</b>"), said[:1]

    def test_the_tornado_needs_a_sensitivity_run(self):
        """From Interpret's Statistics menu (rule 3), and grey with its
        reason after a probabilistic run alone: it was enabled and answered
        with a message box (review of 0.1.433)."""
        from PySide6.QtWidgets import QMainWindow
        from ogr_gui.interpret_window import InterpretWindow
        p, iw = self._interpret()
        host = QMainWindow()
        host._prob_result, host._sens_result = object(), None
        _KEPT.append(host)
        # read inside the block: leaving it rebuilds the window's menus
        with _language("es"):
            w = InterpretWindow(p, iw.results_by_method, host)
            _KEPT.append(w)
            by_text = {}
            for act in w.menuBar().actions():       # as test_interpret_i3
                if act.menu() is not None and act.text() == "Estadística":
                    by_text = {a.text(): (a.isEnabled(), a.statusTip())
                               for a in act.menu().actions()}
            assert by_text, [a.text() for a in w.menuBar().actions()]
        assert by_text.get("Tornado de sensibilidad...") == (
            False, "Requiere un análisis de sensibilidad: ejecuta "
            "Estadística → Calcular estadística en el modelador."), by_text
        assert by_text["Gráfico de sensibilidad..."][0]


class TestTheReportSaysItInSpanish:
    def _said(self, translate):
        import os
        import tempfile
        import reportlab.platypus as platypus
        import ogr_core.report.report_generator as RG
        from ogr_core.project.demo import build_demo_project
        from ogr_core.project.settings import DEFAULT_SUMMARY_TITLE
        p = build_demo_project()
        p.settings.search.surface_type = "non_circular"
        p.settings.search.search_method = "particle_swarm"
        p.settings.summary.title = DEFAULT_SUMMARY_TITLE
        said = []
        real_par, real_tab = platypus.Paragraph, platypus.Table

        class Par(real_par):
            def __init__(self, text, *a, **k):
                said.append(str(text))
                super().__init__(text, *a, **k)

        class Tab(real_tab):
            def __init__(self, data, *a, **k):
                said.extend(c for row in data for c in row
                            if isinstance(c, str))
                super().__init__(data, *a, **k)
        RG.Paragraph, RG.Table = Par, Tab
        try:
            with tempfile.TemporaryDirectory() as tmp:
                RG.generate_report(p, {}, os.path.join(tmp, "r.pdf"),
                                   translate=translate)
        finally:
            RG.Paragraph, RG.Table = real_par, real_tab
        return " | ".join(said)

    def test_the_windows_report_titles_a_default_name(self):
        """Through ``act_generate_report``, as the user makes it: the window
        passes ``title=summary.title``, and a summary is born with the
        project's name, so the demo's report was titled «Demo slope» in
        Spanish (review of 0.1.433). Its dialogs and the file name are
        swapped, and no method is drawn."""
        import os
        import tempfile
        import reportlab.platypus as platypus
        import ogr_core.report.report_generator as RG
        import ogr_gui.dialogs.report_dialog as RD
        import ogr_gui.main_window as MW
        w = _window()
        assert w.project.settings.summary.title == "Demo slope"

        class _Dialog:
            options = {"figures": False, "framing": "model",
                       "annotations": False}

            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

        class _Some(dict):               # a run, with no method to draw
            def __bool__(self):
                return True
        said = []
        real_par = platypus.Paragraph

        class Par(real_par):
            def __init__(self, text, *a, **k):
                said.append(str(text))
                super().__init__(text, *a, **k)
        from PySide6.QtWidgets import QMessageBox
        boxes = []
        kept = getattr(w, "last_search_results", None)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "r.pdf")
            w.last_search_results = _Some()
            try:
                # the closing message boxes are modal: replaced, put back
                with _language("es"), \
                        _swapped(RD, "ReportDialog", _Dialog), \
                        _swapped(MW, "get_save_file_name",
                                 lambda *a, **k: (out, "")), \
                        _swapped(RG, "Paragraph", Par), \
                        _swapped(QMessageBox, "information", staticmethod(
                            lambda *a, **k: boxes.append(a[2]))), \
                        _swapped(QMessageBox, "critical", staticmethod(
                            lambda *a, **k: boxes.append(a[2]))):
                    w.act_generate_report()
            finally:
                w.last_search_results = kept
            assert os.path.exists(out), boxes
        text = " | ".join(said)
        assert "Talud de ejemplo" in text and "Demo slope" not in text, \
            text[:300]

    def test_in_spanish_and_without_a_translator(self):
        from ogr_gui.core_messages import note_text
        with _language("es"):
            es = self._said(note_text)
        assert "No circular" in es and "Non_Circular" not in es, es[:400]
        assert "Búsqueda por enjambre de partículas" in es
        assert "Proyecto sin título" in es and "Untitled Project" not in es
        en = self._said(None)
        assert "Non-Circular" in en and "Particle Swarm Search" in en
        assert "Untitled Project" in en


class TestTheCodedNotesNameTheirIdentifiers:
    """F1: every field of a coded note that holds an identifier declares
    its kind, measured on the samples the catalogue tests keep (the args the
    engine passes), and the window names each new kind."""

    def test_no_identifier_field_without_its_kind(self):
        import ast
        import enum
        import importlib
        import re
        from ogr_gui.core_messages import _catalogue
        ids = set()
        for mod in ("ogr_core.project.settings",
                    "ogr_core.materials.material", "ogr_core.loads.loads",
                    "ogr_core.support", "ogr_core.geometry.focus",
                    "ogr_core.geometry.tension_crack", "ogr_core.hydraulic",
                    "ogr_core.fem.seepage_data"):
            for v in vars(importlib.import_module(mod)).values():
                if isinstance(v, type) and issubclass(v, enum.Enum):
                    ids |= {m.value for m in v if isinstance(m.value, str)
                            and len(m.value) > 2}
        cat = _catalogue()
        here = Path(__file__).parent
        found = []
        for name in ("test_model_notes_v1347", "test_method_notes_v1348",
                     "test_search_notes_v1349", "test_setting_refusals_v1350",
                     "test_seepage_run_notes_v1352", "test_stat_notes_v1353",
                     "test_dxf_export_census_v1354"):
            tree = ast.parse((here / (name + ".py")).read_text(
                encoding="utf-8"))
            for node in tree.body:
                if not (isinstance(node, ast.Assign) and getattr(
                        node.targets[0], "id", "").startswith("_V13")):
                    continue
                for row in ast.literal_eval(node.value):
                    code, args = ((row[0], row[1]) if isinstance(row, tuple)
                                  else (row.get("code"), row.get("args")))
                    spec = cat.get(code)
                    if spec is None or not isinstance(args, dict):
                        continue
                    declared = {f for f, _k in spec.kinds or ()}
                    for field, value in args.items():
                        if field in declared or not isinstance(value, str):
                            continue
                        parts = re.split(r"[,;] ?| ", value)
                        if value in ids or any(p in ids and "_" in p
                                               for p in parts):
                            found.append((code, field, value))
        assert not found, found

    def test_the_window_names_each_new_kind(self):
        from ogr_core.messages import coded
        from ogr_gui.core_messages import _catalogue, note_text
        cat = _catalogue()
        with _language("es"):
            mismatch = note_text(coded(cat, "model.surface_type_mismatch",
                                       surface_type="non_circular",
                                       search_method="grid"))
            unknown = note_text(coded(cat, "setting.drawdown_unknown",
                                      method="x",
                                      available="b_bar, corps_2"))
            stype = note_text(coded(cat, "stat.type", stype="weak_layer"))
        assert "«No circular»" in mismatch and \
            "«Búsqueda por rejilla»" in mismatch, mismatch
        # the Spanish of both: «B-bar» alone is also the English label
        assert "Tensiones efectivas con B-barra" in unknown and \
            "Cuerpo de Ingenieros 2 etapas (1970)" in unknown, unknown
        assert "b_bar" not in unknown and "corps_2" not in unknown, unknown
        assert "superficie de capa débil" in stype, stype

    def test_the_case_texts_and_the_lists_read_right(self):
        """Two the review found: the case of the weak-layer search wrote
        «una superficie superficie de capa débil», and the list of drawdown
        procedures, joined by commas, read six for four (one name has
        two). The engine's English is unchanged."""
        from ogr_core.messages import coded
        from ogr_gui.core_messages import _catalogue, note_text
        cat = _catalogue()
        layers = coded(cat, "stat.case_text_layers", stype="weak_layer",
                       spans="x de 2.00 a 5.00")
        none = coded(cat, "stat.case_text_none", stype="circle")
        avail = coded(cat, "setting.drawdown_unknown", method="x",
                      available="b_bar, duncan_wright, corps_2")
        with _language("es"):
            got = [note_text(layers), note_text(none), note_text(avail)]
        assert got[0] == ("una superficie de capa débil por capas débiles "
                          "en x de 2.00 a 5.00"), got[0]
        assert got[1] == "una superficie circular sin ninguna capa débil", \
            got[1]
        assert ("Tensiones efectivas con B-barra; Duncan, Wright, Wong 3 "
                "etapas (1990); Cuerpo de Ingenieros") in got[2], got[2]
        assert str(none) == "a circle on no weak layer"      # the agent's
        assert "b_bar, duncan_wright, corps_2" in str(avail)


class TestTheNewCensusRulesCheckThemselves:
    """The rules this version adds to test_gui_spanish_v1318 and to the
    runtime census of test_labels_spanish_v1321, on sources of their own."""

    def test_or_concatenation_fields_items_figures(self):
        import test_gui_spanish_v1318 as census
        cases = {
            'w.setText("  |  ".join(p) or "no conditions")\n':
                [(1, "no conditions")],
            'self.s.showMessage(tr("Ready") + " — File → Open", 6)\n':
                [(1, " — File → Open")],
            'self.s.showMessage(tr("Filter: {0}").format(x or "nothing"))\n':
                [(1, "nothing")],
            't.setItem(0, 2, QTableWidgetItem((a + " [BC]").strip()))\n':
                [(1, " [BC]")],
            'ax.set_xlabel("Value")\nax.text(0, 0, "Empty")\n'
            'ax.axvline(1, label="mean")\n':
                [(1, "Value"), (2, "Empty"), (3, "mean")],
            'd = tr("Δ factor") if f else "ΔFoS"\n': [(1, "ΔFoS")],
            # the three rules the review found without a case of their own:
            # the fields of ``tr(...) % (...)``, a tree item's texts and a
            # legend's list
            'QMessageBox.warning(p, t, tr("A %s") % (x or "none"))\n':
                [(1, "none")],
            'it = QTreeWidgetItem(["Name"])\n': [(1, "Name")],
            'ax.legend(["mean", "median"])\n': [(1, "mean"), (1, "median")],
        }
        for src, want in cases.items():
            assert census.loose(src) == want, (src, census.loose(src))
        # controls: through tr(), a colour, and data
        for src in ('w.setText("  |  ".join(p) or tr("no conditions"))\n',
                    'w.setText(c or "#4b0082")\n',
                    'ax.set_xlabel(tr("Value"))\n',
                    'c.addItem(tr("x"), "water_table")\n'):
            assert census.loose(src) == [], (src, census.loose(src))

    def test_the_runtime_census_vocabulary_and_data_names(self):
        import test_labels_spanish_v1321 as runtime
        from ogr_core.geometry import BoundaryType
        from ogr_core.project.demo import build_demo_project
        from test_spanish_texts_v1432 import _line
        spanish = set(runtime._spanish().values())
        reads = runtime._reads_english
        # an English word no Spanish text uses, accents around it or not
        assert reads("Contorno añadido: Material Boundary", spanish, [], ())
        assert reads("nodal_flow: 21", spanish, [], {"nodal_flow"})
        assert not reads("Contorno exterior", spanish, [], ())
        p = build_demo_project()
        p.boundaries.append(_line(BoundaryType.MATERIAL, name="Arcilla"))
        names = runtime._data_names(p)
        assert "Arcilla" in names
        assert "Demo slope" not in names and "Water Table" not in names
