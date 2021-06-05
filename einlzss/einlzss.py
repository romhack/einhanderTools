#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
einlzss

A tool for compressing and decompressing data in "Einhander" game
for PSX

Version:   0.9
Author:    Griever
Web site:  https://github.com/romhack/
License:   MIT License https://opensource.org/licenses/mit-license.php
'''
from typing import NamedTuple
from bitstring import ConstBitStream, BitStream, Bits, pack
import click
from math import ceil

# compression commands: raw or lz:
class RawEntry(NamedTuple):
    value: int  # just raw byte


class LzEntry(NamedTuple):
    distance: int  # offset back in unpacked buffer, 12 bits
    length: int  # copy count, 4 bits



MAX_OFFSET = 0xFFE  # lz offset is encoded with 12 bits, 1-starting
MAX_LEN = 0x11  # lz length is encoded with 8 bits


def deserialize(stream):
    '''
    Deserialize given bits stream to list of compress commands entries
    starts with w16: size of compressed block and then lzss data
    Parameters
    ----------
    stream : ConstBitStream
        input bits stream, read from compressed file

    Returns
    -------
    entries : list of RawEntries or LzEntries
    '''
    stream_size = (stream.read('uintbe:16')) * 8
    assert stream_size > 0, "Compressed size is found zero, aborted!"
    entries = []

    while stream_size > 0: #read until size bytes are read
        plain = stream.read('bool')
        stream_size -= 1
        if plain:
            stream_size -= 8
            if stream_size < 0:
                break #not enough bits to read raw
            entries.append(RawEntry(value=stream.read('uint:8')))
            
        else:
            stream_size -= 12
            if stream_size < 0:
                break #not enough bits to read dist
            dist = stream.read('uint:12') - 1            
            if dist < 0: #signal for the end of stream
                break
            stream_size -= 4
            if stream_size < 0:
              break #not enough bits to read len         
            count = stream.read('uint:4') + 2            
            entries.append(LzEntry(dist, count))
    return entries


def decode(entries):
    '''
    Decode given list of compression commands to plain bytes
    Parameters
    ----------
    entries : list of RawEntries or LzEntries

    Returns
    -------
    buffer : list of ints
        plain buffer of decompressed bytes

    '''
    buffer = []
    for ent in entries:
        if isinstance(ent, RawEntry):
            buffer.append(ent.value)
        else:  # lz compression
            # cycle buffer to decompress out from buffer bounds
            cyclic_buffer = buffer[ent.distance:] * ent.length
            buffer += cyclic_buffer[:ent.length]
    return buffer

def unpack_line_block (stream, base, start_offs, count):
    """
    unpacks block of lines (usually 8 pixels in height)
    each line: is deserialized and then decoded, whole block is saved as separate file
    usually its line with 8 pixels height

    Parameters
    ----------
    stream : ConstBitStream
        input bits stream, read from compressed file 
    base : int
        RAM address, where file is loaded
    start_offs: int
        start of ptr table for lines
    count: int
        number of lines in ptr table

    Returns
    -------
    buffer: list
        List of bytes of unpacked buffer

    """
    ptrs = []
    block_buffer = []
    for n in range(count):
        stream.pos = (start_offs + n* 0x20) * 8 #each line struct is 0x20 bytes
        ptrs.append (stream.read('uintle:32') - base) #read appropriate ptr
    for ptr in ptrs:
        stream.pos = ptr*8
        entries = deserialize(stream)
        block_buffer.extend(decode(entries))#decode next line
    return block_buffer

def find_lz(lst, pos):
    '''
    find best lz match for given position and haystack list

    Parameters
    ----------
    lst : list of ints
        full plain file
    pos : int
        position in plain file to search an lz match

    Returns
    -------
    LzEntry or None
        found best lz entry for this position, if not found, return None

    '''
    def common_start_len(lst, hay_start, pos):
        count = 0
        while count < MAX_LEN and pos < len(lst) and lst[hay_start] == lst[pos]:
            hay_start += 1
            pos += 1
            count += 1
        return count

    assert lst and pos < len(
        lst), "find_lz: position out of bounds or empty list!"
    candidates = []
    # max offset back is 0xFF, haystack start from pos-0xFF, trimmed by 0
    for hay_start in range(0, min (MAX_OFFSET, pos)):
        common_len = common_start_len(lst, hay_start, pos)
        if common_len >= 2:  # minimal efficient entry is 2 bytes long lz
            candidates.append(
                LzEntry(distance=hay_start, length=common_len))
    # compare candidates first by length, next by earliest occurence
    best = max(candidates, key=lambda ent: (ent.length, -ent.distance),
               default=None)

    return best


def encode(lst):
    '''
    encode given plain file to list of compression commands

    Parameters
    ----------
    lst : list of ints
        plain file to encode

    Returns
    -------
    encoded: list of RawEntries or LzEntries

    '''
    pos = 0
    encoded = []
    with click.progressbar(length=len(lst),
                           label='Encoding (1/2)') as bar:
        while pos < len(lst):
            entry = find_lz(lst, pos)
            if entry is None:  # no lz matches found, emit raw
                encoded.append(RawEntry(lst[pos]))
                pos += 1
                bar.update(1)

            else:  # lz match found, check if lazy parsing is more efficient:
                skip_entry = find_lz(lst, pos + 1)
                if isinstance(skip_entry, LzEntry) and skip_entry.length > entry.length:
                    # dump raw + skip entry match
                    encoded.append(RawEntry(lst[pos]))
                    encoded.append(skip_entry)
                    pos += skip_entry.length + 1
                    bar.update(skip_entry.length + 1)
                else:  # current lz match is most efficient, emit it
                    encoded.append(entry)
                    pos += entry.length
                    bar.update(entry.length)
    return encoded 


def serialize(commands):
    '''
    serialize given compression commands to bitstream

    Parameters
    ----------
    commands : list of RawEntries or LzEntries

    Returns
    -------
    stream : Bits
        compressed bitstream

    '''
    stream = Bits()
    with click.progressbar(commands,
                           label='Serializing (2/2)',
                           length=len(commands)) as bar:
        for command in bar:
            if isinstance(command, RawEntry):  # serialize raw
                stream += pack('bool, uint:8', True, command.value)
            else:  # serialize lz
                stream += pack('bool, uint:12, uint:4', False,
                               command.distance + 1, command.length - 2)
    size = ceil(len(stream)/8)
    return pack ('uint:16', size) + stream #prepend packed stream with size word

def pack_line_block (plain, chunk_size):
    """
    packs given file of merged lines in merged lzss blocks,
    split by chunk_size. And return offsets to each line table.

    Parameters
    ----------
    plain : list of ints
        Merged plain lines pixel data.
    chunk_size : int
        Size of each line chunk in bytes

    Returns
    -------
    Tuple: offsets, packed_block_bytes

    """
    def split_chunks(lst, n):
        """
        Yield successive n-sized chunks from lst.

        """
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
            
    chunks = split_chunks (plain, chunk_size)
    block_bytes = bytes()
    offsets = []
    for chunk in chunks:
        encoded = encode(chunk)
        serialized = serialize(encoded)
        offsets.append (len(block_bytes))
        block_bytes += serialized.tobytes()
    return (offsets, block_bytes)


@click.group()
def cli():
    """A tool for compressing and decompressing data for Einhander game.
    """
    pass

@cli.command(name='unpack', short_help='decompress file')
@click.argument('in_name')
@click.argument('base')
@click.argument('start_offset')
@click.argument('count')
@click.option('--out_name', '-o', default='decompressed.bin', help='Output plain file name.')
def decompress_file(in_name, base, start_offset, count, out_name):
    """\b
    Decompress given IN_NAME packed file.
    BASE - PSX RAM address, where file is mapped to.
    START_OFFSET - file offset of first pointer in table.
    COUNT - number of chunk pointers to process
    All unpacked chunks are merged in one output file.
    Output file name can be provided, otherwise default 'decompressed.bin' will be used.

    """
    packed_stream = ConstBitStream(filename=in_name)
    lines_block = unpack_line_block(packed_stream, int(base, 16), int(start_offset, 16), int(count, 16))
    
    with open(out_name, "wb") as decoded_file:
        decoded_file.write(bytes(lines_block))


@cli.command(name='pack', short_help='compress file')
@click.argument('in_name')
@click.argument('base')
@click.argument('ptr_table_offset')
@click.argument('block_start_offset')
@click.argument('plain_chunk_size')
@click.argument('target_size')
@click.option('--out_name', '-o', default='compressed.bin', help='Output packed file name.')
def compress_file(in_name, base, ptr_table_offset, block_start_offset, plain_chunk_size, target_size, out_name):
    """\b
    Compress plain IN_NAME file.
    BASE - PSX RAM address, where file is mapped to.
    PTR_TABLE_OFFSET - file offset of first pointer in table.
    BLOCK_START_OFFSET - file offset of first block to place to.
    PLAIN_CHUNK_SIZE - size in bytes of plain gfx chunk.
    TARGET_SIZE - original size for compressed chunks, which patched gfx must fit in.    
    Output file name can be provided, otherwise default 'compressed.bin' will be used.
    """
 
    with open(in_name, "rb") as plain_file:
        plain = list(plain_file.read())
    (offsets, block_bytes) = pack_line_block (plain, int(plain_chunk_size, 16))
    packed_size = len (block_bytes)
    tail_len = int(target_size, 16) - packed_size
    assert tail_len >= 0, f"Compressed block is larger, than block space by 0x{-tail_len:x} bytes, aborted!"
    tail_bytes = bytes([0]*tail_len)
    
    out_file = open(out_name, 'rb')
    out_stream  = BitStream(out_file)
    out_file.close
    ptrs = [int(base, 16) + int(block_start_offset, 16) + offset for offset in offsets] #calc RAM pointers
    for num, ptr in enumerate (ptrs): #patch pointer table
        out_stream.bytepos = int(ptr_table_offset, 16) + 0x20*num
        out_stream.overwrite(pack('uintle:32', ptr))
    out_file2 = open(out_name, 'wb')
    out_file2.write(out_stream.tobytes())
    out_file2.close

    out_file3 =  open(out_name, "r+b")
    out_file3.seek(int(block_start_offset, 16))#insert patched block
    out_file3.write(block_bytes+tail_bytes)
    out_file3.close  


if __name__ == '__main__':
    cli()
