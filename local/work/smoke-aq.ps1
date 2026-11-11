# Smoke / A-B test for AstroQuest (2026-11-10). Runs one build in a separate test install
# (C:\Games\AstroQuest-test) through that build's own launcher (-NoMenu), with the user's settings
# and a FRESH COPY of the user's config, saves and caches, on the virtual headset (no OpenXR, so
# SteamVR is not touched), muted, with an input script; then closes the game window like a player
# would and summarizes the log into C:\Games\astroquest-work\runs\<stamp>-<Tag>\summary.txt.
# The real install C:\Games\AstroQuest (exe, launcher, settings, saves) is only read, never written.
# usage: smoke-aq.ps1 -Tag name [-Exe path] [-LauncherFrom folder] [-Seconds 150] [-Script file] [-Env @{}]
#   -Exe          the emulator to test (default: the installed one)
#   -LauncherFrom folder with launch.ps1 + collect-crash-report.ps1 (default: the installed pc-vr)
param([Parameter(Mandatory = $true)][string]$Tag,
      [string]$Exe = 'C:\Games\AstroQuest\pc-vr\shadps4.exe',
      [string]$LauncherFrom = 'C:\Games\AstroQuest\pc-vr',
      [int]$Seconds = 150,
      [string]$Script = 'C:\Games\astroquest-work\script-aq-boot.txt',
      [string]$Shots = '30,15',   # SHADPS4_SHOT_SECONDS: a picture every 30 s from 15 s in (emulator-side)
      [string]$WindowShots = '60,100,140',   # window captures (PrintWindow) at these seconds
      [hashtable]$Env = @{})
$ErrorActionPreference = 'Stop'
$real = 'C:\Games\AstroQuest'
$test = 'C:\Games\AstroQuest-test'; $pcvr = Join-Path $test 'pc-vr'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$out = Join-Path 'C:\Games\astroquest-work\runs' "$stamp-$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
if (Get-Process shadps4 -ErrorAction SilentlyContinue) { throw 'shadps4.exe is already running; not starting another.' }
if (Get-Process vrserver, vrcompositor -ErrorAction SilentlyContinue) { throw 'SteamVR is running (someone may be in the headset); not testing now.' }

