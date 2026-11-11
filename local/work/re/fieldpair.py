# Code places that read two struct fields (disp32 offsets) within a window: candidates for the
# code that uses both scene parameters. Usage: fieldpair.py eboot.bin offA offB [window]
import sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
d = open(sys.argv[1], 'rb').read(); B = 0x4000; SZ = 0x10d0000
code = d[B:B + SZ]
a, b = int(sys.argv[2], 16), int(sys.argv[3], 16)
win = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x80
md = Cs(CS_ARCH_X86, CS_MODE_64)
def sites(off):
    out = []
    for m in re.finditer(re.escape(off.to_bytes(4, 'little')), code):
        p = m.start()
        for back in range(2, 9):  # instruction start: disp32 is at most 8 bytes in
            st = p - back
            ins = next(md.disasm(code[st:st + 15], st), None)
            if ins and ins.address == st and st + ins.size >= p + 4 and f'{off:#x}]' in ins.op_str:
                out.append((st, f'{ins.mnemonic} {ins.op_str}'))
                break
    return out
A, Bs = sites(a), sites(b)
print(len(A), len(Bs))
for sa, ta in A:
    for sb, tb in Bs:
        if abs(sa - sb) <= win and ('xmm' in ta or 'xmm' in tb):
            print(f'{sa:#x} {ta:45s} {sb:#x} {tb}')
