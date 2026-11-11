@echo off
rem Starts AstroQuest with the saved settings and no settings window (for launching from SteamVR).
rem Run "Play Astro Bot VR.bat" to change resolution or framerate; its choices are saved.
set SHADPS4_XR_SHARED_QUEUE=0
set SHADPS4_VR_RETRY_SECONDS=15
set SHADPS4_VR_PACE=
set SHADPS4_FRAME_STATS=1
set SHADPS4_FRAME_STATS_EVERY=5
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc-vr\launch.ps1" -NoMenu
