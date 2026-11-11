# Split each traced frame into its two eye renders and compare them draw by draw.
import re, sys
draw_re = re.compile(r"TRACE draw idx=(\w+) n=(\d+) inst=(\d+) prim=(\d+) pipeline=(\w+) cb0=(0x[0-9a-f]+) (\d+x\d+) s(\d) cb_mode=(\d+) mask=(0x[0-9a-f]+) db=(0x[0-9a-f]+) z_en=(\w+) z_wr=(\w+) zfunc=(\d+).*?vp=\(([^)]*)\)\+\(([^)]*)\) vs=(0x[0-9a-f]+) ps=(0x[0-9a-f]+)")
tex_re = re.compile(r"TRACE   texture (\d+) of shader (0x[0-9a-f]+) \(stage (\d+).*?at (0x[0-9a-f]+) -> (\S+) (\S+) at")
frames, cur = [], None
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if "TRACE HMD frame" in line:
        cur = []; frames.append((re.search(r"frame (\d+)", line).group(1), cur)); continue
    if cur is None: continue
    m = draw_re.search(line)
    if m:
        g = m.groups()
        cur.append({"n": g[1], "inst": g[2], "cb0": g[5], "size": g[6], "db": g[10], "z": g[11][0]+g[12][0], "vp": g[14]+"+"+g[15], "vs": g[16], "ps": g[17], "tex": [], "blend": ""})
        continue
    if "TRACE blend target=0" in line and cur and "ps" in cur[-1]:
        cur[-1]["blend"] = re.search(r"enabled=(\w+) color=(\S+)", line).group(0); continue
    m = tex_re.search(line)
    if m and cur and "tex" in cur[-1]:
        cur[-1]["tex"].append(f"s{m.group(3)}t{m.group(1)}:{m.group(4)}:{m.group(5)}:{m.group(6)}"); continue
    m = re.search(r"TRACE (resolve.*|fce.*|dispatch.*|dma-\S+)", line)
    if m:
        cur.append({"op": m.group(1).split(' is_meta')[0]})
def eyes(evs):
    out, cur, prev_copy = [], [], False
    for e in evs:
        copy = e.get("size") == "3712x3840"
        if prev_copy and not copy:
            out.append(cur); cur = []
        cur.append(e); prev_copy = copy
    out.append(cur)
    return out
def key(e):
    if "op" in e: return e["op"]
    return f'{e["cb0"]} {e["size"]} db={e["db"]} z={e["z"]} n={e["n"]}x{e["inst"]} vs={e["vs"]} ps={e["ps"]} {e["blend"]} vp={e["vp"]}'
for fid, evs in frames:
    es = eyes(evs)
    print(f"=== frame {fid}: {len(es)} parts, events {[len(x) for x in es]}")
    if len(es) < 2: continue
    a, b = es[0], es[1]
    diffs = 0
    for i, (x, y) in enumerate(zip(a, b)):
        kx, ky = key(x), key(y)
        if kx != ky or x.get("tex") != y.get("tex"):
            diffs += 1
            if diffs <= int(sys.argv[2] if len(sys.argv) > 2 else 40):
                print(f"  #{i}\n    eye1: {kx}\n    eye2: {ky}")
                if x.get("tex") != y.get("tex"):
                    print(f"    tex1: {x.get('tex')}\n    tex2: {y.get('tex')}")
    print(f"  {diffs} differing events of {min(len(a), len(b))}")

print("\n##### aligned at each eye's first depth-prepass draw")
def from_prepass(evs):
    for i, e in enumerate(evs):
        if e.get("size") == "8x8":
            return evs[i:]
    return evs
for fid, evs in frames:
    es = eyes(evs)
    if len(es) < 2: continue
    a, b = from_prepass(es[0]), from_prepass(es[1])
    print(f"=== frame {fid}: eye1 {len(a)} events, eye2 {len(b)} events")
    diffs = 0
    for i, (x, y) in enumerate(zip(a, b)):
        kx, ky = key(x), key(y)
        if kx != ky or x.get("tex") != y.get("tex"):
            diffs += 1
            if diffs <= 25:
                print(f"  #{i}\n    eye1: {kx}\n    eye2: {ky}")
                if x.get("tex") != y.get("tex"):
                    print(f"    tex1: {x.get('tex')}\n    tex2: {y.get('tex')}")
    print(f"  {diffs} differing events of {min(len(a), len(b))}")
