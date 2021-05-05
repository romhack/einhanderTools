#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
einpack.py
A tool to unpack and pack BININDEX and BINPACK VFS files for PSX game 'Einhander'
Version:   0.9
Author:    Griever
Web site:  https://github.com/romhack/
License:   MIT License https://opensource.org/licenses/mit-license.php
'''

import os
import click
from shutil import rmtree
from bitstring import ConstBitStream, Bits


@click.group()
def cli():
    """A tool to unpack and pack BININDEX and BINPACK VFS files for PSX game 'Einhander'
    """
    pass

SECTOR_SIZE = 0x800
SECTOR_SIZE_BITCOUNT = 11 #1 << 11 = 0x800
MAX_SECTOR_ENTRIES = 0x800/4 #2 16-bit words per entry



def deserialize_binindex(stream, dir_num):
    """
    Process BININDEX.BIN file and collect offset-size tuples for given folder number

    Parameters
    ----------
    stream : bitstring
        Input file stream
    dir_num : Int
        Number of folder to process tuples

    Returns
    -------
    result : list
        Offset-Size tuples (in sectors)

    """
    result = []
    stream.bytepos = dir_num * SECTOR_SIZE
    while True:
        offs = stream.read('uintle:16')
        size = stream.read('uintle:16')
        if size == 0 or len(result) >= MAX_SECTOR_ENTRIES:#no more files or full sector read
            return result
        result.append ((offs,size))

def unpack_dir(dir_num, tuples):
    """
    Process one BINPACK{n}.BIN file and splits files to given folder

    Parameters
    ----------
    dir_num : Int
        Number of folder.
    tuples : list
        Offset-Size tuples for given BINPACK file (in sectors)

    Returns
    -------
    None.

    """
    dir_name = f"{dir_num}"
    if os.path.exists(dir_name):
        rmtree(dir_name)
    os.mkdir(dir_name)
    file_num = 0
    with open(f"BINPACK{dir_num}.BIN", "rb") as pack_file:
        for (file_num, (offs, size)) in enumerate(tuples):     
            pack_file.pos = offs * SECTOR_SIZE
            with open(dir_name + f"\\{file_num:02}.bin", "wb") as end_file:
                end_file.write(pack_file.read(size * SECTOR_SIZE))
                
@cli.command(name='unpack', short_help='unpack binindex and binpacks to folders')
def unpack_index():
    """
    Unpack VFS files with names BININDEX.BIN and BINPACK{n}.BIN to corresponding folders. Files in each folder will be named in continuous numbering.
    """         
    idx_stream = ConstBitStream(filename="BININDEX.BIN")
    dir_count = len(idx_stream) >> 14 #1 sector per dir. 800 bytes per sector, 8 bits per byte.            
    for num in range (dir_count):
        tuples = deserialize_binindex(idx_stream, num)
        unpack_dir(num, tuples) 
        
def pack_dir(dir_name):
    """
    Write new BINPACK{n}.BIN file with contents of given folder,
    collect offset-size tuples and return them for further binindex serialization

    Parameters
    ----------
    dir_name : string
        Name of processing folder.

    Returns
    -------
    tuples : list
        Collected offset-size tuples (in bytes)

    """

    tuples = []
    offs = 0
    with open(f"BINPACK{dir_name}.BIN", "wb") as pack_file:
        for file in os.listdir(dir_name):
            current_name = os.path.join(dir_name, file)
            if os.path.isfile(current_name):
                with open(current_name, "rb") as end_file:
                    data = end_file.read()
                    size = len (data)
                    assert size & (SECTOR_SIZE - 1) == 0, "File size not sector aligned, aborted!"
                    tuples.append((offs, size))
                    offs = offs + size
                    pack_file.write(data)
    return tuples

def serialize_binindex(tuples):
    """
    Write new BININDEX.BIN file with offset-size tuples per each sector

    Parameters
    ----------
    tuples : list of list 
        Each folder offset-size tuples (in bytes)

    Returns
    -------
    None.

    """
    idx_data = Bits()
    for dir_tuples in tuples:
        for (offs, size) in dir_tuples:
            idx_data += Bits (uintle= offs >> SECTOR_SIZE_BITCOUNT, length=16) + Bits (uintle= size >> SECTOR_SIZE_BITCOUNT, length=16)         
        align_block_len = SECTOR_SIZE*8 - (len(idx_data) % (SECTOR_SIZE*8))
        idx_data += Bits (uint=0, length=align_block_len)

    with open("BININDEX.BIN", 'wb') as index_file:
        idx_data.tofile(index_file)
        
        

    
@cli.command(name='pack', short_help='pack folders to binindex and binpacks')
@click.argument('dir_names')           
def pack_index (dir_names):
    """
    Pack given DIR_NAMES in corresponding BINPACK{n}.BIN, assemble new BININDEX.BIN  
    
    DIR_NAMES: Space-separated string of folders names to pack in sequental order. Files in each folder are packed in alphabetical order
    """    
    dir_names_list = dir_names.split()
    tuples = [pack_dir(dir_name) for dir_name in dir_names_list]#pack and get offs-size for dir
    serialize_binindex(tuples)
    
if __name__ == '__main__':
    cli()
