# SPDX-License-Identifier: MPL-2.0
# Builds the probe jar, then starts the three node cluster and the control container.
. "$PSScriptRoot\lib.ps1"
$env:JAVA_HOME = (& mise where java)
if (-not (Test-Path (Join-Path $Spike 'target\probes.jar'))) {
    Push-Location $Spike
    & mise exec -- mvn -q -B package
    Pop-Location
}
Start-Cluster
Start-Ctl
Set-Skew
Invoke-Docker exec msa-i9-rmq1 rabbitmqctl cluster_status
Invoke-Docker exec msa-i9-rmq1 rabbitmqctl version
