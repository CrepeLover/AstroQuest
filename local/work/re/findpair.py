# Finds places that load 2048 into two registers (or stores) within 16 bytes: a 2048x2048 target.
import sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
d = open(sys.argv[1], 'rb').read(); B = 0x4000
code = d[B:B + 0x10d0000]
md = Cs(CS_ARCH_X86, CS_MODE_64)
imm = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x800
pat = imm.to_bytes(4, 'little')
pos = [m.start() for m in re.finditer(re.escape(pat), code)]
seen = set()
for i in range(len(pos) - 1):
    if pos[i + 1] - pos[i] <= 16:
        s = pos[i] - 8
        if s in seen: continue
        seen.add(s)
        # decode from a sync point a bit earlier
        for back in range(0, 12):
            st = pos[i] - back - 1
            ins = list(md.disasm(code[st:st + 48], st))
            if ins and ins[0].address == st and any(f'{imm:#x}' in x.op_str for x in ins[:2]):
                print(f'{st:#x}: ' + ' | '.join(f'{x.mnemonic} {x.op_str}' for x in ins[:7]))
                break
