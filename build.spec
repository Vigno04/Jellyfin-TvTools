# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Jellyfin TV Tools
Generates standalone executables for Windows and Linux
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Flet data files
flet_datas = collect_data_files('flet')
flet_hiddenimports = collect_submodules('flet')

# Application data files to include
datas = [
    ('src/config.json', 'src'),
    ('src/requirements.txt', 'src'),
]

# Add Flet data files
datas.extend(flet_datas)

# Hidden imports - all modules that might be loaded dynamically
hiddenimports = [
    'flet',
    'flet.core',
    'flet.auth',
    'flet.fastapi',
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    'certifi',
    'httpx',
    'websockets',
    'typing_extensions',
] + flet_hiddenimports

# Analysis - find all dependencies
a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='JellyfinTvTools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'icon.ico'
)
