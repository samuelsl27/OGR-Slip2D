# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — one rule for the range of the seismic coefficients, asked by the
API and by the dialog.

THE DEFECT. ``ogr_api.ops.loads.seismic_set`` refused ``|k| ≥ 1`` and the
seismic dialog accepted ±1 exactly: the same model could be built by hand
and not by a script. With the downward-positive convention of v0.1.214 (D170)
the vertical load is ``W·(1 + kv)``, so ``kv = −1`` is a soil with no weight
and every method's driving sum is identically zero.

THE INVARIANTS. The rule lives in ``ogr_core.project.rules`` (the module
AGENTS.md names for a rule the interface used to enforce alone), refuses the
two ends and anything that is not a number, and is what both callers read:
the API raises its message word for word, and the dialog's spin boxes stop
one step inside its limit.
"""
from __future__ import annotations

import math


class TestTheRule:

    def test_refuses_the_ends_and_a_non_number(self):
        from ogr_core.project.rules import seismic_coefficient_refusal
        for v in (1.0, -1.0, 1.5, math.nan, "x"):
            assert seismic_coefficient_refusal("kv", v) is not None, v

    def test_accepts_the_inside(self):
        from ogr_core.project.rules import seismic_coefficient_refusal
        for v in (0.0, 0.999, -0.999, 0.15, -0.05):
            assert seismic_coefficient_refusal("kv", v) is None, v


class TestTheApiAsksIt:

    def _ws(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="Seismic range")["project_id"]
        return ws, pid

    def test_the_message_is_the_rules(self):
        from ogr_api import call
        from ogr_api.errors import InvalidArgument
        from ogr_core.project.rules import seismic_coefficient_refusal
        ws, pid = self._ws()
        for v in (1.0, -1.0):
            try:
                call(ws, "seismic_set", project_id=pid, enabled=True, kv=v)
            except InvalidArgument as exc:
                expected = seismic_coefficient_refusal("kv", v).message
                assert expected in str(exc), (str(exc), expected)
            else:
                raise AssertionError("kv = %r was accepted" % v)

    def test_and_lets_the_inside_through(self):
        from ogr_api import call
        ws, pid = self._ws()
        out = call(ws, "seismic_set", project_id=pid, enabled=True,
                   kh=0.15, kv=-0.999)
        assert out["seismic"]["kv"] == -0.999


class TestTheDialogStaysInside:

    def test_the_spin_boxes_stop_one_step_inside(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.loads import SeismicLoad
        from ogr_core.project.rules import seismic_coefficient_refusal
        from ogr_gui.dialogs.seismic_dialog import SeismicLoadDialog
        QApplication.instance() or QApplication([])
        dlg = SeismicLoadDialog(SeismicLoad())
        try:
            for sb, name in ((dlg.sb_kh, "kh"), (dlg.sb_kv, "kv")):
                for end in (sb.minimum(), sb.maximum()):
                    assert seismic_coefficient_refusal(name, end) is None, (
                        name, end)
                sb.setValue(-1.0)
                assert sb.value() > -1.0, (name, sb.value())
                sb.setValue(1.0)
                assert sb.value() < 1.0, (name, sb.value())
        finally:
            dlg.deleteLater()
