# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.461 (D357) — Sarma's method with non-vertical slices: the solver.

WHAT THIS VERSION ADDS

``ogr_slip2d.sarma.solver``: the factor of safety of a set of wedges between
inclined faces, the largest F at which the critical acceleration Kc of
Sarma (1973) equals the applied kh, from a recurrence that is the project's
own derivation of the force equilibrium of one wedge (spec 009, ``plan.md``;
Sarma 1979 was not consulted). And ``ogr_slip2d.sarma.vertical``: the
slicer's vertical slices read as wedges with vertical faces. Nothing is
registered: no analysis runs it until v0.1.463.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **A wedge in closed form**, to 1e-8: one wedge on a plane gives
   F = (cL + (W cos α − U − H sin α) tan φ)/(W sin α + H cos α), with H the
   horizontal push toward the toe (kh·W_soil plus the water of a crack) and
   W = W_soil(1 + kv), dry, with water, shaken and with a crack, up to a
   factor of 661 and beyond the sweep; and Kc(1) from the same equilibrium
   at F = 1.
2. **Janbu's simplified method** (Janbu 1954, 1973), to 1e-10: vertical
   faces with no strength on the SAME slices of ``slice_surface`` give the
   engine's ``JanbuSimplified``, dry, under a water table, with ponded
   water, with a surcharge, with a water-filled crack, with kh = 0.1 and
   kv = ±0.05, with a curved envelope read where Janbu reads it, and on
   mirrored models with and without horizontal forces. Measured 1.4e-13
   at worst.
3. **The published problem 4** of the verification manual (Sarma's method,
   from Hoek 1987): its two wedges built HERE from the published geometry
   (areas by the shoelace formula, U and PW integrated exactly), at ±1 % of
   the published 1.198 dry and 0.434 saturated (measured +0.03 % and
   +0.15 %), in both senses of the shear. Reducing only the bases misses
   them by +14.8 % and −58 %: that fixes the convention.
4. **The bank's independent tool**, ``_tools/cunas_sarma.py``, which solves
   the 2n equations of the wedges directly instead of this recurrence: at
   1e-6 of its roots, written below with their provenance and NOT imported.
5. **The root next to a pole.** The saturated problem 4 has two roots,
   0.1467 and 0.4347, and a pole of Kc at 0.4288; the published factor is
   the larger. A march on Kc from F = 1 with a step of 0.05 sees no change
   of sign across 0.40–0.45 (root and pole together) and lands on 0.1467;
   the solver returns 0.4347, and on this mass Kc stays below kh above it.
6. **False zeros.** Where a qₖ of the recurrence cancels against an Ẽⱼ (a
   straight base of one strength cut by a face, or a stepped surface whose
   steps repeat), the polynomial the root is sought on would carry a factor
   that crosses zero with no root (found in v0.1.461; spec 009 overlooked
   it): ABOVE the factor on a toe (2.064 for a true 1.741), hiding the
   largest root on a stepped surface (1.084 for a true 1.506), and coming
   back with a difference of 1.3e-12 in tan φ, the rounding of the secant
   of a Mohr-Coulomb material. In every case the solver's F is a root of
   Kc = kh with no root above it, judged on a Kc written apart (the force
   equilibrium of the wedges as one linear system, ``_kc_direct``: no
   recurrence, no polynomial, no cancelled factor) by a fine sweep.
   A base bent by a little more than the rounding has a TRUE root next to
   a pole: it is returned, with forces that say so.
7. **The mirror.** A mass reflected in x gives the same F, the same forces,
   speeds and senses in reversed order, and its codes name the faces and
   wedges of the mirrored model.
8. **The sense of the shear.** Where the upper base is steeper than the
   lower one the rigid wedges give the fixed sense, at a convex vertex the
   other one; a straight base cut by a face takes the fixed sense. That
   rule, written here from the velocities in closed form, against the
   solver's senses; the two modes agree where it agrees and differ where it
   does not; a wedge that would climb its base is flagged.
9. **Equilibrium**, from outside the solver: the N′, E and X it returns
   close the force balance of every wedge in both components, with kh, kv,
   horizontal forces, loads and a crack's thrust, and the shear on every
   face is its strength divided by F.
10. **Rule 7 and the edges.** The tolerance and the iterations move the
    number; the sweep finds a largest root ×1.12 above the next, also at
    F ≈ 17; every code without a factor fires; a malformed call is a
    ValueError; the end faces that carry nothing are not refused.

