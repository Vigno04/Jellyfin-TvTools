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
    ('src/backend', 'src/backend'),  # Include backend directory
    ('src/ui', 'src/ui'),  # Include ui directory
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
    # Project modules
    'ui',
    'ui.main_app',
    'ui.channels_mixin',
    'ui.export_import_mixin',
    'ui.manual_merge_mixin',
    'ui.optimization_mixin',
    'ui.playlist_mixin',
    'ui.session_manager',
    'ui.session_status_mixin',
    'ui.settings_mixin',
    'ui.ui_update_helper',
    'ui.async_utils',
    'ui.channel_list',
    'ui.group_manager',
    'backend',
    'backend.config_manager',
    'backend.m3u_processor',
    'backend.quality_manager',
    'backend.stream_quality_checker',
    'backend.m3u',
    'backend.m3u.dead_check',
    'backend.m3u.downloader',
    'backend.m3u.exporter',
    'backend.m3u.filters',
    'backend.m3u.parser',
    'backend.m3u.quality_merge',
] + flet_hiddenimports

# Analysis - find all dependencies
a = Analysis(
    ['run.py'],
    pathex=['src'],  # Add src to Python path
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],  # Look for hooks in current directory
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
