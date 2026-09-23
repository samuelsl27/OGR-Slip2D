# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.190 — under ``phi = 0`` the m-alpha check is a base-angle ceiling on
BOTH branches, but what it screens by CANCELS on the circular one and
does not on the general one. This file measures what does not cancel.

THE INVARIANT. Defect D61 says that under ``phi = 0`` the check "stops
being a statement about the method". Half of that is exact:

    tan phi = 0, u = 0  =>  q = c*b / m_alpha = c*b / cos a = c*l

exactly, because on a straight chord ``l`` IS ``b / cos a``. So the
resisting term sheds the cosine and, on the circular Bishop branch, the
criterion filters by a quantity that never reaches the answer.

The other half is wrong, and it is wrong on the branch D61 is about. In
``methods/bishop.py::_general_moment_fos`` the normal force KEEPS the
cosine that ``q`` shed — ``normal = (w_n - (q/F) sin a) / cos a`` — and
``normals`` enters ``moment_balance.moment_terms`` with an arm of its
own, on the DENOMINATOR side: ``driving = weight + normal + external``
and ``F = -shear / driving`` (Fredlund & Krahn, 1977). That is D114.

THIS FILE FIXES A MEASUREMENT, NOT A CHANGE, and says so rather than
letting it look like one. No engine arithmetic moved in v0.1.190.
Measured against the v0.1.189 tree by copying this file into a
``git worktree`` at that commit: **1 of 17 cases fails there**, and it is
``test_m_alpha_check_names_the_general_branch``, which fails on the
ABSENCE OF A SYMBOL. That is weak discrimination and it is labelled as
such. The weight of the closure is carried by ``d114()`` in the
verification bank, which requires the number in that docstring to AGREE
with the number in the archived measurement — a literal alone proves
nothing; a literal that has to match a measurement is evidence.

THE ANCHORS ARE IDENTITIES, NOT SNAPSHOTS.

* ``q == c*l`` under ``phi = 0`` — algebra, to 1e-12;
* ``m_alpha == cos a`` under ``phi = 0`` — algebra, exactly;
* on a circle with the axis at the centre, ``terms.normal`` vanishes for
  ARBITRARY normals, because ``base_frame`` returns the midpoint of the
  chord and its perpendicular, and that line is the chord's perpendicular
  bisector: it passes through the centre. Geometry, independent of any
  solver;
* the decomposition is exact: the per-slice moments sum to
  ``terms.normal``, and the three parts sum to ``driving``;
* and the sweep is asserted by ORDER, not by value.

ONE THING THE SWEEP FOUND that is not part of D114 and is reported
rather than measured around: past 76 deg the general recursion has no
usable fixed point. See ``TestPastTheCeilingTheRecursionStopsMeaning``.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

#: The share of the driving moment carried by the normal term, at the two
#: ends of the usable sweep. From
#: ``_auditoria/D110_D114_D61_techos/medida_0.1.189.json`` in the
#: verification bank; reproduced here by measurement, never asserted
#: against these two numbers — they are in the docstrings so the file can
#: be read without the bank.
SHARE_AT_40 = +0.180
SHARE_AT_76 = -1.316


def _slope(phi: float = 0.0):
    from test_block_population_v1135 import _cohesive_slope
    return _cohesive_slope(phi)


def _scarp(beta_deg: float, drop: float = 36.0):
    """A polyline whose back scarp falls at ``beta_deg``.

    The two ENDS are fixed for every beta on purpose: ``moment_axis``
    builds the axis from the chord between entry and exit, so leaving
    them still makes the axis the same point across the whole sweep BY
    CONSTRUCTION rather than by a setting chosen here. The test below
    checks that it really is.
    """
    dx = drop / math.tan(math.radians(beta_deg))
    return [(20.0, 30.0), (20.0 + dx, 30.0 - drop),
            (35.0 + dx, 28.0 - drop), (100.0, 10.0)]


