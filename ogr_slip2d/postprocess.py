# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Interslice-force and line-of-thrust post-processing.

Given a converged :class:`LEMResult`, this module marches the slice
force-equilibrium equations left → right at the converged Factor of
Safety to recover the horizontal (E) and vertical (X) interslice forces
and the *line of thrust* — the locus of application points of the
interslice resultants (Fredlund & Krahn, 1977; Abramson et al., 2001).

Formulation (per slice, raw signed geometry, no slide-sign flip):

    unknowns:  N   (total base normal),  E_R (right-face horizontal)
    given:     E_L, X_L (from previous slice),  X_R = r_R · E_R

    ΣFx = 0:  N·n_x + s·S·t_x + E_L − E_R + H          = 0
    ΣFy = 0:  N·n_y + s·S·t_y + X_L − X_R − W_eff      = 0

with  t = (cos α, sin α),  n = (−sin α, cos α),
      S = (c·l + (N − u·l)·tanφ)/F = k0 + a·N   (mobilised shear),
      s = ±1 the resisting direction (opposes sliding),
      H  the horizontal seismic pseudo-force (in the sliding direction)
         plus the horizontal water force (signed in +x),
      W_eff the total vertical load of the slice, soil and ponded water.

v0.1.214 (D173) — ``H`` and ``W_eff`` come from
:func:`~ogr_slip2d.external_forces.slice_forces`, the loads every method
applied. They were rebuilt here by hand as ``W·(1 − kv)`` and
``kh·W·(1 − kv)``: no ponded water, no horizontal water force, and the
vertical coefficient in the opposite sense to the solvers' (D170). On the
upstream face of a dam, with four times the soil weight in water standing on
the slices, the march returned exactly the same N and E with the water as
without it. The earthquake itself comes from the result
(``details["kh"]``/``details["kv"]``, what the method applied) unless the
caller passes it, so a caller with no project — the slice-data panel of the
interpretation window — no longer marches without it.

Substituting S the system is linear in (N, E_R) and solved in closed
form. The application height of E_R (line of thrust) then follows from
the moment balance about the base midpoint, where N and S are assumed
to act (standard assumption).

Boundary conditions: E = X = 0 at both free ends. For rigorous
force-equilibrium methods (Spencer, GLE, Lowe-Karafiath) the closure
residual E_n is small; for moment-only methods (Bishop, Ordinary) a
non-zero closure is expected and reported, not hidden.

The interslice ratios r_i (X/E at each boundary) come from
``LEMResult.details["boundary_ratios"]`` when the method provides them
(Spencer: λ; GLE: λ·f(x); Lowe-Karafiath: tanθ_i) and default to zeros
(Bishop, Janbu, Ordinary). Because some methods compute λ in a
slide-sign-flipped frame, both sign conventions are tried and the one
with the smaller closure |E_n| is kept.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .checks import equilibrium_fos
from .external_forces import slice_forces
from .methods.base import LEMResult
from .methods.bishop import BishopSimplified


@dataclass
class InterSliceState:
    """Interslice forces and line of thrust for one LEM result."""

    # n+1 boundary values (index 0 = left free end .. n = right free end)
    E: list[float] = field(default_factory=list)   # horizontal force
    X: list[float] = field(default_factory=list)   # vertical force
    y_thrust: list[float] = field(default_factory=list)  # application y
    # n per-slice values, consistent with the E/X march
    N: list[float] = field(default_factory=list)   # total base normal
    S: list[float] = field(default_factory=list)   # mobilised base shear
    closure: float = math.nan   # |E_n| (should be ~0 for force methods)
    e_max: float = 0.0          # max |E| (for normalising closure)
    ok: bool = False
    # v0.1.221 (D212) -- per slice, the reinforcement the march applied:
    # ``[f_x, f_y]`` and its moment about the base midpoint, as the method
    # published them; empty without a support. The free-body diagram of the
    # interpretation draws the force.
    support_force: list = field(default_factory=list)
    support_moment: list = field(default_factory=list)

    @property
    def relative_closure(self) -> float:
        if not math.isfinite(self.closure) or self.e_max <= 0:
            return math.inf
        return self.closure / self.e_max


# ----------------------------------------------------------------------
def _quad_centroid_x(s) -> float:
    """x of the centroid of the slice quadrilateral."""
    xs = (s.base_x_left, s.base_x_right, s.base_x_right, s.base_x_left)
    ys = (s.base_y_left, s.base_y_right, s.top_y_right, s.top_y_left)
    a2 = 0.0
    cx6 = 0.0
    for i in range(4):
        j = (i + 1) % 4
        cross = xs[i] * ys[j] - xs[j] * ys[i]
        a2 += cross
        cx6 += (xs[i] + xs[j]) * cross
    if abs(a2) < 1e-12:
        return 0.5 * (s.base_x_left + s.base_x_right)
    return cx6 / (3.0 * a2)


