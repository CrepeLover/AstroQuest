# Finds cmp <reg>, 0x800 (2048) followed within 24 bytes by a cmov, and mov <reg>, [<reg>+0xd0]
# reads nearby (the scene parameter's shadow map size field), in the eboot's code.
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
d = open(sys.argv[1], 'rb').read(); B = 0x4000
code = d[B:B + 0x10d0000]
md = Cs(CS_ARCH_X86, CS_MODE_64); md.skipdata = True
import re
hits = []
for m in re.finditer(rb'(\x3d|\x81[\xf8-\xff]|\x41\x81[\xf8-\xff])\x00\x08\x00\x00', code):
    s = m.start()
    ins = list(md.disasm(code[s:s + 40], s))
    if not ins or ins[0].mnemonic != 'cmp':
        continue
    tail = ' | '.join(f'{i.mnemonic} {i.op_str}' for i in ins[:6])
    if 'cmov' in tail or 'jg' in tail or 'jl' in tail or 'ja' in tail or 'jb' in tail:
        # look back 0x80 bytes for a read of +0xd0
        back = list(md.disasm(code[max(0, s - 0x60):s], max(0, s - 0x60)))
        near = any('0xd0]' in i.op_str for i in back)
        hits.append((s, near, tail))
print(len(hits))
for s, near, tail in hits:
    if near:
        print(f'{s:#x} NEAR+0xd0  {tail}')
print('--- with cmov (all) ---')
for s, near, tail in hits:
    if 'cmov' in tail:
        print(f'{s:#x} {tail[:150]}')
