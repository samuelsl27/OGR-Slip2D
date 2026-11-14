# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Whose a surface of a run is: the search's, or one the user drew.

v0.1.448 (D404) -- the rule moved here from ``ogr_slip2d.search``, which
re-exports it under the same name, because a caller appeared that cannot
import the engine: the PDF report (``ogr_core.report.report_generator``),
whose «Global Minimums» block now says when a method's critical surface is
the user's. The windows, the API and the back analysis asked the engine's
copy; asking a second rule of its own, the report answered differently for
anything that is not a real ``SearchResult`` (the review of 0.1.448). One
rule, in the lowest layer that has the question.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def is_user_surface_of(result, evaluation) -> bool:
    """Whether ``evaluation`` is one of the surfaces the user drew, by
    identity, for anything that looks like a ``SearchResult`` (v0.1.428).

    By identity and not by equality: a surface the user drew and one the
    search generated can have the same geometry and the same factor, and
    are still two surfaces. ``user_evaluations`` read by ``getattr``, so a
    result without that list (an older stand-in, a test's double with only
    ``evaluations``) has no surface of the user."""
    user = getattr(result, "user_evaluations", None) or ()
    return any(r is evaluation for r in user)
