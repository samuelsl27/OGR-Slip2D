# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a running calculation tells whoever is watching it, without an argument
threaded through every function in between (v0.1.366, D362).

Two things, both per THREAD, so a calculation the window runs on its own
thread is the only one that hears them:

* the **phase** it is in (:func:`progress_phase`, :func:`phase`), which the
  progress callback the caller passed can read when the engine calls it: the
  window says "Optimizing the critical surface…" instead of a bar that goes
  back from 100 % to 0 % as if the run had started again;
* **checkpoints** (:func:`checkpoint`) in the loops that report no progress
  of their own — the Picard passes of the seepage solver, its rescue — where
  a watcher installed with :func:`watching` may stop the run by raising.

With no watcher installed, which is every run of the command line, the API,
a script and the tests, ``checkpoint()`` does nothing and ``phase()`` is
None. Nothing here changes a number: a checkpoint either returns or raises.

The exception a watcher raises is its own (the window's ``TaskCancelled``, a
``BaseException``, so the engine's ``except Exception`` blocks let it pass).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

#: The phase of a search's optimisation of its critical surfaces.
OPTIMIZE = "optimize"

_local = threading.local()


def phase() -> Optional[str]:
    """The phase the calculation on this thread is in, or None."""
    return getattr(_local, "phase", None)


class progress_phase:
    """``with progress_phase(OPTIMIZE): ...`` — the phase while inside."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self):
        self._before = phase()
        _local.phase = self.name
        return self

    def __exit__(self, *exc) -> bool:
        _local.phase = self._before
        return False


class watching:
    """``with watching(check): ...`` — ``check()`` is called at every
    :func:`checkpoint` on this thread while inside, and may raise to stop
    the calculation."""

    def __init__(self, check: Callable[[], None]) -> None:
        self.check = check

    def __enter__(self):
        self._before = getattr(_local, "check", None)
        _local.check = self.check
        return self

    def __exit__(self, *exc) -> bool:
        _local.check = self._before
        return False


def checkpoint() -> None:
    """A point where the calculation may be stopped: calls the watcher of
    this thread, if there is one."""
    check = getattr(_local, "check", None)
    if check is not None:
        check()
