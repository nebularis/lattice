# SPDX-License-Identifier: MPL-2.0
# Probe P3b: loss of a broker node that leads some of the partitions of a super stream, with two consumers in the studio's single
# active consumer group and the studio's AMQP 0.9.1 publisher with confirms. The cluster must be up (cluster-up.ps1).
#   .\p3-leader-kill.ps1 -Run p3-leader-kill-2 -KillNode 2
#   .\p3-leader-kill.ps1 -Run p3-leader-kill-1 -KillNode 1     (node 1 is also the first node the publisher and the clients try)
# Leaders are spread: partition i is declared over a connection to node (i mod 3) + 1. The killed node is started again at the end.
param(
    [Parameter(Mandatory)][string]$Run,
    [ValidateSet(1, 2, 3)][int]$KillNode = 2,
    [int]$Rate = 150,
    [int]$BatchMs = 100,
    [int]$MessageMs = 3,
    [int]$ObserveS = 40,
    [ValidateSet('context', 'env')][string]$StoreVia = 'env',
    [switch]$DebugClient
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"

$dir = Join-Path $Results $Run
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
New-Item -ItemType Directory -Force $dir | Out-Null
$super = "msa-i9-l-$($Run -replace '[^a-z0-9]', '')"
$partitions = 8
$ids = @('c1', 'c2', 'pub')
$alive = if ($KillNode -eq 1) { 2 } else { 1 }
$uris = 'rabbitmq-stream://guest:guest@msa-i9-rmq1:5552,rabbitmq-stream://guest:guest@msa-i9-rmq2:5552,rabbitmq-stream://guest:guest@msa-i9-rmq3:5552'
$hosts = 'msa-i9-rmq1,msa-i9-rmq2,msa-i9-rmq3'
$dockerOptions = @()
if ($DebugClient) { $dockerOptions = @('-e', 'JAVA_TOOL_OPTIONS=-Dorg.slf4j.simpleLogger.defaultLogLevel=info -Dorg.slf4j.simpleLogger.log.com.rabbitmq.stream=debug') }

function Get-Leaders {
    param([int]$Node)
    $rows = Invoke-Docker exec "msa-i9-rmq$Node" rabbitmqctl -q list_queues name leader
    return @($rows | Where-Object { $_ -like "$super-*" } | Sort-Object)
}

Remove-Clients $ids
New-SuperStream $super $partitions -Spread
$consumeOptions = @('--super', $super, '--uris', $uris, '--batch-ms', $BatchMs, '--message-ms', $MessageMs, '--store-via', $StoreVia)

try {
    Write-Harness $dir note harness "run $Run kill node $KillNode rate $Rate batchms $BatchMs storevia $StoreVia"
    $before = Get-Leaders $alive
    Write-Text (Join-Path $dir 'leaders-before.txt') $before
    Start-Client $Run c1 consume $consumeOptions -DockerOptions $dockerOptions
    Start-Sleep -Seconds 6
    Start-Client $Run c2 consume $consumeOptions -DockerOptions $dockerOptions
    Start-Sleep -Seconds 4
    Start-Client $Run pub publish @('--super', $super, '--amqp', $hosts, '--rate', $Rate, '--duration-s', 900)
    $log1 = Join-Path $dir 'c1.log'
    $log2 = Join-Path $dir 'c2.log'
    if (-not (Wait-Until { (Distinct-Partitions $log1) + (Distinct-Partitions $log2) -ge 8 -and (Count-Matches $log1 '"e":"ap"') -gt 50 -and (Count-Matches $log2 '"e":"ap"') -gt 50 } 90)) {
        Write-Harness $dir note harness 'both consumers were not active in 90 s'
    }
    Start-Sleep -Seconds 8
    Write-Text (Join-Path $dir 'broker-view-before.txt') (Get-GroupView $super $partitions)
    Write-Harness $dir note harness "before the fault c1 has seen $(Distinct-Partitions $log1) partitions and c2 $(Distinct-Partitions $log2)"

    $faultAt = Get-VmNow
    Invoke-Docker kill "msa-i9-rmq$KillNode" | Out-Null
    Write-Harness $dir kill "rmq$KillNode" 'docker kill of the broker node' -At $faultAt
    $t0 = Get-Date
    $elected = Wait-Until { -not (@(Get-Leaders $alive) -match "rmq$KillNode") -and @(Get-Leaders $alive).Count -eq $partitions } 120 1
    $took = [int]((Get-Date) - $t0).TotalSeconds
    Write-Harness $dir note harness "leaders off the killed node after about $took s (all elected: $elected)"
    Write-Text (Join-Path $dir 'leaders-after.txt') (Get-Leaders $alive)
    Start-Sleep -Seconds $ObserveS
    Write-Text (Join-Path $dir 'broker-view-after.txt') (Get-GroupView $super $partitions)

    Invoke-Docker start "msa-i9-rmq$KillNode" | Out-Null
    $up = Wait-Node $KillNode 120
    Write-Harness $dir note harness "node $KillNode started again, listening: $up"
    Start-Sleep -Seconds 15
    Write-Text (Join-Path $dir 'cluster-after-restart.txt') (Invoke-Docker exec "msa-i9-rmq$alive" rabbitmqctl -q list_queues name leader members online)
    Invoke-Docker rm -f msa-i9-pub | Out-Null
    Write-Harness $dir note harness 'publisher stopped'
    Start-Sleep -Seconds 10
    Copy-ContainerLogs $dir $ids
}
finally {
    Remove-Clients $ids
}

# Every sequence number the publisher saw confirmed against what the stream holds afterwards.
$pubLog = Join-Path $dir 'pub.log'
$confirmed = New-Object System.Collections.Generic.HashSet[long]
$maxConfirmed = -1
foreach ($m in (Select-String -Path $pubLog -Pattern '"e":"conf","from":(\d+),"to":(\d+)')) {
    $from = [long]$m.Matches[0].Groups[1].Value
    $to = [long]$m.Matches[0].Groups[2].Value
    for ($q = $from; $q -le $to; $q++) { [void]$confirmed.Add($q) }
    if ($to -gt $maxConfirmed) { $maxConfirmed = $to }
}
$unknown = @(Select-String -Path $pubLog -Pattern '"e":"unk"')
$out = Invoke-Probe count --super $super --from 0 --to $maxConfirmed --idle-s 8 --uris $uris
$summary = New-Object System.Collections.Generic.List[string]
$count = @($out | Where-Object { $_ -match '"e":"count"' })
$summary.Add("stream read back: $($count -join ' ')")
$rangeText = ([regex]::Match(($out -join "`n"), '"ranges":"([^"]*)"')).Groups[1].Value
$seen = New-Object System.Collections.Generic.HashSet[long]
foreach ($r in ($rangeText -split ',')) {
    if ($r -match '^(\d+)-(\d+)$') { for ($q = [long]$Matches[1]; $q -le [long]$Matches[2]; $q++) { [void]$seen.Add($q) } }
}
$lost = New-Object System.Collections.Generic.List[long]
foreach ($q in $confirmed) { if (-not $seen.Contains($q)) { $lost.Add($q) } }
$summary.Add("publisher: $($confirmed.Count) sequence numbers confirmed (highest $maxConfirmed), $($unknown.Count) unconfirmed batches logged")
$summary.Add("CONFIRMED BUT NOT IN THE STREAM: $($lost.Count)" + $(if ($lost.Count -gt 0) { ' e.g. ' + (($lost | Select-Object -First 20) -join ' ') } else { '' }))
$unkLines = @($unknown | ForEach-Object { $_.Line })
if ($unkLines.Count -gt 0) {
    $first = [long]([regex]::Match($unkLines[0], '"t":(\d+)').Groups[1].Value)
    $lastU = [long]([regex]::Match($unkLines[-1], '"t":(\d+)').Groups[1].Value)
    $summary.Add("publisher saw failures from t+$($first - $faultAt) ms to t+$($lastU - $faultAt) ms of the node kill; first error: " + ($unkLines[0] -replace '^.*"err":', ''))
}
$connected = @(Select-String -Path $pubLog -Pattern '"e":"pub-connected"' | ForEach-Object { $_.Line })
$summary.Add("publisher connections: $($connected.Count) ($(($connected | ForEach-Object { [regex]::Match($_, '"node":"([^"]*)"').Groups[1].Value }) -join ' '))")
Write-Text (Join-Path $dir 'readback.txt') $summary
$summary | ForEach-Object { Write-Host $_ }

Invoke-Probe delete --super $super --partitions $partitions | Out-Null
Run-Analysis $dir $partitions
Compress-Logs $dir
