# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A tensioned reinforcement can only RESIST, and it must do so whichever
orientation the user picks.

Until v0.1.112 ``_support_force_angle`` returned ``axis_angle + pi`` for
``parallel_to_support`` — anchor → face — while the rest of the module
documents, and ``force_at`` computes with, ``head`` = the slope FACE
(that is where the plate is, and where the stripping length ``L_i`` is
measured from). The force therefore came out pointing DOWN the slope, and
the reinforcement LOWERED the factor of safety. Measured on the Amherst
wall of Sheahan (2003), 50° plane, Janbu simplified:

    no bolts                            0.8519
    parallel_to_support                 0.7431   force at  161.5°
    bisector — SoilNail's own default   0.8207   force at  105.8°
    tangent_to_slip                     0.9256   force at   50.0°

Two of the five orientations went uphill and two downhill, and the two
that went downhill were the ones a user gets without touching anything.
``tangent_to_slip`` and ``horizontal`` were right only because they
consult the sliding sense; the parallel one never did, because it does
not need to — it is pure geometry, and it was the geometry that was
reversed.

The reference's own figure settles which way is which: "Applied Force
Orientation options" draws TANGENT, BISECTOR and PARALLEL as three arrows
all leaving the face and heading INTO the slope, and the soil-nail figure
labels ``Li`` from the face to the slip surface and ``Lo`` beyond it.

What this file protects, in four parts:

1. **A physical identity, not a captured number.** A PASSIVE
   reinforcement whose tail is anchored behind the slip surface can only
   add resistance. So for EVERY method and for the four orientations that
   are derived automatically — tangent, parallel, bisector, horizontal —
   the factor of safety must go UP. ``user_defined`` is excluded on
   purpose: the user may legitimately aim the force downhill, and
   ``tests/test_supports_all_methods_v164.py`` already pins that it then
   lowers the factor.
2. **The direction itself, not just its sign.** ``parallel_to_support``
   must equal ``axis_angle_rad()`` exactly, and ``bisector`` must sit
   strictly between tangent and parallel. The signature of the old bug is
   that the first differed from the axis by exactly π.
3. **The Amherst wall itself**, Sheahan (2003) — problem 47 of the
   reference's verification manual. The published number moved to
   ``tests/test_support_projection_v1113.py`` when the projection was
   corrected; what stays here is the identity that no orientation may
   make that wall LESS safe, which is the assertion the old code failed.
4. **The support type's declared defaults reach the instance**, and they
   move the number. ``SupportInstance`` used to be born TANGENT_TO_SLIP +
   ACTIVE regardless of its type, so a ``PileMicropile`` — which declares
   PASSIVE — silently analysed as Active.

v0.1.113 — the type defaults this file asserts changed with it. OGR had
``SoilNail`` on BISECTOR + ACTIVE and ``PileMicropile`` on
PERPENDICULAR_TO_PILE, and the reference documents PARALLEL + PASSIVE and
TANGENTIAL. The expectations here are now that table, page by page.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _fos, _methods, _nail, _project,
)

# The four orientations the program derives on its own. USER_DEFINED is
# the user's own aim, and PERPENDICULAR_TO_PILE belongs to a pile, whose
# force is a shear and not an anchor tension.
_AUTOMATIC = ("TANGENT_TO_SLIP", "PARALLEL_TO_SUPPORT", "BISECTOR",
              "HORIZONTAL")


def _orientations():
    from ogr_core.support import ForceOrientation
    return [(n, getattr(ForceOrientation, n)) for n in _AUTOMATIC]


