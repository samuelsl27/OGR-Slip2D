# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Earthquake acceleration-time histories.

A :class:`SeismicRecord` is a strong-motion record: a horizontal ground
acceleration sampled at a constant interval. It is the input a Newmark
analysis needs, and the one kind of data this program had no way of
holding — ``SeismicLoad`` stores a single pseudo-static coefficient, and a
coefficient is a summary of a record, not a record.

Two decisions, both deliberate:

* **The samples live INSIDE the project file.** A record kept as a path to
  a file somewhere else is the trap this program already paid for once
  with finite-element seepage fields, which were not serialised until
  v0.1.78 and were silently analysed as ``u = 0`` when they were missing.
  A record of 5000 samples costs of the order of 60 kB of JSON; a wrong
  displacement costs more.
* **Inside, accelerations are ALWAYS in g.** The unit the user typed is
  converted on the way in and remembered only so the interface can show
  it back. One unit inside means the critical acceleration and the record
  are comparable at the point of use, which is where a forgotten factor
  of 981 would hide.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

__all__ = [
    "AccelerationUnit",
    "SeismicRecord",
    "STANDARD_GRAVITY_CM_S2",
    "parse_record_text",
]

# Standard gravity, in cm/s². Written out rather than derived from 9.81
# because the published algorithm this program follows converts a critical
# acceleration given in g with exactly this factor — see
# ``ogr_slip2d.newmark``, which cites Jibson (1993).
STANDARD_GRAVITY_CM_S2 = 980.665


class AccelerationUnit(Enum):
    """How the numbers in an imported file are to be read."""

    G = "g"
    CM_S2 = "cm/s2"
    M_S2 = "m/s2"

    @property
    def per_g(self) -> float:
        """Divisor that turns a value in this unit into a value in g."""
        if self is AccelerationUnit.G:
            return 1.0
        if self is AccelerationUnit.CM_S2:
            return STANDARD_GRAVITY_CM_S2
        return STANDARD_GRAVITY_CM_S2 / 100.0


# ----------------------------------------------------------------------
@dataclass
class SeismicRecord:
    """One acceleration-time history, sampled at a constant interval.

    ``accelerations`` are in **g** and ``dt`` in seconds. A record with
    fewer than two samples has no duration and is refused by
    :meth:`is_usable` rather than silently integrating to zero.

    ``source_unit`` is what the file said; it does not change the stored
    numbers and exists only so the interface can report where they came
    from.
    """

    name: str = "Record"
    dt: float = 0.02
    accelerations: list[float] = field(default_factory=list)
    source_unit: AccelerationUnit = AccelerationUnit.G
    source_file: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)

    # ------------------------------------------------------------------
    @property
    def pga(self) -> float:
        """Peak ground acceleration, in g, as an absolute value."""
        if not self.accelerations:
            return 0.0
        return max(abs(a) for a in self.accelerations)

    @property
    def duration(self) -> float:
        """Length of the record in seconds.

        ``(n - 1) * dt`` and not ``n * dt``: the samples are the ends of
        the intervals, so n samples span n-1 of them. The difference is
        one step, the same size as the discretisation error the
        integrator already carries, so getting it wrong here would be
        invisible to every test that does not check the duration itself.
        """
        n = len(self.accelerations)
        return (n - 1) * self.dt if n > 1 else 0.0

    def is_usable(self) -> bool:
        return (len(self.accelerations) > 1 and self.dt > 0.0
                and all(math.isfinite(a) for a in self.accelerations))

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "dt": self.dt,
            # Stored in g, which is what they are in memory. The key says
            # so, so that a file cannot be read back under another unit.
            "accelerations_g": list(self.accelerations),
            "source_unit": self.source_unit.value,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SeismicRecord":
        try:
            unit = AccelerationUnit(data.get("source_unit", "g"))
        except ValueError:
            unit = AccelerationUnit.G
        rec = cls(
            name=data.get("name", "Record"),
            dt=float(data.get("dt", 0.02)),
            accelerations=[float(a)
                           for a in data.get("accelerations_g", [])],
            source_unit=unit,
            source_file=data.get("source_file", ""),
        )
        if data.get("id"):
            rec.id = data["id"]
        return rec


# ----------------------------------------------------------------------
def parse_record_text(text: str, unit: AccelerationUnit,
                      dt: Optional[float] = None) -> tuple:
    """Read a strong-motion record from plain text.

    Returns ``(accelerations_in_g, dt, note)``.

    The two layouts are the two that Jibson (1993) names for the input of
    a Newmark integration program: **successive pairs of time and
    acceleration**, and **a single string of acceleration values sampled
    at a constant time interval**. Which one a file is, is decided by how
    many numbers its first data line holds, not by an option the user has
    to get right.

    Blank lines and anything that does not parse as a number are skipped:
    strong-motion files carry headers, and refusing a file because of its
    header would send the user to a text editor for no reason. A file
    whose numbers are all header then produces an empty record, and that
    is what :meth:`SeismicRecord.is_usable` is for.

    With paired data the interval is taken from the FIRST pair of times
    and the rest are checked against it; a record that is not uniformly
    sampled comes back with a note saying so, because the integrator of
    Wilson and Keefer (1983) assumes a constant step and resampling it
    here would be inventing data.

    Reference: Jibson, R.W. (1993), Predicting earthquake-induced
    landslide displacements using Newmark sliding block analysis,
    Transportation Research Record 1411, 9-17.
    """
    rows: list[list[float]] = []
    for raw in text.splitlines():
        line = raw.strip().replace(",", " ")
        if not line or line[0] in "#;%":
            continue
        try:
            nums = [float(p) for p in line.split()]
        except ValueError:
            continue
        if nums:
            rows.append(nums)
    if not rows:
        return [], (dt or 0.0), "no numeric data"

    note = ""
    if len(rows[0]) >= 2:
        pairs = [r for r in rows if len(r) >= 2]
        if len(pairs) < 2:
            return [], (dt or 0.0), "fewer than two samples"
        times = [r[0] for r in pairs]
        accel = [r[1] for r in pairs]
        step = times[1] - times[0]
        if step <= 0:
            return [], (dt or 0.0), "non-increasing time column"
        spread = max(abs((times[i + 1] - times[i]) - step)
                     for i in range(len(times) - 1))
        if spread > 1e-6 * step:
            note = "time step is not constant"
    else:
        # One number per line: the interval has to come from outside.
        accel = [r[0] for r in rows]
        if dt is None or dt <= 0:
            return [], 0.0, "single-column file needs a time interval"
        step = dt

    div = unit.per_g
    return [a / div for a in accel], step, note
