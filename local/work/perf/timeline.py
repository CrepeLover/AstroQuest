# Timeline of the periodic performance reports in a shadPS4 AstroQuest log.
import re, sys
path = sys.argv[1]
rows = []      # one per 5 s scheduler report
cur = {}
events = []
t = 0
pat = {
 'sched': re.compile(r'frame stats at (\d+) s: ([\d.]+) fps, per frame ([\d.]+) passes \(([\d.]+) loading their targets, ([\d.]+) Mpx\), (\d+) draws, ([\d.]+) dispatches, ([\d.]+) submits, GPU busy (\d+)%'),
 'path': re.compile(r'frame path: the title hands its lists over within ([\d.]+) ms, the GPU thread is through them ([\d.]+) ms later \(([\d.]+) ms of its time per frame\), the frame is taken ([\d.]+) ms after that and flipped ([\d.]+) ms later; ([\d.]+) ms from'),
 'title': re.compile(r'frames take ([\d.]+) ms, its time step is ([\d.]+) ms, the game ran at (\d+)% of its speed over the last 10 s \(it would have at (\d+)% left to itself\); it draws the scene at (\d+)x(\d+) an eye and is given (\d+) refreshes a frame \(([\d.]+) ms\), the GPU busy (\d+)% of the time, its memory ([\d.]+) of'),
 'hmd': re.compile(r'Headset: the title delivered ([\d.]+) frames a second \((\d+) ms the longest wait for one, (\d+) waits of more than 50 ms\), ([\d.]+) were shown, the headset took ([\d.]+) pictures a second \((\w+)\); handing one over took ([\d.]+) ms, ending a picture ([\d.]+) ms \(([\d.]+) at worst, (\d+) of 50'),
 'recov': re.compile(r'Late-frame recovery: (\d+) pictures recovered, (\d+) waits timed out'),
 'drv': re.compile(r'(\d+) of (\d+) frames came at the title\'s own pace, on average ([\d.]+) ms into a refresh \(by eighths of one: ([\d ]+)\)'),
 'reproj': re.compile(r'shown ([\d.]+) degrees from where they were drawn for \(([\d.]+) at most\)'),
}
compiles = 0
for line in open(path, encoding='utf-8', errors='replace'):
    m = pat['sched'].search(line)
    if m:
        t = int(m[1]); cur = dict(t=t, fps=float(m[2]), passes=float(m[3]), mpx=float(m[5]), draws=int(m[6]), gpu=int(m[9]), compiles=compiles)
        compiles = 0
        rows.append(cur); continue
    m = pat['path'].search(line)
    if m and cur: cur.update(hand=float(m[1]), taken=float(m[4]), e2e=float(m[6])); continue
    m = pat['title'].search(line)
    if m and cur: cur.update(ft=float(m[1]), step=float(m[2]), speed=int(m[3]), headroom=int(m[4]), tgpu=int(m[9]), mem=float(m[10])); continue
    m = pat['hmd'].search(line)
    if m and cur:
        cur.update(deliv=float(m[1]), lwait=int(m[2]), w50=int(m[3]), shown=float(m[4]), hz=float(m[5]), state=m[6], endf=float(m[8]), endw=float(m[9]))
        r = pat['reproj'].search(line)
        if r: cur.update(rdeg=float(r[1]))
        continue
    m = pat['recov'].search(line)
    if m and cur: cur.update(rec=int(m[1]), tout=int(m[2])); continue
    m = pat['drv'].search(line)
    if m and cur: cur.update(own=int(m[1]), tot=int(m[2]), into=float(m[3])); continue
    if 'CompileModule' in line: compiles += 1; continue
    if 'SceneFile:' in line:
        n = re.search(r'parameters (\S+)', line); events.append((t, 'scene ' + (n[1] if n else '?')))
    elif '<Error>' in line or '<Critical>' in line:
        events.append((t, line.strip()[:200]))
def f(r, k, fmt='{:>5}'):
    v = r.get(k); return fmt.format('' if v is None else v)
print('   t   fps  draws  Mpx gpu%| title ft step spd% room tgpu mem | xr deliv shown lwait w50 endf endw rec tout state | own/tot into | cmp')
for r in rows:
    print(f"{r['t']:>4} {r['fps']:>5} {r['draws']:>6} {r['mpx']:>5.0f} {r['gpu']:>4}|", f(r,'ft'), f(r,'step'), f(r,'speed'), f(r,'headroom'), f(r,'tgpu'), f(r,'mem'), '|', f(r,'deliv'), f(r,'shown'), f(r,'lwait'), f(r,'w50','{:>3}'), f(r,'endf'), f(r,'endw'), f(r,'rec','{:>3}'), f(r,'tout','{:>3}'), f(r,'state','{:>8}'), '|', f(r,'own','{:>4}')+'/'+f(r,'tot','{:<4}'), f(r,'into'), '|', r['compiles'])
print('\nEvents:')
seen = {}
for t, e in events:
    k = e[:120]
    seen[k] = seen.get(k, 0) + 1
    if seen[k] <= 2: print(f'{t:>5}  {e}')
for k, n in seen.items():
    if n > 2: print(f'  (x{n}) {k}')
