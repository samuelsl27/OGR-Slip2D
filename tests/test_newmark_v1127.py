# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.127 — the Newmark rigid-block integrator, against closed forms.

There is no strong-motion record in this repository and there is not going
to be one, so every anchor here is either a **closed form** or an
**identity**. That is not a compromise: for this calculation the closed
form is stronger evidence than a record would be, because it pins the
answer exactly instead of to the digitisation of some 1979 accelerogram.

The five invariants
-------------------

1.  **Newmark (1965), single rectangular pulse.** A ground acceleration of
    amplitude ``A·g`` held for ``t₀`` over a block whose critical
    acceleration is ``N·g`` displaces it by::

        u = V² / (2 g N) · (1 − N/A),      V = A·g·t₀

    Derived independently and cross-checked against the equivalent
    published form ``u = (a_p T_p²/2)(a_p/μg − 1)``: the two are the same
    expression.

    Measured here: when the stopping instant ``t_m = (A/N)·t₀`` lands on a
    sample, the trapezoidal scheme reproduces the closed form to **machine
    precision**, at every time step tried from 20 ms down to 0.6 ms. That
    was not the expectation — the scheme carries a half-step deficit in
    velocity at the start of the pulse — and it holds because the same
    half-step reappears with the opposite sign when the pulse ends. When
    the stopping instant falls between samples the remainder of the
    velocity triangle is lost, and that residue is ≤ 3.7e-4 relative at
    dt = 20 ms and falls to 4e-8 as the step is refined.

2.  **A block with no resistance is the ground.** With ``a_c = 0`` and
    both directions allowed, the relative displacement IS the ground
    displacement, exactly. This is the one that catches an index slip, a
    unit slip or a lost factor of ``g``, none of which the closed form
    above would notice — it has only one number in it.

3.  **A block stronger than the earthquake does not move.** ``a_c ≥ PGA``
    gives **zero**, not something small. It was 1.7e-16 until the branch
    that Jibson (1993) writes as ``N = A/T`` was written as the zero it
    means: ``(a/t)*t`` is not ``a`` in floating point.

4.  **Similarity.** Scaling record and critical acceleration together by
    ``s`` scales the displacement by ``s``; stretching the time axis by
    ``τ`` scales it by ``τ²``. Both exact, both dimensional analysis, and
    together they say the integrator has no hidden constant in it.

5.  **Monotonicity.** The displacement never increases with ``a_c``. This
    is the one the search design rests on: it is why the surface that
    moves the most is the surface with the lowest Ky, and therefore why
    the Newmark mode can minimise Ky and never integrate a record inside
    the search.

