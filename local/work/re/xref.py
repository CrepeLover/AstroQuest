# Finds RIP-relative references (disp32 ending an instruction) to given vaddrs in the eboot's
# first PT_LOAD (file offset 0x4000 -> vaddr 0). Usage: xref.py eboot.bin vaddr [vaddr...]
import sys, numpy as np
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
path = sys.argv[1]; targets = [int(t, 16) for t in sys.argv[2:]]
d = open(path, 'rb').read()
BASE_OFF, SIZE = 0x4000, 0x15ad998
seg = np.frombuffer(d, dtype=np.uint8, offset=BASE_OFF, count=SIZE)
n = SIZE - 4
disp = (seg[0:n].astype(np.int64) | (seg[1:n+1].astype(np.int64) << 8) |
        (seg[2:n+2].astype(np.int64) << 16) | (seg[3:n+3].astype(np.int64) << 24))
disp = np.where(disp >= 2**31, disp - 2**32, disp)
pos = np.arange(n, dtype=np.int64)
md = Cs(CS_ARCH_X86, CS_MODE_64)
for t in targets:
    # instruction ends right after disp (no immediate) or 1/4 bytes later (imm8/imm32)
    for extra in (0, 1, 4):
        hits = np.nonzero(pos + 4 + extra + disp == t)[0]
        for h in hits:
            # try decoding from a few bytes before
            for back in range(2, 8):
                start = h - back
                ins = list(md.disasm(bytes(seg[start:start+16]), start))
                if ins and ins[0].address == start and start + ins[0].size == h + 4 + extra and 'rip' in ins[0].op_str:
                    print(hex(t), hex(start), ins[0].mnemonic, ins[0].op_str)
                    break
