# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A reinforcement enters the ratio methods through its projection ON THE
BASE, and every ratio method uses the same two equations.

The reference resolves a support into exactly two numbers — ``T_N``
normal to the slice base and ``T_S`` tangential to it — and writes one
pair of equations for Ordinary/Fellenius, Bishop and both Janbus:

    Active   F = (R + T_N·tan φ') / (D − T_S)
    Passive  F = (R + T_N·tan φ' + T_S) / D

From v0.1.64 to v0.1.112 Janbu obeyed the first term and not the second:
``T_N·tan φ'`` was taken from the reference, while ``T_S`` was replaced
by the HORIZONTAL projection of the support force. The same equation,
one term from the source and the other substituted. The stated reason
was that "Janbu balances horizontal forces", and the changelog that
introduced it contradicted itself in the same page by listing Janbu
among the methods that use the equations above.

The arithmetic does not support the substitution either. With φ' = 0 a
Janbu slice term is c'·b/cos²α = c'·l/cos α and the driving term is
W·tan α = W·sin α/cos α: both sides are SHEAR quantities carrying a
common 1/cos α. A horizontal force H fits that weighting by accident —
its driving shear H·cos α divided by cos α gives H back, which is why
the seismic and water terms are summed raw — but a support at an
arbitrary angle does not.

v0.1.142 — THE SECOND HALF OF THAT SENTENCE WAS WRONG, AND THIS FILE SAID SO

``T_S`` was right and ``T_S/cos α`` was ALSO right: Janbu owes the base
projection AND the ``sec α`` weighting, and it owes them together with a
third change this file never considered — the support's normal part
belongs inside ``n_α`` instead of bolted on outside it. v0.1.113 measured
``T_S/cos α`` on its own, which is two of the three, and recorded it as
"four times worse". Two thirds of a correction is not a hypothesis about
the third.

What settled it is not a published value at all. The six failure surfaces
of problem 48 are PLANES, and on a plane the sliding mass is a single free
body, so limit equilibrium has one answer and every method that closes
global force equilibrium owes it:

    ACTIVE   F = ( c'·L + (W·cos α + T_N)·tan φ' ) / (W·sin α − T_S)
    PASSIVE  F = ( c'·L + (W·cos α + T_N)·tan φ' + T_S ) / (W·sin α)

The two Corps of Engineers, Lowe-Karafiath and Ordinary reproduce that to
the last digit on these very planes; until v0.1.142 Janbu was the only one
that could not, and nobody had ever run the other five here. The full
derivation and its fixture are in ``tests/test_janbu_wedge_v1142.py``.

WHAT THIS FILE PINS, AND WHY IT IS SIX POINTS AND NOT ONE

The strongest anchor is problem 48, because it publishes the factor of
safety for SIX failure-plane angles of the same wall. That matters: a
formulation error leaves a TREND across the six, and a geometry error does
not. What v0.1.113 did not use is that the manual publishes **two**
columns for those six planes — its own and Sheahan's original — and they
disagree with EACH OTHER by up to 4.7 % (1.123 vs 1.176 at 45°; 0.923 vs
0.887 at 70°), which is more than the gap being adjudicated. Comparing
against one of them and calling the result an anchor was the mistake.

Applying that trend argument to both columns:

    error vs             Slide's column        Sheahan's column
                        mean    range         mean    range
    horizontal (v112)  14.96 %   16.2         (worse everywhere)
    T_S only (v113)     1.75 %    4.76         1.38 %    4.27
    the wedge (v142)    7.95 %    8.29         7.73 %  **1.13**

The corrected formulation leaves a residual against the ORIGINAL SOURCE
that is nearly constant — −7.9 %, −7.5 %, −7.1 %, −7.5 %, −8.1 %, −8.2 %
— which is the geometry signature, and this wall's geometry is exactly
what the manual does not publish: the seven nail lengths and their 10° dip
are read off figures 48.1 and 48.2. The formulation it replaces had a
4.3-point trend against the same column. It also reproduces Sheahan's
SHAPE: his column falls monotonically to 70° and the manual's ticks back
up 0.001 at the last point, and the corrected curve falls monotonically.

Three hypotheses were measured and rejected, and are recorded here so they
are not tried again blind:

  * **Passive divided by F** — Method B of Duncan & Wright (2005) factors
    the reinforcement force by F alongside the soil strength, and this
    project's own docstring claimed OGR did so. It improves problem 48
    (0.71 %) but breaks problem 85, which is the reference's Active vs
    Passive case and is itself taken from Duncan & Wright: the published
    passive value goes from +0.23 % to −5.91 %. Rejected on that, and
    ``TestPassiveIsNotDividedByF`` below is what keeps it rejected.
  * **The horizontal projection** — mean 14.96 %, worst +23.6 %. Still
    refuted, by a wider margin than ever; nothing here reopens it.
  * **"The nails are simply stronger than modelled"** — the obvious
    reading of a flat −7.7 % offset, and it does NOT survive measurement.
    Scaling all three nail capacities by one factor moves the mean against
    the manual's column to 1.97 % at ×1.20, but the residual against
    Sheahan's column goes from a 1.13-point range to 4.82, and by ×1.40 to
    9.99. No single scalar flattens both columns, so the cause of the
    offset is named as unresolved rather than explained away.
"""
from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_support_orientation_v1112 import (  # noqa: E402
    _amherst, _amherst_fos, _amherst_plane,
)
from test_supports_all_methods_v164 import _circle, _nail, _project  # noqa: E402


def _amherst_fos_tol(project, method_id, surface, tolerance=1e-10):
    """``_amherst_fos`` with the convergence tolerance under control."""
    return _fos_on(project, surface, method_id, tolerance=tolerance)


def _fos_on(project, surface, method_id, num_slices=50, tolerance=None):
    """``tolerance`` overrides the class default of 1e-3 ABSOLUTE, which on
    a factor of safety near 1 is 1e-3 relative — bigger than the closed
    form below discriminates. Only the wedge test passes it."""
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None
    kwargs = ({} if tolerance is None
              else {"tolerance": tolerance, "max_iterations": 400})
    return get_method(method_id)(**kwargs).compute_fos(
        project, surface, sl).fos


# ======================================================================
# Problem 48 — the Clouterre test wall, Sheahan (2003).
#
# A 7 m nailed wall in Fontainebleau sand, failed by saturating the
# backfill, built for the French national soil-nailing project. The
# manual tabulates the factor of safety for six planar failure surfaces
# through the toe, 45° to 70°, and prints two independent columns: its
# own and Sheahan's.
#
# Seven rows of PASSIVE soil nails at 10° below horizontal, out-of-plane
# spacing 1.5 m, tensile 15 kN, plate 59 kN, bond 7.5 kN/m. Lengths
# 6/8/7.5/8/8/8/6 m. The shotcrete facing weighs 13.2 kN/m and is a line
# load on the wall face. The nail lengths and their dip are NOT published
# — they are read off the figures — which is exactly why the test is
# written as a trend over six angles and not as one tight number.
# ======================================================================
_CLOUTERRE_EXT = [(0, 0), (20, 0), (20, 1), (12, 1), (12, 8), (0, 8)]
_CLOUTERRE_FILAS = [(7.5, 6.0), (6.5, 8.0), (5.5, 7.5), (4.5, 8.0),
                    (3.5, 8.0), (2.5, 8.0), (1.5, 6.0)]
_CLOUTERRE_DIP = 10.0
#: The manual's own column...
_CLOUTERRE_PUBLICADO = {45: 1.123, 50: 1.043, 55: 0.989,
                        60: 0.945, 65: 0.922, 70: 0.923}
#: ...and Sheahan's, which the manual prints beside it. They disagree with
#: each other by up to 4.7 %, so neither is a per-cent anchor on its own.
#: Kept as data because the SHAPE of the residual against each is what
#: v0.1.142 used, and a single column cannot show that.
_CLOUTERRE_SHEAHAN = {45: 1.176, 50: 1.070, 55: 0.989,
                      60: 0.929, 65: 0.893, 70: 0.887}

#: Every method that closes global force equilibrium owes the wedge on a
#: plane. Four of them reproduce it exactly and have done so all along;
#: they are what the Janbu column is now checked against.
_WEDGE_METHODS = ("corps_engineers_1", "corps_engineers_2",
                  "lowe_karafiath", "ordinary_fellenius")


def _clouterre(with_nails=True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SoilNail, SupportInstance)

    p = Project("Clouterre wall - Sheahan (2003)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in _CLOUTERRE_EXT],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    sand = Material(name="Fontainebleau sand", unit_weight=20.0,
                    sat_unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=3.0, friction_angle=38.0))
    p.materials = [sand]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), sand.id)
    p.line_loads = [LineLoad(point=Vertex(12.0, 8.0), magnitude=13.2,
                             orientation=LoadOrientation.VERTICAL)]
    # The face is on the RIGHT and the retained ground on the left, so
    # the mass slides towards +x.
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT

    if with_nails:
        p.support_types = [SoilNail(tensile_capacity=15.0,
                                    plate_capacity=59.0,
                                    bond_strength=7.5,
                                    out_of_plane_spacing=1.5)]
        a = math.radians(_CLOUTERRE_DIP)
        p.supports = [
            SupportInstance(
                type_id="soil_nail",
                head=Vertex(12.0, y),
                tail=Vertex(12.0 - L * math.cos(a), y - L * math.sin(a)),
                force_application=ForceApplication.PASSIVE,
                orientation=ForceOrientation.PARALLEL_TO_SUPPORT,
                name="row %d" % (i + 1))
            for i, (y, L) in enumerate(_CLOUTERRE_FILAS)]
    p.settings.methods.num_slices = 50
    return p


def _clouterre_plane(angle_deg):
    """A plane through the toe (12, 1) outcropping on the crest y = 8."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    dx = 7.0 / math.tan(math.radians(angle_deg))
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(12.0 - dx, 8.0), Vertex(12.0, 1.0)]))


