#!/usr/bin/env bash
# Build a standalone single-file executable via Nuitka. Run natively per-OS
# (e.g. once on Windows, once in WSL) — Nuitka can't cross-compile. Output
# lands as dist/<os>/percolate, ready to attach to a release as-is: onefile
# mode means there's no folder to package, unlike the old PyInstaller onedir
# build.
set -e

python_bin=$(command -v python3 || command -v python)
os=$("$python_bin" -c "import platform; print(platform.system().lower())")
distpath="dist/$os"
buildpath="build/$os"

# Kept in sync with pyproject.toml's [project] version by hand — only feeds
# the onefile cache path (see --onefile-cache-mode below), not published
# anywhere.
version="0.1.0"

"$python_bin" -m nuitka --mode=onefile --onefile-cache-mode=cached \
    --assume-yes-for-downloads \
    --company-name=percolate --product-name=percolate --product-version="$version" \
    --output-dir="$buildpath" --output-filename=percolate \
    --include-data-dir=percolate/data=data \
    --include-data-files=percolate/percolate.tcss=percolate.tcss \
    --include-package-data=textual \
    percolate/main.py

mkdir -p "$distpath"
mv "$buildpath/percolate" "$distpath/percolate"
echo "Built $distpath/percolate"
