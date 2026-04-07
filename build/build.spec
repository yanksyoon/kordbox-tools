# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for CDJ Audio Toolkit.

Usage:
    # macOS (one-dir mode — recommended for FFmpeg bundling)
    pyinstaller build/build.spec

    # Or directly:
    pyinstaller --onedir --windowed --name "CDJAudioToolkit" \
        --add-data "ffmpeg/darwin:ffmpeg/darwin" \
        --icon=assets/icon.icns \
        gui/app.py

This spec file automates the build with bundled FFmpeg binaries.
"""

import platform
import sys
from pathlib import Path

a = Analysis(
    ['gui/app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'src',
        'src.cli',
        'src.config',
        'src.compatibility',
        'src.backup',
        'src.converter',
        'src.metadata',
        'src.utils',
        'gui',
        'gui.theme',
        'gui.app',
        'gui.tabs',
        'gui.tabs.check_tab',
        'gui.tabs.backup_tab',
        'gui.tabs.convert_tab',
        'gui.components',
        'PySide6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'email',
        'xml',
        'pydoc',
    ],
    noarchive=False,
)

# Determine platform-specific FFmpeg directory
system = platform.system().lower()
if system == 'darwin':
    plat_dir = 'darwin'
elif system == 'windows':
    plat_dir = 'win32'
elif system == 'linux':
    plat_dir = 'linux'
else:
    plat_dir = system

# Add FFmpeg binaries if available
ffmpeg_dir = Path(__file__).resolve().parent.parent / 'ffmpeg' / plat_dir
if ffmpeg_dir.is_dir():
    ffmpeg_files = []
    for f in ffmpeg_dir.iterdir():
        if f.is_file():
            ffmpeg_files.append((str(f), str(f.name)))
    if ffmpeg_files:
        a.datas.extend(ffmpeg_files)
        print(f"Bundling FFmpeg from: {ffmpeg_dir}")
        print(f"  Files: {[f[1] for f in ffmpeg_files]}")
    else:
        print(f"WARNING: No FFmpeg binaries found in {ffmpeg_dir}")
        print("  Run: python build/bundle_ffmpeg.py --from-system")
else:
    print(f"WARNING: FFmpeg directory not found: {ffmpeg_dir}")
    print("  The app will require ffmpeg to be installed on the system PATH.")
    print("  Run: python build/bundle_ffmpeg.py --from-system")

# Platform-specific settings
if system == 'darwin':
    app = BUNDLE(
        a,
        name='CDJAudioToolkit',
        icon=None,  # Set to 'assets/icon.icns' when available
        bundle_identifier='com.kordbox.cdj-audio-toolkit',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
        target_arch='universal2',
    )
elif system == 'windows':
    exe = EXE(
        a,
        name='CDJAudioToolkit',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        icon=None,  # Set to 'assets/icon.ico' when available
    )
else:
    # Linux: one-dir
    coll = COLLECT(
        a,
        name='cdj-audio-toolkit',
        strip=False,
        upx=True,
        upx_exclude=[],
    )