# ======================================================================
class TestReinforcementCanOnlyResist:
    """Part 1 — the identity that the old code violated by default."""

    def test_every_automatic_orientation_raises_the_factor(self):
        """A passive nail anchored behind the surface, in every method.

        The fixture's nail runs from (43.5, 8.0) on the face to
        (54.0, 8.0) inside the slope, so its tail is behind the arc
        whichever orientation is chosen. Before v0.1.112
        ``parallel_to_support`` and ``bisector`` FAILED this for all
        seven methods.
        """
        bare = _project()
        for oname, orientation in _orientations():
            for mname, cls in _methods():
                f0 = _fos(cls, bare).fos
                f1 = _fos(cls, _project(_nail(orientation=orientation))).fos
                assert math.isfinite(f0) and math.isfinite(f1), (oname, mname)
                assert f1 > f0, f"{oname} / {mname}: {f0:.5f} -> {f1:.5f}"

    def test_the_gain_is_not_iteration_noise(self):
        """Bishop only, but with a size: the four gains must be percent,
        not digits in the sixth decimal."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        f0 = _fos(BishopSimplified, _project()).fos
        for oname, orientation in _orientations():
            f1 = _fos(BishopSimplified,
                      _project(_nail(orientation=orientation))).fos
            gain = (f1 - f0) / f0
            assert gain > 0.005, f"{oname}: only {100 * gain:.4f} %"


# ======================================================================
class TestTheDirectionItself:
    """Part 2 — where the force points, not merely which way it helps."""

    def _angle(self, orientation, slip_tangent, is_l2r=False):
        from ogr_slip2d.support_integration import _support_force_angle
        return _support_force_angle(_nail(orientation=orientation),
                                    slip_tangent, is_l2r)

    def test_parallel_is_the_axis_from_head_to_tail(self):
        from ogr_core.support import ForceOrientation
        nail = _nail()
        got = self._angle(ForceOrientation.PARALLEL_TO_SUPPORT, 0.3)
        assert abs(got - nail.axis_angle_rad()) < 1e-12, (
            f"{math.degrees(got):.3f} vs axis "
            f"{nail.axis_angle_deg():.3f}")

    def test_parallel_is_not_the_axis_reversed(self):
        """The exact fingerprint of the bug: it used to be off by pi."""
        from ogr_core.support import ForceOrientation
        nail = _nail()
        got = self._angle(ForceOrientation.PARALLEL_TO_SUPPORT, 0.3)
        flipped = nail.axis_angle_rad() + math.pi
        gap = math.atan2(math.sin(got - flipped), math.cos(got - flipped))
        assert abs(gap) > 1e-6

    def test_bisector_sits_between_tangent_and_parallel(self):
        from ogr_core.support import ForceOrientation
        for slope in (-0.5, 0.0, 0.4, 1.2):
            tang = self._angle(ForceOrientation.TANGENT_TO_SLIP, slope)
            par = self._angle(ForceOrientation.PARALLEL_TO_SUPPORT, slope)
            bis = self._angle(ForceOrientation.BISECTOR, slope)
            lo, hi = (tang, par) if tang <= par else (par, tang)
            assert lo - 1e-9 <= bis <= hi + 1e-9, (
                f"slope {slope}: {math.degrees(bis):.2f} outside "
                f"[{math.degrees(lo):.2f}, {math.degrees(hi):.2f}]")

    def test_a_pile_shear_opposes_the_movement_however_it_is_drawn(self):
        """``perpendicular_to_pile`` had a free sign and never used it.

        A vertical pile drawn top-to-bottom and the same pile drawn
        bottom-to-top must push the mass the SAME way. Until v0.1.112 the
        second one pushed it downhill.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.support import ForceOrientation, SupportInstance
        from ogr_slip2d.support_integration import _support_force_angle

        def angle(head, tail):
            s = SupportInstance(
                type_id="pile_micropile",
                head=Vertex(*head), tail=Vertex(*tail),
                orientation=ForceOrientation.PERPENDICULAR_TO_PILE)
            # Sliding right-to-left on a base rising to the right: the
            # resisting direction has a positive x component.
            return _support_force_angle(s, 0.5, False)

        down = angle((45.0, 12.0), (45.0, 2.0))
        up = angle((45.0, 2.0), (45.0, 12.0))
        assert math.cos(down) > 0.0, math.degrees(down)
        assert math.cos(up) > 0.0, math.degrees(up)
        gap = math.atan2(math.sin(down - up), math.cos(down - up))
        assert abs(gap) < 1e-12