class TestClouterreWall:
    """Six published points, and the trend is the measurement."""

    def _curve(self, project):
        return {a: _fos_on(project, _clouterre_plane(a), "janbu_simplified")
                for a in _CLOUTERRE_PUBLICADO}

    def _errors(self, got, column):
        return {a: 100.0 * (got[a] - column[a]) / column[a] for a in column}

    def test_the_six_planes_reproduce_the_closed_form_wedge(self):
        """The anchor, and it is not a published number.

        These six surfaces are PLANES, so the sliding mass is one free body
        and limit equilibrium has a single answer. Four methods reproduce
        it here to six digits and have always done so; before v0.1.142
        Janbu was the only one that could not, and nobody had run the other
        four on these planes. This is what replaced the ±2.5 % band against
        a column that its own manual contradicts by 4.7 %.
        """
        p = _clouterre()
        for a in sorted(_CLOUTERRE_PUBLICADO):
            surf = _clouterre_plane(a)
            ref = [_fos_on(p, surf, mid, tolerance=1e-10)
                   for mid in _WEDGE_METHODS]
            spread = max(ref) - min(ref)
            assert spread < 1e-6 * ref[0], (a, _WEDGE_METHODS, ref)
            janbu = _fos_on(p, surf, "janbu_simplified", tolerance=1e-10)
            # The term this discriminates was worth 1.8 % to 8.7 % on these
            # six planes, so 1e-6 clears it by four decades.
            assert abs(janbu - ref[0]) < 1e-6 * ref[0], (a, janbu, ref[0])

    def test_the_residual_against_the_original_source_is_flat(self):
        """A formulation error leaves a trend across the six angles and a
        geometry error does not — the argument that decided v0.1.113, now
        applied to the column v0.1.113 did not use.

        Against Sheahan (2003) the corrected formulation runs −7.9, −7.5,
        −7.1, −7.5, −8.1, −8.2 %: a 1.1-point range. The formulation it
        replaces ran −4.2 to +0.1, a 4.3-point range. The offset itself is
        not explained — see the third rejected hypothesis in the header —
        but its flatness is what says it is not the equations.
        """
        errs = self._errors(self._curve(_clouterre()), _CLOUTERRE_SHEAHAN)
        spread = max(errs.values()) - min(errs.values())
        detail = "  ".join(f"{a}:{errs[a]:+.2f}%" for a in sorted(errs))
        assert spread < 2.0, f"range {spread:.2f} points — {detail}"
        assert all(e < 0.0 for e in errs.values()), detail

    def test_the_curve_still_brackets_both_published_columns(self):
        """Not agreement — a bracket. Neither column can serve as a
        per-cent anchor while they differ by 4.7 % from each other, but
        both still catch a formulation error of the size the horizontal
        projection had (worst +23.6 %)."""
        got = self._curve(_clouterre())
        for name, column, bound in (("manual", _CLOUTERRE_PUBLICADO, 13.0),
                                    ("Sheahan", _CLOUTERRE_SHEAHAN, 10.0)):
            errs = self._errors(got, column)
            worst = max(abs(e) for e in errs.values())
            detail = "  ".join(f"{a}:{got[a]:.4f}({errs[a]:+.2f}%)"
                               for a in sorted(errs))
            assert worst < bound, f"{name}: worst {worst:.2f} % — {detail}"

    def test_the_curve_has_its_minimum_where_the_published_ones_do(self):
        """The shape is a check on the reinforcement that no single number
        can give. The manual's column bottoms out at 65° and ticks back up
        0.001 at 70°; Sheahan's falls all the way. The corrected curve
        falls all the way too, which is Sheahan's shape and not the
        manual's — recorded, because before v0.1.142 it had the manual's.
        """
        got = self._curve(_clouterre())
        assert min(got, key=got.get) in (60, 65, 70)
        assert got[45] > got[60], got
        ordered = [got[a] for a in sorted(got)]
        assert ordered == sorted(ordered, reverse=True), got

    def test_without_nails_the_wall_is_far_from_the_published_curve(self):
        """Guards the whole file against the reinforcement quietly
        vanishing: unreinforced, this wall is nowhere near 1."""
        bare = self._curve(_clouterre(with_nails=False))
        for a, pub in _CLOUTERRE_PUBLICADO.items():
            assert bare[a] < pub, (a, bare[a], pub)
        assert bare[70] < 0.6, bare[70]


