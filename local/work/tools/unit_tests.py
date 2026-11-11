"""Builds and runs AstroQuest's own unit tests (tools/tests/*_test.cpp) against one source tree, so the
same tests can be compared before and after a merge.

usage: python -I unit_tests.py <root> <out-dir> [--externals <shadps4-arm64-main/externals of a built tree>]
  <root>  folder holding shadps4-arm64-main/, tools/tests/ and quest-host/ (a worktree or a `git archive` export)
Each test is compiled with the clang-cl line its header comment gives (relative to <root>), or, without one,
with /I shadps4-arm64-main/src /I tools/tests /I tools/tests/stubs. Writes <out-dir>/summary.txt and one
<name>.txt per test (compile + run output). Toolchain: clang-cl from LLVM 23.1.4 with the VS 2022 vcvars64
environment, like the emulator build.
"""
import glob
import os
import re
import subprocess
import sys

VCVARS = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
IDLE = 0x00000040  # IDLE_PRIORITY_CLASS: an RDP session stays responsive
EXTRA_SOURCES = {
    'virtualizer_test': ['shadps4-arm64-main/src/core/libraries/audio/surround_virtualizer.cpp',
                         'shadps4-arm64-main/src/core/libraries/audio3d/audio3d_spatializer.cpp'],
}
LLVM = r'C:\Games\SDKs\clang+llvm-23.1.4-x86_64-pc-windows-msvc\bin'


def vc_env():
    out = subprocess.run(f'cmd /s /c ""{VCVARS}" >nul && set"', capture_output=True, text=True, shell=True).stdout
    env = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    env['PATH'] = LLVM + ';' + env.get('PATH', '')
    return env


def documented_command(source):
    """The clang-cl line in the test's leading comment, continuation lines joined, or None."""
    lines = []
    taking = False
    for line in source.splitlines()[:40]:
        if not line.startswith('//'):
            break
        text = line[2:].strip()
        if text.startswith('clang-cl'):
            taking = True
        if taking:
            if not text:
                break
            lines.append(text.rstrip('\\').strip())
            if '/Fe' in text:
                break
    return ' '.join(lines) if lines else None


def main():
    args = sys.argv[1:]
    externals = None
    if '--externals' in args:
        i = args.index('--externals')
        externals = args[i + 1]
        del args[i:i + 2]
    root, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    os.makedirs(out, exist_ok=True)
    env = vc_env()
    summary = []
    for test in sorted(glob.glob(os.path.join(root, 'tools', 'tests', '*_test.cpp'))):
        name = os.path.splitext(os.path.basename(test))[0]
        source = open(test, encoding='utf-8', errors='replace').read()
        exe = os.path.join(out, name + '.exe')
        cmd = documented_command(source)
        if cmd:
            parts = cmd.split()
            parts = [p for p in parts if not p.startswith('/Fe')]
            how = 'documented'
        else:
            parts = ['clang-cl', '/std:c++latest', '/EHsc', '-fuse-ld=lld', '/I', 'shadps4-arm64-main/src',
                     '/I', 'tools/tests', '/I', 'tools/tests/stubs', f'tools/tests/{name}.cpp']
            how = 'fallback'
        # A test whose own header comment gives no build line needs these to compile and link.
        if name in EXTRA_SOURCES and not cmd:
            parts += [s for s in EXTRA_SOURCES[name] if os.path.exists(os.path.join(root, s))]
        if externals:
            for inc in ('fmt/include', 'magic_enum/include', 'ext-boost', 'robin-map/include', 'xbyak', 'toml11',
                        'json/include', 'openxr-sdk/include', 'vulkan-headers/include', 'half/include',
                        'spdlog/include'):
                if os.path.isdir(os.path.join(externals, inc)):
                    parts += ['/I', os.path.join(externals, inc)]
        parts += ['/nologo', '-Wno-everything', f'/Fe:{exe}', f'/Fo:{out}\\']
        if parts[0] == 'clang-cl':  # CreateProcess looks a program up on this process's PATH, not env's
            parts[0] = os.path.join(LLVM, 'clang-cl.exe')
        log = [f'$ {" ".join(parts)}  ({how})']
        c = subprocess.run(parts, cwd=root, env=env, capture_output=True, text=True, errors='replace',
                           creationflags=IDLE)
        log.append(c.stdout + c.stderr)
        if c.returncode != 0 or not os.path.exists(exe):
            summary.append(f'{name:40} COMPILE-FAIL ({how})')
            open(os.path.join(out, name + '.txt'), 'w', encoding='utf-8').write('\n'.join(log))
            continue
        try:
            r = subprocess.run([exe], cwd=root, capture_output=True, text=True, errors='replace', timeout=120,
                               creationflags=IDLE)
            text, code = r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired:
            text, code = 'TIMEOUT', -1
        log.append(f'--- run exit {code}\n{text}')
        ok = len(re.findall(r'(?m)^\s*ok\b', text))
        fail = len(re.findall(r'(?m)^\s*FAIL\b', text))
        summary.append(f'{name:40} exit {code:3}  ok {ok:4}  FAIL {fail:3}  ({how})')
        open(os.path.join(out, name + '.txt'), 'w', encoding='utf-8').write('\n'.join(log))
    open(os.path.join(out, 'summary.txt'), 'w', encoding='utf-8').write('\n'.join(summary) + '\n')
    print('\n'.join(summary))


if __name__ == '__main__':
    main()
