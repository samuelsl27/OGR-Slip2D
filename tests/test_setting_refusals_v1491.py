# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.491 (D429, the engine's part) -- a search or a sampling method this
build does not know is refused with its code, not run as another one.

Invariant protected: ``check_analysis_settings`` refuses a
``search_method`` outside ``SearchMethod`` (``setting.search_unknown``)
and, with the probabilistic analysis on, a ``sampling_method`` outside
``SamplingMethod`` (``setting.sampling_unknown``); ``build_search`` no
longer has an "any other value" branch; and every value of the two
enumerations is NOT refused. The reference is the enumerations of the
core, not a capture.

Why. ``build_search`` ended in "Default = Grid Search", so
``"future_search"`` -- a file of a newer version, or a typo -- ran a Grid
Search, and ``run_configured_statistics`` caught the ``ValueError`` of an
unknown sampling and ran Monte Carlo. Rule 7: the file's value changed the
analysis that ran without changing what anyone was told. The bank holds
none (census of 2026-11-24: 0 of 30 800 ``.ogr``), so no row moves.
"""
from __future__ import annotations

import contextlib

_PROJECT = None


def _demo():
    """The demo project, built once: a search refusal does not need a run."""
    global _PROJECT
    if _PROJECT is None:
        from ogr_core.project.demo import build_demo_project
        _PROJECT = build_demo_project()
    return _PROJECT


@contextlib.contextmanager
def _setting(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def _codes(project):
    from ogr_slip2d.analysis_runner import check_analysis_settings
    return [getattr(p, "code", None) for p in check_analysis_settings(project)]


class TestTheSearch:
    def test_an_unknown_search_is_refused_with_its_code(self):
        p = _demo()
        with _setting(p.settings.search, "search_method", "future_search"):
            from ogr_slip2d.analysis_runner import check_analysis_settings
            problems = check_analysis_settings(p)
            hits = [x for x in problems
                    if getattr(x, "code", None) == "setting.search_unknown"]
            assert len(hits) == 1, problems
            text = str(hits[0])
            assert "'future_search'" in text
            from ogr_core.project.settings import SearchMethod
            for m in SearchMethod:
                assert m.value in text, m

    def test_build_search_has_no_default_branch(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _demo()
        with _setting(p.settings.search, "search_method", "future_search"):
            try:
                build_search(p, "bishop_simplified")
            except ValueError as exc:
                assert getattr(exc.args[0], "code", None) == \
                    "setting.search_unknown"
            else:
                raise AssertionError("an unknown search was built")

    def test_every_known_search_is_not_refused(self):
        from ogr_core.project.settings import SearchMethod
        p = _demo()
        for m in SearchMethod:
            with _setting(p.settings.search, "search_method", m.value):
                assert "setting.search_unknown" not in _codes(p), m

    def test_grid_still_builds_a_grid_search(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import GridSearch
        p = _demo()
        with _setting(p.settings.search, "search_method", "grid"):
            assert isinstance(build_search(p, "bishop_simplified"), GridSearch)


class TestTheSampling:
    def test_an_unknown_sampling_is_refused_with_its_code(self):
        st = _demo().settings.statistics
        with _setting(st, "probabilistic_analysis", True), \
                _setting(st, "sampling_method", "future_sampling"):
            assert _codes(_demo()).count("setting.sampling_unknown") == 1

    def test_it_is_not_asked_without_the_probabilistic_analysis(self):
        """The one run that reads it: a deterministic analysis does not
        sample, so it is not refused for it."""
        st = _demo().settings.statistics
        with _setting(st, "probabilistic_analysis", False), \
                _setting(st, "sampling_method", "future_sampling"):
            assert "setting.sampling_unknown" not in _codes(_demo())

    def test_every_known_sampling_is_not_refused(self):
        from ogr_core.statistics import SamplingMethod
        st = _demo().settings.statistics
        for m in SamplingMethod:
            with _setting(st, "probabilistic_analysis", True), \
                    _setting(st, "sampling_method", m.value):
                assert "setting.sampling_unknown" not in _codes(_demo()), m

    def test_the_statistics_run_refuses_it(self):
        from ogr_slip2d.analysis_runner import (AnalysisNotConfigured,
                                                run_configured_statistics)
        st = _demo().settings.statistics
        with _setting(st, "probabilistic_analysis", True), \
                _setting(st, "sampling_method", "future_sampling"):
            try:
                run_configured_statistics(_demo())
            except AnalysisNotConfigured as exc:
                codes = [getattr(x, "code", None) for x in exc.problems]
                assert "setting.sampling_unknown" in codes, codes
            else:
                raise AssertionError("an unknown sampling ran")


class TestInSpanish:
    def test_both_refusals_name_the_values_by_their_labels(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        from ogr_slip2d import setting_messages as SM
        old = current_language()
        set_language("es")
        try:
            search = note_text(SM.setting_note(
                SM.SEARCH_UNKNOWN, method="future_search",
                available="grid, path"))
            sampling = note_text(SM.setting_note(
                SM.SAMPLING_UNKNOWN, method="future_sampling",
                available="monte_carlo, latin_hypercube"))
        finally:
            set_language(old)
        assert search.startswith("«future_search» no es un método de "
                                 "búsqueda"), search
        assert "Disponibles:" in search and "path" not in search, search
        assert sampling.endswith("Disponibles: Monte Carlo; Hipercubo "
                                 "latino."), sampling
