# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.304 (D292) — loads and supports are undo steps.

Second family of D292: the 16 methods of ``MainWindow`` that added,
changed or deleted a load or a support without leaving a step, now through
``_model_step``, with the names of the API where the operation is the same:

==========================================  ======================
Add Distributed / Line Load (last click)    Set load
Seismic Load                                Set seismic load
Seismic Records                             Seismic records
Delete Load, right-click > Delete           Delete loads
right-click > Modify, Modify Load           Set load
Define Support                              Define support types
Add Support (last click), Properties,       Set support
Modify Support
Add Support Pattern (last click)            Add support pattern
Delete Support (click, right-click)         Delete supports
Stretch Support                             Stretch support
right-click > Modify Pattern                Modify support pattern
Move Support                                Move support
Ungroup Support Pattern                     Ungroup support pattern
==========================================  ======================

*Modify Load* asks for the magnitude and then for the far-end magnitude:
cancelling the second question left the first one written. Cancel now
cancels the edit (``STEP_CANCELLED``).

For each site, through the window's method with its dialog or input boxes
replaced: accepting leaves one named step, undo gives back the model
exactly (JSON) and redo the accepted one; cancelling leaves no step. One
test mixes the window's steps with an agent's.

Not here: the Add Support handler that stays connected (D308), which is
its own defect and comes after P8e.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


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


def _answers(*values):
    """A static input box that gives ``values`` in turn."""
    it = iter(values)
    return staticmethod(lambda *a, **k: next(it))


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()           # crest y = 25 for x <= 25, toe y = 15
    w.project.is_dirty = False
    return w


def _clean(w):
    w.command_stack.clear()
    w.project.is_dirty = False


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _accepted(w, name, act):
    before = _json(w.project)
    act()
    after = _json(w.project)
    assert after != before, name
    assert w.command_stack.history() == ([name], []), \
        w.command_stack.history()
    assert w.project.is_dirty, name
    w.act_undo()
    assert _json(w.project) == before, name
    w.act_redo()
    assert _json(w.project) == after, name


def _cancelled(w, act):
    before = _json(w.project)
    act()
    assert _json(w.project) == before
    assert w.command_stack.history() == ([], [])
    assert not w.project.is_dirty


def _a_load(w, magnitude_2=None):
    from ogr_core.geometry import Vertex
    from ogr_core.loads import DistributedLoad
    from ogr_core.loads.loads import LoadOrientation
    w.project.distributed_loads.append(DistributedLoad(
        start=Vertex(2.0, 25.0), end=Vertex(10.0, 25.0), magnitude_1=20.0,
        magnitude_2=magnitude_2, orientation=LoadOrientation.VERTICAL))


def _a_line_load(w):
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad
    from ogr_core.loads.loads import LoadOrientation
    w.project.line_loads.append(LineLoad(
        point=Vertex(5.0, 25.0), magnitude=30.0,
        orientation=LoadOrientation.VERTICAL))


def _two_types(w):
    from ogr_core.support import EndAnchored
    a = EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)
    b = EndAnchored(anchor_capacity=200.0, out_of_plane_spacing=1.5)
    b._display_name = "Strong anchor"
    w.project.support_types = [a, b]


def _a_support(w, pattern_id=None):
    from ogr_core.geometry import Vertex
    from ogr_core.support import SupportInstance
    st = w.project.support_types[0]
    w.project.supports.append(SupportInstance(
        type_id=st.TYPE_ID, type_ref=st.id, head=Vertex(30.0, 20.0),
        tail=Vertex(18.0, 14.0), pattern_id=pattern_id))


