# einlzss
A tool to unpack and pack lzss compressed data for PSX game 'Einhander'


Synopsis:
```
Usage: einlzss.py [OPTIONS] COMMAND [ARGS]...
Commands:
  pack    compress file
  unpack  decompress file
```
  
Description:
```
einlzss.py unpack [OPTIONS] IN_NAME BASE START_OFFSET COUNT

  Decompress given IN_NAME packed file.
  BASE - PSX RAM address, where file is mapped to.
  START_OFFSET - file offset of first pointer in table.
  COUNT - number of chunk pointers to process
  All unpacked chunks are merged in one output file.
  Output file name can be provided, otherwise default 'decompressed.bin' will be used.

Options:
  -o, --out_name TEXT  Output plain file name.

einlzss.py pack [OPTIONS] IN_NAME BASE PTR_TABLE_OFFSET
                       BLOCK_START_OFFSET PLAIN_CHUNK_SIZE TARGET_SIZE

  Compress plain IN_NAME file.
  BASE - PSX RAM address, where file is mapped to.
  PTR_TABLE_OFFSET - file offset of first pointer in table.
  BLOCK_START_OFFSET - file offset of first block to place to.
  PLAIN_CHUNK_SIZE - size in bytes of plain gfx chunk.
  TARGET_SIZE - original size for compressed chunks, which patched gfx must fit in.
  Output file name can be provided, otherwise default 'compressed.bin' will be used.

Options:
  -o, --out_name TEXT  Output packed file name.
```

Example usage:
```bat
REM unpack
python einlzss.py unpack "12.bin" 0x800ae000 0x35f9c 0x20 -o "full_text_font.pix"
REM pack
python einlzss.py pack "full_text_font_patched.pix" 0x800ae000 0x35f9c 0x32964 0x400 0x362c -o "12_patched.bin"
pause
```
Install:
```
pip install -r requirements.txt
```
  
A tool to unpack and pack lzss compressed chunks for PSX game 'Einhander'. The game uses graphics compressed with LZSS scheme for some of it's graphics. It is initially split into chunks with 8 pixels height and then packed with LZSS in the following format:
```
w16: compressed stream size in bytes
compressed bitstream:
    flag:
    1: uncompressed byte, copy next 8 bits to plain buffer.
    0: lz compressed dist-len tuple. 
    	- Distance is 12 bits; zero distance signifies end of compression, so it serialized as dist + 1. 
    	    This is probably why all gfx is broken into chunks 8 pixels height: 
        	this gives 400-800 bytes per plain chunk, which covers max distance for efficient compression.
    	- Length is 4 bits. LZ is only effective, starting from len = 2 (16 bits < 18 bits). 
    	    len is serialized as len-2.
```
The tool is written solely for translation purposes, so you have to find compressed graphics file in VFS and locate necessary pointers table yourself.
