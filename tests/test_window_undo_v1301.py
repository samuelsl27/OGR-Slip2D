# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.301 (D292) — every edit of the model made by the window is an undo
step, or says why it is not.

The defect (first GUI test, 0.1.284, H8): after the user deleted a material
in *Define Materials*, *Edit > Undo* did not bring it back — it undid the
last boundary condition an AGENT had set, without a word. The window put 26
edits on the undo stack, all of the canvas and the geometry; 54 methods
changed the model without one (the inventory of 2026-10-12, which the walk
below reproduces). The stack is the agent's too (``handle.stack =
window.command_stack``), so the mix of steps is the normal case.

The infrastructure this version adds, and what these tests protect:

* ``MainWindow._model_step(description, fn, attrs)`` — the pattern of
  ``Workspace.mutate``: one step, recorded only when the model changed,
  ``fn`` (a dialog's ``exec()`` included) inside it, ``STEP_CANCELLED`` to
  put back what a dialog wrote while open (D306), re-entrant;
  ``@undo_step`` makes a whole method one step;
* while a step is open an agent's edit, and its undo, answer Busy (the
  bridge serves on the Qt thread, inside a dialog's ``exec()`` too);
* *Undo* and *Redo* name their step, translated, and are disabled with a
  reason when the stack is empty (D289b asks every disabled entry for one);
* a step of the window and a step of the agent undo and redo in order, each
  back to the model it found, compared as JSON;
* the INVENTORY: an AST walk of ``MainWindow`` finds every method that
  writes the model and fails on one that is neither a step nor in
  ``EXCEPTIONS`` with its reason. ``BUDGET`` only goes down: 0.1.303,
  0.1.304 and 0.1.305 take the families out (0.1.302 was D310);
* every step name the stack can hold has its Spanish.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_WIN = _REPO / "ogr_gui" / "main_window.py"

# ----------------------------------------------------------------------
# The inventory
# ----------------------------------------------------------------------
#: What a method writes when it stores under ``self.project.<attr>``: the
#: attributes an undo step captures (LIGHT_ATTRS + HEAVY_ATTRS).
MODEL_ATTRS = {
    "name", "settings", "boundaries", "materials", "supports",
    "support_types", "distributed_loads", "line_loads", "seismic",
    "seismic_records", "region_assignments", "tension_crack_properties",
    "water_pressure_grid", "seepage_bcs", "random_variables", "annotations",
    "focus_objects", "user_surfaces", "fem_mesh", "seepage_result",
    "transient_results",
}
#: Methods that change what they are called on (lists, the annotation
#: layer, the settings' setters, the project's own add_/remove_...).
MUTATOR_NAMES = {"add", "remove", "insert", "append", "extend", "pop",
                 "clear", "sort", "reverse", "update", "setdefault",
                 "discard", "duplicate", "bring_to_front", "send_to_back"}
MUTATOR_PREFIXES = ("set_", "add_", "remove_", "delete_", "assign_",
                    "replace_")
NOT_MUTATORS = {"add_listener"}
#: The ones that only change a CONTAINER: on a copy (``list(...)``, a
#: comprehension) they write nothing.
CONTAINER_MUTATORS = {"add", "remove", "insert", "append", "extend", "pop",
                      "clear", "sort", "reverse", "update", "setdefault",
                      "discard"}
#: Functions of other modules that write the project they are given.
WRITER_FUNCS = {"apply_to_project", "assign_water_surface",
                "import_properties", "set_fem_mesh", "reset_fem_mesh",
                "solve_project_groundwater", "run_transient_stability"}
#: Dialogs that write the model on their own (in their accept, apply or
#: live), from the inventory of D292. A new dialog that does goes here.
WRITER_DIALOGS = {"AddGridDialog", "AnnotationsDialog", "DefineSupportDialog",
                  "HydraulicPropertiesDialog", "ModifySupportPatternDialog",
                  "ProjectSettingsDialog", "RandomVariablesDialog",
                  "SeismicLoadDialog", "SeismicRecordsDialog",
                  "SupportInstancePropertiesDialog", "SurfaceOptionsDialog",
                  "TransientStagesDialog", "WaterPressureGridDialog"}
_COPIES = {"list", "sorted", "reversed", "tuple", "set", "dict"}

_P305 = ("pending: settings and search, statistics, surfaces and focus, "
         "annotations, DXF (0.1.305)")

#: Methods that write the model outside an undo step, each with its reason.
EXCEPTIONS = {
    # -- for good: the live draft of a vertex drag ----------------------
    "_on_vertex_moved": "the live draft of a vertex drag, on every mouse "
                        "move; _on_vertex_drag_finished records the whole "
                        "drag as one ReplaceBoundaryCommand",
    "_on_vertex_drag_finished": "rewinds the draft of _on_vertex_moved and "
                                "records it with command_stack.do",
    # -- 0.1.305 --------------------------------------------------------
    "act_surface_options": _P305,
    "act_auto_grid": _P305,
    "act_add_grid": _P305,
    "_on_grid_picked": _P305,
    "act_project_settings": _P305,
    "_back_analysis": _P305,
    "_move_slope_limits": _P305,
    "_define_moment_axis": _P305,
    "_reset_moment_axis": _P305,
    "_reset_slope_limits": _P305,
    "_edit_random_variables": _P305,
    "_add_focus": _P305,
    "_manage_focus": _P305,
    "_add_surface_centre_radius": _P305,
    "_on_surface_3pt_picked": _P305,
    "_manage_user_surfaces": _P305,
    "_set_annotations_visible": _P305,
    "_delete_all_annotations": _P305,
    "_manage_annotations": _P305,
    "_start_annotation": _P305,
    "_add_image": _P305,
    "_convert_tool_to_boundary": _P305,
    "act_import_dxf": _P305,
}

#: How many there may be. Lowering it is the point; raising it needs a
#: reason in a changelog.
#: 54 in 0.1.301; 41 in 0.1.303 (materials, properties and water);
#: 25 in 0.1.304 (loads and supports).
BUDGET = 25


def _is_project(e):
    return (isinstance(e, ast.Attribute) and e.attr == "project"
            and isinstance(e.value, ast.Name) and e.value.id == "self")


def _root(e, aliases):
    """The model attribute an expression hangs from ('*' for the project
    itself) and whether it is a fresh container (a copy), or (None, _)."""
    copy = False
    while True:
        if _is_project(e):
            return "*", copy
        if isinstance(e, ast.Name):
            r = aliases.get(e.id)
            return (r[0], copy or r[1]) if r else (None, False)
        if isinstance(e, ast.Attribute) and _is_project(e.value):
            return (e.attr if e.attr in MODEL_ATTRS else None), copy
        if isinstance(e, ast.Subscript):
            e, copy = e.value, False          # an element is shared
            continue
        if isinstance(e, ast.Attribute):
            e, copy = e.value, False
            continue
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name):
            if e.func.id in _COPIES and e.args:
                e, copy = e.args[0], True
                continue
            if e.func.id == "enumerate" and e.args:
                e = e.args[0]
                continue
            # getattr(self.project, "supports", []) / getattr(alias, "x")
            if e.func.id == "getattr" and len(e.args) >= 2:
                base, _ = _root(e.args[0], aliases)
                key = e.args[1]
                if base == "*" and isinstance(key, ast.Constant):
                    return (key.value if key.value in MODEL_ATTRS
                            else None), copy
                return (base if base not in (None, "*") else None), copy
        if isinstance(e, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            e, copy = e.generators[0].iter, True
            continue
        if isinstance(e, ast.IfExp):
            r = _root(e.body, aliases)
            return r if r[0] else _root(e.orelse, aliases)
        return None, False


def _store_root(t, aliases):
    """The model attribute a store goes to. Rebinding a plain name, or
    ``self.project`` itself (a replacement), writes nothing."""
    if isinstance(t, ast.Name):
        return None
    if isinstance(t, (ast.Tuple, ast.List)):
        for el in t.elts:
            r = _store_root(el, aliases)
            if r:
                return r
        return None
    if _is_project(t):
        return None
    r, _ = _root(t, aliases)
    return None if r == "*" else r


def _bind(target, root, aliases):
    if isinstance(target, ast.Name):
        if root[0]:
            aliases[target.id] = root
        else:
            aliases.pop(target.id, None)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for el in target.elts:
            _bind(el, (root[0], False), aliases)


def writes_of(fn):
    """``[(lineno, what, node)]``: the writes of the model in ``fn``,
    nested functions and lambdas included."""
    aliases, out = {}, []
    nodes = sorted((n for n in ast.walk(fn) if hasattr(n, "lineno")),
                   key=lambda n: (n.lineno, n.col_offset))
    for n in nodes:
        if isinstance(n, ast.Assign):
            r = _root(n.value, aliases)
            for t in n.targets:
                w = _store_root(t, aliases)
                if w:
                    out.append((n.lineno, "store " + w, n))
                _bind(t, r, aliases)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
            w = _store_root(n.target, aliases)
            if w:
                out.append((n.lineno, "store " + w, n))
        elif isinstance(n, ast.Delete):
            for t in n.targets:
                w = _store_root(t, aliases)
                if w:
                    out.append((n.lineno, "del " + w, n))
        elif isinstance(n, ast.For):
            r = _root(n.iter, aliases)
            _bind(n.target, (r[0], False), aliases)
        elif isinstance(n, ast.comprehension):
            r = _root(n.iter, aliases)
            _bind(n.target, (r[0], False), aliases)
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr not in NOT_MUTATORS \
                    and (f.attr in MUTATOR_NAMES
                         or f.attr.startswith(MUTATOR_PREFIXES)):
                r, copy = _root(f.value, aliases)
                if r and not (copy and f.attr in CONTAINER_MUTATORS):
                    out.append((n.lineno, f"{f.attr} on {r}", n))
                    continue
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr",
                                                                 None)
            if name == "setattr" and n.args:
                r, _ = _root(n.args[0], aliases)
                if r and r != "*":
                    out.append((n.lineno, "setattr on " + r, n))
            elif name in WRITER_FUNCS:
                out.append((n.lineno, "calls " + name, n))
            elif name in WRITER_DIALOGS:
                out.append((n.lineno, "opens " + name, n))
    return out


