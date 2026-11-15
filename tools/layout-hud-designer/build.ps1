# ---------------------------------------------------------------------
# KrydenLayoutHudDesigner - packs the Client PBO with a prefix lock.
#
# Reference for the exact command and the guards. Run it yourself when you
# want a PBO; it is not part of any automated flow.
#
# Guards that are NOT optional:
#   -P               without it MakePbo stops at "Press the ANY key"
#   no 2>&1          in Windows PowerShell 5.1, redirecting stderr of a native
#                    exe turns into NativeCommandError and kills a build that
#                    succeeded
#   check the .pbo   MakePbo exits 0 without packing when it gets an invalid
#                    flag; the exit code proves nothing
#   check prefix     a prefix different from the paths in config.cpp = the mod
#                    loads ZERO files, without one line of log. The prefix here
#                    is multi-segment (Kryden\KrydenLayoutHudDesigner\KrydenLayoutHudDesigner_Client)
#                    ON PURPOSE: it equals $PBOPREFIX$ and every path in config.cpp.
#
# Requires Mikero DePboTools (MakePbo, ExtractPbo). Generate the atlas texture
# first (python tools/gen_atlas.py): without gui/textures/kld_ui_atlas.paa the
# rounded styles have no texture.
# ---------------------------------------------------------------------
param(
    [switch]$NoDeploy,
    [string]$ServerRoot = "C:\Program Files (x86)\Steam\steamapps\common\DayZServer"
)

$ErrorActionPreference = "Stop"

$Root       = $PSScriptRoot
$ModName    = "KrydenLayoutHudDesigner"
$MakePbo    = "C:\Program Files (x86)\Mikero\DePboTools\bin\MakePbo.exe"
$ExtractPbo = "C:\Program Files (x86)\Mikero\DePboTools\bin\ExtractPbo.exe"
$BuildDir   = Join-Path $Root "build"

if (-not (Test-Path $MakePbo))    { throw "MakePbo not found at: $MakePbo" }
if (-not (Test-Path $ExtractPbo)) { throw "ExtractPbo not found at: $ExtractPbo (the prefix lock depends on it)" }

$atlas = Join-Path $Root "${ModName}_Client\gui\textures\kld_ui_atlas.paa"
if (-not (Test-Path $atlas)) { throw "Missing $atlas. Run: python tools/gen_atlas.py" }

if (-not $NoDeploy) {
    $blockers = @(Get-Process -Name DayZServer_x64, DayZ_x64 -ErrorAction Ignore)
    if ($blockers.Count -gt 0) {
        $names = ($blockers | Select-Object -ExpandProperty ProcessName -Unique) -join ", "
        throw "Close before deploying: $names (the process keeps the PBO open)"
    }
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

function Build-Pbo {
    param(
        [string]$Folder,     # <mod>_Client
        [string]$PboName,    # KrydenLayoutHudDesigner_Client
        [string]$DeployTo    # addons folder of the @mod on the test server
    )

    $source = Join-Path $Root $Folder
    if (-not (Test-Path $source)) { throw "Source folder does not exist: $source" }

    # Expected prefix = content of $PBOPREFIX$ = prefix used by every path in config.cpp.
    $expected = "Kryden\$ModName\$Folder"
    $prefixFile = Join-Path $source '$PBOPREFIX$'
    if (-not (Test-Path $prefixFile)) { throw "Missing `$PBOPREFIX`$ in $source" }
    $declared = (Get-Content $prefixFile -Raw).Trim()
    if ($declared -ne $expected) {
        throw "`$PBOPREFIX`$ of $Folder says '$declared', but the expected prefix is '$expected'. One of them is wrong."
    }

    $pbo = Join-Path $BuildDir "$PboName.pbo"
    if (Test-Path $pbo) { Remove-Item $pbo -Force }

    Write-Host "[build]  $PboName  (prefix $expected)" -ForegroundColor Cyan
    & $MakePbo -P "-@=$expected" $source $pbo

    # MakePbo's exit code is not reliable. The file is the proof.
    if (-not (Test-Path $pbo)) { throw "MakePbo did not produce the PBO: $pbo" }

    $listing = & $ExtractPbo -P -L $pbo
    $prefixLine = $listing | Where-Object { $_ -match "^prefix=" } | Select-Object -First 1
    if (-not $prefixLine) { throw "ExtractPbo did not return the prefix= line for $pbo" }
    $actual = ($prefixLine -replace "^prefix=", "").Trim()
    if ($actual -ne $expected) {
        Remove-Item $pbo -Force
        throw "Wrong prefix in ${PboName}: expected '$expected', got '$actual'. PBO discarded."
    }
    Write-Host "[prefix] $actual" -ForegroundColor DarkGray

    if ($NoDeploy) {
        Write-Host "[ok]     $pbo" -ForegroundColor Green
        return
    }

    New-Item -ItemType Directory -Force -Path $DeployTo | Out-Null
    Copy-Item $pbo -Destination $DeployTo -Force
    Write-Host "[deploy] $DeployTo\$PboName.pbo" -ForegroundColor Green
}

Build-Pbo -Folder "${ModName}_Client" -PboName "${ModName}_Client" -DeployTo (Join-Path $ServerRoot "@$ModName\addons")

Write-Host ""
Write-Host "Test server: -mod=@$ModName (the client loads the same @$ModName)" -ForegroundColor Yellow
Write-Host "Acceptance: script_*.log without any SCRIPT (E) - necessary, never sufficient." -ForegroundColor Yellow
