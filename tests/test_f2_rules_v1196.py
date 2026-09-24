# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.196 (spec 008, F2) — what moved out of the interface into the core,
and the interface defects that giving an agent the same actions exposed.

Invariants protected:

* **Moved, not copied.** The interface asks the core for: the demo slope
  (``ogr_core.project.demo``), the properties import
  (``ogr_core.project.properties_import``), the support references after
  editing the sets (``reconcile_support_refs``), the seismic records
  (``rules.set_seismic_records``), the geometry inspection
  (``inspect_boundaries``), the simplification (``simplify_boundary``) and
  both Expand/Shrink modes (``apply_expand_shrink``,
  ``apply_external_offset``). For the two dialogs, replacing the core
  function changes what the dialog does — the test that tells a delegation
  from a second copy; the window's handlers are driven for real and must
  give the core's result, including the fixes only the core has.
* **The defects stay fixed**, each driven through the real handler with
  only its modal dialog replaced (a test must never open one):

  - a NEW load kept ``creates_excess_pore_pressure`` off whatever the
    dialog said (only Modify wrote it);
  - *Simplify Boundary* raised on every use (a list of tuples where a
    ``Polyline`` was expected);
  - the Expand/Shrink draw mode raised at the moment of committing
    (``MacroCommand(commands=...)``; the field is ``children``) and had
    never changed a model;
  - *Geometry Cleanup* never reported crossings (a swallowed TypeError),
    removed vertices with no undo, and printed 3 as the number of
    boundaries left;
  - *Ungroup Support Pattern* never found a pattern: nothing set
    ``pattern_id``;
  - the interface's demo drew a water table and assigned it to nothing;
  - *Import Properties* kept the source's material ids and its water
    references (the imported material was silently dry).
* The support tokens the core checks are the ones the editor offers.
* A result is stale only when something the ANALYSIS reads changed:
  ``model_hash`` leaves the annotations out, ``document_hash`` does not.
