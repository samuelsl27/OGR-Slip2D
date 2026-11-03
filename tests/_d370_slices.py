# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""D370 bisection helper — only on ``dev/d370-shutdown``.

    python tests/_d370_slices.py S N [K M]

prints the test files of slice ``S`` of ``N`` (alphabetical, contiguous),
and with ``K M`` the sub-slice ``K`` of ``M`` of it, space-separated.
"""
import glob
import os
import sys


def part(items, k, n):
    size = -(-len(items) // n)
    return items[k * size:(k + 1) * size]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(os.path.basename(p)
                   for p in glob.glob(os.path.join(here, "test_*.py")))
    a = [int(x) for x in sys.argv[1:]]
    chosen = part(files, a[0], a[1])
    if len(a) == 4:
        chosen = part(chosen, a[2], a[3])
    print(" ".join(chosen))


if __name__ == "__main__":
    main()
