@echo off
title AeonFix Installer
cd /d "%~dp0"
echo.
echo ---------------------------------------------------------
echo        Installing AeonFix dependencies via pip          
echo ---------------------------------------------------------

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 is required. Please install it from:
    echo https://www.python.org/downloads/
    pause
    exit /b
)

:: Install dependencies
python -m pip install --upgrade pip
pip install rich psutil ollama

:: Check if Ollama is installed
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo Ollama is not installed. Please download it from:
    echo https://ollama.com/download
    start https://ollama.com/download
) else (
    echo.
    echo Ollama detected.
)

echo.
echo You can now run AeonFix using the launch_aeonfix.bat script.
pause