# ======================================================================
class TestAmherstWallWithTheDocumentedOrientation:
    """Problem 47, with the orientation the reference documents.

    The reference's page for this support type says the applied force is
    ALWAYS parallel to the soil nail. v0.1.112 declared tangent-to-slip
    instead, because with the horizontal projection that was the only
    option inside ±3 %. With the projection corrected the documented
    orientation is also the one that lands, and it still is.

    v0.1.142 — the published surface here is a PLANE too, so the closed
    form binds it exactly as it binds problem 48, and the wall is φ' = 0
    clay so the wedge reduces to ``(c'·L + T_S)/(W·sin α)``. Six methods
    now return 0.903592 on it, digit for digit. That moved the comparison
    against the published value from −0.27 % to +1.53 %, and the band here
    was widened from 1 % to 3 % to match — not to accommodate the change,
    but because 1 % was never defensible: the nail head positions and the
    18.5° dip are read off a figure, and the header of
    ``test_support_orientation_v1112`` says so and asks for ±3 %. A band
    tighter than the fixture's own stated uncertainty was measuring the
    formulation against a coincidence.
    """

    PUBLISHED = 0.890
    #: Sheahan (2003) for the same wall. The manual prints both.
    PUBLISHED_SOURCE = 0.887
    #: The fixture's own stated geometric uncertainty; see the class
    #: docstring and the header of ``test_support_orientation_v1112``.
    TOL_PCT = 3.0

    def _p(self):
        from ogr_core.support import ForceOrientation
        return _amherst(orientation=ForceOrientation.PARALLEL_TO_SUPPORT)

    def test_both_janbus_reproduce_the_published_value(self):
        for method_id in ("janbu_simplified", "janbu_corrected"):
            f = _amherst_fos(self._p(), method_id)
            err = 100.0 * (f - self.PUBLISHED) / self.PUBLISHED
            assert abs(err) < self.TOL_PCT, (
                f"{method_id}: {f:.4f} ({err:+.2f} %)")

    def test_it_also_reproduces_the_original_source(self):
        """Sheahan (2003) reports 0.887 for the same wall."""
        f = _amherst_fos(self._p(), "janbu_simplified")
        err = 100.0 * (f - self.PUBLISHED_SOURCE) / self.PUBLISHED_SOURCE
        assert abs(err) < self.TOL_PCT, f"{f:.4f} ({err:+.2f} %)"

    def test_six_methods_agree_on_this_plane_to_the_last_digit(self):
        """The anchor that does not depend on a figure being read right.

        The surface is a plane, so the wedge binds every method that closes
        global force equilibrium — and with φ' = 0 the closed form is just
        ``(c'·L + T_S)/(W·sin α)``. Before v0.1.142 Janbu stood apart from
        the other five here by 1.8 %, and no test in the suite looked.
        """
        p = self._p()
        surf = _amherst_plane()
        got = {mid: _amherst_fos_tol(p, mid, surf)
               for mid in _WEDGE_METHODS + ("janbu_simplified",
                                            "janbu_corrected")}
        lo, hi = min(got.values()), max(got.values())
        assert hi - lo < 1e-6 * lo, got

    def test_the_other_orientations_are_further_away(self):
        """Not a preference: with the projection corrected, the
        documented orientation is the closest of the four, which is the
        opposite of what v0.1.112 measured."""
        from ogr_core.support import ForceOrientation
        parallel = abs(_amherst_fos(self._p(), "janbu_simplified")
                       - self.PUBLISHED)
        for name in ("TANGENT_TO_SLIP", "BISECTOR", "HORIZONTAL"):
            other = abs(
                _amherst_fos(_amherst(orientation=getattr(
                    ForceOrientation, name)), "janbu_simplified")
                - self.PUBLISHED)
            assert other > parallel, (name, other, parallel)