# ======================================================================
# Part 3 — Sheahan (2003), the Amherst test wall.
#
# Verification problem 47 of the reference manual. A 6 m soil-nailed wall
# in Amherst clay taken to failure by over-excavation; the shotcrete
# facing weighs 14.6 kN/m and is modelled as a line load on the crest.
# Published: Janbu simplified = Janbu corrected = 0.890 on the planar
# surface running (0, 0) -> (6.279, 6.100); Sheahan himself reports 0.887.
#
# The nail head positions and their 18.5 deg dip are read off the
# published figure, so the geometry itself carries a few per cent of
# uncertainty — hence the +-3 % band rather than a tighter one. What the
# test really guards is the sign and the order of magnitude of the
# reinforcement contribution: with the pre-v0.1.112 direction the same
# model returned 0.7431 on a 50 deg plane, BELOW the unreinforced 0.8519.
# ======================================================================
_AMHERST_EXT = [(-6, -2), (11, -2), (11, 6), (0, 6), (0, 0), (-6, 0)]
_AMHERST_HEADS = [(0.0, 4.86), (0.0, 3.39)]
_AMHERST_DIP = 18.5      # degrees below horizontal, into the slope
_AMHERST_LEN = 4.9       # m


def _amherst(with_nails=True, orientation=None):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SoilNail, SupportInstance)

    p = Project("Amherst wall - Sheahan (2003)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in _AMHERST_EXT],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    clay = Material(name="Amherst clay", unit_weight=18.9,
                    sat_unit_weight=18.9,
                    strength=MohrCoulomb(cohesion=25.0, friction_angle=0.0))
    p.materials = [clay]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), clay.id)
    # The shotcrete facing: a concentrated weight per metre of wall.
    p.line_loads = [LineLoad(point=Vertex(0.0, 6.0), magnitude=14.6,
                             orientation=LoadOrientation.VERTICAL)]
    # The crest is on the RIGHT and the wall face on the left.
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT

    if with_nails:
        p.support_types = [SoilNail(tensile_capacity=118.0,
                                    plate_capacity=86.0,
                                    bond_strength=15.0,
                                    out_of_plane_spacing=1.5)]
        a = math.radians(_AMHERST_DIP)
        p.supports = [
            SupportInstance(
                type_id="soil_nail",
                head=Vertex(hx, hy),
                tail=Vertex(hx + _AMHERST_LEN * math.cos(a),
                            hy - _AMHERST_LEN * math.sin(a)),
                force_application=ForceApplication.PASSIVE,
                orientation=orientation or ForceOrientation.TANGENT_TO_SLIP,
                name="row %d" % (i + 1))
            for i, (hx, hy) in enumerate(_AMHERST_HEADS)]
    p.settings.methods.num_slices = 50
    return p


