# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The leak check moved to the suite's core (``ogr_core.testing.leaks``, OGR
Core 0.2.0). This name stays for the tests that import a helper from it
(``from _leaks import root_logging_kept``): it IS that module, the same
object, so there is one allow-list and one set of rules in the process.

DRAFT of phase 1 of OGR Core 0.2.0.
"""
import sys

from ogr_core.testing import leaks as _shared

sys.modules[__name__] = _shared