# --- the test install: launcher + exe under test, a fresh copy of the user's state ---------------
New-Item -ItemType Directory -Force $pcvr | Out-Null
Copy-Item -LiteralPath $Exe -Destination (Join-Path $pcvr 'shadps4.exe') -Force
foreach ($f in 'launch.ps1', 'collect-crash-report.ps1', 'BUILD.txt') {
    $src = Join-Path $LauncherFrom $f
    if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $pcvr $f) -Force }
}
# Same starting state every run: mirror the user's folder without the big diagnostics.
& robocopy (Join-Path $real 'pc-vr\user') (Join-Path $pcvr 'user') /MIR /NFL /NDL /NJH /NJS /NP /R:1 /W:1 `
    /XD rt_dump rt_dump_prev log screenshots captures | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy of the user folder failed ($LASTEXITCODE)" }
# (Left out of the mirror, so cleared here: what a previous test run wrote.)
foreach ($d in 'log', 'screenshots') {
    $p = Join-Path $pcvr "user\$d"
    if (Test-Path $p) { Get-ChildItem -LiteralPath $p -Force | Remove-Item -Recurse -Force }
}
$settings = Get-Content -LiteralPath (Join-Path $real 'pc-vr\settings.txt')
$settings += @(
    '# --- smoke-aq.ps1 (appended; later lines win) ---',
    "game=$real\games\CUSA12392\eboot.bin",
    'menu=0', 'headset=0', 'wait=0',
    'env=SDL_AUDIO_DRIVER=dummy', 'env=SHADPS4_OPENXR=0', 'env=SHADPS4_XR_WAIT=0',
    'env=SHADPS4_FRAME_STATS=1', 'env=SHADPS4_FRAME_STATS_EVERY=5', "env=SHADPS4_SHOT_SECONDS=$Shots")
if ($Script) { $settings += "env=SHADPS4_INPUT_SCRIPT=$((Resolve-Path -LiteralPath $Script).Path)" }
foreach ($k in $Env.Keys) { $settings += "env=$k=$($Env[$k])" }
$settings | Set-Content -LiteralPath (Join-Path $pcvr 'settings.txt') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $pcvr 'settings.txt') -Destination $out
# (.NET directly: Get-FileHash is missing in a 5.1 started with a PowerShell 7 PSModulePath.)
function Sha256([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create(); $file = [System.IO.File]::OpenRead($path)
    try { return (($sha.ComputeHash($file) | ForEach-Object { $_.ToString('X2') }) -join '') } finally { $file.Dispose(); $sha.Dispose() }
}
@("Tag=$Tag", "Exe=$Exe", "ExeSHA256=$(Sha256 $Exe)",
  "LauncherFrom=$LauncherFrom", "Script=$Script", "Seconds=$Seconds", "Started=$(Get-Date -Format o)") |
    Set-Content (Join-Path $out 'run-info.txt')

# --- run: the launcher in Windows PowerShell 5.1, as "Play Astro Bot VR (Steam).bat" does ---------
# (PSModulePath from a PowerShell 7 session breaks Get-FileHash in 5.1: let 5.1 build its own.)
$savedModulePath = $env:PSModulePath; Remove-Item Env:PSModulePath -ErrorAction SilentlyContinue
try {
    $launcher = Start-Process -FilePath "$env:windir\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$pcvr\launch.ps1`"", '-NoMenu') `
        -WorkingDirectory $pcvr -PassThru -WindowStyle Normal `
        -RedirectStandardOutput (Join-Path $out 'launcher-stdout.txt') -RedirectStandardError (Join-Path $out 'launcher-stderr.txt')
} finally { $env:PSModulePath = $savedModulePath }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class AqW { [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rr, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags); }
'@
# The game window's own content (PrintWindow, PW_RENDERFULLCONTENT), even when covered.
function Shot([System.Diagnostics.Process]$p, [string]$file) {
    $p.Refresh(); $h = $p.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { return $false }
    $r = New-Object AqW+R; [AqW]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.Rr - $r.L; $hh = $r.B - $r.T
    if ($w -le 50 -or $hh -le 50) { return $false }
    $bmp = New-Object System.Drawing.Bitmap $w, $hh
    $gr = [System.Drawing.Graphics]::FromImage($bmp); $hdc = $gr.GetHdc()
    $ok = [AqW]::PrintWindow($h, $hdc, 2); $gr.ReleaseHdc($hdc)
    if (-not $ok) { $gr.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size) }
    $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png); $gr.Dispose(); $bmp.Dispose()
    return $true
}
$t0 = Get-Date
$game = $null
while (-not $game -and ((Get-Date) - $t0).TotalSeconds -lt 60 -and -not $launcher.HasExited) {
    Start-Sleep -Milliseconds 500
    $game = Get-Process shadps4 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Join-Path $pcvr 'shadps4.exe') } | Select-Object -First 1
}
$result = 'no game process'
if ($game) {
    "game pid $($game.Id) for ${Seconds}s -> $out"
    $marks = @($WindowShots -split ',' | Where-Object { $_ } | ForEach-Object { [int]$_.Trim() }) | Sort-Object -Unique; $taken = @()
    while (-not $game.HasExited -and ((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
        Start-Sleep -Seconds 2
        $el = [int]((Get-Date) - $t0).TotalSeconds
        foreach ($m in $marks) { if ($el -ge $m -and $taken -notcontains $m) { $taken += $m; [void](Shot $game (Join-Path $out "window-$m.png")) } }
    }
    if ($game.HasExited) {
        $result = "exited by itself after $([int]((Get-Date) - $t0).TotalSeconds)s"
    } else {
        # Close the window, as a player quits: exit code 0, no crash report.
        [void]$game.CloseMainWindow()
        if (-not $game.WaitForExit(30000)) { Stop-Process -Id $game.Id -Force; $result = 'did not close; killed' }
        else { $result = 'closed after the run' }
    }
}
if (-not $launcher.WaitForExit(20000)) { Stop-Process -Id $launcher.Id -Force -ErrorAction SilentlyContinue }

# --- collect + summarize ---------------------------------------------------------------------------
$logDir = Join-Path $pcvr 'user\log'
Get-ChildItem -LiteralPath $logDir -File -ErrorAction SilentlyContinue | Copy-Item -Destination $out
$shotDir = Join-Path $pcvr 'user\screenshots'
if (Test-Path $shotDir) { New-Item -ItemType Directory -Force (Join-Path $out 'shots') | Out-Null; Get-ChildItem $shotDir -File | Copy-Item -Destination (Join-Path $out 'shots') }
$log = Join-Path $out 'shad_log.txt'
$lines = if (Test-Path $log) { Get-Content -LiteralPath $log } else { @() }
$runResult = Get-Content -LiteralPath (Join-Path $out 'run-result.txt') -ErrorAction SilentlyContinue
$sum = @("RESULT: $result | $(($runResult | Where-Object { $_ -like 'ExitCode=*' }) -join ' ') | log lines $($lines.Count) | $out")
function Marker([string]$name, [string]$pattern) {
    $hits = @($lines | Select-String -Pattern $pattern)
    $first = if ($hits.Count) { ($hits[0].Line -replace '^\[[^\]]*\] <\w+> \([^)]*\) \S+ ', '') } else { '' }
    return ('{0,-22} {1,6}  {2}' -f $name, $hits.Count, $first.Substring(0, [Math]::Min(170, $first.Length)))
}
$sum += '--- feature markers (count, first) ---'
$sum += Marker 'virtual headset' 'Virtual headset connected'
$sum += Marker 'build recognised' 'in a build known'
$sum += Marker 'sun shadow pool' "The sun's shadow maps are"
$sum += Marker 'scene rewrites' 'SceneFile: The scene parameters'
$sum += Marker 'depth array 8192' 'Depth array 8192'
$sum += Marker 'AF16' 'Anisotropic filtering raised'
$sum += Marker 'occlusion (real)' "Occlusion queries: answered with the GPU"
$sum += Marker 'occlusion reports' 'Occlusion queries: \d+ asked'
$sum += Marker 'MLAA' 'MLAA at strength'
$sum += Marker 'pipeline cache' 'PipelineCacheEnabled: true'
$sum += Marker 'microphone' 'Microphone:'
$sum += Marker 'input script' 'cripted input|input script'
$sum += Marker 'title clock' "The title's clock: frames take"
$clock = @($lines | Select-String -Pattern "frames take ([\d.]+) ms" | ForEach-Object { [double]$_.Matches[0].Groups[1].Value })
if ($clock.Count) { $m = $clock | Measure-Object -Average -Minimum -Maximum; $sum += ('frame ms (title clock): n {0} avg {1:N2} min {2:N2} max {3:N2}' -f $m.Count, $m.Average, $m.Minimum, $m.Maximum) }
$crit = @($lines | Where-Object { $_ -match '<Critical>' })
$err = @($lines | Where-Object { $_ -match '<Error>' })
$sum += "--- Critical: $($crit.Count) ---"; $sum += ($crit | Select-Object -First 20)
$sum += "--- Error: $($err.Count) (distinct, numbers folded) ---"
$sum += ($err | ForEach-Object { ($_ -replace '^\[[^\]]*\] <Error> \([^)]*\) ', '') -replace '0x[0-9a-fA-F]+', 'X' -replace '\d+', 'N' } |
         Group-Object | Sort-Object Count -Descending | Select-Object -First 25 | ForEach-Object { '{0,6} {1}' -f $_.Count, $_.Name })
$sum += '--- launcher stdout (last 40) ---'
$sum += (Get-Content (Join-Path $out 'launcher-stdout.txt') -ErrorAction SilentlyContinue | Select-Object -Last 40)
$sum | Set-Content (Join-Path $out 'summary.txt')
$sum