Reference: Newmark, N.M. (1965), Géotechnique 15(2) 139-160; Wilson and
Keefer (1983), BSSA 73(3) 863-877; Jibson (1993), TRR 1411 9-17.
"""
from __future__ import annotations

import math
import random

import pytest

from ogr_core.loads.seismic_record import (
    STANDARD_GRAVITY_CM_S2,
    AccelerationUnit,
    SeismicRecord,
    parse_record_text,
)
from ogr_slip2d.newmark import (
    Polarity,
    displacement_for_record,
    ground_displacement,
    rigid_block_displacement,
)

G = STANDARD_GRAVITY_CM_S2 / 100.0          # m/s²


def _closed_form(amplitude_g: float, critical_g: float,
                 duration_s: float) -> float:
    """Newmark (1965), single rectangular pulse. Metres."""
    v = amplitude_g * G * duration_s
    return v * v / (2.0 * G * critical_g) * (1.0 - critical_g / amplitude_g)


def _pulse(amplitude_g: float, duration_s: float, dt: float,
           tail_s: float) -> list:
    """A rectangular pulse followed by quiet ground."""
    return ([amplitude_g] * int(round(duration_s / dt))
            + [0.0] * int(round(tail_s / dt)))


def _noise(n: int = 4000, peak: float = 0.4, seed: int = 7) -> list:
    rng = random.Random(seed)
    return [rng.uniform(-peak, peak) for _ in range(n)]


# ======================================================================
class TestTheClosedFormOfNewmark:
    """Invariant 1."""

    def test_the_rectangular_pulse_is_exact_when_the_block_stops_on_a_sample(
            self):
        """``t_m = (A/N)·t₀`` a whole number of steps: machine precision.

        A = 0.5 g for 1 s against N = 0.2 g stops at 2.5 s, which every
        step size below is an exact divisor of. Nothing here is fitted:
        the expected value is the published formula.
        """
        amplitude, critical, duration = 0.5, 0.2, 1.0
        expected = _closed_form(amplitude, critical, duration)
        bad = []
        for dt in (0.02, 0.01, 0.005, 0.0025, 0.00125, 0.000625):
            accel = _pulse(amplitude, duration, dt, tail_s=6.0)
            got = rigid_block_displacement(accel, dt, critical)
            err = abs(got - expected) / expected
            if err > 1e-12:
                bad.append(f"dt={dt}: {got:.10f} vs {expected:.10f} "
                           f"= {err:.2e}")
        assert not bad, bad

    def test_it_holds_across_amplitudes_and_critical_accelerations(self):
        """Twenty combinations, one tolerance, no fitting.

        The tail has to be long enough for the block to STOP: it slides
        until ``t_m = (A/N)·t₀``, which for A/N = 60 is forty seconds. A
        tail chosen without that arithmetic truncates the answer and looks
        like an integrator bug — it did, at 26 %, while this test was
        being written.
        """
        dt, duration = 0.005, 0.7
        bad = []
        for amplitude in (0.2, 0.35, 0.5, 0.8, 1.2):
            for critical in (0.02, 0.05, 0.1):
                if critical >= amplitude:
                    continue
                stop = (amplitude / critical) * duration
                accel = _pulse(amplitude, duration, dt,
                               tail_s=1.5 * stop + 1.0)
                got = rigid_block_displacement(accel, dt, critical)
                expected = _closed_form(amplitude, critical, duration)
                err = abs(got - expected) / expected
                if err > 1e-10:
                    bad.append(f"A={amplitude} N={critical}: {err:.2e}")
        assert not bad, bad

    def test_the_off_grid_residue_is_small_and_shrinks(self):
        """When the block stops between samples, the tail of the velocity
        triangle is lost. It is bounded, and refining the step reduces it.

        Not a convergence ORDER: where the stopping instant falls relative
        to the sampling is what sets the residue, so it does not fall
        smoothly. What is asserted is what is true — it is small, and the
        finest step is far better than the coarsest.
        """
        amplitude, critical, duration = 0.2, 0.19, 0.7
        errs = []
        for dt in (0.02, 0.005, 0.000625):
            n = int(round(duration / dt))
            accel = [amplitude] * n + [0.0] * int(round(3.0 / dt))
            expected = _closed_form(amplitude, critical, n * dt)
            errs.append(abs(rigid_block_displacement(accel, dt, critical)
                            - expected) / expected)
        assert errs[0] < 1e-3, errs
        assert errs[-1] < errs[0] / 100.0, errs


# ======================================================================
class TestABlockWithNoResistanceIsTheGround:
    """Invariant 2."""

    def test_zero_critical_acceleration_reproduces_the_ground(self):
        accel = _noise()
        block = rigid_block_displacement(accel, 0.005, 0.0,
                                         allow_upslope=True)
        ground = ground_displacement(accel, 0.005)
        assert block == ground

    def test_and_it_is_not_trivially_zero(self):
        """The identity would also hold if both were zero."""
        assert abs(ground_displacement(_noise(), 0.005)) > 1.0


# ======================================================================
class TestABlockStrongerThanTheEarthquakeDoesNotMove:
    """Invariant 3 — exactly zero, in both senses."""

    def test_at_and_above_the_peak(self):
        accel = _noise()
        pga = max(abs(a) for a in accel)
        for critical in (pga, 1.5 * pga, 10.0 * pga):
            for upslope in (False, True):
                got = rigid_block_displacement(accel, 0.005, critical,
                                               allow_upslope=upslope)
                assert got == 0.0, (critical, upslope, got)

    def test_just_below_the_peak_it_does_move(self):
        """Otherwise the test above would pass on a function returning 0."""
        accel = _noise()
        pga = max(abs(a) for a in accel)
        assert rigid_block_displacement(accel, 0.005, 0.98 * pga) > 0.0


# ======================================================================
class TestSimilarity:
    """Invariant 4."""

    ACCEL = _noise()
    DT = 0.005
    CRITICAL = 0.15

    def test_scaling_the_record_and_the_critical_acceleration(self):
        base = rigid_block_displacement(self.ACCEL, self.DT, self.CRITICAL)
        bad = []
        for s in (0.5, 2.0, 3.7):
            got = rigid_block_displacement([a * s for a in self.ACCEL],
                                           self.DT, self.CRITICAL * s)
            if got / s != pytest.approx(base, rel=1e-12):
                bad.append(f"s={s}: {got / s} vs {base}")
        assert not bad, bad

    def test_stretching_the_time_axis(self):
        base = rigid_block_displacement(self.ACCEL, self.DT, self.CRITICAL)
        bad = []
        for tau in (0.5, 2.0, 3.0):
            got = rigid_block_displacement(self.ACCEL, self.DT * tau,
                                           self.CRITICAL)
            if got / (tau * tau) != pytest.approx(base, rel=1e-12):
                bad.append(f"tau={tau}: {got / tau ** 2} vs {base}")
        assert not bad, bad


# ======================================================================
class TestMonotonicity:
    """Invariant 5 — and it is the search design, not a curiosity."""

    def test_the_displacement_never_grows_with_the_critical_acceleration(
            self):
        accel = _noise()
        pga = max(abs(a) for a in accel)
        previous = math.inf
        bad = []
        for k in range(41):
            critical = pga * k / 40.0
            got = rigid_block_displacement(accel, 0.005, critical)
            if got > previous:
                bad.append(f"a_c={critical:.4f}: {got} > {previous}")
            previous = got
        assert not bad, bad

    def test_and_it_is_strictly_decreasing_over_the_useful_range(self):
        """A constant function would satisfy the test above."""
        accel = _noise()
        pga = max(abs(a) for a in accel)
        low = rigid_block_displacement(accel, 0.005, 0.1 * pga)
        high = rigid_block_displacement(accel, 0.005, 0.6 * pga)
        assert low > high > 0.0


# ======================================================================
class TestEverySettingMovesTheNumber:
    """Rule 7, for the four controls this feature adds to the dialog."""

    ACCEL = _noise()
    DT = 0.005

    def _record(self):
        return SeismicRecord(name="synthetic", dt=self.DT,
                             accelerations=list(self.ACCEL))

    def test_the_four_polarities_are_four_answers(self):
        rec = self._record()
        got = {}
        for polarity in Polarity:
            out = displacement_for_record(rec, 0.15, polarity=polarity)
            assert out is not None
            got[polarity] = out.displacement
        # Direct and inverse differ on any record that is not symmetric,
        # and the average and the maximum are then two more numbers.
        assert got[Polarity.DIRECT] != got[Polarity.INVERSE]
        assert got[Polarity.MAXIMUM] == max(got[Polarity.DIRECT],
                                            got[Polarity.INVERSE])
        assert got[Polarity.AVERAGE] == pytest.approx(
            0.5 * (got[Polarity.DIRECT] + got[Polarity.INVERSE]))
        assert got[Polarity.AVERAGE] != got[Polarity.MAXIMUM]

    def test_allowing_upslope_movement_changes_the_answer(self):
        down = rigid_block_displacement(self.ACCEL, self.DT, 0.15)
        both = rigid_block_displacement(self.ACCEL, self.DT, 0.15,
                                        allow_upslope=True)
        assert down != both

    def test_the_scale_factor_changes_the_answer(self):
        rec = self._record()
        plain = displacement_for_record(rec, 0.15, scale=1.0)
        louder = displacement_for_record(rec, 0.15, scale=1.5)
        assert louder.displacement > plain.displacement

    def test_the_record_is_not_modified_by_being_scaled(self):
        """A calculation may not change the user's model."""
        rec = self._record()
        before = list(rec.accelerations)
        displacement_for_record(rec, 0.15, scale=2.0)
        assert rec.accelerations == before


