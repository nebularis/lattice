# SPDX-License-Identifier: MPL-2.0
# Probe P2: publisher deduplication of the stream protocol (named producers) against the way the studio publishes (AMQP 0.9.1, confirms, no names).
#   .\p2-dedup.ps1 [-Messages 2000] [-KillAfterConfirmed 800] [-DelayMs 5]
# Cases, each on a fresh super stream of 4 partitions, each read back from the first offset and counted:
#   a    named producer, killed mid-run, restarted under the same name, the whole range published again
#   a2   as a, but the restart publishes from last-publishing-id + 1
#   b    control: the same without a name
#   c1   two live producers with the same name, odd and even ids at the same time (different partitions)
#   c1b  as c1, but both write the same partition
#   c2   two producers with the same name one after the other, ids 1000..1199 first, then 0..199
#   d    what the studio does: every message published twice over AMQP 0.9.1, each confirmed
param(
    [int]$Messages = 2000,
    [int]$KillAfterConfirmed = 800,
    [int]$DelayMs = 5
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"

$Run = 'p2-dedup'
$dir = Join-Path $Results $Run
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
New-Item -ItemType Directory -Force $dir | Out-Null
$partitions = 4
$last = $Messages - 1
$ids = @('w1', 'w2', 'wa', 'wb')
$summary = New-Object System.Collections.Generic.List[string]
$supers = @()

function Add-Line {
    param([string]$Text)
    $summary.Add($Text)
    Write-Host $Text
}

function New-Case {
    param([string]$Name)
    $s = "msa-i9-p2$Name"
    $script:supers += $s
    New-SuperStream $s $partitions
    return $s
}

function Wait-Exit {
    param([string]$Id, [int]$Seconds = 180)
    $null = Wait-Until { (Invoke-Docker inspect -f '{{.State.Running}}' "msa-i9-$Id") -join '' -eq 'false' } $Seconds 1
}

function Start-Pub {
    param([string]$Id, [string]$Super, [string[]]$Options)
    Start-Client $Run $Id dedup-pub (@('--super', $Super, '--partitions', $partitions) + $Options)
}

function Get-Confirmed {
    # Confirmed ids in a producer's log: how many, and the highest.
    param([string]$Id)
    $path = Join-Path $dir "$Id.log"
    if (-not (Test-Path $path)) { return @(0, -1) }
    $q = @(Select-String -Path $path -Pattern '"e":"cf","q":(\d+)' | ForEach-Object { [long]$_.Matches[0].Groups[1].Value })
    if ($q.Count -eq 0) { return @(0, -1) }
    return @($q.Count, ($q | Measure-Object -Maximum).Maximum)
}

function Get-Last {
    # The last-publishing-id a restarted producer logged, or what it logged instead.
    param([string]$Id)
    $path = Join-Path $dir "$Id.log"
    $m = Select-String -Path $path -Pattern 'last-publishing-id|resume-from|exception|Exception|error' | Select-Object -First 3
    return ($m | ForEach-Object { $_.Line }) -join ' | '
}

function Read-Back {
    param([string]$Case, [string]$Super, [long]$From, [long]$To)
    $out = Invoke-Probe count --super $Super --from $From --to $To --idle-s 6
    $c = @($out | Where-Object { $_ -match '"e":"count"' })
    $r = @($out | Where-Object { $_ -match '"e":"seen-ranges"' })
    Add-Line ("[$Case] " + ($c -join ' '))
    Add-Line ("[$Case] " + ($r -join ' '))
}

function Invoke-KillRestart {
    # Run a named or unnamed producer until some messages are confirmed, kill it, then run a second one with the restart options.
    param([string]$Case, [string]$Super, [string[]]$NameOptions, [string[]]$RestartOptions)
    Start-Pub w1 $Super (@($NameOptions) + @('--from', 0, '--to', $last, '--delay-ms', $DelayMs))
    $null = Wait-Until { (Get-Confirmed w1)[0] -ge $KillAfterConfirmed } 120 1
    Invoke-Docker kill msa-i9-w1 | Out-Null
    Start-Sleep -Seconds 1
    $c = Get-Confirmed w1
    Add-Line "[$Case] first producer killed, $($c[0]) confirmations logged, highest confirmed id $($c[1])"
    Start-Pub w2 $Super (@($NameOptions) + @($RestartOptions) + @('--to', $last))
    Wait-Exit w2
    $c2 = Get-Confirmed w2
    Add-Line "[$Case] second producer: $(Get-Last w2); $($c2[0]) confirmations, run to completion"
    Copy-Item (Join-Path $dir 'w1.log') (Join-Path $dir "$Case.w1.log") -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $dir 'w2.log') (Join-Path $dir "$Case.w2.log") -ErrorAction SilentlyContinue
    Remove-Clients @('w1', 'w2')
    Remove-Item (Join-Path $dir 'w1.log'), (Join-Path $dir 'w2.log') -ErrorAction SilentlyContinue
    Read-Back $Case $Super 0 $last
}

