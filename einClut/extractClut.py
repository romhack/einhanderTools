#!/usr/bin/env python
# Extracts CLUT from VRAM dump to binary file. Usage:
# extractClut VRAM_DUMP_NAME CLUT_POS OUT_NAME
# CLUT_POS - serialized CLUT poisition in VRAM, as it's stated in GPU packet command word
# x is 6 lower bits, y is 10 higher bits

import sys

_, vramName, clutPos, outName, *rest = sys.argv

val = int(clutPos, base=16)
x = (val & 0x3F) * 16
y = val >> 6
offset = y*0x800 + x*0x2

with open(vramName, 'rb') as fvram:
    fvram.seek(offset)
    bytes_chunk = fvram.read(0x20)
    with open(outName, 'wb') as output_file:
        output_file.write(bytes_chunk)
print("For CLUT position", clutPos, "X =",
      x, "Y =", y, "Offset =", hex(offset))
