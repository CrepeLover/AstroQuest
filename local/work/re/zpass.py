# Find PM4 EVENT_WRITE ZPASS_DONE (event type 21, index 1 -> dword 0x115) packet builders in the eboot.
import sys, struct, re
data = open(sys.argv[1], 'rb').read()
hdr = struct.pack('<I', 0xC0024600)  # type-3, count 2, EVENT_WRITE
for m in re.finditer(re.escape(hdr), data):
    print('EVENT_WRITE hdr literal at file 0x%x' % m.start())
for pat, name in [(b'\x15\x01\x00\x00', 'dword 0x115'), (struct.pack('<I', 0xC0024600), 'hdr')]:
    n = len(re.findall(re.escape(pat), data)); print(name, 'occurs', n)
# mov dword [reg+disp], 0xC0024600 / mov reg, imm32 forms
for m in re.finditer(re.escape(struct.pack('<I', 0xC0024600)), data):
    ctx = data[max(0, m.start()-24):m.start()+40]
    j = ctx.find(b'\x15\x01\x00\x00')
    print('  near 0x%x: 0x115 %s' % (m.start(), 'within' if j >= 0 else 'not within'))