# ======================================================================
class TestItSaysWhenItCannotAnswer:
    """A record that cannot be integrated is not a displacement of zero."""

    def test_no_record(self):
        assert displacement_for_record(None, 0.1) is None

    def test_one_sample(self):
        rec = SeismicRecord(name="x", dt=0.01, accelerations=[0.3])
        assert not rec.is_usable()
        assert displacement_for_record(rec, 0.1) is None

    def test_non_positive_interval(self):
        rec = SeismicRecord(name="x", dt=0.0, accelerations=[0.1, 0.2])
        assert not rec.is_usable()
        assert displacement_for_record(rec, 0.1) is None

    def test_a_usable_record_does_answer(self):
        rec = SeismicRecord(name="x", dt=0.005,
                            accelerations=_noise(n=200))
        assert rec.is_usable()
        assert displacement_for_record(rec, 0.05) is not None


# ======================================================================
class TestTheRecordItself:
    """The data type, its units and its round trip."""

    def test_the_duration_spans_the_intervals_not_the_samples(self):
        rec = SeismicRecord(name="x", dt=0.01,
                            accelerations=[0.1, 0.2, 0.3])
        assert rec.duration == pytest.approx(0.02)

    def test_peak_ground_acceleration_is_an_absolute_value(self):
        rec = SeismicRecord(name="x", dt=0.01,
                            accelerations=[0.1, -0.7, 0.3])
        assert rec.pga == pytest.approx(0.7)

    def test_the_round_trip_is_exact(self):
        rec = SeismicRecord(name="Synthetic", dt=0.005,
                            accelerations=_noise(n=50),
                            source_unit=AccelerationUnit.CM_S2,
                            source_file="somewhere.txt")
        back = SeismicRecord.from_dict(rec.to_dict())
        assert back.to_dict() == rec.to_dict()
        assert back.id == rec.id
        assert back.accelerations == rec.accelerations

    def test_a_record_survives_the_project_file(self):
        """The whole point of storing the samples inside the .ogr."""
        import json

        from ogr_core.project import Project

        project = Project("seismic")
        project.seismic_records.append(
            SeismicRecord(name="Synthetic", dt=0.005,
                          accelerations=_noise(n=64)))
        data = json.loads(json.dumps(project.to_dict()))
        back = Project.from_dict(data)
        assert len(back.seismic_records) == 1
        assert (back.seismic_records[0].accelerations
                == project.seismic_records[0].accelerations)
        assert back.seismic_record_by_id(
            project.seismic_records[0].id) is not None

    def test_the_two_layouts_give_the_same_record(self):
        """Jibson (1993) names both, and a file is one or the other."""
        pairs = "header line\n0.0 10\n0.01 -20\n0.02 30\n"
        single = "10\n-20\n30\n"
        a, dt_a, note_a = parse_record_text(pairs, AccelerationUnit.CM_S2)
        b, dt_b, note_b = parse_record_text(single, AccelerationUnit.CM_S2,
                                            dt=0.01)
        assert note_a == "" and note_b == ""
        assert dt_a == pytest.approx(dt_b)
        # Element by element: this project's test runner supplies its own
        # ``approx``, and it compares numbers, not sequences.
        assert len(a) == len(b)
        for x, y in zip(a, b):
            assert x == pytest.approx(y)
        # And the unit conversion is the standard gravity, not 9.81.
        assert a[0] == pytest.approx(10.0 / STANDARD_GRAVITY_CM_S2)

    def test_an_uneven_time_column_is_reported_not_resampled(self):
        accel, _dt, note = parse_record_text(
            "0 1\n0.01 2\n0.05 3\n", AccelerationUnit.G)
        assert accel == [1.0, 2.0, 3.0]
        assert "not constant" in note

    def test_a_single_column_without_an_interval_is_refused(self):
        accel, _dt, note = parse_record_text("1\n2\n3\n",
                                             AccelerationUnit.G)
        assert accel == []
        assert "time interval" in note
