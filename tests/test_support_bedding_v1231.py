# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.231 — a support reads the LOCAL bedding of a material linked to an
anisotropic surface, as every slice base does (defect D228 of the
verification bank).

THE DEFECT. Since v0.1.126 the slicer gives each slice base the angle of
the material's anisotropic surface at the closest point
(``Slice.bedding_angle_deg``), and the models that read a bedding --
Anisotropic Linear and Snowden Modified Anisotropic Linear -- take it
before their own global angle. The two readers of the soil along a support
(``ogr_core.support.bond.soil_shear_strength_at`` and
``equivalent_c_phi_at``) built their ``SliceContext`` without it, so a
geosynthetic in coefficient mode, a helical anchor (shaft and plates) and
an Ito-Matsui pile read the material's GLOBAL angle: the same material was
two different materials, one for the slices and one for the supports.

THE DECISION. The reference's own rule for a geosynthetic -- the angle of
the anisotropy is measured against the support's axis -- is already what
the readers do (``axis_angle_rad``). Reading the local bedding along the
support is a decision of coherence with the slicer, written here: the
surface is found with the same helper (moved, bit for bit, from the slicer
to ``ogr_core.geometry.anisotropic_surface``).

WHAT IS PINNED:

* a straight surface at an angle is EXACTLY the material whose global
  angle is that angle, in both readers, for both models, and through the
  engine for the three supports that read the soil;
* once the surface is linked, the material's global angle is dead: moving
  it moves nothing (on v0.1.230 it moved the supports);
* linking the surface moves the readers' number (rule 7), and the
  parameters are chosen so that it moves it for the horizontal axis of the
  sheet and the anchor AND for the vertical axis of the pile;
* without a link, or with a link to a surface that was deleted, the readers
  answer with the global angle, by the formula written out by hand;
* the axis has no sense: 165 degrees reads what -15 degrees reads.

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

#: The local bedding. The surface is one straight segment inside the model,
#: so every point of the model has this angle as its closest-point angle.
THETA = 30.0
#: The sheet and the anchor: the horizontal axis of the other support tests.
_ACROSS = ((43.5, 8.0), (54.0, 8.0))
#: The pile: from the face (at x = 45 the ground is at y = 9) down through
#: the circle, which it crosses at y = 7.27.
_DOWN = ((45.0, 9.0), (45.0, -5.0))
SIGMA = 60.0


def _surface():
    from ogr_core.geometry import Polyline, Vertex
    c = math.cos(math.radians(THETA))
    s = math.sin(math.radians(THETA))
    return Polyline(vertices=[Vertex(28.0, -6.0),
                              Vertex(28.0 + 20.0 * c, -6.0 + 20.0 * s)],
                    closed=False)


def _theta_drawn() -> float:
    """The angle the surface gives, to the last bit: what a material must
    carry as its global angle to be the same material."""
    from ogr_core.geometry.anisotropic_surface import segment_angle_deg
    return segment_angle_deg(_surface(), 0)


def _al(bedding=0.0):
    """B = 80 so that 60 degrees from the bedding (the pile's axis against
    the surface) is still in the transition, and 90 (against the global
    angle) is not: with B = 40 both would be the rock mass."""
    from ogr_core.materials.builtin_models import AnisotropicLinear
    return AnisotropicLinear(c1=5.0, phi1=15.0, c2=20.0, phi2=35.0,
                             bedding_angle=bedding, A=10.0, B=80.0)


def _snowden(bedding=10.0):
    """Non-symmetric on purpose, with B2 = 85 for the same reason as B in
    ``_al``; the functions are those of ``test_snowden_reference_v1229``."""
    import copy

    from ogr_core.materials.builtin_models import (
        SnowdenModifiedAnisotropicLinear)
    from test_snowden_reference_v1229 import BEDDING, ROCK_MASS
    return SnowdenModifiedAnisotropicLinear(
        bedding_angle=bedding, A1=5.0, B1=25.0, A2=15.0, B2=85.0,
        bedding=copy.deepcopy(BEDDING), rock_mass=copy.deepcopy(ROCK_MASS))


_MODELS = (("anisotropic_linear", _al), ("snowden", _snowden))


def _geo():
    """A sheet whose pull-out BEHIND the circle governs: with a tensile
    capacity of 50 the tensile mode does, the soil it reads decides nothing
    and the identities below would hold for a support that never read it."""
    from ogr_core.support import Geosynthetic
    return Geosynthetic(tensile_capacity=500.0, pullout_mode="coefficient",
                        coefficient_of_interaction=0.8,
                        connection_strength=1000.0)


def _anchor():
    from ogr_core.support import HelicalAnchor
    return HelicalAnchor(out_of_plane_spacing=2.0)