try {
    Remove-Clients $ids
    Add-Line "run ${Run}: $Messages messages per case, kill after $KillAfterConfirmed confirmations, $DelayMs ms between sends"

    $s = New-Case 'a'
    Invoke-KillRestart 'a-named-full-replay' $s @('--name', 'writer-a') @('--from', 0)

    $s = New-Case 'a2'
    Invoke-KillRestart 'a2-named-resume' $s @('--name', 'writer-a2') @('--from', 0, '--use-last', 'true')

    $s = New-Case 'b'
    Invoke-KillRestart 'b-unnamed-full-replay' $s @() @('--from', 0)

    $s = New-Case 'c1'
    Start-Pub wa $s @('--name', 'shared', '--from', 1, '--step', 2, '--to', $last, '--delay-ms', 2)
    Start-Pub wb $s @('--name', 'shared', '--from', 0, '--step', 2, '--to', ($last - 1), '--delay-ms', 2)
    Wait-Exit wa
    Wait-Exit wb
    foreach ($i in @('wa', 'wb')) {
        $c = Get-Confirmed $i
        Add-Line "[c1-live-same-name] producer $i : $($c[0]) confirmations logged; $(Get-Last $i)"
        Copy-Item (Join-Path $dir "$i.log") (Join-Path $dir "c1.$i.log") -ErrorAction SilentlyContinue
    }
    Remove-Clients @('wa', 'wb')
    Remove-Item (Join-Path $dir 'wa.log'), (Join-Path $dir 'wb.log') -ErrorAction SilentlyContinue
    Read-Back 'c1-live-same-name' $s 0 $last

    # Ids go to partition id mod 4, so odd and even ids above never meet in a partition. Here both producers write partition 0 only:
    # one sends 0, 8, 16 ... and the other 4, 12, 20 ... so the ids of each are increasing and the two interleave.
    $s = New-Case 'c1b'
    Start-Pub wa $s @('--name', 'shared', '--from', 0, '--step', 8, '--to', $last, '--delay-ms', 2)
    Start-Pub wb $s @('--name', 'shared', '--from', 4, '--step', 8, '--to', $last, '--delay-ms', 2)
    Wait-Exit wa
    Wait-Exit wb
    foreach ($i in @('wa', 'wb')) {
        $c = Get-Confirmed $i
        Add-Line "[c1b-live-same-name-same-partition] producer $i : $($c[0]) confirmations logged; $(Get-Last $i)"
        Copy-Item (Join-Path $dir "$i.log") (Join-Path $dir "c1b.$i.log") -ErrorAction SilentlyContinue
    }
    Remove-Clients @('wa', 'wb')
    Remove-Item (Join-Path $dir 'wa.log'), (Join-Path $dir 'wb.log') -ErrorAction SilentlyContinue
    $out = Invoke-Probe count --super $s --from 0 --to $last --idle-s 6
    Add-Line ('[c1b-live-same-name-same-partition] expected 500 messages (ids 0, 4, ... 1996); ' + (@($out | Where-Object { $_ -match '"e":"count"' }) -join ' '))

    $s = New-Case 'c2'
    Start-Pub wa $s @('--name', 'shared', '--from', 1000, '--to', 1199)
    Wait-Exit wa
    Start-Pub wb $s @('--name', 'shared', '--from', 0, '--to', 199)
    Wait-Exit wb
    foreach ($i in @('wa', 'wb')) {
        $c = Get-Confirmed $i
        Add-Line "[c2-sequential-same-name] producer $i : $($c[0]) confirmations logged; $(Get-Last $i)"
        Copy-Item (Join-Path $dir "$i.log") (Join-Path $dir "c2.$i.log") -ErrorAction SilentlyContinue
    }
    Remove-Clients @('wa', 'wb')
    Remove-Item (Join-Path $dir 'wa.log'), (Join-Path $dir 'wb.log') -ErrorAction SilentlyContinue
    $seq = Invoke-Probe count --super $s --from 0 --to 1199 --idle-s 6
    Add-Line ('[c2-sequential-same-name] ' + (@($seq | Where-Object { $_ -match '"e":"(count|seen-ranges)"' }) -join ' '))

    $s = New-Case 'd'
    $out = Invoke-Probe amqp-dup --super $s --partitions $partitions --n 100
    Add-Line ('[d-amqp-twice] ' + ($out -join ' '))
    Read-Back 'd-amqp-twice' $s 0 99
}
finally {
    Remove-Clients $ids
    foreach ($s in $supers) { Invoke-Probe delete --super $s --partitions $partitions | Out-Null }
    Write-Text (Join-Path $dir 'summary.txt') $summary
}
