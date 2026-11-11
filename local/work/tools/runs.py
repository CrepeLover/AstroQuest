# Per traced frame: runs of consecutive draws to the same colour/depth target.
import re, sys
frames, cur = [], None
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if "TRACE HMD frame" in line:
        cur = {"id": re.search(r"frame (\d+)", line).group(1), "ev": []}
        frames.append(cur)
        continue
    if cur is None:
        continue
    m = re.search(r"TRACE draw .*?n=(\d+) inst=(\d+).*?cb0=(0x[0-9a-f]+) (\d+x\d+) s(\d).*?mask=(0x[0-9a-f]+) db=(0x[0-9a-f]+) z_en=(\w+) z_wr=(\w+).*?ps=(0x[0-9a-f]+)", line)
    if m:
        cur["ev"].append(("draw",) + m.groups())
        continue
    m = re.search(r"TRACE blend target=0 enabled=(\w+)", line)
    if m and cur["ev"] and cur["ev"][-1][0] == "draw":
        cur["ev"][-1] = cur["ev"][-1] + (m.group(1),)
        continue
    m = re.search(r"TRACE (dispatch|resolve|fce|dma-\w+|fmask-decompress)", line)
    if m:
        cur["ev"].append((m.group(1),))
for f in frames:
    print(f"=== frame {f['id']}: {sum(e[0]=='draw' for e in f['ev'])} draws")
    run, n = None, 0
    def flush():
        if run:
            print(f"  {n:4d} x {run}")
    for e in f["ev"]:
        key = (f"{e[3]} {e[4]} s{e[5]} db={e[7]}" if e[0] == "draw" else e[0])
        if key != run:
            flush(); run, n = key, 0
        n += 1
    flush()
