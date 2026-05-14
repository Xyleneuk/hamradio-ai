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

import sys
python_dll_path = os.path.join(os.path.dirname(sys.executable), 'python311.dll')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        (python_dll_path, '.'),
        ('hamlib/bin/rigctld.exe', 'hamlib/bin'),
        ('hamlib/bin/libhamlib-4.dll', 'hamlib/bin'),
        ('hamlib/bin/libusb-1.0.dll', 'hamlib/bin'),
        ('hamlib/bin/libgcc_s_seh-1.dll', 'hamlib/bin'),
        ('hamlib/bin/libwinpthread-1.dll', 'hamlib/bin'),
    ],
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