def _quad_centroid_y(s) -> float:
    xs = (s.base_x_left, s.base_x_right, s.base_x_right, s.base_x_left)
    ys = (s.base_y_left, s.base_y_right, s.top_y_right, s.top_y_left)
    a2 = 0.0
    cy6 = 0.0
    for i in range(4):
        j = (i + 1) % 4
        cross = xs[i] * ys[j] - xs[j] * ys[i]
        a2 += cross
        cy6 += (ys[i] + ys[j]) * cross
    if abs(a2) < 1e-12:
        return 0.5 * (s.base_y_left + s.top_y_left)
    return cy6 / (3.0 * a2)


# ----------------------------------------------------------------------
# v0.1.221 (D212) -- whether the march carries the reinforcement the method
# applied. Until this version it rebuilt each slice's equilibrium with the
# method's loads (``slice_forces``, the water, the earthquake and its sense,
# D173) and NO support force, so on a reinforced slope the interslice forces
# and the line of thrust were those of a bare one, and since v0.1.216 (D196)
# its N parted from the column the method publishes on every crossed slice:
# on the -15 degree nail of ``test_support_normal_v1137`` the march gave
# 6.686 kN/m where Bishop's own normal is 15.607 (6.565 against 15.381 with
# Janbu). Each method now publishes the force it applied per slice
# (``details["support_force"]``: the normal part whole and the tangential
# part mobilised at ``t_active + t_passive/F``, the same vector for every
# family; see ``support_integration.support_force_on_slice``) and its moment
# about the base midpoint (``details["support_moment"]``), and the march adds
# them: the force to the slice's two force balances, the moment to its line
# of thrust. The strength is linearised where the method did, with the
# support load its own estimate carried (``details["sigma_support_load"]``).
# A module switch, like ``bishop.SUPPORT_IN_PUBLISHED_NORMAL``, so an A/B can
# rebuild the bare march and a test can demand that it moves (rule 7).
SUPPORT_IN_MARCH = True


def _per_slice_list(details, key, n):
    """``details[key]`` when it is a list of ``n`` entries, else None: the
    march reads what the method published and nothing it did not."""
    raw = details.get(key) if details else None
    if raw is None or isinstance(raw, (str, bytes)):
        return None
    try:
        vals = list(raw)
    except TypeError:
        return None
    return vals if len(vals) == n else None