def _evaluate(project, points):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import BlockSearch
    from ogr_slip2d.surface import SlipSurface

    s = BlockSearch(method=BishopSimplified(), num_slices=30)
    poly = Polyline(vertices=[Vertex(x, y) for x, y in points], closed=False)
    surf = SlipSurface(polyline=poly)
    return s.evaluate_surface(project, surf), surf


def _pass(project, surface, res):
    """One pass of ``_general_moment_fos`` redone at the converged F.

    ``q`` and ``normal`` are the two lines under test, so they are copied
    from the engine rather than rewritten from memory: rewriting them
    would measure a different thing and call it the same. ``m_alpha`` IS
    rewritten from its definition, because that identity is what the
    first two cases check.
    """
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.moment_balance import axis_for, base_frame, moment_terms

    fos = float(res.fos)
    sgn = float((res.details or {}).get("slide_sign", 1.0))
    s_list = list(res.slices)
    axis = axis_for(project, surface)
    weights, resisting, normals, forces, m_alphas, alphas, cl = (
        [], [], [], [], [], [], [])
    for s in s_list:
        f = slice_forces(s, 0.0, 0.0)
        w = f.w_total
        alpha = sgn * s.base_angle
        n_est = w * math.cos(s.base_angle)
        sigma = max(0.0, n_est - s.pore_pressure * s.base_length)
        sigma /= max(s.base_length, 1e-9)
        c, tan_phi = BishopSimplified._local_c_phi(None, s.material, sigma)
        m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / fos
        q = (c * s.width
             + (w - s.pore_pressure * s.width) * tan_phi) / m_alpha
        normal = ((w - (q / fos) * math.sin(alpha))
                  / max(math.cos(alpha), 1e-9))
        weights.append(w)
        resisting.append(q)
        normals.append(normal)
        forces.append(f)
        m_alphas.append(m_alpha)
        alphas.append(alpha)
        cl.append(c * s.base_length)

    terms = moment_terms(axis, s_list, weights, resisting, normals,
                         forces=forces)
    ox, oy = axis
    per = []
    for i, s in enumerate(s_list):
        xm, ym, _tx, _ty, nx, ny = base_frame(axis, s)
        per.append((xm - ox) * normals[i] * ny - (ym - oy) * normals[i] * nx)
    return {"terms": terms, "per": per, "q": resisting, "cl": cl,
            "m_alpha": m_alphas, "alpha": alphas, "axis": axis,
            "fos": fos, "slices": s_list}


