# einvab
A tool to unpack and pack pseudo VAB files for PSX game 'Einhander'


Synopsis:
```
Usage: einpvab.py COMMAND [ARGS]...

Commands:
  pack    pack folder to vab file
  unpack  unpack vab file to given folder
```
  
Description:
```
einvab.py unpack [OPTIONS] VAB_NAME TABLE_OFFS

  Unpack given VAB file to given folder. Need to provide offset to VAGs
  sizes table. Files in each folder will be named in continuous numbering.

einvab.py pack [OPTIONS] DIR_NAME TABLE_OFFS

  Pack given directory in corresponding {name}_patched.bin vab file. Need to
  provide offset to VAGs sizes table. Files in folder are packed in
  alphabetical order. Sizes and last sector number are patched.
```

Example usage:
```bat
python einvab.py unpack 08.bin 0xA20
pause
```
```bat
python einvab.py pack "08" 0xA20
pause
```
Install:
```
pip install -r requirements.txt
```
  
A tool to unpack and pack pseudo VAB files for PSX game 'Einhander'. The game uses VAB-like format for most of it's voice messages. The tool is written solely for translation purposes, so I didn't dive deep in play-sound commands of the game or in pseudo vab file format itself.  
Shortly, pseudo vab has the same header, as generic PSX sound library VAB, except it's 0x2000 in size. The last two words signify last sector number and size of XA sample in the last sector. This sample should remain untouched and sector number need to be patched accordingly after VAB edit.  
In other aspects, this is still VAB file: there is a size table in the header, and actual VAG bodies (compressed ADPCM samples) after header. The last can be edited by MFAudio utility.  
Using the tool you can unpack samples to the folder, replace them with you own edited samples and then reassemble back. The tool will warn you if result VAB file is too large to fit in SPU memory, as Einhander put samples in specific part of memory.
