# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The size in pixels of an image file, from its header (v0.1.337).

A DXF ``IMAGE`` entity links its file and needs its size in pixels
(``ImageDef``): the CAD program stretches the picture over the rectangle the
entity gives it from that. The core has no imaging library and may not
import Qt, and adding one for three integers would be a dependency the
project has to ask for (AGENTS.md). The three formats a user is likely to
place under a slope have their size at a fixed place in the header:

* **PNG**: the IHDR chunk, the first after the 8-byte signature, holds
  width and height as big-endian 32-bit integers (PNG specification, ISO/IEC
  15948, §11.2.2);
* **JPEG**: the first start-of-frame marker (SOF0–SOF15 but SOF4, SOF8 and
  SOF12, which are DHT, JPG and DAC) holds height then width as big-endian
  16-bit integers (ITU-T T.81, B.2.2);
* **BMP**: the DIB header after the 14-byte file header holds width and
  height as little-endian signed 32-bit integers (BITMAPINFOHEADER) or, in
  the old OS/2 header of 12 bytes, as 16-bit ones. A negative height means
  a top-down bitmap; the size is its absolute value.

Anything else, or a file that cannot be read, is None: the caller draws the
frame a missing picture is drawn with.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import struct
from typing import Optional


def pixel_size(path: str) -> Optional[tuple]:
    """``(width, height)`` in pixels of the PNG, JPEG or BMP at ``path``, or
    None."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
                w, h = struct.unpack(">II", head[16:24])
                return _positive(w, h)
            if head.startswith(b"BM") and len(head) >= 26:
                dib = struct.unpack("<I", head[14:18])[0]
                if dib == 12:
                    w, h = struct.unpack("<HH", head[18:22])
                else:
                    w, h = struct.unpack("<ii", head[18:26])
                return _positive(w, abs(h))
            if head.startswith(b"\xff\xd8"):
                f.seek(2)
                return _jpeg_size(f)
    except (OSError, struct.error):
        return None
    return None


def _positive(w: int, h: int) -> Optional[tuple]:
    return (int(w), int(h)) if w > 0 and h > 0 else None


def _jpeg_size(f) -> Optional[tuple]:
    """Walk the JPEG markers to the first start-of-frame."""
    while True:
        byte = f.read(1)
        if not byte:
            return None
        if byte != b"\xff":
            continue
        marker = f.read(1)
        while marker == b"\xff":            # fill bytes
            marker = f.read(1)
        if not marker:
            return None
        code = marker[0]
        if code in (0x01, 0xD8) or 0xD0 <= code <= 0xD7:
            continue                        # markers with no length
        if code == 0xD9:
            return None                     # end of image, no frame
        length = f.read(2)
        if len(length) < 2:
            return None
        n = struct.unpack(">H", length)[0]
        if 0xC0 <= code <= 0xCF and code not in (0xC4, 0xC8, 0xCC):
            data = f.read(5)
            if len(data) < 5:
                return None
            h, w = struct.unpack(">HH", data[1:5])
            return _positive(w, h)
        f.seek(n - 2, 1)
