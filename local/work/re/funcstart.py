# Nearest "push rbp; mov rbp, rsp" (55 48 89 e5) at or before a vaddr, and direct callers (e8 rel32) of it.
import sys, re
d = open(sys.argv[1], 'rb').read()
B = 0x4000
for a in sys.argv[2:]:
    at = int(a, 16)
    s = d.rfind(b'\x55\x48\x89\xe5', B, B + at + 1) - B
    print(f'{at:#x}: function at {s:#x}')
    import numpy as np
    seg = np.frombuffer(d, dtype=np.uint8, offset=B, count=0x15ad998)
    idx = np.nonzero(seg[:-5] == 0xe8)[0]
    rel = (seg[idx+1].astype(np.int64) | (seg[idx+2].astype(np.int64) << 8) | (seg[idx+3].astype(np.int64) << 16) | (seg[idx+4].astype(np.int64) << 24))
    rel = np.where(rel >= 2**31, rel - 2**32, rel)
    callers = idx[idx + 5 + rel == s]
    print('  callers:', [hex(c) for c in callers[:20]])
