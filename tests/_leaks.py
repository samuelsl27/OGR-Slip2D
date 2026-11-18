# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The leak check moved to the suite's core (``ogr_core.testing.leaks``, OGR
Core 0.2.0). This name stays for the tests that import a helper from it
(``from _leaks import root_logging_kept``): it IS that module, the same
object, so there is one allow-list and one set of rules in the process.

v0.1.473 (spec 010) -- until this version the detector lived here (v0.1.374
to v0.1.471); OGR Core 0.2.0 took it, and it is changed there now. This
repository's part of the allow-list is in ``tests/_runner.py``.
"""
import sys

from ogr_core.testing import leaks as _shared

sys.modules[__name__] = _shared
