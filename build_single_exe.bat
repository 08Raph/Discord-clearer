@echo off
title Build Discord Message Cleaner (single .exe)
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

echo Building ONE .exe file (easy to share, can be moved anywhere)...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "DiscordMessageCleaner" ^
  --distpath "dist_single" ^
  --workpath "build_single" ^
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
  --hidden-import everyday ^
  --hidden-import archive ^
  --hidden-import planner ^
  --hidden-import safety ^
  --hidden-import emojis ^
  --hidden-import i18n_keys ^
  --hidden-import lang_es ^
  --hidden-import lang_pt ^
  --hidden-import lang_de ^
  --hidden-import pystray._win32 ^
  --exclude-module matplotlib ^
  --exclude-module numpy.tests ^
  main.py || (echo Build failed. & pause & exit /b 1)

echo Making the zip to share...
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist_single\DiscordMessageCleaner.exe','README.md','LICENSE' -DestinationPath 'dist_single\DiscordMessageCleaner_v7.7.0_windows.zip'"

echo.
echo Done! Your single .exe is here:  %~dp0dist_single\DiscordMessageCleaner.exe
echo and a ready-to-share zip:        %~dp0dist_single\DiscordMessageCleaner_v7.7.0_windows.zip
explorer "%~dp0dist_single"
pause
