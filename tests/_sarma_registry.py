# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.464 (D357) — what the tests that walk the method registry skip of
Sarma's method, and why. Not a list of tests: two refusals the method
makes by its specification (spec 009), recognised by their codes, so a
test skips a result only when the method refused it for one of them:

* ``lem.sarma_face_strength`` — a face crosses a material that is neither
  Mohr–Coulomb nor undrained, whose strength on a face the method does not
  read (spec 009, «Fuera de alcance»; the owner's decision of 2026-11-16
  added the undrained one, c = cu);
* ``lem.sarma_excess_pore_pressure`` — the excess pore pressure of loading
  (B-bar), which the method does not compute;
* ``lem.sarma_supports`` — a support, which it does not take.

What those tests check on the bases, for the models Sarma refuses on a
face, is not checked for Sarma anywhere: its bases read their strength
through the same ``local_c_phi`` as every method (``test_sarma_wedges_v1463``,
``TestTheBaseReadsItsColumn``, with SHANSEP and a vertical-stress ratio), and
the design identities run on Mohr–Coulomb and undrained materials
(``test_sarma_method_v1464``, ``test_sarma_wedges_v1463``).
"""
from __future__ import annotations

SKIPPED_CODES = frozenset({"lem.sarma_face_strength",
                           "lem.sarma_excess_pore_pressure",
                           "lem.sarma_supports"})


def refused_by_its_spec(method_id: str, result) -> bool:
    """Whether ``result`` is Sarma's method refusing for one of the reasons
    of the module; any other refusal of it is a failure like any other."""
    return (method_id == "sarma" and result is not None
            and getattr(result, "message_code", "") in SKIPPED_CODES)


def accepts_supports(cls) -> bool:
    """Whether a registered method class takes supports (the class says
    so: ``ACCEPTS_SUPPORTS``, False for Sarma's)."""
    return getattr(cls, "ACCEPTS_SUPPORTS", True)
