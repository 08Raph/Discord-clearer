@echo off
title Build Discord Message Cleaner
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (
  echo Python is not installed. Get it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during install.
  pause & exit /b 1
)

echo Installing / updating what the app needs (Pillow, OpenCV, pystray, PyInstaller)...
%PY% -m pip install --upgrade -r requirements.txt || (echo pip failed. & pause & exit /b 1)
%PY% tools\make_icon.py

echo Building (folder build: fewer antivirus false alarms than a single .exe)...
%PY% -m PyInstaller --noconfirm --clean --onedir --windowed ^
  --name "DiscordMessageCleaner" ^
  --icon "icon.ico" ^
  --version-file "version_info.txt" ^
  --add-data "icon.ico;." ^
  --add-data "icon.png;." ^
  --add-data "icon_16.png;." ^
  --add-data "icon_32.png;." ^
  --add-data "icon_48.png;." ^
  --add-data "icon_64.png;." ^
  --add-data "icon_256.png;." ^
  --hidden-import app ^
  --hidden-import tray ^
  --hidden-import media ^
  --hidden-import richtext ^
  --hidden-import social ^
  --hidden-import emojis ^
  --hidden-import i18n_keys ^
  --hidden-import lang_es ^
  --hidden-import lang_pt ^
  --hidden-import lang_de ^
  --hidden-import pystray._win32 ^
  --exclude-module matplotlib ^
  --exclude-module numpy.tests ^
  main.py || (echo Build failed. & pause & exit /b 1)

echo.
echo Done! Your app is in:  %~dp0dist\DiscordMessageCleaner\
echo Run DiscordMessageCleaner.exe from that folder (keep the whole folder together).
if "%1"=="nopause" exit /b 0
explorer "%~dp0dist\DiscordMessageCleaner"
pause
