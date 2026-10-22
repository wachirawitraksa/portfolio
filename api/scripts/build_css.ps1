# Builds the admin stylesheet (app/static/admin.css) from css/input.css with the Tailwind standalone CLI and
# daisyUI. Same job as build_css.sh, for Windows PowerShell. No Node is needed.
#
#   scripts\build_css.ps1            build once
#   scripts\build_css.ps1 -Watch     rebuild on every change
param([switch]$Watch)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Tailwind = "4.3.3"
$DaisyUi = "5.7.50"
$Tools = "tools"
New-Item -ItemType Directory -Force $Tools | Out-Null
$Cli = Join-Path $Tools "tailwindcss-$Tailwind.exe"

function Get-File($Url, $Path) {
    Invoke-WebRequest -Uri $Url -OutFile "$Path.part" -UseBasicParsing
    Move-Item -Force "$Path.part" $Path
}

if (-not (Test-Path $Cli)) {
    Write-Host "Downloading Tailwind CSS $Tailwind ..."
    $base = "https://github.com/tailwindlabs/tailwindcss/releases/download/v$Tailwind"
    Get-File "$base/tailwindcss-windows-x64.exe" $Cli
    # Check the download against the checksum the release publishes.
    $sums = (Invoke-WebRequest -Uri "$base/sha256sums.txt" -UseBasicParsing).Content -split "`n"
    $expected = ($sums | Where-Object { $_ -match "tailwindcss-windows-x64\.exe$" }) -split "\s+" | Select-Object -First 1
    $actual = (Get-FileHash $Cli -Algorithm SHA256).Hash.ToLower()
    if (-not $expected -or $expected -ne $actual) {
        Remove-Item $Cli
        throw "Checksum mismatch for tailwindcss-windows-x64.exe"
    }
}

foreach ($file in "daisyui.mjs", "daisyui-theme.mjs") {
    $target = Join-Path $Tools "$DaisyUi-$file"
    if (-not (Test-Path $target)) {
        Write-Host "Downloading daisyUI $DaisyUi ($file) ..."
        Get-File "https://github.com/saadeghi/daisyui/releases/download/v$DaisyUi/$file" $target
    }
    Copy-Item -Force $target (Join-Path $Tools $file)  # css/input.css names the plain file
}

$arguments = @("-i", "css/input.css", "-o", "app/static/admin.css", "--minify")
if ($Watch) { $arguments += "--watch" }
& $Cli @arguments
