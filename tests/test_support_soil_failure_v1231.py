# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.231 — a support whose surrounding soil cannot be read is DECLARED,
not priced with a strength of zero (defect D227 of the verification bank).

THE DEFECT. ``ogr_core.support.bond`` read the strength of the soil around
a support inside ``try: ... except Exception: return 0.0`` (and ``0.0,
0.0`` for the linearised pair), "a plugin must not kill an analysis". A
strength model that raised left the support with a bond of zero along
that stretch -- a pull-out capacity of zero -- and nothing said why: the
class of D56 and D94. Two more silences of the same family came out while
planning it: the failure direction read under a bare ``except`` (anything
unreadable became right-to-left, which flips the sense of a tangent,
horizontal or perpendicular force) and the two Ito-Matsui checks that
answered an exception with False, so their note vanished.

THE DECISION (the owner's, D184: "reject and declare"). The exception
becomes a ``SupportEvaluationError`` whose reason names the material, its
model, the exception and the point, through the channel D95 opened: the
support is left out as ``not_priceable`` on every surface it crosses, with
the reason in ``details["support_failure"]``, in the note, in the canvas
tooltip and in the force diagram. The failure direction is read as it is.
An Ito-Matsui check that cannot be made says so.

THE FIXTURE. The slope of ``test_supports_all_methods_v164`` with a lens
of a material whose model raises, placed BEHIND the slip circle: the tail
of the support runs through it and no slice base does, so only the reading
along the support breaks. The reference is the slope without the support
(D95's identity): a support that cannot be priced moves no number.

DISCRIMINATION, measured on the v0.1.230 tree: see the changelog of
v0.1.231.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _circle, _project,
)

from ogr_core.materials.strength_model import StrengthModel  # noqa: E402

#: The horizontal axis of the other support tests; it crosses the circle at
#: x = 46.71 and runs on to x = 54.
_ACROSS = ((43.5, 8.0), (54.0, 8.0))
#: Behind the circle: at x = 51 the circle is at y = 10.8 and it leaves the
#: crest at x = 52.3, so no slice base enters this box, and the support's
#: tail runs through it from x = 51 to x = 54.
_LENS = ((51.0, 6.0), (58.0, 6.0), (58.0, 10.0), (51.0, 10.0))


class _Unreadable(StrengthModel):
    """A strength model that breaks wherever it is read. Not registered:
    a test model in the registry would leak into every other test."""

    MODEL_ID = "test_unreadable_d227"
    DISPLAY_NAME = "Unreadable (test)"

    def shear_strength(self, sigma_n_eff: float) -> float:
        raise RuntimeError("this model cannot be read here")


def _with_lens(p, strength=None, name="broken"):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    pl = Polyline(vertices=[Vertex(*v) for v in _LENS], closed=True)
    pl.ensure_ccw()
    p.add_boundary(Boundary(polyline=pl, btype=BoundaryType.MATERIAL))
    lens = Material(name=name, unit_weight=18.0,
                    strength=_Unreadable() if strength is None else strength)
    p.materials.append(lens)
    p.invalidate_regions_cache()
    assert p.assign_material_at(54.5, 8.0, lens.id)
    return p


def _instance(type_ref, ends=_ACROSS):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="geosynthetic", head=Vertex(*ends[0]), tail=Vertex(*ends[1]),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP, type_ref=type_ref)


def _geo():
    from ogr_core.support import Geosynthetic
    return Geosynthetic(tensile_capacity=50.0, pullout_mode="coefficient",
                        coefficient_of_interaction=0.8,
                        connection_strength=25.0)


def _anchor():
    from ogr_core.support import HelicalAnchor
    return HelicalAnchor(out_of_plane_spacing=2.0)


def _model(stype=None, lens=True, lens_strength=None, lens_name="broken"):
    p = _project(None)
    if lens:
        _with_lens(p, lens_strength, lens_name)
    if stype is None:
        p.support_types, p.supports = [], []
    else:
        p.support_types = [stype]
        p.supports = [_instance(stype.id)]
    return p


def _result(p):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    return BishopSimplified().compute_fos(p, _circle(), sl)


def _reasons(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=25)
    out: list = []
    compute_support_effects(p, _circle(), sl, reasons=out)
    return out


def _raises(fn, *exc_types):
    try:
        fn()
    except exc_types as exc:
        return exc
    raise AssertionError(f"{fn} did not raise {exc_types}")


