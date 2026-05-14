# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = []
datas += collect_data_files('whisper')
datas += collect_data_files('anthropic')

hiddenimports = [
    'unittest',
    'unittest.mock',
    'anthropic',
    'sounddevice',
    'scipy',
    'scipy.io.wavfile',
    'pyaudio',
    'whisper',
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'numpy',
    'PyQt6',
    'PyQt6.QtWidgets',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'win32com.client',
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'requests',
    'csv',
    'wave',
    'json',
    'socket',
    'subprocess',
]

# Get Python DLL path
python_dll = os.path.join(os.path.dirname(sys.executable), 'python311.dll')
binaries_list = [
    ('hamlib/bin/rigctld.exe', 'hamlib/bin'),
    ('hamlib/bin/libhamlib-4.dll', 'hamlib/bin'),
    ('hamlib/bin/libusb-1.0.dll', 'hamlib/bin'),
    ('hamlib/bin/libgcc_s_seh-1.dll', 'hamlib/bin'),
    ('hamlib/bin/libwinpthread-1.dll', 'hamlib/bin'),
]
if os.path.exists(python_dll):
    binaries_list.insert(0, (python_dll, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HamRadioAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

import shutil
import sys

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HamRadioAI',
)

# Post-build: Copy python311.dll to root folder for runtime access
import shutil
def post_build():
    import os, sys
    python_dll = os.path.join(os.path.dirname(sys.executable), 'python311.dll')
    dist_root = os.path.join('dist', 'HamRadioAI', 'python311.dll')
    if os.path.exists(python_dll):
        try:
            shutil.copy2(python_dll, dist_root)
            print(f"[POST-BUILD] Copied python311.dll to {dist_root}")
        except Exception as e:
            print(f"[POST-BUILD] Warning: Could not copy python311.dll: {e}")

post_build()