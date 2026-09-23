# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.192 — a Material built in code with its pore-pressure model written as
a string gets the same slope as the same Material loaded from disk.

THE INVARIANT. The constructor and the ``.ogr`` loader must agree. The
loader always converted (``PorePressureType(data.get("pore_pressure",
"none"))``); the constructor stored whatever it was given (defect D154). With
``pore_pressure="water_table"`` the attribute stayed a ``str``, every
``== PorePressureType.WATER_TABLE`` in the pore-pressure code compared False,
and the material was evaluated DRY — no exception, no warning, a plausible
number. Measured on the published circle of problem 059 with Spencer (the
slope this file borrows), on the v0.1.191 tree: 1.0886079707982514 with the
string against 0.5592600533686025 with the enum, +94.6 % — and the string's
number is BIT FOR BIT the factor this tree gives with ``NONE``, so "dry" is
not a figure of speech. (The defect report quotes 1.0886090318268722, taken
on v0.1.180; the 1e-6 between the two is engine drift across eleven
versions and moves the wet number not at all.) And ``to_dict`` then raised
``AttributeError`` on ``.value``, so the project broke on SAVING, after it had
already been analysed with the wrong number.

``Material.__setattr__`` now converts ``pore_pressure`` whenever it is
written, which covers the constructor (a dataclass ``__init__`` assigns
through ``setattr``) and every later assignment, where a ``__post_init__``
would have left the door open. The conversion is ``PorePressureType(value)``,
the loader's own, so it is not a new rule: a valid string works, a member is
returned as itself, and anything else fails with ``ValueError`` where it is
written.

THE ANCHOR is the loader, not a number: every assertion on a factor of safety
here is an identity between two doors — string vs enum, and code vs
``to_dict``/``from_dict`` through JSON — plus one control that the case can
tell a dry slope from a wet one at all. No value is compared against what
this code printed on some day.

WHAT THIS FILE DOES NOT CLAIM. Six other classes have the same hole
(``SupportInstance``/``SupportPattern``, ``TensionCrackProperties``,
``DistributedLoad``/``LineLoad``, ``HydraulicProperties``); they are censused
in ``docs/audits/enum_coercion_census_v1192.md`` and reported as D183, not
fixed here.

WHAT THIS FILE DISCRIMINATES against the v0.1.191 tree. MEASURED, by copying
this file into a ``git worktree`` at that commit and running it there. Of
the 11 cases, **10 fail and 1 passes**. All ten fail on behaviour — a string
stored as a string, a number that comes out dry, an ``AttributeError`` from
``to_dict`` — and none on the absence of a symbol. The one that passes is
``the_case_can_tell_dry_from_wet``, BY DESIGN: it is the control that the
case discriminates at all, and it compares two enums, which v0.1.191 handled
correctly.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_CACHE: dict = {}


def _material(pore_pressure):
    from ogr_core.materials import Material, MohrCoulomb
    return Material(name="x", unit_weight=19.0,
                    strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0),
                    pore_pressure=pore_pressure)


def _fos(project):
    """The published circle of problem 059 through the search's own door
    (see ``test_lambda_closure_v1180._evaluate`` for why that door)."""
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle
    from test_lambda_closure_v1180 import CIRCULO
    res = build_search(project, "spencer").evaluate_surface(
        project, SlipCircle(*CIRCULO))
    assert res is not None and res.is_valid, getattr(res, "error_message", "")
    return res.fos


def _slope_with(pore_pressure, door):
    """Problem 059 with its sand's model set to ``pore_pressure``, either
    through the constructor (``dataclasses.replace`` calls ``__init__``) or
    by assigning the attribute after construction."""
    from test_lambda_closure_v1180 import _slope
    p = _slope()
    sand = p.materials[0]
    if door == "constructor":
        p.materials = [dataclasses.replace(sand, pore_pressure=pore_pressure)]
    elif door == "assignment":
        sand.pore_pressure = pore_pressure
    else:
        raise ValueError(door)
    return p


def _cached_fos(key, build):
    if key not in _CACHE:
        _CACHE[key] = _fos(build())
    return _CACHE[key]