def _call_name(call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)


def _is_step_call(call):
    name = _call_name(call)
    if name in ("_model_step", "SnapshotCommand"):
        return True
    f = call.func
    return (name in ("do", "record") and isinstance(f, ast.Attribute)
            and isinstance(f.value, ast.Attribute)
            and f.value.attr == "command_stack")


def _is_step_method(fn):
    return any(isinstance(d, ast.Call) and _call_name(d) == "undo_step"
               for d in fn.decorator_list)


def _step_bodies(fn):
    """The lambdas and nested functions of ``fn`` that run inside a step."""
    names, bodies = set(), set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _is_step_call(n):
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, ast.Lambda):
                    bodies.add(a)
                elif isinstance(a, ast.Name):
                    names.add(a.id)
    for n in ast.walk(fn):
        if isinstance(n, ast.FunctionDef) and n is not fn \
                and n.name in names:
            bodies.add(n)
    return bodies


def _within(node, bodies, parents, stop):
    while node is not None and node is not stop:
        if node in bodies:
            return True
        node = parents.get(node)
    return False


def uncovered_writers(src, cls_name="MainWindow"):
    """``{method: [(lineno, what), ...]}`` for the methods of ``cls_name``
    that write the model outside an undo step.

    A write is covered when its method is an ``@undo_step``, when it sits
    inside a function handed to ``_model_step`` / ``SnapshotCommand`` /
    ``command_stack.do``, or when its method is only ever CALLED from
    covered places (a helper of a step). A method referenced without being
    called — ``.connect(self.m)``, a menu action — is reached from outside
    any step.
    """
    tree = ast.parse(src)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    cls = next(n for n in tree.body
               if isinstance(n, ast.ClassDef) and n.name == cls_name)
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    bodies = {m: _step_bodies(fn) for m, fn in methods.items()}
    loose = {}
    for m, fn in methods.items():
        if _is_step_method(fn):
            continue
        ws = [(ln, what) for ln, what, node in writes_of(fn)
              if not _within(node, bodies[m], parents, fn)]
        if ws:
            loose[m] = ws
    refs = {m: [] for m in methods}
    for m, fn in methods.items():
        for n in ast.walk(fn):
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == "self" and n.attr in methods):
                p = parents.get(n)
                refs[n.attr].append(
                    (m, n, isinstance(p, ast.Call) and p.func is n))
    covered = {m for m, fn in methods.items() if _is_step_method(fn)}
    grew = True
    while grew:
        grew = False
        for m in loose:
            if m in covered or not refs[m]:
                continue
            if all(is_call and (caller in covered
                                or _within(node, bodies[caller], parents,
                                           methods[caller]))
                   for caller, node, is_call in refs[m]):
                covered.add(m)
                grew = True
    return {m: w for m, w in loose.items() if m not in covered}


