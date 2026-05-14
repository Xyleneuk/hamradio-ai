# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = collect_data_files('whisper') + collect_data_files('anthropic')

hiddenimports = [
    'anthropic', 'sounddevice', 'scipy', 'pyaudio', 'whisper',
    'tktoken', 'numpy', 'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore',
    'PyQt6.QtGui', 'win32com.client', 'pyttsx3', 'serial',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('hamlib/bin/rigctld.exe', 'hamlib/bin')],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='HamRadioAI', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False, icon='assets/icon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='HamRadioAI',
)
