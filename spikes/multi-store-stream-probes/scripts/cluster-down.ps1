# SPDX-License-Identifier: MPL-2.0
# Removes every container named msa-i9-* with its volumes, and the network msa-i9-net. Touches nothing else.
. "$PSScriptRoot\lib.ps1"
Stop-Spike
Write-Host 'containers left:'
Invoke-Docker ps -a --filter 'name=msa-i9-' --format '{{.Names}}'
Write-Host 'networks left:'
Invoke-Docker network ls --filter 'name=msa-i9-' --format '{{.Name}}'