def _pile():
    from ogr_core.support import PileMicropile
    return PileMicropile(failure_mode="ito_matsui", out_of_plane_spacing=1.5,
                         pile_diameter=0.5)


#: (name, type, ends, orientation) -- the three supports that read the soil.
def _supports():
    from ogr_core.support import ForceOrientation as O
    return (("geosynthetic", _geo, _ACROSS, O.TANGENT_TO_SLIP),
            ("helical_anchor", _anchor, _ACROSS, O.TANGENT_TO_SLIP),
            ("ito_matsui_pile", _pile, _DOWN, O.PERPENDICULAR_TO_PILE))


def _model(strength, *, link=True, dangling=False, support=None):
    """The slope of ``test_supports_all_methods_v164`` in one bedded
    material, with the surface drawn (linked or not) and at most one
    support ``(type factory, ends, orientation)``."""
    from ogr_core.geometry import Boundary, BoundaryType, Vertex
    from ogr_core.support import ForceApplication, SupportInstance
    p = _project(None)
    mat = p.materials[0]
    mat.strength = strength
    b = Boundary(polyline=_surface(), btype=BoundaryType.ANISOTROPIC_SURFACE)
    p.add_boundary(b)
    if link:
        mat.anisotropic_surface_id = b.id
    elif dangling:
        mat.anisotropic_surface_id = "a-boundary-that-was-deleted"
    p.support_types, p.supports = [], []
    if support is not None:
        factory, ends, orientation = support
        st = factory()
        p.support_types = [st]
        p.supports = [SupportInstance(
            type_id=st.TYPE_ID, head=Vertex(*ends[0]), tail=Vertex(*ends[1]),
            force_application=ForceApplication.PASSIVE,
            orientation=orientation, type_ref=st.id)]
    return p


def _fos(p):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    return BishopSimplified().compute_fos(p, _circle(), sl).fos


def _tau(p, x, y, axis_deg):
    from ogr_core.support.bond import soil_shear_strength_at
    return soil_shear_strength_at(p, x, y, SIGMA,
                                  axis_angle_rad=math.radians(axis_deg))


def _c_tan(p, x, y, axis_deg):
    from ogr_core.support.bond import equivalent_c_phi_at
    return equivalent_c_phi_at(p, x, y, SIGMA,
                               axis_angle_rad=math.radians(axis_deg))


def _al_by_hand(delta_deg):
    """Mercer's linear transition for ``_al``, written out."""
    t = min(1.0, max(0.0, (delta_deg - 10.0) / (80.0 - 10.0)))
    c = 5.0 * (1.0 - t) + 20.0 * t
    tan_phi = (math.tan(math.radians(15.0)) * (1.0 - t)
               + math.tan(math.radians(35.0)) * t)
    return c + SIGMA * tan_phi


# ======================================================================
class TestTheReadersSeeTheSurface:
    """At a point of the sheet (horizontal axis) and of the pile (vertical
    axis): linked, the material is the one whose global angle is the
    surface's -- bit for bit -- and not the one it carries."""

    POINTS = (((50.0, 8.0), 0.0), ((45.0, 6.0), -90.0))

    def test_the_strength_reader(self):
        for name, make in _MODELS:
            linked = _model(make(), link=True)
            same = _model(make(bedding=_theta_drawn()), link=False)
            unlinked = _model(make(), link=False)
            for (x, y), axis in self.POINTS:
                got = _tau(linked, x, y, axis)
                assert got == _tau(same, x, y, axis), (name, axis)
                old = _tau(unlinked, x, y, axis)
                assert abs(got - old) > 1e-3 * old, (name, axis, got, old)

    def test_the_linearised_reader(self):
        for name, make in _MODELS:
            linked = _model(make(), link=True)
            same = _model(make(bedding=_theta_drawn()), link=False)
            unlinked = _model(make(), link=False)
            for (x, y), axis in self.POINTS:
                got = _c_tan(linked, x, y, axis)
                assert got == _c_tan(same, x, y, axis), (name, axis)
                old = _c_tan(unlinked, x, y, axis)
                assert got != old, (name, axis, got)

    def test_anisotropic_linear_by_hand(self):
        """The horizontal axis is 30 degrees from the surface and the pile
        60: t = 20/70 and 50/70 of Mercer's transition."""
        p = _model(_al(), link=True)
        for (x, y), axis, delta in (((50.0, 8.0), 0.0, THETA),
                                    ((45.0, 6.0), -90.0, 90.0 - THETA)):
            got = _tau(p, x, y, axis)
            want = _al_by_hand(delta)
            assert math.isclose(got, want, rel_tol=1e-12), (axis, got, want)

    def test_the_global_angle_is_dead_once_linked(self):
        for name, make in _MODELS:
            a = _model(make(bedding=0.0), link=True)
            b = _model(make(bedding=70.0), link=True)
            for (x, y), axis in self.POINTS:
                assert _tau(a, x, y, axis) == _tau(b, x, y, axis), name
                assert _c_tan(a, x, y, axis) == _c_tan(b, x, y, axis), name


