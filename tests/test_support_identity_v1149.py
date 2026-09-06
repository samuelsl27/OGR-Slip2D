# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.149 — a support refers to ONE property set, among several of its class.

WHAT INVARIANT THIS PROTECTS

``project.support_types`` is a list. Until this version eight places in the
program turned it into a ``{TYPE_ID: type}`` dictionary and resolved each
``SupportInstance`` by ``type_id``, which is the CLASS constant: two soil
nails with different capacities collapsed into the last one declared, with
no warning, while the ``.ogr`` kept both. The file looked right; only the
number was wrong. That is defect D66 of the verification bank, and it
blocked a whole problem (fourteen rows of nails in seven parameter sets)
and forced a detour on another (two tiebacks, one rewritten as a nail).

The cure is identity: every type carries an ``id`` of its own, an instance
names it through ``type_ref``, and ``resolve_support_type`` is the ONE
place that answers "which set". This file pins:

* the identity survives a file (round trip through ``to_dict``, through
  ``Project``, and a file older than this version still loads);
* the resolution order — reference, then FIRST of the class, then the
  registry — and what it reports when it had to guess;
* rule 7 with a number: two sets of one class give a factor of safety that
  neither set alone gives, and one set per class gives the SAME factor,
  digit for digit, whether the instance names it or not. That equality is
  what lets the 190 models of the bank keep their numbers;
* the detour the bank lived on — ``GroutedTieback(bond_length_percent=100)``
  is ``SoilNail`` — stays exact, because problem 49 explains itself with it;
* the notes see every set, not only the last of each class;
* the interface can declare several sets of a class and assign each one
  (rule 3), and the editor keeps a set's identity through every rebuild of
  its object.
