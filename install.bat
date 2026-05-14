@echo off
REM Ham Radio AI - Windows Installation Script

echo.
echo ========================================
echo Ham Radio AI - Installation Script
echo ========================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Git
echo Checking Git installation...
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found!
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)
echo [OK] Git found

REM Check Hamlib
echo Checking Hamlib installation...
where rigctld >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Hamlib not found in PATH
    echo Download from: https://hamlib.sourceforge.io/
    echo Install hamlib-w64-4.7.1.exe or later
    pause
)
echo [OK] Hamlib check complete

REM Upgrade pip and install build tools
echo.
echo Installing/upgrading pip, wheel, setuptools...
python -m pip install --upgrade pip wheel setuptools

REM Install requirements
echo.
echo Installing Python dependencies...
echo This may take a few minutes...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed!
    echo.
    echo If PyAudio failed, try:
    echo 1. Install Visual Studio C++ Build Tools from:
    echo    https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo 2. Then run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To run the app:
echo   python main.py
echo.
pause
