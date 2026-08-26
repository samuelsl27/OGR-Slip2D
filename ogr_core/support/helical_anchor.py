# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Helical anchor: three failure modes, seven capacities, one envelope.

A helical anchor is a shaft with steel helical plates welded to it. What
makes it different from every other reinforcement in this package is that
its capacity does not vary smoothly along its length: it **steps** as the
slip surface passes each plate, because a plate lies either in the anchored
ground or in the moving mass, and the two sides are counted by different
equations.

Three modes compete at every point of the anchor, and the applied force is
the smallest of the three:

    F1  pullout      the anchored length is dragged out of the slope
    F2  tensile      the shaft itself breaks
    F3  stripping    the slope goes and the anchor stays, tearing off the
                     head assembly

and pullout and stripping are each the smallest of three *failure types*,
which is where the seven come from.

Where each equation comes from
------------------------------
* **Bearing factors.** ``N_q = e^{pi tan phi} tan^2(45 + phi/2)`` is the
  deep-foundation factor of Prandtl (1921) and Reissner (1924), the form
  Meyerhof (1976) tabulates for piles and Perko (2009) uses for helices.
  ``N_c = (N_q - 1) cot phi`` is Prandtl's, quoted in helical-pile practice
  as "the Terzaghi equation"; its limit at ``phi = 0`` is exactly
  ``2 + pi = 5.14159...``.
