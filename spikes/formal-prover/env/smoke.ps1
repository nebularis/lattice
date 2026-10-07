# The track D smoke suite (mise task check:formal-smoke): confirms both tools run on the routes
# this machine supports, before anything in spikes/formal-prover/rocq or /isabelle is trusted.
# Isabelle has no image route in this spike (epic §4: a native bundle everywhere, image route is
# Rocq/MetaRocq/GHC-wasm only), so Isabelle is checked natively only.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'env-common.ps1')

$results = [ordered]@{}

function Invoke-Check([string] $Name, [scriptblock] $Body) {
    # Native-command stderr lines captured via 2>&1 become terminating errors under
    # $ErrorActionPreference = 'Stop' (they are the driver's own "+ ..." trace lines, not
    # failures), so relax it for the duration of the call and read $LASTEXITCODE for the
    # real result.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Body 2>&1
        $results[$Name] = if ($LASTEXITCODE -ne 0) { "FAIL (exit $LASTEXITCODE)" } else { 'ok' }
        $out | Select-Object -Last 2 | ForEach-Object { "   $_" }
    } catch {
        $results[$Name] = "FAIL ($_)"
    } finally {
        $ErrorActionPreference = $previous
    }
}

"== rocq, native route"
Invoke-Check 'rocq-native' { python (Join-Path $PSScriptRoot 'driver.py') --route native rocq -- rocq --version }

"== rocq, image route"
Invoke-Check 'rocq-image' { python (Join-Path $PSScriptRoot 'driver.py') --route image rocq -- rocq --version }

"== rocq-metarocq, image route"
Invoke-Check 'rocq-metarocq-image' { python (Join-Path $PSScriptRoot 'driver.py') --route image rocq-metarocq -- opam list rocq-metarocq-template --short }

"== isabelle, native route"
Invoke-Check 'isabelle-native' { python (Join-Path $PSScriptRoot 'driver.py') --route native isabelle -- version }

''
'Results'
$results.GetEnumerator() | ForEach-Object { '  {0,-24} {1}' -f $_.Key, $_.Value }
if ($results.Values -match '^FAIL') { exit 1 }
