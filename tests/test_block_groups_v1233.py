# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.233 — Multiple Groups: each Group ID of the drawn Block
Search objects is searched on its own. Defect D99.

**The invariant** is the reference's own description, item by item: with
the Multiple Groups box on, «the Block Search will be carried out
independently for EACH GROUP of Block Search objects»; «a group may consist
of a single block search object, or multiple block search objects with the
same Group ID»; and «the total number of surfaces specified for the Block
Search is divided equally among the number of groups». Its documented use
is several weak layers at once, one Block Search Polyline per layer, each
with its own Group ID.

**What was wrong.** OGR had no group id on a Block Search object and stitched
a point of EVERY drawn object into one surface — the reference's behaviour
with no groups, permanently. Two polylines in two weak layers could not be
searched as two mechanisms, and since a polyline may not be overlapped in x
by another object, they could not even be drawn together. A boolean called
``block_multiple_groups`` sat in every .ogr until v0.1.156 claiming the
function and doing nothing; it comes back here with the meaning.

**What is asserted, and against what.** There is no published number for a
synthetic two-layer model, so the anchors are identities the reference's
description fixes:

* the budget identity — two groups of N candidates each get N/2, the
  remainder to the first, and ``attempts == N`` still;
* the membership identity — every surface of a group carries vertices of
  its own layer only (the closure criterion of D99, verbatim: «the critical
  surface of each family uses only the objects of its group»);
* the one-group identity — with every object in one group, the run is the
  run without groups DRAW FOR DRAW (same candidates, same factors), so no
  model written before this version moves.

Rule 7: the box moves the number on a model where it can (two objects
that do not overlap: off, every surface has vertices from both; on, each
family from its own).