"""
from __future__ import annotations

import contextlib
import copy
import json
import shutil
import tempfile
from pathlib import Path

_WINDOWS: list = []
_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}


def _raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} was not raised")


def _project(external=None, **spec):
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Rules")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": external or [[20, 20], [70, 20], [70, 35],
                                     [50, 35], [30, 25], [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": _SOIL}], **spec})
        return ws.get(pid).project
    finally:
        ws.shutdown()


def _dump(project) -> str:
    return json.dumps(project.to_dict(), sort_keys=True, default=str)


def _area(polyline):
    pts = [(v.x, v.y) for v in polyline.vertices]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                   in zip(pts, pts[1:] + pts[:1]))) / 2


@contextlib.contextmanager
def _swap(owner, name, value):
    """Replace ``owner.name`` for the block and put back EXACTLY what was
    there — the raw class attribute, or nothing when it was inherited. The
    runner does not call ``teardown_method`` (rule 5)."""
    raw = owner.__dict__.get(name, _MISSING) if isinstance(owner, type) \
        else getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


_MISSING = object()


def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


def _window(project):
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.PROMPT_ASSIGN_ON_DRAW = False
    w._attach_project(project)
    _WINDOWS.append(w)
    return w


# ======================================================================
# Core functions
# ======================================================================
class TestSupportTokens:
    def test_the_core_checks_the_tokens_the_editor_offers(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_core.support.support import PARAMETER_CHOICES
        from ogr_gui.dialogs.define_support_dialog import _CHOICES
        offered = {k: tuple(tok for _label, tok in v)
                   for k, v in _CHOICES.items()}
        assert offered == PARAMETER_CHOICES


class TestPatternIdentity:
    def test_a_pattern_is_saved_and_an_old_file_is_unchanged(self):
        from ogr_core.support.support import SupportInstance, SupportPattern
        pat = SupportPattern(type_id="soil_nail", type_ref="t", length=6.0,
                             spacing=3.0)
        made = pat.generate_along_segment((30, 25), (50, 35))
        assert len({s.pattern_id for s in made}) == 1
        assert made[0].pattern_id
        back = SupportInstance.from_dict(made[0].to_dict())
        assert back.pattern_id == made[0].pattern_id
        loose = SupportInstance.from_dict(made[0].to_dict())
        loose.pattern_id = None
        assert "pattern_id" not in loose.to_dict()   # old files byte-equal


class TestReconcileAndRecords:
    def test_supports_follow_their_sets(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import SupportInstance
        from ogr_core.support.support import SoilNail, reconcile_support_refs
        p = _project()
        nail = SoilNail()
        nail.id = "set-1"
        p.support_types = [nail]
        p.supports = [
            SupportInstance(type_id="end_anchored", type_ref="set-1",
                            head=Vertex(40, 30), tail=Vertex(48, 26)),
            SupportInstance(type_id="end_anchored", type_ref="gone",
                            head=Vertex(42, 31), tail=Vertex(50, 27)),
            SupportInstance(type_id="end_anchored",
                            head=Vertex(44, 32), tail=Vertex(52, 28))]
        rep = reconcile_support_refs(p)
        assert rep == {"cleared": 1, "retyped": 1}
        assert p.supports[0].type_id == "soil_nail"
        assert p.supports[1].type_ref is None
        assert p.supports[2].type_id == "end_anchored"

    def test_a_deleted_record_leaves_no_selection(self):
        from ogr_core.loads.seismic_record import SeismicRecord
        from ogr_core.project.rules import set_seismic_records
        p = _project()
        a = SeismicRecord(name="A", dt=0.01, accelerations=[0, 0.1, 0])
        b = SeismicRecord(name="B", dt=0.01, accelerations=[0, 0.2, 0])
        assert set_seismic_records(p, [a, b]) is False
        p.settings.seismic.record_id = b.id
        assert set_seismic_records(p, [a, b]) is False
        assert p.settings.seismic.record_id == b.id
        assert set_seismic_records(p, [a]) is True
        assert p.settings.seismic.record_id == ""


class TestPropertiesImport:
    def _source(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, PorePressureType
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.support.support import SoilNail
        src = _project()
        wt = Boundary(polyline=Polyline(vertices=[Vertex(20, 23),
                                                  Vertex(70, 30)]),
                      btype=BoundaryType.WATER_TABLE)
        src.add_boundary(wt)
        for name in ("Clay", "Sand", "Gravel"):
            src.materials.append(Material(
                name=name, strength=MohrCoulomb(cohesion=1.0,
                                                friction_angle=30.0),
                pore_pressure=PorePressureType.WATER_TABLE,
                water_surface_id=wt.id, anisotropic_surface_id="aniso"))
        nail = SoilNail()
        nail.id = "nail-src"
        nail._display_name = "Nail"
        src.support_types = [nail]
        return src

    def test_nothing_foreign_comes_across(self):
        from ogr_core.project.properties_import import import_properties
        src = self._source()
        dst = _project()
        out = import_properties(dst, src, names=["clay", "NAIL"])
        assert out["materials"] == ["Clay"]
        assert out["support_types"] == ["Nail"]
        m = dst.materials[-1]
        assert m.id not in {x.id for x in src.materials}
        assert m.water_surface_id is None
        assert m.anisotropic_surface_id is None
        assert m.pore_pressure.value == "none"
        assert len(out["notes"]) == 2
        st = dst.support_types[-1]
        assert st.id != "nail-src"
        st.tensile_capacity = 1.0                     # a copy, not a share
        assert src.support_types[0].tensile_capacity != 1.0

    def test_names_are_unique_without_case_and_the_limit_holds(self):
        from ogr_core.project.properties_import import import_properties
        src = self._source()
        dst = _project()
        dst.materials[0].name = "clay"
        dst.settings.max_materials = 3
        out = import_properties(dst, src, support_types=False,
                                names=["clay", "sand", "gravel"])
        assert out["materials"] == ["Clay (2)", "Sand"]
        assert out["skipped"] == ["Gravel"]
        assert len(dst.materials) == 3


class TestInspection:
    def test_it_reports_without_touching(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.cleanup import inspect_boundaries
        p = _project()
        ext = p.external_boundary()
        ext.polyline.vertices.insert(2, copy.copy(ext.polyline.vertices[2]))
        cross = [Boundary(polyline=Polyline(vertices=[Vertex(25, 21),
                                                      Vertex(65, 24)]),
                          btype=BoundaryType.MATERIAL),
                 Boundary(polyline=Polyline(vertices=[Vertex(25, 24),
                                                      Vertex(65, 21)]),
                          btype=BoundaryType.MATERIAL),
                 Boundary(polyline=Polyline(vertices=[
                     Vertex(22, 21), Vertex(28, 23), Vertex(28, 21),
                     Vertex(22, 23)]), btype=BoundaryType.MATERIAL)]
        for b in cross:
            p.add_boundary(b)
        before = _dump(p)
        rep = inspect_boundaries(p.boundaries)
        assert _dump(p) == before
        rows = {r["id"]: r for r in rep["boundaries"]}
        assert rows[ext.id]["duplicate_vertices"] == 1
        assert rows[cross[2].id]["self_intersects"] is True
        assert not rows[cross[0].id]["self_intersects"]
        pairs = {frozenset((c["a"], c["b"])) for c in
                 rep["cross_intersections"]}
        assert frozenset((cross[0].id, cross[1].id)) in pairs

    def test_the_tolerance_follows_the_model_size(self):
        from ogr_core.geometry.cleanup import inspect_boundaries
        small = _project()
        big = _project(external=[[x * 1000, y * 1000] for x, y in
                                 [[20, 20], [70, 20], [70, 35], [50, 35],
                                  [30, 25], [20, 25]]])
        t_small = inspect_boundaries(small.boundaries)["tolerance"]
        t_big = inspect_boundaries(big.boundaries)["tolerance"]
        assert abs(t_big / t_small - 1000) < 1e-9

    def test_simplify_keeps_the_ids_and_refuses_to_collapse(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.cleanup import simplify_boundary
        b = Boundary(polyline=Polyline(vertices=[
            Vertex(0, 0), Vertex(5, 0.01), Vertex(10, 0)]),
            btype=BoundaryType.MATERIAL)
        s = simplify_boundary(b, 0.1)
        assert (s.id, s.polyline.id) == (b.id, b.polyline.id)
        assert len(s.polyline.vertices) == 2
        assert len(b.polyline.vertices) == 3              # a copy
        p = _project()
        _raised(ValueError, lambda: simplify_boundary(
            p.external_boundary(), 1000.0))
        _raised(ValueError, lambda: simplify_boundary(b, 0.0))


class TestHashes:
    def test_annotations_are_the_document_not_the_model(self):
        from ogr_api.snapshot import document_hash, model_hash
        from ogr_core.annotations.annotation import (Annotation,
                                                     AnnotationKind)
        p = _project()
        m0, d0 = model_hash(p), document_hash(p)
        p.annotations.add(Annotation(kind=AnnotationKind.TEXT,
                                     points=[(30.0, 40.0)], text="x",
                                     id="a1"))
        assert model_hash(p) == m0
        assert document_hash(p) != d0
        p.materials[0].unit_weight = 21.0
        assert model_hash(p) != m0


class TestExpandShrinkCore:
    def test_the_removed_arc_can_stay_as_material(self):
        from ogr_core.geometry import BoundaryType, Polyline, Vertex
        from ogr_core.geometry.expand_shrink import (REMOVED_ARC_NAME,
                                                     apply_expand_shrink)
        p = _project()
        before = _area(p.external_boundary().polyline)
        drawn = Polyline(vertices=[Vertex(50, 35), Vertex(60, 37),
                                   Vertex(70, 35)])
        res = apply_expand_shrink(p, drawn, keep_removed_as_material=True)
        assert res.mode == "expand"
        assert abs(_area(p.external_boundary().polyline) - before - 20) \
            < 1e-9
        kept = [b for b in p.boundaries if b.name == REMOVED_ARC_NAME]
        assert len(kept) == 1 and kept[0].btype == BoundaryType.MATERIAL


# ======================================================================
# The interface asks the core
# ======================================================================
class TestTheInterfaceDelegates:
    def test_the_demo_is_the_core_demo(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_core.project.demo import build_demo_project
        w = _window(_project())
        w.project.is_dirty = False
        w.act_load_demo()
        ref = build_demo_project()
        got = w.project
        assert [(b.btype, [(v.x, v.y) for v in b.polyline.vertices])
                for b in got.boundaries] == \
            [(b.btype, [(v.x, v.y) for v in b.polyline.vertices])
             for b in ref.boundaries]
        wt = got.boundaries[1]
        assert got.materials[0].water_surface_id == wt.id
        assert got.materials[0].pore_pressure.value == "water_table"

    def test_new_loads_keep_the_excess_pore_pressure_tick(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_core.loads import LoadDistribution, LoadOrientation
        w = _window(_project())
        w._pending_dist_load = {
            "magnitude_1": 10.0, "magnitude_2": None,
            "orientation": LoadOrientation.VERTICAL, "angle_deg": 0.0,
            "distribution": LoadDistribution.CONSTANT,
            "creates_excess_pore_pressure": True}
        w._on_dist_load_segment_picked(50.0, 35.0, 60.0, 35.0)
        assert w.project.distributed_loads[-1].creates_excess_pore_pressure
        w._pending_line_load = {
            "magnitude": 10.0, "orientation": LoadOrientation.VERTICAL,
            "angle_deg": 0.0, "creates_excess_pore_pressure": True}
        w._on_line_load_point_picked(60.0, 35.0)
        assert w.project.line_loads[-1].creates_excess_pore_pressure

    def test_geometry_cleanup_reports_and_undoes(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_gui.main_window as mw
        p = _project()
        ext = p.external_boundary()
        ext.polyline.vertices.insert(1, copy.copy(ext.polyline.vertices[1]))
        w = _window(p)
        before = _dump(w.project)
        shown = []

        class _Report:
            def __init__(self, text, parent=None):
                shown.append(text)

            def exec(self):
                return 0

        with _swap(mw, "GeometryCleanupDialog", _Report):
            w.act_geometry_cleanup()
        assert "Duplicate vertices removed: 1" in shown[0]
        assert "1 duplicate vertices" in shown[0]
        assert len(w.project.external_boundary().polyline.vertices) == 6
        w.command_stack.undo(w.project)
        assert _dump(w.project) == before

    def test_simplify_boundary_runs(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_gui.main_window as mw
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _project()
        line = Boundary(polyline=Polyline(vertices=[
            Vertex(20, 22), Vertex(45, 23.01), Vertex(70, 24)]),
            btype=BoundaryType.MATERIAL)
        p.add_boundary(line)
        w = _window(p)
        idx = w.project.boundaries.index(line)

        class _Tol:
            def __init__(self, parent=None):
                pass

            def exec(self):
                return 1

            def tolerance(self):
                return 0.1

        w._ask_boundary_index = lambda: idx
        with _swap(mw, "SimplifyBoundaryDialog", _Tol):
            w.act_simplify_boundary()
        assert len(w.project.boundaries[idx].polyline.vertices) == 2
        assert w.project.boundaries[idx].id == line.id

    def test_both_expand_shrink_modes_commit_and_undo(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_gui.main_window as mw
        from PySide6.QtWidgets import QMessageBox
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.expand_shrink import REMOVED_ARC_NAME

        rect = _project(external=[[0, 0], [10, 0], [10, 5], [0, 5]])
        w = _window(rect)
        before = _dump(w.project)
        idx = w.project.boundaries.index(w.project.external_boundary())

        class _Offset:
            def __init__(self, parent=None):
                pass

            def exec(self):
                return 1

            def distance(self):
                return 1.0

        with _swap(mw, "ExpandShrinkDialog", _Offset):
            w._expand_shrink_numeric(idx)
        assert abs(_area(w.project.external_boundary().polyline) - 84) \
            < 1e-9
        w.command_stack.undo(w.project)
        assert _dump(w.project) == before

        class _Yes:
            Yes, No = QMessageBox.Yes, QMessageBox.No

            @staticmethod
            def question(*_a, **_k):
                return QMessageBox.Yes

            @staticmethod
            def warning(*a, **_k):
                raise AssertionError(f"warning shown: {a[2:]}")

            critical = warning

        w2 = _window(_project())
        before = _dump(w2.project)
        area0 = _area(w2.project.external_boundary().polyline)
        w2._expand_shrink_target_idx = w2.project.boundaries.index(
            w2.project.external_boundary())
        drawn = Boundary(polyline=Polyline(vertices=[
            Vertex(50, 35), Vertex(60, 37), Vertex(70, 35)]),
            btype=BoundaryType.MATERIAL)
        with _swap(mw, "QMessageBox", _Yes):
            w2._on_expand_shrink_polyline_drawn(drawn)
        assert abs(_area(w2.project.external_boundary().polyline)
                   - area0 - 20) < 1e-9
        assert [b.name for b in w2.project.boundaries].count(
            REMOVED_ARC_NAME) == 1
        w2.command_stack.undo(w2.project)
        assert _dump(w2.project) == before

    def test_ungroup_finds_the_pattern(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_core.support.support import SupportPattern
        p = _project()
        p.supports.extend(SupportPattern(
            type_id="soil_nail", type_ref=None, length=6.0,
            spacing=3.0).generate_along_segment((30, 25), (50, 35)))
        w = _window(p)
        w._ungroup_pattern()
        assert w.project.supports
        assert not any(s.pattern_id for s in w.project.supports)

    def test_import_properties_is_the_core_import(self):
        if _qt() is None:  # pragma: no cover
            return
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.i18n import tr
        tmp = Path(tempfile.mkdtemp(prefix="ogr_rules_"))
        try:
            src = build_demo_project()
            path = tmp / "demo.ogr"
            src.save(path)
            w = _window(_project())
            with _swap(QFileDialog, "getOpenFileName",
                       staticmethod(lambda *a, **k: (str(path), ""))), \
                    _swap(QInputDialog, "getItem",
                          staticmethod(lambda *a, **k: (tr("Both"), True))):
                w._import_properties()
            m = w.project.materials[-1]
            assert m.name == "Silty clay"
            assert m.id != src.materials[0].id
            assert m.water_surface_id is None     # was silently dry before
            assert m.pore_pressure.value == "none"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_dialogs_ask_the_core(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_core.project.rules as rules
        import ogr_core.support.support as support
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        from ogr_gui.dialogs.seismic_records_dialog import (
            SeismicRecordsDialog)
        p = _project()
        calls = []
        with _swap(support, "reconcile_support_refs",
                   lambda project: calls.append(("support", project))
                   or {"cleared": 0, "retyped": 0}):
            dlg = DefineSupportDialog(p)
            dlg.accept()
        with _swap(rules, "set_seismic_records",
                   lambda project, records: calls.append(
                       ("records", project)) or False):
            dlg = SeismicRecordsDialog(p)
            dlg.apply()
        assert calls == [("support", p), ("records", p)]
