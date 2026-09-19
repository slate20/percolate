# PyInstaller build spec for Percolate.
#
# Run from the repo root, on whichever OS you want an executable for
# (PyInstaller cannot cross-compile — build on Windows for a .exe, on macOS
# for a .app-less binary, on Linux for an ELF binary):
#
#   pip install pyinstaller
#   pyinstaller percolate.spec --distpath dist/<os> --workpath build/<os>
#
# The --distpath/--workpath flags (e.g. dist/windows, dist/linux) keep a
# Windows build and a WSL/Linux build of the same checkout from overwriting
# each other. They have to be passed on the command line, not set from
# inside the spec: COLLECT/EXE read their output location from PyInstaller's
# internal CONF['distpath']/CONF['workpath'], not from spec-local variables,
# so reassigning DISTPATH/workpath in this file has no effect on where the
# build actually lands.
#
# Output lands in dist/<os>/percolate/ (onedir build — faster startup than
# onefile, which matters for a TUI you might reopen often; ship the whole
# percolate/ folder together, not just the executable inside it).

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
