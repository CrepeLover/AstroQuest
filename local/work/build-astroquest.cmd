@echo off
rem Builds the AstroQuest PC VR emulator (evertec82/AstroQuest, branch frame-controller = v0.8.7 + Steam Frame
rem controller bindings). clang-cl from LLVM 23.1.4, MSVC 14.44 + Windows SDK via vcvars64, VS-bundled CMake/Ninja.
rem HAVE_ENDIAN_H=0: LLVM 23 ships its own endian.h, which libressl then uses instead of its shim.
rem Runs at idle priority with 8 jobs so an RDP session stays responsive.
rem usage: build-astroquest.cmd [configure]
setlocal
set "SRC=C:\Games\AstroQuest-src\shadps4-arm64-main"
set "BLD=C:\Games\AstroQuest-src\build\win-frame"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set "PATH=C:\Games\SDKs\clang+llvm-23.1.4-x86_64-pc-windows-msvc\bin;C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
set "VULKAN_SDK="
if "%~1"=="configure" (
  cmake -S "%SRC%" -B "%BLD%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl -DCMAKE_LINKER=lld-link -DCMAKE_RC_COMPILER=llvm-rc ^
    -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL -DENABLE_DISCORD_RPC=OFF -DENABLE_UPDATER=OFF -DENABLE_OPENXR=ON ^
    -DALSOFT_UPDATE_BUILD_VERSION=OFF -DHAVE_ENDIAN_H=0 ^
    -DPython3_EXECUTABLE=C:\Users\<user>/envs/python-3.13.16/python.exe || exit /b 1
)
start "" /low /b /wait cmake --build "%BLD%" --target shadps4 --parallel 8 || exit /b 1
