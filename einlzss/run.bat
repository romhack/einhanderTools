::unpack
python einlzss.py unpack "12.bin" 0x800ae000 0x35f9c 0x20 -o "full_text_font.pix"
::pack
python einlzss.py pack "full_text_font_patched.pix" 0x800ae000 0x35f9c 0x32964 0x400 0x362c -o "12_patched.bin"
pause