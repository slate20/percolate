#!/usr/bin/env bash
# Build a standalone executable for the current OS (see percolate.spec).
# Run natively per-OS (e.g. once on Windows, once in WSL) — PyInstaller
# can't cross-compile. Output lands in dist/<os>/percolate/, packaged
# alongside as dist/<os>/percolate-<os>.tar.gz, ready to attach to a release.
set -e

python_bin=$(command -v python3 || command -v python)
os=$("$python_bin" -c "import platform; print(platform.system().lower())")
distpath="dist/$os"
pyinstaller percolate.spec --distpath "$distpath" --workpath "build/$os"

archive="$distpath/percolate-$os.tar.gz"
tar -czf "$archive" -C "$distpath" percolate
echo "Packaged $archive"
