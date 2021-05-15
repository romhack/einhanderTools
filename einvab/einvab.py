#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
einvab.py
A tool to unpack and pack pseudo VAB files for PSX game 'Einhander'
Version:   0.9
Author:    Griever
Web site:  https://github.com/romhack/
License:   MIT License https://opensource.org/licenses/mit-license.php
'''

import os
import glob
import math
from shutil import rmtree
import click
from bitstring import ConstBitStream, BitStream


@click.group()
def cli():
    """A tool to unpack and pack pseudo VAB files for PSX game 'Einhander'
    """
    pass


SECTOR_SIZE = 0x800
HEADER_SIZE = 0x2000


def get_offsets(stream, tbl_offs):
    """
    Get start of VAGs and each file sizes from header in VAB

    Parameters
    ----------
    stream : bitstream
        VAB file stream
    tbl_offs : int
        Offset of size table in VAG's header

    Returns
    -------
    start : int
        Start of first VAG
    sizes : list of ints
        List of sizes for each of VAG file

    """
    sizes = []
    stream.bytepos = tbl_offs
    # HEADER_SIZE header size
    start = HEADER_SIZE + stream.read('uintle:16') * 8
    while True:
        size = stream.read('uintle:16') * 8
        if size == 0:
            return (start, sizes)
        sizes.append(size)


def split_vab(sizes_tuple, vab_name):
    """
    Save header, vag files and last sector to given folder

    Parameters
    ----------
    sizes_tuple : tuple(int, [int])
        Start and sizes list
    vab_name : string
        VAB file name to unpack

    Returns
    -------
    None.

    """
    # output folder is input file name
    dir_name = os.path.splitext(vab_name)[0]
    if os.path.exists(dir_name):
        rmtree(dir_name)
    os.mkdir(dir_name)
    file_num = 0
    with open(vab_name, "rb") as vab_file:
        with open(dir_name + "\\header.bin", "wb") as hdr_file:
            hdr_file.write(vab_file.read(HEADER_SIZE))
        (start, sizes) = sizes_tuple
        vab_file.seek(start)
        for (file_num, size) in enumerate(sizes):
            with open(dir_name + f"\\{file_num:02}.adpcm", "wb") as end_file:
                end_file.write(vab_file.read(size))
        vab_file.seek(0, os.SEEK_END)  # then last sector for rebuild
        vab_filesize = vab_file.tell()
        last_sector_start = vab_filesize - SECTOR_SIZE
        vab_file.seek(last_sector_start)
        with open(dir_name + "\\last_sector.bin", "wb") as last_file:
            last_file.write(vab_file.read(SECTOR_SIZE))


@cli.command(name='unpack', short_help='unpack vab file to given folder')
@click.argument('vab_name')
@click.argument('table_offs')
def unpack(vab_name, table_offs):
    """
    Unpack given VAB file to given folder.
    Need to provide offset to VAGs sizes table.
    Files in each folder will be named in continuous numbering.
    """
    vab_stream = ConstBitStream(filename=vab_name)
    sizes_tuple = get_offsets(vab_stream, int(table_offs, 16))
    split_vab(sizes_tuple, vab_name)


@cli.command(name='pack', short_help='pack folder to vab file')
@click.argument('dir_name')
@click.argument('table_offs')
def merge_vab(dir_name, table_offs):
    """
    Pack given directory in corresponding {name}_patched.bin vab file.
    Need to provide offset to VAGs sizes table.
    Files in folder are packed in alphabetical order. Sizes and last sector number are patched.
    """
    with open(dir_name+"_patched.bin", "wb") as merged_file:
        adpcm_names = glob.glob(dir_name+"\\*.adpcm")
        sizes = [os.path.getsize(file_name) for file_name in adpcm_names]
        # first write header
        hdr_stream = BitStream(filename=dir_name+"\\header.bin")
        hdr_stream.bytepos = int(table_offs, 16)
        hdr_stream.overwrite(BitStream(uintle=0, length=16)
                             )  # start with zero offset
        for size in sizes:
            assert size >> 3 <= 0xFFFF, "Size overflows 16 bits!"
            hdr_stream.overwrite(BitStream(uintle=size >> 3, length=16))
        adpcm_size = sum(sizes)
        vab_sector_size = math.ceil(adpcm_size / SECTOR_SIZE)
        # check if vab will fit SPU memory:
        assert adpcm_size <= 0x39000, f"Max ADPCM size exceeded: 0x{adpcm_size-0x39000:x}!"
        hdr_stream.bytepos = 0x1FFC  # end of header - 4 bytes of sector-size
        hdr_stream.overwrite(BitStream(uintle=vab_sector_size, length=16))
        merged_file.write(hdr_stream.tobytes())

        for file_name in adpcm_names:  # then append adpcm bodies
            with open(file_name, "rb") as adpcm_file:
                merged_file.write(adpcm_file.read())

        out_file_size = merged_file.tell()  # align up to sector size
        align_size = SECTOR_SIZE - (out_file_size % SECTOR_SIZE)
        merged_file.write(bytes([0]*align_size))

        with open(dir_name+"\\last_sector.bin", "rb") as last_file:
            merged_file.write(last_file.read())


if __name__ == '__main__':
    cli()