"""
from __future__ import annotations

import math

H = 12.0
TOE = 30.0
CREST = 37.0
PHI = 32.0
COH = 5.0
NSLICES = 50


# ======================================================================
# Fixtures — the geometry of ``test_support_normal_v1137``
# ======================================================================
def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=34.0, centre_y=20.0, radius=15.0)


def _nail(capacity, name=""):
    """A soil nail whose tensile mode governs at the cut: F = capacity / 2."""
    from ogr_core.support import SoilNail
    st = SoilNail(tensile_capacity=capacity, plate_capacity=0.75 * capacity,
                  bond_strength=0.2 * capacity, out_of_plane_spacing=2.0)
    if name:
        st._display_name = name
    return st


def _instance(type_ref=None, y=10.5, name=""):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="soil_nail", type_ref=type_ref, name=name,
        head=Vertex(36.5, y), tail=Vertex(52.0, y),
        force_application=ForceApplication.ACTIVE,
        orientation=ForceOrientation.PARALLEL_TO_SUPPORT)


def _project(types=(), supports=()):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("support-identity")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    p.support_types = list(types)
    p.supports = list(supports)
    return p


def _fos(p, method_id="bishop_simplified"):
    """Through the runner's own factory, as the bank's evaluator does."""
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    method = build_method(p, method_id, NSLICES)
    ev = GridSearch(method=method, num_slices=NSLICES, min_area=0.0)
    return ev.evaluate_circle(p, _circle()).fos


def _effects(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=NSLICES)
    return compute_support_effects(p, _circle(), sl)


def _forces_by_instance(p):
    return {e.support_id: e.force_magnitude for e in _effects(p)}


# ======================================================================
class TestTheIdentitySurvivesAFile:
    def test_every_registered_type_keeps_its_id_through_to_dict(self):
        from ogr_core.support import support_from_dict, support_registry
        for tid, cls in support_registry().items():
            st = cls()
            back = support_from_dict(st.to_dict())
            assert back.id == st.id, tid
            assert back == st, tid

    def test_two_default_sets_are_equal_but_not_the_same(self):
        """``compare=False``: identical parameters are still equal."""
        from ogr_core.support import support_registry
        for tid, cls in support_registry().items():
            a, b = cls(), cls()
            assert a == b, tid
            assert a.id != b.id, tid

    def test_a_file_older_than_this_version_loads_with_a_fresh_id(self):
        from ogr_core.support import support_from_dict, support_registry
        for tid, cls in support_registry().items():
            d = cls().to_dict()
            d.pop("id")
            back = support_from_dict(d)
            assert isinstance(back.id, str) and back.id, tid

    def test_the_instance_reference_round_trips_and_is_optional(self):
        from ogr_core.support import SupportInstance
        s = _instance()
        assert s.type_ref is None
        assert "type_ref" not in s.to_dict(), "an unset reference is not written"
        s.type_ref = "set-1"
        back = SupportInstance.from_dict(s.to_dict())
        assert back.type_ref == "set-1"
        old = s.to_dict()
        old.pop("type_ref")
        assert SupportInstance.from_dict(old).type_ref is None

    def test_the_pattern_reference_round_trips_and_reaches_its_instances(self):
        from ogr_core.support import SupportPattern
        pat = SupportPattern(type_id="soil_nail", length=6.0, spacing=1.5)
        assert "type_ref" not in pat.to_dict()
        pat.type_ref = "set-2"
        assert SupportPattern.from_dict(pat.to_dict()).type_ref == "set-2"
        made = pat.generate_along_segment((0.0, 0.0), (3.0, 0.0))
        assert made and all(s.type_ref == "set-2" for s in made)

    def test_the_project_keeps_ids_and_references(self):
        from ogr_core.project import Project
        a, b = _nail(60.0, "A"), _nail(120.0, "B")
        p = _project([a, b], [_instance(b.id), _instance(a.id, y=8.0)])
        back = Project.from_dict(p.to_dict())
        assert [st.id for st in back.support_types] == [a.id, b.id]
        assert [s.type_ref for s in back.supports] == [b.id, a.id]
        assert getattr(back.support_types[1], "_display_name", "") == "B"


# ======================================================================
class TestTheResolutionOrder:
    def test_the_reference_wins_over_the_class(self):
        from ogr_core.support import resolve_support_type
        a, b = _nail(60.0), _nail(120.0)
        p = _project([a, b], [_instance(b.id)])
        assert resolve_support_type(p, p.supports[0]) is b

    def test_the_reference_is_read_by_id_even_when_type_id_disagrees(self):
        """A set whose class was changed in the editor still resolves."""
        from ogr_core.support import GroutedTieback, resolve_support_type
        a, c = _nail(60.0), GroutedTieback()
        s = _instance(c.id)            # says soil_nail, names the tieback
        p = _project([a, c], [s])
        assert resolve_support_type(p, s) is c

    def test_without_a_reference_the_first_of_the_class_is_used(self):
        """FIRST, not last: the dictionaries this replaces kept the last."""
        from ogr_core.support import resolve_support_type
        a, b = _nail(60.0), _nail(120.0)
        p = _project([a, b], [_instance()])
        assert resolve_support_type(p, p.supports[0]) is a

    def test_a_reference_the_project_no_longer_holds_falls_back_to_the_class(self):
        from ogr_core.support import resolve_support_type
        a, b = _nail(60.0), _nail(120.0)
        p = _project([a, b], [_instance("gone")])
        assert resolve_support_type(p, p.supports[0]) is a

    def test_no_set_of_the_class_gives_the_registry_default(self):
        from ogr_core.support import SoilNail, resolve_support_type
        p = _project([], [_instance()])
        st = resolve_support_type(p, p.supports[0])
        assert isinstance(st, SoilNail) and st == SoilNail()

    def test_an_unknown_class_gives_none(self):
        from ogr_core.support import resolve_support_type
        s = _instance()
        s.type_id = "no_such_support"
        assert resolve_support_type(_project([], [s]), s) is None

    def test_pairs_keep_the_order_of_the_supports(self):
        from ogr_core.support import support_type_pairs
        a, b = _nail(60.0), _nail(120.0)
        s1, s2, s3 = _instance(b.id), _instance(a.id, y=8.0), _instance()
        pairs = support_type_pairs(_project([a, b], [s1, s2, s3]))
        assert [(s.id, st) for s, st in pairs] == [(s1.id, b), (s2.id, a),
                                                    (s3.id, a)]
        assert pairs[0][1] is b and pairs[2][1] is a

    def test_what_had_to_be_guessed_is_reported(self):
        from ogr_core.support import unresolved_support_refs
        a, b = _nail(60.0), _nail(120.0)
        bound, loose, orphan = _instance(b.id), _instance(), _instance("gone")
        refs = unresolved_support_refs(_project([a, b], [bound, loose, orphan]))
        assert [s.id for s, _ in refs["ambiguous"]] == [loose.id]
        assert refs["ambiguous"][0][1] == [a, b]
        assert [(s.id, st) for s, st in refs["orphan"]] == [(orphan.id, a)]
        # One set per class: nothing to guess, nothing to say.
        quiet = unresolved_support_refs(_project([a], [_instance()]))
        assert quiet == {"ambiguous": [], "orphan": []}


# ======================================================================
class TestRuleSevenWithANumber:
    """Two sets of one class move the factor; one set moves nothing."""

    def test_each_instance_computes_with_its_own_set(self):
        a, b = _nail(60.0), _nail(120.0)
        s1, s2 = _instance(a.id), _instance(b.id, y=8.0)
        forces = _forces_by_instance(_project([a, b], [s1, s2]))
        # Tensile governs at both cuts: capacity / spacing, exactly.
        assert abs(forces[s1.id] - 30.0) < 1e-9, forces
        assert abs(forces[s2.id] - 60.0) < 1e-9, forces

    def test_two_sets_give_a_factor_neither_set_gives_alone(self):
        a, b = _nail(60.0), _nail(120.0)
        mixed = _fos(_project([a, b], [_instance(a.id), _instance(b.id, y=8.0)]))
        only_a = _fos(_project([_nail(60.0)], [_instance(), _instance(y=8.0)]))
        only_b = _fos(_project([_nail(120.0)], [_instance(), _instance(y=8.0)]))
        assert only_a < mixed < only_b, (only_a, mixed, only_b)
        assert mixed != only_a and mixed != only_b

    def test_the_old_collapse_is_gone(self):
        """Until v0.1.149 both instances here used B, the LAST set."""
        a, b = _nail(60.0), _nail(120.0)
        p = _project([a, b], [_instance(a.id), _instance(b.id, y=8.0)])
        forces = _forces_by_instance(p)
        assert len(set(round(f, 9) for f in forces.values())) == 2

    def test_one_set_per_class_gives_the_same_factor_bound_or_not(self):
        """Digit for digit: this is what keeps the bank's numbers."""
        a = _nail(60.0)
        loose = _fos(_project([a], [_instance(), _instance(y=8.0)]))
        bound = _fos(_project([a], [_instance(a.id), _instance(a.id, y=8.0)]))
        assert loose == bound
        assert loose > _fos(_project([], []))     # and the nails do act

    def test_loose_instances_take_the_first_set_of_their_class(self):
        a, b = _nail(60.0), _nail(120.0)
        loose = _fos(_project([a, b], [_instance(), _instance(y=8.0)]))
        first = _fos(_project([_nail(60.0)], [_instance(), _instance(y=8.0)]))
        assert loose == first


