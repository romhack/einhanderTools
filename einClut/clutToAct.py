#!/usr/bin/env python
# Converts binary PSX CLUT to photoshop ACT format. Usage:
# python clutToAct.py INPUT_NAME OUTPUT_NAME


import sys
import bitstruct


_, clutName, outName, *rest = sys.argv

results = []
with open(clutName, "rb") as f:
    while True:
        data = f.read(2)
        if not data:
            break
        _, b, g, r = bitstruct.unpack(
            "u1u5u5u5", bitstruct.byteswap('2', data))
        results.extend([r << 3, g << 3, b << 3])
with open(outName, 'wb') as output:
    output.write(bytes(results))
    output.write(bytes([0]*(0x300-0x30)))