def _amherst_plane(angle_deg=None):
    """The published surface, or a plane through the toe at ``angle_deg``.

    The published endpoint is (6.279, 6.100); this model's crest is at
    y = 6.0, so the published plane is reproduced by its ANGLE — 44.17
    degrees — and not by its endpoint, which would hang above ground.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    if angle_deg is None:
        angle_deg = math.degrees(math.atan2(6.100, 6.279))
    x = 6.0 / math.tan(math.radians(angle_deg))
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(0.0, 0.0), Vertex(x, 6.0)]))


def _amherst_fos(project, method_id, surface=None):
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    surface = surface if surface is not None else _amherst_plane()
    sl = slice_surface(project, surface, num_slices=50)
    assert sl is not None
    return get_method(method_id)().compute_fos(project, surface, sl).fos


class TestAmherstWall:
    """Part 3 — the external number.

    v0.1.113 — the value itself moved to
    ``tests/test_support_projection_v1113.py``, together with the
    orientation the reference documents (parallel) and the projection
    that makes it land. What stays here is the half this file is about:
    that NO orientation may make the wall less safe. That is the
    assertion the pre-v0.1.112 code failed; the published value never
    discriminated it, because it was reached with the one orientation
    that was already right.
    """

    PUBLISHED = 0.890

    def test_the_nails_are_what_moves_it(self):
        """Without them the same plane is well below 1, as the wall was —
        it failed. A test that passed with the reinforcement quietly
        dropped would be worth nothing."""
        bare = _amherst_fos(_amherst(with_nails=False), "janbu_simplified")
        assert 0.80 < bare < 0.87, bare
        assert bare < self.PUBLISHED

    def test_no_orientation_makes_the_wall_less_safe(self):
        """The closure criterion of anomaly A47-1, on the real model."""
        for oname, orientation in _orientations():
            for plane in (40.0, 44.17, 50.0):
                f0 = _amherst_fos(_amherst(with_nails=False),
                                  "janbu_simplified", _amherst_plane(plane))
                f1 = _amherst_fos(_amherst(orientation=orientation),
                                  "janbu_simplified", _amherst_plane(plane))
                assert f1 > f0, f"{oname} @ {plane}: {f0:.4f} -> {f1:.4f}"


# ======================================================================
class TestTheTypeDefaultsReachTheInstance:
    """Part 4 — the second defect, and that it moves the number."""

    def test_each_type_hands_down_its_declared_defaults(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance, support_registry)
        # v0.1.113 — this table is the reference's own, page by page:
        # "always PARALLEL" for the three anchored types, TANGENTIAL by
        # default for a pile because it fails in shear on the slip plane,
        # and a free choice for the two sheet/table types.
        expected = {
            "soil_nail": ForceOrientation.PARALLEL_TO_SUPPORT,
            "grouted_tieback": ForceOrientation.PARALLEL_TO_SUPPORT,
            "grouted_tieback_friction": ForceOrientation.PARALLEL_TO_SUPPORT,
            "end_anchored": ForceOrientation.PARALLEL_TO_SUPPORT,
            "geosynthetic": ForceOrientation.PARALLEL_TO_SUPPORT,
            "user_defined": ForceOrientation.PARALLEL_TO_SUPPORT,
            "pile_micropile": ForceOrientation.TANGENT_TO_SLIP,
            # v0.1.122 — the reference's page for the equivalent-fluid
            # retaining wall states its default outright: "The default
            # force orientation for the Retaining Wall support is
            # Horizontal." It is the only type in the catalogue that
            # defaults there, and it is not decoration: an earth thrust
            # quoted as a fluid pressure is a HORIZONTAL pressure, and
            # projecting it on the wall axis would change the resultant.
            "retaining_wall_efp": ForceOrientation.HORIZONTAL,
            # v0.1.124 - the helical anchor. Its page, unlike the pile's,
            # states no default orientation at all; what declares TANGENT
            # is the reference's OWN verification model for this type,
            # whose support table reads "Tangent to Slip Surface". Chosen
            # before any factor of safety was measured, deliberately: the
            # published number for that model would have been decided by
            # the orientation, and choosing one because it fits is what
            # cost two versions in v0.1.112.
            "helical_anchor": ForceOrientation.TANGENT_TO_SLIP,
        }
        # Every registered type must be listed: a new plugin should make
        # this fail rather than slip through untested.
        assert set(expected) == set(support_registry())
        for type_id, orientation in expected.items():
            s = SupportInstance(type_id=type_id,
                                head=Vertex(0.0, 0.0), tail=Vertex(5.0, -1.0))
            assert s.orientation == orientation, type_id
            cls = support_registry()[type_id]
            assert s.force_application == cls.DEFAULT_APPLICATION, type_id
        # The three the reference defaults to Passive, and that this
        # project declared Active until v0.1.113: an untensioned nail, an
        # untensioned sheet and a pile.
        for type_id in ("soil_nail", "geosynthetic", "pile_micropile"):
            s = SupportInstance(type_id=type_id,
                                head=Vertex(0.0, 0.0), tail=Vertex(0.0, -5.0))
            assert s.force_application == ForceApplication.PASSIVE, type_id
        # And the two it defaults to Active, because a tieback is usually
        # tensioned on installation.
        for type_id in ("grouted_tieback", "end_anchored"):
            s = SupportInstance(type_id=type_id,
                                head=Vertex(0.0, 0.0), tail=Vertex(5.0, -1.0))
            assert s.force_application == ForceApplication.ACTIVE, type_id

    def test_an_unknown_type_still_gets_a_usable_default(self):
        """A project carrying a support whose plugin is not loaded must
        still open."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance)
        s = SupportInstance(type_id="not_a_registered_plugin",
                            head=Vertex(0.0, 0.0), tail=Vertex(1.0, -1.0))
        assert s.orientation == ForceOrientation.TANGENT_TO_SLIP
        assert s.force_application == ForceApplication.ACTIVE

    def test_an_explicit_choice_still_wins(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance)
        s = SupportInstance(type_id="pile_micropile",
                            head=Vertex(0.0, 0.0), tail=Vertex(0.0, -5.0),
                            orientation=ForceOrientation.HORIZONTAL,
                            force_application=ForceApplication.ACTIVE)
        assert s.orientation == ForceOrientation.HORIZONTAL
        assert s.force_application == ForceApplication.ACTIVE

    def test_a_missing_key_inherits_and_a_present_key_does_not(self):
        """Serialisation: ``from_dict`` used to invent "tangent_to_slip"
        for a file that never said so."""
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance)
        raw = {"type_id": "pile_micropile", "head": [0.0, 0.0],
               "tail": [0.0, -5.0]}
        s = SupportInstance.from_dict(raw)
        assert s.orientation == ForceOrientation.TANGENT_TO_SLIP
        assert s.force_application == ForceApplication.PASSIVE
        raw["orientation"] = "perpendicular_to_pile"
        got = SupportInstance.from_dict(raw).orientation
        assert got == ForceOrientation.PERPENDICULAR_TO_PILE

    def test_a_pattern_inherits_the_same_way(self):
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportPattern)
        pat = SupportPattern(type_id="grouted_tieback")
        assert pat.orientation == ForceOrientation.PARALLEL_TO_SUPPORT
        assert pat.force_application == ForceApplication.ACTIVE
        made = pat.generate_along_segment((30.0, 0.0), (50.0, 12.0))
        assert made
        assert all(s.orientation == ForceOrientation.PARALLEL_TO_SUPPORT
                   for s in made)

    def test_inheriting_the_default_moves_the_factor_of_safety(self):
        """Rule 7. Without this half, the inheritance could resolve to
        anything at all and no test would notice: the same nail analysed
        as its type declares must give a DIFFERENT number from the same
        nail forced to the old hard-coded default."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance)
        from ogr_slip2d.methods.bishop import BishopSimplified

        def nail(orientation):
            return SupportInstance(
                type_id="soil_nail",
                head=Vertex(43.5, 8.0), tail=Vertex(54.0, 8.0),
                force_application=ForceApplication.PASSIVE,
                orientation=orientation)

        inherited = _fos(BishopSimplified, _project(nail(None))).fos
        forced = _fos(BishopSimplified,
                      _project(nail(ForceOrientation.TANGENT_TO_SLIP))).fos
        # ``soil_nail`` declares PARALLEL_TO_SUPPORT, which is what the
        # reference says a nail always applies its force along, so the
        # inherited value must differ from the old hard-coded default.
        assert nail(None).orientation == ForceOrientation.PARALLEL_TO_SUPPORT
        assert abs(inherited - forced) > 1e-4, (inherited, forced)
