#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
psx_bitmap_converter

PlayStation bitmap image manipulation tool: convert from raw bitmap and palette to image and back

Author:    Griever
Web site:  https://github.com/romhack/
License:   MIT License https://opensource.org/licenses/mit-license.php
'''
__version__ = "0.4"

import click
import struct
from PIL import Image


@click.group()
def cli():
    """Bitmap image manipulation tool: convert from raw bitmap and palette to image and back.
    """
    pass


@cli.command(name='decode', short_help='build normal image file from raw PSX bitmap and palette')
@click.argument('mode', type=click.Choice(['4bpp', '8bpp', '16bpp'], case_sensitive=True))
@click.argument('bitmap', type=click.File('rb'))
@click.option('--palette', '-p', type=click.Path(), default='clut.bin', help='CLUT for building 4bpp and 8bpp images.')
@click.argument('width')
@click.argument('height')
@click.option('--output', '-o', type=click.Path(), default='image.png', help='Output built image file name.')
def decode(mode, bitmap, palette, width, height, output):
    """\b
    Build image file from raw PSX bitmap data in BITMAP and palette data in PALETTE files.
    WIDTH and HEIGHT specify output image size.
    Bitmap data should be in indexed mode or in 16 bpp direct mode. Format is defined by MODE argument.
    With '8bpp' it should be in 8 bit per pixel.
    With '4bpp' it should be in 4 bit ber pixel.
    Palette data should be in 15 bit per color, RGB format as raw binary CLUT. Alpha channel bit will be ignored.
    With '16bpp' it should be PSX direct mode 16 bit per pixel. Palette data is ignored.    
    
    """
    bitmap_data = bitmap.read()
    widthValue = int(width, 0)
    heightValue = int(height, 0)
    if mode == '16bpp':
        image = Image.frombytes("RGB", (widthValue, heightValue), bitmap_data, "raw", "RGB;15", 0, 1)
    else:
        with open(palette, mode='rb') as palette_file: 
            palette_data = palette_file.read()
        if mode == '8bpp':
            image = Image.frombytes('P', (widthValue, heightValue), bitmap_data, 'raw', 'P')
        elif mode == '4bpp':
            swapped_bitmap_data = swapNybbles(bitmap_data)
            image = Image.frombytes('P', (widthValue, heightValue), swapped_bitmap_data, 'raw', 'P;4')
        colors = pal15To24(palette_data)
        image.putpalette(colors)
    image.save(output)



@cli.command(name='encode', short_help='encodes image file to raw PSX bitmap and palette')
@click.argument('image')
@click.argument('mode', type=click.Choice(['4bpp', '8bpp', '16bpp'], case_sensitive=True))
@click.option('--bitmap', '-ob', type=click.File('wb'), default='bitmap.bin', help='Output extracted raw bitmap data name.')
@click.option('--palette', '-op',type=click.File('wb'), default='clut.bin', help='Output extracted palette data name.')
def split(image, mode, bitmap, palette):
    """\b
    Encode IMAGE file to PSX format BITMAP and PALETTE files.
    Raw bitmap format is defined by MODE argument.
    With '8bpp' it will be 8 bit per pixel.
    With '4bpp' it will be in 4 bit ber pixel.
    Palette data will be in 15 bit per color, RGB format. Alpha channel bit will be omitted.
    With '16bpp' it will be in PSX direct mode 16 bit per pixel.

    """
    with Image.open(image) as original_image:
        if mode == '4bpp':
            MAX_COLORS = 16
            pal_image = original_image.convert('P')
            color_count = pal_image.getcolors(maxcolors=MAX_COLORS + 1)
            if color_count is None:
                raise ValueError("ERROR: Image has more than 16 unique colors! Aborting.")
                
            bitmap_data = pal_image.tobytes('raw', 'P;4')
            bitmap.write(swapNybbles(bitmap_data)) 
            
            palette_data = pal_image.getpalette()
            cropped_palette_data = palette_data[:MAX_COLORS * 3]
            palette.write(pal24To15(cropped_palette_data))

        elif mode == '8bpp':
            bitmap.write(bitmap_data)
            palette_data = image.getpalette()
            palette.write(pal24To15(palette_data))
        elif mode == '16bpp':
            bitmap_data = original_image.tobytes("raw")
            bitmap_data_15bpp = pal24To15(bitmap_data)
            bitmap.write(bitmap_data_15bpp)
            
        
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))   
    
# Convert array of 24bpp RGB pixels to 15bpp BGR Little Endian pixels bytes
def pal24To15(colors):
    palBytes = []
    for group in chunker(colors, 3):
        r = group[0] >> 3
        g = group[1] >> 3
        b = group[2] >> 3
        colorRgb15 = ((b << 10) + (g << 5) + r).to_bytes(2, 'little')
        palBytes += colorRgb15
    return bytes(palBytes)
# Convert 15bpp BGR Little Endian pixels bytes to 24bpp RGB array of int colors
def pal15To24(palBytes):
    colors = []
    for group in chunker (palBytes, 2):
        color = int.from_bytes(group, "little")
        b = ((color >> 10) & 0x1F) << 3
        g = ((color >> 5) & 0x1F) << 3
        r = (color  & 0x1F) << 3
        colors.append(r)
        colors.append(g)
        colors.append(b)

    return colors

def swapNybbles(data):      
    swappedArray = map(lambda x: ((x & 0xF) << 4) | ((x >> 4) & 0xF), data)
    return bytes(swappedArray) 
        
if __name__ == '__main__':
    cli()
    