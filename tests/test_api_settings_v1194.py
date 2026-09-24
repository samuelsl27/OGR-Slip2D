# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — a setting is either applied and felt, or refused.

Invariants protected:

1. **Nothing is accepted in silence.** The settings are dataclasses, which
   accept a misspelled attribute as a new one; an unknown
   ``search_method`` runs a Grid Search. Through ``settings_set`` an
   unknown field, a retired field, a value outside a field's choices, a
   2.5 for an integer or a NaN is REFUSED, with a suggestion.
2. **A batch is all or nothing.** One bad entry leaves the model exactly as
   it was (``to_dict`` identical), so a caller never has to work out which
   half of its request landed.
3. **Rules between two settings hold**: a search that cannot run on the
   surface type, a lone grid bound (read by nothing — the engine falls back
   to automatic when either bound is missing), a factor on a named design
   standard, the three mutually exclusive groundwater options.
4. **Every string setting is classified** — choices, free text, complex or
   read-only. A string field nobody classified accepts anything, which is
   how the two above happen; this file fails when a new one appears.
5. **Rule 7: what is set moves the number.** The slice count, the design
   standard and the method list each change the answer they should change,
   on a published circle.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import test_acads_validation_v178 as acads  # noqa: E402


def _ws_with_acads():
    from ogr_api import Workspace, call

    ws = Workspace()
    pid = call(ws, "project_new", name="ACADS")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                     [20, 25]],
        "materials": [{"name": "Soil", "unit_weight": 20.0, "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": 3.0, "friction_angle": 19.6}}}]})
    return ws, pid


def _raised(exc_type, fn):
    """The exception ``fn`` raises. The runner's ``pytest.raises`` yields
    nothing, so a test that needs to READ the message catches it here."""
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"expected {exc_type.__name__}, nothing raised")


def _snapshot(ws, pid) -> str:
    return json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                      default=str)


def _set(ws, pid, changes):
    from ogr_api import call
    return call(ws, "settings_set", project_id=pid, changes=changes)


#: A circle through the ACADS slope (centre and radius of its critical
#: circle as found by the grid of test_api_validation_v1194).
_CIRCLE = {"type": "circle", "centre_x": 29.07, "centre_y": 55.495,
           "radius": 30.495637}


def _fos(ws, pid, methods=("bishop_simplified",)):
    from ogr_api import call
    out = call(ws, "surface_evaluate", project_id=pid, surface=_CIRCLE,
               methods=list(methods))
    return out