def _march(slist, ratios, F, kh, kv,
           envelope_stress=None, slide_sign=None, support_force=None,
           support_moment=None, support_load=None) -> InterSliceState:
    """Single left→right equilibrium march with the given boundary
    ratios. Returns the full state (E, X, N, S, thrust line).

    ``slide_sign`` is the sense of sliding the method solved with
    (``details["slide_sign"]``); None falls back to the soil-weight sum.

    ``support_force``, ``support_moment`` and ``support_load`` (v0.1.221,
    D212) are the reinforcement the method applied, per slice: the force
    ``[f_x, f_y]`` (+x, +y), its moment about the base midpoint and the load
    the method's stress estimate carried; None without a support."""
    n = len(slist)
    st = InterSliceState()
    st.E = [0.0] * (n + 1)
    st.X = [0.0] * (n + 1)
    st.N = [0.0] * n
    st.S = [0.0] * n
    st.y_thrust = [0.0] * (n + 1)

    # Resisting direction: opposes the sliding the METHOD assumed.
    #
    # v0.1.214 (D173) -- read from the method, not re-guessed. The march
    # re-solves the method's own slice equations at its F and its λ, so the
    # shear has to point where the method's did; with X = 0 the N below is
    # then the ``base_normal_force`` Bishop and Janbu publish, exactly. The
    # guess below agrees with every method that derives its sense from
    # ``Σ W·sin α`` (all but the two Janbu), and Janbu derives it from
    # ``Σ w_total·tan α``, which can disagree when water stands on a steep
    # passive base (defect D112's witness). The guess stays as the fallback
    # for a result that does not carry the key.
    if slide_sign in (1.0, -1.0):
        s_dir = float(slide_sign)
    else:
        drive = sum(-s.weight * math.sin(s.base_angle) for s in slist)
        s_dir = -1.0 if drive > 0 else 1.0
    # Horizontal pseudo-force acts in the movement direction (−s_dir·t̄,
    # whose horizontal sign is −s_dir since cos α > 0).
    h_dir = -s_dir

    # Thrust starts at the base end (E=0 there).
    st.y_thrust[0] = slist[0].base_y_left
    if support_force is not None:
        st.support_force = [list(f) if f is not None else [0.0, 0.0]
                            for f in support_force]
        st.support_moment = (list(support_moment)
                             if support_moment is not None
                             else [0.0] * n)

    for i, s in enumerate(slist):
        alpha = s.base_angle
        l = s.base_length
        u = s.pore_pressure
        # v0.1.214 (D173) -- the loads the solver applied, water included.
        fx = slice_forces(s, kh, kv)
        W_eff = fx.w_total
        H_seis = h_dir * fx.h_seismic
        H = H_seis + fx.h_water
        # v0.1.221 (D212) -- and the reinforcement it applied.
        sup_x = sup_y = sup_m = 0.0
        if support_force is not None and support_force[i] is not None:
            sup_x, sup_y = support_force[i]
            if support_moment is not None:
                sup_m = support_moment[i]

        W_est = W_eff
        if support_load is not None and support_load[i]:
            W_est = W_eff + support_load[i]
        sigma_est = max(0.0, W_est * math.cos(alpha) - u * l) / max(l, 1e-9)
        # v0.1.213 (D84) -- the stress the method read a curved envelope at,
        # so the displayed state is built from the same straight line.
        if envelope_stress is not None and envelope_stress[i] is not None:
            sigma_est = max(0.0, envelope_stress[i])
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma_est)

        a = tan_phi / F
        k0 = (c_loc * l - u * l * tan_phi) / F
        tx, ty = math.cos(alpha), math.sin(alpha)
        nx, ny = -ty, tx
        r_R = ratios[i + 1]

        # Linear 2x2 in (N, E_R):
        #   A1·N − E_R       + C1 = 0
        #   A2·N − r_R·E_R   + C2 = 0
        A1 = nx + s_dir * a * tx
        A2 = ny + s_dir * a * ty
        C1 = st.E[i] + H + s_dir * k0 * tx
        C2 = st.X[i] - W_eff + s_dir * k0 * ty
        if sup_x or sup_y:
            C1 += sup_x
            C2 += sup_y
        det = A2 - A1 * r_R
        if abs(det) < 1e-9:
            st.ok = False
            st.closure = math.nan
            return st
        N = (C1 * r_R - C2) / det
        E_R = (A2 * C1 - A1 * C2) / det
        S = k0 + a * N

        st.N[i] = N
        st.S[i] = s_dir * S  # signed along t
        st.E[i + 1] = E_R
        st.X[i + 1] = r_R * E_R

        # ---- line of thrust: moments about the base midpoint ---------
        x_cb = 0.5 * (s.base_x_left + s.base_x_right)
        y_cb = 0.5 * (s.base_y_left + s.base_y_right)
        x_g = _quad_centroid_x(s)
        y_g = _quad_centroid_y(s)
        x_L, x_R = s.base_x_left, s.base_x_right
        y_tL = st.y_thrust[i]

        # M_z of F=(Fx,Fy) applied at (px,py) about (x_cb,y_cb):
        #     (px−x_cb)·Fy − (py−y_cb)·Fx
        M_L = (x_L - x_cb) * st.X[i] - (y_tL - y_cb) * st.E[i]
        # The soil at its centroid; the ponded water's vertical resultant
        # at the middle of the slice top, which shares its x with the base
        # midpoint (``slicer._apply_ponded_water``), so it has no arm here;
        # the seismic force at the soil centroid; the horizontal water
        # forces at their own elevation, through the moment the slicer
        # stored about y = 0 because two of them can have opposite signs.
        M_W = -(x_g - x_cb) * fx.w_soil
        M_H = -(y_g - y_cb) * H_seis
        M_Hw = y_cb * fx.h_water - fx.m_water_ref0
        known = M_L + M_W + M_H + M_Hw
        # v0.1.221 (D212) -- the reinforcement's moment about this same
        # point, published by the method (its tangential part acts along the
        # chord, so only the normal part and the couples have one).
        if sup_m:
            known += sup_m
        if abs(E_R) > 1e-9:
            y_tR = y_cb + ((x_R - x_cb) * st.X[i + 1] + known) / E_R
        else:
            # Undefined application point when E≈0 → conventional h/3.
            y_tR = s.base_y_right + (s.top_y_right - s.base_y_right) / 3.0
        st.y_thrust[i + 1] = y_tR

    st.closure = abs(st.E[n])
    st.e_max = max((abs(e) for e in st.E), default=0.0)
    st.ok = True
    return st


