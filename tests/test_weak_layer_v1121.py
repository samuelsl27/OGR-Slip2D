# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A weak layer must carry its own strength, and must not carry anything else.

WHAT INVARIANT THIS PROTECTS. A weak layer is a polyline with a strength of its
own — a joint between two gabion courses, a geomembrane interface, a bedding
plane. Three things have to be true at once for it to mean anything, and each
one is a different way of getting it wrong:

* the slip surface must RUN ALONG it rather than cross it — otherwise it is a
  thin band of material, which is the thing that cannot be modelled today and
  the reason this exists: a band has thickness and a surface can cut it
  diagonally;
* the slices on it must take ITS strength and not the region's — otherwise the
  layer is decoration that changes only the geometry;
* they must NOT take its weight — a joint has no thickness, so there is nothing
  of it to weigh, and a unit weight typed into its material must not reach the
  driving term.

WHY THESE ANCHORS. None of the numbers below is a value this code printed.

* THE CLOSED FORM. Over a PLANAR surface of constant base angle in a single
  material with no water, the Ordinary method reduces exactly to

      F = (c L + W cos(a) tan(phi)) / (W sin(a))

  with L the base length and W the total weight. It follows from the definition
  of the method and does not depend on the number of slices. The geometry here
  is chosen so that the weight is exactly ``gamma * 80`` by hand-integrated
  area — see ``_AREA`` below.

* THE REDUCTION IDENTITY. Where the clipped path is piecewise linear, the same
  path entered by hand as an ordinary non-circular surface must give the same
  factor of safety to the last bits. This is what says the clipping introduces
  no bias of its own, and it is the test that caught a real defect during
  development: the ends of a layer were being reported as mandatory slice cuts
  even over stretches the layer does not win, which moved the factor by 1.6e-6
  and, worse, spends slices the slicer refuses a surface for running out of.

* THE TWO-MODEL IDENTITY, which is the strongest of the three. A joint that
  supplies a strength must give the SAME factor of safety as a model in which
  that strength is simply the material of the slope, over the same path. Two
  independent descriptions of one mechanism; if the substitution leaked
  anything — a weight, a pore pressure, a slice boundary — they would part.
  Measured: they agree to the last bit for Ordinary, Bishop and Janbu.

* RULE 7. Four settings, four separations: the two handling policies, the
  suppress flag, the layer's own material, and the base-angle ceiling.

WHAT IS DELIBERATELY NOT ASSERTED. Bishop Simplified is not measured against
the planar closed form, and the reason is not this feature. On a plane the
circular Bishop and Ordinary are the same expression —
``(c B + W cos^2(a) tan(phi)) / (W sin(a) cos(a))`` either way — but a
NON-CIRCULAR surface has no centre, so this program takes its moments about a
constructed axis instead, and on this plane that is worth -0.42 % against the
closed form. It is there with no weak layer in the model at all, it is the same
axis sensitivity D15/A22-1 measured at -1.84 % against +0.08 %, and asserting a
circular formula on a non-circular surface would be measuring that, not this.
Ordinary IS asserted, and matches to 4e-16.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402  (the runner supplies it)

from ogr_core.geometry import (  # noqa: E402
    Boundary, BoundaryType, Polyline, Vertex,
)
from ogr_core.materials import Material  # noqa: E402
from ogr_core.materials.builtin_models import MohrCoulomb  # noqa: E402
from ogr_core.project import Project  # noqa: E402
from ogr_core.project.settings import WeakLayerHandling  # noqa: E402
from ogr_slip2d.methods import get_method  # noqa: E402
from ogr_slip2d.search import BaseSearch  # noqa: E402
from ogr_slip2d.surface import (  # noqa: E402
    SlipCircle, SlipSurface, WeakLayerBand, WeakLayerSurface,
)
from ogr_slip2d.weak_layers import (  # noqa: E402
    touching_bands, weak_layer_bands, weak_layer_model_warnings,
)

