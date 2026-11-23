@echo off
title Build Discord Message Cleaner Setup
cd /d "%~dp0"

call build_exe.bat nopause || exit /b 1

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Inno Setup 6 is not installed. It's free: https://jrsoftware.org/isdl.php
  echo Install it, then run this file again.
  start https://jrsoftware.org/isdl.php
  pause & exit /b 1
)

echo Building the setup wizard...
%ISCC% installer.iss || (echo Setup build failed. & pause & exit /b 1)

echo.
echo Done! Your setup file is in:  %~dp0installer_output\
explorer "%~dp0installer_output"
pause
