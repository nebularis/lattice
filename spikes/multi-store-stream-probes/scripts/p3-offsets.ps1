# SPDX-License-Identifier: MPL-2.0
# Probe P3a: a crash of the only consumer of a super stream, at a chosen point of a batch, then a restart under a new id.
#   .\p3-offsets.ps1 -Run p3-before-store -Point before-store -DieAtBatch 3
#   .\p3-offsets.ps1 -Run p3-after-store -Point after-store -DieAtBatch 3
#   .\p3-offsets.ps1 -Run p3-kill -Point kill -KillAfterS 4      (docker kill at a given time instead of a halt in the worker)
param(
    [Parameter(Mandatory)][string]$Run,
    [ValidateSet('before-apply', 'before-store', 'after-store', 'kill')][string]$Point = 'before-store',
    [int]$DieAtBatch = 3,
    [int]$KillAfterS = 4,
    [int]$Rate = 150,
    [int]$PublishS = 8,
    [int]$BatchMs = 100,
    [int]$MessageMs = 3,
    [int]$ObserveS = 20,
    [int]$PauseMs = 0,
    [ValidateSet('context', 'env')][string]$StoreVia = 'context',
    [switch]$DebugClient
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"

$dir = Join-Path $Results $Run
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
New-Item -ItemType Directory -Force $dir | Out-Null
$super = "msa-i9-o-$($Run -replace '[^a-z0-9]', '')"
$partitions = 8
$ids = @('c1', 'c2', 'pub')
Remove-Clients $ids
New-SuperStream $super $partitions
$uri = 'rabbitmq-stream://guest:guest@msa-i9-rmq1:5552'
$base = @('--super', $super, '--uris', $uri, '--batch-ms', $BatchMs, '--message-ms', $MessageMs, '--store-via', $StoreVia)
$dockerOptions = @()
if ($DebugClient) { $dockerOptions = @('-e', 'JAVA_TOOL_OPTIONS=-Dorg.slf4j.simpleLogger.defaultLogLevel=info -Dorg.slf4j.simpleLogger.log.com.rabbitmq.stream=debug') }

try {
    Write-Harness $dir note harness "run $Run point $Point dieAtBatch $DieAtBatch rate $Rate publish $PublishS s"
    Start-Client $Run pub publish @('--super', $super, '--amqp', 'msa-i9-rmq1', '--rate', $Rate, '--duration-s', $PublishS)
    $null = Wait-Until { (Invoke-Docker inspect -f '{{.State.Running}}' msa-i9-pub) -join '' -eq 'false' } ($PublishS + 40) 1

    $c1Options = $base
    if ($Point -ne 'kill') { $c1Options = $base + @('--die-at-batch', $DieAtBatch, '--die-point', $Point, '--pause-before-halt-ms', $PauseMs) }
    Start-Client $Run c1 consume $c1Options -DockerOptions $dockerOptions
    if ($Point -eq 'kill') {
        Start-Sleep -Seconds $KillAfterS
        $killAt = Get-VmNow
        Invoke-Docker kill msa-i9-c1 | Out-Null
        Write-Harness $dir kill c1 'docker kill' -At $killAt
    } else {
        if ($PauseMs -gt 0) {
            # The worker has applied the batch and not stored it: ask the broker what it holds while the consumer is alive.
            $null = Wait-Until { (Count-Matches (Join-Path $dir 'c1.log') '"e":"halt"') -gt 0 } 60 1
            Write-Text (Join-Path $dir 'stored-during-pause.txt') (Invoke-Probe stored-offset --super $super --partitions $partitions)
        }
        $null = Wait-Until { (Invoke-Docker inspect -f '{{.State.Running}}' msa-i9-c1) -join '' -eq 'false' } 60 1
        $haltLine = Select-String -Path (Join-Path $dir 'c1.log') -Pattern '"t":(\d+),"c":"c1","e":"halt"' | Select-Object -First 1
        $haltAt = [long]$haltLine.Matches[0].Groups[1].Value
        Write-Harness $dir kill c1 "halt at batch $DieAtBatch $Point" -At ($haltAt + $PauseMs)
    }
    Start-Sleep -Seconds 2
    Write-Text (Join-Path $dir 'stored-after-crash.txt') (Invoke-Probe stored-offset --super $super --partitions $partitions)
    Start-Client $Run c2 consume ($base + @('--stop-after-s', $ObserveS))
    Write-Harness $dir note harness 'c2 started'
    $null = Wait-Until { (Invoke-Docker inspect -f '{{.State.Running}}' msa-i9-c2) -join '' -eq 'false' } ($ObserveS + 30) 1
    Write-Text (Join-Path $dir 'stored-after-restart.txt') (Invoke-Probe stored-offset --super $super --partitions $partitions)
    Copy-ContainerLogs $dir $ids
    if ($DebugClient) {
        $text = Invoke-Docker logs msa-i9-c1
        Write-Text (Join-Path $dir 'c1.debug.txt') (@($text | Where-Object { $_ -notmatch '^\{"t":' }) | Select-Object -Last 400)
    }
}
finally {
    Remove-Clients $ids
    Invoke-Probe delete --super $super --partitions $partitions | Out-Null
}
Run-Analysis $dir $partitions 'c1,c2'
Compress-Logs $dir