class TestTheInventory:
    def test_every_project_write_goes_through_the_stack(self):
        loose = uncovered_writers(_WIN.read_text(encoding="utf-8"))
        missing = {m: w[:3] for m, w in loose.items() if m not in EXCEPTIONS}
        assert not missing, (
            "these methods of MainWindow change the model without an undo "
            "step: wrap them in _model_step / @undo_step, or add them to "
            "EXCEPTIONS with the reason", missing)

    def test_no_exception_is_a_ghost(self):
        loose = uncovered_writers(_WIN.read_text(encoding="utf-8"))
        ghosts = sorted(set(EXCEPTIONS) - set(loose))
        assert not ghosts, ("no longer write outside a step: take them out "
                            "of EXCEPTIONS and lower BUDGET", ghosts)

    def test_the_exception_list_only_shrinks(self):
        assert all(r.strip() for r in EXCEPTIONS.values())
        assert len(EXCEPTIONS) <= BUDGET, (len(EXCEPTIONS), BUDGET)
        # frozen: a version that takes a family out lowers it
        assert BUDGET == 25

    def test_the_writer_lists_are_not_ghosts(self):
        import ogr_gui.dialogs as dialogs
        src = _WIN.read_text(encoding="utf-8")
        for name in WRITER_DIALOGS:
            mod_has = hasattr(dialogs, name) or f"import {name}" in src \
                or f"{name}," in src or f"{name})" in src
            assert mod_has, name
        for name in WRITER_FUNCS:
            assert f"{name}(" in src, name

    def test_the_walk_sees_what_it_must(self):
        """The analysis itself, on a made-up window: aliases, getattr,
        setattr, copies, dialogs, steps, decorators and helpers."""
        src = '''
class MainWindow:
    def alias(self):
        s = self.project.settings.search
        s.grid_nx = 3
    def by_getattr(self):
        for sp in getattr(self.project, "supports", []):
            sp.pattern_id = None
    def by_setattr(self):
        load = self.project.distributed_loads[0]
        setattr(load, "magnitude", 1.0)
    def a_copy(self):
        items = [x for x in self.project.focus_objects]
        items.append("label")
        names = list(self.project.materials)
        names.pop()
    def a_dialog(self):
        AnnotationsDialog(self.project.annotations, self).exec()
    def a_layer(self):
        self.project.annotations.add(1)
    def reads(self):
        n = len(self.project.materials)
        self.project.is_dirty = True
        self.project._notify("x")
        self.project.add_listener(print)
    def stepped(self):
        self._model_step("Set load", lambda: self.project.line_loads.pop())
    def named(self):
        def edit(project):
            project.seismic.kh = 0.1
            self.project.seismic.kh = 0.1
        self.command_stack.do(self.project, SnapshotCommand("x", edit))
    @undo_step("Set material")
    def decorated(self):
        self.project.materials.clear()
        self.helper()
    def helper(self):
        self.project.materials.append(1)
    def connected(self):
        self.project.user_surfaces.append(1)
    def connector(self):
        self.canvas.sig.connect(self.connected)
'''
        loose = uncovered_writers(src)
        assert set(loose) == {"alias", "by_getattr", "by_setattr",
                              "a_dialog", "a_layer", "connected"}, loose


