# Shared settings for track D's prover spike (formal-methods-phase-0.md).
# Dot-source this file: . .\env-common.ps1
#
# Native toolchains live outside the repository, under $LATTICE_FORMAL_ROOT (epic E6). On the
# machine this spike first ran on, the general toolchain-feasibility spike
# (.local/formal-methods-spike/) already installed opam, Rocq, GHC and Isabelle under C:\fmx and
# %LOCALAPPDATA%\fm-experiment. This file defaults to those locations so the spike reuses them
# without reinstalling; a fresh host sets LATTICE_FORMAL_ROOT (and, if its opam root must sit
# elsewhere, LATTICE_FORMAL_OPAMROOT) to its own outside-repository path instead.
#
# Build outputs that are not toolchain distributions (compiled theories, extracted sources,
# image build contexts, logs) stay under .build/formal/ and .local/formal/ inside the repository,
# both git-ignored (epic E6, plan §7.3).

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$FmxBuild = Join-Path $RepoRoot '.build\formal'
$FmxLocal = Join-Path $RepoRoot '.local\formal'

# Native toolchain root: LATTICE_FORMAL_ROOT first, then the existing spike's FMX_ROOT, then its
# fixed default, so this file is a drop-in continuation of the toolchain-feasibility spike's scripts.
$FmxRoot      = if ($env:LATTICE_FORMAL_ROOT) { $env:LATTICE_FORMAL_ROOT } elseif ($env:FMX_ROOT) { $env:FMX_ROOT } else { 'C:\fmx' }
$FmxDownloads = if ($env:FMX_DOWNLOADS) { $env:FMX_DOWNLOADS } else { Join-Path $FmxRoot 'downloads' }
$FmxOpamRoot  = if ($env:LATTICE_FORMAL_OPAMROOT) { $env:LATTICE_FORMAL_OPAMROOT }
                elseif ($env:FMX_OPAMROOT) { $env:FMX_OPAMROOT }
                else { Join-Path "$env:LOCALAPPDATA\fm-experiment" 'opamroot' }
$FmxSwitch    = if ($env:FMX_SWITCH)    { $env:FMX_SWITCH }    else { 'fm' }
$FmxGhcupBase = if ($env:FMX_GHCUP)     { $env:FMX_GHCUP }     else { $FmxRoot }
$FmxCabalDir  = if ($env:FMX_CABAL_DIR) { $env:FMX_CABAL_DIR } else { Join-Path $FmxRoot 'cabal' }
$FmxIsabelle  = if ($env:FMX_ISABELLE)  { $env:FMX_ISABELLE }  else { Join-Path $FmxRoot 'Isabelle2025-2' }

$FmxOpamExe   = Join-Path $FmxDownloads 'opam.exe'

function New-FmxDirectory([string] $Path) {
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Force $Path | Out-Null }
}
New-FmxDirectory $FmxBuild
New-FmxDirectory $FmxLocal

# Puts the opam switch on PATH for native Windows OCaml and Rocq.
# opam's own Cygwin bin must come before Git for Windows' usr\bin. Otherwise ocamlopt cannot
# find the mingw assembler, or flexlink resolves paths with MSYS cygpath and fails to link.
function Enable-FmxRocq {
    $env:OPAMROOT = $FmxOpamRoot
    $lines = & $FmxOpamExe env "--switch=$FmxSwitch" --shell=powershell
    foreach ($line in ($lines -split "`r?`n")) { if ($line) { Invoke-Expression $line } }
    $cygwinBin = Join-Path $FmxOpamRoot '.cygwin\root\bin'
    $switchBin = Join-Path $FmxOpamRoot "$FmxSwitch\bin"
    $rest = ($env:Path -split ';') | Where-Object { $_ -and $_ -ne $cygwinBin -and $_ -ne $switchBin }
    $env:Path = (@($switchBin, $cygwinBin) + $rest) -join ';'
}

function Enable-FmxHaskell {
    $env:GHCUP_INSTALL_BASE_PREFIX = $FmxGhcupBase
    $env:GHCUP_SKIP_UPDATE_CHECK = '1'
    $env:CABAL_DIR = $FmxCabalDir
    $bin = Join-Path $FmxGhcupBase 'ghcup\bin'
    if (($env:Path -split ';') -notcontains $bin) { $env:Path = "$bin;$env:Path" }
}

# Runs a bash command line inside Isabelle's bundled Cygwin. Use Cygwin paths, for example
# /cygdrive/c/fmx/work/isa. Returns the command's output lines.
function Invoke-FmxIsabelleBash([string] $Command) {
    $bash = Join-Path $FmxIsabelle 'contrib\cygwin\bin\bash.exe'
    $env:CHERE_INVOKING = 'true'
    & $bash --login -c $Command 2>&1
}

function ConvertTo-FmxCygwinPath([string] $WindowsPath) {
    $full = [IO.Path]::GetFullPath($WindowsPath)
    '/cygdrive/' + $full.Substring(0, 1).ToLower() + ($full.Substring(2) -replace '\\', '/')
}

# A proxy that intercepts TLS re-signs it. Containers trust it only if its root CA is copied in.
# NODE_EXTRA_CA_CERTS names the CA file at user level on the test machine.
function Get-FmxExtraCa {
    $ca = [Environment]::GetEnvironmentVariable('NODE_EXTRA_CA_CERTS', 'User')
    if (-not $ca) { $ca = $env:NODE_EXTRA_CA_CERTS }
    if (-not $ca -or -not (Test-Path $ca)) { return $null }
    $ca
}
