# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The factor of safety of a set of wedges with inclined faces: Sarma's method
with non-vertical slices.

THE METHOD

Sarma (1973) defines the critical acceleration Kc of a sliding mass, the
horizontal seismic coefficient that brings it to limit equilibrium, and the
factor of safety as the factor F by which the shear strength must be
reduced for Kc to fall to the applied coefficient (to zero in a static
analysis). Sarma (1979) extends it to slices between inclined faces. That
paper was NOT consulted (spec 009, "Fuentes"): the recurrence below is the
project's own derivation of the force equilibrium of one wedge, written out
in ``spec/features/009-sarma-dovelas-no-verticales/plan.md``. What no
consulted source fixes, the published cases of the verification manual
fix, and the module says where: F reduces c and tan φ on the bases AND on
the faces (reducing only the bases, as the 1973 vertical-slice method
does, moves the three published cases by +14.8 %, −58 % and +2.8 %).

CONVENTIONS (the solving frame)

The mass slides toward −x; one that slides toward +x is reflected first
(x → −x: the order of the wedges, the sign of every angle and of every
horizontal force). Wedges i = 1…n run from the toe, between face i (the
toe side) and face i+1.

* base i: α positive rising toward +x, length l, t = (cos α, sin α),
  n = (−sin α, cos α);
* face j: δ from the vertical, positive when its top leans toward +x,
  length d, water thrust PW, s = (sin δ, cos δ), m = (cos δ, −sin δ);
* reduced strengths: c′ = c/F, tan φ′ = tan φ/F, and on the faces c̄′, φ̄′.

Forces on wedge i: the vertical load Wᵛ (soil·(1 + kv), loads and ponded
water), the seismic force −K·W_soil in x, the horizontal external force
Pₓ, the base N′(n + tan φ′ t) + U n + c′ l t, face i Eᵢ mᵢ + Xᵢ sᵢ and face
i+1 −Eᵢ₊₁ mᵢ₊₁ − Xᵢ₊₁ sᵢ₊₁, with X = σ[(E − PW) tan φ̄′ + c̄′ d]: E is the
TOTAL normal force on the face and σ = +1 the sense in which the upper
wedge moves down relative to the lower one. Projecting on
v = (cos(φ′ − α), −sin(φ′ − α)), normal to n + tan φ′ t, removes N′:

    Eᵢ₊₁ qᵢ = Aᵢ − K Pᵢ + Ẽᵢ Eᵢ
    qᵢ = cos(βᵢ − δᵢ₊₁) − tan φ̄ᵢ₊₁ sin(βᵢ − δᵢ₊₁),   β = φ′ − α
    Ẽᵢ = cos(βᵢ − δᵢ) − tan φ̄ᵢ sin(βᵢ − δᵢ)
    Aᵢ = Wᵛ sin β + Pₓ cos β + (c′l − U tan φ′) cos φ′
         + Sᵢ₊₁ sin(β − δᵢ₊₁) − Sᵢ sin(β − δᵢ)
    Pᵢ = W_soil cos β,      S = c̄′ d − PW tan φ̄′

(φ̄′ and c̄′ carry σ). The face at the toe is free (E₁ = 0) and the one at
the head carries only the water of a tension crack, Eₙ₊₁ (0 without one);
neither carries strength. Kc(F) is then linear in each: Kc = (N − Eₙ₊₁)/D.

THE ROOT

Kc(F) = kh has several roots and Kc has poles: in [0.05, 20], problem 5
of the manual (γw = 1) has 8 roots with the fixed sense and 5 with the
kinematic one, besides its poles. The factor is the LARGEST root, the
least reduction of the strength that brings the mass to limit
equilibrium: it is the rule the three published cases follow. It is
searched on H(F) = (N − kh·D − Eₙ₊₁)·Q, with Q the least common
denominator of Kc, which has no poles, by a descending sweep and Brent's
method (Brent 1973). A march on Kc from F = 1 jumps the published 0.434 of
the saturated problem 4, 1.4 % above a pole at 0.4288, and lands on 0.1467.

Q is NOT the product of every qᵢ. When qₖ and Ẽⱼ (J > K) are the same
function of F, which happens when bases K and J have the same α and tan φ
and faces K+1 and J the same δ and σ·tan φ̄ (a straight base cut by a face,
or a stepped surface whose steps repeat), qₖ cancels in Kc, and a
polynomial that kept it would cross zero where Kc = kh has no root. That
happened in v0.1.461 before this was written: on problem 5 at 0.673,
below its factor; on a toe with strength on the face between two collinear
bases at 2.064, ABOVE a true 1.741; and on a stepped surface the false zero
fell in the same sweep step as the largest root, 1.506, and hid it (1.084
came out). ``_pairs`` finds those factors, to a rounding tolerance, and
``_polynomial`` divides them out exactly.

