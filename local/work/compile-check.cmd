@echo off
rem Compiles only the given object files of the AstroQuest build (one job, idle priority): a quick
rem check that changed sources compile while a game is running. Regenerates build.ninja first if
rem CMakeLists.txt changed. usage: compile-check.cmd <ninja target> [<ninja target> ...]
setlocal
set "BLD=C:\Games\AstroQuest-src\build\win-frame"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set "PATH=C:\Games\SDKs\clang+llvm-23.1.4-x86_64-pc-windows-msvc\bin;C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
set "VULKAN_SDK="
start "" /low /b /wait ninja -C "%BLD%" -j 1 %*