Measured cost: about 2.6 s for the file in the runner, most of it in the
slicer, in Janbu at tolerance 1e-12 and in the fine sweeps of Kc that
judge the root (rule 1: the judge is what makes them worth it).
"""
from __future__ import annotations

import math

_D = math.radians

# ----------------------------------------------------------------- problem 4
#: Problem 4 of the verification manual (from Hoek 1987), as the bank
#: transcribes it (``03_Sarma_Problema004/referencia.json``): the ground of
#: the spoil heap, the published slip surface, the interface the published
#: 1.198 needs (from the kink to x = 82.85 on the face; D122) and table 4.1.
#: Both materials weigh 15.7 kN/m³, dry or saturated.
_GROUND = ((-50.0, -2.97), (0.0, 0.0), (111.4, 76.5), (229.545, 13.6815),
           (250.0, 14.9))
_TOE, _KINK, _HEAD, _CREST = (0.0, 0.0), (108.0, 6.4), (128.0, 67.6737), \
    (111.4, 76.5)
_X_P = 82.85
_GAMMA, _GW = 15.7, 9.81
_SPOIL, _FLOOR = (100.0, 42.0), (10.0, 6.0)        # (c kPa, φ°)
_PUBLISHED = {False: 1.198, True: 0.434}           # dry, saturated
#: ``_tools/cunas_sarma.py`` of the bank, run on 2026-11-15 with OGR
#: 0.1.460 installed (the tool does not import OGR): the roots of problem 4,
#: at full precision (``_auditoria/P7_0356/D122_cunas.json`` archives them
#: rounded: 0.361908 and 1.198339 dry, 0.146694 and 0.434662 saturated). Its
#: U on the scarp's base is Simpson's rule across the kink of the ground at
#: x = 111.4, 3.8e-7 off the exact integral used here, and that moves the
#: saturated F by 7e-8.
_TOOL = {False: 1.1983391299829478, True: 0.4346620085049817}
_TOOL_LOWER_SATURATED = 0.1466942767407493
#: N′ on the scarp's base at the tool's saturated root (the same JSON, to
#: two decimals): in effective tension, as the published case has it.
_TOOL_SCARP_NORMAL = -20012.33


def _ground_y(ground, x):
    for (x0, y0), (x1, y1) in zip(ground, ground[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError(x)


def _area(poly):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _u_integral(ground, p, q, wet):
    """∫u dl from p to q with u = γw·(y_ground − y). The water table IS the
    ground (Hu = 1) and the segment runs inside the mass, so u is linear
    between the ground's vertices and the trapezoid rule between those
    breakpoints is exact."""
    if not wet:
        return 0.0
    ts = {0.0, 1.0}
    for gx, _gy in ground:
        if (p[0] - gx) * (q[0] - gx) < 0.0:
            ts.add((gx - p[0]) / (q[0] - p[0]))
    ts = sorted(ts)

    def u(t):
        x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
        return _GW * max(0.0, _ground_y(ground, x) - y)
    length = math.dist(p, q)
    return sum(0.5 * (u(a) + u(b)) * (b - a) * length
               for a, b in zip(ts, ts[1:]))


def _problem4(wet, mirror=False):
    """(bases, faces, slide_sign) of problem 4, in model order, from the
    published geometry, reflected in x when ``mirror``."""
    from ogr_slip2d.sarma.solver import Base, Face
    k = -1.0 if mirror else 1.0

    def m(p):
        return (k * p[0], p[1])
    ground = sorted(m(p) for p in _GROUND)
    top = m((_X_P, _ground_y(_GROUND, _X_P)))
    toe, kink, head, crest = m(_TOE), m(_KINK), m(_HEAD), m(_CREST)

    def wedge(p, q, poly, strength):
        p, q = sorted((p, q))
        w = _GAMMA * _area(poly)
        return Base(alpha=math.atan2(q[1] - p[1], q[0] - p[0]),
                    length=math.dist(p, q), weight=w, soil_weight=w,
                    pore_force=_u_integral(ground, p, q, wet),
                    cohesion=strength[0], tan_phi=math.tan(_D(strength[1])))
    bases = [wedge(toe, kink, [toe, kink, top], _FLOOR),
             wedge(kink, head, [kink, head, crest, top], _SPOIL)]
    face = Face(delta=math.atan2(top[0] - kink[0], top[1] - kink[1]),
                length=math.dist(kink, top),
                water_force=_u_integral(ground, kink, top, wet),
                cohesion=_SPOIL[0], tan_phi=math.tan(_D(_SPOIL[1])))
    end = Face(0.0, 0.0)
    if mirror:
        bases.reverse()
    return bases, [end, face, end], (-1 if mirror else 1)


def _mirrored(bases, faces):
    """The same wedges reflected in x, by hand: reversed, every angle and
    every horizontal force negated."""
    from ogr_slip2d.sarma.solver import Base, Face
    return ([Base(-b.alpha, b.length, b.weight, b.soil_weight, b.pore_force,
                  b.cohesion, b.tan_phi, -b.force_x) for b in reversed(bases)],
            [Face(-f.delta, f.length, f.water_force, f.cohesion, f.tan_phi)
             for f in reversed(faces)])


def _solve(bases, faces, **kw):
    from ogr_slip2d.sarma.solver import solve
    kw.setdefault("tolerance", 1e-13)
    return solve(bases, faces, **kw)


def _equilibrium(bases, faces, sol, kh=0.0):
    """The worst force residual of any wedge, over the total vertical load,
    and the worst face law residual, written from the conventions alone (a
    mass sliding toward −x; one that slides toward +x is reflected here
    first): base N′n + Un + T t with T = (cl + N′ tan φ)/F; face E m + X s
    with X = σ[(E − PW) tan φ̄ + c̄ d]/F."""
    N, E, X, Ee = (sol.base_normals, sol.face_thrusts, sol.face_shears,
                   sol.face_effective)
    sigma = sol.senses
    if sol.slide_sign == -1:
        bases, faces = _mirrored(bases, faces)
        N, E, X, Ee, sigma = (N[::-1], E[::-1], X[::-1], Ee[::-1],
                              sigma[::-1])
    F = sol.fos
    scale = sum(b.weight for b in bases)
    worst = law = 0.0
    for j, f in enumerate(faces):
        want = sigma[j] * ((E[j] - f.water_force) * f.tan_phi
                           + f.cohesion * f.length) / F
        law = max(law, abs(want - X[j]) / scale)
        assert abs(Ee[j] - (E[j] - f.water_force)) <= 1e-9 * scale
    for i, b in enumerate(bases):
        a = b.alpha
        t, n = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        T = (b.cohesion * b.length + N[i] * b.tan_phi) / F
        fx = -kh * b.soil_weight + b.force_x + (N[i] + b.pore_force) * n[0] \
            + T * t[0]
        fy = -b.weight + (N[i] + b.pore_force) * n[1] + T * t[1]
        for j, sgn in ((i, 1.0), (i + 1, -1.0)):
            d = faces[j].delta
            fx += sgn * (E[j] * math.cos(d) + X[j] * math.sin(d))
            fy += sgn * (-E[j] * math.sin(d) + X[j] * math.cos(d))
        worst = max(worst, abs(fx) / scale, abs(fy) / scale)
    return worst, law


def _kc_direct(bases, faces, F, senses, head=0.0):
    """Kc(F) from the force equilibrium of the wedges written out and solved
    as one linear system, independent of the solver: no recurrence, no
    projection, no polynomial, no cancelled factor. Unknowns N′ of every
    base, E of every interior face and K; two equations (x, y) per wedge;
    E = 0 on the toe face and E = ``head`` on the head face. For a mass
    sliding toward −x."""
    import numpy as np
    n = len(bases)
    size = 2 * n                      # n normals, n − 1 thrusts, K
    M = np.zeros((size, size))
    rhs = np.zeros(size)

    def col_E(j):                     # interior face j (1..n−1)
        return n + j - 1
    for i, b in enumerate(bases):
        a = b.alpha
        t, nn = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        tp = b.tan_phi / F
        for r, axis in ((2 * i, 0), (2 * i + 1, 1)):
            # base: N′(n + tan φ′ t) + U n + c′ l t
            M[r, i] += nn[axis] + tp * t[axis]
            rhs[r] -= b.pore_force * nn[axis] + b.cohesion / F * b.length \
                * t[axis]
            # weight, horizontal force, −K·W_soil
            rhs[r] -= (-b.weight if axis else b.force_x)
            if axis == 0:
                M[r, size - 1] += -b.soil_weight
            for j, sgn in ((i, 1.0), (i + 1, -1.0)):
                f = faces[j]
                d = f.delta
                m = (math.cos(d), -math.sin(d))[axis]
                s = (math.sin(d), math.cos(d))[axis]
                tf = senses[j] * f.tan_phi / F
                const = senses[j] * (f.cohesion / F * f.length
                                     - f.water_force * f.tan_phi / F)
                # E m + X s with X = tf·E + const
                if j == 0 or j == n:
                    E = 0.0 if j == 0 else head
                    rhs[r] -= sgn * (E * m + (tf * E + const) * s)
                else:
                    M[r, col_E(j)] += sgn * (m + tf * s)
                    rhs[r] -= sgn * const * s
    try:
        x = np.linalg.solve(M, rhs)
    except np.linalg.LinAlgError:
        return None
    return float(x[-1])


def _assert_largest_root(bases, faces, sol, top, kh=0.0, steps=3000,
                         head=0.0):
    """The judge of a root, on Kc itself from ``_kc_direct``: Kc(F) = kh at
    the factor, and no root of Kc = kh in (F, top]. Kc changes sign above F
    only through poles, which a fine sweep tells from roots by their
    size. A mass that slides toward +x is reflected here first."""
    senses = sol.senses
    if sol.slide_sign == -1:
        bases, faces = _mirrored(bases, faces)
        senses = senses[::-1]
    F = sol.fos
    at = _kc_direct(bases, faces, F, senses, head)
    assert at is not None and abs(at - kh) <= 1e-9, (F, at)
    prev = None
    for k in range(1, steps + 1):
        Fk = F * (top / F) ** (k / steps)
        value = _kc_direct(bases, faces, Fk, senses, head)
        assert value is not None, Fk
        value -= kh
        if prev is not None and (value > 0.0) != (prev > 0.0):
            assert abs(value) + abs(prev) > 1.0, (
                "a root of Kc = kh above the factor", F, Fk, prev, value)
        prev = value


# ======================================================================
class TestOneWedge:
    """A single wedge on a plane: Coulomb's wedge, pseudo-static, in closed
    form (Kramer 1996, §10.6.1.1, with the push of a crack's water added as
    one more horizontal force)."""

    W_SOIL, L, ALPHA, C, PHI = 1350.0, 20.0, 30.0, 5.0, 30.0
    #: U of the ``control`` case of ``cunas_sarma.py`` (a 30° plane under a
    #: rising water table), which with this wedge gives 0.9249309231188405.
    U_CONTROL = 260.970913040825

    def _closed(self, U, kh, kv, push, alpha=None, c=None):
        a = _D(self.ALPHA if alpha is None else alpha)
        t = math.tan(_D(self.PHI))
        c = self.C if c is None else c
        W = self.W_SOIL * (1.0 + kv)
        H = kh * self.W_SOIL + push
        return ((c * self.L + (W * math.cos(a) - U - H * math.sin(a)) * t)
                / (W * math.sin(a) + H * math.cos(a)))

    def _wedge(self, U, kv, mirror=False, alpha=None, c=None):
        from ogr_slip2d.sarma.solver import Base, Face
        k = -1.0 if mirror else 1.0
        a = self.ALPHA if alpha is None else alpha
        return ([Base(k * _D(a), self.L, self.W_SOIL * (1.0 + kv),
                      self.W_SOIL, U, self.C if c is None else c,
                      math.tan(_D(self.PHI)))],
                [Face(0.0, 0.0), Face(0.0, 0.0)])

    def test_the_closed_form(self):
        n = 0
        for U in (0.0, self.U_CONTROL):
            for kh, kv in ((0.0, 0.0), (0.15, 0.1), (0.15, -0.1)):
                for push in (0.0, 120.0):
                    for mirror in (False, True):
                        b, f = self._wedge(U, kv, mirror)
                        sol = _solve(b, f, kh=kh, head_thrust=push,
                                     slide_sign=-1 if mirror else 1)
                        want = self._closed(U, kh, kv, push)
                        assert abs(sol.fos - want) <= 1e-8 * want, (
                            U, kh, kv, push, mirror, sol.fos, want)
                        worst, law = _equilibrium(b, f, sol, kh=kh)
                        assert worst <= 1e-9 and law <= 1e-12, (worst, law)
                        n += 1
        assert n == 24

    def test_a_factor_above_the_fine_sweep(self):
        """A plane of 0.05° gives 661, in the coarse part of the sweep (a
        top of the sweep at 200 would call it a surface that does not
        slide)."""
        b, f = self._wedge(0.0, 0.0, alpha=0.05, c=0.0)
        want = self._closed(0.0, 0.0, 0.0, 0.0, alpha=0.05, c=0.0)
        assert 500.0 < want < 1000.0
        sol = _solve(b, f)
        assert abs(sol.fos - want) <= 1e-8 * want, (sol.fos, want)

    def test_a_factor_above_the_top_of_the_sweep(self):
        from ogr_slip2d import messages as msg
        b, f = self._wedge(0.0, 0.0, alpha=1e-5, c=0.0)
        assert self._closed(0.0, 0.0, 0.0, 0.0, alpha=1e-5, c=0.0) > 1e6
        sol = _solve(b, f)
        assert sol.fos is None and sol.code == msg.SARMA_NO_DRIVING

    def test_the_tools_control_is_this_closed_form(self):
        """Premise of the constants: the control case of the tool is this
        wedge with its U."""
        assert abs(self._closed(self.U_CONTROL, 0.0, 0.0, 0.0)
                   - 0.9249309231188405) <= 1e-12

    def test_min_q_counts_the_head_only_under_a_crack(self):
        """With no crack the head face divides only the fictitious thrust
        the recurrence ends on, and one wedge has no other face: no q. With
        a crack's thrust it is the head face's q, here cos(atan(tan φ/F)
        − α) (a vertical face with no strength)."""
        b, f = self._wedge(0.0, 0.0)
        assert _solve(b, f).min_q is None
        sol = _solve(b, f, head_thrust=120.0)
        want = math.cos(math.atan(math.tan(_D(self.PHI)) / sol.fos)
                        - _D(self.ALPHA))
        assert abs(sol.min_q - want) <= 1e-12, (sol.min_q, want)

    def test_kc_at_full_strength(self):
        a, t = _D(self.ALPHA), math.tan(_D(self.PHI))
        for U, push in ((0.0, 0.0), (self.U_CONTROL, 80.0)):
            b, f = self._wedge(U, 0.0)
            sol = _solve(b, f, head_thrust=push)
            W = self.W_SOIL
            want = ((self.C * self.L + (W * math.cos(a) - U) * t
                     - W * math.sin(a))
                    / (W * (math.cos(a) + math.sin(a) * t)) - push / W)
            assert abs(sol.kc_at_1 - want) <= 1e-12 * max(1.0, abs(want))


# ======================================================================
def _slope(water, kh, kv, mirror=False, load=False, strength=None):
    """The clay slope of ``test_bishop_general_memo_v1390`` and its polyline,
    reflected in x when ``mirror``; it slides toward +x as drawn. ``load``
    puts 30 kPa on the crest, across the head of the mass (as in
    ``test_seismic_surcharge_v1219``), which ``kv`` must not shake."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.loads import DistributedLoad
    from ogr_core.loads.loads import LoadOrientation
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipSurface
    k = -1 if mirror else 1
    p = Project(name="sarma v1461")
    ext = Polyline(vertices=[Vertex(k * x, y) for x, y in (
        (0, 0), (50, 0), (50, 15), (35, 15), (25, 25), (0, 25))], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay",
                 strength=strength or MohrCoulomb(cohesion=8.0,
                                                  friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=(PorePressureType.WATER_TABLE if water
                                else PorePressureType.NONE))
    p.add_material(m)
    if water:
        wt = Boundary(polyline=Polyline(vertices=sorted(
            [Vertex(0, 14), Vertex(k * 50, 9)], key=lambda v: v.x)),
            btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        m.water_surface_id = wt.id
    if load:
        ends = sorted([Vertex(k * 2.0, 25.0), Vertex(k * 20.0, 25.0)],
                      key=lambda v: v.x)
        p.distributed_loads.append(DistributedLoad(
            start=ends[0], end=ends[1], magnitude_1=30.0,
            orientation=LoadOrientation.VERTICAL))
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh, p.seismic.kv = kh, kv
    surface = SlipSurface(polyline=Polyline(vertices=sorted(
        [Vertex(k * x, y) for x, y in ((10.0, 25.0), (16.0, 15.0),
                                       (26.0, 9.5), (36.0, 10.5),
                                       (43.0, 15.0))],
        key=lambda v: v.x), closed=False))
    return p, surface


def _ponded(kh, kv, mirror=False):
    """The dam face of ``test_interslice_ponded_v1214``, under 14 m of
    ponded water at the toe, reflected in x when ``mirror``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    k = -1 if mirror else 1
    ext = Polyline(vertices=[Vertex(k * x, y) for x, y in (
        (0, 0), (260, 0), (260, 78), (205, 78), (145, 58))], closed=True)
    ext.ensure_ccw()
    p = Project("sarma v1461 ponded")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=sorted(
        [Vertex(k * -5, 72), Vertex(k * 265, 72)], key=lambda v: v.x),
        closed=False), btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="fill", unit_weight=20.0, sat_unit_weight=20.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
        pore_pressure=PorePressureType.WATER_TABLE)]
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh, p.seismic.kv = kh, kv
    return p, SlipCircle(centre_x=k * 52.0, centre_y=186.0, radius=158.2)


def _cracked():
    """The slope of ``test_tension_crack_truncation_v1109`` with c-φ clay
    and its crack at y = 34 full of water."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(100, 0), Vertex(100, 40),
                             Vertex(60, 40), Vertex(30, 20), Vertex(0, 20)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("sarma v1461 crack")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 34), Vertex(100, 34)], closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(name="Clay", unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=15.0,
                                                 friction_angle=20.0))]
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.FILLED)
    return p, SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0)