A geometry NEAR such a coincidence (a base bent by Δα, say) has a true
root next to a true pole, and the largest root then carries face forces
that grow as 1/Δα (88 times the weight of the mass at 0.06°, 10 at 0.57°,
1.9 at 5.7°, against 1.2 with the straight base, in the test's toe). It is
a root of the equation, so it is returned, with ``max_force_ratio`` and
``min_abs_q`` for whoever reads the result to say so (owner's decision,
2026-11-15); the method says it with a note (``method.sarma_near_pole``,
v0.1.466, D451), and which root a near pole should leave is open (D452).

v0.1.470 (D452, the owner's decision): still open, and the factor is still
the largest root. Bent a hair, a cancelled factor splits into a root of N
and a zero of D, the denominator of Kc, a hair apart (problem 4 saturated
with its scarp bent 1 cm gives 0.9005, the published 0.4347 bent the same
being the next root down). A rule that skipped a root within 1.2 % of a
zero of D was measured and refuted by the adversarial review: the published
branch of problem 4 saturated lies 1.4 % from a TRUE zero of D, and kh 0.03
or γw = 10 bring it inside, the factor falling to 0.128 (the bench's
``_auditoria/P9_D452/medir_reglas_d452.py`` and the changelog of v0.1.470).
What is kept is the information: ``near_pair`` says how far the largest
root lies from a zero of D and finds the next root down, and the method
asks it only for a root already next to a pole of the recurrence (least
|q| under 0.2), where the pair is the likely cause.
And a near coincidence the GEOMETRY made, not the model, is no longer
made: the wedges are cut on the ends the vertical slicing resolved
(``wedges._with_resolved_ends``), so a straight end stretch whose end the
slicer put on the ground stays straight and its pair cancels exactly.

Author: Samuel Sáez López (UPCT)

References:
    Sarma, S. K. (1973). Stability analysis of embankments and slopes.
        Géotechnique 23(3), 423–433. Consulted.
    Sarma, S. K. (1979). Stability analysis of embankments and slopes.
        J. Geotech. Eng. Div. ASCE 105(GT12), 1511–1524. NOT consulted.
    Brent, R. P. (1973). Algorithms for Minimization without Derivatives.
        Prentice-Hall, ch. 4.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, NamedTuple, Optional, Sequence

import numpy as np
from scipy.optimize import brentq

from ogr_slip2d import messages as msg

#: The two senses of the shear on the faces.
#: ``fixed``: the upper wedge always moves down relative to the lower one.
#: ``kinematic``: the sense the rigid wedges' motion gives (see
#: :func:`kinematic_senses`), a derivation of the project declared as such.
FIXED = "fixed"
KINEMATIC = "kinematic"
SHEAR_SENSES = (FIXED, KINEMATIC)

#: The descending sweep. Above ``_F_MAX`` it steps by ``_COARSE_RATIO`` up
#: to ``_F_TOP``: a factor there only says the surface barely drives, and
#: above ``_F_TOP`` it is reported as one that does not slide. From
#: ``_F_MAX`` down to ``_F_MIN`` it steps by ``_SWEEP_RATIO``, the step
#: that decides whether a PAIR of roots can hide the largest one: both
#: inside one step leave no change of sign. Measured in v0.1.461: on
#: problem 5 the largest root (1.089) is ×1.38 above the next (0.788), on
#: problem 4 ×3.3 dry and ×2.96 saturated; 1.05 leaves the narrowest of
#: them 6.6 steps.
_F_TOP = 1.0e6
_F_MAX = 100.0
_F_MIN = 0.01
_COARSE_RATIO = 10.0
_SWEEP_RATIO = 1.05
#: v0.1.471 (D357, D457) -- the step of :func:`larger_root_above`, the guard
#: the optimiser of the face angles puts on each factor it accepts: the
#: census of D452 (42 753 surfaces) swept every H with it. A minimiser walks
#: toward where the 1.05 sweep hides a pair of roots (D457: it reports a
#: smaller root there), so its accepted factors are checked one by one; the
#: sweep of ``solve`` itself does not change.
FINE_SWEEP_RATIO = 1.002

#: A face whose direction differs from an adjacent base by less than this
#: (|cos(α + δ)|, the sine of the angle between them) is parallel to it.
_PARALLEL = 1e-12
#: Below this (relative to the wedges' speeds) two wedges do not slide on
#: their common face, and the face takes the fixed sense.
_NO_SLIP = 1e-12
#: v0.1.470 (D452): within this, relative, a zero of D beside the factor is
#: said (``near_pair``); it moves no factor. The window of the refuted rule
#: of the same version, kept for the note: between 1.05 % (the spurious root
#: of a toe bent 0.57°) and 1.4 % (the published saturated problem 4 from a
#: true zero of D), which a note can live with and a rule could not.
NEAR_KC_POLE = 0.012
#: The points ``_near_kc_pole`` looks for a change of sign of D at.
_NEAR_KC_SAMPLES = 33

#: Two angles [rad], or two tangents (relative), closer than this are the
#: same for ``_pairs``: a tan φ read through the numerical secant of a
#: Mohr-Coulomb material differs by up to 1.3e-12 between two slices of one
#: material (measured in v0.1.461), and 1e-9 is still far below any bend
#: a model draws.
_SAME = 1e-9


@dataclass(frozen=True)
class Base:
    """One wedge, as the solver sees it: its base and the loads on it.

    In MODEL coordinates (the solver reflects a mass that slides toward +x).

    Attributes:
        alpha: angle of the base [rad], positive rising toward +x.
        length: length of the base [m].
        weight: the whole vertical load [kN/m], downward: the soil weight
            times (1 + kv), the vertical part of the loads and the ponded
            water.
        soil_weight: the STATIC soil weight [kN/m], on which the
            horizontal coefficient acts (D170, D206).
        pore_force: U = ∫u dl on the base [kN/m].
        cohesion: c on the base [kPa].
        tan_phi: tan φ on the base.
        force_x: the horizontal external force [kN/m], positive toward +x
            (ponded water, loads, a crack's water already folded in).
    """

    alpha: float
    length: float
    weight: float
    soil_weight: float
    pore_force: float
    cohesion: float
    tan_phi: float
    force_x: float = 0.0


@dataclass(frozen=True)
class Face:
    """One face between two wedges (or at an end of the mass).

    Attributes:
        delta: angle from the vertical [rad], positive when the top of the
            face leans toward +x.
        length: length of the face [m].
        water_force: PW = ∫u dl on the face [kN/m].
        cohesion: c̄ on the face [kPa]; 0 on the two end faces.
        tan_phi: tan φ̄ on the face; 0 on the two end faces.
    """

    delta: float
    length: float
    water_force: float = 0.0
    cohesion: float = 0.0
    tan_phi: float = 0.0


@dataclass
class SarmaSolution:
    """What :func:`solve` found. Lists run in MODEL order (increasing x).

    ``fos`` is None, with ``code`` and ``args``, when there is no factor;
    never NaN. Negative effective normals are returned as they are:
    Sarma (1973) asks for the physical acceptability to be checked, and
    the published saturated problem 4 has its scarp in effective tension.
    """

    fos: Optional[float]
    converged: bool
    iterations: int
    slide_sign: int
    shear_sense: str
    code: str = ""
    args: dict = field(default_factory=dict)
    #: Kc at F = 1, Sarma's (1973) critical acceleration of the mass with
    #: its full strength (None at a pole). A diagnostic, unclipped.
    kc_at_1: Optional[float] = None
    #: N′ per base [kN/m]; E (total), E′ = E − PW and X per face [kN/m].
    base_normals: Optional[list] = None
    face_thrusts: Optional[list] = None
    face_effective: Optional[list] = None
    face_shears: Optional[list] = None
    #: PW per face [kN/m] (v0.1.468): the faces' own, and on the head face
    #: the water of a tension crack, which the faces give as 0.
    face_water: Optional[list] = None
    #: σ per face, and the wedges' speeds of the rigid mechanism (toe
    #: wedge 1), with whether all of them are positive.
    senses: Optional[list] = None
    velocities: Optional[list] = None
    kinematically_admissible: Optional[bool] = None
    #: min qᵢ over the q that divide a real face thrust at the factor (the
    #: analogue of m_α: a thrust next to a pole has its q next to zero).
    #: The q of the head face counts only with a crack's thrust on it.
    min_q: Optional[float] = None
    #: v0.1.466 (D451) -- min |qᵢ| over the same q: how close the root sits
    #: to a pole of Kc, whatever the sign of q (a negative q is ordinary: the
    #: published saturated problem 4 has one). A diagnostic; no root moves.
    min_abs_q: Optional[float] = None
    #: max |N′|, |E′|, |X| over the total vertical load: how far the root
    #: sits from a pole. 0.82 on the published saturated problem 4 (the
    #: toe's base normal), 1.2 on the toe of the test; a root next to a
    #: near-coincidence reaches 10 to 10⁵.
    max_force_ratio: Optional[float] = None

    @property
    def message(self) -> str:
        """The English sentence of ``code`` (empty without one)."""
        return msg.text(self.code, **self.args) if self.code else ""


# ---------------------------------------------------------------- the frame
@dataclass(frozen=True)
class _Frame:
    """The wedges in the solving frame (sliding toward −x, from the toe)."""

    alpha: tuple
    length: tuple
    weight: tuple
    soil: tuple
    pore: tuple
    c: tuple
    tan_phi: tuple
    px: tuple
    delta: tuple
    d: tuple
    pw: tuple
    cf: tuple
    tan_phi_f: tuple
    sigma: tuple
    head: float
    reflected: bool
    #: ``{J: K}``: the qₖ that cancels against Ẽⱼ (``_pairs``).
    pairs: dict = field(default_factory=dict)


def _check(bases, faces, slide_sign, shear_sense, tolerance, max_iterations,
           kh=0.0, head_thrust=0.0):
    if len(bases) < 1:
        raise ValueError("Sarma: at least one wedge is needed")
    if len(faces) != len(bases) + 1:
        raise ValueError("Sarma: n wedges need n + 1 faces (toe and head "
                         f"included); got {len(bases)} and {len(faces)}")
    if slide_sign not in (1, -1):
        raise ValueError(f"Sarma: slide_sign must be +1 or -1, not "
                         f"{slide_sign!r}")
    if shear_sense not in SHEAR_SENSES:
        raise ValueError(f"Sarma: shear_sense must be one of {SHEAR_SENSES}, "
                         f"not {shear_sense!r}")
    if not (tolerance > 0.0):
        raise ValueError("Sarma: the tolerance must be positive")
    if int(max_iterations) < 1:
        raise ValueError("Sarma: at least one iteration is needed")
    if not math.isfinite(kh):
        raise ValueError(f"Sarma: kh must be a finite number, not {kh!r}")
    if not (math.isfinite(head_thrust) and head_thrust >= 0.0):
        raise ValueError("Sarma: the head thrust (a crack's water) must be "
                         f"finite and not negative, not {head_thrust!r}")
    for b in bases:
        vals = (b.alpha, b.length, b.weight, b.soil_weight, b.pore_force,
                b.cohesion, b.tan_phi, b.force_x)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError(f"Sarma: a base has a non-finite value: {b}")
    for f in faces:
        vals = (f.delta, f.length, f.water_force, f.cohesion, f.tan_phi)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError(f"Sarma: a face has a non-finite value: {f}")
    # The toe face is free (E = 0) and the head face is a crack's wall: a
    # strength there would put a shear on a face nothing presses.
    for f in (faces[0], faces[-1]):
        if f.cohesion != 0.0 or f.tan_phi != 0.0:
            raise ValueError("Sarma: the faces at the two ends of the mass "
                             f"carry no strength: {f}")


def _frame(bases: Sequence[Base], faces: Sequence[Face], slide_sign: int,
           head_thrust: float) -> _Frame:
    """The wedges in the solving frame. A mass that slides toward +x is
    reflected (x → −x): the toe becomes the first wedge, every angle and
    every horizontal force changes sign. Nothing else does: weights,
    lengths, water forces and strengths are the same mass seen in a
    mirror.

    A head face with no crack's thrust carries nothing (no strength, no
    normal force), and its direction would only orient the fictitious
    Eₙ₊₁ the recurrence ends on; it is read as vertical, so that the sign
    of that Eₙ₊₁ means the same on every mass."""
    reflected = slide_sign == -1
    bs = list(reversed(bases)) if reflected else list(bases)
    fs = list(reversed(faces)) if reflected else list(faces)
    k = -1.0 if reflected else 1.0
    delta = [k * f.delta for f in fs]
    if head_thrust == 0.0:
        delta[-1] = 0.0
    fr = _Frame(
        alpha=tuple(k * b.alpha for b in bs),
        length=tuple(b.length for b in bs),
        weight=tuple(b.weight for b in bs),
        soil=tuple(b.soil_weight for b in bs),
        pore=tuple(b.pore_force for b in bs),
        c=tuple(b.cohesion for b in bs),
        tan_phi=tuple(b.tan_phi for b in bs),
        px=tuple(k * b.force_x for b in bs),
        delta=tuple(delta),
        d=tuple(f.length for f in fs),
        pw=tuple(f.water_force for f in fs),
        cf=tuple(f.cohesion for f in fs),
        tan_phi_f=tuple(f.tan_phi for f in fs),
        sigma=tuple(1 for _ in fs),
        head=float(head_thrust),
        reflected=reflected,
    )
    return replace(fr, pairs=_pairs(fr))


def _with_senses(fr: _Frame, senses: Sequence[int]) -> _Frame:
    fr = replace(fr, sigma=tuple(senses))
    return replace(fr, pairs=_pairs(fr))


def _model_face(fr: _Frame, j: int) -> int:
    """The model index of face ``j`` of the frame."""
    return len(fr.d) - 1 - j if fr.reflected else j


def _model_wedge(fr: _Frame, i: int) -> int:
    """The model index of wedge ``i`` of the frame."""
    return len(fr.alpha) - 1 - i if fr.reflected else i


def _parallel_face(fr: _Frame):
    """The first (face, wedge) pair of the frame whose face is parallel to
    the base of the wedge, or None. Only where the face acts: an interior
    face against both its wedges (one would leave no wedge, the other puts
    a pole of the recurrence at F = ∞, where the sweep starts), and the
    head face against the last wedge. The toe face never acts (E₁ = 0)."""
    n = len(fr.alpha)
    for j in range(1, n + 1):
        for i in (j - 1, j):
            if 0 <= i < n and abs(math.cos(fr.alpha[i] + fr.delta[j])) \
                    <= _PARALLEL:
                return j, i
    return None


def kinematic_senses(fr: _Frame):
    """The rigid wedges' speeds and the sense of the shear on each face.

    Each wedge moves down its own base, Vᵢ = −vᵢ tᵢ, and two neighbours
    keep the component normal to their common face equal (no gap, no
    overlap), so with v₁ = 1 on the toe wedge

        vᵢ = vᵢ₋₁ · cos(αᵢ₋₁ + δᵢ) / cos(αᵢ + δᵢ).

    The upper wedge's velocity relative to the lower one along the face,
    (Vᵢ − Vᵢ₋₁)·sᵢ, gives σ = +1 when it is downward (the fixed sense) and
    −1 when upward. A derivation of the project, declared as such: the
    compatibility of velocities of rigid blocks (spec 009). Two wedges whose
    relative velocity is zero (a straight base cut by a face) do not slide
    on that face, and it takes the fixed sense. The faces at the toe and
    the head take the fixed sense too. Speeds ≤ 0 (a wedge that would have
    to climb its base) are returned, not refused.
    """
    n = len(fr.alpha)
    senses = [1] * (n + 1)
    v = [1.0]
    for j in range(1, n):
        lo, up = j - 1, j
        v_up = v[-1] * math.cos(fr.alpha[lo] + fr.delta[j]) \
            / math.cos(fr.alpha[up] + fr.delta[j])
        rel = (-v_up * math.sin(fr.alpha[up] + fr.delta[j])
               + v[-1] * math.sin(fr.alpha[lo] + fr.delta[j]))
        if rel > _NO_SLIP * max(abs(v[-1]), abs(v_up)):
            senses[j] = -1
        v.append(v_up)
    return v, senses


# --------------------------------------------------------- the recurrence
class _Ops(NamedTuple):
    sin: Callable
    cos: Callable
    atan: Callable


#: One copy of the formulas, two arithmetics: ``math`` for one F (Brent),
#: NumPy for the whole sweep at once (ten times cheaper than a loop over it:
#: v0.1.461, 9 wedges). The sweep only reads signs from it, and they are
#: checked with ``math`` before Brent; every value the solver returns is
#: computed with ``math``.
_SCALAR = _Ops(math.sin, math.cos, math.atan)
_ARRAY = _Ops(np.sin, np.cos, np.arctan)


def _coefficients(fr: _Frame, g, ops: _Ops = _SCALAR):
    """Per wedge (A, P, Ẽ, q) at g = 1/F (g = 0 is F = ∞: no strength),
    and per face (tan φ̄′, S), signed by σ. ``g`` is a number, or an array
    with ``ops = _ARRAY``."""
    tf = [fr.sigma[j] * fr.tan_phi_f[j] * g for j in range(len(fr.d))]
    S = [fr.sigma[j] * fr.cf[j] * g * fr.d[j] - fr.pw[j] * tf[j]
         for j in range(len(fr.d))]
    rows = []
    for i in range(len(fr.alpha)):
        tp = fr.tan_phi[i] * g
        phi = ops.atan(tp)
        beta = phi - fr.alpha[i]
        R = fr.c[i] * g * fr.length[i] - fr.pore[i] * tp
        lo, up = beta - fr.delta[i], beta - fr.delta[i + 1]
        sin_lo, sin_up = ops.sin(lo), ops.sin(up)
        q = ops.cos(up) - tf[i + 1] * sin_up
        e = ops.cos(lo) - tf[i] * sin_lo
        A = (fr.weight[i] * ops.sin(beta) + fr.px[i] * ops.cos(beta)
             + R * ops.cos(phi) + S[i + 1] * sin_up - S[i] * sin_lo)
        P = fr.soil[i] * ops.cos(beta)
        rows.append((A, P, e, q))
    return rows, tf, S


def _same(a: float, b: float, relative: bool) -> bool:
    scale = max(1.0, abs(a)) if relative else 1.0
    return abs(a - b) <= _SAME * scale


def _pairs(fr: _Frame) -> dict:
    """``{J: K}``: qₖ and Ẽⱼ (K < J) are the same function of F, so qₖ
    cancels in Kc.

    qₖ = cos(βₖ − δₖ₊₁) − tan φ̄ₖ₊₁ sin(βₖ − δₖ₊₁) and
    Ẽⱼ = cos(βⱼ − δⱼ) − tan φ̄ⱼ sin(βⱼ − δⱼ), with β = atan(tan φ/F) − α:
    the same for every F when αₖ = αⱼ, tan φₖ = tan φⱼ, δₖ₊₁ = δⱼ and
    σₖ₊₁ tan φ̄ₖ₊₁ = σⱼ tan φ̄ⱼ (J = K + 1, the same face: a straight base of
    one strength cut by a face). In Kc, qₖ divides the terms i ≤ K and Ẽⱼ
    multiplies the same terms, so the pole qₖ = 0 is not a pole of Kc;
    left in the polynomial, it is a zero of it that is no root (module
    docstring, measured). Each qₖ and each Ẽⱼ cancels once; a J takes the
    nearest K still free."""
    n = len(fr.alpha)
    taken: set = set()
    out: dict = {}
    for J in range(1, n):
        for K in range(J - 1, -1, -1):
            if K in taken:
                continue
            if (_same(fr.alpha[K], fr.alpha[J], False)
                    and _same(fr.tan_phi[K], fr.tan_phi[J], True)
                    and _same(fr.delta[K + 1], fr.delta[J], False)
                    and _same(fr.sigma[K + 1] * fr.tan_phi_f[K + 1],
                              fr.sigma[J] * fr.tan_phi_f[J], True)):
                out[J] = K
                taken.add(K)
                break
    return out


def _polynomial(fr: _Frame, g, ops: _Ops = _SCALAR):
    """(Z_N, Z_D, Q): Kc = (Z_N − Eₙ₊₁·Q)/Z_D with Q the least common
    denominator of Kc, and no division by any q.

    Kc is Σᵢ (Aᵢ − K Pᵢ) ∏ⱼ₍ⱼ>ᵢ₎Ẽⱼ / ∏ₖ₍ₖ≥ᵢ₎qₖ − Eₙ₊₁, so with Q = ∏ qₖ
    over the k no pair cancels, term i is (Aᵢ − K Pᵢ)·∏ₖ₍ₖ<ᵢ₎qₖ·∏ⱼ₍ⱼ>ᵢ₎Ẽⱼ
    with, for every pair (K, J), qₖ removed when K < i and Ẽⱼ removed when
    K ≥ i. Horner's scheme carries the sum from the toe; the terms are kept
    in segments split after every K whose J is still ahead, because at
    step J the terms up to K take Ẽⱼ/qₖ = 1 and the later ones Ẽⱼ, and the
    split is dropped once J is passed. With no pair it is the plain
    Zᵢ₊₁ = (Aᵢ − K Pᵢ)·∏ₖ₍ₖ<ᵢ₎qₖ + ẼᵢZᵢ."""
    rows, _tf, _S = _coefficients(fr, g, ops)
    pairs = fr.pairs
    opens = set(pairs.values())
    segs = [[-1, 0.0, 0.0]]          # [K the segment starts after, Z_N, Z_D]
    Q = 1.0
    for i, (A, P, e, q) in enumerate(rows):
        K = pairs.get(i)
        first = 0
        if K is not None:
            first = next(s for s, seg in enumerate(segs) if seg[0] == K)
        for seg in segs[first:]:
            seg[1] = e * seg[1]
            seg[2] = e * seg[2]
        if K is not None:
            # J is passed: the terms on either side of K take the same
            # factors from here on
            segs[first - 1][1] = segs[first - 1][1] + segs[first][1]
            segs[first - 1][2] = segs[first - 1][2] + segs[first][2]
            del segs[first]
        segs[-1][1] = segs[-1][1] + A * Q
        segs[-1][2] = segs[-1][2] + P * Q
        if i in opens:
            segs.append([i, 0.0, 0.0])
        else:
            Q = Q * q
    zn = segs[0][1]
    zd = segs[0][2]
    for seg in segs[1:]:
        zn = zn + seg[1]
        zd = zd + seg[2]
    return zn, zd, Q


def _H(fr: _Frame, g, kh: float, ops: _Ops = _SCALAR):
    zn, zd, Q = _polynomial(fr, g, ops)
    return zn - kh * zd - fr.head * Q


def _kc(fr: _Frame, g: float) -> Optional[float]:
    zn, zd, Q = _polynomial(fr, g)
    if zd == 0.0:
        return None
    return (zn - fr.head * Q) / zd


def kc(bases: Sequence[Base], faces: Sequence[Face], F: float, *,
       slide_sign: int = 1, shear_sense: str = FIXED,
       head_thrust: float = 0.0) -> Optional[float]:
    """Kc(F): the horizontal coefficient that holds the wedges in limit
    equilibrium with their strengths divided by ``F`` (Sarma 1973), from
    the recurrence of :mod:`ogr_slip2d.sarma.solver`. None where it has a
    pole, and with a face parallel to a base."""
    _check(bases, faces, slide_sign, shear_sense, 1.0, 1,
           head_thrust=head_thrust)
    if not (F > 0.0):
        raise ValueError("Sarma: F must be positive")
    fr = _frame(bases, faces, slide_sign, head_thrust)
    if _parallel_face(fr) is not None:
        return None
    if shear_sense == KINEMATIC:
        fr = _with_senses(fr, kinematic_senses(fr)[1])
    g = 0.0 if math.isinf(F) else 1.0 / F
    return _kc(fr, g)


def _forces(fr: _Frame, F: float, kh: float):
    """N′ per base and (E, E′, X) per face at F, in the frame, the min q
    and min |q| of ``SarmaSolution``, and PW per face. None where a q
    vanishes at F itself."""
    g = 1.0 / F
    rows, tf, S = _coefficients(fr, g)
    n = len(fr.alpha)
    E = [0.0]
    for A, P, e, q in rows:
        if q == 0.0:
            return None
        E.append((A - kh * P + e * E[-1]) / q)
    # The recurrence closes on the head thrust: E[n] is Eₙ₊₁ at the root,
    # equal to ``fr.head`` within the root's tolerance. Report the given
    # one, the one that acts.
    E[n] = fr.head
    X = [tf[j] * E[j] + S[j] for j in range(n + 1)]
    normals = []
    for i in range(n):
        a = fr.alpha[i]
        dl, du = fr.delta[i], fr.delta[i + 1]
        # every force on wedge i except the base reaction
        fx = (-kh * fr.soil[i] + fr.px[i]
              + E[i] * math.cos(dl) + X[i] * math.sin(dl)
              - E[i + 1] * math.cos(du) - X[i + 1] * math.sin(du))
        fy = (-fr.weight[i]
              - E[i] * math.sin(dl) + X[i] * math.cos(dl)
              + E[i + 1] * math.sin(du) - X[i + 1] * math.cos(du))
        # base reaction = −(the rest); N′ = R·n − U, n = (−sin α, cos α)
        normals.append((fx * math.sin(a) - fy * math.cos(a))
                       - fr.pore[i])
    # v0.1.468 -- the water of a tension crack is the head thrust, on an end
    # face whose PW is 0 by construction (the review of 0.1.468): it is that
    # face's water, so its E′ = E − PW is 0, not the crack's whole thrust
    water = list(fr.pw)
    water[n] += fr.head
    eff = [E[j] - water[j] for j in range(n + 1)]
    # qᵢ divides Eᵢ₊₁: a real thrust for every interior face, and for the
    # head face only under a crack's water
    dividing = [rows[i][3] for i in range(n - 1)]
    if fr.head != 0.0:
        dividing.append(rows[n - 1][3])
    return (normals, E, eff, X, (min(dividing) if dividing else None),
            (min(abs(q) for q in dividing) if dividing else None), water)


class WedgeForce(NamedTuple):
    """One force on a wedge, in MODEL coordinates [kN/m] (v0.1.467):
    ``name`` is ``Wv`` (the vertical load: soil·(1 + kv), loads and ponded
    water, which is more than the panel's soil weight), ``kh·Ws`` (the
    seismic force on the static soil weight), ``Px`` (the horizontal
    external force), ``N′`` and ``U`` (the effective normal and the water on
    the base), ``S`` (the mobilised shear on the base), or ``E`` and ``X``
    (the total normal and the shear on face ``face``, a model index from 0).

    ``value`` is the force with the sign of its convention, which the
    vector alone hides (the review of v0.1.467: an effective normal in
    tension, the physical acceptability Sarma 1973 asks to check, read as
    its modulus): Wv downward, kh·Ws in the sense of sliding, Px along +x,
    N′ and U along the base's inward normal, S along the base toward its
    rising end in the solving frame, E compressive, X with the sense σ of
    the face."""

    name: str
    face: Optional[int]
    fx: float
    fy: float
    value: float


def wedge_free_bodies(bases: Sequence[Base], faces: Sequence[Face],
                      F: float, *, kh: float = 0.0, slide_sign: int = 1,
                      shear_sense: str = FIXED,
                      head_thrust: float = 0.0) -> Optional[list]:
    """Every force on every wedge at the factor ``F``, in model order and
    model coordinates: a list of :class:`WedgeForce` per wedge, or None
    when a q vanishes at ``F`` itself (v0.1.467, D357).

    E and X come from the recurrence the root was found on
    (:func:`_forces`), with the senses :func:`solve` used; N′ is the
    solver's; S is the base's LIMIT shear, c′l + N′ tan φ′ (the condition
    the projection on v builds in), not the rest of the balance. So each
    list sums to zero only if the wedge is in equilibrium at ``F``: the
    check a free body is for, and the one a sign put wrong breaks. To the
    tolerance of the root: the head face takes the given thrust and not
    the recurrence's last E, so what is left sits on the head wedge
    (2.6e-4 of its load at the default tolerance of 1e-4 on the
    saturated problem 4 with the bisector, 1e-13 at 1e-12).

    No points of application: the derivation balances the forces of each
    wedge, not their moments (module docstring), so where E and X act on a
    face is not part of the solution. Whoever draws them says so.
    """
    fr = _frame(bases, faces, slide_sign, head_thrust)
    if shear_sense == KINEMATIC:
        _v, kin = kinematic_senses(fr)
        fr = _with_senses(fr, kin)
    forces = _forces(fr, F, kh)
    if forces is None:
        return None
    normals, E, _eff, X = forces[:4]
    n = len(fr.alpha)
    g = 1.0 / F
    k = -1.0 if fr.reflected else 1.0
    out = [None] * n
    for i in range(n):
        a = fr.alpha[i]
        dl, du = fr.delta[i], fr.delta[i + 1]
        nv = (-math.sin(a), math.cos(a))
        tv = (math.cos(a), math.sin(a))
        Np = normals[i]
        S = fr.c[i] * g * fr.length[i] + Np * fr.tan_phi[i] * g
        U = fr.pore[i]
        # the faces in MODEL indices: the frame runs from the toe, which
        # is the model's right end when the mass was reflected
        toe = (n - i) if fr.reflected else i
        head = (n - i - 1) if fr.reflected else i + 1
        items = [
            ("Wv", None, 0.0, -fr.weight[i], fr.weight[i]),
            ("kh·Ws", None, -kh * fr.soil[i], 0.0, kh * fr.soil[i]),
            ("Px", None, fr.px[i], 0.0, k * fr.px[i]),
            ("N′", None, Np * nv[0], Np * nv[1], Np),
            ("U", None, U * nv[0], U * nv[1], U),
            ("S", None, S * tv[0], S * tv[1], S),
            ("E", toe, E[i] * math.cos(dl), -E[i] * math.sin(dl), E[i]),
            ("X", toe, X[i] * math.sin(dl), X[i] * math.cos(dl), X[i]),
            ("E", head, -E[i + 1] * math.cos(du), E[i + 1] * math.sin(du),
             E[i + 1]),
            ("X", head, -X[i + 1] * math.sin(du), -X[i + 1] * math.cos(du),
             X[i + 1]),
        ]
        model = (n - 1 - i) if fr.reflected else i
        out[model] = [WedgeForce(name, face, k * fx, fy, value)
                      for name, face, fx, fy, value in items]
    return out


def _near_kc_pole(fr: _Frame, F: float) -> Optional[float]:
    """The relative distance from ``F`` to the nearest zero of D, the
    denominator of Kc, when one lies within ``NEAR_KC_POLE`` of it, or None
    (v0.1.470, D452). A zero is a change of sign of D between two of
    ``_NEAR_KC_SAMPLES`` points across the window, refined by Brent."""
    eps = NEAR_KC_POLE
    if not (0.0 < eps < 1.0):
        return None
    xs = np.geomspace(F * (1.0 - eps), F * (1.0 + eps), _NEAR_KC_SAMPLES)
    zd = np.asarray(_polynomial(fr, 1.0 / xs, _ARRAY)[1], dtype=float)
    if not np.any(zd):
        # D ≡ 0 (no base carries soil weight, which ``_check`` admits): Kc
        # has no denominator to have a zero of, and every sample would be
        # one (the review of v0.1.470)
        return None
    best = None
    for i in range(len(xs) - 1):
        if zd[i] == 0.0:
            p = float(xs[i])
        elif (zd[i] > 0.0) != (zd[i + 1] > 0.0):
            p = brentq(lambda x: _polynomial(fr, 1.0 / x)[1], xs[i],
                       xs[i + 1], xtol=1e-12 * F)
        else:
            continue
        d = abs(F - p) / F
        if best is None or d < best:
            best = d
    return best


def _lower_root(fr: _Frame, kh: float, below: float, tolerance: float,
                max_iterations: int):
    """The next root of H under ``below``, down the sweep, by Brent:
    ``(F, iterations, lower end)``, or None when there is none or Brent does
    not converge (v0.1.470)."""
    grid = [x for x in _sweep() if x < below * (1.0 - 1e-15)]
    h_prev, F_prev = _H(fr, 1.0 / below, kh), below
    if h_prev == 0.0:
        if not grid:
            return None
        F_prev = grid.pop(0)
        h_prev = _H(fr, 1.0 / F_prev, kh)
    for x in grid:
        h = _H(fr, 1.0 / x, kh)
        if h == 0.0:
            return x, 0, x
        if (h > 0.0) != (h_prev > 0.0):
            root, r = brentq(lambda y: _H(fr, 1.0 / y, kh), x, F_prev,
                             xtol=tolerance, maxiter=int(max_iterations),
                             full_output=True, disp=False)
            if not r.converged:
                return None
            return float(root), int(r.iterations), x
        h_prev, F_prev = h, x
    return None


def near_pair(bases: Sequence[Base], faces: Sequence[Face], F: float, *,
              kh: float = 0.0, slide_sign: int = 1, shear_sense: str = FIXED,
              head_thrust: float = 0.0, tolerance: float = 1e-4,
              max_iterations: int = 75) -> Optional[tuple]:
    """Whether the root ``F`` of these wedges (the factor ``solve`` found)
    lies within ``NEAR_KC_POLE`` of a zero of D, the denominator of Kc:
    ``(relative distance, next root down or None)``, or None when it does
    not (v0.1.470, D452).

    With a pole of the recurrence beside it (a least |q| near zero), such a
    root is the likely half of a root and a pole that almost cancel, as a
    straight stretch barely bent leaves them, and the next root down the
    one the unbent surface has. Information, not a rule: the factor stays
    the largest root (module docstring). The next root is the next change
    of sign of H down the sweep, refined by Brent with the same tolerance;
    one the sweep's step hides is not found."""
    fr = _frame(bases, faces, slide_sign, head_thrust)
    if _parallel_face(fr) is not None:
        return None
    if shear_sense == KINEMATIC:
        fr = _with_senses(fr, kinematic_senses(fr)[1])
    d = _near_kc_pole(fr, F)
    if d is None:
        return None
    lower = [x for x in _sweep() if x < F]
    if not lower:
        return d, None
    nxt = _lower_root(fr, kh, lower[0], tolerance, max_iterations)
    return d, (None if nxt is None else nxt[0])


def _sweep(ratio: Optional[float] = None) -> list:
    """The trial factors, from the top down (∞ is tried first, apart), with
    the step ``ratio`` below ``_F_MAX`` (``_SWEEP_RATIO`` when None, read at
    the call, so a test that patches the module's step reaches it)."""
    ratio = _SWEEP_RATIO if ratio is None else ratio
    out = []
    F = _F_TOP
    while F > _F_MAX * (1.0 + 1e-12):
        out.append(F)
        F /= _COARSE_RATIO
    F = _F_MAX
    while F > _F_MIN:
        out.append(F)
        F /= ratio
    out.append(_F_MIN)
    return out


def larger_root_above(bases: Sequence[Base], faces: Sequence[Face],
                      F: float, *, kh: float = 0.0, slide_sign: int = 1,
                      shear_sense: str = FIXED,
                      head_thrust: float = 0.0) -> Optional[float]:
    """A factor above ``F`` where H changes sign, swept down from F = ∞ with
    the step ``FINE_SWEEP_RATIO``, or None (v0.1.471, D357, D457): ``F``,
    the factor :func:`solve` gave these wedges, is then not their largest
    root, because the 1.05 sweep stepped over a pair of roots above it.

    The guard of the optimiser of the face angles (``optimize_angles``):
    a minimiser is drawn to exactly those wedges, where the factor reported
    is too small. The answer is the lower end of the first step down the
    fine sweep whose sign differs from the one above it, at least
    ``1 + 1e-6`` times ``F``: a root that close is ``F`` itself, refined.
    A pair of roots closer than the fine step is not seen either."""
    fr = _frame(bases, faces, slide_sign, head_thrust)
    if _parallel_face(fr) is not None:
        return None
    if shear_sense == KINEMATIC:
        fr = _with_senses(fr, kinematic_senses(fr)[1])
    floor = float(F) * (1.0 + 1e-6)
    grid = np.asarray([x for x in _sweep(FINE_SWEEP_RATIO) if x > floor])
    if not len(grid):
        return None
    h_prev = _H(fr, 0.0, kh)
    hs = np.asarray(_H(fr, 1.0 / grid, kh, _ARRAY), dtype=float)
    for x, h in zip(grid, hs):
        if h == 0.0 or (h > 0.0) != (h_prev > 0.0):
            return float(x)
        h_prev = h
    return None


def _bracket(fr: _Frame, kh: float, h_inf: float, ops: _Ops):
    """(lo, hi): the first change of sign of H down the sweep, from F = ∞
    (``hi`` is ∞ when it is between ∞ and the top), or None."""
    grid = _sweep()
    if ops is _SCALAR:
        hs = [_H(fr, 1.0 / F, kh) for F in grid]
    else:
        hs = np.asarray(_H(fr, 1.0 / np.asarray(grid), kh, ops)).tolist()
    h_prev, F_prev = h_inf, math.inf
    for F, h in zip(grid, hs):
        if h == 0.0 or (h > 0.0) != (h_prev > 0.0):
            return F, F_prev
        h_prev, F_prev = h, F
    return None


def solve(bases: Sequence[Base], faces: Sequence[Face], *, kh: float = 0.0,
          slide_sign: int = 1, shear_sense: str = FIXED,
          head_thrust: float = 0.0, tolerance: float = 1e-4,
          max_iterations: int = 75) -> SarmaSolution:
    """The factor of safety of a set of wedges by Sarma's method with
    non-vertical slices: the largest F with Kc(F) = kh.

    Args:
        bases: the n wedges, in increasing x (model coordinates).
        faces: the n + 1 faces in increasing x: ``faces[i]`` and
            ``faces[i + 1]`` bound ``bases[i]``. The faces at the two ends
            of the mass carry no strength and are usually of zero length.
        kh: the applied horizontal coefficient, a magnitude in the sense of
            sliding (0 in a static analysis).
        slide_sign: +1 when the mass slides toward −x (the toe on the left),
            −1 toward +x.
        shear_sense: ``fixed`` or ``kinematic`` (:func:`kinematic_senses`).
        head_thrust: the total normal force on the face at the head of the
            mass, the water of a tension crack (½γw·h_w²); 0 without one.
        tolerance: Brent's tolerance on F.
        max_iterations: Brent's iterations; past them, no factor.

    Returns:
        A :class:`SarmaSolution`. Without a factor it carries the code:
        ``SARMA_FACE_PARALLEL``, ``SARMA_NO_DRIVING``, ``SARMA_NO_ROOT`` or
        ``NOT_CONVERGED``.

    Raises:
        ValueError: on a malformed call (a count, a non-finite number, a
            strength on an end face): a caller's mistake, not a surface.

    Reference: Sarma (1973) for Kc and F; Sarma (1979, not consulted) for
    the method; the recurrence is the derivation of spec 009 (module
    docstring); Brent (1973) for the root.
    """
    _check(bases, faces, slide_sign, shear_sense, tolerance, max_iterations,
           kh=kh, head_thrust=head_thrust)
    fr = _frame(bases, faces, slide_sign, head_thrust)
    sign = int(slide_sign)

    def failed(code, iterations=0, **args):
        return SarmaSolution(fos=None, converged=False, iterations=iterations,
                             slide_sign=sign, shear_sense=shear_sense,
                             code=code, args=args)

    bad = _parallel_face(fr)
    if bad is not None:
        j, i = bad
        return failed(msg.SARMA_FACE_PARALLEL, face=_model_face(fr, j) + 1,
                      wedge=_model_wedge(fr, i) + 1)
    v, kin = kinematic_senses(fr)
    if shear_sense == KINEMATIC:
        fr = _with_senses(fr, kin)
    senses = list(fr.sigma)
    speeds = list(v)
    if fr.reflected:
        senses.reverse()
        speeds.reverse()

    # F = ∞: no strength anywhere. If the head thrust the recurrence asks
    # for, H/Q, is already at or above the one acting, the mass stands
    # without strength at kh, and no reduction of it brings Kc down to kh.
    h_inf = _H(fr, 0.0, kh)
    q_inf = _polynomial(fr, 0.0)[2]
    if h_inf / q_inf >= 0.0:
        return failed(msg.SARMA_NO_DRIVING, kh=kh, f_top=_F_TOP)

    found = _bracket(fr, kh, h_inf, _ARRAY)
    if found is not None:
        h_lo = _H(fr, 1.0 / found[0], kh)
        h_hi = h_inf if math.isinf(found[1]) else _H(fr, 1.0 / found[1], kh)
        if h_lo != 0.0 and (h_lo > 0.0) == (h_hi > 0.0):
            found = None
    if found is None:
        # No change of sign, or one that the scalar arithmetic does not
        # confirm (H at rounding level at a grid point): the sweep again,
        # with the arithmetic Brent uses.
        found = _bracket(fr, kh, h_inf, _SCALAR)
    if found is None:
        return failed(msg.SARMA_NO_ROOT, kh=kh, f_min=_F_MIN)
    lo, hi = found
    if math.isinf(hi):
        # The sign changed between F = ∞ and the top of the sweep: the
        # factor is above _F_TOP, which is a surface that barely drives.
        return failed(msg.SARMA_NO_DRIVING, kh=kh, f_top=_F_TOP)

    iterations = 0
    h_lo, h_hi = _H(fr, 1.0 / lo, kh), _H(fr, 1.0 / hi, kh)
    if h_lo == 0.0:
        F, converged = lo, True
    elif h_hi == 0.0:
        F, converged = hi, True
    else:
        F, r = brentq(lambda x: _H(fr, 1.0 / x, kh), lo, hi, xtol=tolerance,
                      maxiter=int(max_iterations), full_output=True,
                      disp=False)
        iterations = int(r.iterations)
        converged = bool(r.converged)
    if not converged:
        return failed(msg.NOT_CONVERGED, iterations=iterations)

    out = SarmaSolution(fos=float(F), converged=True, iterations=iterations,
                        slide_sign=sign, shear_sense=shear_sense,
                        kc_at_1=_kc(fr, 1.0), senses=senses,
                        velocities=speeds,
                        kinematically_admissible=all(s > 0.0 for s in v))
    forces = _forces(fr, F, kh)
    if forces is not None:
        normals, E, eff, X, out.min_q, out.min_abs_q, water = forces
        load = abs(sum(fr.weight))
        if load > 0.0:
            out.max_force_ratio = max(
                max(abs(x) for x in normals), max(abs(x) for x in eff),
                max(abs(x) for x in X)) / load
        if fr.reflected:
            normals, E, eff, X, water = (
                list(reversed(normals)), list(reversed(E)),
                list(reversed(eff)), list(reversed(X)), list(reversed(water)))
        out.base_normals, out.face_thrusts = normals, E
        out.face_effective, out.face_shears = eff, X
        out.face_water = water
    return out