# ======================================================================
# Problem 85 — Duncan & Wright (2005), figure 6.34.
#
# A saturated clay slope with one support at mid-height, capacity
# 9000 lb/ft, analysed twice: Active and Passive. It is the reference's
# own case for that distinction, and the original is the textbook that
# defines Method A and Method B, so it is the right place to pin both
# the two numbers and their ORDER.
# ======================================================================
_DW_CIRCLE = (15.446, 37.624, 27.594)   # the panel of figure 85.2
_DW_ACTIVE = 1.531
_DW_PASSIVE = 1.324


def _duncan_wright(application):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceOrientation, SupportInstance,
                                  UserDefined)

    ext = Polyline(vertices=[Vertex(*v) for v in
                             ((15, 10), (57, 10), (57, 30), (25, 30))],
                   closed=True)
    ext.ensure_ccw()
    p = Project("Duncan & Wright fig. 6.34")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    clay = Material(name="clay", unit_weight=98.0, sat_unit_weight=98.0,
                    strength=MohrCoulomb(cohesion=350.0, friction_angle=0.0))
    p.materials = [clay]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), clay.id)
    # A one-point capacity table is a constant force, which is how the
    # statement gives it: "a support of capacity 9000 lb/ft".
    p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                   points=[(0.0, 9000.0)])]
    p.supports = [SupportInstance(
        type_id="user_defined",
        head=Vertex(20.0, 20.0), tail=Vertex(57.0, 20.0),
        force_application=application,
        orientation=ForceOrientation.HORIZONTAL, name="tieback")]
    p.settings.methods.num_slices = 50
    return p