#: (label, builder, slices). Every case of the spec: dry, a water table,
#: ponded water, kh = 0.1 with kv = ±0.05, a crack, and mirrors, also of a
#: mass with horizontal forces; and a surcharge under kv, which acts on the
#: soil only (D206).
_JANBU_CASES = (
    ("surcharge, kh 0.1 kv +0.05",
     lambda: _slope(False, 0.1, 0.05, load=True), 25),
    ("dry", lambda: _slope(False, 0.0, 0.0), 25),
    ("dry, 60 slices", lambda: _slope(False, 0.0, 0.0), 60),
    ("dry, mirrored", lambda: _slope(False, 0.0, 0.0, True), 25),
    ("water table", lambda: _slope(True, 0.0, 0.0), 25),
    ("water table, kh 0.1 kv +0.05", lambda: _slope(True, 0.1, 0.05), 25),
    ("water table, kh 0.1 kv -0.05, mirrored",
     lambda: _slope(True, 0.1, -0.05, True), 60),
    ("ponded", lambda: _ponded(0.0, 0.0), 25),
    ("ponded, kh 0.1 kv +0.05", lambda: _ponded(0.1, 0.05), 25),
    ("ponded, kh 0.1 kv -0.05", lambda: _ponded(0.1, -0.05), 25),
    ("ponded, kh 0.1 kv +0.05, mirrored",
     lambda: _ponded(0.1, 0.05, True), 25),
    ("water-filled crack", _cracked, 40),
)