# ----------------------------------------------------------------------
def compute_interslice_state(result: LEMResult,
                             kh: float | None = None,
                             kv: float | None = None) -> InterSliceState:
    """Interslice forces E/X, base N/S and line of thrust for a
    converged LEM result.

    Uses ``result.details["boundary_ratios"]`` when the method provides
    them, zeros otherwise. Both sign conventions of the ratios are tried
    (some methods solve λ in a flipped frame); the march with the
    smaller closure |E_n| wins.

    ``kh``/``kv`` default to the coefficients the method APPLIED,
    ``details["kh"]`` and ``details["kv"]`` (v0.1.214, D173): the loads of
    the march must be the solver's, and a caller that has no project to
    read them from is exactly the one that marched without them.
    """
    st = InterSliceState()
    if (result is None or not result.slices or result.fos is None
            or not math.isfinite(result.fos)):
        return st
    details = result.details or {}
    if kh is None:
        kh = float(details.get("kh", 0.0) or 0.0)
    if kv is None:
        kv = float(details.get("kv", 0.0) or 0.0)
    slist = list(result.slices)
    n = len(slist)
    ratios = result.details.get("boundary_ratios") if result.details else None
    if not ratios or len(ratios) != n + 1:
        ratios = [0.0] * (n + 1)
    env = result.details.get("envelope_stress") if result.details else None
    if env is not None and len(env) != n:
        env = None
    sense = details.get("slide_sign")
    if sense not in (1.0, -1.0):
        sense = None
    # v0.1.220 (D211) -- the F the method's state was solved at, which is
    # the reported one for every method but Janbu Corrected.
    F = equilibrium_fos(result)
    # v0.1.221 (D212) -- the reinforcement the method applied, as it
    # published it; the load its stress estimate carried only goes with the
    # force, so a result with one and not the other marches as before.
    sup_f = sup_m = sup_l = None
    if SUPPORT_IN_MARCH:
        sup_f = _per_slice_list(details, "support_force", n)
        if sup_f is not None:
            sup_m = _per_slice_list(details, "support_moment", n)
            sup_l = _per_slice_list(details, "sigma_support_load", n)
    kw = dict(envelope_stress=env, slide_sign=sense, support_force=sup_f,
              support_moment=sup_m, support_load=sup_l)

    st_pos = _march(slist, ratios, F, kh, kv, **kw)
    if all(abs(r) < 1e-12 for r in ratios):
        return st_pos
    st_neg = _march(slist, [-r for r in ratios], F, kh, kv, **kw)
    if not st_pos.ok:
        best, sgn = st_neg, -1.0
    elif not st_neg.ok:
        best, sgn = st_pos, 1.0
    elif st_pos.closure <= st_neg.closure:
        best, sgn = st_pos, 1.0
    else:
        best, sgn = st_neg, -1.0

    # ---- scalar refinement of the ratio magnitude ---------------------
    # The method's λ comes from its own inner discretisation; at OUR
    # slice march the exact multiplier k that closes E_n = 0 can differ
    # slightly. Keeping F fixed (the method's answer), find k by secant
    # so the displayed interslice state is self-equilibrated. This is a
    # display-consistency refinement; it never alters the FoS.
    def closure_signed(k: float) -> float:
        stk = _march(slist, [sgn * k * r for r in ratios], F, kh, kv, **kw)
        return stk.E[n] if stk.ok else math.nan

    k_lo, k_hi = 0.0, 2.0
    f_lo, f_hi = closure_signed(k_lo), closure_signed(k_hi)
    if (math.isfinite(f_lo) and math.isfinite(f_hi)
            and f_lo * f_hi < 0):
        for _ in range(40):
            k_mid = (k_hi if abs(f_hi - f_lo) < 1e-15
                     else k_hi - f_hi * (k_hi - k_lo) / (f_hi - f_lo))
            if not (min(k_lo, k_hi) <= k_mid <= max(k_lo, k_hi)):
                k_mid = 0.5 * (k_lo + k_hi)
            f_mid = closure_signed(k_mid)
            if not math.isfinite(f_mid):
                break
            if abs(f_mid) < 1e-6:
                k_lo = k_mid
                break
            if f_lo * f_mid < 0:
                k_hi, f_hi = k_mid, f_mid
            else:
                k_lo, f_lo = k_mid, f_mid
        st_ref = _march(slist, [sgn * k_lo * r for r in ratios],
                        F, kh, kv, **kw)
        if st_ref.ok and st_ref.closure < best.closure:
            return st_ref
    return best
