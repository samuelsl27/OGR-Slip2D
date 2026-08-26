# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A per-unit-length quantity sampled along a reinforcement, and its integral.

v0.1.123 — the module was born (v0.1.116) carrying only ONE thing, the
interface shear strength of a pullout law, and its names still say so. It
now also carries the Ito and Matsui (1975) lateral force per unit depth of
an Ito-Matsui pile, which is not a strength and is not an interface. What
the machinery actually does is general and worth naming as such: a type
declares ``NEEDS_BOND_PROFILE``, the engine samples ``interface_tau`` along
the support ONCE PER ANALYSIS, and ``force_at`` integrates the samples from
the head to the cut. Everything below about WHY the profile can be built
once and reused for every trial surface applies unchanged to both.

v0.1.124 — and to a third thing, which is not per unit length at all: the
``stations``, discrete points where a type needs a value that exists only
there. A helical anchor's plates bear at their own positions and nowhere
between them, so no per-segment average can stand in for them. They ride in
the same object because they are built by the same pass, from the same
stress state, and because ``force_at(d, L, bond)`` then keeps its signature
for all nine types.

v0.1.116 — until this version every stress-dependent pullout law in
:mod:`ogr_core.support.support` was a placeholder: ``tau = self.adhesion``
in ``GroutedTiebackFriction`` and in ``Geosynthetic``'s Mohr-Coulomb mode,
``coefficient * 10.0`` and ``friction_factor * 10.0`` in the other two.
The friction angles were declared, editable and serialised — and read by
nobody, so the answer was BINARY: zero resistance with no adhesion, the
whole tensile capacity with any.

What was missing is not a formula but a NUMBER: the effective normal
stress on the reinforcement. It cannot come from the slice context — that
is evaluated at a slice BASE, per trial surface — because the stress along
a reinforcement depends only on what lies above it, and therefore not on
the trial surface at all. That is the whole reason a profile can be built
once and reused for every surface of a search.

The stress law
--------------
The pullout resistance of a buried sheet or grouted bond is the integral
of an interface shear strength over the embedded area:

    tau(s) = a + sigma'_n(s) · tan(delta)                     (linear)