def _dw_circle():
    from ogr_slip2d.surface import SlipCircle
    cx, cy, r = _DW_CIRCLE
    return SlipCircle(centre_x=cx, centre_y=cy, radius=r)


class TestPassiveIsNotDividedByF:
    """The hypothesis that must stay rejected.

    Factoring the passive reinforcement by F — Method B as Duncan &
    Wright state it — improves the Clouterre curve and problem 54, and
    was the reading of this module's own docstring until v0.1.113. It
    fails here, on the reference's own Active/Passive case: the published
    passive value moves from +0.23 % to −5.91 %. These two assertions are
    what stops it being reintroduced on the strength of the other two
    problems.
    """

    def test_the_two_published_numbers(self):
        from ogr_core.support import ForceApplication
        for name, application, pub in (
                ("active", ForceApplication.ACTIVE, _DW_ACTIVE),
                ("passive", ForceApplication.PASSIVE, _DW_PASSIVE)):
            f = _fos_on(_duncan_wright(application), _dw_circle(),
                        "bishop_simplified")
            err = 100.0 * (f - pub) / pub
            assert abs(err) < 2.0, f"{name}: {f:.4f} vs {pub} ({err:+.2f} %)"

    def test_passive_is_below_active_by_the_published_margin(self):
        """The reference states the ordering as a rule — "Passive support
        will always give a lower Factor of Safety than Active" — and here
        it also publishes the size of the gap, 13.5 %."""
        from ogr_core.support import ForceApplication
        fa = _fos_on(_duncan_wright(ForceApplication.ACTIVE), _dw_circle(),
                     "bishop_simplified")
        fp = _fos_on(_duncan_wright(ForceApplication.PASSIVE), _dw_circle(),
                     "bishop_simplified")
        assert fp < fa, (fp, fa)
        gap = 100.0 * (fa - fp) / fa
        published_gap = 100.0 * (_DW_ACTIVE - _DW_PASSIVE) / _DW_ACTIVE
        assert abs(gap - published_gap) < 3.0, (gap, published_gap)