# ======================================================================
class TestNothingIsAcceptedInSilence:
    def test_a_misspelled_field_is_refused_with_the_right_suggestion(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            exc = _raised(InvalidArgument, lambda: _set(
                ws, pid, {"search.search_metod": "slope"}))
            assert "search_method" in str(exc)
        finally:
            ws.shutdown()

    def test_an_unknown_section_is_refused(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            exc = _raised(InvalidArgument, lambda: _set(
                ws, pid, {"serch.search_method": "slope"}))
            assert "'search'" in str(exc)
        finally:
            ws.shutdown()

    def test_a_retired_field_names_its_replacement(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            text = str(_raised(InvalidArgument, lambda: _set(
                ws, pid, {"search.path_num_paths": 100})))
            assert "path_num_surfaces" in text and "v0.1.103" in text
        finally:
            ws.shutdown()

    def test_a_value_outside_the_choices_is_refused(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            exc = _raised(InvalidArgument, lambda: _set(
                ws, pid, {"search.search_method": "slop"}))
            assert "'slope'" in str(exc)
            with pytest.raises(InvalidArgument):
                _set(ws, pid, {"methods.enabled_methods":
                               ["bishop_simplified", "bishopp"]})
        finally:
            ws.shutdown()

    def test_types_are_not_guessed(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            for bad in ({"methods.num_slices": 2.5},
                        {"advanced.check_m_alpha": 1},
                        {"methods.tolerance": float("nan")},
                        {"methods.tolerance": "abc"}):
                with pytest.raises(InvalidArgument):
                    _set(ws, pid, bad)
            out = _set(ws, pid, {"methods.num_slices": 30.0})
            assert out["changed"]["methods.num_slices"]["new"] == 30
            assert isinstance(
                ws.get(pid).project.settings.methods.num_slices, int)
        finally:
            ws.shutdown()

    def test_ranges_that_follow_from_the_quantity(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            for bad in ({"methods.tolerance": 0.0},
                        {"methods.num_slices": 0},
                        {"design_standard.standard": "custom",
                         "design_standard.factor_cohesion": 50.0}):
                with pytest.raises(InvalidArgument):
                    _set(ws, pid, bad)
        finally:
            ws.shutdown()

    def test_an_enum_field_takes_its_value_or_its_name(self):
        ws, pid = _ws_with_acads()
        try:
            from ogr_core.project import FailureDirection
            _set(ws, pid, {"units.failure_direction": "L2R"})
            fd = ws.get(pid).project.settings.units.failure_direction
            assert fd is FailureDirection.LEFT_TO_RIGHT
            _set(ws, pid, {"units.failure_direction": "right_to_left"})
            fd = ws.get(pid).project.settings.units.failure_direction
            assert fd is FailureDirection.RIGHT_TO_LEFT
        finally:
            ws.shutdown()


class TestABatchIsAllOrNothing:
    def test_one_bad_entry_changes_nothing(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            before = _snapshot(ws, pid)
            with pytest.raises(InvalidArgument):
                _set(ws, pid, {"methods.num_slices": 40,
                               "search.search_metod": "slope"})
            assert _snapshot(ws, pid) == before
            assert ws.get(pid).stack.history()[0] == ["Define model"]
        finally:
            ws.shutdown()

    def test_a_good_batch_is_one_undo_step(self):
        from ogr_api import call
        ws, pid = _ws_with_acads()
        try:
            before = _snapshot(ws, pid)
            _set(ws, pid, {"methods.num_slices": 40,
                           "search.search_method": "slope"})
            assert _snapshot(ws, pid) != before
            call(ws, "project_history", project_id=pid, action="undo")
            assert _snapshot(ws, pid) == before
        finally:
            ws.shutdown()

    def test_the_live_settings_object_is_kept(self):
        """Committed field by field, so a reference held to the settings
        (the interface's, from phase F4) sees the change."""
        ws, pid = _ws_with_acads()
        try:
            live = ws.get(pid).project.settings
            _set(ws, pid, {"methods.num_slices": 33})
            assert ws.get(pid).project.settings is live
            assert live.methods.num_slices == 33
        finally:
            ws.shutdown()


class TestRulesBetweenTwoSettings:
    def test_a_search_that_cannot_run_on_the_surface_type(self):
        from ogr_api import Conflict
        ws, pid = _ws_with_acads()
        try:
            with pytest.raises(Conflict):
                _set(ws, pid, {"search.search_method": "block"})
            out = _set(ws, pid, {"search.surface_type": "non_circular",
                                 "search.search_method": "block"})
            assert set(out["changed"]) == {"search.surface_type",
                                           "search.search_method"}
        finally:
            ws.shutdown()

    def test_a_lone_grid_bound_is_refused(self):
        from ogr_api import Conflict
        ws, pid = _ws_with_acads()
        try:
            with pytest.raises(Conflict):
                _set(ws, pid, {"search.grid_x_min": 10.0})
            with pytest.raises(Conflict):
                _set(ws, pid, {"search.grid_x_min": 10.0,
                               "search.grid_x_max": 5.0})
        finally:
            ws.shutdown()

    def test_a_factor_only_with_the_custom_standard(self):
        from ogr_api import Conflict
        ws, pid = _ws_with_acads()
        try:
            with pytest.raises(Conflict):
                _set(ws, pid, {"design_standard.factor_cohesion": 1.3})
            out = _set(ws, pid, {"design_standard.standard": "custom",
                                 "design_standard.factor_cohesion": 1.3})
            ds = ws.get(pid).project.settings.design_standard
            assert ds.standard == "custom" and ds.factor_cohesion == 1.3
            assert "design_standard.factor_cohesion" in out["changed"]
        finally:
            ws.shutdown()

    def test_a_named_standard_loads_its_own_factors(self):
        from ogr_core.project.settings import DesignStandardSettings
        ws, pid = _ws_with_acads()
        try:
            _set(ws, pid, {"design_standard.enabled": True,
                           "design_standard.standard": "eurocode7_da1c2"})
            ds = ws.get(pid).project.settings.design_standard
            want = DesignStandardSettings.PRESETS["eurocode7_da1c2"]
            assert (ds.factor_permanent, ds.factor_variable,
                    ds.factor_cohesion, ds.factor_friction,
                    ds.factor_unit_weight, ds.factor_resistance) == want
        finally:
            ws.shutdown()

    def test_the_groundwater_options_are_exclusive(self):
        from ogr_api import InvalidArgument
        ws, pid = _ws_with_acads()
        try:
            with pytest.raises(InvalidArgument):
                _set(ws, pid, {"groundwater.rapid_drawdown": True})
            _set(ws, pid, {"groundwater.advanced_option": "rapid_drawdown"})
            gw = ws.get(pid).project.settings.groundwater
            assert gw.advanced_option() == "rapid_drawdown"
            _set(ws, pid, {"groundwater.advanced_option": "transient"})
            assert (gw.transient, gw.rapid_drawdown,
                    gw.excess_pore_pressure) == (True, False, False)
        finally:
            ws.shutdown()


class TestEveryStringSettingIsClassified:
    def test_no_string_field_is_left_unclassified(self):
        from ogr_core.project.settings import ProjectSettings
        from ogr_api import settings_schema as S

        known = (set(S.CHOICES) | set(S.DYNAMIC_CHOICES) | S.FREE_TEXT
                 | S.COMPLEX | S.READONLY)
        loose = [p for p, _ in S.all_string_fields(ProjectSettings())
                 if p not in known]
        assert not loose, (
            "String settings with no classification (add each to CHOICES, "
            f"FREE_TEXT, COMPLEX or READONLY in ogr_api/settings_schema.py):"
            f" {loose}")

    def test_the_classification_names_only_real_fields(self):
        """A classification that outlived its field would be a dead entry
        that no test notices; every path must still resolve. (COMPLEX may
        name a non-string field — ``transient_initial_bcs`` is a dict.)"""
        from ogr_core.project.settings import ProjectSettings
        from ogr_api import settings_schema as S
        from ogr_api.coerce import resolve_field

        s = ProjectSettings()
        strings = {p for p, _ in S.all_string_fields(s)}
        for path in set(S.CHOICES) | set(S.DYNAMIC_CHOICES) | S.FREE_TEXT:
            assert path in strings, f"{path} is not a string field"
        for path in S.COMPLEX:
            resolve_field(s, path)

    def test_every_default_is_one_of_its_own_choices(self):
        """A default outside its own list would make a fresh model refuse
        to have that setting re-set to what it already is."""
        from ogr_core.project.settings import ProjectSettings
        from ogr_api import settings_schema as S
        from ogr_api.coerce import resolve_field

        s = ProjectSettings()
        for path, choices in S.CHOICES.items():
            parent, name, _ = resolve_field(s, path)
            value = getattr(parent, name)
            values = value if isinstance(value, list) else [value]
            options = choices()
            assert options, path
            for v in values:
                assert v in options, (path, v, options)


class TestWhatIsSetMovesTheNumber:
    def test_the_slice_count(self):
        ws, pid = _ws_with_acads()
        try:
            a = _fos(ws, pid)["methods"]["bishop_simplified"]["fos"]
            _set(ws, pid, {"methods.num_slices": 8})
            b = _fos(ws, pid)["methods"]["bishop_simplified"]
            assert b["n_slices"] == 8
            assert abs(a - b["fos"]) > 1e-4, (a, b["fos"])
        finally:
            ws.shutdown()

    def test_the_design_standard(self):
        ws, pid = _ws_with_acads()
        try:
            plain = _fos(ws, pid)
            _set(ws, pid, {"design_standard.enabled": True,
                           "design_standard.standard": "eurocode7_da1c2"})
            factored = _fos(ws, pid)
            assert plain["factor_report"]["applied"] is False
            assert factored["factor_report"]["applied"] is True
            a = plain["methods"]["bishop_simplified"]["fos"]
            b = factored["methods"]["bishop_simplified"]["fos"]
            # DA1-C2 divides tan(phi) and c by 1.25: the over-design factor
            # is necessarily LOWER than the factor of safety.
            assert b < a - 1e-3, (a, b)
        finally:
            ws.shutdown()

    def test_the_method_list_is_what_runs(self):
        ws, pid = _ws_with_acads()
        try:
            _set(ws, pid, {"methods.enabled_methods":
                           ["spencer", "ordinary_fellenius"]})
            from ogr_api import call
            out = call(ws, "surface_evaluate", project_id=pid,
                       surface=_CIRCLE)
            assert set(out["methods"]) == {"spencer", "ordinary_fellenius"}
            assert all(math.isfinite(m["fos"])
                       for m in out["methods"].values())
        finally:
            ws.shutdown()

    def test_settings_get_offers_the_choices(self):
        from ogr_api import call
        ws, pid = _ws_with_acads()
        try:
            out = call(ws, "settings_get", project_id=pid, section="search")
            sm = out["settings"]["search"]["search_method"]
            assert "particle_swarm" in sm["choices"]
            assert sm["value"] == "grid"
        finally:
            ws.shutdown()


def test_the_published_constants_are_the_ones_imported():
    """Keeps this file honest about where its circle came from."""
    assert acads._MEAN_33 == 0.991
