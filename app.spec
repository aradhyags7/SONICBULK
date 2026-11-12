# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None

project_dir = Path.cwd()
src_dir = str(project_dir / 'src')

a = Analysis(
    ['src/app/__main__.py'],
    pathex=[src_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        'aiosqlite',
        'aiohttp',
        'mutagen',
        'mutagen.mp3',
        'mutagen.mp4',
        'mutagen.flac',
        'mutagen.oggopus',
        'mutagen.oggvorbis',
        'pdfplumber',
        'pypdf',
        'docx',
        'rapidfuzz',
        'psutil',
        'yt_dlp',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MusicDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Allows headless CLI output as well as GUI execution
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