def _janbu_and_wedges(p, surface, n):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.sarma.vertical import from_vertical_slices
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, surface, num_slices=n)
    assert sl is not None
    janbu = method_registry()["janbu_simplified"]()
    janbu.tolerance = 1e-12
    res = janbu.compute_fos(p, surface, sl)
    assert res.fos is not None and res.converged
    kh = p.seismic.kh if p.seismic.enabled else 0.0
    kv = p.seismic.kv if p.seismic.enabled else 0.0
    return sl, res, from_vertical_slices(sl, kh, kv), kh


class TestJanbuOnTheSameSlices:

    def test_vertical_faces_without_strength_are_janbu(self):
        seen = set()
        for label, build, n in _JANBU_CASES:
            p, surface = build()
            sl, res, w, kh = _janbu_and_wedges(p, surface, n)
            assert all(f.delta == 0.0 and f.tan_phi == 0.0
                       and f.cohesion == 0.0 for f in w.faces), label
            assert w.slide_sign == res.details["slide_sign"], label
            sol = _solve(w.bases, w.faces, kh=kh, slide_sign=w.slide_sign)
            assert abs(sol.fos - res.fos) <= 1e-10 * res.fos, (
                label, sol.fos, res.fos)
            worst, law = _equilibrium(w.bases, w.faces, sol, kh=kh)
            assert worst <= 1e-9 and law <= 1e-12, (label, worst, law)
            if any(b.force_x != 0.0 for b in w.bases):
                seen.add("horizontal" + (" mirrored" if w.slide_sign == -1
                                         else ""))
            if sl.tension_crack_force:
                seen.add("crack")
            if any(x.soil_weight is not None
                   and x.weight > x.soil_weight + 1.0 for x in sl):
                seen.add("load")
        # premises: the cases carry what they are named after
        assert seen == {"horizontal", "horizontal mirrored", "crack",
                        "load"}, seen

    def test_a_curved_envelope_read_where_janbu_reads_it(self):
        """A power-curve envelope, with the fixed point at the method's own
        stress switched off (Janbu then reads it once, at its Fellenius
        estimate): the wedges read c and tan φ at the same stress. Read
        anywhere else, the factor moves by 6e-3."""
        from ogr_core.materials.builtin_models import PowerCurve
        from ogr_slip2d.methods import base
        old = base.ENVELOPE_AT_OWN_STRESS
        base.ENVELOPE_AT_OWN_STRESS = False
        try:
            p, surface = _slope(True, 0.0, 0.0, strength=PowerCurve(
                a=1.107, b=0.86, c=4.0, d=0.0, waviness=0.0))
            _sl, res, w, kh = _janbu_and_wedges(p, surface, 25)
        finally:
            base.ENVELOPE_AT_OWN_STRESS = old
        assert len({round(b.tan_phi, 9) for b in w.bases}) > 3   # curved
        sol = _solve(w.bases, w.faces, kh=kh, slide_sign=w.slide_sign)
        assert abs(sol.fos - res.fos) <= 1e-10 * res.fos, (sol.fos, res.fos)

    def test_the_crack_is_not_counted_twice(self):
        """The crack's water is already in the wall slice's horizontal
        force; given again as the head thrust it moves F by 9 %."""
        from ogr_slip2d.sarma.vertical import from_vertical_slices
        from ogr_slip2d.slicer import slice_surface
        p, surface = _cracked()
        sl = slice_surface(p, surface, num_slices=40)
        w = from_vertical_slices(sl)
        once = _solve(w.bases, w.faces, slide_sign=w.slide_sign)
        twice = _solve(w.bases, w.faces, slide_sign=w.slide_sign,
                       head_thrust=sl.tension_crack_force)
        assert sl.tension_crack_force > 100.0
        assert (once.fos - twice.fos) / once.fos > 0.05