* **Bearing on one plate**, ``A (1.3 c N_c + q' N_q)``, is Terzaghi (1943)
  for a **circular** footing — ``q_u = 1.3 c N_c + gamma D N_q +
  0.3 gamma B N_gamma`` — with the ``N_gamma`` term dropped, which is
  standard for a thin plate at depth (Perko 2009).
* **Individual bearing** sums that over the plates on the relevant side
  (Perko 2009).
* **Cylindrical shear** is the mechanism of Mitsch and Clemence (1985) for
  sands and Mooney, Adamczak and Clemence (1985) for silts and clays: the
  soil between the plates is mobilised as a cylinder, and the bearing of
  the plate nearest the failure surface is added to the shear on it.
* **Shallow failure** extends that cylinder from the failure surface to the
  farthest plate, which is the breakout mechanism at small embedment
  (Perko 2009).

Two simplifications that belong to the formulation, not to this project
-----------------------------------------------------------------------
They are written here because a reader has to be able to tell what is
published from what is assumed:

1. **No K and no alpha.** The classical cylindrical-shear method carries a
   lateral earth-pressure coefficient in sands and an adhesion factor in
   clays. Here the shear on the cylinder is the SOIL's own strength
   evaluated at the vertical effective stress, which is ``K = alpha = 1``.
   Neither is offered as a parameter because there is no published number
   to validate one against, and an unvalidated knob that moves the answer
   is worse than none.
2. **At phi = 0 this is not the N_c of the anchor literature.** The bearing
   term becomes ``1.3 x 5.14 = 6.68`` times the undrained strength, where
   Mooney and others (1985) use ``N_c = 9`` for deep plates in clay. The
   form above is kept because it is the one the published verification
   numbers were produced with.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from .support import (
    ForceApplication,
    ForceOrientation,
    SupportType,
    register_support,
)

#: Bearing capacity factor for cohesion at ``phi = 0``: Prandtl (1921) gives
#: ``N_c = 2 + pi`` exactly. It is reached here by continuity rather than
#: floored at the rounded 5.14 the reference uses; the two differ by 0.03 %.
NC_AT_ZERO_FRICTION = 2.0 + math.pi


def bearing_factors(phi_rad: float) -> tuple[float, float]:
    """``(N_q, N_c)`` for a friction angle in radians.

    ``N_q = e^{pi tan phi} tan^2(45 + phi/2)`` (Prandtl 1921, Reissner 1924)
    and ``N_c = (N_q - 1) cot phi`` (Prandtl 1921).

    Written with ``expm1`` and ``log1p`` rather than literally, and that is
    not a flourish: ``N_q - 1`` cancels catastrophically as ``phi -> 0``,
    exactly where it has to divide a cotangent that is blowing up. Taking
    logarithms first — ``ln N_q = pi tan(phi) + 2[log1p(t) - log1p(-t)]``
    with ``t = tan(phi/2)``, the tangent half-angle form of
    ``2 ln tan(45 + phi/2)`` — keeps both accurate to the last bit for any
    ``phi > 0``, so the limit ``N_c -> 2 + pi`` arrives by continuity and
    there is no threshold to calibrate. The Ito-Matsui pile of v0.1.123 DID
    need a measured threshold; that cancellation is irreducible and this one
    is removable, which is the whole difference.
    """
    phi = float(phi_rad)
    if not math.isfinite(phi) or phi >= 0.5 * math.pi:
        raise ValueError(f"friction angle out of range: {phi_rad}")
    t = math.tan(phi)
    if t <= 0.0:
        return 1.0, NC_AT_ZERO_FRICTION
    h = math.tan(0.5 * phi)
    log_nq = math.pi * t + 2.0 * (math.log1p(h) - math.log1p(-h))
    return math.exp(log_nq), math.expm1(log_nq) / t


def equivalent_projected_area(
    helix_diameter: float, shaft_width: float, shaft_type: str = "round",
) -> float:
    """Equivalent projected area of one helix, m2.

    The shaft passes through the plate, so what bears is the helix area
    less the shaft area: ``pi w^2 / 4`` for a round shaft of width ``w``
    and ``w^2`` for a square one. Never negative — a shaft as wide as the
    helix leaves no plate, and the caller sees that as zero capacity rather
    than as a negative one.
    """
    d_h = max(0.0, float(helix_diameter))
    w = max(0.0, float(shaft_width))
    a_helix = 0.25 * math.pi * d_h * d_h
    if str(shaft_type).strip().lower() == "square":
        a_shaft = w * w
    else:
        a_shaft = 0.25 * math.pi * w * w
    return max(0.0, a_helix - a_shaft)


def plate_bearing(
    area: float, c: float, phi_rad: float, sigma_v_eff: float,
) -> float:
    """Bearing capacity of one helix, kN.

    ``A (1.3 c N_c + q' N_q)`` — Terzaghi (1943) for a circular footing
    without the self-weight term, as used for helical plates by Perko
    (2009). ``sigma_v_eff`` is the effective vertical stress at the plate.
    """
    n_q, n_c = bearing_factors(phi_rad)
    return max(0.0, area) * (1.3 * max(0.0, c) * n_c
                             + max(0.0, sigma_v_eff) * n_q)


def effective_spacing(
    number_of_helices, spacing: float, total_length: float,
) -> float:
    """Helix spacing actually used, m.

    Impossible input is resolved by letting the NUMBER of helices win: a
    group that does not fit on the anchor is re-spaced at ``L / (n - 1)``,
    which is what the reference documents. A spacing of zero is impossible
    in the same way — the plates would coincide — so it takes the same
    answer.
    """
    n = int(round(number_of_helices))
    if n < 2 or total_length <= 0.0:
        return 0.0
    s = max(0.0, float(spacing))
    if s <= 0.0 or (n - 1) * s > total_length:
        return total_length / (n - 1)
    return s


def helix_distances(
    number_of_helices, spacing: float, total_length: float,
) -> tuple[float, ...]:
    """Distance of each helix from the HEAD, ascending, m.

    The last plate sits at the end of the anchor and the rest march back
    towards the head at the effective spacing, which is how the reference
    generates them from the two inputs.
    """
    n = int(round(number_of_helices))
    if n < 1 or total_length <= 0.0:
        return ()
    s = effective_spacing(n, spacing, total_length)
    return tuple(total_length - (n - 1 - i) * s for i in range(n))


def pullout_capacities(
    cut: float, plates, helix_diameter: float, tau_integral,
) -> tuple[float, float, float]:
    """``(shallow, individual bearing, cylindrical shear)``, kN per anchor.

    ``plates`` is ``(distance from head, bearing capacity kN)`` per helix,
    and ``tau_integral(a, b)`` the integral of the soil shear strength
    along the shaft between two distances, kN/m of perimeter. That integral
    is how "the force contributed by each segment of the effective length
    which passes through different materials" gets in: with one material it
    is ``tau`` times a length, with three it is not.

    Only the plates STRICTLY beyond the cut count. That is not a detail:
    where a plate sits exactly on the slip surface the published table
    counts it on neither side, and its last row — tip plate on the surface,
    pullout capacity zero — is what says so.
    """
    beyond = [(d, q) for d, q in plates if d > cut]
    if not beyond:
        return 0.0, 0.0, 0.0
    perim = math.pi * max(0.0, float(helix_diameter))
    d_near, q_near = min(beyond)
    d_far = max(d for d, _ in beyond)
    shallow = perim * tau_integral(cut, d_far)
    cylindrical = perim * tau_integral(d_near, d_far) + q_near
    individual = sum(q for _, q in beyond)
    return shallow, individual, cylindrical


def stripping_capacities(
    cut: float, plates, helix_diameter: float, tau_integral,
    head_capacity: float,
) -> tuple[float, float, float]:
    """The same three for stripping, kN per anchor.

    Stripping is pullout in reverse: what counts are the plates in the
    MOVING mass, between the head and the cut, and the head assembly
    capacity is added to all three.

    With no plate in the moving mass the three are the head capacity alone.
    The reference's prose says "no capacity is developed" for that case, but
    its own equations, its table and its force diagram all give ``H``; the
    equations win, corroborated twice.
    """
    head = max(0.0, float(head_capacity))
    before = [(d, q) for d, q in plates if d < cut]
    if not before:
        return head, head, head
    perim = math.pi * max(0.0, float(helix_diameter))
    d_far = min(d for d, _ in before)
    d_near, q_near = max(before)
    shallow = perim * tau_integral(d_far, cut) + head
    cylindrical = perim * tau_integral(d_far, d_near) + q_near + head
    individual = sum(q for _, q in before) + head
    return shallow, individual, cylindrical


# ======================================================================
# 9. Helical Anchor
# ======================================================================
@register_support
@dataclass
class HelicalAnchor(SupportType):
    """Screw anchor: a shaft with helical plates, and seven capacities.

    The applied force is ``min(F1, F2, F3) `` per metre of slope, with

        F1 = min(shallow, cylindrical shear, individual bearing) / S
        F2 = T / S
        F3 = [min(the same three, on the moving side) + H] / S

    computed at the point where the slip surface cuts the anchor. See the
    module docstring for where each of the three failure types comes from.

    Two things about the diagram this produces are worth expecting rather
    than discovering. It **steps** at every plate, because the count ``n``
    on each side changes there — the shallow-failure branch stays
    continuous, the other two jump. And it goes to **zero at the tip**: an
    anchor cut beyond its last plate has nothing left to pull out, whatever
    its tendon could carry.

    No **compression capacity**. The reference offers one, defined as the
    tensile calculation with the plate capacity zeroed, but this program
    has no notion of a reinforcement in compression at all: there is
    nowhere to read the sign from. Declaring the parameter would be
    declaring a setting that cannot move the number.
    """

    TYPE_ID: ClassVar[str] = "helical_anchor"
    DISPLAY_NAME: ClassVar[str] = "Helical Anchor"
    DESCRIPTION: ClassVar[str] = (
        "Screw anchor with helical plates. The capacity is computed from "
        "the soil, not entered: shallow failure, cylindrical shear and "
        "individual bearing compete for pullout and for stripping, and "
        "the diagram steps as the slip surface passes each plate."
    )
    # The reference's own verification model for this type declares
    # TANGENT; its page, unlike the pile's, states no default at all.
    # Chosen before measuring anything, on purpose: picking an orientation
    # because it fitted a published number cost two versions in v0.1.112.
    DEFAULT_ORIENTATION = ForceOrientation.TANGENT_TO_SLIP
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    SUPPORTS_SHEAR: ClassVar[bool] = True
    NEEDS_BOND_PROFILE: ClassVar[bool] = True
    PARAMETERS: ClassVar[dict] = {
        "tensile_capacity": (150.0, "kN",
            "Ultimate tensile capacity of the steel shaft, independent of "
            "the helix capacity"),
        "head_assembly_capacity": (100.0, "kN",
            "Load the head assembly connecting the anchor to the slope can "
            "sustain. Called a plate in the other support types; renamed "
            "here so it is not confused with the helical plates."),
        "shear_capacity": (0.0, "kN",
            "Optional force required to shear the anchor across its axis. "
            "0 = disabled."),
        "out_of_plane_spacing": (2.0, "m",
            "Out-of-plane anchor spacing (centre-to-centre)"),
        "shaft_type": ("round", "-",
            "Shaft cross-section: round | square. Only its AREA matters, "
            "which the plate loses to it."),
        "shaft_width": (0.09, "m",
            "Diameter of a round shaft, or side of a square one"),
        "number_of_helices": (3, "-",
            "Number of helical plates along the anchor. The last one sits "
            "at the end of the anchor and the rest march back towards the "
            "head."),
        "average_helix_diameter": (0.25, "m",
            "Average diameter of the helical plates. Should be comfortably "
            "larger than the shaft."),
        "helix_spacing": (1.5, "m",
            "Distance between two plates, assumed equal for all. Design "
            "guides recommend 5 to 12 times the average helix diameter. "
            "Read only when there are two plates or more."),
    }
    PARAMETER_TABS: ClassVar[dict] = {
        "Capacities": ["tensile_capacity", "head_assembly_capacity",
                       "shear_capacity"],
        "Anchor": ["shaft_type", "shaft_width", "number_of_helices",
                   "average_helix_diameter", "helix_spacing"],
        "Geometry": ["out_of_plane_spacing"],
    }
    #: v0.1.124 — a numeric field that another numeric field switches off.
    #: With a single helix there is nothing to space, and the reference
    #: hides the input below two for that reason. Without this the editor
    #: would offer a control that cannot move the number, which is the
    #: defect rule 7 is about, one level up.
    PARAMETER_ENABLED_WHEN: ClassVar[dict] = {
        "helix_spacing": ("number_of_helices", 2),
    }

    tensile_capacity: float = 150.0
    head_assembly_capacity: float = 100.0
    shear_capacity: float = 0.0
    out_of_plane_spacing: float = 2.0
    shaft_type: str = "round"
    shaft_width: float = 0.09
    number_of_helices: int = 3
    average_helix_diameter: float = 0.25
    helix_spacing: float = 1.5

    def __post_init__(self) -> None:
        # A count is a count. JSON round-trips and spin boxes can both hand
        # back 3.0, and a fractional number of plates would silently change
        # where every plate sits.
        try:
            self.number_of_helices = max(1, int(round(
                float(self.number_of_helices))))
        except (TypeError, ValueError):
            self.number_of_helices = 1

    # ------------------------------------------------------------------
    def plate_area(self) -> float:
        """Equivalent projected area of one helix, m2."""
        return equivalent_projected_area(
            self.average_helix_diameter, self.shaft_width, self.shaft_type)

    def interface_tau(self, sigma_v_eff: float, **ctx) -> float:
        """Shear strength of the soil around the shaft, kPa.

        The cylinder that fails in shallow failure and in cylindrical shear
        is a surface THROUGH THE SOIL, not an interface with the steel, so
        what acts on it is the soil's own strength — which is what the
        reference says too ("calculated from the shear strength of the
        surrounding soil"). Asking the material's own model rather than
        rebuilding ``c + sigma tan phi`` is what makes that true for the
        twenty constitutive models and not only for Mohr-Coulomb; for
        Mohr-Coulomb the two are the same number to the last bit, and a
        test pins that.
        """
        from .bond import soil_shear_strength_at

        project = ctx.get("project")
        if project is None:
            return 0.0
        return soil_shear_strength_at(
            project, ctx.get("x", 0.0), ctx.get("y", 0.0), sigma_v_eff,
            depth=ctx.get("depth", 0.0),
            pore_pressure=ctx.get("pore_pressure", 0.0),
            axis_angle_rad=ctx.get("axis_angle_rad", 0.0))

    def station_distances(self, total_length: float) -> tuple:
        """Where the plates are, measured from the head."""
        return helix_distances(
            self.number_of_helices, self.helix_spacing, total_length)

    def station_value(self, sigma_v_eff: float, **ctx) -> float:
        """Bearing capacity of the plate at that station, kN.

        ``c`` and ``phi`` are needed SEPARATELY here — one multiplies
        ``N_c`` and the other decides both factors — so they come from the
        one linearisation this program has,
        ``BishopSimplified._local_c_phi``, taken at the vertical effective
        stress the formulation consumes.
        """
        from .bond import equivalent_c_phi_at

        project = ctx.get("project")
        if project is None:
            return 0.0
        c, tan_phi = equivalent_c_phi_at(
            project, ctx.get("x", 0.0), ctx.get("y", 0.0), sigma_v_eff,
            depth=ctx.get("depth", 0.0),
            pore_pressure=ctx.get("pore_pressure", 0.0),
            axis_angle_rad=ctx.get("axis_angle_rad", 0.0))
        return plate_bearing(self.plate_area(), c, math.atan(tan_phi),
                             max(0.0, sigma_v_eff))

    # ------------------------------------------------------------------
    def capacity_modes(self, distance_from_head: float,
                       total_length: float, bond=None) -> dict:
        s = self.out_of_plane_spacing
        if s <= 0 or total_length <= 0:
            return {}
        cut = max(0.0, min(float(distance_from_head), total_length))
        d_helix = self.average_helix_diameter

        if bond is not None and bond.stations:
            plates = bond.stations
            tau_integral = bond.integral
        else:
            # No project to measure from — a tooltip drawn before the model
            # has geometry. Every term that depends on the soil is zero,
            # and saying so beats inventing a stress state: unlike the two
            # older stress-dependent types, this one has no envelope at
            # zero stress to fall back on, because its cohesion comes from
            # the ground rather than from a parameter of its own.
            plates = tuple((d, 0.0)
                           for d in self.station_distances(total_length))

            def tau_integral(a, b):
                return 0.0

        p_shallow, p_bearing, p_cyl = pullout_capacities(
            cut, plates, d_helix, tau_integral)
        s_shallow, s_bearing, s_cyl = stripping_capacities(
            cut, plates, d_helix, tau_integral,
            self.head_assembly_capacity)
        return {
            "pullout_shallow": p_shallow / s,
            "pullout_cylindrical": p_cyl / s,
            "pullout_bearing": p_bearing / s,
            "tensile": self.tensile_capacity / s,
            "stripping_shallow": s_shallow / s,
            "stripping_cylindrical": s_cyl / s,
            "stripping_bearing": s_bearing / s,
        }

    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        modes = self.capacity_modes(distance_from_head, total_length, bond)
        if not modes:
            return 0.0
        return max(0.0, min(modes.values()))

    def shear_at(self, distance_from_head: float,
                 total_length: float) -> float:
        if self.out_of_plane_spacing <= 0:
            return 0.0
        return max(0.0, self.shear_capacity / self.out_of_plane_spacing)

    def to_dict(self) -> dict:
        d = {"type_id": self.TYPE_ID}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                d[k] = v
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "HelicalAnchor":
        extras = data.get("_extras", {})
        d = {k: v for k, v in data.items()
             if k not in ("type_id", "_extras") and not k.startswith("_")}
        inst = cls(**d)
        if extras:
            inst._apply_extras(extras)
        return inst