# ----------------------------------------------------------------------
# The planar case, and the arithmetic that anchors it
# ----------------------------------------------------------------------
# External boundary: a 45 deg face from (0, 0) up to (10, 10), then flat.
_EXT = [(0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (10.0, 10.0)]
_GAMMA = 20.0
# The joint: a straight line from a point on the face to a point on the crest.
_JX0, _JY0 = 2.0, 2.0
_JX1, _JY1 = 30.0, 10.0
# Area between the ground surface and the joint, integrated by hand:
#   x in [2, 10]:  int (x - 2 - (2/7)(x-2)) dx = (5/7)(8^2/2)      = 22.857142857
#   x in [10, 30]: int (8 - (2/7)(x-2)) dx                          = 57.142857143
#                                                            total  = 80.0
_AREA = 80.0
_B = _JX1 - _JX0                                     # horizontal width, 28
_L = math.hypot(_JX1 - _JX0, _JY1 - _JY0)            # base length, sqrt(848)
_ALPHA = math.atan2(_JY1 - _JY0, _JX1 - _JX0)
_JOINT_C = 5.0
_JOINT_PHI = 20.0


def _ordinary_closed_form(c, phi_deg, gamma):
    """F for a planar surface, one material, no water — Fellenius, exactly."""
    w = gamma * _AREA
    tan_phi = math.tan(math.radians(phi_deg))
    return ((c * _L + w * math.cos(_ALPHA) * tan_phi)
            / (w * math.sin(_ALPHA)))


class _Probe(BaseSearch):
    """A search that never searches: it is only a door into the engine."""

    def _run(self, project):          # pragma: no cover - never called
        raise NotImplementedError


def _fos(project, surface, method="bishop_simplified", num_slices=40):
    s = _Probe(method=get_method(method)(), num_slices=num_slices)
    s._weak_bands_cache = None
    s._pending_notes = []
    with project.regions_frozen():
        res = s.evaluate_surface(project, surface)
    return res, s._pending_notes


def _project(joint=None, joint_gamma=_GAMMA, ext=_EXT,
             soil=(20.0, 30.0), soil_gamma=_GAMMA):
    """A slope, a soil, and optionally one weak layer with its own material."""
    p = Project("weak layer")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(*v) for v in ext], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Soil", unit_weight=soil_gamma,
        strength=MohrCoulomb(cohesion=soil[0], friction_angle=soil[1])))
    jm = None
    if joint is not None:
        jm = Material(
            name="Joint", unit_weight=joint_gamma,
            strength=MohrCoulomb(cohesion=joint[0], friction_angle=joint[1]))
        p.materials.append(jm)
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(_JX0, _JY0), Vertex(_JX1, _JY1)]),
            btype=BoundaryType.WEAK_LAYER, material_id=jm.id))
    return p, jm


def _base_below_the_joint():
    """A trial surface that daylights at the joint's ends and dips under it."""
    return SlipSurface(polyline=Polyline([
        Vertex(_JX0, _JY0), Vertex(16.0, 1.0), Vertex(_JX1, _JY1)]))


# ======================================================================
class TestTheClosedForm:
    """The strength on the joint is the joint's, and the answer is exact."""

    def test_ordinary_matches_the_planar_closed_form(self):
        p, _ = _project(joint=(_JOINT_C, _JOINT_PHI))
        res, _ = _fos(p, _base_below_the_joint(), method="ordinary_fellenius")
        assert res is not None and res.is_valid
        expected = _ordinary_closed_form(_JOINT_C, _JOINT_PHI, _GAMMA)
        assert res.fos == pytest.approx(expected, rel=1e-9)

    def test_the_same_strength_as_a_material_gives_the_same_answer(self):
        """The two-model identity, for the three methods that solve here.

        Left: a slope of strong soil with a weak joint the surface is clipped
        onto. Right: the same path, in a slope made ENTIRELY of the joint's
        material, with no weak layer anywhere. The mechanism is the same one
        described twice, so the two must not differ by a bit — and if the
        substitution leaked a weight, a pore pressure or a slice boundary,
        they would.
        """
        p_joint, _ = _project(joint=(_JOINT_C, _JOINT_PHI))
        p_plain, _ = _project(soil=(_JOINT_C, _JOINT_PHI))
        plain_surface = SlipSurface(polyline=Polyline(
            [Vertex(_JX0, _JY0), Vertex(_JX1, _JY1)]))
        for method in ("ordinary_fellenius", "bishop_simplified",
                       "janbu_simplified"):
            a = _fos(p_joint, _base_below_the_joint(), method=method)[0]
            b = _fos(p_plain, plain_surface, method=method)[0]
            assert a is not None and b is not None, method
            assert a.fos == b.fos, (method, a.fos, b.fos)

    def test_the_answer_does_not_move_with_the_slice_count(self):
        """A closed form that depends on n is not a closed form."""
        p, _ = _project(joint=(_JOINT_C, _JOINT_PHI))
        values = [_fos(p, _base_below_the_joint(),
                       method="ordinary_fellenius", num_slices=n)[0].fos
                  for n in (15, 40, 90)]
        assert max(values) - min(values) < 1e-9

    def test_every_slice_sits_on_the_joint(self):
        p, jm = _project(joint=(_JOINT_C, _JOINT_PHI))
        res, _ = _fos(p, _base_below_the_joint())
        assert all(s.weak_layer_id for s in res.slices)
        assert {s.material.id for s in res.slices} == {jm.id}
        # and the base is planar, which is what the closed form assumes
        angles = [s.base_angle for s in res.slices]
        assert max(angles) - min(angles) < 1e-12
        assert angles[0] == pytest.approx(_ALPHA, abs=1e-12)


