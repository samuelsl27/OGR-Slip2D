# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OGR Slip2D — MCP server (spec 008, phase F1b).

A thin layer: every tool is one operation of ``ogr_api``, published with
the official MCP SDK (``mcp``, MIT) over stdio or streamable HTTP.

    pip install "ogr-slip2d[mcp]"
    ogr-slip2d-mcp --workdir C:\\ruta\\a\\proyectos        # stdio
    ogr-slip2d-mcp --transport http --port 8765        # HTTP, with token

This package is importable WITHOUT the SDK — nothing here imports ``mcp``
at module level — so the test runner can measure it and the command line
can say "install the [mcp] extra" instead of crashing on an import.

Author: Samuel Sáez López (UPCT)
"""
__version__ = "0.1.203"
