# Installs Isabelle natively on Windows without running the GUI installer (mise task
# bootstrap:formal-native-isabelle). macOS and Linux use install_native.py.
# Re-runnable. Timings on the test machine (2026-10-06): download 1 min (1.07 GB),
# extraction 2.5 min, first-run Cygwin initialisation under 1 min.

. (Join-Path $PSScriptRoot 'env-common.ps1')
New-FmxDirectory $FmxDownloads

$archive = Join-Path $FmxDownloads "$FmxIsabelleName.exe"
if (-not (Test-Path $archive)) {
    curl.exe -sSL --fail -o $archive $FmxIsabelleUrl
    if ($LASTEXITCODE -ne 0) { throw "Isabelle download failed: $FmxIsabelleUrl" }
}

if (-not (Test-Path (Join-Path $FmxIsabelle 'bin\isabelle'))) {
    # The installer is a 7-Zip self-extracting archive. 7z extracts it without a GUI.
    $sevenZip = (Get-Command 7z -ErrorAction SilentlyContinue).Source
    if (-not $sevenZip) { throw '7z not found (on the test machine it comes from scoop)' }
    $parent = Split-Path $FmxIsabelle -Parent
    & $sevenZip x -y "-o$parent" $archive | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { throw '7z extraction failed' }
}

# Isabelle initialises its bundled Cygwin (symlinks, rebase, postinstall) the first time any
# of its Java entry points runs, and removes contrib\cygwin\isabelle\uninitialized when done.
# The setup jar is such an entry point. Its "classpath" operation then fails with a
# NoClassDefFoundError, which is harmless: the initialisation has already happened.
$marker = Join-Path $FmxIsabelle 'contrib\cygwin\isabelle\uninitialized'
if (Test-Path $marker) {
    $java = Get-ChildItem (Join-Path $FmxIsabelle 'contrib') -Directory -Filter 'jdk-*' |
        ForEach-Object { Join-Path $_.FullName 'x86_64-windows\bin\java.exe' } | Select-Object -First 1
    $setupJar = Get-ChildItem (Join-Path $FmxIsabelle 'contrib') -Directory -Filter 'isabelle_setup-*' |
        ForEach-Object { Join-Path $_.FullName 'lib\isabelle_setup.jar' } | Select-Object -First 1
    Push-Location $FmxIsabelle
    try {
        $ErrorActionPreference = 'Continue'
        & $java "-Disabelle.root=$FmxIsabelle" -cp $setupJar isabelle.setup.Setup classpath 2>&1 | Out-Null
        $ErrorActionPreference = 'Stop'
    } finally { Pop-Location }
    if (Test-Path $marker) { throw 'Isabelle Cygwin initialisation did not run' }
}

Invoke-FmxIsabelleBash "$(ConvertTo-FmxCygwinPath $FmxIsabelle)/bin/isabelle version"