which is Mohr-Coulomb applied to the soil/reinforcement interface — the
classical bond formulation for geotextiles in Jewell (1996) — or

    tau(s) = a_inf · sigma'_n · tan(phi_0)
             / (a_inf + sigma'_n · tan(phi_0))             (hyperbolic)

from the study of geosynthetic interface behaviour by Esterhuizen, Filz
and Duncan (2001), where ``a_inf`` is the limiting strength as
sigma_n → ∞ and ``phi_0`` the tangent friction angle at sigma_n = 0.
Those two parameters do NOT mean what the same names mean in the linear
envelope, which is exactly the confusion that paper warns about.

The normal stress
-----------------
sigma'_n is taken as the VERTICAL effective stress at the reinforcement:
the weight of everything above it, plus the vertical component of any
external load acting on the ground above it, minus the pore pressure.
For reinforcement laid other than horizontally a hydrostatic state is
assumed, so the normal stress is still the vertical one.

That identification is not this project's invention. FHWA-NHI-10-024
(Berg, Christopher and Samtani 2009), Eq. 3-2, writes the pullout
resistance per unit width of reinforcement as

    P_r = F* · alpha · sigma'_v · L_e · C

with sigma'_v the effective vertical stress at the soil-reinforcement
interfaces, ``L_e`` the embedment length **in the resisting zone behind
the failure surface**, and ``C`` the effective unit perimeter — ``C = 2``
for sheets, because a sheet has two faces. Three separate things this
module needs are settled by that one published equation: that the stress
is the effective vertical one, that the pullout length is the one BEHIND
the surface (not the shorter of the two sides, which is what this project
computed until v0.1.116), and the factor of two.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..project import Project
    from .support import SupportInstance, SupportType


# Number of segments a reinforcement is cut into to integrate tau along
# it. The stress varies with depth, with the layers above and with the
# water table, so the integral has to be numerical. Fifty is the
# subdivision the reference interface documents, and it is fine enough
# that halving the step is invisible in the published verification
# factors — the check is in ``tests/test_support_pullout_v1116.py``.
DEFAULT_SEGMENTS = 50


@dataclass(frozen=True)
class BondProfile:
    """Interface shear strength sampled along a support, head to tail.

    ``tau[i]`` is the strength at the midpoint of segment ``i``, in kPa,
    and the segments are equal and cover ``[0, total_length]`` measured
    from the HEAD — the end at the slope face, which is the end
    :class:`~ogr_core.support.support.SupportInstance` measures
    ``distance_from_head`` from.

    ``cum[i]`` is the integral of tau from the head to the START of
    segment ``i``, so ``cum[-1]`` is the integral over the whole length.
    Keeping the running sum instead of re-adding on every query is what
    makes :meth:`integral` O(1): a grid search asks for it once per
    support per trial surface per method.
    """

    total_length: float
    tau: tuple[float, ...]
    cum: tuple[float, ...]
    #: v0.1.124 — DISCRETE points along the support, ``(distance from the
    #: head, value)``, for the part of a capacity that is not a per-unit-length
    #: quantity at all: the bearing capacity of a helical anchor's plates,
    #: which exists at the plates and nowhere else. Sampled by the same pass,
    #: with the same stress state, once per analysis. Empty for every type
    #: that has none, which is all of them but one.
    stations: tuple[tuple[float, float], ...] = ()

    # ------------------------------------------------------------------
    @classmethod
    def from_samples(cls, tau, total_length: float,
                     stations=()) -> "BondProfile":
        """Build a profile from per-segment strengths, head to tail."""
        st = tuple((float(d), float(v)) for d, v in stations)
        tau_t = tuple(float(t) for t in tau)
        if not tau_t or total_length <= 0.0:
            return cls(max(0.0, float(total_length)), (), (0.0,), st)
        step = total_length / len(tau_t)
        cum = [0.0]
        run = 0.0
        for t in tau_t:
            run += t * step
            cum.append(run)
        return cls(float(total_length), tau_t, tuple(cum), st)

    @classmethod
    def uniform(cls, tau: float, total_length: float) -> "BondProfile":
        """A constant-strength profile.

        The closed-form cases — a horizontal sheet under level ground, a
        hand calculation, the analytical identities the tests are
        anchored to — all have uniform tau, and one segment represents
        them exactly rather than approximately.
        """
        return cls.from_samples((tau,), total_length)

    # ------------------------------------------------------------------
    def integral(self, a: float, b: float) -> float:
        """Integral of tau ds over ``[a, b]``, in kN per metre of width.

        Linear inside a segment, so the answer is CONTINUOUS in both
        limits. That continuity is not cosmetic: it is what makes the
        available support force vary smoothly as a trial surface sweeps
        along the reinforcement, instead of stepping every time the
        intersection crosses a sample point.
        """
        n = len(self.tau)
        if n == 0 or self.total_length <= 0.0:
            return 0.0
        lo = max(0.0, min(a, b))
        hi = min(self.total_length, max(a, b))
        if hi <= lo:
            return 0.0
        return self._upto(hi) - self._upto(lo)

    def _upto(self, x: float) -> float:
        """Integral from the head to ``x``, with ``x`` already clamped."""
        n = len(self.tau)
        step = self.total_length / n
        i = min(n - 1, int(x / step))
        return self.cum[i] + self.tau[i] * (x - i * step)

    def moment(self, a: float, b: float) -> float:
        """First moment ``integral of s*tau ds`` over ``[a, b]``.

        v0.1.123 — what the *location of force* setting needs: divided by
        :meth:`integral` it is the centroid of the mobilised diagram,
        measured from the head. It is written with the SAME piecewise
        convention as :meth:`integral` — tau constant inside a segment —
        so the quotient is guaranteed to land inside ``[a, b]`` instead of
        drifting outside it when the two disagree about the last partial
        segment.
        """
        n = len(self.tau)
        if n == 0 or self.total_length <= 0.0:
            return 0.0
        lo = max(0.0, min(a, b))
        hi = min(self.total_length, max(a, b))
        if hi <= lo:
            return 0.0
        return self._moment_upto(hi) - self._moment_upto(lo)

    def _moment_upto(self, x: float) -> float:
        """First moment from the head to ``x``, with ``x`` already clamped."""
        n = len(self.tau)
        step = self.total_length / n
        i = min(n - 1, int(x / step))
        run = 0.0
        for j in range(i):
            lo_j, hi_j = j * step, (j + 1) * step
            run += self.tau[j] * 0.5 * (hi_j * hi_j - lo_j * lo_j)
        lo_i = i * step
        return run + self.tau[i] * 0.5 * (x * x - lo_i * lo_i)

    @property
    def total(self) -> float:
        """Integral over the whole length."""
        return self.cum[-1] if self.cum else 0.0

    def mean_tau(self) -> float:
        """Length-weighted mean strength, kPa. For reporting only."""
        if self.total_length <= 0.0:
            return 0.0
        return self.total / self.total_length


# ======================================================================
# Building a profile from a project
# ======================================================================
def sigma_v_effective_at(
    project: "Project", x: float, y: float,
    ground_y: Optional[float] = None,
) -> tuple[float, float, float]:
    """Effective vertical stress at (x, y): ``(sigma_v_eff, u, depth)``.

    All in kPa except the depth, in metres. The soil column above the
    point is weighed band by band, cut at every material boundary and at
    the water table, so a point under several layers or under a partly
    submerged column gets the unit weight the stability analysis itself
    would give each band. External distributed loads acting above the
    point add their vertical pressure, and the pore pressure at the point
    is subtracted.

    The depth below ground comes back too, because the strength models
    that want a context want it, and computing it here saves asking the
    ground surface for the same abscissa twice.
    """
    # Deferred, and reaching into the analysis package on purpose:
    # ``_column_weight`` IS the band decomposition the slice weight uses,
    # and two versions of "what is above this point" would eventually
    # disagree about a water table or a saturated unit weight. The same
    # deferred import is already made for the same reason in
    # ``ogr_core/hydraulic/excess_pore_pressure.py``. There are now three
    # readers of that decomposition and it deserves lifting into ogr_core
    # proper — but it is the slicer's hot loop, so not in the version that
    # is changing the pullout law.
    from ogr_slip2d.slicer import _column_weight, _surface_pressure_at

    from ..geometry import Vertex
    from ..geometry.ground import envelope_y_at, ground_surface
    from ..hydraulic.pore_pressure import pore_pressure_at

    if ground_y is None:
        ext = project.external_boundary()
        if ext is not None:
            ground_y = envelope_y_at(ground_surface(ext), x)
    if ground_y is None or ground_y <= y:
        # Above ground, or no boundary to measure from: no overburden.
        # Distributed loads below still act, which is how a surcharge at
        # the crest reaches reinforcement laid immediately under it.
        depth = 0.0
        sigma_v = 0.0
    else:
        depth = ground_y - y
        # v0.1.120 — ``_column_weight`` now returns the top of the band the
        # bottom of the column sits in as well; here only the weight is
        # wanted. See ``_layer_top_at`` below for the reader of the other.
        sigma_v = _column_weight(project, x, y, ground_y, 1.0)[0]

    sigma_v += _surface_pressure_at(project, x)

    mat = project.material_at(x, y)
    u = pore_pressure_at(project, Vertex(x, y), mat, ground_surface_y=ground_y)
    return max(0.0, sigma_v - u), u, depth


def build_bond_profile(
    project: "Project",
    support: "SupportInstance",
    stype: "SupportType",
    segments: int = DEFAULT_SEGMENTS,
) -> BondProfile:
    """Sample the interface strength along ``support``, head to tail.

    The support type decides the law — see
    :meth:`~ogr_core.support.support.SupportType.interface_tau` — and this
    function supplies the stress state that law needs at each sample. A
    type whose capacity does not depend on stress declares
    ``NEEDS_BOND_PROFILE = False`` and gets a profile of zeros it never
    reads, which keeps the cost off the four types that are constants or
    tables.
    """
    length = support.length()
    if length <= 0.0 or segments < 1:
        return BondProfile.uniform(0.0, max(0.0, length))
    if not getattr(stype, "NEEDS_BOND_PROFILE", False):
        return BondProfile.uniform(0.0, length)

    hx, hy = support.head.x, support.head.y
    ux = (support.tail.x - hx) / length
    uy = (support.tail.y - hy) / length
    step = length / segments
    axis_angle = support.axis_angle_rad()

    def _state(s: float):
        x = hx + ux * s
        y = hy + uy * s
        sigma_v_eff, u, depth = sigma_v_effective_at(project, x, y)
        return sigma_v_eff, dict(
            project=project, x=x, y=y, pore_pressure=u, depth=depth,
            axis_angle_rad=axis_angle)

    taus = []
    for i in range(segments):
        sigma_v_eff, ctx = _state((i + 0.5) * step)
        taus.append(stype.interface_tau(sigma_v_eff, **ctx))

    # v0.1.124 — the discrete half. A helical anchor needs the bearing
    # capacity AT each of its plates, which no per-segment average can
    # stand in for: the plates sit at fixed distances along the anchor and
    # their positions have nothing to do with the sampling step. They are
    # gathered here, in the same pass and from the same stress state, so
    # that ``force_at`` keeps its signature and the cache stays a single
    # object built once per analysis.
    stations = []
    for d in stype.station_distances(length):
        d = float(d)
        sigma_v_eff, ctx = _state(min(max(0.0, d), length))
        stations.append((d, stype.station_value(sigma_v_eff, **ctx)))

    return BondProfile.from_samples(taus, length, stations)


def _layer_top_at(project: "Project", x: float, y: float):
    """Top of the material band containing ``(x, y)``, or None.

    The same decomposition the slice weight uses — see the note inside
    :func:`sigma_v_effective_at` about why this package reaches into the
    slicer for it instead of keeping a second opinion about what is above
    a point.
    """
    from ogr_slip2d.slicer import _column_weight

    from ..geometry.ground import envelope_y_at, ground_surface

    ext = project.external_boundary()
    if ext is None:
        return None
    ground_y = envelope_y_at(ground_surface(ext), x)
    if ground_y is None or ground_y <= y:
        return ground_y
    return _column_weight(project, x, y, ground_y, 1.0)[1]


def soil_shear_strength_at(
    project: "Project", x: float, y: float, sigma_v_eff: float,
    depth: float = 0.0, pore_pressure: float = 0.0,
    axis_angle_rad: float = 0.0,
) -> float:
    """Shear strength of the material at (x, y) under sigma'_v, in kPa.

    Used by the coefficient-of-interaction law, which takes a fraction of
    the SURROUNDING SOIL's own strength rather than describing the
    interface directly. Asking the material's own strength model is what
    makes that work for the twenty models this project implements instead
    of only for Mohr-Coulomb — and it is also the honest answer for the
    ones where an "equivalent cohesion and friction angle" would otherwise
    have to be invented.

    For an anisotropic model the plane of interest is the reinforcement's
    own plane, so the support axis angle is passed as the base angle.

    v0.1.120 — the two fields the slicer measures for the depth-dependent
    undrained models are measured here too, and only when the material's
    own model declares that it reads them. Leaving them empty would have
    let a sheet buried in a clay whose strength grows with depth take its
    fraction of the strength at the TOP of that clay, all along the sheet,
    without saying so.
    """
    from ..materials.strength_model import SliceContext

    mat = project.material_at(x, y)
    if mat is None or getattr(mat, "strength", None) is None:
        return 0.0
    strength = mat.strength
    layer_top_y = None
    if getattr(strength, "NEEDS_LAYER_TOP", False):
        layer_top_y = _layer_top_at(project, x, y)
    slope_distance = None
    if getattr(strength, "NEEDS_SLOPE_DISTANCE", False):
        ext = project.external_boundary()
        if ext is not None:
            from ..geometry.ground import distance_to_profile, ground_surface
            slope_distance = distance_to_profile(ground_surface(ext), x, y)
    ctx = SliceContext(
        base_angle_rad=axis_angle_rad,
        sigma_v_eff=sigma_v_eff,
        depth=depth,
        pore_pressure=pore_pressure,
        y_base=y,
        layer_top_y=layer_top_y,
        slope_distance=slope_distance,
    )
    try:
        tau = strength.shear_strength_ctx(sigma_v_eff, ctx)
    except Exception:  # noqa: BLE001 - a plugin must not kill an analysis
        return 0.0
    # Infinite Strength is a modelling device for rigid bedrock, not a
    # promise that a sheet buried in it can never be pulled out. Letting
    # the infinity through would make the pullout mode vanish from the
    # minimum without saying so.
    if not math.isfinite(tau):
        return 0.0
    return max(0.0, tau)


class _PointAsSlice:
    """The handful of attributes ``_local_c_phi`` reads off a slice.

    v0.1.123 — an Ito-Matsui pile needs the soil's cohesion and friction
    angle at a point along its shaft, and the reference itself says "the
    soil cohesion and friction angle (or equivalent values)". This program
    has exactly ONE linearisation of a strength envelope,
    ``BishopSimplified._local_c_phi``, and it is the one the nine methods
    use; writing a second one here would be a second opinion about the
    twenty constitutive models, and the two would drift apart.

    So the point is dressed as the only argument that function knows how to
    read. The fields are the ones it actually touches, and nothing else:
    ``weight/width`` is how it recovers the total vertical stress, and the
    two ``top``/``base`` pairs are how it recovers the depth. A test pins
    this to ``_local_c_phi`` so that the dressing cannot silently rot.
    """

    __slots__ = ("width", "weight", "pore_pressure", "base_angle",
                 "base_y_left", "base_y_right", "top_y_left", "top_y_right",
                 "layer_top_y", "slope_distance", "suction_cohesion")

    def __init__(self, y, sigma_v_eff, pore_pressure, depth,
                 axis_angle_rad, layer_top_y, slope_distance):
        self.width = 1.0
        self.weight = sigma_v_eff + pore_pressure
        self.pore_pressure = pore_pressure
        self.base_angle = axis_angle_rad
        self.base_y_left = self.base_y_right = y
        self.top_y_left = self.top_y_right = y + max(0.0, depth)
        self.layer_top_y = layer_top_y
        self.slope_distance = slope_distance
        # Not measured along a support: the slicer computes the matric
        # suction term at a slice BASE, from that slice's own state. Left
        # at zero rather than guessed, and said out loud because a soil
        # with real suction will give a slightly lower c here than the
        # same soil gives the slip surface that crosses it.
        self.suction_cohesion = 0.0


def equivalent_c_phi_at(
    project: "Project", x: float, y: float, sigma_v_eff: float,
    depth: float = 0.0, pore_pressure: float = 0.0,
    axis_angle_rad: float = 0.0,
) -> tuple[float, float]:
    """``(c, tan phi)`` of the material at (x, y), linearised at sigma'_v.

    The equivalent Mohr-Coulomb pair a formulation written for ``c`` and
    ``phi`` needs when the material is not Mohr-Coulomb. Linearised at the
    VERTICAL effective stress, which is the stress that formulation
    consumes, so the tangent is taken where it is going to be used.

    Returns ``(0.0, 0.0)`` for a material with no strength model and for
    Infinite Strength, for the same reason
    :func:`soil_shear_strength_at` does: rigid bedrock is a modelling
    device, and letting an infinity through here would turn into an
    infinite pile force.
    """
    import math as _math

    from ogr_slip2d.methods.bishop import BishopSimplified

    mat = project.material_at(x, y) if project is not None else None
    if mat is None or getattr(mat, "strength", None) is None:
        return 0.0, 0.0
    strength = mat.strength
    layer_top_y = None
    if getattr(strength, "NEEDS_LAYER_TOP", False):
        layer_top_y = _layer_top_at(project, x, y)
    slope_distance = None
    if getattr(strength, "NEEDS_SLOPE_DISTANCE", False):
        ext = project.external_boundary()
        if ext is not None:
            from ..geometry.ground import distance_to_profile, ground_surface
            slope_distance = distance_to_profile(ground_surface(ext), x, y)
    stand_in = _PointAsSlice(y, sigma_v_eff, pore_pressure, depth,
                             axis_angle_rad, layer_top_y, slope_distance)
    try:
        c, tan_phi = BishopSimplified._local_c_phi(
            stand_in, mat, max(0.0, sigma_v_eff))
    except Exception:  # noqa: BLE001 - a plugin must not kill an analysis
        return 0.0, 0.0
    if not (_math.isfinite(c) and _math.isfinite(tan_phi)) or c >= 1e11:
        return 0.0, 0.0
    return max(0.0, c), max(0.0, tan_phi)
