"""
Build script for Ham Radio AI Windows installer.
Requires:
  - PyInstaller: pip install pyinstaller
  - Inno Setup 6: https://jrsoftware.org/isdl.php

Run this script to build the full Windows installer.
"""

import os
import subprocess
import sys
import shutil

APP_NAME    = 'HamRadioAI'
APP_VERSION = '1.2.0'
INNO_SETUP  = r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'


def build_exe():
    """Build the executable with PyInstaller"""
    print("=" * 50)
    print("Step 1: Building executable with PyInstaller...")
    print("=" * 50)

    result = subprocess.run(
        ['pyinstaller', 'hamradio_ai.spec', '--clean', '--noconfirm'],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(1)

    print("PyInstaller build complete!")


def build_installer():
    """Build the Windows installer with Inno Setup"""
    print("\n" + "=" * 50)
    print("Step 2: Building Windows installer with Inno Setup...")
    print("=" * 50)

    if not os.path.exists(INNO_SETUP):
        print(f"Inno Setup not found at: {INNO_SETUP}")
        print("Download from: https://jrsoftware.org/isdl.php")
        print("Skipping installer build - exe is in dist/HamRadioAI/")
        return

    iss_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'hamradio_ai.iss'
    )

    result = subprocess.run([INNO_SETUP, iss_file])
    if result.returncode != 0:
        print("Inno Setup build failed!")
        sys.exit(1)

    print("Installer build complete!")
    print(f"Installer saved to: installer/output/HamRadioAI_Setup_{APP_VERSION}.exe")


if __name__ == '__main__':
    build_exe()
    build_installer()