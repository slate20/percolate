# Build a standalone executable for the current OS (see percolate.spec).
# Run natively per-OS (e.g. once on Windows, once in WSL) — PyInstaller
# can't cross-compile. Output lands in dist/<os>/percolate/, packaged
# alongside as dist/<os>/percolate-<os>.zip, ready to attach to a release.
$ErrorActionPreference = "Stop"

$os = (python -c "import platform; print(platform.system().lower())").Trim()
$distpath = "dist/$os"
pyinstaller percolate.spec --distpath $distpath --workpath "build/$os"

$archive = "$distpath/percolate-$os.zip"
if (Test-Path $archive) { Remove-Item $archive }
Compress-Archive -Path "$distpath/percolate" -DestinationPath $archive
Write-Host "Packaged $archive"