# ======================================================================
class TestProblem4:

    def test_the_published_factors_and_the_tool(self):
        from ogr_slip2d.sarma.solver import SHEAR_SENSES
        for wet in (False, True):
            b, f, sign = _problem4(wet)
            for sense in SHEAR_SENSES:
                sol = _solve(b, f, shear_sense=sense)
                assert sol.converged, (wet, sense, sol.message)
                assert abs(sol.fos / _PUBLISHED[wet] - 1.0) <= 0.01, (
                    wet, sense, sol.fos)
                assert abs(sol.fos - _TOOL[wet]) <= 1e-6, (wet, sense,
                                                           sol.fos)

    def test_reducing_only_the_bases_misses_the_published(self):
        """What fixes the convention: F divides the strength of the faces
        too. Sarma's 1973 vertical-slice method divides only the bases'; on
        problem 4 that lands +14.8 % dry and −58 % saturated off the
        published factors (here as a fixed point: the faces' strength
        multiplied back by F until F stops moving)."""
        from ogr_slip2d.sarma.solver import Face
        for wet, want in ((False, 0.148), (True, -0.580)):
            b, f, _s = _problem4(wet)
            F = _solve(b, f).fos
            for _ in range(100):
                undivided = [Face(x.delta, x.length, x.water_force,
                                  x.cohesion * F, x.tan_phi * F) for x in f]
                F_next = _solve(b, undivided).fos
                if abs(F_next - F) <= 1e-12:
                    break
                F = F_next
            off = F_next / _PUBLISHED[wet] - 1.0
            assert abs(off - want) <= 0.005, (wet, F_next, off)

    def test_the_weights_are_the_tools(self):
        """Premise: the wedges built here are the tool's (its weights, in
        the archived JSON, 44072.603 and 24557.666 kN/m)."""
        b, _f, _s = _problem4(False)
        assert [round(x.weight, 3) for x in b] == [44072.603, 24557.666]

    def test_the_scarp_is_in_effective_tension(self):
        b, f, _s = _problem4(True)
        sol = _solve(b, f)
        assert sol.base_normals[1] < 0.0
        assert abs(sol.base_normals[1] / _TOOL_SCARP_NORMAL - 1.0) <= 1e-5
        worst, law = _equilibrium(b, f, sol)
        assert worst <= 1e-9 and law <= 1e-12, (worst, law)
        # the published root is no near-pole one: its largest force is the
        # toe's base normal, 56 414 kN/m of a 68 630 kN/m mass
        assert abs(sol.max_force_ratio
                   - sol.base_normals[0] / sum(x.weight for x in b)) <= 1e-12
        assert 0.8 < sol.max_force_ratio < 0.85, sol.max_force_ratio

    def test_min_q_is_the_q_of_the_interface(self):
        """Two wedges and no crack: the only q that divides a real thrust is
        q₁, of the interface (the head face's divides only the fictitious
        thrust the recurrence ends on)."""
        b, f, _s = _problem4(True)
        sol = _solve(b, f)
        tp = b[0].tan_phi / sol.fos
        tpf = f[1].tan_phi / sol.fos
        beta = math.atan(tp) - b[0].alpha
        want = math.cos(beta - f[1].delta) - tpf * math.sin(beta - f[1].delta)
        assert abs(sol.min_q - want) <= 1e-12, (sol.min_q, want)

    def test_the_rigid_wedges_move_as_the_closed_form_says(self):
        """Steeper upper base: the fixed sense, so both modes agree."""
        b, f, _s = _problem4(False)
        fixed = _solve(b, f, shear_sense="fixed")
        kin = _solve(b, f, shear_sense="kinematic")
        a0, a1, d = b[0].alpha, b[1].alpha, f[1].delta
        assert a1 > a0
        assert kin.senses == [1, 1, 1]
        v = math.cos(a0 + d) / math.cos(a1 + d)
        assert abs(kin.velocities[1] - v) <= 1e-12 * v
        assert kin.kinematically_admissible
        assert abs(kin.fos - fixed.fos) <= 1e-14 * fixed.fos


# ======================================================================
class TestTheRootNextToAPole:

    def test_the_largest_root_is_the_published_one(self):
        from ogr_slip2d.sarma.solver import kc
        b, f, _s = _problem4(True)
        sol = _solve(b, f)
        F = sol.fos
        assert abs(F - _TOOL[True]) <= 1e-6
        # both roots of the tool are roots here
        for root in (_TOOL_LOWER_SATURATED, _TOOL[True]):
            assert abs(kc(b, f, root)) <= 1e-5, root
        # a march on Kc from F = 1 with a step of 0.05: 0.45 and 0.40 have
        # the same sign, with the root 0.4347 AND the pole between them
        assert kc(b, f, 0.45) < 0.0 and kc(b, f, 0.40) < 0.0
        steps = [1.0 - 0.05 * k for k in range(19)]
        march = None
        for hi, lo in zip(steps, steps[1:]):
            if (kc(b, f, hi) > 0.0) != (kc(b, f, lo) > 0.0):
                march = (lo, hi)
                break
        assert march is not None and march[0] < _TOOL_LOWER_SATURATED \
            < march[1], march
        # above the factor, on this mass, Kc stays below kh = 0
        for k in range(1, 3001):
            Fk = F * (100.0 / F) ** (k / 3000.0)
            value = kc(b, f, Fk)
            assert value is not None and value < 0.0, (Fk, value)


