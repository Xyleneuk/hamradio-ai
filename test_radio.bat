@echo off
REM Test rigctld on new laptop
REM Usage: test_radio.bat [COM_PORT] [BAUD_RATE]
REM Example: test_radio.bat COM7 9600

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: test_radio.bat COM_PORT BAUD_RATE
    echo Example: test_radio.bat COM7 9600
    echo.
    echo Testing default: COM7 at 9600 baud...
    set COM_PORT=COM7
    set BAUD_RATE=9600
) else (
    set COM_PORT=%1
    set BAUD_RATE=%2
    if "!BAUD_RATE!"=="" set BAUD_RATE=9600
)

echo.
echo ============================================================
echo Testing rigctld on !COM_PORT! at !BAUD_RATE! baud
echo ============================================================
echo.

python test_rigctld.py !COM_PORT! !BAUD_RATE!

pause
