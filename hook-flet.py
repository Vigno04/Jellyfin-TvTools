# PyInstaller hook for Flet
# This ensures all Flet dependencies are properly included

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all Flet modules and data files
datas, binaries, hiddenimports = collect_all('flet')

# Add additional hidden imports that might be missed
hiddenimports += [
    'flet.core',
    'flet.auth',
    'flet.fastapi',
    'flet.utils',
    'httpx',
    'websockets',
    'typing_extensions',
    'certifi',
    'charset_normalizer',
    'idna',
]

# Collect all submodules
hiddenimports += collect_submodules('flet')
hiddenimports += collect_submodules('httpx')
hiddenimports += collect_submodules('websockets')
