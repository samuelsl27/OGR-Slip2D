# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""``python -m ogr_mcp``.

Everything under the ``__main__`` guard: on Windows a process pool started
from this process re-imports the main module in each worker, and a module
that started the server at import time would start it again in every one.
"""

if __name__ == "__main__":
    import sys

    from ogr_mcp.cli import main

    sys.exit(main())