def _is_cohesive(material) -> bool:
    """Whether the envelope has no friction, ASKED rather than listed."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    _c0, t0 = BishopSimplified._local_c_phi(None, material, 0.0)
    _c1, t1 = BishopSimplified._local_c_phi(None, material, 500.0)
    return abs(t0) < 1e-12 and abs(t1) < 1e-12


def _row(beta: float):
    p = _slope(0.0)
    res, surf = _evaluate(p, _scarp(beta))
    assert res is not None and res.fos is not None, beta
    return _pass(p, surf, res)


def _usable(row) -> bool:
    """Whether redoing the pass at the published F reproduces it.

    The method's stopping rule is an ABSOLUTE step (``tolerance`` 1e-3),
    so a small enough factor is declared converged with a huge RELATIVE
    step. A row past that is not a measurement and is not used as one.
    """
    t = row["terms"]
    return abs(-t.shear / t.driving - row["fos"]) / abs(row["fos"]) < 1e-2


# ======================================================================
class TestTheResistingSideCancelsUnderNoFriction:
    """The half of D61 that is exact. Passes on v0.1.189 too: it is the
    premise this file starts from, not something it changes."""

    def test_q_is_the_cohesion_times_the_base_length(self):
        """``q = c*b/cos a = c*l`` exactly — the cancellation itself.

        Checked on the geometry, at the converged F, and not argued from
        the source: ``l`` is the slicer's own ``base_length``, so this
        also pins that the base is a straight chord.
        """
        row = _row(70.0)
        for q, cl in zip(row["q"], row["cl"]):
            assert abs(q - cl) <= 1e-12 * max(1.0, abs(cl)), (q, cl)

    def test_and_m_alpha_is_the_cosine_exactly(self):
        row = _row(70.0)
        for m, a in zip(row["m_alpha"], row["alpha"]):
            assert m == math.cos(a), (m, math.cos(a))


# ======================================================================
class TestOnACircleThatTermIsZeroByConstruction:
    """The contrast, and it is an ANALYTIC anchor rather than a small
    number: the moment of the base normal about the centre of a circle
    vanishes for any normals at all, because the line it acts along is
    the perpendicular bisector of the chord."""

    def _circle_residual(self, cx, cy, r, n):
        import random

        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.moment_balance import moment_terms
        from ogr_slip2d.search import BlockSearch
        from ogr_slip2d.surface import SlipCircle

        s = BlockSearch(method=BishopSimplified(), num_slices=n)
        res = s.evaluate_surface(_slope(0.0),
                                 SlipCircle(centre_x=cx, centre_y=cy,
                                            radius=r))
        assert res is not None and res.slices
        s_list = list(res.slices)
        rnd = random.Random(20260922)
        normals = [rnd.uniform(-900.0, 900.0) for _ in s_list]
        terms = moment_terms((cx, cy), s_list, [sl.weight for sl in s_list],
                             [0.0] * len(s_list), normals)
        scale = math.fsum(abs(v) for v in normals) * r
        return abs(terms.normal) / scale

    def test_the_normal_moment_vanishes_for_arbitrary_normals(self):
        """The normals are RANDOM on purpose: if this depended on the
        values the solver happens to produce it would be a coincidence,
        and it is a theorem."""
        assert self._circle_residual(60.0, 60.0, 55.0, 20) < 1e-12

    def test_and_it_is_not_one_lucky_geometry(self):
        for (cx, cy, r) in ((60.0, 60.0, 55.0), (55.0, 70.0, 68.0)):
            for n in (20, 40):
                got = self._circle_residual(cx, cy, r, n)
                assert got < 1e-12, (cx, cy, r, n, got)


# ======================================================================
class TestTheNormalSideDoesNot:
    """The general branch, where the cosine survives into the answer."""

    def test_the_decomposition_is_complete(self):
        """Before any share is quoted, the parts have to add up — a
        fraction of a total that is not the total measures nothing."""
        row = _row(70.0)
        t = row["terms"]
        assert abs(math.fsum(row["per"]) - t.normal) < 1e-6 * max(
            1.0, abs(t.normal))
        assert abs((t.weight + t.normal + t.external) - t.driving) < 1e-9

    def test_the_normal_term_is_a_real_part_of_the_driving_moment(self):
        """Not a rounding correction: at 70 deg it is already tens of per
        cent of the denominator, and the factor is ``-shear/driving``."""
        row = _row(70.0)
        t = row["terms"]
        assert _usable(row)
        assert abs(t.normal / t.driving) > 0.05, t.normal / t.driving

    def test_and_the_share_grows_with_the_base_angle(self):
        """ORDER, not value — which is what keeps this out of snapshot
        territory. It is the share of the WHOLE normal term and not of
        one slice: measured, a single slice's share is noisy (at 65 deg
        it reads 0.31 between neighbours of 0.02 and 0.06) because which
        slice ends up steepest after slicing, and its arm, both move.
        The whole term does not.
        """
        rows = [(b, _row(b)) for b in (40, 45, 50, 55, 60, 65, 70, 72,
                                       74, 75, 76)]
        rows = [(b, r) for b, r in rows if _usable(r)]
        assert len(rows) >= 8, len(rows)
        shares = [r["terms"].normal / r["terms"].driving for _b, r in rows]
        for a, b in zip(shares, shares[1:]):
            assert a > b, (shares,)
        # From positive to larger in magnitude than the whole driving
        # moment: past 74 deg the term D61 treated as cancelled IS the
        # denominator.
        assert shares[0] > 0.15, shares[0]
        assert shares[-1] < -1.0, shares[-1]

    def test_the_axis_is_the_same_point_across_the_sweep(self):
        """So the sweep moves ONE thing. The ends of the polyline are
        fixed and ``moment_axis`` builds the axis from that chord, so
        this is an identity rather than a setting — and it is checked
        instead of assumed, because if it ever stopped holding the sweep
        would be mixing two effects and still look tidy.
        """
        axes = {tuple(round(v, 9) for v in _row(b)["axis"])
                for b in (40, 55, 70, 76)}
        assert len(axes) == 1, axes

    def test_removing_only_that_contribution_moves_the_factor(self):
        """(b') — the same geometry, with the steep base's normal moment
        taken out of the denominator, which is exactly what a circle does
        by construction. P-D114 asked instead for the steep slice to be
        replaced by two flatter ones of equal weight; that cannot be a
        controlled A/B, because with the ends fixed any such replacement
        changes the enclosed area, hence the weight, and moving the ends
        moves the axis, the arms and the daylight point at once. This
        does none of those.
        """
        row = _row(75.0)
        assert _usable(row)
        t = row["terms"]
        i = max(range(len(row["alpha"])), key=lambda k: abs(row["alpha"][k]))
        without = -t.shear / (t.driving - row["per"][i])
        assert abs(without / row["fos"] - 1.0) > 0.01, (without, row["fos"])


# ======================================================================
class TestThePublishedCaseIsTheModestEnd:
    """The honest half of the measurement: on the one published
    non-circular ``phi = 0`` surface this project holds, the share is
    small — because its steepest cohesive base is 43.7 deg and nowhere
    near the ceiling. A measurement that only showed the dramatic end
    would be an argument, not a measurement."""

    def _james_bay(self):
        from ogr_core.project import Project
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import Slices
        from test_james_bay_v1158 import (JB_F729, _positioned_slices,
                                          _slip_surface)
        p = Project()
        surf = _slip_surface()
        res = BishopSimplified().compute_fos(
            p, surf, Slices(_positioned_slices(JB_F729)))
        assert res is not None and res.fos is not None
        return p, surf, res

    def test_the_published_surface_sits_far_below_the_ceiling(self):
        """Its steepest COHESIVE base, which is the one D114 is about —
        the 57.2 deg base is the sheet's only frictional slice, and
        quoting that one would answer a different question."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        from test_james_bay_v1158 import JB_F729

        steep = max(abs(a) for (_b, a, _W, _l, _c, phi) in JB_F729
                    if abs(phi) < 1e-12)
        assert abs(steep - 43.7) < 1e-9, steep
        assert steep < math.degrees(math.acos(M_ALPHA_LIMIT)) - 30.0

    def test_and_its_share_is_small_but_not_zero(self):
        """Small, and NOT zero — which is the whole point. On a circle it
        would be zero by construction; here it is a few per cent, on the
        one surface the literature hands over."""
        p, surf, res = self._james_bay()
        row = _pass(p, surf, res)
        # Purely cohesive is INTERROGATED from the envelope, not inferred
        # from ``q == c*l``: the published sheet's ``l`` column is the
        # measured base length, which agrees with ``b/cos a`` to 1 % and
        # not to machine precision, so that test would have called six
        # cohesive slices frictional.
        coh = [i for i, s in enumerate(row["slices"])
               if _is_cohesive(s.material)]
        assert len(coh) == 10, len(coh)
        i = max(coh, key=lambda k: abs(row["alpha"][k]))
        share = row["per"][i] / row["terms"].driving
        assert 0.005 < abs(share) < 0.15, share


# ======================================================================
class TestPastTheCeilingTheRecursionStopsMeaning:
    """Found by the sweep, reported rather than measured around.

    At 77 deg and beyond the general recursion still reports
    ``converged=True`` and a factor, and the factor is not a solution:
    redoing the pass at it moves it by tens of per cent. It is declared
    converged because the stopping rule is an ABSOLUTE step against
    ``tolerance`` (1e-3), and on a factor of 3.7e-3 that is a 27 % step.
    Tightening the tolerance to 1e-8 walks the same surface down to
    2.6e-8, the same with 30, 60 and 120 slices.

    Both halves are reported and neither is fixed here: they are defects
    D168 and D169 of the verification bank. This class pins the symptom
    so a later version cannot quietly change it without saying so.
    """

    def test_the_sweep_has_a_wall_and_it_is_past_the_ceiling(self):
        from ogr_slip2d.checks import M_ALPHA_LIMIT

        good = [b for b in (70, 72, 74, 75, 76) if _usable(_row(float(b)))]
        bad = [b for b in (77, 78) if not _usable(_row(float(b)))]
        assert good == [70, 72, 74, 75, 76], good
        assert bad == [77, 78], bad
        # And the wall is past the m-alpha ceiling, so the check is not
        # what keeps those surfaces out: it admits them.
        assert min(bad) > math.degrees(math.acos(M_ALPHA_LIMIT)) - 2.0

    def test_a_collapsed_factor_is_still_reported_as_converged(self):
        """The symptom of D169, stated as the gap between the absolute
        rule and the relative error it allows."""
        p = _slope(0.0)
        res, _surf = _evaluate(p, _scarp(78.0))
        assert res is not None and res.fos is not None
        assert res.converged is True
        row = _row(78.0)
        rel = abs(-row["terms"].shear / row["terms"].driving
                  - row["fos"]) / abs(row["fos"])
        assert rel > 0.1, rel

    def test_and_the_m_alpha_check_admits_it(self):
        """D168's edge: the surface clears 0.2 — by eight thousandths —
        and the factor it returns is meaningless. The limit screens
        arithmetic that has become untrustworthy; it does not certify
        what survives."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT, base_m_alphas, check_surface

        p = _slope(0.0)
        res, _surf = _evaluate(p, _scarp(78.0))
        worst = min(base_m_alphas(res))
        assert M_ALPHA_LIMIT < worst < M_ALPHA_LIMIT + 0.02, worst
        ok, _why = check_surface(res, tensile=False, m_alpha=True)
        assert ok


# ======================================================================
class TestTheMeasurementIsWrittenWhereTheCheckIs:
    """A measurement nobody can find is a measurement that gets made
    twice. It goes in the docstring of the gate, because that is the
    function a reader opens to ask what the check decides."""

    def test_m_alpha_check_names_the_general_branch(self):
        """FAILS on v0.1.189 — and it fails on the ABSENCE OF A SYMBOL,
        which is weak discrimination. Said here rather than left to look
        stronger than it is. What makes the closure real is ``d114()``
        in the bank, which requires this number to agree with the
        archived measurement."""
        import re

        from ogr_slip2d.checks import m_alpha_check

        # NORMALISE THE WHITESPACE instead of choosing substrings that
        # happen not to straddle a line break. That trap has bitten this
        # project three times (v0.1.180, v0.1.185, v0.1.187), including
        # inside the closure check written to catch it, and "pick short
        # tokens carefully" is the fix that stops working the next time
        # someone reflows a docstring to 79 columns.
        doc = re.sub(r"\s+", " ", m_alpha_check.__doc__ or "")
        for tok in ("general branch", "_general_moment_fos", "78.463",
                    "Fredlund", "%", "zero by construction"):
            assert tok in doc, tok

    def test_and_base_m_alphas_still_carries_its_seven(self):
        """Deliberately duplicated from
        ``test_m_alpha_screening_v1189.py``, and said out loud: this
        closure must not be buyable by moving text from one docstring to
        the other."""
        from ogr_slip2d.checks import base_m_alphas

        doc = base_m_alphas.__doc__ or ""
        for tok in ("n_alpha", "0.7230", "0.5181", "0.6896", "78.463",
                    "63.435", "M_ALPHA_SCREENED"):
            assert tok in doc, tok


# ======================================================================
class TestTheJamesBayNumbersDidNotMove:
    """The published anchor, re-run here because this file leans on that
    surface. If it moved, everything above would be measuring something
    else."""

    def test_spencer_still_finds_the_published_factor(self):
        from test_james_bay_v1158 import JB_F729, _spencer

        res = _spencer(JB_F729)
        assert res is not None and res.fos is not None
        assert abs(res.fos / 1.17 - 1.0) < 0.01, res.fos
