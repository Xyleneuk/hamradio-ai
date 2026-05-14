# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('whisper') + collect_data_files('anthropic')
hiddenimports = ['anthropic', 'sounddevice', 'scipy', 'pyaudio', 'whisper',
    'tiktoken', 'numpy', 'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore',
    'PyQt6.QtGui', 'win32com.client', 'pyttsx3', 'serial']

a = Analysis(['main.py'], pathex=[], binaries=[('hamlib/bin/rigctld.exe', '.')],
    datas=datas, hiddenimports=hiddenimports, hookspath=[], runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'], win_no_prefer_redirects=False,
    cipher=None, noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [], name='HamRadioAI',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, icon='assets/icon.ico')
