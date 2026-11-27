# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.499 (D437) — with Newmark and upslope sliding allowed, the critical
surface a run publishes is the one with the largest net displacement, not
the one with the lowest Ky.

The search minimises Ky in both Newmark modes, and that is right for a
block that slides one way: its displacement never grows with its critical
acceleration (Newmark 1965), so the lowest Ky IS the largest displacement.
With upslope sliding the integrator returns a NET displacement, downslope
less upslope, and that premise fails. Measured with 0.1.485 and 0.1.496 on
the demo slope with c = 12 kPa, a 5×5×6 grid, Bishop and a 0.3 g, 2 Hz
sinusoid for 4 s plus 2 s of calm: the critical surface (Ky 0.1137) moved
0.236 cm while 4 of 152 moved more, the most 1.269 cm at Ky 0.1543 (the
bench's ``medir_d437.py``). The reference highlights the surface of the
largest displacement.

The owner's decision (option a): the search still steers on Ky, so its
population does not change, and the run chooses afterwards, among the
valid surfaces with a displacement (``SearchResult.net_newmark``,
``newmark_net_key``).

The invariants:

* the premise, measured and written down: on this grid (5×5×4, which keeps
  the separation: 0.050 cm at the lowest Ky against 1.081 cm), with upslope
  sliding some valid surface moves more than the one of the lowest Ky;
* an identity: the published critical surface is the maximum of
  ``details["newmark_displacement"]`` over the valid surfaces, and it is
  ``top_n(1)[0]`` (D361);
* rule 7: ``allow_upslope`` changes the surface published;
* without upslope sliding nothing moves: the critical surface is the lowest
  Ky by the old key (``criticality_key``), and the flag stays down;
* a run with upslope sliding and no usable record keeps the lowest Ky;
* the flag survives the pickle that carries an agent's job back.

Cost: three runs of a 5×5×4 grid (103 valid circles), about 0.45 s each:
the separation does not appear on any grid below 5×5×4 that was tried
(2×2×2 to 4×4×3 have the largest displacement at the lowest Ky).
"""
from __future__ import annotations

import math
import pickle

_METHOD = "bishop_simplified"
_DT = 0.005
_RUNS: dict = {}


def _project(upslope, record=True):
    from examples.quick_slope import build_demo_slope
    from ogr_core.loads.seismic_record import SeismicRecord
    p = build_demo_slope()
    p.materials[0].strength.params["cohesion"] = 12.0
    s = p.settings.search
    s.grid_nx, s.grid_ny, s.radius_increment = 5, 5, 4
    p.settings.methods.enabled_methods = [_METHOD]
    accel = ([0.3 * math.sin(2 * math.pi * 2 * i * _DT)
              for i in range(int(4 / _DT))] + [0.0] * int(2 / _DT))
    rec = SeismicRecord(name="sinusoid", dt=_DT, accelerations=accel)
    p.seismic_records = [rec]
    cfg = p.settings.seismic
    cfg.newmark, cfg.polarity = True, "maximum"
    cfg.record_id = rec.id if record else ""
    cfg.allow_upslope = upslope
    return p


def _result(case):
    """``"upslope"``, ``"oneway"`` or ``"upslope_no_record"``, once."""
    if case not in _RUNS:
        from ogr_slip2d.analysis_runner import run_analysis
        p = {"upslope": lambda: _project(True),
             "oneway": lambda: _project(False),
             "upslope_no_record": lambda: _project(True, record=False)}[case]()
        _RUNS[case] = run_analysis(p).results[_METHOD]
    return _RUNS[case]


def _moved(r):
    return r.details["newmark_displacement"]


def _with_displacement(res):
    return [r for r in res.valid()
            if "newmark_displacement" in (r.details or {})]


def _lowest_ky(res):
    from ogr_slip2d.search import criticality_key
    return min(res.valid(), key=lambda r: criticality_key(r, res.score))


class TestThePremise:

    def test_with_upslope_a_higher_ky_moves_more(self):
        res = _result("upslope")
        low = _lowest_ky(res)
        more = [r for r in _with_displacement(res) if _moved(r) > _moved(low)]
        assert more, "the grid no longer separates the two"
        assert max(r.details["ky"] for r in more) > low.details["ky"]


class TestTheCriticalMovesTheMost:

    def test_it_is_the_largest_displacement(self):
        res = _result("upslope")
        assert res.net_newmark
        crit = res.critical
        assert _moved(crit) == max(_moved(r) for r in _with_displacement(res))

    def test_it_is_the_first_of_top_n(self):
        res = _result("upslope")
        assert res.top_n(1)[0] is res.critical

    def test_the_upslope_setting_moves_the_critical_surface(self):
        """Rule 7."""
        up, one = _result("upslope").critical, _result("oneway").critical
        assert (up.surface.to_dict() != one.surface.to_dict()
                or up.details["ky"] != one.details["ky"])
        assert _moved(up) > _moved(_lowest_ky(_result("upslope")))


class TestWithoutUpslopeNothingMoves:

    def test_the_critical_is_the_lowest_ky(self):
        res = _result("oneway")
        assert not res.net_newmark
        assert res.critical is _lowest_ky(res)

    def test_and_it_moves_the_most_anyway(self):
        """Newmark (1965) for a one-way block: the lowest Ky is the largest
        displacement, which is why the search could minimise Ky."""
        res = _result("oneway")
        assert _moved(res.critical) == max(
            _moved(r) for r in _with_displacement(res))

    def test_without_a_record_the_lowest_ky_is_kept(self):
        res = _result("upslope_no_record")
        assert not res.net_newmark
        assert res.critical is _lowest_ky(res)


class TestTheFlagTravels:

    def test_it_survives_a_pickle(self):
        res = _result("upslope")
        back = pickle.loads(pickle.dumps(res))
        assert back.net_newmark
        assert _moved(back.critical) == _moved(res.critical)
