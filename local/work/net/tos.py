# Counts the DSCP of IPv4 UDP packets in a pktmon pcapng, per source -> destination.
import collections
import struct
import sys

data = open(sys.argv[1], 'rb').read()
counts = collections.Counter()
pos = 0
endian = '<'
while pos + 12 <= len(data):
    btype, blen = struct.unpack_from(endian + 'II', data, pos)
    if btype == 0x0A0D0D0A:
        endian = '<' if data[pos + 8:pos + 12] == b'\x4d\x3c\x2b\x1a' else '>'
        btype, blen = struct.unpack_from(endian + 'II', data, pos)
    if blen < 12:
        break
    if btype == 6:  # enhanced packet block
        caplen = struct.unpack_from(endian + 'I', data, pos + 20)[0]
        frame = data[pos + 28:pos + 28 + caplen]
        off = 12
        ethertype = struct.unpack_from('>H', frame, off)[0] if len(frame) > 14 else 0
        while ethertype == 0x8100 and len(frame) > off + 6:
            off += 4
            ethertype = struct.unpack_from('>H', frame, off)[0]
        ip = frame[off + 2:]
        if ethertype == 0x0800 and len(ip) >= 20 and ip[9] == 17:
            src = '.'.join(map(str, ip[12:16]))
            dst = '.'.join(map(str, ip[16:20]))
            ihl = (ip[0] & 15) * 4
            sport, dport = struct.unpack_from('>HH', ip, ihl) if len(ip) >= ihl + 4 else (0, 0)
            counts[(f'{src}:{sport}', f'{dst}:{dport}', ip[1] >> 2)] += 1
    pos += blen

for (src, dst, dscp), n in counts.most_common(12):
    print(f'{n:7d}  {src:>22} -> {dst:<22} DSCP {dscp}')