# ======================================================================
class TestTheProjectionIsTheBaseNotTheHorizontal:
    """The mechanism itself, without a published value.

    Two identities that hold whatever the geometry, and that the
    horizontal projection violated. They are written against the base
    angle the slicer actually reports, so they do not depend on a
    hand-computed surface:

      1. A support force aimed ALONG the base contributes its whole
         magnitude to T_S and nothing to T_N.
      2. A support force PERPENDICULAR to the base contributes nothing to
         T_S — it presses instead. With the horizontal projection it
         contributed its full horizontal component, which for this
         fixture is 87 % of the force.
    """

    def _at(self, angle_deg):
        """(terms, effect, slice) for a nail aimed at ``angle_deg``."""
        from ogr_core.support import ForceOrientation
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import (compute_support_effects,
                                                    resolve_support_terms)
        p = _project(_nail(orientation=ForceOrientation.USER_DEFINED,
                           angle_deg=angle_deg))
        sl = slice_surface(p, _circle(), num_slices=25)
        assert sl is not None
        eff = compute_support_effects(p, _circle(), sl)
        assert len(eff) == 1
        s_list = sl.slices if hasattr(sl, "slices") else sl
        return (resolve_support_terms(p, _circle(), sl, 1.0),
                eff[0], s_list[eff[0].slice_index])

    def _base_angle_deg(self):
        return math.degrees(self._at(0.0)[2].base_angle)

    def test_a_force_along_the_base_is_all_tangential(self):
        a = self._base_angle_deg()
        terms, eff, _s = self._at(a)
        F = eff.force_magnitude
        assert F > 1.0, F
        assert abs(abs(terms.total_passive_t()) - F) < 1e-6 * F, (
            terms.total_passive_t(), F)
        assert abs(sum(terms.n_press)) < 1e-6 * F, sum(terms.n_press)

    def test_a_force_perpendicular_to_the_base_adds_nothing_tangential(self):
        a = self._base_angle_deg()
        terms, eff, _s = self._at(a - 90.0)
        F = eff.force_magnitude
        assert abs(terms.total_passive_t()) < 1e-6 * F,             terms.total_passive_t()
        # Not silently lost: it goes into the normal, where tan phi picks
        # it up. This is the half of the equation Janbu already had right.
        assert abs(sum(terms.n_press)) > 0.99 * F, sum(terms.n_press)
        # And this is what the horizontal projection used to hand Janbu
        # for the very same force: on this fixture the base sits at
        # 25.9 deg, so a force perpendicular to it points at -64.1 deg
        # and still has 44 % of its magnitude in x. Janbu counted all of
        # that as resisting T_S, and the correct answer is zero.
        assert abs(eff.force_h) > 0.4 * F, eff.force_h

    def test_the_terms_no_longer_carry_a_horizontal_pair(self):
        """The field is gone, not merely unused: leaving it would invite
        routing a method through it again."""
        from ogr_slip2d.support_integration import SupportTerms
        assert not hasattr(SupportTerms, "total_passive_h")
        assert "h_passive" not in SupportTerms.__dataclass_fields__