# ----------------------------------------------------------------------
# The mechanics, on a real window
# ----------------------------------------------------------------------
def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _set_weight(w, value):
    def edit():
        w.project.materials[0].unit_weight = value
    return edit


class TestTheStep:
    def test_a_change_is_one_named_step_that_undoes_and_redoes(self):
        w = _window()
        try:
            before = _json(w.project)
            w._model_step("Set material", _set_weight(w, 23.5))
            after = _json(w.project)
            assert after != before
            assert w.command_stack.history() == (["Set material"], [])
            assert w.project.is_dirty
            w.act_undo()
            assert _json(w.project) == before
            w.act_redo()
            assert _json(w.project) == after
        finally:
            _done(w)

    def test_no_change_no_step(self):
        w = _window()
        try:
            w._model_step("Set material", lambda: None)
            assert w.command_stack.history() == ([], [])
            assert not w.project.is_dirty
        finally:
            _done(w)

    def test_cancelled_puts_back_what_was_written_and_leaves_no_step(self):
        from ogr_gui.main_window import STEP_CANCELLED
        w = _window()
        try:
            before = _json(w.project)
            settings = w.project.settings

            def live_then_cancel():
                w.project.materials[0].unit_weight = 99.0
                w.project.is_dirty = True
                return STEP_CANCELLED
            assert w._model_step("Set material", live_then_cancel) is None
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            assert not w.project.is_dirty
            # what the dialog did not touch keeps its object
            assert w.project.settings is settings
        finally:
            _done(w)

    def test_a_failing_edit_leaves_no_trace(self):
        w = _window()
        try:
            before = _json(w.project)

            def boom():
                w.project.materials[0].unit_weight = 99.0
                raise ValueError("refused")
            try:
                w._model_step("Set material", boom)
            except ValueError:
                pass
            else:
                raise AssertionError("the error was swallowed")
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            assert w._open_step is None
        finally:
            _done(w)

    def test_a_step_inside_a_step_is_part_of_it(self):
        from ogr_gui.main_window import STEP_CANCELLED
        w = _window()
        try:
            before = _json(w.project)

            def outer():
                w.project.materials[0].unit_weight = 21.0
                w._model_step("Set load", _set_weight(w, 22.0))
                # a cancelled inner step puts back only its own writes
                w._model_step("Change settings", lambda: (
                    setattr(w.project.settings.methods, "num_slices", 77),
                    STEP_CANCELLED)[1])
            w._model_step("Python script", outer)
            assert w.command_stack.history() == (["Python script"], [])
            assert w.project.materials[0].unit_weight == 22.0
            assert w.project.settings.methods.num_slices != 77
            w.act_undo()
            assert _json(w.project) == before
        finally:
            _done(w)

    def test_the_decorator_takes_what_qt_passes_and_is_a_step(self):
        from PySide6.QtGui import QAction
        from ogr_gui.main_window import MainWindow, undo_step

        class _W(MainWindow):
            @undo_step("Set material")
            def heavier(self):
                self.project.materials[0].unit_weight += 1.0

        QApplication.instance() or QApplication([])
        w = _W()
        w.act_load_demo()
        try:
            act = QAction("x", w)
            act.triggered.connect(w.heavier)    # triggered(bool checked)
            act.trigger()
            assert w.command_stack.history() == (["Set material"], [])
        finally:
            _done(w)

    def test_a_click_on_a_vertex_without_moving_it_leaves_no_step(self):
        import copy
        w = _window()
        try:
            b = w.project.boundaries[0]
            w._on_vertex_drag_finished(0, copy.deepcopy(b))
            assert w.command_stack.history() == ([], [])
        finally:
            _done(w)


