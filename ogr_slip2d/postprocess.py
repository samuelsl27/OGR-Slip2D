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
      H  the horizontal seismic pseudo-force (in the sliding direction),
      W_eff = W·(1 − kv).

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
def _march(slist, ratios, F, kh, kv) -> InterSliceState:
    """Single left→right equilibrium march with the given boundary
    ratios. Returns the full state (E, X, N, S, thrust line)."""
    n = len(slist)
    st = InterSliceState()
    st.E = [0.0] * (n + 1)
    st.X = [0.0] * (n + 1)
    st.N = [0.0] * n
    st.S = [0.0] * n
    st.y_thrust = [0.0] * (n + 1)

    # Resisting direction: opposes the along-base gravity drive.
    drive = sum(-s.weight * math.sin(s.base_angle) for s in slist)
    s_dir = -1.0 if drive > 0 else 1.0
    # Horizontal pseudo-force acts in the movement direction (−s_dir·t̄,
    # whose horizontal sign is −s_dir since cos α > 0).
    h_dir = -s_dir

    # Thrust starts at the base end (E=0 there).
    st.y_thrust[0] = slist[0].base_y_left

    for i, s in enumerate(slist):
        alpha = s.base_angle
        l = s.base_length
        u = s.pore_pressure
        W_eff = s.weight * (1.0 - kv)
        H = h_dir * kh * W_eff

        sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
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
        M_W = -(x_g - x_cb) * W_eff
        M_H = -(y_g - y_cb) * H
        known = M_L + M_W + M_H
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
                             kh: float = 0.0,
                             kv: float = 0.0) -> InterSliceState:
    """Interslice forces E/X, base N/S and line of thrust for a
    converged LEM result.

    Uses ``result.details["boundary_ratios"]`` when the method provides
    them, zeros otherwise. Both sign conventions of the ratios are tried
    (some methods solve λ in a flipped frame); the march with the
    smaller closure |E_n| wins.
    """
    st = InterSliceState()
    if result is None or not result.slices or not math.isfinite(result.fos):
        return st
    slist = list(result.slices)
    n = len(slist)
    ratios = result.details.get("boundary_ratios") if result.details else None
    if not ratios or len(ratios) != n + 1:
        ratios = [0.0] * (n + 1)

    st_pos = _march(slist, ratios, result.fos, kh, kv)
    if all(abs(r) < 1e-12 for r in ratios):
        return st_pos
    st_neg = _march(slist, [-r for r in ratios], result.fos, kh, kv)
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
        stk = _march(slist, [sgn * k * r for r in ratios], result.fos, kh, kv)
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
                        result.fos, kh, kv)
        if st_ref.ok and st_ref.closure < best.closure:
            return st_ref
    return best
