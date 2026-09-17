# PyInstaller build spec for Percolate.
#
# Run from the repo root, on whichever OS you want an executable for
# (PyInstaller cannot cross-compile — build on Windows for a .exe, on macOS
# for a .app-less binary, on Linux for an ELF binary):
#
#   pip install pyinstaller
#   pyinstaller percolate.spec
#
# Output lands in dist/percolate/ (onedir build — faster startup than
# onefile, which matters for a TUI you might reopen often; ship the whole
# dist/percolate/ folder together, not just the executable inside it).

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ("percolate/data", "percolate/data"),
    ("percolate/percolate.tcss", "percolate"),
]
datas += collect_data_files("textual")

a = Analysis(
    ["percolate/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="percolate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="percolate",
)
