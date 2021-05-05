# einpack
A tool to unpack and pack BININDEX and BINPACK VFS files for PSX game 'Einhander'


Synopsis:
```
Usage: einpack.py COMMAND [ARGS]...
```
  
Description:
```
 einpack.py unpack [OPTIONS]

  Unpack VFS files with names BININDEX.BIN and BINPACK{n}.BIN to
  corresponding folders. Files in each folder will be named in continuous
  numbering.

einpack.py pack [OPTIONS] DIR_NAMES

  Pack given DIR_NAMES in corresponding BINPACK{n}.BIN, assemble new
  BININDEX.BIN

  DIR_NAMES: Space-separated string of folders names to pack in sequental
  order. Files in each folder are packed in alphabetical order
```

Example usage:
```bat
@echo off
cd original
python ..\..\einpack\einpack.py unpack && echo Unpacked successfully in original directory
pause
```
```bat
@echo off
cd patched
python ..\..\einpack\einpack.py pack "0 1 2 3 4 5" && echo Packed successfully in patched directory
pause
```
Install:
```
pip install -r requirements.txt
```
  
A tool for to unpack and pack Virtual File System BININDEX.BIN and BINPACK.BIN files for PSX game 'Einhander'. Each sector (0x800 bytes) of BININDEX.BIN contains size-offset pair for each file of the folder. Values are in uintle:16. One sector corresponds to one folder. Free space of sector can be zero-aligned up to 0x800.   
File extension or other attributes are not stored in this VFS.   
BINPACK{n}.BIN contains all concatenated files of corresponding folder. 
