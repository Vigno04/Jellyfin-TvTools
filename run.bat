@echo off
title Jellyfin TV Tools
echo ================================================
echo Jellyfin TV Tools - Modern IPTV Manager
echo ================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo.
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Starting application...
echo.
python run.py

echo.
echo Application closed.
pause