# ======================================================================
class TestTheDetourOfProblem49StaysExact:
    """``GroutedTieback(bond_length_percent=100)`` is a ``SoilNail``.

    The bank's problem 49 lived on this equality while D66 was open, and
    its record explains itself with it. If it ever stops holding, the
    record lies and the problem loses its explanation.
    """

    def test_the_same_force_at_ten_stations(self):
        from ogr_core.support import GroutedTieback, SoilNail
        kw = dict(tensile_capacity=120344.9, plate_capacity=120344.9,
                  bond_strength=13571.68, out_of_plane_spacing=8.0)
        tie = GroutedTieback(bond_length_percent=100.0, **kw)
        nail = SoilNail(**kw)
        L = 33.6
        for i in range(11):
            d = L * i / 10.0
            assert abs(tie.force_at(d, L) - nail.force_at(d, L)) < 1e-9, d


# ======================================================================
class TestTheAnalysisSaysWhenItGuessed:
    def _notes(self, p):
        from ogr_slip2d.analysis_runner import settings_warnings
        return settings_warnings(p, ["bishop_simplified"])

    def test_two_sets_and_a_loose_instance_are_reported_with_the_set_used(self):
        a, b = _nail(60.0, "short nails"), _nail(120.0, "long nails")
        notes = self._notes(_project([a, b], [_instance(), _instance(y=8.0)]))
        hit = [n for n in notes if "name no property set" in n]
        assert len(hit) == 1, notes
        assert "2 supports" in hit[0] and "Soil Nail" in hit[0]
        assert "'short nails'" in hit[0] and "'long nails'" in hit[0]
        assert "The first, 'short nails', is used" in hit[0]

    def test_bound_instances_say_nothing(self):
        a, b = _nail(60.0), _nail(120.0)
        notes = self._notes(_project([a, b], [_instance(a.id), _instance(b.id)]))
        assert not any("property set" in n for n in notes), notes

    def test_one_set_per_class_says_nothing(self):
        notes = self._notes(_project([_nail(60.0)], [_instance()]))
        assert not any("property set" in n for n in notes), notes

    def test_an_orphan_reference_is_reported_with_what_replaced_it(self):
        a = _nail(60.0, "the nail")
        notes = self._notes(_project([a], [_instance("gone", name="N7")]))
        hit = [n for n in notes if "no longer in the project" in n]
        assert len(hit) == 1, notes
        assert "'N7'" in hit[0] and "'the nail' is used instead" in hit[0]


