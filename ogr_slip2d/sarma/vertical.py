# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Vertical slices read as wedges: the special case of Sarma's method with
vertical faces.

A set of vertical slices from :func:`ogr_slip2d.slicer.slice_surface` is a
set of wedges whose faces are vertical (δ = 0). With no strength on those
faces the interslice shear X vanishes, and the force equilibrium of the
wedges is Janbu's simplified method (Janbu 1954, 1973): the recurrence of
:mod:`ogr_slip2d.sarma.solver` then reduces, wedge by wedge, to
Σ[c′l + (W cos α − U) tan φ′ − W sin α]/m_α = 0 with
m_α = cos α (1 + tan α tan φ′). That identity is how the solver is checked
against a path of the engine already validated.

Everything a slice carries is read the way Janbu's method reads it, through
the same functions, so the identity is exact and not a copy that can drift:

* the loads, from :func:`ogr_slip2d.external_forces.slice_forces` (the
  vertical load with ``kv`` on the soil, ponded water included, D170 and
  D206; the horizontal external force) and
  :func:`~ogr_slip2d.external_forces.seismic_soil_part` (the static soil
  weight ``kh`` acts on);
* U = u·l, ``Slice.pore_pressure`` being u at the middle of the base;
* c and tan φ from ``BishopSimplified._local_c_phi`` at the normal stress
  Janbu's method reads them at, the Fellenius estimate
  max(0, W cos α − u·l)/l (``x0_resisting_pass``), so that even the secant
  a Mohr-Coulomb material is read through rounds the same way;
* the sense of sliding, from :func:`ogr_slip2d.methods.janbu.slide_sense`.

The faces carry no strength and no water force here (with no strength the
water on a vertical face adds nothing: it acts across the face and is
balanced by the neighbour). The water of a tension crack is already in the
``water_force_h`` of the slice at the wall, so it is NOT given again as the
head thrust: that would count it twice.

Left out, and stated: supports (the registered method refuses them, from
v0.1.464), and a curved envelope read at the method's own stress (it comes
with the method too). The faces' own strength, of a policy or given, is the
wedges' (:mod:`ogr_slip2d.sarma.wedges`, v0.1.463). Until v0.1.462 this
said v0.1.463 and v0.1.462: D447 came in front, and the versions of the
method moved by one.

Author: Samuel Sáez López (UPCT)

References:
    Janbu, N. (1954). Application of composite slip surfaces for stability
        analysis. Proc. European Conf. on Stability of Earth Slopes,
        Stockholm, vol. 3, 43–49.
    Janbu, N. (1973). Slope stability computations. In Embankment-Dam
        Engineering (Casagrande volume), Wiley, 47–86.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ogr_slip2d.external_forces import seismic_soil_part, slice_forces
from ogr_slip2d.methods.bishop import BishopSimplified
from ogr_slip2d.methods.janbu import slide_sense
from ogr_slip2d.sarma.solver import Base, Face


@dataclass(frozen=True)
class VerticalWedges:
    """The wedges of a set of vertical slices, ready for
    :func:`ogr_slip2d.sarma.solver.solve`."""

    bases: tuple
    faces: tuple
    slide_sign: int


def from_vertical_slices(slices, kh: float = 0.0,
                         kv: float = 0.0) -> VerticalWedges:
    """The wedges with vertical faces and no face strength that a set of
    vertical slices is.

    Args:
        slices: the slices of :func:`ogr_slip2d.slicer.slice_surface` (a
            ``Slices`` or a list of ``Slice``), in increasing x.
        kh: the horizontal seismic coefficient (0 without seismic).
        kv: the vertical one, positive downward.

    Returns:
        A :class:`VerticalWedges`. ``solve(w.bases, w.faces, kh=kh,
        slide_sign=w.slide_sign)`` gives Janbu's simplified factor of the
        same slices (Janbu 1954, 1973).
    """
    s_list = list(slices)
    sign = int(slide_sense(s_list, kh, kv))
    bases = []
    for s in s_list:
        f = slice_forces(s, kh, kv)
        a, length = s.base_angle, s.base_length
        # Janbu's own estimate of the effective normal stress, at which it
        # reads the strength (``bishop.x0_resisting_pass``).
        raw = f.w_total * math.cos(a) - s.pore_pressure * length
        sigma = max(0.0, raw) / max(length, 1e-9)
        c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma)
        bases.append(Base(alpha=a, length=length, weight=f.w_total,
                          soil_weight=seismic_soil_part(s),
                          pore_force=s.pore_pressure * length,
                          cohesion=c, tan_phi=tan_phi, force_x=f.h_water))
    faces = [Face(delta=0.0,
                  length=max(0.0, s_list[0].top_y_left
                             - s_list[0].base_y_left))]
    for s in s_list:
        faces.append(Face(delta=0.0,
                          length=max(0.0, s.top_y_right - s.base_y_right)))
    return VerticalWedges(tuple(bases), tuple(faces), sign)
