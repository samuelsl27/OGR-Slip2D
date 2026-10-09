# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.293 (D291b) — what D291 left in English in the main window.

D291 (0.1.290) put the direct message arguments of ``main_window.py``
through ``tr()``; its test reads those arguments, so it could not see a
message built in a variable first («FE mesh: N elements…», «Transient: N
stage(s) solved…», the «(default properties used for: …)» and «(N methods
computed — …)» tails, «External {mode}ed.»), the dialogs' titles and
labels passed to ``QInputDialog``, the geometry cleanup report, or a reason
that comes from ``ogr_core.project.rules`` with no Spanish entry (the
Water Pressure Grid's). The second GUI test saw several of them on screen.

What these tests protect:

* every disabled action of a new project that carries a reason carries it
  translated: the same window built in English and in Spanish shows two
  different status tips;
* generating a mesh through the window, with Spanish active, says so in
  Spanish;
* no f-string with letters is left in ``main_window.py`` outside the
  places that are data, not interface: the names of undo steps (which the
  agent reads in ``project_history``) and the default names of loads
  (which the ``.ogr`` keeps).

The language and the replaced dialog are restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QInputDialog  # noqa: E402

from ogr_gui.i18n import current_language, set_language  # noqa: E402

_WIN = Path(__file__).resolve().parent.parent / "ogr_gui" / "main_window.py"


def _app():
    return QApplication.instance() or QApplication([])


def _window(lang):
    from ogr_gui.main_window import MainWindow
    _app()
    set_language(lang)
    w = MainWindow()
    w.refresh_action_availability()
    return w


class TestTheReasons:
    def test_every_reason_of_a_disabled_action_is_translated(self):
        prev = current_language()
        try:
            en = _window("en")
            tips_en = {k: a.statusTip() for k, a in en._actions.items()
                       if not a.isEnabled() and a.statusTip()}
            es = _window("es")
            same = {k: t for k, t in tips_en.items()
                    if es._actions[k].statusTip() == t}
            assert tips_en, "no disabled action carries a reason"
            assert not same, same
            en.close()
            es.close()
        finally:
            set_language(prev)


class TestTheMeshMessage:
    def test_generating_a_mesh_speaks_spanish(self):
        from ogr_api import Workspace, call
        prev = current_language()
        ws = Workspace()
        raw = QInputDialog.__dict__.get("getInt")
        w = None
        try:
            pid = call(ws, "project_new", name="d291b")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
                "materials": [{"name": "Soil", "unit_weight": 20,
                               "strength": {"model": "mohr_coulomb", "params": {
                                   "cohesion": 5.0, "friction_angle": 30.0}}}]})
            w = _window("es")
            w._attach_project(ws.get(pid).project)
            QInputDialog.getInt = staticmethod(lambda *a, **k: (150, True))
            w._generate_fem_mesh()
            msg = w.statusBar().currentMessage()
            assert msg.startswith("Malla de elementos finitos:"), msg
            assert "elements" not in msg and "nodes" not in msg, msg
        finally:
            if raw is None:
                del QInputDialog.getInt
            else:
                QInputDialog.getInt = raw
            set_language(prev)
            if w is not None:
                w.close()
            ws.shutdown()


def _letters(text):
    """Letters outside replacement fields and HTML tags."""
    text = re.sub(r"<[^>]*>", "", re.sub(r"[{][^}]*[}]", "", text))
    return any(c.isalpha() for c in text)


#: The f-strings that stay, each with its reason: the window title carries
#: the product's name and the PROJECT's name (data: a new project is named
#: "Untitled", the demo "Demo slope"), and the report's file name.
_DATA = {
    "OGR Slip2D v{} — OpenGeoRock Suite",
    "OGR Slip2D v{} — Untitled",
    "OGR Slip2D v{} — Demo slope",
    "OGR Slip2D v{} — {}",
    "{}_report.pdf",
}


class TestNoEnglishLeft:
    def test_no_fstring_with_letters_outside_data(self):
        tree = ast.parse(_WIN.read_text(encoding="utf-8"))
        allowed = set()
        for node in ast.walk(tree):
            # the format spec of a field (":.1f") is a JoinedStr too
            if isinstance(node, ast.FormattedValue) and node.format_spec:
                allowed.add(id(node.format_spec))
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            # undo steps: the agent reads their names in project_history
            if name and name.endswith("Command") and node.args:
                allowed.add(id(node.args[0]))
            # the default name of a load is data the .ogr keeps
            for kw in node.keywords:
                if kw.arg == "name":
                    allowed.add(id(kw.value))
        loose = []
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr) and id(node) not in allowed:
                text = "".join(v.value if isinstance(v, ast.Constant) else "{}"
                               for v in node.values)
                if _letters(text) and text not in _DATA:
                    loose.append((node.lineno, text[:60]))
        assert not loose, loose
