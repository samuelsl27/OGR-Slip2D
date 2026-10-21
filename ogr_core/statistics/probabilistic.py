# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Moved: :mod:`ogr_slip2d.probabilistic` (v0.1.346, D337).

The statistical runners run the engine, and the core does not import the
engine; a re-export from here would be exactly that import. So the old path
fails loudly, with the new one.

Author: Samuel Sáez López (UPCT)
"""
raise ImportError(
    "ogr_core.statistics.probabilistic moved to ogr_slip2d.probabilistic in v0.1.346 "
    "(D337): import it from there.")
