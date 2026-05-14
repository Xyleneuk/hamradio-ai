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
set HAMLIB_FOUND=0

REM Check if rigctld is in PATH
where rigctld >nul 2>&1
if not errorlevel 1 (
    set HAMLIB_FOUND=1
    echo [OK] Hamlib found in PATH
    goto HAMLIB_DONE
)

REM Check default installation locations
if exist "C:\Program Files\hamlib-w64-4.7.1\bin\rigctld.exe" (
    set HAMLIB_FOUND=1
    echo [OK] Hamlib found at C:\Program Files\hamlib-w64-4.7.1\
    echo Adding to PATH...
    setx PATH "%PATH%;C:\Program Files\hamlib-w64-4.7.1\bin"
    goto HAMLIB_DONE
)

if exist "C:\Program Files\hamlib\bin\rigctld.exe" (
    set HAMLIB_FOUND=1
    echo [OK] Hamlib found at C:\Program Files\hamlib\
    echo Adding to PATH...
    setx PATH "%PATH%;C:\Program Files\hamlib\bin"
    goto HAMLIB_DONE
)

if exist "C:\Program Files (x86)\hamlib\bin\rigctld.exe" (
    set HAMLIB_FOUND=1
    echo [OK] Hamlib found at C:\Program Files (x86)\hamlib\
    echo Adding to PATH...
    setx PATH "%PATH%;C:\Program Files (x86)\hamlib\bin"
    goto HAMLIB_DONE
)

:HAMLIB_DONE
if %HAMLIB_FOUND%==0 (
    echo [WARNING] Hamlib not found!
    echo.
    echo Please install Hamlib:
    echo 1. Download from: https://hamlib.sourceforge.io/
    echo 2. Run hamlib-w64-4.7.1.exe installer
    echo 3. Use default installation path
    echo 4. Restart this script after installation
    echo.
    pause
) else (
    echo [OK] Hamlib is ready
)

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
