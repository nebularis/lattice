# SPDX-License-Identifier: MPL-2.0
# Probe P1: two consumers of one super stream in the studio's single active consumer group, an abrupt stop of one of them (kill)
# or a network partition of one of them (partition). The cluster must be up (cluster-up.ps1).
#   .\p1.ps1 -Mode kill -Run p1-kill-1
#   .\p1.ps1 -Mode partition -Run p1-partition-1 [-HeartbeatS 60] [-CutSeconds 10] [-Rate 150]
param(
    [ValidateSet('kill', 'partition')][string]$Mode = 'partition',
    [Parameter(Mandatory)][string]$Run,
    [int]$HeartbeatS = 0,
    [int]$CutSeconds = 10,
    [int]$Rate = 150,
    [int]$BatchMs = 300,
    [int]$MessageMs = 5,
    [int]$TakeoverTimeoutS = 260,
    [int]$ObserveS = 20,
    [switch]$DebugClient
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"

$dir = Join-Path $Results $Run
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
New-Item -ItemType Directory -Force $dir | Out-Null
$super = "msa-i9-w-$($Run -replace '[^a-z0-9]', '')"
$partitions = 8
$ids = @('c1', 'c2', 'pub')
Remove-Clients $ids
New-SuperStream $super $partitions

$consumeOptions = @('--super', $super, '--uris', 'rabbitmq-stream://guest:guest@msa-i9-rmq1:5552', '--batch-ms', $BatchMs, '--message-ms', $MessageMs)
if ($HeartbeatS -gt 0) { $consumeOptions += @('--heartbeat-s', $HeartbeatS) }

$dockerOptions = @()
if ($DebugClient) { $dockerOptions = @('-e', 'JAVA_TOOL_OPTIONS=-Dorg.slf4j.simpleLogger.log.com.rabbitmq.stream.impl.StreamConsumer=debug') }

try {
    Write-Harness $dir note harness "run $Run mode $Mode heartbeat $HeartbeatS rate $Rate batchms $BatchMs messagems $MessageMs"
    Start-Client $Run c1 consume $consumeOptions $dockerOptions
    Start-Sleep -Seconds 6
    Start-Client $Run c2 consume $consumeOptions $dockerOptions
    Start-Sleep -Seconds 4
    Start-Client $Run pub publish @('--super', $super, '--amqp', 'msa-i9-rmq1', '--rate', $Rate, '--duration-s', 900)
    $log1 = Join-Path $dir 'c1.log'
    $log2 = Join-Path $dir 'c2.log'
    if (-not (Wait-Until { (Distinct-Partitions $log1) + (Distinct-Partitions $log2) -ge 8 -and (Count-Matches $log1 '"e":"ap"') -gt 50 -and (Count-Matches $log2 '"e":"ap"') -gt 50 } 60)) {
        Write-Harness $dir note harness 'both consumers were not active in 60 s'
    }
    Start-Sleep -Seconds 8
    $before = Get-GroupView $super $partitions
    Write-Text (Join-Path $dir 'broker-view-before.txt') $before
    $c1Parts = Distinct-Partitions $log1
    $c2Before = Distinct-Partitions $log2
    Write-Harness $dir note harness "before the fault c1 has seen $c1Parts partitions and c2 $c2Before"

    $faultAt = Get-VmNow
    if ($Mode -eq 'kill') {
        Invoke-Docker kill msa-i9-c1 | Out-Null
        Write-Harness $dir kill c1 'docker kill' -At $faultAt
    } else {
        Invoke-Docker network disconnect $Net msa-i9-c1 | Out-Null
        Write-Harness $dir cut c1 'docker network disconnect' -At $faultAt
    }
    $cutAt = Get-Date
    $target = 8
    $took = Wait-Until { (Distinct-Partitions $log2) -ge $target } $TakeoverTimeoutS 1
    $elapsed = [int]((Get-Date) - $cutAt).TotalSeconds
    Write-Harness $dir note harness "c2 has seen $(Distinct-Partitions $log2) partitions after $elapsed s, all partitions: $took"
    Write-Text (Join-Path $dir 'broker-view-after-takeover.txt') (Get-GroupView $super $partitions)

    if ($Mode -eq 'partition') {
        Start-Sleep -Seconds $CutSeconds
        $healAt = Get-VmNow
        Invoke-Docker network connect $Net msa-i9-c1 | Out-Null
        Write-Harness $dir heal c1 'docker network connect' -At $healAt
        Start-Sleep -Seconds $ObserveS
        Write-Text (Join-Path $dir 'broker-view-after-heal.txt') (Get-GroupView $super $partitions)
    } else {
        Start-Sleep -Seconds $ObserveS
    }
    Invoke-Docker rm -f msa-i9-pub | Out-Null
    Write-Harness $dir note harness 'publisher stopped'
    Start-Sleep -Seconds 8
    Copy-ContainerLogs $dir $ids
}
finally {
    Remove-Clients $ids
    Invoke-Probe delete --super $super --partitions $partitions | Out-Null
}
Run-Analysis $dir $partitions
Compress-Logs $dir