# ======================================================================
class TestTheStringBecomesTheModel:

    def test_the_constructor_converts_a_valid_string(self):
        from ogr_core.materials import PorePressureType
        m = _material("water_table")
        assert m.pore_pressure is PorePressureType.WATER_TABLE

    def test_an_assignment_converts_too(self):
        from ogr_core.materials import PorePressureType
        m = _material(PorePressureType.NONE)
        m.pore_pressure = "ru"
        assert m.pore_pressure is PorePressureType.RU_COEFFICIENT

    def test_every_member_by_value_and_by_itself(self):
        """Idempotent on members, and every stored value a file can carry
        is accepted — the loader's contract, member by member."""
        from ogr_core.materials import Material, PorePressureType
        for t in PorePressureType:
            assert _material(t.value).pore_pressure is t, t
            assert _material(t).pore_pressure is t, t
            loaded = Material.from_dict(_material(t).to_dict())
            assert loaded.pore_pressure is _material(t.value).pore_pressure

    def test_to_dict_and_the_tooltip_never_raise(self):
        from ogr_core.materials import PorePressureType
        for t in PorePressureType:
            m = _material(t.value)
            assert m.to_dict()["pore_pressure"] == t.value
            assert isinstance(m.tooltip_html(), str)


# ======================================================================
class TestAWrongNameFailsWhereItIsWritten:

    #: ``piezo_line`` is the realistic mistake: it is the value of
    #: ``GroundwaterMethod.PIEZO_LINE`` in the settings, while the material's
    #: member is spelled ``piezometric``. ``WATER_TABLE`` is the member's
    #: NAME, not its value.
    WRONG = ("WATER_TABLE", "piezo_line", "", "dry", None)

    def test_an_invalid_value_fails_in_the_constructor(self):
        for bad in self.WRONG:
            try:
                _material(bad)
            except ValueError:
                continue
            raise AssertionError(f"{bad!r} was accepted by the constructor")

    def test_an_invalid_assignment_fails_and_leaves_the_old_value(self):
        from ogr_core.materials import PorePressureType
        m = _material(PorePressureType.PIEZO_LINE)
        for bad in self.WRONG:
            try:
                m.pore_pressure = bad
            except ValueError:
                assert m.pore_pressure is PorePressureType.PIEZO_LINE
                continue
            raise AssertionError(f"{bad!r} was accepted by assignment")

    def test_a_copy_still_goes_through_the_door(self):
        """``deepcopy`` and ``pickle`` restore ``__dict__`` without calling
        ``__setattr__`` — the search ships projects to worker processes that
        way — so a converted member must travel as a member."""
        import copy
        import pickle
        from ogr_core.materials import PorePressureType
        m = _material("fem")
        for clone in (copy.deepcopy(m), pickle.loads(pickle.dumps(m))):
            assert clone.pore_pressure is PorePressureType.FEM_SEEPAGE


# ======================================================================
class TestTheSlopeIsNotDry:
    """Problem 059 without its support, the published circle, Spencer."""

    def test_the_constructor_with_a_string_equals_the_enum(self):
        from ogr_core.materials import PorePressureType
        enum = _cached_fos(("constructor", "enum"), lambda: _slope_with(
            PorePressureType.WATER_TABLE, "constructor"))
        text = _cached_fos(("constructor", "text"), lambda: _slope_with(
            "water_table", "constructor"))
        assert text == enum, (text, enum)

    def test_an_assignment_with_a_string_equals_the_enum(self):
        from ogr_core.materials import PorePressureType
        enum = _cached_fos(("constructor", "enum"), lambda: _slope_with(
            PorePressureType.WATER_TABLE, "constructor"))
        text = _cached_fos(("assignment", "text"), lambda: _slope_with(
            "water_table", "assignment"))
        assert text == enum, (text, enum)

    def test_the_code_built_model_equals_the_loaded_one(self):
        """The anchor of the whole file: the same model through
        ``to_dict`` -> JSON -> ``from_dict``, which is what the bank and
        the interface read, gives the same factor as the one built in
        code with a string. Before v0.1.192 ``to_dict`` raised here."""
        from ogr_core.project import Project
        built = _slope_with("water_table", "constructor")
        loaded = Project.from_dict(json.loads(json.dumps(built.to_dict())))
        assert _fos(loaded) == _cached_fos(
            ("constructor", "text"),
            lambda: _slope_with("water_table", "constructor"))

    def test_the_case_can_tell_dry_from_wet(self):
        """Guard on the guard: if the water table did not reach the slip
        mass, the three identities above would hold for a dry slope too
        and prove nothing. The dry factor is what the string used to give."""
        from ogr_core.materials import PorePressureType
        wet = _cached_fos(("constructor", "enum"), lambda: _slope_with(
            PorePressureType.WATER_TABLE, "constructor"))
        dry = _cached_fos(("constructor", "none"), lambda: _slope_with(
            PorePressureType.NONE, "constructor"))
        assert dry > 1.5 * wet, (dry, wet)
