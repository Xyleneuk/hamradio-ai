# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = (
    collect_data_files('whisper') +
    collect_data_files('anthropic') +
    collect_data_files('tiktoken')
)

hiddenimports = [
    'anthropic', 'sounddevice', 'scipy', 'scipy.signal', 'pyaudio',
    'whisper', 'tiktoken', 'tiktoken_ext', 'tiktoken_ext.openai_public',
    'numpy', 'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
    'win32com.client', 'win32com', 'pyttsx3', 'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5', 'serial', 'serial.tools', 'serial.tools.list_ports',
    'comtypes', 'numba', 'llvmlite',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(r'hamlib\bin\*.exe', r'hamlib\bin'),
              (r'hamlib\bin\*.dll', r'hamlib\bin')],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HamRadioAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='assets/icon.ico',
    version_file=None,
)
