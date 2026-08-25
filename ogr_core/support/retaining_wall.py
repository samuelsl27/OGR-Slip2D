# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Retaining wall defined by an equivalent fluid pressure (EFP) profile.

Its own module rather than another block in ``support.py`` — which is
already 1400 lines — following the extension pattern documented in
``docs/plugins.md``. The registration happens on import, and
``ogr_core/support/__init__.py`` is what imports it: importing any
submodule of the package runs that first, so the type is in the registry
by the time anything can ask for it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .support import (ForceApplication, ForceOrientation, SupportType,
                      register_support)


@register_support
@dataclass
class RetainingWallEFP(SupportType):
    """Retaining wall whose capacity is a PRESSURE PROFILE over its height.

    The engineer receives the thrust on a wall as an *equivalent fluid
    pressure*: a unit weight in force per volume which, multiplied by the
    retained height, gives the pressure at the base. The concept and its
    tabulated coefficients are Terzaghi & Peck (1967), *Soil Mechanics in
    Engineering Practice*, 2nd ed., Wiley, Art. 46; the trapezoidal
    envelope is the apparent-pressure diagram of the same book, Art. 48.

    This class derives no pressure. It INTEGRATES the profile the user
    supplies, from the crest down to the point where the slip surface
    crosses the wall, and reports the resultant per metre of wall::

        force_at(d) = ∫₀ᵈ p(x) dx

    so a surface clipping the wall near the crest mobilises little and one
    passing under the toe mobilises the whole diagram. That dependence on
    WHERE the surface cuts is the only thing separating a wall from an
    anchor of fixed capacity, and it is why this is a support type rather
    than a load.

    Four profile shapes, with ``s`` the relative distance from the crest
    (0 at the top, 1 at the toe) and ``L`` the wall length:

    ``uniform``      p(s) = ``pressure``
    ``triangular``   p(s) = ``efp`` · L · s, i.e. zero at the crest
    ``trapezoidal``  ramp 0 → ``efp``·L over (1−f)/2, flat over f, ramp → 0
                     over (1−f)/2, with f = ``distributed_over`` / 100
    ``custom``       the ``points`` table, linearly interpolated

    The trapezoid is SYMMETRIC — both ramps the same length, pressure zero
    at both ends. That is not an inference from its area, which would be
    the same with the flat part anywhere: it is read off the dimensioned
    figure the reference publishes, 0.2H / 0.6H / 0.2H with EFP·H on the
    flat. The area alone cannot decide a shape, and the whole point of this
    class is the PARTIAL integral.

    Every shape has a closed primitive, so ``force_at`` is exact rather
    than quadrature. That matters: the two published check values this was
    written against — 312.5 for a 5-unit wall reaching 125, and 2000 for a
    10-unit wall with EFP 25 spread over 60 % — are exact, and a quadrature
    would make them approximate for no gain.

    NO OUT-OF-PLANE SPACING. The other seven types divide by one because
    they are discrete elements; a wall is continuous and its pressure is
    already per metre of wall. A parameter permanently holding 1 would be a
    control that cannot move the result, which this project treats as worse
    than no control at all. The consequence is deliberate: a support
    PATTERN of this type would stack N copies of the same pressure, so
    ``ALLOWS_PATTERN`` refuses it rather than answering it.
    """

    TYPE_ID: ClassVar[str] = "retaining_wall_efp"
    DISPLAY_NAME: ClassVar[str] = "Retaining Wall (EFP)"
    DESCRIPTION: ClassVar[str] = (
        "Retaining wall defined by an equivalent fluid pressure profile. "
        "The profile is integrated from the crest down to the slip "
        "surface, so the force depends on where the surface cuts the wall."
    )
    DEFAULT_ORIENTATION = ForceOrientation.HORIZONTAL
    DEFAULT_APPLICATION = ForceApplication.ACTIVE
    NEEDS_BOND_PROFILE: ClassVar[bool] = False

    #: The profile runs from the CREST down, and ``force_at`` never sees
    #: the instance — it cannot tell which end is higher. A wall drawn
    #: bottom-to-top would put the peak pressure at the crest and return a
    #: plausible, wrong number, which is the failure mode v0.1.112 and
    #: v0.1.113 spent two versions on with the support ORIENTATION. So the
    #: engine measures from the higher end for any type setting this. An
    #: advisory would not do: the wrong number would still be on screen.
    MEASURED_FROM_TOP: ClassVar[bool] = True
    #: Edited through a table widget rather than a spin box, like
    #: ``UserDefined.points``. Declared here so the dialog needs no second
    #: hard-wired ``if TYPE_ID == ...``.
    TABLE_FIELD: ClassVar[str] = "points"
    #: Group-box title for that table.
    TABLE_TITLE: ClassVar[str] = "Custom Pressure Profile (points)"
    #: Column headers for that table, and the range each column accepts.
    TABLE_COLUMNS: ClassVar[tuple] = (
        ("Relative distance from crest", 0.0, 1.0),
        ("Pressure", -1e9, 1e9),
    )
    #: A row of walls would stack the same pressure N times over.
    ALLOWS_PATTERN: ClassVar[bool] = False

    PARAMETERS: ClassVar[dict] = {
        "profile_type": ("triangular", "",
            "Shape of the pressure profile over the height of the wall"),
        "pressure": (20.0, "kPa",
            "Uniform profile only: the pressure, constant over the whole "
            "height of the wall"),
        "efp": (25.0, "kN/m³",
            "Triangular and trapezoidal profiles: equivalent fluid "
            "pressure, i.e. pressure per unit length of wall. Multiplied "
            "by the wall length it gives the peak pressure"),
        "distributed_over": (60.0, "%",
            "Trapezoidal profile only: percentage of the wall height taken "
            "by the flat part. The rest is split evenly between the two "
            "ramps"),
        "force_location": ("intersection", "",
            "Where the resultant acts: at the point the slip surface cuts "
            "the wall, or at the centroid of the pressure diagram above "
            "that point. Only the methods that write a moment equation "
            "can tell the two apart"),
    }
    #: Which parameters the chosen shape actually uses. The dialog reads
    #: this to grey out the rest: three of the four fields do nothing for
    #: any given shape, and a field that is editable but inert is the same
    #: defect as an inert setting, only harder to spot.
    PARAMETER_USED_BY: ClassVar[dict] = {
        "uniform": ("pressure",),
        "triangular": ("efp",),
        "trapezoidal": ("efp", "distributed_over"),
        "custom": (),
    }

    profile_type: str = "triangular"
    #: ``intersection`` or ``centroid``. The default is the intersection
    #: because that is what the other seven types do and what the engine
    #: already assumes — the reference introduces the option with the words
    #: "as with other support options", which says the same. The centroid
    #: is the physically truer place for the resultant of a pressure
    #: diagram, and it is what the published verification of this type
    #: uses, but a new type silently disagreeing with the other seven would
    #: be a worse surprise than an option the user has to pick.
    #:
    #: IT ONLY MOVES THE NUMBER IN FOUR OF THE NINE METHODS. Moving a force
    #: leaves a pure couple, and a couple has nowhere to go in a method
    #: that writes only force equilibrium: the two Janbu and the three
    #: marching methods cannot honour it. The analysis says so rather than
    #: letting the setting look universal.
    force_location: str = "intersection"
    pressure: float = 20.0            # kPa, uniform only
    efp: float = 25.0                 # kN/m³, triangular and trapezoidal
    distributed_over: float = 60.0    # %, trapezoidal only
    #: ``(relative distance from the crest, pressure)``. RELATIVE, unlike
    #: ``UserDefined.points`` which is in metres: a wall profile is quoted
    #: as a fraction of the height, so the same table survives a change of
    #: wall length.
    points: list = field(
        default_factory=lambda: [(0.0, 0.0), (1.0, 100.0)])

    # ------------------------------------------------------------------
    # The profile
    # ------------------------------------------------------------------
    def _kind(self) -> str:
        return (self.profile_type or "triangular").strip().lower()

    def custom_table(self) -> list:
        """The ``points`` table with the two end rules applied.

        The convention is the one the profile is quoted with: a table that
        states no value at the crest starts from ZERO there, and one that
        states no value at the toe holds its last value down to the toe.
        Both come from the reference's own note on the custom profile.

        The sort is stable, so two rows at the same abscissa keep the order
        they were given and describe a STEP in the pressure. That is a
        legitimate profile — a surcharge starting part-way down a wall is
        exactly that — and it integrates to zero extra area, which is what
        a step should contribute.
        """
        pts = []
        for pair in (self.points or []):
            a, b = pair
            pts.append((min(1.0, max(0.0, float(a))), float(b)))
        if not pts:
            return [(0.0, 0.0), (1.0, 0.0)]
        pts.sort(key=lambda ab: ab[0])
        if pts[0][0] > 0.0:
            pts.insert(0, (0.0, 0.0))
        if pts[-1][0] < 1.0:
            pts.append((1.0, pts[-1][1]))
        return pts

    def shape_at(self, s: float) -> float:
        """Profile ordinate at relative distance ``s`` from the crest.

        For ``uniform`` and ``custom`` this IS the pressure. For the two
        ``efp`` shapes it is the pressure per unit length of wall, so a
        caller wanting a pressure multiplies by the wall length once — see
        :meth:`pressure_at`.
        """
        s = min(1.0, max(0.0, float(s)))
        kind = self._kind()
        if kind == "uniform":
            return float(self.pressure)
        if kind == "custom":
            pts = self.custom_table()
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                if x0 <= s <= x1:
                    if x1 <= x0:
                        continue      # a step: the next segment answers
                    return y0 + (y1 - y0) * (s - x0) / (x1 - x0)
            return pts[-1][1]
        if kind == "trapezoidal":
            f = min(1.0, max(0.0, float(self.distributed_over) / 100.0))
            r = 0.5 * (1.0 - f)
            if r <= 0.0:
                return float(self.efp)
            if s <= r:
                return float(self.efp) * s / r
            if s <= r + f:
                return float(self.efp)
            return float(self.efp) * (1.0 - s) / r
        return float(self.efp) * s          # triangular

    def pressure_at(self, s: float, total_length: float) -> float:
        """Pressure at relative distance ``s``, in pressure units."""
        scale = (float(total_length)
                 if self._kind() in ("triangular", "trapezoidal") else 1.0)
        return scale * self.shape_at(s)

    def _shape_integral(self, t: float) -> float:
        """``∫₀ᵗ shape(s) ds``, in closed form. 0 ≤ t ≤ 1."""
        t = min(1.0, max(0.0, float(t)))
        kind = self._kind()
        if kind == "uniform":
            return float(self.pressure) * t
        if kind == "custom":
            acc = 0.0
            pts = self.custom_table()
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                if x1 <= x0:
                    continue          # a step has zero width and zero area
                if t >= x1:
                    acc += 0.5 * (y0 + y1) * (x1 - x0)
                    continue
                if t <= x0:
                    break
                yt = y0 + (y1 - y0) * (t - x0) / (x1 - x0)
                acc += 0.5 * (y0 + yt) * (t - x0)
                break
            return acc
        if kind == "trapezoidal":
            f = min(1.0, max(0.0, float(self.distributed_over) / 100.0))
            r = 0.5 * (1.0 - f)
            e = float(self.efp)
            if r <= 0.0:                      # f = 1: the uniform limit
                return e * t
            if t <= r:
                return e * t * t / (2.0 * r)
            if t <= r + f:
                return e * (0.5 * r + (t - r))
            # The closing ramp, written in u = 1 − s so its primitive is
            # the opening triangle seen backwards. At t = 1 the bracket is
            # r/2 + f + r/2 = r + f, which is the whole trapezoid.
            return e * (0.5 * r + f + (r * r - (1.0 - t) ** 2) / (2.0 * r))
        return 0.5 * float(self.efp) * t * t   # triangular

    # ------------------------------------------------------------------
    # The contract
    # ------------------------------------------------------------------
    def force_at(self, distance_from_head: float, total_length: float,
                 bond=None) -> float:
        """Resultant of the pressure diagram above the cut, kN/m of wall.

        ``distance_from_head`` is measured from the CREST for this type —
        see ``MEASURED_FROM_TOP``. A cut at the toe returns the area of the
        whole diagram: 312.5 for the published 5-unit wall reaching 125,
        and 2000 for the published 10-unit wall with EFP 25 over 60 %.

        Returns zero at the crest by definition, which is worth saying out
        loud because a caller reporting "force at head" for this type is
        reporting a zero that means "no wall above the cut", not "no wall".
        """
        L = float(total_length)
        if L <= 0.0:
            return 0.0
        d = min(L, max(0.0, float(distance_from_head)))
        scale = L if self._kind() in ("triangular", "trapezoidal") else 1.0
        return max(0.0, scale * L * self._shape_integral(d / L))

    def resultant_arm(self, distance_from_head: float,
                      total_length: float) -> float:
        """Distance from the CREST to the centroid of the diagram above
        the cut, in model units.

        This is what the *location of force* setting needs: the reference
        lets the resultant act either at the slip-surface intersection or
        at the centroid of the pressure profile above it. Computed by
        first moment, sampled only where the profile is not piecewise
        linear — which is nowhere, so it is exact for all four shapes.

        Returns the cut depth itself when the diagram above the cut has no
        area, so a caller never divides by zero and the degenerate answer
        is "at the cut", which is where a zero force acts.
        """
        L = float(total_length)
        d = min(L, max(0.0, float(distance_from_head)))
        if L <= 0.0 or d <= 0.0:
            return d
        area = self._shape_integral(d / L)
        if area <= 0.0:
            return d
        # First moment of the shape over [0, t], by exact trapezoid
        # quadrature on the breakpoints: every profile here is piecewise
        # LINEAR, so s·p(s) is piecewise quadratic and Simpson on each
        # piece is exact.
        t = d / L
        acc = 0.0
        for a, b in _pieces(self, t):
            fa, fm, fb = (a * self.shape_at(a),
                          0.5 * (a + b) * self.shape_at(0.5 * (a + b)),
                          b * self.shape_at(b))
            acc += (b - a) * (fa + 4.0 * fm + fb) / 6.0
        return L * acc / area

    def to_dict(self) -> dict:
        d = {
            "type_id": self.TYPE_ID,
            "profile_type": self.profile_type,
            "force_location": self.force_location,
            "pressure": self.pressure,
            "efp": self.efp,
            "distributed_over": self.distributed_over,
            # Written as lists on purpose: JSON has no tuples, so writing
            # tuples and reading lists is what makes a round-trip compare
            # unequal for no reason at all.
            "points": [[float(a), float(b)] for a, b in (self.points or [])],
        }
        extras = self._extras_dict()
        if extras:
            d["_extras"] = extras
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RetainingWallEFP":
        extras = data.get("_extras", {})
        inst = cls(
            profile_type=data.get("profile_type", "triangular"),
            force_location=data.get("force_location", "intersection"),
            pressure=data.get("pressure", 20.0),
            efp=data.get("efp", 25.0),
            distributed_over=data.get("distributed_over", 60.0),
            points=[tuple(p) for p in data.get("points", [])],
        )
        if extras:
            inst._apply_extras(extras)
        return inst


def _pieces(wall: RetainingWallEFP, t: float) -> list:
    """The sub-intervals of ``[0, t]`` on which the profile is linear.

    Splitting at the breakpoints is what makes the centroid exact instead
    of approximate: Simpson is exact for a quadratic, and ``s·p(s)`` is
    quadratic only where ``p`` itself is linear.
    """
    kind = wall._kind()
    cuts = [0.0, t]
    if kind == "trapezoidal":
        f = min(1.0, max(0.0, float(wall.distributed_over) / 100.0))
        r = 0.5 * (1.0 - f)
        cuts += [r, r + f]
    elif kind == "custom":
        cuts += [x for x, _ in wall.custom_table()]
    cuts = sorted({round(c, 15) for c in cuts if 0.0 <= c <= t})
    return [(a, b) for a, b in zip(cuts[:-1], cuts[1:]) if b > a]