COST. A synthetic slope with two thin weak layers; seven Block Searches of
60–81 candidates (Bishop), a few rule and file checks, one dialog. About
fifteen seconds.
"""
from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


#: The two weak layers (their mid-planes): 0.5 m thick bands of c = 0,
#: phi = 12 deg inside a c = 20, phi = 30 deg slope.
_UPPER, _LOWER = 14.5, 7.5
_N = 60
_CACHE: dict = {}


def _model(multiple, ids=(1, 2), overlap=True, n=_N):
    """A slope with two weak layers and one Block Search Polyline in each.

    ``overlap`` puts the two polylines over the same x-range — the
    reference's use case, legal only in different groups — or side by side,
    where the box off is legal too and the rule-7 comparison can be made.
    """
    from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec, Boundary,
                                   BoundaryType, Polyline, Vertex)
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("D99")
    ext = Polyline(vertices=[Vertex(*v) for v in (
        (0, 0), (100, 0), (100, 40), (60, 40), (30, 20), (0, 20))],
        closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    for y in (7.0, 8.0, 14.0, 15.0):
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, y), Vertex(100, y)], closed=False),
            btype=BoundaryType.MATERIAL))
    soil = Material(name="soil", unit_weight=19.0,
                    strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0))
    weak = Material(name="weak", unit_weight=19.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=12.0))
    p.materials = [soil, weak]
    p.resolve_regions()
    for y, m in ((3.0, soil), (_LOWER, weak), (11.0, soil), (_UPPER, weak),
                 (18.0, soil)):
        p.assign_material_at(50.0, y, m.id)
    p.assign_material_at(80.0, 30.0, soil.id)
    spans = (((20.0, 70.0), (15.0, 80.0)) if overlap else
             ((22.0, 45.0), (50.0, 80.0)))
    for (y, (x0, x1), g) in ((_UPPER, spans[0], ids[0]),
                             (_LOWER, spans[1], ids[1])):
        b = Boundary(polyline=Polyline(
            vertices=[Vertex(x0, y), Vertex(x1, y)], closed=False),
            btype=BoundaryType.BLOCK_SEARCH_OBJECT)
        b.block_object = BlockObjectSpec(BlockObjectKind.POLYLINE, group_id=g)
        p.add_boundary(b)
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "block"
    s.block_num_surfaces = n
    s.block_multiple_groups = multiple
    return p


def _run(key, **kw):
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        p = _model(**kw)
        _CACHE[key] = build_search(p, "bishop_simplified").run(p)
    return _CACHE[key]


def _layers(surface):
    """Which weak layers a surface has vertices on."""
    ys = {round(v.y, 6) for v in surface.polyline.vertices}
    return {y for y in (_UPPER, _LOWER) if y in ys}


def _factors(result):
    return [None if e.fos is None else round(e.fos, 12)
            for e in result.evaluations]


# ======================================================================
class TestEachGroupIsSearchedOnItsOwn:
    """D99's closure criterion: two polylines over two weak layers with
    different Group IDs give two families, half the budget each, and every
    surface of a family uses only the objects of its group."""

    def test_the_budget_is_divided_equally(self):
        r = _run("on", multiple=True)
        assert r.attempts == _N
        assert [g["budget"] for g in r.block_groups] == [_N // 2, _N // 2]
        assert [g["group_id"] for g in r.block_groups] == [1, 2]

    def test_an_odd_budget_gives_the_remainder_to_the_first_group(self):
        r = _run("odd", multiple=True, n=81)
        assert r.attempts == 81
        assert [g["budget"] for g in r.block_groups] == [41, 40]

    def test_every_surface_uses_only_its_own_layer(self):
        r = _run("on", multiple=True)
        own = {1: _UPPER, 2: _LOWER}
        seen = {1: 0, 2: 0}
        for e in r.evaluations:
            g = e.surface.block_group
            assert g in own, g
            assert _layers(e.surface) <= {own[g]}, (g, _layers(e.surface))
            seen[g] += 1
        assert seen[1] and seen[2], seen

    def test_a_family_runs_along_its_layer(self):
        """The polyline's stretch: at least two vertices on the layer, so
        the surface FOLLOWS it between its two points (D109) in each
        family."""
        r = _run("on", multiple=True)
        for g, y in ((1, _UPPER), (2, _LOWER)):
            fam = [e for e in r.evaluations if e.surface.block_group == g
                   and e.is_valid]
            assert fam, g
            assert any(sum(1 for v in e.surface.polyline.vertices
                           if abs(v.y - y) < 1e-9) >= 2 for e in fam), g

    def test_the_critical_is_the_lowest_of_the_groups(self):
        r = _run("on", multiple=True)
        mins = [g["min_fos"] for g in r.block_groups]
        assert all(m is not None for m in mins), mins
        c = r.critical
        assert abs(c.fos - min(mins)) < 1e-12
        best = r.block_groups[mins.index(min(mins))]["group_id"]
        assert c.surface.block_group == best


class TestOneGroupIsTheSearchWithoutGroups:
    """The identity that keeps every model written before this version
    where it was: one group holds every object in model order, and the
    random stream is consumed exactly as before."""

    def test_the_same_id_is_the_box_off_draw_for_draw(self):
        off = _run("side_off", multiple=False, overlap=False)
        same = _run("side_same", multiple=True, ids=(4, 4), overlap=False)
        assert _factors(same) == _factors(off)
        assert same.attempts == off.attempts

    def test_the_box_off_ignores_the_ids(self):
        off = _run("side_off", multiple=False, overlap=False)
        ids = _run("side_off_ids", multiple=False, ids=(1, 2), overlap=False)
        assert _factors(ids) == _factors(off)
        assert ids.block_groups == []
        assert all(e.surface.block_group is None for e in ids.evaluations)


class TestRule7TheBoxMovesTheNumber:

    def test_on_and_off_differ_where_they_can(self):
        """Side by side, the box off stitches both layers into every
        surface; on, each family has one. Different populations, different
        minimum — and the surfaces say which."""
        off = _run("side_off", multiple=False, overlap=False)
        on = _run("side_on", multiple=True, overlap=False)
        assert round(off.min_fos, 9) != round(on.min_fos, 9)
        assert any(_layers(e.surface) == {_UPPER, _LOWER}
                   for e in off.evaluations if e.is_valid)
        assert all(len(_layers(e.surface)) <= 1 for e in on.evaluations)


class TestTheOverlapRuleIsPerGroup:
    """The reference forbids overlapping the x-range of a polyline, and
    groups are how it lets two weak layers be searched at once."""

    def test_different_groups_may_overlap(self):
        from ogr_core.project.rules import block_objects_refusal
        assert block_objects_refusal(_model(True)) is None

    def test_the_same_group_may_not(self):
        from ogr_core.project.rules import block_objects_refusal
        why = block_objects_refusal(_model(True, ids=(3, 3)))
        assert why is not None and why.code == "block_polyline_overlap"
        assert "Group ID 3" in why.message, why.message

    def test_with_the_box_off_the_ids_do_not_help(self):
        from ogr_core.project.rules import block_objects_refusal
        why = block_objects_refusal(_model(False))
        assert why is not None and why.code == "block_polyline_overlap"
        assert "Multiple Groups" in why.message, why.message


class TestTheFileCarriesTheGroups:

    def test_the_id_is_written_only_when_set(self):
        from ogr_core.geometry import BlockObjectKind, BlockObjectSpec
        assert "group_id" not in BlockObjectSpec(BlockObjectKind.LINE).to_dict()
        d = BlockObjectSpec(BlockObjectKind.LINE, group_id=2).to_dict()
        assert d["group_id"] == 2
        assert BlockObjectSpec.from_dict(d).group_id == 2

    def test_a_project_round_trip(self):
        from ogr_core.project import Project
        p = _model(True, ids=(5, 9))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "groups.ogr")
            p.save(path)
            raw = json.load(open(path, encoding="utf-8"))
            q = Project.load(path)
        assert raw["settings"]["search"]["block_multiple_groups"] is True
        ids = sorted(b.block_object.group_id for b in q.boundaries
                     if b.block_object is not None)
        assert ids == [5, 9]
        assert q.settings.search.block_multiple_groups is True

    def test_an_old_file_without_ids_runs_as_one_group(self):
        """A file that stored the boolean before v0.1.156 — true or false —
        and no ids: one group, so the same search either way."""
        from ogr_core.project.settings import SearchSettings
        for flag in (True, False):
            s = SearchSettings.from_dict({"search_method": "block",
                                          "block_multiple_groups": flag})
            assert s.block_multiple_groups is flag
        off = _run("side_off", multiple=False, overlap=False)
        zero = _run("side_zero", multiple=True, ids=(0, 0), overlap=False)
        assert _factors(zero) == _factors(off)


class TestTheOperations:

    def _pid(self, ws):
        from ogr_api import call
        pid = call(ws, "project_new", name="D99")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [100, 0], [100, 30], [60, 30], [40, 20],
                         [0, 20]],
            "materials": [{"name": "Soil", "unit_weight": 20.0, "strength": {
                "model": "mohr_coulomb",
                "params": {"cohesion": 5.0, "friction_angle": 30.0}}}],
            "settings": {"search.surface_type": "non_circular",
                         "search.search_method": "block",
                         "search.block_multiple_groups": True}})
        return pid

    def test_the_group_id_goes_in_and_comes_back(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = self._pid(ws)
        out = call(ws, "boundary_add", project_id=pid,
                   type="block_search_object", points=[[30, 10], [70, 12]],
                   block_object={"kind": "polyline", "group_id": 2})
        assert out["boundary"]["block_object"]["group_id"] == 2
        s = call(ws, "settings_get", project_id=pid)
        flat = json.dumps(s)
        assert "block_multiple_groups" in flat

    def test_a_bad_group_id_is_refused(self):
        from ogr_api import Workspace, call
        from ogr_api.errors import InvalidArgument
        ws = Workspace()
        pid = self._pid(ws)
        for bad in (-1, "2", True, 1.5):
            try:
                call(ws, "boundary_add", project_id=pid,
                     type="block_search_object",
                     points=[[30, 10], [70, 12]],
                     block_object={"kind": "line", "group_id": bad})
            except InvalidArgument as exc:
                assert "group_id" in str(exc), str(exc)
            else:
                raise AssertionError("group_id %r was accepted" % (bad,))

    def test_the_catalog_says_when_it_is_read(self):
        from ogr_api.catalog import catalog
        entry = next(e for e in catalog("boundary_types")
                     if e["id"] == "block_search_object")
        assert "block_multiple_groups" in entry["block_object"]["group_id"]


@_requires_qt
class TestTheInterface:

    @staticmethod
    def _app():
        return QApplication.instance() or QApplication([])

    def test_the_box_writes_the_setting(self):
        from ogr_gui.dialogs import SurfaceOptionsDialog
        self._app()
        p = _model(False)
        d = SurfaceOptionsDialog(p)
        assert d._b_multi.isChecked() is False
        d._b_multi.setChecked(True)
        d.apply()
        assert p.settings.search.block_multiple_groups is True

    def test_the_object_dialog_edits_the_id_only_with_the_box_on(self):
        from ogr_gui.dialogs import BlockObjectDialog
        self._app()
        p = _model(True, ids=(7, 2))
        obj = next(b for b in p.boundaries if b.block_object is not None)
        on = BlockObjectDialog(obj, None, multiple_groups=True)
        assert on.spn_group.isEnabled() and on.spn_group.value() == 7
        on.spn_group.setValue(4)
        assert on.spec().group_id == 4
        off = BlockObjectDialog(obj, None, multiple_groups=False)
        assert not off.spn_group.isEnabled()
        # Disabled, it keeps the id the object stores.
        assert off.spec().group_id == 7