# ======================================================================
class TestTheJointCarriesStrengthAndNothingElse:

    def test_the_joint_unit_weight_never_reaches_the_answer(self):
        """A joint has no thickness, so it has no weight.

        Fifty times the soil's unit weight typed into the joint's material
        must not move the factor of safety by a single bit. This is the
        assertion that separates a weak layer from a thin band of material.
        """
        p_a, _ = _project(joint=(_JOINT_C, _JOINT_PHI), joint_gamma=_GAMMA)
        p_b, _ = _project(joint=(_JOINT_C, _JOINT_PHI), joint_gamma=1000.0)
        fa = _fos(p_a, _base_below_the_joint())[0].fos
        fb = _fos(p_b, _base_below_the_joint())[0].fos
        assert fa == fb

    def test_the_weight_is_the_soil_column(self):
        """Rule 1, on the driving side: sum of weights == gamma * area."""
        p, _ = _project(joint=(_JOINT_C, _JOINT_PHI), joint_gamma=1000.0)
        res, _ = _fos(p, _base_below_the_joint())
        total = sum(s.weight for s in res.slices)
        assert total == pytest.approx(_GAMMA * _AREA, rel=1e-9)

    def test_the_joint_material_moves_the_number(self):
        """Rule 7 for the assignment itself."""
        weak = _fos(_project(joint=(0.0, 5.0))[0],
                    _base_below_the_joint())[0].fos
        strong = _fos(_project(joint=(60.0, 40.0))[0],
                      _base_below_the_joint())[0].fos
        assert strong > weak * 1.5


# ======================================================================
class TestTheReductionIdentity:
    """Clipping must add nothing of its own."""

    # A base polyline that meets a horizontal joint inside its own extent,
    # so the clipped path is piecewise linear and can be written down.
    _BASE = [(9.0, 10.0), (18.0, 5.0), (25.0, 20.0)]
    _JY, _JX0, _JX1 = 8.0, 12.0, 22.0
    _EXT2 = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (25.0, 20.0),
             (10.0, 10.0), (0.0, 10.0)]

    def _crossings(self):
        xa = 9.0 + (10.0 - self._JY) * 9.0 / 5.0
        xb = 18.0 + (self._JY - 5.0) * 7.0 / 15.0
        return xa, xb

    def _model(self, with_layer):
        p = Project("reduction identity")
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(*v) for v in self._EXT2], closed=True),
            btype=BoundaryType.EXTERNAL))
        soil = Material(name="Soil", unit_weight=20.0,
                        strength=MohrCoulomb(cohesion=20.0,
                                             friction_angle=30.0))
        p.materials.append(soil)
        if with_layer:
            p.boundaries.append(Boundary(
                polyline=Polyline([Vertex(self._JX0, self._JY),
                                   Vertex(self._JX1, self._JY)]),
                btype=BoundaryType.WEAK_LAYER, material_id=soil.id))
        return p

    def test_the_clipping_is_solved_and_not_sampled(self):
        p = self._model(True)
        base = SlipSurface(polyline=Polyline(
            [Vertex(*v) for v in self._BASE]))
        bands = weak_layer_bands(p)
        clipped = WeakLayerSurface(base=base, bands=touching_bands(base, bands))
        xa, xb = self._crossings()
        spans = clipped.spans()
        assert len(spans) == 1
        assert spans[0][0] == pytest.approx(xa, abs=1e-12)
        assert spans[0][1] == pytest.approx(xb, abs=1e-12)

    def test_only_the_real_corners_are_mandatory_cuts(self):
        """The ends of a layer are not kinks where the layer does not win.

        Before this was filtered, a joint reaching from x = 12 to x = 22 over
        a base it only wins between 12.6 and 19.4 reported FOUR mandatory
        cuts. Two of them separate nothing, and the slicer refuses a surface
        that has more mandatory cuts than slices to spend.
        """
        p = self._model(True)
        base = SlipSurface(polyline=Polyline(
            [Vertex(*v) for v in self._BASE]))
        clipped = WeakLayerSurface(
            base=base, bands=touching_bands(base, weak_layer_bands(p)))
        xa, xb = self._crossings()
        kinks = clipped.kinks(*clipped.x_range())
        assert len(kinks) == 2
        assert kinks[0] == pytest.approx(xa, abs=1e-12)
        assert kinks[1] == pytest.approx(xb, abs=1e-12)

    def test_the_clipped_path_answers_like_the_same_path_by_hand(self):
        xa, xb = self._crossings()
        by_hand = SlipSurface(polyline=Polyline([
            Vertex(9.0, 10.0), Vertex(xa, self._JY),
            Vertex(xb, self._JY), Vertex(25.0, 20.0)]))
        f_hand = _fos(self._model(False), by_hand)[0].fos
        f_clip = _fos(self._model(True), SlipSurface(polyline=Polyline(
            [Vertex(*v) for v in self._BASE])))[0].fos
        assert f_clip == pytest.approx(f_hand, rel=1e-11)


