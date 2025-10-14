@echo off
REM Quick test script for building the Windows executable
echo ========================================
echo Jellyfin TV Tools - Quick Build Test
echo ========================================
echo.

echo [1/2] Testing PyInstaller build...
python build_release.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build FAILED! Check the errors above.
    pause
    exit /b 1
)

echo.
echo [2/2] Build completed successfully!
echo.
echo Your release package is in: release\JellyfinTvTools-Windows.zip
echo.
echo You can test the executable at:
echo   release\JellyfinTvTools-Windows\JellyfinTvTools.exe
echo.

pause