class TestUndoAndRedoEntries:
    def test_empty_stack_disabled_with_a_reason(self):
        w = _window()
        try:
            for key in ("undo", "redo"):
                act = w._actions[key]
                assert not act.isEnabled(), key
                assert act.statusTip(), key
        finally:
            _done(w)

    def test_they_name_the_step_in_english_and_in_spanish(self):
        from ogr_gui.i18n import set_language
        w = _window()
        try:
            w._model_step("Set material", _set_weight(w, 23.5))
            assert w._actions["undo"].isEnabled()
            assert w._actions["undo"].text() == "Undo Set material"
            assert not w._actions["redo"].isEnabled()
            w.act_undo()
            assert w._actions["redo"].text() == "Redo Set material"
            set_language("es")
            try:
                w._refresh_undo_actions()
                assert w._actions["redo"].text() == \
                    "Rehacer «Definir material»", w._actions["redo"].text()
                assert w._actions["undo"].statusTip() == \
                    "No hay nada que deshacer."
            finally:
                set_language("en")
        finally:
            _done(w)

    def test_undo_waits_for_the_step_in_progress(self):
        w = _window()
        try:
            w._model_step("Set material", _set_weight(w, 23.5))
            seen = []

            def inside():
                w.act_undo()             # e.g. from the terminal
                seen.append(w.command_stack.history())
                w.project.materials[0].unit_weight = 24.0
            w._model_step("Python script", inside)
            assert seen == [(["Set material"], [])]
            assert w.command_stack.history()[0] == ["Set material",
                                                    "Python script"]
        finally:
            _done(w)


# ----------------------------------------------------------------------
# With an agent
# ----------------------------------------------------------------------
def _bridge(w):
    """The workspace of the live bridge, wired as AgentBridge does it,
    without starting its server."""
    from ogr_gui.agent_bridge import AgentBridge
    return AgentBridge(w)


