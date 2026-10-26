# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for LegalSearch Offline Qt (windowed, no console)

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['launcher_qt.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtNetwork',
        'chromadb',
        'chromadb.db.impl.sqlite',
        'chromadb.segment.impl.vector.local_hnsw',
        'chromadb.segment.impl.metadata.sqlite',
        'pypdf',
        'pypdf._reader',
        'requests',
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'streamlit',
        'tornado',
        'altair',
        'pandas',
        'numpy',
        'matplotlib',
        'IPython',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    exclude_binaries=False,
    name='LegalSearchOfflineQt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/legalsearch_icon.ico',
)