# ======================================================================
class TestFalseZeros:
    """Where a q of the recurrence cancels against an Ẽ, ∏q is not the
    denominator of Kc, and a polynomial that kept the factor would have a
    zero that is no root."""

    def _toe(self, eps=0.0, dalpha=0.0, phi2=50.0):
        """Two toe wedges on one straight base of one strength, with
        strength on the face between them, under a steep weak wedge: q₁ = Ẽ₂
        crosses zero at F = tan 50°/tan 30° = 2.064, where Kc ≠ kh."""
        from ogr_slip2d.sarma.solver import Base, Face
        t50, t10 = math.tan(_D(50.0)), math.tan(_D(10.0))
        bases = [Base(_D(-30.0), 6.0, 300.0, 300.0, 0.0, 0.0, t50),
                 Base(_D(-30.0) + dalpha, 6.0, 600.0, 600.0, 0.0, 0.0,
                      math.tan(_D(phi2)) + eps),
                 Base(_D(60.0), 12.0, 2000.0, 2000.0, 0.0, 5.0, t10)]
        faces = [Face(0.0, 0.0), Face(0.0, 4.0, 0.0, 0.0, t50),
                 Face(0.0, 6.0, 0.0, 0.0, t10), Face(0.0, 0.0)]
        return bases, faces

    def _steps(self):
        """A stepped surface whose steps repeat (bases 1 and 3 at 20° with
        φ = 35°, and every interior face at −50° with φ̄ = 45°): q₁ = Ẽ₃, a
        pair of wedges that do not touch."""
        from ogr_slip2d.sarma.solver import Base, Face
        bases = [Base(_D(a), 8.0, w, w, 0.0, c, math.tan(_D(p)))
                 for a, w, c, p in ((20.0, 500.0, 0.0, 35.0),
                                    (35.0, 1000.0, 0.0, 35.0),
                                    (20.0, 500.0, 0.0, 35.0),
                                    (60.0, 3000.0, 5.0, 10.0))]
        faces = [Face(0.0, 0.0)] + [
            Face(_D(-50.0), 5.0, 0.0, 0.0, math.tan(_D(45.0)))
            for _ in range(3)] + [Face(0.0, 0.0)]
        return bases, faces

    def test_on_a_straight_toe_the_false_zero_would_be_above(self):
        b, f = self._toe()
        sol = _solve(b, f)
        assert sol.fos < math.tan(_D(50.0)) / math.tan(_D(30.0)) * 0.99
        _assert_largest_root(b, f, sol, 50.0)
        worst, law = _equilibrium(b, f, sol)
        assert worst <= 1e-9 and law <= 1e-12, (worst, law)

    def test_on_steps_the_false_zero_would_hide_the_largest_root(self):
        b, f = self._steps()
        sol = _solve(b, f)
        assert abs(sol.fos - 1.5055) <= 1e-3, sol.fos
        _assert_largest_root(b, f, sol, 50.0)
        # the largest force here is a face's E′, not a base normal
        biggest = {"N": max(abs(x) for x in sol.base_normals),
                   "E": max(abs(x) for x in sol.face_effective),
                   "X": max(abs(x) for x in sol.face_shears)}
        assert max(biggest, key=biggest.get) == "E", biggest
        assert abs(sol.max_force_ratio - max(biggest.values())
                   / sum(x.weight for x in b)) <= 1e-12

    def test_steps_whose_faces_differ_do_not_pair(self):
        """The same steps with the second interior face at −40°, or with
        φ̄ = 40° on it: q₁ and Ẽ₃ are no longer one function, and a
        cancellation would solve another equation (1.467 and 1.485 for the
        true 1.527 and 1.521)."""
        from ogr_slip2d.sarma.solver import Face
        b, f = self._steps()
        t45 = math.tan(_D(45.0))
        for face in (Face(_D(-40.0), 5.0, 0.0, 0.0, t45),
                     Face(_D(-50.0), 5.0, 0.0, 0.0, math.tan(_D(40.0)))):
            g = [f[0], f[1], face, f[3], f[4]]
            sol = _solve(b, g)
            _assert_largest_root(b, g, sol, 50.0)

    def test_the_rounding_of_a_secant_does_not_bring_it_back(self):
        exact = _solve(*self._toe()).fos
        for eps in (1.3e-12, -1.3e-12):
            got = _solve(*self._toe(eps=eps)).fos
            assert abs(got - exact) <= 1e-9 * exact, (eps, got, exact)

    def test_collinear_bases_of_different_strength_do_not_cancel(self):
        """φ = 40° on the second toe wedge: q₁ and Ẽ₂ differ, and the pole
        q₁ = 0 is a true one."""
        b, f = self._toe(phi2=40.0)
        sol = _solve(b, f)
        _assert_largest_root(b, f, sol, 50.0)

    def test_a_bent_base_has_a_true_root_by_a_pole_and_says_so(self):
        """A bend of 1e-6 rad is no rounding: the equation has a true root
        next to a true pole there, above the straight base's factor, with
        face forces of 1e5 times the weight of the mass. It is returned
        (it is a root), with the forces that tell (owner's decision)."""
        straight = _solve(*self._toe())
        b, f = self._toe(dalpha=1e-6)
        bent = _solve(b, f)
        _assert_largest_root(b, f, bent, 50.0)
        assert bent.fos > straight.fos * 1.1
        assert straight.max_force_ratio < 2.0
        assert bent.max_force_ratio > 1e4, bent.max_force_ratio


# ======================================================================
class TestTheSweep:
    """Two true roots ×1.12 apart at the top (0.8627 and 0.7710, with
    forces of 0.64 times the weight): a sweep step of ×1.15 or coarser
    puts both in one step and lands on 0.1235. Kc depends on the strengths
    only through c/F and tan φ/F, so every strength ×20 puts the same two
    roots at 17.25 and 15.42, where a fine sweep that started at 5 instead
    of 100 would step over them by ×10. The wedges were found by a random
    search of three-wedge masses (seed 7, trial 480), rounded as written."""

    BASES = ((16.46, 4.345, 2576.3, 4.083, 14.92),
             (23.616, 14.223, 1263.4, 6.182, 22.335),
             (55.662, 14.72, 914.7, 13.819, 25.187))     # α°, l, W, c, φ°
    FACES = ((0.0, 0.0, 0.0, 0.0), (-35.511, 4.192, 5.819, 43.198),
             (-7.134, 7.837, 5.402, 11.66), (0.0, 0.0, 0.0, 0.0))  # δ°, d, c, φ°

    def _case(self, scale):
        from ogr_slip2d.sarma.solver import Base, Face
        return ([Base(_D(a), l, w, w, 0.0, c * scale,
                      math.tan(_D(p)) * scale) for a, l, w, c, p in self.BASES],
                [Face(_D(dl), dd, 0.0, c * scale, math.tan(_D(p)) * scale)
                 for dl, dd, c, p in self.FACES])

    def test_close_roots_at_the_top(self):
        from ogr_slip2d.sarma.solver import kc
        b, f = self._case(1.0)
        sol = _solve(b, f)
        _assert_largest_root(b, f, sol, 10.0)
        # premise: the next root is ×1.12 below, at 0.7711 (a clean change
        # of sign of Kc, just above a pole at 0.766), and the factor's
        # forces are no near-pole ones
        lo, hi = kc(b, f, 0.770), kc(b, f, 0.772)
        assert lo < 0.0 < hi and abs(lo) + abs(hi) < 0.05, (lo, hi)
        assert 1.11 < sol.fos / 0.7711 < 1.13
        assert sol.max_force_ratio < 1.0

    def test_the_same_roots_twenty_times_stronger(self):
        b1, f1 = self._case(1.0)
        b, f = self._case(20.0)
        sol = _solve(b, f)
        assert abs(sol.fos - 20.0 * _solve(b1, f1).fos) <= 1e-9 * sol.fos
        _assert_largest_root(b, f, sol, 200.0)


