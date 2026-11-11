# Disassembles the eboot (vaddr = file offset - 0x4000) from a vaddr for n bytes.
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
d = open(sys.argv[1], 'rb').read()
start = int(sys.argv[2], 16); n = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x100
md = Cs(CS_ARCH_X86, CS_MODE_64)
for i in md.disasm(d[0x4000 + start:0x4000 + start + n], start):
    extra = ''
    if 'rip +' in i.op_str or 'rip -' in i.op_str:
        try:
            disp = int(i.op_str.split('rip ')[1].split(']')[0].replace(' ', ''), 16)
            t = i.address + i.size + disp
            s = d[0x4000 + t:0x4000 + t + 40].split(b'\0')[0]
            extra = f'  ; -> {t:#x} {s[:40]!r}' if s and all(32 <= c < 127 for c in s) else f'  ; -> {t:#x}'
        except Exception:
            pass
    print(f'{i.address:#08x}: {i.mnemonic:8s} {i.op_str}{extra}')