class TestWithAnAgent:
    def test_an_open_step_makes_the_agent_wait(self):
        from ogr_api import call
        from ogr_api.errors import Busy
        w = _window()
        br = _bridge(w)
        try:
            call(br.ws, "settings_set",
                 changes={"methods.num_slices": 31})       # one agent step
            answers = []

            def dialog_open():
                for op, kw in (("settings_set",
                                {"changes": {"methods.num_slices": 33}}),
                               ("project_history", {"action": "undo"})):
                    try:
                        call(br.ws, op, **kw)
                        answers.append("done")
                    except Busy as e:
                        answers.append(str(e))
                w.project.materials[0].unit_weight = 24.0
            w._model_step("Set material", dialog_open)
            assert len(answers) == 2 and all("Set material" in a
                                             for a in answers), answers
            assert w.project.settings.methods.num_slices == 31
            assert w.command_stack.history()[0] == ["Change settings",
                                                    "Set material"]
            # and afterwards the agent is served again
            call(br.ws, "project_history", action="undo")
            assert w.command_stack.history()[0] == ["Change settings"]
        finally:
            br.ws.shutdown()
            _done(w)

    def test_window_and_agent_steps_undo_in_order(self):
        from ogr_api import call
        w = _window()
        br = _bridge(w)
        try:
            s0 = _json(w.project)
            w._model_step("Set material", _set_weight(w, 21.0))
            s1 = _json(w.project)
            call(br.ws, "settings_set", changes={"methods.num_slices": 31})
            s2 = _json(w.project)
            w._model_step("Set material", _set_weight(w, 22.0))
            s3 = _json(w.project)
            assert len({s0, s1, s2, s3}) == 4
            assert w.command_stack.history()[0] == [
                "Set material", "Change settings", "Set material"]
            for expected in (s2, s1, s0):
                w.act_undo()
                assert _json(w.project) == expected
            for expected in (s1, s2, s3):
                w.act_redo()
                assert _json(w.project) == expected
            # and the agent's undo walks the same stack
            call(br.ws, "project_history", action="undo", steps=2)
            assert _json(w.project) == s1
        finally:
            br.ws.shutdown()
            _done(w)


# ----------------------------------------------------------------------
# The names
# ----------------------------------------------------------------------
def _literal_step_names():
    """Every step name written as a literal: the typed commands' defaults,
    the window's steps and the API's edits."""
    names = set()
    cmds = ast.parse((_REPO / "ogr_core" / "project" / "commands.py")
                     .read_text(encoding="utf-8"))
    for cls in (n for n in cmds.body if isinstance(n, ast.ClassDef)):
        for st in cls.body:
            if (isinstance(st, ast.AnnAssign)
                    and getattr(st.target, "id", None) == "description"
                    and isinstance(st.value, ast.Constant)
                    and st.value.value):          # Command's own ""
                names.add(st.value.value)
    win = ast.parse(_WIN.read_text(encoding="utf-8"))
    for n in ast.walk(win):
        if isinstance(n, ast.Call) and n.args and \
                isinstance(n.args[0], ast.Constant) and \
                isinstance(n.args[0].value, str) and \
                _call_name(n) in ("_model_step", "undo_step",
                                  "SnapshotCommand"):
            names.add(n.args[0].value)
    for path in (_REPO / "ogr_api" / "ops").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and _call_name(n) == "mutate" and \
                    len(n.args) >= 2 and isinstance(n.args[1], ast.Constant):
                names.add(n.args[1].value)
    return names


class TestTheNames:
    def test_every_step_name_has_spanish(self):
        from ogr_gui.i18n import _DICTS
        names = _literal_step_names()
        assert {"Set material", "Change settings", "Compute groundwater",
                "Add Boundary", "Change slope angle"} <= names, names
        missing = sorted(n for n in names if n not in _DICTS["es"])
        assert not missing, missing

    def test_an_add_of_every_boundary_type_has_spanish(self):
        """``f"Add {btype.display_name}"`` (boundary_add, the canvas)."""
        from ogr_core.geometry import BoundaryType
        from ogr_gui.i18n import _DICTS
        missing = [f"Add {b.display_name}" for b in BoundaryType
                   if f"Add {b.display_name}" not in _DICTS["es"]]
        assert not missing, missing
