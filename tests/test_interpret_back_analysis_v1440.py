# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.440 (D419) — Interpret's back analysis reads the run it is shown on.

The invariant: a count made on a result reads the result. Interpret prices
the critical surface of a run, on the run's slices; so the seismic
coefficients are the ones the method APPLIED (``details["kh"]``/``["kv"]``,
the design standard's seismic factor in them) and the supports are the ones
of the model the run was computed on. Until this version the window took the
slices from the run and both of those from the project AS IT IS NOW, measured
on 0.1.435 with this file's grid (Janbu, target 1.5, elevation 20, kN/m):

    nothing changed, no earthquake, no standard      145.99   145.99
    kh raised from 0 to 0.1 after computing          145.99   258.49
    a nail added after computing                     145.99    36.42
    a standard with seismic factor 1.5, kh 0.1,
      and NOTHING changed                            314.73   258.49

(the run's data, and what the window published). A result does not carry the
supports it was computed with, so the window cannot price it against another
model: with the model changed it refuses before asking anything, by the
fingerprint the main window marks a stale result with (D304), and shows the
notice and the reason on its greyed entry.

The reference is an IDENTITY, not a snapshot (Bishop 1955; Janbu 1954; the
identity of v0.1.220, D210): at a surface's own factor of safety, with the
data it was computed with, the support force is zero. It is measured
UNCLIPPED -- ``required_force`` reports a negative force as 0, which hides
the unsafe half -- to 1e-9 of the weight of the mass, on runs solved to
1e-12 (with the default tolerance, 0.005, the run's own force is 6e-6 to
7e-4 of the weight and the identity resolves nothing). "Active equals
passive at a target of 1.0" is not used: at F = 1 the two formulas are the
same sum, so it holds whatever is passed.

``_V1439`` is MEASURED on the tree of 0.1.439 (38f0cae) by running this
file's ``_capture()`` there (``_auditoria/P10_herramientas/capture_d419.py``
of the bench); it is not what this code prints. It holds the run's forces to
the last bit, found with ``required_force`` and the run's own data, and the
window's message where nothing may change: no change after computing, no
earthquake, no supports.

The model handed over with the slices is the one the run was computed on,
the factored copy under a design standard (D210). It decides a number only
when a support reads the soil: the fourth run has a geosynthetic whose
pull-out is a fraction of the soil's strength, under a standard that
factors that strength.

From the review of 0.1.440 (the owner's decisions of 2026-11-13):

* the model is asked again once the two inputs are answered -- they are
  modal, and an agent's edit goes through the event loop they keep running;
* a model that cannot be read is not called "an earlier model";
* **Optimize Surfaces refuses the result of an earlier model.** It walked
  from that run's critical surface and stamped the whole result, every
  method's, with the model of now, so the notice went and Interpret took a
  run made before a nail was added for a run of the model with it;
* **an agent's edit schedules the check** even when it notifies nothing (a
  setting): the panel and Interpret were left unmarked until the next event.

Cost, measured one test at a time: four runs of a 64-circle grid with two
methods (0.3 to 1.6 s each, the one with the sheet the dearest), nine main
windows of 0.1 s with a one-method Compute each; about seven seconds, the
dearest test a little over two (the one that attaches a second project and
computes it). The first test to open a window also pays the imports of the
interface when the file runs alone.
"""
from __future__ import annotations

import ast
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parent.parent
_ELEV, _TARGET = 20.0, 1.5
_METHODS = ("janbu_simplified", "bishop_simplified")
_TOL_W = 1e-9
_STALE = "Results of an earlier model: compute again."
_STALE_ES = "Resultados de un modelo anterior: vuelve a calcular."

# Measured on 0.1.439 (38f0cae) with ``_capture()``: see the header. Per
# run: active and passive force (hex), the passive as the window prints it,
# and the kh the method applied.
_V1439 = {
    "plain.bishop_simplified.message":
        "Required support force for FS = 1.5\n\nactive: 91.30\n"
        "passive: 136.95\n\nThe passive value is the larger and therefore "
        "the conservative one for design.",
    "plain.bishop_simplified.run": [
        "0x1.6d32e595c4c50p+6", "0x1.11e62c305393cp+7", "136.95", "0.0"],
    "plain.janbu_simplified.message":
        "Required support force for FS = 1.5\n\nactive: 97.33\n"
        "passive: 145.99\n\nThe passive value is the larger and therefore "
        "the conservative one for design.",
    "plain.janbu_simplified.run": [
        "0x1.854e22adc8764p+6", "0x1.23fa9a025658cp+7", "145.99", "0.0"],
    "standard.bishop_simplified.run": [
        "0x1.8bd3b993e202bp+7", "0x1.28decb2ee9821p+8", "296.87",
        "0.15000000000000002"],
    "standard.janbu_simplified.run": [
        "0x1.a3a54fd490ebep+7", "0x1.3abbfbdf6cb10p+8", "314.73",
        "0.15000000000000002"],
}


def _is(value, measured_hex) -> bool:
    """``value`` against a force measured on another tree. To 1e-9 and not
    to the last bit: the literal was measured on one machine and the suite
    also runs on another (the CI's libm), where the last bits of a sum may
    differ. The bit-for-bit comparisons of this file are between two values
    computed in the same process."""
    ref = float.fromhex(measured_hex)
    return abs(value - ref) <= 1e-9 * abs(ref)


def _by_the_run(name, mid, target):
    """``required_force`` with the run's own data, computed here: the
    slices, the coefficients the method applied and the analysed model."""
    import ogr_slip2d.back_analysis as BA
    from ogr_core.project import prepare_analysis_project
    p, outcome, _fp = _run(name)
    factored, _report = prepare_analysis_project(p)
    c = outcome.results[mid].critical
    kh, kv = _applied(c)
    return BA.required_force(_slices(c), c.surface, target, mid, _ELEV,
                             kh, kv, project=factored)


# ======================================================================
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    kept = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(kept)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced and put back, an instance attribute removed
    again if it was not there."""
    own = vars(owner) if not isinstance(owner, type) else None
    had = own is None or name in own
    kept = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if had:
            setattr(owner, name, kept)
        else:
            delattr(owner, name)


def _grid_project(methods=_METHODS):
    """The 64-circle grid of ``_circle_project``
    (``test_back_analysis_user_surfaces_v1428``) on the demo slope (crest at
    elevation 25, toe at 15), solved to 1e-12."""
    from examples.quick_slope import build_demo_slope
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "circular", "grid"
    s.grid_x_min, s.grid_x_max = 30.0, 45.0
    s.grid_y_min, s.grid_y_max = 40.0, 55.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    p.settings.methods.enabled_methods = list(methods)
    p.settings.methods.tolerance = 1e-12
    p.settings.methods.max_iterations = 400
    ba = p.settings.back_analysis
    ba.method_id, ba.target_fos, ba.elevation = (
        "janbu_simplified", _TARGET, _ELEV)
    return p


def _seismic(p, kh, kv=0.0, on=True):
    p.seismic.enabled, p.seismic.kh, p.seismic.kv = on, kh, kv


def _seismic_standard(p, factor):
    """A custom design standard whose only factor is the seismic one."""
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("none")
    ds.standard = "custom"
    ds.factor_seismic = factor


def _add_nail(p):
    """A 12 m nail on the face at elevation 20, which crosses the critical
    circle of the grid ((40, 40), R 24.93)."""
    from ogr_core.geometry import Vertex
    from ogr_core.support import SoilNail, SupportInstance
    p.support_types = [SoilNail(tensile_capacity=100.0, plate_capacity=75.0,
                                bond_strength=20.0,
                                out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(type_id="soil_nail",
                                  head=Vertex(30.0, 20.0),
                                  tail=Vertex(18.0, 20.0))]


def _remove_nail(p):
    p.support_types, p.supports = [], []


def _add_sheet(p):
    """A geosynthetic on the face at elevation 20 whose pull-out is a
    fraction of the SOIL's own strength (Jewell 1996): what it carries
    depends on the materials, so under a standard that factors them it
    depends on which model it is read from."""
    from ogr_core.geometry import Vertex
    from ogr_core.support import Geosynthetic, SupportInstance
    p.support_types = [Geosynthetic(tensile_capacity=500.0,
                                    pullout_mode="coefficient",
                                    coefficient_of_interaction=0.8)]
    p.supports = [SupportInstance(type_id="geosynthetic",
                                  head=Vertex(30.0, 20.0),
                                  tail=Vertex(14.0, 20.0))]


_RUNS: dict = {}


def _run(name):
    """``(project, outcome, fingerprint)`` of one of the four runs, once:
    ``plain`` (no earthquake, no standard), ``seismic`` (kh 0.1 and kv
    0.05), ``standard`` (kh 0.1 under a standard whose seismic factor is
    1.5) and ``sheet`` (a geosynthetic that reads the soil's strength,
    under Eurocode 7 DA1-C2, which factors it). The fingerprint is the
    model's as the run started."""
    if name not in _RUNS:
        from ogr_api.snapshot import model_hash
        from ogr_slip2d.analysis_runner import run_analysis
        p = _grid_project()
        if name == "seismic":
            _seismic(p, 0.1, 0.05)
        if name == "standard":
            _seismic(p, 0.1)
            _seismic_standard(p, 1.5)
        if name == "sheet":
            _add_sheet(p)
            p.settings.design_standard.enabled = True
            p.settings.design_standard.apply_preset("eurocode7_da1c2")
        _RUNS[name] = (p, run_analysis(p), model_hash(p))
    return _RUNS[name]


@contextmanager
def _changed(p, change, undo):
    """The model edited after its run, and put back as it was."""
    from ogr_api.snapshot import model_hash
    before = model_hash(p)
    try:
        change(p)
        yield
    finally:
        # the project is shared by the file: put back whatever happened
        undo(p)
    assert model_hash(p) == before, "the edit was not undone"


# The edits made after a run: (run, edit, its undo)
_EDITS = {
    "kh raised": ("plain", lambda p: _seismic(p, 0.1),
                  lambda p: _seismic(p, 0.0, on=False)),
    "earthquake off": ("seismic", lambda p: _seismic(p, 0.1, 0.05, on=False),
                       lambda p: _seismic(p, 0.1, 0.05)),
    "a nail added": ("plain", _add_nail, _remove_nail),
}


def _slices(result):
    from ogr_slip2d.slice_store import SpilledSlices
    sl = result.slices
    return sl.materialize() if type(sl) is SpilledSlices else sl


def _applied(result):
    """The seismic coefficients the method applied on this result."""
    d = result.details
    return float(d.get("kh", 0.0) or 0.0), float(d.get("kv", 0.0) or 0.0)


def _unclipped(result, target, mid, kh, kv, project):
    """``(passive, W)``: the passive force WITHOUT the clip to zero, from
    the method's own two sums at a fixed factor."""
    import ogr_slip2d.back_analysis as BA
    sl = _slices(result)
    resisting, driving, arm = BA._sums_at_fixed_fos(
        sl, result.surface, target, kh, kv, _ELEV, mid, stress_fos=target,
        project=project)
    return (target * driving - resisting) / arm, sum(s.weight for s in sl)


def _window(name, mid, **kw):
    from ogr_gui.interpret_window import InterpretWindow
    _app()
    p, outcome, _fp = _run(name)
    return InterpretWindow(p, {mid: outcome.results[mid]}, None,
                           factor_report=outcome.factor_report, **kw)


def _ask(w, target, elevation=_ELEV):
    """Interpret's back analysis with its two inputs answered and its box
    captured (no modal opens): what it said, what it asked, and every call
    it made to ``required_force`` with what that returned."""
    from PySide6.QtWidgets import QInputDialog
    import ogr_slip2d.back_analysis as BA
    answers = iter([(target, True), (elevation, True)])
    said, asked, calls = [], [], []
    real = BA.required_force

    def get_double(_parent, _title, label, *a, **k):
        asked.append(label)
        return next(answers)

    def spy(slices, surface, target_fos, method_id="bishop_simplified",
            elevation=0.0, kh=0.0, kv=0.0, project=None):
        r = real(slices, surface, target_fos, method_id, elevation, kh, kv,
                 project=project)
        calls.append(NS(kh=kh, kv=kv, project=project, method_id=method_id,
                        result=r))
        return r

    with _swapped(QInputDialog, "getDouble", staticmethod(get_double)), \
            _swapped(BA, "required_force", spy), \
            _swapped(w, "_info", lambda text, *a: said.append(text)):
        w._back_analysis_report()
    return NS(said=said, asked=asked, calls=calls)


def _capture():
    """What the tree it runs on gives where 0.1.440 must change nothing:
    the run's forces with the run's own data, and the window's message with
    no change after computing, no earthquake and no supports. Run on the
    tree of 0.1.439 for ``_V1439`` (see the header)."""
    import ogr_slip2d.back_analysis as BA
    from ogr_core.project import prepare_analysis_project
    out = {}
    with _language("en"):
        for name in ("plain", "standard"):
            p, outcome, _fp = _run(name)
            factored, _report = prepare_analysis_project(p)
            for mid in _METHODS:
                c = outcome.results[mid].critical
                kh, kv = _applied(c)
                r = BA.required_force(_slices(c), c.surface, _TARGET, mid,
                                      _ELEV, kh, kv, project=factored)
                out[f"{name}.{mid}.run"] = [
                    r.active_force.hex(), r.passive_force.hex(),
                    "%.2f" % r.passive_force, repr(kh)]
        for mid in _METHODS:
            w = _window("plain", mid)
            try:
                out[f"plain.{mid}.message"] = _ask(w, _TARGET).said[0]
            finally:
                w.close()
    return out


# ======================================================================
class TestTheCountReadsTheResult:
    """``required_force_of_result``, without Qt."""

    def test_zero_at_its_own_factor_whatever_the_project_says_now(self):
        """The identity, unclipped: priced at its own factor of safety, the
        critical surface needs no force -- with the earthquake raised or
        switched off in the project after the run, and under a standard
        that factors it. The coefficients come from the result."""
        import ogr_slip2d.back_analysis as BA
        from ogr_core.project import prepare_analysis_project
        cases = [(run, edit, undo) for run, edit, undo in _EDITS.values()
                 if edit is not _add_nail]
        cases.append(("standard", lambda p: None, lambda p: None))
        for run, edit, undo in cases:
            p, outcome, _fp = _run(run)
            with _changed(p, edit, undo):
                now, _report = prepare_analysis_project(p)
                for mid in _METHODS:
                    c = outcome.results[mid].critical
                    seen = []
                    real = BA.required_force

                    def spy(slices, surface, target, method_id, elevation,
                            kh, kv, project=None):
                        seen.append((method_id, kh, kv, project))
                        return real(slices, surface, target, method_id,
                                    elevation, kh, kv, project=project)
                    with _swapped(BA, "required_force", spy):
                        r = BA.required_force_of_result(c, c.fos, _ELEV,
                                                        project=now)
                    assert r is not None, (run, mid)
                    (method_id, kh, kv, project), = seen
                    assert method_id == mid and project is now
                    assert (kh, kv) == _applied(c), (run, mid, kh, kv)
                    passive, weight = _unclipped(c, c.fos, mid, kh, kv, now)
                    assert abs(passive) <= _TOL_W * weight, (
                        run, mid, passive / weight)

    def test_the_cases_are_the_ones_they_claim_to_be(self):
        """Under the standard the method applied the project's kh times the
        seismic factor; the seismic run has both coefficients (a count that
        dropped kv would pass every case with kv = 0)."""
        p, outcome, _fp = _run("standard")
        assert p.seismic.kh == 0.1
        for mid in _METHODS:
            kh, kv = _applied(outcome.results[mid].critical)
            assert abs(kh - 0.15) < 1e-15 and kv == 0.0, (mid, kh, kv)
            assert _applied(_run("seismic")[1].results[mid].critical) == (
                0.1, 0.05)
            assert _applied(_run("plain")[1].results[mid].critical) == (
                0.0, 0.0)

    def test_slices_spilled_to_disk_are_read_back(self):
        """A result whose slices a large run left in its store prices the
        same, to the last bit."""
        import copy
        import ogr_slip2d.back_analysis as BA
        from ogr_slip2d.slice_store import SliceStore, SpilledSlices
        p, outcome, _fp = _run("seismic")
        c = outcome.results["janbu_simplified"].critical
        spilled = copy.copy(c)
        store = SliceStore()
        store.spill(spilled)
        assert type(spilled.slices) is SpilledSlices
        assert type(c.slices) is not SpilledSlices
        r = BA.required_force_of_result(spilled, _TARGET, _ELEV, p)
        assert r.passive_force == _by_the_run(
            "seismic", "janbu_simplified", _TARGET).passive_force

    def test_a_result_that_cannot_be_priced(self):
        """No slices, no force; and a result built by hand, with no
        ``details``, had no earthquake (as the free body reads it)."""
        import ogr_slip2d.back_analysis as BA
        p, outcome, _fp = _run("plain")
        c = outcome.results["janbu_simplified"].critical
        bare = NS(slices=None, surface=c.surface, details={},
                  method_id="janbu_simplified")
        assert BA.required_force_of_result(bare, _TARGET, _ELEV, p) is None
        by_hand = NS(slices=_slices(c), surface=c.surface, details=None,
                     method_id="janbu_simplified")
        r = BA.required_force_of_result(by_hand, _TARGET, _ELEV, p)
        assert r.passive_force == _by_the_run(
            "plain", "janbu_simplified", _TARGET).passive_force
        assert _is(r.passive_force, _V1439["plain.janbu_simplified.run"][1])

    def test_the_method_is_the_results_own_unless_named(self):
        import ogr_slip2d.back_analysis as BA
        p, outcome, _fp = _run("plain")
        c = outcome.results["bishop_simplified"].critical
        own = BA.required_force_of_result(c, _TARGET, _ELEV, p)
        named = BA.required_force_of_result(c, _TARGET, _ELEV, p,
                                            method_id="janbu_simplified")
        assert own.passive_force == _by_the_run(
            "plain", "bishop_simplified", _TARGET).passive_force
        assert _is(own.passive_force,
                   _V1439["plain.bishop_simplified.run"][1])
        # Janbu's sums on the same slices: another force (it has no arm)
        assert abs(named.passive_force - own.passive_force) > 1.0
        assert BA.required_force_of_result(c, _TARGET, _ELEV, p,
                                           method_id="spencer") is None


# ======================================================================
class TestInterpretRefusesAnotherModel:

    def _refused(self, w, sentence=_STALE):
        got = _ask(w, _TARGET)
        assert got.said == [sentence], got.said
        assert got.asked == [], "it asked before refusing: %r" % got.asked
        assert got.calls == [], "it priced the run against another model"

    def test_with_the_model_changed_it_refuses_before_asking(self):
        """Each edit, with the fingerprint the window takes as it is built
        (on the tree before, each published a force: 258.49, 145.99 and
        36.42 kN/m with Janbu)."""
        for label, (run, edit, undo) in _EDITS.items():
            for mid in _METHODS:
                w = _window(run, mid)
                try:
                    with _language("en"), _changed(_run(run)[0], edit, undo):
                        self._refused(w)
                    # and with the edit undone it answers again
                    with _language("en"):
                        got = _ask(w, _TARGET)
                    assert len(got.calls) == 1 and len(got.asked) == 2, label
                finally:
                    w.close()

    def test_with_the_fingerprint_of_the_run(self):
        """What the main window hands over: the model as the run STARTED.
        A window opened after the edit is of an earlier model from birth."""
        for label, (run, edit, undo) in _EDITS.items():
            p, _outcome, fingerprint = _run(run)
            with _language("en"), _changed(p, edit, undo):
                w = _window(run, "janbu_simplified",
                            model_fingerprint=fingerprint)
                try:
                    assert not w.results_are_current(), label
                    self._refused(w)
                finally:
                    w.close()

    def test_it_says_it_in_spanish(self):
        run, edit, undo = _EDITS["kh raised"]
        w = _window(run, "janbu_simplified")
        try:
            with _language("es"), _changed(_run(run)[0], edit, undo):
                self._refused(w, _STALE_ES)
        finally:
            w.close()

    def test_a_model_edited_while_the_inputs_are_open(self):
        """The two inputs are modal and an agent's edit goes through the
        event loop they keep running: the model is asked again once they
        are answered, and the run is not priced against what it became."""
        from PySide6.QtWidgets import QInputDialog
        import ogr_slip2d.back_analysis as BA
        run, edit, undo = _EDITS["a nail added"]
        p = _run(run)[0]
        w = _window(run, "janbu_simplified")
        said, asked, calls = [], [], []

        def get_double(_parent, _title, label, *a, **k):
            asked.append(label)
            if len(asked) == 2:           # while the second one is open
                edit(p)
            return (_TARGET, True) if len(asked) == 1 else (_ELEV, True)

        def spy(*a, **k):
            calls.append(a)
        try:
            with _language("en"), \
                    _swapped(QInputDialog, "getDouble",
                             staticmethod(get_double)), \
                    _swapped(BA, "required_force", spy), \
                    _swapped(w, "_info", lambda text, *a: said.append(text)):
                try:
                    w._back_analysis_report()
                finally:
                    undo(p)
        finally:
            w.close()
        assert len(asked) == 2 and said == [_STALE] and not calls, (
            asked, said, calls)

    def test_a_window_that_cannot_tell_is_not_refused(self):
        """A project that cannot be serialised (a test's stand-in) has no
        fingerprint, and a window without one says its results are current
        and prices them; so does one whose model cannot be read NOW: «an
        earlier model» is said of a model that was compared."""
        import ogr_gui.interpret_window as IW
        assert IW._fingerprint_of(NS()) is None
        assert IW._fingerprint_of(_run("plain")[0]) == _run("plain")[2]
        run, edit, undo = _EDITS["kh raised"]
        w = _window(run, "janbu_simplified")
        try:
            with _language("en"), _changed(_run(run)[0], edit, undo):
                assert not w.results_are_current()
                with _swapped(IW, "_fingerprint_of", lambda project: None):
                    assert w.results_are_current()
                with _swapped(w, "_model_fingerprint", None):
                    assert w.results_are_current()
                    got = _ask(w, _TARGET)
                    assert len(got.calls) == 1 and len(got.asked) == 2
        finally:
            w.close()


# ======================================================================
class TestTheRunsNumbers:

    def test_the_identity_through_the_window(self):
        """With nothing changed, what the window passes on gives zero at the
        critical surface's own factor. Under a standard with seismic factor
        1.5 it passed the project's kh, 0.1, where the method had applied
        0.15: -0.044 of the weight, published as 0. And the model it hands
        over is the one the run was computed on, the FACTORED copy (D210):
        a sheet that takes a fraction of the soil's strength carries less
        on the factored soil, and read from the project as drawn the same
        surface is -0.044 of its weight off too."""
        for run in ("standard", "sheet"):
            for mid in _METHODS:
                c = _run(run)[1].results[mid].critical
                w = _window(run, mid)
                try:
                    with _language("en"):
                        got = _ask(w, c.fos)
                finally:
                    w.close()
                call, = got.calls
                assert call.project is not w.project, run
                passive, weight = _unclipped(c, c.fos, mid, call.kh,
                                             call.kv, call.project)
                assert abs(passive) <= _TOL_W * weight, (
                    run, mid, passive / weight)

    def test_the_standard_case_publishes_the_runs_force(self):
        """To the last bit of ``required_force`` with the run's data
        (314.73 and 296.87 kN/m; the window said 258.49 and 243.56)."""
        for mid, shown in (("janbu_simplified", "314.73"),
                           ("bishop_simplified", "296.87")):
            active, passive, text, kh = _V1439[f"standard.{mid}.run"]
            w = _window("standard", mid)
            try:
                with _language("en"):
                    got = _ask(w, _TARGET)
            finally:
                w.close()
            call, = got.calls
            ref = _by_the_run("standard", mid, _TARGET)
            assert call.result.passive_force == ref.passive_force, mid
            assert call.result.active_force == ref.active_force, mid
            assert _is(call.result.passive_force, passive), mid
            assert _is(call.result.active_force, active), mid
            # the coefficient the method applied on 0.1.439, and its print
            assert abs(call.kh - float(kh)) < 1e-15 and call.kv == 0.0
            assert "%.2f" % call.result.passive_force == text == shown
            lines = got.said[0].split("\n")
            assert lines[0] == "Required support force for ODF = 1.5"
            assert "passive: " + shown in lines, lines

    def test_nothing_changed_nothing_moves(self):
        """No change after computing, no earthquake, no supports: the
        message of 0.1.439, byte for byte (145.99 and 136.95 kN/m)."""
        for mid, shown in (("janbu_simplified", "145.99"),
                           ("bishop_simplified", "136.95")):
            w = _window("plain", mid)
            try:
                with _language("en"):
                    got = _ask(w, _TARGET)
            finally:
                w.close()
            assert got.said == [_V1439[f"plain.{mid}.message"]], got.said
            assert "passive: " + shown in got.said[0].split("\n")
            call, = got.calls
            active, passive, text, kh = _V1439[f"plain.{mid}.run"]
            assert call.result.passive_force == _by_the_run(
                "plain", mid, _TARGET).passive_force
            assert _is(call.result.passive_force, passive)
            assert _is(call.result.active_force, active)
            assert "%.2f" % call.result.passive_force == text == shown
            assert (call.kh, call.kv) == (float(kh), 0.0)


# ======================================================================
def _main_window(p, methods=("janbu_simplified",)):
    """A main window on ``p`` with a Compute done in it."""
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w._attach_project(p)
    _compute(w, methods)
    return w


def _compute(w, methods=("janbu_simplified",)):
    from ogr_gui.main_window import _ComputeWorker
    errors: list = []
    w.worker = _ComputeWorker(w.project, list(methods))
    w.worker.failed.connect(errors.append)
    w.worker.run()
    assert not errors, errors
    w._on_compute_done(w.worker.results)


def _done(w):
    for win in list(w.interpret_windows):
        win.close()
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


def _marked(win):
    """``(notice shown, Back Analysis enabled, its status tip)``."""
    return (not win.summary_dock.stale_label.isHidden(),
            win._act_back_analysis.isEnabled(),
            win._act_back_analysis.statusTip())


class TestTheNoticeAndTheGate:

    def test_the_edit_marks_interpret_and_undoing_it_unmarks_it(self):
        for lang, sentence in (("en", _STALE), ("es", _STALE_ES)):
            with _language(lang):
                w = _main_window(_grid_project(("janbu_simplified",)))
                try:
                    w.act_interpret()
                    win = w.interpret_windows[-1]
                    assert win.summary_dock.stale_label.text() == sentence
                    assert _marked(win) == (False, True, "")
                    _seismic(w.project, 0.1)
                    w._check_results_stale()
                    assert w.results_dock.is_stale()
                    assert _marked(win) == (True, False, sentence), lang
                    _seismic(w.project, 0.0, on=False)
                    w._check_results_stale()
                    assert not w.results_dock.is_stale()
                    assert _marked(win) == (False, True, ""), lang
                finally:
                    _done(w)

    def test_opened_on_a_stale_result_it_is_marked_from_birth(self):
        with _language("en"):
            w = _main_window(_grid_project(("janbu_simplified",)))
            try:
                _add_nail(w.project)
                w.act_interpret()
                win = w.interpret_windows[-1]
                assert _marked(win) == (True, False, _STALE)
                got = _ask(win, _TARGET)
                assert got.said == [_STALE] and not got.asked
            finally:
                _done(w)

    def test_each_window_keeps_the_fingerprint_of_its_own_run(self):
        """One opened before the last Compute is of the earlier model: the
        results panel is current again, and that window is not."""
        with _language("en"):
            w = _main_window(_grid_project(("janbu_simplified",)))
            try:
                w.act_interpret()
                old = w.interpret_windows[-1]
                _seismic(w.project, 0.1)
                _compute(w)
                w.act_interpret()
                new = w.interpret_windows[-1]
                w._check_results_stale()
                assert not w.results_dock.is_stale()
                assert _marked(old) == (True, False, _STALE)
                assert _marked(new) == (False, True, "")
            finally:
                _done(w)

    def test_the_timer_runs_for_an_open_interpret_alone(self):
        """With no result in the main window's own panel (another project
        attached), an edit still reaches the windows it has open."""
        with _language("en"):
            w = _main_window(_grid_project(("janbu_simplified",)))
            try:
                w.act_interpret()
                win = w.interpret_windows[-1]
                w._results_model_hash = None
                w._stale_timer.stop()
                _seismic(win.project, 0.1)
                w._on_project_event("seismic_changed")
                assert w._stale_timer.isActive()
                w._stale_timer.stop()
                w._check_results_stale()
                assert _marked(win) == (True, False, _STALE)
            finally:
                _done(w)

    def test_a_window_of_another_project_is_asked_about_its_own(self):
        """After New or Open the main window holds another project; an
        Interpret left open keeps the one it was opened on, and an edit of
        the new project does not mark it."""
        with _language("en"):
            w = _main_window(_grid_project(("janbu_simplified",)))
            try:
                w.act_interpret()
                win = w.interpret_windows[-1]
                other = _grid_project(("janbu_simplified",))
                w._attach_project(other)
                assert win.project is not w.project
                _compute(w)
                _seismic(other, 0.1)
                w._check_results_stale()
                assert w.results_dock.is_stale()
                assert _marked(win) == (False, True, "")
            finally:
                _done(w)


# ======================================================================
class TestTheOtherWaysIn:
    """From the review of 0.1.440 (the owner's decisions): two older gaps
    through which Interpret still took a run of an earlier model for one of
    the model as it is."""

    _CIRCLE = "Optimisation applies to NON-CIRCULAR surfaces."

    def _optimize(self, w):
        """Optimize Surfaces with its box captured; an input that opens
        fails the test."""
        from PySide6.QtWidgets import QInputDialog

        def opened(*a, **k):
            raise AssertionError("it asked before refusing")
        said = []
        with _swapped(QInputDialog, "getItem", staticmethod(opened)), \
                _swapped(QInputDialog, "getInt", staticmethod(opened)), \
                _swapped(w, "_info", lambda text, *a: said.append(text)):
            w._optimize_surfaces()
        return said

    def test_optimize_surfaces_refuses_the_result_of_an_earlier_model(self):
        """It walked from the critical surface of the earlier run and
        stamped the WHOLE result, every other method's too, with the model
        of now: measured, after adding a nail the results panel lost its
        notice and Interpret took the run made before the nail for current.
        With the model as it was it goes on to the engine's own question
        (this run is of circles, which it does not optimise)."""
        for lang, sentence in (("en", _STALE), ("es", _STALE_ES)):
            with _language(lang):
                w = _main_window(_grid_project())
                try:
                    stamped = w._results_model_hash
                    kept = dict(w.last_search_results)
                    if lang == "en":
                        first, = self._optimize(w)
                        assert first.startswith(self._CIRCLE), first
                    _add_nail(w.project)
                    assert self._optimize(w) == [sentence]
                    assert w._results_model_hash == stamped
                    assert w.last_search_results == kept
                    w._check_results_stale()
                    assert w.results_dock.is_stale()
                    w.act_interpret()
                    assert _marked(w.interpret_windows[-1])[:2] == (
                        True, False)
                finally:
                    _done(w)

    def test_results_put_there_by_hand_are_not_refused(self):
        """Without a fingerprint nothing says they are of another model."""
        with _language("en"):
            w = _main_window(_grid_project())
            try:
                w._results_model_hash = None
                _add_nail(w.project)
                first, = self._optimize(w)
                assert first.startswith(self._CIRCLE), first
            finally:
                _done(w)

    def test_an_agents_edit_schedules_the_check(self):
        """An operation that notifies nothing (a setting) reaches the
        window through the bridge's ``after_edit`` alone: the results
        panel and the open Interpret were left unmarked until the next
        event of the project."""
        from ogr_gui.agent_bridge import WindowHost
        with _language("en"):
            w = _main_window(_grid_project(("janbu_simplified",)))
            try:
                w.act_interpret()
                win = w.interpret_windows[-1]
                w._stale_timer.stop()
                _seismic(w.project, 0.1)        # set, with no event
                assert not w._stale_timer.isActive()
                WindowHost(w).after_edit()
                assert w._stale_timer.isActive()
                w._stale_timer.stop()
                w._check_results_stale()
                assert w.results_dock.is_stale()
                assert _marked(win) == (True, False, _STALE)
            finally:
                _done(w)


# ======================================================================
class TestTheSource:

    def _slot(self):
        tree = ast.parse((_ROOT / "ogr_gui" / "interpret_window.py")
                         .read_text(encoding="utf-8"))
        return next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef)
                    and n.name == "_back_analysis_report")

    def test_the_slot_does_not_read_the_earthquake_of_now(self):
        """Read by AST: the slot opens two modal inputs. Nothing in it reads
        a ``.seismic``, and the count is the core's, on the result."""
        fn = self._slot()
        read = [n.lineno for n in ast.walk(fn)
                if isinstance(n, ast.Attribute)
                and n.attr in ("seismic", "kh", "kv")]
        assert not read, read
        names = [getattr(n.func, "id", "") for n in ast.walk(fn)
                 if isinstance(n, ast.Call)]
        assert names.count("required_force_of_result") == 1, names
        assert "required_force" not in names
        assert "results_are_current" in [
            getattr(n.func, "attr", "") for n in ast.walk(fn)
            if isinstance(n, ast.Call)]

    def test_the_main_window_hands_over_the_fingerprint(self):
        tree = ast.parse((_ROOT / "ogr_gui" / "main_window.py")
                         .read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "act_interpret")
        call = next(n for n in ast.walk(fn) if isinstance(n, ast.Call)
                    and getattr(n.func, "id", "") == "InterpretWindow")
        assert "model_fingerprint" in [k.arg for k in call.keywords]