# ======================================================================
class TestTheMirror:

    def test_problem_4_reflected(self):
        from ogr_slip2d.sarma.solver import SHEAR_SENSES
        for wet in (False, True):
            b, f, _s = _problem4(wet)
            bm, fm, sm = _problem4(wet, mirror=True)
            assert sm == -1 and bm[0].alpha < 0.0
            for sense in SHEAR_SENSES:
                a = _solve(b, f, shear_sense=sense)
                m = _solve(bm, fm, shear_sense=sense, slide_sign=sm)
                assert abs(m.fos - a.fos) <= 1e-12 * a.fos, (wet, sense)
                scale = sum(x.weight for x in b)
                for got, want in ((m.base_normals, a.base_normals),
                                  (m.face_thrusts, a.face_thrusts),
                                  (m.face_effective, a.face_effective),
                                  (m.face_shears, a.face_shears)):
                    assert all(abs(g - w) <= 1e-9 * scale for g, w in
                               zip(got, reversed(want))), (wet, sense)
                assert m.senses == list(reversed(a.senses))
                assert all(abs(g - w) <= 1e-12 for g, w in
                           zip(m.velocities, reversed(a.velocities)))
                worst, law = _equilibrium(bm, fm, m)
                assert worst <= 1e-9 and law <= 1e-12, (worst, law)

    def test_three_wedges_with_different_faces_and_horizontal_forces(self):
        """Problem 4's faces read the same in either order; these do not
        (two interior faces of different length and inclination), one of
        them takes the kinematic sense −1, and the wedges carry horizontal
        forces, which change sign in the mirror."""
        from ogr_slip2d.sarma.solver import Base
        b, f = TestTheSenseOfTheShear()._case(-20.0)
        b = [Base(x.alpha, x.length, x.weight, x.soil_weight, x.pore_force,
                  x.cohesion, x.tan_phi, px)
             for x, px in zip(b, (60.0, -40.0, 25.0))]
        bm, fm = _mirrored(b, f)
        assert [x.length for x in f] != [x.length for x in reversed(f)]
        for sense in ("fixed", "kinematic"):
            a = _solve(b, f, shear_sense=sense, kh=0.1)
            m = _solve(bm, fm, shear_sense=sense, kh=0.1, slide_sign=-1)
            assert abs(m.fos - a.fos) <= 1e-12 * a.fos, sense
            assert m.senses == list(reversed(a.senses)), sense
            for s in (a, m):
                worst, law = _equilibrium(b if s is a else bm,
                                          f if s is a else fm, s, kh=0.1)
                assert worst <= 1e-9 and law <= 1e-12, (sense, worst, law)

    def test_a_code_names_the_mirrored_models_face_and_wedge(self):
        from ogr_slip2d import messages as msg
        b, f = TestEveryCodeFires()._parallel_case()
        bm, fm = _mirrored(b, f)
        sol = _solve(bm, fm, slide_sign=-1)
        assert sol.code == msg.SARMA_FACE_PARALLEL
        # face 2 of 3 is face 2 of 3 reflected; wedge 1 of 2 is wedge 2
        assert sol.args == {"face": 2, "wedge": 2}, sol.args


# ======================================================================
class TestTheSenseOfTheShear:

    #: α of three wedges: concave at face 2 (40° above 10°), convex at face
    #: 3 (25° above 40°).
    ALPHAS = (10.0, 40.0, 25.0)

    def _case(self, delta):
        from ogr_slip2d.sarma.solver import Base, Face
        t25, t30 = math.tan(_D(25.0)), math.tan(_D(30.0))
        bases = [Base(_D(a), l, w, w, 0.0, 5.0, t25) for a, l, w in
                 zip(self.ALPHAS, (10.0, 15.0, 8.0), (400.0, 1500.0, 600.0))]
        faces = [Face(0.0, 0.0), Face(_D(delta), 6.0, 0.0, 10.0, t30),
                 Face(_D(delta) / 2.0, 5.0, 0.0, 10.0, t30), Face(0.0, 0.0)]
        return bases, faces

    def test_the_kinematic_senses_are_the_closed_form(self):
        for delta in (0.0, -20.0, 15.0):
            b, f = self._case(delta)
            sol = _solve(b, f, shear_sense="kinematic")
            want, v = [1], [1.0]
            for j in (1, 2):
                lo, up, d = b[j - 1].alpha, b[j].alpha, f[j].delta
                v.append(v[-1] * math.cos(lo + d) / math.cos(up + d))
                rel = v[-2] * math.sin(lo - up) / math.cos(up + d)
                want.append(1 if rel < 0.0 else -1)
            want.append(1)
            assert want == [1, 1, -1, 1], delta     # premise of the case
            assert sol.senses == want, (delta, sol.senses)
            assert all(abs(g - w) <= 1e-12 for g, w in
                       zip(sol.velocities, v)), delta
            assert sol.kinematically_admissible
            fixed = _solve(b, f, shear_sense="fixed")
            assert fixed.senses == [1, 1, 1, 1]
            assert abs(sol.fos - fixed.fos) > 1e-3 * fixed.fos, (
                delta, sol.fos, fixed.fos)
            for s in (sol, fixed):
                worst, law = _equilibrium(b, f, s)
                assert worst <= 1e-9 and law <= 1e-12, (delta, worst, law)

    def test_a_straight_base_cut_by_a_face_takes_the_fixed_sense(self):
        from ogr_slip2d.sarma.solver import Base, Face
        t = math.tan(_D(30.0))
        b = [Base(_D(20.0), 10.0, 800.0, 800.0, 0.0, 5.0, t),
             Base(_D(20.0), 10.0, 900.0, 900.0, 0.0, 5.0, t)]
        f = [Face(0.0, 0.0), Face(_D(-10.0), 4.0, 0.0, 10.0, t),
             Face(0.0, 0.0)]
        kin = _solve(b, f, shear_sense="kinematic")
        fixed = _solve(b, f, shear_sense="fixed")
        assert kin.senses == [1, 1, 1]
        assert abs(kin.fos - fixed.fos) <= 1e-14 * fixed.fos

    def test_a_wedge_that_would_climb_its_base_is_flagged(self):
        """α = 10° under 60° with the face at 40°: cos(α + δ) changes sign
        across the face, so the upper wedge's speed is negative."""
        from ogr_slip2d.sarma.solver import Base, Face
        t = math.tan(_D(30.0))
        b = [Base(_D(10.0), 10.0, 800.0, 800.0, 0.0, 5.0, t),
             Base(_D(60.0), 10.0, 900.0, 900.0, 0.0, 5.0, t)]
        f = [Face(0.0, 0.0), Face(_D(40.0), 4.0, 0.0, 10.0, t),
             Face(0.0, 0.0)]
        sol = _solve(b, f, shear_sense="kinematic")
        want = math.cos(_D(50.0)) / math.cos(_D(100.0))
        assert want < 0.0
        assert abs(sol.velocities[1] - want) <= 1e-12 * abs(want)
        assert sol.kinematically_admissible is False