# ======================================================================
class TestTheSupportIsLeftOutAndSaidSo:

    def _check(self, stype):
        p = _model(stype)
        res = _result(p)
        bare = _result(_model(None)).fos
        assert res.fos is not None
        assert math.isclose(res.fos, bare, rel_tol=1e-15), (res.fos, bare)
        failure = (res.details or {}).get("support_failure") or ""
        assert "cannot be read" in failure and "'broken'" in failure, failure
        codes = [c for _sid, c in _reasons(p)]
        assert "not_priceable" in codes, codes

    def test_a_geosynthetic_in_coefficient_mode(self):
        self._check(_geo())

    def test_a_helical_anchor(self):
        self._check(_anchor())

    def test_without_the_lens_the_support_is_priced(self):
        """The control: the same support in readable soil moves F."""
        with_support = _result(_model(_geo(), lens=False)).fos
        bare = _result(_model(None, lens=False)).fos
        assert abs(with_support - bare) > 1e-4 * bare, (with_support, bare)


class TestTheTwoReaders:

    def test_the_strength_reader(self):
        from ogr_core.support import SupportEvaluationError
        from ogr_core.support.bond import soil_shear_strength_at
        p = _model(None)
        exc = _raises(lambda: soil_shear_strength_at(p, 54.0, 8.0, 60.0),
                      SupportEvaluationError)
        assert "'broken'" in exc.reason and "RuntimeError" in exc.reason
        assert "(54, 8)" in exc.reason, exc.reason

    def test_the_linearised_reader(self):
        from ogr_core.support import SupportEvaluationError
        from ogr_core.support.bond import equivalent_c_phi_at
        p = _model(None)
        exc = _raises(lambda: equivalent_c_phi_at(p, 54.0, 8.0, 60.0),
                      SupportEvaluationError)
        assert "'broken'" in exc.reason and "RuntimeError" in exc.reason

    def test_a_readable_soil_is_read_as_before(self):
        from ogr_core.support.bond import soil_shear_strength_at
        p = _model(None)
        tau = soil_shear_strength_at(p, 45.0, 8.0, 60.0)
        want = 8.0 + 60.0 * math.tan(math.radians(20.0))
        assert math.isclose(tau, want, rel_tol=1e-12), (tau, want)


class TestTheWordsAreSafe:

    def test_no_reserved_substring(self):
        """A bank check reads the warnings to keep D40 closed: "stable"
        with "head", "edge of the search grid" and "path_optimize" are
        reserved (``test_bond_profile_failure_v1163``)."""
        from ogr_slip2d.support_integration import (
            uncontributing_support_notes)
        p = _model(_geo())
        res = _result(p)
        texts = [(res.details or {}).get("support_failure") or ""]
        texts += list(uncontributing_support_notes(p, res) or [])
        from ogr_core.materials.builtin_models import InfiniteStrength
        from ogr_slip2d.support_notes import infinite_strength_notes
        texts += infinite_strength_notes(_model(
            _anchor(), lens_strength=InfiniteStrength(), lens_name="rock"))
        assert len(texts) >= 3, texts
        for t in texts:
            low = t.lower()
            assert not ("stable" in low and "head" in low), t
            assert "edge of the search grid" not in low, t
            assert "path_optimize" not in low, t