class TestTheEngineSeesTheSurface:
    """Through Bishop, for the three supports that read the soil."""

    def test_linked_is_the_material_at_that_angle(self):
        wrong = []
        for name, make in _MODELS:
            for sname, factory, ends, orientation in _supports():
                sup = (factory, ends, orientation)
                linked = _fos(_model(make(), link=True, support=sup))
                same = _fos(_model(make(bedding=_theta_drawn()),
                                   link=False, support=sup))
                if linked != same:
                    wrong.append((name, sname, linked, same))
        assert not wrong, wrong

    def test_the_global_angle_moves_nothing_once_linked(self):
        wrong = []
        for name, make in _MODELS:
            for sname, factory, ends, orientation in _supports():
                sup = (factory, ends, orientation)
                a = _fos(_model(make(bedding=0.0), link=True, support=sup))
                b = _fos(_model(make(bedding=70.0), link=True, support=sup))
                if a != b:
                    wrong.append((name, sname, a, b))
        assert not wrong, wrong

    def test_every_support_is_priced(self):
        """The control: each support moves F, so the identities above are
        not the identity of a support that contributes nothing."""
        for name, make in _MODELS:
            bare = _fos(_model(make(), link=True))
            for sname, factory, ends, orientation in _supports():
                got = _fos(_model(make(), link=True,
                                  support=(factory, ends, orientation)))
                assert abs(got - bare) > 1e-4 * bare, (name, sname, got,
                                                       bare)


class TestWithoutASurface:

    def test_no_link_and_a_deleted_surface_read_the_global_angle(self):
        from ogr_core.geometry.anisotropic_surface import bedding_angle_at
        for kw in (dict(link=False), dict(link=False, dangling=True)):
            p = _model(_al(bedding=0.0), **kw)
            assert bedding_angle_at(p, p.materials[0], 50.0, 8.0) is None
            for (x, y), axis, delta in (((50.0, 8.0), 0.0, 0.0),
                                        ((45.0, 6.0), -90.0, 90.0)):
                got = _tau(p, x, y, axis)
                want = _al_by_hand(delta)
                assert math.isclose(got, want, rel_tol=1e-12), (kw, got)

    def test_a_deleted_surface_is_no_surface_bit_for_bit(self):
        for name, make in _MODELS:
            gone = _model(make(), link=False, dangling=True)
            none = _model(make(), link=False)
            for (x, y), axis in TestTheReadersSeeTheSurface.POINTS:
                assert _tau(gone, x, y, axis) == _tau(none, x, y, axis)
                assert _c_tan(gone, x, y, axis) == _c_tan(none, x, y, axis)

    def test_no_material_has_no_bedding(self):
        from ogr_core.geometry.anisotropic_surface import bedding_angle_at
        p = _model(_al(), link=True)
        assert bedding_angle_at(p, None, 50.0, 8.0) is None
        assert bedding_angle_at(p, p.materials[0], 50.0, 8.0) == \
            _theta_drawn()

    def test_the_slicer_reads_the_moved_helper(self):
        from ogr_core.geometry.anisotropic_surface import material_surfaces
        from ogr_slip2d.slicer import _anisotropic_surfaces
        p = _model(_al(), link=True)
        assert _anisotropic_surfaces(p) == material_surfaces(p)
        assert list(material_surfaces(p)) == [p.materials[0].id]


class TestTheAxisHasNoSense:

    def test_165_degrees_reads_what_minus_15_reads(self):
        for name, make in _MODELS:
            p = _model(make(), link=True)
            a = _tau(p, 50.0, 8.0, 165.0)
            b = _tau(p, 50.0, 8.0, -15.0)
            assert math.isclose(a, b, rel_tol=1e-12), (name, a, b)
            # The pair comes from a numerical slope of tau(sigma), which
            # turns the last bit of the folded angle (165 - 30 and -15 - 30
            # round differently) into ~1e-12 of tan phi and, times sigma,
            # ~1e-11 of c: 1e-9 is the linearisation, not the model.
            ca, cb = _c_tan(p, 50.0, 8.0, 165.0), _c_tan(p, 50.0, 8.0, -15.0)
            assert all(math.isclose(u, v, rel_tol=1e-9)
                       for u, v in zip(ca, cb)), (name, ca, cb)
