@echo off
title AeonFix - PC Diagnostic Assistant

:: Get the directory where the BAT file is located
set SCRIPT_DIR=%~dp0
:: Create the full path to the python script, including quotes for safety
set SCRIPT_PATH="%SCRIPT_DIR%aeon_fix.py"

:: Set working directory (still good practice, especially for fallback)
cd /d "%SCRIPT_DIR%"

echo.
echo ---------------------------------------------------------
echo       This tool works best with Windows Terminal!
echo ---------------------------------------------------------
echo If you don't have it, download from:
echo https://apps.microsoft.com/detail/9n0dx20hk701
echo.

:: Launch AeonFix using Windows Terminal if available
where wt >nul 2>nul
if %errorlevel%==0 (
    echo Found Windows Terminal. Launching...
    :: Launch WT, telling the cmd inside to run python with the FULL script path
    wt -w 0 nt -p "AeonFix" cmd /k "python %SCRIPT_PATH%"
) else (
    echo Could not detect Windows Terminal. Launching normally...
    :: Launch python directly using the FULL script path
    python %SCRIPT_PATH%
)

pause