# ======================================================================
class TestRuleSeven:
    """Every setting this feature adds has to move the number."""

    _CX, _CY, _R = 18.0, 28.0, 20.0
    _EXT3 = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (25.0, 20.0),
             (10.0, 10.0), (0.0, 10.0)]

    def _arc_x_at(self, y):
        d = math.sqrt(self._R ** 2 - (self._CY - y) ** 2)
        return self._CX - d, self._CX + d

    def _model(self, layers):
        """``layers`` is a list of ``(elevation, (c, phi))``."""
        p = Project("rule seven")
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(*v) for v in self._EXT3], closed=True),
            btype=BoundaryType.EXTERNAL))
        p.materials.append(Material(
            name="Soil", unit_weight=20.0,
            strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
        for y, (c, phi) in layers:
            m = Material(name=f"Joint {y}", unit_weight=20.0,
                         strength=MohrCoulomb(cohesion=c, friction_angle=phi))
            p.materials.append(m)
            x0, x1 = self._arc_x_at(y)
            p.boundaries.append(Boundary(
                polyline=Polyline([Vertex(x0, y), Vertex(x1, y)]),
                btype=BoundaryType.WEAK_LAYER, material_id=m.id))
        return p

    def _circle_fos(self, project, num_slices=40,
                    method="bishop_simplified"):
        s = _Probe(method=get_method(method)(), num_slices=num_slices)
        s._weak_bands_cache = None
        s._pending_notes = []
        with project.regions_frozen():
            res = s.evaluate_circle(
                project, SlipCircle(self._CX, self._CY, self._R))
        return res, s._pending_notes

    def test_a_model_with_no_weak_layers_is_untouched(self):
        """The invariant the whole suite rests on: nothing else may move."""
        bare = self._circle_fos(self._model([]))[0]
        assert isinstance(bare.surface, SlipCircle)

    def test_the_two_policies_disagree_on_a_strong_joint(self):
        strong = (200.0, 45.0)
        bare = self._circle_fos(self._model([]))[0].fos

        p = self._model([(9.0, strong)])
        p.settings.search.weak_layer_handling = WeakLayerHandling.HIGHEST.value
        f_high = self._circle_fos(p)[0].fos

        p = self._model([(9.0, strong)])
        p.settings.search.weak_layer_handling = (
            WeakLayerHandling.AUTO_CASES.value)
        f_auto = self._circle_fos(p)[0].fos

        # Snapping to the layer forces the surface onto a strong joint and
        # RAISES the factor; case generation also tries the surface with the
        # joint off, and that case is the unclipped circle exactly.
        assert f_high > bare * 1.5
        assert f_auto == bare

    def test_case_generation_finds_a_joint_that_snapping_hides(self):
        """Two joints, the lower one weak: 'highest' can never see it."""
        layers = [(9.0, (200.0, 45.0)), (8.5, (1.0, 5.0))]

        p = self._model(layers)
        p.settings.search.weak_layer_handling = WeakLayerHandling.HIGHEST.value
        res_high, _ = self._circle_fos(p)
        names_high = {s.material.name for s in res_high.slices
                      if s.weak_layer_id}

        p = self._model(layers)
        p.settings.search.weak_layer_handling = (
            WeakLayerHandling.AUTO_CASES.value)
        res_auto, _ = self._circle_fos(p)
        names_auto = {s.material.name for s in res_auto.slices
                      if s.weak_layer_id}

        assert names_high == {"Joint 9.0"}
        assert names_auto == {"Joint 8.5"}
        assert res_auto.fos < res_high.fos / 2.0

    def test_suppress_puts_the_bare_number_back(self):
        bare = self._circle_fos(self._model([]))[0].fos
        p = self._model([(9.0, (1.0, 5.0))])
        assert self._circle_fos(p)[0].fos < bare
        for b in p.boundaries:
            if b.btype is BoundaryType.WEAK_LAYER:
                b.suppressed = True
        assert self._circle_fos(p)[0].fos == bare

    def test_the_case_limit_is_never_truncated_in_silence(self):
        p = self._model([(9.0, (1.0, 5.0)), (8.5, (1.0, 5.0))])
        p.settings.search.weak_layer_handling = (
            WeakLayerHandling.AUTO_CASES.value)
        p.settings.search.weak_layer_max_cases_log2 = 1
        _, notes = self._circle_fos(p)
        assert any("weak layers" in n for n in notes), notes

    def test_the_base_angle_ceiling_discards_and_says_so(self):
        """A joint that stops in mid-air leaves a near-vertical base.

        The joint here ends where the arc is far below it, so the clipped
        surface has to fall back to the arc over one slice. With the ceiling
        at its default the surface is refused; raised past that angle, the
        very same surface is analysed.
        """
        p = self._model([])
        m = Material(name="Steep joint", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=1.0, friction_angle=5.0))
        p.materials.append(m)
        # The arc is at y = 8.40 under x = 14, so a joint at y = 12 that
        # simply stops there leaves a 3.6 m drop inside one slice: 82.7 deg.
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(14.0, 12.0), Vertex(22.0, 12.0)]),
            btype=BoundaryType.WEAK_LAYER, material_id=m.id))
        # Ordinary and not Bishop, deliberately: Bishop divides by m_alpha,
        # which collapses towards zero at exactly the angles this ceiling is
        # about, so it answers NaN instead of a number and the two sides of
        # the comparison would not be comparable. The ceiling has to be shown
        # discarding a surface that WOULD otherwise have been answered.
        p.settings.advanced.max_base_angle_deg = 89.9
        allowed, _ = self._circle_fos(
            p, num_slices=60, method="ordinary_fellenius")
        assert allowed is not None and allowed.is_valid
        steepest = math.degrees(max(abs(s.base_angle)
                                    for s in allowed.slices))
        assert steepest > 80.0, steepest

        p.settings.advanced.max_base_angle_deg = 80.0
        refused, notes = self._circle_fos(
            p, num_slices=60, method="ordinary_fellenius")
        assert refused is None or refused.fos != allowed.fos
        assert any("ceiling" in n for n in notes), notes


