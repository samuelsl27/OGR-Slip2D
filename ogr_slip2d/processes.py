# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
How the calculation processes are started (v0.1.329, D326).

On Windows a process with no console that starts ``python.exe`` children
gives each of them a console window of its own. The window started from a
shortcut or detached put three or four terminals in front of the program
when it computed, one of them maximised in the statistics, stealing the
focus (the third GUI test, H11). It is not the window's alone: the jobs of
the API start their worker with ``CREATE_NO_WINDOW`` (measured:
``GetConsoleWindow()`` is 0 in it), and an MCP server started by a desktop
client may have none either. ``pythonw.exe``, next to ``python.exe``, is the
same interpreter without a console, so the search points multiprocessing at
it just before it creates its pool, whoever started it.

With a console (a terminal, the test runner) the children share it and
nothing changes; neither on another system, nor in a frozen build, whose
workers start through the executable itself (``freeze_support``). The
numbers cannot move: the split of a search reproduces the sequential one bit
for bit (``tests/test_parallel_search_v197.py``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os
import sys
from typing import Optional


def child_executable(platform: Optional[str] = None,
                     executable: Optional[str] = None,
                     console: Optional[int] = None,
                     frozen: Optional[bool] = None) -> Optional[str]:
    """The interpreter the calculation processes should start with, or None
    to leave multiprocessing its own. The arguments are for the tests; by
    default they are read from this process."""
    platform = sys.platform if platform is None else platform
    if platform != "win32":
        return None
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return None
    if console is None:
        import ctypes
        console = ctypes.windll.kernel32.GetConsoleWindow()
    if console:
        return None
    executable = sys.executable if executable is None else executable
    candidate = os.path.join(os.path.dirname(executable), "pythonw.exe")
    return candidate if os.path.isfile(candidate) else None


def windowless_children(**kwargs) -> Optional[str]:
    """Point multiprocessing at :func:`child_executable` when it names one,
    and return it; None when nothing changed. Cheap, and the same every
    time, so it is called before every pool rather than once at a start
    that some callers never go through."""
    exe = child_executable(**kwargs)
    if exe is not None:
        import multiprocessing
        multiprocessing.set_executable(exe)
    return exe