# ======================================================================
class TestKcAsTheSolverReadsIt:
    """``kc`` with every argument ``solve`` takes: Kc = kh at the factor."""

    def test_with_a_crack_a_sense_and_a_mirror(self):
        from ogr_slip2d.sarma.solver import kc
        w = TestOneWedge()
        b, f = w._wedge(0.0, 0.0)
        sol = _solve(b, f, head_thrust=120.0, kh=0.05)
        assert abs(kc(b, f, sol.fos, head_thrust=120.0) - 0.05) <= 1e-9
        b, f = TestTheSenseOfTheShear()._case(-20.0)
        sol = _solve(b, f, shear_sense="kinematic")
        assert abs(kc(b, f, sol.fos, shear_sense="kinematic")) <= 1e-9
        assert abs(kc(b, f, sol.fos, shear_sense="fixed")) > 1e-4
        bm, fm = _mirrored(b, f)
        assert abs(kc(bm, fm, sol.fos, shear_sense="kinematic",
                      slide_sign=-1)) <= 1e-9


# ======================================================================
class TestTheSettingsMoveTheNumber:

    def test_the_tolerance(self):
        b, f, _s = _problem4(False)
        fine = _solve(b, f, tolerance=1e-13).fos
        coarse = _solve(b, f, tolerance=1e-3).fos
        assert 1e-9 < abs(coarse - fine) <= 2e-3, (coarse, fine)

    def test_the_iterations(self):
        from ogr_slip2d import messages as msg
        b, f, _s = _problem4(False)
        short = _solve(b, f, max_iterations=2)
        assert short.fos is None and not short.converged
        assert short.code == msg.NOT_CONVERGED
        assert _solve(b, f, max_iterations=75).converged


# ======================================================================
class TestTheScalarCheckOfTheSweep:

    def test_a_sweep_whose_signs_are_wrong_is_redone(self):
        """The sweep evaluates H with NumPy, Brent with ``math``. If the
        array's signs are not the scalar ones (here forced: an array
        arithmetic that gives NaN, so the array sweep finds either no
        change of sign or one at the top that the scalar H does not
        confirm), the sweep is redone with ``math`` and the factor does not
        move. Negating sin and cos would not do: it flips H as a whole and
        leaves its changes of sign where they were."""
        import numpy as np
        from ogr_slip2d.sarma import solver as S
        from ogr_slip2d.sarma.solver import Base, Face
        t = math.tan(_D(30.0))
        # a face at 40° over a base at 60°: cos(α + δ) < 0, so H(∞) > 0 and
        # the NaN sweep "changes sign" at its top, which the scalar H must
        # refuse (premise below)
        steep = ([Base(_D(60.0), 10.0, 800.0, 800.0, 0.0, 5.0, t),
                  Base(_D(70.0), 10.0, 900.0, 900.0, 0.0, 5.0, t)],
                 [Face(0.0, 0.0), Face(_D(40.0), 4.0, 0.0, 10.0, t),
                  Face(0.0, 0.0)])
        assert S._H(S._frame(*steep, 1, 0.0), 0.0, 0.0) > 0.0
        cases = [_problem4(True)[:2], TestTheSweep()._case(1.0), steep]
        wants = [_solve(b, f).fos for b, f in cases]
        saved = S._ARRAY
        S._ARRAY = S._Ops(np.sin, np.cos,
                          lambda x: np.full(np.shape(x), np.nan))
        try:
            gots = [_solve(b, f).fos for b, f in cases]
        finally:
            S._ARRAY = saved
        for got, want in zip(gots, wants):
            assert got is not None and abs(got - want) <= 1e-12 * want, (
                got, want)


# ======================================================================
class TestEveryCodeFires:

    def _one(self, alpha, phi, c=0.0):
        from ogr_slip2d.sarma.solver import Base, Face
        return ([Base(_D(alpha), 10.0, 500.0, 500.0, 0.0, c,
                      math.tan(_D(phi)))], [Face(0.0, 0.0), Face(0.0, 0.0)])

    def _parallel_case(self):
        from ogr_slip2d.sarma.solver import Base, Face
        t = math.tan(_D(30.0))
        b = [Base(_D(30.0), 10.0, 800.0, 800.0, 0.0, 5.0, t),
             Base(_D(45.0), 10.0, 900.0, 900.0, 0.0, 5.0, t)]
        # 60° from the vertical, leaning to +x: along the lower base
        f = [Face(0.0, 0.0), Face(_D(60.0), 4.0, 0.0, 10.0, t),
             Face(0.0, 0.0)]
        return b, f

    def test_a_mass_that_stands_without_strength(self):
        from ogr_slip2d import messages as msg
        b, f = self._one(-10.0, 30.0)
        sol = _solve(b, f)
        assert sol.fos is None and sol.code == msg.SARMA_NO_DRIVING
        assert sol.message == msg.text(msg.SARMA_NO_DRIVING, **sol.args)
        assert "does not slide" in sol.message

    def test_a_mass_weaker_than_the_sweep(self):
        from ogr_slip2d import messages as msg
        b, f = self._one(30.0, 0.2)      # F = tan 0.2°/tan 30° = 0.006
        sol = _solve(b, f)
        assert sol.fos is None and sol.code == msg.SARMA_NO_ROOT
        assert sol.args["f_min"] == 0.01

    def test_a_face_parallel_to_a_base(self):
        from ogr_slip2d import messages as msg
        b, f = self._parallel_case()
        for sense in ("fixed", "kinematic"):
            sol = _solve(b, f, shear_sense=sense)
            assert sol.fos is None and sol.code == msg.SARMA_FACE_PARALLEL
            assert sol.args == {"face": 2, "wedge": 1}, sol.args

    def test_end_faces_that_carry_nothing_are_not_refused(self):
        """A zero-length toe face along the first base, and a zero-length
        head face with no crack along the last: neither acts, and the
        factor is the one with vertical end faces."""
        from ogr_slip2d.sarma.solver import Face
        b, f = TestTheSenseOfTheShear()._case(-20.0)
        want = _solve(b, f).fos
        f2 = [Face(_D(90.0) - b[0].alpha, 0.0)] + f[1:-1] + [
            Face(_D(90.0) - b[-1].alpha, 0.0)]
        got = _solve(b, f2)
        assert got.code == "" and abs(got.fos - want) <= 1e-14 * want

    def test_a_malformed_call_is_an_error_not_a_surface(self):
        import pytest
        from ogr_slip2d.sarma.solver import Face
        b, f = self._one(30.0, 30.0)
        with pytest.raises(ValueError):
            _solve(b, [Face(0.0, 0.0)])
        for kw in ({"kh": float("nan")}, {"kh": float("inf")},
                   {"head_thrust": float("nan")}, {"head_thrust": -500.0}):
            with pytest.raises(ValueError):
                _solve(b, f, **kw)
        # strength on an end face: a shear on a face nothing presses
        for end in (0, -1):
            g = list(f)
            g[end] = Face(0.0, 3.0, 20.0, 10.0, 0.0)
            with pytest.raises(ValueError):
                _solve(b, g)