# ======================================================================
class TestModelLevelWarnings:

    def test_a_layer_with_no_material_is_reported(self):
        p, _ = _project()
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(_JX0, _JY0), Vertex(_JX1, _JY1)]),
            btype=BoundaryType.WEAK_LAYER))
        notes = weak_layer_model_warnings(p)
        assert any("no material" in n for n in notes), notes

    def test_a_layer_above_the_ground_is_reported(self):
        p, _ = _project()
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(12.0, 18.0), Vertex(30.0, 18.0)]),
            btype=BoundaryType.WEAK_LAYER,
            material_id=p.materials[0].id))
        notes = weak_layer_model_warnings(p)
        assert any("above the ground" in n for n in notes), notes

    def test_a_suppressed_layer_is_not_reported(self):
        p, _ = _project()
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(12.0, 18.0), Vertex(30.0, 18.0)]),
            btype=BoundaryType.WEAK_LAYER, suppressed=True))
        assert weak_layer_model_warnings(p) == []


# ======================================================================
class TestSerialisation:

    def test_a_weak_layer_survives_a_round_trip(self, tmp_path=None):
        p, jm = _project(joint=(_JOINT_C, _JOINT_PHI))
        for b in p.boundaries:
            if b.btype is BoundaryType.WEAK_LAYER:
                b.suppressed = True
        clone = Project.from_dict(p.to_dict())
        wl = [b for b in clone.boundaries
              if b.btype is BoundaryType.WEAK_LAYER]
        assert len(wl) == 1
        assert wl[0].material_id == jm.id
        assert wl[0].suppressed is True
        assert len(wl[0].polyline.vertices) == 2

    def test_an_old_file_reads_back_unsuppressed(self):
        """A file written before v0.1.121 carries no ``suppressed`` key."""
        p, _ = _project(joint=(_JOINT_C, _JOINT_PHI))
        data = p.to_dict()
        for b in data["boundaries"]:
            b.pop("suppressed", None)
        clone = Project.from_dict(data)
        wl = [b for b in clone.boundaries
              if b.btype is BoundaryType.WEAK_LAYER]
        assert wl[0].suppressed is False

    def test_the_boundary_type_is_complete(self):
        """Both maps in ``BoundaryType`` index without a fallback."""
        assert BoundaryType.WEAK_LAYER.display_name == "Weak Layer"
        assert BoundaryType.WEAK_LAYER.default_color.startswith("#")