# ----------------------------------------------------------------------
class TestLoads:
    def test_add_a_distributed_load(self):
        from ogr_gui.dialogs import load_dialogs
        w = _window()
        try:
            with _swap(load_dialogs.DistributedLoadDialog, "exec",
                       lambda self: 1):
                w.act_add_distributed_load()
            _accepted(w, "Set load",
                      lambda: w._on_dist_load_segment_picked(
                          2.0, 25.0, 10.0, 25.0))
        finally:
            _done(w)

    def test_add_a_line_load(self):
        from ogr_gui.dialogs import load_dialogs
        w = _window()
        try:
            with _swap(load_dialogs.LineLoadDialog, "exec", lambda self: 1):
                w.act_add_line_load()
            _accepted(w, "Set load",
                      lambda: w._on_line_load_point_picked(5.0, 25.0))
        finally:
            _done(w)

    def test_seismic_load(self):
        import ogr_gui.dialogs.seismic_dialog as sd

        class _Fake:
            result = 1

            def __init__(self, seismic, parent=None):
                self.seismic = seismic

            def exec(self):
                return self.result

            def apply(self):
                self.seismic.enabled = True
                self.seismic.kh = 0.12

        class _No(_Fake):
            result = 0

        w = _window()
        try:
            with _swap(sd, "SeismicLoadDialog", _No):
                _cancelled(w, w.act_seismic_load)
            with _swap(sd, "SeismicLoadDialog", _Fake):
                _accepted(w, "Set seismic load", w.act_seismic_load)
        finally:
            _done(w)

    def test_seismic_records(self):
        from ogr_core.loads.seismic_record import SeismicRecord
        import ogr_gui.dialogs.seismic_records_dialog as srd

        class _Fake:
            result = 1

            def __init__(self, project, parent=None):
                self.project = project

            def exec(self):
                return self.result

            def apply(self):
                self.project.seismic_records = list(
                    self.project.seismic_records) + [SeismicRecord(
                        name="Pulse", dt=0.01,
                        accelerations=[0.0, 0.1, -0.2, 0.0])]

        class _No(_Fake):
            result = 0

        w = _window()
        try:
            with _swap(srd, "SeismicRecordsDialog", _No):
                _cancelled(w, w.act_seismic_records)
            with _swap(srd, "SeismicRecordsDialog", _Fake):
                _accepted(w, "Seismic records", w.act_seismic_records)
        finally:
            _done(w)

    def test_delete_load_from_the_list(self):
        from PySide6.QtWidgets import QDialog, QListWidget

        def _all(self):
            self.findChild(QListWidget).selectAll()
            return QDialog.DialogCode.Accepted

        w = _window()
        try:
            _a_load(w)
            _a_line_load(w)
            _clean(w)
            with _swap(QDialog, "exec", lambda self: 0):
                _cancelled(w, w.act_delete_load)
            with _swap(QDialog, "exec", _all):
                _accepted(w, "Delete loads", w.act_delete_load)
        finally:
            _done(w)

    def test_right_click_delete_and_modify(self):
        from ogr_gui.dialogs import load_dialogs
        w = _window()
        try:
            _a_load(w)
            _a_line_load(w)
            _clean(w)
            _accepted(w, "Delete loads",
                      lambda: w._on_load_action("delete", "line", 0))
            _clean(w)
            cls = load_dialogs.DistributedLoadDialog
            with _swap(cls, "exec", lambda self: 0):
                _cancelled(w, lambda: w._on_load_action(
                    "modify", "distributed", 0))
            with _swap(cls, "exec", lambda self: 1), \
                    _swap(cls, "magnitude_1", lambda self: 77.0):
                _accepted(w, "Set load", lambda: w._on_load_action(
                    "modify", "distributed", 0))
        finally:
            _done(w)

    def test_modify_load_cancel_on_the_second_question_cancels(self):
        from PySide6.QtWidgets import QInputDialog
        pick_first = staticmethod(lambda *a, **k: (a[3][0], True))
        w = _window()
        try:
            _a_load(w, magnitude_2=40.0)
            _clean(w)
            with _swap(QInputDialog, "getItem", pick_first), \
                    _swap(QInputDialog, "getDouble",
                          _answers((55.0, True), (0.0, False))):
                _cancelled(w, w._modify_load)
            assert w.project.distributed_loads[0].magnitude_1 == 20.0
            with _swap(QInputDialog, "getItem", pick_first), \
                    _swap(QInputDialog, "getDouble",
                          _answers((55.0, True), (65.0, True))):
                _accepted(w, "Set load", w._modify_load)
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestSupports:
    def test_define_support_types(self):
        from ogr_core.support import EndAnchored
        import ogr_gui.dialogs.define_support_dialog as dsd

        class _Fake:
            result = 1

            def __init__(self, project, parent=None):
                self.project = project

            def exec(self):
                if self.result:
                    self.project.support_types.append(EndAnchored(
                        anchor_capacity=90.0, out_of_plane_spacing=1.0))
                return self.result

        class _No(_Fake):
            result = 0

        w = _window()
        try:
            with _swap(dsd, "DefineSupportDialog", _No):
                _cancelled(w, w.act_define_support)
            with _swap(dsd, "DefineSupportDialog", _Fake):
                _accepted(w, "Define support types", w.act_define_support)
        finally:
            _done(w)

    def test_add_a_support_and_a_pattern(self):
        from ogr_gui.dialogs import support_pattern_dialog as spd
        w = _window()
        try:
            _two_types(w)
            _clean(w)
            _accepted(w, "Set support",
                      lambda: w._on_add_support_picked(30.0, 20.0, 18.0,
                                                        14.0))
            _clean(w)
            with _swap(spd.AddSupportPatternDialog, "exec",
                       lambda self: (self.accept(), 1)[1]):
                w.act_add_support_pattern()
            _accepted(w, "Add support pattern",
                      lambda: w._on_pattern_picked(26.0, 24.0, 34.0, 16.0))
        finally:
            _done(w)

    def test_delete_stretch_and_right_click(self):
        w = _window()
        try:
            _two_types(w)
            _a_support(w)
            _a_support(w)
            _clean(w)
            _accepted(w, "Delete supports",
                      lambda: w._on_delete_support_clicked(1))
            _clean(w)
            _accepted(w, "Stretch support",
                      lambda: w._on_stretch_support_picked(30.0, 20.0,
                                                            31.0, 19.0))
            _clean(w)
            _accepted(w, "Delete supports",
                      lambda: w._on_support_action_requested(
                          "support_delete", 0))
        finally:
            _done(w)

    def test_right_click_properties_and_pattern(self):
        import ogr_gui.dialogs.modify_support_pattern_dialog as mspd
        import ogr_gui.dialogs.support_properties_dialog as spd

        class _Props:
            result = 1

            def __init__(self, support, project, parent=None):
                self.support = support

            def exec(self):
                if self.result:
                    self.support.name = "Renamed"
                return self.result

        class _NoProps(_Props):
            result = 0

        class _Pattern:
            def __init__(self, project, sidx, parent=None):
                self.project, self.sidx = project, sidx

            def exec(self):
                self.project.supports[self.sidx].pattern_id = None
                return 1

        w = _window()
        try:
            _two_types(w)
            _a_support(w, pattern_id="p1")
            _clean(w)
            with _swap(spd, "SupportInstancePropertiesDialog", _NoProps):
                _cancelled(w, lambda: w._on_support_action_requested(
                    "support_properties", 0))
            with _swap(spd, "SupportInstancePropertiesDialog", _Props):
                _accepted(w, "Set support",
                          lambda: w._on_support_action_requested(
                              "support_properties", 0))
            _clean(w)
            with _swap(mspd, "ModifySupportPatternDialog", _Pattern):
                _accepted(w, "Modify support pattern",
                          lambda: w._on_support_action_requested(
                              "support_modify_pattern", 0))
        finally:
            _done(w)

    def test_modify_move_and_ungroup(self):
        from PySide6.QtWidgets import QInputDialog
        w = _window()
        try:
            _two_types(w)
            _a_support(w, pattern_id="p1")
            _clean(w)
            # the support, then the SECOND type
            with _swap(QInputDialog, "getItem",
                       _answers(("1: x", False))):
                _cancelled(w, w._modify_support)

            def _support_then_type(*a, **k):
                items = a[3]
                return (items[1] if len(items) > 1 and "Strong" in items[1]
                        else items[0]), True
            with _swap(QInputDialog, "getItem",
                       staticmethod(_support_then_type)):
                _accepted(w, "Set support", w._modify_support)
            _clean(w)
            pick_first = staticmethod(lambda *a, **k: (a[3][0], True))
            with _swap(QInputDialog, "getItem", pick_first), \
                    _swap(QInputDialog, "getDouble",
                          _answers((1.5, True), (-0.5, True))):
                _accepted(w, "Move support", w._move_support)
            _clean(w)
            _accepted(w, "Ungroup support pattern", w._ungroup_pattern)
        finally:
            _done(w)

    def test_with_an_agent_step_in_between(self):
        from ogr_api import call
        from ogr_gui.agent_bridge import AgentBridge
        w = _window()
        br = AgentBridge(w)
        try:
            _two_types(w)
            _clean(w)
            s0 = _json(w.project)
            w._on_add_support_picked(30.0, 20.0, 18.0, 14.0)
            s1 = _json(w.project)
            call(br.ws, "load_set", kind="distributed", start=[2, 25],
                 end=[10, 25], magnitude=20.0, orientation="vertical")
            s2 = _json(w.project)
            w._on_delete_support_clicked(0)
            s3 = _json(w.project)
            assert w.command_stack.history()[0] == [
                "Set support", "Set load", "Delete supports"]
            for expected in (s2, s1, s0):
                w.act_undo()
                assert _json(w.project) == expected
            for expected in (s1, s2, s3):
                w.act_redo()
                assert _json(w.project) == expected
        finally:
            br.ws.shutdown()
            _done(w)
