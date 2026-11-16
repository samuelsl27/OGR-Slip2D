# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Sarma's method with non-vertical slices (spec 009, D357).

* :mod:`ogr_slip2d.sarma.solver` — the factor of safety of a set of wedges
  between inclined faces, from the recurrence of the critical acceleration
  Kc (pure functions: no project, no slicer, no Qt);
* :mod:`ogr_slip2d.sarma.vertical` — vertical slices of the slicer read as
  wedges with vertical faces, the special case that must give Janbu's
  simplified method when the faces carry no strength;
* :mod:`ogr_slip2d.sarma.wedges` (v0.1.463) — the wedges of a surface the
  slicer has resolved: faces, weights, water and loads;
* :mod:`ogr_slip2d.sarma.angles` (v0.1.463) — the angle of a face nobody
  gives one.

The method is NOT registered yet (v0.1.461–v0.1.463): nothing here enters
``ogr_slip2d.methods.method_registry`` until v0.1.464, so no analysis,
search or interface runs it. (Until v0.1.462 this said v0.1.463: D447 came
in front, and the versions of the method moved by one.)

Author: Samuel Sáez López (UPCT)
"""
