# Installs opam, an OCaml switch, Rocq, dune, ppxlib and js_of_ocaml natively on Windows (mise
# task bootstrap:formal-native-rocq). macOS and Linux use install_native.py.
# Re-runnable: each step is skipped when its result already exists.
# Timings on the test machine (2026-10-06): opam init 7 min, OCaml switch 34 min, Rocq and
# the rest over an hour, most of it in Cygwin process start-up.
param([string[]] $Packages = @('rocq-prover', 'dune', 'ppxlib', 'js_of_ocaml-compiler'))

. (Join-Path $PSScriptRoot 'env-common.ps1')
New-FmxDirectory $FmxDownloads

if (-not (Test-Path $FmxOpamExe)) {
    $url = "https://github.com/ocaml/opam/releases/download/$FmxOpamVersion/opam-$FmxOpamVersion-x86_64-windows.exe"
    curl.exe -sSL --fail -o $FmxOpamExe $url
    if ($LASTEXITCODE -ne 0) { throw "opam download failed: $url" }
}
& $FmxOpamExe --version

$env:OPAMROOT = $FmxOpamRoot
$env:OPAMYES = '1'
# Lets opam install system packages (for example GMP for zarith) into its own Cygwin.
$env:OPAMCONFIRMLEVEL = 'unsafe-yes'

if (-not (Test-Path (Join-Path $FmxOpamRoot 'config'))) {
    # opam installs a private Cygwin for its build tools and the mingw-w64 compiler.
    # The flag is marked experimental and prints a warning, which is expected.
    & $FmxOpamExe init --bare --no-setup --cygwin-internal-install -y
    if ($LASTEXITCODE -ne 0) { throw 'opam init failed' }
}

$switches = & $FmxOpamExe switch list --short
if ($switches -notcontains $FmxSwitch) {
    & $FmxOpamExe switch create $FmxSwitch $FmxOcamlVersion -y
    if ($LASTEXITCODE -ne 0) { throw 'opam switch create failed' }
}

$repos = & $FmxOpamExe repo list "--switch=$FmxSwitch" --short
if ($repos -notcontains 'rocq-released') {
    & $FmxOpamExe repo add rocq-released https://rocq-prover.org/opam/released "--switch=$FmxSwitch"
}

& $FmxOpamExe install "--switch=$FmxSwitch" @Packages -y
if ($LASTEXITCODE -ne 0) { throw 'opam install failed' }

Enable-FmxRocq
ocamlopt -version
rocq --version
