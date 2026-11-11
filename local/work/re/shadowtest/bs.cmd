@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
C:\Games\SDKs\clang+llvm-23.1.4-x86_64-pc-windows-msvc\bin\clang-cl.exe /nologo /std:c++20 /EHsc /O1 /I C:\Games\AstroQuest-src\shadps4-arm64-main\src s.cpp /Fe:s.exe