# ======================================================================
class TestTheNotesSeeEverySet:
    """Until v0.1.149 the model notes saw the LAST set of each class."""

    def test_helical_anchor_notes_are_per_set(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.support import HelicalAnchor, SupportInstance
        from ogr_slip2d.helical_anchor_notes import helical_anchor_notes
        good = HelicalAnchor(shaft_width=0.1, average_helix_diameter=0.25)
        bad = HelicalAnchor(shaft_width=0.25, average_helix_diameter=0.25)
        p = Project("two anchors")
        p.support_types = [good, bad]
        p.supports = [
            SupportInstance(type_id="helical_anchor", type_ref=good.id,
                            name="fine", head=Vertex(0, 0), tail=Vertex(5, 0)),
            SupportInstance(type_id="helical_anchor", type_ref=bad.id,
                            name="plateless", head=Vertex(0, 2),
                            tail=Vertex(5, 2)),
        ]
        notes = helical_anchor_notes(p)
        blind = [n for n in notes if "no bearing area" in n]
        assert len(blind) == 1 and "'plateless'" in blind[0], notes

    def test_ito_matsui_notes_are_per_set(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.support import PileMicropile, SupportInstance
        from ogr_slip2d.ito_matsui_notes import ito_matsui_notes
        open_row = PileMicropile(failure_mode="ito_matsui",
                                 out_of_plane_spacing=1.8, pile_diameter=0.6)
        closed_row = PileMicropile(failure_mode="ito_matsui",
                                   out_of_plane_spacing=0.6, pile_diameter=0.6)
        p = Project("two rows")
        p.support_types = [open_row, closed_row]
        p.supports = [
            SupportInstance(type_id="pile_micropile", type_ref=open_row.id,
                            head=Vertex(10, 10), tail=Vertex(10, 0)),
            SupportInstance(type_id="pile_micropile", type_ref=closed_row.id,
                            head=Vertex(20, 10), tail=Vertex(20, 0)),
        ]
        notes = ito_matsui_notes(p)
        assert sum("no opening" in n for n in notes) == 1, notes

    def test_grouping_is_by_set(self):
        from ogr_slip2d.support_notes import resolved_types, supports_by_type
        a, b = _nail(60.0), _nail(120.0)
        s1, s2, s3 = _instance(a.id), _instance(b.id), _instance(a.id, y=8.0)
        p = _project([a, b], [s1, s2, s3])
        groups = supports_by_type(p)
        assert [(st, [s.id for s in sups]) for st, sups in groups] == [
            (a, [s1.id, s3.id]), (b, [s2.id])]
        assert groups[0][0] is a and groups[1][0] is b
        assert set(resolved_types(p)) == {a.id, b.id}


# ======================================================================
class TestTheInterface:
    """Offscreen, real widgets, never ``exec()``."""

    def _app(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance() or QApplication([])

    def _two_nails(self):
        a, b = _nail(60.0, "A"), _nail(120.0, "B")
        return a, b, _project([a, b], [_instance(b.id, name="n1"),
                                        _instance(a.id, y=8.0, name="n2")])

    def test_the_instance_dialog_offers_each_set_and_assigns_by_identity(self):
        from ogr_gui.dialogs.support_properties_dialog import (
            SupportInstancePropertiesDialog)
        self._app()
        a, b, p = self._two_nails()
        s = p.supports[0]
        dlg = SupportInstancePropertiesDialog(s, p)
        assert dlg.cbo_type.count() == 2
        assert dlg.cbo_type.currentData() == b.id
        dlg.cbo_type.setCurrentIndex(dlg.cbo_type.findData(a.id))
        dlg.accept()
        assert s.type_ref == a.id and s.type_id == "soil_nail"

    def test_assigning_a_set_of_another_class_moves_type_id_too(self):
        from ogr_core.support import GroutedTieback
        from ogr_gui.dialogs.support_properties_dialog import (
            SupportInstancePropertiesDialog)
        self._app()
        a, b, p = self._two_nails()
        c = GroutedTieback()
        p.support_types.append(c)
        s = p.supports[0]
        dlg = SupportInstancePropertiesDialog(s, p)
        dlg.cbo_type.setCurrentIndex(dlg.cbo_type.findData(c.id))
        dlg.accept()
        assert s.type_ref == c.id and s.type_id == "grouted_tieback"

    def test_the_pattern_dialog_names_the_set(self):
        from ogr_gui.dialogs.support_pattern_dialog import (
            AddSupportPatternDialog)
        self._app()
        a, b, p = self._two_nails()
        dlg = AddSupportPatternDialog(p)
        dlg.cbo_type.setCurrentIndex(dlg.cbo_type.findData(b.id))
        dlg.accept()
        assert dlg.pattern.type_ref == b.id
        assert dlg.pattern.type_id == "soil_nail"

    def test_the_editor_keeps_identities_through_accept(self):
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        self._app()
        a, b, p = self._two_nails()
        dlg = DefineSupportDialog(p)
        assert [r.id for r in dlg._rows] == [a.id, b.id]
        dlg.accept()
        assert [st.id for st in p.support_types] == [a.id, b.id]
        # The objects were rebuilt from the panel; the sets are the same.
        assert p.support_types[1].tensile_capacity == 120.0
        assert [s.type_ref for s in p.supports] == [b.id, a.id]

    def test_a_duplicated_row_is_a_new_set(self):
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        self._app()
        a, b, p = self._two_nails()
        dlg = DefineSupportDialog(p)
        dlg.list_widget.setCurrentRow(0)
        dlg._duplicate_row()
        assert dlg._rows[2].id not in (a.id, b.id)
        assert dlg._rows[2].support.id == dlg._rows[2].id
        dlg.accept()
        assert len({st.id for st in p.support_types}) == 3

    def test_changing_the_class_of_a_row_keeps_its_identity(self):
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        self._app()
        a, b, p = self._two_nails()
        dlg = DefineSupportDialog(p)
        dlg.list_widget.setCurrentRow(0)
        idx = dlg.cbo_type.findData("grouted_tieback")
        dlg.cbo_type.setCurrentIndex(idx)
        dlg._on_type_changed(idx)
        assert dlg._rows[0].support.id == a.id
        assert dlg._rows[0].support.TYPE_ID == "grouted_tieback"
        dlg.accept()
        # The instance that named A follows it into the new class.
        assert p.supports[1].type_ref == a.id
        assert p.supports[1].type_id == "grouted_tieback"
        assert p.supports[0].type_id == "soil_nail"

    def test_deleting_a_row_releases_the_instances_that_named_it(self):
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        self._app()
        a, b, p = self._two_nails()
        dlg = DefineSupportDialog(p)
        dlg.list_widget.setCurrentRow(1)
        dlg._delete_row()
        dlg.accept()
        assert [st.id for st in p.support_types] == [a.id]
        assert p.supports[0].type_ref is None      # named B, which is gone
        assert p.supports[1].type_ref == a.id

    def test_the_data_tip_shows_the_set_and_its_parameters(self):
        from ogr_gui.data_tips import DataTipMode, support_tip
        a, b, p = self._two_nails()
        tip = support_tip(p.supports[0], DataTipMode.MAXIMUM, project=p)
        assert tip.splitlines()[0] == "B"
        assert "tensile capacity" in tip and "120" in tip
