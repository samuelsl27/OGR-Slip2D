# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.401 (D386) — a setting that says HOW a calculation runs, not WHAT it
computes, does not make a result stale.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.397 (DUDA 4): ticking or unticking «Buscar
superficies en paralelo» left the result marked «de un modelo anterior»,
with factors bit-identical in series and in parallel. ``model_hash`` hashed
the whole ``to_dict`` except the annotations, and that includes
``settings.advanced.parallel_search`` and ``parallel_cpu_percent``.

That a split grid is the sequential one is an invariant of the engine: the
batches are contiguous and are put back in submission order
(``test_parallel_search_v197``). The bench's ``version_serie`` checked it 12
of 12 in every version of phase 3 of the compute audit and in 0.1.399. The
owner's decision (2026-11-01): the two settings stay out of the fingerprint
of a result. The window and the API both ask ``model_hash``, so both agree.

1. **The two keys do not move ``model_hash``.** They still move
   ``document_hash``, because they are saved in the ``.ogr`` and a change
   asks to be saved. They are where the rule expects them: a rename would
   leave the rule on a key that no longer exists, so the test checks that
   both are in ``to_dict``.
2. **Every other setting of ``advanced`` moves ``model_hash``.** A census
   over the fields, so that a new setting cannot slip out of the fingerprint
   unnoticed.
3. **In the window,** after a Compute, toggling either keeps the result
   current, and another setting of ``advanced`` marks it stale.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MODE = ("parallel_search", "parallel_cpu_percent")


def _changed(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.5
    raise AssertionError("a setting of a type the census cannot change: %r"
                         % (value,))


class TestTheFingerprintOfAResult:
    """Invariants 1 and 2."""

    def test_the_computation_mode_is_left_out(self):
        from ogr_api.snapshot import document_hash, model_hash
        from ogr_core.project import Project
        p = Project()
        saved = p.to_dict()["settings"]["advanced"]
        for key in _MODE:
            assert key in saved, "the rule names %s, which is not saved" % key
        for key in _MODE:
            model, document = model_hash(p), document_hash(p)
            adv = p.settings.advanced
            setattr(adv, key, _changed(getattr(adv, key)))
            assert model_hash(p) == model, "%s made the result stale" % key
            assert document_hash(p) != document, (
                "%s no longer asks to be saved" % key)

    def test_every_other_advanced_setting_is_in(self):
        from dataclasses import fields
        from ogr_api.snapshot import model_hash
        from ogr_core.project import Project
        p = Project()
        adv = p.settings.advanced
        saved = p.to_dict()["settings"]["advanced"]
        others = [f.name for f in fields(adv) if f.name not in _MODE]
        assert others
        for name in others:
            assert name in saved, "%s is not saved" % name
            before = model_hash(p)
            value = getattr(adv, name)
            setattr(adv, name, _changed(value))
            try:
                assert model_hash(p) != before, (
                    "%s does not make a result stale" % name)
            finally:
                setattr(adv, name, value)


class TestTheWindow:
    """Invariant 3."""

    def test_toggling_the_mode_keeps_the_result_current(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.main_window import MainWindow
        from ogr_slip2d.analysis_runner import run_analysis
        QApplication.instance() or QApplication([])
        w = MainWindow()
        try:
            p = build_demo_project()
            p.settings.search.grid_nx = p.settings.search.grid_ny = 2
            p.settings.search.radius_increment = 2
            w._attach_project(p)
            w._on_compute_done(
                run_analysis(w.project, ["bishop_simplified"]).results)
            adv = w.project.settings.advanced
            for key in _MODE:
                setattr(adv, key, _changed(getattr(adv, key)))
                w._check_results_stale()
                assert w.results_dock.is_stale() is False, (
                    "%s made the result stale" % key)
            adv.check_m_alpha = not adv.check_m_alpha
            w._check_results_stale()
            assert w.results_dock.is_stale() is True
        finally:
            w.project.is_dirty = False
            w.close()
            w.deleteLater()