class TestTheInfiniteZeroIsSaid:
    """Finding c of D227. The readers take an Infinite Strength soil as
    ZERO -- a written decision (rigid bedrock is a modelling device), which
    stays: measured in the verification bank, none of its supports that
    read the soil crosses such a material. What was missing was saying
    where it applies."""

    def _bedrock(self, stype, **kw):
        from ogr_core.materials.builtin_models import InfiniteStrength
        return _model(stype, lens_strength=InfiniteStrength(),
                      lens_name="bedrock", **kw)

    def test_the_note_names_the_support_the_material_and_how_much(self):
        from ogr_slip2d.support_notes import infinite_strength_notes
        notes = infinite_strength_notes(self._bedrock(_geo()))
        assert len(notes) == 1, notes
        # 14 of the 50 mid-points of the sheet lie beyond x = 51.
        assert "about 28 % of its length in 'bedrock'" in notes[0], notes
        assert "Infinite Strength" in notes[0] and "zero" in notes[0]

    def test_a_helical_anchor_counts_its_plates(self):
        from ogr_slip2d.support_notes import infinite_strength_notes
        notes = infinite_strength_notes(self._bedrock(_anchor()))
        assert len(notes) == 1 and "plates" in notes[0], notes

    def test_it_reaches_the_analysis(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        notes = settings_warnings(self._bedrock(_geo()))
        assert any("Infinite Strength" in n for n in notes), notes

    def test_the_zero_is_a_soil_of_no_strength(self):
        """The identity that pins the decision: along the sheet an
        Infinite Strength soil reads as a soil of zero strength, to the
        last bit (no slice base enters the lens). A sheet whose pull-out
        BEHIND the circle governs -- with ``_geo`` the tensile capacity
        does, and the lens moves nothing, which the control catches."""
        from ogr_core.materials.builtin_models import NoStrength
        from ogr_core.support import Geosynthetic

        def strong():
            return Geosynthetic(tensile_capacity=500.0,
                                pullout_mode="coefficient",
                                coefficient_of_interaction=0.8,
                                connection_strength=1000.0)
        bedrock = _result(self._bedrock(strong())).fos
        void = _result(_model(strong(), lens_strength=NoStrength(),
                              lens_name="void")).fos
        assert bedrock == void, (bedrock, void)
        soil = _result(_model(strong(), lens=False)).fos
        assert abs(bedrock - soil) > 0.1 * soil, (bedrock, soil)

    def test_no_note_where_the_soil_is_finite_or_not_read(self):
        from ogr_core.support import Geosynthetic, SoilNail
        from ogr_slip2d.support_notes import infinite_strength_notes
        assert infinite_strength_notes(_model(_geo(), lens=False)) == []
        nail = SoilNail(tensile_capacity=30, plate_capacity=20,
                        bond_strength=8, out_of_plane_spacing=3.0)
        assert infinite_strength_notes(self._bedrock(nail)) == []
        own_law = Geosynthetic(tensile_capacity=50.0,
                               pullout_mode="mohr_coulomb")
        assert infinite_strength_notes(self._bedrock(own_law)) == []

    def test_which_types_read_the_soil(self):
        from ogr_core.support import (Geosynthetic, HelicalAnchor,
                                      PileMicropile, SoilNail)
        assert Geosynthetic(pullout_mode="coefficient").READS_SOIL_STRENGTH
        assert not Geosynthetic(pullout_mode="mohr_coulomb")             .READS_SOIL_STRENGTH
        assert not Geosynthetic(pullout_mode="friction_factor")             .READS_SOIL_STRENGTH
        assert HelicalAnchor().READS_SOIL_STRENGTH
        assert PileMicropile(failure_mode="ito_matsui").READS_SOIL_STRENGTH
        assert not PileMicropile(failure_mode="shear").READS_SOIL_STRENGTH
        assert not SoilNail().READS_SOIL_STRENGTH


class TestTheOtherSilences:

    def test_the_failure_direction_is_read_as_it_is(self):
        import ast
        import inspect

        from ogr_slip2d import support_integration
        src = inspect.getsource(support_integration.compute_support_effects)
        tree = ast.parse(src.lstrip())
        handlers = [h for h in ast.walk(tree)
                    if isinstance(h, ast.Try)
                    and "failure_direction" in ast.unparse(h)]
        assert not handlers, "failure_direction is read under an except"

    def test_an_ito_matsui_check_that_cannot_be_made_says_so(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      PileMicropile, SupportInstance)
        from ogr_slip2d import support_integration
        from ogr_slip2d.ito_matsui_notes import ito_matsui_notes
        p = _project(None)
        pile = PileMicropile(failure_mode="ito_matsui",
                             out_of_plane_spacing=1.5, pile_diameter=0.5)
        p.support_types = [pile]
        p.supports = [SupportInstance(
            type_id="pile_micropile", head=Vertex(45.0, 9.0),
            tail=Vertex(45.0, -5.0),
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.PERPENDICULAR_TO_PILE,
            type_ref=pile.id)]

        def _broken(_project):
            raise RuntimeError("the profiles cannot be built")

        real = support_integration._bond_profiles
        support_integration._bond_profiles = _broken
        try:
            notes = ito_matsui_notes(p)
        finally:
            support_integration._bond_profiles = real
        assert any("could not be checked" in n and "negative" in n
                   and "RuntimeError" in n for n in notes), notes


class TestTheInterfaceSaysIt:

    def test_the_canvas_tooltip(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.canvas.graphics_items import SupportItem
        QApplication.instance() or QApplication([])
        stype = _geo()
        p = _model(stype)
        item = SupportItem(p.supports[0], "Geosynthetic", stype, None, p)
        tip = item.toolTip()
        assert "This support cannot be priced" in tip, tip
        assert "cannot be read" in tip and "broken" in tip, tip
        assert "Bond profile could not be built" not in tip, tip

    def test_the_force_diagram(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        QApplication.instance() or QApplication([])
        w = SupportForceDiagramWindow(_model(_geo()))
        try:
            note = w.note.text()
            assert "This support cannot be priced" in note, note
            assert "cannot be read" in note, note
        finally:
            w.close()
            w.deleteLater()

    def test_the_sentence_has_its_spanish(self):
        from ogr_gui.i18n import current_language, set_language, tr
        key = ("This support cannot be priced (%s): the analysis leaves it "
               "out.")
        prev = current_language()
        try:
            set_language("es")
            assert tr(key) != key and "no se puede calcular" in tr(key)
        finally:
            set_language(prev)
