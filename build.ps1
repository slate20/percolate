# Build a standalone single-file executable via Nuitka. Run natively per-OS
# (e.g. once on Windows, once in WSL) — Nuitka can't cross-compile. Output
# lands as dist/<os>/percolate.exe, ready to attach to a release as-is:
# onefile mode means there's no folder to package, unlike the old
# PyInstaller onedir build.
$ErrorActionPreference = "Stop"

$os = (python -c "import platform; print(platform.system().lower())").Trim()
$distpath = "dist/$os"
$buildpath = "build/$os"

# Kept in sync with pyproject.toml's [project] version by hand — only feeds
# the onefile cache path (see --onefile-cache-mode below), not published
# anywhere.
$version = "0.1.0"

python -m nuitka --mode=onefile --onefile-cache-mode=cached `
    --assume-yes-for-downloads `
    --company-name=percolate --product-name=percolate --product-version=$version `
    --output-dir=$buildpath --output-filename=percolate `
    --include-data-dir=percolate/data=data `
    --include-data-files=percolate/percolate.tcss=percolate.tcss `
    --include-package-data=textual `
    percolate/main.py

New-Item -ItemType Directory -Force -Path $distpath | Out-Null
Move-Item -Force "$buildpath/percolate.exe" "$distpath/percolate.exe"
Write-Host "Built $distpath/percolate.exe"
