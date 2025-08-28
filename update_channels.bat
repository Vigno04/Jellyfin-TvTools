@echo off
echo ================================================
echo Italian TV Channels Updater
echo ================================================
echo.
echo This will:
echo  1. Download latest M3U from TivuStream
echo  2. Filter to keep only main Italian channels
echo  3. Clean this folder and save the filtered list
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo Running channel updater...
echo.

python "%~dp0update_channels.py"

echo.
echo ================================================
echo Done! Check tivustream_list.m3u
echo ================================================
pause
